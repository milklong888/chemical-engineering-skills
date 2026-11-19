"""Check planning evidence for a later physical separation or reactor model."""
from __future__ import annotations

import math
import os
from pathlib import Path
import re
import subprocess
from unicodedata import normalize
from xml.etree import ElementTree
from zipfile import BadZipFile


_STRATEGIES = ("kinetic", "equilibrium", "lumped", "multi_condition", "balance")
_PLACEHOLDER = re.compile(
    r"^(?:tbd|tba|unknown|none|later|to be decided|see (?:later|literature)|"
    r"待定|待查|后续查找|见文献|暂缺|不详)[.!。]?$", re.IGNORECASE
)
_UNAVAILABLE = re.compile(
    r"\b(?:not reported|not supplied|not available|undisclosed|to be determined)\b|未报道|未报告|未给出|尚未确定",
    re.IGNORECASE,
)


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and not _PLACEHOLDER.fullmatch(value.strip())


def _words(value):
    return " ".join(value.split())


def _pdftotext(path, page):
    # Search configured local directories without implicitly executing from the case CWD.
    name = "pdftotext.exe" if os.name == "nt" else "pdftotext"
    directories = (Path(folder.strip('"')) for folder in os.get_exec_path() if folder)
    reader = next((folder / name for folder in directories
                   if folder.is_absolute() and (folder / name).is_file() and os.access(folder / name, os.X_OK)), None)
    if reader is None:
        raise ValueError("Local PDF text reader unavailable; retain a source extract with original page/section locator")
    try:
        result = subprocess.run([str(reader), "-f", str(page), "-l", str(page), "-layout", "-enc", "UTF-8",
                                 str(path), "-"], capture_output=True, timeout=15, check=False,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"Local PDF text reader could not extract physical page {page}") from exc
    if result.returncode:
        raise ValueError(f"Local PDF text reader could not extract physical page {page}")
    return result.stdout.decode("utf-8-sig")


def _pypdf_text(path, page):
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    try:
        with path.open("rb") as handle:
            return PdfReader(handle).pages[page - 1].extract_text()
    except (PyPdfError, IndexError) as exc:
        raise ValueError(f"Cannot read text on physical PDF page {page}") from exc


def _pdf_text(path, page):
    """Read one physical page and number its nonempty text lines."""
    try:
        text = _pypdf_text(path, page)
    except ImportError:
        text = _pdftotext(path, page)
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"No machine-readable text on physical PDF page {page}; retain a checked source extract")
    return "\n".join(line for line in text.splitlines() if line.strip())


def _passage(gate, record, where, read_article):
    """Verify a quote against retained source bytes at its declared text line."""
    ref = gate.read(record.get("source_ref"), where + ".source_ref", json_value=False)
    if "original_ref" in record:
        gate.read(record["original_ref"], where + ".original_ref", json_value=False)
    locator, quote = record.get("locator"), record.get("excerpt")
    path = Path(ref["path"]) if ref else None
    pdf = path is not None and path.suffix.casefold() == ".pdf"
    line_pattern = r"L(?P<line>[1-9][0-9]{0,7})"
    pattern = r"P(?P<page>[1-9][0-9]{0,7}):" + line_pattern if pdf else line_pattern
    match = re.fullmatch(pattern, locator) if isinstance(locator, str) else None
    if path is None or not match or not all(_text(record.get(k)) for k in ("citation", "source_locator", "excerpt")):
        gate.need("PLAN_RESEARCH_SOURCE_PASSAGE", where,
                  "Keep the identifiable original source with page/table/equation locator, plus the quote and L-number in retained text or P<n>:L<n> in a PDF")
        return None
    if isinstance(getattr(gate, "buildable_article_ref", None), dict) and ref["sha256"] == gate.buildable_article_ref.get("sha256"):
        gate.need("PLAN_RESEARCH_SOURCE_PASSAGE", where,
                  "Read the original technical source or retain its extract; quoting this planning article only repeats the design claim")
        return None
    try:
        content = _pdf_text(path, int(match["page"])) if pdf else read_article(path)
    except (OSError, ValueError, KeyError, BadZipFile, ElementTree.ParseError) as exc:
        gate.need("PLAN_RESEARCH_SOURCE_PASSAGE", where, f"Read the located original technical passage or retain its text extract: {exc}")
        return None
    lines = content.splitlines()
    start = int(match["line"]) - 1
    span = "\n".join(lines[start:start + len(quote.splitlines())])
    matches_bytes = _words(quote) in _words(span) if pdf else quote in span
    if not gate.require(matches_bytes, "PLAN_RESEARCH_SOURCE_PASSAGE", where,
                        "Match the exact words at the declared retained source line"):
        return None
    return _words(quote)


