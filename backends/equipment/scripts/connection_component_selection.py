from __future__ import annotations

import csv
import functools
import hashlib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Mapping


SCHEMA = "equipment-connection-selection-package-v1"
ENGINE_VERSION = "1.3.0"
COMPONENT_FAMILIES = (
    "flange_type",
    "facing",
    "gasket_type",
    "fastener_type",
)
LOGIC_BLOCK_TYPES = frozenset({"FSPLIT", "MIXER", "HIERARCHY"})
DIRECT_LABEL_FIELDS = frozenset({
    "service_labels",
    "condition_labels",
    "derived_service_labels",
    "phase",
    "corrosivity",
    "toxicity",
    "flammability",
    "explosivity",
    "oxidizing",
    "vacuum_level",
    "severe_corrosion",
    "crevice_corrosion_risk",
    "cleanliness",
    "leak_tightness",
    "fire_safe_required",
    "cleanability_required",
})
DIRECT_LABEL_ALIASES = {
    "corrosive": "corrosivity",
    "toxic": "toxicity",
    "flammable": "flammability",
}
MECHANICAL_FIELDS = frozenset({
    "system_series",
    "pn",
    "class_rating",
    "dn_mm",
    "nominal_diameter_mm",
    "pressure_tap_connection",
    "gasket_family_preference",
    "flush_bore_required",
    "user_forced_candidate_id",
})
PROPERTY_FACTS = frozenset({
    "corrosivity",
    "toxicity",
    "flammability",
    "explosivity",
    "oxidizing",
    "crevice_corrosion_risk",
    "severe_corrosion",
    "cleanliness",
    "leak_tightness",
    "severe_cyclic",
    "thermal_shock",
    "utility_service",
    "instrument_service",
    "low_sealing_demand",
    "lining_material",
    "flange_material_group",
    "mating_material_group",
    "current_facing",
    "ring_joint_required",
    "core_corrosion_risk",
    "fire_safe_required",
    "cleanability_required",
    "jacketed_pipe",
    "orifice_service",
    "closure_required",
    "internal_component_connection",
})
MIXTURE_DEPENDENT_FACTS = frozenset({
    "corrosivity",
    "toxicity",
    "flammability",
    "explosivity",
    "oxidizing",
    "crevice_corrosion_risk",
    "severe_corrosion",
})
SOURCE_QA_STATES = frozenset({"VALIDATED", "PROMOTED", "ACCEPTED"})
SHA256_PATTERN = re.compile(r"^[A-Fa-f0-9]{64}$")
CANONICAL_PHASES = frozenset({"liquid", "vapor", "two_phase", "solid_bearing"})
PROPERTY_FACT_ENUMS = {
    "corrosivity": frozenset({"none", "low", "moderate", "high", "severe"}),
    "toxicity": frozenset({"normal", "moderate", "high", "extreme"}),
    "flammability": frozenset({"nonflammable", "flammable", "highly_flammable"}),
    "explosivity": frozenset({"none", "possible", "explosive"}),
    "cleanliness": frozenset({"ordinary", "clean", "high_purity", "sterile"}),
    "leak_tightness": frozenset({"ordinary", "enhanced", "high", "zero_emission"}),
    "vacuum_level": frozenset({"none", "vacuum", "high_vacuum"}),
    "lining_material": frozenset({"none", "stainless", "nickel", "titanium", "other"}),
    "flange_material_group": frozenset({"steel", "stainless", "nickel", "titanium", "cast_iron", "other"}),
    "mating_material_group": frozenset({"steel", "stainless", "nickel", "titanium", "cast_iron", "other"}),
    "current_facing": frozenset({"RF", "FF", "FM/M", "T/G", "RJ"}),
}
PROPERTY_BOOL_FACTS = frozenset({
    "severe_cyclic", "thermal_shock", "oxidizing", "crevice_corrosion_risk",
    "severe_corrosion", "utility_service", "instrument_service",
    "low_sealing_demand", "ring_joint_required", "core_corrosion_risk",
    "fire_safe_required", "cleanability_required", "jacketed_pipe",
    "orifice_service", "closure_required", "internal_component_connection",
})
FACT_BINDING_FIELDS = (
    "source_id", "fact", "value", "qa_status", "subject_scope", "stream_id",
    "block_id", "connection_id", "project_context_sha256", "composition_sha256",
    "valid_phase", "valid_phases", "valid_temperature_min_c",
    "valid_temperature_max_c", "valid_pressure_min_mpa",
    "valid_pressure_max_mpa", "pressure_basis",
)

SCRIPT_PATH = Path(__file__).resolve()
FROZEN_ROOT = getattr(sys, "_MEIPASS", None)
PACKAGE_ROOT = Path(FROZEN_ROOT).resolve() if FROZEN_ROOT else SCRIPT_PATH.parents[1]
SELECTOR_ROOT = (
    PACKAGE_ROOT
    / "knowledge_graph"
    / "type_selection"
    / "hgt20592_20635"
)
MANIFEST_PATH = SELECTOR_ROOT / "hash_manifest.csv"
SELECTOR_PATH = SELECTOR_ROOT / "select_terminal_type.py"


class ConnectionComponentSelectionError(RuntimeError):
    pass


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _trusted_graph_asset(path_value: Any, expected_sha256: str) -> Path | None:
    text = str(path_value or "").strip()
    if not text or not SHA256_PATTERN.fullmatch(expected_sha256):
        return None
    path = Path(text)
    if not path.is_absolute():
        path = PACKAGE_ROOT / path
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to((PACKAGE_ROOT / "knowledge_graph").resolve())
    except (OSError, ValueError):
        return None
    if not resolved.is_file() or resolved.is_symlink():
        return None
    return resolved if sha256_file(resolved) == expected_sha256.upper() else None


