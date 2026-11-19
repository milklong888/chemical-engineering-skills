"""Aspen evidence parsing and run assessment without COM or filesystem writes.

The strict solver gate requires every count in the source-verified native
summary to be present and zero. A normal run can establish clean completion
from complete native messages and fresh history while the counts stay unknown.
"""
from __future__ import annotations

import codecs
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

SCHEMA_VERSION = 'aspen_summary_audit/2'
ROWS = ('Terminal Errors', 'Severe Errors', 'Errors', 'Warnings')
COLUMNS = ('Physical', 'Property', 'System', 'Simulation', 'Terminal')
NATIVE_THREE_COLUMNS = ('Physical Property', 'System', 'Simulation')
DEFAULT_PROFILE = 'verified_native_summaries'
ALLOWED_PROFILES = {DEFAULT_PROFILE, 'explicit_matrix5', 'observed_aspen_three_physical_property'}
VERIFIED_NATIVE_SCHEMA = 'aspen_native_physical_property_system_simulation/1'
PROFILE_AUTHORITY = {
    'user_authorization': 'Publication acceptance contract: complete verified-format counts must all be zero.',
    'native_three_header': 'Exact two-line Physical / Property System Simulation header; no positional three-column fallback',
    'source_manifest': 'references/summary_format_contract.md',
    'source_sha256': ['F1B53FC170C02E67645EEBA0FACB7FBB1D3B2082AA4EC74C7E276FBEED154E00',
                      '1ACF565B48863C416F4D2E256BCA42D5B067BB9515773C1DB13681689E047A92'],
    'version_scope': 'Source-verified native table format; not blanket Aspen version compatibility',
    'production_schemas': [VERIFIED_NATIVE_SCHEMA],
    'explicit_matrix5': {'provenance_status': 'synthetic_diagnostic_only', 'source_verified': False,
                         'acceptance_eligible': False, 'reason': 'Synthetic diagnostic profile; no native five-column source is registered.'},
}
HARD_PATTERNS = [
    r'\*\s+WARNING', r'^\s*\*+\s+ERROR\b', r'^\s*WARNING\b', r'^\s*ERROR\b',
    r'WARNING IN THE', r'WARNING WHILE', r'SEVERE ERROR',
    r'ERROR IN THE', r'ERROR WHILE EXECUTING', r'TERMINAL ERROR',
    r'CHECK THE RUN STATUS', r'M-BAL LOOP DID NOT CONVERGE',
    r'ZEROTH ORDER REACTANT NOT PRESENT', r'FAILED TO CONVERGE',
    r'ZERO FEED', r'BLOCK BYPASSED',
    r'^\s*\**\s*[1-9][0-9]*\s+(?:errors?|warnings?)\b.*\b(?:issued|generated)\b',
]
_TITLE = re.compile(r'^\s*(?:\*{3}\s*)?(?:Summary of Simulation Errors|Summary of Errors)(?:\s*\*{3})?\s*$', re.I)
_ROW = re.compile(r'^\s*(Terminal Errors|Severe Errors|Errors|Warnings)\b(.*)$', re.I)
_CLEAN = re.compile(r'NO ERRORS OR WARNINGS (?:GENERATED|WERE ISSUED)', re.I)
_CONTROL_COMPLETED = re.compile(r'^\s*(?:->\s*)?Simulation calculations completed\s*(?:\.{3})?\s*$', re.I)
_CONTROL_CLEAN = re.compile(r'^\s*\**\s*No Errors or Warnings were issued during Simulation\s*\**\s*$', re.I)
_HISTORY_CLEAN = re.compile(r'^\s*\**\s*NO ERRORS OR WARNINGS GENERATED\s*\**\s*$', re.I)
_HISTORY_HEADER = re.compile(r'^\s*(?:\+\s*)*ASPEN PLUS CALCULATION HISTORY\s*(?:\+\s*)*$', re.I)
_HISTORY_RESULTS = re.compile(r'^\s*Results generated\s+Time\s*=\s*[0-9]+(?:\.[0-9]+)?\s*$', re.I)
_INTEGER = re.compile(r'^[0-9]+$')
_HASH = re.compile(r'^[A-Fa-f0-9]{64}$')
_MAX_TABLE_LINES = 80


def _issue(code: str, line: int | None = None, **details: Any) -> dict[str, Any]:
    return {'code': code, 'severity': 'error', 'line': line, **details}


def _row_parts(raw: str) -> tuple[str, list[str]] | None:
    match = _ROW.fullmatch(raw)
    if not match:
        return None
    label = next(row for row in ROWS if row.casefold() == match.group(1).casefold())
    return label, match.group(2).strip().split()


