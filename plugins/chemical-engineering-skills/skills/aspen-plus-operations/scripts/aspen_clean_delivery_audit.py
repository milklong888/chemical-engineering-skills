from __future__ import annotations

import argparse
import codecs
import ctypes
import hashlib
import json
import locale
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
                            find_hard_messages, hard_pattern_counts, inspect_history_text, parse_summary_counts)
import aspen_runtime


MESSAGES: list[str] = []
_SESSIONS: dict[int, aspen_runtime.AspenSession] = {}


class AspenEvents:
    def OnControlPanelMessage(self, *args: Any) -> None:
        for arg in args:
            if isinstance(arg, str) and arg.strip():
                MESSAGES.append(arg.rstrip())


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


def run_async(app: Any, timeout_s: int, *, run_id: str | None = None, case_sha256: str | None = None) -> dict[str, Any]:
    MESSAGES.clear()
    session = _SESSIONS[id(app)]
    result = aspen_runtime.run_case(session, timeout_s=timeout_s, run_id=run_id or uuid.uuid4().hex, case_sha256=case_sha256)
    if result['status'] == 'completed':
        pump_until = time.monotonic() + 2.0
        try:
            while time.monotonic() < pump_until:
                session.pythoncom.PumpWaitingMessages()
                time.sleep(.05)
            result['status'] = 'returned'  # legacy status with stricter evidence
        except Exception as exc:
            result.update(status='state_unknown', event_drain_error=str(exc))
    result['events_cleared_before_run'] = True
    result['finished_epoch'] = time.time()
    return result