def _quoted(value, passages):
    return _text(value) and any(_words(value) in passage for passage in passages)


def _species_in(passages, species):
    species = normalize("NFKC", species)
    if re.fullmatch(r"[A-Za-z0-9_-]+", species):
        pattern = r"(?<![A-Za-z0-9])" + re.escape(species) + r"(?![A-Za-z0-9])"
        flags = 0 if len(species) == 1 else re.IGNORECASE
        return any(re.search(pattern, normalize("NFKC", passage), flags) for passage in passages)
    return any(species in normalize("NFKC", passage) for passage in passages)


def _check_same_system(gate, module, section, row, passages, where):
    """Catch missing source identity and explicit, same-unit scope contradictions."""
    if row.get("transfer_scope") != "same_system" or not passages:
        return
    role = module["role"]
    if role == "reaction" and row.get("strategy") not in ("kinetic", "multi_condition"):
        return
    code = "PLAN_RESEARCH_SYSTEM_MISMATCH"
    feed = {k for inlet in module.get("inlets", []) if isinstance(inlet, dict)
            for k in inlet.get("composition", {}) if _text(k)}
    if role == "reaction":
        required = {x["key_reactant"] for x in section.get("extent", []) if isinstance(x, dict) and _text(x.get("key_reactant"))}
        reactants = [re.split(r"\s*(?:<=>|<->|=>|->|→|⇌|↔|=)\s*", str(x.get("equation")))[0]
                     for x in section.get("network", []) if isinstance(x, dict)]
        required |= {component for component in feed if _species_in(reactants, component)}
    else:
        required = {x["component"] for x in section.get("targets", []) if isinstance(x, dict) and _text(x.get("component"))}
        identified = {component for component in feed if _species_in(passages, component)}
        gate.require(len(identified) >= min(2, len(feed)), code, where,
                     "A same-system separation source must identify the case separation pair or medium and solute")
    missing = sorted(species for species in required if not _species_in(passages, species))
    gate.require(not missing, code, where, {"unidentified_case_species": missing})

    basis = row.get("basis") or {}
    scope = basis.get("validity" if role == "reaction" else "operating_range")
    if not _quoted(scope, passages):
        return
    number = r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)"
    span = rf"(?<![\d.])({number})\s*(?:[-–—~～]|to\b|至)\s*({number})"
    for condition in section.get("conditions", []):
        if not isinstance(condition, dict) or condition.get("name") not in ("temperature", "pressure"):
            continue
        value, unit = condition.get("value"), condition.get("unit_or_basis")
        if type(value) not in (int, float) or not math.isfinite(value) or not _text(unit):
            continue
        ranges = re.findall(span + r"\s*" + re.escape(unit.strip()) + r"(?![A-Za-z])", scope, re.I)
        if len(ranges) == 1:
            lower, upper = map(float, ranges[0])
            gate.require(lower <= value <= upper, "PLAN_RESEARCH_WINDOW_MISMATCH", where,
                         {"condition": condition["name"], "nominal": value, "source_range": [lower, upper], "unit": unit})


def _rows(gate, value, code, where, detail):
    return value if gate.require(isinstance(value, list) and bool(value), code, where, detail) else []


def _passages(gate, row, where, read_article):
    evidence = _rows(gate, row.get("evidence"), "PLAN_RESEARCH_SOURCE_PASSAGE", where + ".evidence",
                     "Read and retain actual technical content from the relevant source")
    passages = []
    for i, raw in enumerate(evidence):
        at = f"{where}.evidence.{i}"
        quote = _passage(gate, gate.obj(raw, at), at, read_article)
        if quote:
            passages.append(quote)
    return passages


def _measurements(gate, basis, passages, where, code):
    conditions = set()
    for i, raw in enumerate(_rows(gate, basis.get("measurements"), code, where,
                                  "Provide checked measurements at multiple distinct operating states")):
        row = gate.obj(raw, f"{where}.{i}")
        condition, result, unit = row.get("condition"), row.get("result"), row.get("unit_or_basis")
        pair, value = row.get("source_basis"), row.get("value")
        measured = type(value) is int or (type(value) is float and math.isfinite(value))
        literals = re.findall(r"(?<![\d.])[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", str(result))
        if gate.require(_quoted(pair, passages) and _quoted(condition, [_words(pair)]) and _quoted(result, [_words(pair)])
                        and measured and any(float(x) == value for x in literals) and _text(unit) and unit in result,
                        code, f"{where}.{i}",
                        "Keep a paired checked passage with the operating condition and numeric measured response on its stated unit/basis"):
            conditions.add(_words(condition))
    gate.require(len(conditions) >= 2, code, where,
                 "A single fixed conversion or repeated condition cannot support a multi-condition response model")