@functools.lru_cache(maxsize=64)
def _asset_records(asset_path: str, asset_sha256: str) -> tuple[dict[str, Any], ...]:
    path = _trusted_graph_asset(asset_path, asset_sha256)
    if path is None:
        return ()
    if path.suffix.casefold() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return tuple(dict(row) for row in csv.DictReader(handle))
    if path.suffix.casefold() in {".json", ".jsonl"}:
        if path.suffix.casefold() == ".jsonl":
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        else:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(value, list):
                rows = value
            elif isinstance(value, dict) and isinstance(value.get("records"), list):
                rows = value["records"]
            else:
                rows = [value]
        return tuple(dict(row) for row in rows if isinstance(row, Mapping))
    return ()


def _fact_record_from_graph_asset(fact: Mapping[str, Any]) -> dict[str, Any] | None:
    asset_path = str(fact.get("source_asset_path") or "")
    asset_sha256 = str(fact.get("source_asset_sha256") or "").upper()
    record_sha256 = str(fact.get("source_record_sha256") or "").upper()
    if not SHA256_PATTERN.fullmatch(record_sha256):
        return False
    for row in _asset_records(asset_path, asset_sha256):
        if canonical_sha256(row) != record_sha256:
            continue
        return dict(row)
    return None


def _semantic_token(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).casefold()
    return str(value if value is not None else "").strip().casefold()


def _record_metadata_matches_request(
    record: Mapping[str, Any],
    request: Mapping[str, Any],
) -> bool:
    """Caller metadata may locate a record but may never widen its semantics."""

    for field in FACT_BINDING_FIELDS:
        if field not in request:
            continue
        if _semantic_token(request.get(field)) != _semantic_token(record.get(field)):
            return False
    return True


# Backward-compatible internal test hook. Production callers consume the
# authoritative row returned above rather than trusting caller-supplied fields.
def _fact_exists_in_graph_asset(fact: Mapping[str, Any]) -> dict[str, Any] | None:
    return _fact_record_from_graph_asset(fact)


@functools.lru_cache(maxsize=1)
def verify_selector_package() -> dict[str, Any]:
    if not MANIFEST_PATH.is_file():
        raise ConnectionComponentSelectionError("HG/T selector manifest is missing")
    manifest_sha256 = sha256_file(MANIFEST_PATH)
    records: list[dict[str, Any]] = []
    with MANIFEST_PATH.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            relative = str(row.get("relative_path") or "").strip()
            expected = str(row.get("sha256") or "").strip().upper()
            expected_size = int(str(row.get("size_bytes") or "0"))
            if not relative or not SHA256_PATTERN.fullmatch(expected):
                raise ConnectionComponentSelectionError("invalid HG/T selector manifest row")
            asset = (SELECTOR_ROOT / relative).resolve()
            try:
                asset.relative_to(SELECTOR_ROOT.resolve())
            except ValueError as exc:
                raise ConnectionComponentSelectionError("selector asset escapes package root") from exc
            if not asset.is_file() or asset.is_symlink():
                raise ConnectionComponentSelectionError(f"selector asset missing: {relative}")
            actual_size = int(asset.stat().st_size)
            actual = sha256_file(asset)
            if actual_size != expected_size or actual != expected:
                raise ConnectionComponentSelectionError(f"selector asset mismatch: {relative}")
            records.append({"relative_path": relative, "sha256": actual, "size_bytes": actual_size})
    if not records or not any(item["relative_path"] == "select_terminal_type.py" for item in records):
        raise ConnectionComponentSelectionError("selector manifest does not bind the executable selector")
    return {
        "status": "VERIFIED",
        "manifest_path": str(MANIFEST_PATH),
        "manifest_sha256": manifest_sha256,
        "asset_count": len(records),
    }


