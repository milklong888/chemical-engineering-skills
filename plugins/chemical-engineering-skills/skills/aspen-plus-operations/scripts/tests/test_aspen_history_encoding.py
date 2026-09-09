"""Offline caller tests; no COM creation and no Aspen execution."""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import aspen_clean_delivery_audit as caller
from aspen_evidence import inspect_history_text


class HistoryEncodingTests(unittest.TestCase):
    def setUp(self):
        self.run = {'run_id': 'synthetic-run', 'case_sha256': 'A' * 64}
        self.data = ('\u8f93\u5165\u6587\u4ef6\u521b\u5efa\u7531\nNO ERRORS OR WARNINGS GENERATED\n').encode('cp936')

    def evidence(self, acp=936):
        with patch.object(caller, '_windows_ansi_code_page', return_value=acp):
            return caller.capture_history_encoding_evidence(**self.run, progid='Apwn.Document.40.0')

    def sidecar(self, data=None):
        data = self.data if data is None else data
        return {'path': 'synthetic.his', 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest().upper(),
                'evidence_role': 'current_run_candidate', 'new_or_changed': True,
                'association': {**self.run, 'verified': True}}

    def decode(self, evidence=None, data=None, sidecar=None):
        data = self.data if data is None else data
        return caller.decode_current_history(data, sidecar=sidecar or self.sidecar(data), run=self.run,
                                             encoding_evidence=self.evidence() if evidence is None else evidence)

    def test_cp936_current_run_has_complete_history_but_no_matrix(self):
        result = self.decode()
        self.assertTrue(result['verified'])
        self.assertEqual(result['encoding'], 'cp936')
        self.assertTrue(result['encoding_evidence']['fallback_roundtrip_verified'])
        inspected = inspect_history_text(result['text'])
        self.assertTrue(inspected['complete'])
        self.assertFalse(inspected['summary']['found'])
        self.assertEqual(inspected['messages'], [])

    def test_no_acp_does_not_guess_from_locale(self):
        with patch.object(caller, '_windows_ansi_code_page', side_effect=OSError('ACP unavailable')):
            evidence = caller.capture_history_encoding_evidence(**self.run, progid='Apwn.Document.40.0')
        self.assertFalse(evidence['verified'])
        self.assertFalse(self.decode(evidence)['verified'])

    def test_unknown_encoding_is_rejected(self):
        evidence = self.evidence(999999)
        self.assertFalse(evidence['verified'])
        self.assertFalse(self.decode(evidence)['verified'])

    def test_stale_history_cannot_borrow_local_acp(self):
        sidecar = self.sidecar()
        sidecar['evidence_role'] = 'stale_excluded'
        self.assertFalse(self.decode(sidecar=sidecar)['verified'])

    def test_wrong_run_cannot_borrow_local_acp(self):
        sidecar = self.sidecar()
        sidecar['association']['run_id'] = 'different-run'
        self.assertFalse(self.decode(sidecar=sidecar)['verified'])

    def test_hash_drift_cannot_borrow_local_acp(self):
        sidecar = self.sidecar()
        sidecar['sha256'] = 'F' * 64
        self.assertFalse(self.decode(sidecar=sidecar)['verified'])

    def test_encoding_evidence_is_run_bound(self):
        evidence = self.evidence()
        evidence['case_sha256'] = 'B' * 64
        self.assertFalse(self.decode(evidence)['verified'])

    def test_utf8_precedes_native_ansi(self):
        data = self.data.decode('cp936').encode('utf-8')
        result = self.decode(data=data)
        self.assertTrue(result['verified'])
        self.assertEqual(result['encoding'], 'utf-8')
        self.assertFalse(result['encoding_evidence']['fallback_used'])

    def test_bom_precedes_native_ansi(self):
        data = self.data.decode('cp936').encode('utf-16')
        result = self.decode(data=data)
        self.assertTrue(result['verified'])
        self.assertEqual(result['encoding'], 'utf-16')
        self.assertFalse(result['encoding_evidence']['fallback_used'])

    def test_incomplete_multibyte_character_is_not_ignored(self):
        self.assertFalse(self.decode(data=b'\x81')['verified'])

    def test_actual_warning_survives_native_decode(self):
        result = self.decode(data=self.data + b'* WARNING\nreal issue\n')
        self.assertTrue(inspect_history_text(result['text'])['messages'])

    def _actual_caller_with_ansi_history(self, acp):
        # Reuse the existing fake-session harness, but emit native ANSI bytes.
        from test_aspen_evidence_integration import MainWiringTests
        original = Path.write_text
        def native_history(path, text, *args, **kwargs):
            if path.suffix.lower() == '.his':
                return path.write_bytes(text.encode('cp936', errors='strict'))
            return original(path, text, *args, **kwargs)
        with patch.object(Path, 'write_text', native_history), \
             patch.object(caller, '_windows_ansi_code_page', return_value=acp):
            return MainWiringTests().run_audit(history=self.data.decode('cp936'))

    def test_actual_main_collects_and_consumes_native_acp(self):
        code, result = self._actual_caller_with_ansi_history(936)
        self.assertEqual(code, 0, result.get('rejection_reasons'))
        self.assertEqual(result['encoding_evidence']['acp'], 936)
        self.assertTrue(result['histories'][0]['encoding_evidence']['fallback_used'])

    def test_actual_main_does_not_guess_when_acp_unknown(self):
        code, result = self._actual_caller_with_ansi_history(999999)
        self.assertEqual(code, 1)
        self.assertIn('HISTORY_DECODE_UNVERIFIED', [x['code'] for x in result['rejection_reasons']])

    def test_actual_main_does_not_guess_when_acp_absent(self):
        code, result = self._actual_caller_with_ansi_history(None)
        self.assertEqual(code, 1)
        self.assertIn('HISTORY_DECODE_UNVERIFIED', [x['code'] for x in result['rejection_reasons']])


if __name__ == '__main__':
    unittest.main(verbosity=2)
