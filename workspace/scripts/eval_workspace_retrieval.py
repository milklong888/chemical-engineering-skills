# -*- coding: utf-8 -*-
"""Run lightweight regression checks for workspace knowledge retrieval."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from query_workspace_vectors import infer_routes, load_index, load_route_config, rank_records


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


DEFAULT_EVAL_SET = Path(__file__).with_name("retrieval_eval_set.jsonl")


def load_cases(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def searchable_blob(record: dict) -> str:
    fields = [
        "vector_id",
        "source_group",
        "source_type",
        "source_path",
        "extract_path",
        "node_id",
        "chapter_node_id",
        "title",
        "text",
        "knowledge_role",
        "knowledge_status",
        "retrieval_priority",
        "knowledge_layer",
        "authority_scope",
        "scope_keys",
    ]
    return "\n".join(str(record.get(field, "")) for field in fields).casefold()


def source_identity_blob(record: dict) -> str:
    """Return only record identity fields, excluding links mentioned in its text."""
    fields = [
        "vector_id",
        "source_group",
        "source_type",
        "source_path",
        "extract_path",
        "node_id",
        "chapter_node_id",
    ]
    return "\n".join(str(record.get(field, "")) for field in fields).casefold()


def first_hit_rank(results: list[dict], expected_any: list[str], top_k: int) -> int | None:
    if not expected_any:
        return 1 if results else None
    needles = [item.casefold() for item in expected_any]
    for rank, record in enumerate(results[:top_k], 1):
        blob = searchable_blob(record)
        if any(needle in blob for needle in needles):
            return rank
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-file", type=Path, default=DEFAULT_EVAL_SET)
    parser.add_argument("--route", default="auto", help="auto, off, or a route name.")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    route_config = load_route_config()
    records, vectors = load_index()
    cases = load_cases(args.eval_file)
    failures = 0
    report = []

    for case in cases:
        query = case["query"]
        top_k = int(case.get("top_k", 5))
        selected_routes = infer_routes(query, route_config, args.route)
        routes = [route for route, _ in selected_routes]
        route_scores = [score for _, score in selected_routes]
        route_names = [str(route.get("name", "")) for route in routes]
        results = rank_records(
            query,
            records,
            vectors,
            limit=max(args.limit, top_k),
            routes=routes,
            route_scores=route_scores,
            active_scope_keys=case.get("scope_keys", []),
        )
        rank = first_hit_rank(results, case.get("expected_any", []), top_k)
        expected_route_any = case.get("expected_route_any", [])
        expected_route_all = case.get("expected_route_all", [])
        forbidden_route_any = case.get("forbidden_route_any", [])
        if args.route == "off":
            route_any_ok = True
            route_all_ok = True
            forbidden_route_ok = True
        else:
            route_any_ok = not expected_route_any or any(item in route_names for item in expected_route_any)
            route_all_ok = all(item in route_names for item in expected_route_all)
            forbidden_route_ok = not any(item in route_names for item in forbidden_route_any)

        forbidden_top_any = [item.casefold() for item in case.get("forbidden_top_any", [])]
        forbidden_hit = False
        if forbidden_top_any:
            forbidden_hit = any(
                any(needle in searchable_blob(record) for needle in forbidden_top_any)
                for record in results[:top_k]
            )
        forbidden_source_any = [
            item.casefold() for item in case.get("forbidden_source_any", [])
        ]
        forbidden_source_hit = False
        if forbidden_source_any:
            forbidden_source_hit = any(
                any(
                    needle in source_identity_blob(record)
                    for needle in forbidden_source_any
                )
                for record in results[:top_k]
            )

        expected_top_group_any = case.get("expected_top_group_any", [])
        expected_top_any = [item.casefold() for item in case.get("expected_top_any", [])]
        top_blob = searchable_blob(results[0]) if results else ""
        top_match_ok = not expected_top_any or any(needle in top_blob for needle in expected_top_any)
        top_group = results[0].get("source_group", "") if results else ""
        top_group_ok = not expected_top_group_any or top_group in expected_top_group_any

        ok = (
            rank is not None
            and route_any_ok
            and route_all_ok
            and forbidden_route_ok
            and not forbidden_hit
            and not forbidden_source_hit
            and top_match_ok
            and top_group_ok
        )
        failures += 0 if ok else 1
        top = results[0] if results else {}
        report.append(
            {
                "id": case["id"],
                "ok": ok,
                "rank": rank,
                "top_k": top_k,
                "routes": route_names,
                "route_scores": route_scores,
                "route_any_ok": route_any_ok,
                "route_all_ok": route_all_ok,
                "forbidden_route_ok": forbidden_route_ok,
                "forbidden_hit": forbidden_hit,
                "forbidden_source_hit": forbidden_source_hit,
                "top_match_ok": top_match_ok,
                "top_group_ok": top_group_ok,
                "top_source": top.get("source_path", ""),
                "top_group": top.get("source_group", ""),
                "top_title": top.get("title", ""),
                "top_score": top.get("score"),
            }
        )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in report:
            status = "PASS" if item["ok"] else "FAIL"
            rank_text = item["rank"] if item["rank"] is not None else "-"
            print(
                f"{status} {item['id']} rank={rank_text}/{item['top_k']} "
                f"routes={'+'.join(item['routes']) or 'none'} top={item['top_group']}::{item['top_source']} "
                f"route_ok={item['route_any_ok'] and item['route_all_ok']} "
                f"forbidden_hit={item['forbidden_hit']} "
                f"forbidden_source_hit={item['forbidden_source_hit']}"
            )
        print(f"\n{len(cases) - failures}/{len(cases)} retrieval checks passed.")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
