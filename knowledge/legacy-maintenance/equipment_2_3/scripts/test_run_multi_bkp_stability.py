from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("run_multi_bkp_stability.py")


class RunMultiBkpStabilityCliTests(unittest.TestCase):
    def test_refuses_a_nonempty_output_directory_before_starting_aspen(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            root = Path(raw_tmp)
            source = root / "case.bkp"
            source.write_bytes(b"BKP")
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps({"cases": [{"group": "fixture", "path": str(source)}]}),
                encoding="utf-8",
            )
            output_dir = root / "existing-output"
            output_dir.mkdir()
            marker = output_dir / "do-not-overwrite.txt"
            marker.write_text("existing result", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--manifest",
                    str(manifest),
                    "--output-dir",
                    str(output_dir),
                    "--limit",
                    "1",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
                timeout=30,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("output directory must be empty", completed.stderr + completed.stdout)
            self.assertEqual(marker.read_text(encoding="utf-8"), "existing result")
            self.assertEqual(sorted(path.name for path in output_dir.iterdir()), [marker.name])


if __name__ == "__main__":
    unittest.main()
