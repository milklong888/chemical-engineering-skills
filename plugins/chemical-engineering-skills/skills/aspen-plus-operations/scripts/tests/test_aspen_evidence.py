"""Strict evidence regressions. Synthetic fixtures do not certify an Aspen case."""
from __future__ import annotations

import codecs
import copy
import importlib.util
import re
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import aspen_evidence as ev


def table(values=None, columns=None):
    columns = columns or list(ev.COLUMNS)
    values = values or {row: [0] * 5 for row in ev.ROWS}
    return '\n'.join(['Summary of Simulation Errors', ' '.join(columns)] + [row + '  ' + ' '.join(map(str, values[row])) for row in ev.ROWS if row in values])


def diagnostic_five(text):
    """Historical synthetic shape tests, explicitly not production acceptance."""
    return ev.parse_summary_counts(text, profile='explicit_matrix5')


def native_table():
    return '\n'.join(['Summary of Simulation Errors', 'Physical', 'Property System Simulation'] + [row + ' 0 0 0' for row in ev.ROWS])


class SummaryTests(unittest.TestCase):
    def test_clean_full_table_and_named_columns(self):
        result = diagnostic_five(table())
        self.assertTrue(result['found'])
        self.assertTrue(result['complete'])
        self.assertTrue(result['valid_schema'])
        self.assertTrue(result['all_zero'])
        self.assertEqual(result['total'], 0)
        self.assertEqual(result['columns'], list(ev.COLUMNS))
        self.assertTrue(all(len(row) == 5 for row in result['counts'].values()))
        self.assertFalse(result['acceptance_eligible'])
        self.assertFalse(result['source_verified_schema'])
        self.assertEqual(result['gate_status'], 'DIAGNOSTIC_ONLY')

    def test_all_twenty_cells(self):
        for row in ev.ROWS:
            for col in range(5):
                with self.subTest(row=row, column=col):
                    values = {name: [0] * 5 for name in ev.ROWS}
                    values[row][col] = 1
                    result = diagnostic_five(table(values))
                    self.assertEqual(result['total'], 1)
                    self.assertFalse(result['all_zero'])
                    cell = result['nonzero_cells'][0]
                    self.assertEqual((cell['row'], cell['column'], cell['value']), (row, ev.COLUMNS[col], 1))

    def test_missing_each_row(self):
        for missing in ev.ROWS:
            values = {name: [0] * 5 for name in ev.ROWS if name != missing}
            result = diagnostic_five(table(values))
            self.assertFalse(result['complete'])
            self.assertIsNone(result['total'])
            self.assertIn(missing, result['tables'][0]['missing_rows'])

    def test_success_statement_never_fills_counts(self):
        for text in ['', 'NO ERRORS OR WARNINGS GENERATED']:
            result = ev.parse_summary_counts(text)
            self.assertFalse(result['found'])
            self.assertFalse(result['all_zero'])
            self.assertEqual(result['counts'], {})
            self.assertIsNone(result['total'])

    def test_nonzero_and_success_conflict(self):
        values = {row: [0] * 5 for row in ev.ROWS}
        values['Errors'][0] = 1
        result = diagnostic_five(table(values) + '\nNO ERRORS OR WARNINGS GENERATED')
        self.assertEqual(result['counts']['Errors'][0], 1)
        self.assertIn('CLEAN_STATEMENT_CONFLICTS_WITH_COUNTS', [d['code'] for d in result['diagnostics']])

    def test_duplicate_rows_are_not_silently_overwritten(self):
        for row in ['Errors 0 0 0 0 0', 'Errors 1 0 0 0 0']:
            result = diagnostic_five(table() + '\n' + row)
            self.assertFalse(result['complete'])
            self.assertIsNone(result['total'])
            self.assertIn('DUPLICATE_ROW', [d['code'] for d in result['diagnostics']])

    def test_malformed_row_counts(self):
        for tokens in ['0 0 0', '0 0 0 0', '0 0 0 0 0 0', '-1 0 0 0 0', '0.0 0 0 0 0', 'N/A 0 0 0 0', '***** 0 0 0 0', 'O 0 0 0 0']:
            result = diagnostic_five(table().replace('Warnings  0 0 0 0 0', 'Warnings ' + tokens))
            self.assertFalse(result['all_zero'])
            self.assertIsNone(result['total'])

    def test_header_identity_and_reordering(self):
        no_header = table().replace('Physical Property System Simulation Terminal\n', '')
        self.assertFalse(diagnostic_five(no_header)['valid_schema'])
        duplicate = table().replace('Physical Property', 'Physical Physical')
        self.assertFalse(diagnostic_five(duplicate)['valid_schema'])
        values = {row: [0] * 5 for row in ev.ROWS}
        values['Warnings'][0] = 2
        result = diagnostic_five(table(values, list(reversed(ev.COLUMNS))))
        self.assertEqual(result['nonzero_cells'][0]['column'], 'Terminal')

    def test_real_three_column_wrapped_header_is_not_five(self):
        text = ' *** Summary of Simulation Errors ***\n Physical\n Property System Simulation\nTerminal Errors 0 0 0\nSevere Errors 0 0 0\nErrors 0 0 0\nWarnings 0 0 23'
        result = ev.parse_summary_counts(text, profile='explicit_matrix5')
        self.assertTrue(result['found'])
        self.assertFalse(result['valid_schema'])
        self.assertFalse(result['all_zero'])
        self.assertIsNone(result['total'])
        self.assertIn('UNSUPPORTED_SUMMARY_SCHEMA', [d['code'] for d in result['diagnostics']])
        self.assertEqual(ev.find_hard_messages(text), [])
        self.assertEqual(result['nonzero_cells'][0]['value'], 23)

    def test_verified_native_three_profile_checks_all_twelve_cells(self):
        baseline = ' *** Summary of Simulation Errors ***\n Physical\n Property System Simulation\nTerminal Errors 0 0 0\nSevere Errors 0 0 0\nErrors 0 0 0\nWarnings 0 0 0'
        result = ev.parse_summary_counts(baseline)
        self.assertTrue(result['all_zero'])
        self.assertEqual(result['columns'], list(ev.NATIVE_THREE_COLUMNS))
        for row in ev.ROWS:
            for index in range(3):
                values = ['0'] * 3
                values[index] = '1'
                dirty = re.sub('^' + re.escape(row) + r' 0 0 0$', row + ' ' + ' '.join(values), baseline, flags=re.M)
                with self.subTest(row=row, index=index):
                    result = ev.parse_summary_counts(dirty)
                    self.assertFalse(result['all_zero'])
                    self.assertEqual(result['nonzero_cells'][0]['column'], ev.NATIVE_THREE_COLUMNS[index])
                    self.assertEqual(result['nonzero_cells'][0]['row'], row)
                    self.assertEqual(len(result['nonzero_cells']), 1)
        self.assertFalse(ev.parse_summary_counts(baseline.replace(' Physical\n', ''))['valid_schema'])
        self.assertFalse(ev.parse_summary_counts(baseline + '\n' + table())['all_zero'])
        with self.assertRaises(ValueError): ev.parse_summary_counts(baseline, profile='accept_any_columns')

    def test_multiple_tables_conflicts_and_last_incomplete(self):
        same = diagnostic_five(table() + '\n' + table())
        self.assertTrue(same['all_zero'])
        self.assertEqual(len(same['tables']), 2)
        dirty = table().replace('Warnings  0 0 0 0 0', 'Warnings 0 0 0 1 0')
        for text in [dirty + '\n' + table(), table() + '\n' + dirty]:
            result = diagnostic_five(text)
            self.assertFalse(result['all_zero'])
            self.assertIsNone(result['total'])
            self.assertIn('CONFLICTING_SUMMARIES', [d['code'] for d in result['diagnostics']])
        result = diagnostic_five(table() + '\nSummary of Simulation Errors\nPhysical Property System Simulation Terminal\nWarnings 0 0 0 0 0')
        self.assertFalse(result['complete'])
        self.assertIsNone(result['total'])

    def test_whitespace_blank_separator_and_scan_limit(self):
        text = table().lower().replace('\n', '\r\n  \t').replace('severe errors', '\n---\nsevere errors')
        self.assertTrue(diagnostic_five(text)['all_zero'])
        result = ev.parse_summary_counts('Summary of Simulation Errors\n' + '\n' * 100 + table())
        self.assertFalse(result['all_zero'])
        self.assertIn('SUMMARY_SCAN_LIMIT_REACHED', [d['code'] for d in result['diagnostics']])

    def test_unverified_five_is_rejected_by_production_default(self):
        result = ev.parse_summary_counts(table())
        self.assertTrue(result['found'])
        self.assertFalse(result['valid_schema'])
        self.assertFalse(result['acceptance_eligible'])
        self.assertEqual(result['gate_status'], 'FAIL')
        self.assertIn('UNSUPPORTED_SUMMARY_SCHEMA', [item['code'] for item in result['diagnostics']])

    def test_native_production_missing_rows_values_and_multiple_tables(self):
        baseline = native_table()
        self.assertEqual(ev.parse_summary_counts(baseline)['gate_status'], 'PASS')
        for row in ev.ROWS:
            with self.subTest(row=row):
                self.assertFalse(ev.parse_summary_counts(baseline.replace(row + ' 0 0 0', ''))['complete'])
        for tokens in ['0 0', '0 0 0 0', '-1 0 0', '0.0 0 0', 'N/A 0 0']:
            self.assertFalse(ev.parse_summary_counts(baseline.replace('Warnings 0 0 0', 'Warnings ' + tokens))['all_zero'])
        self.assertFalse(ev.parse_summary_counts(baseline + '\nErrors 1 0 0')['complete'])
        self.assertTrue(ev.parse_summary_counts(baseline + '\n' + baseline)['all_zero'])
        dirty = baseline.replace('Errors 0 0 0', 'Errors 0 0 1')
        for text in [dirty + '\n' + baseline, baseline + '\n' + dirty, dirty + '\nNO ERRORS OR WARNINGS GENERATED']:
            self.assertFalse(ev.parse_summary_counts(text)['all_zero'])


