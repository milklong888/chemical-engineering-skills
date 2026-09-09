"""Source-preserved section builder with explicit hash-bound project profiles.

No historical project values are defaults. This entry prepares candidate input
and an operation handoff; it never starts COM or claims simulation acceptance.
"""
from __future__ import annotations
import argparse
import csv
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any

SOURCE_SHA256 = "7874c7765e9760e59f674402eae883d0b7dcaf07a51848721254d3fc0e8108fc"


@dataclass(frozen=True)
class VerifiedProfile:
    data: dict[str, Any]
    source_sha256: str
    content_sha256: str


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def load_profile(path: Path, expected_sha256: str) -> VerifiedProfile:
    if not re.fullmatch(r"[A-Fa-f0-9]{64}", expected_sha256 or ""):
        raise ValueError("An explicit profile SHA256 is required")
    raw = Path(path).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual.lower() != expected_sha256.lower():
        raise ValueError("Profile hash mismatch")
    data = json.loads(raw)
    if data.get("schema") != "two-section-explicit-profile-v1":
        raise ValueError("Unsupported profile schema")
    if data.get("source_builder_sha256") != SOURCE_SHA256:
        raise ValueError("Profile belongs to another source builder")
    if not data.get("profile_id") or not isinstance(data.get("authority"), dict):
        raise ValueError("Profile identity and authority locator are required")
    profile = VerifiedProfile(data, actual, _canonical_hash(data))
    profile_data(profile)
    return profile


def profile_data(profile: VerifiedProfile) -> dict:
    if not isinstance(profile, VerifiedProfile) or _canonical_hash(profile.data) != profile.content_sha256:
        raise ValueError("Missing or mutated hash-bound profile")
    components = profile.data.get("components")
    if not isinstance(components, list) or not components:
        raise ValueError("Explicit component pairs are required")
    ids = []
    for pair in components:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("Invalid component pair")
        for value in pair:
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_+.-]+", value):
                raise ValueError("Invalid component/card identifier")
        ids.append(pair[0])
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate component identity")
    for cid in ids:
        require_positive(profile.data.get("molecular_weights", {}).get(cid), "molecular weight " + cid)
    if profile.data.get("molecular_weight_unit") != "kg/kmol":
        raise ValueError("Molecular weight basis must be explicit kg/kmol")
    return profile.data


def literal(profile: VerifiedProfile, function: str, key: str):
    return profile.data["literals"][function][key]


def joined(profile: VerifiedProfile, function: str, key: str, values: list[Any]) -> str:
    parts = profile.data["joined_strings"][function][key]
    text = []
    for part in parts:
        if isinstance(part, str):
            text.append(part)
        else:
            value = values[part["field"]]
            conversion = part["conversion"]
            if conversion == 115: value = str(value)
            elif conversion == 114: value = repr(value)
            elif conversion == 97: value = ascii(value)
            elif conversion != -1: raise ValueError("Unregistered string conversion")
            text.append(format(value, part["format"]))
    return "".join(text)


def finite_number(value: Any, label: str) -> float:
    if value is None or isinstance(value, bool):
        raise ValueError("Missing or nonnumeric " + label)
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Missing or nonnumeric " + label) from exc
    if not math.isfinite(number):
        raise ValueError("Nonfinite " + label)
    return number


def require_positive(value: Any, label: str) -> float:
    number = finite_number(value, label)
    if number <= 0:
        raise ValueError("Positive value required: " + label)
    return number


def required_number(row: dict, key: str) -> float:
    if key not in row:
        raise ValueError("Missing required field " + key)
    return finite_number(row[key], key)


def _flows(values: dict[str, float]) -> dict[str, float]:
    if not isinstance(values, dict) or not values:
        raise ValueError("Explicit component flows are required")
    result = {key: finite_number(value, key) for key, value in values.items()}
    if any(value < 0 for value in result.values()):
        raise ValueError("Negative component flow")
    return result


def kmol_from_mass(mass_kg_h: dict[str, float], *, mw: dict[str, float]) -> dict[str, float]:
    mass_kg_h = _flows(mass_kg_h)
    weights = {comp: require_positive(mw.get(comp), "molecular weight " + comp) for comp in mass_kg_h}
    return {comp: value / weights[comp] for comp, value in mass_kg_h.items()}