def _parse_table(lines: list[str], start: int, stop: int, index: int, profile: str) -> dict[str, Any]:
    observed: list[dict[str, Any]] = []
    row_occurrences: dict[str, list[dict[str, Any]]] = {}
    diagnostics = []
    source_columns: list[str] = []
    header_lines: list[dict[str, Any]] = []
    previous_physical = False
    end = start
    limit = min(stop, start + _MAX_TABLE_LINES + 1)
    for pos in range(start + 1, limit):
        raw, stripped = lines[pos], lines[pos].strip()
        end = pos
        if not stripped or re.fullmatch(r'[-=_+]+', stripped):
            continue
        if stripped.startswith(('->', '<<', '\f')):
            break
        row = _row_parts(raw)
        if row:
            label, tokens = row
            entry = {'row': label, 'tokens': tokens, 'line': pos + 1, 'raw': raw}
            entry['numeric'] = bool(tokens) and all(_INTEGER.fullmatch(token) for token in tokens)
            entry['values'] = [int(token) for token in tokens] if entry['numeric'] else None
            observed.append(entry)
            row_occurrences.setdefault(label, []).append(entry)
            if len(row_occurrences[label]) > 1:
                diagnostics.append(_issue('DUPLICATE_ROW', pos + 1, row=label, occurrence_lines=[r['line'] for r in row_occurrences[label]]))
            if not entry['numeric']:
                diagnostics.append(_issue('INVALID_COUNT', pos + 1, row=label, tokens=tokens))
            continue
        # A new section after all four row labels ends this table. Only table
        # data lines, never the entire region, are excluded from message scans.
        if all(row in row_occurrences for row in ROWS):
            break
        tokens = stripped.split()
        canonical = {col.casefold(): col for col in COLUMNS}
        if all(token.casefold() in canonical for token in tokens):
            header_lines.append({'line': pos + 1, 'raw': raw})
            named = [canonical[token.casefold()] for token in tokens]
            if named == ['Physical'] and not source_columns:
                previous_physical = True
                continue
            if previous_physical and named == ['Property', 'System', 'Simulation']:
                source_columns = ['Physical Property', 'System', 'Simulation']
            elif source_columns:
                diagnostics.append(_issue('DUPLICATE_HEADER', pos + 1, observed=named))
            else:
                source_columns = named
            previous_physical = False
        else:
            diagnostics.append(_issue('UNRECOGNIZED_SUMMARY_CONTENT', pos + 1, raw=raw))
    else:
        if limit < stop:
            diagnostics.append(_issue('SUMMARY_SCAN_LIMIT_REACHED', start + 1, end_line=limit, limit=_MAX_TABLE_LINES))
    native_three = source_columns == list(NATIVE_THREE_COLUMNS)
    explicit_five = len(source_columns) == 5 and set(source_columns) == set(COLUMNS)
    supported_three = native_three and profile in {DEFAULT_PROFILE, 'observed_aspen_three_physical_property'}
    supported_five = explicit_five and profile == 'explicit_matrix5'
    valid_header = supported_three or supported_five
    columns = list(NATIVE_THREE_COLUMNS if supported_three else COLUMNS)
    native_schema = VERIFIED_NATIVE_SCHEMA if native_three else 'aspen_explicit_five_columns/1' if explicit_five else 'unknown'
    if not source_columns:
        diagnostics.append(_issue('COLUMN_IDENTITY_UNVERIFIED', start + 1, observed_header=header_lines))
    elif not valid_header:
        code = 'UNSUPPORTED_SUMMARY_SCHEMA' if len(set(source_columns)) == len(source_columns) else 'INVALID_HEADER'
        diagnostics.append(_issue(code, start + 1, observed_columns=source_columns, profile=profile, expected_columns=columns))
    missing = [row for row in ROWS if row not in row_occurrences]
    if missing:
        diagnostics.append(_issue('SUMMARY_MISSING_ROW', start + 1, missing_rows=missing))
    counts = {}
    nonzero = []
    for row in observed:
        if len(row['tokens']) != len(columns):
            diagnostics.append(_issue('ROW_COLUMN_COUNT_MISMATCH', row['line'], row=row['row'], expected=len(columns), observed=len(row['tokens'])))
        if row['values'] is None:
            continue
        values = row['values']
        for col, value in enumerate(values):
            if value:
                nonzero.append({'table_index': index, 'row': row['row'], 'column': source_columns[col] if col < len(source_columns) else f'unverified_column_{col + 1}', 'value': value, 'line': row['line'], 'raw': row['raw']})
        if valid_header and len(values) == len(columns) and len(row_occurrences[row['row']]) == 1:
            counts[row['row']] = [values[source_columns.index(col)] for col in columns]
    complete = not diagnostics and len(counts) == len(ROWS)
    return {'index': index, 'start_line': start + 1, 'end_line': end + 1,
            'source_columns': source_columns, 'columns': columns, 'native_schema': native_schema, 'header_lines': header_lines,
            'observed_rows': observed, 'counts': counts, 'complete': complete,
            'valid_schema': valid_header and not diagnostics,
            'all_zero': complete and not nonzero, 'missing_rows': missing,
            'summary_row_lines': [row['line'] for row in observed if row['numeric']],
            'nonzero_cells': nonzero, 'diagnostics': diagnostics}


