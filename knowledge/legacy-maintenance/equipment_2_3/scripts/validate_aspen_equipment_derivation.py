from __future__ import annotations

import hashlib
import json
from pathlib import Path

import aspen_equipment_derivation as adapter


def main() -> int:
    sample_path = adapter.PACKAGE_ROOT / "data" / "aspen_equipment_export_sample.json"
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    left = adapter.derive_bundle(sample, sample_path)
    right = adapter.derive_bundle(sample, sample_path)
    checks = {
        "derived": left.get("status") == "DERIVED",
        "clean_run_evidence_verified": left.get("aspen_run_gate", {}).get("run_status_evidence", {}).get("status") == "VERIFIED",
        "formal_process_basis": left.get("formal_use_gate") == "ELIGIBLE_AS_PROCESS_BASIS",
        "family_pump": left["equipment"][0]["match_result"]["match"]["family_id"] == "family_pump",
        "type_only_not_vendor_model": left["equipment"][0]["match_result"]["model_decision"]["model_status"] == "type_selected",
        "source_hash_on_every_lineage": all(
            item["source_file_sha256"] == left["source_export_sha256"]
            for equipment in left["equipment"]
            for item in equipment["parameter_lineage"]
        ),
        "deterministic_repeat": left == right,
        "llm_unused": left.get("llm_used") is False and left["equipment"][0]["match_result"].get("llm_used") is False,
    }
    rendered = json.dumps(left, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    report = {
        "schema": "aspen-equipment-derivation-validation-v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "result_sha256": hashlib.sha256(rendered).hexdigest().upper(),
        "sample_source_sha256": left["source_export_sha256"],
    }
    output = adapter.PACKAGE_ROOT / "outputs" / "aspen_equipment_derivation_validation_report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
