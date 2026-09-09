from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

_RUNTIME_DIR = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills/aspen-plus-operations/scripts"
if not (_RUNTIME_DIR / "aspen_runtime.py").is_file():
    raise ImportError(f"Shared Aspen runtime missing: {_RUNTIME_DIR}")
sys.path.insert(0, str(_RUNTIME_DIR))
import aspen_runtime as runtime
from aspen_run_supervisor import run_worker


@dataclass(frozen=True)
class Component:
    cid: str
    lookup: str
    database_verified: bool


def read_components(path: Path, database_only: bool) -> list[Component]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    comps: list[Component] = []
    for row in rows:
        verified = (row.get("Database verified") or "").strip().lower() in {"yes", "true", "1"}
        if database_only and not verified:
            continue
        cid = (row.get("Component ID") or "").strip()
        lookup = (row.get("Aspen lookup/formula") or "").strip()
        if not cid or not lookup:
            raise ValueError(f"Missing Component ID or Aspen lookup/formula in row: {row}")
        comps.append(Component(cid=cid, lookup=lookup, database_verified=verified))
    if not comps:
        raise ValueError("No components selected.")
    return comps


def quote_lookup(value: str) -> str:
    if "," in value or " " in value or "(" in value or ")" in value:
        return f'"{value}"'
    return value


def wrap_components(comps: list[Component]) -> list[str]:
    lines: list[str] = []
    current = "COMPONENTS"
    for idx, comp in enumerate(comps):
        entry = f"{comp.cid} {quote_lookup(comp.lookup)}"
        token = f" {entry}" + (" /" if idx < len(comps) - 1 else "")
        if len(current) + len(token) > 74:
            lines.append(current)
            current = "           " + entry + (" /" if idx < len(comps) - 1 else "")
        else:
            current += token
    lines.append(current)
    return lines


def write_input(path: Path, title: str, comps: list[Component], with_dummy_flow: bool) -> None:
    lines = [
        f"TITLE '{title}'",
        "SUMMARY MM",
        "IN-UNITS MET TEMP=C PRES=BAR",
        "DEF-STREAMS CONVEN ALL",
        *wrap_components(comps),
        "PROPERTIES NRTL",
    ]
    if with_dummy_flow:
        lines.extend(
            [
                "FLOWSHEET GLOBAL",
                "   BLOCK B1 IN=S1 OUT=S2",
                "STREAM S1 TEMP=25 PRES=1 MOLE-FLOW=1",
                "   MOLE-FRAC CO2 1",
                "BLOCK B1 MIXER",
            ]
        )
    lines.extend(["STREAM-REPORT MOLEFLOW", ""])
    too_long = [line for line in lines if len(line) > 80]
    if too_long:
        raise ValueError(f"Aspen input line exceeds 80 columns: {too_long[:3]}")
    path.write_text("\n".join(lines), encoding="ascii")


def export_template(inp: Path, stem: str, out_dir: Path, *, prog_id: str = "Apwn.Document", session_factory=None) -> dict[str, Path]:
    paths = {
        "bkp": out_dir / f"{stem}.bkp",
        "apwz": out_dir / f"{stem}.apwz",
        "roundtrip": out_dir / f"{stem}_roundtrip.inp",
        "verify": out_dir / f"{stem}_verify_from_bkp.inp",
    }
    for path in paths.values():
        if path.exists():
            raise FileExistsError(f"Existing component-template output protected: {path}")
    recorder = runtime.StageRecorder()
    factory = session_factory or runtime.create_session
    session = None
    creation_in_progress = False
    evidence = {"schema": "aspen-component-template-runtime-v1", "run_id": recorder.run_id,
        "component_template_only": True, "run_requested": False, "simulation_clean": None, "delivery_passed": False,
        "input": runtime.artifact(inp), "sessions": [], "lifecycles": [], "exports": [],
        "runtime_identity": runtime.artifact(Path(runtime.__file__))}
    try:
        recorder.update("creating_com")
        creation_in_progress = True
        session = factory(prog_id)
        creation_in_progress = False
        evidence["sessions"].append(session.metadata)
        recorder.update("opening")
        evidence["input_open"] = runtime.open_case(session, inp, method="InitFromFile")
        recorder.update("exporting")
        evidence["exports"].append(runtime.export_case(session, 1, paths["bkp"]))
        recorder.update("saving")
        session.app.SaveAs(str(paths["apwz"].resolve()), True)
        archive = runtime.artifact(paths["apwz"])
        evidence["archive_save"] = archive
        if not archive["size"]:
            raise RuntimeError("SaveAs did not create nonempty APWZ")
        recorder.update("exporting")
        evidence["exports"].append(runtime.export_case(session, 4, paths["roundtrip"]))
        recorder.update("closing")
        lifecycle = runtime.close_session(session)
        evidence["lifecycles"].append(lifecycle)
        session = None
        if not lifecycle["closed_cleanly"]:
            raise RuntimeError("Initial component session close incomplete; second session not dispatched")
        recorder.update("creating_com")
        creation_in_progress = True
        session = factory(prog_id)
        creation_in_progress = False
        evidence["sessions"].append(session.metadata)
        recorder.update("opening")
        evidence["bkp_open"] = runtime.open_case(session, paths["bkp"])
        recorder.update("exporting")
        evidence["exports"].append(runtime.export_case(session, 4, paths["verify"]))
        if not all(row["ok"] for row in evidence["exports"]):
            raise RuntimeError("A component-template export failed")
    except Exception as exc:
        evidence["error"] = str(exc)
        raise
    finally:
        if session is not None:
            recorder.update("closing")
            evidence["lifecycles"].append(runtime.close_session(session))
        if creation_in_progress:
            evidence["lifecycles"].append({"closed_cleanly": False, "status": "COM_CREATION_RESULT_UNPROVEN"})
        lifecycle_clean = all(row["closed_cleanly"] for row in evidence["lifecycles"])
        evidence["lifecycle_clean"] = lifecycle_clean
        evidence["input_unchanged"] = runtime.sha256(inp) == evidence["input"]["sha256"]
        evidence["mechanical_export_completed"] = lifecycle_clean and "error" not in evidence and evidence["input_unchanged"]
        runtime.atomic_json(out_dir / f"{stem}_runtime_evidence.json", evidence)
        recorder.update("finished", lifecycle_clean=lifecycle_clean)
    if not evidence["mechanical_export_completed"]:
        raise RuntimeError("Component export lifecycle or input identity failed")
    return paths