def parse_summary_counts(text: str, *, profile: str = DEFAULT_PROFILE) -> dict[str, Any]:
    """Parse every table; retain partial/unsupported evidence without filling it."""
    if profile not in ALLOWED_PROFILES:
        raise ValueError(f'Unknown summary profile: {profile}')
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if _TITLE.fullmatch(line)]
    tables = [_parse_table(lines, start, starts[index + 1] if index + 1 < len(starts) else len(lines), index, profile) for index, start in enumerate(starts)]
    diagnostics = [dict(issue, table_index=table['index']) for table in tables for issue in table['diagnostics']]
    if not tables:
        diagnostics.append(_issue('SUMMARY_MISSING'))
    valid = [table for table in tables if table['complete'] and table['valid_schema']]
    selected = valid[-1] if valid else None
    complete = bool(tables) and all(table['complete'] for table in tables)
    valid_schema = bool(tables) and all(table['valid_schema'] for table in tables)
    signatures = {json.dumps(table['counts'], sort_keys=True) for table in valid}
    mixed_schemas = len({table['native_schema'] for table in tables}) > 1
    if mixed_schemas:
        diagnostics.append(_issue('MIXED_SUMMARY_SCHEMAS', observed_schemas=sorted({table['native_schema'] for table in tables})))
    conflicting = len(signatures) > 1
    if conflicting:
        diagnostics.append(_issue('CONFLICTING_SUMMARIES', table_indices=[table['index'] for table in valid]))
    nonzero = [cell for table in tables for cell in table['nonzero_cells']]
    for cell in nonzero:
        diagnostics.append(_issue('NONZERO_SUMMARY_COUNT', **cell))
    if nonzero and len(tables) > 1:
        diagnostics.append(_issue('NONZERO_SUMMARY_IN_RUN'))
    clean = bool(_CLEAN.search(text))
    if clean and nonzero:
        diagnostics.append(_issue('CLEAN_STATEMENT_CONFLICTS_WITH_COUNTS'))
    usable = complete and valid_schema and not conflicting and not mixed_schemas
    source_verified = bool(tables) and all(table['native_schema'] == VERIFIED_NATIVE_SCHEMA for table in tables)
    acceptance_eligible = source_verified and profile != 'explicit_matrix5'
    counts = selected['counts'] if selected else {}
    total = sum(sum(row) for row in counts.values()) if usable else None
    return {'schema_version': SCHEMA_VERSION, 'found': bool(tables), 'complete': complete,
            'valid_schema': valid_schema, 'all_zero': usable and not nonzero,
            'clean_statement': clean, 'columns': selected['columns'] if selected else [], 'rows': list(ROWS),
            'profile': profile, 'native_schema': selected['native_schema'] if selected else None, 'profile_authority': PROFILE_AUTHORITY,
            'source_verified_schema': source_verified, 'acceptance_eligible': acceptance_eligible,
            'selected_table_index': selected['index'] if selected else None,
            'counts': counts, 'total': total, 'nonzero_cells': nonzero,
            'diagnostics': diagnostics, 'tables': tables,
            'summary_row_lines': sorted({line for table in tables for line in table['summary_row_lines']}),
            'chunk': '\n'.join(lines[selected['start_line'] - 1:selected['end_line']])[:1600] if selected else '',
            'gate_status': 'PASS' if usable and not nonzero and acceptance_eligible else 'DIAGNOSTIC_ONLY' if usable and not nonzero else 'FAIL'}


def find_hard_messages(text: str, *, source: str = 'text', source_sha256: str | None = None) -> list[dict[str, Any]]:
    """Return one record per source line, with every matched original pattern."""
    rows = set(parse_summary_counts(text)['summary_row_lines'])
    records = []
    for number, raw in enumerate(text.splitlines(), 1):
        if number in rows:
            continue
        cleaned = _CLEAN.sub('CLEAN_RUN_STATEMENT', raw)
        patterns = [pattern for pattern in HARD_PATTERNS if re.search(pattern, cleaned, re.I)]
        if patterns:
            records.append({'source': source, 'source_sha256': source_sha256,
                            'line': number, 'raw': raw, 'patterns': patterns,
                            'severity': 'warning' if all('WARNING' in p for p in patterns) else 'error'})
    return records