def mole_frac_lines(flows: dict[str, float]) -> list[str]:
    flows = _flows(flows)
    total = require_positive(sum(flows.values()), "total molar flow")
    tokens = [f"{comp} {flow / total:.8f}" for comp, flow in flows.items()]
    lines: list[str] = []
    current = "   MOLE-FRAC"
    for idx, token in enumerate(tokens):
        suffix = " /" if idx < len(tokens) - 1 else ""
        piece = f" {token}{suffix}"
        if len(current) + len(piece) > 118:
            lines.append(current)
            current = f"            {token}{suffix}"
        else:
            current += piece
    lines.append(current)
    return lines


def stream_lines_mass(sid: str, temp_c: float, pressure_bar: float, mass_kg_h: dict[str, float], *, mw: dict[str, float]) -> list[str]:
    flows = kmol_from_mass(mass_kg_h, mw=mw)
    return stream_lines_kmol(sid, temp_c, pressure_bar, flows)


def stream_lines_kmol(sid: str, temp_c: float, pressure_bar: float, flows: dict[str, float]) -> list[str]:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", sid): raise ValueError("Invalid stream identifier")
    temp_c = finite_number(temp_c, "temperature C")
    pressure_bar = require_positive(pressure_bar, "absolute pressure bar")
    flows = _flows(flows)
    total = require_positive(sum(flows.values()), "total molar flow")
    return [
        f"STREAM {sid} TEMP={temp_c:.3f} PRES={pressure_bar:.4f} MOLE-FLOW={total:.8f}",
        *mole_frac_lines({k: v for k, v in flows.items() if v > 0}),
    ]


def blank_stream(sid: str, temp_c: float, pressure_bar: float, comp: str, *, seed_flow_kmol_h: float) -> list[str]:
    # The old hidden 1E-9 seed is now an explicit provisional initializer.
    seed = require_positive(seed_flow_kmol_h, "explicit placeholder seed")
    temp_c = finite_number(temp_c, "temperature C")
    pressure_bar = require_positive(pressure_bar, "absolute pressure bar")
    lines = stream_lines_kmol(sid, temp_c, pressure_bar, {comp: seed})
    lines[0] = f"STREAM {sid} TEMP={temp_c:.3f} PRES={pressure_bar:.4f} MOLE-FLOW={seed:.12g}"
    return lines


def wrap_components(*, components: list[tuple[str, str]]) -> list[str]:
    if not components: raise ValueError("Explicit components required")
    if len({cid for cid, _ in components}) != len(components): raise ValueError("Duplicate component identity")
    lines: list[str] = []
    current = "COMPONENTS"
    for idx, (cid, lookup) in enumerate(components):
        if not all(re.fullmatch(r"[A-Za-z0-9_+.-]+", value) for value in (cid, lookup)):
            raise ValueError("Invalid component identifier")
        suffix = " /" if idx < len(components) - 1 else ""
        token = f" {cid} {lookup}{suffix}"
        if len(current) + len(token) > 118:
            lines.append(current)
            current = f"           {cid} {lookup}{suffix}"
        else:
            current += token
    lines.append(current)
    return lines


