"""Check final review evidence and inherited findings for a frozen engineering delivery."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

from backends.process.feedback import read_reference


REGISTER = "PROJECT_REVIEW_FINDINGS.json"
HISTORY = "PROJECT_REVIEW_HISTORY"


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def records(value, name, *, allow_empty=False):
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValueError(f"Supply the registered {name} list.")
    return value


def file_at(root, ref):
    if not isinstance(ref, dict) or set(ref) != {"path", "sha256"} or not nonempty(ref["path"]):
        raise ValueError("Expected an exact file path and SHA-256.")
    path = root / ref["path"]
    with path.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if digest != str(ref["sha256"]).lower():
        raise ValueError(f"File changed: {ref['path']}")
    return path


def document(root, ref):
    return json.loads(file_at(root, ref).read_text(encoding="utf-8-sig"))


def same_set(left, right):
    return (isinstance(left, list) and isinstance(right, list)
            and sorted(json.dumps(x, sort_keys=True) for x in left)
            == sorted(json.dumps(x, sort_keys=True) for x in right))


def evidence_value(data, path):
    if not nonempty(path):
        raise ValueError("Missing result path.")
    for part in path.split("."):
        data = data[int(part)] if isinstance(data, list) and part.isdigit() else data[part]
    return data


def native_record_path_matches(root, ref, record):
    return (isinstance(record, dict) and nonempty(record.get("path"))
            and (root / record["path"]).resolve() == (root / ref["path"]).resolve())


def native_record_matches(root, ref, record):
    return (native_record_path_matches(root, ref, record)
            and str(record.get("sha256", "")).lower() == ref["sha256"].lower())


def frozen_native_ref(reference, accepted_refs):
    if not isinstance(reference, dict) or reference not in accepted_refs:
        raise ValueError("Freeze each native audit and output readback reference in the delivery evidence.")
    return reference


def matching_native_run(record, run):
    return (record.get("run_id") == run["run_id"]
            and str(record.get("case_sha256", "")).lower() == run["case_sha256"].lower())


def verified_native_asset(root, ref, record, size):
    return (native_record_matches(root, ref, record) and record.get("exists") is True
            and type(record.get("size")) is int and record["size"] == size and size > 0)


def verify_native_report_producer(root, row, path, accepted_refs, audit, run, size):
    producer_ref = row.get("native_producer_ref")
    if not isinstance(producer_ref, dict) or producer_ref not in accepted_refs:
        raise ValueError("Freeze the actual same-run native producer receipt for the Aspen report.")
    producer = document(root, producer_ref)
    label = audit.get("label")
    inp = audit.get("after_run_inp") or {}
    association = inp.get("association", {})
    if (not nonempty(label) or not nonempty(inp.get("path")) or inp.get("role") != "input_export"
            or association.get("verified") is not True or not matching_native_run(association, run)):
        raise ValueError("The native producer output directory must be identified by the same-run audit.")
    native_dir = (root / inp["path"]).resolve().parent
    producer_path = (root / producer_ref["path"]).resolve()
    record = producer.get("rep")
    if (producer.get("run_id") != run["run_id"]
            or ("case_sha256" in producer and not matching_native_run(producer, run))
            or producer.get("moment") != "after Run2 before export and close"
            or not all(isinstance(producer.get(key), dict) for key in ("streams", "blocks"))
            or producer_path.parent != native_dir or producer_path.name.casefold() != f"{label}_streams_blocks.json".casefold()
            or path.resolve().parent != native_dir or path.name.casefold() != f"{label}_live{path.suffix}".casefold()
            or not verified_native_asset(root, row["evidence_ref"], record, size)):
        raise ValueError("The native producer must bind the current run's original report role, path, size and SHA-256.")


def native_review_text(root, row, path, accepted_refs, identity):
    import codecs
    from importlib.util import module_from_spec, spec_from_file_location
    from tools.fullflow_gate import _skill_root

    audit_ref = frozen_native_ref(row.get("native_audit_ref"), accepted_refs)
    audit = document(root, audit_ref)
    run = audit.get("run", {})
    if (audit.get("schema_version") != "aspen_clean_delivery_audit/3"
            or not run.get("case_sha256") or audit.get("run_id") != identity.get("run_id")
            or run.get("run_id") != identity.get("run_id") or run.get("status") != "completed"
            or not all(audit.get(key) is True for key in ("open_source_direct", "source_unchanged", "operation_completed"))):
        raise ValueError("Use the current completed native audit of the exact unedited model.")
    source = {"path": audit.get("source"), "sha256": audit.get("source_sha256")}
    model = next((ref for ref in accepted_refs if Path(ref["path"]).suffix.lower() in {".bkp", ".apw", ".apwz", ".inp"}
                  and native_record_matches(root, ref, source)), None)
    if model is None or model["sha256"].lower() != run["case_sha256"].lower():
        raise ValueError("The native audit must identify the frozen model path and bytes.")
    file_at(root, model)

    ref = row["evidence_ref"]
    raw = path.read_bytes()
    size = len(raw)
    suffix = path.suffix.lower()
    history = suffix == ".his"
    output = None
    if "native_output_index_ref" in row:
        index_ref = frozen_native_ref(row["native_output_index_ref"], accepted_refs)
        index = document(root, index_ref)
        if (index.get("schema") != "aspen-native-review-outputs-v1"
                or any(index.get(key) != value for key, value in identity.items())
                or index.get("model_ref") != model or index.get("native_audit_ref") != audit_ref):
            raise ValueError("The native output index must bind the current case, revision, model and audit.")
        matched = [item for item in records(index.get("outputs"), "native output entries") if item.get("raw_ref") == ref]
        if len(matched) != 1:
            raise ValueError("Locate this exact raw file once in the native output index.")
        output = matched[0]

    if history or suffix == ".inp":
        assets = audit.get("histories", []) if history else [audit.get("after_run_inp")]
        matched = [asset for asset in assets if verified_native_asset(root, ref, asset, size)]
        if len(matched) != 1:
            raise ValueError("The native audit must bind this exact raw output to the current run.")
        asset = matched[0]
        link = asset.get("association", {})
        if (link.get("verified") is not True or not matching_native_run(link, run)
                or not history and asset.get("role") != "input_export"):
            raise ValueError("The native output association is missing or belongs to another run.")
    else:
        sidecars = [record for record in audit.get("sidecars", []) if native_record_path_matches(root, ref, record)]
        if sidecars:
            sidecar = sidecars[0]
            link = sidecar.get("association", {})
            if (len(sidecars) != 1 or sidecar.get("evidence_role") != "current_run_candidate"
                    or not verified_native_asset(root, ref, sidecar, size)
                    or link.get("verified") is not True or not matching_native_run(link, run)):
                raise ValueError("The native audit report sidecar does not match the exact current run and bytes.")
        else:
            verify_native_report_producer(root, row, path, accepted_refs, audit, run, size)

    fallback = ()
    conversion = None if history or output is None else output.get("conversion")
    if history:
        encoding = asset.get("encoding_evidence", {})
        session_encoding = audit.get("encoding_evidence", {})
        codec = encoding.get("codec")
        if (asset.get("decode_verified") is True and all(encoding.get(key) is True for key in
                ("verified", "fallback_used", "fallback_eligible_for_current_history", "fallback_roundtrip_verified"))
                and matching_native_run(encoding, run)
                and matching_native_run(session_encoding, run)
                and str(encoding.get("history_sha256", "")).lower() == ref["sha256"].lower()
                and codec == f"cp{encoding.get('acp')}" and codec == session_encoding.get("codec")
                and encoding.get("source") == session_encoding.get("source") == "Windows kernel32.GetACP"):
            fallback = (codec,)
    elif conversion is not None:
        codec = conversion.get("codec")
        if not nonempty(codec):
            raise ValueError("State the decoder used for the exact native output conversion.")
        fallback = (codec,)

    installed_root = _skill_root()
    if installed_root is None:
        raise ValueError("The Aspen native evidence reader is unavailable.")
    spec = spec_from_file_location("review_native_aspen_evidence",
                                   installed_root / "aspen-plus-operations/scripts/aspen_evidence.py")
    reader = module_from_spec(spec)
    spec.loader.exec_module(reader)
    result = reader.decode_history_bytes(raw, verified_fallback_encodings=fallback)
    if result.get("verified") is not True or result["sha256"].lower() != ref["sha256"].lower():
        raise ValueError("Unable to strictly decode the exact native output with the bound evidence.")
    encoding = result["encoding"]
    content = result["text"]
    if encoding == "utf-16":
        bom = raw[:2]
        roundtrip = bom + content.encode("utf-16-le" if bom == codecs.BOM_UTF16_LE else "utf-16-be")
    else:
        roundtrip = content.encode(encoding)
    if roundtrip != raw:
        raise ValueError("The native output did not round-trip to the original bytes.")
    if conversion is not None:
        text_ref = frozen_native_ref(conversion.get("text_ref"), accepted_refs)
        normalized = file_at(root, text_ref).read_bytes().decode("utf-8")
        if normalized != content or codecs.lookup(codec) != codecs.lookup(encoding):
            raise ValueError("The supplied UTF-8 conversion does not match the exact native output.")
    return content


def verify_locator(root, row, *, accepted_refs=(), identity=None):
    import re
    from xml.etree.ElementTree import ParseError
    from zipfile import BadZipFile

    path = file_at(root, row["evidence_ref"])
    suffix = path.suffix.lower()
    locator = row["locator"]
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        value = evidence_value(data, locator)
        from tools.fullflow_gate import _same_observed_value
        if "observed_value" not in row or not _same_observed_value(row["observed_value"], value):
            raise ValueError(f"Review readback disagrees with {path.name} at {locator}")
        return data

    quote = row.get("excerpt")
    if not nonempty(quote):
        raise ValueError(f"Quote the actual contents of {path.name} at {locator}")
    if suffix == ".pdf":
        from tools.planning_research import _pdf_text
        marker = re.fullmatch(r"P([1-9][0-9]{0,7})(?::L([1-9][0-9]{0,7}))?", locator)
        if not marker:
            raise ValueError(f"Use physical PDF page P<n> or P<n>:L<n> in {path.name}")
        passage = _pdf_text(path, int(marker[1]))
        if marker[2]:
            lines = passage.splitlines()
            start = int(marker[2]) - 1
            passage = "\n".join(lines[start:start + len(quote.splitlines())])
        if " ".join(quote.split()) not in " ".join(passage.split()):
            raise ValueError(f"Quoted observation not found on {path.name} at {locator}")
        return None

    if suffix not in REVIEW_TEXT_SUFFIXES:
        raise ValueError(f"Use readable, same-candidate evidence bound to the binary artifact {path.name}")
    pattern = r"(?:L|PARA)([1-9][0-9]{0,7})" if suffix == ".docx" else r"L([1-9][0-9]{0,7})"
    marker = re.fullmatch(pattern, locator)
    if not marker:
        raise ValueError(f"Use a numbered text line or DOCX paragraph in {path.name}")
    if suffix == ".docx":
        from tools.fullflow_gate import _article_text
        try:
            contents = _article_text(path)
        except (BadZipFile, ParseError) as exc:
            raise ValueError(f"Unable to read DOCX paragraphs in {path.name}") from exc
    elif suffix in NATIVE_REVIEW_SUFFIXES:
        contents = native_review_text(root, row, path, accepted_refs, identity or {})
    else:
        contents = path.read_text(encoding="utf-8-sig")
    start = int(marker[1]) - 1
    lines = contents.splitlines()
    passage = "\n".join(lines[start:start + len(quote.splitlines())])
    if quote not in passage:
        raise ValueError(f"Quoted observation not found in {path.name} at {locator}")
    return None


NATIVE_REVIEW_SUFFIXES = frozenset({".inp", ".his", ".rep", ".rpt"})
REVIEW_TEXT_SUFFIXES = frozenset({".md", ".txt", ".csv", ".docx"}) | NATIVE_REVIEW_SUFFIXES
DIRECT_REVIEW_SUFFIXES = REVIEW_TEXT_SUFFIXES | {".json", ".pdf"}


def verify_scoped_checks(root, mapping, scopes, artifacts, accepted_refs, checks, identity):
    """Check every frozen scope-to-evidence obligation, including the deliverables."""
    if not isinstance(mapping, dict) or mapping.keys() != set(scopes):
        raise ValueError("Declare scope_evidence for all and only the frozen delivery scopes.")
    obligations = {}
    for scope, refs in mapping.items():
        obligations[scope] = list(records(refs, f"evidence for {scope}"))
        for ref in refs:
            if ref not in accepted_refs:
                raise ValueError(f"Scope {scope} cites an unregistered final file.")
            file_at(root, ref)
    if any(not any(artifact in refs for refs in obligations.values()) for artifact in artifacts):
        raise ValueError("Every actual delivery file must be assigned to a frozen review scope.")

    checked = {scope: [] for scope in scopes}
    for row in records(checks, "independent final checks"):
        scope, locator = row.get("scope"), row.get("locator")
        if scope not in obligations or not nonempty(row.get("observation")) or not nonempty(locator):
            raise ValueError("Each final check needs a frozen scope, observed result and source locator.")
        evidence = row["evidence_ref"]
        if evidence not in obligations[scope]:
            raise ValueError(f"Final check cites evidence outside the frozen {scope} scope.")
        data = verify_locator(root, row, accepted_refs=accepted_refs, identity=identity)
        checked[scope].append(evidence)
        if "artifact_ref" in row:
            artifact = row["artifact_ref"]
            if (artifact not in artifacts or artifact not in obligations[scope]
                    or Path(artifact["path"]).suffix.lower() in DIRECT_REVIEW_SUFFIXES):
                raise ValueError("Review readable delivery files directly; bind binary evidence to its frozen delivery scope.")
            if (not isinstance(data, dict) or data.get("artifact") != artifact
                    or any(data.get(key) != value for key, value in identity.items())
                    or not locator.startswith("results.")):
                raise ValueError("Binary evidence must report a current-case result and the exact artifact reference.")
            checked[scope].append(artifact)
    for scope, refs in obligations.items():
        if any(ref not in checked[scope] for ref in refs):
            raise ValueError(f"Final review missed a frozen file or readback in scope {scope}.")


def satisfies(actual, rule):
    expected = rule["expected"]
    op = rule.get("comparison", "eq")
    if type(expected) in (int, float):
        if type(actual) not in (int, float) or not (math.isfinite(expected) and math.isfinite(actual)):
            return False
        return {"eq": actual == expected, "ge": actual >= expected, "le": actual <= expected}.get(op, False)
    return op == "eq" and type(actual) is type(expected) and actual == expected


def review_issues(source):
    groups = source["module_reviews"] if "module_reviews" in source else [source]
    return [issue for group in records(groups, "review sections")
            for issue in records(group.get("issues"), "review issues", allow_empty=True)]


def flow_sources(root, contract, names=("source_gate", "scaffold_gate")):
    return [document(root, ref)["output_ref"] for name in names
            for ref in contract.get(name, {}).get("independent_calls", [])]


def retain_review_findings(root, case_id, sources):
    """Persist original findings once per review, including reviews that prevent advancement."""
    if not nonempty(case_id):
        raise ValueError("Project case ID required to retain findings.")
    root = Path(root)
    retained = []
    for ref in sources:
        source = document(root, ref)
        if source.get("case_id") != case_id:
            raise ValueError("Cannot register a review from another case.")
        issues = review_issues(source)
        if not issues:
            continue
        if any(not isinstance(i, dict) or not nonempty(i.get("id")) for i in issues):
            raise ValueError("Cannot retain a finding without its stable ID.")
        entry = {"case_id": case_id, "source_revision": source.get("task_revision"),
                 "source_ref": ref, "issues": issues}
        data = (json.dumps(entry, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        directory = root / HISTORY
        directory.mkdir(exist_ok=True)
        target = directory / (hashlib.sha256(data).hexdigest() + ".json")
        if not target.exists():
            with tempfile.NamedTemporaryFile(dir=directory, suffix=".tmp", delete=False) as tmp:
                temporary = Path(tmp.name)
                try:
                    tmp.write(data)
                except Exception:
                    tmp.close()
                    temporary.unlink(missing_ok=True)
                    raise
            try:
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
        if target.read_bytes() != data:
            raise ValueError(f"Changed finding history: {target.name}")
        retained.extend(i["id"] for i in issues)
    return sorted(set(retained))


def registered_findings(root, case_id):
    for path in sorted((Path(root) / HISTORY).glob("*.json")):
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != path.stem:
            raise ValueError(f"Changed prior finding snapshot: {path.name}")
        entry = json.loads(data)
        if entry["case_id"] == case_id:
            yield from entry["issues"]


def registered_case(root, case_id):
    """A narrow request in another case sharing the workspace does not inherit this case's delivery."""
    from tools.review_scope_history import check_scope
    root = Path(root)
    try:
        register = root / REGISTER
        if register.is_file() and json.loads(register.read_text(encoding="utf-8-sig")).get("case_id") == case_id:
            return True
        if next(registered_findings(root, case_id), None) is not None:
            return True
        return bool(check_scope(root, {"case_id": case_id}, None, None)["needs"])
    except (OSError, ValueError, KeyError, AttributeError):
        return True


