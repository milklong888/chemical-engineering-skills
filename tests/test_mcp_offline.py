#!/usr/bin/env python3
"""Offline installer unit tests and optional real SDK/stdio checks, never Aspen.

Integration confines the Python client and server with socket/DNS audit guards
and COM creation blockers. It is not an operating-system firewall or a claim
that arbitrary hostile native extensions are sandboxed.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOLKIT = ROOT / 'vendor' / 'aspen-mcp-toolkit'
spec = importlib.util.spec_from_file_location('offline_mcp_installer', ROOT / 'tools' / 'install_offline_runtime.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class OfflineInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='synthetic-mcp-lock-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.wheelhouse = self.directory / 'wheels'
        self.wheelhouse.mkdir()
        self.lockfile = self.directory / 'lock.json'
        self.lock = {'schema': 'aspen-mcp-offline-runtime-v1',
                     'target': {'implementation': 'CPython', 'python_major_minor': '3.14',
                                'platform': 'win_amd64', 'bits': 64}, 'wheel_count': 4, 'wheels': []}
        # Clearly synthetic byte fixtures: only preflight validation is exercised.
        for name in ('fastmcp', 'fastmcp-slim', 'mcp', 'pywin32'):
            filename = name.replace('-', '_') + '-1.0-py3-none-any.whl'
            path = self.wheelhouse / filename
            path.write_bytes(b'synthetic-preflight-not-an-installable-wheel')
            self.lock['wheels'].append({'name': name, 'version': '1.0', 'filename': filename,
                                        'bytes': path.stat().st_size, 'sha256': installer.sha256(path)})
        self.save()

    def save(self):
        self.lockfile.write_text(json.dumps(self.lock), encoding='utf-8')

    def check(self):
        return installer.validate_lock(self.lockfile, self.wheelhouse)

    def test_synthetic_preflight_accepts_consistent_inventory(self):
        lock, requirements = self.check()
        self.assertEqual(lock['wheel_count'], 4)
        self.assertEqual(requirements.count('--hash=sha256:'), 4)

    def test_missing_wheel_is_not_downloaded(self):
        (self.wheelhouse / self.lock['wheels'][0]['filename']).unlink()
        with self.assertRaises(installer.OfflineInstallError): self.check()

    def test_changed_wheel_is_rejected(self):
        path = self.wheelhouse / self.lock['wheels'][0]['filename']
        path.write_bytes(b'X' * path.stat().st_size)
        with self.assertRaises(installer.OfflineInstallError): self.check()

    def test_unlisted_wheel_is_rejected(self):
        (self.wheelhouse / 'unexpected.whl').write_bytes(b'synthetic')
        with self.assertRaises(installer.OfflineInstallError): self.check()

    def test_path_escape_is_rejected(self):
        self.lock['wheels'][0]['filename'] = '../outside.whl'
        self.save()
        with self.assertRaises(installer.OfflineInstallError): self.check()

    def test_requirement_injection_is_rejected(self):
        self.lock['wheels'][0]['version'] = '1.0\nhttps://invalid.example/item.whl'
        self.save()
        with self.assertRaises(installer.OfflineInstallError): self.check()

    def test_normalized_duplicate_is_rejected(self):
        self.lock['wheels'][0]['name'] = 'fastmcp_slim'
        self.save()
        with self.assertRaises(installer.OfflineInstallError): self.check()

    def test_existing_target_is_not_reused(self):
        target = self.directory / 'existing'
        target.mkdir()
        with self.assertRaises(installer.OfflineInstallError):
            installer.validate_new_target(target, self.wheelhouse, self.lockfile)

    def test_existing_target_stops_before_any_interpreter_or_install(self):
        target = self.directory / 'existing-target'; target.mkdir()
        with mock.patch.object(installer, 'inspect_python', side_effect=AssertionError('must not launch')):
            with self.assertRaises(installer.OfflineInstallError):
                installer.install(python=Path(sys.executable), target=target,
                                  wheelhouse=self.wheelhouse, lock_path=self.lockfile)

    def test_wrong_python_or_platform_is_rejected(self):
        good = {'implementation': 'CPython', 'version': '3.14.3', 'bits': 64, 'platform': 'win-amd64'}
        installer.validate_python_info(good)
        for key, value in [('version', '3.12.14'), ('bits', 32), ('platform', 'linux-x86_64')]:
            bad = dict(good); bad[key] = value
            with self.assertRaises(installer.OfflineInstallError): installer.validate_python_info(bad)

    def extension(self, name='numpy'):
        directory = self.directory / 'extension'; directory.mkdir()
        wheel = directory / (name.replace('-', '_') + '-1.0-py3-none-any.whl')
        wheel.write_bytes(b'synthetic-extension-preflight')
        extension = {'schema': 'aspen-mcp-offline-extension-v1', 'target': self.lock['target'],
                     'base_lock_sha256': installer.sha256(self.lockfile), 'wheel_count': 1,
                     'wheels': [{'name': name, 'version': '1.0', 'filename': wheel.name,
                                 'bytes': wheel.stat().st_size, 'sha256': installer.sha256(wheel)}]}
        path = self.directory / 'extension.json'
        path.write_text(json.dumps(extension), encoding='utf-8')
        return path, directory

    def test_extension_preserves_base_identity(self):
        before = installer.sha256(self.lockfile)
        path, directory = self.extension()
        extra, requirements = installer.validate_extension(self.lockfile, self.lock, path, directory)
        self.assertEqual(extra['base_lock_sha256'], before)
        self.assertIn('numpy==1.0', requirements)
        self.assertEqual(installer.sha256(self.lockfile), before)

    def test_extension_wrong_base_hash_is_rejected(self):
        path, directory = self.extension()
        self.lock['note'] = 'changed synthetic baseline'; self.save()
        with self.assertRaises(installer.OfflineInstallError):
            installer.validate_extension(self.lockfile, self.lock, path, directory)

    def test_extension_cannot_override_mcp(self):
        path, directory = self.extension('mcp')
        with self.assertRaises(installer.OfflineInstallError):
            installer.validate_extension(self.lockfile, self.lock, path, directory)


GUARD_SOURCE = r'''"""Process-local test guard; blocks Python sockets and COM creation."""
import json
import os
import sys
import time
import socket
from pathlib import Path

_directory = Path(os.environ['MCP_OFFLINE_GUARD_DIR'])
_forbidden_roots = [os.path.normcase(os.path.abspath(value)) for value in
                    json.loads(os.environ.get('MCP_OFFLINE_FORBIDDEN_ROOTS', '[]'))]
_control = False
GUARD_ACTIVE = False

def _record(kind, detail=''):
    row = {'pid': os.getpid(), 'time': time.time(), 'kind': kind,
           'negative_control': _control, 'detail': str(detail)[:160]}
    path = _directory / ('guard-' + str(os.getpid()) + '.jsonl')
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(row, ensure_ascii=True) + '\n')

def _audit(event, args):
    if event in {'open', 'os.listdir', 'os.scandir'} and args:
        value = args[0]
        if isinstance(value, (str, bytes, os.PathLike)):
            path = os.path.normcase(os.path.abspath(os.fsdecode(value)))
            if any(path == root or path.startswith(root + os.sep) for root in _forbidden_roots):
                _record('original_source_read_blocked', event + ':' + path)
                raise PermissionError('Isolated installed test forbids original workspace or user configuration reads')
    # Windows asyncio uses the standard-library socketpair fallback as its
    # self-wakeup IPC. Permit only that exact function's own loopback listener,
    # not general localhost networking. All external sockets/DNS stay blocked.
    if event in {'socket.connect', 'socket.bind'}:
        frame = sys._getframe(1)
        trusted = getattr(socket, '_fallback_socketpair', None)
        if trusted is not None and frame.f_code is trusted.__code__:
            address = args[1]
            listener = frame.f_locals.get('lsock')
            if isinstance(address, tuple) and address[0] in {'127.0.0.1', '::1'}:
                if event == 'socket.bind' and args[0] is listener and address[1] == 0:
                    _record('local_socketpair_ipc_allowed', event)
                    return
                if event == 'socket.connect' and listener is not None:
                    if address[:2] == listener.getsockname()[:2] and args[0] is frame.f_locals.get('csock'):
                        _record('local_socketpair_ipc_allowed', event)
                        return
    if event in {'socket.connect', 'socket.bind', 'socket.getaddrinfo', 'socket.gethostbyname',
                 'socket.gethostbyaddr', 'socket.getnameinfo', 'socket.sendto'}:
        _record('network_blocked', event)
        raise PermissionError('Offline test forbids network or DNS: ' + event)

sys.addaudithook(_audit)

def _blocked_com(*args, **kwargs):
    _record('com_blocked', 'COM creation/attachment forbidden')
    raise PermissionError('Offline protocol test cannot create or attach COM objects')

import pythoncom
import win32com.client
import win32com.client.gencache
for module, names in [
    (pythoncom, ('CoCreateInstance', 'CoCreateInstanceEx', 'GetActiveObject', 'Connect', 'CoGetObject')),
    (win32com.client, ('Dispatch', 'DispatchEx', 'GetActiveObject', 'GetObject')),
    (win32com.client.gencache, ('EnsureDispatch',)),
]:
    for name in names:
        if hasattr(module, name): setattr(module, name, _blocked_com)

GUARD_ACTIVE = True
_record('guard_ready')

if os.environ.get('MCP_OFFLINE_DEBUG_STACKS') == '1':
    import faulthandler
    _stack_stream = (_directory / ('stack-' + str(os.getpid()) + '.txt')).open('w', encoding='utf-8')
    faulthandler.dump_traceback_later(15, repeat=True, file=_stack_stream)

def negative_controls():
    global _control
    import socket
    _control = True
    try:
        try:
            with socket.socket() as s: s.connect(('198.51.100.1', 9))
        except PermissionError: pass
        else: raise AssertionError('Network guard did not reject control')
        try: win32com.client.Dispatch('Apwn.Document')
        except PermissionError: pass
        else: raise AssertionError('COM guard did not reject control')
        for root in _forbidden_roots:
            try: open(os.path.join(root, '_synthetic_guard_control_not_a_real_user_file'), 'rb')
            except PermissionError: pass
            else: raise AssertionError('Original-source read guard did not reject control')
    finally:
        _control = False
'''

CLIENT_SOURCE = r'''import asyncio
from datetime import timedelta
import json
import os
from pathlib import Path
import sys
import sitecustomize

assert sitecustomize.GUARD_ACTIVE, 'Required process guard missing'
sitecustomize.negative_controls()

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    output = Path(sys.argv[1]); toolkit = Path(sys.argv[2])
    source = json.loads((toolkit / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    expected = sorted(source['tool_names'])
    numpy_result = None
    if os.environ.get('MCP_TEST_NUMPY') == '1':
        import numpy as np
        value = int(np.dot(np.array([1, 2]), np.array([3, 4])))
        assert value == 11
        numpy_result = {'version': np.__version__, 'integer_dot_product': value,
                        'scope': 'installed numeric runtime smoke test, not RAG or process validation'}
    # Guard is verified before executing the unchanged upstream entry point.
    bootstrap = "import sitecustomize; assert sitecustomize.GUARD_ACTIVE; import runpy,sys; runpy.run_path(sys.argv[1], run_name='__main__')"
    params = StdioServerParameters(command=sys.executable, args=['-B', '-c', bootstrap, str(toolkit / 'run_offline_mcp.py')],
                                   env=dict(os.environ), cwd=str(output))
    with (output / 'server.stderr.txt').open('w', encoding='utf-8') as errors:
        async with stdio_client(params, errlog=errors) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=25)) as session:
                initialized = await session.initialize()
                listed = await session.list_tools()
                actual = sorted(tool.name for tool in listed.tools)
                if len(actual) != 70 or actual != expected:
                    raise AssertionError('Tool list differs from frozen source')
                # Verified source body calls only search_failures on local text.
                # Its upstream docstring is broader than the implementation.
                knowledge = await session.call_tool('search_convergence_knowledge', {'keywords': ['Wegstein']})
                if knowledge.isError or not knowledge.content:
                    raise AssertionError('Local knowledge tool failed')
                result = {'schema': 'mcp-offline-protocol-result-v1', 'status': 'passed',
                          'client_pid': os.getpid(), 'initialize': initialized.model_dump(mode='json'),
                          'tool_count': len(actual), 'tools': [tool.model_dump(mode='json') for tool in listed.tools],
                          'knowledge_call': knowledge.model_dump(mode='json'),
                          'numpy_smoke': numpy_result,
                          'aspen_tools_called': [], 'simulation_clean': False,
                          'validation_scope': 'real SDK stdio protocol plus local knowledge text only'}
                (output / 'protocol_result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

asyncio.run(asyncio.wait_for(main(), timeout=35))
'''


EXPERT_CLIENT_SOURCE = r'''import asyncio
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import sitecustomize

assert sitecustomize.GUARD_ACTIVE
sitecustomize.negative_controls()
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

def payload(result):
    if result.isError: raise AssertionError('MCP tool returned isError')
    structured = result.structuredContent
    if isinstance(structured, dict): return structured
    for content in result.content:
        if getattr(content, 'type', '') == 'text':
            try: return json.loads(content.text)
            except ValueError: pass
    raise AssertionError('Tool response has no structured JSON')

def objects(value, path=''):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items(): yield from objects(child, path + '/' + key)
    elif isinstance(value, list):
        for index, child in enumerate(value): yield from objects(child, path + '/' + str(index))

async def main():
    output, repository = Path(sys.argv[1]), Path(sys.argv[2])
    expected = sorted(['knowledge_search', 'equipment_calculate', 'pressure_calculate',
                       'process_feedback', 'process_replay_audit', 'equipment_batch', 'product_describe', 'design_stage_check', 'aspen_solve_route'])
    bootstrap = r"""
