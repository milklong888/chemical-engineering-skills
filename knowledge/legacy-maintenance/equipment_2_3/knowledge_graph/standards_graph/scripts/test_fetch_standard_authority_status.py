import unittest
from datetime import date

from fetch_standard_authority_status import (
    authority_state,
    collapse_official_resolution_rows,
    lifecycle_state,
    norm_code,
    parse_detail,
    parse_entries,
)


class AuthorityStatusParserTest(unittest.TestCase):
    def test_exact_code_and_status_are_parsed(self) -> None:
        content = '''
        <a href="#" tid="BV_GB" pid="ABC123" target="_blank">
          <span class="en-code">GB/T 1047-2019</span>&nbsp;&nbsp;title
        </a>
        <span class="s-status label label-success">现行</span>
        '''
        entries = parse_entries(content)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["normalized_code"], norm_code("GB/T 1047-2019"))
        self.assertEqual(authority_state(entries[0]["status_text"]), "CURRENT")

    def test_withdrawn_status(self) -> None:
        self.assertEqual(authority_state("废止"), "WITHDRAWN")

    def test_plan_entry_is_not_a_current_status(self) -> None:
        self.assertEqual(authority_state("已发布"), "UNRESOLVED")

    def test_upcoming_replacement_and_dates_are_parsed(self) -> None:
        content = '''
        <div>即将被以下标准替代</div>
        <a href="https://std.samr.gov.cn/gb/search/gbDetailed?id=NEW">
          <span></span>GB/T 151-2026
        </a><span class="replA">（全部代替）</span>
        <dt class="basicInfo-item name">发布日期</dt>
        <dd class="basicInfo-item value">2014-12-05</dd>
        <dt class="basicInfo-item name">实施日期</dt>
        <dd class="basicInfo-item value">2015-05-01</dd>
        '''
        profile = parse_detail(content)
        self.assertEqual(profile["replaced_by_code"], "GB/T 151-2026")
        self.assertEqual(profile["replacement_relation"], "（全部代替）")
        self.assertEqual(profile["implementation_date"], "2015-05-01")

    def test_current_pending_replacement_uses_effective_date(self) -> None:
        self.assertEqual(
            lifecycle_state("CURRENT", "GB/T 151-2026", "2026-08-01", date(2026, 7, 19)),
            "CURRENT_PENDING_REPLACEMENT",
        )

    def test_verified_manual_resolution_preserves_pending_replacement(self) -> None:
        import csv
        import tempfile
        from pathlib import Path

        fields = [
            "source_id", "sha256", "official_standard_no", "authority_status",
            "resolution", "official_url", "publication_date", "implementation_date",
            "future_replacement_date", "replacement_relation",
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "official.csv"
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow(
                    {
                        "source_id": "std_x", "sha256": "A" * 64,
                        "official_standard_no": "GB/T X-2014",
                        "authority_status": "现行（即将被替代）", "resolution": "VERIFIED",
                        "official_url": "https://example.invalid/official",
                        "future_replacement_date": "2026-08-01",
                    }
                )
            with path.open(encoding="utf-8-sig", newline="") as handle:
                source_rows = list(csv.DictReader(handle))
            result = collapse_official_resolution_rows(
                source_rows, path, date(2026, 7, 19)
            )["std_x"]
            self.assertEqual(result["authority_state"], "CURRENT")
            self.assertEqual(result["lifecycle_state"], "CURRENT_PENDING_REPLACEMENT")
            self.assertTrue(result["resolution_evidence_sha256"])

    def test_unresolved_manual_member_keeps_source_unresolved(self) -> None:
        import csv
        import tempfile
        from pathlib import Path

        fields = [
            "source_id", "sha256", "official_standard_no", "authority_status", "resolution"
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "official.csv"
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow(
                    {
                        "source_id": "std_u", "sha256": "B" * 64,
                        "official_standard_no": "HGJ 1", "authority_status": "未决",
                        "resolution": "UNRESOLVED",
                    }
                )
            with path.open(encoding="utf-8-sig", newline="") as handle:
                source_rows = list(csv.DictReader(handle))
            result = collapse_official_resolution_rows(
                source_rows, path, date(2026, 7, 19)
            )["std_u"]
            self.assertEqual(result["authority_state"], "UNRESOLVED")


if __name__ == "__main__":
    unittest.main()