def hard_pattern_counts(text: str) -> dict[str, int]:
    records = find_hard_messages(text)
    return {pattern: sum(pattern in record['patterns'] for record in records) for pattern in HARD_PATTERNS}


def inspect_control_events(events: list[dict[str, Any]], run: dict[str, Any],
                           final_drain: dict[str, Any]) -> dict[str, Any]:
    """Replay native callbacks, retaining messages that arrive during exports."""
    malformed = []
    messages = []
    completions = []
    for index, row in enumerate(events):
        epoch = row.get('epoch') if isinstance(row, dict) else None
        if type(epoch) not in (int, float) or not math.isfinite(epoch):
            malformed.append(index)
            continue
        if row.get('event') == 'OnCalculationCompleted':
            completions.append(epoch)
            continue
        clear, message = row.get('clear'), row.get('message')
        if (row.get('event') != 'OnControlPanelMessage' or type(clear) not in (bool, int)
                or clear not in (0, 1, -1) or (clear == 0 and not isinstance(message, str))):
            malformed.append(index)
        if isinstance(message, str):
            messages.append(message)
    start, finish = run.get('started_epoch'), run.get('finished_epoch')
    valid_window = all(type(value) in (int, float) and math.isfinite(value) for value in (start, finish))
    in_run = sum(start <= epoch <= finish for epoch in completions) if valid_window else 0
    complete = (run.get('events_cleared_before_run') is True and in_run > 0 and not malformed
                and final_drain.get('completed') is True and final_drain.get('event_count') == len(events))
    # Preserve message payload whitespace and add a boundary when Aspen did not
    # include one. Clear callbacks never erase previously captured diagnostics.
    text = ''.join(message if message.endswith(('\n', '\r')) else message + '\n' for message in messages)
    return {'text': text, 'capture_complete': complete, 'completion_event_count': len(completions),
            'run_completion_event_count': in_run, 'malformed_event_indices': malformed,
            'message_count': len(messages)}


def inspect_control_terminal(text: str, summary: dict[str, Any]) -> dict[str, Any]:
    """Identify documented native completion text without deriving counts from prose."""
    lines = text.splitlines()
    completed = [number for number, line in enumerate(lines, 1) if _CONTROL_COMPLETED.fullmatch(line)]
    clean = [number for number, line in enumerate(lines, 1) if _CONTROL_CLEAN.fullmatch(line)]
    completion_line = completed[0] if len(completed) == 1 else None
    table_starts = [table['start_line'] for table in summary.get('tables', []) if table['complete']]
    terminal_clean = completion_line is not None and any(line > completion_line for line in clean + table_starts)
    return {'verified': terminal_clean, 'completion_lines': completed, 'clean_status_lines': clean,
            'complete_summary_start_lines': table_starts}


def inspect_history_text(text: str, *, source: str = 'history', source_sha256: str | None = None) -> dict[str, Any]:
    """Inspect a full history; only a native end marker or terminal table closes it."""
    summary = parse_summary_counts(text)
    messages = find_hard_messages(text, source=source, source_sha256=source_sha256)
    nonblank = [(number, line) for number, line in enumerate(text.splitlines(), 1) if line.strip()]
    last_line, last_text = nonblank[-1] if nonblank else (0, '')
    clean_statement = bool(_HISTORY_CLEAN.fullmatch(last_text))
    # end_line may include a following non-table line. Use actual row lines here.
    terminal_table = summary['complete'] and last_line in summary['summary_row_lines']
    complete = clean_statement or terminal_table
    header_lines = [number for number, line in nonblank if _HISTORY_HEADER.fullmatch(line)]
    results_lines = [number for number, line in nonblank if _HISTORY_RESULTS.fullmatch(line)]
    native_run_body_verified = bool(header_lines and
                                    any(header_lines[0] < number < last_line for number in results_lines))
    issues = []
    if not complete:
        issues.append(_issue('HISTORY_TERMINAL_EVIDENCE_MISSING'))
    if summary['found'] and not summary['complete']:
        issues.append(_issue('HISTORY_SUMMARY_INCOMPLETE', diagnostics=summary['diagnostics']))
        complete = False
    if clean_statement and messages:
        issues.append(_issue('CLEAN_STATEMENT_CONFLICTS_WITH_MESSAGES'))
    return {'complete': complete, 'terminal_evidence': 'CLEAN_STATEMENT' if clean_statement else 'COMPLETE_SUMMARY' if terminal_table else None,
            'native_run_body_verified': native_run_body_verified,
            'native_run_body': {'header_lines': header_lines, 'results_lines': results_lines},
            'summary': summary, 'messages': messages, 'issues': issues}


