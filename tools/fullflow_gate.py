"""Read-only evidence-structure gate for document-driven full-flow generation.

This is not a simulator or a provider-log authenticator. It checks current,
hash-bound records and reuses the existing handoff structure checker. Even a
consistent dossier never proves chemistry, an independent model invocation,
actual Aspen execution, or engineering acceptance. No simulation commands are executed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from pathlib import Path
import re
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "fullflow-workflow-contract-v1"
AUXILIARIES = ("heating", "heat_exchange", "compression", "pumping", "pressure_control")
STAGES = ("source", "scaffold", "island", "reconnect", "change", "delivery")
READS = (
    "aspen-document-driven-flowsheet/references/fullflow_generation_workflow.md",
    "aspen-document-driven-flowsheet/references/source_scaffold_handoff.md",
    "aspen-document-driven-flowsheet/references/document_driven_workflow.md",
    "chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md",
)
PLANNING_REVIEW_BRIEF = "aspen-document-driven-flowsheet/references/planning_review_brief.md"
PLANNING_REVIEW_REFS = ("planning_article_ref", "design_basis_ref", "handoff_input_ref", "planning_checks_ref")
BOUNDARY = ("Evidence completeness and declared identity consistency only; hashes do not authenticate "
            "provider invocations, Aspen provenance, scientific truth or engineering acceptance.")


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


_STATE_UNITS = {
    "temperature": {"k", "c", "°c", "℃", "f", "°f", "r", "°r", "kelvin", "degc", "degf", "摄氏度"},
    "pressure": {"pa", "kpa", "mpa", "bar", "bara", "barg", "atm", "psi", "psia", "psig", "torr", "mmhg",
                 "帕", "千帕", "兆帕"},
}


def _pressure_reading(row):
    """Return pascals and reference for a declared Aspen operating pressure."""
    if not isinstance(row, dict):
        return None
    unit = str(row.get("unit_or_basis", "")).strip().casefold().replace(" ", "")
    unit = {"帕": "pa", "千帕": "kpa", "兆帕": "mpa"}.get(unit, unit)
    match = re.fullmatch(r"(mpa|kpa|pa|bar|atm|psi|torr|mmhg)(?:\((a|g)\)|(abs|gauge|a|g))?", unit)
    if not match:
        return None
    scales = {"pa": 1, "kpa": 1e3, "mpa": 1e6, "bar": 1e5, "atm": 101325,
              "psi": 6894.757293168, "torr": 101325 / 760, "mmhg": 133.322387415}
    value = row.get("value")
    qualifier = match[2] or match[3]
    basis = str(row.get("basis", "")).lower()
    if qualifier is None:
        if re.search(r"表压|\bgauge\b", basis):
            qualifier = "g"
        elif re.search(r"绝压|绝对压|\babsolute\b", basis):
            qualifier = "a"
    reference = "gauge" if qualifier in ("gauge", "g") else "absolute" if qualifier in ("abs", "a") else "aspen"
    return (value * scales[match[1]] if _finite(value) else None, reference)


def _temperature_in_kelvin(value, unit):
    if not _finite(value):
        return None
    aliases = {"°c": "c", "℃": "c", "degc": "c", "摄氏度": "c", "kelvin": "k",
               "°f": "f", "degf": "f", "°r": "r"}
    unit = str(unit).strip().casefold()
    unit = aliases.get(unit, unit)
    value = Decimal(str(value))
    absolute = {"c": lambda: value + Decimal("273.15"), "k": lambda: value,
                "f": lambda: (value + Decimal("459.67")) * 5 / 9, "r": lambda: value * 5 / 9}
    return float(absolute[unit]()) if unit in absolute else None


def _state_unit_supported(name, row):
    if name == "pressure":
        return _pressure_reading(row) is not None
    return str(row.get("unit_or_basis", "")).strip().casefold() in _STATE_UNITS[name]


def _feed_rate_unit(unit):
    unit = str(unit).casefold().replace(" ", "")
    amount = r"(?:[kmµu]?g|kg|t|tonne?|lbm?|[kμmu]?mol|[cnm]?m[³3]|[mµu]?l|千克|公斤|吨|克|千摩尔|摩尔|立方米)"
    time = r"(?:s|sec(?:ond)?s?|min(?:ute)?s?|h|hr|hours?|d|days?|秒|分钟|小时|日|天)"
    return bool(re.fullmatch(amount + r"(?:(?:/|per|每)" + time + "|" + time + r"(?:\^-1|-1|⁻¹))", unit))


def _article_text(path):
    """Read the bound editable body; paragraphs and table cells retain document order."""
    if path.suffix.lower() in {".md", ".txt"}:
        if path.stat().st_size > 5_000_000:
            raise ValueError("Planning article text exceeds 5 MB")
        content = path.read_text(encoding="utf-8-sig")
    elif path.suffix.lower() == ".docx":
        with ZipFile(path) as package:
            entry = package.getinfo("word/document.xml")
            if entry.file_size > 10_000_000:
                raise ValueError("Planning article document body exceeds 10 MB")
            body = ElementTree.fromstring(package.read(entry))
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        content = "\n".join("".join(run.text or "" for run in p.iter(ns + "t"))
                            for p in body.iter(ns + "p"))
    else:
        raise ValueError("Use the exact editable MD, TXT or DOCX planning article")
    if not content.strip() or "\x00" in content or content.lstrip().startswith(("{", "[")) and _is_json(content):
        raise ValueError("An editable prose article is required")
    return content


def _is_json(content):
    try:
        json.loads(content)
        return True
    except ValueError:
        return False


def _ratio(row):
    """Convert percent/fraction specifications without guessing the scale."""
    value, unit = row.get("value"), str(row.get("unit_or_basis", "")).strip().casefold()
    if not _finite(value):
        return None
    if unit in {"%", "wt%", "mol%", "vol%", "percent", "percentage", "百分比", "％"}:
        return value / 100
    if unit in {"1", "-", "fraction", "mole fraction", "mass fraction", "volume fraction",
                "mol/mol", "kg/kg", "摩尔分率", "质量分率", "分率"}:
        return value
    return None


def _meets_design(value, target, rule):
    """Compare in the frozen target's units; allowances include their endpoints."""
    if not _finite(target):
        return type(value) is type(target) and value == target
    if not _finite(value) and not isinstance(value, Fraction):
        return False
    comparison = rule["comparison"]
    actual, nominal = Fraction(str(value)), Fraction(str(target))
    if comparison == "eq" and "acceptance_decimals" in rule:
        factor = 10 ** rule["acceptance_decimals"]
        rounded = math.floor(abs(actual) * factor + Fraction(1, 2))
        return Fraction(rounded if actual >= 0 else -rounded, factor) == nominal
    if "acceptance_width" in rule:
        width = Fraction(rule["acceptance_width"])
        if comparison == "ge":
            return actual >= nominal - width
        if comparison == "le":
            return actual <= nominal + width
        return comparison == "eq" and abs(actual - nominal) <= width
    if comparison == "ge":
        return actual >= nominal
    if comparison == "le":
        return actual <= nominal
    return actual == nominal if rule.get("design_target") else math.isclose(value, target, rel_tol=1e-12, abs_tol=1e-12)


def _recovery_interval(row, rule):
    """Permitted physical split for a single outlet, including any open half-up upper end."""
    scale = Decimal(str(_ratio({"value": 1, "unit_or_basis": row["unit_or_basis"]})))
    nominal = Decimal(str(row["value"]))
    precision = rule.get("acceptance_decimals")
    width = Decimal("0.5").scaleb(-precision) if precision is not None else rule.get("acceptance_width", Decimal(0))
    lower = 0 if rule["comparison"] == "le" else max(0, (nominal - width) * scale)
    upper = 1 if rule["comparison"] == "ge" else (nominal + width) * scale
    return lower, min(1, upper), precision is not None and upper <= 1


def _cut_rank(matrix):
    """Rank of the component-balance/product-specification coefficient matrix."""
    pivots = {}
    for coefficients in matrix:
        row = list(coefficients)
        for col in sorted(pivots):
            factor = row[col]
            row = [x - factor * y for x, y in zip(row, pivots[col])]
        first = next((col for col, value in enumerate(row) if abs(value) > 1e-10), None)
        if first is not None:
            pivots[first] = [x / row[first] for x in row]
    return len(pivots)


def _amount_rate_basis(unit, *, exact=False):
    """Normalize the common molar and mass amount rates to mol/s or kg/s."""
    match = re.fullmatch(r"(mol|kmol|g|kg|t)/(s|sec|min|h|hr|d|day)", str(unit).casefold().replace(" ", ""))
    if match is None:
        return None
    amount, time = match.groups()
    scale = {"mol": 1, "kmol": 1000, "g": 0.001, "kg": 1, "t": 1000}
    seconds = {"s": 1, "sec": 1, "min": 60, "h": 3600, "hr": 3600, "d": 86400, "day": 86400}
    factor = Fraction(str(scale[amount])) / seconds[time] if exact else scale[amount] / seconds[time]
    return ("mole" if amount.endswith("mol") else "mass"), factor


def _declared_material(stream, *, exact=False):
    """Normalize an explicitly quantified material stream without guessing missing values."""
    if not isinstance(stream, dict) or stream.get("stream_kind", "material") in ("heat", "work"):
        return None
    composition = stream.get("composition")
    if not isinstance(composition, dict) or not composition or not all(_finite(v) and v >= 0 for v in composition.values()):
        return None
    unit = str(stream.get("basis", "")).strip().casefold()
    if rate_basis := _amount_rate_basis(unit, exact=exact):
        kind, scale = rate_basis
        dimension = "rate"
    elif unit in ("mole fraction", "mass fraction", "mol%", "wt%"):
        kind = "mole" if unit in ("mole fraction", "mol%") else "mass"
        scale = 0.01 if unit.endswith("%") else 1
        dimension = "fraction"
    else:
        return None
    if exact:
        return kind, dimension, {component: Fraction(str(amount)) * Fraction(str(scale)) for component, amount in composition.items()}
    return kind, dimension, {component: amount * scale for component, amount in composition.items()}


def _composition_differences(first, second):
    return {component: [first.get(component, 0), second.get(component, 0)] for component in sorted(first.keys() | second.keys())
            if not math.isclose(first.get(component, 0), second.get(component, 0), rel_tol=1e-6, abs_tol=1e-9)}


def _known_feed(inlets):
    """Resolve only explicit same-basis material rates or fractions with a known rate."""
    totals = {}
    basis = None
    for row in inlets:
        if not isinstance(row, dict) or row.get("stream_kind", "material") in ("heat", "work"):
            continue
        declared = _declared_material(row, exact=True)
        if not declared:
            return None
        kind, dimension, composition = declared
        scale = 1
        if dimension == "fraction":
            flow = (row.get("feed_state") or {}).get("flow") or {}
            rate = _amount_rate_basis(flow.get("unit_or_basis"), exact=True)
            value = flow.get("value")
            if (not rate or rate[0] != kind or not _finite(value) or value < 0
                    or not math.isclose(math.fsum(composition.values()), 1, rel_tol=1e-6)):
                return None
            scale = Fraction(str(value)) * rate[1]
        if basis is not None and basis != kind:
            return None
        basis = kind
        for component, amount in composition.items():
            totals[component] = totals.get(component, 0) + amount * scale
    return (basis, totals) if basis and totals else None


def _outlet_fractions(inputs, component, outlets):
    rows = [row for row in inputs if isinstance(row, dict) and row.get("kind") == "recovery"
            and row.get("component") == component and row.get("outlet") in outlets]
    splits = {}
    for row in rows:
        if _ratio(row) is None:
            return None
        scale = _ratio({"value": 1, "unit_or_basis": row["unit_or_basis"]})
        splits[row["outlet"]] = Fraction(str(row["value"])) * Fraction(str(scale))
    if len(outlets) < 2 or len(splits) != len(rows) or len(splits) < len(outlets) - 1:
        return None
    if not all(value is not None and 0 <= value <= 1 for value in splits.values()):
        return None
    total = sum(splits.values())
    if total > 1 + 1e-9 or (len(splits) == len(outlets) and not math.isclose(total, 1, abs_tol=1e-9)):
        return None
    splits.update({outlet: max(0, 1 - total) for outlet in outlets - splits.keys()})
    return splits


