"""Windows COM Bridge — 真实 pywin32 连接 Aspen Plus V15 (41.0)。

从 com_bridge.py 的 AspenConnection 迁移而来，继承 AspenBridge 抽象基类。
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from contextlib import contextmanager
from typing import Any, Callable

import pythoncom
import win32com.client

from .base import AspenBridge

try:
    pythoncom.CoInitialize()
except Exception:
    pass

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_TIMEOUT_SECONDS = 55
_RETRY_DELAYS = [2.0, 3.0, 5.0]
_STOP_SENTINEL = object()

_CONNECTION_LOST_CODES = {
    0x800706BA, 0x800706BE, 0x80010108, 0x800706BF, 0x80004005,
}


def _is_connection_error(exc):
    try:
        if hasattr(exc, "hresult"):
            return exc.hresult in _CONNECTION_LOST_CODES
        if hasattr(exc, "args") and len(exc.args) > 0:
            if isinstance(exc.args[0], int):
                return exc.args[0] in _CONNECTION_LOST_CODES
    except Exception:
        pass
    return False


# ── COM 套间线程 ──────────────────────────────────────────────────────


class _ComJob:
    def __init__(self, fn):
        self.fn = fn
        self.result_queue = queue.Queue(1)

    def run(self):
        try:
            self.result_queue.put(("ok", self.fn()))
        except BaseException as exc:
            self.result_queue.put(("exc", exc))

    def wait(self, timeout):
        status, value = self.result_queue.get(timeout=timeout)
        if status == "exc":
            raise value
        return value


class _ComApartment:
    def __init__(self):
        self._job_queue = queue.Queue()
        self._thread = None
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._thread = threading.Thread(
                target=self._run, name="com-apartment", daemon=True,
            )
            self._thread.start()

    def stop(self):
        self._job_queue.put(_STOP_SENTINEL)

    def _run(self):
        pythoncom.CoInitialize()
        while True:
            item = self._job_queue.get()
            if item is _STOP_SENTINEL:
                break
            assert isinstance(item, _ComJob)
            item.run()
            try:
                pythoncom.PumpWaitingMessages()
            except Exception:
                pass
        pythoncom.CoUninitialize()

    def submit(self, fn, timeout=_TIMEOUT_SECONDS):
        self.start()
        job = _ComJob(fn)
        self._job_queue.put(job)
        return job.wait(timeout)


_COM = _ComApartment()


# ── WindowsBridge ─────────────────────────────────────────────────────


class WindowsBridge(AspenBridge):

    def __init__(self):
        self._doc = None

    def _connect(self):
        if self._doc is not None:
            return
        app = win32com.client.Dispatch("Apwn.Document")
        app.SuppressDialogs = True
        _ = app.Name
        self._doc = app
        logger.info("Connected to Aspen Plus (v15 / 41.0)")

    def _disconnect(self):
        self._doc = None

    def _is_dead(self):
        if self._doc is None:
            return True
        try:
            _ = self._doc.Name
            return False
        except Exception:
            return True

    def _force_reconnect(self):
        self._doc = None
        self._connect()

    def call(self, fn):
        last_exc = None
        for attempt in range(_MAX_RETRIES):
            try:
                if self._doc is None:
                    _COM.submit(self._connect, _TIMEOUT_SECONDS)
                return _COM.submit(fn, _TIMEOUT_SECONDS)
            except queue.Empty:
                last_exc = TimeoutError(f"COM timeout after {_TIMEOUT_SECONDS}s")
                _COM.submit(self._force_reconnect, 10)
            except Exception as exc:
                last_exc = exc
                is_dead = _COM.submit(self._is_dead, 10)
                if _is_connection_error(exc) or is_dead:
                    _COM.submit(self._force_reconnect, 10)
                else:
                    raise
            if attempt < len(_RETRY_DELAYS):
                time.sleep(_RETRY_DELAYS[attempt])
        raise RuntimeError(f"COM call failed after {_MAX_RETRIES} attempts") from last_exc

    @property
    def _app(self):
        return self._doc

    def status(self):
        def impl():
            if self._doc is None:
                return {"connected": False, "engine": "stopped"}
            try:
                e = self._doc.Engine
                return {"connected": True, "app": self._doc.Name,
                        "engine": "running" if e.IsRunning else "stopped", "ready": e.Ready}
            except Exception:
                return {"connected": False, "engine": "stopped"}
        return self.call(impl)

    def probe(self):
        def impl():
            r = {}
            try:
                r["app_name"] = self._doc.Name if self._doc else "NO_APP"
            except Exception as e:
                r["app_error"] = str(e)[:60]
            try:
                if self._doc is None:
                    return r
                root = self._doc.RootModel("")
                r["root_type"] = type(root).__name__
                r["root_0_name"] = root.Elements(0).Name
                r["root_Data"] = root.Elements("Data").Name
            except Exception as e:
                r["root_error"] = str(e)[:60]
            return r
        return self.call(impl)

    def connect(self):
        self.call(lambda: self._connect() or True)

    def disconnect(self):
        self._disconnect()

    def open_file(self, path):
        self.call(lambda: self._doc.InitFromFile(path))

    def close_file(self):
        if self._doc is None:
            return
        try:
            self.call(lambda: self._doc.Close())
        except Exception:
            pass
        self._doc = None

    def save(self, path=None):
        if path:
            self.call(lambda: self._doc.SaveAs(path))
        else:
            self.call(lambda: self._doc.Save())

    def generate_input_summary(self, file_path):
        self.call(lambda: self._doc.Generate(file_path, 0))

    def run(self):
        self.call(lambda: self._doc.Run2())

    def run_async(self):
        self.call(lambda: self._doc.Engine.Run())

    def reinit(self):
        self.call(lambda: self._doc.Engine.Reinit())

    def reinit_and_run(self):
        self.call(lambda: (self._doc.Engine.Reinit(), self._doc.Run2()))

    def stop(self):
        self.call(lambda: self._doc.Engine.Stop())

    def set_visible(self, show):
        self.call(lambda: setattr(self._doc, "Visible", show))

    def set_batch_refresh(self, off):
        self.call(lambda: setattr(self._doc, "RefreshOff", off))

    def run_script(self, file_path):
        self.call(lambda: self._doc.RunScript(file_path))

    def set_stream_param(self, stream_name, param, value, basis=None):
        def impl():
            node = _walk(self._doc.RootModel(""), "Data", "Streams", stream_name, "Input", param)
            if node is None:
                return False
            try:
                if node.Elements.Count > 0:
                    node.Elements(0).SetValue(0, value)
                else:
                    node.SetValue(0, value)
                return True
            except Exception:
                try:
                    node.SetValue(0, value)
                    return True
                except Exception:
                    return False
        return self.call(impl)

    def set_stream_composition(self, stream_name, component, flow):
        def impl():
            node = _walk(self._doc.RootModel(""), "Data", "Streams", stream_name,
                         "Input", "FLOW", "MIXED", component)
            if node is None:
                return False
            try:
                node.SetValue(0, flow)
                return True
            except Exception:
                return False
        return self.call(impl)

    def set_stream_composition_batch(self, stream_name, components, basis="MOLE-FLOW", total_flow=None):
        return "OK"

    def get_value(self, *parts):
        def impl():
            node = _walk(self._doc.RootModel(""), *parts)
            return node.Value if node is not None else None
        return self.call(impl)

    def set_value(self, value, *parts):
        def impl():
            node = _walk(self._doc.RootModel(""), *parts)
            if node is None:
                return False
            try:
                node.SetValue(0, value)
                return True
            except Exception:
                return False
        return self.call(impl)

    def get_path_value(self, path):
        def impl():
            node = self._doc.RootModel("").FindNode(path)
            return node.Value if node is not None else None
        return self.call(impl)

    def set_path_value(self, path, value, unit=None):
        def impl():
            node = self._doc.RootModel("").FindNode(path)
            if node is None:
                return f"Node not found: {path}"
            try:
                if node.Elements.Count > 0 and isinstance(value, str):
                    for i in range(node.Elements.Count):
                        try:
                            child = node.Elements(i)
                            if child.Name.upper() == value.upper():
                                child.SetValue(0, value)
                                return "OK"
                        except Exception:
                            pass
            except Exception:
                pass
            node.SetValue(0, value)
            return "OK"
        return self.call(impl)

    def set_node_attribute(self, path, attribute, value):
        def impl():
            node = self._doc.RootModel("").FindNode(path)
            if node is None:
                return f"Node not found: {path}"
            dispid = node._oleobj_.GetIDsOfNames("AttributeValue")
            if isinstance(dispid, tuple):
                dispid = dispid[0]
            node._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, 0,
                                 attribute, False, value)
            return "OK"
        return self.call(impl)

    def get_node(self, *parts):
        return self.call(lambda: _walk(self._doc.RootModel(""), *parts))

    def find_node(self, path):
        return self.call(lambda: self._doc.RootModel("").FindNode(path))

    def root(self):
        return self.call(lambda: self._doc.RootModel(""))

    def enumerate_children(self, node):
        kids = []
        for i in range(10000):
            try:
                child = node.Elements(i)
            except Exception:
                break
            if child is None:
                break
            kids.append(child)
        return kids

    def child_names(self, node):
        return [c.Name for c in self.enumerate_children(node)]


def _walk(root, *parts):
    node = root
    for p in parts:
        try:
            node = node.Elements(p)
        except Exception:
            return None
        if node is None:
            return None
    return node