def remember_stage(root, payload):
    """Public engineering workflow records received findings before its next revision."""
    root = Path(root)
    case_id = payload.get("case_id")
    refs = []
    if payload.get("fullflow_contract"):
        contract = read_reference(root, payload["fullflow_contract"])
        if case_id and contract.get("case_id") != case_id:
            raise ValueError("Case differs from the bound flow contract.")
        case_id = contract.get("case_id")
        names = ("source_gate",) if payload["stage"] == "source" else ("source_gate", "scaffold_gate")
        refs.extend(flow_sources(root, contract, names))
    if payload.get("authority"):
        authority = read_reference(root, payload["authority"])
        basis = authority.get("delivery_review", {})
        if basis:
            from tools.review_scope_history import remember_scope
            identity = {k: payload.get(k) or authority.get(k) for k in ("case_id", "task_revision", "run_id")}
            remember_scope(root, identity, basis, payload["authority"])
            refs.extend(basis.get("review_sources", []))
            register = root / REGISTER
            if payload["stage"] == "delivery" and register.is_file():
                reg = json.loads(register.read_text(encoding="utf-8-sig"))
                if reg.get("case_id") == case_id and reg.get("final_review_ref"):
                    refs.append(reg["final_review_ref"])
    return retain_review_findings(root, case_id, refs) if refs else []