def _canonical(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _same_observed_value(actual, expected):
    """Compare JSON values exactly, allowing alternative representations of the same number."""
    if isinstance(expected, dict):
        return (isinstance(actual, dict) and actual.keys() == expected.keys()
                and all(_same_observed_value(actual[key], value) for key, value in expected.items()))
    if isinstance(expected, list):
        return (isinstance(actual, list) and len(actual) == len(expected)
                and all(_same_observed_value(a, e) for a, e in zip(actual, expected)))
    if type(expected) in (int, float):
        return type(actual) in (int, float) and actual == expected
    return type(actual) is type(expected) and actual == expected


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _skill_root():
    bundled = ROOT / "plugins/chemical-engineering-skills/skills"
    if bundled.is_dir():
        return bundled
    from tools.product_contract import skill_location
    location = skill_location()
    return Path(location["path"]).parent.parent if location.get("available") else None


def _readings():
    root = _skill_root()
    return [{"logical_path": name, "path": str(root / name) if root else None,
             "available": bool(root and (root / name).is_file()),
             "sha256": hashlib.sha256((root / name).read_bytes()).hexdigest()
             if root and (root / name).is_file() else None,
             "reading_status": "AGENT_READING_REQUIRED_NOT_PROVEN_BY_HASH"} for name in READS]


def planning_review_layout(review):
    """Report misplaced or missing module fields in a raw planning answer."""
    if not isinstance(review, dict):
        return ["Expected one JSON object for the complete review."]
    fields = {"verification_checks": dict, "planning_assessments": dict,
              "quantitative_extractions": list, "issues": list}
    problems = [f"Move top-level {key} into the owning module_reviews entry."
                for key in fields if key in review]
    rows = review.get("module_reviews")
    if not isinstance(rows, list) or not rows:
        return problems + ["module_reviews must contain one object per declared module."]
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            problems.append(f"module_reviews[{index}] must be an object.")
            continue
        for key, kind in fields.items():
            if not isinstance(row.get(key), kind):
                label = "array" if kind is list else "object"
                problems.append(f"module_reviews[{index}].{key} must be a JSON {label}.")
    return problems


def _planning_review_brief():
    root = _skill_root()
    if root is None:
        raise ValueError("Registered planning reviewer brief is unavailable")
    brief = (root / PLANNING_REVIEW_BRIEF).read_text(encoding="utf-8-sig").rstrip()
    if not brief:
        raise ValueError("Registered planning reviewer brief is empty")
    return brief


def build_planning_review_prompt(case_id, task_revision, *, evidence_root, planning_article_ref,
                                 design_basis_ref, handoff_input_ref, planning_checks_ref,
                                 review_specifications):
    """Render the whole common instruction body and exact project input references."""
    frozen = {"case_id": case_id, "task_revision": task_revision, "evidence_root": str(Path(evidence_root).resolve()),
              "planning_article_ref": planning_article_ref, "design_basis_ref": design_basis_ref,
              "handoff_input_ref": handoff_input_ref, "planning_checks_ref": planning_checks_ref,
              "review_specifications": review_specifications}
    if not _text(case_id) or not _text(task_revision):
        raise ValueError("Planning review requires the frozen case_id and task_revision")
    invalid_refs = [name for name in PLANNING_REVIEW_REFS
                    if not isinstance(frozen[name], dict) or set(frozen[name]) != {"path", "sha256"}
                    or not _text(frozen[name]["path"]) or not _text(frozen[name]["sha256"])
                    or not re.fullmatch(r"[0-9a-fA-F]{64}", frozen[name]["sha256"])]
    if invalid_refs:
        raise ValueError("Planning review requires exact references for " + ", ".join(invalid_refs))
    inputs = json.dumps(frozen, ensure_ascii=False, sort_keys=True, indent=2)
    prompt = f"{_planning_review_brief()}\n\n## 本次送审冻结输入\n\n```json\n{inputs}\n```\n"
    return {"text": prompt, "sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest()}


def _planning_review_dispatch():
    result = {"entrypoint": "tools.fullflow_gate.build_planning_review_prompt",
              "brief_path": PLANNING_REVIEW_BRIEF,
              "required_inputs": ["case_id", "task_revision", "evidence_root", *PLANNING_REVIEW_REFS,
                                  "review_specifications"],
              "source_review_closed": False,
              "delivery": "Save text verbatim as UTF-8 source_gate.prompt_ref. Send it to each required independent context and record it as invocation.dispatched_prompt. Reuse valid calls for the same complete reviewed input."}
    try:
        result.update(status="INPUTS_REQUIRED", brief=_planning_review_brief())
    except (OSError, ValueError) as exc:
        result.update(status="BRIEF_UNAVAILABLE", detail=str(exc))
    return result


def schema():
    """Small discovery contract; synthetic examples live with the regression tests."""
    return {"schema": SCHEMA, "entrypoint": "tools.fullflow_gate.check_fullflow",
            "discovery_only": True, "not_a_complete_json_schema": True,
            "payload_field": "fullflow_contract", "reference": {"path": "project-relative path", "sha256": "64 hex characters"},
            "planning_review_dispatch": _planning_review_dispatch(),
            "first_scaffold_python_entrypoint": {
                "callable": "tools.design_stage.run_buildable_first_scaffold",
                "input": "Current source payload and evidence root; fullflow_contract must bind the accepted planning article and completed reviews",
                "runner": "A zero-argument callable for the authorized native first scaffold, called only after the live source precheck",
            },
            "required_contract_fields": ["schema", "case_id", "task_revision", "scope", "modules", "source_gate"],
            "stage_fields": {"source": ["source_gate"], "scaffold": ["source_gate", "scaffold_gate"],
                "island": ["source_gate", "scaffold_gate", "islands"],
                "reconnect/change/delivery": ["source_gate", "scaffold_gate", "islands", "replacements", "current_run_ref"]},
            "source_gate": ["design_basis_ref", "prompt_ref", "independent_calls (3 references)",
                            "difference_closure_ref", "handoff_input_ref", "handoff_review_ref", "planning_checks_ref"],
            "planning_checks_ref": "One short source-bound record: pressure_budget, heat_strategy, compression_decisions; group modules when appropriate. Reuse existing calculations; no new solver.",
            "scaffold_gate": ["run_ref", "cycle_initials_ref", "prompt_ref", "independent_calls (3 references)",
                              "difference_closure_ref"],
            "module_fields": ["id", "module_revision", "role", "purpose", "node_ids", "inlets", "outlets", "targets",
                              "thermodynamics", "auxiliary_requirements", "auxiliaries", "unknowns",
                              "reaction (reaction role) or separation (separation role)"],
            "scope": {"mode": "fullflow or module", "module_ids": "explicit current module IDs for module scope"},
            "buildable_plan": {
                "activation": "planning_scope=buildable_flowsheet; source_gate.planning_article_ref names the exact editable MD/TXT/DOCX",
                "module": "physical_service, exact article_excerpt, first_model; nested auxiliaries also carry first_model. thermodynamics.selection_status=supported|uncertain|conflict|outside_range",
                "first_model": "block_type, required_inputs (case/configuration-specific names), source_ref, inputs (quantity or {name,spec_id}); no_input_basis explains a legitimately empty inventory",
                "setting": "name, value, unit_or_basis, basis, source_ref, article_excerpt, mode=fixed|adjustable|derived|default|determined; adjustable also needs bounds.lower/upper; determined names depends_on inputs.",
                "numeric_design_target": "Freeze acceptance_tolerance={kind:absolute|relative|hard_limit,value,unit,basis,source_ref}. basis quotes the rule from the source or calculation note (source_page for PDF). article_excerpt locates its wording in the reviewed plan, defaults to basis. Absolute differences use the target unit (percentage_point or 百分点 for percentage targets; also supported on fraction targets). Relative uses unit=% and reference=target, applied to the absolute nominal value. A hard_limit uses ge/le, value=0 and no rounding. Ordinary eq/ge/le use an inclusive band/favorable side. An existing explicit acceptance_decimals nominal equality ratio with a bound half-up acceptance excerpt is also valid. Unrelated model inputs do not require a target tolerance.",
                "scaffold_target_readback": "Replay net separations and single-reaction per-pass conversions from the bound run's result_snapshot_ref. For other numeric targets, design_readback_paths maps spec_id to design_readbacks.* with the same units, basis, design_context and native Output path. An existing unambiguous matching projection can also be reused.",
                "reaction": "network[{id,equation,source_ref,article_excerpt}], conditions, extent (kind=conversion|yield|model_determined, reaction_id, key_reactant, denominator, pass_basis=per_pass|overall); hydrogen_basis for consumed H2. An RStoic input must bind each per-pass nominal conversion",
                "separation": "initial_method, targets (kind=recovery|purity|cut, outlet, component where applicable, comparison=eq|ge|le, amount_basis=mole|mass for mixture targets). SEP/SEP2 needs native numeric splits; its internal T/P and detailed island design are optional",
                "planning_research": {
                    "location": "module.reaction.planning_research or module.separation.planning_research (including RStoic/SEP placeholders)",
                    "record": "selected_candidate_id, selection_criterion, article_excerpt, candidates[], target_mappings[], alternatives_limit if only one source-based candidate",
                    "candidate": "id, method, mechanism, applicability, assessment, transfer_scope=same_system|analog, evidence[]; selected candidate adds basis and mapped_inputs[{parameter,source_basis,model_use}]",
                    "evidence": "source_ref to MD/TXT/DOCX source text or machine-readable PDF, citation, source_locator (original page/table/section), locator (L<n> in text or P<n>:L<n> for nonempty PDF text lines read by pypdf or local pdftotext), excerpt, optional original_ref for retained original bytes",
                    "reaction": "response_required (bool), response_basis; candidates use strategy=kinetic|equilibrium|lumped|multi_condition|balance. Selected kinetic basis has rate_law, rate_units, rate_basis, parameters, catalyst, validity. Other selected bases have relation, validity, limit (multi_condition adds measurements[{condition,result,value,unit_or_basis,source_basis}]). A non-kinetic choice includes an assessed kinetic source with quoted validity or kinetics_exclusion={source_finding,case_limit,evidence[]}.",
                    "separation": "Selected basis has phases[], phase_data and operating_range from the checked physical separation evidence",
                    "target_mapping": "spec_id points to each reaction.extent or separation.targets row; model_use=input|solve_target|verification, basis retains the same definition",
                    "provisional": "For unresolved later-island inputs, record unresolved_inputs[], refine_trigger and independent_work; the first-model baseline still needs its own checked inputs",
                },
                "feed": "External material inlet feed_state contains flow, temperature, pressure quantities; existing composition and basis specify component rates/fractions. External heat/work stream_kind uses duty. Inherit a defined variable via mode=determined and depends_on",
            },
            "identity_fields": ["case_id", "task_revision"],
            "first_model_scope": "Freeze planning_scope=buildable_flowsheet on new complete first-model contracts; source_work=buildable_plan at planning. A site may configure CHEMENG_REFERENCE_LIBRARY for the optional TH03 adapter.",
            "island_design_specifications": {
                "location": "island.boundary_ref -> design_specifications",
                "article_sha256": "Exact hash of the reviewed first-model article",
                "parameters": "Key every primary first-model spec_id (including external feed input and net component allocation); bounds accompany their parameter.",
                "parameter_mapping": "baseline_path and refined_path address each module export's design_readbacks projection with value, unit_or_basis, basis, and original design_context. Reconnect uses the same logical address as refined_path, backed by its own actual native run.",
                "use": "preserve, solve_target or verification always retain the original comparison. vary is only for explicitly adjustable operating values inside their approved range. Retain governing_relation for source-determined quantities.",
                "native_results": "The native run receipt binds result_snapshot_ref to the same run/model. The JSON snapshot uses the existing Aspen probes format plus run_id and case_sha256. Direct readbacks identify native_path; separation recovery, purity and cut replay their net boundary quantity from native stream output. SEP component allocations require the component flow at every net outlet, including the balance outlet."},
            "nested_fields": {
                "stream": ["stream_id", "composition (component->amount/fraction or sourced relation)", "basis", "source_ref"],
                "quantity": ["name", "value", "unit_or_basis", "source_ref"],
                "thermodynamics": ["components[]", "temperature_range", "pressure_range", "phases[]", "method", "applicability", "source_refs[]"],
                "reaction": ["conditions[quantity]", "extent[quantity]"],
                "separation": ["conditions[quantity]", "targets[quantity]"],
                "auxiliary_requirements": {key: ["state=required|not_required", "basis", "source_ref"] for key in AUXILIARIES},
                "auxiliary": ["node_id", "kind", "source_ref"],
                "unknown": ["question", "external_search_ref", "resolution", "resolution_sources[]", "fallback_reason when no hit/unavailable"],
                "external_search_record": ["case_id", "task_revision", "query", "source_scope", "response_ref", "result=hits|no_hits|unavailable"],
                "source_design_basis": ["case_id", "task_revision", "modules (source module records without module_revision)"],
                "island": ["module_id", "module_revision", "boundary_ref", "specialist_route_ref", "run_ref", "equipment_gate_ref", "optional thermodynamics_change_ref"],
                "island_equipment_gate": "Hash-bound design_stage(stage=island) receipt from the exact island run; isolated model export physical_equipment_ids must equal the canonical equipment export and every calculated tag. Pending process revision blocks module completion.",
                "island_boundary": ["case_id", "task_revision", "module_id", "module_revision", "original_node_ids", "from_run_id", "from_run_ref", "from_export_ref", "inlets", "outlets", "targets"],
                "specialist_route": ["case_id", "task_revision", "module_id", "module_revision", "boundary_sha256", "owner (installed Skill name)", "method", "source_refs[]"],
                "replacement": ["module_id", "module_revision", "island_run_id", "original_node_ids", "replacement_node_ids", "installed_run_id", "evidence_ref (same fields plus task identity)"],
                "property_change": ["case_id", "task_revision", "module_id", "module_revision", "prior_thermodynamics_sha256 (canonical sorted compact UTF-8 JSON)", "basis", "authority_ref", "thermodynamics"],
                "proposal_authorization": ["case_id", "task_revision", "stream_ids", "basis", "authority_ref"],
                "observation": ["evidence_ref", "value_path (dotted object/list path)", "value (exact actual field value, including its JSON type)"],
                "verification_check": ["observation[]", "evidence_refs[]"],
                "source_verification_checks": ["module_purpose", "inlet_outlet_composition", "reaction_or_separation_basis", "thermodynamic_basis", "heat_pressure_auxiliaries", "connections_terminals"],
                "scaffold_additional_verification_checks": ["actual_block_parameters", "omitted_components", "cycle_initials", "current_export_binding"],
                "module_review": ["module_id", "role_summary", "boundary_summary", "thermodynamics_summary", "reaction_or_separation_summary", "issues[{id,finding}]", "verification_checks (fixed keys above)", "buildable source: quantitative_extractions[] and issue node_id/recommended_change/rereview_scope"],
                "buildable_planning_assessments": {
                    "each_module": ["physical_feasibility", "design_depth", "evidence_applicability", "handoff"],
                    "role_specific": {"reaction": "reaction_kinetics", "separation": "separation_readiness"},
                    "assessment": ["node_ids[]", "evidence[]", "observed_result", "action", "status=adequate|provisional|issue", "issue_id if status=issue"],
                    "evidence": "{evidence_ref,value_path,value} for exact JSON observations or {evidence_ref,article_locator,article_excerpt} for the reviewed article. Use the canonical brief for the required evidence for each assessment.",
                },
                "quantitative_extraction": ["node_id", "spec_id", "value (finite number, {lower,upper}, or quoted named input/governing relation; null for ambiguity)", "unit_or_basis", "basis", "design_context (applicable structured reaction or separation basis)", "article_locator (L<n>)", "article_excerpt", "comparison=match|difference|ambiguous", "issue_id for differences or ambiguity"],
                "verification_anchor_rule": "Source observations address design_basis.modules.<index> role/purpose/inlets/outlets/reaction-or-separation/thermodynamics/auxiliary_requirements/auxiliaries, and handoff nodes/streams. Scaffold additionally observes current export block_type/parameters, source and export modules/auxiliary_nodes, cycle mode/streams plus export recycle_stream_ids, and export run_id/model_sha256/raw_export_ref.",
                "planning_row": ["module_ids[]", "state=calculated|provisional_bounds|not_applicable|blocked (heat/compression also reasoned)", "method", "input_basis", "evidence_refs[]"],
                "planning_calculated": ["calculation_ref (existing JSON output)", "result_path (dotted numeric field)", "unit"],
                "planning_provisional_bounds": ["bounds={lower,upper,unit,source_ref}", "unresolved_inputs[]", "refine_trigger"],
                "planning_not_applicable_or_blocked": ["reason (source-bound, not a pass label)"],
                "current_equipment_export_binding": ["case_id", "run_id", "model_sha256", "raw_export_sha256"],
            },
            "record_schemas": {
                "fullflow-agent-call-v1": ["case_id", "task_revision", "stage", "call_id", "independent_context_id", "model_id", "reasoning_effort (same actual model and effort across the group)", "prompt_sha256", "invocation_ref", "output_ref"],
                "invocation_record": ["case_id", "task_revision", "invocation_id", "call_id", "independent_context_id", "model_id", "reasoning_effort", "prompt_sha256", "output_sha256", "buildable plan flow: started_epoch/finished_epoch", "buildable source: dispatched_prompt (actual complete common text sent)", "buildable source, optional: raw_output_refs[] (separate raw answer files)"],
                "fullflow-independent-review-v1": ["case_id", "task_revision", "call_id", "process_chain[{stream_id,from,to}]", "module_reviews[]", "source: design_basis_sha256", "buildable source: planning_article_sha256", "scaffold: run_id/export_sha256/cycle_initials_sha256"],
                "fullflow-difference-closure-v1": ["case_id", "task_revision", "reviewer_id", "comparisons[{call_id,module_id,output_sha256,issue_ids,disposition=adopt|reject|no_difference,rationale,evidence_refs}]", "buildable plan flow: closed_epoch"],
                "buildable_source_issue_closure": {
                    "with_findings": "On the call/module comparison, use issue_dispositions[{issue_id,disposition=adopt|reject,rationale,evidence_refs}] instead of comparison-level issue_ids/disposition/rationale/evidence_refs. Include each issue exactly once. An adopted finding keeps this revision open.",
                    "without_findings": "Use issue_ids=[] and disposition=no_difference with rationale and evidence_refs on the comparison.",
                },
                "fullflow-run-evidence-v1": ["case_id", "task_revision", "run_id", "model_ref", "native_run_ref", "export_ref", "island: module_id/module_revision/boundary_sha256"],
                "native_run_record": ["run_id", "case_sha256", "status=completed", "started_epoch", "finished_epoch", "may be nested under existing audit.run"],
                "scaffold_interface_names": "Optional on the reviewed source design_basis_ref. Map streams and terminals as {frozen_id:{actual_id,basis}}. The source review reads this frozen mapping; export-supplied aliases cannot redefine endpoint identity.",
                "fullflow-model-export-v1": ["case_id", "task_revision", "run_id", "model_sha256", "raw_export_ref", "connections[{stream_id,from,to}]", "modules[{module_id,module_revision,original_node_ids,node_ids,block_type,parameters,inlets,outlets,targets,thermodynamics}]", "multi-node buildable scaffold: block_types{native_node_id:block_type}, in the frozen original_node_ids/node_ids correspondence", "auxiliary_nodes[{node_id,block_type}]", "recycle_stream_ids[]", "island: module_id/module_revision/boundary_sha256"],
                "fullflow-cycle-initials-v1": ["case_id", "task_revision", "run_id", "export_sha256", "mode=recycle|no_recycle", "basis", "source_refs[]", "streams[{stream_id,flow:{value,unit_or_basis},temperature:{value,unit_or_basis},pressure:{value,unit_or_basis},phase,composition,basis,source_ref}]", "Recycle streams must match the frozen tear plan and actual scaffold endpoints, with flow, temperature, absolute pressure, fluid phase (liquid|vapor|two_phase), and molar/mass composition replayed from the same run's Output probes"],
                "fullflow-planning-checks-v1": ["case_id", "task_revision", "pressure_budget[planning_row]", "heat_strategy[planning_row]", "compression_decisions[planning_row]"],
                "handoff": "Existing document-flow-handoff-v1 and document-flow-handoff-check-v1; original input and checker hash required. source_gate.proposal_authorizations[] is optional for source-backed proposed edges, never unknown endpoints.",
            },
            "identity": "task_revision freezes requirements; module_revision changes invalidate only corresponding island/replacement records",
            "synthetic_fixture": "tests/test_fullflow_gate.py:FullflowFixture",
            "engineering_accepted": False, "boundary": BOUNDARY}


contract_schema = schema


class _Gate:
    def __init__(self, payload, root, documents):
        self.payload = payload
        self.root = Path(root).resolve()
        self.documents = documents or {}
        self.needs = []
        self.identity = {}
        self.modules = {}
        self.scope = []
        self.summary = {}
        self.current_thermodynamics = {}
        self.require_buildable_plan = False

    def need(self, code, where, detail):
        self.needs.append({"code": code, "scope": where, "detail": detail})

    def require(self, condition, code, where, detail):
        if not condition:
            self.need(code, where, detail)
        return bool(condition)

    def obj(self, value, where):
        if not isinstance(value, dict):
            self.need("INVALID_SHAPE", where, "Object required")
            return {}
        return value

    def rows(self, value, where, *, nonempty=True):
        if not isinstance(value, list) or (nonempty and not value):
            self.need("INVALID_SHAPE", where, "Nonempty array required" if nonempty else "Array required")
            return []
        return value

    def text(self, value, where):
        return self.require(_text(value), "MISSING_TEXT", where, "Explicit nonempty value/reason required")

    def read(self, reference, where, *, json_value=True):
        try:
            if (not isinstance(reference, dict) or set(reference) != {"path", "sha256"}
                    or not _text(reference.get("path"))
                    or not isinstance(reference.get("sha256"), str)
                    or not re.fullmatch(r"[0-9a-fA-F]{64}", reference["sha256"])):
                raise ValueError("Reference requires exactly path and SHA-256")
            path = Path(reference["path"])
            if not path.is_absolute():
                path = self.root / path
            path = path.resolve()
            if not path.is_relative_to(self.root):
                raise ValueError("Evidence reference leaves the declared project evidence root")
            if not path.is_file():
                raise ValueError("Evidence file is missing")
            if json_value and path.stat().st_size > 5_000_000:
                raise ValueError("Structured evidence exceeds 5 MB")
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != reference["sha256"].lower():
                raise ValueError("Evidence hash differs from current bytes")
            if not json_value:
                return {"path": str(path), "sha256": digest.hexdigest()}
            value = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_object,
                               parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"nonfinite JSON value: {x}")))
            if not isinstance(value, dict):
                raise ValueError("Structured evidence root must be an object")
            return value
        except (OSError, ValueError, TypeError, RecursionError) as exc:
            self.need("EVIDENCE_UNAVAILABLE", where, str(exc))
            return None

    def refs(self, values, where):
        for index, reference in enumerate(self.rows(values, where)):
            self.read(reference, f"{where}[{index}]", json_value=False)

    def identity_check(self, data, where, *, run_id=None):
        for key, expected in self.identity.items():
            self.require(data.get(key) == expected, "STALE_IDENTITY", where, f"{key} differs from the frozen task")
        if run_id is not None:
            self.require(data.get("run_id") == run_id, "STALE_RUN", where, "Evidence belongs to another run")

    def streams(self, values, where):
        seen = set()
        for index, raw in enumerate(self.rows(values, where)):
            item = self.obj(raw, f"{where}[{index}]")
            tag = item.get("stream_id")
            self.require(_text(tag) and tag not in seen, "INVALID_STREAM_ID", where, "Unique stream ID required")
            if isinstance(tag, str):
                seen.add(tag)
            if self.require_buildable_plan and item.get("stream_kind") in ("heat", "work"):
                self.text(item.get("basis"), where + ".basis")
                self.read(item.get("source_ref"), where + ".source_ref", json_value=False)
                continue
            composition = self.obj(item.get("composition"), where + ".composition")
            self.require(bool(composition) and all(_text(k) and
                ((_text(v)) or (type(v) in (int, float) and math.isfinite(v) and v >= 0))
                for k, v in composition.items()), "EMPTY_OR_INVALID_COMPOSITION", where,
                "Component amounts/fractions or explicit sourced relations are required")
            self.text(item.get("basis"), where + ".basis")
            self.read(item.get("source_ref"), where + ".source_ref", json_value=False)

    def quantities(self, values, where):
        for index, raw in enumerate(self.rows(values, where)):
            item = self.obj(raw, f"{where}[{index}]")
            self.text(item.get("name"), where + ".name")
            value = item.get("value")
            self.require(_text(value) or (type(value) in (int, float) and math.isfinite(value)),
                         "QUANTITY_VALUE_REQUIRED", where, "A sourced value or relation is required")
            self.text(item.get("unit_or_basis"), where + ".unit_or_basis")
            self.read(item.get("source_ref"), where + ".source_ref", json_value=False)

    def thermodynamics(self, raw, where):
        thermo = self.obj(raw, where)
        for field in ("temperature_range", "pressure_range", "method", "applicability"):
            self.text(thermo.get(field), where + "." + field)
        for field in ("components", "phases"):
            self.require(all(_text(x) for x in self.rows(thermo.get(field), where + "." + field)),
                         "THERMODYNAMIC_BASIS_REQUIRED", where, "Actual components and phases required")
        self.refs(thermo.get("source_refs"), where + ".source_refs")
        return thermo

    def article_anchor(self, row, where, *numbers):
        excerpt = row.get("article_excerpt")
        offset = self.buildable_article_text.find(excerpt) if _text(excerpt) else -1
        if not self.require(offset >= 0, "PLAN_ARTICLE_EXCERPT", where,
                            "Keep the exact passage from this revision of the editable planning article"):
            return ""
        literals = re.findall(r"(?<![\d.])[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", excerpt)
        for number in numbers:
            if _finite(number):
                self.require(any(float(value) == number for value in literals), "PLAN_ARTICLE_VALUE", where,
                             f"Article passage must contain the declared numeric value {number}")
        return "L" + str(self.buildable_article_text.count("\n", 0, offset) + 1)

    def buildable_quantity(self, row, module, spec_id, default_node, *, setting=False):
        """Bind the reviewable value to the exact article, input basis and real node."""
        where = f"module.{module['id']}.{spec_id}"
        value, unit = row.get("value"), row.get("unit_or_basis")
        self.text(row.get("name"), where + ".name")
        self.text(unit, where + ".unit_or_basis")
        self.text(row.get("basis"), where + ".basis")
        self.read(row.get("source_ref"), where + ".source_ref", json_value=False)
        mode = row.get("mode")
        if setting:
            self.require(mode in ("fixed", "adjustable", "determined", "default", "derived"),
                         "PLAN_SETTING_MODE", where, "Declare fixed, adjustable, default, derived or determined")
        if mode == "determined":
            self.require(_text(value) and _text(row.get("basis")), "PLAN_GOVERNING_RELATION", where,
                         "State the governing relation and its resolved physical input basis")
            inputs = self.rows(row.get("depends_on"), where + ".depends_on")
            self.require(all(_text(x) for x in inputs), "PLAN_GOVERNING_RELATION", where,
                         "Name the upstream inputs determining this setting")
        else:
            self.require(_finite(value) or (setting and _text(value) and mode in ("fixed", "default", "derived")),
                         "PLAN_NOMINAL_REQUIRED", where, "Declare a reproducible first-pass value")
            if _text(value):
                unresolved = re.search(r"\b(?:TBD|TBA|unknown|unspecified)\b|待定|未确定|待补|"
                                       r"\d\s*(?:[-–—~～]|to\b|至)\s*[+-]?\d", value, re.I)
                unit_text = str(unit).strip().casefold()
                measurable = unit_text in (_STATE_UNITS["temperature"] | _STATE_UNITS["pressure"]) or _feed_rate_unit(unit)
                self.require(not unresolved and not measurable, "PLAN_NOMINAL_REQUIRED", where,
                             "Use a finite nominal quantity or a resolved named model choice")
        bounds = row.get("bounds")
        if mode == "adjustable" or bounds is not None:
            bounds = self.obj(bounds, where + ".bounds")
            low, high = bounds.get("lower"), bounds.get("upper")
            self.require(all(_finite(x) for x in (low, value, high)) and low <= value <= high,
                         "PLAN_OPERATING_BOUNDS", where, "Initial operating value must lie inside its stated bounds")
        node = row.get("node_id", default_node)
        owned = set(module.get("node_ids", [])) | {x.get("node_id") for x in module.get("auxiliaries", []) if isinstance(x, dict)}
        self.require(_text(node) and node in owned, "PLAN_SPEC_NODE", where, "Identify the physical node receiving this setting")
        locator = self.article_anchor(row, where, value, *(bounds.get(k) for k in ("lower", "upper")) if bounds else ())
        if _finite(value):
            unit_text = str(unit).strip().casefold()
            passage = str(row.get("article_excerpt", "")).casefold().replace("％", "%")
            aliases = {"percent": ("%", "百分之", "mol%", "wt%", "vol%"), "percentage": ("%", "百分之", "mol%", "wt%", "vol%"),
                       "%": ("%", "百分之", "mol%", "wt%", "vol%"),
                       "fraction": ("fraction", "分率", "份额", "mol/mol", "kg/kg"),
                       "degc": ("°c", "℃"), "°c": ("℃", "摄氏度"), "℃": ("°c", "摄氏度")}
            labels = [unit_text, *aliases.get(unit_text, ())]
            if unit_text.endswith("fraction"):
                labels.append(unit_text + "s")
            self.require(any(label and re.search(r"(?<![a-z])" + re.escape(label) + r"(?![a-z])", passage)
                             for label in labels), "PLAN_ARTICLE_UNIT", where,
                         "Quote the unit, fraction scale or table heading with the numeric setting")
        if _text(value):
            self.require(value in str(row.get("article_excerpt", "")), "PLAN_ARTICLE_VALUE", where,
                         "The operative setting or relation must occur in its quoted passage")
        specs = self.buildable_review_specs[module["id"]]
        specs[spec_id] = {"node_id": node, "article_locator": locator, "article_excerpt": row.get("article_excerpt"),
                          "value": value, "unit_or_basis": unit, "basis": row.get("basis")}
        context = {field: row[field] for field in ("kind", "outlet", "inlet", "component", "amount_basis", "comparison",
                    "reaction_id", "key_reactant", "pass_basis", "denominator", "basis_components") if field in row}
        if context:
            specs[spec_id]["design_context"] = context
        self.buildable_operating_rules[module["id"]][spec_id] = {
            "mode": row.get("mode", "fixed"), "comparison": row.get("comparison", "eq"),
            "bounds": bounds or {}, "kind": row.get("kind"),
            "design_target": spec_id.startswith(("targets.", "reaction.extent.", "separation.targets."))
            or row.get("comparison") in ("eq", "ge", "le")}
        rule = self.buildable_operating_rules[module["id"]][spec_id]
        if rule["design_target"] and _finite(value):
            self.require(rule["comparison"] in ("eq", "ge", "le"), "PLAN_MEASURABLE_TARGET", where,
                         "Specify a recognized comparison for this design requirement")
            if "acceptance_tolerance" in row:
                self.freeze_tolerance(row, rule, where)
                if "acceptance_width" in rule:
                    specs[spec_id]["acceptance_tolerance"] = {k: row["acceptance_tolerance"][k]
                        for k in ("kind", "value", "unit", "reference") if k in row["acceptance_tolerance"]}
            elif "acceptance_decimals" not in row:
                self.need("PLAN_TARGET_TOLERANCE_REQUIRED", where,
                          "Recover the existing source or engineering acceptance rule for this target and freeze its value, units and basis")
        if "acceptance_decimals" in row:
            decimals = row["acceptance_decimals"]
            clause = row.get("acceptance_excerpt")
            chinese_digits = ("零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二", "十三", "十四", "十五")
            precision_label = rf"(?:{decimals}|{chinese_digits[decimals]})" if type(decimals) is int and 0 <= decimals <= 15 else None
            valid = ("acceptance_tolerance" not in row and precision_label is not None and rule["comparison"] == "eq"
                     and row.get("kind") in ("recovery", "purity", "cut", "conversion", "model_determined")
                     and _finite(value) and _ratio(row) is not None and 0 <= _ratio(row) <= 1
                     and _text(clause) and clause.strip() == str(row.get("article_excerpt", "")).strip()
                     and not re.search(r"不|禁止|勿|假设|例如|仅供|暂定|待确认|[?？]|\b(?:no|not|never|if|example|proposed|hypothetical)\b", clause, re.I)
                     and _text(row.get("name")) and row["name"].casefold() in clause.casefold()
                     and _text(unit) and unit.casefold() in clause.casefold()
                     and any(float(n) == value for n in re.findall(r"(?<![a-zA-Z0-9_.])[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", clause))
                     and re.search(r"验收|\bacceptance\b", clause, re.I)
                     and re.search(r"四舍五入|\bhalf[ -]up\b", clause, re.I)
                     and re.search(rf"(?:小数点?后\s*{precision_label}\s*位|(?<![零一二三四五六七八九十\d]){precision_label}\s*位小数|(?<!\d){decimals}\s+decimal\s+places?\b)", clause, re.I))
            if valid:
                step = Decimal(1).scaleb(-decimals)
                nominal = Decimal(str(value))
                valid = nominal == nominal.quantize(step, rounding=ROUND_HALF_UP)
            if self.require(valid, "PLAN_ACCEPTANCE_PRECISION", where,
                            "Bind the named nominal ratio and its decimal reporting convention to the frozen article; keep inequality limits unrounded"):
                rule["acceptance_decimals"] = decimals
                specs[spec_id]["acceptance_decimals"] = decimals
        if bounds:
            for key in ("lower", "upper"):
                specs[f"{spec_id}.bounds.{key}"] = {**specs[spec_id], "value": bounds.get(key)}

    def freeze_tolerance(self, row, rule, where):
        tolerance = self.obj(row["acceptance_tolerance"], where + ".acceptance_tolerance")
        kind, value, unit = (tolerance.get(k) for k in ("kind", "value", "unit"))
        source = self.read(tolerance.get("source_ref"), where + ".acceptance_tolerance.source_ref", json_value=False)
        if not self.require(_finite(value) and value >= 0 and _text(unit), "PLAN_TARGET_TOLERANCE", where,
                            "Declare a finite nonnegative acceptance allowance and its unit"):
            return
        width = Decimal(str(value))
        ratio_scale = _ratio({"value": 1, "unit_or_basis": row.get("unit_or_basis")})
        points = unit.strip().casefold() in {"percentage_point", "percentage point", "percentage points", "百分点"}
        if kind == "relative":
            valid = unit == "%" and tolerance.get("reference") == "target" and row["value"] != 0
            width = abs(Decimal(str(row["value"]))) * width / 100
        else:
            valid = ("reference" not in tolerance and (points and ratio_scale is not None
                     or ratio_scale != 0.01 and unit == row.get("unit_or_basis")))
            if points and ratio_scale == 1:
                width /= 100
            if kind == "hard_limit":
                valid = valid and width == 0 and rule["comparison"] in ("ge", "le")
            else:
                valid = valid and kind == "absolute"
        if not self.require(valid and "acceptance_decimals" not in row, "PLAN_TARGET_TOLERANCE", where,
                            "Use one sourced absolute allowance, a percentage of a nonzero nominal target, or an unrounded zero-tolerance hard limit"):
            return
        basis = tolerance.get("basis")
        article = tolerance.get("article_excerpt", basis)
        if not source or not self.require(_text(basis) and _text(article) and article in self.buildable_article_text,
                                           "PLAN_TOLERANCE_EVIDENCE", where,
                                           "Locate the acceptance clause in the reviewed article and quote its source or engineering calculation"):
            return
        try:
            path = Path(source["path"])
            if path.suffix.casefold() == ".pdf":
                from tools.planning_research import _pdf_text
                page = tolerance.get("source_page")
                if type(page) is not int or page < 1:
                    raise ValueError("Identify the physical source_page in the PDF")
                content = _pdf_text(path, page)
            else:
                content = _article_text(path)
        except (ValueError, KeyError, OSError, BadZipFile, ElementTree.ParseError) as exc:
            self.need("PLAN_TOLERANCE_EVIDENCE", where, str(exc))
            return
        hard = (r"硬(?:性)?(?:限|上限|下限|边界)|不(?:得)?(?:超过|高于|低于)|严禁(?:超过|低于)|零容差|"
                r"hard[ -](?:(?:upper|lower)[ -])?(?:limit|minimum|maximum)|zero tolerance|must (?:not|never) (?:exceed|fall below)|maximum accepted|minimum accepted")
        rejected = (r"不允许|不(?:得)?(?:采用|使用|适用|接受)|禁止采用|不作为|并非|没有|未获|仅供|示例|举例|例如|待确认|假设|"
                    r"如果|若|除非|仅当|仅适用于|(?:只有|在).{0,40}(?:才|条件下)|(?:后|时)方可|[?？]|"
                    r"\b(?:example|hypothetical|proposed|if|unless|except|provided|assuming|pending|subject to approval|"
                    r"without|no|never|not|\w+n['’]t)\b")
        affirmative_limit = r"不(?:得)?(?:超过|高于|低于)|must (?:not|never) (?:exceed|fall below)"
        sentence_break = r"[。！？!\n]|(?<=\.)\s+"
        acceptance = r"±|\+/-|容差|允(?:许|收)|许可(?:偏差|误差)|验收|公差|可接受|tolerance|accept(?:ed|able|ance)?|allow(?:ed|able|ance)?"
        known_kind = {"conversion": r"\bconversion\b|转化率", "recovery": r"\brecovery\b|回收率",
                      "purity": r"\bpurity\b|纯度", "cut": r"\bcut\b|切分率"}
        scope_words = "|".join(known_kind.values())
        nominal_unit = re.escape(row["unit_or_basis"])
        if ratio_scale == 0.01:
            nominal_unit = r"(?:%|％|percent\b|百分比)"
        nominal_pattern = rf"(?<![\d.])([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*{nominal_unit}(?![a-zA-Z])"
        location_pattern = r"(?:(?:at|to)\s+(?:(?:the|outlet|stream)\s+)*|出口\s*|在\s*)(?-i:([A-Z][A-Z\d_-]*))\b"
        name = str(row.get("name", "")).strip()
        target_name = r"[\s-]+".join(re.escape(part) for part in re.split(r"[\s-]+", name))
        if name and name[-1].isascii() and name[-1].isalnum():
            target_name += r"\b"
        target_head = rf"^(?:for\s+(?:the\s+)?|the\s+|对于?\s*|仅对\s*|only\s+)?(?:allowable\s+)?{target_name}"
        other_scope = (rf"\b(?:and|or|but|while|whereas|only|instead|however|temperature|pressure|capacity|flow|yield)\b|"
                       rf"而|但是|另有|另一个|仅限|其余|温度|压力|流量|产量|产率|{scope_words}")
        named_kinds = {label for label, pattern in known_kind.items() if re.search(pattern, name, re.I)}
        scope_kind = row.get("kind")
        if scope_kind == "model_determined" and _text(row.get("reaction_id")):
            scope_kind = "conversion"
        if "kind" not in row and len(named_kinds) == 1 and not re.search(r"\b(?:and|or|not|versus|vs)\b|或|非", name, re.I):
            scope_kind = next(iter(named_kinds))
        # Earlier SEP records use “cut” as an outlet label; the component and ratio basis distinguish the metric there.
        component_cut = (named_kinds == {"cut"} and _text(row.get("component")) and _text(row.get("outlet"))
                         and (scope_kind == "recovery" or scope_kind == "purity" and row.get("amount_basis") in ("mole", "mass")))
        if len(named_kinds) > 1 or (scope_kind in known_kind and named_kinds and scope_kind not in named_kinds and not component_cut):
            self.need("PLAN_TOLERANCE_EVIDENCE", where, "Resolve conflicting metric classes in the target name and structured kind")
            return

        def clauses(passage):
            boundary = rf"[。；;!?！？\n]|(?<=\.)\s+|[,，]\s*(?=(?:\w+[ -]|[\u3400-\u9fff]{{1,12}})(?:{scope_words}))"
            return [part.strip() for part in re.split(boundary, passage) if part.strip()]

        def names_nominal(clause):
            return any(Decimal(n) == Decimal(str(row["value"])) for n in re.findall(nominal_pattern, clause, re.I))

        def outlet_matches(clause):
            outlet = row.get("outlet")
            expected = {outlet} if _text(outlet) else set(re.findall(location_pattern, str(row.get("article_excerpt", "")), re.I))
            observed = set(re.findall(location_pattern, clause, re.I))
            return not observed or not expected or observed == expected

        def scoped_allowance(clause):
            if kind != "hard_limit" and scope_kind in known_kind:
                # A written blanket rule can apply to each declared member of its metric classes.
                shared = re.search(rf"\b(?:each|all)\s+((?:{scope_words})(?:\s*(?:,|and\b|or\b)\s*(?:{scope_words}))*)"
                                   rf"(?:\s+(?:targets?|metrics?|requirements?|specifications?))?(?=\s*(?:is\b|are\b|have\b|has\b|:|=|±|[\d.]))|"
                                   rf"(?:每项|所有|各项)\s*((?:{scope_words})(?:\s*[、和及或]\s*(?:{scope_words}))*)"
                                   rf"\s*(?:指标|目标|规定|规格)?(?=\s*(?:的|按|为|:|：|±|[\d.]))", clause, re.I)
                if shared and re.search(known_kind[scope_kind], shared[1] or shared[2], re.I):
                    return not re.search(r"\b(?:only|other)\b|仅限|其余|而|但", clause, re.I)
            found = re.match(target_head, clause, re.I) if name else None
            if not found:
                # Retain a pressure/temperature target whose structured basis states the exact measurement location.
                location = re.fullmatch(r"(pressure|temperature)\s+at\s+([\w-]+)", str(row.get("basis", "")), re.I)
                return bool(kind == "hard_limit" and location and location[1].casefold() in name.casefold() and re.match(
                    rf"^at\s+{re.escape(location[2])}\s+the\s+(?:minimum|maximum)\s+accepted\s+{location[1]}\b", clause, re.I))
            suffix = clause[found.end():]
            if re.search(other_scope, suffix, re.I):
                return False
            # Require a direct predicate about this subject rather than a nearby allowance about another metric.
            suffix = re.sub(rf"^\s*{location_pattern}\s*", "", suffix, count=1, flags=re.I)
            prefix = (r"\s*(?:['’]s|的)?\s*(?:[,:：，]\s*)?(?:(?:is|has|must be|shall be|allows?|accepts?)\s+|取|为|按|采用|接受)?\s*"
                      r"(?:(?:a|an|the|for acceptance)\s+|验收时)?\s*")
            if kind != "hard_limit":
                declared_nominal = re.match(rf"\s*(?:(?:nominal(?:ly)?|target|is)\s+|名义(?:值)?(?:为)?|目标(?:为)?|为)?"
                                            rf"{nominal_pattern}\s*[,，:：]?", suffix, re.I)
                if declared_nominal and Decimal(declared_nominal[1]) == Decimal(str(row["value"])):
                    suffix = suffix[declared_nominal.end():]
            return bool(re.match(prefix + rf"(?:{acceptance}|(?:(?:engineering|absolute|relative)\s+)?(?:deviation|allowance|tolerance)\b|"
                                 rf"绝对偏差|相对偏差|{hard}|[<>≤≥]|at (?:least|most)\b)", suffix, re.I))
        if kind == "hard_limit":
            def supports_part(clause):
                lower = r"≥|>=|不(?:得)?低于|至少|下限|minimum|lower limit|at least|must (?:not|never) fall below"
                upper = r"≤|<=|不(?:得)?(?:高于|超过)|至多|上限|maximum|upper limit|at most|must (?:not|never) exceed"
                limit_marker, opposite = (lower, upper) if rule["comparison"] == "ge" else (upper, lower)
                if re.search(opposite, clause, re.I):
                    return False
                return names_nominal(clause) and bool(re.search(limit_marker, clause, re.I))
        else:
            units = (r"(?:percentage[_ ]points?|百分点|个?百分[点點])" if points else
                     r"(?:%|％|percent\b)" if kind == "relative" else re.escape(unit))
            pairs = rf"(?<![\d.eE])([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*{units}(?![a-zA-Z])"
            def supports_part(clause):
                if kind == "relative" and not re.search(r"(?:目标|标称|名义)(?:数?值)?的|相对(?:于)?(?:目标|标称|名义)|以(?:目标|标称|名义)(?:数?值)?为基准|"
                                                        r"(?:of|relative to|based on) (?:the )?(?:absolute )?(?:nominal|target)", clause, re.I):
                    return False
                return bool(re.search(acceptance, clause, re.I)) and any(Decimal(n) == Decimal(str(value)) for n in re.findall(pairs, clause, re.I))
            # A distinct downstream constraint in the same paragraph cannot turn this nominal target into a hard limit.
            target_parts = clauses(str(row.get("article_excerpt", "")))
            current_parts = [p for p in target_parts if len(target_parts) == 1 or str(row.get("name", "")).casefold() in p.casefold()]
            allowance_parts = [p for passage in (basis, article) for p in clauses(passage) if supports_part(p)]
            def nominal_hard_limit(part):
                limit = re.search(hard, part, re.I)
                if not (limit and names_nominal(part)):
                    return False
                # “Deviation must not exceed X” caps the allowance, even in a sentence listing the nominal target first.
                return (not re.fullmatch(affirmative_limit, limit[0], re.I)
                        or names_nominal(part[limit.end():]))
            if width and any(nominal_hard_limit(p) for p in current_parts + [p for p in allowance_parts if scoped_allowance(p)]):
                self.need("PLAN_TARGET_TOLERANCE", where, "Do not widen a sourced hard limit with an engineering allowance")
                return
        def supports(passage, quoted):
            quoted = " ".join(quoted.split())
            for sentence in re.split(sentence_break, passage):
                if not sentence.strip() or " ".join(sentence.strip().rstrip(".").split()) not in quoted:
                    continue
                assess = re.sub(affirmative_limit, "", sentence, flags=re.I)
                if re.search(rejected, assess, re.I):
                    continue
                previous = ""
                for part in clauses(sentence):
                    continuation = (kind != "hard_limit" and name and re.match(target_head, previous, re.I)
                                    and names_nominal(previous) and outlet_matches(previous)
                                    and re.match(rf"^(?:{acceptance}|for acceptance)", part, re.I)
                                    and not re.search(other_scope, part, re.I))
                    if supports_part(part) and outlet_matches(part) and (scoped_allowance(part) or continuation):
                        return True
                    previous = part
            return False
        if self.require(" ".join(basis.split()) in " ".join(content.split())
                        and supports(content, basis) and supports(self.buildable_article_text, article),
                        "PLAN_TOLERANCE_EVIDENCE", where,
                        "Match the acceptance magnitude and unit or explicit hard-limit clause in both frozen passages"):
            rule["acceptance_width"] = width

    def buildable_conditions(self, section, module, role, node):
        covered = set()
        aggregate_cut = self.aggregate_sep(module)
        conditions = section.get("conditions", [] if aggregate_cut else None)
        for index, raw in enumerate(self.rows(conditions, f"module.{module['id']}.{role}.conditions", nonempty=not aggregate_cut)):
            spec_id = f"{role}.conditions.{index}"
            where = f"module.{module['id']}.{spec_id}"
            row = self.obj(raw, where)
            self.buildable_quantity(row, module, spec_id, node, setting=True)
            name = row.get("name")
            if name in _STATE_UNITS:
                covered.add(name)
                self.require(_state_unit_supported(name, row),
                             "PLAN_CONDITION_UNIT", where, f"Specify an explicit {name} unit")
                self.require(row.get("mode") == "determined" or _finite(row.get("value")),
                             "PLAN_CONDITION_START", where, f"Give a numeric starting {name} or a determined relation")
        if not aggregate_cut:
            self.require(covered == set(_STATE_UNITS), "PLAN_OPERATING_CONDITIONS", f"module.{module['id']}.{role}",
                         "Resolve operating temperature and pressure as settings or evidence-defined constraints")

    @staticmethod
    def aggregate_sep(module):
        first = module.get("first_model")
        return (module.get("role") == "separation" and isinstance(first, dict)
                and str(first.get("block_type", "")).casefold() in ("sep", "sep2"))

    def buildable_reaction(self, module, section, node):
        where = "module." + module["id"] + ".reaction"
        network = {}
        needs_hydrogen = bool(re.search(r"\b(?:hydrogenat\w*|hydrocrack\w*|hydrotreat\w*)\b|加氢|氢解",
                                        str(module.get("physical_service", "")), re.I))
        for index, item in enumerate(self.rows(section.get("network"), where + ".network")):
            name = f"{where}.network.{index}"
            row = self.obj(item, name)
            key, equation = row.get("id"), row.get("equation")
            self.require(_text(key) and key not in network, "PLAN_REACTION_ID", name, "Give each source reaction or lump a unique ID")
            terms = re.split(r"\s*(?:<=>|<->|=>|->|→|⇌|↔|=)\s*", str(equation))
            self.require(len(terms) == 2 and all(_text(x) for x in terms), "PLAN_REACTION_MAP", name,
                         "Identify the reactants and products in a reaction equation or explicit lumped mapping")
            if _text(key):
                network[key] = terms[0]
            needs_hydrogen |= bool(re.search(r"(?:^|[+\s(])(?:\d+(?:\.\d+)?\s*)?(?:H[2₂]|hydrogen)(?![A-Za-z0-9])|氢气",
                                             terms[0], re.I))
            self.read(row.get("source_ref"), name + ".source_ref", json_value=False)
            self.article_anchor(row, name)
            self.require(_text(equation) and equation in str(row.get("article_excerpt", "")), "PLAN_ARTICLE_REACTION", name,
                         "The quoted article passage must state the source-based reaction or lumped map")
        if needs_hydrogen:
            row = self.obj(section.get("hydrogen_basis"), where + ".hydrogen_basis")
            self.buildable_quantity(row, module, "reaction.hydrogen_basis", node, setting=True)
        covered = set()
        for index, item in enumerate(self.rows(section.get("extent"), where + ".extent")):
            name = f"{where}.extent.{index}"
            row = self.obj(item, name)
            self.buildable_quantity(row, module, f"reaction.extent.{index}", node)
            key, reactant = row.get("reaction_id"), row.get("key_reactant")
            if self.require(_text(key) and key in network, "PLAN_REACTION_EXTENT_MAP", name, "Name the reaction or lump being quantified"):
                covered.add(key)
                self.require(_text(reactant) and reactant in network[key], "PLAN_REACTION_DENOMINATOR", name,
                             "Name the key reactant on the inlet side of this reaction or lump")
            self.text(row.get("denominator"), name + ".denominator")
            if _text(reactant):
                self.require(reactant in str(row.get("article_excerpt", "")), "PLAN_ARTICLE_REACTANT", name,
                             "Quote the reactant basis of the conversion or yield")
            self.require(row.get("pass_basis") in ("per_pass", "overall"), "PLAN_CONVERSION_BASIS", name,
                         "Identify per-pass or cumulative conversion/yield basis")
            kind = row.get("kind")
            self.require(kind in ("conversion", "yield", "model_determined"), "PLAN_REACTION_EXTENT", name,
                         "Declare conversion, calibrated yield, or a design conversion target for a governing model")
            ratio = _ratio(row)
            self.require(ratio is not None and ratio >= 0 and (kind == "yield" or ratio <= 1),
                         "PLAN_FRACTION_UNIT_OR_RANGE", name, "Give a nominal value with explicit percent/fraction or yield basis")
            if kind == "model_determined":
                self.text(row.get("governing_model"), name + ".governing_model")
        self.require(set(network) <= covered, "PLAN_REACTION_UNSPECIFIED", where, "Resolve the nominal basis for every reaction or lump")

    def buildable_separation(self, module, section, node):
        where = "module." + module["id"] + ".separation"
        self.text(section.get("initial_method"), where + ".initial_method")
        streams = [row.get("stream_id") for row in module.get("outlets", []) if isinstance(row, dict)]
        components = sorted({name for row in module.get("inlets", []) if isinstance(row, dict)
                             for name in row.get("composition", {})})
        self.require(len(streams) >= 2, "PLAN_PRODUCT_DESTINATIONS", where, "Identify each distinct outlet stream")
        variables = [(s, c) for s in streams for c in components]
        # Unknowns are component outlet amounts. Each feed component supplies one balance.
        matrix = [[int(c == target) for _, c in variables] for target in components]
        recovery_sum, mixture_bases = {}, set()
        for index, item in enumerate(self.rows(section.get("targets"), where + ".targets")):
            name = f"{where}.targets.{index}"
            row = self.obj(item, name)
            self.buildable_quantity(row, module, f"separation.targets.{index}", node)
            outlet, component, kind = row.get("outlet"), row.get("component"), row.get("kind")
            self.require(outlet in streams, "PLAN_PRODUCT_DESTINATION", name, "Name the outlet receiving the product or cut")
            passage = str(row.get("article_excerpt", ""))
            self.require(_text(outlet) and outlet in passage and (kind == "cut" or _text(component) and component in passage),
                         "PLAN_ARTICLE_DESTINATION", name, "Locate the named product destination and component in the article")
            self.require(row.get("comparison") in ("eq", "ge", "le"), "PLAN_MEASURABLE_TARGET", name, "Declare eq/ge/le acceptance")
            ratio = _ratio(row)
            valid = self.require(ratio is not None and 0 <= ratio <= 1, "PLAN_FRACTION_UNIT_OR_RANGE", name,
                                 "State a recoverable numeric split, purity or cut on its explicit scale")
            if not self.require(kind in ("purity", "recovery", "cut") and (kind == "cut" or component in components),
                                "PLAN_PRODUCT_COMPONENT", name, "Name the inlet component for component recovery or product purity"):
                continue
            if not valid or outlet not in streams:
                continue
            if kind in ("purity", "cut"):
                amount_basis = row.get("amount_basis")
                unit = str(row.get("unit_or_basis", "")).strip().casefold()
                unit_basis = {"mol%": "mole", "mole fraction": "mole", "mol/mol": "mole", "摩尔分率": "mole",
                              "wt%": "mass", "mass fraction": "mass", "kg/kg": "mass", "质量分率": "mass",
                              "vol%": "volume", "volume fraction": "volume"}.get(unit)
                self.require(amount_basis in ("mole", "mass") and unit_basis in (None, amount_basis),
                             "PLAN_MIXTURE_BASIS", name, "Match the mixture ratio units to the declared mole or mass basis")
                mixture_bases.add(str(amount_basis))
            if kind == "recovery":
                matrix.append([int(s == outlet and c == component) for s, c in variables])
                pairs = recovery_sum.setdefault(component, {})
                self.require(outlet not in pairs, "PLAN_DUPLICATE_RECOVERY", name, "Use one nominal split per component and destination")
                pairs[outlet] = _recovery_interval(row, self.buildable_operating_rules[module["id"]][f"separation.targets.{index}"])
            elif kind == "cut":
                matrix.append([int(s == outlet) for s, c in variables])
            else:
                matrix.append([(int(c == component) - ratio) if s == outlet else 0 for s, c in variables])
        for component, fractions in recovery_sum.items():
            minimum = sum(low for low, high, upper_open in fractions.values())
            maximum = len(streams) - len(fractions) + sum(high for low, high, upper_open in fractions.values())
            self.require(minimum <= 1 and (maximum > 1 or maximum == 1 and not any(open_end for _, _, open_end in fractions.values())),
                         "PLAN_COMPONENT_RECOVERY_BALANCE", where, f"The recovery limits for {component} must allow a complete allocation")
        model = section.get("governing_model")
        if model is not None:
            row = self.obj(model, where + ".governing_model")
            self.text(row.get("relation"), where + ".governing_model.relation")
            self.refs(row.get("source_refs"), where + ".governing_model.source_refs")
            self.article_anchor(row, where + ".governing_model")
            self.require(_text(row.get("relation")) and row["relation"] in str(row.get("article_excerpt", "")),
                         "PLAN_ARTICLE_MODEL", where, "Locate the governing separation relation in the article")
        fixed_splits = False
        if self.aggregate_sep(module):
            native = [self.at_path(module, row["spec_id"]) if "spec_id" in row else row
                      for row in module["first_model"].get("inputs", []) if isinstance(row, dict)]
            fixed_splits = bool(components) and all(_outlet_fractions(native, c, set(streams)) for c in components)
        if (model is None or self.aggregate_sep(module)) and not fixed_splits:
            self.require(len(mixture_bases) <= 1 and variables and _cut_rank(matrix) == len(variables),
                         "PLAN_SEPARATION_UNDERSPECIFIED", where,
                         "Independent nominal split/cut/purity specifications and balances must determine every outlet, or cite the model that supplies the remaining constraints")

    def buildable_plan(self, gate):
        from tools.planning_research import check_module_research

        self.buildable_article_ref = gate.get("planning_article_ref")
        self.buildable_article_text = ""
        self.buildable_review_specs = {tag: {} for tag in self.modules}
        self.buildable_operating_rules = {tag: {} for tag in self.modules}
        info = self.read(self.buildable_article_ref, "source.planning_article_ref", json_value=False)
        if info:
            try:
                self.buildable_article_text = _article_text(Path(info["path"]))
            except (ValueError, OSError, KeyError, BadZipFile, ElementTree.ParseError) as exc:
                self.need("PLAN_ARTICLE_UNREADABLE", "source.planning_article_ref", str(exc))
        research_rows = []
        for tag, module in self.modules.items():
            where = "module." + tag
            thermo = self.obj(module.get("thermodynamics"), where + ".thermodynamics")
            self.require(thermo.get("selection_status") in ("supported", "uncertain", "conflict", "outside_range"),
                         "PLAN_PROPERTY_SELECTION", where + ".thermodynamics",
                         "Record whether the chosen property method covers the actual mixture, phase and operating range")
            if thermo.get("selection_status") == "supported":
                from tools.planning_property_lookup import check_property_method_basis
                check_property_method_basis(self, module, _article_text)
            if thermo.get("selection_status") in ("uncertain", "conflict", "outside_range"):
                self.need("PLAN_PROPERTY_REVIEW_OPEN", where + ".thermodynamics",
                          "Adjudicate the method against the registered thermodynamics evidence and the case operating window")
            service = module.get("physical_service")
            self.require(_text(service) and service.strip().casefold() not in {"sep", "rstoic", "separator", "reactor", "反应器", "分离器"},
                         "PLAN_PHYSICAL_SERVICE", where, "State what the real process unit does, including for placeholders")
            self.article_anchor(module, where)
            self.require(_text(service) and service in str(module.get("article_excerpt", "")), "PLAN_ARTICLE_SERVICE", where,
                         "Locate the physical service in the current article")
            nodes = module.get("node_ids", [])
            passage = str(module.get("article_excerpt", ""))
            for side in ("inlets", "outlets"):
                for stream in module.get(side, []):
                    if isinstance(stream, dict):
                        if "article_excerpt" in stream:
                            self.article_anchor(stream, where + "." + side)
                        identifier = stream.get("stream_id")
                        self.require(_text(identifier) and identifier in str(stream.get("article_excerpt", passage)),
                                     "PLAN_ARTICLE_STREAM", where + "." + side,
                                     f"Identify stream {identifier} at the unit interface in the article")
            node = nodes[0] if len(nodes) == 1 else None
            for index, target in enumerate(module.get("targets", [])):
                if isinstance(target, dict) and (_finite(target.get("value")) or target.get("comparison") in ("eq", "ge", "le")):
                    self.buildable_quantity(target, module, f"targets.{index}", node)
            role = module.get("role")
            if role in ("reaction", "separation"):
                section = self.obj(module.get(role), where + "." + role)
                self.buildable_conditions(section, module, role, node)
                if role == "reaction":
                    self.buildable_reaction(module, section, node)
                else:
                    self.buildable_separation(module, section, node)
                research_rows.append(check_module_research(self, module, section, _article_text))
            self.buildable_first_models(module)
        self.summary["planning_research"] = {
            "modules": research_rows,
            "unresolved_module_ids": [row["module_id"] for row in research_rows if row["status"] == "unresolved"],
            "provisional_module_ids": [row["module_id"] for row in research_rows if row["status"] == "provisional"],
        }

    def buildable_interfaces(self, data):
        """Locate feeds from actual external-to-process edges, preserving internal solved streams."""
        owners = {}
        for tag, module in self.modules.items():
            nodes = set(module.get("node_ids", [])) | {r.get("node_id") for r in module.get("auxiliaries", []) if isinstance(r, dict)}
            for node in nodes:
                self.require(node not in owners, "PLAN_NODE_OWNERSHIP", "module." + tag, f"Ambiguous physical-node owner for {node}")
                owners[node] = tag
        external = {n.get("id") for n in data.get("nodes", []) if isinstance(n, dict) and n.get("kind") == "external"}
        directions = {(tag, side): set() for tag in self.modules for side in ("inlets", "outlets")}
        for edge in data.get("streams", []):
            if not isinstance(edge, dict):
                continue
            source, dest, stream_id = edge.get("from"), edge.get("to"), edge.get("id")
            source_owner, dest_owner = owners.get(source), owners.get(dest)
            if source_owner and dest_owner and source_owner != dest_owner:
                source_stream = next((r for r in self.modules[source_owner].get("outlets", [])
                                      if isinstance(r, dict) and r.get("stream_id") == stream_id), None)
                dest_stream = next((r for r in self.modules[dest_owner].get("inlets", [])
                                    if isinstance(r, dict) and r.get("stream_id") == stream_id), None)
                produced, received = _declared_material(source_stream), _declared_material(dest_stream)
                if produced and received and produced[:2] == received[:2]:
                    differences = _composition_differences(produced[2], received[2])
                    self.require(not differences, "PLAN_INTERFACE_COMPOSITION_MISMATCH", "stream." + str(stream_id),
                                 {"upstream_module": source_owner, "downstream_module": dest_owner,
                                  "basis": produced[0], "quantity": produced[1], "upstream_and_downstream": differences})
            for node, peer, side in ((source, dest, "outlets"), (dest, source, "inlets")):
                tag = owners.get(node)
                if tag is None or owners.get(peer) == tag:
                    continue
                directions[tag, side].add(stream_id)
                if side == "inlets" and peer in external:
                    module = self.modules[tag]
                    for idx, inlet in enumerate(module.get(side, [])):
                        if isinstance(inlet, dict) and inlet.get("stream_id") == stream_id:
                            self.buildable_feed(module, inlet, idx, node)
        for (tag, side), streams in directions.items():
            declared = {r.get("stream_id") for r in self.modules[tag].get(side, []) if isinstance(r, dict)}
            self.require(declared == streams, "PLAN_INTERFACE_TOPOLOGY", "module." + tag + "." + side,
                         f"Match the owned module boundary to the handoff streams {sorted(map(str, streams))}")

    def buildable_feed(self, module, stream, index, node):
        prefix = f"inlets.{index}"
        where = f"module.{module['id']}.{prefix}"
        state = self.obj(stream.get("feed_state"), where + ".feed_state")
        kind = stream.get("stream_kind", "material")
        fields = ("duty",) if kind in ("heat", "work") else ("flow", "temperature", "pressure")
        for field in fields:
            row = self.obj(state.get(field), where + ".feed_state." + field)
            self.buildable_quantity(row, module, f"{prefix}.feed_state.{field}", node, setting=True)
            self.require(row.get("mode") == "determined" or _finite(row.get("value")),
                         "PLAN_FEED_START", where + "." + field, "Supply a finite inlet state or a resolved governing relation")
            if field == "flow":
                self.require(_feed_rate_unit(row.get("unit_or_basis")) and (not _finite(row.get("value")) or row["value"] >= 0),
                             "PLAN_FEED_RATE_BASIS", where, "Supply a nonnegative rate per stated time basis")
            if field in _STATE_UNITS:
                self.require(_state_unit_supported(field, row),
                             "PLAN_CONDITION_UNIT", where + "." + field, f"Use an explicit {field} unit")
        if kind in ("heat", "work"):
            return
        self.check_direct_reactor_pressure(module, state.get("pressure"), node, where)
        composition = self.obj(stream.get("composition"), where + ".composition")
        basis = str(stream.get("basis", ""))
        self.require(bool(composition) and bool(re.search(r"mol|mass|kg|lb|kmol|volume|vol|m³|m3|摩尔|质量|体积", basis, re.I)),
                     "PLAN_FEED_COMPOSITION_BASIS", where, "Specify the amount or mass/molar/volumetric composition basis")
        for component, value in composition.items():
            row = {"name": component, "value": value, "unit_or_basis": basis, "basis": basis,
                   "mode": "fixed" if _finite(value) else "determined",
                   "depends_on": stream.get("composition_depends_on"), "source_ref": stream.get("source_ref"),
                   "article_excerpt": stream.get("article_excerpt")}
            self.buildable_quantity(row, module, f"{prefix}.composition.{component}", node, setting=True)
        if composition and all(_finite(v) for v in composition.values()):
            values = list(composition.values())
            total = 100 if re.search("%|％|percent|百分", basis, re.I) else 1 if re.search("fraction|分率|分数", basis, re.I) else None
            self.require(min(values) >= 0 and (total is None or math.isclose(sum(values), total, rel_tol=1e-6)),
                         "PLAN_FEED_COMPOSITION_SUM", where, "Explicit component fractions must close on their stated basis")

    def check_direct_reactor_pressure(self, module, supply, node, where):
        """Check an external feed connected straight to one flow-through reactor."""
        first = module.get("first_model")
        if (module.get("role") != "reaction" or module.get("node_ids") != [node]
                or not isinstance(first, dict) or str(first.get("block_type", "")).upper() not in ("RSTOIC", "RPLUG")):
            return
        entry = _pressure_reading(supply)
        if not entry or entry[0] is None:
            return
        auxiliaries = module.get("auxiliary_requirements", {})
        if not isinstance(auxiliaries, dict) or not all(
                isinstance(auxiliaries.get(k), dict) and auxiliaries[k].get("state") == "not_required"
                for k in ("compression", "pumping", "pressure_control")):
            return
        for condition in (module.get("reaction") or {}).get("conditions", []):
            if not isinstance(condition, dict) or str(condition.get("name", "")).lower() != "pressure":
                continue
            required = _pressure_reading(condition)
            if required and required[0] is not None and required[1] == entry[1]:
                self.require(required[0] <= entry[0] or math.isclose(required[0], entry[0], rel_tol=1e-12),
                             "PLAN_FEED_PRESSURE_SHORTFALL", where,
                             "A direct feed is below the reactor operating pressure; resolve the supply condition or specify the pressure service")

    def buildable_first_models(self, module):
        where = "module." + module["id"]
        nodes = module.get("node_ids", [])
        units = [(node, "first_model", module.get("first_model")) for node in nodes] if len(nodes) == 1 else [
            (node, f"first_model.{node}", (module.get("first_model") or {}).get(node)) for node in nodes]
        for i, aux in enumerate(module.get("auxiliaries", [])):
            if isinstance(aux, dict):
                units.append((aux.get("node_id"), f"auxiliaries.{i}.first_model", aux.get("first_model")))
        for node, prefix, item in units:
            location = f"{where}.{prefix}"
            model = self.obj(item, location)
            block = model.get("block_type")
            self.text(block, location + ".block_type")
            self.read(model.get("source_ref"), location + ".source_ref", json_value=False)
            if isinstance(block, str) and block.casefold() in ("rstoic", "sep", "sep2"):
                role = "reaction" if block.casefold() == "rstoic" else "separation"
                self.require(module.get("role") == role, "PLAN_PLACEHOLDER_SERVICE", location,
                             f"The {block} placeholder requires a physical {role} specification")
                if role == "reaction":
                    extents = (module.get("reaction") or {}).get("extent", [])
                    required_reactions = {r.get("id") for r in (module.get("reaction") or {}).get("network", []) if isinstance(r, dict)}
                    conversion_reactions = {r.get("reaction_id") for r in extents if isinstance(r, dict)
                                            and r.get("kind") == "conversion" and r.get("pass_basis") == "per_pass"}
                    self.require(required_reactions and required_reactions <= conversion_reactions,
                                 "PLAN_FIXED_CONVERSION", location, "Translate each nominal extent to an inlet/per-pass basis for RStoic")
            required = self.rows(model.get("required_inputs"), location + ".required_inputs", nonempty=False)
            if not required:
                self.text(model.get("no_input_basis"), location + ".no_input_basis")
                self.require(module.get("role") not in ("reaction", "separation") or node not in nodes,
                             "PLAN_MODEL_INPUT_COVERAGE", location,
                             "Supply the native inputs of the selected first-version reactor/separator")
            seen, native_inputs = [], []
            for i, raw in enumerate(self.rows(model.get("inputs"), location + ".inputs", nonempty=False)):
                spec_id = f"{prefix}.inputs.{i}"
                row = self.obj(raw, where + "." + spec_id)
                seen.append(row.get("name"))
                if "spec_id" in row:
                    target = self.buildable_review_specs[module["id"]].get(str(row["spec_id"]), {})
                    self.require(target.get("node_id") == node and _text(node), "PLAN_MODEL_INPUT_BINDING", location,
                                 "Reference a declared operative setting of this physical node")
                    native_inputs.append(self.at_path(module, row["spec_id"]) or {})
                else:
                    self.buildable_quantity(row, module, spec_id, node, setting=True)
                    native_inputs.append(row)
            self.require(all(_text(x) for x in required + seen) and len(required) == len(set(map(str, required)))
                         and sorted(map(str, required)) == sorted(map(str, seen)), "PLAN_MODEL_INPUT_COVERAGE", location,
                         "Resolve each required native input of this sourced first-version configuration exactly once")
            if str(block).casefold() == "rstoic":
                conversions = [r for r in native_inputs if isinstance(r, dict)
                               and r.get("kind") == "conversion" and r.get("pass_basis") == "per_pass"]
                consumed = {r.get("reaction_id"): r for r in conversions}
                self.require(required_reactions == consumed.keys() and len(consumed) == len(conversions),
                             "PLAN_MODEL_INPUT_BINDING", location,
                             "Bind each nominal per-pass conversion to the first RStoic model")
                self.buildable_conversion_balance(module, consumed, location)
            if str(block).casefold() in ("sep", "sep2"):
                outlets = {r.get("stream_id") for r in module.get("outlets", []) if isinstance(r, dict)}
                components = {c for r in module.get("inlets", []) if isinstance(r, dict) for c in r.get("composition", {})}
                if str(block).casefold() == "sep2":
                    self.require(len(outlets) == 2, "PLAN_NATIVE_SEP_OUTLET_COUNT", location,
                                 "SEP2 requires two outlet streams; the case boundary must match the chosen native block")
                self.require(all(r.get("component") in components and r.get("outlet") in outlets for r in native_inputs
                                 if isinstance(r, dict) and r.get("kind") == "recovery"),
                             "PLAN_NATIVE_SEP_SPLITS", location, "Every native split must name an inlet component and a real outlet")
                splits = {component: _outlet_fractions(native_inputs, component, outlets) for component in components}
                for component, fractions in splits.items():
                    self.require(fractions is not None, "PLAN_NATIVE_SEP_SPLITS", location,
                                 f"Supply independent, nonnegative nominal native splits that close all outlets for {component}")
                if splits and all(splits.values()):
                    self.buildable_split_targets(module, splits, outlets)

    def buildable_conversion_balance(self, module, consumed, location):
        reaction = module.get("reaction") or {}
        extents = [r for r in reaction.get("extent", []) if isinstance(r, dict)
                   and r.get("kind") == "conversion" and r.get("pass_basis") == "per_pass"]
        by_reaction = {}
        for row in extents:
            reaction_id = row.get("reaction_id")
            self.require(reaction_id not in by_reaction, "PLAN_DUPLICATE_CONVERSION", location,
                         f"A single first RStoic setting must be defined for {reaction_id}")
            by_reaction[reaction_id] = row
        used = {}
        product_sides = [re.split(r"\s*(?:<=>|<->|=>|->|→|⇌|↔|=)\s*", str(r.get("equation")))[-1]
                         for r in reaction.get("network", []) if isinstance(r, dict)]
        for reaction_id, row in consumed.items():
            frozen = by_reaction.get(reaction_id, {})
            reactant, denominator, fraction = row.get("key_reactant"), row.get("denominator"), _ratio(row)
            if not self.require(fraction is not None and 0 <= fraction <= 1 and _ratio(frozen) == fraction
                                and _text(reactant) and reactant == frozen.get("key_reactant")
                                and _text(denominator) and denominator == frozen.get("denominator"),
                                "PLAN_MODEL_INPUT_BINDING", location,
                                f"The native conversion of {reaction_id} must match the frozen value, reactant and denominator"):
                continue
            original = re.search(r"\b(?:inlet|entering|original)\b|入口|进料|原始", denominator, re.I)
            sequential = re.search(r"\b(?:remaining|residual|after)\b|剩余|之后|之后的", denominator, re.I)
            produces_reactant = any(reactant in side for side in product_sides)
            if original and not sequential and not produces_reactant:
                key = reactant, " ".join(denominator.casefold().split())
                used[key] = used.get(key, 0) + fraction
        for (reactant, denominator), fraction in used.items():
            self.require(fraction <= 1 + 1e-9, "PLAN_REACTANT_OVERCONSUMED", location,
                         f"Conversions consume {fraction:.6g} of {reactant} on the same inlet denominator ({denominator})")

    def buildable_split_targets(self, module, splits, outlets):
        feed = _known_feed(module.get("inlets", []))
        if feed is None:
            return
        basis, amounts = feed
        total = sum(amounts.values())
        allocations = {outlet: {component: amount * splits[component][outlet] for component, amount in amounts.items()}
                       for outlet in outlets}
        outlet_amounts = {outlet: sum(rows.values()) for outlet, rows in allocations.items()}
        for stream in module.get("outlets", []):
            declared = _declared_material(stream)
            if declared is None or declared[0] != basis:
                continue
            outlet = stream.get("stream_id")
            calculated = allocations[outlet]
            if declared[1] == "fraction" and outlet_amounts[outlet] > 0:
                calculated = {component: rate / outlet_amounts[outlet] for component, rate in calculated.items()}
            differences = _composition_differences({c: float(amount) for c, amount in calculated.items()}, declared[2])
            self.require(not differences, "PLAN_SEP_OUTLET_COMPOSITION_MISMATCH", f"module.{module['id']}.outlets.{outlet}",
                         {"basis": basis, "quantity": declared[1], "calculated_and_declared": differences})
        for i, row in enumerate((module.get("separation") or {}).get("targets", [])):
            if not isinstance(row, dict):
                continue
            kind, outlet, component = row.get("kind"), row.get("outlet"), row.get("component")
            comparison, target = row.get("comparison"), _ratio(row)
            if outlet not in outlets or target is None or comparison not in ("eq", "ge", "le"):
                continue
            if kind == "recovery":
                denominator = amounts.get(component, 0)
                numerator = denominator * splits.get(component, {}).get(outlet, 0)
            elif kind == "purity" and row.get("amount_basis") == basis:
                denominator = outlet_amounts[outlet]
                numerator = amounts.get(component, 0) * splits.get(component, {}).get(outlet, 0)
            elif kind == "cut" and row.get("amount_basis") == basis:
                denominator, numerator = total, outlet_amounts[outlet]
            else:
                continue
            where = f"module.{module['id']}.separation.targets.{i}"
            if not self.require(denominator > 0, "PLAN_SEP_TARGET_UNDEFINED", where,
                                f"The nominal {kind} for {outlet} has a zero denominator"):
                continue
            actual = numerator / denominator
            rule = self.buildable_operating_rules[module["id"]][f"separation.targets.{i}"]
            scale = _ratio({"value": 1, "unit_or_basis": row["unit_or_basis"]})
            self.require(_meets_design(actual / Fraction(str(scale)), row["value"], rule), "PLAN_SEP_TARGET_MISMATCH", where,
                         {"kind": kind, "outlet": outlet, "component": component, "amount_basis": basis,
                          "actual_fraction": float(actual), "comparison": comparison, "target_fraction": target})

    def module_basis(self, module, where):
        self.text(module.get("module_revision"), where + ".module_revision")
        self.require(module.get("role") in {"reaction", "separation", "auxiliary", "other"},
                     "MODULE_ROLE_REQUIRED", where, "Explicit reaction/separation/auxiliary/other role required")
        self.text(module.get("purpose"), where + ".purpose")
        nodes = self.rows(module.get("node_ids"), where + ".node_ids")
        self.require(all(_text(x) for x in nodes) and len(set(str(x) for x in nodes)) == len(nodes),
                     "MODULE_NODE_IDS_INVALID", where, "Unique original process-node IDs required")
        self.streams(module.get("inlets"), where + ".inlets")
        self.streams(module.get("outlets"), where + ".outlets")
        self.quantities(module.get("targets"), where + ".targets")
        self.thermodynamics(module.get("thermodynamics"), where + ".thermodynamics")
        if module.get("role") == "reaction":
            reaction = self.obj(module.get("reaction"), where + ".reaction")
            self.quantities(reaction.get("conditions"), where + ".reaction.conditions")
            self.quantities(reaction.get("extent"), where + ".reaction.extent")
        if module.get("role") == "separation":
            separation = self.obj(module.get("separation"), where + ".separation")
            if separation.get("conditions") or not (self.require_buildable_plan and self.aggregate_sep(module)):
                self.quantities(separation.get("conditions"), where + ".separation.conditions")
            self.quantities(separation.get("targets"), where + ".separation.targets")
        auxiliaries = self.rows(module.get("auxiliaries"), where + ".auxiliaries", nonempty=False)
        aux_kinds = set()
        for index, raw in enumerate(auxiliaries):
            aux = self.obj(raw, f"{where}.auxiliaries[{index}]")
            self.text(aux.get("node_id"), where + ".auxiliaries.node_id")
            self.require(aux.get("kind") in AUXILIARIES, "AUXILIARY_KIND_INVALID", where, "Registered service kind required")
            if isinstance(aux.get("kind"), str):
                aux_kinds.add(aux["kind"])
            self.read(aux.get("source_ref"), where + ".auxiliaries.source_ref", json_value=False)
        requirements = self.obj(module.get("auxiliary_requirements"), where + ".auxiliary_requirements")
        for kind in AUXILIARIES:
            row = self.obj(requirements.get(kind), where + ".auxiliary_requirements." + kind)
            self.require(row.get("state") in {"required", "not_required"}, "AUXILIARY_REQUIREMENT_UNRESOLVED",
                         where + "." + kind, "Decide required/not_required using a stated physical basis; unknown remains open")
            self.text(row.get("basis"), where + "." + kind + ".basis")
            self.read(row.get("source_ref"), where + "." + kind + ".source_ref", json_value=False)
            if row.get("state") == "required":
                self.require(kind in aux_kinds, "REQUIRED_AUXILIARY_MISSING", where + "." + kind,
                             "Heating/heat transfer/pressure service cannot disappear from the scaffold")
        for index, raw in enumerate(self.rows(module.get("unknowns"), where + ".unknowns", nonempty=False)):
            unknown = self.obj(raw, f"{where}.unknowns[{index}]")
            self.text(unknown.get("question"), where + ".unknown.question")
            lookup = self.read(unknown.get("external_search_ref"), where + ".external_search_ref")
            if lookup is not None:
                self.identity_check(lookup, where + ".external_search")
                self.text(lookup.get("query"), where + ".external_search.query")
                self.text(lookup.get("source_scope"), where + ".external_search.source_scope")
                self.read(lookup.get("response_ref"), where + ".external_search.response_ref", json_value=False)
                self.require(lookup.get("result") in {"hits", "no_hits", "unavailable"}, "SEARCH_RESULT_REQUIRED", where,
                             "Keep the actual external source lookup outcome")
                if lookup.get("result") != "hits":
                    self.text(unknown.get("fallback_reason"), where + ".fallback_reason")
            self.text(unknown.get("resolution"), where + ".resolution")
            self.refs(unknown.get("resolution_sources"), where + ".resolution_sources")

    def handoff(self, gate):
        data = self.read(gate.get("handoff_input_ref"), "source.handoff_input_ref")
        report = self.read(gate.get("handoff_review_ref"), "source.handoff_review_ref")
        root = _skill_root()
        owner = root / "aspen-document-driven-flowsheet/scripts/check_flow_handoff.py" if root else None
        if not self.require(bool(owner and owner.is_file()), "HANDOFF_CHECKER_UNAVAILABLE", "source", "Install the existing handoff checker"):
            return
        if data is None or report is None:
            return
        spec = importlib.util.spec_from_file_location("fullflow_existing_handoff_checker", owner)
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        # Source-review mode invokes the same named-method, interface-action
        # and reaction-math checks as the public planning-stage entry.
        actual = checker.check(data, source_root=self.root, require_source_review=self.require_buildable_plan)
        self.require(actual.get("source_review_checked") is True,
                     "SOURCE_REVIEW_REQUIRED", "source",
                     "The formal full-flow source gate requires the current source text to be mapped paragraph-by-paragraph to the declared nodes/streams; a structurally valid graph alone is insufficient")
        self.require(report.get("input_sha256") == gate["handoff_input_ref"]["sha256"].lower()
                     and report.get("checker_sha256") == hashlib.sha256(owner.read_bytes()).hexdigest(),
                     "HANDOFF_IDENTITY_MISMATCH", "source", "Existing report must bind its exact input and current checker")
        # The existing checker correctly keeps proposed edges unobserved. A
        # hash-bound current authorization can close a proposal for a source
        # arrangement, not turn it into observed Aspen connectivity.
        approved = set()
        for index, reference in enumerate(self.rows(gate.get("proposal_authorizations", []), "source.proposal_authorizations", nonempty=False)):
            approval = self.read(reference, f"source.proposal_authorizations[{index}]")
            if approval is not None:
                self.identity_check(approval, "source.proposal_authorization")
                self.text(approval.get("basis"), "source.proposal_authorization.basis")
                self.read(approval.get("authority_ref"), "source.proposal_authorization.authority_ref", json_value=False)
                for identifier in self.rows(approval.get("stream_ids"), "source.proposal_authorization.stream_ids"):
                    if _text(identifier): approved.add(identifier)
        permitted_unresolved = {f"stream {row['id']}: proposed; {row.get('gap') or 'proposal, not observed connectivity'}"
                                for row in data.get("streams", []) if isinstance(row, dict) and row.get("state") == "proposed"
                                and row.get("id") in approved and row.get("from") is not None and row.get("to") is not None}
        if self.require_buildable_plan:
            flags = ("expert_plan_checked", "reaction_derivations_checked", "plan_action_declarations_checked",
                     "named_method_declarations_checked", "source_review_checked")
            self.require(all(actual.get(flag) is True for flag in flags), "BUILDABLE_HANDOFF_CHECK_INCOMPLETE",
                         "source.handoff", {"checks": {flag: actual.get(flag) for flag in flags}, "errors": actual["errors"]})
            # The handoff checker puts explicit verification limits next to actual missing inputs.
            # A calculated pressure path generates a notice even for a fully specified design.
            # Retain these in the receipt; specific gaps, errors and open connections still block.
            plan_rows = actual.get("expert_plan_rows", {})
            limits = {f"expert_plan.methods[{i}]: {row['status']} declaration; applicability is unverified"
                      for i, row in enumerate(plan_rows.get("methods", [])) if row.get("status") in ("candidate", "not_applicable")}
            limits.update(f"expert_plan.pressure_paths[{row['id']}]: {row['state']} declaration only; calculation/absence unverified"
                          for row in plan_rows.get("pressure_paths", []))
            self.summary["planning_verification_limits"] = [msg for msg in actual["unresolved"] if msg in limits]
            permitted_unresolved.update(limits)
        remaining = [x for x in actual["unresolved"] if x not in permitted_unresolved]
        self.require(not actual["errors"] and not remaining and report.get("status") == actual["status"],
                     "HANDOFF_INCOMPLETE", "source", {"status": actual["status"], "errors": actual["errors"], "unresolved": remaining})
        process_ids = {row.get("id") for row in data.get("nodes", []) if isinstance(row, dict) and row.get("kind") == "process"}
        expected = {node for module in self.modules.values() for node in module.get("node_ids", []) if isinstance(node, str)}
        expected |= {row.get("node_id") for module in self.modules.values() for row in module.get("auxiliaries", []) if isinstance(row, dict)}
        self.require(expected <= process_ids, "HANDOFF_MODULE_COVERAGE", "source", "Every declared module and required auxiliary must exist in the existing topology record")
        if self.require_buildable_plan:
            self.require(process_ids <= expected, "PLAN_UNSPECIFIED_PROCESS_NODES", "source",
                         f"Register the first-version service and model of nodes {sorted(process_ids - expected)}")
            self.buildable_interfaces(data)

    @staticmethod
    def at_path(data, dotted):
        if not _text(dotted):
            return None
        for part in dotted.split("."):
            if isinstance(data, dict):
                if part not in data:
                    return None
                data = data[part]
            elif isinstance(data, list) and part.isdigit() and int(part) < len(data):
                data = data[int(part)]
            else:
                return None
        return data

    @staticmethod
    def review_connection_paths(handoff, module):
        owned = set(module.get("node_ids", []))
        owned.update(aux.get("node_id") for aux in module.get("auxiliaries", []) if isinstance(aux, dict))
        endpoints = owned.copy()
        streams = []
        for index, row in enumerate(handoff.get("streams", [])):
            if isinstance(row, dict) and ({row.get("from"), row.get("to")} & owned):
                streams.append(f"streams.{index}")
                endpoints.update((row.get("from"), row.get("to")))
        nodes = [f"nodes.{index}" for index, row in enumerate(handoff.get("nodes", []))
                 if isinstance(row, dict) and row.get("id") in endpoints]
        return nodes + streams

    def verification_specs(self, gate, stage):
        """Required observations reuse current source/export fields, not prose length."""
        source_gate = self.contract["source_gate"]
        basis_ref = source_gate.get("design_basis_ref")
        handoff_ref = source_gate.get("handoff_input_ref")
        handoff = self.read(handoff_ref, stage + ".verification.handoff") or {}
        chain = [{"stream_id": x.get("id"), "from": x.get("from"), "to": x.get("to")}
                 for x in handoff.get("streams", []) if isinstance(x, dict)]
        exported, run_record, export_ref = {}, {}, None
        if stage == "scaffold":
            run_record = self.read(gate.get("run_ref"), "scaffold.verification.run") or {}
            export_ref = run_record.get("export_ref")
            exported = self.read(export_ref, "scaffold.verification.export") or {}
            chain = exported.get("connections")
            self.require(isinstance(chain, list) and bool(chain) and all(isinstance(x, dict)
                         and set(x) == {"stream_id", "from", "to"} and all(_text(v) for v in x.values()) for x in chain),
                         "EXPORTED_CONNECTIONS_REQUIRED", "scaffold", "Retain current exported stream endpoints for full-flow restatement")
        result = {}
        for index, (tag, module) in enumerate(self.modules.items()):
            prefix = f"modules.{index}."
            specs = {
                "module_purpose": [(basis_ref, prefix + "role"), (basis_ref, prefix + "purpose")],
                "inlet_outlet_composition": [(basis_ref, prefix + "inlets"), (basis_ref, prefix + "outlets")],
                "reaction_or_separation_basis": [(basis_ref, prefix + (module["role"] if module.get("role") in {"reaction", "separation"} else "targets"))],
                "thermodynamic_basis": [(basis_ref, prefix + "thermodynamics")],
                "heat_pressure_auxiliaries": [(basis_ref, prefix + "auxiliary_requirements"), (basis_ref, prefix + "auxiliaries")],
                "connections_terminals": [(handoff_ref, "nodes"), (handoff_ref, "streams")],
            }
            if stage == "source" and self.require_buildable_plan:
                specs["connections_terminals"] = [(handoff_ref, path)
                    for path in self.review_connection_paths(handoff, module)]
            if getattr(self, "scaffold_interface_names", {}):
                specs["connections_terminals"].append((basis_ref, "scaffold_interface_names"))
            if stage == "scaffold":
                matches = [i for i, x in enumerate(exported.get("modules", [])) if isinstance(x, dict) and x.get("module_id") == tag]
                actual_prefix = f"modules.{matches[0]}." if len(matches) == 1 else "missing_module."
                parameters = self.at_path(exported, actual_prefix + "parameters")
                self.require(isinstance(parameters, dict) and bool(parameters)
                             and not set(parameters) <= {"passed", "status", "checked"},
                             "EXPORTED_BLOCK_PARAMETERS_REQUIRED", tag, "Actual current block parameters are required, not a check label")
                specs.update({
                    "actual_block_parameters": [(export_ref, actual_prefix + "block_type"), (export_ref, actual_prefix + "parameters")],
                    "omitted_components": [(basis_ref, "modules"), (export_ref, "modules"), (export_ref, "auxiliary_nodes")],
                    "cycle_initials": [(gate.get("cycle_initials_ref"), "mode"), (gate.get("cycle_initials_ref"), "streams"), (export_ref, "recycle_stream_ids")],
                    "current_export_binding": [(export_ref, "run_id"), (export_ref, "model_sha256"), (export_ref, "raw_export_ref")],
                })
                if self.require_buildable_plan and len(module.get("node_ids", [])) > 1:
                    specs["actual_block_parameters"].append((export_ref, actual_prefix + "block_types"))
            result[tag] = specs
        return result, chain

    def verify_observations(self, row, specs, where):
        checks = self.obj(row.get("verification_checks"), where + ".verification_checks")
        self.require(set(checks) == set(specs), "VERIFICATION_CHECK_COVERAGE", where,
                     {"required_checks": list(specs), "reported_checks": list(checks)})
        for name, expected in specs.items():
            item = self.obj(checks.get(name), where + "." + name)
            observations = self.rows(item.get("observation"), where + "." + name + ".observation")
            references = self.rows(item.get("evidence_refs"), where + "." + name + ".evidence_refs")
            self.refs(references, where + "." + name + ".evidence_refs")
            def key(reference, path=None):
                if not isinstance(reference, dict):
                    return (None, None, path)
                return (reference.get("path"), str(reference.get("sha256", "")).lower(), path)
            expected_keys = {key(reference, path) for reference, path in expected}
            actual_keys = set()
            for raw in observations:
                observation = self.obj(raw, where + "." + name + ".observation")
                ref, path = observation.get("evidence_ref"), observation.get("value_path")
                identity = key(ref, path)
                self.require(identity in expected_keys and identity not in actual_keys,
                             "VERIFICATION_ANCHOR_MISMATCH", where + "." + name, "Observe each required field from the exact current evidence")
                actual_keys.add(identity)
                data = self.read(ref, where + "." + name + ".observed_evidence")
                value = self.at_path(data, path)
                self.require(value is not None and "value" in observation and _same_observed_value(observation["value"], value),
                             "VERIFICATION_OBSERVATION_MISMATCH", where + "." + name,
                             "Actual observation must match the referenced field; OK/considered/passed prose is not a field readback")
            self.require(actual_keys == expected_keys and {key(x) for x in references} >= {key(x) for x, _ in expected},
                         "VERIFICATION_CHECK_INCOMPLETE", where + "." + name, "Every required observation and its source reference must be retained")

    @staticmethod
    def review_epoch(value):
        return type(value) in (int, float) and 0 <= value < math.inf

    def review_detail(self, value, where):
        generic = {"all ok", "ok", "pass", "passed", "done", "checked", "verified", "yes", "no issue",
                   "no issues", "all good", "all checks passed", "all checks pass", "looks good",
                   "continue", "proceed", "no action", "no action required",
                   "已核对", "已检查", "通过", "正常", "符合", "无异议", "无问题", "全部通过",
                   "全部正常", "各项正常", "各项通过", "均通过", "继续", "无需处理", "无须处理"}
        self.require(_text(value) and value.strip().strip(".!。！").casefold() not in generic,
                     "REVIEW_ANALYSIS_REQUIRED", where, "Record the actual observation or reasoning")

    def review_article_excerpt(self, excerpt, locator):
        if not _text(excerpt) or not _text(locator):
            return False
        match = re.fullmatch(r"L([1-9][0-9]{0,8})", locator)
        if match is None:
            return False
        lines = getattr(self, "buildable_article_text", "").splitlines()
        start = int(match[1]) - 1
        length = len(excerpt.splitlines())
        return start < len(lines) and excerpt in "\n".join(lines[start:start + length])

    def review_assessment_inputs(self, gate):
        """Load the three frozen structured inputs used by the planning assessments."""
        return {name: (gate.get(name), self.read(gate.get(name), "source.planning_assessments." + name) or {})
                for name in ("design_basis_ref", "handoff_input_ref", "planning_checks_ref")}

    def review_assessment_requirements(self, inputs, module_id):
        basis_ref, basis = inputs["design_basis_ref"]
        handoff_ref, handoff = inputs["handoff_input_ref"]
        checks_ref, planning = inputs["planning_checks_ref"]
        module = self.modules[module_id]
        primary = {node for node in module.get("node_ids", []) if _text(node)}
        nodes = primary | {aux["node_id"] for aux in module.get("auxiliaries", [])
                           if isinstance(aux, dict) and _text(aux.get("node_id"))}
        index = next((i for i, row in enumerate(basis.get("modules", []))
                      if isinstance(row, dict) and row.get("id") == module_id), "missing_module")
        prefix = f"modules.{index}."
        required = {
            "physical_feasibility": [[(basis_ref, prefix + field)] for field in ("inlets", "outlets")],
            "design_depth": [[(basis_ref, prefix + field)] for field in ("physical_service", "first_model")],
            "evidence_applicability": [[(basis_ref, prefix + "thermodynamics")]],
            "handoff": [],
        }
        for category in ("pressure_budget", "heat_strategy", "compression_decisions"):
            required["physical_feasibility"].append([
                (checks_ref, f"{category}.{i}") for i, row in enumerate(planning.get(category, []))
                if isinstance(row, dict) and module_id in row.get("module_ids", [])])
        edge_groups = [[(handoff_ref, f"streams.{i}")] for i, row in enumerate(handoff.get("streams", []))
                       if isinstance(row, dict) and (row.get("from") in nodes or row.get("to") in nodes)]
        required["handoff"].extend(edge_groups or [[]])
        required["handoff"].extend([[(handoff_ref, f"handoffs.{i}")] for i, row in enumerate(handoff.get("handoffs", []))
                                    if isinstance(row, dict) and row.get("id") in nodes | {module_id}])
        role = module.get("role")
        if role in {"reaction", "separation"}:
            research = (module.get(role) or {}).get("planning_research") or {}
            selected_id = research.get("selected_candidate_id")
            candidate = next((i for i, row in enumerate(research.get("candidates", []))
                              if isinstance(row, dict) and selected_id and row.get("id") == selected_id), "missing_candidate")
            root = prefix + role + ".planning_research."
            selected = (basis_ref, root + "selected_candidate_id")
            candidate_path = root + f"candidates.{candidate}"
            candidate_evidence = [(basis_ref, candidate_path + ".evidence"), (basis_ref, candidate_path)]
            required["design_depth"].append([selected])
            required["evidence_applicability"].append(candidate_evidence)
            key = "reaction_kinetics" if role == "reaction" else "separation_readiness"
            required[key] = [[selected], [(basis_ref, root + "target_mappings")], candidate_evidence,
                             [(basis_ref, candidate_path + ".basis"), (basis_ref, candidate_path)]]
            if role == "reaction" and research.get("kinetics_exclusion") is not None:
                required[key].append([(basis_ref, root + "kinetics_exclusion")])
        return primary, nodes, required

    @staticmethod
    def review_evidence_key(reference, path=None):
        if (not isinstance(reference, dict) or set(reference) != {"path", "sha256"}
                or not _text(reference["path"]) or not _text(reference["sha256"])):
            return None
        return reference["path"], reference["sha256"].lower(), path

    def review_planning_assessments(self, row, module_id, issues, inputs, where):
        module = self.modules[module_id]
        primary, nodes, required = self.review_assessment_requirements(inputs, module_id)
        reported = self.obj(row.get("planning_assessments"), where + ".planning_assessments")
        self.require(set(reported) == set(required), "PLANNING_REVIEW_ASSESSMENT_COVERAGE", where,
                     {"required": list(required), "reported": list(reported)})
        article_key = self.review_evidence_key(self.buildable_article_ref)
        known_inputs = {self.review_evidence_key(ref): data for ref, data in inputs.values() if ref}
        issue_evidence = {}
        for name, groups in required.items():
            scope = where + ".planning_assessments." + name
            assessment = self.obj(reported.get(name), scope)
            node_ids = self.rows(assessment.get("node_ids"), scope + ".node_ids")
            actual_nodes = {node for node in node_ids if _text(node)}
            self.require(primary <= actual_nodes <= nodes and len(actual_nodes) == len(node_ids),
                         "PLANNING_REVIEW_ASSESSMENT_NODE", scope, "Identify the actual principal nodes of this module and applicable auxiliaries")
            for field in ("observed_result", "action"):
                self.review_detail(assessment.get(field), scope + "." + field)
            status = assessment.get("status")
            self.require(status in ("adequate", "provisional", "issue"), "PLANNING_REVIEW_ASSESSMENT_STATUS", scope,
                         "State the conclusion and any limited planning or corrective action")
            evidence_keys, article_anchored = set(), False
            for raw in self.rows(assessment.get("evidence"), scope + ".evidence"):
                evidence = self.obj(raw, scope + ".evidence_entry")
                ref, path = evidence.get("evidence_ref"), evidence.get("value_path")
                identity = self.review_evidence_key(ref)
                if "article_locator" in evidence or "article_excerpt" in evidence:
                    excerpt = evidence.get("article_excerpt")
                    valid_article = (identity is not None and identity == article_key
                                     and set(evidence) == {"evidence_ref", "article_locator", "article_excerpt"}
                                     and self.review_article_excerpt(excerpt, evidence.get("article_locator")))
                    self.require(valid_article, "PLANNING_REVIEW_EVIDENCE_MISMATCH", scope,
                                 "Quote actual text at that locator in the frozen article")
                    if valid_article:
                        module_excerpt = module.get("article_excerpt")
                        article_anchored |= _text(module_excerpt) and module_excerpt in excerpt
                        evidence_keys.add(identity)
                    continue
                key = self.review_evidence_key(ref, path) if _text(path) else None
                data = known_inputs.get(identity)
                if key is not None and data is None:
                    data = self.read(ref, scope + ".evidence_ref")
                value = self.at_path(data, path)
                valid_value = (key is not None and set(evidence) == {"evidence_ref", "value_path", "value"}
                               and value is not None and _same_observed_value(evidence["value"], value))
                if self.require(valid_value, "PLANNING_REVIEW_EVIDENCE_MISMATCH", scope,
                                "Retain the actual field value from the cited exact record"):
                    evidence_keys.add(key)
            matches = [{self.review_evidence_key(ref, path) for ref, path in group} & evidence_keys for group in groups]
            missing = [[path for _, path in group] for group, match in zip(groups, matches) if not match]
            if name == "design_depth" and not article_anchored:
                missing.append(["current module passage in frozen planning article"])
            self.require(not missing, "PLANNING_REVIEW_EVIDENCE_INCOMPLETE", scope, {"missing_anchor_groups": missing})
            issue_id = assessment.get("issue_id")
            if status == "issue":
                issue = issues.get(issue_id) if _text(issue_id) else None
                if self.require(issue is not None and issue.get("node_id") in actual_nodes,
                                "PLANNING_REVIEW_FINDING_UNREPORTED", scope,
                                "Link a blocking engineering assessment to a located issue and corrective action"):
                    anchors = set().union(*matches)
                    if article_anchored:
                        anchors.add(article_key)
                    issue_evidence.setdefault(issue_id, set()).update(key[:2] for key in anchors)
            elif issue_id is not None:
                self.need("PLANNING_REVIEW_ASSESSMENT_STATUS", scope, "Use status=issue when referring to a blocking issue")
        return issue_evidence

    def review_dispatch(self, gate):
        upstream = [{"code": item["code"], "scope": item["scope"]} for item in self.needs]
        dispatch = _planning_review_dispatch()
        if dispatch["status"] == "BRIEF_UNAVAILABLE":
            self.need("PLANNING_REVIEW_BRIEF_UNAVAILABLE", "source", dispatch["detail"])
            return dispatch
        try:
            rendered = build_planning_review_prompt(
                self.identity.get("case_id"), self.identity.get("task_revision"),
                evidence_root=self.root, review_specifications=self.review_specification_index(),
                **{name: gate.get(name) for name in PLANNING_REVIEW_REFS})
        except (OSError, ValueError) as exc:
            self.need("PLANNING_REVIEW_INPUTS_REQUIRED", "source", str(exc))
            dispatch["detail"] = str(exc)
        else:
            checked = [self.read(gate[name], "source.planning_review_dispatch." + name, json_value=False)
                       for name in PLANNING_REVIEW_REFS]
            if all(checked):
                dispatch.update(rendered, status="PLANNING_INPUTS_BLOCKED" if upstream else "READY_TO_SEND")
                dispatch.pop("brief")
                if upstream:
                    dispatch["blocking_checks"] = upstream
            else:
                dispatch.update(status="INPUTS_UNVERIFIED", detail="Use the current bytes of each frozen input")
        return dispatch

    def review_specification_index(self):
        """Expose identifiers needed for the return contract without any expected results."""
        index = {}
        for module_id, specs in self.buildable_review_specs.items():
            index[module_id] = []
            for spec_id, spec in specs.items():
                entry = {"spec_id": spec_id, "node_id": spec["node_id"],
                         "design_context_keys": sorted(spec.get("design_context", {}))}
                for field in ("acceptance_tolerance", "acceptance_decimals"):
                    if field in spec:
                        entry["acceptance_field"] = field
                index[module_id].append(entry)
        return index

    def review_extractions(self, row, module_id, issues, where):
        specs = getattr(self, "buildable_review_specs", {}).get(module_id, {})
        extractions = self.rows(row.get("quantitative_extractions"), where + ".quantitative_extractions", nonempty=False)
        seen, discrepancies = set(), set()
        for raw in extractions:
            entry = self.obj(raw, where + ".extraction")
            spec_id = entry.get("spec_id")
            spec = specs.get(spec_id) if isinstance(spec_id, str) else None
            if not self.require(spec is not None and spec_id not in seen, "REVIEW_QUANTITY_COVERAGE", where,
                                "Identify each exact current node specification once"):
                continue
            seen.add(spec_id)
            tag = entry.get("node_id")
            self.require(tag == spec.get("node_id"), "REVIEW_QUANTITY_NODE", where, spec_id)
            excerpt = entry.get("article_excerpt")
            self.require(self.review_article_excerpt(excerpt, entry.get("article_locator")),
                         "REVIEW_ARTICLE_ANCHOR", where, f"{spec_id}: cite text at its line in the current article")
            unit = entry.get("unit_or_basis")
            basis = entry.get("basis")
            self.text(unit, where + ".extraction.unit_or_basis")
            self.text(basis, where + ".extraction.basis")
            comparison = entry.get("comparison")
            value = entry.get("value")
            numeric = type(value) in (int, float) and -math.inf < value < math.inf
            if isinstance(value, dict):
                numeric = set(value) == {"lower", "upper"} and all(type(bound) in (int, float)
                    and -math.inf < bound < math.inf for bound in value.values()) and value["lower"] <= value["upper"]
            sourced_input = numeric or (_text(value) and _text(excerpt) and value in excerpt)
            self.require(sourced_input or (comparison == "ambiguous" and "value" in entry and value is None),
                         "REVIEW_QUANTITY_VALUE", where, f"{spec_id}: record a finite number, range, or quoted input relation, or explain the ambiguity")
            if numeric:
                literals = re.findall(r"(?<![\d.])[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", str(excerpt))
                declared = value.values() if isinstance(value, dict) else [value]
                self.require(all(any(float(literal) == number for literal in literals) for number in declared),
                             "REVIEW_ARTICLE_VALUE", where, f"{spec_id}: show the extracted value in the cited passage")
            expected_context = spec.get("design_context", {})
            context = self.obj(entry.get("design_context", {}), where + ".extraction.design_context")
            self.require(set(context) == set(expected_context), "REVIEW_DESIGN_CONTEXT", where,
                         f"{spec_id}: independently identify the applicable reaction or separation basis fields")
            for field in ("outlet", "component", "key_reactant"):
                if field in context and comparison != "ambiguous":
                    self.require(_text(context[field]) and context[field] in str(excerpt), "REVIEW_ARTICLE_DESIGN_CONTEXT", where,
                                 f"{spec_id}: locate the reported {field} in the cited passage")
            same_acceptance = all((field in spec) == (field in entry)
                                  and _same_observed_value(entry.get(field), spec.get(field))
                                  for field in ("acceptance_tolerance", "acceptance_decimals"))
            if comparison == "match":
                self.require(same_acceptance, "REVIEW_ACCEPTANCE_RULE", where,
                             f"{spec_id}: independently read the frozen tolerance, units and reference or stated precision")
            matches = (same_acceptance and sourced_input and value == spec.get("value") and unit == spec.get("unit_or_basis")
                       and basis == spec.get("basis") and context == expected_context)
            self.require(comparison == "ambiguous" or (comparison == "match" and matches)
                         or (comparison == "difference" and not matches), "REVIEW_QUANTITY_COMPARISON", where,
                         f"{spec_id}: reconcile the extracted value, unit and basis against the current plan")
            if comparison != "match":
                issue_id = entry.get("issue_id")
                issue = issues.get(issue_id) if isinstance(issue_id, str) else None
                if self.require(issue is not None and issue.get("node_id") == tag, "REVIEW_DIFFERENCE_UNREPORTED", where,
                                f"{spec_id}: attach the discrepancy or ambiguity to a finding at this node"):
                    discrepancies.add(issue_id)
        self.require(seen == set(specs), "REVIEW_QUANTITY_COVERAGE", where,
                     {"missing": sorted(set(specs) - seen)})
        return discrepancies

    def review_native_window(self, stage):
        scaffold = self.contract.get("scaffold_gate")
        if not isinstance(scaffold, dict) or "run_ref" not in scaffold:
            return {}
        run = self.read(scaffold["run_ref"], stage + ".review_order.run_ref")
        if run is None:
            return {}
        model = self.read(run.get("model_ref"), stage + ".review_order.model_ref", json_value=False)
        native = self.read(run.get("native_run_ref"), stage + ".review_order.native_run_ref") or {}
        native = self.obj(native.get("run", native), stage + ".review_order.native_run")
        started, finished = native.get("started_epoch"), native.get("finished_epoch")
        if not self.require(self.review_epoch(started) and self.review_epoch(finished) and started <= finished
                            and native.get("status") == "completed" and model is not None
                            and native.get("case_sha256") == model["sha256"] and _text(run.get("run_id"))
                            and native.get("run_id") == run.get("run_id"), "REVIEW_NATIVE_TIMING_REQUIRED", stage,
                            "Use the timed native scaffold run bound to this scaffold receipt"):
            return {}
        self.identity_check(run, stage + ".review_order.run")
        return {"scaffold_started_epoch": started, "scaffold_finished_epoch": finished}

    def close_planning_findings(self, comparison, expected, article_sha):
        where = f"source.comparison.{comparison.get('call_id')}.{comparison.get('module_id')}"
        self.require(not {"issue_ids", "disposition", "rationale", "evidence_refs"} & comparison.keys(),
                     "DIFFERENCE_UNRESOLVED", where, "Use individual dispositions for each planning finding")
        seen = set()
        for raw in self.rows(comparison.get("issue_dispositions"), where + ".issue_dispositions"):
            item = self.obj(raw, where + ".issue_disposition")
            issue_id = item.get("issue_id")
            if not self.require(_text(issue_id) and issue_id in expected["issues"] and issue_id not in seen,
                                "DIFFERENCE_COVERAGE", where, "Each disposition must identify one distinct reported issue"):
                continue
            seen.add(issue_id)
            scope = where + "." + issue_id
            disposition = item.get("disposition")
            self.require(disposition in ("adopt", "reject"), "DIFFERENCE_UNRESOLVED", scope,
                         "Adopt or reject the finding using its evidence")
            self.review_detail(item.get("rationale"), scope + ".rationale")
            evidence = self.rows(item.get("evidence_refs"), scope + ".evidence_refs")
            self.refs(evidence, scope + ".evidence_refs")
            closure_evidence = {key[:2] for ref in evidence if (key := self.review_evidence_key(ref))}
            self.require(any(digest != expected["output_sha256"].lower() for _, digest in closure_evidence),
                         "PLANNING_REVIEW_CLOSURE_EVIDENCE", scope, "Cite evidence beyond the finding's own answer")
            if issue_id in expected["quantitative_discrepancies"]:
                self.require(isinstance(article_sha, str)
                             and any(digest == article_sha.lower() for _, digest in closure_evidence),
                             "DIFFERENCE_ARTICLE_EVIDENCE_REQUIRED", scope,
                             "Reconcile differing readings against the accepted article")
            anchors = expected["planning_assessment_issues"].get(issue_id)
            if anchors is not None:
                self.require(anchors & closure_evidence, "PLANNING_REVIEW_CLOSURE_EVIDENCE", scope,
                             "Answer the blocking engineering finding using its actual source, article or handoff evidence")
            if disposition == "adopt":
                self.need("REVIEW_PLAN_REVISION_REQUIRED", scope,
                          "Resolve the adopted finding in the plan and re-review the resulting frozen inputs")
        self.require(seen == expected["issues"], "DIFFERENCE_COVERAGE", where,
                     "Retain one sourced disposition for every issue from this call and module")

    def reviews(self, gate, stage, expected_count, *, bindings):
        before = len(self.needs)
        timed = getattr(self, "require_buildable_plan", False)
        buildable_source = timed and stage == "source"
        article_ref = getattr(self, "buildable_article_ref", None)
        article_sha = article_ref.get("sha256") if isinstance(article_ref, dict) else None
        dispatch_text = None
        assessment_inputs = {}
        if buildable_source:
            bindings = {**bindings, "planning_article_sha256": article_sha}
            self.planning_review_dispatch = self.review_dispatch(gate)
            dispatch_text = self.planning_review_dispatch.get("text")
            assessment_inputs = self.review_assessment_inputs(gate)
        native_window = self.review_native_window(stage) if timed else {}
        verification_specs, process_chain = self.verification_specs(gate, stage)
        prompt = self.read(gate.get("prompt_ref"), stage + ".prompt_ref", json_value=False)
        if buildable_source:
            self.require(prompt is not None and dispatch_text is not None
                         and prompt["sha256"] == self.planning_review_dispatch["sha256"],
                         "PLANNING_REVIEW_PROMPT_INCOMPLETE", stage,
                         "Use the complete registered reviewer instructions and exact frozen inputs as source_gate.prompt_ref")
        references = self.rows(gate.get("independent_calls"), stage + ".independent_calls")
        self.require(len(references) == expected_count, "INDEPENDENT_REVIEW_COUNT", stage,
                     f"Exactly {expected_count} independent call records required; unavailable calls remain incomplete")
        calls, contexts, invoked, review_map = set(), set(), set(), {}
        capabilities, finished_calls = set(), []
        evidence_hashes = {"invocation_ref": set(), "output_ref": set()}
        for index, reference in enumerate(references):
            where = f"{stage}.independent_calls[{index}]"
            record = self.read(reference, where)
            if record is None:
                continue
            self.identity_check(record, where)
            call_id, context_id = record.get("call_id"), record.get("independent_context_id")
            self.require(_text(call_id) and call_id not in calls, "DUPLICATE_CALL_ID", where, "Distinct real call IDs required")
            self.require(_text(context_id) and context_id not in contexts, "NONINDEPENDENT_REVIEW", where, "Distinct isolated agent/context IDs required")
            if _text(call_id): calls.add(call_id)
            if _text(context_id): contexts.add(context_id)
            self.require(record.get("schema") == "fullflow-agent-call-v1" and record.get("stage") == stage,
                         "REVIEW_SCHEMA_OR_STAGE", where, "Expected current-stage call record, not a passed flag")
            model, effort = record.get("model_id"), record.get("reasoning_effort")
            if self.require(_text(model) and _text(effort), "REVIEW_CAPABILITY_REQUIRED", where,
                            "Record the actual model and reasoning effort used for the independent call"):
                capabilities.add((model, effort))
            prompt_hash = prompt.get("sha256") if prompt else None
            self.require(prompt_hash is not None and record.get("prompt_sha256") == prompt_hash,
                         "REVIEW_PROMPT_MISMATCH", where, "All independent calls must use the exact frozen prompt")
            for field, seen_hashes in evidence_hashes.items():
                ref = record.get(field)
                digest = ref.get("sha256") if isinstance(ref, dict) else None
                if _text(digest):
                    digest = digest.lower()
                    self.require(digest not in seen_hashes, "REUSED_REVIEW_EVIDENCE", where,
                                 f"Each call needs its own {field} bytes")
                    seen_hashes.add(digest)
            invocation = self.read(record.get("invocation_ref"), where + ".invocation_ref")
            output = self.read(record.get("output_ref"), where + ".output_ref")
            if invocation is not None:
                self.identity_check(invocation, where + ".invocation")
                invocation_id = invocation.get("invocation_id")
                self.require(_text(invocation_id) and invocation_id not in invoked, "DUPLICATE_INVOCATION", where,
                             "Distinct raw invocation records required")
                if _text(invocation_id): invoked.add(invocation_id)
                for field in ("call_id", "independent_context_id", "model_id", "reasoning_effort", "prompt_sha256"):
                    self.require(invocation.get(field) == record.get(field), "INVOCATION_IDENTITY_MISMATCH", where, field)
                self.require(invocation.get("output_sha256") == (record.get("output_ref") or {}).get("sha256"),
                             "INVOCATION_OUTPUT_MISMATCH", where, "Invocation must identify this exact output")
                if buildable_source:
                    self.require(dispatch_text is not None and invocation.get("dispatched_prompt") == dispatch_text,
                                 "PLANNING_REVIEW_PROMPT_NOT_SENT", where,
                                 "Retain the complete actual sent instruction text and frozen inputs in this invocation")
                    if "raw_output_refs" in invocation:
                        self.refs(invocation["raw_output_refs"], where + ".invocation.raw_output_refs")
                if timed:
                    started, finished = invocation.get("started_epoch"), invocation.get("finished_epoch")
                    if self.require(self.review_epoch(started) and self.review_epoch(finished) and started <= finished,
                                    "REVIEW_INVOCATION_TIMING_REQUIRED", where, "Retain ordered start/finish epochs in the invocation record"):
                        finished_calls.append(finished)
                        if stage == "scaffold" and native_window:
                            self.require(started >= native_window["scaffold_finished_epoch"], "REVIEW_BEFORE_NATIVE_RUN", where,
                                         "Scaffold review must start after the native scaffold run finishes")
            if output is None:
                continue
            if buildable_source:
                layout_problems = planning_review_layout(output)
                self.require(not layout_problems, "PLANNING_REVIEW_OUTPUT_LAYOUT", where, layout_problems)
            self.identity_check(output, where + ".output")
            self.require(output.get("schema") == "fullflow-independent-review-v1" and output.get("call_id") == call_id,
                         "REVIEW_OUTPUT_IDENTITY", where, "Structured independent output required")
            for field, value in bindings.items():
                self.require(output.get(field) == value, "STALE_REVIEW_BASIS", where, field)
            self.require(output.get("process_chain") == process_chain and bool(process_chain),
                         "REVIEW_PROCESS_CHAIN_MISMATCH", where, "Restate each current source/export stream endpoint, not a generic process sentence")
            seen = set()
            for row in self.rows(output.get("module_reviews"), where + ".module_reviews"):
                row = self.obj(row, where + ".module_review")
                module_id = row.get("module_id")
                self.require(module_id in self.modules and module_id not in seen, "REVIEW_MODULE_COVERAGE", where, "One review per declared module required")
                if not isinstance(module_id, str):
                    continue
                seen.add(module_id)
                for field in ("role_summary", "boundary_summary", "thermodynamics_summary", "reaction_or_separation_summary"):
                    (self.review_detail if timed else self.text)(row.get(field), where + "." + field)
                if module_id in verification_specs:
                    self.verify_observations(row, verification_specs[module_id], where + "." + module_id)
                issues = self.rows(row.get("issues"), where + ".issues", nonempty=False)
                issue_ids, issue_details = [], {}
                for issue in issues:
                    issue = self.obj(issue, where + ".issue")
                    self.text(issue.get("id"), where + ".issue.id")
                    self.text(issue.get("finding"), where + ".issue.finding")
                    if _text(issue.get("id")):
                        issue_ids.append(issue["id"])
                        issue_details[issue["id"]] = issue
                    if buildable_source and module_id in self.modules:
                        module = self.modules[module_id]
                        nodes = module.get("node_ids", []) + [a.get("node_id") for a in module.get("auxiliaries", []) if isinstance(a, dict)]
                        self.require(issue.get("node_id") in nodes, "REVIEW_FINDING_NODE", where, "Locate the finding at a node in this module")
                        for field in ("finding", "recommended_change", "rereview_scope"):
                            self.review_detail(issue.get(field), where + ".issue." + field)
                self.require(len(set(issue_ids)) == len(issue_ids), "DUPLICATE_REVIEW_ISSUE", where, "Issue IDs must be distinct")
                discrepancies = self.review_extractions(row, module_id, issue_details, where + "." + module_id) if buildable_source else set()
                assessed_issues = (self.review_planning_assessments(row, module_id, issue_details,
                                                                   assessment_inputs, where + "." + module_id)
                                   if buildable_source and module_id in self.modules else {})
                if _text(call_id):
                    review_map[(call_id, module_id)] = {"issues": set(issue_ids), "output_sha256": record["output_ref"]["sha256"],
                                                       "quantitative_discrepancies": discrepancies,
                                                       "planning_assessment_issues": assessed_issues}
            self.require(seen == set(self.modules), "REVIEW_MODULE_COVERAGE", where, "Missing module-by-module restatement")
        self.require(len(capabilities) == 1, "REVIEW_CAPABILITY_MISMATCH", stage,
                     "All independent calls in this review group must use the same actual model and reasoning effort")
        closure = self.read(gate.get("difference_closure_ref"), stage + ".difference_closure_ref")
        if closure is None:
            return
        self.identity_check(closure, stage + ".difference_closure")
        self.text(closure.get("reviewer_id"), stage + ".difference_closure.reviewer_id")
        self.require(closure.get("schema") == "fullflow-difference-closure-v1", "DIFFERENCE_CLOSURE_REQUIRED", stage,
                     "Main reviewer must close each comparison; votes and bare passed values do not count")
        seen = set()
        for item in self.rows(closure.get("comparisons"), stage + ".comparisons"):
            item = self.obj(item, stage + ".comparison")
            pair = (str(item.get("call_id")), str(item.get("module_id")))
            expected = review_map.get(pair)
            self.require(expected is not None and pair not in seen, "DIFFERENCE_COVERAGE", stage, "Comparison must identify a unique actual call/module")
            seen.add(pair)
            if expected:
                self.require(item.get("output_sha256") == expected["output_sha256"], "DIFFERENCE_COVERAGE", stage,
                             "Bind the comparison to the exact independent output")
                if buildable_source and expected["issues"]:
                    self.close_planning_findings(item, expected, article_sha)
                    continue
            disposition = item.get("disposition")
            evidence = item.get("evidence_refs")
            allowed = ("no_difference",) if buildable_source else ("adopt", "reject", "no_difference")
            if stage == "scaffold" and expected is not None:
                scope = f"{stage}.comparison.{pair[0]}.{pair[1]}"
                allowed = ("adopt", "reject") if expected["issues"] else ("no_difference",)
                if expected["issues"] and disposition == "adopt":
                    self.need("SCAFFOLD_REVIEW_RERUN_REQUIRED", scope,
                              "Resolve adopted findings, rerun the corrected scaffold and review its new export")
                if expected["issues"] and disposition == "reject":
                    export_sha = bindings.get("export_sha256")
                    closure_hashes = {
                        key[1] for ref in (evidence if isinstance(evidence, list) else ())
                        if (key := self.review_evidence_key(ref))
                    }
                    self.require(isinstance(export_sha, str) and export_sha.lower() in closure_hashes,
                                 "SCAFFOLD_REVIEW_EXPORT_EVIDENCE_REQUIRED", scope,
                                 "Ground this rejection in the exact scaffold export being reviewed; attach other evidence as needed")
            self.require(disposition in allowed, "DIFFERENCE_UNRESOLVED", stage,
                         "Explicit disposition must match whether this comparison has reported findings")
            (self.review_detail if timed else self.text)(item.get("rationale"), stage + ".comparison.rationale")
            self.refs(evidence, stage + ".comparison.evidence_refs")
            issue_ids = self.rows(item.get("issue_ids"), stage + ".comparison.issue_ids", nonempty=False)
            if expected:
                covers_issues = set(str(x) for x in issue_ids) == expected["issues"]
                if stage == "scaffold":
                    covers_issues = (covers_issues and len(issue_ids) == len(expected["issues"])
                                     and all(_text(issue_id) for issue_id in issue_ids))
                self.require(covers_issues and (not buildable_source or item.get("issue_dispositions", []) == []),
                             "DIFFERENCE_COVERAGE", stage, "Account for each issue reported by this call and module")
        self.require(seen == set(review_map) and len(review_map) == expected_count * len(self.modules),
                     "DIFFERENCE_COVERAGE", stage, "Missing independent call/module comparison")
        if timed:
            closed = closure.get("closed_epoch")
            self.require(self.review_epoch(closed) and len(finished_calls) == expected_count
                         and all(finished <= closed for finished in finished_calls), "REVIEW_CLOSURE_TIMING_REQUIRED", stage,
                         "Close the review after all required calls finish")
            if stage == "source" and native_window and self.review_epoch(closed):
                self.require(closed < native_window["scaffold_started_epoch"], "SOURCE_REVIEW_AFTER_NATIVE_START", stage,
                             "Close the source review before starting the first native scaffold run")
            if len(self.needs) == before:
                self.summary.setdefault("buildable_review_epochs", {}).update(native_window, **{stage + "_closed_epoch": closed})
                if buildable_source and before == 0:
                    self.planning_review_dispatch.update(source_review_closed=True, status="REVIEWS_CLOSED")

    def run(self, reference, where, *, module=None, boundary_hash=None, current=False):
        record = self.read(reference, where)
        if record is None:
            return {}, {}
        self.identity_check(record, where)
        self.require(record.get("schema") == "fullflow-run-evidence-v1", "RUN_RECORD_REQUIRED", where, "Run/export references required, not passed=True")
        run_id = record.get("run_id")
        self.text(run_id, where + ".run_id")
        model = self.read(record.get("model_ref"), where + ".model_ref", json_value=False)
        native = self.read(record.get("native_run_ref"), where + ".native_run_ref")
        exported = self.read(record.get("export_ref"), where + ".export_ref")
        if native is not None:
            run = native.get("run", native)
            run = self.obj(run, where + ".native_run")
            self.require(run.get("run_id") == run_id and model is not None and run.get("case_sha256") == model["sha256"],
                         "NATIVE_RUN_IDENTITY", where, "Recorded engine run must identify this model and run")
            self.require(run.get("status") == "completed" and type(run.get("started_epoch")) in (int, float)
                         and type(run.get("finished_epoch")) in (int, float)
                         and math.isfinite(run.get("started_epoch", float("nan")))
                         and math.isfinite(run.get("finished_epoch", float("nan")))
                         and run.get("finished_epoch", 0) >= run.get("started_epoch", 1),
                         "NATIVE_RUN_INCOMPLETE", where, "A completed timed run record is required; this does not certify convergence")
        if exported is not None:
            self.identity_check(exported, where + ".export", run_id=run_id)
            self.require(exported.get("schema") == "fullflow-model-export-v1" and model is not None
                         and exported.get("model_sha256") == model["sha256"], "EXPORT_MODEL_IDENTITY", where,
                         "Structured export must bind the same model bytes")
            self.read(exported.get("raw_export_ref"), where + ".raw_export_ref", json_value=False)
        if module:
            for data in (record, exported or {}):
                self.require(data.get("module_id") == module["id"] and data.get("module_revision") == module["module_revision"]
                             and data.get("boundary_sha256") == boundary_hash,
                             "STALE_MODULE_RUN", where, "Current module revision and exact boundary must match")
            entries = self.rows((exported or {}).get("modules"), where + ".export.modules")
            matching = [row for row in entries if isinstance(row, dict) and row.get("module_id") == module["id"]]
            self.require(len(matching) == 1, "ISLAND_EXPORT_MODULE_COVERAGE", where, "Exactly one current module export required")
            if len(matching) == 1:
                self.require(matching[0].get("module_revision") == module["module_revision"]
                             and matching[0].get("thermodynamics") == self.current_thermodynamics.get(module["id"], module.get("thermodynamics")),
                             "ISLAND_PROPERTY_MISMATCH", where, "Island export must retain its current sourced property basis")
        if current:
            current_run = self.payload.get("run_id")
            source = self.documents.get("source_export", {})
            self.require(_text(current_run) and run_id == current_run, "STALE_CURRENT_RUN", where, "Current stage run differs")
            if source:
                self.require(source.get("case_id") == self.identity.get("case_id") and source.get("run_id") == run_id,
                             "CURRENT_EXPORT_MISMATCH", where, "Equipment export and full-flow evidence use different runs")
                self.require(model is not None and source.get("model_sha256") == model["sha256"]
                             and exported is not None and source.get("raw_export_sha256") == (exported.get("raw_export_ref") or {}).get("sha256"),
                             "CURRENT_EXPORT_MODEL_BINDING", where, "Equipment canonical export must bind this exact native model and raw export, not only case/run labels")
        return record, exported or {}

    def source(self, contract):
        gate = self.obj(contract.get("source_gate"), "source_gate")
        basis = self.read(gate.get("design_basis_ref"), "source.design_basis_ref")
        if basis is not None:
            self.identity_check(basis, "source.design_basis")
            expected = [{k: v for k, v in module.items() if k != "module_revision"} for module in self.modules.values()]
            self.require(basis.get("modules") == expected, "STALE_SOURCE_DESIGN_BASIS", "source",
                         "Source facts changed; module revision alone does not invalidate this frozen source basis")
            if "scaffold_interface_names" in basis:
                self.scaffold_interface_names = self.obj(basis["scaffold_interface_names"], "source.scaffold_interface_names")
                self.require(self.scaffold_interface_names.keys() <= {"streams", "terminals"},
                             "SCAFFOLD_INTERFACE_ALIAS_INVALID", "source", "Freeze only stream and terminal names here")
        if self.require_buildable_plan:
            self.buildable_plan(gate)
        self.handoff(gate)
        self.planning(gate)
        self.reviews(gate, "source", 3, bindings={"design_basis_sha256": (gate.get("design_basis_ref") or {}).get("sha256")})

    def planning(self, gate):
        """Check short planning records; reuse outputs, never recalculate pressure."""
        record = self.read(gate.get("planning_checks_ref"), "source.planning_checks_ref")
        if record is None:
            return
        self.identity_check(record, "source.planning_checks")
        self.require(record.get("schema") == "fullflow-planning-checks-v1", "PLANNING_RECORD_REQUIRED", "source", "Use the three short planning groups, not passed=True")
        summaries = []
        for group in ("pressure_budget", "heat_strategy", "compression_decisions"):
            covered = set()
            for index, raw in enumerate(self.rows(record.get(group), "planning." + group)):
                where = f"planning.{group}[{index}]"
                row = self.obj(raw, where)
                ids = self.rows(row.get("module_ids"), where + ".module_ids")
                self.require(all(_text(x) and x in self.modules for x in ids), "PLANNING_MODULE_IDENTITY", where, "Name the modules to which this planning statement applies")
                covered.update(x for x in ids if isinstance(x, str) and x in self.modules)
                for field in ("method", "input_basis"):
                    self.text(row.get(field), where + "." + field)
                self.refs(row.get("evidence_refs"), where + ".evidence_refs")
                state = row.get("state")
                allowed = {"calculated", "provisional_bounds", "not_applicable", "blocked"}
                if group != "pressure_budget":
                    allowed.add("reasoned")
                self.require(state in allowed, "PLANNING_STATE_INVALID", where, "Pressure planning needs a calculation or sourced bounds; considering it is not evidence")
                if state == "calculated":
                    calculation = self.read(row.get("calculation_ref"), where + ".calculation_ref")
                    result_path = row.get("result_path")
                    self.text(result_path, where + ".result_path")
                    self.text(row.get("unit"), where + ".unit")
                    actual = calculation
                    if isinstance(result_path, str):
                        for part in result_path.split("."):
                            if isinstance(actual, dict):
                                actual = actual.get(part)
                            elif isinstance(actual, list) and part.isdigit() and int(part) < len(actual):
                                actual = actual[int(part)]
                            else:
                                actual = None
                                break
                    self.require(type(actual) in (int, float) and math.isfinite(actual),
                                 "PLANNING_CALCULATION_EVIDENCE_REQUIRED", where, "Locate a finite numerical result in the existing calculation output; a PASS flag is not a pressure result")
                elif state == "provisional_bounds":
                    bounds = self.obj(row.get("bounds"), where + ".bounds")
                    lower, upper = bounds.get("lower"), bounds.get("upper")
                    self.require(type(lower) in (int, float) and type(upper) in (int, float)
                                 and math.isfinite(lower) and math.isfinite(upper) and lower <= upper,
                                 "PLANNING_BOUNDS_REQUIRED", where, "Finite ordered source-backed bounds required")
                    self.text(bounds.get("unit"), where + ".bounds.unit")
                    self.read(bounds.get("source_ref"), where + ".bounds.source_ref", json_value=False)
                    self.require(all(_text(x) for x in self.rows(row.get("unresolved_inputs"), where + ".unresolved_inputs")),
                                 "PLANNING_REFINEMENT_REQUIRED", where, "Name the missing geometry or other indispensable inputs")
                    self.text(row.get("refine_trigger"), where + ".refine_trigger")
                elif state in {"not_applicable", "blocked"}:
                    self.text(row.get("reason"), where + ".reason")
                    if state == "blocked":
                        self.need("PLANNING_ITEM_UNRESOLVED", where, row.get("reason"))
                    else:
                        relevant = {"pressure_budget": ("compression", "pumping", "pressure_control"),
                                    "heat_strategy": ("heating", "heat_exchange"), "compression_decisions": ("compression",)}[group]
                        contradictory = [tag for tag in ids if isinstance(tag, str) and tag in self.modules
                            and any((self.modules[tag].get("auxiliary_requirements", {}).get(kind) or {}).get("state") == "required" for kind in relevant)]
                        self.require(not contradictory, "PLANNING_NOT_APPLICABLE_CONFLICT", where,
                                     {"required_service_modules": contradictory})
                summaries.append({"group": group, "module_ids": ids, "state": state})
            self.require(covered == set(self.modules), "PLANNING_SCOPE_INCOMPLETE", group,
                         "Cover source modules, grouped where useful; use a sourced not-applicable reason instead of omitting a branch")
        self.summary["planning_records"] = summaries

    def scaffold(self, contract):
        gate = self.obj(contract.get("scaffold_gate"), "scaffold_gate")
        record, exported = self.run(gate.get("run_ref"), "scaffold.run_ref")
        exported_modules = {}
        for row in self.rows(exported.get("modules"), "scaffold.export.modules"):
            row = self.obj(row, "scaffold.export.module")
            tag = row.get("module_id")
            if _text(tag):
                self.require(tag not in exported_modules, "DUPLICATE_EXPORTED_MODULE", "scaffold", tag)
                exported_modules[tag] = row
        self.require(set(exported_modules) == set(self.modules), "SCAFFOLD_MODULE_COVERAGE", "scaffold", "Run the complete original flowsheet before refining modules")
        aux_ids = set()
        for aux in self.rows(exported.get("auxiliary_nodes"), "scaffold.export.auxiliary_nodes", nonempty=False):
            aux = self.obj(aux, "scaffold.export.auxiliary_node")
            if _text(aux.get("node_id")): aux_ids.add(aux["node_id"])
            self.text(aux.get("block_type"), "scaffold.export.auxiliary.block_type")
        for tag, module in self.modules.items():
            row = exported_modules.get(tag, {})
            self.scaffold_block_types(tag, module, row)
            self.require(row.get("original_node_ids") == module.get("node_ids"), "SCAFFOLD_LOCATION_MISMATCH", tag, "Preserve original module location")
            self.streams(row.get("inlets"), "scaffold." + tag + ".inlets")
            self.streams(row.get("outlets"), "scaffold." + tag + ".outlets")
            self.require(row.get("thermodynamics") == module.get("thermodynamics"), "SCAFFOLD_PROPERTY_MISMATCH", tag,
                         "Exported property basis differs from the frozen module basis")
            required = {x.get("node_id") for x in module.get("auxiliaries", []) if isinstance(x, dict)}
            self.require(required <= aux_ids, "SCAFFOLD_AUXILIARY_MISSING", tag, "Required heat/pressure nodes are absent from the run export")
        cycle = self.read(gate.get("cycle_initials_ref"), "scaffold.cycle_initials_ref")
        has_targets = self.has_scaffold_targets()
        has_cycle = cycle is not None and cycle.get("mode") == "recycle"
        results = self.native_design_results(record, "scaffold") if has_targets or has_cycle else {}
        if has_targets:
            self.scaffold_design_targets(exported_modules, results)
        if cycle is not None:
            self.scaffold_cycles(contract, record, exported, exported_modules, cycle, results)
        self.reviews(gate, "scaffold", 3, bindings={"run_id": record.get("run_id"),
            "export_sha256": (record.get("export_ref") or {}).get("sha256"),
            "cycle_initials_sha256": (gate.get("cycle_initials_ref") or {}).get("sha256")})

    def scaffold_block_types(self, tag, module, exported):
        """Use the frozen first-model choice, with defaults for older dossiers."""
        default = {"reaction": "RSTOIC", "separation": "SEP"}.get(module.get("role"))
        first = module.get("first_model")
        if not self.require_buildable_plan or not isinstance(first, dict):
            if default:
                self.require(str(exported.get("block_type", "")).upper() == default,
                             "SCAFFOLD_MODEL_TYPE", tag, f"Source scaffold without a reviewed first model requires {default}")
            return
        source_ids = self.rows(module.get("node_ids"), tag + ".first_model.node_ids")
        if not source_ids or not all(_text(node) for node in source_ids):
            return
        if len(source_ids) == 1:
            expected = first.get("block_type")
            self.require(_text(expected) and str(exported.get("block_type", "")).upper() == expected.upper(),
                         "SCAFFOLD_MODEL_TYPE", tag, f"Frozen first model requires {expected}")
            return
        native_ids = exported.get("node_ids")
        native_types = exported.get("block_types")
        if not self.require(isinstance(native_ids, list) and len(native_ids) == len(source_ids)
                            and all(_text(node) for node in native_ids) and len(set(native_ids)) == len(native_ids)
                            and isinstance(native_types, dict) and native_types.keys() == set(native_ids),
                            "SCAFFOLD_MODEL_TYPE", tag, "Retain the actual native block type for every frozen node"):
            return
        for source_node, native_node in zip(source_ids, native_ids):
            source_model = first.get(source_node)
            expected = source_model.get("block_type") if isinstance(source_model, dict) else None
            self.require(_text(expected) and str(native_types[native_node]).upper() == expected.upper(),
                         "SCAFFOLD_MODEL_TYPE", native_node, f"Frozen first model for {source_node} requires {expected}")

    def scaffold_cycles(self, contract, run, exported, exported_modules, cycle, results):
        where = "scaffold.cycle_initials"
        self.identity_check(cycle, where, run_id=run.get("run_id"))
        self.require(cycle.get("schema") == "fullflow-cycle-initials-v1"
                     and cycle.get("export_sha256") == (run.get("export_ref") or {}).get("sha256"),
                     "CYCLE_EXPORT_MISMATCH", where, "Cycle initialization must originate from this scaffold export")
        self.text(cycle.get("basis"), where + ".basis")
        self.refs(cycle.get("source_refs"), where + ".source_refs")
        source_gate = self.obj(contract.get("source_gate"), "source_gate")
        source = self.read(source_gate.get("handoff_input_ref"), where + ".source_handoff") or {}
        output_edges, stream_names, verified = self.scaffold_connections(source, exported, exported_modules)
        expected = self.at_path(source, "expert_plan.recycle_plan")
        expected_ids = {row["stream_id"] for row in expected if isinstance(row, dict) and _text(row.get("stream_id"))} if isinstance(expected, list) else None
        native_ids = self.rows(exported.get("recycle_stream_ids"), where + ".exported_recycles", nonempty=False)
        if not self.require(all(_text(tag) for tag in native_ids) and len(set(native_ids)) == len(native_ids),
                            "CYCLE_INITIALS_COVERAGE", where, "Retain unique native recycle stream identities"):
            return
        native_ids = set(native_ids)
        if expected_ids is not None:
            named_recycles = {stream_names.get(stream, stream) for stream in native_ids}
            self.require(named_recycles == expected_ids, "CYCLE_FROZEN_PLAN_MISMATCH", where,
                         {"expected": sorted(expected_ids), "exported": sorted(named_recycles)})
        if cycle.get("mode") == "no_recycle":
            self.require(not native_ids and cycle.get("streams") == [], "NO_RECYCLE_CONTRADICTION", where,
                         "No-recycle statement conflicts with exported recycle inventory")
            return
        if cycle.get("mode") != "recycle":
            self.need("CYCLE_MODE_REQUIRED", where, "Use sourced recycle initial states or an explicit no_recycle record")
            return
        rows = self.rows(cycle.get("streams"), where + ".streams")
        self.streams(rows, where + ".streams")
        states = {row["stream_id"]: row for row in rows if isinstance(row, dict) and _text(row.get("stream_id"))}
        self.require(bool(native_ids) and states.keys() == native_ids, "CYCLE_INITIALS_COVERAGE", where,
                     "Every exported recycle needs an initial state")
        self.require(bool(results), "CYCLE_NATIVE_STATE_UNAVAILABLE", where, "Read the current native stream Output leaves")
        for stream in sorted(native_ids):
            if self.require(stream in verified, "CYCLE_CONNECTION_NOT_VERIFIED", stream,
                            "Recycle must connect the frozen source endpoints in the scaffold export"):
                self.require(self.scaffold_path_exists(output_edges, stream),
                             "CYCLE_CONNECTION_NOT_VERIFIED", stream, "The declared tear stream must be on a directed loop in the actual scaffold")
                if stream in states and results:
                    self.scaffold_cycle_state(stream, states[stream], results)

    def scaffold_connections(self, source, exported, exported_modules):
        """Check net material boundaries against the current connection export."""
        source_edges = {row["id"]: (row["from"], row["to"]) for row in source.get("streams", []) if isinstance(row, dict)
                        and all(_text(row.get(field)) for field in ("id", "from", "to"))}
        terminals = {row["id"] for row in source.get("nodes", []) if isinstance(row, dict)
                     and row.get("kind") == "external" and _text(row.get("id"))}
        output_edges = {}
        for row in self.rows(exported.get("connections"), "scaffold.export.connections"):
            if isinstance(row, dict) and all(_text(row.get(field)) for field in ("stream_id", "from", "to")):
                stream = row["stream_id"]
                self.require(stream not in output_edges, "SCAFFOLD_DUPLICATE_CONNECTION", stream, "One native connection per stream")
                output_edges[stream] = (row["from"], row["to"])
        original_nodes = {}
        for module in exported_modules.values():
            original = module.get("original_node_ids")
            current = module.get("node_ids")
            if isinstance(original, list) and isinstance(current, list) and len(original) == len(current):
                original_nodes.update({actual: prior for prior, actual in zip(original, current) if _text(actual) and _text(prior)})
        output_nodes = {node for edge in output_edges.values() for node in edge}
        process_names = {row["id"] for row in source.get("nodes", []) if isinstance(row, dict)
                         and row.get("kind") == "process" and _text(row.get("id"))}
        process_names.update(original_nodes)
        process_names.update(row["node_id"] for row in exported.get("auxiliary_nodes") or []
                             if isinstance(row, dict) and _text(row.get("node_id")))
        stream_names = self.scaffold_aliases("streams", source_edges.keys(), output_edges.keys())
        terminal_names = self.scaffold_aliases("terminals", terminals, output_nodes - process_names)
        original_nodes.update(terminal_names)
        delivered = {}
        verified = set()
        mismatched = set()
        for actual, endpoints in output_edges.items():
            stream = stream_names.get(actual, actual)
            if stream not in source_edges:
                continue
            projected = tuple(original_nodes.get(node, node) for node in endpoints)
            self.require(stream not in delivered, "SCAFFOLD_DUPLICATE_CONNECTION", stream, "More than one native stream maps to this frozen connection")
            delivered[stream] = actual
            if projected == source_edges[stream]:
                verified.add(actual)
            else:
                mismatched.add(stream)
        self.require(not mismatched, "SCAFFOLD_CONNECTION_MISMATCH", "scaffold",
                     {"streams_on_wrong_endpoints": sorted(mismatched)})
        ports = [row for module in self.modules.values() for side in ("inlets", "outlets")
                 for row in (module[side] if isinstance(module.get(side), list) else []) if isinstance(row, dict)
                 and _text(row.get("stream_id"))]
        net_material = {row["stream_id"] for row in ports if row.get("stream_kind", "material") == "material"}
        duties = {row["stream_id"] for row in ports if row.get("stream_kind") in ("heat", "work")}
        external_material = {tag for tag, edge in source_edges.items() if terminals.intersection(edge)} - duties
        required = (external_material | net_material) & source_edges.keys()
        self.require(required <= delivered.keys(), "SCAFFOLD_NET_INTERFACE_MISSING", "scaffold",
                     {"missing_net_material_streams": sorted(required - delivered.keys())})
        return output_edges, stream_names, verified

    def scaffold_aliases(self, field, frozen_ids, actual_ids):
        frozen = getattr(self, "scaffold_interface_names", {})
        aliases = self.obj(frozen.get(field, {}), "source.scaffold_interface_names." + field)
        result = {}
        for original, row in aliases.items():
            actual = row.get("actual_id") if isinstance(row, dict) else None
            if self.require(original in frozen_ids and _text(actual) and actual in actual_ids
                            and actual not in frozen_ids and actual not in result and _text(row.get("basis")),
                            "SCAFFOLD_INTERFACE_ALIAS_INVALID", f"{field}.{original}",
                            "The reviewed source must identify one native name and explain its original interface identity"):
                result[actual] = original
        return result

    @staticmethod
    def scaffold_path_exists(edges, stream):
        """Find a return path without reusing the same tear stream."""
        sender, receiver = edges[stream]
        downstream = {}
        for other, (origin, target) in edges.items():
            if other != stream:
                downstream.setdefault(origin, set()).add(target)
        pending = {receiver}
        visited = set()
        while pending:
            node = pending.pop()
            if node == sender:
                return True
            visited.add(node)
            pending.update(downstream.get(node, set()) - visited)
        return False

    def scaffold_cycle_state(self, stream, state, results):
        prefix = f"\\Data\\Streams\\{stream}\\Output\\"

        def scalar(field):
            return results.get(prefix + field + "\\MIXED", results.get(prefix + field, {}))

        def matched(field, expected, actual):
            self.require(_finite(expected) and _finite(actual) and math.isclose(expected, actual, rel_tol=1e-9),
                         "CYCLE_NATIVE_STATE_MISMATCH", stream, {"field": field, "declared": expected, "native": actual})

        def amount_rate(amount, component=None):
            rate = self.native_amount_rate(results, amount, stream, component)
            return float(rate) if rate is not None else None

        flow = self.obj(state.get("flow"), stream + ".flow")
        flow_scale = _amount_rate_basis(flow.get("unit_or_basis"))
        flow_value = flow.get("value")
        if self.require(flow_scale is not None and _finite(flow_value) and flow_value >= 0,
                        "CYCLE_STATE_UNITS_REQUIRED", stream, "Record a finite total molar or mass flow with its units"):
            matched("flow", flow_value * flow_scale[1], amount_rate(flow_scale[0]))
        temp = self.obj(state.get("temperature"), stream + ".temperature")
        temp_native = scalar("TEMP_OUT")
        temperature = _temperature_in_kelvin(temp.get("value"), temp.get("unit_or_basis"))
        native_temp = _temperature_in_kelvin(temp_native.get("Value"), temp_native.get("UnitString"))
        if self.require(temperature is not None and temperature > 0 and native_temp is not None,
                        "CYCLE_STATE_UNITS_REQUIRED", stream, "Record a physical temperature with C, K, F or R units"):
            matched("temperature", temperature, native_temp)
        pressure = _pressure_reading(state.get("pressure"))
        native_pressure = scalar("PRES_OUT")
        actual = _pressure_reading({"value": native_pressure.get("Value"), "unit_or_basis": native_pressure.get("UnitString")})
        if self.require(pressure is not None and actual is not None and "gauge" not in (pressure[1], actual[1]),
                        "CYCLE_STATE_UNITS_REQUIRED", stream, "Record the native absolute pressure with a supported pressure unit"):
            self.require(_finite(pressure[0]) and pressure[0] > 0, "CYCLE_STATE_UNITS_REQUIRED", stream, "Absolute pressure must be positive")
            matched("pressure (Pa)", pressure[0], actual[0])
        vapor = scalar("VFRAC_OUT")
        vapor_value = vapor.get("Value")
        phase = None
        solid_values = [scalar(field).get("Value") for field in ("SFRAC_OUT", "SOLIDFRAC_OUT")]
        solid_values.extend(results.get(prefix + "MASSFLMX\\" + field, {}).get("Value") for field in ("CISOLID", "SOLID"))
        if any(_finite(value) and value > 0 for value in solid_values):
            self.need("CYCLE_NATIVE_PHASE_UNSUPPORTED", stream, "A solid-bearing recycle needs its specialist phase and substream evidence")
        elif _finite(vapor_value) and 0 <= vapor_value <= 1 and vapor.get("UnitString") in (None, "", "-", "1", "fraction"):
            phase = "liquid" if vapor_value == 0 else "vapor" if vapor_value == 1 else "two_phase"
        self.require(phase is not None and state.get("phase") == phase, "CYCLE_NATIVE_STATE_MISMATCH", stream,
                     {"field": "phase", "declared": state.get("phase"), "native_vapor_fraction": vapor_value, "native_fluid_phase": phase})

        material = _declared_material(state)
        if not self.require(material is not None, "CYCLE_STATE_UNITS_REQUIRED", stream,
                            "Record every component on an explicit molar or mass rate or fraction basis"):
            return
        amount, dimension, declared = material
        native_total = amount_rate(amount)
        field = "MOLEFLOW" if amount == "mole" else "MASSFLOW"
        component_root = prefix + field + "\\MIXED\\"
        components = {path[len(component_root):] for path in results if path.startswith(component_root)
                      and "\\" not in path[len(component_root):]}
        rates = {key: amount_rate(amount, key) for key in components}
        if not self.require(bool(rates) and all(_finite(value) for value in rates.values()) and _finite(native_total)
                            and math.isclose(math.fsum(rates.values()), native_total, rel_tol=1e-6)
                            and declared.keys() <= rates.keys() and (dimension == "rate" or native_total > 0),
                            "CYCLE_NATIVE_COMPOSITION_UNAVAILABLE", stream, "Retain the complete native component-flow inventory and its total"):
            return
        for key, rate in rates.items():
            matched("composition." + key, declared.get(key, 0), rate if dimension == "rate" else rate / native_total)

    def islands(self, contract):
        rows = self.rows(contract.get("islands"), "islands")
        indexed = {}
        for raw in rows:
            item = self.obj(raw, "island")
            tag = item.get("module_id")
            if isinstance(tag, str):
                self.require(tag not in indexed, "DUPLICATE_ISLAND", tag, "One current record per module")
                indexed[tag] = item
        results = {}
        self.island_design_boundaries = {}
        for tag in self.scope:
            module = self.modules[tag]
            item = self.obj(indexed.get(tag), "island." + tag)
            self.require(item.get("module_revision") == module.get("module_revision"), "STALE_ISLAND_REVISION", tag, "Refine this module's current revision only")
            boundary = self.read(item.get("boundary_ref"), "island." + tag + ".boundary_ref")
            route = self.read(item.get("specialist_route_ref"), "island." + tag + ".specialist_route_ref")
            boundary_hash = (item.get("boundary_ref") or {}).get("sha256")
            origin_module = {}
            origin_run, origin_export = {}, {}
            if boundary is not None:
                self.identity_check(boundary, "island." + tag + ".boundary")
                self.require(boundary.get("module_id") == tag and boundary.get("module_revision") == module.get("module_revision")
                             and boundary.get("original_node_ids") == module.get("node_ids"),
                             "ISLAND_BOUNDARY_IDENTITY", tag, "Frozen island must represent the same original module")
                self.text(boundary.get("from_run_id"), "island." + tag + ".from_run_id")
                origin = self.read(boundary.get("from_export_ref"), "island." + tag + ".from_export_ref")
                if origin is not None:
                    self.identity_check(origin, "island." + tag + ".from_export", run_id=boundary.get("from_run_id"))
                origin_run, origin_export = self.run(boundary.get("from_run_ref"), "island." + tag + ".from_run_ref")
                self.require(origin_run.get("run_id") == boundary.get("from_run_id")
                             and (origin_run.get("export_ref") or {}).get("sha256") == (boundary.get("from_export_ref") or {}).get("sha256"),
                             "ISLAND_ORIGIN_RUN_MISMATCH", tag, "Boundary must come from its exact completed baseline run/export")
                origin_rows = [x for x in origin_export.get("modules", []) if isinstance(x, dict) and x.get("module_id") == tag]
                self.require(len(origin_rows) == 1, "ISLAND_ORIGIN_MODULE_MISSING", tag, "Find this original module in the baseline export")
                if len(origin_rows) == 1:
                    origin_module = origin_rows[0]
                    for field in ("inlets", "outlets", "targets"):
                        self.require(boundary.get(field) == origin_rows[0].get(field), "ISLAND_BOUNDARY_STATE_MISMATCH", tag,
                                     f"Frozen {field} must match this baseline export; approved boundary changes need a new baseline run")
                self.streams(boundary.get("inlets"), "island." + tag + ".inlets")
                self.streams(boundary.get("outlets"), "island." + tag + ".outlets")
                self.quantities(boundary.get("targets"), "island." + tag + ".targets")
            if route is not None:
                self.identity_check(route, "island." + tag + ".route")
                self.require(route.get("module_id") == tag and route.get("module_revision") == module.get("module_revision")
                             and route.get("boundary_sha256") == boundary_hash, "ISLAND_ROUTE_IDENTITY", tag, "Specialist route must bind this boundary/revision")
                owner = route.get("owner")
                root = _skill_root()
                self.require(_text(owner) and "/" not in owner and "\\" not in owner and root is not None
                             and (root / owner / "SKILL.md").is_file(), "SPECIALIST_OWNER_UNAVAILABLE", tag, "Use an existing installed specialist")
                self.text(route.get("method"), "island." + tag + ".method")
                self.refs(route.get("source_refs"), "island." + tag + ".route.source_refs")
            expected_thermo = module.get("thermodynamics")
            if "thermodynamics_change_ref" in item:
                change = self.read(item["thermodynamics_change_ref"], "island." + tag + ".thermodynamics_change_ref")
                if change is not None:
                    self.identity_check(change, "island." + tag + ".thermodynamics_change")
                    self.require(change.get("module_id") == tag and change.get("module_revision") == module.get("module_revision")
                                 and change.get("prior_thermodynamics_sha256") == _canonical(expected_thermo),
                                 "PROPERTY_CHANGE_IDENTITY", tag, "Property change must identify the frozen basis and affected module revision")
                    self.text(change.get("basis"), "island." + tag + ".thermodynamics_change.basis")
                    self.read(change.get("authority_ref"), "island." + tag + ".thermodynamics_change.authority_ref", json_value=False)
                    expected_thermo = self.thermodynamics(change.get("thermodynamics"), "island." + tag + ".changed_thermodynamics")
            self.current_thermodynamics[tag] = expected_thermo
            run_record, run_export = self.run(item.get("run_ref"), "island." + tag + ".run_ref", module=module, boundary_hash=boundary_hash)
            if self.require_buildable_plan and boundary is not None:
                refined_rows = [r for r in run_export.get("modules", []) if isinstance(r, dict) and r.get("module_id") == tag]
                refined_module = refined_rows[0] if len(refined_rows) == 1 else {}
                self.island_design_boundaries[tag] = boundary
                checks_results = bool(self.buildable_operating_rules.get(tag))
                baseline_results = self.native_design_results(origin_run, f"island.{tag}.baseline") if checks_results else {}
                refined_results = self.native_design_results(run_record, f"island.{tag}.refined") if checks_results else {}
                self.island_design_specs(tag, boundary, origin_module, refined_module,
                                         baseline_results, refined_results)
            results[tag] = run_record
            self.island_equipment_gate(tag, item, run_record, run_export)
        return results

    def native_design_results(self, run, where):
        """Read the existing Aspen Output/Input probe format from this native run's receipt."""
        if not run:
            return {}
        native = self.read(run.get("native_run_ref"), where + ".native_run_ref") or {}
        native_run = native.get("run", native)
        snapshot_ref = native.get("result_snapshot_ref") or native_run.get("result_snapshot_ref")
        if not self.require(isinstance(snapshot_ref, dict), "NATIVE_DESIGN_RESULTS_REQUIRED", where,
                            "The native run receipt must bind its Aspen result snapshot"):
            return {}
        snapshot = self.read(snapshot_ref, where + ".result_snapshot_ref") or {}
        if not self.require(snapshot.get("run_id") == run.get("run_id")
                            and snapshot.get("case_sha256") == (run.get("model_ref") or {}).get("sha256")
                            and isinstance(snapshot.get("probes"), dict) and bool(snapshot["probes"]),
                            "NATIVE_DESIGN_RESULT_IDENTITY", where, "Use the result tree of the exact native model and run"):
            return {}
        root = _skill_root()
        try:
            reader_path = root / "aspen-plus-operations/scripts/flowsheet_boundary/native_results.py"
            loader = importlib.util.spec_from_file_location("fullflow_native_results", reader_path)
            reader = importlib.util.module_from_spec(loader)
            loader.loader.exec_module(reader)
            leaves = {}
            for rows in snapshot["probes"].values():
                for path, row in reader.leaf_index(rows).items():
                    prior = leaves.get(path)
                    if prior is not None and any(row.get(key) != prior.get(key) for key in ("Value", "UnitString")):
                        raise ValueError(f"inconsistent result leaf across probe groups: {path}")
                    leaves[path] = row
            return reader.leaf_index(leaves.values())
        except (AttributeError, ImportError, OSError, TypeError, ValueError) as exc:
            self.need("NATIVE_DESIGN_RESULTS_UNREADABLE", where, str(exc))
            return {}

    @staticmethod
    def native_material_ids(native, side):
        return {row["stream_id"] for row in native.get(side, []) if isinstance(row, dict)
                and _text(row.get("stream_id")) and row.get("stream_kind", "material") == "material"}

    @staticmethod
    def native_amount_rate(results, amount_basis, stream, component=None):
        prefix = "MASS" if amount_basis == "mass" else "MOLE"
        path = f"\\Data\\Streams\\{stream}\\Output\\{prefix}{'FLOW' if component else 'FLMX'}\\MIXED"
        row = results.get(path + (f"\\{component}" if component else ""), {})
        scale = _amount_rate_basis(row.get("UnitString"), exact=True)
        value = row.get("Value")
        return Fraction(str(value)) * scale[1] if scale and scale[0] == amount_basis and _finite(value) and value >= 0 else None

    @classmethod
    def native_amount_total(cls, results, amount_basis, streams, components=None):
        rates = [cls.native_amount_rate(results, amount_basis, stream, component)
                 for stream in streams for component in components or (None,)]
        return sum(rates) if rates and all(value is not None for value in rates) else None

    @classmethod
    def separation_target_value(cls, planned, native, results, *, complete_allocation=False):
        """Calculate a net separation metric from the current Output material rates."""
        context = planned.get("design_context", {})
        unit = planned["unit_or_basis"]
        kind, outlet, component = (context.get(key) for key in ("kind", "outlet", "component"))
        inlets = cls.native_material_ids(native, "inlets")
        outlets = cls.native_material_ids(native, "outlets")
        if not inlets or outlet not in outlets:
            return None
        if "inlet" in context:
            inlet = context["inlet"]
            if inlet not in inlets:
                return None
            inlets = {inlet}
        amount = context.get("amount_basis") or ("mass" if unit in ("wt%", "mass fraction", "kg/kg", "质量分率") else "mole")
        if amount not in ("mass", "mole"):
            return None
        subset = context.get("basis_components")
        if kind in ("purity", "cut") and re.search(r"\bdry\b|干基", str(planned.get("basis", "")), re.I) and subset is None:
            return None
        if subset is not None and not (isinstance(subset, list) and subset and all(_text(value) for value in subset)
                                      and len(set(subset)) == len(subset)):
            return None
        if kind == "recovery" and _text(component):
            numerator = cls.native_amount_rate(results, amount, outlet, component)
            denominator = cls.native_amount_total(results, amount, inlets, (component,))
            if complete_allocation:
                # An unlisted SEP destination receives the remainder. Read it even for a zero split.
                incoming = cls.native_amount_total(results, amount, cls.native_material_ids(native, "inlets"), (component,))
                outgoing = cls.native_amount_total(results, amount, outlets, (component,))
                if incoming is None or outgoing is None or not math.isclose(incoming, outgoing, rel_tol=1e-6):
                    return None
        elif kind == "purity" and _text(component):
            if subset is not None and component not in subset:
                return None
            numerator = cls.native_amount_rate(results, amount, outlet, component)
            denominator = cls.native_amount_total(results, amount, (outlet,), subset)
        elif kind == "cut":
            numerator = cls.native_amount_total(results, amount, (outlet,), subset)
            denominator = cls.native_amount_total(results, amount, inlets, subset)
        else:
            return None
        if numerator is None or denominator is None or denominator <= 0 or numerator > denominator * (1 + 1e-9):
            return None
        scale = _ratio({"value": 1, "unit_or_basis": unit})
        return numerator / denominator / Fraction(str(scale)) if scale else None

    @classmethod
    def single_reaction_conversion(cls, planned, native, results):
        """Replay an unambiguous per-pass conversion on the whole reactor material boundary."""
        context = planned["design_context"]
        component = context.get("key_reactant")
        inlets = cls.native_material_ids(native, "inlets")
        outlets = cls.native_material_ids(native, "outlets")
        if not _text(component) or ("inlet" in context and inlets != {context["inlet"]}):
            return None
        incoming = cls.native_amount_total(results, "mole", inlets, (component,))
        remaining = cls.native_amount_total(results, "mole", outlets, (component,))
        scale = _ratio({"value": 1, "unit_or_basis": planned["unit_or_basis"]})
        if incoming is None or remaining is None or incoming <= 0 or not scale:
            return None
        return (incoming - remaining) / incoming / Fraction(str(scale))

    @staticmethod
    def native_design_value(path, unit, native, results, *, require_output):
        if not _text(path):
            return None
        segments = path.split("\\")
        if len(segments) < 6 or segments[:2] != ["", "Data"] or segments[4] not in ("Input", "Output"):
            return None
        section, tag, area = segments[2:5]
        stream_ids = {row.get("stream_id") for key in ("inlets", "outlets") for row in native.get(key, []) if isinstance(row, dict)}
        if (section == "Blocks" and tag in native.get("node_ids", [])) or (section == "Streams" and tag in stream_ids):
            if require_output and area != "Output":
                return None
        else:
            return None
        row = results.get(path, {})
        value, source_unit = row.get("Value"), row.get("UnitString")
        if source_unit == unit:
            return value
        source, target = _amount_rate_basis(source_unit, exact=True), _amount_rate_basis(unit, exact=True)
        if _finite(value) and source and target and source[0] == target[0]:
            return float(Fraction(str(value)) * source[1] / target[1])
        if _finite(value) and source_unit == "bar" and unit in ("bar(a)", "bara"):
            return value
        if unit == "K" and (kelvin := _temperature_in_kelvin(value, source_unit)) is not None:
            return kelvin
        source_fraction = _ratio({"value": 1, "unit_or_basis": source_unit})
        target_fraction = _ratio({"value": 1, "unit_or_basis": unit})
        ratio_basis = {"mol%": "mole", "mole fraction": "mole", "mol/mol": "mole", "摩尔分率": "mole",
                       "wt%": "mass", "mass fraction": "mass", "kg/kg": "mass", "质量分率": "mass",
                       "vol%": "volume", "volume fraction": "volume"}
        source_basis, target_basis = (ratio_basis.get(str(x).casefold().strip()) for x in (source_unit, unit))
        if _finite(value) and source_fraction and target_fraction and (not source_basis or not target_basis or source_basis == target_basis):
            return float(Fraction(str(value)) * Fraction(str(source_fraction)) / Fraction(str(target_fraction)))
        return None

    def net_target_kind(self, tag, key, planned):
        context = planned.get("design_context", {})
        module = self.modules.get(tag, {})
        split = (context.get("kind") == "recovery" and self.aggregate_sep(module)
                 and (key.startswith("first_model.inputs.") or any(row.get("spec_id") == key
                      for row in module["first_model"].get("inputs", []) if isinstance(row, dict))))
        if split or key.startswith("separation.targets.") or (
                key.startswith("targets.") and context.get("kind") in ("recovery", "purity", "cut")):
            return "split" if split else "separation"
        if (key.startswith("reaction.extent.") and len(module.get("reaction", {}).get("network", [])) == 1
              and context.get("kind") in ("conversion", "model_determined") and context.get("pass_basis") == "per_pass"):
            return "conversion"
        return None

    def net_target_value(self, kind, planned, native, results):
        if kind == "conversion":
            return self.single_reaction_conversion(planned, native, results)
        return self.separation_target_value(planned, native, results, complete_allocation=kind == "split")

    def design_projection(self, tag, key, planned, rule, path, native, results, where, label):
        entry = self.at_path(native, path) if _text(path) and path.startswith("design_readbacks.") else None
        if not self.require(isinstance(entry, dict) and entry.get("unit_or_basis") == planned["unit_or_basis"]
                            and entry.get("basis") == planned["basis"] and entry.get("design_context", {}) == planned.get("design_context", {})
                            and "value" in entry, "ISLAND_SPEC_READBACK", where,
                            f"Read the same design definition, value, units and denominator from the {label} export"):
            return None
        kind = self.net_target_kind(tag, key, planned)
        if kind:
            actual = self.net_target_value(kind, planned, native, results)
        else:
            actual = self.native_design_value(entry.get("native_path"), planned["unit_or_basis"], native, results,
                                              require_output=rule.get("design_target", False) or rule["mode"] == "determined")
        stated = entry["value"]
        matches = (math.isclose(stated, actual, rel_tol=1e-9, abs_tol=1e-10) if _finite(stated) and (_finite(actual) or isinstance(actual, Fraction))
                   else type(stated) is type(actual) and _text(stated) and stated == actual)
        if not self.require(matches, "DESIGN_RESULT_NOT_VERIFIED", where,
                            {"stage_readback": label, "declared": stated, "actual_native": float(actual) if isinstance(actual, Fraction) else actual}):
            return None
        return {**entry, "value": actual}

    def scaffold_targets(self):
        if self.require_buildable_plan:
            for tag, rules in getattr(self, "buildable_operating_rules", {}).items():
                for key, rule in rules.items():
                    planned = self.buildable_review_specs[tag][key]
                    if rule.get("design_target") and _finite(planned["value"]):
                        yield tag, key, rule, planned

    def has_scaffold_targets(self):
        return next(self.scaffold_targets(), None) is not None

    def scaffold_design_targets(self, exported_modules, results):
        for tag, key, rule, planned in self.scaffold_targets():
            native = exported_modules.get(tag, {})
            where = f"scaffold.{tag}.{key}"
            if not self.require(all(self.native_material_ids(native, side) == self.native_material_ids(self.modules[tag], side)
                                    for side in ("inlets", "outlets")), "DESIGN_RESULT_BOUNDARY_MISMATCH", where,
                                "Use the original material boundary for the scaffold target"):
                continue
            kind = self.net_target_kind(tag, key, planned)
            if kind:
                actual = self.net_target_value(kind, planned, native, results)
            else:
                paths = native.get("design_readback_paths", {})
                path = paths.get(key) if isinstance(paths, dict) else None
                if isinstance(paths, dict) and key not in paths and isinstance(native.get("design_readbacks"), dict):
                    matches = [name for name, entry in native["design_readbacks"].items()
                               if isinstance(name, str) and isinstance(entry, dict) and _text(entry.get("native_path"))
                               and entry.get("unit_or_basis") == planned["unit_or_basis"] and entry.get("basis") == planned["basis"]
                               and entry.get("design_context", {}) == planned.get("design_context", {})]
                    same_targets = [other for other_tag, _, _, other in self.scaffold_targets() if other_tag == tag
                                    and all(other.get(k) == planned.get(k) for k in ("unit_or_basis", "basis", "design_context"))]
                    if len(matches) == len(same_targets) == 1:
                        path = "design_readbacks." + matches[0]
                entry = self.design_projection(tag, key, planned, rule, path, native, results, where, "scaffold")
                actual = entry["value"] if entry else None
            self.require(_meets_design(actual, planned["value"], rule), "FIRST_RUN_MISSES_DESIGN", where,
                         {"actual_native": float(actual) if isinstance(actual, Fraction) else actual,
                          "target": planned["value"], "unit": planned["unit_or_basis"],
                          **({"exact_ratio_in_target_units": str(actual)} if isinstance(actual, Fraction) else {})})

    def island_design_specs(self, tag, boundary, original, refined, baseline_results, refined_results, *, stage="island"):
        """Apply the original source obligation to actual island and reconnected results."""
        where = f"{stage}.{tag}.design_specifications"
        mapping = self.obj(boundary.get("design_specifications"), where)
        self.require(mapping.get("article_sha256") == (self.buildable_article_ref or {}).get("sha256"),
                     "ISLAND_PLAN_VERSION", where, "Use the reviewed article that specified the first flowsheet")
        for side in ("inlets", "outlets"):
            self.require(self.native_material_ids(refined, side) == self.native_material_ids(boundary, side),
                         "DESIGN_RESULT_BOUNDARY_MISMATCH", where + "." + side,
                         "The current results must cover the original net material boundary")
        rules = self.buildable_operating_rules.get(tag, {})
        specs = self.buildable_review_specs.get(tag, {})
        fields = self.obj(mapping.get("parameters"), where + ".parameters")
        self.require(set(fields) == set(rules), "ISLAND_PLAN_COVERAGE", where,
                     {"missing": sorted(set(rules) - set(fields)), "extra": sorted(set(fields) - set(rules))})
        for key in sorted(rules.keys() & fields.keys()):
            rule, planned = rules[key], specs[key]
            location = where + "." + key
            field = self.obj(fields[key], location)
            observed = []
            checks = [("refined", refined, refined_results)] if stage == "reconnect" else [
                ("baseline", original, baseline_results), ("refined", refined, refined_results)]
            for label, native, results in checks:
                observed.append(self.design_projection(tag, key, planned, rule, field.get(label + "_path"),
                                                       native, results, location, stage if stage == "reconnect" else label))
            if any(entry is None for entry in observed):
                continue
            result = observed[-1]["value"]
            nominal = planned["value"]
            mode = rule["mode"]

            if mode == "determined" and not rule.get("design_target"):
                # A calculated initial value fixes the design basis, not a second Aspen input.
                self.require(all(_finite(entry["value"]) for entry in observed) and field.get("use", "preserve") == "preserve"
                             and all(entry.get("governing_relation") == nominal for entry in observed),
                             "ISLAND_SOLVED_BASIS", location, "Retain the source equation and read both calculated values")
                continue
            if stage == "island":
                self.require(_meets_design(observed[0]["value"], nominal, rule), "FIRST_RUN_MISSES_DESIGN", location,
                             "The observed result does not establish the frozen target; check the reporting precision and the actual operating point")
            if field.get("use") == "vary":
                bounds = rule.get("bounds", {})
                permitted = (not rule.get("design_target") and mode == "adjustable" and _finite(result) and _finite(bounds.get("lower"))
                             and _finite(bounds.get("upper")) and bounds["lower"] <= result <= bounds["upper"])
                self.require(permitted, "ISLAND_VARY_OUTSIDE_PLAN", location,
                             "Only a stated operating variable may move, and only inside the approved range")
            else:
                self.require(field.get("use", "preserve") in ("preserve", "solve_target", "verification")
                             and _meets_design(result, nominal, rule),
                             "ISLAND_DESIGN_SPEC_MISSED" if stage == "island" else "RECONNECT_DESIGN_SPEC_MISSED", location,
                             "Hold the first-version design requirement in the current actual results")

    def island_equipment_gate(self, tag, item, run_record, run_export):
        """Require the existing selector receipt after each island's rigorous run."""
        receipt = self.read(item.get("equipment_gate_ref"), "island." + tag + ".equipment_gate_ref")
        if receipt is None:
            self.need("ISLAND_EQUIPMENT_GATE_REQUIRED", tag,
                      "Run design_stage(stage=island) on the exact refined island export before reconnecting")
            return
        receipt = self.obj(receipt, "island." + tag + ".equipment.receipt")
        self.require(receipt.get("schema") == "chemical-design-stage-receipt-v1"
                     and receipt.get("stage") == "island"
                     and receipt.get("status") == "MODULE_CHECKS_EXECUTED"
                     and receipt.get("needs") == [], "ISLAND_EQUIPMENT_GATE_INCOMPLETE", tag,
                     "A completed island selector calculation receipt is required; stage status is not engineering acceptance")
        declared_hash = receipt.get("receipt_sha256")
        self.require(_text(declared_hash) and declared_hash.lower() == _canonical({k: v for k, v in receipt.items() if k != "receipt_sha256"}),
                     "ISLAND_EQUIPMENT_RECEIPT_HASH", tag, "Preserve the original stage receipt bytes and internal digest")
        identity = self.obj(receipt.get("identity"), "island." + tag + ".equipment.identity")
        self.require(identity.get("case_id") == self.identity.get("case_id")
                     and identity.get("run_id") == run_record.get("run_id"),
                     "ISLAND_EQUIPMENT_RUN_MISMATCH", tag, "Equipment checks must use this island run")
        canonical = self.read(identity.get("source_export"), "island." + tag + ".equipment.source_export")
        if canonical is None:
            return
        canonical = self.obj(canonical, "island." + tag + ".equipment.source_export")
        self.require(canonical.get("schema") == "equipment-process-canonical-export-v1"
                     and canonical.get("case_id") == self.identity.get("case_id")
                     and canonical.get("run_id") == run_record.get("run_id")
                     and canonical.get("model_sha256") == (run_record.get("model_ref") or {}).get("sha256")
                     and canonical.get("raw_export_sha256") == (run_export.get("raw_export_ref") or {}).get("sha256"),
                     "ISLAND_EQUIPMENT_EXPORT_MISMATCH", tag,
                     "Equipment export must bind the exact island model and raw result export")
        exported_rows = [row for row in run_export.get("modules", [])
                         if isinstance(row, dict) and row.get("module_id") == tag]
        physical_ids = exported_rows[0].get("physical_equipment_ids") if len(exported_rows) == 1 else None
        self.require(isinstance(physical_ids, list) and physical_ids
                     and all(_text(device) for device in physical_ids)
                     and len(set(physical_ids)) == len(physical_ids),
                     "ISLAND_PHYSICAL_INVENTORY_REQUIRED", tag,
                     "List the physical equipment of this isolated module, including necessary auxiliaries")
        expected = set(physical_ids) if isinstance(physical_ids, list) and all(_text(x) for x in physical_ids) else set()
        inventory = canonical.get("equipment")
        canonical_ids = set(inventory) if isinstance(inventory, dict) else set()
        coverage = self.obj(receipt.get("inventory_coverage"), "island." + tag + ".equipment.coverage")
        declared = coverage.get("declared_ids")
        declared_ids = set(declared) if isinstance(declared, list) and all(_text(x) for x in declared) else set()
        self.require(bool(expected) and expected == canonical_ids == declared_ids,
                     "ISLAND_EQUIPMENT_COVERAGE", tag,
                     "Every exported physical tag, including auxiliary devices, must be calculated exactly once")
        rows = receipt.get("equipment")
        calculated = set()
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                device = row.get("equipment_id")
                if _text(device):
                    calculated.add(device)
                feedback = row.get("feedback") if isinstance(row.get("feedback"), dict) else {}
                feedback_result = feedback.get("result") if isinstance(feedback.get("result"), dict) else {}
                plans = feedback_result.get("equipment", [])
                result = row.get("result") if isinstance(row.get("result"), dict) else {}
                self.require(row.get("status") == "EXECUTED"
                             and result.get("backend_exit_code") == 0
                             and feedback.get("status") == "EXECUTED"
                             and isinstance(plans, list) and len(plans) == 1 and isinstance(plans[0], dict)
                             and plans[0].get("equipment_id") == device
                             and plans[0].get("binding_gaps") == []
                             and plans[0].get("revision") is None,
                             "ISLAND_EQUIPMENT_PENDING", f"{tag}:{device}",
                             "Resolve selector/input gaps and real limits, then rerun and reselect the revised island")
        self.require(isinstance(rows, list) and calculated == expected and len(rows) == len(expected),
                     "ISLAND_EQUIPMENT_CALCULATION_COVERAGE", tag,
                     "One current selector and feedback result is required for every physical device")

    def reconnect(self, contract, islands):
        current, exported = self.run(contract.get("current_run_ref"), "current_run_ref", current=True)
        needs_results = self.require_buildable_plan and any(self.buildable_operating_rules.get(tag) for tag in self.scope)
        current_results = self.native_design_results(current, "reconnect.current") if needs_results else {}
        modules = {}
        for raw in self.rows(exported.get("modules"), "current.export.modules"):
            row = self.obj(raw, "current.export.module")
            tag = row.get("module_id")
            self.require(_text(tag) and tag not in modules, "RECONNECT_MODULE_DUPLICATE_OR_INVALID", "current.export.modules", "Unique nonempty module IDs required")
            if _text(tag): modules[tag] = row
        replacements = {}
        for raw in self.rows(contract.get("replacements"), "replacements"):
            row = self.obj(raw, "replacement")
            tag = row.get("module_id")
            if isinstance(tag, str):
                self.require(tag not in replacements, "DUPLICATE_REPLACEMENT", tag, "One current replacement per module")
                replacements[tag] = row
        self.require(set(modules) == set(self.modules), "RECONNECT_TOPOLOGY_COVERAGE", "reconnect", "Current full-flow export must retain all source modules, including untouched ones")
        for tag in self.scope:
            row = self.obj(replacements.get(tag), "replacement." + tag)
            evidence = self.read(row.get("evidence_ref"), "replacement." + tag + ".evidence_ref")
            if evidence is not None:
                self.identity_check(evidence, "replacement." + tag)
                for field in ("module_id", "module_revision", "island_run_id", "original_node_ids", "replacement_node_ids", "installed_run_id"):
                    self.require(evidence.get(field) == row.get(field), "REPLACEMENT_RECORD_MISMATCH", tag, field)
            expected = self.modules[tag]
            self.require(row.get("module_revision") == expected.get("module_revision")
                         and row.get("original_node_ids") == expected.get("node_ids")
                         and row.get("island_run_id") == islands.get(tag, {}).get("run_id"),
                         "STALE_REPLACEMENT", tag, "Only this current module's accepted island can replace its original location")
            self.require(row.get("installed_run_id") == current.get("run_id"), "REPLACEMENT_RUN_MISMATCH", tag, "Rerun after replacement")
            node_ids = self.rows(row.get("replacement_node_ids"), "replacement." + tag + ".replacement_node_ids")
            self.require(modules.get(tag, {}).get("node_ids") == node_ids
                         and modules.get(tag, {}).get("module_revision") == expected.get("module_revision"),
                         "REPLACEMENT_EXPORT_MISMATCH", tag, "Current native export must contain the stated replacement and revision")
            self.require(modules.get(tag, {}).get("thermodynamics") == self.current_thermodynamics.get(tag, expected.get("thermodynamics")),
                         "RECONNECT_PROPERTY_MISMATCH", tag, "Reconnected export must keep the current module's reviewed property basis")
            if self.require_buildable_plan:
                boundary = getattr(self, "island_design_boundaries", {}).get(tag)
                if self.require(boundary is not None, "RECONNECT_DESIGN_BASIS_REQUIRED", tag,
                                "Recover the exact reviewed source design mapping from the replaced island"):
                    self.island_design_specs(tag, boundary, {}, modules.get(tag, {}), {}, current_results, stage="reconnect")

    def evaluate(self, contract):
        self.contract = contract
        self.require(contract.get("schema") == SCHEMA, "CONTRACT_SCHEMA_INVALID", "contract", SCHEMA)
        for key in ("case_id", "task_revision"):
            self.text(contract.get(key), "contract." + key)
            self.identity[key] = contract.get(key)
            if self.payload.get(key) is not None:
                self.require(self.payload[key] == contract.get(key), "CONTRACT_CURRENT_IDENTITY", "contract", key)
        authority = self.documents.get("authority", {})
        for key in ("case_id", "task_revision"):
            if key in authority:
                self.require(authority[key] == contract.get(key), "CONTRACT_AUTHORITY_IDENTITY", "contract", key)
        for index, raw in enumerate(self.rows(contract.get("modules"), "modules")):
            module = self.obj(raw, f"modules[{index}]")
            tag = module.get("id")
            self.require(_text(tag) and tag not in self.modules, "MODULE_ID_INVALID", "modules", "Unique module ID required")
            if _text(tag):
                self.modules[tag] = module
                self.module_basis(module, "module." + tag)
        stage = self.payload.get("stage")
        self.require(stage in STAGES, "FULLFLOW_STAGE_REQUIRED", "stage", "Use the actual current engineering stage")
        scope = self.obj(contract.get("scope"), "scope")
        mode = scope.get("mode")
        self.require(mode in {"fullflow", "module"}, "FULLFLOW_SCOPE_REQUIRED", "scope", "Explicit fullflow/module scope required")
        if mode == "module":
            ids = self.rows(scope.get("module_ids"), "scope.module_ids")
            self.require(all(_text(x) and x in self.modules for x in ids) and len(set(str(x) for x in ids)) == len(ids),
                         "FULLFLOW_SCOPE_INVALID", "scope", "Current module IDs must belong to the source flow")
            self.scope = [x for x in ids if isinstance(x, str) and x in self.modules]
        else:
            self.scope = list(self.modules)
        if stage in {"source", "scaffold", "delivery"}:
            self.scope = list(self.modules)
        self.summary["equipment_scope"] = {"mode": "fullflow" if stage in {"source", "scaffold", "delivery"} else mode,
            "module_ids": self.scope, "whole_flow_required": stage != "source" and (mode == "fullflow" or stage in {"scaffold", "delivery"})}
        for name, function, applies in (
            ("source", self.source, True),
            ("scaffold", self.scaffold, stage in {"scaffold", "island", "reconnect", "change", "delivery"}),
        ):
            before = len(self.needs)
            if applies:
                function(contract)
            self.summary[name] = {"required": applies, "status": "NOT_REQUIRED" if not applies else
                ("NEEDS_EVIDENCE" if len(self.needs) > before else "STRUCTURE_CONSISTENT")}
        for name in ("island", "reconnect"):
            self.summary[name] = {"required": False, "status": "NOT_REQUIRED"}
        if stage in {"island", "reconnect", "change", "delivery"}:
            before = len(self.needs)
            islands = self.islands(contract)
            self.summary["island"] = {"required": True, "status": "NEEDS_EVIDENCE" if len(self.needs) > before else "STRUCTURE_CONSISTENT"}
            if stage != "island":
                before = len(self.needs)
                self.reconnect(contract, islands)
                self.summary["reconnect"] = {"required": True, "status": "NEEDS_EVIDENCE" if len(self.needs) > before else "STRUCTURE_CONSISTENT"}


