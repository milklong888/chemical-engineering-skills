from __future__ import annotations

import hashlib
import json
from pathlib import Path

import equipment_design_match as matcher


OUT = matcher.PACKAGE_ROOT / "outputs" / "equipment_match_validation_report.json"


def main() -> int:
    rules = matcher.load_rules()
    graph = matcher.load_graph()
    checks: list[dict[str, object]] = []

    rule_check = matcher.validate_rules(rules, graph)
    checks.append({"id": "rule_graph_coverage", "pass": rule_check["status"] == "PASS", "detail": rule_check})

    alias_failures: list[dict[str, object]] = []
    for rule in rules["families"]:
        result = matcher.match_one({"equipment_type": rule["aliases"][0]}, rules, graph)
        if result.get("status") != "MATCHED" or result.get("match", {}).get("family_id") != rule["id"]:
            alias_failures.append({"expected": rule["id"], "result": result})
    checks.append({"id": "all_family_exact_aliases", "pass": not alias_failures, "family_count": len(rules["families"]), "failures": alias_failures})

    examples = json.loads((matcher.PACKAGE_ROOT / "data" / "equipment_match_examples.json").read_text(encoding="utf-8"))["equipment"]
    example_results = [matcher.match_one(item, rules, graph) for item in examples]
    checks.append({"id": "example_batch", "pass": all(item["status"] == "MATCHED" for item in example_results), "record_count": len(example_results), "statuses": [item["status"] for item in example_results]})

    deterministic_input = {"设备类型": "工艺管道", "flow_m3_h": 50, "target_velocity_m_s": 1.5}
    left = json.dumps(matcher.match_one(deterministic_input, rules, graph), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    right = json.dumps(matcher.match_one(deterministic_input, rules, graph), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    checks.append({"id": "same_input_same_output", "pass": left == right, "sha256": hashlib.sha256(left.encode("utf-8")).hexdigest().upper()})

    conflict = matcher.match_one({"equipment_type": "泵", "aspen_block_type": "RADFRAC"}, rules, graph)
    checks.append({"id": "strong_identity_conflict_stops", "pass": conflict["status"] == "BLOCKED_IDENTITY_CONFLICT", "status": conflict["status"]})

    tag_only = matcher.match_one({"equipment_tag": "P-101"}, rules, graph)
    checks.append({"id": "tag_only_never_selects", "pass": tag_only["status"] == "BLOCKED_MISSING_DECISIVE_IDENTITY", "status": tag_only["status"]})

    bad_hash = matcher.match_one({"equipment_type": "泵", "vendor_datasheet_sha256": "bad"}, rules, graph)
    checks.append({"id": "invalid_hash_blocks", "pass": bad_hash["status"] == "BLOCKED_INVALID_PARAMETERS", "status": bad_hash["status"]})

    source = Path(matcher.__file__).read_text(encoding="utf-8")
    forbidden = [needle for needle in ("import openai", "from openai", "import requests", "urllib.request", "httpx") if needle in source]
    checks.append({"id": "no_llm_or_network_dependency", "pass": not forbidden, "forbidden_hits": forbidden})

    pump = matcher.match_one({"equipment_type": "泵"}, rules, graph)
    pump_numbers = {item["number"] for item in pump["standard_routes"]}
    checks.append({"id": "pump_standard_gate_traversal", "pass": {"GB/T 3215-2025", "GB/T 5662-2013"}.issubset(pump_numbers), "standards": sorted(item for item in pump_numbers if item)})

    tower = matcher.match_one({"equipment_type": "精馏塔"}, rules, graph)
    tower_route = next((item for item in tower["standard_routes"] if item["number"] == "NB/T 47041-2014"), None)
    checks.append({"id": "tower_current_standard_route", "pass": bool(tower_route and tower_route["source_layer"]["package_state"] == "PASS" and not tower_route["automatic_numeric_reuse_allowed"]), "route": tower_route})

    report = {
        "schema": "equipment-deterministic-match-validation-v1",
        "engine_version": matcher.ENGINE_VERSION,
        "status": "PASS" if all(bool(item["pass"]) for item in checks) else "FAIL",
        "llm_used": False,
        "checks": checks,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": len(checks), "output": str(OUT)}, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
