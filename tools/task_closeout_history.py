"""Advance the project-local current closeout record independently of old receipts."""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

from tools.task_closeout import STATE_SCHEMA, effective_upload_authorizations, json_ref, require, text, transition


HISTORY = "PROJECT_TASK_CLOSEOUT.sqlite3"
_BATCH_MESSAGE_ACTIONS = {"batch_presented", "approve_upload"}
_MESSAGE_ACTIONS = {"delivery_sent", "reply"} | _BATCH_MESSAGE_ACTIONS


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _receipt_body(state):
    return {key: value for key, value in state.items() if key != "history_sequence"}


def _connect(path, *, readonly=False):
    location = path.as_uri() + "?mode=ro" if readonly else path
    db = sqlite3.connect(location, uri=readonly, timeout=30, isolation_level=None)
    db.row_factory = sqlite3.Row
    return db


def _register(db):
    db.execute("""CREATE TABLE IF NOT EXISTS task_heads (
        task_id TEXT PRIMARY KEY, sequence INTEGER NOT NULL, state TEXT NOT NULL,
        state_sha256 TEXT NOT NULL, previous_sha256 TEXT, request_sha256 TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS displayed_batches (
        task_id TEXT NOT NULL, revision INTEGER NOT NULL, batch_sha256 TEXT NOT NULL,
        PRIMARY KEY(task_id, revision, batch_sha256))""")
    db.execute("""CREATE TABLE IF NOT EXISTS message_events (
        task_id TEXT NOT NULL, actor TEXT NOT NULL, message_id TEXT NOT NULL, revision INTEGER NOT NULL,
        operation TEXT NOT NULL, source_sha256 TEXT NOT NULL, batch_sha256 TEXT,
        PRIMARY KEY(task_id, actor, message_id))""")


def _current(db, task_id):
    row = db.execute("SELECT * FROM task_heads WHERE task_id=?", (task_id,)).fetchone()
    if row is None:
        return None, None
    state = json.loads(row["state"])
    require(isinstance(state, dict) and state.get("schema") == STATE_SCHEMA and state.get("task_id") == task_id
            and state.get("history_sequence") == row["sequence"] and _digest(state) == row["state_sha256"],
            "The registered task closeout state has changed")
    return row, state


def _verify_previous(request, root):
    return json_ref(root, request["previous_ref"]) if "previous_ref" in request else None


def _status(request, root, path):
    task_id = request["task_id"]
    previous = _verify_previous(request, root)
    if path.is_file():
        with closing(_connect(path, readonly=True)) as db:
            ready = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='task_heads'").fetchone()
            row, state = _current(db, task_id) if ready is not None else (None, None)
        if state is not None:
            effective = effective_upload_authorizations(state, root)
            require(previous is None or _digest(previous) in {row["state_sha256"], _digest(effective)},
                    "The supplied closeout receipt is stale")
            return effective
    require(previous is None, "The supplied receipt is not the registered task head")
    return {"schema": STATE_SCHEMA, "task_id": task_id, "status": "NO_CLOSEOUT_STATE"}


def _record_message(db, request, root):
    operation = request["operation"]
    if operation not in _MESSAGE_ACTIONS:
        return
    source_ref = request["message_ref"]
    message = json_ref(root, source_ref)
    task_id, revision = request["task_id"], request["task_revision"]
    require(message.get("task_id", task_id) == task_id and message.get("task_revision", revision) == revision,
            "The host message identifies another task or revision")
    key = task_id, message["actor"], message["source_message_id"]
    batch_sha = request.get("batch_sha256") if operation in _BATCH_MESSAGE_ACTIONS else None
    binding = revision, operation, source_ref["sha256"].lower(), batch_sha
    previous = db.execute("""SELECT revision, operation, source_sha256, batch_sha256 FROM message_events
                          WHERE task_id=? AND actor=? AND message_id=?""", key).fetchone()
    if previous is not None:
        require(tuple(previous) == binding, "This host message was already recorded for a different revision, operation or batch")
        return
    db.execute("INSERT INTO message_events VALUES (?, ?, ?, ?, ?, ?, ?)", (*key, *binding))


def _record_batch(db, request, previous, result):
    if request["operation"] != "retrospective":
        return
    digest = result["batch"]["sha256"]
    active = previous.get("batch") if previous else None
    if active is not None and active["sha256"] == digest:
        return
    key = request["task_id"], request["task_revision"], digest
    found = db.execute("SELECT 1 FROM displayed_batches WHERE task_id=? AND revision=? AND batch_sha256=?", key)
    require(found.fetchone() is None, "An older displayed batch cannot be restored as the current batch")
    db.execute("INSERT INTO displayed_batches VALUES (?, ?, ?)", key)


def advance_closeout(request, evidence_root):
    """Validate, advance and persist the exact current task head in one transaction."""
    require(isinstance(request, dict) and text(request.get("task_id")), "Bind the current task ID")
    root = Path(evidence_root).resolve()
    path = root / HISTORY
    require(path.resolve().parent == root, "Keep the task closeout register beneath the evidence root")
    try:
        if request.get("operation") == "status":
            return _status(request, root, path)
        task_id = request["task_id"]
        previous = _verify_previous(request, root)
        request_sha = _digest({key: value for key, value in request.items() if key != "previous_ref"})
        with closing(_connect(path)) as db:
            db.execute("BEGIN IMMEDIATE")
            _register(db)
            row, active = _current(db, task_id)
            previous_sha = _digest(previous) if previous is not None else None
            active_sha = row["state_sha256"] if row is not None else None
            effective = effective_upload_authorizations(active, root)
            effective_sha = _digest(effective) if effective is not None else None
            if previous is not None and previous_sha not in {active_sha, effective_sha}:
                # Accept only an exact retry of the transition that produced the still-current head.
                if row is not None and previous_sha == row["previous_sha256"] and request_sha == row["request_sha256"]:
                    repeated = transition(request, previous, root)
                    require(_receipt_body(repeated) == _receipt_body(effective),
                            "The previous receipt no longer reproduces the current result")
                    db.rollback()
                    return effective
                raise ValueError("The supplied closeout receipt is stale or is not a registered task head")
            result = transition(request, effective, root)
            if result["status"] == "DELIVERY_QUESTION_MISSING":
                db.commit()
                return result
            _record_message(db, request, root)
            _record_batch(db, request, active, result)
            if active is not None and _receipt_body(result) == _receipt_body(active):
                db.commit()
                return active
            sequence = 1 if row is None else row["sequence"] + 1
            result["history_sequence"] = sequence
            db.execute("""INSERT INTO task_heads VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT(task_id) DO UPDATE SET sequence=excluded.sequence, state=excluded.state,
                       state_sha256=excluded.state_sha256, previous_sha256=excluded.previous_sha256,
                       request_sha256=excluded.request_sha256""",
                       (task_id, sequence, _json(result), _digest(result), previous_sha or active_sha, request_sha))
            db.commit()
            return result
    except sqlite3.Error as exc:
        raise ValueError(f"The local task closeout register is unavailable: {exc}") from exc
