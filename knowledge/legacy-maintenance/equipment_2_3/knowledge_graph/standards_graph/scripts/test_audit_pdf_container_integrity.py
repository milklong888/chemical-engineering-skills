import tempfile
import unittest
from pathlib import Path

from audit_pdf_container_integrity import audit_pdf


class PdfContainerIntegrityTests(unittest.TestCase):
    def test_detects_zero_padded_truncation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "truncated.pdf"
            path.write_bytes(
                b"%PDF-1.6\n1 0 obj\n<</Type/Page>>\nendobj\n"
                + (b"\x00" * (1024 * 1024 + 1))
            )
            result = audit_pdf(path)
            self.assertEqual(result["status"], "TRUNCATED_ZERO_PADDED")
            self.assertEqual(
                result["content_recovery_state"],
                "SOURCE_UNREADABLE_BLOCKED_REACQUIRE_REQUIRED",
            )

    def test_basic_marker_candidate_is_not_claimed_parser_valid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate.pdf"
            path.write_bytes(b"%PDF-1.4\nstartxref\n0\n%%EOF\n")
            result = audit_pdf(path)
            self.assertEqual(result["status"], "BASIC_CONTAINER_MARKERS_PRESENT")
            self.assertEqual(result["content_recovery_state"], "PARSER_VALIDATION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
