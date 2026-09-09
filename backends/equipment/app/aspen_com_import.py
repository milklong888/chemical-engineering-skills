from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any


FROZEN_ROOT = getattr(sys, "_MEIPASS", None)
if FROZEN_ROOT:
    PACKAGE_ROOT = Path(FROZEN_ROOT).resolve()
    APP_DIR = PACKAGE_ROOT / "app"
    WORKSPACE_ROOT = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "EquipmentDesignGraphApp"
else:
    APP_DIR = Path(__file__).resolve().parent
    PACKAGE_ROOT = APP_DIR.parent
    WORKSPACE_ROOT = PACKAGE_ROOT.parent
SCRIPTS_DIR = PACKAGE_ROOT / "scripts"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import aspen_equipment_derivation as derivation  # noqa: E402
import aspen_pfd  # noqa: E402


CONTROL_MESSAGES: list[str] = []
PROBLEM_PATTERNS = (
    r"(?im)^\s*\*\s*WARNING\b",
    r"(?im)^\s*WARNING IN THE\b",
    r"(?im)^\s*WARNING WHILE\b",
    r"(?im)^\s*SEVERE ERROR\b",
    r"(?im)^\s*ERROR IN THE\b",
    r"(?im)^\s*ERROR WHILE EXECUTING\b",
    r"(?im)^\s*TERMINAL ERROR\b(?!S\s+\d)",
    r"(?im)^.*CHECK THE RUN STATUS.*$",
)

# Aspen V14 HAPCompStatusCode values from the installed COM type library.
# A node may still expose numeric zero-valued Output children when its owning
# stream/block has no results.  Those are tree placeholders, not process data.
HAP_RESULTS_SUCCESS = 1
HAP_NORESULTS = 2
HAP_NOT_RUN = 2097152


STREAM_FIELDS: dict[str, list[str]] = {
    "TEMP_OUT": [r"Output\TEMP_OUT\MIXED", r"Output\TEMP_OUT"],
    "PRES_OUT": [r"Output\PRES_OUT\MIXED", r"Output\PRES_OUT"],
    "MASSFLMX": [r"Output\MASSFLMX\MIXED", r"Output\MASSFLMX"],
    "VOLFLMX": [r"Output\VOLFLMX\MIXED", r"Output\VOLFLMX"],
    # Aspen V14 exposes transport-property results below STRM_UPP and keeps
    # phase values as separate real-valued leaves.  The MUMX and MIXED parent
    # nodes are integer tree-card placeholders and must not be used as the
    # physical viscosity.
    "MUMX_LIQUID": [
        r"Output\STRM_UPP\MUMX\MIXED\LIQUID",
    ],
    "MUMX_VAPOR": [
        r"Output\STRM_UPP\MUMX\MIXED\VAPOR",
    ],
    "VFRAC_OUT": [r"Output\VFRAC_OUT\MIXED", r"Output\VFRAC_OUT"],
    "SFRAC_OUT": [r"Output\SFRAC_OUT\MIXED", r"Output\SFRAC_OUT", r"Output\SOLIDFRAC_OUT"],
    "SOLID_MASSFLMX": [r"Output\MASSFLMX\CISOLID", r"Output\MASSFLMX\SOLID"],
    "molecular_weight": [r"Output\MW_OUT\MIXED", r"Output\MW\MIXED", r"Output\MW"],
    "density_kg_m3": [r"Output\RHOMX_MASS\MIXED", r"Output\RHO_MASS\MIXED"],
    "compressibility_factor": [r"Output\ZMX\MIXED", r"Output\Z_FACTOR\MIXED"],
}


BLOCK_FIELDS: dict[str, list[str]] = {
    "QCALC": [r"Output\QCALC", r"Output\B_QCALC"],
    # Keep Aspen's generic net-work card separate from the three PUMP power
    # channels.  In particular, a PUMP WNET observation can be the electrical
    # utility demand; it must never inherit BRAKE_POWER and be relabelled as
    # shaft power.
    "WNET": [r"Output\WNET", r"Output\B_WNET"],
    "FLUID_POWER": [r"Output\FLUID_POWER"],
    "BRAKE_POWER": [r"Output\BRAKE_POWER"],
    "ELEC_POWER": [r"Output\ELEC_POWER"],
    "DEFF": [r"Input\DEFF"],
    "AREA": [r"Output\AREA", r"Output\HX_AREAP"],
    "HEAD_CAL": [r"Output\HEAD_CAL", r"Output\HEAD"],
    "NPSHA": [
        r"Output\NPSHA",
        r"Output\NPSH_AVAIL",
        r"Output\NPSH-A",
        r"Output\NPSHAVAIL",
    ],
    "CEFF": [r"Output\CEFF", r"Input\CEFF", r"Input\SEFF"],
    "DELP_CAL": [r"Output\DELP_CAL", r"Output\PDRP"],
    "PRES_RATIO": [r"Output\PRES_RATIO", r"Output\PRATIO"],
    "NSTAGE": [r"Input\NSTAGE", r"Output\NSTAGE"],
    "VOLUME": [r"Input\VOLUME", r"Output\VOLUME"],
    "DIAMETER": [r"Input\DIAMETER", r"Output\DIAMETER"],
    "HEIGHT": [r"Input\HEIGHT", r"Output\HEIGHT"],
}


PROCESS_FUNCTIONS = {
    "PUMP": "liquid pressure boosting",
    "COMPR": "gas compression",
    "MCOMPR": "multistage gas compression",
    "MIXER": "stream mixing",
    "HEATER": "process heating or cooling",
    "HEATX": "two-stream heat exchange",
    "RADFRAC": "rigorous staged separation",
    "DSTWU": "shortcut distillation",
    "FLASH2": "vapor-liquid flash separation",
    "FLASH3": "three-phase flash separation",
    "DECANTER": "liquid-liquid separation",
    "SEP": "general separation; construction subtype requires confirmation",
    "SEP2": "general separation; construction subtype requires confirmation",
    "BATCHSEP": "batch separation; construction subtype requires confirmation",
    "CRYSTALLIZER": "solid crystallization; operating mode and heat-removal route require confirmation",
    "FILTER": "solid-liquid filtration; area and cycle require confirmation",
    "DRYER": "solids drying; evaporation duty and drying route require confirmation",
    "RPLUG": "plug-flow reaction",
    "RCSTR": "continuous stirred-tank reaction",
    "RSTOIC": "specified-conversion reaction",
    "RYIELD": "specified-yield reaction",
    "RGIBBS": "equilibrium reaction",
    "VALVE": "pressure reduction",
}


# Aspen leaves UnitString empty for a narrow set of named, dimensionless (or
# definition-fixed) cards. These defaults come from the field definition, not
# from the numeric magnitude. Every other missing unit remains explicit.
SEMANTIC_UNIT_DEFAULTS = {
    "VFRAC_OUT": "-",
    "SFRAC_OUT": "-",
    "molecular_weight": "kg/kmol",
    "compressibility_factor": "-",
    "CEFF": "fraction",
    "DEFF": "fraction",
    "PRES_RATIO": "-",
    "NSTAGE": "-",
}


RAW_FIELD_TO_IN_UNITS_KEY = {
    "TEMP_OUT": "TEMPERATURE",
    "PRES_OUT": "PRESSURE",
    "MASSFLMX": "MASS-FLOW",
    "SOLID_MASSFLMX": "MASS-FLOW",
    "VOLFLMX": "VOLUME-FLOW",
    "VOLFLMX_LIQ": "VOLUME-FLOW",
    "VOLFLMX_GAS": "VOLUME-FLOW",
    "density_kg_m3": "MASS-DENSITY",
    "MUMX": "VISCOSITY",
    "MUMX_LIQUID": "VISCOSITY",
    "MUMX_VAPOR": "VISCOSITY",
    "molecular_weight": "MOLE-WEIGHT",
    "QCALC": "ENTHALPY-FLO",
    "QNET": "ENTHALPY-FLO",
    "DUTY_OUT": "ENTHALPY-FLO",
    "WNET": "POWER",
    "FLUID_POWER": "POWER",
    "BRAKE_POWER": "POWER",
    "ELEC_POWER": "POWER",
    "HEAD_CAL": "HEAD",
    "DELP_CAL": "PDROP",
    "PDRP": "PDROP",
    "AREA": "AREA",
    "VOLUME": "VOLUME",
    "DIAMETER": "SHORT-LENGTH",
    "HEIGHT": "SHORT-LENGTH",
}


PUMP_POWER_QUANTITY_KINDS = {
    "FLUID_POWER": "pump_hydraulic_fluid_power",
    "BRAKE_POWER": "pump_brake_shaft_power",
    "ELEC_POWER": "pump_electrical_input_power",
    "DEFF": "pump_driver_efficiency_fraction",
}


def block_field_quantity_kind(field: str, block_type: str) -> str | None:
    """Return an explicit semantic label for ambiguous Aspen block cards."""

    model = str(block_type or "").strip().upper()
    if field == "WNET":
        if model == "PUMP":
            return "pump_electrical_utility_power_not_shaft_power"
        return "aspen_net_work_rate_not_assumed_shaft_power"
    if model == "PUMP":
        return PUMP_POWER_QUANTITY_KINDS.get(field)
    return None


def parse_in_units_cards(text: str) -> list[dict[str, Any]]:
    """Parse the IN-UNITS cards Aspen writes when a BKP is exported to INP."""

    lines = text.splitlines()
    cards: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        match = re.match(r"^(?P<indent>\s*)IN-UNITS\b", lines[index], re.IGNORECASE)
        if match is None:
            index += 1
            continue
        start = index
        parts: list[str] = []
        while index < len(lines):
            part = lines[index].strip()
            continued = part.endswith("&")
            if continued:
                part = part[:-1].rstrip()
            parts.append(part)
            index += 1
            if not continued:
                break
        raw_card = " ".join(part for part in parts if part)
        tokens = shlex.split(raw_card, posix=True)
        if len(tokens) < 2 or tokens[0].upper() != "IN-UNITS":
            continue
        fields: dict[str, str] = {}
        conflicts: list[dict[str, str]] = []
        for token in tokens[2:]:
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            key = key.strip().upper()
            value = value.strip()
            if not key or not value:
                continue
            if key in fields and fields[key] != value:
                conflicts.append({"field": key, "first": fields[key], "second": value})
                continue
            fields[key] = value
        indent = len(match.group("indent").replace("\t", "    "))
        cards.append({
            "line_number": start + 1,
            "scope": "GLOBAL" if indent == 0 else "LOCAL_CARD",
            "indent": indent,
            "unit_set": tokens[1],
            "fields": fields,
            "conflicts": conflicts,
            "raw_card": raw_card,
        })
    return cards


