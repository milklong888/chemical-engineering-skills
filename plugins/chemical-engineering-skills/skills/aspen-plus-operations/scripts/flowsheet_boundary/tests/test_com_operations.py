# SPDX-License-Identifier: MIT
"""Synthetic adapter-contract tests; these do not emulate Aspen thermodynamics."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from flowsheet_boundary.com_operations import remove_terminal_heaters, enable_hcurves


class Elements:
    def __init__(self, owner): self.owner = owner
    def __iter__(self): return iter(self.owner.children.values())
    def Remove(self, name): del self.owner.children[name]
    def Add(self, name):
        if name in self.owner.children: raise ValueError("duplicate")
        n = self.owner.add(name)
        if self.owner.on_add: self.owner.on_add(name)
        return n


class Node:
    def __init__(self, name, value=None, kind=""):
        self.Name, self.Value, self.kind = name, value, kind
        self.children = {}; self.on_add = None; self.Elements = Elements(self)
    def add(self, name, value=None, kind=""):
        n = Node(name, value, kind); self.children[name] = n; return n
    def AttributeValue(self, attribute):
        if attribute != 6: raise ValueError(attribute)
        return self.kind


class Tree:
    def __init__(self): self.root = Node("")
    def FindNode(self, path):
        n = self.root
        for segment in path.strip("\\").split("\\"):
            if segment not in n.children: return None
            n = n.children[segment]
        return n


class App:
    def __init__(self):
        self.Tree = Tree(); data = self.Tree.root.add("Data")
        blocks = data.add("Blocks"); streams = data.add("Streams")
        for sid in ["FEED", "MID", "PRODUCT"]: streams.add(sid)
        for bid, inputs, outputs, kind in [("UP", ["FEED"], ["MID"], "RADFRAC"), ("END", ["MID"], ["PRODUCT"], "HEATER")]:
            block = blocks.add(bid, kind=kind); ports = block.add("Ports")
            for label, names in [("F(IN)", inputs), ("P(OUT)", outputs)]:
                port = ports.add(label)
                for name in names: port.add(name)
            block.add("Input").add("TOL", 0.0001)
        curves = blocks.children["END"].add("Subobjects").add("Hcurves")
        def add_curve(name):
            root = blocks.children["END"].children["Input"]
            for key in ["INDEP_VAR", "OPT_RANGE", "NPOINTS", "PRES_PROFILE"]:
                if key not in root.children: root.add(key)
                root.children[key].add(name)
        curves.on_add = add_curve


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.app = App()
        self.request = [{"block": "END", "inlet": "MID", "outlet": "PRODUCT", "confirmed_no_outlet_conditioning_requirement": True}]
        self.counts = {"blocks_before": 2, "streams_before": 3, "blocks_after": 1, "streams_after": 2}
        self.guard = [r"\Data\Blocks\UP\Input"]
        self.env = patch.dict(os.environ, {"ASPEN_RUNTIME_OWNER_TOKEN": "synthetic-test-only"}); self.env.start(); self.addCleanup(self.env.stop)
    def run_remove(self):
        return remove_terminal_heaters(self.app, self.request, input_guard_paths=self.guard, expected_counts=self.counts)
    def test_removes_only_approved_end_and_dead_outlet(self):
        result = self.run_remove()
        self.assertEqual(result["remaining_blocks"], ["UP"])
        self.assertEqual(result["remaining_streams"], ["FEED", "MID"])
        self.assertEqual(self.app.Tree.FindNode(r"\Data\Blocks\UP\Input\TOL").Value, 0.0001)
    def test_requires_owned_runner(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(RuntimeError): self.run_remove()
    def test_requires_engineering_authority(self):
        self.request[0]["confirmed_no_outlet_conditioning_requirement"] = False
        with self.assertRaises(ValueError): self.run_remove()
        self.assertIsNotNone(self.app.Tree.FindNode(r"\Data\Blocks\END"))
    def test_downstream_consumer_prevents_removal(self):
        self.app.Tree.FindNode(r"\Data\Blocks\UP\Ports\F(IN)").add("PRODUCT")
        with self.assertRaises(ValueError): self.run_remove()
        self.assertIsNotNone(self.app.Tree.FindNode(r"\Data\Streams\PRODUCT"))
    def test_wrong_type_prevents_removal(self):
        self.app.Tree.FindNode(r"\Data\Blocks\END").kind = "HEATX"
        with self.assertRaises(ValueError): self.run_remove()
    def test_changed_path_prevents_removal(self):
        self.request[0]["inlet"] = "FEED"
        with self.assertRaises(ValueError): self.run_remove()
    def test_wrong_count_prevents_removal(self):
        self.counts["blocks_before"] = 3
        with self.assertRaises(ValueError): self.run_remove()
    def test_duplicate_request_prevents_partial_mutation(self):
        self.request *= 2
        with self.assertRaises(ValueError): self.run_remove()
        self.assertIsNotNone(self.app.Tree.FindNode(r"\Data\Blocks\END"))
    def test_missing_guard_prevents_mutation(self):
        self.guard = [r"\Data\Blocks\MISSING\Input"]
        with self.assertRaises(ValueError): self.run_remove()
        self.assertIsNotNone(self.app.Tree.FindNode(r"\Data\Blocks\END"))
    def test_connected_energy_port_prevents_removal(self):
        self.app.Tree.FindNode(r"\Data\Blocks\END\Ports").add("HS(OUT)").add("Q")
        with self.assertRaises(ValueError): self.run_remove()
        self.assertIsNotNone(self.app.Tree.FindNode(r"\Data\Blocks\END"))
    def test_guarded_stream_reference_prevents_removal(self):
        self.app.Tree.FindNode(r"\Data\Blocks\UP\Input").add("TARGET_STREAM", "PRODUCT")
        with self.assertRaises(ValueError): self.run_remove()
        self.assertIsNotNone(self.app.Tree.FindNode(r"\Data\Streams\PRODUCT"))
    def test_hcurve_creates_analysis_cards(self):
        result = enable_hcurves(self.app, [{"block": "END", "kind": "heater_or_flash", "curve_id": "1", "points": 11}])
        self.assertEqual(len(result["writes"]), 4)
        self.assertEqual(self.app.Tree.FindNode(r"\Data\Blocks\END\Input\NPOINTS\1").Value, 11)
        self.assertEqual(self.app.Tree.FindNode(r"\Data\Blocks\END\Input\TOL").Value, 0.0001)
    def test_duplicate_curve_preflight(self):
        spec = {"block": "END", "kind": "heater_or_flash", "curve_id": "1", "points": 11}
        with self.assertRaises(ValueError): enable_hcurves(self.app, [spec, spec])
        self.assertEqual(list(self.app.Tree.FindNode(r"\Data\Blocks\END\Subobjects\Hcurves").Elements), [])
    def test_invalid_curve_point_count(self):
        with self.assertRaises(ValueError): enable_hcurves(self.app, [{"block": "END", "kind": "heater_or_flash", "curve_id": "1", "points": 1}])


if __name__ == "__main__": unittest.main()
