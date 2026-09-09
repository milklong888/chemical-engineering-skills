"""Portable evidence/configuration adapter, not a replacement hydraulic model.

All case-specific inputs come from an explicit JSON config. Hashes establish
artifact identity, not truth or a clean Aspen run. Output never grants L3.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
from types import SimpleNamespace

PROFILE = {
    "temperature": ("RAD_PRO2", "C"), "pressure": ("RAD_PRO2", "bar_abs"),
    "vapor_mole": ("RAD_PRO2", "kmol/h"), "liquid_mole": ("RAD_PRO2", "kmol/h"),
    "vapor_mass": ("RAD_PR2S", "kg/h"), "liquid_mass": ("RAD_PR2S", "kg/h"),
}
PARAM_UNITS = {"hetp_m": "m", "flooding_f_factor": "Pa^0.5", "capacity_factor_target": "1",
               "capacity_factor_min": "1", "capacity_factor_max": "1", "max_bed_height_m": "m",
               "diameter_round_step_m": "m", "packing_type": "label"}

class BasisError(ValueError):
    pass

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()

def read_verified_text(path, encoding="utf-8-sig"):
    if encoding.lower() not in {"utf-8", "utf-8-sig", "cp936", "gbk", "ascii"}:
        raise BasisError("Unsupported/unknown text encoding; no lossy fallback")
    raw = Path(path).read_bytes()
    text = raw.decode(encoding, errors="strict")
    if "\x00" in text or "\ufffd" in text:
        raise BasisError("Binary/damaged text is not a verified DSET export")
    return text

def evidence(row):
    return isinstance(row, dict) and all(isinstance(row.get(k), str) and row[k].strip() for k in ("source", "locator", "basis"))

def parameter(config, name, gaps):
    item = config.get("parameters", {}).get(name)
    if not isinstance(item, dict) or not evidence(item) or item.get("unit") != PARAM_UNITS[name]:
        gaps.append({"field": name, "reason": "missing_value_unit_or_source", "affected": "packing" if name in {"hetp_m", "max_bed_height_m", "packing_type"} else "capacity_sizing"})
        return None
    value = item.get("value")
    if name == "packing_type":
        if not isinstance(value, str) or not value.strip():
            raise BasisError("packing_type must be an explicit label")
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise BasisError(f"Invalid {name}; finite positive value required")
    return value

def load_config(config_path, mode):
    path = Path(config_path).resolve()
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    if config.get("schema") != "packed-hydraulic-case-config-v1" or config.get("mode") != mode:
        raise BasisError("Wrong config schema/mode")
    if not isinstance(config.get("run_id"), str) or not config["run_id"].strip():
        raise BasisError("Explicit same-run identity required")
    artifacts = {}
    for name in ("bkp", "streams") + (("inp",) if mode == "parallel" else ()):
        record = config.get("artifacts", {}).get(name, {})
        if record.get("run_id") != config["run_id"]:
            raise BasisError(f"{name}: same-run identity mismatch")
        target = Path(record.get("path", ""))
        if not target.is_absolute():
            target = path.parent / target
        target = target.resolve()
        if not target.is_file() or sha(target) != str(record.get("sha256", "")).upper():
            raise BasisError(f"{name}: artifact missing or SHA256 mismatch")
        if not evidence(record):
            raise BasisError(f"{name}: source/locator/basis missing")
        artifacts[name] = {**record, "path": str(target), "encoding": record.get("encoding", "utf-8-sig")}
    density = config.get("vapor_density_model", {})
    if density.get("method") != "ideal_gas" or density.get("accepted_for_preliminary") is not True or not evidence(density):
        raise BasisError("Original ideal-gas density method requires explicit preliminary applicability; no alternate EOS is invented")
    if not evidence(config.get("property_method", {})):
        raise BasisError("Property-method/phase applicability evidence required")
    towers = config.get("towers")
    if not isinstance(towers, list) or len(towers) < (2 if mode == "parallel" else 1) or (mode == "single" and len(towers) != 1):
        raise BasisError("Explicit tower list required; no equal-split default")
    if len({row.get("block") for row in towers}) != len(towers):
        raise BasisError("Duplicate tower identity")
    config["_artifacts"] = artifacts
    config["_config_path"] = str(path)
    config["_config_sha256"] = sha(path)
    return config

def tower_args(config, tower):
    gaps = []
    if not tower.get("block") or not isinstance(tower.get("nstage"), int) or tower["nstage"] < 4:
        raise BasisError("Explicit block and nstage >= 4 required")
    if not isinstance(tower.get("feed_stage"), int) or not 2 < tower["feed_stage"] < tower["nstage"]:
        raise BasisError("Feed stage must leave rectifying and stripping stages")
    if not evidence(tower):
        raise BasisError("Tower geometry/stage identity requires source/locator/basis")
    merged = {**config, "parameters": {**config.get("parameters", {}), **tower.get("parameters", {})}}
    not_used_for_rating = {"hetp_m", "packing_type", "capacity_factor_target", "diameter_round_step_m"} if config["mode"] == "parallel" else set()
    values = {name: (None if name in not_used_for_rating and name not in merged["parameters"] else parameter(merged, name, gaps)) for name in PARAM_UNITS}
    if values["capacity_factor_min"] is not None and values["capacity_factor_max"] is not None:
        if not values["capacity_factor_min"] < values["capacity_factor_max"] <= 1:
            raise BasisError("Invalid source capacity range")
    for name in ("capacity_factor_target",):
        if values[name] is not None and values[name] > 1:
            raise BasisError("Capacity target must not exceed flooding basis")
    return SimpleNamespace(**values, block=tower["block"], nstage=tower["nstage"], feed_stage=tower["feed_stage"],
        config=config, tower_config=tower, gaps=gaps, bkp=config["_artifacts"]["bkp"]["path"],
        streams=config["_artifacts"]["streams"]["path"], bkp_encoding=config["_artifacts"]["bkp"]["encoding"],
        liquid_density_kg_m3=None, liquid_nozzle_velocity_m_s=None, vapor_nozzle_velocity_m_s=None)

def validated_profiles(text, args, extractor):
    result = {}
    mapping = args.tower_config.get("profiles", {})
    used = set()
    for name, (dataset, unit) in PROFILE.items():
        row = mapping.get(name, {})
        label = row.get("label", "")
        if not evidence(row) or row.get("unit") != unit or row.get("dataset") != dataset or not re.fullmatch(r"@L_\d+", label):
            args.gaps.append({"field": "profiles." + name, "reason": "explicit_verified_label_unit_source_required", "affected": "profile_column"})
            result[name] = [None] * args.nstage
            continue
        identity = dataset, label
        if identity in used:
            raise BasisError("A DSET column cannot represent two different physical quantities")
        used.add(identity)
        pattern = re.compile(rf"DSET\s+BLOCK\s+RADFRAC\s+{re.escape(args.block)}\s+{dataset}\s+{label}\s*\(", re.S)
        matches = list(pattern.finditer(text))
        if len(matches) != 1:
            args.gaps.append({"field": "profiles." + name, "reason": "missing_or_duplicate_DSET", "affected": "profile_column"})
            result[name] = [None] * args.nstage
            continue
        start = matches[0].end()
        end = text.find(")", start)
        if end < 0 or "DSET" in text[start:end]:
            raise BasisError("Unterminated DSET")
        body = re.sub(r"<[^>]+>", " ", text[start:end])
        if "*" in body:
            raise BasisError("Missing-value marker must not shift DSET stage positions")
        values = extractor(text, args.block, dataset, label)
        if len(values) != args.nstage or not all(math.isfinite(x) for x in values):
            raise BasisError(f"{name}: complete finite per-stage values required")
        if name == "temperature":
            valid = all(x > -273.15 for x in values)
        elif name.startswith("liquid"):
            valid = all(x >= 0 for x in values)
        else:
            valid = all(x > 0 for x in values)
        if not valid:
            raise BasisError(f"{name}: physical-domain error")
        result[name] = values
    return result

def profiles_tuple(values, args):
    labels = {name: row.get("label") for name, row in args.tower_config.get("profiles", {}).items()}
    return (*(values[k] for k in PROFILE), labels)

def build_nozzles(args, streams, liquid, vapor):
    out = {}
    for row in args.tower_config.get("nozzles", []):
        name = row.get("service", row.get("stream", "unknown"))
        stream = streams.get(row.get("stream"))
        velocity = row.get("velocity", {})
        density = row.get("density", {})
        try:
            if stream is None or not evidence(row) or not evidence(velocity) or velocity.get("unit") != "m/s":
                raise BasisError("nozzle stream/velocity/source missing")
            v = float(velocity["value"])
            if not math.isfinite(v) or v <= 0 or float(stream["total_mass_flow_kg_h"]) < 0:
                raise BasisError("invalid nozzle flow or velocity")
            if row.get("phase") == "liquid":
                if not evidence(density) or density.get("unit") != "kg/m3" or float(density.get("value", 0)) <= 0:
                    raise BasisError("liquid nozzle density source required")
                value = liquid(stream, float(density["value"]), v)
            elif row.get("phase") == "vapor":
                if not (float(stream["temp_C"]) > -273.15 and float(stream["pressure_bar"]) > 0 and float(stream["total_mole_flow_kmol_h"]) > 0):
                    raise BasisError("vapor nozzle state invalid")
                value = vapor(stream, v)
            else:
                raise BasisError("nozzle phase not declared")
            if not all(math.isfinite(x) for x in value.values()):
                raise BasisError("nonfinite nozzle result")
            out[name] = {**value, "stream": row["stream"], "phase": row["phase"], "status": "CALCULATED_PRELIMINARY", "source": row}
        except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
            out[name] = {"status": "BLOCKED_NOZZLE_ONLY", "reason": str(exc)}
            args.gaps.append({"field": "nozzles." + name, "reason": str(exc), "affected": "nozzle_only"})
    return out

def ensure_uniform_internals(rows, args):
    if not rows or not evidence(args.tower_config.get("internals_units", {})) or args.tower_config["internals_units"].get("unit") != "m":
        raise BasisError("Internals geometry units/source required")
    if len({row["diameter_m"] for row in rows}) != 1 or any(row["diameter_m"] <= 0 or row["packing_height_m"] <= 0 for row in rows):
        raise BasisError("Original calculation supports uniform positive diameter only; stepped diameter requires section-specific method")
    stages = []
    for row in rows:
        stages.extend(range(row["stage1"], row["stage2"]+1))
        row["segment_height_gate"] = "UNKNOWN" if args.max_bed_height_m is None else ("PASS" if row["packing_height_m"] <= args.max_bed_height_m else "FAIL")
    if sorted(stages) != list(range(2, args.nstage)):
        raise BasisError("Internals must cover packed stages exactly without overlap/gaps")
    return rows

def partial_profile(args, profiles):
    rows = []
    for idx in range(args.nstage):
        row = {key: values[idx] for key, values in profiles.items()}
        row["stage"] = idx+1
        if all(row[k] is not None for k in ("temperature", "pressure", "vapor_mole", "vapor_mass")):
            mw = row["vapor_mass"] / row["vapor_mole"]
            rho = row["pressure"] * 100000.0 * (mw / 1000.0) / (8.314462618 * (row["temperature"] + 273.15))
            row.update(vapor_mw_kg_kmol=mw, vapor_density_kg_m3=rho, vapor_volumetric_flow_m3_s=row["vapor_mass"]/3600.0/rho)
        rows.append(row)
    return {"block": args.block, "stage_profile": rows, "status": "PARTIAL_RELATED_COMPUTATIONS_ONLY", "gaps": args.gaps}

def execute(module, config):
    text = read_verified_text(config["_artifacts"]["bkp"]["path"], config["_artifacts"]["bkp"]["encoding"])
    # CSV schema names explicitly carry units; no guessing alternate columns.
    streams = module.load_streams(Path(config["_artifacts"]["streams"]["path"]))
    inp = read_verified_text(config["_artifacts"]["inp"]["path"], config["_artifacts"]["inp"]["encoding"]) if config["mode"] == "parallel" else None
    results = []
    for tower in config["towers"]:
        args = tower_args(config, tower)
        profiles = validated_profiles(text, args, module.extract_dset_values)
        args.validated_profile_values = profiles
        core_missing = any(profiles[k][0] is None for k in ("temperature", "pressure", "vapor_mole", "vapor_mass")) or any(getattr(args, k) is None for k in ("flooding_f_factor", "capacity_factor_min", "capacity_factor_max"))
        if config["mode"] == "single":
            core_missing |= args.capacity_factor_target is None or args.diameter_round_step_m is None
        if core_missing:
            result = partial_profile(args, profiles)
            liquid = getattr(module, "stream_nozzle_liquid", getattr(module, "nozzle_liquid", None))
            vapor = getattr(module, "stream_nozzle_vapor", getattr(module, "nozzle_vapor", None))
            result["nozzles"] = build_nozzles(args, streams, liquid, vapor)
        else:
            try:
                if config["mode"] == "parallel":
                    body = module.block_body(inp, args.block)
                    for field, token in re.findall(r"\b(DIAM|PACK-HT)=([^\s]+)", body, re.I):
                        if not re.fullmatch(r"(?:\d+(?:\.\d*)?|\.\d+)", token):
                            raise BasisError(f"Original INP parser does not support {field} token format; explicit decimal export required")
                result = module.build_design(args) if config["mode"] == "single" else module.build_block_design(text, inp, streams, args.block, args)
            except (BasisError, RuntimeError) as exc:
                if config["mode"] != "parallel":
                    raise
                args.gaps.append({"field": "internals", "reason": str(exc), "affected": "geometry_dependent_capacity_only"})
                result = partial_profile(args, profiles)
                result["nozzles"] = build_nozzles(args, streams, module.nozzle_liquid, module.nozzle_vapor)
        result["gaps"] = args.gaps
        result["evidence_level"] = "L2_PRELIMINARY_PARTIAL" if args.gaps else "L2_PRELIMINARY_CALCULATION"
        result["software_rating_verified"] = False
        result["engineering_accepted"] = False
        results.append(result)
    complete = all(not row["gaps"] for row in results)
    local_pass = complete and all((row.get("hydraulic_sizing", {}).get("capacity_factor_gate", row.get("capacity_factor_gate")) == "PASS") and row.get("height_gate_source", "PASS") == "PASS" for row in results)
    return {"schema": "packed-hydraulic-preliminary-result-v1", "generated": datetime.now().isoformat(timespec="seconds"),
            "run_id": config["run_id"], "config_sha256": config["_config_sha256"], "config_path": config["_config_path"],
            "artifacts": config["_artifacts"], "basis": {k: config.get(k) for k in ("property_method", "vapor_density_model", "parameters", "towers", "parallel_distribution")},
            "towers": results, "local_calculation_gate": "PASS" if local_pass else "REVIEW",
            "simulation_clean_verified": False, "software_rating_verified": False, "engineering_accepted": False,
            "parallel_distribution_verified": False,
            "unassessed": ["Aspen strict same-file run", "pressure-drop method and branch pressure balance", "liquid loading/turndown and distribution", "vendor HETP/flooding guarantee", "support/mechanical design", "full-flow reconnect/products"],
            "original_method_boundary": "Ideal-gas density and F-factor preliminary method; source assumptions are not validated physical properties; original diameter selection considers all exported stages"}

def write_preliminary_markdown(path, result):
    lines = ["# Packed tower preliminary calculation", "", "Local calculation gate: " + result["local_calculation_gate"] + ".", "",
             "This is a source-bound preliminary calculation, not an Aspen hydraulic rating, vendor guarantee or accepted flowsheet.", "",
             "## Calculation basis", "", "- Run: " + result["run_id"], "- Configuration SHA256: " + result["config_sha256"],
             "- Density uses the explicitly accepted ideal-gas assumption; F-factor and all limits come from the supplied sources.",
             "- MW = vapor mass / vapor mole; rho = P MW / (R T); Qv = vapor mass / rho; F = u sqrt(rho).",
             "- Single-tower diameter uses the original target-F/area/diameter rounding calculation. Bed height uses stages × sourced HETP.",
             "- Parallel checks use each tower's own export and uniform INP diameter; no equal split or branch pressure solution is assumed.", ""]
    for artifact, row in result["artifacts"].items():
        lines.append(f"- {artifact}: `{row['path']}`; SHA256 `{row['sha256']}`; source {row['source']}; locator {row['locator']}.")
    for tower in result["towers"]:
        tag = tower.get("block", tower.get("tower", {}).get("aspen_block", "unresolved"))
        lines.extend(["", "## " + str(tag), "", "Evidence: " + tower["evidence_level"] + "."])
        sizing = tower.get("hydraulic_sizing", tower)
        diameter = sizing.get("selected_inside_diameter_m", sizing.get("selected_diameter_m"))
        lines.append("- Selected diameter (m): " + str(diameter))
        lines.append("- Capacity gate: " + str(sizing.get("capacity_factor_gate", "NOT_COMPUTED")))
        for bound in ("min_actual_capacity_factor", "max_actual_capacity_factor"):
            value = sizing.get(bound, {})
            if value:
                lines.append(f"- {bound}: {value.get('actual_capacity_factor_fraction')}; governing stage {value.get('stage')}.")
        beds = tower.get("packing_beds", tower.get("internals", []))
        if beds:
            lines.extend(["", "| Bed/section | Stages | Height m | H/D | Local height gate |", "| --- | --- | ---: | ---: | --- |"])
            for row in beds:
                lines.append(f"| {row.get('section', row.get('bed_index'))} | {row.get('stage1', '')}-{row.get('stage2', row.get('theoretical_stages', ''))} | {row.get('packing_height_m')} | {row.get('height_to_diameter')} | {row.get('segment_height_gate', 'UNKNOWN')} |")
        nozzles = tower.get("nozzle_predesign", tower.get("nozzles", {}))
        if nozzles:
            lines.extend(["", "| Nozzle/service | Flow m3/s | Velocity m/s | ID m | State |", "| --- | ---: | ---: | ---: | --- |"])
            for name, row in nozzles.items():
                lines.append(f"| {name} | {row.get('volumetric_flow_m3_s')} | {row.get('velocity_m_s')} | {row.get('diameter_m')} | {row.get('status')} |")
        if tower["gaps"]:
            lines.extend(["", "### Affected-only gaps", ""])
            lines.extend(f"- {row['field']}: {row['reason']}; affects {row['affected']}." for row in tower["gaps"])
    lines.extend(["", "## Not verified", ""])
    lines.extend("- " + item for item in result["unassessed"])
    lines.extend(["", "A local calculation PASS does not imply the missing checks pass. Recalculate from the same final operating point after any process or geometry change.", ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8", newline="\n")

def cli(module, mode):
    parser = argparse.ArgumentParser(description="Original packed hydraulic equations with explicit source-bound case config; no Aspen execution")
    parser.add_argument("--config", required=True, help="packed-hydraulic-case-config-v1 JSON; all paths relative to config")
    parser.add_argument("--out-prefix", required=True)
    args = parser.parse_args()
    try:
        config = load_config(args.config, mode)
        result = execute(module, config)
        prefix = Path(args.out_prefix).resolve()
        paths = [prefix.with_suffix(".json"), prefix.with_suffix(".md"), Path(str(prefix)+"_stage_profile.csv")]
        if any(p.exists() for p in paths):
            raise BasisError("Output collision; choose a fresh project-local prefix")
        encoded = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        prefix.parent.mkdir(parents=True, exist_ok=True)
        paths[0].write_text(encoded, encoding="utf-8", newline="\n")
        rows = [{"block": row.get("block", row.get("tower", {}).get("aspen_block")), **stage} for row in result["towers"] for stage in row.get("stage_profile", [])]
        if rows:
            import csv
            fields = list(dict.fromkeys(key for row in rows for key in row))
            with paths[2].open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fields); writer.writeheader(); writer.writerows(rows)
        write_preliminary_markdown(paths[1], result)
        print(json.dumps({"status": result["local_calculation_gate"], "json": str(paths[0]), "engineering_accepted": False}))
        return 0 if result["local_calculation_gate"] == "PASS" else 1
    except (BasisError, OSError, ValueError, KeyError, TypeError, ZeroDivisionError) as exc:
        print(json.dumps({"status": "basis_invalid_or_dependency_unavailable", "reason": str(exc), "engineering_accepted": False}))
        return 2