def decode_history_bytes(data: bytes, *, verified_fallback_encodings: tuple[str, ...] = ()) -> dict[str, Any]:
    """Select one strict decoding. Fallback encodings require caller-held evidence."""
    digest = hashlib.sha256(data).hexdigest().upper()
    encodings = ['utf-8-sig'] if data.startswith(codecs.BOM_UTF8) else ['utf-16'] if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)) else ['utf-8', *verified_fallback_encodings]
    failures = []
    for encoding in dict.fromkeys(encodings):
        if encoding.casefold().replace('-', '') in {'latin1', 'iso88591'}:
            failures.append({'encoding': encoding, 'reason': 'UNVERIFIABLE_UNIVERSAL_BYTE_DECODER'})
            continue
        try:
            text = data.decode(encoding, errors='strict')
        except (UnicodeDecodeError, LookupError) as exc:
            failures.append({'encoding': encoding, 'reason': str(exc)})
            continue
        if '\x00' in text or '\ufffd' in text or any(ord(char) < 32 and char not in '\n\r\t\f' for char in text):
            failures.append({'encoding': encoding, 'reason': 'UNEXPECTED_CONTROL_OR_REPLACEMENT_CHARACTER'})
            continue
        return {'text': text, 'encoding': encoding, 'verified': True, 'sha256': digest,
                'size': len(data), 'issues': [], 'attempts': failures}
    return {'text': None, 'encoding': None, 'verified': False, 'sha256': digest,
            'size': len(data), 'issues': [_issue('DECODE_UNVERIFIED', attempts=failures)]}