def global_in_units(cards: list[dict[str, Any]]) -> dict[str, Any] | None:
    globals_found = [card for card in cards if card.get("scope") == "GLOBAL"]
    if not globals_found:
        return None
    return globals_found[0]


def resolve_aspen_unit(
    field: str,
    unit: str,
    in_units_fields: dict[str, str] | None = None,
) -> tuple[str | None, bool]:
    declared = str(unit or "").strip()
    if declared:
        return declared, False
    unit_set_key = RAW_FIELD_TO_IN_UNITS_KEY.get(field)
    if unit_set_key and isinstance(in_units_fields, dict):
        from_unit_set = str(in_units_fields.get(unit_set_key) or "").strip()
        if from_unit_set:
            return from_unit_set, True
    semantic = SEMANTIC_UNIT_DEFAULTS.get(field)
    return (semantic, True) if semantic else (None, False)


def project_stream_phase_observation(
    row: dict[str, Any],
    *,
    source_field: str,
    target_field: str,
    phase: str,
) -> bool:
    """Project one Aspen stream result without breaking its raw evidence path."""

    if source_field not in row:
        return False
    row[target_field] = row[source_field]
    raw_paths = row.setdefault("aspen_raw_paths", {})
    raw_values = row.setdefault("aspen_raw_values", {})
    source_path = raw_paths.get(source_field)
    source_record = raw_values.get(source_field)
    if source_path:
        raw_paths[target_field] = source_path
    if isinstance(source_record, dict):
        raw_values[target_field] = {
            **source_record,
            "phase_projection": phase,
            "projection_source_field": source_field,
            "phase_source_field": row.get("phase_source_field"),
        }
    return True


def stage_aspen_sidecars(source: Path, staged: Path) -> list[dict[str, Any]]:
    """Copy bounded local Aspen sidecars into the isolated work directory."""
    copied: list[dict[str, Any]] = []
    for suffix in (".def", ".ads", ".appdf"):
        sidecar = source.with_suffix(suffix)
        if not sidecar.is_file():
            continue
        destination = staged.with_suffix(suffix)
        shutil.copy2(sidecar, destination)
        copied.append({
            "kind": suffix.lstrip(".").upper(),
            "source": str(sidecar),
            "staged": str(destination),
            "sha256": sha256(sidecar),
            "staged_sha256": sha256(destination),
        })
    # EDR links commonly use equipment-tag filenames, not the BKP stem. Copy
    # only same-directory EDR files; never recurse or follow arbitrary paths.
    for sidecar in sorted(
        (item for item in source.parent.iterdir() if item.is_file() and item.suffix.casefold() == ".edr"),
        key=lambda item: item.name.casefold(),
    ):
        destination = staged.parent / sidecar.name
        shutil.copy2(sidecar, destination)
        copied.append({
            "kind": "EDR",
            "source": str(sidecar),
            "staged": str(destination),
            "sha256": sha256(sidecar),
            "staged_sha256": sha256(destination),
        })
    return copied


class AspenEvents:
    def OnControlPanelMessage(self, *args: Any) -> None:
        for arg in args:
            if isinstance(arg, str) and arg.strip():
                CONTROL_MESSAGES.append(arg.rstrip())


class AspenLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.fd: int | None = None

    def __enter__(self) -> "AspenLock":
        try:
            self.fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise RuntimeError(f"Aspen COM 正由其他任务占用：{self.path}") from exc
        os.write(self.fd, f"pid={os.getpid()}\nstarted={time.strftime('%Y-%m-%dT%H:%M:%S')}\n".encode("ascii"))
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_text_latin1(text: str) -> str:
    return hashlib.sha256(text.encode("latin-1")).hexdigest().upper()


def inp_card_spans(text: str, keyword: str) -> list[tuple[int, int]]:
    """Return byte-stable text spans for Aspen top-level input cards."""

    wanted = keyword.upper()
    lines = text.splitlines(keepends=True)
    offsets: list[int] = []
    offset = 0
    for line in lines:
        offsets.append(offset)
        offset += len(line)
    starts = [
        index
        for index, line in enumerate(lines)
        if re.match(rf"^{re.escape(wanted)}(?:\s|$)", line, flags=re.IGNORECASE)
    ]
    spans: list[tuple[int, int]] = []
    for start_index in starts:
        end_index = len(lines)
        for index in range(start_index + 1, len(lines)):
            line = lines[index]
            if re.match(r"^[A-Z][A-Z0-9-]*(?:\s|$)", line, flags=re.IGNORECASE):
                end_index = index
                break
        start_offset = offsets[start_index]
        end_offset = offsets[end_index] if end_index < len(lines) else len(text)
        spans.append((start_offset, end_offset))
    return spans


def _unused_transport_prop_set_name(text: str) -> str:
    names = {
        match.group(1).upper()
        for match in re.finditer(
            r"(?im)^PROP-SET\s+([A-Z0-9_-]+)\b",
            text,
        )
    }
    for candidate in ("TXPORT", "EDGTXPRT", "EDGMU001", "EDGMU002"):
        if candidate not in names:
            return candidate
    raise RuntimeError("BLOCKED_NO_AVAILABLE_TRANSPORT_PROPERTY_SET_NAME")


def augment_transport_property_inp(text: str) -> tuple[str, dict[str, Any]]:
    """Ensure an isolated Aspen INP requests stream dynamic viscosity.

    The operation is intentionally text-only and idempotent.  The caller must
    reload the returned INP through Aspen COM and rerun the staged case; this
    function never writes to or mutates the source BKP.
    """

    before_sha = sha256_text_latin1(text)
    property_set_name: str | None = None
    property_set_created = False
    report_updated = False

    for start, end in inp_card_spans(text, "PROP-SET"):
        card = text[start:end]
        if re.search(r"(?i)\bMUMX\b", card):
            match = re.match(r"(?i)PROP-SET\s+([A-Z0-9_-]+)\b", card)
            if match:
                property_set_name = match.group(1)
                break

    if property_set_name is None:
        property_set_name = _unused_transport_prop_set_name(text)
        card = (
            f"PROP-SET {property_set_name} MUMX SUBSTREAM=MIXED PHASE=V L\n"
            ";  Added in an isolated copy by EquipmentDesignApp for viscosity extraction\n"
            "\n"
        )
        insertion_matches = list(
            re.finditer(r"(?im)^(?:STREAM|BLOCK)\s+", text)
        )
        insertion = insertion_matches[0].start() if insertion_matches else len(text)
        text = text[:insertion] + card + text[insertion:]
        property_set_created = True

    report_spans = inp_card_spans(text, "STREAM-REPOR")
    if report_spans:
        start, end = report_spans[0]
        card = text[start:end]
        if not re.search(
            rf"(?i)\bPROPERTIES\s*=[^\r\n]*(?:\b|/){re.escape(property_set_name)}\b",
            card,
        ):
            if re.search(r"(?i)\bPROPERTIES\s*=", card):
                card = re.sub(
                    r"(?i)(\bPROPERTIES\s*=\s*[A-Z0-9_-]+)",
                    rf"\1 / {property_set_name}",
                    card,
                    count=1,
                )
            else:
                line_end_match = re.search(r"\r?\n", card)
                line_end = line_end_match.start() if line_end_match else len(card)
                card = (
                    card[:line_end].rstrip()
                    + f" PROPERTIES={property_set_name}"
                    + card[line_end:]
                )
            text = text[:start] + card + text[end:]
            report_updated = True
    else:
        suffix = f"\nSTREAM-REPOR PROPERTIES={property_set_name}\n"
        text = text.rstrip() + suffix
        report_updated = True

    after_sha = sha256_text_latin1(text)
    return text, {
        "schema": "aspen-transport-property-augmentation-v1",
        "status": "CHANGED" if before_sha != after_sha else "ALREADY_PRESENT",
        "property_set_name": property_set_name,
        "requested_property": "MUMX",
        "property_set_created": property_set_created,
        "stream_report_updated": report_updated,
        "before_inp_sha256": before_sha,
        "after_inp_sha256": after_sha,
        "com_reload_required": before_sha != after_sha,
        "mutation_scope": "ISOLATED_INP_COPY_ONLY",
        "source_bkp_mutated": False,
    }


def prepare_transport_property_augmentation(
    app: Any,
    work: Path,
    out_dir: Path,
    source: Path,
) -> tuple[Path | None, dict[str, Any], Path]:
    """Export, augment and audit an isolated Aspen input deck."""

    before = work / "TRANSPORT_BEFORE.INP"
    after = work / "TRANSPORT_AUGMENTED.INP"
    app.Export(4, str(before.resolve()))
    if not before.is_file() or before.stat().st_size <= 0:
        raise RuntimeError("BLOCKED_ASPEN_INP_EXPORT_FOR_TRANSPORT_AUGMENTATION")
    original_text = before.read_text(encoding="latin-1")
    augmented_text, manifest = augment_transport_property_inp(original_text)
    manifest.update({
        "source_case_path": str(source),
        "source_case_sha256": sha256(source),
        "original_source_read_only": True,
        "com_export_method": "Document.Export(4, isolated_path)",
        "com_reload_method": "Document.InitFromFile2(isolated_augmented_inp)",
        "rerun_method": "Engine.Run2(False)",
    })
    before_copy = out_dir / "transport_property_before.inp"
    shutil.copy2(before, before_copy)
    manifest["before_artifact"] = {
        "path": before_copy.name,
        "sha256": sha256(before_copy),
    }
    if manifest["status"] == "CHANGED":
        after.write_text(augmented_text, encoding="latin-1")
        after_copy = out_dir / "transport_property_augmented.inp"
        shutil.copy2(after, after_copy)
        manifest["after_artifact"] = {
            "path": after_copy.name,
            "sha256": sha256(after_copy),
        }
        reload_path: Path | None = after
    else:
        reload_path = None
    manifest_path = out_dir / "transport_property_augmentation_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return reload_path, manifest, manifest_path


