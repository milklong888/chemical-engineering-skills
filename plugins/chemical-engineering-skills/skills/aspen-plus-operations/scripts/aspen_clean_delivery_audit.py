from __future__ import annotations

import argparse
import codecs
import ctypes
import hashlib
import json
import locale
import math
import os
import platform
import re
import shutil
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any
import zipfile
import sys
import uuid

from aspen_evidence import (HARD_PATTERNS, decode_history_bytes, evaluate_clean_gate,
                            find_hard_messages, hard_pattern_counts, inspect_control_events, inspect_control_terminal,
                            inspect_history_text, parse_summary_counts)
import aspen_runtime


_SESSIONS: dict[int, aspen_runtime.AspenSession] = {}


class AspenEvents:
    """Retain all event payloads even if Aspen asks to clear the displayed panel."""

    def OnControlPanelMessage(self, clear: Any, message: Any) -> None:
        self.audit_events.append({'event': 'OnControlPanelMessage', 'epoch': time.time(),
                                  'clear': clear, 'message': message})

    def OnCalculationCompleted(self) -> None:
        self.audit_events.append({'event': 'OnCalculationCompleted', 'epoch': time.time()})


def drain_events(session: aspen_runtime.AspenSession, events: list[dict[str, Any]], *,
                 quiet_s: float, timeout_s: float) -> dict[str, Any]:
    started = last_change = time.monotonic()
    initial_count = observed_count = len(events)
    try:
        while True:
            if session.pythoncom.PumpWaitingMessages():
                raise RuntimeError('COM event pump received WM_QUIT')
            now_monotonic = time.monotonic()
            if len(events) != observed_count:
                last_change, observed_count = now_monotonic, len(events)
            quiet = now_monotonic - last_change >= quiet_s
            if quiet or now_monotonic - started >= timeout_s:
                return {'completed': quiet, 'quiet_s': quiet_s, 'elapsed_s': now_monotonic - started,
                        'event_count': len(events), 'events_added': len(events) - initial_count}
            time.sleep(.05)
    except Exception as exc:
        return {'completed': False, 'error': str(exc), 'event_count': len(events)}


def capture_control_panel(out: Path, label: str, events: list[dict[str, Any]], *,
                          run: dict[str, Any], final_drain: dict[str, Any]) -> dict[str, Any]:
    raw_path = out / f'{label}_control_panel_events.json'
    aspen_runtime.atomic_json(raw_path, {'run_id': run.get('run_id'), 'case_sha256': run.get('case_sha256'),
                                        'events': events})
    control_path = out / f'{label}_control_panel.txt'
    capture = inspect_control_events(events, run, final_drain)
    text = capture.pop('text')
    with control_path.open('x', encoding='utf-8', newline='') as handle:
        handle.write(text)
    counts = parse_summary_counts(text)
    terminal = inspect_control_terminal(text, counts)
    control_artifact = artifact(control_path)
    return {**control_artifact, 'raw_events': artifact(raw_path), **capture,
            'summary_counts': counts, 'hard_pattern_counts': hard_pattern_counts(text),
            'actual_messages': find_hard_messages(text, source=str(control_path), source_sha256=control_artifact['sha256']),
            'terminal': terminal, 'final_drain': final_drain,
            'association': {'verified': run.get('events_cleared_before_run') is True,
                            'run_id': run.get('run_id'), 'case_sha256': run.get('case_sha256'),
                            'capture_complete': capture['capture_complete'], 'terminal_verified': terminal['verified']}}


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def artifact(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() else None,
        "sha256": sha256(path),
    }


def _windows_ansi_code_page() -> int:
    """Read the native ANSI page, not Python UTF-8 mode or console encoding."""
    if os.name != 'nt':
        raise OSError('Windows GetACP is unavailable on this platform')
    get_acp = ctypes.WinDLL('kernel32', use_last_error=True).GetACP
    get_acp.argtypes = []
    get_acp.restype = ctypes.c_uint
    return int(get_acp())