@functools.lru_cache(maxsize=1)
def _selector_module() -> ModuleType:
    verify_selector_package()
    spec = importlib.util.spec_from_file_location(
        "equipment_hgt20592_20635_terminal_selector",
        SELECTOR_PATH,
    )
    if spec is None or spec.loader is None:
        raise ConnectionComponentSelectionError("cannot load HG/T selector module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # The source selector deliberately reads only frozen CSV/JSON assets. Cache
    # each table after its first read so a resident process does not reload the
    # same equipment-family authority for every connection/component call.
    module.read_csv = functools.lru_cache(maxsize=None)(module.read_csv)
    return module


def _finite(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and abs(result) != float("inf") else None


def _stream_kind(stream: Mapping[str, Any]) -> str:
    record_type = str(stream.get("stream_record_type") or "").strip().upper()
    if record_type in {"", "MATERIAL"}:
        return "material"
    if record_type in {"HEAT", "ENERGY", "QSTREAM"}:
        return "heat"
    if record_type in {"WORK", "WSTREAM"}:
        return "work"
    return "unknown"


def _composition(stream: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = stream.get("composition")
    if not isinstance(rows, list):
        return []
    normalized = [
        {
            "component_id": str(item.get("component_id") or "").strip().upper(),
            "fraction": float(item["fraction"]),
            "basis": str(item.get("basis") or ""),
            "source_path": str(item.get("source_path") or ""),
        }
        for item in rows
        if isinstance(item, Mapping)
        and str(item.get("component_id") or "")
        and _finite(item.get("fraction")) is not None
    ]
    return sorted(normalized, key=lambda item: (item["basis"], item["component_id"]))


def composition_context_sha256(stream: Mapping[str, Any]) -> str:
    valid, _reason = _composition_binding_status(stream)
    if not valid:
        return ""
    semantic_rows = [
        {
            "component_id": item["component_id"],
            "fraction": item["fraction"],
            "basis": item["basis"],
        }
        for item in _composition(stream)
    ]
    return canonical_sha256(semantic_rows) if semantic_rows else ""


def _composition_binding_status(stream: Mapping[str, Any]) -> tuple[bool, str]:
    rows = _composition(stream)
    if not rows:
        return False, "mixture_composition_missing"
    component_ids = [item["component_id"] for item in rows]
    if len(component_ids) != len(set(component_ids)):
        return False, "mixture_composition_has_duplicate_components"
    if any(item["fraction"] < 0.0 or item["fraction"] > 1.0 for item in rows):
        return False, "mixture_composition_fraction_out_of_range"
    bases = {item["basis"].strip().casefold() for item in rows if item["basis"].strip()}
    if len(bases) != 1 or any(not item["basis"].strip() for item in rows):
        return False, "mixture_composition_basis_not_unique"
    total = sum(item["fraction"] for item in rows)
    if not math.isclose(total, 1.0, rel_tol=1.0e-6, abs_tol=1.0e-8):
        return False, "mixture_composition_not_closed"
    return True, ""


def _fact_range_covers(fact: Mapping[str, Any], stream: Mapping[str, Any]) -> tuple[bool, str]:
    temperature = _finite(stream.get("temperature_c"))
    pressure = _finite(stream.get("pressure_mpa"))
    for value, lower_key, upper_key, label in (
        (temperature, "valid_temperature_min_c", "valid_temperature_max_c", "temperature"),
        (pressure, "valid_pressure_min_mpa", "valid_pressure_max_mpa", "pressure"),
    ):
        lower = _finite(fact.get(lower_key))
        upper = _finite(fact.get(upper_key))
        if lower is not None and upper is not None and lower > upper:
            return False, f"invalid_{label}_range"
        if value is None and (lower is not None or upper is not None):
            return False, f"current_{label}_missing_for_fact_range"
        if value is not None and ((lower is not None and value < lower) or (upper is not None and value > upper)):
            return False, f"outside_{label}_range"
    return True, ""


def _normalized_phase(value: Any) -> str:
    token = str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
    aliases = {
        "liq": "liquid",
        "liquid": "liquid",
        "vap": "vapor",
        "vapour": "vapor",
        "vapor": "vapor",
        "gas": "vapor",
        "two_phase": "two_phase",
        "mixed": "two_phase",
        "multiphase": "two_phase",
        "solid": "solid_bearing",
        "solid_bearing": "solid_bearing",
    }
    return aliases.get(token, "")


def _stream_phase(stream: Mapping[str, Any]) -> str:
    solid_fraction = _finite(stream.get("solid_fraction"))
    if solid_fraction is not None and not 0.0 <= solid_fraction <= 1.0:
        return ""
    if solid_fraction is not None and solid_fraction > 1.0e-9:
        return "solid_bearing"
    vapor_fraction = _finite(stream.get("vapor_fraction"))
    if vapor_fraction is not None:
        if not 0.0 <= vapor_fraction <= 1.0:
            return ""
        if vapor_fraction <= 1.0e-9:
            return "liquid"
        if vapor_fraction >= 1.0 - 1.0e-9:
            return "vapor"
        return "two_phase"
    return _normalized_phase(stream.get("phase"))


def _fact_phase_covers(
    fact: Mapping[str, Any],
    stream: Mapping[str, Any],
    *,
    normalized_stream_phase: str = "",
) -> tuple[bool, str]:
    raw_phases = fact.get("valid_phases", fact.get("valid_phase"))
    if raw_phases is None:
        return True, ""
    if isinstance(raw_phases, str):
        raw_phases = [raw_phases]
    if not isinstance(raw_phases, list):
        return False, "fact_phase_applicability_invalid"
    normalized_rows = [_normalized_phase(item) for item in raw_phases]
    if not normalized_rows or any(item not in CANONICAL_PHASES for item in normalized_rows):
        return False, "fact_phase_applicability_invalid"
    valid_phases = set(normalized_rows)
    current_phase = normalized_stream_phase or _stream_phase(stream)
    if not current_phase:
        has_phase_input = any(
            stream.get(field) not in (None, "")
            for field in ("phase", "vapor_fraction", "solid_fraction")
        )
        return False, "current_phase_invalid" if has_phase_input else "current_phase_missing_for_fact_scope"
    if current_phase not in valid_phases:
        return False, "outside_phase_applicability"
    return True, ""


def _fact_pressure_basis_covers(
    fact: Mapping[str, Any],
    *,
    pressure_basis: str,
) -> tuple[bool, str]:
    has_pressure_range = any(
        _finite(fact.get(field)) is not None
        for field in ("valid_pressure_min_mpa", "valid_pressure_max_mpa")
    )
    if not has_pressure_range:
        return True, ""
    current_basis = str(pressure_basis or "").strip().casefold()
    fact_basis = str(fact.get("pressure_basis") or "").strip().casefold()
    if current_basis not in {"absolute", "gauge"}:
        return False, "current_pressure_basis_missing_for_fact_range"
    if fact_basis not in {"absolute", "gauge"}:
        return False, "fact_pressure_basis_missing_for_range"
    if current_basis != fact_basis:
        return False, "pressure_basis_mismatch"
    return True, ""


def _validated_fact_value(name: str, value: Any) -> tuple[Any, str]:
    if name in PROPERTY_BOOL_FACTS:
        if isinstance(value, bool):
            return value, ""
        token = str(value if value is not None else "").strip().casefold()
        if token in {"true", "yes", "1"}:
            return True, ""
        if token in {"false", "no", "0"}:
            return False, ""
        return None, "property_fact_boolean_value_invalid"
    allowed = PROPERTY_FACT_ENUMS.get(name)
    if allowed is not None:
        text = str(value if value is not None else "").strip()
        if name != "current_facing":
            text = text.casefold()
        if text not in allowed:
            return None, "property_fact_enum_value_invalid"
        return text, ""
    return value, ""


def _property_facts_for_stream(
    facts: Iterable[Mapping[str, Any]],
    *,
    stream: Mapping[str, Any],
    block_id: str,
    connection_id: str,
    project_context_sha256: str,
    pressure_basis: str = "",
    normalized_stream_phase: str = "",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Accept only hash-locked same-stream/requirement facts.

    A component name match is intentionally insufficient. Mixture facts must
    bind the exact normalized composition hash; project requirements must bind
    the exact block. This prevents a user/LLM label from becoming engineering
    evidence merely by carrying a plausible field name.
    """

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    stream_id = str(stream.get("stream_id") or "")
    composition = _composition(stream)
    composition_valid, composition_reason = _composition_binding_status(stream)
    composition_sha256 = composition_context_sha256(stream)
    for raw in facts:
        request_fact = dict(raw)
        source_sha256 = str(request_fact.get("source_asset_sha256") or "")
        registered_manual_mechanical_fact = (
            request_fact.get("source_kind") == "MANUAL_REGISTERED_MECHANICAL_FACT"
            and request_fact.get("fact") == "current_facing"
            and request_fact.get("source_asset_path") == "manual_input.flange_face"
            and str(request_fact.get("subject_scope") or "").lower() == "connection_requirement"
            and str(request_fact.get("connection_id") or "") == connection_id
            and str(request_fact.get("project_context_sha256") or "").upper()
            == str(project_context_sha256 or "").upper()
        )
        record = (
            dict(request_fact)
            if registered_manual_mechanical_fact
            else _fact_exists_in_graph_asset(request_fact)
        )
        if record is True:  # compatibility for isolated unit-test monkeypatches only
            record = dict(request_fact)
        if not isinstance(record, Mapping):
            rejected.append({
                "fact": str(request_fact.get("fact") or ""),
                "source_id": str(request_fact.get("source_id") or "") or None,
                "reason": "source_fact_not_in_verified_graph_asset",
            })
            continue
        if not _record_metadata_matches_request(record, request_fact):
            rejected.append({
                "fact": str(request_fact.get("fact") or record.get("fact") or ""),
                "source_id": str(request_fact.get("source_id") or record.get("source_id") or "") or None,
                "reason": "caller_fact_metadata_conflicts_with_graph_record",
            })
            continue
        fact = dict(record)
        fact.update({
            "source_asset_path": request_fact.get("source_asset_path"),
            "source_asset_sha256": source_sha256,
            "source_record_sha256": str(request_fact.get("source_record_sha256") or ""),
        })
        name = str(fact.get("fact") or "")
        source_id = str(fact.get("source_id") or "")
        qa_status = str(fact.get("qa_status") or "").upper()
        scope = str(fact.get("subject_scope") or "").lower()
        reason = ""
        if name not in PROPERTY_FACTS:
            reason = "unknown_fact"
        elif not source_id or not SHA256_PATTERN.fullmatch(source_sha256):
            reason = "missing_source_id_or_asset_hash"
        elif qa_status not in SOURCE_QA_STATES:
            reason = "source_not_validated"
        elif name in MIXTURE_DEPENDENT_FACTS and scope not in {"stream", "mixture"}:
            reason = "hazard_fact_requires_exact_mixture_scope"
        elif scope in {"stream", "mixture"}:
            if str(fact.get("stream_id") or "") != stream_id:
                reason = "different_stream"
            elif not composition_valid:
                reason = composition_reason
            elif not composition or str(fact.get("composition_sha256") or "").upper() != composition_sha256:
                reason = "mixture_composition_not_exactly_bound"
        elif scope == "module_requirement":
            if str(fact.get("block_id") or "") != block_id:
                reason = "different_block_requirement"
        elif scope == "connection_requirement":
            if str(fact.get("connection_id") or "") != connection_id:
                reason = "different_connection_requirement"
        elif scope == "project_requirement":
            if (
                not SHA256_PATTERN.fullmatch(str(fact.get("project_context_sha256") or ""))
                or str(fact.get("project_context_sha256") or "").upper()
                != str(project_context_sha256 or "").upper()
            ):
                reason = "different_or_unbound_project_requirement"
        else:
            reason = "component_or_unbounded_scope_cannot_classify_current_mixture"
        if (
            not reason
            and name in MIXTURE_DEPENDENT_FACTS
            and fact.get("valid_phases", fact.get("valid_phase")) is None
        ):
            reason = "fact_phase_applicability_missing"
        if not reason:
            covered, reason = _fact_phase_covers(
                fact,
                stream,
                normalized_stream_phase=normalized_stream_phase,
            )
            if not covered:
                pass
        if not reason:
            covered, reason = _fact_pressure_basis_covers(fact, pressure_basis=pressure_basis)
            if not covered:
                pass
        if not reason:
            covered, reason = _fact_range_covers(fact, stream)
            if not covered:
                pass
        normalized_value: Any = fact.get("value")
        if not reason:
            normalized_value, reason = _validated_fact_value(name, normalized_value)
        if reason:
            rejected.append({
                "fact": name,
                "source_id": source_id or None,
                "reason": reason,
            })
            continue
        accepted.append({
            "fact": name,
            "value": normalized_value,
            "source_id": source_id,
            "source_asset_path": fact.get("source_asset_path"),
            "source_asset_sha256": source_sha256.upper(),
            "source_record_sha256": str(fact.get("source_record_sha256") or "").upper(),
            "qa_status": qa_status,
            "subject_scope": scope,
            "stream_id": fact.get("stream_id"),
            "block_id": fact.get("block_id"),
            "connection_id": fact.get("connection_id"),
            "project_context_sha256": fact.get("project_context_sha256"),
            "composition_sha256": fact.get("composition_sha256"),
            "valid_phases": fact.get("valid_phases", fact.get("valid_phase")),
            "valid_temperature_min_c": fact.get("valid_temperature_min_c"),
            "valid_temperature_max_c": fact.get("valid_temperature_max_c"),
            "valid_pressure_min_mpa": fact.get("valid_pressure_min_mpa"),
            "valid_pressure_max_mpa": fact.get("valid_pressure_max_mpa"),
            "pressure_basis": fact.get("pressure_basis"),
        })

    # A single connection/context may not carry contradictory values for one
    # fact. Same-value records are deterministic corroboration; conflicting
    # values are all rejected so downstream equipment labels remain UNKNOWN.
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in accepted:
        grouped.setdefault(str(item["fact"]), []).append(item)
    collapsed: list[dict[str, Any]] = []
    for name in sorted(grouped):
        rows = sorted(
            grouped[name],
            key=lambda item: (
                _semantic_token(item.get("value")),
                str(item.get("source_id") or ""),
                str(item.get("source_record_sha256") or ""),
            ),
        )
        distinct = {_semantic_token(item.get("value")) for item in rows}
        if len(distinct) > 1:
            rejected.extend({
                "fact": name,
                "source_id": item.get("source_id"),
                "reason": "property_fact_conflict",
            } for item in rows)
            continue
        primary = dict(rows[0])
        primary["corroborating_source_records"] = [
            {
                "source_id": item.get("source_id"),
                "source_asset_sha256": item.get("source_asset_sha256"),
                "source_record_sha256": item.get("source_record_sha256"),
            }
            for item in rows
        ]
        collapsed.append(primary)
    return collapsed, sorted(
        rejected,
        key=lambda item: (str(item.get("fact") or ""), str(item.get("reason") or ""), str(item.get("source_id") or "")),
    )


def _selector_input(
    *,
    family: str,
    block: Mapping[str, Any],
    stream: Mapping[str, Any],
    mechanical_context: Mapping[str, Any],
    property_evidence: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "object_family": family,
        "module_id": str(block.get("block_id") or ""),
        "module_type": str(block.get("block_type") or ""),
        "temperature_value": stream.get("temperature_c"),
        "temperature_unit": "C",
        "pressure_value": stream.get("pressure_mpa"),
        "pressure_unit": "MPa",
        "vapor_fraction": stream.get("vapor_fraction"),
        "solid_fraction": stream.get("solid_fraction"),
        "components": _composition(stream),
    }
    for field in sorted(MECHANICAL_FIELDS):
        if field in mechanical_context:
            raw[field] = mechanical_context[field]
    # Keep attempted direct labels visible to the canonical selector, which
    # ignores them and emits W_DERIVED_INPUT_IGNORED. They never bypass facts.
    for field in sorted(DIRECT_LABEL_FIELDS):
        if field in mechanical_context:
            raw[field] = mechanical_context[field]
    return raw


def _parent_context_sha256(match_result: Mapping[str, Any]) -> str:
    package = match_result.get("design_parameter_package")
    if not isinstance(package, Mapping):
        return ""
    context = package.get("selection_context")
    return str(context.get("sha256") or "") if isinstance(context, Mapping) else ""


def _connection_id(block_id: str, direction: str, ordinal: int, stream_id: str) -> str:
    return f"{block_id}:{direction.upper()}:{ordinal}:{stream_id}"


def _profile_token(value: Any) -> str:
    text = str(value or "").strip().casefold()
    normalized = "".join(
        character if character.isascii() and character.isalnum() else "_"
        for character in text
    )
    return normalized.strip("_") or "unknown"


def _service_profile_phase(
    profile: Mapping[str, Any] | None,
    *,
    source_export_sha256: str,
    direction: str,
    stream_id: str,
) -> tuple[str, str]:
    if not isinstance(profile, Mapping):
        return "", "raw_stream_fallback"
    if (
        profile.get("schema") != "equipment-service-profile-v1"
        or str(profile.get("source_bundle_sha256") or "").upper()
        != str(source_export_sha256 or "").upper()
        or not SHA256_PATTERN.fullmatch(str(profile.get("profile_context_sha256") or ""))
    ):
        return "", "invalid_service_profile"
    expected_id = f"process.stream_phase.{_profile_token(direction)}.{_profile_token(stream_id)}"
    for label in profile.get("service_labels", []):
        if not isinstance(label, Mapping) or label.get("label_id") != expected_id:
            continue
        phase = str(label.get("value") or "")
        if phase in CANONICAL_PHASES and label.get("evidence_state") == "D":
            return phase, "equipment_service_profile"
    return "", "service_profile_phase_missing"


def build_aspen_connection_component_selections(
    *,
    block: Mapping[str, Any],
    streams: Mapping[str, Mapping[str, Any]],
    match_result: Mapping[str, Any],
    source_export_sha256: str,
    pfd_mapping_sha256: str,
    endpoints: Mapping[str, Mapping[str, list[str]]] | None = None,
    mechanical_context: Mapping[str, Any] | None = None,
    property_evidence: Iterable[Mapping[str, Any]] = (),
    pressure_basis: str = "",
    service_profile: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    verification = verify_selector_package()
    selector = _selector_module()
    block_id = str(block.get("block_id") or "")
    block_type = str(block.get("block_type") or "").upper()
    parent_sha256 = _parent_context_sha256(match_result)
    context = dict(mechanical_context or {})
    ignored_direct_label_fields = sorted(
        set(context).intersection(DIRECT_LABEL_FIELDS | frozenset(DIRECT_LABEL_ALIASES))
    )
    endpoint_map = endpoints or {}
    all_connections: list[dict[str, Any]] = []
    package_diagnostics: list[dict[str, Any]] = []
    if isinstance(service_profile, Mapping):
        for diagnostic in service_profile.get("diagnostics", []):
            if isinstance(diagnostic, Mapping) and diagnostic.get("code") == "MODULE_STREAM_CONDITION_CONFLICT":
                package_diagnostics.append({
                    "connection_id": None,
                    "object_family": "service_profile",
                    "code": "MODULE_STREAM_CONDITION_CONFLICT",
                    "detail": str(diagnostic.get("detail") or "Module intent conflicts with observed stream operation."),
                })
    for direction, stream_ids in (
        ("inlet", block.get("inlet_streams", [])),
        ("outlet", block.get("outlet_streams", [])),
    ):
        for ordinal, raw_stream_id in enumerate(stream_ids if isinstance(stream_ids, list) else [], start=1):
            stream_id = str(raw_stream_id)
            connection_id = _connection_id(block_id, direction, ordinal, stream_id)
            stream = streams.get(stream_id)
            endpoint = endpoint_map.get(stream_id, {})
            base: dict[str, Any] = {
                "connection_id": connection_id,
                "stream_id": stream_id,
                "block_id": block_id,
                "block_type": block_type,
                "end_role": direction.upper(),
                "port_index": ordinal,
                "port_identity_status": "PROVISIONAL_PORT_ID",
                "from_block_ids": list(endpoint.get("from_block_ids", [])),
                "to_block_ids": list(endpoint.get("to_block_ids", [])),
            }
            if block_type in LOGIC_BLOCK_TYPES:
                all_connections.append({
                    **base,
                    "applicability": "NOT_APPLICABLE",
                    "reason_code": "NOT_APPLICABLE_SIMULATION_LOGIC_NODE",
                    "component_types": {},
                })
                continue
            if not isinstance(stream, Mapping):
                all_connections.append({
                    **base,
                    "applicability": "LOCAL_DIAGNOSTIC",
                    "reason_code": "CONNECTED_STREAM_NOT_FOUND",
                    "component_types": {},
                })
                continue
            kind = _stream_kind(stream)
            base["stream_kind"] = kind
            if kind != "material":
                all_connections.append({
                    **base,
                    "applicability": "NOT_APPLICABLE",
                    "reason_code": f"NOT_APPLICABLE_{kind.upper()}_STREAM",
                    "component_types": {},
                })
                continue
            profile_phase, phase_origin = _service_profile_phase(
                service_profile,
                source_export_sha256=source_export_sha256,
                direction=direction,
                stream_id=stream_id,
            )
            normalized_phase = profile_phase or _stream_phase(stream)
            accepted_facts, rejected_facts = _property_facts_for_stream(
                property_evidence,
                stream=stream,
                block_id=block_id,
                connection_id=connection_id,
                project_context_sha256=source_export_sha256,
                pressure_basis=pressure_basis or str(stream.get("pressure_basis") or ""),
                normalized_stream_phase=normalized_phase,
            )
            composition_valid, composition_reason = _composition_binding_status(stream)
            for rejection in rejected_facts:
                if rejection.get("reason") in {
                    "property_fact_conflict",
                    "caller_fact_metadata_conflicts_with_graph_record",
                }:
                    package_diagnostics.append({
                        "connection_id": connection_id,
                        "object_family": "property_join",
                        "code": str(rejection.get("reason") or "PROPERTY_FACT_REJECTED").upper(),
                        "detail": f"Property fact {rejection.get('fact')} was rejected for the current connection/context.",
                    })
            if not normalized_phase and any(
                stream.get(field) not in (None, "")
                for field in ("phase", "vapor_fraction", "solid_fraction")
            ):
                package_diagnostics.append({
                    "connection_id": connection_id,
                    "object_family": "service_profile",
                    "code": "CURRENT_PHASE_INVALID",
                    "detail": "Raw phase/fraction input exists but does not normalize to a registered phase; phase-dependent facts remain unusable.",
                })
            component_types: dict[str, Any] = {}
            for family in COMPONENT_FAMILIES:
                selector_input = _selector_input(
                    family=family,
                    block=block,
                    stream=stream,
                    mechanical_context=context,
                    property_evidence=accepted_facts,
                )
                try:
                    selected = selector._select_verified(
                        selector_input,
                        verified_property_evidence=accepted_facts,
                        normalized_stream_phase=normalized_phase,
                    )
                    if selected.get("terminal_count") != 1:
                        raise ConnectionComponentSelectionError(
                            f"{family} did not return exactly one terminal type"
                        )
                    component_types[family] = selected
                except Exception as exc:  # item-local by contract
                    component_types[family] = {
                        "schema": "connection-component-local-diagnostic-v1",
                        "status": "LOCAL_SELECTION_FAILED",
                        "terminal_count": 0,
                        "object_family": family,
                        "error": {"code": "COMPONENT_SELECTOR_FAILED", "detail": str(exc)},
                    }
                    package_diagnostics.append({
                        "connection_id": connection_id,
                        "object_family": family,
                        "code": "COMPONENT_SELECTOR_FAILED",
                        "detail": str(exc),
                    })
            all_connections.append({
                **base,
                "applicability": "APPLICABLE",
                "raw_service_context": {
                    "temperature_c": stream.get("temperature_c"),
                    "pressure_mpa": stream.get("pressure_mpa"),
                    "pressure_basis": pressure_basis or stream.get("pressure_basis"),
                    "vapor_fraction": stream.get("vapor_fraction"),
                    "solid_fraction": stream.get("solid_fraction"),
                    "normalized_phase": normalized_phase or None,
                    "normalized_phase_origin": phase_origin if profile_phase else "strict_raw_stream_fallback",
                    "service_profile_context_sha256": (
                        service_profile.get("profile_context_sha256")
                        if isinstance(service_profile, Mapping)
                        else None
                    ),
                    "composition": _composition(stream),
                    "composition_sha256": composition_context_sha256(stream),
                    "composition_binding_status": "CLOSED" if composition_valid else "NOT_BINDABLE",
                    "composition_binding_reason": composition_reason or None,
                },
                "accepted_property_facts": accepted_facts,
                "rejected_property_facts": rejected_facts,
                "ignored_direct_label_fields": ignored_direct_label_fields,
                "component_types": component_types,
            })
    status = (
        "NOT_APPLICABLE"
        if all_connections and all(item["applicability"] == "NOT_APPLICABLE" for item in all_connections)
        else "DERIVED_WITH_LOCAL_DIAGNOSTICS"
        if package_diagnostics
        else "DERIVED"
    )
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "engine_version": ENGINE_VERSION,
        "status": status,
        "deterministic": True,
        "llm_used": False,
        "runtime_vision": False,
        "runtime_source_access": False,
        "parent_selection_context_sha256": parent_sha256,
        "source_export_sha256": source_export_sha256,
        "pfd_mapping_sha256": pfd_mapping_sha256,
        "selector_manifest_sha256": verification["manifest_sha256"],
        "selector_asset_count": verification["asset_count"],
        "ignored_direct_label_fields": ignored_direct_label_fields,
        "connections": all_connections,
        "diagnostics": package_diagnostics,
    }
    result["selection_package_sha256"] = canonical_sha256(result)
    return result


def build_manual_connection_component_selections(
    raw: Mapping[str, Any],
    *,
    match_result: Mapping[str, Any],
    equipment_id: str,
    block_type: str = "",
    service_profile: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    def manual_stream(direction: str) -> dict[str, Any] | None:
        prefix = direction + "_"
        has_directional = any(
            field in raw
            for field in (
                prefix + "temperature_c",
                prefix + "pressure_mpa",
            )
        )
        if direction != "inlet" and not has_directional:
            return None
        temperature = raw.get(prefix + "temperature_c")
        if temperature is None:
            temperature = raw.get("operating_temperature_c", raw.get("temperature_c"))
        pressure = raw.get(prefix + "pressure_mpa")
        if pressure is None:
            pressure = raw.get("operating_pressure_mpa")
        stream_id = f"MANUAL:{direction.upper()}"
        return {
            "stream_id": stream_id,
            "stream_record_type": "MATERIAL",
            "temperature_c": temperature,
            "pressure_mpa": pressure,
            "vapor_fraction": raw.get(prefix + "vapor_fraction", raw.get("vapor_fraction")),
            "solid_fraction": raw.get(prefix + "solid_fraction", raw.get("solid_fraction")),
            "phase": raw.get(prefix + "phase", raw.get("phase")),
            "composition": raw.get(prefix + "composition", raw.get("composition", [])),
            "_sources": {},
        }

    streams = {
        stream["stream_id"]: stream
        for direction in ("inlet", "outlet")
        for stream in [manual_stream(direction)]
        if stream is not None
    }
    inlet_ids = [stream_id for stream_id in streams if stream_id.endswith(":INLET")]
    outlet_ids = [stream_id for stream_id in streams if stream_id.endswith(":OUTLET")]
    block = {
        "block_id": equipment_id,
        "block_type": str(block_type or raw.get("aspen_block_type") or "MANUAL_EQUIPMENT").upper(),
        "inlet_streams": inlet_ids,
        "outlet_streams": outlet_ids,
    }
    mechanical = {
        field: raw[field]
        for field in sorted(MECHANICAL_FIELDS | DIRECT_LABEL_FIELDS)
        if field in raw
    }
    for alias, canonical in DIRECT_LABEL_ALIASES.items():
        if alias in raw:
            mechanical[canonical] = raw[alias]
    nested_context = raw.get("connection_design_context")
    if isinstance(nested_context, Mapping):
        mechanical.update({
            str(key): value
            for key, value in nested_context.items()
            if str(key) in MECHANICAL_FIELDS | DIRECT_LABEL_FIELDS
        })

    # Manual equipment forms use customer-facing field names.  Bridge only
    # registered mechanical facts into the HG/T selector contract; arbitrary
    # material/type text remains a visible preference and never becomes
    # component-selection evidence.
    input_ledger: list[dict[str, Any]] = []

    selected_dn = raw.get("selected_dn")
    dn_value: float | None = None
    if isinstance(selected_dn, (int, float)) and not isinstance(selected_dn, bool):
        dn_value = float(selected_dn)
    elif isinstance(selected_dn, str):
        dn_match = re.fullmatch(r"\s*DN\s*(\d+(?:\.\d+)?)\s*", selected_dn, re.IGNORECASE)
        if dn_match:
            dn_value = float(dn_match.group(1))
    if dn_value is not None and math.isfinite(dn_value) and dn_value > 0:
        mechanical["dn_mm"] = int(dn_value) if dn_value.is_integer() else dn_value
        input_ledger.append({
            "field": "selected_dn",
            "status": "NORMALIZED_TO_SELECTOR_FACT",
            "selector_field": "dn_mm",
            "normalized_value": mechanical["dn_mm"],
        })
    elif selected_dn not in (None, ""):
        input_ledger.append({
            "field": "selected_dn",
            "status": "IGNORED_INVALID_MANUAL_MECHANICAL_VALUE",
            "reason": "Expected a positive number or DN<number>.",
        })

    pressure_class = raw.get("pressure_class")
    pressure_text = str(pressure_class or "").strip().upper().replace(" ", "")
    pn_match = re.fullmatch(r"PN(\d+(?:\.\d+)?)", pressure_text)
    class_match = re.fullmatch(r"(?:CLASS|CL)(\d+(?:\.\d+)?)", pressure_text)
    lb_match = re.fullmatch(r"(\d+(?:\.\d+)?)LB", pressure_text)
    if pn_match:
        pn_value = float(pn_match.group(1))
        if pn_value > 0:
            mechanical["system_series"] = "PN"
            mechanical["pn"] = int(pn_value) if pn_value.is_integer() else pn_value
            input_ledger.append({
                "field": "pressure_class",
                "status": "NORMALIZED_TO_SELECTOR_FACT",
                "selector_field": "pn",
                "normalized_value": mechanical["pn"],
            })
    elif class_match or lb_match:
        matched = class_match or lb_match
        class_value = float(matched.group(1))
        if class_value > 0:
            mechanical["system_series"] = "CLASS"
            mechanical["class_rating"] = int(class_value) if class_value.is_integer() else class_value
            input_ledger.append({
                "field": "pressure_class",
                "status": "NORMALIZED_TO_SELECTOR_FACT",
                "selector_field": "class_rating",
                "normalized_value": mechanical["class_rating"],
            })
    elif pressure_class not in (None, ""):
        input_ledger.append({
            "field": "pressure_class",
            "status": "IGNORED_INVALID_MANUAL_MECHANICAL_VALUE",
            "reason": "Expected PN<number>, Class<number>, CL<number>, or <number>LB.",
        })

    flange_face = raw.get("flange_face")
    face_text = str(flange_face or "").strip().upper().replace(" ", "")
    if face_text in PROPERTY_FACT_ENUMS["current_facing"]:
        # Facing is accepted only through the verified property-fact join, not
        # as a direct selector label.  Create a same-manual-record, hash-bound
        # fact below after the connection identities are known.
        input_ledger.append({
            "field": "flange_face",
            "status": "NORMALIZED_PENDING_PROPERTY_FACT_BINDING",
            "selector_field": "current_facing",
            "normalized_value": face_text,
        })
    elif flange_face not in (None, ""):
        input_ledger.append({
            "field": "flange_face",
            "status": "IGNORED_UNREGISTERED_MANUAL_MECHANICAL_VALUE",
            "reason": "Facing is not in the registered current_facing enumeration.",
        })

    if raw.get("gasket_material") not in (None, ""):
        input_ledger.append({
            "field": "gasket_material",
            "status": "IGNORED_UNTRUSTED_COMPONENT_PREFERENCE",
            "reason": "Free material text cannot select a gasket family or terminal type.",
        })
    property_evidence = raw.get("property_evidence")
    property_rows = [
        dict(item)
        for item in property_evidence
        if isinstance(item, Mapping)
    ] if isinstance(property_evidence, list) else []
    source_sha256 = canonical_sha256(raw)
    endpoints = {
        stream_id: {
            "from_block_ids": [] if stream_id in inlet_ids else [equipment_id],
            "to_block_ids": [equipment_id] if stream_id in inlet_ids else [],
        }
        for stream_id in streams
    }
    pfd_sha256 = canonical_sha256({"manual_block": block, "endpoints": endpoints})
    if face_text in PROPERTY_FACT_ENUMS["current_facing"]:
        for stream_id in streams:
            connection_id = _connection_id(
                equipment_id,
                "inlet" if stream_id in inlet_ids else "outlet",
                1,
                stream_id,
            )
            property_rows.append({
                "source_id": f"manual:{equipment_id}:{stream_id}:current_facing",
                "source_kind": "MANUAL_REGISTERED_MECHANICAL_FACT",
                "source_asset_path": "manual_input.flange_face",
                "source_asset_sha256": source_sha256,
                "source_record_sha256": canonical_sha256({
                    "equipment_id": equipment_id,
                    "stream_id": stream_id,
                    "field": "flange_face",
                    "value": face_text,
                }),
                "fact": "current_facing",
                "value": face_text,
                "qa_status": "ACCEPTED",
                "subject_scope": "connection_requirement",
                "connection_id": connection_id,
                "block_id": equipment_id,
                "project_context_sha256": source_sha256,
            })
    result = build_aspen_connection_component_selections(
        block=block,
        streams=streams,
        match_result=match_result,
        source_export_sha256=source_sha256,
        pfd_mapping_sha256=pfd_sha256,
        endpoints=endpoints,
        mechanical_context=mechanical,
        property_evidence=property_rows,
        pressure_basis=str(raw.get("pressure_basis") or ""),
        service_profile=service_profile,
    )
    result["manual_mechanical_input_ledger"] = input_ledger
    for item in input_ledger:
        if str(item.get("status", "")).startswith("IGNORED_"):
            result.setdefault("diagnostics", []).append({
                "connection_id": None,
                "object_family": "manual_mechanical_input",
                "code": str(item["status"]),
                "field": item.get("field"),
                "detail": item.get("reason"),
            })
    if result.get("diagnostics") and result.get("status") == "DERIVED":
        result["status"] = "DERIVED_WITH_LOCAL_DIAGNOSTICS"
    result.pop("selection_package_sha256", None)
    result["selection_package_sha256"] = canonical_sha256(result)
    return result


__all__ = [
    "COMPONENT_FAMILIES",
    "ENGINE_VERSION",
    "SCHEMA",
    "build_aspen_connection_component_selections",
    "build_manual_connection_component_selections",
    "canonical_sha256",
    "composition_context_sha256",
    "verify_selector_package",
]