import sitecustomize,runpy,sys,subprocess
from pathlib import Path
assert sitecustomize.GUARD_ACTIVE
sitecustomize.negative_controls()
target=Path(sys.argv[1]);root=target.parent.parent
sys.path.insert(0,str(root));sys.path.insert(0,str(target.parent))
import tools.equipment_gateway as gateway
guard_file=str(Path(sitecustomize.__file__).resolve())
child="import importlib.util,runpy,sys; from pathlib import Path; spec=importlib.util.spec_from_file_location('explicit_mcp_child_guard',sys.argv[1]); guard=importlib.util.module_from_spec(spec); spec.loader.exec_module(guard); assert guard.GUARD_ACTIVE; guard.negative_controls(); target=sys.argv[2]; sys.argv=[target,*sys.argv[3:]]; sys.path.insert(0,str(Path(target).parent)); runpy.run_path(target,run_name='__main__')"
original_command=gateway._command
def command(environment):
    argv=original_command(environment)
    assert Path(argv[-2]).resolve()==gateway.AGENT.resolve()
    return argv[:-2]+['-c',child,guard_file,str(gateway.AGENT),'--session-jsonl']
gateway._command=command
original_run=subprocess.run
def run(argv,*args,**kwargs):
    if isinstance(argv,list) and '-c' not in argv:
        for index,value in enumerate(argv):
            if str(value)==str(root/'knowledge/scripts/query_knowledge.py'):
                assert kwargs.get('stdin')==subprocess.DEVNULL
                argv=argv[:index]+['-c',child,guard_file,str(value),*argv[index+1:]]
                break
    return original_run(argv,*args,**kwargs)