def capture_history_encoding_evidence(*, run_id: str, case_sha256: str,
                                      progid: str) -> dict[str, Any]:
    """Caller-owned platform evidence; the shared parser remains platform-free."""
    record: dict[str, Any] = {
        'schema': 'aspen-native-history-encoding-evidence-v1',
        'source': 'Windows kernel32.GetACP', 'captured_epoch': time.time(),
        'run_id': run_id, 'case_sha256': case_sha256, 'progid': progid,
        'platform': platform.system(), 'os_version': platform.version(),
        'python_version': platform.python_version(), 'python_utf8_mode': sys.flags.utf8_mode,
        'locale_ctype': locale.setlocale(locale.LC_CTYPE),
        'locale_encoding': locale.getencoding(),
        'python_preferred_encoding': locale.getpreferredencoding(False),
        'acp': None, 'codec': None, 'verified': False, 'issues': [],
        'scope': 'Fallback only for hash-matched fresh history associated with this local run; no universal encoding guess.',
    }
    try:
        acp = _windows_ansi_code_page()
        record['acp'] = acp
        if not isinstance(acp, int) or isinstance(acp, bool) or acp <= 0:
            raise ValueError('GetACP did not return a positive code page')
        codec = 'cp' + str(acp)
        canonical = codecs.lookup(codec).name
        if canonical in {'iso8859-1', 'latin-1'}:
            raise ValueError('Universal Latin-1 fallback is forbidden')
        record.update(codec=codec, canonical_codec=canonical, verified=True)
    except (OSError, ValueError, LookupError, AttributeError) as exc:
        record['issues'].append({'code': 'NATIVE_ACP_UNVERIFIED', 'error': str(exc)})
    return record


def decode_current_history(data: bytes, *, sidecar: dict[str, Any], run: dict[str, Any],
                           encoding_evidence: dict[str, Any]) -> dict[str, Any]:
    """BOM/UTF-8 first; explicit native fallback requires current-run identity."""
    digest = hashlib.sha256(data).hexdigest().upper()
    association = sidecar.get('association', {})

    def same_identity(record: dict[str, Any]) -> bool:
        return bool(run.get('run_id') and run.get('case_sha256')
                    and record.get('run_id') == run['run_id']
                    and str(record.get('case_sha256', '')).upper() == str(run['case_sha256']).upper())

    eligible = bool(encoding_evidence.get('verified') is True
                    and encoding_evidence.get('source') == 'Windows kernel32.GetACP'
                    and same_identity(encoding_evidence)
                    and association.get('verified') is True and same_identity(association)
                    and sidecar.get('evidence_role') == 'current_run_candidate'
                    and sidecar.get('new_or_changed') is True
                    and str(sidecar.get('sha256', '')).upper() == digest
                    and sidecar.get('size') == len(data))
    # A caller may not substitute an unrelated codec into the ACP receipt.
    expected_codec = 'cp' + str(encoding_evidence.get('acp'))
    eligible = eligible and encoding_evidence.get('codec') == expected_codec
    fallback = (expected_codec,) if eligible else ()
    decoded = decode_history_bytes(data, verified_fallback_encodings=fallback)
    used = decoded.get('verified') is True and decoded.get('encoding') in fallback
    roundtrip = False
    if used:
        try:
            roundtrip = decoded['text'].encode(decoded['encoding'], errors='strict') == data
        except (UnicodeError, LookupError):
            roundtrip = False
        if not roundtrip:
            decoded.update(verified=False, text=None)
            decoded['issues'].append({'code': 'NATIVE_FALLBACK_ROUNDTRIP_FAILED'})
    decoded['encoding_evidence'] = {
        **encoding_evidence, 'history_sha256': digest,
        'fallback_eligible_for_current_history': eligible, 'fallback_used': used,
        'fallback_roundtrip_verified': roundtrip,
        'decode_order': 'BOM / UTF-8 first, then identity-bound native ACP; strict only',
    }
    return decoded


def create_aspen(progid: str = 'Apwn.Document.40.0') -> tuple[Any, str]:
    session = aspen_runtime.create_session(progid)
    _SESSIONS[id(session.app)] = session
    return session.app, session.prog_id


def open_case(app: Any, source: Path) -> tuple[str, list[str]]:
    result = aspen_runtime.open_case(_SESSIONS[id(app)], source)
    return result['method'], []


def export_file(app: Any, export_type: int, path: Path) -> dict[str, Any]:
    return aspen_runtime.export_case(_SESSIONS[id(app)], export_type, path)