_WHOLE_FLOW = r"(?:全流程|整厂|完整(?:工艺)?流程|完整工艺|full[- ]?(?:process|flow(?:sheet)?)|whole[- ]plant|plant[- ]wide)"
_FLOW_ACTION = r"(?:生成|建立|搭建|构建|建模|细化|替换|接回|交付|校核|修复|generate|generation|build|construct|model|reconnect|deliver|check|repair)"
_SAME_CLAUSE = r"[^，,。；;！？!?\n]"
_NARROW_REQUEST = re.compile(
    r"(?:仅|只)(?:需要|需|要|做|看|讨论)?(?:一张|一份)?(?:路线图|流程图|概念草案|路线讨论|工艺路线)"
    r"|(?:仅|只)(?:先)?(?:讨论|解释|画|排版)|改写|图示对照|解释原理"
    r"|^\s*(?:(?:请|帮我|先)\s*){0,3}(?:画|绘制|出)(?:一张|一份)?" + _SAME_CLAUSE + r"{0,20}(?:方案图|流程图|路线图|PFD)\s*[。！!]?$"
    r"|^\s*(?:(?:please|only|just)\s+)?(?:rewrite|reformat|explain)\b|\b(?:diagram|wording)\s+only\b"
    r"|^\s*(?:(?:please|only|just)\s+)?(?:read|extract|report|show)\b" + _SAME_CLAUSE + r"{0,24}\b(?:temperatures?|pressures?|results?|stream\s+values?)\b"
    r"|(?:不(?:需要|要求|做|用|必)|无需)" + _SAME_CLAUSE + r"{0,14}"
    r"(?:可直接建模|首版建模规划|各单元(?:的)?参数|逐单元参数|模型参数)", re.I)
