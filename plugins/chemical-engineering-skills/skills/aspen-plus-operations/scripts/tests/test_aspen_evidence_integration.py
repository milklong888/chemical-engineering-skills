"""Fake-session tests of the actual clean-audit main wiring. No Aspen/COM."""
from __future__ import annotations
import contextlib
import io
import json
import os
import shutil
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import aspen_clean_delivery_audit as audit

NATIVE_ZERO = (' *** Summary of Simulation Errors ***\n Physical\n Property System Simulation\n'
               'Terminal Errors 0 0 0\nSevere Errors 0 0 0\nErrors 0 0 0\nWarnings 0 0 0\n')


class MainWiringTests(unittest.TestCase):
    def test_existing_output_is_rejected_before_supervisor_or_com(self):
        with tempfile.TemporaryDirectory(prefix='aspen-evidence-offline-preflight-') as directory:
            root = Path(directory)
            source = root / 'OFFLINE_after_run.bkp'
            source.write_bytes(b'PROTECTED_USER_SOURCE')
            argv = ['aspen_clean_delivery_audit.py', '--source', str(source), '--out-dir', str(root), '--label', 'OFFLINE']
            with patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()):
                code = audit.main()
            self.assertEqual(code, 1)
            self.assertEqual(source.read_bytes(), b'PROTECTED_USER_SOURCE')

    def run_audit(self, control=NATIVE_ZERO, history='NO ERRORS OR WARNINGS GENERATED\n', stale=False, state='returned'):
        with tempfile.TemporaryDirectory(prefix='aspen-evidence-offline-') as directory:
            root = Path(directory)
            source = root / 'source.bkp'
            source.write_bytes(b'SYNTHETIC_CASE_NOT_ASPEN')
            out = root / 'evidence'
            app = types.SimpleNamespace()
            def save_as(value):
                path = Path(value)
                path.write_bytes(b'SYNTHETIC_SAVED_CASE')
                if history is not None and not stale:
                    path.with_suffix('.his').write_text(history, encoding='utf-8')
            app.SaveAs = save_as
            def create(progid):
                audit._SESSIONS[id(app)] = types.SimpleNamespace(metadata={'fixture': True})
                return app, progid
            def open_case(_app, staged):
                if stale:
                    (staged.parent / 'OLD.his').write_text('NO ERRORS OR WARNINGS GENERATED\n', encoding='utf-8')
                return 'FAKE_OPEN', []
            def run(_app, timeout_s, *, run_id, case_sha256):
                audit.MESSAGES[:] = control.splitlines()
                import time
                now = time.time()
                return {'status': state, 'run_id': run_id, 'case_sha256': case_sha256,
                        'started_epoch': now, 'finished_epoch': now + .001, 'events_cleared_before_run': True}
            def export(_app, kind, path):
                path.write_bytes(b'BLOCK B1 HEATER\n' if kind == 4 else b'SYNTHETIC_EXPORT')
                return {'ok': True, **audit.artifact(path)}
            fake_win = types.ModuleType('win32com')
            fake_client = types.ModuleType('win32com.client')
            fake_client.WithEvents = lambda app, events: object()
            fake_win.client = fake_client
            argv = ['aspen_clean_delivery_audit.py', '--_worker', '--source', str(source), '--out-dir', str(out), '--label', 'OFFLINE']
            with patch.dict(sys.modules, {'win32com': fake_win, 'win32com.client': fake_client}), \
                 patch.dict(os.environ, {'ASPEN_RUNTIME_OWNER_TOKEN': 'OFFLINE_TOKEN', 'ASPEN_RUNTIME_RUN_ID': 'OFFLINE_RUN'}), \
                 patch.object(sys, 'argv', argv), patch.object(audit, 'create_aspen', create), \
                 patch.object(audit, 'open_case', open_case), patch.object(audit, 'run_async', run), \
                 patch.object(audit, 'export_file', export), \
                 patch.object(audit, 'block_statuses', return_value=([{'block': 'B1', 'blkstat': 0}], [])), \
                 patch.object(audit, 'close_aspen', return_value={'closed_cleanly': True, 'status': 'FAKE_CLOSED'}), \
                 contextlib.redirect_stdout(io.StringIO()):
                exit_code = audit.main()
            audit._SESSIONS.pop(id(app), None)
            result = json.loads((out / 'OFFLINE_summary.json').read_text(encoding='utf-8'))
            # Keep the diagnostic result in memory only; source remains untouched.
            self.assertEqual(source.read_bytes(), b'SYNTHETIC_CASE_NOT_ASPEN')
            owned_work = Path(result['work_dir']).resolve()
            if owned_work.parent != Path(tempfile.gettempdir()).resolve() or not owned_work.name.startswith('AspenAudit_OFFLINE_'):
                raise AssertionError('Unexpected offline test work directory; refusing cleanup')
            shutil.rmtree(owned_work)
            return exit_code, result

    def test_real_main_accepts_complete_current_native_evidence_only(self):
        code, result = self.run_audit()
        self.assertEqual(code, 0, result.get('rejection_reasons'))
        self.assertTrue(result['simulation_clean'])
        self.assertFalse(result['delivery_verified'])
        self.assertEqual(result['control_panel']['summary_counts']['columns'], ['Physical Property', 'System', 'Simulation'])

    def test_real_main_rejects_missing_history(self):
        code, result = self.run_audit(history=None)
        self.assertEqual(code, 1)
        self.assertFalse(result['history_present'])
        self.assertIsNone(result['history_hard_pattern_counts'])
        self.assertIn('HISTORY_MISSING', [gate['code'] for gate in result['rejection_reasons']])

    def test_real_main_rejects_unverified_synthetic_five_even_if_zero(self):
        control = '\n'.join(['Summary of Simulation Errors', 'Physical Property System Simulation Terminal'] + [row + ' 0 0 0 0 0' for row in ['Terminal Errors', 'Severe Errors', 'Errors', 'Warnings']])
        code, result = self.run_audit(control=control)
        self.assertEqual(code, 1)
        self.assertFalse(result['simulation_clean'])
        self.assertIn('SUMMARY_SCHEMA_NOT_SOURCE_VERIFIED', [gate['code'] for gate in result['rejection_reasons']])

    def test_real_main_rejects_stale_only_history(self):
        code, result = self.run_audit(stale=True)
        self.assertEqual(code, 1)
        self.assertFalse(result['history_present'])
        self.assertTrue(any(item['evidence_role'] == 'stale_excluded' for item in result['sidecars']))

    def test_real_main_rejects_actual_warning_even_with_clean_summary(self):
        code, result = self.run_audit(history='* WARNING IN THE BLOCK\nNO ERRORS OR WARNINGS GENERATED\n')
        self.assertEqual(code, 1)
        self.assertTrue(result['histories'][0]['messages'])

    def test_real_main_rejects_success_only_summary_and_unknown_run(self):
        for options in [{'control': 'NO ERRORS OR WARNINGS GENERATED'}, {'state': 'state_unknown'}, {'history': 'Calculation started\n'}]:
            with self.subTest(options=options):
                code, result = self.run_audit(**options)
                self.assertEqual(code, 1)
                self.assertFalse(result['passed'])


if __name__ == '__main__':
    unittest.main()
