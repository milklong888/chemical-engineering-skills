#!/usr/bin/env python3
"""Internal deterministic, no-LLM selector for HG/T 20592~20635.

The selector reads only package CSV/JSON.  It deliberately never opens the
source PDF, OCR layer or page images.  Service labels are derived from raw
Aspen/manual mechanical fields are accepted by the public ``select``/CLI path,
but caller-supplied property facts and phase labels are never promoted there.
The hash-locked parent wrapper uses ``_select_verified`` only after binding
facts to graph rows and freezing the normalized stream phase.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
UNKNOWN = "unknown"


def read_csv(name):
    with (ROOT / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return UNKNOWN
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return UNKNOWN


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def convert_pressure(value, unit):
    value = number(value)
    if value is None:
        return None
    factors = {"pa":1e-6,"kpa":1e-3,"mpa":1.0,"bar":0.1,"bara":0.1,"barg":0.1,"psi":0.006894757293}
    factor = factors.get(str(unit or "").strip().lower())
    return value * factor if factor is not None else None


def convert_temperature(value, unit):
    value = number(value)
    if value is None:
        return None
    unit = str(unit or "c").strip().lower()
    if unit in {"c", "°c", "degc", "celsius"}: return value
    if unit in {"k", "kelvin"}: return value - 273.15
    if unit in {"f", "°f", "degf", "fahrenheit"}: return (value - 32.0) * 5.0 / 9.0
    return None


DERIVED_FIELDS = {
    "phase","corrosivity","toxicity","flammability","explosivity","cleanliness",
    "leak_tightness","vacuum_level","severe_cyclic","thermal_shock","oxidizing",
    "crevice_corrosion_risk","severe_corrosion","utility_service","instrument_service",
    "low_sealing_demand","lining_material","flange_material_group","mating_material_group",
    "current_facing","ring_joint_required","core_corrosion_risk","fire_safe_required",
    "cleanability_required","jacketed_pipe","orifice_service","closure_required",
    "internal_component_connection",
}


FACT_ENUMS = {
    "corrosivity":{"none","low","moderate","high","severe"},
    "toxicity":{"normal","moderate","high","extreme"},
    "flammability":{"nonflammable","flammable","highly_flammable"},
    "explosivity":{"none","possible","explosive"},
    "cleanliness":{"ordinary","clean","high_purity","sterile"},
    "leak_tightness":{"ordinary","enhanced","high","zero_emission"},
    "vacuum_level":{"none","vacuum","high_vacuum"},
    "lining_material":{"none","stainless","nickel","titanium","other"},
    "flange_material_group":{"steel","stainless","nickel","titanium","cast_iron","other"},
    "mating_material_group":{"steel","stainless","nickel","titanium","cast_iron","other"},
    "current_facing":{"RF","FF","FM/M","T/G","RJ"},
}


BOOL_FACTS = {
    "severe_cyclic","thermal_shock","oxidizing","crevice_corrosion_risk","severe_corrosion",
    "utility_service","instrument_service","low_sealing_demand","ring_joint_required",
    "core_corrosion_risk","fire_safe_required","cleanability_required","jacketed_pipe",
    "orifice_service","closure_required","internal_component_connection",
}


def derive_context(raw, *, verified_property_evidence=(), normalized_stream_phase=None):
    """Derive service labels only from raw fields and cited property facts."""
    warnings = []
    ctx = {
        "object_family": raw.get("object_family"),
        "system_series": str(raw.get("system_series") or "").upper() or UNKNOWN,
        "pn": number(raw.get("pn")),
        "class_rating": number(raw.get("class_rating")),
        "dn_mm": number(raw.get("dn_mm") or raw.get("nominal_diameter_mm")),
        "temperature_c": convert_temperature(raw.get("temperature_value"), raw.get("temperature_unit", "C")),
        "pressure_mpa": convert_pressure(raw.get("pressure_value"), raw.get("pressure_unit")),
        "pressure_tap_connection": raw.get("pressure_tap_connection", UNKNOWN),
        "gasket_family_preference": raw.get("gasket_family_preference", "none"),
        "flush_bore_required": parse_bool(raw.get("flush_bore_required")),
        "user_forced_candidate_id": raw.get("user_forced_candidate_id"),
    }
    for field in DERIVED_FIELDS:
        ctx[field] = UNKNOWN

    # Aspen-native phase derivation is deterministic and does not require a
    # chemistry-property lookup.
    vf = number(raw.get("vapor_fraction"))
    sf = number(raw.get("solid_fraction"))
    if sf is not None and not 0 <= sf <= 1:
        warnings.append({"warning_id":"W_PHASE_FRACTION_INVALID","message_zh":"固相分率超出0~1，已隔离；不据此贴相态标签。","fields":["solid_fraction"]})
        sf = None
    if vf is not None and not 0 <= vf <= 1:
        warnings.append({"warning_id":"W_PHASE_FRACTION_INVALID","message_zh":"汽相分率超出0~1，已隔离；不据此贴相态标签。","fields":["vapor_fraction"]})
        vf = None
    if normalized_stream_phase in {"liquid", "vapor", "two_phase", "solid_bearing"}:
        ctx["phase"] = normalized_stream_phase
    elif sf is not None and sf > 1e-9:
        ctx["phase"] = "solid_bearing"
    elif vf is not None:
        if vf <= 1e-9: ctx["phase"] = "liquid"
        elif vf >= 1 - 1e-9: ctx["phase"] = "vapor"
        else: ctx["phase"] = "two_phase"

    # Raw JSON facts are untrusted at this layer. Only the parent wrapper's
    # separately supplied, graph-bound records can create service labels.
    accepted_facts = []
    rejected_facts = []
    for fact in raw.get("property_evidence", []) or []:
        rejected_facts.append({
            "fact": fact.get("fact") if isinstance(fact, dict) else None,
            "reason": "untrusted_direct_property_evidence_input",
        })
    for fact in verified_property_evidence or []:
        name, value, source_id = fact.get("fact"), fact.get("value"), fact.get("source_id")
        if not source_id or name not in DERIVED_FIELDS:
            rejected_facts.append({"fact":name,"reason":"missing_source_id_or_unknown_fact"})
            continue
        t = ctx["temperature_c"]
        tmin, tmax = number(fact.get("valid_temperature_min_c")), number(fact.get("valid_temperature_max_c"))
        if t is not None and ((tmin is not None and t < tmin) or (tmax is not None and t > tmax)):
            rejected_facts.append({"fact":name,"reason":"outside_evidence_temperature_range","source_id":source_id})
            continue
        if name in BOOL_FACTS:
            value = parse_bool(value)
            if value == UNKNOWN:
                rejected_facts.append({"fact":name,"reason":"invalid_boolean","source_id":source_id})
                continue
        elif name in FACT_ENUMS:
            if value not in FACT_ENUMS[name]:
                rejected_facts.append({"fact":name,"reason":"invalid_enum","source_id":source_id})
                continue
        ctx[name] = value
        accepted_facts.append({"fact":name,"value":value,"source_id":source_id})

    ignored = sorted(k for k in raw if k in DERIVED_FIELDS)
    if ignored:
        warnings.append({"warning_id":"W_DERIVED_INPUT_IGNORED","message_zh":"直接传入的派生工况标签已忽略；这些标签必须由Aspen原始字段和带来源的物性/相容性事实生成。","fields":ignored})
    unknown_property_labels = sorted(k for k in ("corrosivity","toxicity","flammability","explosivity","oxidizing","crevice_corrosion_risk","severe_corrosion") if ctx[k] == UNKNOWN)
    if unknown_property_labels:
        warnings.append({"warning_id":"W_PROPERTY_LABEL_UNKNOWN","message_zh":"组分/条件缺少可追溯物性或相容性证据，相关工况标签保持UNKNOWN；程序未按组分名称猜测。","fields":unknown_property_labels})
    return ctx, accepted_facts, rejected_facts, warnings


def evaluate(node, ctx):
    if "all" in node: return all(evaluate(x, ctx) for x in node["all"])
    if "any" in node: return any(evaluate(x, ctx) for x in node["any"])
    if "not" in node: return not evaluate(node["not"], ctx)
    value = ctx.get(node.get("field"), UNKNOWN)
    op, target = node.get("op"), node.get("value")
    if op == "eq": return value == target
    if op == "ne": return value != target
    if op == "in": return value in target
    if op == "not_in": return value not in target
    if op == "known": return value not in (None, "", UNKNOWN)
    if value in (None, "", UNKNOWN): return False
    try:
        if op == "gt": return value > target
        if op == "gte": return value >= target
        if op == "lt": return value < target
        if op == "lte": return value <= target
    except TypeError:
        return False
    raise ValueError(f"unsupported predicate operator: {op}")


def family_series_match(row, family, series):
    return row["object_family"] == family and row["terminal_selectable"].lower() == "true" and row["system_series"] in {series, "BOTH"}


def warning_map():
    return {row["warning_id"]:row["message_zh"] for row in read_csv("warning_templates.csv")}


def add_warning(items, templates, warning_id, **extra):
    if any(x["warning_id"] == warning_id for x in items):
        return
    item = {"warning_id":warning_id,"message_zh":templates.get(warning_id, warning_id)}
    item.update(extra)
    items.append(item)


def missing_fields(ctx, family):
    fields = {
        "flange_type":["system_series","pn_or_class","dn_mm","temperature_c","phase","corrosivity","flammability","severe_cyclic"],
        "facing":["system_series","pn_or_class","flange_material_group","mating_material_group","leak_tightness","ring_joint_required"],
        "gasket_type":["system_series","pn_or_class","dn_mm","temperature_c","phase","corrosivity","toxicity","flammability","vacuum_level","oxidizing","current_facing","leak_tightness"],
        "fastener_type":["system_series","pn_or_class","temperature_c","severe_cyclic","thermal_shock","flange_material_group"],
    }[family]
    missing = []
    for field in fields:
        if field == "pn_or_class":
            key = "pn" if ctx["system_series"] == "PN" else "class_rating"
            if ctx.get(key) is None: missing.append(key)
        elif ctx.get(field) in (None, "", UNKNOWN):
            missing.append(field)
    return missing


def scope_mismatches(row, ctx):
    mismatches = []
    pairs = [
        ("pn","pn_min","min"),("pn","pn_max","max"),
        ("class_rating","class_min","min"),("class_rating","class_max","max"),
        ("dn_mm","dn_min_mm","min"),("dn_mm","dn_max_mm","max"),
        ("temperature_c","temperature_min_c","min"),("temperature_c","temperature_max_c","max"),
    ]
    for field, bound_field, direction in pairs:
        value, bound = number(ctx.get(field)), number(row.get(bound_field))
        if value is None or bound is None: continue
        if (direction == "min" and value < bound) or (direction == "max" and value > bound):
            mismatches.append({"field":field,"value":value,"bound":bound,"direction":direction})
    return mismatches


def scope_penalty(row, ctx):
    weights = {"temperature_c":2.0,"pn":2.0,"class_rating":2.0,"dn_mm":1.0}
    return sum(weights.get(item["field"], 1.0) for item in scope_mismatches(row, ctx))


def _select(raw, *, verified_property_evidence=(), normalized_stream_phase=None):
    catalog = read_csv("type_catalog.csv")
    hard = read_csv("hard_exclusions.csv")
    compat = read_csv("compatibility_matrix.csv")
    scores = read_csv("selection_rules.csv")
    templates = warning_map()
    ctx, accepted_facts, rejected_facts, warnings = derive_context(
        raw,
        verified_property_evidence=verified_property_evidence,
        normalized_stream_phase=normalized_stream_phase,
    )
    family, series = ctx.get("object_family"), ctx.get("system_series")
    if family not in {"flange_type","facing","gasket_type","fastener_type"}:
        raise ValueError("object_family must be flange_type, facing, gasket_type, or fastener_type")
    if series not in {"PN","CLASS"}:
        # Facing and gasket still need the series to map table ranges; choose a
        # deterministic PN default only as a routing convention, never as a
        # claimed design rating.
        series = "PN"
        ctx["system_series"] = series
        add_warning(warnings, templates, "W_RATING_MISSING", detail="system_series defaulted to PN routing only")

    candidates = {r["candidate_id"]:r for r in catalog if family_series_match(r, family, series)}
    excluded = {}
    fired = []
    for rule in hard:
        if rule["object_family"] != family or not evaluate(json.loads(rule["predicate_json"]), ctx): continue
        fired.append(rule["rule_id"])
        for cid in rule["candidate_ids"].split("|"):
            if cid in candidates:
                excluded.setdefault(cid, []).append({"rule_id":rule["rule_id"],"reason":rule["reason"],"source_refs":rule["source_refs"]})
    viable = set(candidates) - set(excluded)
    if not viable:
        raise RuntimeError("all registered terminal types were hard-excluded; package invariant violated")

    # Table-range mismatch is not treated as a hard exclusion because the
    # user requires a terminal type even outside the standard scope.  It does,
    # however, receive a dominant penalty so an in-scope candidate wins when
    # one exists.  If every candidate is out of range, the least-conflicted
    # registered type still terminates with W_SCOPE_MISMATCH.
    points = {
        cid: float(candidates[cid]["default_priority"] or 0)
        - 1000.0 * scope_penalty(candidates[cid], ctx)
        for cid in viable
    }
    applied_compat = []
    for rule in sorted((x for x in compat if x["object_family"] == family), key=lambda x:-int(x["priority"])):
        if not evaluate(json.loads(rule["predicate_json"]), ctx): continue
        allowed = viable.intersection(rule["allowed_candidate_ids"].split("|"))
        strength = rule["strength"]
        if strength.startswith("MANDATORY"):
            if allowed:
                viable = allowed
                points = {cid:points[cid] for cid in viable}
                applied_compat.append(rule["rule_id"])
            else:
                add_warning(warnings, templates, "W_COMPAT_CONFLICT", conflicting_rule=rule["rule_id"])
        else:
            bonus = 1000 if strength == "PREFERRED_STRONG" else 120
            for cid in allowed: points[cid] += bonus
            applied_compat.append(rule["rule_id"])

    applied_scores = []
    for rule in scores:
        if rule["object_family"] != family or not evaluate(json.loads(rule["predicate_json"]), ctx): continue
        for cid in rule["candidate_ids"].split("|"):
            if cid in viable:
                points[cid] += float(rule["score"])
                applied_scores.append(rule["rule_id"])

    forced = ctx.get("user_forced_candidate_id")
    if forced:
        if forced in viable:
            points[forced] += 1_000_000
        else:
            add_warning(warnings, templates, "W_FORCED_REJECTED", forced_candidate_id=forced)

    chosen_id = sorted(viable, key=lambda cid:(-points[cid], cid))[0]
    chosen = candidates[chosen_id]
    missing = missing_fields(ctx, family)
    mismatches = scope_mismatches(chosen, ctx)
    meaningful = bool(applied_compat or applied_scores or forced)
    if mismatches:
        add_warning(warnings, templates, "W_SCOPE_MISMATCH", mismatches=mismatches)
    if (ctx.get("pn") is None if series == "PN" else ctx.get("class_rating") is None):
        add_warning(warnings, templates, "W_RATING_MISSING")
    if chosen_id == "G_ASBESTOS_RUBBER": add_warning(warnings, templates, "W_ASBESTOS")
    if chosen_id == "G_FLEX_GRAPHITE_REINFORCED" and ctx.get("flange_material_group") in {"stainless","nickel"}: add_warning(warnings, templates, "W_CHLORIDE")
    if ctx.get("flush_bore_required") is True: add_warning(warnings, templates, "W_FLUSH_BORE")
    if ctx.get("fire_safe_required") is True or ctx.get("cleanability_required") is True: add_warning(warnings, templates, "W_FIRE_CLEAN")
    if ctx.get("leak_tightness") == "zero_emission" or mismatches: add_warning(warnings, templates, "W_VENDOR_SPECIAL")
    if family == "gasket_type": add_warning(warnings, templates, "W_MATERIAL_PT")
    if not meaningful:
        add_warning(warnings, templates, "W_DEFAULTED")
    elif missing:
        add_warning(warnings, templates, "W_INCOMPLETE_CONTEXT")
    add_warning(warnings, templates, "W_ERRATA_APPLIED")

    if not meaningful:
        status = "DEFAULTED_PROVISIONAL"
    elif missing or mismatches:
        status = "CONDITION_SELECTED_PROVISIONAL"
    else:
        status = "CONDITION_SELECTED"

    return {
        "schema":"hgt20592-20635-terminal-selection-v1",
        "deterministic":True,
        "llm_used":False,
        "runtime_vision":False,
        "terminal_count":1,
        "terminal_type":{
            "candidate_id":chosen_id,
            "code":chosen["current_code"],
            "name_zh":chosen["name_zh"],
            "object_family":family,
            "system_series":series,
        },
        "status":status,
        "normalized_service_labels":ctx,
        "service_fact_evidence":accepted_facts,
        "rejected_property_facts":rejected_facts,
        "hard_excluded_candidates":[{"candidate_id":cid,"reasons":reasons} for cid,reasons in sorted(excluded.items())],
        "decision_chain":{
            "hard_exclusion_rules":fired,
            "mandatory_or_preferred_compatibility":applied_compat,
            "applicability_score_rules":sorted(set(applied_scores)),
            "tie_break":"default_priority_desc_then_candidate_id_asc",
            "chosen_score":points[chosen_id],
        },
        "minimum_missing_fields":missing,
        "scope_mismatches":mismatches,
        "assumptions":["未知标签未按名称猜测", "默认优先级仅用于唯一收敛，不是标准原文默认", "材料p-T与专项认证留待后续证据核定"],
        "warnings":warnings,
        "source_refs":sorted(set(chosen["source_refs"].split("|"))),
    }


def select(raw):
    """Public mechanical-only selector; direct facts and phase labels stay untrusted."""

    return _select(raw)


def _select_verified(raw, *, verified_property_evidence, normalized_stream_phase):
    """Internal route used only by the hash-verifying parent wrapper."""

    return _select(
        raw,
        verified_property_evidence=verified_property_evidence,
        normalized_stream_phase=normalized_stream_phase,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON file path, or '-' for stdin")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    raw = json.load(sys.stdin if args.input == "-" else open(args.input, encoding="utf-8"))
    print(json.dumps(select(raw), ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))


if __name__ == "__main__":
    main()
