from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    from build_bkp_benchmark_dataset import build_dataset
except ModuleNotFoundError:  # package-style discovery from the repository root
    from scripts.build_bkp_benchmark_dataset import build_dataset


class BuildBkpBenchmarkDatasetTests(unittest.TestCase):
    def test_writes_runnable_training_and_holdout_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            source_dir = root / "sources"
            source_dir.mkdir()
            paths: list[Path] = []
            for index in range(4):
                path = source_dir / f"case_{index}.bkp"
                path.write_bytes(f"BKP-{index}".encode("ascii"))
                paths.append(path)

            registry = {
                "schema": "equipment-design-bkp-benchmark-registry-v1",
                "dataset_id": "fixture-v1",
                "policy": {
                    "minimum_project_groups": {"training": 2, "validation": 2},
                    "minimum_process_clusters": {"training": 2, "validation": 2},
                    "minimum_workflow_families": {"training": 2, "validation": 2},
                },
                "cases": [
                    {
                        "case_id": "train-reactor",
                        "split": "training",
                        "path": str(paths[0]),
                        "project_group": "project-a",
                        "process_cluster": "reaction-a",
                        "workflow_family": "reaction",
                        "case_kind": "single_unit",
                        "challenge_tags": ["reactor"],
                    },
                    {
                        "case_id": "train-hen",
                        "split": "training",
                        "path": str(paths[1]),
                        "project_group": "project-b",
                        "process_cluster": "hen-b",
                        "workflow_family": "heat_integration",
                        "case_kind": "full_flow",
                        "challenge_tags": ["heatx"],
                    },
                    {
                        "case_id": "val-column",
                        "split": "validation",
                        "path": str(paths[2]),
                        "project_group": "project-c",
                        "process_cluster": "distillation-c",
                        "workflow_family": "distillation",
                        "case_kind": "full_flow",
                        "challenge_tags": ["radfrac"],
                    },
                    {
                        "case_id": "val-solids",
                        "split": "validation",
                        "path": str(paths[3]),
                        "project_group": "project-d",
                        "process_cluster": "crystallization-d",
                        "workflow_family": "solids",
                        "case_kind": "full_flow",
                        "challenge_tags": ["crystallizer"],
                    },
                ],
            }
            registry_path = root / "registry.json"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")

            outputs = build_dataset(registry_path, root / "out")

            training = json.loads(outputs["training_manifest"].read_text(encoding="utf-8"))
            validation = json.loads(outputs["validation_manifest"].read_text(encoding="utf-8"))
            self.assertEqual(training["dataset_role"], "development_training")
            self.assertTrue(training["tuning_allowed"])
            self.assertEqual(validation["dataset_role"], "holdout_validation")
            self.assertFalse(validation["tuning_allowed"])
            self.assertEqual(len(training["cases"]), 2)
            self.assertEqual(len(validation["cases"]), 2)
            for case in training["cases"] + validation["cases"]:
                self.assertEqual(len(case["source_sha256"]), 64)
                self.assertGreater(case["source_size_bytes"], 0)
                self.assertIn("process_cluster", case)
                self.assertIn("workflow_family", case)

    def test_rejects_project_or_process_cluster_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            paths = []
            for index in range(2):
                path = root / f"case_{index}.bkp"
                path.write_bytes(f"UNIQUE-{index}".encode("ascii"))
                paths.append(path)
            registry = {
                "schema": "equipment-design-bkp-benchmark-registry-v1",
                "dataset_id": "leakage-fixture",
                "policy": {
                    "minimum_project_groups": {"training": 1, "validation": 1},
                    "minimum_process_clusters": {"training": 1, "validation": 1},
                    "minimum_workflow_families": {"training": 1, "validation": 1},
                },
                "cases": [
                    {
                        "case_id": "train",
                        "split": "training",
                        "path": str(paths[0]),
                        "project_group": "same-project",
                        "process_cluster": "same-process",
                        "workflow_family": "distillation",
                        "case_kind": "full_flow",
                        "challenge_tags": ["base"],
                    },
                    {
                        "case_id": "validation",
                        "split": "validation",
                        "path": str(paths[1]),
                        "project_group": "same-project",
                        "process_cluster": "same-process",
                        "workflow_family": "distillation",
                        "case_kind": "full_flow",
                        "challenge_tags": ["variant"],
                    },
                ],
            }
            registry_path = root / "registry.json"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "train/validation leakage"):
                build_dataset(registry_path, root / "out")

    def test_rejects_exact_content_duplicates_even_under_different_names(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            first = root / "first.bkp"
            second = root / "renamed-copy.bkp"
            first.write_bytes(b"SAME-BKP")
            second.write_bytes(b"SAME-BKP")
            registry = {
                "schema": "equipment-design-bkp-benchmark-registry-v1",
                "dataset_id": "duplicate-fixture",
                "policy": {
                    "minimum_project_groups": {"training": 1, "validation": 1},
                    "minimum_process_clusters": {"training": 1, "validation": 1},
                    "minimum_workflow_families": {"training": 1, "validation": 1},
                },
                "cases": [
                    {
                        "case_id": "train",
                        "split": "training",
                        "path": str(first),
                        "project_group": "project-a",
                        "process_cluster": "process-a",
                        "workflow_family": "reaction",
                        "case_kind": "single_unit",
                        "challenge_tags": ["base"],
                    },
                    {
                        "case_id": "validation",
                        "split": "validation",
                        "path": str(second),
                        "project_group": "project-b",
                        "process_cluster": "process-b",
                        "workflow_family": "distillation",
                        "case_kind": "full_flow",
                        "challenge_tags": ["renamed-copy"],
                    },
                ],
            }
            registry_path = root / "registry.json"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "duplicate Aspen source content"):
                build_dataset(registry_path, root / "out")

    def test_rejects_source_extension_not_supported_by_the_aspen_importer(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            unsupported = root / "archive.apwz"
            supported = root / "validation.bkp"
            unsupported.write_bytes(b"APWZ")
            supported.write_bytes(b"BKP")
            registry = {
                "schema": "equipment-design-bkp-benchmark-registry-v1",
                "dataset_id": "extension-fixture",
                "policy": {
                    "minimum_project_groups": {"training": 1, "validation": 1},
                    "minimum_process_clusters": {"training": 1, "validation": 1},
                    "minimum_workflow_families": {"training": 1, "validation": 1},
                },
                "cases": [
                    {
                        "case_id": "train-unsupported",
                        "split": "training",
                        "path": str(unsupported),
                        "project_group": "project-a",
                        "process_cluster": "process-a",
                        "workflow_family": "batch",
                        "case_kind": "single_unit",
                        "challenge_tags": ["unsupported-import-path"],
                    },
                    {
                        "case_id": "validation-supported",
                        "split": "validation",
                        "path": str(supported),
                        "project_group": "project-b",
                        "process_cluster": "process-b",
                        "workflow_family": "reaction",
                        "case_kind": "single_unit",
                        "challenge_tags": ["supported-import-path"],
                    },
                ],
            }
            registry_path = root / "registry.json"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unsupported Aspen source extension"):
                build_dataset(registry_path, root / "out")


if __name__ == "__main__":
    unittest.main()
