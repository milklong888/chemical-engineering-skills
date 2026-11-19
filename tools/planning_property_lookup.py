"""Read the registered TH03 collection when a first-model method is in doubt."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from tools.planning_research import _passage, _text


PROPERTY_HISTORY = "PROJECT_PROPERTY_SELECTION_HISTORY"
CASE_BASIS = ("components", "phases", "temperature_range", "pressure_range", "method")
OPEN_STATES = ("uncertain", "conflict", "outside_range")
GRAPH_NODE = re.compile(r"\b(?:TH03-[A-Z][0-9]+|L[0-3]-[0-9]+|CEPR-[A-Z0-9_-]+)\b", re.I)
GRAPH_SOURCE = re.compile(r"\bTH03\b|图谱|knowledge[ _-]graph", re.I)
LOOKUP_ONLY = re.compile(r"未采用|不作为|仅供检索|无命中|未命中|查询失败|not used|lookup failed|no hits", re.I)


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _history(root, case_id, module_id):
    namespace = hashlib.sha256(_encoded([case_id, module_id])).hexdigest()
    return Path(root) / PROPERTY_HISTORY / namespace


def record_property_selection_issue(root, case_id, task_revision, module, query, lookup_call):
    """Retain one actual unresolved lookup per case, module, issue and outcome."""
    module_id = module.get("id")
    thermo = module.get("thermodynamics", {})
    if not all(_text(value) for value in (case_id, task_revision, module_id, query)) or thermo.get("selection_status") not in OPEN_STATES:
        raise ValueError("Bind a genuinely unresolved property-selection lookup to the current case and module")
    call_status = lookup_call.get("status")
    result = lookup_call.get("result") or {}
    if (call_status not in {"EXECUTED", "FAILED"}
            or call_status == "EXECUTED" and result.get("outcome") not in {"hits", "no_hits"}):
        raise ValueError("Retain the existing lookup call result")
    record = {"case_id": case_id, "task_revision": task_revision, "module_id": module_id,
              "state": thermo["selection_status"], "query": query,
              "case_basis": {key: thermo.get(key) for key in CASE_BASIS},
              "lookup_outcome": result.get("outcome", call_status),
              "node_ids": sorted({item["node_id"] for item in result.get("materials", [])})}
    data = _encoded(record)
    issue_id = hashlib.sha256(data).hexdigest()
    directory = _history(root, case_id, module_id)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (issue_id + ".json")
    if not path.exists():
        with tempfile.NamedTemporaryFile(dir=directory, suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            try:
                handle.write(data)
            except OSError:
                handle.close()
                temporary.unlink(missing_ok=True)
                raise
        try:
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    if path.read_bytes() != data:
        raise ValueError("The retained property-selection issue has changed")
    return {**record, "issue_id": issue_id}


def _prior_issues(root, case_id, module_id):
    result = {}
    for path in sorted(_history(root, case_id, module_id).glob("*.json")):
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != path.stem:
            raise ValueError(f"Changed property-selection evidence: {path.name}")
        record = json.loads(data)
        if record.get("case_id") != case_id or record.get("module_id") != module_id:
            raise ValueError(f"Property-selection evidence belongs to another case or module: {path.name}")
        result[path.stem] = record
    return result


def _lookup_receipt(data):
    if not isinstance(data, dict):
        return False
    return (data.get("collection") == "external:TH03" or data.get("source") == "TH03"
            or data.get("schema") == "offline-knowledge-query-v1"
            or (data.get("schema") == "chemical-design-stage-receipt-v1"
                and any(call.get("kind") == "external_property_lookup" for call in data.get("calls", [])
                        if isinstance(call, dict))))


def _graph_claim(gate, thermo, scope):
    # A diagnostic lookup is separate from what the plan actually relies on.
    claims = []
    for key in ("applicability", "method_basis", "basis"):
        for clause in re.split(r"[;；。\n]", str(thermo.get(key, ""))):
            if not LOOKUP_ONLY.search(clause):
                claims.append(clause)
    for ref in thermo.get("source_refs") or []:
        if isinstance(ref, dict):
            name = Path(str(ref.get("path", ""))).name
            claims.append(name)
            if Path(name).suffix.lower() == ".json" and not GRAPH_SOURCE.search(name):
                bound = gate.read(ref, scope + ".graph_source_refs", json_value=False)
                if bound:
                    path = Path(bound["path"])
                    if path.stat().st_size <= 5_000_000:
                        try:
                            if _lookup_receipt(json.loads(path.read_text(encoding="utf-8-sig"))):
                                claims.append("knowledge graph")
                        except (OSError, ValueError):
                            pass
    used_nodes = {node.upper() for claim in claims for node in GRAPH_NODE.findall(claim)}
    return bool(used_nodes or any(GRAPH_SOURCE.search(claim) for claim in claims)), used_nodes


def _primary_property_readback(gate, row, scope, read_article):
    path = Path(str((row.get("source_ref") or {}).get("path", "")))
    if row.get("source_kind") == "project_data" and path.suffix.lower() == ".json":
        from tools.fullflow_gate import _same_observed_value

        data = gate.read(row.get("source_ref"), scope + ".source_ref")
        if not data or data.get("schema") == "chemical-design-stage-receipt-v1" or _lookup_receipt(data):
            return False
        value = gate.at_path(data, row.get("locator"))
        return (value is not None and "observed_value" in row
                and _same_observed_value(value, row["observed_value"]))
    if re.search(r"query title|lookup title|查询标题|节点标题", str(row.get("excerpt", "")), re.I):
        return False
    return bool(_passage(gate, row, scope, read_article))


def check_property_method_basis(gate, module, read_article):
    """Confirm cited source passages and their current case link without repeating lookup."""
    thermo = module.get("thermodynamics")
    if not isinstance(thermo, dict) or thermo.get("selection_status") != "supported":
        return
    scope = f"module.{module['id']}.thermodynamics"
    try:
        prior = _prior_issues(gate.root, gate.identity.get("case_id"), module["id"])
    except (OSError, ValueError, AttributeError) as exc:
        gate.need("PLAN_PROPERTY_HISTORY_UNAVAILABLE", scope, str(exc))
        return
    if "prior_selection_issue_ref" in thermo:
        reference = thermo["prior_selection_issue_ref"]
        earlier = gate.read(reference, scope + ".prior_selection_issue_ref") or {}
        earlier_case = (earlier.get("identity") or {}).get("case_id", earlier.get("case_id"))
        matches = [item for item in earlier.get("needs", []) if isinstance(item, dict)
                   and item.get("code") in {"PLAN_PROPERTY_REVIEW_OPEN", "PROPERTY_SELECTION_REVIEW_REQUIRED"}
                   and item.get("scope") in {scope, module["id"]}]
        if earlier_case != gate.identity.get("case_id") or not matches:
            gate.need("PLAN_PROPERTY_HISTORY_UNAVAILABLE", scope, "Use the earlier issue for this exact case and module.")
            return
        prior[reference["sha256"].lower()] = {"issues": matches}
    graph_claim, expected_nodes = _graph_claim(gate, thermo, scope)
    rows = thermo.get("selection_basis")
    if not (graph_claim or prior or rows):
        return
    if not isinstance(rows, list) or not rows:
        gate.need("PLAN_PROPERTY_BASIS_REQUIRED", scope, {
            "graph_nodes": sorted(expected_nodes), "prior_issues": prior,
            "action": "Retain the applicable original passage or same-case property data and explain the method outcome.",
        })
        return
    current_basis = {key: thermo.get(key) for key in CASE_BASIS}
    supported_nodes, resolved = set(), set()
    for index, row in enumerate(rows):
        where = f"{scope}.selection_basis.{index}"
        if not isinstance(row, dict) or not isinstance(row.get("source_ref"), dict):
            gate.need("PLAN_PROPERTY_BASIS_UNVERIFIED", where, "Use a hash-bound original source.")
            continue
        kind, node = row.get("source_kind"), str(row.get("node_id", "")).upper()
        if (kind not in ("graph", "primary", "project_data") or row.get("case_basis") != current_basis
                or not all(_text(row.get(key)) for key in ("citation", "source_locator", "conclusion"))):
            gate.need("PLAN_PROPERTY_BASIS_UNVERIFIED", where,
                      "Tie the actual source to this method, mixture, phases and temperature/pressure range.")
            continue
        if kind == "graph":
            excerpt = str(row.get("excerpt", "")).strip()
            if (not _text(node) or node in excerpt.upper() or excerpt.startswith("#")
                    or not re.search(r"(?:第\s*\d|[页表式节]\s*\d|\b(?:p|pp|page|table|eq|section)\.?\s*\d)",
                                     row["source_locator"], re.I)):
                gate.need("PLAN_PROPERTY_SOURCE_NOT_PRIMARY", where,
                          "Cite the original numbered page, section, table or equation and its technical passage.")
                continue
        if not _primary_property_readback(gate, row, where, read_article):
            gate.need("PLAN_PROPERTY_BASIS_UNVERIFIED", where, "Read back the actual original passage or measured field.")
            continue
        if kind == "graph":
            supported_nodes.add(node)
        addressed = row.get("resolves", [])
        if (not isinstance(addressed, list) or any(not isinstance(key, str) or key not in prior for key in addressed)):
            gate.need("PLAN_PROPERTY_BASIS_UNVERIFIED", where, "Use the retained issue IDs for this module.")
        else:
            resolved.update(addressed)
    if (graph_claim and not supported_nodes) or not expected_nodes <= supported_nodes or set(prior) - resolved:
        gate.need("PLAN_PROPERTY_BASIS_REQUIRED", scope, {
            "graph_nodes": sorted(expected_nodes - supported_nodes),
            "prior_issues": {key: record for key, record in prior.items() if key not in resolved},
            "action": "Resolve each outstanding applicability question using the selected evidence and current conditions.",
        })


def reference_library():
    configured = os.environ.get("CHEMENG_REFERENCE_LIBRARY")
    if configured:
        return Path(configured)
    # The standalone runtime is installed in <project>/skill_packages/<kit>/workspace/<runtime>.
    # Never execute a library discovered inside a caller's case/evidence directory.
    for parent in Path(__file__).resolve().parents:
        if parent.name == "skill_packages" and (parent.parent / "LOCAL_KNOWLEDGE_GRAPH_LINKS.md").is_file():
            return parent.parent / "_skill_refactor/fullflow_gate_20260918/external-reference-library"
    raise FileNotFoundError("Set CHEMENG_REFERENCE_LIBRARY to the installed external-reference-library directory")


def retrieve_property_method(query):
    library = reference_library()
    adapter = library / "src" / "query_collection.py"
    if not adapter.is_file():
        raise FileNotFoundError("The registered external TH03 lookup adapter is unavailable")

    def run(arguments):
        completed = subprocess.run([sys.executable, "-B", "-X", "utf8", str(adapter), "--source", "TH03", *arguments],
                                   cwd=library, capture_output=True, encoding="utf-8", timeout=60)
        if completed.returncode:
            raise RuntimeError("External TH03 query failed: " + completed.stderr.strip()[-700:])
        result = json.loads(completed.stdout)
        if result.get("status") != "candidate_result" or result.get("source") != "TH03":
            raise ValueError("Invalid result from the external TH03 collection")
        return result.get("results", [])

    hits = run(["--method", "lexical", "--query", query, "--limit", "3"])
    materials = []
    for hit in hits:
        node = hit["knowledge_unit_id"]
        rows = run(["--node-id", node])
        if len(rows) != 1 or rows[0]["knowledge_unit_id"] != node:
            raise ValueError("External TH03 node readback failed: " + node)
        unit = rows[0]["knowledge_unit"]
        materials.append({"node_id": node, "unit": unit})
    return {"collection": "external:TH03", "query": query, "outcome": "hits" if materials else "no_hits",
            "materials": materials, "case_applicability_verified": False}