def run_async(app: Any, timeout_s: int, *, run_id: str, case_sha256: str,
              events: list[dict[str, Any]]) -> dict[str, Any]:
    session = _SESSIONS[id(app)]
    pre_run_drain = drain_events(session, events, quiet_s=.2, timeout_s=3)
    if not pre_run_drain['completed']:
        return {'status': 'event_capture_error', 'run_id': run_id, 'case_sha256': case_sha256,
                'pre_run_event_drain': pre_run_drain, 'events_cleared_before_run': False}
    events.clear()
    result = aspen_runtime.run_case(
        session, timeout_s=timeout_s, run_id=run_id, case_sha256=case_sha256,
        completion_observed=lambda: any(event['event'] == 'OnCalculationCompleted' for event in events))
    return {**result, 'events_cleared_before_run': True, 'pre_run_event_drain': pre_run_drain}


def capture_expected_blocks(app: Any) -> dict[str, Any]:
    """Take the physical block inventory from the opened model before dispatch."""
    path = r'\Data\Blocks'
    try:
        node = app.Tree.FindNode(path)
        if node is None:
            return {'path': path, 'verified': False, 'blocks': [], 'reason': 'NATIVE_BLOCK_ROOT_MISSING'}
        names = [child.Name for child in node.Elements]
        valid = all(isinstance(name, str) and name.strip() and name == name.strip() for name in names)
        verified = bool(names) and valid and len({name.casefold() for name in names}) == len(names)
        return {'path': path, 'verified': verified, 'blocks': names if valid else []}
    except Exception as exc:
        return {'path': path, 'verified': False, 'blocks': [], 'error': str(exc)}


def node_value(app: Any, path: str) -> Any:
    try:
        node = app.Tree.FindNode(path)
        return None if node is None else node.Value
    except Exception:
        return None


