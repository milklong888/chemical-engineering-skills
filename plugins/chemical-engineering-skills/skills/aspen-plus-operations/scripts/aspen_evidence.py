"""Pure Aspen evidence parsing; no COM, filesystem writes, or policy exemptions.

The user-approved contract requires all four rows and every column of an
allowlisted, source-verified native schema to be present and zero. Success prose
never supplies absent counts. No arbitrary smaller matrix is inferred.
"""
from __future__ import annotations

import codecs
import hashlib
import json
import math
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
    r'\*\s+WARNING', r'WARNING IN THE', r'WARNING WHILE', r'SEVERE ERROR',
    r'ERROR IN THE', r'ERROR WHILE EXECUTING', r'TERMINAL ERROR',
    r'CHECK THE RUN STATUS', r'M-BAL LOOP DID NOT CONVERGE',
    r'ZEROTH ORDER REACTANT NOT PRESENT', r'FAILED TO CONVERGE',
    r'ZERO FEED', r'BLOCK BYPASSED',
]
_TITLE = re.compile(r'^\s*(?:\*{3}\s*)?(?:Summary of Simulation Errors|Summary of Errors)(?:\s*\*{3})?\s*$', re.I)
_ROW = re.compile(r'^\s*(Terminal Errors|Severe Errors|Errors|Warnings)\b(.*)$', re.I)
_CLEAN = re.compile(r'NO ERRORS OR WARNINGS (?:GENERATED|WERE ISSUED)', re.I)
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


def inspect_history_text(text: str, *, source: str = 'history', source_sha256: str | None = None) -> dict[str, Any]:
    """Inspect a captured full file; an unknown/truncated terminal format stays open."""
    summary = parse_summary_counts(text)
    messages = find_hard_messages(text, source=source, source_sha256=source_sha256)
    clean_statement = bool(_CLEAN.search(text))
    complete = bool(text.strip()) and (clean_statement or summary['complete'])
    issues = []
    if not complete:
        issues.append(_issue('HISTORY_TERMINAL_EVIDENCE_MISSING'))
    if summary['found'] and not summary['complete']:
        issues.append(_issue('HISTORY_SUMMARY_INCOMPLETE', diagnostics=summary['diagnostics']))
        complete = False
    if clean_statement and messages:
        issues.append(_issue('CLEAN_STATEMENT_CONFLICTS_WITH_MESSAGES'))
    return {'complete': complete, 'terminal_evidence': 'CLEAN_STATEMENT' if clean_statement else 'COMPLETE_SUMMARY' if summary['complete'] else None,
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
                        artifacts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Strict current-run solver evidence gate; never certifies project delivery."""
    gates = []
    def check(code: str, passed: bool, **details: Any) -> None:
        gates.append({'code': code, 'passed': bool(passed), **details})
    run_id, case_hash = run.get('run_id'), run.get('case_sha256')
    check('RUN_IDENTITY_REQUIRED', bool(run_id) and bool(_HASH.fullmatch(str(case_hash))))
    try:
        timing = math.isfinite(run['started_epoch']) and math.isfinite(run['finished_epoch']) and run['finished_epoch'] >= run['started_epoch']
    except (KeyError, TypeError, ValueError):
        timing = False
    check('RUN_TIME_IDENTITY_REQUIRED', timing)
    check('RUN_NOT_COMPLETED', run.get('status') in {'returned', 'completed'} and not run.get('forced_termination', False), observed=run.get('status'))
    def associated(item: dict[str, Any] | None) -> bool:
        return bool(item and item.get('verified') is True and item.get('run_id') == run_id and str(item.get('case_sha256', '')).upper() == str(case_hash).upper())
    check('CONTROL_ASSOCIATION_UNVERIFIED', associated(control_association))
    check('SUMMARY_SCHEMA_NOT_SOURCE_VERIFIED', summary.get('source_verified_schema') is True
          and summary.get('acceptance_eligible') is True and summary.get('native_schema') == VERIFIED_NATIVE_SCHEMA,
          profile=summary.get('profile'), native_schema=summary.get('native_schema'))
    check('SUMMARY_INCOMPLETE_OR_NONZERO', summary.get('found') is True and summary.get('complete') is True and summary.get('valid_schema') is True and summary.get('all_zero') is True and summary.get('total') == 0 and not summary.get('diagnostics'), diagnostics=summary.get('diagnostics', []))
    check('ACTUAL_CONTROL_PROBLEM', not control_messages, messages=control_messages)
    check('HISTORY_MISSING', bool(histories))
    for index, history in enumerate(histories):
        identity = {'history_index': index, 'path': history.get('path')}
        check('HISTORY_EMPTY_OR_UNHASHED', isinstance(history.get('size'), (int, float)) and history['size'] > 0 and bool(_HASH.fullmatch(str(history.get('sha256', '')))), **identity)
        check('HISTORY_DECODE_UNVERIFIED', history.get('decode_verified') is True, **identity)
        check('HISTORY_INCOMPLETE', history.get('complete') is True, issues=history.get('issues', []), **identity)
        check('HISTORY_ASSOCIATION_UNVERIFIED', associated(history.get('association')), association=history.get('association'), **identity)
        check('ACTUAL_HISTORY_PROBLEM', isinstance(history.get('messages'), list) and not history['messages'], messages=history.get('messages'), **identity)
        # Three-column history summaries are auxiliary evidence only, but any
        # visible nonzero cell still contradicts a claimed clean run.
        check('NONZERO_HISTORY_SUMMARY', not history.get('summary', {}).get('nonzero_cells'), **identity)
    simulation_clean = all(gate['passed'] for gate in gates)
    if block_statuses is not None:
        for row in block_statuses:
            try:
                value = float(row.get('blkstat'))
                valid = math.isfinite(value) and value == 0
            except (TypeError, ValueError):
                valid = False
            check('BLOCK_STATUS_NONZERO_OR_UNKNOWN', valid, block=row.get('block'), observed=row.get('blkstat'))
    if artifacts is not None:
        for item in artifacts:
            size = item.get('size', item.get('size_bytes'))
            check('ARTIFACT_MISSING_EMPTY_OR_UNHASHED', item.get('exists') is True and isinstance(size, (int, float)) and size > 0 and bool(_HASH.fullmatch(str(item.get('sha256', '')))), path=item.get('path'))
    passed = all(gate['passed'] for gate in gates)
    return {'schema_version': 'aspen_clean_gate/2', 'passed': passed, 'simulation_clean': simulation_clean,
            'delivery_verified': False, 'gate_status': 'PASS' if passed else 'FAIL',
            'gate_results': gates, 'rejection_reasons': [gate for gate in gates if not gate['passed']],
            'boundary': 'Solver evidence only. Exact delivery identity, lifecycle and current project engineering targets remain separate required gates.'}
