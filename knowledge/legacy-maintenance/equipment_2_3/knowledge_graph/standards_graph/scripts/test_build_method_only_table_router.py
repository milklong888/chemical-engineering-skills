import unittest

from build_method_only_table_router import build_rows


class MethodOnlyTableRouterTests(unittest.TestCase):
    def test_builds_caption_router_without_numeric_reuse(self):
        source = [{
            "record_id": "R1",
            "table_id": "T1",
            "physical_page": "12",
            "caption": "表1 示例",
            "source_pdf_sha256": "ABC",
            "reuse_class": "METHOD_ONLY",
            "numeric_cells_exposed": "False",
            "runtime_numeric_reuse_allowed": "False",
            "query_payload": "locator only",
        }]
        result = build_rows(source, "ABC")
        self.assertEqual(result[0]["normalized_value"], "表1 示例")
        self.assertEqual(result[0]["terminal_class"], "METHOD_ONLY_ROUTER")

    def test_rejects_numeric_exposure(self):
        source = [{
            "record_id": "R1", "table_id": "T1", "physical_page": "12",
            "caption": "表1", "source_pdf_sha256": "ABC", "reuse_class": "METHOD_ONLY",
            "numeric_cells_exposed": "True", "runtime_numeric_reuse_allowed": "False",
        }]
        with self.assertRaises(ValueError):
            build_rows(source, "ABC")


if __name__ == "__main__":
    unittest.main()