subprocess.run=run
sys.argv=[str(target)];runpy.run_path(str(target),run_name='__main__')
"""
    params = StdioServerParameters(command=sys.executable,
        args=['-B', '-c', bootstrap, str(repository / 'tools/expert_mcp.py')],
        env=dict(os.environ), cwd=str(output))
    with (output / 'server.stderr.txt').open('w', encoding='utf-8') as errors:
        async with stdio_client(params, errlog=errors) as (reader, writer):
            async with ClientSession(reader, writer, read_timeout_seconds=timedelta(seconds=75)) as session:
                initialized = await session.initialize()
                listed = await session.list_tools()
                if sorted(t.name for t in listed.tools) != expected:
                    raise AssertionError('Expert tool list mismatch')
                (output / 'initialize_and_tools.json').write_text(json.dumps({
                    'initialize': initialized.model_dump(mode='json'),
                    'tool_count': len(listed.tools), 'tools': [t.model_dump(mode='json') for t in listed.tools]},
                    ensure_ascii=False, indent=2), encoding='utf-8')
                timings = []
                async def measured_call(name, arguments):
                    started = time.monotonic()
                    entry = {'tool': name, 'single_request_budget_s': 75}
                    try:
                        response = await session.call_tool(name, arguments)
                        entry['status'] = 'returned_tool_error' if response.isError else 'returned'
                        snapshot = output / ('transaction_' + str(len(timings) + 1) + '_' + name + '.json')
                        snapshot.write_text(json.dumps(response.model_dump(mode='json'), ensure_ascii=False, indent=2), encoding='utf-8')
                        return response
                    except BaseException as exc:
                        entry['status'] = 'raised'
                        entry['error_type'] = type(exc).__name__
                        raise
                    finally:
                        entry['elapsed_s'] = time.monotonic() - started
                        timings.append(entry)
                        (output / 'tool_call_timings.json').write_text(json.dumps({
                            'single_request_budget_s': 75, 'complete_session_budget_s': 120,
                            'outer_process_budget_including_teardown_s': 135,
                            'calls': timings}, ensure_ascii=False, indent=2), encoding='utf-8')
                pressure_request = {'method': 'series_pressure', 'inputs': {
                    'inlet_pressure_pa': 500000, 'losses_pa': [20000, 30000]}}
                pressure_raw = await measured_call('pressure_calculate', pressure_request)
                (output / 'pressure.raw.json').write_text(json.dumps(pressure_raw.model_dump(mode='json'), ensure_ascii=False, indent=2), encoding='utf-8')
                pressure = payload(pressure_raw)
                if pressure.get('outlet_pressure_pa') != 450000 or pressure.get('total_loss_pa') != 50000:
                    raise AssertionError('Same-input arithmetic pressure oracle failed')
                request = {'schema': 'equipment-design-agent-request-v1',
                    'request_id': 'SYNTHETIC-EXPERT-MCP-AREA', 'operation': 'manual_match',
                    'payload': {'selection_id': 'family:family_fixed_tubesheet_exchanger',
                        'values': {'equipment_tag': 'SYNTHETIC-EXPERT-E1',
                            'heat_duty_kw': 1000, 'overall_u_w_m2k': 500,
                            'lmtd_k': 40, 'lmtd_correction_factor': 1}}}
                equipment_raw = await measured_call('equipment_calculate', {'request': request})
                (output / 'equipment.raw.json').write_text(json.dumps(equipment_raw.model_dump(mode='json'), ensure_ascii=False, indent=2), encoding='utf-8')
                equipment = payload(equipment_raw)
                if equipment.get('backend_exit_code') != 0:
                    raise AssertionError('Original equipment backend failed: ' + json.dumps(equipment)[:1500])
                expected_area = 1000 * 1000 / (500 * 40 * 1)
                areas, traces = [], []
                for path, item in objects(equipment):
                    derived = item.get('derived_parameters')
                    if isinstance(derived, dict) and 'heat_transfer_area_m2' in derived:
                        areas.append({'path': path + '/derived_parameters/heat_transfer_area_m2',
                                      'value': derived['heat_transfer_area_m2']})
                    trace = item.get('formula_trace')
                    if isinstance(trace, dict) and trace.get('calculation_trace_sha256'):
                        traces.append(path + '/formula_trace')
                if not areas or not traces or any(row['value'] != expected_area for row in areas):
                    raise AssertionError('Area result/trace fails Q/(U*LMTD*F) oracle')
                knowledge_raw = standards_raw = feedback_raw = replay_raw = None
                if os.environ.get('MCP_TEST_KNOWLEDGE') == '1':
                    knowledge_raw = await measured_call('knowledge_search', {
                        'query': '预热 压缩', 'corpus': 'chemical_principles', 'limit': 3, 'vector': True})
                    knowledge = payload(knowledge_raw)
                    response = knowledge.get('knowledge') or {}
                    hits = response.get('results') or []
                    if not hits or hits[0].get('node_id') != 'L3-05':
                        raise AssertionError('Vector macro retrieval did not return the registered L3-05 card')
                    if response.get('current_project_authority') is not False or response.get('project_value_transfer_allowed') is not False:
                        raise AssertionError('Knowledge lookup lost its project-evidence boundary')
                    standards_raw = await measured_call('knowledge_search', {
                        'query': 'GB/T 17395', 'corpus': 'equipment_standards', 'limit': 2,
                        'package_ids': ['design_standards']})
                    standards = payload(standards_raw)
                    if standards.get('requested_equipment_packages') != ['design_standards']:
                        raise AssertionError('Standards request did not bind the actual registered package')
                    database_result = standards.get('equipment') or {}
                    standard_hits = (database_result.get('response') or {}).get('result', {}).get('hits', [])
                    if database_result.get('backend_exit_code') != 0 or len(standard_hits) != 2:
                        raise AssertionError('Registered design standards database did not return two actual records')
                    if any('gbt17395' not in row.get('source_path', '').lower()
                           or row.get('numeric_reuse_allowed') is not False
                           or len(row.get('parent_database_sha256', '')) != 64 for row in standard_hits):
                        raise AssertionError('Database hit provenance or numeric reuse boundary lost')

                    def evidence_file(name, content):
                        path = output / name
                        data = (json.dumps(content, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
                        with path.open('xb') as handle: handle.write(data)
                        return {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest().upper()}
                    source_export = evidence_file('synthetic_feedback_export.json', {
                        'schema': 'equipment-process-canonical-export-v1',
                        'case_id': 'SYNTHETIC-EXPERT-PROTOCOL', 'run_id': 'SYNTHETIC-RUN-CURRENT',
                        'synthetic': True, 'not_an_aspen_export': True,
                        'equipment': {'SYNTHETIC-EXPERT-E1': {
                            'family_id': 'family_fixed_tubesheet_exchanger',
                            'values': {key: value for key, value in request['payload']['values'].items()
                                       if key != 'equipment_tag'},
                            'units': {'heat_duty_kw': 'kW', 'overall_u_w_m2k': 'W/m2/K',
                                      'lmtd_k': 'K', 'lmtd_correction_factor': '1'}}}})
                    authority = evidence_file('synthetic_feedback_authority.json', {
                        'schema': 'equipment-process-authority-v1',
                        'case_id': 'SYNTHETIC-EXPERT-PROTOCOL', 'run_id': 'SYNTHETIC-RUN-CURRENT',
                        'synthetic': True, 'not_user_authorization': True,
                        'required_method': 'Synthetic deterministic area screening with explicit missing rating evidence',
                        'acceptance_criteria': ['Do not claim engineering acceptance without required domain evidence']})
                    context = {'case_id': 'SYNTHETIC-EXPERT-PROTOCOL', 'run_id': 'SYNTHETIC-RUN-CURRENT',
                               'source_export': source_export,
                               'authority': authority, 'constraint_evidence': {}}
                    feedback_raw = await measured_call('process_feedback', {
                        'payload': {'selector_request': request, 'context': context}, 'evidence_root': str(output)})
                    feedback = payload(feedback_raw)
                    plan = feedback.get('plan') or {}
                    if feedback.get('backend_exit_code') != 0 or not plan.get('equipment'):
                        raise AssertionError('Feedback did not preserve the actual equipment calculation')
                    if plan.get('engineering_accepted') is not False or plan.get('flowsheet_modified') is not False:
                        raise AssertionError('Missing domain evidence was treated as engineering acceptance or mutation')
                    if any(row.get('revision') is not None for row in plan['equipment']):
                        raise AssertionError('No applicable capacity evidence was provided; automatic revision is not justified')
                    if any(row.get('binding_gaps') != [] for row in plan['equipment']):
                        raise AssertionError('Same-case synthetic values and units did not bind to the actual selector inputs')
                    candidate = evidence_file('synthetic_replay_candidate.json', {
                        'synthetic': True, 'not_an_aspen_model': True})
                    replay_raw = await measured_call('process_replay_audit', {
                        'payload': {'plan': plan, 'replay': {'case_id': context['case_id'],
                            'run_id': context['run_id'],
                            'plan_sha256': plan['plan_sha256'], 'candidate': candidate,
                            'source_export': source_export, 'gates': {}}}, 'evidence_root': str(output)})
                    replay = payload(replay_raw)
                    if replay.get('engineering_accepted') is not False or replay.get('evidence_chain_complete') is not False:
                        raise AssertionError('Empty replay gates were treated as completed evidence')
                    if {row['gate'] for row in replay.get('failed_gates', [])} != set(plan['required_replay_gates']):
                        raise AssertionError('Missing replay requirements were not fully enumerated')
                    for name, raw in [('knowledge', knowledge_raw), ('standards', standards_raw),
                                      ('feedback', feedback_raw), ('replay', replay_raw)]:
                        (output / (name + '.raw.json')).write_text(json.dumps(raw.model_dump(mode='json'), ensure_ascii=False, indent=2), encoding='utf-8')
                result = {'schema': 'expert-offline-protocol-result-v1', 'status': 'passed',
                    'synthetic_inputs': True, 'initialize': initialized.model_dump(mode='json'),
                    'tool_count': len(listed.tools), 'tools': [t.model_dump(mode='json') for t in listed.tools],
                    'tool_call_timings': timings, 'single_request_budget_s': 75,
                    'complete_session_budget_s': 120, 'outer_process_budget_s': 135,
                    'pressure_request': pressure_request, 'pressure_result': pressure,
                    'pressure_oracle': '500000-20000-30000 = 450000 Pa absolute',
                    'equipment_request': request, 'equipment_result': equipment,
                    'equipment_oracle': {'equation': '1000 kW * 1000 /(500 W/m2/K * 40 K * 1)',
                                          'area_m2': expected_area, 'observed': areas, 'trace_paths': traces},
                    'knowledge_result': knowledge_raw.model_dump(mode='json') if knowledge_raw else None,
                    'knowledge_validation': 'requested' if knowledge_raw else 'not_requested_waiting_source_ready',
                    'standards_database_result': standards_raw.model_dump(mode='json') if standards_raw else None,
                    'feedback_result': feedback_raw.model_dump(mode='json') if feedback_raw else None,
                    'replay_result': replay_raw.model_dump(mode='json') if replay_raw else None,
                    'aspen_tools_called': [], 'simulation_clean': False,
                    'validation_scope': 'real MCP protocol and original deterministic synthetic calculations, not equipment/model release'}
                (output / 'protocol_result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

asyncio.run(asyncio.wait_for(main(), timeout=120))
'''


def aspen_processes() -> list[dict]:
    command = ("$p=@(Get-Process | Where-Object { $_.ProcessName -match "
               "'(?i)(aspen|apmain|apwn|bjac)' } | Select-Object Id,ProcessName,"
               "@{Name='StartTimeUtc';Expression={$_.StartTime.ToUniversalTime().ToString('o')}});"
               "ConvertTo-Json -InputObject $p -Compress")
    result = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', command],
                            capture_output=True, text=True, timeout=20, check=True)
    return json.loads(result.stdout or '[]')


def verify_source(toolkit: Path) -> dict:
    lock = json.loads((toolkit / 'offline-runtime.lock.json').read_text(encoding='utf-8'))
    if installer.sha256(toolkit / 'SOURCE_MANIFEST.json') != lock['source_manifest_sha256']:
        raise ValueError('Source manifest differs from frozen runtime lock')
    source = json.loads((toolkit / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    for row in source['files']:
        path = toolkit / row['path']
        if not path.is_file() or installer.sha256(path) != row['sha256']:
            raise ValueError('Source hash mismatch: ' + row['path'])
    return source


def live_owned_pids(pids: set[int]) -> list[int]:
    if not pids:
        return []
    values = ','.join(str(int(pid)) for pid in sorted(pids))
    command = (f'$p=@(Get-Process -Id {values} -ErrorAction SilentlyContinue | '
               'Select-Object -ExpandProperty Id); ConvertTo-Json -InputObject $p -Compress')
    result = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', command],
                            capture_output=True, text=True, timeout=20, check=True)
    return json.loads(result.stdout or '[]')


def integration(runtime: Path, toolkit: Path, output: Path, *, server_mode: str = 'aspen',
                knowledge_ready: bool = False) -> dict:
    runtime, toolkit, output = runtime.resolve(), toolkit.resolve(), output.resolve()
    if output.exists(): raise ValueError('Integration output must not exist')
    python = runtime / 'Scripts' / 'python.exe'
    installer.inspect_python(python)
    source = verify_source(toolkit)
    receipt = json.loads((runtime / 'offline-install-receipt.json').read_text(encoding='utf-8'))
    if receipt.get('status') != 'installed_offline': raise ValueError('Fresh offline install receipt required')
    if receipt.get('lock_sha256') != installer.sha256(toolkit / 'offline-runtime.lock.json'):
        raise ValueError('Runtime receipt belongs to another vendor lock')
    if installer.sha256(runtime / 'offline-runtime.lock.json') != receipt['lock_sha256']:
        raise ValueError('Installed runtime lock differs from receipt')
    before = aspen_processes()
    # This always-on vendor service is not a document/solver instance. Keep its
    # identity in both snapshots; never stop it or consider it owned by the test.
    background_service = 'AspenTech.HybridModel.Desktop.Service'
    active = [row for row in before if row['ProcessName'] != background_service]
    if active: raise ValueError('Aspen document/solver process exists; do not overlap protocol test')
    output.mkdir(parents=True, exist_ok=False)
    guard_dir = output / 'guard'; guard_dir.mkdir()
    (guard_dir / 'sitecustomize.py').write_text(GUARD_SOURCE, encoding='utf-8')
    client = output / 'protocol_client.py'
    client.write_text(EXPERT_CLIENT_SOURCE if server_mode == 'expert' else CLIENT_SOURCE, encoding='utf-8')
    expert_files = ['tools/expert_mcp.py', 'tools/expert_cli.py', 'backends/process/pressure.py',
                    'backends/process/feedback.py', 'backends/equipment/app/equipment_design_agent.py']
    if knowledge_ready:
        expert_files.extend(['knowledge/scripts/query_knowledge.py', 'knowledge/scripts/vector_adapter.py',
                             'knowledge/manifest.json', 'workspace/scripts/vectorize_workspace_knowledge.py',
                             'backends/process/selector_analysis.py'])
    expert_hashes = {p: installer.sha256(ROOT / p) for p in expert_files} if server_mode == 'expert' else {}
    env = installer.safe_environment()
    env.update({'PYTHONPATH': os.pathsep.join([str(guard_dir), str(toolkit / 'src')]),
                'MCP_OFFLINE_GUARD_DIR': str(output),
                'FASTMCP_ENV_FILE': str(output / 'intentionally-absent.env')})
    if any(row.get('extension_id') == 'workspace-retrieval-numpy' for row in receipt.get('extensions', [])):
        env['MCP_TEST_NUMPY'] = '1'
    if knowledge_ready: env['MCP_TEST_KNOWLEDGE'] = '1'
    if os.environ.get('MCP_OFFLINE_DEBUG_STACKS') == '1':
        env['MCP_OFFLINE_DEBUG_STACKS'] = '1'
    if os.environ.get('MCP_OFFLINE_FORBIDDEN_ROOTS'):
        env['MCP_OFFLINE_FORBIDDEN_ROOTS'] = os.environ['MCP_OFFLINE_FORBIDDEN_ROOTS']
    command = [str(python), '-B', str(client), str(output), str(ROOT if server_mode == 'expert' else toolkit)]
    timed_out = False
    with (output / 'client.stdout.txt').open('w', encoding='utf-8') as stdout, \
         (output / 'client.stderr.txt').open('w', encoding='utf-8') as stderr:
        proc = subprocess.Popen(command, cwd=output, env=env, stdout=stdout, stderr=stderr,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            returncode = proc.wait(timeout=135 if server_mode == 'expert' else 45)
        except subprocess.TimeoutExpired:
            timed_out = True
            # Exact owned subprocess tree only; no named-process or Aspen cleanup.
            subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                           capture_output=True, timeout=15, check=False)
            returncode = proc.wait(timeout=15)
    after = aspen_processes()
    verify_source(toolkit)
    expert_sources_unchanged = all(installer.sha256(ROOT / p) == value for p, value in expert_hashes.items())
    events = [json.loads(line) for path in output.glob('guard-*.jsonl')
              for line in path.read_text(encoding='utf-8').splitlines() if line]
    ready = {row['pid'] for row in events if row['kind'] == 'guard_ready'}
    remaining_owned = live_owned_pids(ready)
    controls = {row['kind'] for row in events if row.get('negative_control')}
    unexpected = [row for row in events if row['kind'].endswith('_blocked') and not row.get('negative_control')]
    resultpath = output / 'protocol_result.json'
    protocol = json.loads(resultpath.read_text(encoding='utf-8')) if resultpath.exists() else {}
    process_snapshot_unchanged = sorted(before, key=lambda p: p['Id']) == sorted(after, key=lambda p: p['Id'])
    # Expert: client + server + one resident equipment worker; knowledge-ready
    # adds one vector-query worker (standards use the resident equipment worker).
    # Every child loads the test guard explicitly even
    # though production correctly removes inherited PYTHONPATH.
    expected_process_count = (4 if knowledge_ready else 3) if server_mode == 'expert' else 2
    passed = (returncode == 0 and not timed_out and process_snapshot_unchanged and expert_sources_unchanged
              and not remaining_owned and len(ready) == expected_process_count
              and {'network_blocked', 'com_blocked'}.issubset(controls)
              and not unexpected and protocol.get('status') == 'passed')
    result = {'schema': 'mcp-offline-validation-v1', 'passed': passed, 'returncode': returncode,
              'server_mode': server_mode, 'expert_source_hashes': expert_hashes,
              'expert_sources_unchanged': expert_sources_unchanged,
              'timed_out': timed_out, 'guarded_processes': sorted(ready),
              'remaining_owned_processes': remaining_owned,
              'negative_controls': sorted(controls), 'unexpected_guard_events': unexpected,
              'forbidden_original_roots': json.loads(env.get('MCP_OFFLINE_FORBIDDEN_ROOTS', '[]')),
              'original_source_read_guard': 'Python open/listdir/scandir audit; not an OS sandbox for hostile native code',
              'aspen_processes_before': before, 'aspen_processes_after': after,
              'aspen_process_snapshot_unchanged': process_snapshot_unchanged,
              'network_policy': 'Python process socket/DNS block; only exact stdlib socketpair self-wakeup IPC allowed; no system firewall changed',
              'com_policy': 'COM creation and attachment entry points blocked in both Python processes',
              'tool_count': protocol.get('tool_count'), 'aspen_started': False,
              'simulation_clean': False, 'source_manifest_sha256': installer.sha256(toolkit / 'SOURCE_MANIFEST.json'),
              'runtime_lock_sha256': receipt['lock_sha256'],
              'test_runner_sha256': installer.sha256(Path(__file__)),
              'launcher_sha256': installer.sha256(toolkit / 'run_offline_mcp.py'),
              'guard_source_sha256': hashlib.sha256(GUARD_SOURCE.encode('utf-8')).hexdigest(),
              'installer_sha256': installer.sha256(ROOT / 'tools' / 'install_offline_runtime.py'),
              'runtime_extensions': receipt.get('extensions', []),
              'numpy_smoke': protocol.get('numpy_smoke'),
              'artifacts': {p.name: installer.sha256(p) for p in output.iterdir() if p.is_file()}}
    (output / 'validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--integration', action='store_true')
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--toolkit', type=Path, default=TOOLKIT)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--server-mode', choices=['aspen', 'expert'], default='aspen')
    parser.add_argument('--knowledge-ready', action='store_true')
    args, rest = parser.parse_known_args()
    if not args.integration:
        program = unittest.main(argv=[sys.argv[0], *rest], exit=False)
        return 0 if program.result.wasSuccessful() else 1
    if args.runtime is None or args.output is None:
        parser.error('--integration requires --runtime and --output')
    result = integration(args.runtime, args.toolkit, args.output,
                         server_mode=args.server_mode, knowledge_ready=args.knowledge_ready)
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
