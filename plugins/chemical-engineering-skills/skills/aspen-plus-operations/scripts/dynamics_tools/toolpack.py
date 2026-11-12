"""Read-only local-tool catalog and file checks. No Aspen/COM/MCP launch.

MIT licensed. File checks never certify native simulation or engineering.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import sys

VERSION = "1.1.0"
PUBLIC_PARSER_SHA256_LF = "7465d04fc8d1114d65a9f64c94abda32fa885b7a6c8e493aec4b90034e9a3f31"
PUBLIC_PARSER = Path(__file__).resolve().parent.parent / "aspen_evidence.py"
ROOT = Path(__file__).resolve().parent


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    def bad_constant(value):
        raise ValueError(f"Non-finite JSON constant: {value}")
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      object_pairs_hook=pairs, parse_constant=bad_constant,
                      parse_float=lambda value: finite(value, "JSON number"))


def contained_file(root, relative):
    if not isinstance(relative, str) or not relative:
        raise ValueError("Manifest path must be a nonempty relative string")
    posix = PurePosixPath(relative)
    if ("\\" in relative or ":" in relative or posix.is_absolute()
            or PureWindowsPath(relative).drive
            or any(part in ("", ".", "..") for part in relative.split("/"))):
        raise ValueError(f"Unsafe manifest path: {relative}")
    root = Path(root).resolve(strict=True)
    candidate = root
    for part in posix.parts:
        candidate = candidate / part
        # Reject links and Windows junction/reparse redirections.
        if candidate.is_symlink() or (hasattr(candidate, "is_junction") and candidate.is_junction()):
            raise ValueError(f"Linked manifest path: {relative}")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError(f"Not a regular contained file: {relative}")
    return resolved


def verify_manifest(root, manifest):
    obj = load_json(manifest)
    rows = obj.get("files")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Manifest needs a nonempty files array")
    seen = set()
    checks = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Manifest entry must be an object")
        name = row.get("path")
        file = contained_file(root, name)
        normalized = os.path.normcase(str(file))
        if normalized in seen:
            raise ValueError(f"Duplicate manifest file: {name}")
        seen.add(normalized)
        size, digest = row.get("size"), row.get("sha256")
        if type(size) is not int or size < 0:
            raise ValueError(f"Invalid size: {name}")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
            raise ValueError(f"Invalid SHA256: {name}")
        actual_size, actual_hash = file.stat().st_size, sha256(file)
        checks.append({"path": name, "size": actual_size, "sha256": actual_hash,
                       "matches": actual_size == size and actual_hash == digest.lower()})
    return {"scope": "listed_file_bytes_only", "matches": all(x["matches"] for x in checks),
            "checked_files": len(checks), "unlisted_files_checked": False,
            "strict_simulation_passed": False, "files": checks}


def finite(value, label):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"Non-finite {label}")
    return result


def check_grid(path, *, time_column, interval, start, end, tolerance, numeric_columns=()):
    interval, start, end, tolerance = [finite(x, "grid argument") for x in (interval, start, end, tolerance)]
    if interval <= 0 or tolerance < 0 or end <= start:
        raise ValueError("Require interval>0, tolerance>=0 and end>start")
    times = []
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader, None)
        if not header or len(set(header)) != len(header) or any(not x for x in header):
            raise ValueError("Missing, empty or duplicate CSV headers")
        for column in (time_column, *numeric_columns):
            if column not in header:
                raise ValueError(f"Missing column: {column}")
        ti = header.index(time_column)
        ni = [header.index(x) for x in numeric_columns]
        for line, row in enumerate(reader, 2):
            if len(row) != len(header):
                raise ValueError(f"Ragged CSV row {line}")
            value = finite(row[ti], f"time at row {line}")
            if times and value <= times[-1]:
                raise ValueError(f"Non-increasing time at row {line}")
            for index in ni:
                finite(row[index], f"{header[index]} at row {line}")
            times.append(value)
    if len(times) < 2:
        raise ValueError("At least two samples are required")
    expected_last_index = round((end - start) / interval)
    grid_aligned = abs(start + expected_last_index * interval - end) <= tolerance
    grid_error = max(abs(t - (start + i * interval)) for i, t in enumerate(times))
    matches = (grid_aligned and len(times) == expected_last_index + 1
               and abs(times[0] - start) <= tolerance
               and abs(times[-1] - end) <= tolerance and grid_error <= tolerance)
    return {"scope": "supplied_csv_grid_only", "matches": matches, "rows": len(times),
            "columns": len(header), "time_column": time_column,
            "start": times[0], "end": times[-1], "interval": interval,
            "caller_time_abs_tolerance": tolerance, "max_grid_error": grid_error,
            "native_provenance_verified": False, "strict_simulation_passed": False}


def history_report(path, operations_root=None, verified_encoding=None, expected_owner_sha256=None):
    """Reuse the public sibling parser; explicit installed-owner fallback only.

    Identity is checked before importing code. The pinned public parser accepts
    an independently reported LF/CRLF checkout difference. A fallback requires
    an explicit expected raw-byte SHA256, never a guessed owner version.
    """
    if PUBLIC_PARSER.is_file():
        owner, owner_source = PUBLIC_PARSER, "public_sibling_parser"
    elif operations_root:
        owner = Path(operations_root) / "scripts" / "aspen_evidence.py"
        owner_source = "explicit_operations_fallback"
    else:
        raise ValueError("Public sibling parser is missing; provide operations_root and expected_owner_sha256 for an explicit fallback")
    raw = owner.read_bytes()
    raw_hash = hashlib.sha256(raw).hexdigest()
    lf_hash = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    if expected_owner_sha256 is not None:
        if (not isinstance(expected_owner_sha256, str) or len(expected_owner_sha256) != 64
                or any(c not in "0123456789abcdefABCDEF" for c in expected_owner_sha256)):
            raise ValueError("expected_owner_sha256 must be a 64-character SHA256")
        if raw_hash != expected_owner_sha256.lower():
            raise ValueError("Parser raw-byte SHA256 does not match the caller's expected identity")
    if lf_hash != PUBLIC_PARSER_SHA256_LF:
        raise ValueError("Parser differs from the pinned public source; review and update its dependency identity")
    if owner_source == "explicit_operations_fallback" and expected_owner_sha256 is None:
        raise ValueError("Explicit fallback requires expected_owner_sha256 before importing the owner")
    identity = {"owner_path": str(owner.resolve()), "owner_source": owner_source,
                "owner_sha256": raw_hash, "owner_sha256_lf_normalized": lf_hash,
                "owner_expected_raw_sha256": expected_owner_sha256,
                "owner_identity_verified": True,
                "owner_identity_scope": "pinned public bytes allowing only CRLF-to-LF normalization" if owner_source == "public_sibling_parser" else "pinned public parser plus caller-supplied raw-byte identity; not source authenticity"}
    spec = importlib.util.spec_from_file_location("toolpack_aspen_evidence_owner", owner)
    if spec is None or spec.loader is None:
        raise ValueError("Cannot load the existing operations evidence owner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = Path(path).read_bytes()
    decoded = module.decode_history_bytes(data, verified_fallback_encodings=(verified_encoding,) if verified_encoding else ())
    if not decoded["verified"]:
        return {"scope": "offline_history_text_only", "matches": False, "decoded": decoded,
                **identity, "strict_simulation_passed": False}
    report = module.inspect_history_text(decoded["text"], source=str(path), source_sha256=decoded["sha256"])
    text_ok = report["complete"] and not report["messages"] and report["summary"]["complete"] and report["summary"]["gate_status"] == "PASS"
    return {"scope": "offline_history_text_only", "matches": bool(text_ok),
            "encoding": decoded["encoding"], "source_sha256": decoded["sha256"],
            **identity, "report": report, "strict_simulation_passed": False,
            "limitation": "No run identity, live Control Panel, products, tolerance lock or exact-file reopen verified."}


def local_catalog(settings=None):
    catalog = load_json(ROOT / "tool_catalog.json")
    configuration = load_json(settings) if settings else {}
    paths = configuration.get("paths", {})
    for tool in catalog["tools"]:
        root = paths.get(tool["id"]) or os.environ.get(tool["root_environment_variable"])
        tool["configured"] = bool(root)
        tool["root"] = root
        tool["entry_exists"] = bool(root and (Path(root) / tool["entry"]).is_file())
        configured_python = configuration.get("interpreters", {}).get(tool["id"])
        tool["python_executable"] = configured_python or (str(Path(root) / tool["python"]) if root and tool.get("python") else None)
    return catalog


def invocation_plan(tool_id, settings=None):
    catalog = local_catalog(settings)
    tool = next((x for x in catalog["tools"] if x["id"] == tool_id), None)
    if tool is None or not tool["entry_exists"]:
        raise ValueError("Tool is unknown, unconfigured or missing; inspect catalog")
    if tool["category"] == "local-python-library":
        raise ValueError("Library entry: use the history bridge, not direct execution")
    root = Path(tool["root"]).resolve()
    if tool.get("requires_configured_python") and not tool["python_executable"]:
        raise ValueError("This service needs its configured environment Python; set interpreters in local settings")
    executable = Path(tool["python_executable"] or sys.executable)
    if not executable.is_file():
        raise ValueError("Configured Python executable is missing")
    if tool.get("module"):
        argv = [str(executable), "-m", tool["module"]]
    else:
        argv = [str(executable), "-B", "-X", "utf8", str(root / tool["entry"])]
    return {"tool": tool_id, "argv": argv, "cwd": str(root),
            "execution_performed": False, "transport": tool.get("transport"),
            "existing_connected_mcp_preferred": True,
            "note": "Plan only. Use connected tools first; native operations need the active task contract."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command", required=True)
    cat = sub.add_parser("catalog"); cat.add_argument("--settings")
    plan = sub.add_parser("plan"); plan.add_argument("tool"); plan.add_argument("--settings")
    man = sub.add_parser("manifest"); man.add_argument("root"); man.add_argument("manifest")
    grid = sub.add_parser("grid"); grid.add_argument("csv")
    grid.add_argument("--time-column", required=True)
    for arg in ("interval", "start", "end", "time-abs-tol"):
        grid.add_argument("--" + arg, type=float, required=True)
    grid.add_argument("--numeric-column", action="append", default=[])
    his = sub.add_parser("history"); his.add_argument("history")
    his.add_argument("--operations-root", help="Explicit fallback only when the public sibling parser is unavailable")
    his.add_argument("--expected-owner-sha256", help="Required raw-byte source identity for fallback; optional assertion for public sibling")
    his.add_argument("--verified-encoding", help="Only provide an encoding independently verified for this file")
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog": result = local_catalog(args.settings)
        elif args.command == "plan": result = invocation_plan(args.tool, args.settings)
        elif args.command == "manifest": result = verify_manifest(args.root, args.manifest)
        elif args.command == "grid": result = check_grid(args.csv, time_column=args.time_column, interval=args.interval, start=args.start, end=args.end, tolerance=args.time_abs_tol, numeric_columns=args.numeric_column)
        else: result = history_report(args.history, args.operations_root, args.verified_encoding, args.expected_owner_sha256)
    except (OSError, ValueError, TypeError, KeyError, ImportError, AttributeError, OverflowError) as exc:
        print(json.dumps({"status": "invalid_or_unavailable", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if result.get("matches", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