class MessageDecodeTests(unittest.TestCase):
    def test_summary_labels_are_not_diagnostics(self):
        self.assertEqual(ev.find_hard_messages(table()), [])
        self.assertEqual(sum(ev.hard_pattern_counts(table()).values()), 0)

    def test_each_original_pattern_remains(self):
        lines = ['* WARNING IN THE BLOCK X', 'WARNING WHILE CALCULATING', '*** SEVERE ERROR IN THE BLOCK X', 'ERROR WHILE EXECUTING', 'TERMINAL ERROR IN THE BLOCK', 'CHECK THE RUN STATUS', 'M-BAL LOOP DID NOT CONVERGE', 'ZEROTH ORDER REACTANT NOT PRESENT', 'FAILED TO CONVERGE', 'ZERO FEED', 'BLOCK BYPASSED']
        messages = ev.find_hard_messages('\n'.join(lines), source='history', source_sha256='A' * 64)
        self.assertEqual(len(messages), len(lines))
        self.assertGreater(len(messages[0]['patterns']), 1)
        self.assertEqual(messages[0]['line'], 1)
        self.assertEqual(messages[0]['raw'], lines[0])

    def test_diagnostic_inside_or_after_summary_never_skipped(self):
        for text in [table() + '\n* WARNING REAL\nNO ERRORS OR WARNINGS GENERATED', table().replace('Errors  0 0 0 0 0', 'Errors 0 0 0 0 0 * WARNING REAL', 1), table().replace('Severe Errors', '* WARNING REAL\nSevere Errors')]:
            self.assertTrue(ev.find_hard_messages(text))

    def test_supported_encodings_once_and_unknown_failclosed(self):
        text = '* WARNING 中文\n'
        for data in [text.encode('utf-8'), codecs.BOM_UTF8 + text.encode('utf-8'), codecs.BOM_UTF16_LE + text.encode('utf-16-le'), codecs.BOM_UTF16_BE + text.encode('utf-16-be')]:
            decoded = ev.decode_history_bytes(data)
            self.assertTrue(decoded['verified'])
            self.assertEqual(decoded['text'], text)
            self.assertEqual(len(ev.find_hard_messages(decoded['text'])), 1)
        bad = ev.decode_history_bytes(b'\x81\xff\x00\x00')
        self.assertFalse(bad['verified'])
        self.assertFalse(ev.decode_history_bytes(b'W\x00A\x00R\x00N\x00')['verified'])
        self.assertFalse(ev.decode_history_bytes(text.encode('gb18030'))['verified'])
        self.assertTrue(ev.decode_history_bytes(text.encode('gb18030'), verified_fallback_encodings=('gb18030',))['verified'])