def evaluate_clean_gate(*, run: dict[str, Any], summary: dict[str, Any],
                        control_messages: list[dict[str, Any]], histories: list[dict[str, Any]],
                        control_association: dict[str, Any] | None = None,
                        block_statuses: list[dict[str, Any]] | None = None,
                        artifacts: list[dict[str, Any]] | None = None,
                        expected_blocks: list[str] | None = None,
                        mode: str | None = None) -> dict[str, Any]:
    """Assess a current run; omitted mode retains the legacy strict input contract."""
    if mode not in {None, 'run', 'strict'}:
        raise ValueError(f'Unknown audit mode: {mode}')
    gates: list[dict[str, Any]] = []

    def check(code: str, passed: bool, *, problem: bool = False, **details: Any) -> None:
        gates.append({'code': code, 'passed': bool(passed), 'actual_problem': problem and not passed, **details})

    run_id, case_hash = run.get('run_id'), run.get('case_sha256')
    check('RUN_IDENTITY_REQUIRED', bool(run_id) and bool(_HASH.fullmatch(str(case_hash))))
    try:
        timing = math.isfinite(run['started_epoch']) and math.isfinite(run['finished_epoch']) and run['finished_epoch'] >= run['started_epoch']
    except (KeyError, TypeError, ValueError):
        timing = False
    check('RUN_TIME_IDENTITY_REQUIRED', timing)
    completed = run.get('status') in {'returned', 'completed'} and not run.get('forced_termination', False)
    if mode is not None:
        completed = (completed and run.get('status') == 'completed'
                     and run.get('completion_event_observed') is True and run.get('terminal_engine_idle') is True)
    check('RUN_NOT_COMPLETED', completed, observed=run.get('status'))

    def associated(item: dict[str, Any] | None) -> bool:
        return bool(item and item.get('verified') is True and item.get('run_id') == run_id
                    and str(item.get('case_sha256', '')).upper() == str(case_hash).upper())

    check('CONTROL_ASSOCIATION_UNVERIFIED', associated(control_association))
    if mode is not None:
        check('CONTROL_CAPTURE_INCOMPLETE', (control_association or {}).get('capture_complete') is True)
        check('CONTROL_TERMINAL_EVIDENCE_MISSING', (control_association or {}).get('terminal_verified') is True)
    check('ACTUAL_CONTROL_PROBLEM', isinstance(control_messages, list) and not control_messages,
          problem=bool(control_messages), messages=control_messages)
    check('HISTORY_MISSING', bool(histories))
    for index, history in enumerate(histories):
        identity = {'history_index': index, 'path': history.get('path')}
        check('HISTORY_EMPTY_OR_UNHASHED', isinstance(history.get('size'), (int, float)) and history['size'] > 0 and bool(_HASH.fullmatch(str(history.get('sha256', '')))), **identity)
        check('HISTORY_DECODE_UNVERIFIED', history.get('decode_verified') is True, **identity)
        check('HISTORY_INCOMPLETE', history.get('complete') is True, issues=history.get('issues', []), **identity)
        association = history.get('association')
        check('HISTORY_ASSOCIATION_UNVERIFIED', associated(association), association=association, **identity)
        if mode is not None:
            check('HISTORY_FRESH_CAPTURE_UNVERIFIED',
                  all((association or {}).get(key) is True
                      for key in ('new_or_changed', 'fresh_time', 'unchanged_during_capture')), **identity)
            check('HISTORY_NATIVE_RUN_BODY_UNVERIFIED',
                  history.get('terminal_evidence') == 'COMPLETE_SUMMARY' or history.get('native_run_body_verified') is True,
                  **identity)
        check('ACTUAL_HISTORY_PROBLEM', isinstance(history.get('messages'), list) and not history['messages'],
              problem=bool(history.get('messages')), messages=history.get('messages'), **identity)
        history_nonzero = history.get('summary', {}).get('nonzero_cells')
        check('NONZERO_HISTORY_SUMMARY', not history_nonzero, problem=bool(history_nonzero), **identity)

    source_verified = (summary.get('source_verified_schema') is True
                       and summary.get('acceptance_eligible') is True
                       and summary.get('native_schema') == VERIFIED_NATIVE_SCHEMA)
    summary_zero = (summary.get('found') is True and summary.get('complete') is True
                    and summary.get('valid_schema') is True and summary.get('all_zero') is True
                    and summary.get('total') == 0 and not summary.get('diagnostics'))
    summary_diagnostics = summary.get('diagnostics', [])
    if mode is not None:
        check('SUMMARY_OBSERVATION_UNVERIFIED',
              summary.get('schema_version') == SCHEMA_VERSION and type(summary.get('found')) is bool)
        counts = summary.get('counts')
        summary_zero = (summary_zero and summary.get('columns') == list(NATIVE_THREE_COLUMNS)
                        and isinstance(counts, dict) and set(counts) == set(ROWS)
                        and all(isinstance(row, list) and len(row) == len(NATIVE_THREE_COLUMNS)
                                and all(type(value) is int and value == 0 for value in row)
                                for row in counts.values()))
    conflict = any(row['code'] in {'CONFLICTING_SUMMARIES', 'MIXED_SUMMARY_SCHEMAS',
                                   'CLEAN_STATEMENT_CONFLICTS_WITH_COUNTS', 'DUPLICATE_ROW', 'DUPLICATE_HEADER'}
                   for row in summary_diagnostics)
    nonzero = bool(summary.get('nonzero_cells'))
    counts_status = ('conflicting' if conflict else 'nonzero' if nonzero else
                     'all_zero' if source_verified and summary_zero else 'unknown')
    check('NONZERO_CONTROL_SUMMARY', not nonzero, problem=nonzero, cells=summary.get('nonzero_cells', []))
    check('CONFLICTING_CONTROL_SUMMARY', not conflict, diagnostics=summary_diagnostics if conflict else [])
    if summary.get('found') is True:
        check('SUMMARY_SCHEMA_NOT_SOURCE_VERIFIED', source_verified,
              profile=summary.get('profile'), native_schema=summary.get('native_schema'))
        check('SUMMARY_INCOMPLETE_OR_NONZERO', summary_zero, diagnostics=summary_diagnostics)

    # Preserve the old meaning of simulation_clean for callers that omit mode.
    legacy_simulation_clean = all(gate['passed'] for gate in gates) and source_verified and summary_zero
    if mode is not None:
        expected = [name.casefold() for name in expected_blocks or [] if isinstance(name, str) and name]
        observed = [row['block'].casefold() for row in block_statuses or []
                    if isinstance(row.get('block'), str) and row['block']]
        check('BLOCK_INVENTORY_UNVERIFIED',
              bool(expected) and len(expected) == len(expected_blocks or []) == len(set(expected))
              and len(observed) == len(block_statuses or []) == len(set(observed))
              and set(expected) == set(observed), expected=expected_blocks, observed=observed)
        roles = [item.get('role') for item in artifacts or []]
        check('REQUIRED_ARTIFACTS_UNVERIFIED', len(roles) == 2 and set(roles) == {'input_export', 'backup_export'}, roles=roles)
    for row in block_statuses or []:
        value = row.get('blkstat')
        try:
            number = float(value)
            numeric = not isinstance(value, bool) and math.isfinite(number)
        except (TypeError, ValueError, OverflowError):
            numeric = False
        check('BLOCK_STATUS_NONZERO_OR_UNKNOWN', numeric and number == 0,
              problem=numeric and number != 0, block=row.get('block'), observed=value)
        messages = find_hard_messages(str(row.get('blkmsg') or ''))
        if messages:
            check('ACTUAL_BLOCK_PROBLEM', False, problem=True, block=row.get('block'), messages=messages)
    for item in artifacts or []:
        size = item.get('size', item.get('size_bytes'))
        valid = (item.get('exists') is True and isinstance(size, (int, float)) and size > 0
                 and bool(_HASH.fullmatch(str(item.get('sha256', '')))))
        if mode is not None:
            valid = valid and associated(item.get('association'))
        check('ARTIFACT_MISSING_EMPTY_OR_UNHASHED', valid, path=item.get('path'))

    normal_passed = all(gate['passed'] for gate in gates)
    if mode != 'run' and summary.get('found') is not True:
        check('SUMMARY_SCHEMA_NOT_SOURCE_VERIFIED', source_verified,
              profile=summary.get('profile'), native_schema=summary.get('native_schema'))
        check('SUMMARY_INCOMPLETE_OR_NONZERO', summary_zero, diagnostics=summary_diagnostics)
    strict_solver_passed = normal_passed and source_verified and summary_zero
    passed = normal_passed if mode == 'run' else strict_solver_passed
    actual_problem = any(gate['actual_problem'] for gate in gates)
    assessment = 'PASS' if normal_passed else 'FAIL' if actual_problem else 'UNKNOWN'
    return {'schema_version': 'aspen_clean_gate/2' if mode is None else 'aspen_clean_gate/3',
            'mode': mode or 'strict',
            'passed': passed, 'simulation_assessment': assessment,
            'simulation_clean': legacy_simulation_clean if mode is None else normal_passed,
            'summary_counts_status': counts_status, 'strict_solver_passed': strict_solver_passed,
            'delivery_verified': False, 'precision_lock_verified': False,
            'gate_status': 'PASS' if passed else 'FAIL' if actual_problem or mode is None else 'UNKNOWN',
            'gate_results': gates, 'rejection_reasons': [gate for gate in gates if not gate['passed']],
            'boundary': 'Solver evidence only. Engineering targets, exact delivery identity, and solver-tolerance preservation require separate evidence.'}