def parse_component_ids(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"\nCOMPONENTS\s+(.*?)(?:\n\n|FORMULA|SOLVE|FLOWSHEET|PROPERTIES)", text, re.S)
    if not match:
        return set()
    ids: set[str] = set()
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if stripped:
            ids.add(stripped.split()[0].strip('"'))
    return ids


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--stem", required=True)
    parser.add_argument("--title")
    parser.add_argument("--database-only", action="store_true")
    parser.add_argument("--with-dummy-flow", action="store_true")
    parser.add_argument("--prog-id", default="Apwn.Document")
    parser.add_argument("--stage-timeout", type=float, default=60)
    parser.add_argument("--lock-file", default="")
    parser.add_argument("--_worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.csv, args.out_dir = args.csv.resolve(), args.out_dir.resolve()
    if Path(args.stem).name != args.stem:
        raise ValueError("Stem must be a filename component")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if not args._worker:
        read_components(args.csv, args.database_only)
        for suffix in (".inp", ".bkp", ".apwz", "_roundtrip.inp", "_verify_from_bkp.inp", "_runtime_evidence.json"):
            if (args.out_dir / f"{args.stem}{suffix}").exists():
                raise FileExistsError("Choose a new component-template stem or output directory")
        run_dir = Path(tempfile.mkdtemp(prefix="component_worker_", dir=args.out_dir))
        command = [sys.executable, str(Path(__file__).resolve()), "--csv", str(args.csv), "--out-dir", str(args.out_dir),
                   "--stem", args.stem, "--prog-id", args.prog_id, "--_worker"]
        if args.title:
            command += ["--title", args.title]
        for active, flag in ((args.database_only, "--database-only"), (args.with_dummy_flow, "--with-dummy-flow")):
            if active:
                command.append(flag)
        result = run_worker(command, run_dir=run_dir,
            stage_timeouts={phase: args.stage_timeout for phase in ("creating_com", "opening", "exporting", "saving", "closing")},
            overall_timeout_s=12 * args.stage_timeout,
            lock_path=Path(args.lock_file).resolve() if args.lock_file else runtime.DEFAULT_LOCK_PATH)
        print(json.dumps({"status": result["status"], "runtime_evidence": str(args.out_dir / f"{args.stem}_runtime_evidence.json"),
                          "supervisor": str(run_dir / "supervisor_result.json"), "component_template_only": True,
                          "delivery_passed": False}, ensure_ascii=False))
        if result["status"] != "completed" or not result.get("lifecycle_clean"):
            raise SystemExit(2)
        return
    if not os.environ.get("ASPEN_RUNTIME_OWNER_TOKEN"):
        raise RuntimeError("Component worker requires external supervisor context")
    comps = read_components(args.csv, args.database_only)
    title = args.title or args.stem.replace("_", " ").upper()
    inp = args.out_dir / f"{args.stem}.inp"
    write_input(inp, title, comps, args.with_dummy_flow)
    paths = export_template(inp, args.stem, args.out_dir, prog_id=args.prog_id)

    expected = {c.cid for c in comps}
    roundtrip_ids = parse_component_ids(paths["roundtrip"])
    verify_ids = parse_component_ids(paths["verify"])
    missing_roundtrip = sorted(expected - roundtrip_ids)
    missing_verify = sorted(expected - verify_ids)
    if missing_roundtrip or missing_verify:
        raise SystemExit(
            f"Verification failed. missing_roundtrip={missing_roundtrip}, missing_verify={missing_verify}"
        )
    for label, path in {"input": inp, **paths}.items():
        print(f"{label}: {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
