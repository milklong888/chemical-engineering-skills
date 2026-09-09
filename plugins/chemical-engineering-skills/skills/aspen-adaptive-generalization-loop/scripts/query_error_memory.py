"""Read compact guards or explicitly audit byte-preserved legacy incidents.

Historical retrieval does not authorize engineering reuse, learning, or changing
the current project authority. This command does not write files or run Aspen.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
ENTRY = SKILL_ROOT / "references/ERROR_MEMORY.md"
STORE = SKILL_ROOT / "references/error_memory"
INDEX = STORE / "index.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def load_index() -> dict:
    if not INDEX.is_file():
        raise ValueError("dependency_unavailable: no local historical index is configured; this release supplies current guards only")
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    if index.get("schema_version") != "adaptive-error-memory-atomic-index-1.0":
        raise ValueError("Unsupported memory schema; no inferred migration")
    uids = [row["event_uid"] for row in index["events"]]
    if len(uids) != len(set(uids)):
        raise ValueError("Duplicate event UID in index")
    return index


def event_body(row: dict) -> str:
    path = (STORE / row["entry_path"]).resolve()
    if not path.is_relative_to((STORE / "events").resolve()):
        raise ValueError("Event path escaped the atomic store")
    raw = path.read_bytes()
    if len(raw) != row["content_bytes"] or digest(raw) != row["content_sha256"]:
        raise ValueError(f"Preserved event bytes changed: {row['event_uid']}")
    return raw.decode("utf-8")


def compact_guards() -> list[dict]:
    # The default hot path reads only the short canonical entry, not the archive.
    text = ENTRY.read_text(encoding="utf-8")
    block = text.split("## Three current procedural guards", 1)[1].split("## At-point retrieval", 1)[0]
    pieces = re.split(r"(?m)^(?=\d+\. \*\*)", block)
    return [{"guard_id": f"AAG-GUARD-{i:02}", "text": part.strip(), "source": str(ENTRY),
             "knowledge_role": "error_memory_router", "authority_scope": "shared_procedural_router"}
            for i, part in enumerate([p for p in pieces if p.strip()], 1)]


def effective_flags(row: dict) -> dict:
    # Legacy source status is evidence text, not a current approval decision.
    # There is intentionally no command-line promotion or eligibility override.
    return {"knowledge_role": "error_memory_event", "knowledge_status": "legacy_unassessed",
            "authority_scope": "historical_case", "learning_eligible": False,
            "success_case_eligible": False, "default_rule_eligible": False,
            "default_retrieval_eligible": False, "audit_retrieval_eligible": True,
            "embedding_eligible": False, "current_project_authority": False}


def query_memory(*, query: str = "", audit: bool = False, legacy_id: str | None = None,
                 uid: str | None = None, scope: str | None = None, limit: int = 5,
                 include_body: bool = False) -> dict:
    if not 1 <= limit <= 144:
        raise ValueError("limit must be between 1 and 144")
    if legacy_id and uid:
        raise ValueError("Choose a legacy ID or a UID, not both")
    query = query.strip()
    if not legacy_id and not uid:
        if re.fullmatch(r"AAG-ERR-\d+", query, re.IGNORECASE):
            legacy_id = query.upper()
        elif re.fullmatch(r"aag-err-\d+--[0-9a-f]{16}", query, re.IGNORECASE):
            uid = query.lower()
    explicit_history = audit or legacy_id is not None or uid is not None
    if not explicit_history:
        if include_body:
            raise ValueError("Historical body requires --audit or an exact legacy ID/UID")
        return {"schema_version": "adaptive-memory-query-1.0", "mode": "current_guards_only",
                "query": query, "archive_index_loaded": False, "guards": compact_guards(),
                "events": [], "history_access": "Use --audit with project/theme terms or an exact legacy ID/UID",
                "project_authority_replaced": False}
    index = load_index()
    selected = index["events"]
    if legacy_id:
        legacy_id = legacy_id.upper()
        selected = [row for row in selected if row["legacy_id"] == legacy_id]
    elif uid:
        selected = [row for row in selected if row["event_uid"] == uid.lower()]
    tokens = [part.casefold() for part in re.split(r"[\s,，;；/]+", query) if part]
    ranked = []
    for row in selected:
        haystack = "\n".join([row["legacy_title"], str(row.get("original_scope") or ""),
                             *(field["value_raw"] for field in row["legacy_fields"])]).casefold()
        if scope and scope.casefold() not in haystack:
            continue
        score = sum(min(haystack.count(token), 8) for token in tokens)
        if not legacy_id and not uid and tokens and score == 0:
            continue
        ranked.append((score, row))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]["legacy_locator"]["ordinal"]))
    # An ambiguous exact legacy ID returns every title, regardless of limit.
    chosen = ranked if legacy_id or uid else ranked[:limit]
    events = []
    for score, row in chosen:
        body = event_body(row)
        result = {"event_uid": row["event_uid"], "legacy_id": row["legacy_id"],
            "title": row["legacy_title"], "original_status": row["original_status"],
            "original_scope": row["original_scope"], "original_repeat_count": row["original_repeat_count"],
            "original_last_seen": row["original_last_seen"], "effective": effective_flags(row),
            "legacy_locator": row["legacy_locator"], "content_sha256": row["content_sha256"],
            "entry_path": str((STORE / row["entry_path"]).resolve()), "audit_match_score": score,
            "notice": "Original labels are preserved, not revalidated. Audit-only; do not learn, generalize, apply defaults, or replace current project authority."}
        if include_body:
            result["original_body"] = body
        events.append(result)
    alternatives = index["aliases"].get(legacy_id, []) if legacy_id else []
    return {"schema_version": "adaptive-memory-query-1.0", "mode": "explicit_historical_audit",
        "query": query, "scope_filter": scope, "archive_index_loaded": True,
        "legacy_id": legacy_id, "ambiguous_legacy_id": len(alternatives) > 1,
        "disambiguation": alternatives if len(alternatives) > 1 else [],
        "matched_events": len(ranked), "events": events, "project_authority_replaced": False,
        "learning_eligible": False, "strict_validation_performed": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--legacy-id")
    parser.add_argument("--uid")
    parser.add_argument("--scope", help="Explicit audit scope text; never a current project authority declaration")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--include-body", action="store_true")
    args = parser.parse_args()
    try:
        report = query_memory(query=args.query, audit=args.audit, legacy_id=args.legacy_id,
                              uid=args.uid, scope=args.scope, limit=args.limit, include_body=args.include_body)
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Memory query refused: {exc}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