_LOCAL_REQUEST = re.compile(
    r"单塔|单模块|单个(?:设备|模块|工段)|(?:现有|已有|这个|该)(?:精馏|分离|反应|热泵)?(?:塔岛|工段|塔|岛)"
    r"|\b(?:single|existing)[- ](?:column|island|unit)\b", re.I)


def _describes_whole_flow_action(question):
    if _LOCAL_REQUEST.search(question):
        # A plant mentioned as context for a local operation is not its object.
        return bool(re.search(_FLOW_ACTION + r"\s*(?:当前|新的|整个|the\s+)?\s*" + _WHOLE_FLOW, question, re.I))
    gap = _SAME_CLAUSE + r"{0,20}"
    return bool(re.search(_WHOLE_FLOW + gap + _FLOW_ACTION + "|" + _FLOW_ACTION + gap + _WHOLE_FLOW, question, re.I))


def buildable_plan_requested(payload, authority=None):
    """Recognize a request to specify a first model, also when only prose is delivered."""
    authority = authority if isinstance(authority, dict) else {}
    if (payload.get("source_work") == "buildable_plan"
            or authority.get("planning_scope") == "buildable_flowsheet"
            or authority.get("workflow_profile") == "fullflow_generation"):
        return True
    question = payload.get("question", "")
    if payload.get("stage", "source") != "source" or not isinstance(question, str) or _NARROW_REQUEST.search(question):
        return False
    if _LOCAL_REQUEST.search(question) and not _describes_whole_flow_action(question):
        return False
    direct = (r"(?:可直接|能直接|无歧义|没有歧义|可据以|可开工|开工版).{0,12}(?:建模|搭建|规划|搭模)"
              r"|(?:首版|第一版|初版).{0,14}(?:流程模型|模型规划|全流程|简化模型|流程.{0,4}参数|模型参数|工艺流程)"
              r"|(?:项目|装置|工艺流程|全流程|Aspen(?:\s+Plus)?).{0,32}(?:建立|搭建|构建).{0,12}(?:简化|稳态|首版).{0,6}模型"
              r"|(?:从头|从零).{0,8}(?:设计|规划|搭建|建模).{0,24}(?:一套|整套).{0,16}(?:装置|流程|项目)"
              r"|直接.{0,20}(?:首版|第一版|初版).{0,8}(?:建|搭|复建)"
              r"|(?:能|可)(?:直接)?(?:复建|重建|搭出).{0,8}(?:首版|第一版|初版)"
              r"|\b(?:build[- ]ready|model[- ]ready|ready[- ]to[- ](?:build|model))\b")
    if re.search(direct, question, re.I):
        return True
    plan = r"(?:规划|方案|设计|建模|搭建|构建|建立|生成|build|construct|generat\w*|model(?:l?ing)?|plan(?:ning)?)"
    gap = _SAME_CLAUSE + r"{0,20}"
    return bool(re.search(_WHOLE_FLOW + gap + plan + "|" + plan + gap + _WHOLE_FLOW, question, re.I))


