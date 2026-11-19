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
import time
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import aspen_clean_delivery_audit as audit
import aspen_run_supervisor as supervisor

NATIVE_COMPLETED = '->Simulation calculations completed ...\n'
NATIVE_CLEAN = '  ***  No Errors or Warnings were issued during Simulation ***\n'
NATIVE_HISTORY = ('+ + ASPEN PLUS CALCULATION HISTORY + +\n'
                  '  Results generated     Time = 0.58\n'
                  '  NO ERRORS OR WARNINGS GENERATED\n')
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

    def run_audit(self, control=NATIVE_CLEAN, history=NATIVE_HISTORY, stale=False, state='completed',
                  mode=None, late=None, native_blocks=('B1',), missing_export=False,
                  drained=True, parent=False, closeout_verified=True):
        with tempfile.TemporaryDirectory(prefix='aspen-evidence-offline-') as directory:
            root = Path(directory)
            source = root / 'source.bkp'
            source.write_bytes(b'SYNTHETIC_CASE')
            out = root / 'evidence'
            stage_path = root / 'stage.json'
            pending = []
            app = types.SimpleNamespace()

            def pump():
                if pending:
                    pending.pop(0)()
                return 0

            def save_as(value):
                path = Path(value)
                path.write_bytes(b'SYNTHETIC_SAVED_CASE')
                if history is not None and not stale:
                    path.with_suffix('.his').write_text(history, encoding='utf-8')

            app.SaveAs = save_as

            def create(progid):
                audit._SESSIONS[id(app)] = types.SimpleNamespace(
                    metadata={'fixture': True}, pythoncom=types.SimpleNamespace(PumpWaitingMessages=pump))
                return app, progid

            def open_case(_app, staged):
                if stale:
                    (staged.parent / 'OLD.his').write_text(NATIVE_HISTORY, encoding='utf-8')
                return 'FAKE_OPEN', []

            def run(_app, timeout_s, *, run_id, case_sha256, events):
                now = time.time()
                for line in control.splitlines():
                    app.events.OnControlPanelMessage(False, line)
                if state == 'completed':
                    app.events.OnCalculationCompleted()
                return {'status': state, 'run_id': run_id, 'case_sha256': case_sha256,
                        'started_epoch': now, 'finished_epoch': time.time(), 'events_cleared_before_run': True,
                        'completion_event_observed': state == 'completed', 'terminal_engine_idle': state == 'completed'}

            def export(_app, kind, path):
                if kind == 1 and late is not None:
                    pending.append(lambda: app.events.OnControlPanelMessage(False, late))
                if not (missing_export and kind == 1):
                    path.write_bytes(b'BLOCK B1 HEATER\n' if kind == 4 else b'SYNTHETIC_EXPORT')
                return {'ok': path.is_file(), **audit.artifact(path)}

            def drain(session, events, *, quiet_s, timeout_s):
                receipt = real_drain(session, events, quiet_s=0, timeout_s=timeout_s)
                return {**receipt, 'completed': drained}

            def create_events(_app, event_type):
                app.events = event_type()
                return app.events

            def run_supervised(command, *, audit_summary_path, **kwargs):
                worker_args = [arg for arg in command[command.index('--_worker') - 1:]]
                with patch.object(sys, 'argv', worker_args):
                    code = audit.main()
                stage = json.loads(stage_path.read_text(encoding='utf-8'))
                outcome = supervisor._verified_audit_outcome(stage, audit_summary_path, 'OFFLINE_RUN', code)
                self.assertEqual(outcome, 'audit_accepted' if code == 0 else 'audit_rejected')
                return {'status': 'completed', 'lifecycle_clean': True, 'forced_termination': False,
                        'audit_closeout_verified': closeout_verified, 'last_stage': stage}

            real_drain = audit.drain_events
            fake_win = types.ModuleType('win32com')
            fake_client = types.ModuleType('win32com.client')
            fake_client.WithEvents = create_events
            fake_win.client = fake_client
            argv = ['aspen_clean_delivery_audit.py', '--source', str(source), '--out-dir', str(out), '--label', 'OFFLINE']
            if not parent:
                argv.append('--_worker')
            if mode is not None:
                argv.extend(['--mode', mode])
            with patch.dict(sys.modules, {'win32com': fake_win, 'win32com.client': fake_client}), \
                 patch.dict(os.environ, {'ASPEN_RUNTIME_OWNER_TOKEN': 'OFFLINE_TOKEN', 'ASPEN_RUNTIME_RUN_ID': 'OFFLINE_RUN',
                                         'ASPEN_RUNTIME_STAGE_FILE': str(stage_path)}), \
                 patch.object(sys, 'argv', argv), patch.object(audit, 'create_aspen', create), \
                 patch.object(audit, 'open_case', open_case), patch.object(audit, 'run_async', run), \
                 patch.object(audit, 'export_file', export), patch.object(audit, 'drain_events', drain), \
                 patch.object(audit, 'capture_expected_blocks',
                              return_value={'verified': bool(native_blocks), 'blocks': list(native_blocks)}), \
                 patch.object(audit, 'block_statuses',
                              return_value=([{'block': 'B1', 'blkstat': 0}], [])), \
                 patch.object(audit, 'close_aspen', return_value={'closed_cleanly': True, 'status': 'FAKE_CLOSED'}), \
                 patch.object(supervisor, 'run_worker', run_supervised), contextlib.redirect_stdout(io.StringIO()):
                exit_code = audit.main()
            audit._SESSIONS.pop(id(app), None)
            result = json.loads((out / 'OFFLINE_summary.json').read_text(encoding='utf-8'))
            self.assertEqual(source.read_bytes(), b'SYNTHETIC_CASE')
            if parent:
                worker_summary = result['worker_summary']
                self.assertEqual(audit.artifact(Path(worker_summary['path']))['sha256'], worker_summary['sha256'])
            if 'control_panel' in result:
                raw_events = result['control_panel']['raw_events']
                result['test_raw_events'] = json.loads(Path(raw_events['path']).read_text(encoding='utf-8'))['events']
            result['test_finished_stage'] = json.loads(stage_path.read_text(encoding='utf-8'))
            owned_work = Path(result['work_dir']).resolve()
            if owned_work.parent != Path(tempfile.gettempdir()).resolve() or not owned_work.name.startswith('AspenAudit_OFFLINE_'):
                raise AssertionError('Unexpected offline test work directory; refusing cleanup')
            shutil.rmtree(owned_work)
            return exit_code, result

    def test_default_mode_accepts_complete_current_run_without_counts(self):
        code, result = self.run_audit(control=NATIVE_COMPLETED + NATIVE_CLEAN, parent=True)
        self.assertEqual(code, 0, result.get('rejection_reasons'))
        self.assertEqual(result['mode'], 'run')
        self.assertTrue(result['operation_completed'])
        self.assertTrue(result['simulation_clean'])
        self.assertEqual(result['summary_counts_status'], 'unknown')
        self.assertFalse(result['strict_solver_passed'])
        self.assertFalse(result['delivery_verified'])
        self.assertIsNone(result['control_panel']['summary_counts']['total'])

    def test_strict_mode_retains_complete_zeros_requirement(self):
        code, result = self.run_audit(control=NATIVE_COMPLETED + NATIVE_CLEAN, mode='strict', parent=True)
        self.assertEqual(code, 1)
        self.assertTrue(result['operation_completed'])
        self.assertTrue(result['simulation_clean'])
        self.assertFalse(result['strict_solver_passed'])
        self.assertEqual(result['test_finished_stage']['worker_outcome'], 'audit_rejected')

        code, result = self.run_audit(control=NATIVE_COMPLETED + NATIVE_ZERO, mode='strict', parent=True)
        self.assertEqual(code, 0, result.get('rejection_reasons'))
        self.assertTrue(result['strict_solver_passed'])
        self.assertEqual(result['summary_counts_status'], 'all_zero')
        self.assertEqual(result['control_panel']['summary_counts']['columns'], ['Physical Property', 'System', 'Simulation'])
        self.assertFalse(result['delivery_verified'])

    def test_supervisor_authentication_rejection_clears_public_result(self):
        code, result = self.run_audit(control=NATIVE_COMPLETED + NATIVE_ZERO, parent=True, closeout_verified=False)
        self.assertEqual(code, 1)
        self.assertFalse(result['operation_completed'])
        self.assertFalse(result['strict_solver_passed'])

    def test_real_main_rejects_missing_or_stale_history(self):
        for options in [{'history': None}, {'stale': True}]:
            with self.subTest(options=options):
                code, result = self.run_audit(control=NATIVE_COMPLETED + NATIVE_CLEAN, **options)
                self.assertEqual(code, 1)
                self.assertFalse(result['history_present'])
                self.assertIsNone(result['history_hard_pattern_counts'])
                self.assertIn('HISTORY_MISSING', [gate['code'] for gate in result['rejection_reasons']])

    def test_real_main_rejects_unverified_synthetic_five_even_if_zero(self):
        control = NATIVE_COMPLETED + '\n'.join(
            ['Summary of Simulation Errors', 'Physical Property System Simulation Terminal']
            + [row + ' 0 0 0 0 0' for row in ['Terminal Errors', 'Severe Errors', 'Errors', 'Warnings']])
        code, result = self.run_audit(control=control)
        self.assertEqual(code, 1)
        self.assertEqual(result['simulation_assessment'], 'UNKNOWN')
        self.assertIn('SUMMARY_SCHEMA_NOT_SOURCE_VERIFIED', [gate['code'] for gate in result['rejection_reasons']])

    def test_actual_problems_are_rejected_and_late_control_event_is_retained(self):
        code, result = self.run_audit(control=NATIVE_COMPLETED + NATIVE_ZERO, late=' ** ERROR IN THE BLOCK  ')
        self.assertEqual(code, 1)
        self.assertEqual(result['simulation_assessment'], 'FAIL')
        self.assertEqual(result['control_panel']['actual_messages'][-1]['raw'], ' ** ERROR IN THE BLOCK  ')
        self.assertEqual(result['test_raw_events'][-1]['message'], ' ** ERROR IN THE BLOCK  ')
        self.assertTrue(result['operation_completed'])
        code, result = self.run_audit(control=NATIVE_COMPLETED + NATIVE_CLEAN,
                                      history=NATIVE_HISTORY.replace('  NO ERRORS', '* WARNING IN THE BLOCK\n  NO ERRORS'))
        self.assertEqual(code, 1)
        self.assertTrue(result['histories'][0]['messages'])

    def test_incomplete_evidence_stays_unknown_in_run_mode(self):
        for options in [{'control': NATIVE_CLEAN}, {'history': 'NO ERRORS OR WARNINGS GENERATED\n'},
                        {'history': 'Calculation started\n'}, {'drained': False},
                        {'native_blocks': ()}, {'native_blocks': ('B1', 'B2')}, {'missing_export': True}]:
            with self.subTest(options=options):
                code, result = self.run_audit(**({'control': NATIVE_COMPLETED + NATIVE_CLEAN} | options))
                self.assertEqual(code, 1)
                self.assertEqual(result['simulation_assessment'], 'UNKNOWN')

    def test_unknown_engine_state_does_not_report_completed_rejection(self):
        code, result = self.run_audit(control=NATIVE_COMPLETED + NATIVE_CLEAN, state='state_unknown')
        self.assertEqual(code, 1)
        self.assertFalse(result['operation_completed'])
        self.assertEqual(result['run']['status'], 'state_unknown')
        self.assertNotIn('worker_outcome', result['test_finished_stage'])


if __name__ == '__main__':
    unittest.main()
