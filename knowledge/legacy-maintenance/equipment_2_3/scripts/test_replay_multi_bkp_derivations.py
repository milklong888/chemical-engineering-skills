from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

try:
    from replay_multi_bkp_derivations import stage_replay_bundle
except ModuleNotFoundError:
    from scripts.replay_multi_bkp_derivations import stage_replay_bundle


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


class ReplayEvidenceBundleTests(unittest.TestCase):
    def test_stages_export_evidence_and_raw_history_as_self_contained_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            output_dir = root / "output"
            source_dir.mkdir()
            history = source_dir / "run.his"
            history.write_text("NO ERRORS OR WARNINGS GENERATED\n", encoding="utf-8")
            evidence = source_dir / "aspen_run_status_evidence.json"
            evidence.write_text(json.dumps({
                "raw_history_path": history.name,
                "raw_history_sha256": sha256(history),
                "counts": {"warnings": 0},
            }), encoding="utf-8")
            export = source_dir / "aspen_equipment_export.json"
            export.write_text(json.dumps({
                "schema": "aspen-equipment-export-v1",
                "case": {
                    "run_status_evidence_path": evidence.name,
                    "run_status_evidence_sha256": sha256(evidence),
                },
                "blocks": [],
                "streams": [],
            }), encoding="utf-8")

            staged, manifest = stage_replay_bundle(export, output_dir)

            self.assertEqual(manifest["status"], "COMPLETE")
            self.assertTrue((output_dir / history.name).is_file())
            self.assertTrue((output_dir / evidence.name).is_file())
            staged_bundle = json.loads(staged.read_text(encoding="utf-8"))
            staged_evidence = json.loads((output_dir / evidence.name).read_text(encoding="utf-8"))
            self.assertEqual(staged_evidence["raw_history_path"], history.name)
            self.assertEqual(staged_evidence["raw_history_sha256"], sha256(output_dir / history.name))
            self.assertEqual(
                staged_bundle["case"]["run_status_evidence_sha256"],
                sha256(output_dir / evidence.name),
            )
            self.assertEqual(manifest["staged_export_sha256"], sha256(staged))

    def test_missing_evidence_is_explicit_and_export_still_staged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            output_dir = root / "output"
            source_dir.mkdir()
            export = source_dir / "aspen_equipment_export.json"
            export.write_text(json.dumps({
                "case": {
                    "run_status_evidence_path": "missing.json",
                    "run_status_evidence_sha256": "A" * 64,
                },
                "blocks": [],
                "streams": [],
            }), encoding="utf-8")

            staged, manifest = stage_replay_bundle(export, output_dir)

            self.assertTrue(staged.is_file())
            self.assertEqual(manifest["status"], "EVIDENCE_NOT_BUNDLED")
            self.assertIn("RUN_STATUS_EVIDENCE_FILE_NOT_FOUND", manifest["issues"])


if __name__ == "__main__":
    unittest.main()