def check_fullflow(payload, evidence_root, documents=None):
    """Inspect explicit/full-flow-intent evidence; never write files or execute models."""
    payload = payload if isinstance(payload, dict) else {}
    documents = documents if isinstance(documents, dict) else {}
    authority = documents.get("authority", {})
    question = payload.get("question", "")
    explicit = "fullflow_contract" in payload
    intended = (isinstance(question, str) and not _NARROW_REQUEST.search(question)
                and _describes_whole_flow_action(question))
    buildable = buildable_plan_requested(payload, authority)
    required = explicit or buildable or intended
    result = {"required": required, "buildable_plan_required": buildable, "status": "NOT_APPLICABLE", "needs": [], "required_reading": [],
              "gate_summary": {}, "engineering_accepted": False, "execution_verified": False,
              "stage_advanced": False, "boundary": BOUNDARY}
    if not required:
        return result
    gate = _Gate(payload, evidence_root, documents)
    gate.summary["equipment_scope"] = {"mode": "fullflow", "module_ids": [],
        "whole_flow_required": payload.get("stage") in {"scaffold", "reconnect", "change", "delivery"},
        "scope_verified": False}
    try:
        result["required_reading"] = _readings()
        contract = gate.read(payload.get("fullflow_contract"), "fullflow_contract")
        if contract is not None:
            source_gate = contract.get("source_gate") if isinstance(contract, dict) else None
            gate.require_buildable_plan = (buildable or contract.get("planning_scope") == "buildable_flowsheet"
                                           or (isinstance(source_gate, dict) and "planning_article_ref" in source_gate))
            result["buildable_plan_required"] = gate.require_buildable_plan
            if gate.require_buildable_plan and isinstance(source_gate, dict) and "planning_handoff" in payload:
                expected = source_gate.get("handoff_input_ref")
                actual = payload["planning_handoff"]
                gate.require(isinstance(expected, dict) and isinstance(actual, dict)
                             and expected.get("sha256") == actual.get("sha256"), "BUILDABLE_HANDOFF_MISMATCH", "source",
                             "Use the same handoff for the planning check and the independent source reviews")
            if gate.require_buildable_plan and contract.get("planning_scope") != "buildable_flowsheet":
                gate.need("BUILDABLE_SCOPE_REQUIRED", "contract",
                          "Freeze planning_scope=buildable_flowsheet on the contract so a later stage retains the first-model design basis")
            gate.evaluate(contract)
    except (ValueError, TypeError, KeyError, IndexError, OSError, AttributeError, RecursionError) as exc:
        gate.need("FULLFLOW_STRUCTURE_ERROR", "contract", f"{type(exc).__name__}: {exc}")
    if result["buildable_plan_required"]:
        result["planning_review_dispatch"] = (getattr(gate, "planning_review_dispatch", None)
                                              or _planning_review_dispatch())
    result.update(status="ACTION_REQUIRED" if gate.needs else "EVIDENCE_STRUCTURE_CONSISTENT",
                  needs=gate.needs, gate_summary=gate.summary)
    return result