def _candidate(gate, row, where, selected, role, read_article):
    for field in ("id", "method", "mechanism", "applicability", "assessment"):
        gate.require(_text(row.get(field)), "PLAN_RESEARCH_CANDIDATE", where + "." + field,
                     "State the actual method, mechanism, case operating applicability and reason to retain or rule it out")
    gate.require(row.get("transfer_scope") in ("same_system", "analog"), "PLAN_RESEARCH_CANDIDATE",
                 where + ".transfer_scope", "Classify the studied system; explain transfer and excluded transfers in applicability")
    passages = _passages(gate, row, where, read_article)
    strategy = row.get("strategy")
    if role == "reaction":
        gate.require(strategy in _STRATEGIES, "PLAN_REACTION_RESEARCH_STRATEGY", where,
                     "Identify a kinetic, equilibrium, lumped, multi_condition or balance strategy")
    if not selected and not (role == "reaction" and strategy == "kinetic"):
        return passages
    basis = gate.obj(row.get("basis"), where + ".basis")
    if role == "separation":
        fields, code = ("phase_data", "operating_range"), "PLAN_SEPARATION_RESEARCH_BASIS"
        phases = basis.get("phases")
        gate.require(isinstance(phases, list) and bool(phases) and all(_text(x) for x in phases), code, where + ".basis.phases",
                     "State the phases or media used for the physical separation")
    elif strategy == "kinetic":
        # An excluded study can be evidenced by its tested scope or a specific missing input.
        fields = ("rate_law", "rate_units", "rate_basis", "parameters", "catalyst", "validity") if selected else ("validity",)
        code = "PLAN_REACTION_RESEARCH_BASIS"
    else:
        fields, code = ("relation", "validity"), "PLAN_REACTION_RESEARCH_BASIS"
        gate.require(_text(basis.get("limit")), code, where + ".basis.limit",
                     "Name the variables and operating response that this non-kinetic route cannot establish")
    for field in fields:
        value = basis.get(field)
        gate.require(_quoted(value, passages) and (not selected or not _UNAVAILABLE.search(value)), code, where + ".basis." + field,
                     "Extract this technical value, relation or scope from a checked source passage")
    if not selected:
        return passages
    if strategy == "multi_condition" and role == "reaction":
        _measurements(gate, basis, passages, where + ".basis.measurements", code)
    inputs = _rows(gate, row.get("mapped_inputs"), "PLAN_RESEARCH_INPUT_MAPPING", where + ".mapped_inputs",
                   "Identify what data or relation can actually map onto the chosen model")
    for i, raw in enumerate(inputs):
        at = f"{where}.mapped_inputs.{i}"
        mapped = gate.obj(raw, at)
        gate.require(_text(mapped.get("parameter")) and _quoted(mapped.get("source_basis"), passages)
                     and _text(mapped.get("model_use")), "PLAN_RESEARCH_INPUT_MAPPING", at,
                     "Name the physical model input, exact source datum/relation and basis conversion or permitted use")
    return passages


