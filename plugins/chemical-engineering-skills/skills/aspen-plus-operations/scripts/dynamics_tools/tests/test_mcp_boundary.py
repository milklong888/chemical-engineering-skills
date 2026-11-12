"""Optional real SDK argument validation in process; no stdio/COM/native run."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@unittest.skipUnless(importlib.util.find_spec('mcp'), 'Optional MCP SDK not installed')
class MCPNumericBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from dynamics_tools.mcp_server import create_server
        self.server = create_server()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.csv = Path(self.temp.name) / 'synthetic.csv'
        self.csv.write_text('t,x\n0,1\n1,2\n2,3\n', encoding='utf-8')
        self.arguments = dict(csv_path=str(self.csv), time_column='t', interval=1,
                              start=0, end=2, time_abs_tolerance=0, numeric_columns=['x'])

    async def test_integer_and_float_json_numbers_remain_valid(self):
        for numeric_type in (int, float):
            args = dict(self.arguments)
            for key in ('interval', 'start', 'end', 'time_abs_tolerance'):
                args[key] = numeric_type(args[key])
            result = await self.server.call_tool('check_csv_grid', args)
            # SDK structured tools return (content blocks, structured result).
            structured = result[1] if isinstance(result, tuple) else json.loads(result[0].text)
            self.assertEqual(structured['status'], 'ok')
            self.assertTrue(structured['matches'])
            self.assertFalse(structured['strict_simulation_passed'])

    async def test_all_four_numeric_arguments_reject_coercion(self):
        from mcp.server.fastmcp.exceptions import ToolError
        for key in ('interval', 'start', 'end', 'time_abs_tolerance'):
            for invalid in (True, False, '1', '0', {}, [], None):
                with self.subTest(argument=key, invalid=invalid):
                    args = dict(self.arguments); args[key] = invalid
                    with self.assertRaises(ToolError):
                        await self.server.call_tool('check_csv_grid', args)


if __name__ == '__main__':
    unittest.main()
