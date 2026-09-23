"""Independent synthetic-source tests; no project exercises or answers."""
from __future__ import annotations

import hashlib
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TEST_DIRECTORY = Path(__file__).resolve().parent
CANDIDATE = (TEST_DIRECTORY.parent / "check_flow_handoff.py" if TEST_DIRECTORY.name == "tests"
             else TEST_DIRECTORY / "check_flow_handoff.py")
spec = importlib.util.spec_from_file_location("candidate_handoff", CANDIDATE)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class SourceReviewTests(unittest.TestCase):
    def handoff(self):
        return {
            "schema": "document-flow-handoff-v1", "stage": "source",
            "authority_reference": "synthetic arrangement; no project data",
            "nodes": [{"id": "FEED", "kind": "external"},
                      {"id": "P", "kind": "process"}, {"id": "EXIT", "kind": "external"}],
            "streams": [{"id": "S1", "from": "FEED", "to": "P", "state": "documented",
                         "evidence": "inert synthetic citation", "gap": None},
                        {"id": "S2", "from": "P", "to": "EXIT", "state": "documented",
                         "evidence": "inert synthetic citation", "gap": None}],
            "control_volumes": [{"id": "V", "members": ["P"], "inflows": ["S1"],
                                 "outflows": ["S2"], "balance_basis": "synthetic steady flow",
                                 "reaction_terms": "no reaction in this logical fixture"}],
            "placeholders": [], "no_placeholders_reason": "No simplified physical duties in this synthetic fixture.",
            "handoffs": [],
        }

    def reviewed_handoff(self):
        data = self.handoff()
        inventory = checker.source_inventory(self.documents, source_root=self.root)
        data["source_review"] = {"documents": copy.deepcopy(self.documents), "units": [
            {"unit_id": inventory[0]["unit_id"], "disposition": "mapped", "stream_ids": ["S1"],
             "reason": "The listed feed connection is represented by S1."},
            {"unit_id": inventory[1]["unit_id"], "disposition": "context", "stream_ids": [],
             "reason": "This paragraph provides context, not a connection requirement."},
            {"unit_id": inventory[2]["unit_id"], "disposition": "unresolved", "stream_ids": [],
             "reason": "The receiver of the mentioned transfer is absent from this source."},
        ]}
        return data

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="handoff-source-review-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.md"
        self.raw = "流股从入口送往处理节点。\n此句属于同一段。\n\nThis paragraph is context only.\n\nA destination remains unspecified.\n".encode("utf-8")
        self.source.write_bytes(self.raw)
        self.documents = [{"id": "source", "path": "source.md",
                           "sha256": hashlib.sha256(self.raw).hexdigest()}]

    def test_reads_inventory_from_explicit_sources(self):
        inventory = checker.source_inventory(self.documents, source_root=self.root)
        self.assertEqual(len(inventory), 3)
        self.assertEqual((inventory[0]["line_start"], inventory[0]["line_end"]), (1, 2))
        self.assertEqual(inventory[0]["text"], "流股从入口送往处理节点。\n此句属于同一段。")
        self.assertEqual(inventory[0]["text_sha256"],
                         hashlib.sha256(inventory[0]["text"].encode("utf-8")).hexdigest())
        self.assertEqual(inventory, checker.source_inventory(self.documents, source_root=self.root))

    def test_mixed_separator_network_device_paths_rejected_before_io(self):
        paths = ["/\\example.invalid/share/source.md", "\\/example.invalid/share/source.md",
                 "/\\?\\C:\\source.md", "\\/.\\C:\\source.md"]
        for value in paths:
            with self.subTest(value=value), patch.object(Path, "resolve", side_effect=AssertionError("No filesystem access allowed")):
                with self.assertRaisesRegex(ValueError, "network, device or URI"):
                    checker._source_local_path(value, "synthetic")
                with self.assertRaisesRegex(ValueError, "network, device or URI"):
                    checker.source_inventory(self.documents, source_root=value)

    def test_dos_device_names_rejected_before_io(self):
        values = ["C:/source/NUL.txt", "C:/source/CON.md", "NUL.txt", "AUX.md",
                  "C:/COM1.txt", "LPT1.md", "PRN.txt", "con. "]
        for value in values:
            with self.subTest(value=value), patch.object(Path, "resolve", side_effect=AssertionError("No filesystem access allowed")):
                with self.assertRaisesRegex(ValueError, "reserved Windows device"):
                    checker._source_local_path(value, "synthetic")
                with self.assertRaisesRegex(ValueError, "reserved Windows device"):
                    checker.source_inventory(self.documents, source_root=value)

    def test_checks_each_disposition_and_projects_original_edges(self):
        result = checker.check(self.reviewed_handoff(), source_root=self.root)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["status"], "STRUCTURE_VALID_WITH_UNRESOLVED")
        self.assertTrue(result["source_review_checked"])
        self.assertEqual(len(result["source_review"]["inventory"]), 3)
        self.assertEqual([x["disposition"] for x in result["source_review"]["rows"]],
                         ["mapped", "context", "unresolved"])
        projected = result["source_review"]["rows"][0]
        self.assertEqual(projected["streams"][0]["from"], "FEED")
        self.assertEqual(projected["streams"][0]["to"], "P")
        self.assertEqual(projected["text"], result["source_review"]["inventory"][0]["text"])
        for flag in ("source_inventory_verified", "authority_verified", "engineering_accepted", "execution_verified"):
            self.assertIs(result[flag], False)

    def test_actual_cli_inventory_then_checked_report(self):
        request = self.root / "request.json"
        request.write_text(json.dumps({"source_review": {"documents": self.documents}}), encoding="utf-8")
        run = subprocess.run([sys.executable, "-B", "-X", "utf8", str(CANDIDATE),
                              "--source-inventory", "--input", str(request), "--source-root", str(self.root)],
                             capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        inventory = json.loads(run.stdout)
        self.assertEqual(inventory["schema"], "document-flow-source-inventory-v1")
        self.assertEqual(len(inventory["inventory"]), 3)
        self.assertIs(inventory["source_inventory_verified"], False)
        data = self.reviewed_handoff()
        request.write_text(json.dumps(data), encoding="utf-8")
        output = self.root / "report"
        run = subprocess.run([sys.executable, "-B", "-X", "utf8", str(CANDIDATE),
                              "--input", str(request), "--source-root", str(self.root), "--output-dir", str(output)],
                             capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        summary = json.loads(run.stdout)
        self.assertTrue(summary["source_review_checked"])
        report = json.loads((output / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(report["source_review"]["rows"][0]["streams"][0]["stream_id"], "S1")
        rendered = (output / "handoff.md").read_text(encoding="utf-8")
        self.assertIn("This paragraph is context only.", rendered)
        self.assertIn('"from": "FEED"', rendered)


    def assert_review_invalid(self, data, message, root=None):
        result = checker.check(data, source_root=self.root if root is None else root)
        self.assertEqual(result["status"], "STRUCTURE_INVALID")
        self.assertFalse(result["source_review_checked"])
        self.assertTrue(result["source_review"]["errors"])
        self.assertIn(message, " ".join(result["errors"]))
        self.assertFalse(result["source_inventory_verified"])

    def test_missing_paragraph_is_rejected(self):
        data = self.reviewed_handoff()
        data["source_review"]["units"].pop()
        self.assert_review_invalid(data, "missing source paragraphs")

    def test_unresolved_paragraph_preserves_known_stream_mapping(self):
        data = self.reviewed_handoff()
        data["source_review"]["units"][2]["stream_ids"] = ["S2"]
        result = checker.check(data, source_root=self.root)
        self.assertEqual(result["errors"], [])
        self.assertTrue(result["source_review_checked"])
        self.assertEqual(result["status"], "STRUCTURE_VALID_WITH_UNRESOLVED")
        row = result["source_review"]["rows"][2]
        self.assertEqual(row["disposition"], "unresolved")
        self.assertEqual(row["stream_ids"], ["S2"])
        self.assertEqual(row["streams"][0]["to"], "EXIT")
        self.assertIn("receiver", row["reason"])
        data["source_review"]["units"][2]["stream_ids"] = ["UNKNOWN"]
        self.assert_review_invalid(data, "unregistered streams")

    def test_duplicate_paragraph_is_rejected(self):
        data = self.reviewed_handoff()
        data["source_review"]["units"].append(copy.deepcopy(data["source_review"]["units"][0]))
        self.assert_review_invalid(data, "duplicate source paragraph")

    def test_unknown_paragraph_is_rejected(self):
        data = self.reviewed_handoff()
        data["source_review"]["units"][0]["unit_id"] = "not-in-the-source"
        self.assert_review_invalid(data, "unknown source paragraph")

    def test_unknown_stream_is_rejected(self):
        data = self.reviewed_handoff()
        data["source_review"]["units"][0]["stream_ids"] = ["UNKNOWN"]
        self.assert_review_invalid(data, "unregistered streams")

    def test_source_hash_drift_is_rejected(self):
        data = self.reviewed_handoff()
        self.source.write_bytes(self.raw + b"\nNew paragraph.\n")
        self.assert_review_invalid(data, "source hash differs")

    def test_root_escape_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="handoff-outside-") as outside:
            path = Path(outside) / "outside.md"
            path.write_bytes(self.raw)
            data = self.reviewed_handoff()
            data["source_review"]["documents"][0]["path"] = str(path)
            self.assert_review_invalid(data, "leaves explicit source_root")

    def test_missing_explicit_root_is_rejected(self):
        result = checker.check(self.reviewed_handoff())
        self.assertFalse(result["source_review_checked"])
        self.assertIn("source_root", " ".join(result["errors"]))

    def test_bad_utf8_is_rejected(self):
        data = self.reviewed_handoff()
        raw = b"\xff\xfe invalid"
        self.source.write_bytes(raw)
        data["source_review"]["documents"][0]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.assert_review_invalid(data, "not valid UTF-8")

    def test_per_file_size_limit_is_rejected(self):
        data = self.reviewed_handoff()
        raw = b"a" * (checker.SOURCE_MAX_FILE_BYTES + 1)
        self.source.write_bytes(raw)
        data["source_review"]["documents"][0]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.assert_review_invalid(data, "source exceeds")

    def test_document_count_is_bounded(self):
        documents = self.documents * (checker.SOURCE_MAX_DOCUMENTS + 1)
        with self.assertRaisesRegex(ValueError, "exceeds .* documents"):
            checker.source_inventory(documents, source_root=self.root)

    def test_total_read_size_is_bounded(self):
        documents = []
        raw = b"z" * checker.SOURCE_MAX_FILE_BYTES
        for index in range(checker.SOURCE_MAX_TOTAL_BYTES // checker.SOURCE_MAX_FILE_BYTES + 1):
            path = self.root / f"part{index}.txt"
            path.write_bytes(raw)
            documents.append({"id": f"d{index}", "path": path.name,
                              "sha256": hashlib.sha256(raw).hexdigest()})
        with self.assertRaisesRegex(ValueError, "total bytes"):
            checker.source_inventory(documents, source_root=self.root)

    def test_paragraph_count_is_bounded(self):
        raw = b"x\n\n" * (checker.SOURCE_MAX_UNITS + 1)
        self.source.write_bytes(raw)
        self.documents[0]["sha256"] = hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(ValueError, "nonempty paragraphs"):
            checker.source_inventory(self.documents, source_root=self.root)

    def test_duplicate_documents_and_paths_are_rejected(self):
        for second in (self.documents[0], {**self.documents[0], "id": "different"}):
            with self.subTest(second=second["id"]):
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    checker.source_inventory(self.documents + [second], source_root=self.root)

    def test_network_and_device_paths_are_rejected_before_read(self):
        for path in ("//example.invalid/share/source.md", r"\\example.invalid\share\source.md",
                     r"\\?\C:\source.md", "https://example.invalid/source.md"):
            with self.subTest(path=path):
                documents = [{**self.documents[0], "path": path}]
                with self.assertRaisesRegex(ValueError, "not allowed"):
                    checker.source_inventory(documents, source_root=self.root)
        with self.assertRaisesRegex(ValueError, "not allowed"):
            checker.source_inventory(self.documents, source_root="//example.invalid/share")

    def test_empty_unsupported_and_missing_sources_fail_closed(self):
        for path, raw, expected in (("empty.txt", b" \n\n", "no nonempty paragraphs"),
                                    ("unsafe.py", b"print('never executed')", ".txt/.md"),
                                    ("nul-byte.txt", b"content\x00", "NUL")):
            with self.subTest(path=path):
                source = self.root / path
                source.write_bytes(raw)
                documents = [{"id": "edge", "path": path, "sha256": hashlib.sha256(raw).hexdigest()}]
                with self.assertRaisesRegex(ValueError, expected):
                    checker.source_inventory(documents, source_root=self.root)
        with self.assertRaises(OSError):
            checker.source_inventory([{**self.documents[0], "path": "missing.md"}], source_root=self.root)

    def test_disposition_shape_and_nonempty_reasons(self):
        cases = [
            (0, "stream_ids", [], "nonempty array"),
            (0, "stream_ids", ["S1", "S1"], "duplicate identifiers"),
            (1, "reason", "   ", "nonempty text"),
            (2, "reason", "", "nonempty text"),
            (1, "stream_ids", ["S1"], "requires empty stream_ids"),
            (2, "disposition", "passed", "mapped, context or unresolved"),
        ]
        for index, field, value, message in cases:
            with self.subTest(field=field, value=value):
                data = self.reviewed_handoff()
                data["source_review"]["units"][index][field] = value
                self.assert_review_invalid(data, message)

    def test_old_call_and_inert_citations_are_compatible(self):
        data = self.handoff()
        data["streams"][0]["evidence"] = "//example.invalid/not-opened"
        result = checker.check(data)
        self.assertEqual(result["status"], "STRUCTURE_VALID")
        self.assertEqual(result["errors"], [])
        self.assertFalse(result["source_review_checked"])
        self.assertNotIn("source_review", result)

    def test_same_paragraph_repetition_has_distinct_unit_ids(self):
        raw = b"Repeated source paragraph.\n\nRepeated source paragraph.\n"
        self.source.write_bytes(raw)
        self.documents[0]["sha256"] = hashlib.sha256(raw).hexdigest()
        inventory = checker.source_inventory(self.documents, source_root=self.root)
        self.assertNotEqual(inventory[0]["unit_id"], inventory[1]["unit_id"])
        self.assertEqual(inventory[0]["text_sha256"], inventory[1]["text_sha256"])

    def test_inventory_cli_requires_root_and_never_writes_a_report(self):
        request = self.root / "inventory.json"
        request.write_text(json.dumps({"source_review": {"documents": self.documents}}), encoding="utf-8")
        run = subprocess.run([sys.executable, "-B", "-X", "utf8", str(CANDIDATE),
                              "--source-inventory", "--input", str(request)],
                             capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(run.returncode, 2)
        self.assertIn("source_root", run.stdout)
        self.assertFalse((self.root / "review.json").exists())


    def strict_runtime(self):
        """Install only candidate + fixed registered assets into this test's disposable tree."""
        import shutil
        skills = self.root / "test-runtime" / "skills"
        target = skills / "aspen-document-driven-flowsheet" / "scripts" / "check_flow_handoff.py"
        target.parent.mkdir(parents=True)
        shutil.copyfile(CANDIDATE, target)
        candidates = [CANDIDATE.parents[2]] + [
            parent / "_skill_refactor/fullflow_gate_20260918/repository/plugins/chemical-engineering-skills/skills"
            for parent in TEST_DIRECTORY.parents]
        registered = next((path for path in candidates
                           if (path / "chemical-engineering-expert/scripts/check_reaction_derivations.py").is_file()
                           and (path / "aspen-document-driven-flowsheet/assets/property_method_names_v14.json").is_file()), None)
        if registered is None:
            raise RuntimeError("Fixed sibling test assets are unavailable in this source layout")
        for owner, relative in (
            ("chemical-engineering-expert", "scripts/check_reaction_derivations.py"),
            ("aspen-document-driven-flowsheet", "assets/property_method_names_v14.json"),
        ):
            source = registered / owner / relative
            destination = skills / owner / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        runtime_spec = importlib.util.spec_from_file_location("synthetic_runtime_handoff", target)
        runtime = importlib.util.module_from_spec(runtime_spec)
        runtime_spec.loader.exec_module(runtime)
        return runtime, target

    def strict_handoff(self):
        data = self.reviewed_handoff()
        data["expert_plan"] = {
            "methods": [{"node_ids": ["P"], "method": "synthetic identity transport",
                         "phases": ["liquid"], "applicability": "A test-only logical transfer.",
                         "source": "synthetic declared model", "status": "source_fixed", "unresolved_inputs": [],
                         "named_methods": [{"name": "Synthetic identity", "name_origin": "source_defined",
                                           "source_ref": "synthetic local definition",
                                           "definition_ref": "outlet equals inlet in this logical fixture",
                                           "applies_when": "No physical property calculation is asserted."}]}],
            "pressure_paths": [{"id": "P-BASIS", "node_ids": ["P"], "stream_ids": [],
                                "state": "not_applicable", "method": "logical identity",
                                "equation_or_reason": "This fixture models no physical pressure operation.",
                                "source": "synthetic local scope", "inputs": [],
                                "refine_trigger": "Replace logical fixture if physical service is introduced.",
                                "interface_actions": []}],
            "recycle_plan": [], "no_recycle_reason": "The synthetic graph is a single forward transfer.",
            "reaction_derivations": {"reactions": [], "none_reason": "No reaction-derived number is used by this logical fixture."},
        }
        return data

    def test_strict_source_flag_executes_all_existing_checks(self):
        runtime, target = self.strict_runtime()
        data = self.strict_handoff()
        result = runtime.check(data, require_source_review=True, source_root=self.root)
        self.assertEqual(result["errors"], [])
        for flag in ("source_review_checked", "expert_plan_checked", "named_method_declarations_checked",
                     "plan_action_declarations_checked", "reaction_derivations_checked"):
            self.assertIs(result[flag], True)
        self.assertEqual(result["reaction_math"]["result"]["status"], "not_applicable")
        self.assertIs(result["reaction_math"]["result"]["math_valid"], False)
        request = self.root / "strict.json"
        request.write_text(json.dumps(data), encoding="utf-8")
        output = self.root / "strict-report"
        run = subprocess.run([sys.executable, "-B", "-X", "utf8", str(target),
                              "--input", str(request), "--output-dir", str(output),
                              "--require-source-review", "--source-root", str(self.root)],
                             capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertTrue(json.loads(run.stdout)["source_review_checked"])

    def test_strict_source_flag_rejects_missing_review_and_prior_declarations(self):
        runtime, _ = self.strict_runtime()
        data = self.strict_handoff()
        del data["source_review"]
        result = runtime.check(data, require_source_review=True, source_root=self.root)
        self.assertIn("source_review: required", " ".join(result["errors"]))
        self.assertFalse(result["source_review_checked"])
        for field, expected in (("expert_plan", "expert_plan"),
                                ("named_methods", "named_methods"),
                                ("reaction_derivations", "reaction_derivations")):
            with self.subTest(field=field):
                data = self.strict_handoff()
                if field == "expert_plan":
                    del data["expert_plan"]
                elif field == "named_methods":
                    del data["expert_plan"]["methods"][0]["named_methods"]
                else:
                    del data["expert_plan"]["reaction_derivations"]
                result = runtime.check(data, require_source_review=True, source_root=self.root)
                self.assertEqual(result["status"], "STRUCTURE_INVALID")
                self.assertIn(expected, " ".join(result["errors"]))

    def test_bom_and_crlf_have_document_hash_and_normalized_paragraph_hash(self):
        raw = b"\xef\xbb\xbfFirst line.\r\nSecond line.\r\n\r\nThird line.\r\n"
        self.source.write_bytes(raw)
        self.documents[0]["sha256"] = hashlib.sha256(raw).hexdigest()
        inventory = checker.source_inventory(self.documents, source_root=self.root)
        self.assertEqual(inventory[0]["text"], "First line.\nSecond line.")
        self.assertEqual(inventory[0]["document_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(inventory[1]["line_start"], 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
