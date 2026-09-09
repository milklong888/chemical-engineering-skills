from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA = "equipment-design-bkp-benchmark-manifest-v1"
REGISTRY_SCHEMA = "equipment-design-bkp-benchmark-registry-v1"
# Keep the benchmark runnable through the same public import surface as the
# application.  Archive-only APWZ files need a separate conversion/import
# feature and must not silently enter a BKP/APW stability gate.
ALLOWED_EXTENSIONS = frozenset({".bkp", ".apw", ".inp"})
SPLIT_CONTRACT = {
    "training": ("development_training", True),
    "validation": ("holdout_validation", False),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _required_text(case: Mapping[str, Any], field: str) -> str:
    value = str(case.get(field) or "").strip()
    if not value:
        raise ValueError(f"case {case.get('case_id')!r}: {field} is required")
    return value


def _minimum(policy: Mapping[str, Any], key: str, split: str) -> int:
    values = policy.get(key)
    if not isinstance(values, Mapping):
        raise ValueError(f"policy.{key} must be an object")
    value = values.get(split)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"policy.{key}.{split} must be a positive integer")
    return value


def _case_counter(cases: Iterable[Mapping[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(case[field]) for case in cases).items()))


def _safe_dataset_id(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    if not safe:
        raise ValueError("dataset_id must contain at least one filename-safe character")
    return safe


def build_dataset(registry_path: Path, output_dir: Path) -> dict[str, Path]:
    registry_path = registry_path.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    registry = json.loads(registry_path.read_text(encoding="utf-8-sig"))
    if not isinstance(registry, Mapping) or registry.get("schema") != REGISTRY_SCHEMA:
        raise ValueError(f"registry.schema must equal {REGISTRY_SCHEMA}")
    dataset_id = _safe_dataset_id(str(registry.get("dataset_id") or ""))
    policy = registry.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("registry.policy must be an object")
    raw_cases = registry.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("registry.cases must be a non-empty array")

    normalized: list[dict[str, Any]] = []
    seen_case_ids: set[str] = set()
    seen_hashes: dict[str, str] = {}
    for raw in raw_cases:
        if not isinstance(raw, Mapping):
            raise ValueError("every registry case must be an object")
        case_id = _required_text(raw, "case_id")
        if case_id in seen_case_ids:
            raise ValueError(f"duplicate case_id: {case_id}")
        seen_case_ids.add(case_id)
        split = _required_text(raw, "split")
        if split not in SPLIT_CONTRACT:
            raise ValueError(f"case {case_id!r}: split must be training or validation")
        source = Path(_required_text(raw, "path")).expanduser().resolve()
        if not source.is_file():
            raise ValueError(f"case {case_id!r}: source file does not exist: {source}")
        if source.suffix.casefold() not in ALLOWED_EXTENSIONS:
            raise ValueError(f"case {case_id!r}: unsupported Aspen source extension: {source.suffix}")
        source_hash = sha256_file(source)
        if source_hash in seen_hashes:
            raise ValueError(
                f"duplicate Aspen source content: {case_id} and {seen_hashes[source_hash]} share {source_hash}"
            )
        seen_hashes[source_hash] = case_id
        tags = raw.get("challenge_tags") or []
        if not isinstance(tags, list) or not tags or any(not str(tag).strip() for tag in tags):
            raise ValueError(f"case {case_id!r}: challenge_tags must be a non-empty array")
        normalized.append({
            "case_id": case_id,
            "group": _required_text(raw, "project_group"),
            "project_group": _required_text(raw, "project_group"),
            "process_cluster": _required_text(raw, "process_cluster"),
            "workflow_family": _required_text(raw, "workflow_family"),
            "case_kind": _required_text(raw, "case_kind"),
            "challenge_tags": sorted({str(tag).strip() for tag in tags}),
            "expected_module_families": sorted({
                str(value).strip() for value in (raw.get("expected_module_families") or [])
                if str(value).strip()
            }),
            "unit_system_hint": str(raw.get("unit_system_hint") or "unknown").strip(),
            "path": str(source),
            "source_sha256": source_hash,
            "source_size_bytes": source.stat().st_size,
            "split": split,
        })

    split_cases = {
        split: [case for case in normalized if case["split"] == split]
        for split in SPLIT_CONTRACT
    }
    for split, cases in split_cases.items():
        if not cases:
            raise ValueError(f"split {split!r} has no cases")
        for field, key in (
            ("project_group", "minimum_project_groups"),
            ("process_cluster", "minimum_process_clusters"),
            ("workflow_family", "minimum_workflow_families"),
        ):
            actual = len({case[field] for case in cases})
            required = _minimum(policy, key, split)
            if actual < required:
                raise ValueError(
                    f"split {split!r} has {actual} unique {field} values; policy requires {required}"
                )

    for field in ("project_group", "process_cluster"):
        training_values = {case[field] for case in split_cases["training"]}
        validation_values = {case[field] for case in split_cases["validation"]}
        overlap = sorted(training_values & validation_values)
        if overlap:
            raise ValueError(f"train/validation leakage in {field}: {overlap}")

    output_dir.mkdir(parents=True, exist_ok=True)
    registry_hash = sha256_file(registry_path)
    outputs: dict[str, Path] = {}
    for split, cases in split_cases.items():
        role, tuning_allowed = SPLIT_CONTRACT[split]
        manifest = {
            "schema": SCHEMA,
            "dataset_id": dataset_id,
            "dataset_role": role,
            "split": split,
            "tuning_allowed": tuning_allowed,
            "selection_method": (
                "curated heterogeneous project/process-cluster split with exact-content deduplication; "
                "project_group and process_cluster are disjoint across training and validation"
            ),
            "source_registry_path": str(registry_path),
            "source_registry_sha256": registry_hash,
            "case_count": len(cases),
            "diversity": {
                "project_groups": _case_counter(cases, "project_group"),
                "process_clusters": _case_counter(cases, "process_cluster"),
                "workflow_families": _case_counter(cases, "workflow_family"),
                "case_kinds": _case_counter(cases, "case_kind"),
            },
            "acceptance_profiles": [
                "transport_stability",
                "deterministic_equipment_identity",
                "calculation_chain_coverage",
                "model_or_engineering_specification",
                "authority_overview_field_coverage",
                "formal_evidence_state",
            ],
            "cases": [{key: value for key, value in case.items() if key != "split"} for case in cases],
        }
        path = output_dir / f"{dataset_id}_{split}_manifest.json"
        path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        outputs[f"{split}_manifest"] = path

    audit = {
        "schema": "equipment-design-bkp-benchmark-split-audit-v1",
        "dataset_id": dataset_id,
        "status": "PASS",
        "source_registry_path": str(registry_path),
        "source_registry_sha256": registry_hash,
        "exact_content_duplicate_count": 0,
        "cross_split_project_group_overlap": [],
        "cross_split_process_cluster_overlap": [],
        "training_manifest": str(outputs["training_manifest"]),
        "training_manifest_sha256": sha256_file(outputs["training_manifest"]),
        "validation_manifest": str(outputs["validation_manifest"]),
        "validation_manifest_sha256": sha256_file(outputs["validation_manifest"]),
    }
    audit_path = output_dir / f"{dataset_id}_split_audit.json"
    audit_path.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    outputs["split_audit"] = audit_path
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build leakage-resistant heterogeneous Aspen training and holdout-validation manifests."
    )
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    outputs = build_dataset(args.registry, args.output_dir)
    print(json.dumps({key: str(value) for key, value in outputs.items()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