def block_statuses(app: Any, blocks: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    bad: list[dict[str, Any]] = []
    for block in blocks:
        status = node_value(app, rf"\Data\Blocks\{block}\Output\BLKSTAT")
        message = str(node_value(app, rf"\Data\Blocks\{block}\Output\BLKMSG") or "").strip()
        row = {"block": block, "blkstat": status, "blkmsg": message}
        rows.append(row)
        try:
            is_bad = isinstance(status, bool) or not math.isfinite(float(status)) or float(status) != 0.0
        except (TypeError, ValueError, OverflowError):
            is_bad = True
        if isinstance(status, float) and not math.isfinite(status):
            row['blkstat'] = repr(status)
        if is_bad:
            bad.append(row)
    return rows, bad


def capture_run_status_tree(app: Any, *, max_nodes: int = 256, max_depth: int = 5) -> dict[str, Any]:
    """Read raw, version-specific nodes only; never synthesize a count matrix."""
    root_path = r'\Data\Results Summary\Run-Status\Output'
    rows: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    try:
        root = app.Tree.FindNode(root_path)
        if root is None:
            return {'status': 'NODE_MISSING', 'root_path': root_path, 'rows': [], 'count_mapping_verified': False}
        def visit(node: Any, path: str, depth: int) -> None:
            if len(rows) >= max_nodes:
                issues.append({'code': 'NODE_LIMIT_REACHED', 'path': path})
                return
            row: dict[str, Any] = {'path': path, 'depth': depth}
            for attribute in ('Name', 'Value', 'UnitString'):
                try:
                    value = getattr(node, attribute)
                    if value is None or isinstance(value, (str, int, bool)):
                        row[attribute] = value
                    elif isinstance(value, float):
                        row[attribute] = value if value == value and abs(value) != float('inf') else repr(value)
                    else:
                        row[attribute] = repr(value)
                        row[attribute + '_representation'] = 'repr_non_json_value'
                except Exception as exc:
                    row[attribute + '_error'] = str(exc)
            rows.append(row)
            if depth >= max_depth:
                row['children_not_expanded_at_depth_limit'] = True
                return
            try:
                for child in node.Elements:
                    try:
                        name = str(child.Name)
                    except Exception:
                        name = '<unreadable-name>'
                    visit(child, path + '\\' + name, depth + 1)
                    if len(rows) >= max_nodes:
                        break
            except Exception as exc:
                row['children_error'] = str(exc)
        visit(root, root_path, 0)
    except Exception as exc:
        issues.append({'code': 'READ_ONLY_TREE_CAPTURE_FAILED', 'error': str(exc)})
    return {'schema': 'aspen-raw-run-status-tree-v1', 'status': 'CAPTURED_RAW' if rows else 'UNAVAILABLE',
            'root_path': root_path, 'rows': rows, 'issues': issues, 'count_mapping_verified': False,
            'boundary': 'Raw diagnostic values and labels only. These nodes do not supply absent matrix cells without a separately verified native schema mapping.'}


def snapshot_sidecars(work: Path) -> dict[str, dict[str, Any]]:
    return {str(path.resolve()): {**artifact(path), 'mtime_ns': path.stat().st_mtime_ns}
            for path in work.rglob('*') if path.is_file() and not path.is_symlink()
            and path.suffix.lower() in {'.his', '.sum', '.rep', '.out', '.err'}}


def copy_sidecars(work: Path, out: Path, started: float, *,
                  before: dict[str, dict[str, Any]] | None = None,
                  run: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Capture owned-tree deltas before closing; old same-content logs stay stale."""
    rows: list[dict[str, Any]] = []
    side_dir = out / "sidecars"
    side_dir.mkdir(parents=True, exist_ok=True)
    current = snapshot_sidecars(work)
    for key, metadata in current.items():
        source = Path(key)
        old = (before or {}).get(key)
        changed = old is None or old.get('sha256') != metadata.get('sha256')
        relative = source.relative_to(work.resolve())
        target = side_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError(f'History capture would overwrite evidence: {target}')
        shutil.copy2(source, target)
        captured = artifact(target)
        unchanged_during_capture = captured['sha256'] == metadata['sha256'] == sha256(source)
        fresh_time = metadata['mtime_ns'] / 1e9 >= started - 2.0
        verified = before is not None and bool(run) and changed and fresh_time and unchanged_during_capture
        association = {'verified': verified, 'run_id': (run or {}).get('run_id'),
                       'case_sha256': (run or {}).get('case_sha256'),
                       'reason': 'EXCLUSIVE_NEW_WORKTREE_CURRENT_SESSION_SNAPSHOT_DELTA' if verified else 'OLD_UNCHANGED_OR_UNBOUND_HISTORY',
                       'source_path': str(source), 'owned_worktree': str(work.resolve()),
                       'before': old, 'after': metadata, 'new_or_changed': changed,
                       'fresh_time': fresh_time, 'unchanged_during_capture': unchanged_during_capture}
        rows.append({**captured, 'original_path': str(source), 'mtime_ns': metadata['mtime_ns'],
                     'new_or_changed': changed, 'association': association,
                     'evidence_role': 'current_run_candidate' if changed else 'stale_excluded'})
    return rows


def extract_compound(source: Path, work: Path) -> tuple[Path, list[dict[str, Any]]]:
    members: list[dict[str, Any]] = []
    work_root = work.resolve()
    with zipfile.ZipFile(source, "r") as archive:
        for info in archive.infolist():
            relative = Path(info.filename.replace("\\", "/"))
            if relative.is_absolute() or ".." in relative.parts:
                raise RuntimeError(f"Unsafe APWZ member path: {info.filename}")
            target = (work / relative).resolve()
            try:
                target.relative_to(work_root)
            except ValueError as exc:
                raise RuntimeError(f"APWZ member escapes extraction root: {info.filename}") from exc
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as source_handle, target.open("wb") as target_handle:
                shutil.copyfileobj(source_handle, target_handle)
            members.append(
                {
                    "name": info.filename,
                    "extracted": str(target),
                    "size": target.stat().st_size,
                    "sha256": sha256(target),
                }
            )

    candidates = sorted(
        path
        for path in work.rglob("*")
        if path.is_file() and path.suffix.lower() in {".bkp", ".apw"}
    )
    if not candidates:
        raise RuntimeError("APWZ contains no .bkp or .apw model member")
    preferred = [path for path in candidates if path.stem.lower() == source.stem.lower()]
    if len(preferred) == 1:
        model = preferred[0]
    elif len(candidates) == 1:
        model = candidates[0]
    else:
        names = ", ".join(str(path.relative_to(work)) for path in candidates)
        raise RuntimeError(f"APWZ model member is ambiguous: {names}")
    return model, members


def close_aspen(app: Any | None) -> dict[str, Any]:
    if app is None:
        return {'status': 'not_created', 'closed_cleanly': True, 'attempts': []}
    session = _SESSIONS.pop(id(app), None)
    if session is None:
        return {'status': 'ownership_unknown', 'closed_cleanly': False, 'attempts': []}
    return aspen_runtime.close_session(session)


def run_completed(run: dict[str, Any]) -> bool:
    return (run.get('status') == 'completed' and not run.get('forced_termination')
            and run.get('completion_event_observed') is True and run.get('terminal_engine_idle') is True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--label", default="AUDIT01")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument('--progid', default='Apwn.Document.40.0', help='Exact requested Aspen COM ProgID; no silent version fallback.')
    parser.add_argument('--mode', choices=('run', 'strict'), default='run',
                        help='Assess the completed simulation, or also require proof of every native summary count.')
    parser.add_argument('--_worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--_worker-summary', type=Path, help=argparse.SUPPRESS)
    parser.add_argument(
        "--sidecar",
        action="append",
        default=[],
        help="Additional file copied beside the staged BKP before open; repeat as needed.",
    )
    parser.add_argument(
        "--open-source-direct",
        action="store_true",
        help="Open the source path directly while keeping Aspen's working directory isolated.",
    )
    args = parser.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9_-]{1,24}", args.label):
        raise SystemExit("--label must be 1-24 ASCII letters, digits, '_' or '-'")

    source = Path(args.source).resolve()
    if source.suffix.lower() not in {".bkp", ".inp", ".apw", ".apwz"}:
        raise SystemExit("This audit supports .bkp, .inp, .apw, and .apwz")
    out = Path(args.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    summary_path = out / f'{args.label}_summary.json'
    if args._worker_summary is not None and not args._worker:
        raise SystemExit('The worker summary path is internal.')
    planned_outputs = [summary_path, out / f'{args.label}_control_panel.txt',
                       out / f'{args.label}_after_run.inp', out / f'{args.label}_after_run.bkp',
                       out / f'{args.label}_run_status_tree.json', out / f'{args.label}_control_panel_events.json']
    if args._worker_summary is not None:
        planned_outputs.append(args._worker_summary)
    conflicts = [str(path) for path in planned_outputs if path.exists() or path.resolve() == source]
    if conflicts:
        print(json.dumps({'passed': False, 'summary': str(summary_path), 'error': 'Existing input/output evidence is immutable; choose another label or output directory.', 'conflicts': conflicts}))
        return 1
    if not args._worker:
        from aspen_run_supervisor import run_worker
        requested_source_sha256 = sha256(source)
        run_dir = out / f'{args.label}_supervision_{uuid.uuid4().hex}'
        worker_summary_path = run_dir / 'worker_summary.json'
        command = [sys.executable, '-B', '-X', 'utf8', str(Path(__file__).resolve()), '--_worker',
                   '--source', str(source), '--out-dir', str(out), '--label', args.label,
                   '--timeout', str(args.timeout), '--progid', args.progid, '--mode', args.mode,
                   '--_worker-summary', str(worker_summary_path)]
        for item in args.sidecar:
            command.extend(['--sidecar', str(Path(item).resolve())])
        if args.open_source_direct:
            command.append('--open-source-direct')
        supervisor = run_worker(command, run_dir=run_dir, stage_timeouts={'running': args.timeout + 5.0, 'assessing': 90.0},
                                overall_timeout_s=args.timeout + 300.0, audit_summary_path=worker_summary_path)
        worker_summary = artifact(worker_summary_path)
        try:
            summary = json.loads(worker_summary_path.read_text(encoding='utf-8'))
            if not isinstance(summary, dict):
                raise ValueError('Worker summary is not a JSON object')
        except (OSError, ValueError) as exc:
            summary = {'schema_version': 'aspen_clean_delivery_audit/3', 'source': str(source), 'mode': args.mode,
                       'rejection_reasons': [{'code': 'WORKER_DID_NOT_PRODUCE_READABLE_AUDIT', 'details': str(exc)}]}
        receipt = (supervisor.get('last_stage') or {}).get('closeout') or {}
        operation_completed = bool(
            summary.get('operation_completed') is True and supervisor.get('status') == 'completed'
            and supervisor.get('audit_closeout_verified') is True and supervisor.get('lifecycle_clean') is True
            and not supervisor.get('forced_termination') and summary.get('mode') == args.mode
            and summary.get('run_id') == receipt.get('run_id') and worker_summary['sha256'] == receipt.get('summary_sha256')
            and requested_source_sha256 and summary.get('source_sha256') == requested_source_sha256)
        summary['worker_summary'] = worker_summary
        summary['supervisor'] = supervisor
        summary['operation_completed'] = operation_completed
        summary['passed'] = bool(summary.get('passed') and operation_completed)
        if not operation_completed:
            summary.update(simulation_clean=False, simulation_assessment='UNKNOWN',
                           summary_counts_status='unknown', strict_solver_passed=False)
            summary.setdefault('rejection_reasons', []).append({'code': 'SUPERVISED_AUDIT_COMPLETION_UNVERIFIED'})
        summary['delivery_verified'] = False
        summary['precision_lock_verified'] = False
        aspen_runtime.atomic_json(summary_path, summary)
        print(json.dumps({'passed': summary['passed'], 'summary': str(summary_path)}, ensure_ascii=False))
        return 0 if summary['passed'] else 1
    if not os.environ.get('ASPEN_RUNTIME_OWNER_TOKEN'):
        raise SystemExit('Internal worker requires the supervisor ownership token.')
    if args._worker_summary is not None:
        summary_path = args._worker_summary.resolve()
    stages = aspen_runtime.StageRecorder()
    work = Path(tempfile.mkdtemp(prefix=f"AspenAudit_{args.label}_"))
    staged = source if args.open_source_direct else work / f"SOURCE{source.suffix.lower()}"
    summary: dict[str, Any] = {
        'schema_version': 'aspen_clean_delivery_audit/3',
        'run_id': stages.run_id,
        'mode': args.mode,
        "started": now(),
        "source": str(source),
        "source_sha256": sha256(source),
        "work_dir": str(work),
        "label": args.label,
        "open_source_direct": args.open_source_direct,
        'delivery_verified': False,
        'precision_lock_verified': False,
        'simulation_clean': False,
        'simulation_assessment': 'UNKNOWN',
        'summary_counts_status': 'unknown',
        'strict_solver_passed': False,
        'verification_scope': 'EXACT_CANDIDATE_SOLVER_EVIDENCE',
        'parser': artifact(Path(__file__).with_name('aspen_evidence.py')),
    }
    app = None
    event_handler = None
    events: list[dict[str, Any]] = []
    final_drain: dict[str, Any] = {}
    lifecycle = None
    creation_attempted = False
    original_cwd = Path.cwd()
    old_environment = {key: os.environ.get(key) for key in ('TEMP', 'TMP')}
    try:
        if not source.exists():
            raise FileNotFoundError(source)
        if source.suffix.lower() == ".apwz":
            staged, compound_members = extract_compound(source, work)
            summary["apwz_open_strategy"] = "safe_extract_exact_package_then_open_embedded_model"
            summary["compound_members"] = compound_members
            summary["embedded_model"] = str(staged)
            summary["embedded_model_sha256"] = sha256(staged)
        elif not args.open_source_direct:
            shutil.copy2(source, staged)
        staged_sidecars: list[dict[str, Any]] = []
        for raw_sidecar in args.sidecar:
            sidecar = Path(raw_sidecar).resolve()
            if not sidecar.is_file():
                raise FileNotFoundError(f"Sidecar file is missing: {sidecar}")
            direct_sidecar = args.open_source_direct and source.suffix.lower() != ".apwz"
            target = sidecar if direct_sidecar else staged.parent / sidecar.name
            if not direct_sidecar:
                if target.exists() and sha256(sidecar) != sha256(target):
                    raise FileExistsError(f'Sidecar would overwrite a different staged input: {target}')
                if not target.exists():
                    shutil.copy2(sidecar, target)
            staged_sidecars.append(
                {
                    "source": str(sidecar),
                    "staged": str(target),
                    "sha256": sha256(target),
                }
            )
        summary["staged_sidecars"] = staged_sidecars
        working_dir = work if args.open_source_direct else staged.parent
        os.chdir(working_dir)
        os.environ["TEMP"] = str(working_dir)
        os.environ["TMP"] = str(working_dir)

        import win32com.client as win32
        stages.update('creating_com')
        creation_attempted = True
        app, progid = create_aspen(args.progid)
        summary["progid"] = progid
        summary['session'] = _SESSIONS[id(app)].metadata
        summary['opened_candidate_before'] = artifact(staged)
        case_hash = summary['opened_candidate_before']['sha256']
        expected_case_hash = summary.get('embedded_model_sha256', summary['source_sha256'])
        if not case_hash or case_hash != expected_case_hash:
            raise RuntimeError('Staged candidate hash differs from source identity')
        stages.update('opening', source=str(staged), case_sha256=case_hash)
        method, open_errors = open_case(app, staged)
        summary["open_method"] = method
        summary["open_errors"] = open_errors
        event_handler = win32.WithEvents(app, AspenEvents)
        event_handler.audit_events = events
        summary["control_panel_event_attach"] = True
        block_inventory = capture_expected_blocks(app)
        summary['expected_block_inventory'] = block_inventory
        summary['expected_blocks'] = block_inventory['blocks'] if block_inventory['verified'] else []
        before_history = snapshot_sidecars(work)
        summary['pre_run_sidecar_snapshot'] = before_history
        if sha256(staged) != case_hash:
            raise RuntimeError('Opened candidate bytes changed before simulation')
        summary['encoding_evidence'] = capture_history_encoding_evidence(
            run_id=stages.run_id, case_sha256=case_hash, progid=progid)
        summary['encoding_evidence']['session_version_readback'] = summary['session'].get('version_readback', {})
        stages.update('running', case_sha256=case_hash)
        summary['run'] = run_async(app, args.timeout, run_id=stages.run_id, case_sha256=case_hash, events=events)
        if not run_completed(summary['run']):
            raise RuntimeError(f"Aspen run completion was unproven: {summary['run'].get('status')}")

        stages.update('exporting')
        tree_snapshot = capture_run_status_tree(app)
        tree_snapshot.update(run_id=stages.run_id, case_sha256=case_hash)
        tree_path = out / f'{args.label}_run_status_tree.json'
        aspen_runtime.atomic_json(tree_path, tree_snapshot)
        summary['raw_run_status_tree'] = {**artifact(tree_path), 'count_mapping_verified': False}
        work_inp = work / f"{args.label}_after_run.inp"
        work_bkp = work / f"{args.label}_after_run.bkp"
        summary["work_after_run_inp"] = export_file(app, 4, work_inp)
        summary["work_after_run_bkp"] = export_file(app, 1, work_bkp)
        out_inp = out / work_inp.name
        out_bkp = out / work_bkp.name
        if work_inp.exists():
            shutil.copy2(work_inp, out_inp)
        if work_bkp.exists():
            shutil.copy2(work_bkp, out_bkp)
        for export_role, suffix, target in (('input_export', 'inp', out_inp), ('backup_export', 'bkp', out_bkp)):
            item = artifact(target)
            exported = summary[f'work_after_run_{suffix}']
            item['role'] = export_role
            item['association'] = {'verified': bool(exported.get('ok') is True and item['sha256']
                                                    and item['sha256'] == exported.get('sha256')),
                                   'run_id': stages.run_id, 'case_sha256': case_hash}
            summary[f'after_run_{suffix}'] = item

        save_as = work / f"{args.label}_post_run.bkp"
        stages.update('saving')
        try:
            if save_as.exists():
                raise FileExistsError(f'Post-run SaveAs would overwrite a staged file: {save_as}')
            app.SaveAs(str(save_as))
            summary["work_save_as"] = {"ok": save_as.exists(), **artifact(save_as)}
        except Exception as exc:
            summary["work_save_as"] = {"ok": False, "error": str(exc)}

        blocks, bad_blocks = block_statuses(app, summary['expected_blocks'])
        final_drain = drain_events(_SESSIONS[id(app)], events, quiet_s=2, timeout_s=10)
        summary['control_panel'] = capture_control_panel(out, args.label, events, run=summary['run'], final_drain=final_drain)
        stages.update('closing')
        lifecycle = close_aspen(app)
        stages.update('assessing')
        sidecars = copy_sidecars(work, out, summary['run']['started_epoch'], before=before_history, run=summary['run'])
        histories = []
        history_counts = {pattern: 0 for pattern in HARD_PATTERNS}
        scanned_hashes: set[str] = set()
        for sidecar in sidecars:
            path = Path(sidecar["path"])
            if path.suffix.lower() != ".his" or sidecar['evidence_role'] == 'stale_excluded':
                continue
            decoded = decode_current_history(path.read_bytes(), sidecar=sidecar, run=summary['run'],
                                             encoding_evidence=summary['encoding_evidence'])
            capture_matches = decoded['sha256'] == sidecar['sha256'] and decoded['size'] == sidecar['size']
            if not capture_matches:
                sidecar['association'] = {**sidecar['association'], 'verified': False,
                                          'reason': 'COPIED_HISTORY_CHANGED_BEFORE_READ'}
            history_text = decoded.get('text') or ''
            inspection = inspect_history_text(history_text, source=str(path), source_sha256=decoded['sha256'])
            history = {**sidecar, **inspection, 'decode_verified': decoded['verified'], 'encoding': decoded['encoding'],
                       'decode_issues': decoded['issues'],
                       'encoding_evidence': decoded['encoding_evidence'],
                       'duplicate_content': decoded['sha256'] in scanned_hashes}
            histories.append(history)
            if history['duplicate_content']:
                continue
            scanned_hashes.add(decoded['sha256'])
            counts = hard_pattern_counts(history_text)
            for pattern, count in counts.items():
                history_counts[pattern] += count

        summary["block_count"] = len(blocks)
        summary["bad_blocks"] = bad_blocks
        summary["block_statuses"] = blocks
        summary["sidecars"] = sidecars
        summary['histories'] = histories
        summary['history_present'] = bool(histories)
        summary['history_file_count'] = len(histories)
        summary['history_hard_pattern_counts'] = history_counts if histories else None
        control = summary['control_panel']
        gate = evaluate_clean_gate(run=summary['run'], summary=control['summary_counts'],
                                   control_messages=control['actual_messages'], control_association=control['association'],
                                   histories=histories, block_statuses=blocks, expected_blocks=summary['expected_blocks'],
                                   artifacts=[summary['after_run_inp'], summary['after_run_bkp']], mode=args.mode)
        summary['clean_gate'] = gate
        for field in ('simulation_clean', 'simulation_assessment', 'summary_counts_status',
                      'strict_solver_passed', 'gate_results', 'rejection_reasons'):
            summary[field] = gate[field]
        summary['source_after_run'] = artifact(source)
        summary['opened_candidate_after'] = artifact(staged)
        summary['source_unchanged'] = summary['source_sha256'] == summary['source_after_run']['sha256']
        summary['opened_candidate_unchanged'] = case_hash == summary['opened_candidate_after']['sha256']
        identity_verified = summary['source_unchanged'] and summary['opened_candidate_unchanged']
        summary['passed'] = gate['passed'] and identity_verified
        if not identity_verified:
            summary.update(simulation_clean=False, simulation_assessment='UNKNOWN',
                           summary_counts_status='unknown', strict_solver_passed=False)
            summary['rejection_reasons'].append({'code': 'SOURCE_OR_OPENED_CANDIDATE_CHANGED_DURING_AUDIT'})
        summary["finished"] = now()
    except Exception as exc:
        summary["passed"] = False
        summary["error"] = str(exc)
        summary["traceback"] = traceback.format_exc()
        summary["finished"] = now()
    finally:
        try:
            if lifecycle is None:
                stages.update('closing')
                if event_handler is not None and 'control_panel' not in summary:
                    try:
                        summary['control_panel'] = capture_control_panel(
                            out, args.label, events, run=summary.get('run', {}), final_drain=final_drain)
                    except Exception as exc:
                        summary['control_capture_error'] = str(exc)
                try:
                    lifecycle = close_aspen(app)
                except Exception as exc:
                    lifecycle = {'closed_cleanly': False, 'error': str(exc)}
        finally:
            os.chdir(original_cwd)
            for key, old in old_environment.items():
                if old is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old
        if creation_attempted and app is None:
            lifecycle.update(closed_cleanly=False, status='COM_CREATION_RESULT_UNPROVEN')
        summary['lifecycle'] = lifecycle
        lifecycle_clean = lifecycle.get('closed_cleanly') is True
        summary['operation_completed'] = bool(run_completed(summary.get('run', {})) and lifecycle_clean
                                              and 'clean_gate' in summary and 'error' not in summary)
        summary['passed'] = bool(summary.get('passed') and summary['operation_completed'])
        summary['strict_solver_passed'] = bool(summary['strict_solver_passed'] and summary['operation_completed'])
        if not lifecycle_clean:
            summary.setdefault('rejection_reasons', []).append({'code': 'LIFECYCLE_NOT_CLEAN', 'details': lifecycle})
        summary['finished'] = now()
        aspen_runtime.atomic_json(summary_path, summary)
        closeout = {}
        if summary['operation_completed']:
            closeout['worker_outcome'] = 'audit_accepted' if summary['passed'] else 'audit_rejected'
            closeout['closeout'] = {'run_id': stages.run_id, 'summary_path': str(summary_path),
                                    'summary_sha256': sha256(summary_path), 'source_sha256': summary['source_sha256'],
                                    'mode': args.mode, 'passed': summary['passed']}
        stages.update('finished', lifecycle_clean=lifecycle_clean, **closeout)

    print(json.dumps({"passed": summary.get("passed"), "summary": str(summary_path)}, ensure_ascii=False))
    return 0 if summary.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