def verify_stream_transport_properties(bundle: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    unverifiable_phase: list[dict[str, Any]] = []
    for stream in bundle.get("streams", []):
        if str(stream.get("stream_record_type", "")).upper() != "MATERIAL":
            continue
        stream_id = str(stream.get("stream_id", ""))
        phase = str(stream.get("phase", "")).casefold()
        if phase in {"liquid", "solid_liquid"}:
            required = ["MUMX"]
        elif phase == "vapor":
            required = ["MUMX"]
        elif phase == "two_phase":
            required = ["MUMX_LIQUID", "MUMX_VAPOR"]
        elif phase == "solid":
            required = []
        else:
            required = ["PHASE", "MUMX"]
        absent = [
            field
            for field in required
            if (
                field == "PHASE"
                or (
                    field == "MUMX"
                    and not any(
                        isinstance(stream.get(candidate), (int, float))
                        for candidate in (
                            "MUMX",
                            "MUMX_LIQUID",
                            "MUMX_VAPOR",
                        )
                    )
                )
                or (
                    field not in {"PHASE", "MUMX"}
                    and not isinstance(stream.get(field), (int, float))
                )
            )
        ]
        row = {
            "stream_id": stream_id,
            "phase": phase or None,
            "required_fields": required,
            "missing_fields": absent,
            "selected_mumx_path": (stream.get("aspen_raw_paths") or {}).get("MUMX"),
            "liquid_mumx_path": (stream.get("aspen_raw_paths") or {}).get("MUMX_LIQUID"),
            "vapor_mumx_path": (stream.get("aspen_raw_paths") or {}).get("MUMX_VAPOR"),
            "verification_state": (
                "NOT_APPLICABLE_SOLID_STREAM"
                if phase == "solid"
                else (
                    "BLOCKED_UNVERIFIABLE_PHASE"
                    if "PHASE" in absent
                    else (
                        "BLOCKED_MISSING_ASPEN_VISCOSITY"
                        if absent
                        else "VERIFIED"
                    )
                )
            ),
        }
        rows.append(row)
        if absent:
            missing.append(row)
        if "PHASE" in absent:
            unverifiable_phase.append(row)
    if unverifiable_phase:
        status = "BLOCKED_UNVERIFIABLE_ASPEN_PHASE_AND_VISCOSITY"
    elif missing:
        status = "BLOCKED_MISSING_ASPEN_VISCOSITY"
    else:
        status = "PASS"
    return {
        "schema": "aspen-stream-transport-verification-v1",
        "status": status,
        "material_stream_count": len(rows),
        "verified_stream_count": sum(
            1 for row in rows if row["verification_state"] == "VERIFIED"
        ),
        "not_applicable_solid_stream_count": sum(
            1
            for row in rows
            if row["verification_state"] == "NOT_APPLICABLE_SOLID_STREAM"
        ),
        "unverifiable_phase_stream_count": len(unverifiable_phase),
        "missing_stream_count": len(missing),
        "missing": missing,
        "rows": rows,
    }


def persist_stream_transport_evidence(
    out_dir: Path,
    source: Path,
    verification: dict[str, Any],
    *,
    augmentation_requested: bool,
    run_result: dict[str, Any] | None,
    manifest: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], Path, Path]:
    """Persist verification even when Aspen already exposes all required MUMX."""

    verification_path = out_dir / "stream_transport_verification.json"
    verification_path.write_text(
        json.dumps(verification, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if manifest is None:
        manifest = {
            "schema": "aspen-transport-property-augmentation-v2",
            "status": (
                "NO_CHANGE_ALREADY_AVAILABLE"
                if verification.get("status") == "PASS"
                else "NO_AUGMENTATION_REQUESTED_VERIFICATION_BLOCKED"
            ),
            "method": "READ_ONLY_COM_TREE_EXTRACTION_AND_VERIFICATION",
            "requested_property": "MUMX",
            "property_set_created": False,
            "stream_report_updated": False,
            "operations": [],
            "augmentation_requested": augmentation_requested,
            "claim_boundary": (
                "The extracted Aspen stream results already contained the required "
                "phase-specific MUMX observations; no report-configuration claim is made."
            ),
            "source_case_path": str(source),
            "source_case_sha256": sha256(source),
            "original_source_read_only": True,
            "source_bkp_mutated": False,
            "mutation_scope": "NONE",
        }
    else:
        manifest = dict(manifest)
        manifest["augmentation_requested"] = augmentation_requested
        if (
            manifest.get("status") == "ALREADY_PRESENT"
            and verification.get("status") == "PASS"
        ):
            manifest["configuration_status"] = "ALREADY_PRESENT"
            manifest["status"] = "NO_CHANGE_ALREADY_AVAILABLE"
    manifest["rerun_completed"] = bool(
        isinstance(run_result, dict) and run_result.get("status") == "returned"
    )
    manifest["verification"] = verification
    manifest["verification_artifact"] = {
        "path": verification_path.name,
        "sha256": sha256(verification_path),
    }
    manifest_path = out_dir / "transport_property_augmentation_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest, manifest_path, verification_path


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def strip_unit(unit: Any) -> str:
    text = str(unit or "").strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()
    replacements = {"C": "C", "degC": "C", "kmol/hr": "kmol/h", "kg/hr": "kg/h"}
    return replacements.get(text, text)


def finite(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed == parsed and abs(parsed) != float("inf") else None


# This is only a floating-point endpoint tolerance.  It is deliberately many
# orders of magnitude smaller than an engineering phase split and must never be
# interpreted as a permissible vapor/liquid carry-over threshold.
VAPOR_FRACTION_ENDPOINT_TOLERANCE = 1.0e-9


def phase_from_vapor_fraction(value: Any) -> dict[str, Any]:
    """Classify only numerical 0/1 endpoints as pure phases.

    Every material value strictly between the endpoints remains mixed.  Values
    outside [0, 1] beyond the stated numerical tolerance are invalid rather
    than silently clamped.
    """
    vapor_fraction = finite(value)
    result: dict[str, Any] = {
        "source_field": "VFRAC_OUT",
        "raw_vapor_fraction": vapor_fraction,
        "policy": "numeric_endpoint_tolerance_only; every material 0<VFRAC_OUT<1 is two_phase",
        "endpoint_tolerance": VAPOR_FRACTION_ENDPOINT_TOLERANCE,
        "evidence_class": "D",
    }
    if vapor_fraction is None:
        return {**result, "status": "UNAVAILABLE", "phase": None}
    tolerance = VAPOR_FRACTION_ENDPOINT_TOLERANCE
    if vapor_fraction < -tolerance or vapor_fraction > 1.0 + tolerance:
        return {**result, "status": "INVALID_OUT_OF_RANGE", "phase": None}
    if vapor_fraction <= tolerance:
        return {**result, "status": "PURE_ENDPOINT", "phase": "liquid"}
    if vapor_fraction >= 1.0 - tolerance:
        return {**result, "status": "PURE_ENDPOINT", "phase": "vapor"}
    return {**result, "status": "MIXED", "phase": "two_phase"}


def node_elements(node: Any) -> list[Any]:
    if node is None:
        return []
    try:
        elements = node.Elements
    except Exception:
        return []
    try:
        count = int(elements.Count)
    except Exception:
        count = None

    def collect(start: int) -> list[Any]:
        rows: list[Any] = []
        limit = count if count is not None and count >= 0 else 10000
        for offset in range(limit):
            index = start + offset
            try:
                child = elements(index)
            except Exception:
                try:
                    child = elements.Item(index)
                except Exception:
                    break
            if child is None:
                break
            rows.append(child)
        return rows

    zero_based = collect(0)
    one_based = collect(1)
    return one_based if len(one_based) > len(zero_based) else zero_based


def node_name(node: Any) -> str:
    try:
        return str(node.Name)
    except Exception:
        return ""


def node_value(node: Any) -> Any:
    try:
        return node.Value
    except Exception:
        return None


def node_unit(node: Any) -> str:
    try:
        return strip_unit(node.UnitString)
    except Exception:
        return ""


def node_value_type(node: Any) -> Any:
    try:
        return node.ValueType
    except Exception:
        return None


def extract_stream_composition(
    tree: Any,
    base: str,
    stream_id: str,
    stream_compstatus: Any,
    warnings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    r"""Read the complete MIXED-stream composition vector from Aspen.

    The path order follows the existing workspace Aspen COM references:
    ``Output\MOLEFRAC\MIXED\<component>`` first, then MASSFRAC.  Component
    names are preserved only as identifiers; no hazard or compatibility label
    is inferred here.
    """

    if owner_has_no_results(stream_compstatus):
        return []
    for relative, basis in (
        (r"Output\MOLEFRAC\MIXED", "mole_fraction"),
        (r"Output\MASSFRAC\MIXED", "mass_fraction"),
    ):
        root = find_node(tree, base + "\\" + relative)
        children = node_elements(root)
        if not children:
            continue
        rows: list[dict[str, Any]] = []
        invalid: list[dict[str, Any]] = []
        for child in children:
            component_id = node_name(child).strip()
            fraction = finite(node_value(child))
            if not component_id or fraction is None or not 0.0 <= fraction <= 1.0:
                invalid.append({
                    "component_id": component_id,
                    "value": node_value(child),
                })
                continue
            rows.append({
                "component_id": component_id,
                "fraction": fraction,
                "basis": basis,
                "source_path": base + "\\" + relative + "\\" + component_id,
            })
        if invalid:
            warnings.append({
                "code": "COMPOSITION_COMPONENT_VALUE_INVALID",
                "object": stream_id,
                "path": base + "\\" + relative,
                "invalid_components": invalid,
                "action": "composition_vector_retained_for_local_normalizer_rejection",
            })
        if rows:
            total = sum(float(item["fraction"]) for item in rows)
            if abs(total - 1.0) > max(1.0e-8, 1.0e-6 * max(1.0, abs(total))):
                warnings.append({
                    "code": "COMPOSITION_VECTOR_NOT_CLOSED",
                    "object": stream_id,
                    "path": base + "\\" + relative,
                    "basis": basis,
                    "fraction_sum": total,
                    "action": "property_and_compatibility_labels_remain_unknown",
                })
            return rows
    return []


def node_record_type(node: Any) -> tuple[str, str]:
    """Return Aspen semantic record type; node.Value may only be an icon token."""
    try:
        value = node.AttributeValue(6)  # V14 HAP_RECORDTYPE
        if value not in (None, ""):
            return str(value).strip().upper(), "AttributeValue(6):HAP_RECORDTYPE"
    except Exception:
        pass
    return "", "missing:HAP_RECORDTYPE"


def node_compstatus(node: Any) -> Any:
    try:
        return node.AttributeValue(12)  # V14 HAP_COMPSTATUS
    except Exception:
        return None


def named_child(node: Any, name: str) -> Any:
    try:
        return node.Elements(name)
    except Exception:
        wanted = name.casefold()
        return next((child for child in node_elements(node) if node_name(child).casefold() == wanted), None)


def find_node(tree: Any, path: str) -> Any:
    try:
        return tree.FindNode(path)
    except Exception:
        return None


def _aspen_child_names(node: Any) -> list[str]:
    return [
        node_name(child).strip()
        for child in node_elements(node)
        if node_name(child).strip()
    ]


def _aspen_child_values(node: Any) -> list[Any]:
    return [node_value(child) for child in node_elements(node)]


def _append_aspen_list_value(node: Any, value: Any) -> Any:
    if node is None:
        raise RuntimeError("BLOCKED_ASPEN_COM_LIST_NODE_NOT_FOUND")
    elements = node.Elements
    location = int(elements.RowCount(0))
    elements.InsertRow(0, location)
    row = elements.Item(location)
    row.Value = value
    return row


def _append_aspen_named_row(node: Any, name: str) -> Any:
    if node is None:
        raise RuntimeError("BLOCKED_ASPEN_COM_NAMED_LIST_NODE_NOT_FOUND")
    elements = node.Elements
    location = int(elements.RowCount(0))
    elements.InsertRow(0, location)
    elements.SetItemName(location, 0, False, name)
    return elements.Item(name)


def _set_required_aspen_value(tree: Any, path: str, value: Any) -> None:
    node = find_node(tree, path)
    if node is None:
        raise RuntimeError(f"BLOCKED_ASPEN_COM_CONFIGURATION_NODE_NOT_FOUND:{path}")
    node.Value = value


def _unused_transport_prop_set_name_from_tree(existing_names: set[str]) -> str:
    for candidate in ("TXPORT", "EDGTXPRT", "EDGMU001", "EDGMU002"):
        if candidate not in existing_names:
            return candidate
    raise RuntimeError("BLOCKED_NO_AVAILABLE_TRANSPORT_PROPERTY_SET_NAME")


def ensure_stream_transport_property_via_com(
    app: Any,
    out_dir: Path,
    source: Path,
) -> tuple[dict[str, Any], Path]:
    """Request Aspen MUMX directly in the isolated live COM document.

    This avoids an INP export/reload round trip.  Some valid Aspen BKPs contain
    GUI-side records that do not round-trip through the text deck, so changing
    only the staged live document is the safest general path.
    """

    tree = app.Tree
    prop_sets = find_node(tree, r"\Data\Properties\Prop-Sets")
    report_properties = find_node(tree, r"\Data\Setup\Main\Input\PROPERTIES")
    if prop_sets is None:
        raise RuntimeError("BLOCKED_COM_PROP_SETS_NODE_NOT_FOUND")
    if report_properties is None:
        raise RuntimeError("BLOCKED_COM_REPORT_PROPERTIES_NODE_NOT_FOUND")

    existing_names = {
        name.upper()
        for name in _aspen_child_names(prop_sets)
    }
    report_before = [
        str(value).strip()
        for value in _aspen_child_values(report_properties)
        if value not in (None, "")
    ]
    candidates: list[str] = []
    for name in existing_names:
        base = rf"\Data\Properties\Prop-Sets\{name}\Input"
        units = find_node(tree, base + r"\UNITS")
        phases = {
            str(value).strip().upper()
            for value in _aspen_child_values(find_node(tree, base + r"\PHASE"))
            if value not in (None, "")
        }
        substream = str(
            node_value(find_node(tree, base + r"\SUBSTREAM")) or ""
        ).strip().upper()
        property_names = {
            item.upper()
            for item in _aspen_child_names(units)
        }
        if (
            "MUMX" in property_names
            and substream == "MIXED"
            and {"V", "L"}.issubset(phases)
        ):
            candidates.append(name)
    candidates.sort(key=lambda name: (name != "TXPORT", name))

    operations: list[dict[str, Any]] = []
    property_set_created = False
    if candidates:
        property_set_name = candidates[0]
    else:
        property_set_name = _unused_transport_prop_set_name_from_tree(existing_names)
        prop_sets.Elements.Add(property_set_name)
        property_set_created = True
        operations.append({
            "operation": "Prop-Sets.Elements.Add",
            "argument": property_set_name,
        })
        base = rf"\Data\Properties\Prop-Sets\{property_set_name}\Input"
        for field, value in (
            ("DESCRIPTION", "Dynamic viscosity requested by EquipmentDesignApp"),
            ("SUBSTREAM", "MIXED"),
            ("SYSPRES", "YES"),
            ("SYSTEMP", "YES"),
        ):
            path = base + "\\" + field
            _set_required_aspen_value(tree, path, value)
            operations.append({
                "operation": "set_value",
                "path": path,
                "value": value,
            })
        phase = find_node(tree, base + r"\PHASE")
        for value in ("V", "L"):
            row = _append_aspen_list_value(phase, value)
            operations.append({
                "operation": "PHASE.Elements.InsertRow",
                "value": value,
                "returned_name": node_name(row),
            })
        units = find_node(tree, base + r"\UNITS")
        property_node = _append_aspen_named_row(units, "MUMX")
        operations.append({
            "operation": "UNITS.Elements.InsertRow+SetItemName",
            "argument": "MUMX",
            "returned_name": node_name(property_node),
        })

    report_updated = property_set_name.upper() not in {
        value.upper()
        for value in report_before
    }
    if report_updated:
        row = _append_aspen_list_value(report_properties, property_set_name)
        operations.append({
            "operation": "Setup.Main.PROPERTIES.Elements.InsertRow",
            "value": property_set_name,
            "returned_name": node_name(row),
        })

    base = rf"\Data\Properties\Prop-Sets\{property_set_name}\Input"
    manifest: dict[str, Any] = {
        "schema": "aspen-transport-property-augmentation-v2",
        "status": (
            "CHANGED"
            if property_set_created or report_updated
            else "ALREADY_PRESENT"
        ),
        "method": "DIRECT_COM_TREE_MUTATION_ON_ISOLATED_DOCUMENT",
        "property_set_name": property_set_name,
        "requested_property": "MUMX",
        "property_set_created": property_set_created,
        "stream_report_updated": report_updated,
        "operations": operations,
        "tree_configuration_before": {
            "property_set_names": sorted(existing_names),
            "stream_report_property_sets": report_before,
        },
        "tree_configuration_after": {
            "property_set_exists": find_node(
                tree,
                rf"\Data\Properties\Prop-Sets\{property_set_name}",
            ) is not None,
            "properties": _aspen_child_names(find_node(tree, base + r"\UNITS")),
            "phases": _aspen_child_values(find_node(tree, base + r"\PHASE")),
            "substream": node_value(find_node(tree, base + r"\SUBSTREAM")),
            "stream_report_property_sets": _aspen_child_values(report_properties),
        },
        "source_case_path": str(source),
        "source_case_sha256": sha256(source),
        "original_source_read_only": True,
        "mutation_scope": "ISOLATED_LIVE_COM_DOCUMENT_ONLY",
        "source_bkp_mutated": False,
        "com_reload_required": False,
        "rerun_method": "Engine.Run2(False)",
    }
    manifest_path = out_dir / "transport_property_augmentation_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest, manifest_path


def owner_has_no_results(compstatus: Any) -> bool:
    if isinstance(compstatus, bool):
        return False
    try:
        status = int(compstatus)
    except (TypeError, ValueError):
        return False
    return bool(status & (HAP_NORESULTS | HAP_NOT_RUN))


def read_first(
    tree: Any,
    base: str,
    relative_paths: list[str],
    owner_compstatus: Any = None,
    require_continuous: bool = False,
) -> tuple[float | None, str, str, Any, str]:
    skipped_output = ""
    skipped_integer_node = ""
    no_results = owner_has_no_results(owner_compstatus)
    for relative in relative_paths:
        node = find_node(tree, base + "\\" + relative)
        if (
            node is not None
            and no_results
            and relative.lstrip("\\").upper().startswith("OUTPUT\\")
        ):
            skipped_output = skipped_output or relative
            continue
        value = finite(node_value(node))
        if value is not None:
            value_type = node_value_type(node)
            # The official IHNode ValueType contract uses 1 for integer and 2
            # for real. Aspen's generic tree exposes integer 0/1 placeholders
            # for several inapplicable continuous result cards (for example
            # RADFRAC CEFF and MCOMPR PRES_RATIO). Do not promote those into a
            # physical continuous quantity merely because they are numeric.
            if require_continuous and value_type == 1:
                skipped_integer_node = skipped_integer_node or relative
                continue
            return value, node_unit(node), relative, value_type, "defined"
    if skipped_output:
        return None, "", skipped_output, None, "skipped_owner_no_results"
    if skipped_integer_node:
        return None, "", skipped_integer_node, 1, "skipped_integer_node_for_continuous_field"
    return None, "", "", None, "undefined_or_missing"


def parse_aspen_history(text: str) -> dict[str, Any]:
    clean_statement = bool(re.search(r"NO ERRORS OR WARNINGS (?:GENERATED|WERE ISSUED)", text, flags=re.I))
    chunks = list(re.finditer(r"(?:SUMMARY OF ERRORS|Summary of Simulation Errors)(.*?)(?:\f|\Z)", text, flags=re.S | re.I))
    counts: dict[str, int] | None = None
    if chunks:
        chunk = chunks[-1].group(1)
        counts = {}
        labels = {
            "terminal_errors": "TERMINAL ERRORS",
            "severe_errors": "SEVERE ERRORS",
            "errors": "ERRORS",
            "warnings": "WARNINGS",
        }
        for key, label in labels.items():
            match = re.search(rf"(?im)^\s*{label}\s+((?:\d+\s+)+\d+)\s*$", chunk)
            if not match:
                counts = None
                break
            counts[key] = sum(int(value) for value in re.findall(r"\d+", match.group(1)))
    if counts is None and clean_statement:
        counts = {"terminal_errors": 0, "severe_errors": 0, "errors": 0, "warnings": 0}
    problem_lines = [
        line.strip()
        for line in text.splitlines()
        if any(re.search(pattern, line) for pattern in PROBLEM_PATTERNS)
    ]
    return {
        "found": counts is not None,
        "counts": counts,
        "clean_statement": clean_statement,
        "problem_lines": problem_lines[:200],
    }


def parse_history_block_results(text: str) -> dict[str, dict[str, dict[str, Any]]]:
    """Recover final UOS results that Aspen omits from some COM output cards.

    Aspen's raw ``.his`` UOS trace uses SI working values: W for HEATX duty
    and the three distinct PUMP channels ``FLUID PWR``, ``BRAKE PWR`` and
    ``ELEC PWR``; and kPa of available suction-pressure margin for PUMP
    ``NPSH AVAIL``.  The latter is not metres of liquid head and must not be
    exposed as such until a downstream calculation converts pressure to head
    using density and gravity.  PUMP input-card ``DEFF`` is retained as a
    dimensionless fraction. Repeated recycle-iteration blocks are
    intentionally processed in order so the final ``GENERATING RESULTS``
    occurrence replaces earlier provisional iterations.
    """

    header = re.compile(
        r"(?im)^\s*(?P<final>GENERATING\s+RESULTS\s+FOR\s+)?"
        r"UOS\s+BLOCK\s+(?P<block>\S+)\s+MODEL:\s*(?P<model>\S+)"
    )
    matches = list(header.finditer(text))
    recovered: dict[str, dict[str, dict[str, Any]]] = {}
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"

    # The raw history contains a numbered echo of the Aspen input deck before
    # the UOS result trace. Bound each PARAM search by the next BLOCK card so a
    # missing DEFF can never be borrowed from a neighbouring pump.
    input_header = re.compile(
        r"(?im)^\s*(?:\d+\s+)?BLOCK\s+"
        r"(?P<block>\S+)\s+(?P<model>[A-Z0-9_-]+)\b"
    )
    input_matches = list(input_header.finditer(text))
    pump_driver_efficiency: dict[str, dict[str, Any]] = {}
    for index, input_match in enumerate(input_matches):
        if input_match.group("model").strip().upper() != "PUMP":
            continue
        segment_end = (
            input_matches[index + 1].start()
            if index + 1 < len(input_matches)
            else len(text)
        )
        segment = text[input_match.end():segment_end]
        efficiency = re.search(
            rf"(?im)\bDEFF\s*=\s*(?P<value>{number})",
            segment,
        )
        if efficiency is None:
            continue
        raw_fraction = float(efficiency.group("value"))
        block_id = input_match.group("block").strip()
        pump_driver_efficiency[block_id] = {
            "value": raw_fraction,
            "unit": "fraction",
            "raw_value": raw_fraction,
            "raw_unit": "fraction",
            "history_label": "DEFF",
            "quantity_kind": "pump_driver_efficiency_fraction",
            "transform": (
                "DEFF_fraction = Aspen_history_input_card_DEFF (identity)"
            ),
            "status": "raw_history_input_card_fallback",
            "source": "Aspen .his PUMP input PARAM card field DEFF",
        }

    for index, match in enumerate(matches):
        segment_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        segment = text[match.end():segment_end]
        block_id = match.group("block").strip()
        model = match.group("model").strip().upper()
        observations: dict[str, dict[str, Any]] = {}
        if model == "PUMP":
            power_fields = (
                (
                    "FLUID_POWER",
                    r"FLUID\s+PWR",
                    "FLUID PWR",
                    "pump_hydraulic_fluid_power",
                ),
                (
                    "BRAKE_POWER",
                    r"BRAKE\s+PWR",
                    "BRAKE PWR",
                    "pump_brake_shaft_power",
                ),
                (
                    "ELEC_POWER",
                    r"ELEC\s+PWR",
                    "ELEC PWR",
                    "pump_electrical_input_power",
                ),
            )
            for field, pattern, label, quantity_kind in power_fields:
                power = re.search(
                    rf"(?im)\b{pattern}\s*=\s*(?P<value>{number})",
                    segment,
                )
                if power is None:
                    continue
                raw_power_w = float(power.group("value"))
                observations[field] = {
                    "value": raw_power_w / 1000.0,
                    "unit": "kW",
                    "raw_value": raw_power_w,
                    "raw_unit": "W",
                    "history_label": label,
                    "quantity_kind": quantity_kind,
                    "transform": (
                        f"{field}_kW = Aspen_history_{label.replace(' ', '_')}_W / 1000"
                    ),
                    "status": "raw_history_pump_power_fallback",
                    "source": f"Aspen .his UOS PUMP result field {label}",
                }
            npsh = re.search(rf"(?im)\bNPSH\s+AVAIL\s*=\s*(?P<value>{number})", segment)
            if npsh:
                raw_pressure_margin_kpa = float(npsh.group("value"))
                observations["NPSHA"] = {
                    "value": raw_pressure_margin_kpa,
                    "unit": "kPa",
                    "raw_value": raw_pressure_margin_kpa,
                    "raw_unit": "kPa",
                    "history_label": "NPSH AVAIL",
                    "quantity_kind": "available_suction_pressure_margin",
                    "transform": (
                        "NPSHA_pressure_margin_kPa = "
                        "Aspen_history_NPSH_AVAIL_kPa (identity; no pressure-to-head conversion)"
                    ),
                    "status": "raw_history_pressure_margin_fallback",
                    "source": "Aspen .his UOS PUMP result field NPSH AVAIL",
                }
            if block_id in pump_driver_efficiency:
                observations["DEFF"] = dict(pump_driver_efficiency[block_id])
        if model == "HEATX":
            area = re.search(rf"(?im)\bAREA\s*=\s*(?P<value>{number})", segment)
            if area:
                observations["AREA"] = {
                    "value": float(area.group("value")),
                    "unit": "m2",
                    "raw_value": float(area.group("value")),
                    "raw_unit": "m2",
                    "history_label": "AREA",
                    "status": "raw_history_fallback",
                }
            duty = re.search(rf"(?im)\bDUTY\s*=\s*(?P<value>{number})", segment)
            if duty:
                raw_w = float(duty.group("value"))
                observations["QCALC"] = {
                    "value": raw_w / 1000.0,
                    "unit": "kW",
                    "raw_value": raw_w,
                    "raw_unit": "W",
                    "history_label": "DUTY",
                    "transform": "QCALC_kW = Aspen_history_DUTY_W / 1000",
                    "status": "raw_history_fallback",
                }
        if observations:
            recovered[block_id] = observations
    return recovered


def merge_history_block_results(
    bundle: dict[str, Any],
    recovered: dict[str, dict[str, dict[str, Any]]],
    history_path: Path,
) -> list[dict[str, Any]]:
    """Fill only missing COM block values from the exact hashed raw history."""

    diagnostics: list[dict[str, Any]] = []
    units = bundle.setdefault("units", {})
    blocks = {
        str(row.get("block_id")): row
        for row in bundle.get("blocks", [])
        if isinstance(row, dict) and row.get("block_id")
    }
    history_hash = sha256(history_path)
    for block_id, observations in recovered.items():
        row = blocks.get(block_id)
        if row is None:
            continue
        raw_paths = row.setdefault("aspen_raw_paths", {})
        raw_values = row.setdefault("aspen_raw_values", {})
        for field, observation in observations.items():
            if finite(row.get(field)) is not None:
                continue
            value = finite(observation.get("value"))
            unit = str(observation.get("unit") or "").strip()
            if value is None or not unit:
                continue
            source_path = f"raw_history:{block_id}:{observation.get('history_label') or field}"
            row[field] = value
            raw_paths[field] = source_path
            raw_values[field] = {
                **observation,
                "value": value,
                "unit": unit,
                "path": source_path,
                "source_file_path": str(history_path),
                "source_file_sha256": history_hash,
            }
            units[f"block.{block_id}.{field}"] = unit
            unit_key = f"block.{field}"
            if not str(units.get(unit_key) or "").strip():
                units[unit_key] = unit
            diagnostics.append({
                "code": "RAW_HISTORY_RESULT_FALLBACK",
                "object": block_id,
                "field": field,
                "unit": unit,
                "raw_value": observation.get("raw_value"),
                "raw_unit": observation.get("raw_unit"),
                "quantity_kind": observation.get("quantity_kind"),
                "status": observation.get("status"),
                "source": observation.get("source"),
                "transform": observation.get("transform"),
                "source_file_sha256": history_hash,
                "basis": observation.get("transform") or "Aspen final UOS raw-history result",
            })
    return diagnostics


def verified_run_status(parsed: dict[str, Any]) -> dict[str, int] | None:
    counts = parsed.get("counts")
    if not parsed.get("found") or not isinstance(counts, dict):
        return None
    required = ("terminal_errors", "severe_errors", "errors", "warnings")
    if any(not isinstance(counts.get(name), int) or counts[name] < 0 for name in required):
        return None
    return {name: counts[name] for name in required}


def create_aspen() -> tuple[Any, str]:
    import win32com.client as win32

    errors: list[str] = []
    for progid in ("Apwn.Document.40.0", "Apwn.Document"):
        try:
            app = win32.DispatchEx(progid)
            try:
                app.SuppressDialogs = True
                app.Visible = False
            except Exception:
                pass
            return app, progid
        except Exception as exc:
            errors.append(f"{progid}: {exc}")
    raise RuntimeError("Aspen COM 创建失败；可改用手动输入或 LLM 辅助模式。" + " | ".join(errors))


def open_case(app: Any, source: Path) -> tuple[str, list[str]]:
    if source.suffix.lower() == ".bkp":
        name = "InitFromArchive2"
        action = lambda: app.InitFromArchive2(str(source.resolve()))
    else:
        name = "InitFromFile2"
        action = lambda: app.InitFromFile2(str(source.resolve()))
    try:
        action()
        return name, []
    except Exception as exc:
        raise RuntimeError(f"Aspen 文件打开失败（{name}）；源文件未被修改：{exc}") from exc


def run_async(app: Any, timeout_s: int) -> dict[str, Any]:
    import pythoncom

    CONTROL_MESSAGES.clear()
    started = time.time()
    result: dict[str, Any] = {"started": now(), "timeout_s": timeout_s}
    try:
        app.Engine.ProcessInput()
        result["process_input"] = "returned"
    except Exception as exc:
        # Some already-processed archives do not expose ProcessInput through
        # every COM build.  Run2 remains the deciding operation, but the
        # diagnostic is retained instead of silently treating input processing
        # as verified.
        result["process_input"] = "unavailable"
        result["process_input_warning"] = str(exc)
    result["run2_return"] = repr(app.Engine.Run2(False))
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        pythoncom.PumpWaitingMessages()
        try:
            running = bool(app.Engine.IsRunning)
        except Exception:
            running = False
        if not running:
            for _ in range(20):
                pythoncom.PumpWaitingMessages()
                time.sleep(0.05)
            result.update({"status": "returned", "elapsed_s": round(time.time() - started, 3)})
            return result
        time.sleep(0.25)
    result.update({"status": "timeout", "elapsed_s": round(time.time() - started, 3)})
    return result


def request_run_artifacts(app: Any, work: Path, out_dir: Path) -> dict[str, Any]:
    """Ask Aspen to flush run evidence without touching the source archive.

    Aspen commonly finalizes the current ``.his`` beside a SaveAs target.  The
    target lives only in the isolated worker directory and is removed after the
    history has been copied and hashed.  REP/SUM/MSG exports are retained as
    diagnostics; only a parsed raw history can promote the formal process-basis
    gate.
    """

    result: dict[str, Any] = {"source_mutation_allowed": False}
    capture = work / "RUN_CAPTURE.bkp"
    try:
        app.SaveAs(str(capture.resolve()))
        result["save_as"] = {
            "status": "PASS" if capture.is_file() and capture.stat().st_size > 0 else "NO_FILE",
            "filename": capture.name,
            "size_bytes": capture.stat().st_size if capture.is_file() else 0,
        }
    except Exception as exc:
        result["save_as"] = {"status": "FAILED", "error": str(exc)}

    exports: dict[str, Any] = {}
    for name, export_type, filename in (
        ("report", 2, "raw_aspen_run_report.rep"),
        ("summary", 3, "raw_aspen_run_summary.sum"),
        ("messages", 6, "raw_aspen_run_messages.msg"),
    ):
        target = out_dir / filename
        try:
            app.Export(export_type, str(target.resolve()))
            exports[name] = {
                "status": "PASS" if target.is_file() and target.stat().st_size > 0 else "NO_FILE",
                "filename": target.name,
                "size_bytes": target.stat().st_size if target.is_file() else 0,
            }
        except Exception as exc:
            exports[name] = {"status": "FAILED", "error": str(exc)}
    result["exports"] = exports
    return result


def port_connections(block: Any) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    ports = named_child(block, "Ports")
    inlet: list[str] = []
    outlet: list[str] = []
    detail: list[dict[str, Any]] = []
    for port in node_elements(ports):
        name = node_name(port)
        streams = [node_name(stream) for stream in node_elements(port) if node_name(stream)]
        direction = "unknown"
        if "(IN)" in name.upper():
            inlet.extend(streams)
            direction = "in"
        elif "(OUT)" in name.upper():
            outlet.extend(streams)
            direction = "out"
        detail.append({"port": name, "direction": direction, "streams": streams})
    return list(dict.fromkeys(inlet)), list(dict.fromkeys(outlet)), detail


def connection_records(node: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    connections = named_child(node, "Connections")
    for child in node_elements(connections):
        rows.append({"name": node_name(child), "value": str(node_value(child) or "").strip()})
    return rows


def extract_bundle(
    tree: Any,
    case: dict[str, Any],
    in_units_fields: dict[str, str] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    units: dict[str, str] = {}
    warnings: list[dict[str, Any]] = []

    def register_unit(scope: str, field: str, unit: str, object_id: str) -> None:
        resolved, fallback_used = resolve_aspen_unit(field, unit, in_units_fields)
        if resolved is None:
            warnings.append({"code": "MISSING_UNITSTRING", "object": object_id, "field": field})
            return
        normalized = resolved
        if fallback_used:
            unit_set_key = RAW_FIELD_TO_IN_UNITS_KEY.get(field)
            from_unit_set = bool(
                unit_set_key
                and isinstance(in_units_fields, dict)
                and str(in_units_fields.get(unit_set_key) or "").strip()
            )
            warnings.append({
                "code": "IN_UNITS_FIELD_FALLBACK" if from_unit_set else "SEMANTIC_UNIT_FALLBACK",
                "object": object_id,
                "field": field,
                "unit": normalized,
                "in_units_field": unit_set_key if from_unit_set else None,
                "basis": (
                    "Aspen BKP-derived global IN-UNITS card"
                    if from_unit_set
                    else "Aspen named-card field semantics"
                ),
            })
        units[f"{scope}.{object_id}.{field}"] = normalized
        key = f"{scope}.{field}"
        existing = units.get(key)
        if existing and existing != normalized:
            warnings.append({"code": "CONFLICTING_UNITSTRING", "object": object_id, "field": field, "units": [existing, normalized]})
            return
        units[key] = normalized

    streams: list[dict[str, Any]] = []
    stream_record_types: dict[str, str] = {}
    stream_root = find_node(tree, r"\Data\Streams")
    for stream in node_elements(stream_root):
        stream_id = node_name(stream)
        if not stream_id:
            continue
        record_type, record_type_source = node_record_type(stream)
        stream_record_types[stream_id] = record_type
        stream_compstatus = node_compstatus(stream)
        row: dict[str, Any] = {
            "stream_id": stream_id,
            "stream_record_type": record_type or "UNKNOWN",
            "stream_record_type_source": record_type_source,
            "stream_compstatus": stream_compstatus,
            "connections": connection_records(stream),
            "aspen_raw_paths": {},
            "aspen_raw_values": {},
        }
        base = rf"\Data\Streams\{stream_id}"
        for field, paths in STREAM_FIELDS.items():
            value, unit, relative, value_type, value_status = read_first(
                tree, base, paths, stream_compstatus, require_continuous=True
            )
            if value is None:
                if value_status == "skipped_owner_no_results":
                    warnings.append({
                        "code": "OUTPUT_SKIPPED_NO_RESULTS",
                        "object": stream_id,
                        "field": field,
                        "path": base + "\\" + relative,
                        "compstatus": stream_compstatus,
                        "basis": "HAP_COMPSTATUS includes HAP_NORESULTS or HAP_NOT_RUN",
                    })
                elif value_status == "skipped_integer_node_for_continuous_field":
                    warnings.append({
                        "code": "CONTINUOUS_FIELD_SKIPPED_INTEGER_NODE",
                        "object": stream_id,
                        "field": field,
                        "path": base + "\\" + relative,
                        "value_type": value_type,
                        "basis": "IHNode.ValueType=1 is integer; target field requires a real physical quantity",
                    })
                continue
            row[field] = value
            row["aspen_raw_paths"][field] = base + "\\" + relative
            row["aspen_raw_values"][field] = {
                "value": value,
                "value_type": value_type,
                "unit": unit,
                "path": base + "\\" + relative,
                "status": value_status,
            }
            register_unit("stream", field, unit, stream_id)
        solid_fraction = finite(row.get("SFRAC_OUT"))
        solid_fraction_source = "SFRAC_OUT"
        if solid_fraction is None:
            solid_mass = finite(row.get("SOLID_MASSFLMX"))
            total_mass = finite(row.get("MASSFLMX"))
            if solid_mass is not None and total_mass is not None and total_mass > 0:
                solid_fraction = solid_mass / total_mass
                solid_fraction_source = "SOLID_MASSFLMX/MASSFLMX"
        if solid_fraction is not None:
            if 0.0 <= solid_fraction <= 1.0:
                row["solid_fraction"] = solid_fraction
                row["solid_fraction_source"] = solid_fraction_source
                register_unit("stream", "solid_fraction", "-", stream_id)
            else:
                warnings.append({
                    "code": "SOLID_FRACTION_OUT_OF_RANGE",
                    "object": stream_id,
                    "field": solid_fraction_source,
                    "value": solid_fraction,
                    "allowed_range": [0.0, 1.0],
                    "action": "solid_phase_not_inferred",
                })
                solid_fraction = None
        phase_inference = phase_from_vapor_fraction(row.get("VFRAC_OUT"))
        if phase_inference["status"] != "UNAVAILABLE":
            row["phase_inference"] = phase_inference
        inferred_phase = (
            "solid_bearing"
            if solid_fraction is not None and solid_fraction > VAPOR_FRACTION_ENDPOINT_TOLERANCE
            else phase_inference.get("phase")
        )
        if inferred_phase is not None:
            row["phase"] = inferred_phase
            row["phase_origin"] = (
                "EXACT_DERIVATION_FROM_SOLID_FRACTION"
                if inferred_phase == "solid_bearing"
                else "EXACT_DERIVATION_FROM_VFRAC_OUT"
            )
            row["phase_source_field"] = solid_fraction_source if inferred_phase == "solid_bearing" else "VFRAC_OUT"
            if inferred_phase == "liquid" and project_stream_phase_observation(
                row,
                source_field="VOLFLMX",
                target_field="VOLFLMX_LIQ",
                phase="liquid",
            ):
                register_unit("stream", "VOLFLMX_LIQ", units.get("stream.VOLFLMX", ""), stream_id)
            elif inferred_phase == "vapor" and project_stream_phase_observation(
                row,
                source_field="VOLFLMX",
                target_field="VOLFLMX_GAS",
                phase="vapor",
            ):
                register_unit("stream", "VOLFLMX_GAS", units.get("stream.VOLFLMX", ""), stream_id)
        elif phase_inference["status"] == "INVALID_OUT_OF_RANGE":
            warnings.append({
                "code": "VAPOR_FRACTION_OUT_OF_RANGE",
                "object": stream_id,
                "field": "VFRAC_OUT",
                "value": phase_inference.get("raw_vapor_fraction"),
                "allowed_range": [0.0, 1.0],
                "endpoint_tolerance": VAPOR_FRACTION_ENDPOINT_TOLERANCE,
                "action": "phase_not_inferred",
            })
        viscosity_source_field = {
            "liquid": "MUMX_LIQUID",
            "solid_bearing": "MUMX_LIQUID",
            "vapor": "MUMX_VAPOR",
        }.get(str(inferred_phase or ""))
        if viscosity_source_field and viscosity_source_field in row:
            row["MUMX"] = row[viscosity_source_field]
            source_path = row["aspen_raw_paths"].get(viscosity_source_field)
            source_record = row["aspen_raw_values"].get(viscosity_source_field)
            if source_path:
                row["aspen_raw_paths"]["MUMX"] = source_path
            if isinstance(source_record, dict):
                row["aspen_raw_values"]["MUMX"] = {
                    **source_record,
                    "phase_selection": inferred_phase,
                    "phase_source_field": row.get("phase_source_field"),
                }
            source_unit = (
                units.get(f"stream.{stream_id}.{viscosity_source_field}")
                or units.get(f"stream.{viscosity_source_field}")
                or ""
            )
            register_unit("stream", "MUMX", source_unit, stream_id)
            row["dynamic_viscosity_phase_selection"] = {
                "status": "PURE_OR_CONTINUOUS_PHASE_SELECTED",
                "selected_raw_field": viscosity_source_field,
                "phase": inferred_phase,
                "source_path": source_path,
            }
        elif inferred_phase == "two_phase":
            available_phase_fields = [
                field for field in ("MUMX_LIQUID", "MUMX_VAPOR")
                if field in row
            ]
            row["dynamic_viscosity_phase_selection"] = {
                "status": "TWO_PHASE_NO_SINGLE_EFFECTIVE_VISCOSITY",
                "available_raw_fields": available_phase_fields,
                "phase": inferred_phase,
            }
            warnings.append({
                "code": "TWO_PHASE_EFFECTIVE_VISCOSITY_NOT_DEFINED",
                "object": stream_id,
                "available_raw_fields": available_phase_fields,
                "action": (
                    "retain Aspen liquid/vapor phase viscosities separately; "
                    "do not invent a single mixture viscosity"
                ),
            })
        composition = extract_stream_composition(
            tree,
            base,
            stream_id,
            stream_compstatus,
            warnings,
        )
        if composition:
            row["composition"] = composition
            row["composition_basis"] = composition[0]["basis"]
        streams.append(row)

    blocks: list[dict[str, Any]] = []
    equipment_map: list[dict[str, Any]] = []
    block_root = find_node(tree, r"\Data\Blocks")
    for block in node_elements(block_root):
        block_id = node_name(block)
        if not block_id:
            continue
        block_type, block_type_source = node_record_type(block)
        icon_token = str(node_value(block) or "").strip()
        if not block_type:
            block_type = "UNKNOWN"
        if block_type_source.startswith("missing:"):
            warnings.append({
                "code": "BLOCKED_MODEL_IDENTITY",
                "object": block_id,
                "icon_token": icon_token,
                "required": "AttributeValue(6):HAP_RECORDTYPE",
            })
        inlet_all, outlet_all, port_detail = port_connections(block)
        block_compstatus = node_compstatus(block)
        inlet = [stream for stream in inlet_all if stream_record_types.get(stream, "MATERIAL") == "MATERIAL"]
        outlet = [stream for stream in outlet_all if stream_record_types.get(stream, "MATERIAL") == "MATERIAL"]
        connections = connection_records(block)
        connection_inlet = [item["name"] for item in connections if "(IN)" in item["value"].upper() and stream_record_types.get(item["name"], "MATERIAL") == "MATERIAL"]
        connection_outlet = [item["name"] for item in connections if "(OUT)" in item["value"].upper() and stream_record_types.get(item["name"], "MATERIAL") == "MATERIAL"]
        if connection_inlet and set(connection_inlet) != set(inlet):
            warnings.append({"code": "BLOCKED_CONNECTIVITY_CONFLICT", "object": block_id, "direction": "in", "ports": inlet, "connections": connection_inlet})
        if connection_outlet and set(connection_outlet) != set(outlet):
            warnings.append({"code": "BLOCKED_CONNECTIVITY_CONFLICT", "object": block_id, "direction": "out", "ports": outlet, "connections": connection_outlet})
        row: dict[str, Any] = {
            "block_id": block_id,
            "block_type": block_type,
            "block_type_source": block_type_source,
            "icon_token": icon_token,
            "block_compstatus": block_compstatus,
            "inlet_streams": inlet,
            "outlet_streams": outlet,
            "port_detail": port_detail,
            "connections": connections,
            "aspen_raw_paths": {},
            "aspen_raw_values": {},
        }
        base = rf"\Data\Blocks\{block_id}"
        block_status_node = find_node(tree, base + r"\Output\BLKSTAT")
        if owner_has_no_results(block_compstatus):
            if block_status_node is not None:
                warnings.append({
                    "code": "OUTPUT_SKIPPED_NO_RESULTS",
                    "object": block_id,
                    "field": "BLKSTAT",
                    "path": base + r"\Output\BLKSTAT",
                    "compstatus": block_compstatus,
                    "basis": "HAP_COMPSTATUS includes HAP_NORESULTS or HAP_NOT_RUN",
                })
        else:
            status = node_value(block_status_node)
            if status is not None:
                row["block_status"] = status
        for field, paths in BLOCK_FIELDS.items():
            value, unit, relative, value_type, value_status = read_first(
                tree,
                base,
                paths,
                block_compstatus,
                require_continuous=field != "NSTAGE",
            )
            if value is None:
                if value_status == "skipped_owner_no_results":
                    warnings.append({
                        "code": "OUTPUT_SKIPPED_NO_RESULTS",
                        "object": block_id,
                        "field": field,
                        "path": base + "\\" + relative,
                        "compstatus": block_compstatus,
                        "basis": "HAP_COMPSTATUS includes HAP_NORESULTS or HAP_NOT_RUN",
                    })
                elif value_status == "skipped_integer_node_for_continuous_field":
                    warnings.append({
                        "code": "CONTINUOUS_FIELD_SKIPPED_INTEGER_NODE",
                        "object": block_id,
                        "field": field,
                        "path": base + "\\" + relative,
                        "value_type": value_type,
                        "basis": "IHNode.ValueType=1 is integer; target field requires a real physical quantity",
                    })
                continue
            row[field] = value
            row["aspen_raw_paths"][field] = base + "\\" + relative
            raw_observation = {
                "value": value,
                "value_type": value_type,
                "unit": unit,
                "path": base + "\\" + relative,
                "status": value_status,
            }
            quantity_kind = block_field_quantity_kind(field, block_type)
            if quantity_kind:
                raw_observation["quantity_kind"] = quantity_kind
            if field == "WNET":
                raw_observation["semantic_warning"] = (
                    "Aspen WNET is retained as its own raw net-work/utility "
                    "channel and must not be interpreted as pump brake/shaft "
                    "power."
                )
            row["aspen_raw_values"][field] = raw_observation
            register_unit("block", field, unit, block_id)
        blocks.append(row)
        equipment_map.append({
            "block_id": block_id,
            "equipment_tag": block_id,
            "process_function": PROCESS_FUNCTIONS.get(block_type, "Aspen module; physical equipment role requires review"),
        })

    bundle = {
        "schema": "aspen-equipment-export-v1",
        "case": case,
        "units": units,
        "streams": streams,
        "blocks": blocks,
        "equipment_map": equipment_map,
    }
    return bundle, warnings


def close_aspen(app: Any | None) -> None:
    if app is None:
        return
    try:
        app.Close(False)
    except Exception:
        pass
    try:
        app.Quit()
    except Exception:
        pass


def write_and_derive(bundle: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    bundle_path = out_dir / "aspen_equipment_export.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    reloaded = json.loads(bundle_path.read_text(encoding="utf-8"))
    # First persist a topology-safe PFD.  Without the derivation adapter this
    # projection may display only explicitly canonical field names; raw Aspen
    # aliases are never relabelled with target units.  If derivation succeeds,
    # the same file is rewritten below with the unit-normalized cards.
    pfd_mapping = aspen_pfd.build_pfd_mapping(reloaded)
    pfd_path = out_dir / "aspen_pfd_mapping.json"
    pfd_path.write_text(
        json.dumps(pfd_mapping, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result = derivation.derive_bundle(reloaded, bundle_path)
    result_path = out_dir / "equipment_derivation_result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    canonical_blocks = aspen_pfd.canonical_parameters_by_block(result)
    canonical_streams = aspen_pfd.canonical_parameters_by_stream(result)
    pfd_mapping = aspen_pfd.build_pfd_mapping(
        reloaded,
        canonical_parameters_by_block=canonical_blocks,
        canonical_parameters_by_stream=canonical_streams,
        parameter_normalization_issues=(
            result.get("normalization_diagnostics")
            if isinstance(result.get("normalization_diagnostics"), list)
            else result.get("errors") if isinstance(result.get("errors"), list) else ()
        ),
    )
    pfd_path.write_text(
        json.dumps(pfd_mapping, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    pfd_summary = aspen_pfd.summarize_pfd_mapping(pfd_mapping)
    return {
        "bundle": str(bundle_path),
        "derivation": str(result_path),
        "result": result,
        "pfd_mapping": str(pfd_path),
        "pfd_mapping_file_sha256": sha256(pfd_path),
        "mapping_sha256": pfd_mapping["mapping_sha256"],
        "pfd_summary": pfd_summary,
    }


def build_run_evidence(case_id: str, history_path: Path, parsed: dict[str, Any], out_dir: Path) -> tuple[Path, dict[str, Any]]:
    if not parsed.get("found") or not history_path.is_file():
        raise ValueError("运行历史中未找到可复核的四类计数。")
    evidence = {
        "schema": "aspen-run-status-evidence-v1",
        "case_id": case_id,
        "raw_history_path": history_path.name,
        "raw_history_sha256": sha256(history_path),
        "raw_history_kind": "aspen_his",
        "run_status": parsed["counts"],
    }
    evidence_path = out_dir / "aspen_run_status_evidence.json"
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    return evidence_path, evidence


def run_mock(
    fixture_path: Path,
    out_dir: Path,
    pressure_basis: str | None = None,
    atmospheric_pressure_mpa: float | None = None,
) -> dict[str, Any]:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    bundle = fixture["bundle"]
    if pressure_basis is not None:
        bundle["case"]["pressure_basis"] = pressure_basis
    if atmospheric_pressure_mpa is not None:
        bundle["case"]["atmospheric_pressure_mpa"] = atmospheric_pressure_mpa
    else:
        bundle["case"].pop("atmospheric_pressure_mpa", None)
    case_id = str(bundle["case"]["case_id"])
    history = out_dir / "mock_aspen_history.his"
    history.write_text(str(fixture.get("history_text", "NO ERRORS OR WARNINGS GENERATED\n")), encoding="utf-8")
    parsed = parse_aspen_history(history.read_text(encoding="utf-8"))
    evidence_path, evidence = build_run_evidence(case_id, history, parsed, out_dir)
    bundle["case"]["source_case_path"] = str(fixture_path)
    bundle["case"]["run_status"] = evidence["run_status"]
    bundle["case"]["run_status_evidence_path"] = evidence_path.name
    bundle["case"]["run_status_evidence_sha256"] = sha256(evidence_path)
    pipeline = write_and_derive(bundle, out_dir)
    return {
        "schema": "equipment-design-app-aspen-worker-v1",
        "status": "PASS_MOCK",
        "mock": True,
        "history_parse": parsed,
        **pipeline,
    }


def run_real(
    source: Path,
    out_dir: Path,
    pressure_basis: str,
    atmospheric_pressure_mpa: float | None,
    run: bool,
    timeout_s: int,
    ensure_stream_transport: bool = False,
) -> dict[str, Any]:
    if os.environ.get("EQUIPMENT_BACKEND_ALLOW_COM") != "1":
        raise RuntimeError("COM_EXECUTION_NOT_AUTHORIZED: explicit optional COM permission is required")
    import pythoncom
    import win32com.client as win32

    out_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="EquipmentDesignAspen_"))
    staged = work / f"SOURCE{source.suffix.lower()}"
    shutil.copy2(source, staged)
    source_sha256 = sha256(source)
    staged_copy_sha256 = sha256(staged)
    if source_sha256 != staged_copy_sha256:
        raise RuntimeError("BLOCKED_SOURCE_STAGE_HASH_MISMATCH")
    staged_sidecars = stage_aspen_sidecars(source, staged)
    app = None
    event_handler = None
    transport_manifest: dict[str, Any] | None = None
    transport_manifest_path: Path | None = None
    metadata: dict[str, Any] = {
        "source": str(source),
        "source_sha256": source_sha256,
        "staged": str(staged),
        "staged_copy_sha256": staged_copy_sha256,
        "staged_copy_hash_matches_source": True,
        "staged_sidecars": staged_sidecars,
        "started": now(),
    }
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    lock = WORKSPACE_ROOT / "_aspen_com_global.lock"
    old_cwd = Path.cwd()
    old_temp = os.environ.get("TEMP")
    old_tmp = os.environ.get("TMP")
    with AspenLock(lock):
        try:
            pythoncom.CoInitialize()
            os.chdir(work)
            os.environ["TEMP"] = str(work)
            os.environ["TMP"] = str(work)
            app, progid = create_aspen()
            metadata["progid"] = progid
            open_method, open_errors = open_case(app, staged)
            metadata.update({"open_method": open_method, "open_errors": open_errors})
            event_handler = win32.WithEvents(app, AspenEvents)
            if ensure_stream_transport:
                if not run:
                    raise ValueError(
                        "--ensure-stream-transport requires --run because "
                        "new Aspen properties must be recalculated"
                    )
                (
                    transport_manifest,
                    transport_manifest_path,
                ) = ensure_stream_transport_property_via_com(
                    app,
                    out_dir,
                    source,
                )
                metadata["transport_property_augmentation"] = transport_manifest
                metadata["transport_property_augmentation"][
                    "com_reload_status"
                ] = "NOT_USED_DIRECT_COM_TREE_MUTATION"
            if run:
                metadata["run"] = run_async(app, timeout_s)
                if metadata["run"].get("status") != "returned":
                    raise RuntimeError(f"Aspen 运行未正常返回：{metadata['run']}")
            else:
                metadata["run"] = {"status": "not_requested"}
            case_id = re.sub(r"[^A-Za-z0-9_-]+", "_", source.stem)[:64] or "ASPEN_CASE"
            case: dict[str, Any] = {
                "case_id": case_id,
                "pressure_basis": pressure_basis,
                "source_case_path": str(source),
                "source_case_sha256": sha256(source),
                "run_status": None,
                "run_requested": run,
            }
            if atmospheric_pressure_mpa is not None:
                case["atmospheric_pressure_mpa"] = atmospheric_pressure_mpa

            # Export the active BKP to text first so its own IN-UNITS field
            # names/values are available as a deterministic fallback. Export
            # is read-only for the source archive and does not replace the live
            # COM tree as the primary source of field values or UnitString.
            ascii_export = work / "AFTER.INP"
            in_units_cards: list[dict[str, Any]] = []
            in_units_global: dict[str, Any] | None = None
            try:
                app.Export(4, str(ascii_export.resolve()))
                if ascii_export.is_file():
                    ascii_text = ascii_export.read_text(encoding="utf-8", errors="replace")
                    in_units_cards = parse_in_units_cards(ascii_text)
                    in_units_global = global_in_units(in_units_cards)
                    shutil.copy2(ascii_export, out_dir / "after_run_or_current.inp")
            except Exception as exc:
                metadata["inp_export_warning"] = str(exc)
            case["aspen_in_units_cards"] = in_units_cards
            case["aspen_global_in_units"] = in_units_global
            metadata["aspen_in_units_card_count"] = len(in_units_cards)
            metadata["aspen_global_unit_set"] = (
                str((in_units_global or {}).get("unit_set") or "") or None
            )
            metadata["aspen_global_in_units_fields"] = dict(
                (in_units_global or {}).get("fields") or {}
            )

            # Read the live COM tree before SaveAs changes the active document
            # identity.  The source archive itself remains untouched.
            bundle, extraction_warnings = extract_bundle(
                app.Tree,
                case,
                (in_units_global or {}).get("fields") if in_units_global else None,
            )
            transport_verification = verify_stream_transport_properties(bundle)
            (
                transport_manifest,
                transport_manifest_path,
                transport_verification_path,
            ) = persist_stream_transport_evidence(
                out_dir,
                source,
                transport_verification,
                augmentation_requested=ensure_stream_transport,
                run_result=metadata.get("run"),
                manifest=transport_manifest,
            )
            metadata["stream_transport_verification"] = transport_verification
            metadata["stream_transport_verification_path"] = (
                transport_verification_path.name
            )
            metadata["stream_transport_verification_sha256"] = sha256(
                transport_verification_path
            )
            metadata["transport_property_augmentation"] = transport_manifest
            bundle["case"]["stream_transport_verification"] = transport_verification
            bundle["case"]["stream_transport_verification_path"] = (
                transport_verification_path.name
            )
            bundle["case"]["stream_transport_verification_sha256"] = sha256(
                transport_verification_path
            )
            if transport_verification["status"] != "PASS":
                extraction_warnings.append({
                    "code": "BLOCKED_TRANSPORT_PROPERTY_EXTRACTION_AFTER_RUN",
                    "missing_stream_count": transport_verification["missing_stream_count"],
                    "missing": transport_verification["missing"],
                    "augmentation_requested": ensure_stream_transport,
                    "action": (
                        "do_not_default_viscosity; retain blocked state and inspect "
                        "the isolated Aspen property-set rerun evidence"
                    ),
                })
            bundle["case"]["transport_property_augmentation_manifest_path"] = (
                transport_manifest_path.name
            )
            bundle["case"]["transport_property_augmentation_manifest_sha256"] = (
                sha256(transport_manifest_path)
            )
            bundle["case"]["com_extraction_warnings"] = extraction_warnings
            bundle["case"]["com_extraction_blockers"] = [
                item for item in extraction_warnings if str(item.get("code", "")).startswith("BLOCKED_")
            ]
            if run:
                metadata["run_artifact_capture"] = request_run_artifacts(app, work, out_dir)

            # A SaveAs history is commonly finalized only when Aspen closes.
            # Close the isolated document now, then discover evidence before
            # deleting the worker directory.  The finally block remains a
            # harmless second-close guard.
            event_handler = None
            close_aspen(app)
            app = None
            time.sleep(0.1)

            control_path = out_dir / "control_panel_capture.txt"
            control_path.write_text("\n".join(CONTROL_MESSAGES) + ("\n" if CONTROL_MESSAGES else ""), encoding="utf-8")
            histories = sorted(work.rglob("*.his"), key=lambda path: path.stat().st_mtime, reverse=True)
            history_path: Path | None = None
            parsed = {"found": False, "counts": None, "problem_lines": []}
            if histories:
                history_path = out_dir / "raw_aspen_run_history.his"
                shutil.copy2(histories[0], history_path)
                parsed = parse_aspen_history(history_path.read_text(encoding="utf-8", errors="replace"))
                metadata["history_source"] = str(histories[0].relative_to(work))
            elif CONTROL_MESSAGES:
                parsed = parse_aspen_history(control_path.read_text(encoding="utf-8", errors="replace"))
                metadata["history_source"] = "control_panel_capture.txt"

            run_status = verified_run_status(parsed)
            case["run_status"] = run_status
            if history_path is not None and parsed.get("found"):
                history_text = history_path.read_text(encoding="utf-8", errors="replace")
                recovered_results = parse_history_block_results(history_text)
                history_fallback_diagnostics = merge_history_block_results(
                    bundle,
                    recovered_results,
                    history_path,
                )
                extraction_warnings.extend(history_fallback_diagnostics)
                metadata["history_result_fallback_count"] = sum(
                    1
                    for item in history_fallback_diagnostics
                    if item.get("code") == "RAW_HISTORY_RESULT_FALLBACK"
                )
                evidence_path, _ = build_run_evidence(case_id, history_path, parsed, out_dir)
                case["run_status_evidence_path"] = evidence_path.name
                case["run_status_evidence_sha256"] = sha256(evidence_path)

            pipeline = write_and_derive(bundle, out_dir)
            worker_status = (
                "PASS"
                if transport_verification["status"] == "PASS"
                else "BLOCKED_TRANSPORT_PROPERTY_VERIFICATION"
            )
            metadata.update({
                "status": worker_status,
                "history_parse": parsed,
                "stream_count": len(bundle["streams"]),
                "block_count": len(bundle["blocks"]),
                "extraction_warning_count": len(extraction_warnings),
                "finished": now(),
            })
            return {"schema": "equipment-design-app-aspen-worker-v1", **metadata, **pipeline}
        finally:
            event_handler = None
            close_aspen(app)
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
            os.chdir(old_cwd)
            if old_temp is None:
                os.environ.pop("TEMP", None)
            else:
                os.environ["TEMP"] = old_temp
            if old_tmp is None:
                os.environ.pop("TMP", None)
            else:
                os.environ["TMP"] = old_tmp
            shutil.rmtree(work, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aspen BKP read/run/traverse worker for the equipment-design app.")
    parser.add_argument("--source")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--pressure-basis", choices=["absolute", "gauge"], required=True)
    parser.add_argument("--atmospheric-pressure-mpa", type=float)
    parser.add_argument("--run", action="store_true")
    parser.add_argument(
        "--ensure-stream-transport",
        action="store_true",
        help=(
            "On the isolated Aspen copy, add/request MUMX directly through the "
            "live COM tree and rerun when the report request is absent."
        ),
    )
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--mock-fixture")
    args = parser.parse_args(argv)
    if not args.mock_fixture and os.environ.get("EQUIPMENT_BACKEND_ALLOW_COM") != "1":
        print(json.dumps({"status": "dependency_unavailable", "reason": "COM_EXECUTION_NOT_AUTHORIZED", "outputs_created": False}))
        return 2
    if args.pressure_basis == "gauge" and args.atmospheric_pressure_mpa is None:
        parser.error("--pressure-basis gauge requires --atmospheric-pressure-mpa")
    if args.atmospheric_pressure_mpa is not None and args.atmospheric_pressure_mpa <= 0:
        parser.error("--atmospheric-pressure-mpa must be greater than zero")
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / "worker_result.json"
    result: dict[str, Any]
    rc = 0
    try:
        if args.mock_fixture:
            result = run_mock(
                Path(args.mock_fixture).resolve(),
                out_dir,
                args.pressure_basis,
                args.atmospheric_pressure_mpa,
            )
        else:
            if not args.source:
                raise ValueError("缺少 --source。")
            source = Path(args.source).resolve()
            if not source.is_file():
                raise FileNotFoundError(source)
            if source.suffix.lower() not in {".bkp", ".apw", ".inp"}:
                raise ValueError("自动导入支持 .bkp、.apw、.inp；其他情况请用手动模式。")
            result = run_real(
                source,
                out_dir,
                args.pressure_basis,
                args.atmospheric_pressure_mpa,
                args.run,
                max(10, min(args.timeout, 7200)),
                args.ensure_stream_transport,
            )
    except Exception as exc:
        result = {
            "schema": "equipment-design-app-aspen-worker-v1",
            "status": "FAILED",
            "error": str(exc),
            "fallback": "manual_or_llm_mode",
            "traceback": traceback.format_exc(),
        }
        rc = 2
    if rc == 0 and result.get("status") not in {"PASS", "PASS_MOCK"}:
        rc = 3
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": result.get("status"), "worker_result": str(result_path)}, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