def check_module_research(gate, module, section, read_article):
    role = module["role"]
    where = f"module.{module['id']}.{role}.planning_research"
    code = f"PLAN_{role.upper()}_RESEARCH_REQUIRED"
    research = section.get("planning_research")
    summary = {"module_id": module["id"], "role": role, "status": "unresolved",
               "scope": where, "selected_candidate_id": None}
    if not gate.require(isinstance(research, dict), code, where,
                        "Read a technical source now and map the result to the later reactor or physical separation, even if the first model is RStoic or SEP"):
        return summary
    count_before = len(gate.needs)
    chosen = research.get("selected_candidate_id")
    criterion = research.get("selection_criterion")
    gate.require(_text(criterion), "PLAN_RESEARCH_SELECTION", where + ".selection_criterion",
                 "Explain which physical or operating criterion selects this route at the frozen target")
    candidates, selected = {}, None
    rows = _rows(gate, research.get("candidates"), code, where + ".candidates",
                 "Retain a source-based proposal and evaluate applicable alternatives now")
    for i, raw in enumerate(rows):
        at = f"{where}.candidates.{i}"
        row = gate.obj(raw, at)
        tag = row.get("id")
        if gate.require(_text(tag) and tag not in candidates, "PLAN_RESEARCH_CANDIDATE", at,
                        "Identify each distinct sourced candidate"):
            candidates[tag] = row
            if tag == chosen:
                selected = row
        passages = _candidate(gate, row, at, row is selected, role, read_article)
        if row is selected:
            _check_same_system(gate, module, section, row, passages, at)
    gate.require(selected is not None, "PLAN_RESEARCH_SELECTION", where + ".selected_candidate_id",
                 "Select one sourced method or combined method matching the project boundary")
    if not selected:
        return summary
    summary["selected_candidate_id"] = chosen
    if len(candidates) == 1:
        gate.require(_text(research.get("alternatives_limit")), "PLAN_RESEARCH_SELECTION", where + ".alternatives_limit",
                     "Compare a credible alternative or explain the case constraint that leaves one method")
    method = selected.get("method")
    gate.article_anchor(research, where)
    gate.require(_text(method) and method in str(research.get("article_excerpt", "")),
                 "PLAN_RESEARCH_SELECTION", where + ".article_excerpt",
                 "Put the selected later-model method in this revision of the editable planning article")

    strategy = selected.get("strategy")
    provisional_required = selected.get("transfer_scope") == "analog"
    provisional = research.get("provisional")
    response_open = False
    if role == "reaction":
        needs_response = research.get("response_required")
        gate.require(type(needs_response) is bool and _text(research.get("response_basis")),
                     "PLAN_REACTION_RESEARCH_STRATEGY", where + ".response_basis",
                     "State whether kinetic response is needed and identify the reaction, conditions and task requirement that decide it")
        if strategy != "kinetic":
            code = "PLAN_REACTION_RESEARCH_KINETICS_SCREEN"
            at = where + ".kinetics_exclusion"
            exclusion = research.get("kinetics_exclusion")
            if exclusion is not None:
                exclusion = gate.obj(exclusion, at)
                passages = _passages(gate, exclusion, at, read_article)
                gate.require(_quoted(exclusion.get("source_finding"), passages) and _text(exclusion.get("case_limit")),
                             code, at, "Quote the actual technical finding and explain how it limits use of formal kinetics in this case")
            elif not any(c.get("strategy") == "kinetic" for c in candidates.values()):
                gate.need(code, at, "Inspect an actual kinetic source, or substantiate why a rate model is inapplicable using checked technical evidence")
        response_open = needs_response is True and (strategy not in ("kinetic", "multi_condition")
                                                    or provisional_required or provisional is not None)
        provisional_required |= response_open
    if provisional is not None or provisional_required:
        provisional = provisional if isinstance(provisional, dict) else {}
        inputs = provisional.get("unresolved_inputs")
        gate.require(isinstance(inputs, list) and bool(inputs) and all(_text(x) for x in inputs)
                     and all(_text(provisional.get(k)) for k in ("refine_trigger", "independent_work")),
                     "PLAN_RESEARCH_PROVISIONAL_SCOPE", where + ".provisional",
                     "State the exact later-model gaps, evidence needed to close them and what can proceed on the existing baseline")
        if provisional:
            summary["unresolved_inputs"] = inputs
            summary["refine_trigger"] = provisional.get("refine_trigger")
            summary["independent_work"] = provisional.get("independent_work")

    key = "extent" if role == "reaction" else "targets"
    rows = section.get(key)
    specs = {f"{role}.{key}.{i}" for i in range(len(rows))} if isinstance(rows, list) else set()
    covered = set()
    code = "PLAN_RESEARCH_TARGET_MAPPING"
    mappings = _rows(gate, research.get("target_mappings"), code, where + ".target_mappings",
                     "Map the selected physical model to the frozen targets")
    for i, raw in enumerate(mappings):
        at = f"{where}.target_mappings.{i}"
        mapping = gate.obj(raw, at)
        spec = mapping.get("spec_id")
        if gate.require(_text(spec) and spec in specs and spec not in covered
                        and mapping.get("model_use") in ("input", "solve_target", "verification") and _text(mapping.get("basis")),
                        "PLAN_RESEARCH_TARGET_MAPPING", at,
                        "Map a distinct frozen target to a physical input, solve target or verification with the same inlet/outlet basis"):
            covered.add(spec)
    gate.require(covered == specs and bool(specs), "PLAN_RESEARCH_TARGET_MAPPING", where,
                 "Account for every frozen reaction extent or separation target: " + ", ".join(sorted(specs - covered)))
    if not response_open and len(gate.needs) == count_before:
        summary["status"] = "provisional" if provisional is not None else "supported"
    if response_open:
        summary["response_open"] = True
        gate.need("PLAN_REACTION_RESEARCH_RESPONSE_OPEN", where + ".response_basis",
                  "Complete the in-scope kinetic response evidence with a valid rate model or applicable multi-condition data; keep the fixed baseline and other modules separately usable")
    return summary
