# -*- coding: utf-8 -*-
"""Query the workspace-wide knowledge and skill-chain vector index."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
from pathlib import Path

import numpy as np

from vectorize_workspace_knowledge import (
    CONFIG_PATH,
    RECORDS_JSONL,
    VECTORS_NPY,
    document_text,
    record_admission_reason,
    normalize_text,
    tokenise,
    vectorize_text,
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROUTES_JSON = Path(__file__).with_name("retrieval_routes.json")


def load_records(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def compact(text: str, limit: int = 420) -> str:
    text = re.sub(r"\s+", " ", str(text)).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def ensure_index() -> None:
    if CONFIG_PATH.exists() and RECORDS_JSONL.exists() and VECTORS_NPY.exists():
        return
    raise SystemExit("Workspace vector index missing. Build it first: python scripts\\vectorize_workspace_knowledge.py")


def load_route_config(path: Path = ROUTES_JSON) -> dict:
    if not path.exists():
        return {"default_min_score": 1.15, "routes": []}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def lexical_bonus(query: str, record: dict) -> float:
    haystack = normalize_text(document_text(record))
    query_norm = normalize_text(query)
    bonus = 0.0
    if query_norm and query_norm in haystack:
        bonus += 0.08
    seen: set[str] = set()
    for token in tokenise(query_norm):
        if token in seen:
            continue
        seen.add(token)
        if token in haystack:
            bonus += 0.018 if len(token) <= 3 else 0.03
    return min(bonus, 0.24)


def route_match_score(query: str, route: dict) -> float:
    query_norm = normalize_text(query)
    if not query_norm:
        return 0.0

    # Suppress a misleading keyword route when a compound semantic phrase
    # clearly selects another meaning (for example, model/Skill distillation
    # is not a distillation-column task).
    for term in route.get("suppress_triggers", []):
        term_norm = normalize_text(str(term))
        if term_norm and term_norm in query_norm:
            return 0.0

    score = 0.0
    seen_terms: set[str] = set()
    for term in route.get("triggers", []):
        term_norm = normalize_text(str(term))
        if not term_norm or term_norm in seen_terms:
            continue
        seen_terms.add(term_norm)
        if re.fullmatch(r"[a-z0-9]+", term_norm) and len(term_norm) <= 2:
            matched = re.search(
                rf"(?<![a-z0-9]){re.escape(term_norm)}(?![a-z0-9])",
                query_norm,
            ) is not None
        else:
            matched = term_norm in query_norm
        if matched:
            score += 1.25 if len(term_norm) <= 3 else 2.0

    route_tokens: set[str] = set()
    for term in seen_terms:
        route_tokens.update(tokenise(term))
    for token in set(tokenise(query_norm)):
        if token in route_tokens:
            score += 0.35 if len(token) <= 3 else 0.55
    return score


def infer_route(query: str, route_config: dict, requested: str = "auto") -> tuple[dict | None, float]:
    """Compatibility wrapper returning the primary route only."""
    selected = infer_routes(query, route_config, requested)
    if not selected:
        return None, 0.0
    for route, score in selected:
        if route.get("kind") != "guard":
            return route, score
    return selected[0]


def infer_routes(query: str, route_config: dict, requested: str = "auto") -> list[tuple[dict, float]]:
    """Select one domain route plus every matched cross-domain guard route."""
    routes = route_config.get("routes", [])
    if requested == "off" or not routes:
        return []
    if requested != "auto":
        for route in routes:
            if route.get("name") == requested:
                return [(route, route_match_score(query, route))]
        raise SystemExit(f"Unknown retrieval route: {requested}")

    scored = [(route_match_score(query, route), route) for route in routes]
    scored.sort(key=lambda item: item[0], reverse=True)
    selected: list[tuple[dict, float]] = []

    domain_scored = [(score, route) for score, route in scored if route.get("kind") != "guard"]
    if domain_scored:
        best_score, best_route = domain_scored[0]
        min_score = float(best_route.get("min_score", route_config.get("default_min_score", 1.15)))
        if best_score >= min_score:
            selected.append((best_route, best_score))

    for score, route in scored:
        if route.get("kind") != "guard":
            continue
        min_score = float(route.get("min_score", route_config.get("default_min_score", 1.15)))
        if score >= min_score:
            selected.append((route, score))
    return selected


def single_route_bonus(record: dict, route: dict | None) -> float:
    if not route:
        return 0.0
    bonus = 0.0
    bonus += float(route.get("source_group_bonus", {}).get(record.get("source_group"), 0.0))
    bonus += float(route.get("source_type_bonus", {}).get(record.get("source_type"), 0.0))
    bonus += float(route.get("scope_bonus", {}).get(record.get("scope"), 0.0))
    bonus += float(route.get("knowledge_role_bonus", {}).get(record.get("knowledge_role"), 0.0))
    bonus += float(route.get("knowledge_status_bonus", {}).get(record.get("knowledge_status"), 0.0))

    source_path = str(record.get("source_path", "")).replace("\\", "/")
    for needle, value in route.get("source_path_contains_bonus", {}).items():
        if str(needle).replace("\\", "/") in source_path:
            bonus += float(value)
    upper = 0.42 if route.get("kind") == "guard" else 0.30
    return max(min(bonus, upper), -0.14)


def route_bonus(record: dict, routes: list[dict] | dict | None) -> float:
    if not routes:
        return 0.0
    if isinstance(routes, dict):
        routes = [routes]
    total = sum(single_route_bonus(record, route) for route in routes)
    return max(min(total, 0.55), -0.20)


def knowledge_role_bonus(query: str, record: dict) -> float:
    role = record.get("knowledge_role", "")
    query_norm = normalize_text(query)
    explicit_history = any(
        term in query_norm
        for term in ["evolution", "candidate", "self-evolution", "演化记录", "候选补丁", "历史方案"]
    )
    explicit_new = any(
        term in query_norm
        for term in ["new knowledge", "new_knowledge", "新知识", "新增知识", "候选知识", "最近加入"]
    )
    if role == "evolution_history" and not explicit_history:
        return -0.20
    if role == "template" and not any(term in query_norm for term in ["template", "模板", "schema", "字段"]):
        return -0.10
    if role == "new_knowledge" and not explicit_new:
        status = record.get("knowledge_status", "")
        return -0.10 if "candidate" in status else -0.04
    if role == "error_memory":
        return -0.02 if record.get("knowledge_status") == "empty_memory" else 0.03
    if role == "canonical_router":
        return 0.01
    return 0.0


def knowledge_layer_bonus(query: str, record: dict) -> float:
    """Prefer the highest sufficient knowledge layer, then descend for detail."""
    layer = str(record.get("knowledge_layer", ""))
    if not layer:
        return 0.0

    query_norm = normalize_text(query)
    high_level_terms = [
        "思想", "观念", "为什么", "整体", "宏观", "常识", "合理", "原则",
        "判断", "系统", "本质", "机制", "怎样算好", "设计思路", "工程思维",
        "worldview", "principle", "why", "system thinking",
    ]
    detail_terms = [
        "公式", "方程", "数值", "参数", "图", "表", "页码", "原文", "例题",
        "计算", "系数", "关联式", "单位", "推导", "符号", "具体", "哪一页",
        "equation", "formula", "value", "table", "figure", "page", "unit",
    ]
    asks_high = any(term in query_norm for term in high_level_terms)
    asks_detail = any(term in query_norm for term in detail_terms)

    if asks_high and not asks_detail:
        return {
            "L3_worldview": 0.22,
            "L2_principle": 0.09,
            "L1_method": -0.02,
            "L0_source_detail": -0.28,
        }.get(layer, 0.0)
    if asks_detail:
        return {
            "L3_worldview": -0.02,
            "L2_principle": 0.05,
            "L1_method": 0.13,
            "L0_source_detail": 0.16,
        }.get(layer, 0.0)
    return {
        "L3_worldview": 0.06,
        "L2_principle": 0.04,
        "L1_method": 0.01,
        "L0_source_detail": -0.08,
    }.get(layer, 0.0)


def scope_allowed(
    query: str,
    record: dict,
    *,
    explicit_source_group: str | None = None,
    active_scope_keys: list[str] | None = None,
) -> bool:
    """Hard-filter scoped knowledge before scoring; vectors never grant authority."""
    if record_admission_reason(record):
        return False
    authority_scope = str(record.get("authority_scope", "shared"))
    if authority_scope == "shared":
        return True
    if explicit_source_group and record.get("source_group") == explicit_source_group:
        return True
    context = normalize_text(" ".join([query, *(active_scope_keys or [])]))
    keys = [normalize_text(str(item)) for item in record.get("scope_keys", [])]
    return any(key and key in context for key in keys)


def authority_scope_bonus(
    query: str,
    record: dict,
    *,
    explicit_source_group: str | None = None,
    active_scope_keys: list[str] | None = None,
) -> float:
    """Prefer an explicitly activated scoped authority after the hard filter."""
    if str(record.get("authority_scope", "shared")) == "shared":
        return 0.0
    if explicit_source_group and record.get("source_group") == explicit_source_group:
        return 0.35

    keys = [normalize_text(str(item)) for item in record.get("scope_keys", [])]
    explicit_context = normalize_text(" ".join(active_scope_keys or []))
    explicit_matches = sum(1 for key in keys if key and key in explicit_context)
    if explicit_matches:
        return min(0.43, 0.35 + 0.04 * (explicit_matches - 1))

    query_context = normalize_text(query)
    query_matches = sum(1 for key in keys if key and key in query_context)
    if query_matches:
        return min(0.30, 0.18 + 0.04 * (query_matches - 1))
    return 0.0


def load_index() -> tuple[list[dict], np.ndarray]:
    ensure_index()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    # Hash exactly the bytes that are parsed, so a mid-publication replacement
    # cannot pair a verified file with a differently reopened payload.
    record_bytes = RECORDS_JSONL.read_bytes()
    vector_bytes = VECTORS_NPY.read_bytes()
    for key, payload in (("records_sha256", record_bytes), ("vectors_sha256", vector_bytes)):
        if key in config and hashlib.sha256(payload).hexdigest().upper() != str(config[key]).upper():
            raise SystemExit(f"Index integrity mismatch: {key}; rebuild or publish a consistent index set")
    records = [json.loads(line) for line in record_bytes.decode("utf-8").splitlines() if line.strip()]
    vectors = np.load(io.BytesIO(vector_bytes), allow_pickle=False)
    if len(records) != vectors.shape[0]:
        raise SystemExit(f"Index mismatch: {len(records)} records but {vectors.shape[0]} vectors")
    return records, vectors


def group_error_memory_hits(results: list[dict], *, additional_location_limit: int = 4) -> list[dict]:
    """Group sorted guard chunks by exact source version and authority scope.

    This is result presentation, not score fusion or evidence deduplication:
    the highest-ranked chunk stays verbatim and the original index is intact.
    Missing source hashes, different scopes, and ordinary references never merge.
    """
    grouped: list[dict] = []
    leaders: dict[tuple, dict] = {}
    for record in results:
        path = str(record.get("source_path", "")).replace("\\", "/")
        source_hash = str(record.get("source_sha256", "")).upper()
        if record.get("knowledge_role") != "error_memory" or not path or not re.fullmatch(r"[A-F0-9]{64}", source_hash):
            grouped.append(record)
            continue
        key = (path.casefold(), source_hash, str(record.get("source_group", "")),
               str(record.get("authority_scope", "shared")), str(record.get("scope", "")),
               tuple(sorted(str(item) for item in record.get("scope_keys", []))))
        if key not in leaders:
            leader = dict(record)
            leader["guard_grouping"] = {"policy": "same-source-version-scope-error-memory-v1",
                                       "chunk_count": 1, "additional_chunk_locations": [],
                                       "additional_locations_truncated": False}
            leaders[key] = leader
            grouped.append(leader)
            continue
        metadata = leaders[key]["guard_grouping"]
        metadata["chunk_count"] += 1
        if len(metadata["additional_chunk_locations"]) < max(additional_location_limit, 0):
            metadata["additional_chunk_locations"].append({key: record.get(key) for key in
                ("vector_id", "chunk_index", "node_id", "page", "score") if key in record})
        else:
            metadata["additional_locations_truncated"] = True
    return grouped


def rank_records(
    query: str,
    records: list[dict],
    vectors: np.ndarray,
    *,
    limit: int = 10,
    source_group: str | None = None,
    source_type: str | None = None,
    route: dict | None = None,
    route_score: float = 0.0,
    routes: list[dict] | None = None,
    route_scores: list[float] | None = None,
    active_scope_keys: list[str] | None = None,
) -> list[dict]:
    qvec = vectorize_text(query, dim=vectors.shape[1])
    scores = vectors @ qvec

    results = []
    active_routes = list(routes or ([] if route is None else [route]))
    active_route_scores = list(route_scores or ([] if route is None else [route_score]))
    route_names = [str(item.get("name", "")) for item in active_routes if item]
    for idx, raw_score in enumerate(scores.tolist()):
        record = records[idx]
        if source_group and record.get("source_group") != source_group:
            continue
        if source_type and record.get("source_type") != source_type:
            continue
        if not scope_allowed(
            query,
            record,
            explicit_source_group=source_group,
            active_scope_keys=active_scope_keys,
        ):
            continue
        base_bonus = lexical_bonus(query, record)
        if record.get("scope") in {"detail-node", "file-chunk"}:
            base_bonus += 0.01
        routed_bonus = route_bonus(record, active_routes)
        role_bonus = knowledge_role_bonus(query, record)
        layer_bonus = knowledge_layer_bonus(query, record)
        scoped_bonus = authority_scope_bonus(
            query,
            record,
            explicit_source_group=source_group,
            active_scope_keys=active_scope_keys,
        )
        result = dict(record)
        result["score"] = (
            float(raw_score)
            + base_bonus
            + routed_bonus
            + role_bonus
            + layer_bonus
            + scoped_bonus
        )
        result["raw_cosine"] = float(raw_score)
        result["lexical_bonus"] = base_bonus
        result["route_bonus"] = routed_bonus
        result["knowledge_role_bonus"] = role_bonus
        result["knowledge_layer_bonus"] = layer_bonus
        result["authority_scope_bonus"] = scoped_bonus
        result["route"] = "+".join(route_names)
        result["routes"] = route_names
        result["route_score"] = max(active_route_scores, default=0.0)
        result["route_scores"] = active_route_scores
        results.append(result)

    results.sort(key=lambda item: item["score"], reverse=True)
    return group_error_memory_hits(results)[: max(limit, 1)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("terms", nargs="*", help="Query terms.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum results.")
    parser.add_argument("--json", action="store_true", help="Print JSON results.")
    parser.add_argument("--ids", action="store_true", help="Print only vector IDs.")
    parser.add_argument("--source-group", help="Restrict to one source_group, such as aspen-plus-operations.")
    parser.add_argument("--source-type", help="Restrict to one source_type, such as skill_chain_file.")
    parser.add_argument(
        "--scope-key",
        action="append",
        default=[],
        help="Activate a project/course scope explicitly; may be repeated.",
    )
    parser.add_argument(
        "--route",
        default="auto",
        help="Route-aware reranking mode: auto, off, or a route name from scripts\\retrieval_routes.json.",
    )
    parser.add_argument("--show-route", action="store_true", help="Print the inferred retrieval route before results.")
    args = parser.parse_args()

    if not args.terms:
        parser.print_help()
        return 2

    query = " ".join(args.terms)
    route_config = load_route_config()
    selected_routes = infer_routes(query, route_config, args.route)
    active_routes = [route for route, _ in selected_routes]
    inferred_scores = [score for _, score in selected_routes]
    records, vectors = load_index()
    results = rank_records(
        query,
        records,
        vectors,
        limit=args.limit,
        source_group=args.source_group,
        source_type=args.source_type,
        routes=active_routes,
        route_scores=inferred_scores,
        active_scope_keys=args.scope_key,
    )

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    if args.ids:
        print("\n".join(str(item["vector_id"]) for item in results))
        return 0

    if args.show_route:
        if selected_routes:
            rendered = " + ".join(
                f"{route.get('name')} ({route.get('label', '')}) score={score:.2f}"
                for route, score in selected_routes
            )
            print(f"routes: {rendered}")
        else:
            print("routes: none")

    for item in results:
        print(
            f"{item['vector_id']} | score {item['score']:.4f} | "
            f"cosine {item['raw_cosine']:.4f} | route_bonus {item.get('route_bonus', 0.0):+.3f} | "
            f"role_bonus {item.get('knowledge_role_bonus', 0.0):+.3f}"
        )
        print(f"  group/type: {item.get('source_group')} / {item.get('source_type')}")
        print(f"  title: {item.get('title', '')}")
        if item.get("node_id"):
            print(f"  node: {item.get('node_id')} chapter={item.get('chapter_node_id', '')}")
        if item.get("page"):
            print(f"  page: {item.get('page')}")
        if item.get("source_path"):
            print(f"  source: {item.get('source_path')}")
        if item.get("extract_path"):
            print(f"  extract: {item.get('extract_path')}")
        grouping = item.get("guard_grouping", {})
        if grouping.get("chunk_count", 1) > 1:
            locations = ", ".join(str(row.get("vector_id", "")) for row in grouping.get("additional_chunk_locations", []))
            print(f"  same-source guard chunks: {grouping['chunk_count']}; additional locations: {locations}")
        print(f"  text: {compact(item.get('text', ''))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
