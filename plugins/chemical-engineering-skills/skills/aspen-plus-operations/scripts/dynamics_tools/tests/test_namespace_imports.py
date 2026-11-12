"""Relocation regression: unrelated top-level names cannot capture this package.

SPDX-License-Identifier: MIT
"""
import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class NamespaceImportTests(unittest.TestCase):
    def test_facade_and_server_resolve_siblings_under_namespace(self):
        unrelated = types.ModuleType("unrelated_placeholder")
        with patch.dict(sys.modules, {"toolpack": unrelated, "offline_facade": unrelated}):
            facade = importlib.import_module("dynamics_tools.offline_facade")
            server = importlib.import_module("dynamics_tools.mcp_server")
            importlib.reload(facade)
            importlib.reload(server)
            self.assertEqual(facade.toolpack.__name__, "dynamics_tools.toolpack")
            self.assertIs(server.TOOLS, facade.TOOLS)
            self.assertEqual(len(server.TOOLS), 5)
            self.assertTrue(all(fn.__module__ == "dynamics_tools.offline_facade"
                                for fn in server.TOOLS))


if __name__ == "__main__":
    unittest.main()
