"""Real stdio transport checks using synthetic files, never native Aspen."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec('mcp'), 'optional MCP SDK absent')
class DynamicTransportTests(unittest.TestCase):
    def test_all_five_tools_over_real_stdio(self):
        import anyio
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async def exercise():
            with tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                payload = base / 'payload.txt'
                payload.write_bytes(b'synthetic')
                manifest = base / 'manifest.json'
                manifest.write_text(json.dumps({'files': [{'path': payload.name, 'size': 9,
                    'sha256': hashlib.sha256(b'synthetic').hexdigest()}]}), encoding='utf-8')
                grid = base / 'grid.csv'
                grid.write_text('time,value\n0,1\n1,2\n2,3\n', encoding='utf-8')
                history = base / 'history.txt'
                history.write_text('* WARNING synthetic unresolved condition\n', encoding='utf-8')
                settings = base / 'settings.json'
                external = base / 'external'
                (external / 'tools').mkdir(parents=True)
                (external / 'tools/expert_cli.py').write_text('raise RuntimeError("must never execute")', encoding='utf-8')
                settings.write_text(json.dumps({'paths': {'chemical-expert-cli': str(external)},
                    'interpreters': {'chemical-expert-cli': sys.executable}}), encoding='utf-8')
                params = StdioServerParameters(command=sys.executable,
                    args=['-B', '-X', 'utf8', str(ROOT / 'mcp_server.py')],
                    env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'})
                with anyio.fail_after(40):
                    async with stdio_client(params) as (read, write):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            inventory = await session.list_tools()
                            self.assertEqual({x.name for x in inventory.tools}, {'verify_package_manifest',
                                'check_csv_grid', 'inspect_history', 'list_external_tools', 'plan_external_invocation'})

                            async def call(name, args):
                                out = await session.call_tool(name, args)
                                self.assertFalse(out.isError)
                                obj = out.structuredContent or json.loads(next(x.text for x in out.content if x.type == 'text'))
                                self.assertFalse(obj['external_process_started'])
                                self.assertFalse(obj['strict_simulation_passed'])
                                return obj

                            self.assertTrue((await call('verify_package_manifest', {'root': tmp, 'manifest_path': str(manifest)}))['matches'])
                            payload.write_bytes(b'changed')
                            self.assertFalse((await call('verify_package_manifest', {'root': tmp, 'manifest_path': str(manifest)}))['matches'])
                            args = {'csv_path': str(grid), 'time_column': 'time', 'interval': 1,
                                    'start': 0, 'end': 2, 'time_abs_tolerance': 0, 'numeric_columns': ['value']}
                            self.assertTrue((await call('check_csv_grid', args))['matches'])
                            bad = await call('check_csv_grid', {**args, 'interval': -1})
                            self.assertEqual(bad['status'], 'invalid_or_unavailable')
                            for key in ['interval', 'start', 'end', 'time_abs_tolerance']:
                                for invalid in [True, '1']:
                                    rejected = await session.call_tool('check_csv_grid', {**args, key: invalid})
                                    if not rejected.isError:
                                        body = rejected.structuredContent or json.loads(next(x.text for x in rejected.content if x.type == 'text'))
                                        self.assertEqual(body['status'], 'invalid_or_unavailable')
                            overflow = await call('check_csv_grid', {**args, 'interval': 5e-324})
                            self.assertEqual(overflow['status'], 'invalid_or_unavailable')
                            hist = await call('inspect_history', {'history_path': str(history)})
                            self.assertFalse(hist['matches'])
                            self.assertTrue(hist['owner_identity_verified'])
                            self.assertEqual((await call('inspect_history', {'history_path': str(base / 'missing.txt')}))['status'], 'invalid_or_unavailable')
                            listed = await call('list_external_tools', {'settings_path': str(settings)})
                            self.assertEqual(len(listed['tools']), 5)
                            self.assertEqual((await call('list_external_tools', {'settings_path': str(base / 'missing.json')}))['status'], 'invalid_or_unavailable')
                            planned = await call('plan_external_invocation', {'tool_id': 'chemical-expert-cli', 'settings_path': str(settings)})
                            self.assertFalse(planned['execution_performed'])
                            self.assertEqual((await call('plan_external_invocation', {'tool_id': 'unknown'}))['status'], 'invalid_or_unavailable')
        anyio.run(exercise)


if __name__ == '__main__':
    unittest.main()