def replay_audit_evidence(native: dict[str, Any], *, root: Path) -> dict[str, Any]:
    """Recheck a supervised v3 receipt against its worker report and native artifacts."""
    def require(condition: bool, message: str) -> None:
        if not condition:
            raise ValueError(message)

    def read_ref(ref: dict[str, Any]) -> bytes:
        raw = (root / ref['path']).read_bytes()
        require(bool(raw) and hashlib.sha256(raw).hexdigest().upper() == ref['sha256'].upper(),
                f"Artifact is empty or its digest changed: {ref['path']}")
        if 'size' in ref:
            require(type(ref['size']) is int and ref['size'] == len(raw), 'Artifact size mismatch')
        return raw

    try:
        require(native['schema_version'] == 'aspen_clean_delivery_audit/3', 'Unsupported native receipt')
        supervisor = native['supervisor']
        stage = supervisor['last_stage']
        process = supervisor['owned_worker']
        require(process['verified'] is True and stage['process_identity'] == process
                and stage['pid'] == process['pid'] and supervisor['run_id'] == stage['run_id'],
                'Worker process identity mismatch')
        closeout = stage['closeout']
        worker_ref = native['worker_summary']
        require(supervisor['status'] == 'completed' and supervisor['lifecycle_clean'] is True
                and supervisor['audit_closeout_verified'] is True and supervisor['forced_termination'] is False
                and stage['phase'] == 'finished' and stage['lifecycle_clean'] is True,
                'Supervised worker closeout is missing or incomplete')
        require(worker_ref['sha256'] == closeout['summary_sha256']
                and (root / worker_ref['path']).resolve() == (root / closeout['summary_path']).resolve(),
                'Unexpected worker evidence path or digest')
        worker = json.loads(read_ref(worker_ref))
        require(all(native.get(k) == v for k, v in worker.items()),
                'Published report differs from the closed worker report')
        require(type(worker['passed']) is bool and worker['operation_completed'] is True
                and worker['lifecycle']['closed_cleanly'] is True and not worker.get('error')
                and not worker.get('traceback'), 'Incomplete worker lifecycle')
        outcome = 'audit_accepted' if worker['passed'] else 'audit_rejected'
        require(supervisor['worker_outcome'] == stage['worker_outcome'] == outcome
                and supervisor['worker_exit_code'] == (0 if worker['passed'] else 1)
                and closeout['passed'] is worker['passed'], 'Worker result disagrees with closeout')
        mode, run = worker['mode'], worker['run']
        require(mode in ('run', 'strict') and mode == closeout['mode']
                and run['run_id'] == worker['run_id'] == closeout['run_id'] == stage['run_id'],
                'Run identity or mode mismatch')
        digest = worker['source_sha256']
        require(digest == closeout['source_sha256'] and worker['source_unchanged'] is True
                and worker['source_after_run']['sha256'] == digest and worker['opened_candidate_unchanged'] is True
                and run['case_sha256'] == worker['opened_candidate_before']['sha256']
                == worker['opened_candidate_after']['sha256'] == worker.get('embedded_model_sha256', digest),
                'Opened model identity mismatch')
        read_ref({'path': worker['source'], 'sha256': digest})
        inventory = worker['expected_block_inventory']
        require(inventory['verified'] is True and inventory['blocks'] == worker['expected_blocks']
                and inventory['path'] == r'\Data\Blocks', 'Unverified native block inventory')

        control = worker['control_panel']
        control_text = read_ref(control).decode('utf-8')
        raw_events = json.loads(read_ref(control['raw_events']))
        require(raw_events['run_id'] == run['run_id'] and raw_events['case_sha256'] == run['case_sha256'],
                'Control event identity mismatch')
        capture = inspect_control_events(raw_events['events'], run, control['final_drain'])
        require(capture['text'] == control_text, 'Control text differs from original events')
        summary = parse_summary_counts(control_text)
        association = dict(control['association'], capture_complete=capture['capture_complete'],
                           terminal_verified=inspect_control_terminal(control_text, summary)['verified'])
        observed_histories = []
        current = {entry['path'] for entry in worker['sidecars']
                   if Path(entry['path']).suffix.casefold() == '.his'
                   and entry['evidence_role'] != 'stale_excluded'}
        require(current and current == {item['path'] for item in worker['histories']},
                'Current history inventory mismatch')
        for item in worker['histories']:
            raw = read_ref(item)
            assoc = item['association']
            after = assoc['after']
            before = worker['pre_run_sidecar_snapshot'].get(assoc['source_path'])
            require(before == assoc['before'] and (before is None or before['sha256'] != after['sha256'])
                    and after['sha256'] == item['sha256'] and after['size'] == len(raw)
                    and after['mtime_ns'] / 1e9 >= run['started_epoch'] - 2,
                    'History is stale or has inconsistent capture records')
            proof = item.get('encoding_evidence', {})
            fallback = ()
            if (proof.get('fallback_eligible_for_current_history') is True
                    and proof.get('fallback_roundtrip_verified') is True
                    and proof.get('history_sha256') == item['sha256'] and proof.get('verified') is True
                    and proof.get('source') == 'Windows kernel32.GetACP' and proof.get('run_id') == run['run_id']
                    and proof.get('case_sha256') == run['case_sha256'] and type(proof.get('acp')) is int
                    and proof.get('codec') == 'cp' + str(proof['acp'])):
                fallback = (proof['codec'],)
            decoded = decode_history_bytes(raw, verified_fallback_encodings=fallback)
            if decoded['verified'] and decoded['encoding'] in fallback:
                require(decoded['text'].encode(decoded['encoding'], errors='strict') == raw,
                        'Native code-page round trip changed history bytes')
            inspection = inspect_history_text(decoded.get('text') or '', source=item['path'], source_sha256=item['sha256'])
            observed_histories.append({**item, **inspection, 'decode_verified': decoded['verified']})
        exports = [worker['after_run_inp'], worker['after_run_bkp']]
        for item in exports:
            read_ref(item)
        return evaluate_clean_gate(run=run, summary=summary, control_messages=find_hard_messages(control_text),
                                   control_association=association, histories=observed_histories,
                                   block_statuses=worker['block_statuses'], expected_blocks=inventory['blocks'],
                                   artifacts=exports, mode=mode)
    except (OSError, UnicodeError, ValueError, KeyError, IndexError, TypeError, AttributeError, OverflowError) as exc:
        return {'passed': False, 'simulation_clean': False, 'strict_solver_passed': False,
                'simulation_assessment': 'UNKNOWN', 'summary_counts_status': 'unknown',
                'rejection_reasons': [{'code': 'RAW_AUDIT_EVIDENCE_INVALID', 'detail': str(exc)}]}
