"""Deterministic Aspen block-to-equipment and PFD mapping core.

This module deliberately stops at the *mapping* boundary.  An Aspen block
record or a user override can select an application catalog entry, but neither
is evidence for a mechanical/vendor model.  Unknown block types are routed by
explicit fields, phases, port counts and connectivity.  If those signals do
not identify one catalog entry without ambiguity, the result keeps the common
equipment family (when one exists) and leaves ``selection_id`` unset.

The functions are UI independent and use JSON-compatible values only:

``build_pfd_mapping(bundle, overrides=None)``
    Build automatic/effective mappings and deterministic PFD geometry.

``update_type_override(bundle, overrides, block_id, selection_id)``
    Validate and apply one user choice.  ``selection_id=None`` restores the
    automatic mapping.  The returned impact ledger marks only the changed
    block, incident streams, and immediate upstream/downstream blocks stale.

``update_parameter_override(bundle, type_overrides, parameter_overrides, ...)``
    Maintain a separate, per-block manual-parameter layer and return the same
    local stale-propagation projection.  The layer never mutates the Aspen
    bundle and is not evidence by itself; callers must replay the deterministic
    matcher with the merged input.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_ID = "equipment-design-pfd-mapping-v1"
POLICY_VERSION = "1.2.0"

PARAMETER_OVERRIDE_FORBIDDEN_FIELDS = {
    "aspen_block_id",
    "aspen_block_type",
    "block_type",
    "candidate_model",
    "equipment_family",
    "equipment_tag",
    "family_id",
    "final_model",
    "model_status",
    "selection_id",
}

MATCHER_ROUTE_FIELDS = {"aspen_block_type", "block_type", "equipment_family"}

UNKNOWN_BLOCK_TYPES = {"", "UNKNOWN", "UNAVAILABLE", "MISSING", "NONE", "NULL", "?"}

# A narrow alias table is intentionally used.  These aliases describe an
# Aspen-module equivalence, not a vendor/mechanical construction choice.
UNIQUE_BLOCK_TYPE_ALIASES: dict[str, str] = {
    "COMPRESSOR": "block:COMPR",
    "COMP": "block:COMPR",
    "MULTISTAGECOMPRESSOR": "block:MCOMPR",
    "MULTISTAGECOMPR": "block:MCOMPR",
    "MCOMPRESSOR": "block:MCOMPR",
    "COOLER": "block:HEATER",
    "PFR": "block:RPLUG",
    "PLUGFLOWREACTOR": "block:RPLUG",
    "CSTR": "block:RCSTR",
    "FLASH": "block:FLASH2",
    "THREEPHASEFLASH": "block:FLASH3",
    "3PHFLASH": "block:FLASH3",
    "LLDECANTER": "block:DECANTER",
    "DISTILLATION": "block:RADFRAC",
    "ABSORBER": "block:ABSBR",
    "VLV": "block:VALVE",
    "PIPE": "family:family_process_piping",
    "PIPELINE": "family:family_process_piping",
    "TANK": "family:family_storage_vessel",
    "STORAGE": "family:family_storage_vessel",
    "MEMBRANE": "family:family_membrane",
    "STATICMIXER": "family:family_static_mixer",
}

# General Aspen categories map to candidate sets.  They are never collapsed to
# a subtype merely because all candidates happen to share one family.
GENERAL_BLOCK_TYPE_FAMILIES: dict[str, tuple[str, ...]] = {
    "COLUMN": ("family_tower",),
    "TOWER": ("family_tower",),
    "MULTIFRAC": ("family_tower",),
    "REACTOR": ("family_reactor_vessel_separator",),
    "VESSEL": ("family_reactor_vessel_separator", "family_storage_vessel"),
    "SEPARATOR": ("family_reactor_vessel_separator",),
    "SEP": ("family_reactor_vessel_separator",),
    "SEP2": ("family_reactor_vessel_separator",),
    "BATCHSEP": ("family_reactor_vessel_separator",),
    "MHEATX": ("family_other_heat_exchanger", "family_fixed_tubesheet_exchanger"),
    "EXCHANGER": ("family_other_heat_exchanger", "family_fixed_tubesheet_exchanger"),
    "HEATEXCHANGER": ("family_other_heat_exchanger", "family_fixed_tubesheet_exchanger"),
    "MIXER": ("family_static_mixer", "family_agitator", "family_pipe_fitting"),
    "FSPLIT": ("family_pipe_fitting", "family_process_piping", "family_valve"),
    "SPLITTER": ("family_pipe_fitting", "family_process_piping", "family_valve"),
    "TURBINE": ("family_gas_expander_turbine", "family_liquid_power_recovery_turbine"),
    "EXPANDER": ("family_gas_expander_turbine", "family_liquid_power_recovery_turbine"),
}

BLOCK_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "heat_duty_kw": ("heat_duty_kw", "QCALC"),
    "heat_transfer_area_m2": ("heat_transfer_area_m2", "AREA"),
    "hydraulic_power_kw": (
        "hydraulic_power_kw",
        "FLUID_POWER",
    ),
    "shaft_power_kw": (
        "shaft_power_kw",
        "BRAKE_POWER",
    ),
    "electrical_power_kw": (
        "electrical_power_kw",
        "ELEC_POWER",
        "WNET",
    ),
    "head_m": ("head_m", "HEAD_CAL", "HEAD"),
    "efficiency_percent": ("efficiency_percent", "CEFF", "SEFF"),
    "pressure_drop_kpa": ("pressure_drop_kpa", "DELP_CAL", "PDRP"),
    "pressure_ratio": ("pressure_ratio", "PRES_RATIO", "PRATIO"),
    "stage_count": ("stage_count", "NSTAGE"),
    "volume_m3": ("volume_m3", "VOLUME"),
    "inner_diameter_mm": ("inner_diameter_mm",),
    "diameter_mm": ("diameter_mm", "DIAMETER"),
    "height_mm": ("height_mm", "HEIGHT"),
}

STREAM_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "temperature_c": ("temperature_c", "TEMP_OUT"),
    "pressure_bar": ("pressure_bar", "PRES_OUT"),
    "mass_flow_kg_h": ("mass_flow_kg_h", "MASSFLMX"),
    "volumetric_flow_m3_h": ("volumetric_flow_m3_h", "VOLFLMX"),
    "vapor_fraction": ("vapor_fraction", "VFRAC_OUT"),
    "density_kg_m3": ("density_kg_m3",),
    "phase": ("phase",),
    "dominant_components": ("dominant_components",),
}

BLOCK_PARAMETER_META: tuple[tuple[str, str, str], ...] = (
    ("heat_duty_kw", "热负荷", "kW"),
    ("heat_transfer_area_m2", "换热面积", "m²"),
    ("hydraulic_power_kw", "流体水力功率", "kW"),
    ("shaft_power_kw", "轴功率", "kW"),
    ("electrical_power_kw", "电功率", "kW"),
    ("head_m", "扬程", "m"),
    ("efficiency_percent", "效率", "%"),
    ("pressure_drop_kpa", "压降", "kPa"),
    ("pressure_ratio", "压比", ""),
    ("stage_count", "级数/理论级", ""),
    ("volume_m3", "容积", "m³"),
    ("inner_diameter_mm", "计算内径", "mm"),
    ("diameter_mm", "直径", "mm"),
    ("height_mm", "高度", "mm"),
)

STREAM_PARAMETER_META: tuple[tuple[str, str, str], ...] = (
    ("temperature_c", "温度", "°C"),
    ("pressure_mpa", "压力", "MPa"),
    ("pressure_bar", "压力", "bar"),
    ("mass_flow_kg_h", "质量流量", "kg/h"),
    ("volumetric_flow_m3_h", "体积流量", "m³/h"),
    ("vapor_fraction", "汽相分率", ""),
    ("density_kg_m3", "密度", "kg/m³"),
    ("phase", "相态", ""),
    ("dominant_components", "主要组分", ""),
)


class AspenPFDMappingError(ValueError):
    """A machine-readable, fail-closed mapping error."""

    def __init__(self, code: str, message: str, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


@dataclass(frozen=True)
class _Topology:
    blocks: dict[str, dict[str, Any]]
    streams: dict[str, dict[str, Any]]
    inlet_by_block: dict[str, tuple[str, ...]]
    outlet_by_block: dict[str, tuple[str, ...]]
    producers_by_stream: dict[str, tuple[str, ...]]
    consumers_by_stream: dict[str, tuple[str, ...]]
    connectivity_source_by_block: dict[str, str]


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def _normalize_token(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").strip().upper())


def _finite(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _compact(value: Any) -> str:
    if isinstance(value, bool):
        return "是" if value else "否"
    number = _finite(value)
    if number is not None:
        if number == 0:
            return "0"
        magnitude = abs(number)
        if magnitude >= 1_000_000 or magnitude < 0.001:
            return f"{number:.4g}"
        return f"{number:.6g}"
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return ", ".join(str(item) for item in value)
    return str(value)


def _first_value(record: Mapping[str, Any], aliases: Iterable[str]) -> Any:
    for key in aliases:
        if key in record and record[key] not in (None, ""):
            return record[key]
    raw_values = record.get("aspen_raw_values")
    if isinstance(raw_values, Mapping):
        for key in aliases:
            item = raw_values.get(key)
            if isinstance(item, Mapping) and item.get("value") not in (None, ""):
                return item["value"]
    return None


def _field_values(record: Mapping[str, Any], alias_map: Mapping[str, Iterable[str]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for canonical, aliases in alias_map.items():
        value = _first_value(record, aliases)
        if value not in (None, ""):
            values[canonical] = value
    return values


def _load_catalog(catalog: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if catalog is None:
        try:
            from . import app_core  # type: ignore
        except ImportError:
            import app_core  # type: ignore

        loaded = app_core.load_catalog()
    else:
        loaded = dict(catalog)
    selections = loaded.get("selections")
    if not isinstance(selections, list) or not selections:
        raise AspenPFDMappingError("INVALID_CATALOG", "设备类型目录缺少 selections。")
    seen: set[str] = set()
    for index, item in enumerate(selections):
        if not isinstance(item, Mapping):
            raise AspenPFDMappingError("INVALID_CATALOG", f"selections[{index}] 不是对象。")
        selection_id = str(item.get("selection_id", "")).strip()
        if not selection_id or selection_id in seen:
            raise AspenPFDMappingError("INVALID_CATALOG", "设备类型目录 selection_id 缺失或重复。", {"selection_id": selection_id})
        seen.add(selection_id)
    return loaded


def _catalog_indexes(catalog: Mapping[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    by_id: dict[str, dict[str, Any]] = {}
    by_block_type: dict[str, dict[str, Any]] = {}
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in catalog["selections"]:
        item = dict(raw)
        selection_id = str(item["selection_id"])
        by_id[selection_id] = item
        block_type = _normalize_token(item.get("block_type"))
        if block_type:
            by_block_type[block_type] = item
        by_family[str(item.get("family_id", ""))].append(item)
    for entries in by_family.values():
        entries.sort(key=lambda item: str(item["selection_id"]))
    return by_id, by_block_type, dict(by_family)


def _connection_fallback(block: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    inlet: set[str] = set()
    outlet: set[str] = set()
    connections = block.get("connections")
    if isinstance(connections, list):
        for item in connections:
            if not isinstance(item, Mapping):
                continue
            name = str(item.get("name", item.get("stream_id", ""))).strip()
            direction = str(item.get("direction", item.get("value", ""))).upper()
            if not name:
                continue
            if "(IN)" in direction or direction in {"IN", "INPUT", "INLET"}:
                inlet.add(name)
            if "(OUT)" in direction or direction in {"OUT", "OUTPUT", "OUTLET"}:
                outlet.add(name)
    port_detail = block.get("port_detail")
    if isinstance(port_detail, list):
        for item in port_detail:
            if not isinstance(item, Mapping):
                continue
            name = str(item.get("stream_id", item.get("name", ""))).strip()
            direction = str(item.get("direction", item.get("port_type", ""))).upper()
            if not name:
                continue
            if direction in {"IN", "INPUT", "INLET"} or "(IN)" in direction:
                inlet.add(name)
            if direction in {"OUT", "OUTPUT", "OUTLET"} or "(OUT)" in direction:
                outlet.add(name)
    return tuple(sorted(inlet)), tuple(sorted(outlet))


def _build_topology(bundle: Mapping[str, Any]) -> _Topology:
    if bundle.get("schema") != "aspen-equipment-export-v1":
        raise AspenPFDMappingError(
            "INVALID_ASPEN_EXPORT_SCHEMA",
            "PFD 映射只接受 aspen-equipment-export-v1。",
            {"received": bundle.get("schema")},
        )
    raw_blocks = bundle.get("blocks")
    raw_streams = bundle.get("streams")
    if not isinstance(raw_blocks, list) or not isinstance(raw_streams, list):
        raise AspenPFDMappingError("INVALID_ASPEN_EXPORT", "blocks 和 streams 必须是数组。")

    blocks: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(raw_blocks):
        if not isinstance(raw, Mapping):
            raise AspenPFDMappingError("INVALID_BLOCK", f"blocks[{index}] 不是对象。")
        block_id = str(raw.get("block_id", "")).strip()
        if not block_id:
            raise AspenPFDMappingError("INVALID_BLOCK", f"blocks[{index}] 缺少 block_id。")
        if block_id in blocks:
            raise AspenPFDMappingError("DUPLICATE_BLOCK_ID", f"Aspen 模块 ID 重复：{block_id}", {"block_id": block_id})
        blocks[block_id] = dict(raw)

    streams: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(raw_streams):
        if not isinstance(raw, Mapping):
            raise AspenPFDMappingError("INVALID_STREAM", f"streams[{index}] 不是对象。")
        stream_id = str(raw.get("stream_id", "")).strip()
        if not stream_id:
            raise AspenPFDMappingError("INVALID_STREAM", f"streams[{index}] 缺少 stream_id。")
        if stream_id in streams:
            raise AspenPFDMappingError("DUPLICATE_STREAM_ID", f"Aspen 流股 ID 重复：{stream_id}", {"stream_id": stream_id})
        streams[stream_id] = dict(raw)

    inlet_by_block: dict[str, tuple[str, ...]] = {}
    outlet_by_block: dict[str, tuple[str, ...]] = {}
    source_by_block: dict[str, str] = {}
    referenced_streams: set[str] = set(streams)
    for block_id, block in blocks.items():
        raw_inlet = block.get("inlet_streams")
        raw_outlet = block.get("outlet_streams")
        inlet = tuple(sorted({str(item).strip() for item in raw_inlet if str(item).strip()})) if isinstance(raw_inlet, list) else ()
        outlet = tuple(sorted({str(item).strip() for item in raw_outlet if str(item).strip()})) if isinstance(raw_outlet, list) else ()
        fallback_inlet, fallback_outlet = _connection_fallback(block)
        if not inlet and fallback_inlet:
            inlet = fallback_inlet
        if not outlet and fallback_outlet:
            outlet = fallback_outlet
        source_by_block[block_id] = "inlet_streams/outlet_streams" if (raw_inlet or raw_outlet) else ("connections/port_detail" if (fallback_inlet or fallback_outlet) else "none")
        inlet_by_block[block_id] = inlet
        outlet_by_block[block_id] = outlet
        referenced_streams.update(inlet)
        referenced_streams.update(outlet)

    # A referenced stream without a result row remains visible, but its missing
    # data is an explicit topology/evidence warning rather than an invented row.
    for stream_id in referenced_streams:
        streams.setdefault(stream_id, {"stream_id": stream_id, "data_status": "REFERENCED_STREAM_DATA_MISSING"})

    producers: dict[str, list[str]] = defaultdict(list)
    consumers: dict[str, list[str]] = defaultdict(list)
    for block_id in sorted(blocks):
        for stream_id in outlet_by_block[block_id]:
            producers[stream_id].append(block_id)
        for stream_id in inlet_by_block[block_id]:
            consumers[stream_id].append(block_id)
    return _Topology(
        blocks=blocks,
        streams=streams,
        inlet_by_block=inlet_by_block,
        outlet_by_block=outlet_by_block,
        producers_by_stream={key: tuple(sorted(value)) for key, value in producers.items()},
        consumers_by_stream={key: tuple(sorted(value)) for key, value in consumers.items()},
        connectivity_source_by_block=source_by_block,
    )


def _stream_phase(stream: Mapping[str, Any] | None) -> str | None:
    if not stream:
        return None
    values = _field_values(stream, STREAM_FIELD_ALIASES)
    phase = str(values.get("phase", "")).strip().casefold()
    if phase:
        if any(token in phase for token in ("vap", "gas", "气", "汽")):
            return "vapor"
        if any(token in phase for token in ("liq", "液")):
            return "liquid"
        if any(token in phase for token in ("mix", "two", "两相", "混")):
            return "mixed"
    vapor_fraction = _finite(values.get("vapor_fraction"))
    if vapor_fraction is not None:
        if vapor_fraction >= 0.95:
            return "vapor"
        if vapor_fraction <= 0.05:
            return "liquid"
        return "mixed"
    return None


def _stream_pressure(stream: Mapping[str, Any] | None) -> float | None:
    if not stream:
        return None
    return _finite(_field_values(stream, STREAM_FIELD_ALIASES).get("pressure_bar"))


def _display_parameters(
    record: Mapping[str, Any],
    meta: Iterable[tuple[str, str, str]],
    aliases: Mapping[str, Iterable[str]],
    *,
    canonical_only: bool = False,
    source_status: str = "ASPEN_EXPORTED_VALUE",
    source_status_by_field: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    if canonical_only:
        values = {
            field: record[field]
            for field, _label, _unit in meta
            if field in record and record[field] not in (None, "")
        }
    else:
        values = _field_values(record, aliases)
    status_by_field = dict(source_status_by_field or {})
    rows: list[dict[str, Any]] = []
    for field, label, unit in meta:
        if field not in values:
            continue
        raw_item = values[field]
        metadata: dict[str, Any] = {}
        if isinstance(raw_item, Mapping) and "value" in raw_item:
            metadata = {
                str(key): value
                for key, value in raw_item.items()
                if key not in {"value", "canonical_unit", "formal_design_evidence"}
            }
            canonical_unit = str(raw_item.get("canonical_unit", ""))
            if canonical_unit != unit:
                rows.append({
                    "field": field,
                    "label": label,
                    "value": None,
                    "unit": "",
                    "display": "单位归一化待复核",
                    **metadata,
                    "expected_canonical_unit": unit,
                    "received_canonical_unit": canonical_unit,
                    "source_status": "BLOCKED_UNIT_NORMALIZATION",
                    "formal_design_evidence": False,
                })
                continue
            value = raw_item["value"]
        else:
            value = raw_item
        rows.append({
            "field": field,
            "label": label,
            "value": value,
            "unit": unit,
            "display": f"{_compact(value)}{(' ' + unit) if unit else ''}",
            **metadata,
            "source_status": metadata.get("source_status", status_by_field.get(field, source_status)),
            "formal_design_evidence": False,
        })
    return rows


def canonical_parameters_by_block(derivation_result: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Extract trusted, unit-normalized block inputs from one adapter result.

    Aspen block output cards often use units different from the application
    fields (for example W versus kW, J/kg versus m, fraction versus percent,
    and bar versus kPa).  A PFD parameter card must therefore consume the same
    ``canonical_match_input`` used by deterministic matching, never relabel a
    raw Aspen card value with a target unit.
    """

    if not isinstance(derivation_result, Mapping):
        return {}
    rows = derivation_result.get("equipment")
    if not isinstance(rows, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        block_id = str(row.get("aspen_block_id") or row.get("equipment_tag") or "").strip()
        canonical = row.get("pfd_parameters")
        if not isinstance(canonical, Mapping):
            canonical = row.get("canonical_match_input")
        if not block_id or not isinstance(canonical, Mapping):
            continue
        if block_id in result:
            raise AspenPFDMappingError(
                "DUPLICATE_CANONICAL_PARAMETER_BLOCK",
                f"设备推导结果包含重复模块：{block_id}",
                {"block_id": block_id},
            )
        result[block_id] = dict(canonical)
    return dict(sorted(result.items()))


def canonical_parameters_by_stream(derivation_result: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Extract display-safe, unit-normalized stream fields from one adapter result."""

    if not isinstance(derivation_result, Mapping):
        return {}
    rows = derivation_result.get("piping")
    if not isinstance(rows, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        stream_id = str(row.get("stream_id") or "").strip()
        canonical = row.get("pfd_parameters")
        if not stream_id or not isinstance(canonical, Mapping):
            continue
        if stream_id in result:
            raise AspenPFDMappingError(
                "DUPLICATE_CANONICAL_PARAMETER_STREAM",
                f"设备推导结果包含重复流股：{stream_id}",
                {"stream_id": stream_id},
            )
        result[stream_id] = dict(canonical)
    return dict(sorted(result.items()))


def _normalize_canonical_parameters(
    topology: _Topology,
    values: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    if values is None:
        return {}
    if not isinstance(values, Mapping):
        raise AspenPFDMappingError(
            "INVALID_CANONICAL_PARAMETER_MAP",
            "canonical_parameters_by_block 必须是 block_id -> canonical field -> value 对象。",
        )
    normalized: dict[str, dict[str, Any]] = {}
    for raw_block_id, raw_parameters in values.items():
        block_id = str(raw_block_id).strip()
        if block_id not in topology.blocks:
            raise AspenPFDMappingError(
                "UNKNOWN_CANONICAL_PARAMETER_BLOCK",
                f"规范参数指向未知模块：{block_id}",
                {"block_id": block_id},
            )
        if not isinstance(raw_parameters, Mapping):
            raise AspenPFDMappingError(
                "INVALID_CANONICAL_PARAMETER_ROW",
                f"模块 {block_id} 的规范参数不是对象。",
                {"block_id": block_id},
            )
        normalized[block_id] = dict(raw_parameters)
    return dict(sorted(normalized.items()))


def _normalize_canonical_stream_parameters(
    topology: _Topology,
    values: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    if values is None:
        return {}
    if not isinstance(values, Mapping):
        raise AspenPFDMappingError(
            "INVALID_CANONICAL_STREAM_PARAMETER_MAP",
            "canonical_parameters_by_stream 必须是 stream_id -> canonical field -> value 对象。",
        )
    normalized: dict[str, dict[str, Any]] = {}
    for raw_stream_id, raw_parameters in values.items():
        stream_id = str(raw_stream_id).strip()
        if stream_id not in topology.streams:
            raise AspenPFDMappingError(
                "UNKNOWN_CANONICAL_PARAMETER_STREAM",
                f"规范参数指向未知流股：{stream_id}",
                {"stream_id": stream_id},
            )
        if not isinstance(raw_parameters, Mapping):
            raise AspenPFDMappingError(
                "INVALID_CANONICAL_STREAM_PARAMETER_ROW",
                f"流股 {stream_id} 的规范参数不是对象。",
                {"stream_id": stream_id},
            )
        normalized[stream_id] = dict(raw_parameters)
    return dict(sorted(normalized.items()))


class _CandidateAccumulator:
    def __init__(self, by_id: Mapping[str, Mapping[str, Any]], by_family: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
        self.by_id = by_id
        self.by_family = by_family
        self.scores: dict[str, int] = defaultdict(int)
        self.evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def add_selection(self, selection_id: str, score: int, code: str, reason: str, source: str, strength: str = "supporting") -> None:
        if selection_id not in self.by_id:
            return
        self.scores[selection_id] += score
        self.evidence[selection_id].append({
            "code": code,
            "evidence_class": "D",
            "source": source,
            "strength": strength,
            "reason": reason,
        })

    def add_family(self, family_id: str, score: int, code: str, reason: str, source: str, strength: str = "supporting") -> None:
        for item in self.by_family.get(family_id, ()):
            self.add_selection(str(item["selection_id"]), score, code, reason, source, strength)


def _equipment_map_row(bundle: Mapping[str, Any], block_id: str) -> dict[str, Any]:
    rows = bundle.get("equipment_map")
    if not isinstance(rows, list):
        return {}
    for raw in rows:
        if isinstance(raw, Mapping) and str(raw.get("block_id", "")).strip() == block_id:
            return dict(raw)
    return {}


def _text_feature(acc: _CandidateAccumulator, text: str, source: str) -> None:
    normalized = text.casefold()
    rules: tuple[tuple[tuple[str, ...], tuple[str, ...], int, str], ...] = (
        (("pump", "泵", "liquid pressure boosting"), ("family_pump",), 6, "TEXT_PUMP"),
        (("compress", "blower", "fan", "压缩", "风机"), ("family_compressor",), 6, "TEXT_COMPRESSOR"),
        (("tower", "column", "distill", "absorb", "extract", "塔", "精馏", "吸收", "萃取"), ("family_tower",), 6, "TEXT_TOWER"),
        (("heat exchanger", "heater", "cooler", "换热", "加热", "冷却"), ("family_other_heat_exchanger", "family_fixed_tubesheet_exchanger"), 5, "TEXT_EXCHANGER"),
        (("reactor", "reaction", "反应"), ("family_reactor_vessel_separator",), 6, "TEXT_REACTOR"),
        (("separator", "flash", "decant", "分离", "闪蒸", "沉降"), ("family_reactor_vessel_separator",), 6, "TEXT_SEPARATOR"),
        (("storage", "tank", "buffer", "储罐", "缓冲罐"), ("family_storage_vessel",), 7, "TEXT_STORAGE"),
        (("valve", "throttle", "阀", "节流"), ("family_valve",), 7, "TEXT_VALVE"),
        (("static mixer", "静态混合"), ("family_static_mixer",), 7, "TEXT_STATIC_MIXER"),
        (("agitator", "stirrer", "搅拌"), ("family_agitator",), 7, "TEXT_AGITATOR"),
        (("membrane", "膜"), ("family_membrane",), 7, "TEXT_MEMBRANE"),
        (("pipe", "piping", "管道"), ("family_process_piping",), 6, "TEXT_PIPE"),
        (("flange", "gasket", "法兰", "垫片"), ("family_flange_gasket",), 7, "TEXT_FLANGE"),
        (("fitting", "elbow", "tee", "管件", "弯头", "三通"), ("family_pipe_fitting",), 7, "TEXT_FITTING"),
        (("package", "skid", "adsorb", "dryer", "撬装", "成套", "吸附", "干燥"), ("family_package_equipment",), 6, "TEXT_PACKAGE"),
    )
    for tokens, families, score, code in rules:
        if any(token in normalized for token in tokens):
            for family in families:
                acc.add_family(family, score, code, f"文字条件命中：{text}", source, "strong")


def _automatic_mapping(
    bundle: Mapping[str, Any],
    topology: _Topology,
    block_id: str,
    catalog: Mapping[str, Any],
    by_id: Mapping[str, Mapping[str, Any]],
    by_block_type: Mapping[str, Mapping[str, Any]],
    by_family: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    block = topology.blocks[block_id]
    raw_type = str(block.get("block_type", "")).strip()
    block_type = _normalize_token(raw_type)
    source = str(block.get("block_type_source", "block.block_type"))
    inlet = topology.inlet_by_block[block_id]
    outlet = topology.outlet_by_block[block_id]
    map_row = _equipment_map_row(bundle, block_id)

    direct = by_block_type.get(block_type)
    if direct is not None and block_type not in UNKNOWN_BLOCK_TYPES:
        candidate = _candidate_payload(direct, 100, [{
            "code": "DIRECT_ASPEN_BLOCK_TYPE_MATCH",
            "evidence_class": "R",
            "source": source,
            "strength": "decisive",
            "reason": f"Aspen 模块类别 {raw_type} 与应用目录精确一致。",
        }], 0)
        return _finalize_automatic(
            status="AUTO_EXACT",
            candidates=[candidate],
            selected=candidate,
            confidence="EXACT",
            source_type=raw_type,
            inference_basis="ASPEN_BLOCK_TYPE",
        )

    alias_selection = UNIQUE_BLOCK_TYPE_ALIASES.get(block_type)
    if alias_selection in by_id:
        item = by_id[alias_selection]
        candidate = _candidate_payload(item, 90, [{
            "code": "ASPEN_BLOCK_TYPE_ALIAS",
            "evidence_class": "D",
            "source": source,
            "strength": "decisive",
            "reason": f"模块类别 {raw_type} 按冻结别名映射为 {item.get('display_name')}。",
        }], 0)
        return _finalize_automatic(
            status="AUTO_INFERRED_UNIQUE",
            candidates=[candidate],
            selected=candidate,
            confidence="HIGH",
            source_type=raw_type,
            inference_basis="FROZEN_BLOCK_TYPE_ALIAS",
        )

    acc = _CandidateAccumulator(by_id, by_family)
    if block_type in GENERAL_BLOCK_TYPE_FAMILIES:
        for family_id in GENERAL_BLOCK_TYPE_FAMILIES[block_type]:
            acc.add_family(
                family_id,
                8,
                "GENERAL_ASPEN_BLOCK_CATEGORY",
                f"模块类别 {raw_type} 只支持设备上位族，不能确定专用子型。",
                source,
                "strong",
            )

    # equipment_map is useful when COM did not expose HAP_RECORDTYPE.  It does
    # not outrank a readable direct block_type above.
    equipment_type = _normalize_token(map_row.get("equipment_type"))
    if equipment_type in by_block_type:
        item = by_block_type[equipment_type]
        acc.add_selection(str(item["selection_id"]), 9, "EQUIPMENT_MAP_TYPE", "equipment_map 给出了目录内模块类型。", "equipment_map.equipment_type", "strong")
    family_text = str(map_row.get("equipment_family", "")).strip()
    if family_text:
        normalized_family = _normalize_token(family_text)
        for family_id, selections in by_family.items():
            family_name = str(selections[0].get("family_name", "")) if selections else ""
            if normalized_family in {_normalize_token(family_id), _normalize_token(family_name)}:
                acc.add_family(family_id, 8, "EQUIPMENT_MAP_FAMILY", "equipment_map 给出了目录内设备族。", "equipment_map.equipment_family", "strong")

    for field in ("process_function", "equipment_type", "equipment_family"):
        text = str(map_row.get(field, "")).strip()
        if text:
            _text_feature(acc, text, f"equipment_map.{field}")
    for field in ("process_function", "name", "description"):
        text = str(block.get(field, "")).strip()
        if text:
            _text_feature(acc, text, f"block.{field}")

    values = _field_values(block, BLOCK_FIELD_ALIASES)
    inlet_streams = [topology.streams.get(item) for item in inlet]
    outlet_streams = [topology.streams.get(item) for item in outlet]
    inlet_phases = {phase for phase in (_stream_phase(item) for item in inlet_streams) if phase}
    outlet_phases = {phase for phase in (_stream_phase(item) for item in outlet_streams) if phase}
    inlet_pressures = [p for p in (_stream_pressure(item) for item in inlet_streams) if p is not None]
    outlet_pressures = [p for p in (_stream_pressure(item) for item in outlet_streams) if p is not None]
    pressure_delta = None
    if inlet_pressures and outlet_pressures:
        pressure_delta = max(outlet_pressures) - min(inlet_pressures)

    def family(family_id: str, score: int, code: str, reason: str, field: str, strength: str = "supporting") -> None:
        acc.add_family(family_id, score, code, reason, field, strength)

    # Strong physical fingerprints.  Scores are integer and frozen so the same
    # export gives byte-stable candidate ordering without a model or network.
    if "head_m" in values:
        family("family_pump", 7, "FIELD_HEAD", "扬程字段是液体泵的强特征。", "block.head_m/HEAD_CAL", "strong")
    if "pressure_ratio" in values:
        ratio = _finite(values["pressure_ratio"])
        if ratio is not None and ratio > 1.0:
            family("family_compressor", 5, "FIELD_PRESSURE_RATIO_GT_ONE", "压比大于 1 支持气体压缩设备。", "block.pressure_ratio", "strong")
        elif ratio is not None and 0 < ratio < 1.0:
            family("family_gas_expander_turbine", 4, "FIELD_PRESSURE_RATIO_LT_ONE", "压比小于 1 支持膨胀/动力回收。", "block.pressure_ratio", "strong")
            family("family_liquid_power_recovery_turbine", 4, "FIELD_PRESSURE_RATIO_LT_ONE", "压比小于 1 支持膨胀/动力回收。", "block.pressure_ratio", "strong")
    power_fields = {
        "hydraulic_power_kw",
        "shaft_power_kw",
        "electrical_power_kw",
    }
    if power_fields.intersection(values):
        power_field_route = (
            "block.hydraulic_power_kw/"
            "shaft_power_kw/electrical_power_kw"
        )
        for family_id in (
            "family_pump",
            "family_compressor",
            "family_gas_expander_turbine",
            "family_liquid_power_recovery_turbine",
            "family_agitator",
        ):
            family(
                family_id,
                1,
                "FIELD_ROTATING_EQUIPMENT_POWER",
                "流体、轴或电功率是旋转设备的共有辅助特征。",
                power_field_route,
            )
    if "heat_duty_kw" in values or "heat_transfer_area_m2" in values:
        if len(inlet) >= 2 and len(outlet) >= 2:
            acc.add_selection("block:HEATX", 8, "HEAT_FIELD_TWO_SIDE_PORTS", "热负荷/面积且至少两进两出，支持两股流换热模块。", "block fields + ports", "strong")
            family("family_fixed_tubesheet_exchanger", 3, "HEAT_FIELD_CONSTRUCTION_OPEN", "流程数据不能独自确定固定管板结构。", "block fields + ports")
        elif len(inlet) == 1 and len(outlet) == 1:
            acc.add_selection("block:HEATER", 8, "HEAT_FIELD_ONE_SIDE_PORTS", "热负荷且一进一出，支持 Aspen HEATER/COOLER 类模块。", "block fields + ports", "strong")
            family("family_fixed_tubesheet_exchanger", 2, "HEAT_FIELD_CONSTRUCTION_OPEN", "流程数据不能独自确定固定管板结构。", "block fields + ports")
        else:
            family("family_other_heat_exchanger", 5, "FIELD_HEAT_DUTY_OR_AREA", "热负荷/面积支持换热设备族。", "block.heat_duty_kw/area", "strong")
            family("family_fixed_tubesheet_exchanger", 5, "FIELD_HEAT_DUTY_OR_AREA", "热负荷/面积不能确定换热器结构。", "block.heat_duty_kw/area", "strong")
    if "stage_count" in values:
        family("family_tower", 7, "FIELD_STAGE_COUNT", "理论级/塔板数是塔器强特征。", "block.stage_count/NSTAGE", "strong")
        if "pressure_ratio" in values:
            family("family_compressor", 2, "FIELD_STAGE_AND_PRESSURE_RATIO", "级数与压比组合也支持多级压缩。", "block.stage_count + pressure_ratio")
    geometry_count = sum(field in values for field in ("volume_m3", "diameter_mm", "height_mm"))
    if geometry_count:
        score = 2 + geometry_count
        family("family_reactor_vessel_separator", score, "VESSEL_GEOMETRY_FIELDS", "容积/直径/高度支持容器类设备，但不能确定反应或分离子型。", "block geometry")
        family("family_storage_vessel", score, "VESSEL_GEOMETRY_FIELDS", "容积/直径/高度也支持储存容器，需功能证据消歧。", "block geometry")
    if (
        "pressure_drop_kpa" in values
        and not power_fields.intersection(values)
    ):
        family("family_valve", 3, "FIELD_PRESSURE_DROP", "无轴功的压降字段支持节流/阀门候选。", "block.pressure_drop_kpa")
        family("family_static_mixer", 2, "FIELD_PRESSURE_DROP", "静态混合器也以压降为关键约束。", "block.pressure_drop_kpa")

    if pressure_delta is not None:
        if pressure_delta > 1e-9:
            if "liquid" in inlet_phases and "vapor" not in inlet_phases:
                family("family_pump", 5, "LIQUID_PRESSURE_RISE", "液相流股压力升高支持泵。", "connected streams", "strong")
            if "vapor" in inlet_phases and "liquid" not in inlet_phases:
                family("family_compressor", 5, "VAPOR_PRESSURE_RISE", "气相流股压力升高支持压缩机。", "connected streams", "strong")
        elif pressure_delta < -1e-9:
            if "vapor" in inlet_phases and "liquid" not in inlet_phases:
                family("family_gas_expander_turbine", 5, "VAPOR_PRESSURE_DROP", "气相压降支持膨胀机候选；是否做功仍需字段证据。", "connected streams", "strong")
                family("family_valve", 2, "PRESSURE_DROP_VALVE_ALTERNATIVE", "无做功证据时阀门仍是候选。", "connected streams")
            if "liquid" in inlet_phases and "vapor" not in inlet_phases:
                family("family_liquid_power_recovery_turbine", 5, "LIQUID_PRESSURE_DROP", "液相压降支持液力回收透平候选；是否做功仍需字段证据。", "connected streams", "strong")
                family("family_valve", 2, "PRESSURE_DROP_VALVE_ALTERNATIVE", "无做功证据时阀门仍是候选。", "connected streams")

    if len(inlet) >= 2 and len(outlet) == 1 and "heat_duty_kw" not in values:
        family("family_static_mixer", 3, "PORTS_MANY_IN_ONE_OUT", "多进一出支持混合功能，但不能确定静态混合器/搅拌容器/管件。", "block ports")
        family("family_agitator", 2, "PORTS_MANY_IN_ONE_OUT", "多进一出也可能进入搅拌容器。", "block ports")
        family("family_pipe_fitting", 2, "PORTS_MANY_IN_ONE_OUT", "多进一出也可能是管汇/三通。", "block ports")
    if len(inlet) == 1 and len(outlet) >= 2 and "stage_count" not in values:
        family("family_reactor_vessel_separator", 3, "PORTS_ONE_IN_MANY_OUT", "一进多出支持分离容器候选。", "block ports")
        family("family_pipe_fitting", 2, "PORTS_ONE_IN_MANY_OUT", "一进多出也可能只是分流管件。", "block ports")

    ranked = sorted(acc.scores, key=lambda selection_id: (-acc.scores[selection_id], selection_id))
    candidates = [
        _candidate_payload(by_id[selection_id], acc.scores[selection_id], acc.evidence[selection_id], rank)
        for rank, selection_id in enumerate(ranked[:12])
    ]
    if not candidates:
        return _finalize_automatic(
            status="AUTO_UNRESOLVED",
            candidates=[],
            selected=None,
            confidence="NONE",
            source_type=raw_type or None,
            inference_basis="NO_DECISIVE_FEATURE",
        )

    top = candidates[0]
    second_score = candidates[1]["score"] if len(candidates) > 1 else 0
    margin = top["score"] - second_score
    decisive = any(item.get("strength") in {"decisive", "strong"} for item in top["evidence"])
    # A feature-only result is selected only when it has a strong signal and a
    # material lead.  A group of equally-scored Aspen subtypes remains open.
    unique = top["score"] >= 8 and decisive and (len(candidates) == 1 or margin >= 4)
    if unique:
        confidence = "HIGH" if top["score"] >= 10 and margin >= 5 else "MEDIUM"
        return _finalize_automatic(
            status="AUTO_INFERRED_UNIQUE",
            candidates=candidates,
            selected=top,
            confidence=confidence,
            source_type=raw_type or None,
            inference_basis="DETERMINISTIC_FIELD_PORT_STREAM_FEATURES",
        )
    confidence = "MEDIUM" if top["score"] >= 8 else "LOW"
    return _finalize_automatic(
        status="AUTO_AMBIGUOUS",
        candidates=candidates,
        selected=None,
        confidence=confidence,
        source_type=raw_type or None,
        inference_basis="DETERMINISTIC_CANDIDATES_NOT_UNIQUE",
    )


def _candidate_payload(item: Mapping[str, Any], score: int, evidence: Sequence[Mapping[str, Any]], rank: int) -> dict[str, Any]:
    if score >= 90:
        confidence = "EXACT" if score >= 100 else "HIGH"
    elif score >= 10:
        confidence = "HIGH"
    elif score >= 6:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"
    return {
        "rank": rank + 1,
        "selection_id": item.get("selection_id"),
        "block_type": item.get("block_type"),
        "family_id": item.get("family_id"),
        "family_name": item.get("family_name"),
        "display_name": item.get("display_name"),
        "score": score,
        "confidence_level": confidence,
        "evidence": [dict(row) for row in evidence],
        "model_promotion_allowed": False,
    }


def _finalize_automatic(
    *,
    status: str,
    candidates: list[dict[str, Any]],
    selected: Mapping[str, Any] | None,
    confidence: str,
    source_type: str | None,
    inference_basis: str,
) -> dict[str, Any]:
    # The most-general automatic family is the common family of the *leading
    # tied candidates*.  Low-scoring alternatives remain visible for review,
    # but must not erase a well-supported common parent (for example COMPR and
    # MCOMPR tied above generic rotating-equipment alternatives).
    leading_score = candidates[0].get("score") if candidates else None
    leading_candidates = [item for item in candidates if item.get("score") == leading_score]
    family_ids = {str(item.get("family_id")) for item in leading_candidates if item.get("family_id")}
    common_family_id = next(iter(family_ids)) if len(family_ids) == 1 else None
    common_family_name = None
    if common_family_id:
        common_family_name = next((item.get("family_name") for item in leading_candidates if item.get("family_id") == common_family_id), None)
    return {
        "status": status,
        "source_block_type": source_type,
        "inference_basis": inference_basis,
        "confidence_level": confidence,
        "selection_id": selected.get("selection_id") if selected else None,
        "block_type": selected.get("block_type") if selected else None,
        "family_id": selected.get("family_id") if selected else common_family_id,
        "family_name": selected.get("family_name") if selected else common_family_name,
        "display_name": selected.get("display_name") if selected else (f"{common_family_name}（子型待确认）" if common_family_name else "设备类型待确认"),
        "candidate_options": candidates,
        "ambiguity_retained": status in {"AUTO_AMBIGUOUS", "AUTO_UNRESOLVED"},
        "evidence_gate": {
            "status": "TYPE_MAPPING_ONLY_NOT_MODEL_EVIDENCE",
            "formal_design_evidence": False,
            "model_promotion_allowed": False,
            "reason": "Aspen 模块/特征只能映射设备类型，不能证明机械结构、厂家型号或正式设计状态。",
        },
    }


def _validate_overrides(topology: _Topology, overrides: Mapping[str, Any] | None, by_id: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    if overrides is None:
        return normalized
    if not isinstance(overrides, Mapping):
        raise AspenPFDMappingError("INVALID_OVERRIDE_MAP", "overrides 必须是 block_id -> selection_id 对象。")
    for raw_block_id, raw_selection_id in overrides.items():
        block_id = str(raw_block_id).strip()
        if block_id not in topology.blocks:
            raise AspenPFDMappingError("UNKNOWN_OVERRIDE_BLOCK", f"人工改型指向未知模块：{block_id}", {"block_id": block_id})
        selection_id = str(raw_selection_id).strip()
        if selection_id not in by_id:
            raise AspenPFDMappingError(
                "INVALID_OVERRIDE_SELECTION",
                f"模块 {block_id} 的人工类型不在应用目录：{selection_id}",
                {"block_id": block_id, "selection_id": selection_id, "allowed_selection_ids": sorted(by_id)},
            )
        normalized[block_id] = selection_id
    return dict(sorted(normalized.items()))


def _effective_mapping(automatic: Mapping[str, Any], override_selection: Mapping[str, Any] | None) -> dict[str, Any]:
    if override_selection is None:
        return {
            "mode": "automatic",
            "status": automatic.get("status"),
            "selection_id": automatic.get("selection_id"),
            "block_type": automatic.get("block_type"),
            "family_id": automatic.get("family_id"),
            "family_name": automatic.get("family_name"),
            "display_name": automatic.get("display_name"),
            "confidence_level": automatic.get("confidence_level"),
            "ambiguity_retained": automatic.get("ambiguity_retained", True),
            "evidence_gate": dict(automatic.get("evidence_gate", {})),
        }
    return {
        "mode": "user_override",
        "status": "USER_OVERRIDE_VALIDATED",
        "selection_id": override_selection.get("selection_id"),
        "block_type": override_selection.get("block_type"),
        "family_id": override_selection.get("family_id"),
        "family_name": override_selection.get("family_name"),
        "display_name": override_selection.get("display_name"),
        "confidence_level": "USER_SPECIFIED",
        "ambiguity_retained": False,
        "override_provenance": {
            "status": "USER_EXPLICIT_UNVERIFIED_TYPE_CHOICE",
            "evidence_class": "J",
            "formal_design_evidence": False,
        },
        "evidence_gate": {
            "status": "USER_TYPE_OVERRIDE_NOT_MODEL_EVIDENCE",
            "formal_design_evidence": False,
            "model_promotion_allowed": False,
            "reason": "人工改型只改变映射和后续计算路线；仍需重算及同设备证据门。",
        },
    }


def _impact_ledger(
    topology: _Topology,
    changed_block_ids: Iterable[str],
    *,
    change_kind: str = "type",
) -> dict[str, Any]:
    changed = sorted({item for item in changed_block_ids if item in topology.blocks})
    affected_streams: set[str] = set()
    upstream: set[str] = set()
    downstream: set[str] = set()
    for block_id in changed:
        incident_in = topology.inlet_by_block[block_id]
        incident_out = topology.outlet_by_block[block_id]
        affected_streams.update(incident_in)
        affected_streams.update(incident_out)
        for stream_id in incident_in:
            upstream.update(topology.producers_by_stream.get(stream_id, ()))
        for stream_id in incident_out:
            downstream.update(topology.consumers_by_stream.get(stream_id, ()))
    upstream.difference_update(changed)
    downstream.difference_update(changed)
    normalized_kind = "parameter" if str(change_kind).casefold() == "parameter" else "type"
    if not changed:
        status = "NO_PARAMETER_CHANGE" if normalized_kind == "parameter" else "NO_TYPE_CHANGE"
    else:
        status = (
            "PENDING_RECALC_AFTER_PARAMETER_CHANGE"
            if normalized_kind == "parameter"
            else "PENDING_RECALC_AFTER_TYPE_CHANGE"
        )
    invalidated_scopes = [
        "equipment_design_parameter_package",
        "constraint_checks",
        "model_recommendation",
        "customer_delivery_projection",
    ]
    if normalized_kind == "type":
        invalidated_scopes.insert(0, "block_type_binding")
    return {
        "status": status,
        "change_kind": normalized_kind,
        "changed_blocks": changed,
        "affected_streams": sorted(affected_streams),
        "immediate_upstream_blocks": sorted(upstream),
        "immediate_downstream_blocks": sorted(downstream),
        "unchanged_blocks": sorted(set(topology.blocks) - set(changed) - upstream - downstream),
        "invalidated_scopes": invalidated_scopes if changed else [],
        "propagation_policy": "changed block + incident streams + immediate upstream/downstream only; no unrelated device is invalidated",
    }


def _recalc_state(block_id: str, impact: Mapping[str, Any]) -> str:
    if block_id in impact["changed_blocks"]:
        return (
            "PARAMETERS_CHANGED_PENDING_RECALC"
            if impact.get("change_kind") == "parameter"
            else "TYPE_CHANGED_PENDING_RECALC"
        )
    if block_id in impact["immediate_upstream_blocks"]:
        return "UPSTREAM_RELATED_PENDING_RECALC"
    if block_id in impact["immediate_downstream_blocks"]:
        return "DOWNSTREAM_RELATED_PENDING_RECALC"
    return "STABLE"


def _stream_edges(
    topology: _Topology,
    impact: Mapping[str, Any],
    canonical_parameters: Mapping[str, Mapping[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    boundary_nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    canonical_by_stream = dict(canonical_parameters or {})
    for stream_id in sorted(topology.streams):
        producers = topology.producers_by_stream.get(stream_id, ())
        consumers = topology.consumers_by_stream.get(stream_id, ())
        topology_status = "PASS"
        if len(producers) > 1:
            topology_status = "MULTIPLE_PRODUCERS_REVIEW"
        elif len(consumers) > 1:
            topology_status = "MULTIPLE_CONSUMERS_REVIEW"
        elif not producers and not consumers:
            topology_status = "ORPHAN_STREAM_REVIEW"
        elif not producers:
            topology_status = "EXTERNAL_FEED"
        elif not consumers:
            topology_status = "EXTERNAL_OUTLET"

        sources = list(producers)
        targets = list(consumers)
        if not sources:
            node_id = f"boundary:feed:{stream_id}"
            boundary_nodes[node_id] = {
                "node_id": node_id,
                "kind": "boundary_feed",
                "label": f"{stream_id} · 外部进料",
                "stream_id": stream_id,
                "recalculation_status": "RELATED_STREAM_PENDING_RECALC" if stream_id in impact["affected_streams"] else "STABLE",
            }
            sources = [node_id]
        else:
            sources = [f"block:{item}" for item in sources]
        if not targets:
            node_id = f"boundary:outlet:{stream_id}"
            boundary_nodes[node_id] = {
                "node_id": node_id,
                "kind": "boundary_outlet",
                "label": f"{stream_id} · 外部出口",
                "stream_id": stream_id,
                "recalculation_status": "RELATED_STREAM_PENDING_RECALC" if stream_id in impact["affected_streams"] else "STABLE",
            }
            targets = [node_id]
        else:
            targets = [f"block:{item}" for item in targets]

        display_record = {
            field: topology.streams[stream_id][field]
            for field, _label, _unit in STREAM_PARAMETER_META
            if field in topology.streams[stream_id] and topology.streams[stream_id][field] not in (None, "")
        }
        canonical_stream = dict(canonical_by_stream.get(stream_id, {}))
        if "pressure_mpa" in canonical_stream:
            display_record.pop("pressure_bar", None)
        display_record.update(canonical_stream)
        combinations = [(source, target) for source in sources for target in targets]
        for index, (source, target) in enumerate(combinations, start=1):
            edge_id = f"stream:{stream_id}" if len(combinations) == 1 else f"stream:{stream_id}:{index}"
            edges.append({
                "edge_id": edge_id,
                "kind": "process_stream_pipeline",
                "stream_id": stream_id,
                "label": stream_id,
                "source_node_id": source,
                "target_node_id": target,
                "topology_status": topology_status,
                "parameters": _display_parameters(
                    display_record,
                    STREAM_PARAMETER_META,
                    STREAM_FIELD_ALIASES,
                    canonical_only=True,
                    source_status="CANONICAL_FIELD_VALUE",
                    source_status_by_field={field: "ASPEN_DERIVED_PROCESS_SIDE" for field in canonical_stream},
                ),
                "recalculation_status": "RELATED_STREAM_PENDING_RECALC" if stream_id in impact["affected_streams"] else "STABLE",
                "formal_design_evidence": False,
            })
    return list(boundary_nodes.values()), edges


def _tarjan_scc(node_ids: Sequence[str], adjacency: Mapping[str, Sequence[str]]) -> list[list[str]]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    components: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlink[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in sorted(adjacency.get(node, ())):
            if target not in indices:
                visit(target)
                lowlink[node] = min(lowlink[node], lowlink[target])
            elif target in on_stack:
                lowlink[node] = min(lowlink[node], indices[target])
        if lowlink[node] == indices[node]:
            component: list[str] = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component.append(member)
                if member == node:
                    break
            components.append(sorted(component))

    for node in sorted(node_ids):
        if node not in indices:
            visit(node)
    return components


def _layout(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    node_ids = sorted(item["node_id"] for item in nodes)
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    reverse_adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    for edge in edges:
        source = str(edge["source_node_id"])
        target = str(edge["target_node_id"])
        if source != target:
            adjacency[source].add(target)
            reverse_adjacency[target].add(source)
    components = _tarjan_scc(node_ids, {key: sorted(value) for key, value in adjacency.items()})

    # Deterministic Eades-style cycle removal.  A whole strongly connected
    # component must not collapse into one visual column: that made every
    # internal process edge look like a recycle.  The resulting total order
    # defines a feedback-free DAG; only edges opposing that order use recycle
    # rails.
    remaining = set(node_ids)
    work_out = {node: set(adjacency[node]) for node in node_ids}
    work_in = {node: set(reverse_adjacency[node]) for node in node_ids}
    left_order: list[str] = []
    right_order: list[str] = []

    def remove_order_node(node_id: str) -> None:
        for predecessor in list(work_in[node_id]):
            work_out[predecessor].discard(node_id)
        for successor in list(work_out[node_id]):
            work_in[successor].discard(node_id)
        remaining.discard(node_id)

    while remaining:
        sink = min((node for node in remaining if not work_out[node]), default=None)
        if sink is not None:
            right_order.append(sink)
            remove_order_node(sink)
            continue
        source = min((node for node in remaining if not work_in[node]), default=None)
        if source is not None:
            left_order.append(source)
            remove_order_node(source)
            continue
        chosen = min(
            remaining,
            key=lambda node: (-(len(work_out[node]) - len(work_in[node])), node),
        )
        left_order.append(chosen)
        remove_order_node(chosen)

    linear_order = left_order + list(reversed(right_order))
    order_index = {node: index for index, node in enumerate(linear_order)}
    feedback_edge_ids = {
        str(edge["edge_id"])
        for edge in edges
        if edge["source_node_id"] == edge["target_node_id"]
        or order_index[str(edge["source_node_id"])] >= order_index[str(edge["target_node_id"])]
    }
    forward_adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    forward_indegree = {node_id: 0 for node_id in node_ids}
    for edge in edges:
        if str(edge["edge_id"]) in feedback_edge_ids:
            continue
        source = str(edge["source_node_id"])
        target = str(edge["target_node_id"])
        if target not in forward_adjacency[source]:
            forward_adjacency[source].add(target)
            forward_indegree[target] += 1
    layers = {node_id: 0 for node_id in node_ids}
    queue = deque(sorted((node for node, degree in forward_indegree.items() if degree == 0), key=lambda node: (order_index[node], node)))
    while queue:
        source = queue.popleft()
        for target in sorted(forward_adjacency[source], key=lambda node: (order_index[node], node)):
            layers[target] = max(layers[target], layers[source] + 1)
            forward_indegree[target] -= 1
            if forward_indegree[target] == 0:
                queue.append(target)

    node_by_id = {item["node_id"]: item for item in nodes}
    by_layer: dict[int, list[str]] = defaultdict(list)
    for node_id in node_ids:
        by_layer[layers[node_id]].append(node_id)
    kind_order = {"boundary_feed": 0, "equipment": 1, "boundary_outlet": 2}
    positions: dict[str, dict[str, float]] = {}
    x_spacing = 260.0
    y_spacing = 140.0
    for layer in sorted(by_layer):
        def layer_sort_key(node_id: str) -> tuple[float, int, str]:
            predecessor_slots = [
                positions[predecessor]["slot"]
                for predecessor in reverse_adjacency[node_id]
                if predecessor in positions and order_index[predecessor] < order_index[node_id]
            ]
            barycenter = sum(predecessor_slots) / len(predecessor_slots) if predecessor_slots else float("inf")
            return barycenter, kind_order.get(node_by_id[node_id].get("kind"), 9), node_id

        members = sorted(by_layer[layer], key=layer_sort_key)
        for slot, node_id in enumerate(members):
            node = node_by_id[node_id]
            is_equipment = node.get("kind") == "equipment"
            width = 170.0 if is_equipment else 120.0
            height = 86.0 if is_equipment else 52.0
            positions[node_id] = {
                "x": 60.0 + layer * x_spacing,
                "y": 60.0 + slot * y_spacing,
                "width": width,
                "height": height,
                "layer": layer,
                "slot": slot,
            }
            node["geometry"] = dict(positions[node_id])

    max_y = max((position["y"] + position["height"] for position in positions.values()), default=0.0)
    ordered_edges = sorted(edges, key=lambda item: item["edge_id"])
    parallel_groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for edge in ordered_edges:
        parallel_groups[(str(edge["source_node_id"]), str(edge["target_node_id"]))].append(str(edge["edge_id"]))
    parallel_slots = {
        edge_id: (index, len(edge_ids))
        for edge_ids in parallel_groups.values()
        for index, edge_id in enumerate(edge_ids)
    }

    def stream_fan_slots(node_field: str) -> dict[str, tuple[int, int]]:
        streams_by_node: dict[str, list[str]] = defaultdict(list)
        for item in ordered_edges:
            node_id = str(item[node_field])
            stream_id = str(item.get("stream_id") or item["edge_id"])
            if stream_id not in streams_by_node[node_id]:
                streams_by_node[node_id].append(stream_id)
        slots: dict[str, tuple[int, int]] = {}
        for node_id, stream_ids in streams_by_node.items():
            ordered_streams = sorted(stream_ids)
            stream_slot = {stream_id: index for index, stream_id in enumerate(ordered_streams)}
            for item in ordered_edges:
                if str(item[node_field]) == node_id:
                    stream_id = str(item.get("stream_id") or item["edge_id"])
                    slots[str(item["edge_id"])] = (stream_slot[stream_id], len(ordered_streams))
        return slots

    source_fan_slots = stream_fan_slots("source_node_id")
    target_fan_slots = stream_fan_slots("target_node_id")

    def fan_offset(index: int, count: int) -> float:
        pitch = min(12.0, 30.0 / max(1, count - 1))
        return (index - (count - 1) / 2.0) * pitch

    def route_crosses_other_node(
        points: list[list[float]], source_node_id: str, target_node_id: str,
    ) -> bool:
        for node_id, box in positions.items():
            if node_id in {source_node_id, target_node_id}:
                continue
            x1 = box["x"] - 8.0
            y1 = box["y"] - 8.0
            x2 = box["x"] + box["width"] + 8.0
            y2 = box["y"] + box["height"] + 8.0
            for left, right in zip(points, points[1:]):
                if abs(left[1] - right[1]) < 1e-9:
                    low, high = sorted((left[0], right[0]))
                    if y1 <= left[1] <= y2 and max(low, x1) <= min(high, x2):
                        return True
                elif abs(left[0] - right[0]) < 1e-9:
                    low, high = sorted((left[1], right[1]))
                    if x1 <= left[0] <= x2 and max(low, y1) <= min(high, y2):
                        return True
        return False

    outer_lane_index = 0
    forward_bypass_count = 0
    for edge in ordered_edges:
        source = positions[edge["source_node_id"]]
        target = positions[edge["target_node_id"]]
        parallel_index, parallel_count = parallel_slots[str(edge["edge_id"])]
        source_fan_index, source_fan_count = source_fan_slots[str(edge["edge_id"])]
        target_fan_index, target_fan_count = target_fan_slots[str(edge["edge_id"])]
        source_offset = fan_offset(source_fan_index, source_fan_count)
        target_offset = fan_offset(target_fan_index, target_fan_count)
        lane_offset = fan_offset(parallel_index, parallel_count)
        sx = source["x"] + source["width"]
        sy = source["y"] + source["height"] / 2.0 + source_offset
        tx = target["x"]
        ty = target["y"] + target["height"] / 2.0 + target_offset
        edge_id = str(edge["edge_id"])
        is_feedback = edge_id in feedback_edge_ids
        if not is_feedback:
            middle = (sx + tx) / 2.0
            direct_points = [[sx, sy], [middle, sy], [middle, ty], [tx, ty]]
            if route_crosses_other_node(direct_points, str(edge["source_node_id"]), str(edge["target_node_id"])):
                outer_y = max_y + 70.0 + outer_lane_index * 44.0
                outer_lane_index += 1
                forward_bypass_count += 1
                route_kind = "forward_bypass_orthogonal"
                points = [[sx, sy], [sx + 30.0, sy], [sx + 30.0, outer_y], [tx - 30.0, outer_y], [tx - 30.0, ty], [tx, ty]]
            else:
                route_kind = "forward_orthogonal"
                points = direct_points
        else:
            recycle_y = max_y + 70.0 + outer_lane_index * 44.0
            outer_lane_index += 1
            route_kind = "recycle_orthogonal" if edge["source_node_id"] != edge["target_node_id"] else "self_loop_orthogonal"
            points = [[sx, sy], [sx + 30.0, sy], [sx + 30.0, recycle_y], [tx - 30.0, recycle_y], [tx - 30.0, ty], [tx, ty]]
        edge["route"] = {
            "kind": route_kind,
            "points": points,
            "parallel_lane_index": parallel_index,
            "parallel_lane_count": parallel_count,
            "parallel_lane_offset": lane_offset,
            "source_fan_index": source_fan_index,
            "source_fan_count": source_fan_count,
            "source_port_offset": source_offset,
            "target_fan_index": target_fan_index,
            "target_fan_count": target_fan_count,
            "target_port_offset": target_offset,
        }
    max_x = max((position["x"] + position["width"] for position in positions.values()), default=0.0)
    routed_max_y = max(
        [max_y] + [point[1] for edge in edges for point in edge.get("route", {}).get("points", [])]
    )
    return {
        "algorithm": "deterministic-feedback-dag-obstacle-orthogonal-v3",
        "coordinate_system": "canvas_px",
        "parallel_lane_max_pitch": 12.0,
        "recycle_lane_pitch": 44.0,
        "feedback_edge_count": len(feedback_edge_ids),
        "forward_edge_count": len(edges) - len(feedback_edge_ids),
        "forward_bypass_count": forward_bypass_count,
        "canvas": {"width": max_x + 80.0, "height": routed_max_y + 80.0},
        "node_count": len(nodes),
        "edge_count": len(edges),
        "scc_count": len(components),
    }


def _selection_catalog_view(catalog: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "selection_id": item.get("selection_id"),
            "block_type": item.get("block_type"),
            "family_id": item.get("family_id"),
            "family_name": item.get("family_name"),
            "display_name": item.get("display_name"),
        }
        for item in sorted(catalog["selections"], key=lambda row: (str(row.get("family_name", "")), str(row.get("selection_id", ""))))
    ]


def build_pfd_mapping(
    bundle: Mapping[str, Any],
    overrides: Mapping[str, str] | None = None,
    *,
    catalog: Mapping[str, Any] | None = None,
    canonical_parameters_by_block: Mapping[str, Mapping[str, Any]] | None = None,
    canonical_parameters_by_stream: Mapping[str, Mapping[str, Any]] | None = None,
    parameter_overrides: Mapping[str, Mapping[str, Any]] | None = None,
    parameter_normalization_issues: Iterable[Mapping[str, Any]] = (),
    changed_block_ids: Iterable[str] = (),
    change_kind: str = "type",
) -> dict[str, Any]:
    """Build one deterministic block mapping and PFD projection.

    ``changed_block_ids`` is normally supplied by :func:`update_type_override`.
    It controls stale propagation only; it never changes type inference.
    """

    loaded_catalog = _load_catalog(catalog)
    by_id, by_block_type, by_family = _catalog_indexes(loaded_catalog)
    topology = _build_topology(bundle)
    normalized_overrides = _validate_overrides(topology, overrides, by_id)
    canonical_blocks = _normalize_canonical_parameters(topology, canonical_parameters_by_block)
    canonical_streams = _normalize_canonical_stream_parameters(topology, canonical_parameters_by_stream)
    normalized_parameter_overrides = normalize_parameter_overrides(bundle, parameter_overrides)
    normalization_issues = [dict(item) for item in parameter_normalization_issues if isinstance(item, Mapping)]
    impact = _impact_ledger(topology, changed_block_ids, change_kind=change_kind)

    block_results: list[dict[str, Any]] = []
    equipment_nodes: list[dict[str, Any]] = []
    for block_id in sorted(topology.blocks):
        automatic = _automatic_mapping(bundle, topology, block_id, loaded_catalog, by_id, by_block_type, by_family)
        override_selection = by_id.get(normalized_overrides.get(block_id, ""))
        effective = _effective_mapping(automatic, override_selection)
        block_record = topology.blocks[block_id]
        recalc_status = _recalc_state(block_id, impact)
        display_record = {
            field: block_record[field]
            for field, _label, _unit in BLOCK_PARAMETER_META
            if field in block_record and block_record[field] not in (None, "")
        }
        canonical_block = dict(canonical_blocks.get(block_id, {}))
        if "inner_diameter_mm" in canonical_block:
            display_record.pop("diameter_mm", None)
        display_record.update(canonical_block)
        for field, value in normalized_parameter_overrides.get(block_id, {}).items():
            target_unit = next((unit for meta_field, _label, unit in BLOCK_PARAMETER_META if meta_field == field), None)
            if target_unit is None:
                continue
            display_record[field] = {
                "value": value,
                "canonical_unit": target_unit,
                "source_status": "USER_SUPPLIED_PER_BLOCK_NOT_EVIDENCE",
                "normalization_status": "USER_CANONICAL_INPUT",
                "evidence_class": "A",
                "formal_design_evidence": False,
            }
        row = {
            "block_id": block_id,
            "equipment_tag": str(_equipment_map_row(bundle, block_id).get("equipment_tag") or block_id),
            "source": {
                "block_type": block_record.get("block_type"),
                "block_type_source": block_record.get("block_type_source", "block.block_type"),
                "icon_token": block_record.get("icon_token"),
                "inlet_streams": list(topology.inlet_by_block[block_id]),
                "outlet_streams": list(topology.outlet_by_block[block_id]),
                "connectivity_source": topology.connectivity_source_by_block[block_id],
                "field_signature": sorted(_field_values(block_record, BLOCK_FIELD_ALIASES)),
            },
            "automatic_mapping": automatic,
            "effective_mapping": effective,
            "recalculation_status": recalc_status,
            "parameters": _display_parameters(
                display_record,
                BLOCK_PARAMETER_META,
                BLOCK_FIELD_ALIASES,
                canonical_only=True,
                source_status="CANONICAL_FIELD_VALUE",
                source_status_by_field={field: "ASPEN_DERIVED_PROCESS_SIDE" for field in canonical_block},
            ),
        }
        block_results.append(row)
        equipment_nodes.append({
            "node_id": f"block:{block_id}",
            "kind": "equipment",
            "block_id": block_id,
            "label": block_id,
            "subtitle": effective.get("display_name"),
            "selection_id": effective.get("selection_id"),
            "family_id": effective.get("family_id"),
            "mapping_mode": effective.get("mode"),
            "mapping_status": effective.get("status"),
            "source_block_type": block_record.get("block_type"),
            "model_selection_status": "NOT_EXECUTED_BY_PFD_MAPPER",
            "confidence_level": effective.get("confidence_level"),
            "candidate_options": automatic.get("candidate_options", []),
            "parameters": row["parameters"],
            "display": {
                "default_level": "standard",
                "compact": {
                    "equipment_id": block_id,
                    "mapped_type": effective.get("display_name"),
                },
                "standard": {
                    "equipment_id": block_id,
                    "source_module_type": block_record.get("block_type") or "UNKNOWN",
                    "mapped_type": effective.get("display_name"),
                    "selection_status": "TYPE_MAPPING_ONLY_NOT_MODEL_SELECTED",
                },
                "detailed": {
                    "parameter_sidebar_on_left_click": True,
                    "parameter_count": len(row["parameters"]),
                    "inline_parameter_fields": [],
                },
                "parameters_inline_on_canvas": False,
            },
            "recalculation_status": recalc_status,
            "interaction": {
                "left_click": "open_block_parameter_detail",
                "right_click": "open_validated_type_override_menu",
                "restore_automatic_action": "restore_automatic_mapping",
            },
        })

    boundary_nodes, edges = _stream_edges(topology, impact, canonical_streams)
    nodes = equipment_nodes + boundary_nodes
    layout = _layout(nodes, edges)
    topology_issues = [
        {"edge_id": edge["edge_id"], "stream_id": edge["stream_id"], "status": edge["topology_status"]}
        for edge in edges
        if edge["topology_status"] not in {"PASS", "EXTERNAL_FEED", "EXTERNAL_OUTLET"}
    ]
    missing_stream_rows = sorted(
        stream_id for stream_id, stream in topology.streams.items() if stream.get("data_status") == "REFERENCED_STREAM_DATA_MISSING"
    )
    result: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "policy_version": POLICY_VERSION,
        "source": {
            "schema": bundle.get("schema"),
            "case_id": (bundle.get("case") or {}).get("case_id") if isinstance(bundle.get("case"), Mapping) else None,
            "canonical_content_sha256": _canonical_sha256(bundle),
            "process_basis_status": "ASPEN_EXPORT_NOT_MECHANICAL_DESIGN_EVIDENCE",
            "parameter_binding": {
                "status": "CANONICAL_DERIVATION_BOUND" if (canonical_blocks or canonical_streams) else "TOPOLOGY_ONLY_CANONICAL_FIELDS_ONLY",
                "raw_aspen_alias_relabeling_allowed": False,
                "canonical_block_count": len(canonical_blocks),
                "canonical_stream_count": len(canonical_streams),
                "normalization_issue_count": len(normalization_issues),
                "normalization_issues": normalization_issues,
            },
        },
        "mapping_policy": {
            "priority": ["readable Aspen block_type", "frozen module alias", "equipment_map", "field/phase/port/connectivity features"],
            "ambiguous_result": "retain common most-general family and candidates; selection_id remains null",
            "llm_used": False,
            "network_used": False,
            "override_scope": "type route only; recalculation and evidence gates remain mandatory",
        },
        "catalog": {
            "schema": loaded_catalog.get("schema"),
            "rule_version": loaded_catalog.get("rule_version"),
            "model_rule_version": loaded_catalog.get("model_rule_version"),
            "parameter_template_version": loaded_catalog.get("parameter_template_version"),
            "selection_count": len(by_id),
            "selection_options": _selection_catalog_view(loaded_catalog),
        },
        "overrides": normalized_overrides,
        "blocks": block_results,
        "pfd": {
            "schema": "equipment-design-pfd-view-v1",
            "display_contract": {
                "default_level": "standard",
                "levels": {
                    "compact": {
                        "node_fields": ["equipment_id", "mapped_type"],
                        "stream_fields": ["stream_id"],
                    },
                    "standard": {
                        "node_fields": ["equipment_id", "source_module_type", "mapped_type", "selection_status"],
                        "stream_fields": ["stream_id"],
                    },
                    "detailed": {
                        "interaction": "left_click_opens_parameter_sidebar",
                        "canvas_parameter_dump": False,
                    },
                },
                "design_intent": "concise and clear without reducing the machine-readable parameter detail",
            },
            "nodes": sorted(nodes, key=lambda item: item["node_id"]),
            "edges": sorted(edges, key=lambda item: item["edge_id"]),
            "layout": layout,
            "topology_gate": {
                "status": "PASS" if not topology_issues and not missing_stream_rows else "REVIEW",
                "issues": topology_issues,
                "referenced_stream_data_missing": missing_stream_rows,
            },
        },
        "change_impact": impact,
        "evidence_gate": {
            "status": "PFD_MAPPING_ONLY",
            "formal_design_evidence": False,
            "model_promotion_allowed": False,
            "reason": "PFD 显示和类型映射不替代 Aspen clean-run、机械设计、软件/厂家证据或独立审核。",
        },
    }
    result["mapping_sha256"] = _canonical_sha256(result)
    return result


def summarize_pfd_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
    """Return a compact machine summary without reinterpreting the mapping.

    Both the Aspen worker and Agent protocol use this projection so their
    node/edge/topology counts cannot drift.  It is deliberately descriptive:
    no mapping, override, evidence, or model state is promoted here.
    """

    if mapping.get("schema") != SCHEMA_ID:
        raise AspenPFDMappingError(
            "INVALID_PFD_MAPPING_SCHEMA",
            f"PFD 摘要只接受 {SCHEMA_ID}。",
            {"received": mapping.get("schema")},
        )
    pfd = mapping.get("pfd")
    blocks = mapping.get("blocks")
    if not isinstance(pfd, Mapping) or not isinstance(blocks, list):
        raise AspenPFDMappingError("INVALID_PFD_MAPPING", "PFD mapping 缺少 pfd/blocks。")
    nodes = pfd.get("nodes")
    edges = pfd.get("edges")
    topology_gate = pfd.get("topology_gate")
    if not isinstance(nodes, list) or not isinstance(edges, list) or not isinstance(topology_gate, Mapping):
        raise AspenPFDMappingError("INVALID_PFD_MAPPING", "PFD mapping 的 nodes/edges/topology_gate 无效。")
    mapping_status_counts: dict[str, int] = defaultdict(int)
    recalculation_status_counts: dict[str, int] = defaultdict(int)
    ambiguous_count = 0
    for row in blocks:
        if not isinstance(row, Mapping):
            continue
        effective = row.get("effective_mapping")
        automatic = row.get("automatic_mapping")
        if isinstance(effective, Mapping):
            mapping_status_counts[str(effective.get("status", "UNKNOWN"))] += 1
        if isinstance(automatic, Mapping) and automatic.get("ambiguity_retained") is True:
            ambiguous_count += 1
        recalculation_status_counts[str(row.get("recalculation_status", "UNKNOWN"))] += 1
    issues = topology_gate.get("issues")
    missing = topology_gate.get("referenced_stream_data_missing")
    return {
        "mapping_sha256": mapping.get("mapping_sha256"),
        "block_count": len(blocks),
        "node_count": len(nodes),
        "equipment_node_count": sum(1 for item in nodes if isinstance(item, Mapping) and item.get("kind") == "equipment"),
        "boundary_node_count": sum(1 for item in nodes if isinstance(item, Mapping) and str(item.get("kind", "")).startswith("boundary_")),
        "edge_count": len(edges),
        "default_display_level": (pfd.get("display_contract") or {}).get("default_level") if isinstance(pfd.get("display_contract"), Mapping) else None,
        "topology_gate": {
            "status": topology_gate.get("status"),
            "issue_count": len(issues) if isinstance(issues, list) else 0,
            "referenced_stream_data_missing_count": len(missing) if isinstance(missing, list) else 0,
        },
        "mapping_status_counts": dict(sorted(mapping_status_counts.items())),
        "ambiguous_block_count": ambiguous_count,
        "override_count": len(mapping.get("overrides", {})) if isinstance(mapping.get("overrides"), Mapping) else 0,
        "recalculation_status_counts": dict(sorted(recalculation_status_counts.items())),
        "evidence_status": (mapping.get("evidence_gate") or {}).get("status") if isinstance(mapping.get("evidence_gate"), Mapping) else None,
        "model_promotion_allowed": False,
    }


def update_type_override(
    bundle: Mapping[str, Any],
    overrides: Mapping[str, str] | None,
    block_id: str,
    selection_id: str | None,
    *,
    catalog: Mapping[str, Any] | None = None,
    canonical_parameters_by_block: Mapping[str, Mapping[str, Any]] | None = None,
    canonical_parameters_by_stream: Mapping[str, Mapping[str, Any]] | None = None,
    parameter_overrides: Mapping[str, Mapping[str, Any]] | None = None,
    parameter_normalization_issues: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Apply one validated type choice, or restore automatic with ``None``."""

    topology = _build_topology(bundle)
    normalized_block_id = str(block_id).strip()
    if normalized_block_id not in topology.blocks:
        raise AspenPFDMappingError("UNKNOWN_OVERRIDE_BLOCK", f"人工改型指向未知模块：{normalized_block_id}", {"block_id": normalized_block_id})
    next_overrides = dict(overrides or {})
    action: str
    if selection_id is None or str(selection_id).strip().upper() in {"", "AUTO", "AUTOMATIC", "RESTORE_AUTO"}:
        next_overrides.pop(normalized_block_id, None)
        action = "RESTORE_AUTOMATIC_MAPPING"
    else:
        next_overrides[normalized_block_id] = str(selection_id).strip()
        action = "APPLY_USER_TYPE_OVERRIDE"
    mapping = build_pfd_mapping(
        bundle,
        next_overrides,
        catalog=catalog,
        canonical_parameters_by_block=canonical_parameters_by_block,
        canonical_parameters_by_stream=canonical_parameters_by_stream,
        parameter_overrides=parameter_overrides,
        parameter_normalization_issues=parameter_normalization_issues,
        changed_block_ids=[normalized_block_id],
    )
    return {
        "schema": "equipment-design-pfd-override-result-v1",
        "action": action,
        "block_id": normalized_block_id,
        "selection_id": next_overrides.get(normalized_block_id),
        "overrides": mapping["overrides"],
        "change_impact": mapping["change_impact"],
        "mapping": mapping,
    }


def _normalize_parameter_values(block_id: str, values: Mapping[str, Any] | None) -> dict[str, Any]:
    if values is None:
        return {}
    if not isinstance(values, Mapping):
        raise AspenPFDMappingError(
            "INVALID_PARAMETER_OVERRIDE_VALUES",
            "设备参数补录必须是 field -> scalar 对象。",
            {"block_id": block_id},
        )
    normalized: dict[str, Any] = {}
    for raw_field, raw_value in values.items():
        field = str(raw_field).strip()
        if not field:
            raise AspenPFDMappingError(
                "INVALID_PARAMETER_OVERRIDE_FIELD",
                "设备参数补录包含空字段名。",
                {"block_id": block_id},
            )
        if field in PARAMETER_OVERRIDE_FORBIDDEN_FIELDS:
            raise AspenPFDMappingError(
                "PARAMETER_OVERRIDE_ROUTE_FIELD_FORBIDDEN",
                f"参数补录不得改变类型/型号路由字段：{field}",
                {"block_id": block_id, "field": field},
            )
        if raw_value is None or isinstance(raw_value, str) and not raw_value.strip():
            continue
        if isinstance(raw_value, (Mapping, list, tuple, set)):
            raise AspenPFDMappingError(
                "INVALID_PARAMETER_OVERRIDE_VALUE",
                "每个设备参数补录字段只能保存一个标量值。",
                {"block_id": block_id, "field": field},
            )
        if isinstance(raw_value, float) and not math.isfinite(raw_value):
            raise AspenPFDMappingError(
                "INVALID_PARAMETER_OVERRIDE_VALUE",
                "设备参数补录不接受 NaN 或无穷值。",
                {"block_id": block_id, "field": field},
            )
        normalized[field] = raw_value.strip() if isinstance(raw_value, str) else raw_value
    return dict(sorted(normalized.items()))


def normalize_parameter_overrides(
    bundle: Mapping[str, Any],
    parameter_overrides: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    """Validate a complete per-block parameter-override state map.

    Values remain user inputs and do not acquire Aspen, software, vendor or
    formal-design evidence status merely by appearing in this state layer.
    """

    topology = _build_topology(bundle)
    if parameter_overrides is None:
        return {}
    if not isinstance(parameter_overrides, Mapping):
        raise AspenPFDMappingError(
            "INVALID_PARAMETER_OVERRIDE_MAP",
            "parameter_overrides 必须是 block_id -> field -> scalar 对象。",
        )
    normalized: dict[str, dict[str, Any]] = {}
    for raw_block_id, values in parameter_overrides.items():
        block_id = str(raw_block_id).strip()
        if block_id not in topology.blocks:
            raise AspenPFDMappingError(
                "UNKNOWN_PARAMETER_OVERRIDE_BLOCK",
                f"设备参数补录指向未知模块：{block_id}",
                {"block_id": block_id},
            )
        row = _normalize_parameter_values(block_id, values)
        if row:
            normalized[block_id] = row
    return dict(sorted(normalized.items()))


def merge_canonical_input_with_parameter_overrides(
    block_id: str,
    base_input: Mapping[str, Any],
    parameter_values: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Merge one validated user layer without deleting trusted Aspen identity.

    Only matcher route selectors are removed from the trusted base because the
    caller supplies the current catalog selection separately.  Identity such
    as ``equipment_tag`` remains intact.  Forbidden identity/route/model fields
    are rejected only when they originate in the user override layer.
    """

    if not isinstance(base_input, Mapping):
        raise AspenPFDMappingError(
            "INVALID_CANONICAL_MATCH_INPUT",
            "设备规范输入必须是 field -> value 对象。",
            {"block_id": str(block_id)},
        )
    normalized_values = _normalize_parameter_values(str(block_id), parameter_values)
    merged = dict(base_input)
    for field in MATCHER_ROUTE_FIELDS:
        merged.pop(field, None)
    merged.update(normalized_values)
    return merged


def update_parameter_override(
    bundle: Mapping[str, Any],
    type_overrides: Mapping[str, str] | None,
    parameter_overrides: Mapping[str, Mapping[str, Any]] | None,
    block_id: str,
    values: Mapping[str, Any] | None = None,
    *,
    clear: bool = False,
    catalog: Mapping[str, Any] | None = None,
    canonical_parameters_by_block: Mapping[str, Mapping[str, Any]] | None = None,
    canonical_parameters_by_stream: Mapping[str, Mapping[str, Any]] | None = None,
    parameter_normalization_issues: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Update one block's separate manual-parameter layer.

    This function only validates state and prepares a locally invalidated PFD
    mapping.  The caller must merge the returned values into the block's
    canonical Aspen-derived matcher input and execute the deterministic matcher.
    """

    topology = _build_topology(bundle)
    normalized_block_id = str(block_id).strip()
    if normalized_block_id not in topology.blocks:
        raise AspenPFDMappingError(
            "UNKNOWN_PARAMETER_OVERRIDE_BLOCK",
            f"设备参数补录指向未知模块：{normalized_block_id}",
            {"block_id": normalized_block_id},
        )
    next_overrides = normalize_parameter_overrides(bundle, parameter_overrides)
    if clear:
        next_overrides.pop(normalized_block_id, None)
        action = "CLEAR_BLOCK_PARAMETER_OVERRIDES"
    else:
        normalized_values = _normalize_parameter_values(normalized_block_id, values)
        if normalized_values:
            next_overrides[normalized_block_id] = normalized_values
        else:
            next_overrides.pop(normalized_block_id, None)
        action = "APPLY_BLOCK_PARAMETER_OVERRIDES"
    mapping = build_pfd_mapping(
        bundle,
        type_overrides,
        catalog=catalog,
        canonical_parameters_by_block=canonical_parameters_by_block,
        canonical_parameters_by_stream=canonical_parameters_by_stream,
        parameter_overrides=next_overrides,
        parameter_normalization_issues=parameter_normalization_issues,
        changed_block_ids=[normalized_block_id],
        change_kind="parameter",
    )
    return {
        "schema": "equipment-design-pfd-parameter-override-result-v1",
        "action": action,
        "block_id": normalized_block_id,
        "parameter_overrides": next_overrides,
        "effective_values": next_overrides.get(normalized_block_id, {}),
        "change_impact": mapping["change_impact"],
        "mapping": mapping,
        "source_bundle_mutated": False,
        "parameter_override_evidence_gate": {
            "status": "USER_INPUT_NOT_EVIDENCE_BY_ITSELF",
            "formal_design_evidence": False,
            "model_promotion_allowed_by_override_alone": False,
        },
    }


def mark_block_recalculated(mapping: Mapping[str, Any], block_id: str) -> dict[str, Any]:
    """Return a copied mapping with one changed block marked current again.

    Direct neighbours and incident streams intentionally remain pending: their
    own parameter packages were not replayed by recalculating only this block.
    """

    if mapping.get("schema") != SCHEMA_ID:
        raise AspenPFDMappingError(
            "INVALID_PFD_MAPPING_SCHEMA",
            f"参数重算状态只接受 {SCHEMA_ID}。",
            {"received": mapping.get("schema")},
        )
    normalized_block_id = str(block_id).strip()
    copied = json.loads(json.dumps(mapping, ensure_ascii=False, allow_nan=False))
    block_found = False
    for row in copied.get("blocks", []):
        if isinstance(row, dict) and str(row.get("block_id")) == normalized_block_id:
            row["recalculation_status"] = "RECALCULATED_CURRENT"
            block_found = True
    pfd = copied.get("pfd") if isinstance(copied.get("pfd"), dict) else {}
    for node in pfd.get("nodes", []) if isinstance(pfd.get("nodes"), list) else []:
        if isinstance(node, dict) and str(node.get("block_id")) == normalized_block_id:
            node["recalculation_status"] = "RECALCULATED_CURRENT"
    if not block_found:
        raise AspenPFDMappingError(
            "UNKNOWN_PARAMETER_OVERRIDE_BLOCK",
            f"参数重算指向未知 PFD 模块：{normalized_block_id}",
            {"block_id": normalized_block_id},
        )
    impact = copied.get("change_impact") if isinstance(copied.get("change_impact"), dict) else {}
    impact["recalculated_blocks"] = [normalized_block_id]
    impact["status"] = "CHANGED_BLOCK_RECALCULATED_RELATED_ENTITIES_PENDING"
    copied["change_impact"] = impact
    copied.pop("mapping_sha256", None)
    copied["mapping_sha256"] = _canonical_sha256(copied)
    return copied


def restore_automatic_mapping(
    bundle: Mapping[str, Any],
    overrides: Mapping[str, str] | None,
    block_id: str,
    *,
    catalog: Mapping[str, Any] | None = None,
    canonical_parameters_by_block: Mapping[str, Mapping[str, Any]] | None = None,
    canonical_parameters_by_stream: Mapping[str, Mapping[str, Any]] | None = None,
    parameter_overrides: Mapping[str, Mapping[str, Any]] | None = None,
    parameter_normalization_issues: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Named convenience entry for a GUI's “恢复自动识别” action."""

    return update_type_override(
        bundle,
        overrides,
        block_id,
        None,
        catalog=catalog,
        canonical_parameters_by_block=canonical_parameters_by_block,
        canonical_parameters_by_stream=canonical_parameters_by_stream,
        parameter_overrides=parameter_overrides,
        parameter_normalization_issues=parameter_normalization_issues,
    )


__all__ = [
    "AspenPFDMappingError",
    "POLICY_VERSION",
    "SCHEMA_ID",
    "build_pfd_mapping",
    "canonical_parameters_by_block",
    "canonical_parameters_by_stream",
    "mark_block_recalculated",
    "merge_canonical_input_with_parameter_overrides",
    "normalize_parameter_overrides",
    "restore_automatic_mapping",
    "summarize_pfd_mapping",
    "update_parameter_override",
    "update_type_override",
]
