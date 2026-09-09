import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("apply_registry_fragments.py")
SPEC = importlib.util.spec_from_file_location("apply_registry_fragments", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class ApplyRegistryFragmentsTests(unittest.TestCase):
    def test_insert_only_merge(self):
        merged, added, replaced = MODULE.merge_rows(
            [{"id": "A", "value": "1"}], [{"id": "B", "value": "2"}],
            "id", set(), "sample",
        )
        self.assertEqual([row["id"] for row in merged], ["A", "B"])
        self.assertEqual(added, ["B"])
        self.assertEqual(replaced, [])

    def test_duplicate_requires_explicit_replacement(self):
        with self.assertRaises(ValueError):
            MODULE.merge_rows(
                [{"id": "A", "value": "1"}], [{"id": "A", "value": "2"}],
                "id", set(), "sample",
            )

    def test_explicit_replacement_preserves_order(self):
        merged, added, replaced = MODULE.merge_rows(
            [{"id": "A", "value": "1"}, {"id": "B", "value": "2"}],
            [{"id": "A", "value": "9"}], "id", {"A"}, "sample",
        )
        self.assertEqual(merged, [{"id": "A", "value": "9"}, {"id": "B", "value": "2"}])
        self.assertEqual(added, [])
        self.assertEqual(replaced, ["A"])


if __name__ == "__main__":
    unittest.main()