def parse_block_ids(inp: Path) -> list[str]:
    if not inp.exists():
        return []
    text = inp.read_text(encoding="utf-8", errors="replace")
    ids: list[str] = []
    for match in re.finditer(r"(?im)^\s*BLOCK\s+([A-Za-z0-9_+\-]+)(?=\s)", text):
        block = match.group(1)
        if block not in ids:
            ids.append(block)
    return ids


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
            is_bad = status is not None and float(status) != 0.0
        except (TypeError, ValueError):
            is_bad = bool(status)
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--label", default="AUDIT01")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument('--progid', default='Apwn.Document.40.0', help='Exact requested Aspen COM ProgID; no silent version fallback.')
    parser.add_argument('--_worker', action='store_true', help=argparse.SUPPRESS)
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
    planned_outputs = [summary_path, out / f'{args.label}_control_panel.txt',
                       out / f'{args.label}_after_run.inp', out / f'{args.label}_after_run.bkp',
                       out / f'{args.label}_run_status_tree.json']
    conflicts = [str(path) for path in planned_outputs if path.exists() or path.resolve() == source]
    if conflicts:
        print(json.dumps({'passed': False, 'summary': str(summary_path), 'error': 'Existing input/output evidence is immutable; choose another label or output directory.', 'conflicts': conflicts}))
        return 1
    if not args._worker:
        from aspen_run_supervisor import run_worker
        command = [sys.executable, '-B', '-X', 'utf8', str(Path(__file__).resolve()), '--_worker',
                   '--source', str(source), '--out-dir', str(out), '--label', args.label,
                   '--timeout', str(args.timeout), '--progid', args.progid]
        for item in args.sidecar:
            command.extend(['--sidecar', str(Path(item).resolve())])
        if args.open_source_direct:
            command.append('--open-source-direct')
        supervisor = run_worker(command, run_dir=out / f'{args.label}_supervision_{uuid.uuid4().hex}',
                                stage_timeouts={'running': args.timeout + 5.0},
                                overall_timeout_s=args.timeout + 300.0)
        summary = json.loads(summary_path.read_text(encoding='utf-8')) if summary_path.is_file() else {
            'schema_version': 'aspen_clean_delivery_audit/2', 'source': str(source), 'passed': False,
            'rejection_reasons': [{'code': 'WORKER_DID_NOT_PRODUCE_AUDIT'}]}
        summary['supervisor'] = supervisor
        summary['passed'] = bool(summary.get('passed') and supervisor.get('status') == 'completed'
                                 and supervisor.get('lifecycle_clean') is True and not supervisor.get('forced_termination'))
        summary['delivery_verified'] = False
        aspen_runtime.atomic_json(summary_path, summary)
        print(json.dumps({'passed': summary['passed'], 'summary': str(summary_path)}, ensure_ascii=False))
        return 0 if summary['passed'] else 1
    if not os.environ.get('ASPEN_RUNTIME_OWNER_TOKEN'):
        raise SystemExit('Internal worker requires the supervisor ownership token.')
    stages = aspen_runtime.StageRecorder()
    started = time.time()
    work = Path(tempfile.mkdtemp(prefix=f"AspenAudit_{args.label}_"))
    staged = source if args.open_source_direct else work / f"SOURCE{source.suffix.lower()}"
    summary: dict[str, Any] = {
        'schema_version': 'aspen_clean_delivery_audit/2',
        'run_id': stages.run_id,
        "started": now(),
        "source": str(source),
        "source_sha256": sha256(source),
        "work_dir": str(work),
        "label": args.label,
        "open_source_direct": args.open_source_direct,
        'delivery_verified': False,
        'verification_scope': 'EXACT_INPUT_COPY_SOLVER_GATE_NOT_PROJECT_DELIVERY',
        'parser': artifact(Path(__file__).with_name('aspen_evidence.py')),
    }
    app = None
    event_handler = None
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
        os.chdir(staged.parent)
        os.environ["TEMP"] = str(staged.parent)
        os.environ["TMP"] = str(staged.parent)

        import win32com.client as win32
        stages.update('creating_com')
        creation_attempted = True
        app, progid = create_aspen(args.progid)
        summary["progid"] = progid
        summary['session'] = _SESSIONS[id(app)].metadata
        summary['opened_candidate_before'] = artifact(staged)
        stages.update('opening', source=str(staged), case_sha256=sha256(staged))
        method, open_errors = open_case(app, staged)
        summary["open_method"] = method
        summary["open_errors"] = open_errors
        event_handler = win32.WithEvents(app, AspenEvents)
        summary["control_panel_event_attach"] = True
        before_history = snapshot_sidecars(work)
        summary['pre_run_sidecar_snapshot'] = before_history
        case_hash = summary['opened_candidate_before']['sha256']
        summary['encoding_evidence'] = capture_history_encoding_evidence(
            run_id=stages.run_id, case_sha256=case_hash, progid=progid)
        summary['encoding_evidence']['session_version_readback'] = summary['session'].get('version_readback', {})
        stages.update('running', case_sha256=case_hash)
        summary["run"] = run_async(app, args.timeout, run_id=stages.run_id, case_sha256=case_hash)
        control_association = {'verified': summary['run'].get('events_cleared_before_run') is True,
                               'run_id': stages.run_id, 'case_sha256': case_hash,
                               'reason': 'CURRENT_SESSION_EVENT_SINK_CLEARED_IMMEDIATELY_BEFORE_RUN2'}

        control_text = "\n".join(MESSAGES) + ("\n" if MESSAGES else "")
        control_path = out / f"{args.label}_control_panel.txt"
        control_path.write_text(control_text, encoding="utf-8")
        control_counts = parse_summary_counts(control_text)
        control_hard = hard_pattern_counts(control_text)
        control_messages = find_hard_messages(control_text, source=str(control_path), source_sha256=sha256(control_path))

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
        summary["after_run_inp"] = artifact(out_inp)
        summary["after_run_bkp"] = artifact(out_bkp)

        save_as = work / f"{args.label}_post_run.bkp"
        stages.update('saving')
        try:
            if save_as.exists():
                raise FileExistsError(f'Post-run SaveAs would overwrite a staged file: {save_as}')
            app.SaveAs(str(save_as))
            summary["work_save_as"] = {"ok": save_as.exists(), **artifact(save_as)}
        except Exception as exc:
            summary["work_save_as"] = {"ok": False, "error": str(exc)}

        blocks, bad_blocks = block_statuses(app, parse_block_ids(work_inp))
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

        summary["control_panel"] = {
            **artifact(control_path),
            "message_count": len(MESSAGES),
            "summary_counts": control_counts,
            "hard_pattern_counts": control_hard,
            'actual_messages': control_messages,
            'association': control_association,
        }
        summary["block_count"] = len(blocks)
        summary["bad_blocks"] = bad_blocks
        summary["block_statuses"] = blocks
        summary["sidecars"] = sidecars
        summary['histories'] = histories
        summary['history_present'] = bool(histories)
        summary['history_file_count'] = len(histories)
        summary['history_hard_pattern_counts'] = history_counts if histories else None
        gate = evaluate_clean_gate(run=summary['run'], summary=control_counts, control_messages=control_messages,
                                   control_association=control_association, histories=histories,
                                   block_statuses=blocks, artifacts=[summary['after_run_inp'], summary['after_run_bkp']])
        summary['clean_gate'] = gate
        summary['simulation_clean'] = gate['simulation_clean']
        summary['gate_results'] = gate['gate_results']
        summary['rejection_reasons'] = gate['rejection_reasons']
        summary['source_after_run'] = artifact(source)
        summary['source_unchanged'] = summary['source_sha256'] == summary['source_after_run']['sha256']
        summary['passed'] = gate['passed'] and summary['source_unchanged']
        if not summary['source_unchanged']:
            summary['rejection_reasons'].append({'code': 'SOURCE_FILE_CHANGED_DURING_AUDIT'})
        summary["finished"] = now()
    except Exception as exc:
        summary["passed"] = False
        summary["error"] = str(exc)
        summary["traceback"] = traceback.format_exc()
        summary["finished"] = now()
    finally:
        stages.update('closing')
        try:
            lifecycle = close_aspen(app)
        except Exception as exc:
            lifecycle = {'closed_cleanly': False, 'error': str(exc)}
        if creation_attempted and app is None:
            lifecycle.update(closed_cleanly=False, status='COM_CREATION_RESULT_UNPROVEN')
        summary['lifecycle'] = lifecycle
        summary['passed'] = bool(summary.get('passed') and lifecycle.get('closed_cleanly') is True)
        if lifecycle.get('closed_cleanly') is not True:
            summary.setdefault('rejection_reasons', []).append({'code': 'LIFECYCLE_NOT_CLEAN', 'details': lifecycle})
        summary['operation_completed'] = bool(summary.get('run', {}).get('status') == 'returned' and lifecycle.get('closed_cleanly'))
        summary['finished'] = now()
        aspen_runtime.atomic_json(summary_path, summary)
        stages.update('finished', lifecycle_clean=lifecycle.get('closed_cleanly') is True)
        os.chdir(original_cwd)
        for key, old in old_environment.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old

    print(json.dumps({"passed": summary.get("passed"), "summary": str(summary_path)}, ensure_ascii=False))
    return 0 if summary.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
