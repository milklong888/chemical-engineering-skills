from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = APP_DIR.parent
SCRIPTS_DIR = PACKAGE_ROOT / "scripts"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import aspen_equipment_derivation as derivation
import audit_stage1_detailed_reliability as audit


class Stage1DetailedReliabilityAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = (
            PACKAGE_ROOT
            / "outputs"
            / "real_bkp_stage1_20260723"
            / "exercise2_4_augmented_run"
            / "aspen_equipment_export.json"
        )
        bundle = json.loads(cls.source.read_text(encoding="utf-8"))
        cls.document = derivation.derive_bundle(bundle, cls.source)
        cls.physical_pipe = next(
            item
            for item in cls.document["equipment"]
            if item.get("aspen_block_id") == "P1"
        )

    def _binding_is_valid(self, item: dict) -> bool:
        valid, _ = audit.program_generated_record_binding_valid(
            item=item,
            record_kind="physical_pipe_block",
            identity="P1",
            source_export_sha256=self.document[
                "source_export_sha256"
            ],
        )
        return valid

    def test_final_row_binding_covers_lineage_provenance_and_derivation(
        self,
    ) -> None:
        self.assertTrue(self._binding_is_valid(self.physical_pipe))

        binding = self.physical_pipe[
            "program_generated_record_binding"
        ]
        self.assertEqual(
            binding["parameter_lineage_sha256"],
            audit.canonical_sha256(
                self.physical_pipe["parameter_lineage"]
            ),
        )
        self.assertEqual(
            binding["derivation_chain_sha256"],
            audit.canonical_sha256(
                self.physical_pipe["derivation_chain"]
            ),
        )
        self.assertEqual(
            binding["input_provenance_snapshot_sha256"],
            self.physical_pipe["input_provenance"][
                "final_snapshot_sha256"
            ],
        )

    def test_stale_lineage_count_is_rejected_even_if_binding_is_untouched(
        self,
    ) -> None:
        tampered = copy.deepcopy(self.physical_pipe)
        tampered["input_provenance"]["lineage_count"] -= 1
        tampered["match_result"]["input_provenance"] = copy.deepcopy(
            tampered["input_provenance"]
        )
        self.assertFalse(self._binding_is_valid(tampered))

    def test_derivation_chain_tamper_is_rejected(self) -> None:
        tampered = copy.deepcopy(self.physical_pipe)
        tampered["derivation_chain"].append(
            {"formula": "forged = 1"}
        )
        self.assertFalse(self._binding_is_valid(tampered))


if __name__ == "__main__":
    unittest.main()
