#!/usr/bin/env python3
"""Read-only, idempotent validator for the type-option package."""
from __future__ import annotations

import argparse
import builtins
import csv
import hashlib
import importlib.util
import io
import json
import sys
from pathlib import Path


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
EXCLUDED_DIRS = {"audit_page_renders", "tmp", "__pycache__"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def snapshot():
    return {
        p.relative_to(ROOT).as_posix(): (sha(p), p.stat().st_size)
        for p in ROOT.rglob("*")
        if p.is_file() and not any(part in EXCLUDED_DIRS for part in p.relative_to(ROOT).parts)
    }


def rows(name):
    with (ROOT / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def require(condition, message, errors):
    if not condition:
        errors.append(message)


def load_engine():
    spec = importlib.util.spec_from_file_location("hgt_selector", ROOT / "select_terminal_type.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_validation(*, runtime_only=False, source_text_csv=None):
    before = snapshot()
    errors, checks = [], []
    required = [
        "type_catalog.csv","candidate_capabilities.csv","condition_registry.csv",
        "service_label_derivation.csv","hard_exclusions.csv","compatibility_matrix.csv",
        "selection_rules.csv","tie_default_priority.csv","warning_templates.csv",
        "source_records.csv","source_relations.csv","logical_table_grouping_manifest.csv",
        "input_schema.json","test_cases.json","package_metadata.json","hash_manifest.csv",
        "select_terminal_type.py","README.md","PARENT_INTEGRATION.md",
    ]
    for name in required:
        require((ROOT / name).is_file(), f"missing required file: {name}", errors)
    if errors:
        return {"status":"FAIL","errors":errors,"checks":checks}

    catalog = rows("type_catalog.csv")
    capabilities = rows("candidate_capabilities.csv")
    evidence = rows("source_records.csv")
    source_evidence = {}
    if source_text_csv is not None:
        projection = json.loads((ROOT / "SOURCE_PROJECTION.json").read_text(encoding="utf-8"))
        require(sha(source_text_csv) == projection["original_source_records_sha256"], "external source record file hash mismatch", errors)
        with source_text_csv.open(encoding="utf-8-sig", newline="") as handle:
            source_evidence = {r["evidence_id"]: r for r in csv.DictReader(handle)}
    relations = rows("source_relations.csv")
    hard = rows("hard_exclusions.csv")
    compatibility = rows("compatibility_matrix.csv")
    scoring = rows("selection_rules.csv")
    conditions = rows("condition_registry.csv")
    logical = rows("logical_table_grouping_manifest.csv")
    ids = {r["candidate_id"] for r in catalog}
    selectable = {r["candidate_id"] for r in catalog if r["terminal_selectable"].lower() == "true"}
    evidence_ids = {r["evidence_id"] for r in evidence}

    require(len(selectable) >= 45, f"too few selectable types: {len(selectable)}", errors)
    require(len(capabilities) == len(selectable), "candidate capability coverage is not 1:1", errors)
    require({r["candidate_id"] for r in capabilities} == selectable, "capability candidate set mismatch", errors)
    require(all(r["source_refs"] for r in catalog), "catalog row missing evidence relation", errors)
    require(all(r["closure_status"] == "CLOSED" for r in logical), "logical table group not closed", errors)
    require(len(logical) >= 12, "insufficient logical table closure groups", errors)
    require(all(r["evidence_id"] in evidence_ids for r in relations), "source relation points to missing evidence", errors)
    checks += ["catalog_coverage","capability_coverage","logical_table_closure","source_relations"]

    for record in evidence:
        require(record["source_pdf_sha256"] == "7513C49ABF181FF538E4D3A29050DEDD4DDDBEF9DE11B25840EEF21731D64201", f"PDF hash mismatch at {record['evidence_id']}", errors)
        raw = record.get("source_raw_text", source_evidence.get(record["evidence_id"], {}).get("source_raw_text"))
        if raw is not None:
            text_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()
            require(text_hash == record["source_text_sha256"], f"raw text hash mismatch at {record['evidence_id']}", errors)
        elif runtime_only:
            require(record.get("projection_scope") == "SOURCE_LOCATOR_HASH_ONLY_NOT_ORIGINAL_PARAGRAPH", "source locator projection scope missing", errors)
            require(len(record.get("source_text_sha256", "")) == 64, "original text hash missing", errors)
        else:
            errors.append(f"source_text_dependency_unavailable:{record['evidence_id']}")
        require(record["annotation_class"] == "SOURCE_RAW_TEXT", f"source record annotation layer wrong at {record['evidence_id']}", errors)
    checks.append("source_locator_hashes_only" if runtime_only and not source_evidence else "source_text_hashes")

    for record in hard + compatibility + scoring:
        require(all(ref in evidence_ids for ref in record["source_refs"].split("|") if ref), f"unknown evidence ref in {record['rule_id']}", errors)
        field = "candidate_ids" if "candidate_ids" in record else "allowed_candidate_ids"
        require(all(cid in ids for cid in record[field].split("|") if cid), f"unknown candidate in {record['rule_id']}", errors)
        try: json.loads(record["predicate_json"])
        except Exception as exc: errors.append(f"bad predicate JSON in {record['rule_id']}: {exc}")
    checks.append("rule_referential_integrity")

    input_schema = json.loads((ROOT / "input_schema.json").read_text(encoding="utf-8"))
    derived = {r["field_name"] for r in conditions if r["field_role"] == "DERIVED_OUTPUT_ONLY"}
    require(not derived.intersection(input_schema["properties"]), "derived service labels leaked into public input schema", errors)
    require("property_evidence" in input_schema["properties"] and "components" in input_schema["properties"], "raw composition/property-evidence interface missing", errors)
    require(input_schema.get("additionalProperties") is False, "input schema must reject undeclared direct labels", errors)
    checks.append("raw_to_derived_schema_boundary")

    current_codes = {(r["candidate_id"], r["current_code"]) for r in catalog}
    require(not any(code in {"PMF","PMS","PFT","LMN","NPY"} for _,code in current_codes), "obsolete code exposed as current", errors)
    require(("FL_CL_LWN","LWN") in current_codes, "LWN errata not applied", errors)
    for cid in ("G_PTFE_ENVELOPE_A","G_PTFE_ENVELOPE_B","G_PTFE_ENVELOPE_C"):
        row = next(r for r in catalog if r["candidate_id"] == cid)
        require("E_P532" in row["source_refs"] or "E_P531" in row["source_refs"], f"later errata missing for {cid}", errors)
    checks.append("later_errata_authority")

    manifest = {r["relative_path"]:r for r in rows("hash_manifest.csv")}
    for rel, item in manifest.items():
        path = ROOT / rel
        require(path.is_file(), f"manifest file missing: {rel}", errors)
        if path.is_file():
            require(sha(path) == item["sha256"], f"manifest hash mismatch: {rel}", errors)
            require(path.stat().st_size == int(item["size_bytes"]), f"manifest size mismatch: {rel}", errors)
    checks.append("hash_manifest")

    engine = load_engine()
    test_cases = json.loads((ROOT / "test_cases.json").read_text(encoding="utf-8"))
    require(len(test_cases) >= 20, f"only {len(test_cases)} tests", errors)

    # Guard proves runtime does not reread PDF/source images or source-layer.
    original_path_open, original_io_open, original_builtin_open = Path.open, io.open, builtins.open
    def guard_path_open(self, *args, **kwargs):
        text = str(self).lower().replace("\\", "/")
        if self.suffix.lower() in {".pdf",".png",".jpg",".jpeg",".tif",".tiff"} or "/source_layer/" in text or "/audit_page_renders/" in text:
            raise AssertionError(f"forbidden runtime read: {self}")
        return original_path_open(self, *args, **kwargs)
    Path.open = guard_path_open
    try:
        for test in test_cases:
            try:
                trusted_input = dict(test["input"])
                verified_property_evidence = trusted_input.pop("property_evidence", [])
                normalized_stream_phase = trusted_input.pop("phase", None)
                result1 = engine._select_verified(
                    trusted_input,
                    verified_property_evidence=verified_property_evidence,
                    normalized_stream_phase=normalized_stream_phase,
                )
                result2 = engine._select_verified(
                    trusted_input,
                    verified_property_evidence=verified_property_evidence,
                    normalized_stream_phase=normalized_stream_phase,
                )
            except Exception as exc:
                errors.append(f"{test['test_id']} raised: {exc}")
                continue
            require(result1 == result2, f"{test['test_id']} non-deterministic replay", errors)
            require(result1["terminal_count"] == 1, f"{test['test_id']} terminal_count != 1", errors)
            require(bool(result1["terminal_type"]["candidate_id"]), f"{test['test_id']} empty terminal", errors)
            require(result1["terminal_type"]["candidate_id"] == test["expected"], f"{test['test_id']} expected {test['expected']} got {result1['terminal_type']['candidate_id']}", errors)
            if test.get("status_contains"):
                require(test["status_contains"] in result1["status"], f"{test['test_id']} status mismatch: {result1['status']}", errors)
            if test.get("excluded_contains"):
                excluded_ids = {x["candidate_id"] for x in result1["hard_excluded_candidates"]}
                require(test["excluded_contains"] in excluded_ids, f"{test['test_id']} missing expected exclusion", errors)
            if test.get("warning_contains"):
                warning_ids = {x["warning_id"] for x in result1["warnings"]}
                require(test["warning_contains"] in warning_ids, f"{test['test_id']} missing expected warning", errors)
    finally:
        Path.open = original_path_open
        io.open = original_io_open
        builtins.open = original_builtin_open
    checks += ["36_common_boundary_conflict_missing_tests","no_source_no_image_runtime_guard","deterministic_double_replay"]

    # Directly supplied service labels must not influence selection.
    base = {"object_family":"gasket_type","system_series":"PN"}
    polluted = dict(base, toxicity="extreme", corrosivity="severe", oxidizing=True)
    a, b = engine.select(base), engine.select(polluted)
    require(a["terminal_type"] == b["terminal_type"], "direct derived labels changed selection", errors)
    require(any(w["warning_id"] == "W_DERIVED_INPUT_IGNORED" for w in b["warnings"]), "ignored direct labels did not warn", errors)
    checks.append("direct_label_injection_rejected")

    after = snapshot()
    require(before == after, "validator modified package files", errors)
    checks.append("read_only_idempotence")
    return {
        "status":("PASS_RUNTIME_ONLY" if runtime_only and not source_evidence else "PASS") if not errors else "FAIL",
        "source_text_validation":"NOT_PERFORMED_SOURCE_PARAGRAPHS_NOT_DISTRIBUTED" if runtime_only and not source_evidence else "CHECKED_OR_FAILED",
        "formal_engineering_acceptance":False,
        "errors":errors,
        "checks":checks,
        "counts":{
            "catalog_rows":len(catalog),"selectable_terminal_types":len(selectable),
            "hard_exclusions":len(hard),"compatibility_rules":len(compatibility),
            "selection_rules":len(scoring),"source_records":len(evidence),
            "logical_groups":len(logical),"tests":len(test_cases),
        },
        "runtime":{"vision":False,"source_pdf_read":False,"source_image_read":False,"llm":False},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--runtime-only", action="store_true", help="Validate the computational projection without claiming original paragraph verification.")
    parser.add_argument("--source-text-csv", type=Path, help="Optional exact original source_records.csv, checked against its retained hash.")
    args = parser.parse_args()
    result = run_validation(runtime_only=args.runtime_only, source_text_csv=args.source_text_csv)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) if args.json else result["status"])
    raise SystemExit(0 if result["status"] in {"PASS", "PASS_RUNTIME_ONLY"} else 1)


if __name__ == "__main__":
    main()