def parse_block_ids(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    names: list[str] = []
    for match in re.finditer(r"(?im)^\s*BLOCK\s+([A-Za-z0-9_-]+)\b", text):
        name = match.group(1).upper()
        if name not in names:
            names.append(name)
    return names


def get_value(aspen: Any, path: str) -> Any:
    try:
        node = aspen.Tree.FindNode(path)
        return None if node is None else node.Value
    except Exception:
        return None


def set_sep2_splits(aspen: Any, block: str, outlet: str, splits: dict[str, float], *, runtime: Any, expected_units: dict[str, str], allowed_input_paths: tuple[str, ...]) -> list[str]:
    """Use an existing owned AspenSession and exact upstream-authorized inputs.

    The caller must already be inside the existing supervised operation worker.
    This function never creates a COM session or guesses a node's unit.
    """
    if not os.environ.get("ASPEN_RUNTIME_OWNER_TOKEN") or not os.environ.get("ASPEN_RUNTIME_STAGE_FILE"):
        raise RuntimeError("SEP mutation requires the existing external-supervisor worker context")
    aspen.assert_owner()
    missing: list[str] = []
    for comp, frac in splits.items():
        frac = finite_number(frac, "split " + comp)
        if not 0 <= frac <= 1: raise ValueError("Split fraction outside [0,1]")
        path = rf"\Data\Blocks\{block}\Input\FRACS\MIXED\{outlet}\{comp}"
        before = runtime.read_node(aspen, path)
        if before["status"] != "read":
            missing.append(f"{block}/{outlet}/{comp}")
            continue
        if path not in expected_units:
            raise ValueError("Expected node unit missing from operation contract")
        result = runtime.write_input_node(aspen, path, frac, expected_unit=expected_units[path], allowed_input_paths=allowed_input_paths)
        if result["status"] != "written_verified":
            raise ValueError("SEP split write readback mismatch")
    return missing


def all_splits(default: float, overrides: dict[str, float], *, components: list[tuple[str, str]]) -> dict[str, float]:
    ids = {cid for cid, _ in components}
    if not ids or set(overrides) - ids: raise ValueError("Unknown split component")
    values = {cid: default for cid, _ in components}
    values.update(overrides)
    for value in values.values():
        if not 0 <= finite_number(value, "split") <= 1: raise ValueError("Split outside [0,1]")
    return values


def block_status_rows(aspen: Any, export_path: Path, *, calculator_ids: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in parse_block_ids(export_path):
        rows.append({"block": name, "blkstat": get_value(aspen, rf"\Data\Blocks\{name}\Output\BLKSTAT"),
                     "blkmsg": get_value(aspen, rf"\Data\Blocks\{name}\Output\BLKMSG")})
    for calc_id in calculator_ids:
        rows.append({"block": f"CALC:{calc_id}",
                     "blkstat": get_value(aspen, rf"\Data\Flowsheeting Options\Calculator\{calc_id}\Output\BLKSTAT"),
                     "blkmsg": get_value(aspen, rf"\Data\Flowsheeting Options\Calculator\{calc_id}\Output\BLKMSG")})
    return rows


def is_clean_block(row: dict) -> bool:
    return row.get("blkstat") in (0, 0.0, "0") and row.get("blkstat") is not False and not row.get("blkmsg")


def read_stream(aspen: Any, stream: str, *, components: list[tuple[str, str]], expected_units: dict[str, str]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "stream": stream,
        "temp_C": get_value(aspen, rf"\Data\Streams\{stream}\Output\TEMP_OUT\MIXED"),
        "pressure_bar": get_value(aspen, rf"\Data\Streams\{stream}\Output\PRES_OUT\MIXED"),
        "mole_flow_kmol_h": get_value(aspen, rf"\Data\Streams\{stream}\Output\MOLEFLMX\MIXED"),
        "mass_flow_kg_h": get_value(aspen, rf"\Data\Streams\{stream}\Output\MASSFLMX\MIXED"),
    }
    for comp, _ in components:
        row[f"mol_{comp}"] = get_value(aspen, rf"\Data\Streams\{stream}\Output\MOLEFLOW\MIXED\{comp}")
    paths = {"temp_C": rf"\Data\Streams\{stream}\Output\TEMP_OUT\MIXED",
             "pressure_bar": rf"\Data\Streams\{stream}\Output\PRES_OUT\MIXED",
             "mole_flow_kmol_h": rf"\Data\Streams\{stream}\Output\MOLEFLMX\MIXED",
             "mass_flow_kg_h": rf"\Data\Streams\{stream}\Output\MASSFLMX\MIXED",
             **{f"mol_{cid}": rf"\Data\Streams\{stream}\Output\MOLEFLOW\MIXED\{cid}" for cid, _ in components}}
    if set(paths) != set(expected_units) or any(not isinstance(unit, str) or not unit for unit in expected_units.values()):
        raise ValueError("Explicit expected units required for every numeric stream field")
    evidence = {}
    for field, path in paths.items():
        raw_value = row[field]
        try:
            node = aspen.Tree.FindNode(path)
            observed_unit = str(node.UnitString) if node is not None else None
        except Exception:
            observed_unit = None
        verified = raw_value is not None and observed_unit == expected_units[field]
        evidence[field] = {"raw_value": raw_value, "observed_unit": observed_unit,
                           "expected_unit": expected_units[field], "unit_verified": verified}
        if not verified: row[field] = None
    row["field_evidence"] = evidence
    return row


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        return
    keys = list(rows[0])
    if any(set(row) != set(keys) for row in rows): raise ValueError("Inconsistent CSV fields")
    with path.open("x", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def mass(row: dict[str, Any], comp: str, *, mw: dict[str, float]) -> float:
    value = required_number(row, f"mol_{comp}")
    if value < 0: raise ValueError("Negative component flow")
    return value * require_positive(mw.get(comp), "molecular weight " + comp)


def mass_frac(row: dict[str, Any], comp: str, *, components: list[tuple[str, str]], mw: dict[str, float]) -> float:
    if comp not in {cid for cid, _ in components}: raise ValueError("Fraction component not in explicit component set")
    total = sum(mass(row, cid, mw=mw) for cid, _ in components)
    return mass(row, comp, mw=mw) / require_positive(total, "total mass flow")


def mole_ratio(row: dict[str, Any], top: str, bottom: str) -> float:
    den = required_number(row, f"mol_{bottom}")
    numerator = required_number(row, f"mol_{top}")
    if numerator < 0: raise ValueError("Negative numerator flow")
    return numerator / require_positive(den, "ratio denominator flow")


def safe_output(output_dir: Path, filename: str) -> Path:
    root = Path(output_dir).resolve()
    path = (root / filename).resolve()
    if Path(filename).name != filename or not path.is_relative_to(root):
        raise ValueError("Output filename escapes explicit project directory")
    if path.exists(): raise FileExistsError(path)
    return path


def write_text_exclusive(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    with path.open("x", encoding=encoding, newline="\n") as handle:
        handle.write(text)


def run_case(stem: str, lines: list[str], sep_settings: list[tuple[str, str, dict[str, float]]], streams_to_read: list[str], *, profile: VerifiedProfile, output_dir: Path) -> dict:
    """Prepare a protected no-execution handoff to existing runtime operations.

    Original unsafe COM body is preserved separately as audit-only source text.
    Post-import SEP changes need an upstream owned/supervised mutation worker;
    the existing no-edit operation template is never claimed to implement them.
    """
    data = profile_data(profile)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", stem): raise ValueError("Invalid output stem")
    if not lines or any(not isinstance(line, str) or "\n" in line or "\r" in line or len(line) > 132 for line in lines):
        raise ValueError("Invalid INP line or line exceeds 132 columns")
    text = "\n".join(lines) + "\n"
    text.encode("ascii")
    root = Path(output_dir).resolve()
    # Explicit new directory only. Never delete/replace user files.
    if root.exists() and any(root.iterdir()): raise FileExistsError("Output directory is not empty")
    root.mkdir(parents=True, exist_ok=True)
    inp = safe_output(root, stem + ".inp")
    request = safe_output(root, stem + "_operation_request.json")
    skills = Path(__file__).resolve().parents[2]
    template = skills / "aspen-document-driven-flowsheet/scripts/templates/aspen_operation_template.py"
    runtime = skills / "aspen-plus-operations/scripts/aspen_runtime.py"
    supervisor = runtime.with_name("aspen_run_supervisor.py")
    for dependency in (template, runtime, supervisor):
        if not dependency.is_file(): raise FileNotFoundError(dependency)
    dependencies = [{"skill_relative_path": str(path.relative_to(skills)).replace("\\", "/"), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in (template, runtime, supervisor)]
    command = [sys.executable, str(template), "--case-file", str(inp), "--out-dir", str(root / "operations"), "--mode", "run-export", "--runtime-path", str(runtime), "--runtime-sha256", dependencies[1]["sha256"]]
    handoff = {"schema": "two-section-operation-handoff-v1", "status": "candidate_input_prepared_not_run",
               "profile_id": data["profile_id"], "profile_sha256": profile.source_sha256,
               "source_builder_sha256": SOURCE_SHA256, "candidate_sha256": hashlib.sha256(text.encode("ascii")).hexdigest(),
               "candidate_file": str(inp), "runtime_dependencies": dependencies,
               "operation_command_after_mutation_evidence": command,
               "pending_sep_settings": sep_settings, "streams_to_read": streams_to_read,
               "automatic_execution": False, "simulation_clean": None, "delivery_passed": False,
               "default_retrieval_eligible": False, "learning_eligible": False,
               "execution_blockers": (["POST_IMPORT_MUTATIONS_REQUIRE_CURRENT_AUTHORITY_AND_SUPERVISED_WORKER"] if sep_settings else []) + (["SYNTHETIC_PROFILE_NOT_AN_ENGINEERING_MODEL"] if data.get("synthetic") else []),
               "acceptance_boundary": "Shared runtime operation return does not replace exact-file Summary/history and project/equipment gates."}
    serialized = json.dumps(handoff, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    write_text_exclusive(inp, text, encoding="ascii")
    write_text_exclusive(request, serialized)
    return handoff


# BEGIN SOURCE-PRESERVED PROFILE FUNCTIONS

def segment_a_lines(*, profile: VerifiedProfile) -> list[str]:
    profile_data(profile)
    return [literal(profile, 'segment_a_lines', 'v000'), literal(profile, 'segment_a_lines', 'v001'), literal(profile, 'segment_a_lines', 'v002'), literal(profile, 'segment_a_lines', 'v003'), *wrap_components(components=profile.data['components']), literal(profile, 'segment_a_lines', 'v004'), literal(profile, 'segment_a_lines', 'v005'), literal(profile, 'segment_a_lines', 'v006'), literal(profile, 'segment_a_lines', 'v007'), literal(profile, 'segment_a_lines', 'v008'), literal(profile, 'segment_a_lines', 'v009'), literal(profile, 'segment_a_lines', 'v010'), literal(profile, 'segment_a_lines', 'v011'), literal(profile, 'segment_a_lines', 'v012'), literal(profile, 'segment_a_lines', 'v013'), literal(profile, 'segment_a_lines', 'v014'), literal(profile, 'segment_a_lines', 'v015'), literal(profile, 'segment_a_lines', 'v016'), literal(profile, 'segment_a_lines', 'v017'), literal(profile, 'segment_a_lines', 'v018'), literal(profile, 'segment_a_lines', 'v019'), literal(profile, 'segment_a_lines', 'v020'), literal(profile, 'segment_a_lines', 'v021'), literal(profile, 'segment_a_lines', 'v022'), literal(profile, 'segment_a_lines', 'v023'), *stream_lines_mass(literal(profile, 'segment_a_lines', 'v024'), literal(profile, 'segment_a_lines', 'v025'), literal(profile, 'segment_a_lines', 'v026'), profile.data['original_mass_feed'], mw=profile.data['molecular_weights']), *stream_lines_mass(literal(profile, 'segment_a_lines', 'v027'), literal(profile, 'segment_a_lines', 'v028'), literal(profile, 'segment_a_lines', 'v029'), {literal(profile, 'segment_a_lines', 'v030'): literal(profile, 'segment_a_lines', 'v031')}, mw=profile.data['molecular_weights']), *stream_lines_mass(literal(profile, 'segment_a_lines', 'v032'), literal(profile, 'segment_a_lines', 'v033'), literal(profile, 'segment_a_lines', 'v034'), {literal(profile, 'segment_a_lines', 'v035'): literal(profile, 'segment_a_lines', 'v036')}, mw=profile.data['molecular_weights']), *stream_lines_mass(literal(profile, 'segment_a_lines', 'v037'), literal(profile, 'segment_a_lines', 'v038'), literal(profile, 'segment_a_lines', 'v039'), {literal(profile, 'segment_a_lines', 'v040'): literal(profile, 'segment_a_lines', 'v042'), literal(profile, 'segment_a_lines', 'v041'): literal(profile, 'segment_a_lines', 'v043')}, mw=profile.data['molecular_weights']), *stream_lines_mass(literal(profile, 'segment_a_lines', 'v044'), literal(profile, 'segment_a_lines', 'v045'), literal(profile, 'segment_a_lines', 'v046'), {literal(profile, 'segment_a_lines', 'v047'): literal(profile, 'segment_a_lines', 'v048')}, mw=profile.data['molecular_weights']), literal(profile, 'segment_a_lines', 'v049'), literal(profile, 'segment_a_lines', 'v050'), literal(profile, 'segment_a_lines', 'v051'), literal(profile, 'segment_a_lines', 'v052'), literal(profile, 'segment_a_lines', 'v053'), literal(profile, 'segment_a_lines', 'v054'), literal(profile, 'segment_a_lines', 'v055'), literal(profile, 'segment_a_lines', 'v056'), literal(profile, 'segment_a_lines', 'v057'), literal(profile, 'segment_a_lines', 'v058'), literal(profile, 'segment_a_lines', 'v059'), literal(profile, 'segment_a_lines', 'v060'), literal(profile, 'segment_a_lines', 'v061'), literal(profile, 'segment_a_lines', 'v062'), literal(profile, 'segment_a_lines', 'v063'), literal(profile, 'segment_a_lines', 'v064'), literal(profile, 'segment_a_lines', 'v065'), literal(profile, 'segment_a_lines', 'v066'), literal(profile, 'segment_a_lines', 'v067'), literal(profile, 'segment_a_lines', 'v068'), literal(profile, 'segment_a_lines', 'v069'), literal(profile, 'segment_a_lines', 'v070'), literal(profile, 'segment_a_lines', 'v071'), literal(profile, 'segment_a_lines', 'v072'), literal(profile, 'segment_a_lines', 'v073'), literal(profile, 'segment_a_lines', 'v074'), literal(profile, 'segment_a_lines', 'v075'), literal(profile, 'segment_a_lines', 'v076'), literal(profile, 'segment_a_lines', 'v077'), literal(profile, 'segment_a_lines', 'v078'), literal(profile, 'segment_a_lines', 'v079'), literal(profile, 'segment_a_lines', 'v080'), literal(profile, 'segment_a_lines', 'v081'), literal(profile, 'segment_a_lines', 'v082'), literal(profile, 'segment_a_lines', 'v083'), literal(profile, 'segment_a_lines', 'v084'), literal(profile, 'segment_a_lines', 'v085'), literal(profile, 'segment_a_lines', 'v086'), literal(profile, 'segment_a_lines', 'v087'), literal(profile, 'segment_a_lines', 'v088'), literal(profile, 'segment_a_lines', 'v089'), literal(profile, 'segment_a_lines', 'v090'), literal(profile, 'segment_a_lines', 'v091'), literal(profile, 'segment_a_lines', 'v092'), literal(profile, 'segment_a_lines', 'v093'), literal(profile, 'segment_a_lines', 'v094'), literal(profile, 'segment_a_lines', 'v095'), literal(profile, 'segment_a_lines', 'v096'), literal(profile, 'segment_a_lines', 'v097'), literal(profile, 'segment_a_lines', 'v098'), literal(profile, 'segment_a_lines', 'v099'), literal(profile, 'segment_a_lines', 'v100'), literal(profile, 'segment_a_lines', 'v101'), literal(profile, 'segment_a_lines', 'v102'), literal(profile, 'segment_a_lines', 'v103'), literal(profile, 'segment_a_lines', 'v104'), literal(profile, 'segment_a_lines', 'v105')]


def segment_b_lines(syngas: dict[str, Any], *, profile: VerifiedProfile) -> list[str]:
    profile_data(profile)
    feed_flows = {comp: required_number(syngas, joined(profile, 'segment_b_lines', 's000', [comp])) for comp, _ in profile.data['components'] if required_number(syngas, joined(profile, 'segment_b_lines', 's001', [comp])) > literal(profile, 'segment_b_lines', 'v000')}
    return [literal(profile, 'segment_b_lines', 'v001'), literal(profile, 'segment_b_lines', 'v002'), literal(profile, 'segment_b_lines', 'v003'), literal(profile, 'segment_b_lines', 'v004'), *wrap_components(components=profile.data['components']), literal(profile, 'segment_b_lines', 'v005'), literal(profile, 'segment_b_lines', 'v006'), literal(profile, 'segment_b_lines', 'v007'), literal(profile, 'segment_b_lines', 'v008'), literal(profile, 'segment_b_lines', 'v009'), literal(profile, 'segment_b_lines', 'v010'), literal(profile, 'segment_b_lines', 'v011'), literal(profile, 'segment_b_lines', 'v012'), literal(profile, 'segment_b_lines', 'v013'), literal(profile, 'segment_b_lines', 'v014'), literal(profile, 'segment_b_lines', 'v015'), literal(profile, 'segment_b_lines', 'v016'), literal(profile, 'segment_b_lines', 'v017'), literal(profile, 'segment_b_lines', 'v018'), literal(profile, 'segment_b_lines', 'v019'), literal(profile, 'segment_b_lines', 'v020'), literal(profile, 'segment_b_lines', 'v021'), literal(profile, 'segment_b_lines', 'v022'), literal(profile, 'segment_b_lines', 'v023'), *stream_lines_kmol(literal(profile, 'segment_b_lines', 'v024'), literal(profile, 'segment_b_lines', 'v025'), literal(profile, 'segment_b_lines', 'v026'), feed_flows), *blank_stream(literal(profile, 'segment_b_lines', 'v027'), literal(profile, 'segment_b_lines', 'v028'), literal(profile, 'segment_b_lines', 'v029'), literal(profile, 'segment_b_lines', 'v030'), seed_flow_kmol_h=profile.data['placeholder_seed_flow_kmol_h']), literal(profile, 'segment_b_lines', 'v031'), literal(profile, 'segment_b_lines', 'v032'), literal(profile, 'segment_b_lines', 'v033'), literal(profile, 'segment_b_lines', 'v034'), literal(profile, 'segment_b_lines', 'v035'), literal(profile, 'segment_b_lines', 'v036'), literal(profile, 'segment_b_lines', 'v037'), literal(profile, 'segment_b_lines', 'v038'), literal(profile, 'segment_b_lines', 'v039'), literal(profile, 'segment_b_lines', 'v040'), literal(profile, 'segment_b_lines', 'v041'), literal(profile, 'segment_b_lines', 'v042'), literal(profile, 'segment_b_lines', 'v043'), literal(profile, 'segment_b_lines', 'v044'), literal(profile, 'segment_b_lines', 'v045'), literal(profile, 'segment_b_lines', 'v046'), literal(profile, 'segment_b_lines', 'v047'), literal(profile, 'segment_b_lines', 'v048'), literal(profile, 'segment_b_lines', 'v049'), literal(profile, 'segment_b_lines', 'v050'), literal(profile, 'segment_b_lines', 'v051'), literal(profile, 'segment_b_lines', 'v052'), literal(profile, 'segment_b_lines', 'v053'), literal(profile, 'segment_b_lines', 'v054'), literal(profile, 'segment_b_lines', 'v055'), literal(profile, 'segment_b_lines', 'v056'), literal(profile, 'segment_b_lines', 'v057'), literal(profile, 'segment_b_lines', 'v058'), literal(profile, 'segment_b_lines', 'v059'), literal(profile, 'segment_b_lines', 'v060'), literal(profile, 'segment_b_lines', 'v061'), literal(profile, 'segment_b_lines', 'v062'), literal(profile, 'segment_b_lines', 'v063'), literal(profile, 'segment_b_lines', 'v064'), literal(profile, 'segment_b_lines', 'v065'), literal(profile, 'segment_b_lines', 'v066'), literal(profile, 'segment_b_lines', 'v067'), literal(profile, 'segment_b_lines', 'v068'), literal(profile, 'segment_b_lines', 'v069'), literal(profile, 'segment_b_lines', 'v070'), literal(profile, 'segment_b_lines', 'v071'), literal(profile, 'segment_b_lines', 'v072'), literal(profile, 'segment_b_lines', 'v073'), literal(profile, 'segment_b_lines', 'v074'), literal(profile, 'segment_b_lines', 'v075'), literal(profile, 'segment_b_lines', 'v076'), literal(profile, 'segment_b_lines', 'v077'), literal(profile, 'segment_b_lines', 'v078')]


def audit_text(a_streams: list[dict[str, Any]], a_blocks: list[dict[str, Any]], a_missing: list[str], a_status: str, b_streams: list[dict[str, Any]], b_blocks: list[dict[str, Any]], b_missing: list[str], b_status: str, *, profile: VerifiedProfile) -> str:
    profile_data(profile)
    a = {row[literal(profile, 'audit_text', 'v000')]: row for row in a_streams}
    b = {row[literal(profile, 'audit_text', 'v001')]: row for row in b_streams}
    bad_a = [row for row in a_blocks if not is_clean_block(row)]
    bad_b = [row for row in b_blocks if not is_clean_block(row)]
    sty = a.get(literal(profile, 'audit_text', 'v002'), {})
    syngas = a.get(literal(profile, 'audit_text', 'v003'), {})
    alkeb = b.get(literal(profile, 'audit_text', 'v004'), {})
    alkfeed = b.get(literal(profile, 'audit_text', 'v005'), {})
    mtoraw = b.get(literal(profile, 'audit_text', 'v006'), {})
    c2 = literal(profile, 'audit_text', 'v007') * required_number(mtoraw, literal(profile, 'audit_text', 'v008'))
    c3 = literal(profile, 'audit_text', 'v009') * required_number(mtoraw, literal(profile, 'audit_text', 'v010'))
    c4 = literal(profile, 'audit_text', 'v011') * required_number(mtoraw, literal(profile, 'audit_text', 'v012'))
    ctot = c2 + c3 + c4
    lines = [literal(profile, 'audit_text', 'v013'), literal(profile, 'audit_text', 'v014'), literal(profile, 'audit_text', 'v015'), literal(profile, 'audit_text', 'v016'), literal(profile, 'audit_text', 'v017'), literal(profile, 'audit_text', 'v018'), literal(profile, 'audit_text', 'v019'), literal(profile, 'audit_text', 'v020'), literal(profile, 'audit_text', 'v021'), literal(profile, 'audit_text', 'v022'), literal(profile, 'audit_text', 'v023'), literal(profile, 'audit_text', 'v024'), literal(profile, 'audit_text', 'v025'), literal(profile, 'audit_text', 'v026'), literal(profile, 'audit_text', 'v027'), literal(profile, 'audit_text', 'v028'), literal(profile, 'audit_text', 'v029'), literal(profile, 'audit_text', 'v030'), joined(profile, 'audit_text', 's000', [a_status]), joined(profile, 'audit_text', 's001', [len(a_blocks), len(bad_a)]), joined(profile, 'audit_text', 's002', [len(a_missing)]), joined(profile, 'audit_text', 's003', [required_number(sty, literal(profile, 'audit_text', 'v031'))]), joined(profile, 'audit_text', 's004', [mass_frac(sty, literal(profile, 'audit_text', 'v032'), mw=profile.data['molecular_weights'], components=profile.data['components']) * literal(profile, 'audit_text', 'v033')]), joined(profile, 'audit_text', 's005', [mole_ratio(syngas, literal(profile, 'audit_text', 'v034'), literal(profile, 'audit_text', 'v035'))]), literal(profile, 'audit_text', 'v036'), literal(profile, 'audit_text', 'v037'), literal(profile, 'audit_text', 'v038'), joined(profile, 'audit_text', 's006', [b_status]), joined(profile, 'audit_text', 's007', [len(b_blocks), len(bad_b)]), joined(profile, 'audit_text', 's008', [len(b_missing)]), joined(profile, 'audit_text', 's009', [c2 / require_positive(ctot, literal(profile, 'audit_text', 'v039')) * literal(profile, 'audit_text', 'v040'), c3 / require_positive(ctot, literal(profile, 'audit_text', 'v041')) * literal(profile, 'audit_text', 'v042'), c4 / require_positive(ctot, literal(profile, 'audit_text', 'v043')) * literal(profile, 'audit_text', 'v044')]), joined(profile, 'audit_text', 's010', [mole_ratio(alkfeed, literal(profile, 'audit_text', 'v045'), literal(profile, 'audit_text', 'v046'))]), joined(profile, 'audit_text', 's011', [mass(alkeb, literal(profile, 'audit_text', 'v047'), mw=profile.data['molecular_weights'])]), joined(profile, 'audit_text', 's012', [mass_frac(alkeb, literal(profile, 'audit_text', 'v048'), mw=profile.data['molecular_weights'], components=profile.data['components']) * literal(profile, 'audit_text', 'v049')]), literal(profile, 'audit_text', 'v050'), literal(profile, 'audit_text', 'v051'), literal(profile, 'audit_text', 'v052'), literal(profile, 'audit_text', 'v053'), literal(profile, 'audit_text', 'v054'), literal(profile, 'audit_text', 'v055'), literal(profile, 'audit_text', 'v056'), literal(profile, 'audit_text', 'v057'), literal(profile, 'audit_text', 'v058'), literal(profile, 'audit_text', 'v059')]
    if bad_a or bad_b:
        lines.extend([literal(profile, 'audit_text', 'v060'), literal(profile, 'audit_text', 'v061'), literal(profile, 'audit_text', 'v062'), literal(profile, 'audit_text', 'v063')])
        for row in bad_a:
            lines.append(joined(profile, 'audit_text', 's013', [row[literal(profile, 'audit_text', 'v064')], row.get(literal(profile, 'audit_text', 'v065')), row.get(literal(profile, 'audit_text', 'v066'))]))
        for row in bad_b:
            lines.append(joined(profile, 'audit_text', 's014', [row[literal(profile, 'audit_text', 'v067')], row.get(literal(profile, 'audit_text', 'v068')), row.get(literal(profile, 'audit_text', 'v069'))]))
    return '# Candidate section audit — no delivery approval\n\ndefault_retrieval_eligible: false\nlearning_eligible: false\n\n' + (literal(profile, 'audit_text', 'v070').join(lines) + literal(profile, 'audit_text', 'v071'))


def write_pfd(*, profile: VerifiedProfile, output_dir: Path) -> None:
    profile_data(profile)
    text = literal(profile, 'write_pfd', 'v000')
    write_text_exclusive(safe_output(output_dir, literal(profile, 'write_pfd', 'v001')), text, encoding=literal(profile, 'write_pfd', 'v002'))

# END SOURCE-PRESERVED PROFILE FUNCTIONS


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--profile-sha256", required=True)
    parser.add_argument("--section", choices=("a", "b"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--boundary-stream-json", type=Path)
    args = parser.parse_args(argv)
    try:
        profile = load_profile(args.profile, args.profile_sha256)
        data = profile_data(profile)
        section = data["sections"][args.section]
        if args.section == "a":
            lines = segment_a_lines(profile=profile)
        else:
            if args.boundary_stream_json is None: raise ValueError("Section B requires explicit current boundary stream JSON")
            boundary = json.loads(args.boundary_stream_json.read_text(encoding="utf-8"))
            lines = segment_b_lines(boundary, profile=profile)
        result = run_case(section["stem"], lines, section["sep_settings"], section["streams_to_read"], profile=profile, output_dir=args.output_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "not_prepared", "reason": str(exc), "automatic_execution": False, "delivery_passed": False}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
