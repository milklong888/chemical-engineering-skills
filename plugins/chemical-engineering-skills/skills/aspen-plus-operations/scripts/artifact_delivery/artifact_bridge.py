"""Deliver explicit immutable file snapshots over a bounded loopback HTTP server.

MIT license. This repairs a file-delivery route, not a desktop application's code.
Only the Python standard library is required. No directory is served.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import mimetypes
from pathlib import Path
import secrets
import socket
import threading
import time
from urllib.parse import quote, urlsplit


@dataclass(frozen=True)
class Artifact:
    name: str
    label: str
    content: bytes

    def __post_init__(self):
        if not isinstance(self.name, str) or not isinstance(self.label, str) or not isinstance(self.content, bytes):
            raise TypeError("Artifact requires text names/labels and immutable bytes")
        if not self.name or any(c in self.name for c in "\r\n/\\"):
            raise ValueError("Artifact name must be a single filename without control characters")
        if any(ord(c) < 32 for c in self.name):
            raise ValueError("Artifact name contains a control character")

    @property
    def sha256(self):
        return hashlib.sha256(self.content).hexdigest()


def load_artifacts(files: list[dict], max_bytes: int = 64 * 1024 * 1024):
    if not files or max_bytes <= 0:
        raise ValueError("Explicit files and a positive byte limit are required")
    artifacts = []
    total = 0
    for item in files:
        path = Path(item["path"]).resolve(strict=True)
        if not path.is_file():
            raise ValueError("Only explicit regular files may be delivered")
        name = item.get("name", path.name)
        # Bound the actual read, rather than trusting a possibly stale stat size.
        with path.open("rb") as stream:
            content = stream.read(max_bytes - total + 1)
        total += len(content)
        if total > max_bytes:
            raise ValueError("Artifact snapshots exceed the configured byte limit")
        artifacts.append(Artifact(name, item.get("label", name), content))
    if len({a.name for a in artifacts}) != len(artifacts):
        raise ValueError("Artifact filenames must be unique")
    return artifacts


class _SnapshotServer(ThreadingHTTPServer):
    # Non-daemon handlers are joined by server_close after their sockets close.
    daemon_threads = False

    def __init__(self, *args):
        self.connections = set()
        self.connection_guard = threading.Lock()
        super().__init__(*args)

    def get_request(self):
        request, address = super().get_request()
        request.settimeout(5)
        with self.connection_guard:
            self.connections.add(request)
        return request, address

    def shutdown_request(self, request):
        try:
            super().shutdown_request(request)
        finally:
            with self.connection_guard:
                self.connections.discard(request)

    def close_connections(self):
        with self.connection_guard:
            sockets = tuple(self.connections)
        for request in sockets:
            try:
                request.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            request.close()


class ArtifactBridge:
    def __init__(self, artifacts, *, idle_seconds=1800, lifetime_seconds=7200):
        if not artifacts or not all(math.isfinite(t) and t > 0 for t in (idle_seconds, lifetime_seconds)):
            raise ValueError("Artifacts and positive lifetimes are required")
        if len({a.name for a in artifacts}) != len(artifacts):
            raise ValueError("Artifact filenames must be unique")
        self.artifacts = tuple(artifacts)
        self.idle_seconds = float(idle_seconds)
        self.lifetime_seconds = float(lifetime_seconds)
        self.token = secrets.token_urlsafe(24)
        self.started = self.last_access = time.monotonic()
        self.closed = threading.Event()
        self._guard = threading.Lock()
        self._close_guard = threading.Lock()
        self._started = False
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def handle(self):
                try:
                    super().handle()
                except OSError:
                    pass  # A peer or shutdown can close a live request socket.

            def log_message(self, *args):
                pass  # Avoid logging private filenames or capability URLs.

            def do_GET(self):
                self.deliver(False)

            def do_HEAD(self):
                self.deliver(True)

            def do_POST(self):
                self.send_error(405)

            def deliver(self, head):
                expected = {f"127.0.0.1:{bridge.port}", f"localhost:{bridge.port}"}
                if self.headers.get("Host") not in expected:
                    self.send_error(421)
                    return
                path = urlsplit(self.path).path
                prefix = f"/{bridge.token}/"
                routes = {prefix + quote(a.name, safe=""): a for a in bridge.artifacts}
                if path == prefix:
                    body = bridge.index_html().encode("utf-8")
                    media = "text/html; charset=utf-8"
                    artifact = None
                elif path in routes:
                    artifact = routes[path]
                    body = artifact.content
                    media = mimetypes.guess_type(artifact.name)[0] or "application/octet-stream"
                else:
                    self.send_error(404)
                    return
                with bridge._guard:
                    bridge.last_access = time.monotonic()
                self.send_response(200)
                self.send_header("Content-Type", media)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Content-Type-Options", "nosniff")
                if artifact:
                    self.send_header("Content-Disposition", "attachment; filename=artifact; filename*=UTF-8''" + quote(artifact.name, safe=""))
                    self.send_header("X-Artifact-SHA256", artifact.sha256)
                else:
                    self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'")
                self.end_headers()
                if not head:
                    try:
                        self.wfile.write(body)
                    except (BrokenPipeError, ConnectionResetError):
                        pass

        self.server = _SnapshotServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}/{self.token}/"

    def index_html(self):
        items = "".join(
            f'<li><a href="{quote(a.name, safe="")}">{html.escape(a.label)}</a> '
            f'({len(a.content)} bytes)<small> SHA256: {a.sha256}</small></li>'
            for a in self.artifacts
        )
        return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>本地交付文件</title><style>body{font:18px system-ui;max-width:900px;margin:48px auto;padding:16px}li{margin:24px 0}small{display:block;font-size:12px;overflow-wrap:anywhere}</style><h1>本地交付文件</h1><p>仅提供本次明确选择的文件快照。下载后可按 SHA256 核对。</p><ul>' + items + '</ul><p>空闲超时或达到总时限后，服务自动退出。需要再次交付时重新启动脚本。</p></html>'

    def manifest(self):
        return {
            "schema": "local-artifact-bridge-v1", "index_url": self.url,
            "idle_seconds": self.idle_seconds, "lifetime_seconds": self.lifetime_seconds,
            "artifacts": [{"name": a.name, "label": a.label, "size": len(a.content),
                           "sha256": a.sha256, "url": self.url + quote(a.name, safe="")}
                          for a in self.artifacts],
        }

    def start(self):
        if self._started or self.closed.is_set():
            raise RuntimeError("Bridge has already started or closed")
        self._started = True
        self._serving = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .1}, daemon=True)
        self._serving.start()

        def expire():
            while not self.closed.wait(.1):
                now = time.monotonic()
                with self._guard:
                    idle = now - self.last_access
                if idle >= self.idle_seconds or now - self.started >= self.lifetime_seconds:
                    self.close()
                    break
        self._expiry = threading.Thread(target=expire, daemon=True)
        self._expiry.start()
        return self.manifest()

    def close(self):
        with self._close_guard:
            if self.closed.is_set():
                return
            if self._started:
                self.server.shutdown()
                self._serving.join(timeout=2)
            self.server.close_connections()
            self.server.server_close()
            self.closed.set()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    artifacts = load_artifacts(config["files"], config.get("max_bytes", 64 * 1024 * 1024))
    bridge = ArtifactBridge(artifacts, idle_seconds=config.get("idle_seconds", 1800), lifetime_seconds=config.get("lifetime_seconds", 7200))
    receipt = None
    try:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt = bridge.start()
        args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"index_url": bridge.url}), flush=True)
        while not bridge.closed.wait(.5):
            pass
    except KeyboardInterrupt:
        pass
    finally:
        bridge.close()
        if receipt is not None and args.receipt.exists():
            receipt["state"] = "closed"
            args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