class GateTests(unittest.TestCase):
    def inputs(self):
        identity = {'verified': True, 'run_id': 'RUN-1', 'case_sha256': 'A' * 64}
        return dict(run={'status': 'returned', 'run_id': 'RUN-1', 'case_sha256': 'A' * 64, 'started_epoch': 100.0, 'finished_epoch': 110.0}, summary=ev.parse_summary_counts(native_table()), control_messages=[], control_association=identity.copy(), histories=[{'path': '/owned/run.his', 'size': 20, 'sha256': 'B' * 64, 'decode_verified': True, 'complete': True, 'association': identity.copy(), 'messages': []}])

    def test_explicit_diagnostic_five_cannot_pass_clean_gate(self):
        args = self.inputs()
        args['summary'] = diagnostic_five(table())
        self.assertTrue(args['summary']['all_zero'])
        result = ev.evaluate_clean_gate(**args)
        self.assertFalse(result['passed'])
        self.assertIn('SUMMARY_SCHEMA_NOT_SOURCE_VERIFIED', [item['code'] for item in result['rejection_reasons']])

    def test_complete_current_evidence_can_pass_simulation_gate(self):
        result = ev.evaluate_clean_gate(**self.inputs())
        self.assertTrue(result['passed'])
        self.assertTrue(result['simulation_clean'])
        self.assertFalse(result['delivery_verified'])

    def test_missing_empty_unverified_history_and_wrong_run(self):
        for mutation in ['missing', 'empty', 'decode', 'association', 'run', 'case', 'hash', 'run_unknown', 'control', 'incomplete']:
            args = self.inputs()
            if mutation == 'missing': args['histories'] = []
            elif mutation == 'empty': args['histories'][0]['size'] = 0
            elif mutation == 'decode': args['histories'][0]['decode_verified'] = False
            elif mutation == 'association': args['histories'][0]['association']['verified'] = False
            elif mutation == 'run': args['histories'][0]['association']['run_id'] = 'OLD-RUN'
            elif mutation == 'case': args['histories'][0]['association']['case_sha256'] = 'C' * 64
            elif mutation == 'hash': args['histories'][0]['sha256'] = None
            elif mutation == 'run_unknown': args['run']['status'] = 'returned_status_unknown'
            elif mutation == 'control': args['control_association'] = None
            elif mutation == 'incomplete': args['histories'][0]['complete'] = False
            with self.subTest(mutation=mutation): self.assertFalse(ev.evaluate_clean_gate(**args)['passed'])

    def test_actual_history_warning_always_fails(self):
        args = self.inputs()
        args['histories'][0]['messages'] = ev.find_hard_messages('* WARNING: REAL\nNO ERRORS OR WARNINGS GENERATED')
        self.assertFalse(ev.evaluate_clean_gate(**args)['passed'])

    def test_truncated_history_is_not_complete(self):
        self.assertFalse(ev.inspect_history_text('Aspen calculation started\nBlock X')['complete'])
        self.assertTrue(ev.inspect_history_text('NO ERRORS OR WARNINGS GENERATED')['complete'])
        # The history end marker does not stand in for the independent matrix.
        self.assertFalse(ev.inspect_history_text('NO ERRORS OR WARNINGS GENERATED')['summary']['found'])

    def test_block_and_artifact_unknown_not_default_zero(self):
        for extra in [{'block_statuses': [{'block': 'B1', 'blkstat': None}]}, {'artifacts': [{'exists': False, 'size': 0, 'sha256': None}]}]:
            self.assertFalse(ev.evaluate_clean_gate(**self.inputs(), **extra)['passed'])


if __name__ == '__main__':
    unittest.main()
