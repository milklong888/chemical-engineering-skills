"""Persist delivery commitments separately from editable authority files.

Register when a delivery scope and precise evidence files are available. A
planning task without that delivery decision can omit the delivery basis.
New revisions and named forks retain their parents' scope. Equivalent file
renames use the retained hash. A technical revision can bind a changed file to
the same obligation using scope_revision_ref and the existing project source.
Actual scope reductions and independent delivery scopes require a separately
sourced scope_decision_ref. Decisions are checked against retained records,
not authenticated as user messages by this module.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3


SCOPE_HISTORY = "PROJECT_REVIEW_SCOPE_HISTORY.sqlite3"
_SHA256 = re.compile(r"[0-9a-f]{64}")


class ScopeHistoryError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _ref(value):
    if not isinstance(value, dict) or value.keys() != {"path", "sha256"} or not _text(value.get("path")):
        raise ScopeHistoryError("DELIVERY_SCOPE_EVIDENCE_REQUIRED", "Each scope item must bind an exact path and SHA-256.")
    sha = str(value["sha256"]).lower()
    if not _SHA256.fullmatch(sha):
        raise ScopeHistoryError("DELIVERY_SCOPE_EVIDENCE_REQUIRED", f"Invalid SHA-256 for {value['path']}.")
    return {"path": Path(value["path"]).as_posix(), "sha256": sha}


def _read_json(root, ref):
    data = (root / ref["path"]).read_bytes()
    if _digest(data) != ref["sha256"]:
        raise ScopeHistoryError("DELIVERY_SCOPE_ORIGINAL_CHANGED", f"The referenced original changed: {ref['path']}.")
    value = json.loads(data.decode("utf-8-sig"))
    if not isinstance(value, dict):
        raise ScopeHistoryError("DELIVERY_SCOPE_AUTHORITY_REQUIRED", f"An authority record is required: {ref['path']}.")
    return value


def _normalize(basis):
    scope, evidence = basis.get("scope"), basis.get("scope_evidence")
    if (not isinstance(scope, list) or not scope or not all(_text(item) for item in scope)
            or len(set(scope)) != len(scope) or not isinstance(evidence, dict) or set(evidence) != set(scope)):
        raise ScopeHistoryError("DELIVERY_SCOPE_EVIDENCE_REQUIRED", "Map every unique nonempty delivery scope item to its required evidence files.")
    mapped = {}
    for item in sorted(scope):
        references = evidence[item] if isinstance(evidence[item], list) else [evidence[item]]
        values = [_ref(ref) for ref in references]
        if not values or len({ref["path"] for ref in values}) != len(values):
            raise ScopeHistoryError("DELIVERY_SCOPE_EVIDENCE_REQUIRED", f"Provide distinct exact evidence paths for {item}.")
        mapped[item] = sorted(values, key=lambda ref: ref["path"])
    return {"scope": sorted(scope), "scope_evidence": mapped}


def _entry(root, identity, basis, authority_ref):
    case, revision = identity.get("case_id"), identity.get("task_revision")
    if not _text(case) or not _text(revision) or not isinstance(basis, dict):
        raise ScopeHistoryError("DELIVERY_SCOPE_AUTHORITY_REQUIRED", "Provide the case ID, task revision and frozen delivery authority.")
    authority_ref = _ref(authority_ref)
    authority = _read_json(root, authority_ref)
    if (authority.get("case_id") != case or authority.get("task_revision") != revision
            or authority.get("delivery_review") != basis
            or authority.get("run_id") is not None and identity.get("run_id") is not None
            and authority["run_id"] != identity["run_id"]):
        raise ScopeHistoryError("DELIVERY_SCOPE_AUTHORITY_REQUIRED", "The exact authority file must contain this scope and identify the same case and revision.")
    branch = basis.get("scope_branch", "main")
    parents = basis.get("scope_parents")
    if (not _text(branch) or parents is not None and (not isinstance(parents, list)
            or not all(isinstance(x, str) and _SHA256.fullmatch(x) for x in parents) or len(set(parents)) != len(parents))):
        raise ScopeHistoryError("DELIVERY_SCOPE_LINEAGE_INVALID", "Provide a branch and distinct registered parent snapshot IDs.")
    return {"case_id": case, "task_revision": revision, "scope_branch": branch, "authority_ref": authority_ref,
            "scope_parents": sorted(parents) if parents is not None else None, **_normalize(basis)}


def _connect(database, *, write=False):
    target = database if write else database.resolve().as_uri() + "?mode=ro"
    db = sqlite3.connect(target, uri=not write, timeout=30, isolation_level=None)
    db.row_factory = sqlite3.Row
    return db


def _create(db):
    db.execute("""CREATE TABLE IF NOT EXISTS snapshots (
        ordinal INTEGER PRIMARY KEY, snapshot_id TEXT NOT NULL UNIQUE, case_id TEXT NOT NULL,
        task_revision TEXT NOT NULL, branch TEXT NOT NULL, record TEXT NOT NULL, UNIQUE(case_id, task_revision))""")
    db.execute("CREATE INDEX IF NOT EXISTS snapshot_case_branch ON snapshots (case_id, branch, ordinal)")
    db.execute("""CREATE TABLE IF NOT EXISTS originals (
        object_id INTEGER PRIMARY KEY, sha256 TEXT NOT NULL UNIQUE, content BLOB NOT NULL)""")


def _snapshot(row):
    if row is None:
        return None
    record = json.loads(row["record"])
    if (_digest(row["record"].encode("utf-8")) != row["snapshot_id"] or record["case_id"] != row["case_id"]
            or record["task_revision"] != row["task_revision"] or record["scope_branch"] != row["branch"]):
        raise ScopeHistoryError("DELIVERY_SCOPE_HISTORY_CHANGED", "A registered delivery-scope snapshot changed.")
    return {**record, "snapshot_id": row["snapshot_id"]}


def _revision(db, entry):
    return _snapshot(db.execute("SELECT * FROM snapshots WHERE case_id=? AND task_revision=?",
                                (entry["case_id"], entry["task_revision"])).fetchone())


def _head(db, entry):
    return _snapshot(db.execute("SELECT * FROM snapshots WHERE case_id=? AND branch=? ORDER BY ordinal DESC LIMIT 1",
                                (entry["case_id"], entry["scope_branch"])).fetchone())


def _case_exists(db, case_id):
    return db.execute("SELECT 1 FROM snapshots WHERE case_id=? LIMIT 1", (case_id,)).fetchone() is not None


def _check_prior_records(db, start):
    pending = [start]
    seen = set()
    while pending:
        record = pending.pop()
        if record["snapshot_id"] in seen:
            continue
        seen.add(record["snapshot_id"])
        for key in ("authority_ref", "scope_decision_ref", "approval_source_ref", "scope_revision_ref", "revision_source_ref"):
            ref = record.get(key)
            if ref is None:
                continue
            original = db.execute("SELECT content FROM originals WHERE sha256=?", (ref["sha256"],)).fetchone()
            if original is None or _digest(original["content"]) != ref["sha256"]:
                raise ScopeHistoryError("DELIVERY_SCOPE_HISTORY_CHANGED", f"Missing or altered retained authority: {ref['path']}.")
        for snapshot_id in record["scope_parents"]:
            parent = _snapshot(db.execute("SELECT * FROM snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone())
            if parent is None or parent["case_id"] != start["case_id"]:
                raise ScopeHistoryError("DELIVERY_SCOPE_HISTORY_CHANGED", "The original scope history is incomplete.")
            pending.append(parent)


def _same_revision(saved, entry):
    differences = [key for key in ("scope_branch", "scope", "scope_evidence") if saved[key] != entry[key]]
    explicitly_linked = entry["scope_parents"]
    if differences or explicitly_linked is not None and explicitly_linked != saved["scope_parents"]:
        raise ScopeHistoryError("DELIVERY_SCOPE_REVISION_DRIFT", f"The frozen scope or evidence requirements changed on this revision: {', '.join(differences) or 'scope_parents'}.")


def _transition(root, entry, ref, *, approval):
    schema = "delivery-scope-decision-v1" if approval else "delivery-scope-revision-v1"
    code = "DELIVERY_SCOPE_CHANGE_UNAPPROVED" if approval else "DELIVERY_SCOPE_REBINDING_REQUIRED"
    if ref is None:
        need = "a sourced authorization for the changed delivery scope" if approval else "a same-case project record for the revised evidence mapping"
        raise ScopeHistoryError(code, f"Provide {need}.")
    ref = _ref(ref)
    record = _read_json(root, ref)
    keys = ("case_id", "task_revision", "scope_branch", "scope_parents", "scope", "scope_evidence")
    normalized = {**record, **_normalize(record)}
    if isinstance(normalized.get("scope_parents"), list) and all(isinstance(x, str) for x in normalized["scope_parents"]):
        normalized["scope_parents"] = sorted(normalized["scope_parents"])
    excerpt_name = "approval_excerpt" if approval else "source_excerpt"
    source_name = "approval_source_ref" if approval else "source_ref"
    if (record.get("schema") != schema or any(not _text(record.get(key)) for key in ("reason", excerpt_name))
            or approval and (record.get("decision") != "approved" or not _text(record.get("approved_by")))
            or any(normalized.get(key) != entry[key] for key in keys)):
        raise ScopeHistoryError(code, "The record must bind this case, revision, branch, parents, scope and evidence.")
    source = _ref(record.get(source_name))
    if source["sha256"] in (ref["sha256"], entry["authority_ref"]["sha256"]):
        raise ScopeHistoryError(code, "Retain the source behind this scope decision or evidence revision separately.")
    raw = (root / source["path"]).read_bytes()
    if _digest(raw) != source["sha256"] or record[excerpt_name] not in raw.decode("utf-8-sig"):
        raise ScopeHistoryError(code, "The quoted passage must occur in the exact retained source.")
    if Path(source["path"]).suffix.lower() == ".json":
        data = json.loads(raw.decode("utf-8-sig"))
        if (not isinstance(data, dict) or data.get("case_id") != entry["case_id"]
                or data.get("task_revision") != entry["task_revision"]):
            raise ScopeHistoryError(code, "Structured source evidence must identify this same case and revision.")
    return ref, source, record


def _unbound_requirements(parents, entry):
    missing, used = {}, set()
    for parent in parents:
        for scope, refs in parent["scope_evidence"].items():
            if scope not in entry["scope_evidence"]:
                continue
            current = {ref["path"]: ref for ref in entry["scope_evidence"][scope]}
            prefix = parent["snapshot_id"], scope
            taken = {ref["path"] for ref in refs if ref["path"] in current}
            for ref in refs:
                if ref["path"] in taken:
                    continue
                renamed = [p for p, row in current.items() if p not in taken and row["sha256"] == ref["sha256"]]
                if len(renamed) == 1:
                    taken.add(renamed[0])
                else:
                    missing[(*prefix, ref["path"])] = ref
            used.update((*prefix, path) for path in taken)
    return missing, used


def _rebind(entry, transition, missing, used):
    code = "DELIVERY_SCOPE_REBINDING_REQUIRED"
    rows = transition.get("rebindings")
    if not isinstance(rows, list) or len(rows) != len(missing):
        raise ScopeHistoryError(code, "Map each previously required evidence file that changed identity.")
    for row in rows:
        if not isinstance(row, dict) or not _text(row.get("scope")) or not _text(row.get("parent_snapshot_id")):
            raise ScopeHistoryError(code, "Each mapping must identify its original snapshot and scope item.")
        source, target = _ref(row.get("from")), _ref(row.get("to"))
        prefix = row["parent_snapshot_id"], row["scope"]
        old, new = (*prefix, source["path"]), (*prefix, target["path"])
        if missing.get(old) != source or target not in entry["scope_evidence"].get(row["scope"], []) or new in used:
            raise ScopeHistoryError(code, "Keep each previous requirement bound to distinct evidence of the same scope in the new revision.")
        del missing[old]
        used.add(new)


def _store(db, root, ref):
    """Retain authority and transition originals without duplicating engineering files."""
    if db.execute("SELECT 1 FROM originals WHERE sha256=?", (ref["sha256"],)).fetchone():
        return
    data = (root / ref["path"]).read_bytes()
    if _digest(data) != ref["sha256"]:
        raise ScopeHistoryError("DELIVERY_SCOPE_ORIGINAL_CHANGED", f"The referenced original changed: {ref['path']}.")
    db.execute("INSERT INTO originals(sha256, content) VALUES(?, ?)", (ref["sha256"], data))


def _evidence(entry):
    return [ref for refs in entry["scope_evidence"].values() for ref in refs]


def _validate_files(root, entry):
    identities = {(ref["path"], ref["sha256"]) for ref in _evidence(entry)}
    for path, expected in identities:
        with (root / path).open("rb") as source:
            actual = hashlib.file_digest(source, "sha256").hexdigest()
        if actual != expected:
            raise ScopeHistoryError("DELIVERY_SCOPE_ORIGINAL_CHANGED", f"The referenced original changed: {path}.")


def remember_scope(root, identity, basis, authority_ref):
    """Freeze a case revision once. Same-revision reruns cannot replace its contents."""
    root = Path(root)
    entry = _entry(root, identity, basis, authority_ref)
    _validate_files(root, entry)
    try:
        with closing(_connect(root / SCOPE_HISTORY, write=True)) as db:
            db.execute("BEGIN IMMEDIATE")
            _create(db)
            saved = _revision(db, entry)
            if saved is not None:
                _same_revision(saved, entry)
                _check_prior_records(db, saved)
                db.rollback()
                return saved
            head = _head(db, entry)
            parents = entry["scope_parents"]
            if parents is None:
                parents = [head["snapshot_id"]] if head else []
            ancestors = []
            for parent in parents:
                record = _snapshot(db.execute("SELECT * FROM snapshots WHERE snapshot_id=?", (parent,)).fetchone())
                if record is None or record["case_id"] != entry["case_id"]:
                    raise ScopeHistoryError("DELIVERY_SCOPE_LINEAGE_INVALID", "Every parent must be a registered snapshot from this same case.")
                if _head(db, record)["snapshot_id"] != parent:
                    raise ScopeHistoryError("DELIVERY_SCOPE_LINEAGE_INVALID", "Use the current heads of contributing branches for the new revision.")
                _check_prior_records(db, record)
                ancestors.append(record)
            if head and head["snapshot_id"] not in parents:
                raise ScopeHistoryError("DELIVERY_SCOPE_LINEAGE_INVALID", "The revision must descend from the current head of its branch.")
            entry["scope_parents"] = parents
            removed = {item for parent in ancestors for item in parent["scope"]} - set(entry["scope"])
            independent = not parents and _case_exists(db, entry["case_id"])
            references = [entry["authority_ref"]]
            if removed or independent or basis.get("scope_decision_ref") is not None:
                decision, source, _ = _transition(root, entry, basis.get("scope_decision_ref"), approval=True)
                entry.update(scope_decision_ref=decision, approval_source_ref=source)
                references.extend((decision, source))
            else:
                missing, used = _unbound_requirements(ancestors, entry)
                if missing or basis.get("scope_revision_ref") is not None:
                    revision, source, transition = _transition(root, entry, basis.get("scope_revision_ref"), approval=False)
                    _rebind(entry, transition, missing, used)
                    entry.update(scope_revision_ref=revision, revision_source_ref=source)
                    references.extend((revision, source))
            for ref in references:
                _store(db, root, ref)
            record = _json(entry)
            snapshot_id = _digest(record.encode("utf-8"))
            db.execute("INSERT INTO snapshots(snapshot_id, case_id, task_revision, branch, record) VALUES(?, ?, ?, ?, ?)",
                       (snapshot_id, entry["case_id"], entry["task_revision"], entry["scope_branch"], record))
            db.commit()
            return {**entry, "snapshot_id": snapshot_id}
    except sqlite3.Error as exc:
        raise ScopeHistoryError("DELIVERY_SCOPE_HISTORY_UNAVAILABLE", str(exc)) from exc


def _check_final(entry, final_checks):
    if not isinstance(final_checks, list):
        raise ScopeHistoryError("DELIVERY_SCOPE_FINAL_EVIDENCE_MISSING", "Provide the final independent reviewer’s checks by scope item.")
    covered = {scope: set() for scope in entry["scope"]}
    expected = {scope: {(ref["path"], ref["sha256"]) for ref in refs} for scope, refs in entry["scope_evidence"].items()}
    for item in final_checks:
        if not isinstance(item, dict) or item.get("scope") not in covered:
            raise ScopeHistoryError("DELIVERY_SCOPE_FINAL_EVIDENCE_MISSING", "Every final check must identify a frozen scope item.")
        ref = _ref(item.get("evidence_ref"))
        evidence = ref["path"], ref["sha256"]
        if evidence in expected[item["scope"]]:
            covered[item["scope"]].add(evidence)
    missed = [scope for scope in entry["scope"] if covered[scope] != expected[scope]]
    if missed:
        raise ScopeHistoryError("DELIVERY_SCOPE_FINAL_EVIDENCE_MISSING", f"The final review omitted required evidence for: {', '.join(missed)}.")


def check_scope(root, identity, basis, authority_ref, *, final_checks=None):
    """Read only. Validate the current branch head and independent per-scope evidence."""
    root = Path(root)
    database = root / SCOPE_HISTORY
    try:
        case = identity.get("case_id")
        if not database.is_file():
            if basis is None:
                return {"status": "NOT_APPLICABLE", "needs": []}
            raise ScopeHistoryError("DELIVERY_SCOPE_HISTORY_REQUIRED", "Register the delivery scope when the project authorization is first frozen.")
        with closing(_connect(database)) as db:
            db.execute("BEGIN")
            if basis is None:
                if _text(case) and _case_exists(db, case):
                    raise ScopeHistoryError("DELIVERY_SCOPE_REMOVED", "Restore the already registered scope authority for this case.")
                return {"status": "NOT_APPLICABLE", "needs": []}
            entry = _entry(root, identity, basis, authority_ref)
            saved = _revision(db, entry)
            if saved is None:
                raise ScopeHistoryError("DELIVERY_SCOPE_REVISION_NOT_REGISTERED", "Register this authorized revision against its retained scope history before delivery review.")
            _same_revision(saved, entry)
            if _head(db, entry)["snapshot_id"] != saved["snapshot_id"]:
                raise ScopeHistoryError("DELIVERY_SCOPE_REVISION_STALE", "Check the current scope revision on this branch.")
            _check_prior_records(db, saved)
            _validate_files(root, entry)
            if final_checks is not None:
                _check_final(saved, final_checks)
            return {"status": "SCOPE_HISTORY_CHECKED", "needs": [], "snapshot_id": saved["snapshot_id"],
                    "scope_evidence": saved["scope_evidence"]}
    except (OSError, ValueError, TypeError, AttributeError, KeyError, sqlite3.Error) as exc:
        return {"status": "ACTION_REQUIRED", "needs": [{"code": getattr(exc, "code", "DELIVERY_SCOPE_HISTORY_UNAVAILABLE"),
                                                          "scope": "delivery", "detail": str(exc)}]}