def check_delivery_review(root, payload):
    """Read the actual project register, frozen sources, prior branches and exact final outputs."""
    root = Path(root)
    needs, required, carried, source_keys, parent_keys = [], {}, set(), set(), set()
    identity = {k: payload.get(k) for k in ("case_id", "task_revision", "run_id")}
    outside_delivery, replacements = [], []

    def need(code, scope, detail):
        needs.append({"code": code, "scope": scope, "detail": str(detail)})

    def add(issue):
        key = issue["id"]
        if not nonempty(key):
            raise ValueError("Finding ID missing.")
        old = required.setdefault(key, [])
        if issue not in old:
            old.append(issue)

    def raw_source(ref):
        if ref["sha256"] in source_keys:
            return
        source = document(root, ref)
        if source.get("case_id") != identity["case_id"]:
            raise ValueError("Review belongs to another case.")
        source_keys.add(ref["sha256"])
        for issue in review_issues(source):
            add(issue)

    def parent(ref, ancestors):
        key = ref["sha256"]
        if key in ancestors:
            raise ValueError("Cyclic finding history.")
        if key in parent_keys:
            return
        data = document(root, ref)
        if data["case_id"] != identity["case_id"] or not nonempty(data.get("task_revision")):
            raise ValueError("Prior finding register has no matching project identity.")
        parent_keys.add(key)
        for prev in records(data.get("parents"), "prior registers", allow_empty=True):
            parent(prev, ancestors | {key})
        for src in records(data.get("review_sources"), "prior raw reviews", allow_empty=True):
            raw_source(src)
        if data.get("final_review_ref"):
            raw_source(data["final_review_ref"])
        for row in records(data.get("items"), "prior findings", allow_empty=True):
            carried.add(row["id"])

    try:
        if not all(nonempty(v) for v in identity.values()):
            raise ValueError("Bind the case, revision and run for final delivery.")
        for issue in registered_findings(root, identity["case_id"]):
            add(issue)
        authority = read_reference(root, payload["authority"])
        basis = authority["delivery_review"]
        if authority.get("case_id") != identity["case_id"]:
            raise ValueError("Frozen delivery authority belongs to another case.")
        from tools.review_scope_history import check_scope
        needs.extend(check_scope(root, identity, basis, payload["authority"])["needs"])
        scopes = records(basis["scope"], "delivery scope")
        if len(set(scopes)) != len(scopes) or not all(nonempty(x) for x in scopes):
            raise ValueError("Frozen delivery scope has empty or duplicate items.")
        artifacts = records(basis["artifacts"], "delivery files")
        for ref in artifacts:
            file_at(root, ref)
        accepted_refs = artifacts + records(basis.get("evidence_refs", []), "other final evidence", allow_empty=True)
        if payload.get("source_export"):
            accepted_refs = [*accepted_refs, payload["source_export"]]
        reg = json.loads((root / REGISTER).read_text(encoding="utf-8-sig"))
        if any(reg.get(k) != v for k, v in identity.items()):
            raise ValueError("Current issue register belongs to another revision or run.")
        sources = list(records(basis["review_sources"], "registered additional reviews", allow_empty=True))
        contract_ref = basis.get("fullflow_contract", payload.get("fullflow_contract"))
        if "fullflow_contract" in basis and "fullflow_contract" in payload and basis["fullflow_contract"] != payload["fullflow_contract"]:
            raise ValueError("Stage and delivery authority reference different flow contracts.")
        if contract_ref:
            contract = read_reference(root, contract_ref)
            if any(contract.get(k) != identity[k] for k in ("case_id", "task_revision")):
                raise ValueError("Flow review sources belong to another project revision.")
            for name in ("source_gate", "scaffold_gate"):
                if len(records(contract[name]["independent_calls"], name)) != 3:
                    raise ValueError(f"Missing required full-flow reviews in {name}.")
            sources.extend(flow_sources(root, contract))
        for src in sources:
            raw_source(src)
        parents = records(basis["parents"], "parent registers", allow_empty=True)
        if not same_set(reg.get("parents"), parents) or not same_set(reg.get("review_sources"), sources):
            raise ValueError("Register must preserve all frozen parent branches and raw review sources.")
        for previous in parents:
            parent(previous, set())
        review_ref = reg["final_review_ref"]
        raw_source(review_ref)
        final = document(root, review_ref)
        call = document(root, reg["invocation_ref"])
        if (any(final.get(k) != v for k, v in identity.items())
                or final.get("kind") != "final_delivery_review"
                or not same_set(final.get("artifacts"), artifacts)
                or not same_set(final.get("scope"), scopes)):
            raise ValueError("Final reviewer must inspect the current delivery files, run and entire frozen scope.")
        if (not nonempty(basis.get("preparer_id")) or not nonempty(final.get("reviewer_id"))
                or final["reviewer_id"] == basis["preparer_id"] or not nonempty(final.get("call_id"))
                or call.get("call_id") != final["call_id"] or call.get("reviewer_id") != final["reviewer_id"]
                or str(call.get("output_sha256", "")).lower() != review_ref["sha256"].lower()):
            raise ValueError("Bind a distinct final reviewer and the actual call to the saved review output.")
        verify_scoped_checks(root, basis.get("scope_evidence"), scopes, artifacts, accepted_refs,
                             final["checks"], identity)
        decisions = {}
        for row in records(final["finding_rechecks"], "independent finding rechecks", allow_empty=True):
            key = row["id"]
            if key in decisions:
                raise ValueError(f"Duplicate final finding recheck: {key}")
            decisions[key] = row
        from tools.review_finding_scope import plan_finding_review
        current_items = records(reg["items"], "current findings", allow_empty=True)
        plan = plan_finding_review(root, identity, basis, required, carried_ids=carried, current_items=current_items)
        needs.extend(plan["needs"])
        outside_delivery, replacements = plan["out_of_scope"], plan["replacements"]
        outside_ids = {row["id"] for row in outside_delivery}
        seen = set()
        for row in current_items:
            key = row["id"]
            if not nonempty(key) or key in seen:
                raise ValueError(f"Empty or duplicate finding: {key}")
            seen.add(key)
            if key in outside_ids:
                continue
            if row.get("status") not in ("verified_fixed", "evidence_refuted"):
                need("REVIEW_FINDING_OPEN", key, row.get("next_action") or "Repair and recheck the original finding.")
                continue
            recon = decisions.get(key, {})
            if (recon.get("status") != row["status"] or not nonempty(recon.get("observation"))
                    or not nonempty(recon.get("locator"))):
                need("FINDING_RECHECK_REQUIRED", key, "Independent reviewer must recheck this finding on the current candidate.")
                continue
            evidence = recon.get("evidence_ref")
            if evidence not in accepted_refs:
                need("FINDING_RECHECK_REQUIRED", key, "Reference evidence bound to this delivery.")
                continue
            verify_locator(root, recon, accepted_refs=accepted_refs, identity=identity)
            criteria = plan["criteria_by_id"].get(key, [])
            if criteria:
                measurement = document(root, evidence)
                if (any(measurement.get(k) != v for k, v in identity.items())
                        or measurement.get("artifact") not in artifacts):
                    need("FINDING_MEASUREMENT_STALE", key, "Use the current artifact and run for its measured values.")
                    continue
                for rule in criteria:
                    value = evidence_value(measurement["results"], rule["path"])
                    if (value.get("unit") != rule["unit"] or value.get("basis") != rule["basis"]
                            or not satisfies(value.get("value"), rule)):
                        need("FINDING_CRITERION_MISSED", key, rule["path"])
        for key in sorted(set(plan["blocking_ids"]) - seen):
            need("REVIEW_FINDING_OMITTED", key, "Restore the finding from the original review or previous version.")
        for key in sorted(set(decisions) - seen - outside_ids):
            need("REVIEW_FINDING_OMITTED", key, "Reconcile this recheck with the issue register.")
    except (OSError, ValueError, TypeError, AttributeError, KeyError, IndexError, OverflowError, RecursionError) as exc:
        need("FINAL_REVIEW_EVIDENCE_REQUIRED", "delivery", exc)
    return {"status": "ACTION_REQUIRED" if needs else "REVIEW_EVIDENCE_CHECKED", "needs": needs,
            "finding_ids": sorted(set(required) | carried), "outside_delivery": outside_delivery,
            "criterion_replacements": replacements, "engineering_accepted": False}
