"""Read-only evidence-structure gate for document-driven full-flow generation.

This is not a simulator or a provider-log authenticator. It checks current,
hash-bound records and reuses the existing handoff structure checker. Even a
consistent dossier never proves chemistry, an independent model invocation,
actual Aspen execution, or engineering acceptance. No commands are executed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re

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
BOUNDARY = ("Evidence completeness and declared identity consistency only; hashes do not authenticate "
            "provider invocations, Aspen provenance, scientific truth or engineering acceptance.")


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _canonical(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


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


def schema():
    """Small discovery contract; synthetic examples live with the regression tests."""
    return {"schema": SCHEMA, "entrypoint": "tools.fullflow_gate.check_fullflow",
            "discovery_only": True, "not_a_complete_json_schema": True,
            "payload_field": "fullflow_contract", "reference": {"path": "project-relative path", "sha256": "64 hex characters"},
            "required_contract_fields": ["schema", "case_id", "task_revision", "scope", "modules", "source_gate"],
            "stage_fields": {"source": ["source_gate"], "scaffold": ["source_gate", "scaffold_gate"],
                "island": ["source_gate", "scaffold_gate", "islands"],
                "reconnect/change/delivery": ["source_gate", "scaffold_gate", "islands", "replacements", "current_run_ref"]},
            "source_gate": ["design_basis_ref", "prompt_ref", "independent_calls (5 references)",
                            "difference_closure_ref", "handoff_input_ref", "handoff_review_ref", "planning_checks_ref"],
            "planning_checks_ref": "One short source-bound record: pressure_budget, heat_strategy, compression_decisions; group modules when appropriate. Reuse existing calculations; no new solver.",
            "scaffold_gate": ["run_ref", "cycle_initials_ref", "prompt_ref", "independent_calls (3 references)",
                              "difference_closure_ref"],
            "module_fields": ["id", "module_revision", "role", "purpose", "node_ids", "inlets", "outlets", "targets",
                              "thermodynamics", "auxiliary_requirements", "auxiliaries", "unknowns",
                              "reaction (reaction role) or separation (separation role)"],
            "scope": {"mode": "fullflow or module", "module_ids": "explicit current module IDs for module scope"},
            "identity_fields": ["case_id", "task_revision"],
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
                "module_review": ["module_id", "role_summary", "boundary_summary", "thermodynamics_summary", "reaction_or_separation_summary", "issues[{id,finding}]", "verification_checks (fixed keys above)"],
                "verification_anchor_rule": "Source observations address design_basis.modules.<index> role/purpose/inlets/outlets/reaction-or-separation/thermodynamics/auxiliary_requirements/auxiliaries, and handoff nodes/streams. Scaffold additionally observes current export block_type/parameters, source and export modules/auxiliary_nodes, cycle mode/streams plus export recycle_stream_ids, and export run_id/model_sha256/raw_export_ref.",
                "planning_row": ["module_ids[]", "state=calculated|provisional_bounds|not_applicable|blocked (heat/compression also reasoned)", "method", "input_basis", "evidence_refs[]"],
                "planning_calculated": ["calculation_ref (existing JSON output)", "result_path (dotted numeric field)", "unit"],
                "planning_provisional_bounds": ["bounds={lower,upper,unit,source_ref}", "unresolved_inputs[]", "refine_trigger"],
                "planning_not_applicable_or_blocked": ["reason (source-bound, not a pass label)"],
                "current_equipment_export_binding": ["case_id", "run_id", "model_sha256", "raw_export_sha256"],
            },
            "record_schemas": {
                "fullflow-agent-call-v1": ["case_id", "task_revision", "stage", "call_id", "independent_context_id", "model_id", "prompt_sha256", "invocation_ref", "output_ref"],
                "invocation_record": ["case_id", "task_revision", "invocation_id", "call_id", "independent_context_id", "model_id", "prompt_sha256", "output_sha256"],
                "fullflow-independent-review-v1": ["case_id", "task_revision", "call_id", "process_chain[{stream_id,from,to}]", "module_reviews[]", "source: design_basis_sha256", "scaffold: run_id/export_sha256/cycle_initials_sha256"],
                "fullflow-difference-closure-v1": ["case_id", "task_revision", "reviewer_id", "comparisons[{call_id,module_id,output_sha256,issue_ids,disposition=adopt|reject|no_difference,rationale,evidence_refs}]"],
                "fullflow-run-evidence-v1": ["case_id", "task_revision", "run_id", "model_ref", "native_run_ref", "export_ref", "island: module_id/module_revision/boundary_sha256"],
                "native_run_record": ["run_id", "case_sha256", "status=completed", "started_epoch", "finished_epoch", "may be nested under existing audit.run"],
                "fullflow-model-export-v1": ["case_id", "task_revision", "run_id", "model_sha256", "raw_export_ref", "connections[{stream_id,from,to}]", "modules[{module_id,module_revision,original_node_ids,node_ids,block_type,parameters,inlets,outlets,targets,thermodynamics}]", "auxiliary_nodes[{node_id,block_type}]", "recycle_stream_ids[]", "island: module_id/module_revision/boundary_sha256"],
                "fullflow-cycle-initials-v1": ["case_id", "task_revision", "run_id", "export_sha256", "mode=recycle|no_recycle", "basis", "source_refs[]", "streams[] (recycle adds flow/temperature/pressure/phase)"],
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
        actual = checker.check(data, source_root=self.root)
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
        remaining = [x for x in actual["unresolved"] if x not in permitted_unresolved]
        self.require(not actual["errors"] and not remaining and report.get("status") == actual["status"],
                     "HANDOFF_INCOMPLETE", "source", {"status": actual["status"], "errors": actual["errors"], "unresolved": remaining})
        process_ids = {row.get("id") for row in data.get("nodes", []) if isinstance(row, dict) and row.get("kind") == "process"}
        expected = {node for module in self.modules.values() for node in module.get("node_ids", []) if isinstance(node, str)}
        expected |= {row.get("node_id") for module in self.modules.values() for row in module.get("auxiliaries", []) if isinstance(row, dict)}
        self.require(expected <= process_ids, "HANDOFF_MODULE_COVERAGE", "source", "Every declared module and required auxiliary must exist in the existing topology record")

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
                self.require(value is not None and "value" in observation and _canonical(observation["value"]) == _canonical(value),
                             "VERIFICATION_OBSERVATION_MISMATCH", where + "." + name,
                             "Actual observation must match the referenced field; OK/considered/passed prose is not a field readback")
            self.require(actual_keys == expected_keys and {key(x) for x in references} >= {key(x) for x, _ in expected},
                         "VERIFICATION_CHECK_INCOMPLETE", where + "." + name, "Every required observation and its source reference must be retained")

    def reviews(self, gate, stage, expected_count, *, bindings):
        verification_specs, process_chain = self.verification_specs(gate, stage)
        prompt = self.read(gate.get("prompt_ref"), stage + ".prompt_ref", json_value=False)
        references = self.rows(gate.get("independent_calls"), stage + ".independent_calls")
        self.require(len(references) == expected_count, "INDEPENDENT_REVIEW_COUNT", stage,
                     f"Exactly {expected_count} independent call records required; unavailable calls remain incomplete")
        calls, contexts, invoked, review_map = set(), set(), set(), {}
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
            model = record.get("model_id")
            self.require(model == "gpt-6-luna" if stage == "source" else _text(model),
                         "REVIEW_MODEL_MISMATCH", where, "Current source review uses exactly gpt-6-luna; scaffold must declare its actual model")
            prompt_hash = prompt.get("sha256") if prompt else None
            self.require(prompt_hash is not None and record.get("prompt_sha256") == prompt_hash,
                         "REVIEW_PROMPT_MISMATCH", where, "All independent calls must use the exact frozen prompt")
            invocation = self.read(record.get("invocation_ref"), where + ".invocation_ref")
            output = self.read(record.get("output_ref"), where + ".output_ref")
            if invocation is not None:
                self.identity_check(invocation, where + ".invocation")
                invocation_id = invocation.get("invocation_id")
                self.require(_text(invocation_id) and invocation_id not in invoked, "DUPLICATE_INVOCATION", where,
                             "Distinct raw invocation records required")
                if _text(invocation_id): invoked.add(invocation_id)
                for field in ("call_id", "independent_context_id", "model_id", "prompt_sha256"):
                    self.require(invocation.get(field) == record.get(field), "INVOCATION_IDENTITY_MISMATCH", where, field)
                self.require(invocation.get("output_sha256") == (record.get("output_ref") or {}).get("sha256"),
                             "INVOCATION_OUTPUT_MISMATCH", where, "Invocation must identify this exact output")
            if output is None:
                continue
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
                    self.text(row.get(field), where + "." + field)
                if module_id in verification_specs:
                    self.verify_observations(row, verification_specs[module_id], where + "." + module_id)
                issues = self.rows(row.get("issues"), where + ".issues", nonempty=False)
                issue_ids = []
                for issue in issues:
                    issue = self.obj(issue, where + ".issue")
                    self.text(issue.get("id"), where + ".issue.id")
                    self.text(issue.get("finding"), where + ".issue.finding")
                    if _text(issue.get("id")): issue_ids.append(issue["id"])
                self.require(len(set(issue_ids)) == len(issue_ids), "DUPLICATE_REVIEW_ISSUE", where, "Issue IDs must be distinct")
                if _text(call_id):
                    review_map[(call_id, module_id)] = {"issues": set(issue_ids), "output_sha256": record["output_ref"]["sha256"]}
            self.require(seen == set(self.modules), "REVIEW_MODULE_COVERAGE", where, "Missing module-by-module restatement")
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
            self.require(item.get("disposition") in {"adopt", "reject", "no_difference"}, "DIFFERENCE_UNRESOLVED", stage, "Explicit disposition required")
            self.text(item.get("rationale"), stage + ".comparison.rationale")
            self.refs(item.get("evidence_refs"), stage + ".comparison.evidence_refs")
            issue_ids = self.rows(item.get("issue_ids"), stage + ".comparison.issue_ids", nonempty=False)
            if expected:
                self.require(set(str(x) for x in issue_ids) == expected["issues"]
                             and item.get("output_sha256") == expected["output_sha256"],
                             "DIFFERENCE_COVERAGE", stage, "All output issues and its exact output identity must be accounted for")
        self.require(seen == set(review_map) and len(review_map) == expected_count * len(self.modules),
                     "DIFFERENCE_COVERAGE", stage, "Missing independent call/module comparison")

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
        self.handoff(gate)
        self.planning(gate)
        self.reviews(gate, "source", 5, bindings={"design_basis_sha256": (gate.get("design_basis_ref") or {}).get("sha256")})

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
            expected_type = {"reaction": "RSTOIC", "separation": "SEP"}.get(module.get("role"))
            if expected_type:
                self.require(str(row.get("block_type", "")).upper() == expected_type, "SCAFFOLD_MODEL_TYPE", tag,
                             f"Default source scaffold requires {expected_type}; do not substitute a rigorous final unit silently")
            self.require(row.get("original_node_ids") == module.get("node_ids"), "SCAFFOLD_LOCATION_MISMATCH", tag, "Preserve original module location")
            self.streams(row.get("inlets"), "scaffold." + tag + ".inlets")
            self.streams(row.get("outlets"), "scaffold." + tag + ".outlets")
            self.require(row.get("thermodynamics") == module.get("thermodynamics"), "SCAFFOLD_PROPERTY_MISMATCH", tag,
                         "Exported property basis differs from the frozen module basis")
            required = {x.get("node_id") for x in module.get("auxiliaries", []) if isinstance(x, dict)}
            self.require(required <= aux_ids, "SCAFFOLD_AUXILIARY_MISSING", tag, "Required heat/pressure nodes are absent from the run export")
        cycle = self.read(gate.get("cycle_initials_ref"), "scaffold.cycle_initials_ref")
        if cycle is not None:
            self.identity_check(cycle, "scaffold.cycle_initials", run_id=record.get("run_id"))
            self.require(cycle.get("schema") == "fullflow-cycle-initials-v1"
                         and cycle.get("export_sha256") == (record.get("export_ref") or {}).get("sha256"),
                         "CYCLE_EXPORT_MISMATCH", "scaffold", "Cycle initialization must originate from this scaffold export")
            self.text(cycle.get("basis"), "scaffold.cycle_initials.basis")
            self.refs(cycle.get("source_refs"), "scaffold.cycle_initials.source_refs")
            if cycle.get("mode") == "no_recycle":
                self.require(exported.get("recycle_stream_ids") == [] and cycle.get("streams") == [],
                             "NO_RECYCLE_CONTRADICTION", "scaffold", "No-recycle statement conflicts with exported recycle inventory")
            elif cycle.get("mode") == "recycle":
                self.streams(cycle.get("streams"), "scaffold.cycle_initials.streams")
                ids = {x.get("stream_id") for x in cycle.get("streams", []) if isinstance(x, dict)}
                self.require(ids == set(exported.get("recycle_stream_ids", [])) and bool(ids), "CYCLE_INITIALS_COVERAGE", "scaffold", "Every exported recycle needs an initial state")
                for row in cycle.get("streams", []):
                    if isinstance(row, dict):
                        for field in ("flow", "temperature", "pressure", "phase"):
                            self.text(row.get(field), "scaffold.cycle_initials." + field)
            else:
                self.need("CYCLE_MODE_REQUIRED", "scaffold", "Use sourced recycle initial states or an explicit no_recycle record")
        self.reviews(gate, "scaffold", 3, bindings={"run_id": record.get("run_id"),
            "export_sha256": (record.get("export_ref") or {}).get("sha256"),
            "cycle_initials_sha256": (gate.get("cycle_initials_ref") or {}).get("sha256")})

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
        for tag in self.scope:
            module = self.modules[tag]
            item = self.obj(indexed.get(tag), "island." + tag)
            self.require(item.get("module_revision") == module.get("module_revision"), "STALE_ISLAND_REVISION", tag, "Refine this module's current revision only")
            boundary = self.read(item.get("boundary_ref"), "island." + tag + ".boundary_ref")
            route = self.read(item.get("specialist_route_ref"), "island." + tag + ".specialist_route_ref")
            boundary_hash = (item.get("boundary_ref") or {}).get("sha256")
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
            results[tag] = run_record
            self.island_equipment_gate(tag, item, run_record, run_export)
        return results

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


def check_fullflow(payload, evidence_root, documents=None):
    """Inspect explicit/full-flow-intent evidence; never write files or execute models."""
    payload = payload if isinstance(payload, dict) else {}
    documents = documents if isinstance(documents, dict) else {}
    authority = documents.get("authority", {})
    question = payload.get("question", "")
    explicit = "fullflow_contract" in payload
    whole_flow = r"(?:全流程|整厂|full[ -]?(?:flow|flowsheet)|plant[ -]wide)"
    action = r"(?:生成|建立|搭建|构建|建模|细化|替换|接回|交付|校核|修复|generate|generation|build|construct|model|reconnect|deliver|check|repair)"
    presentation_only = isinstance(question, str) and bool(re.search(r"(?:仅|只|纯).*(?:解释|说明|图示|改写|措辞)|(?:改写|排版|图示对照|解释原理)|\b(?:explain|diagram|rewrite|wording)\b", question, re.I))
    intended = isinstance(question, str) and not presentation_only and bool(re.search(
        whole_flow + ".*?" + action + "|" + action + ".*?" + whole_flow, question, re.I))
    required = explicit or (isinstance(authority, dict) and authority.get("workflow_profile") == "fullflow_generation") or intended
    result = {"required": required, "status": "NOT_APPLICABLE", "needs": [], "required_reading": [],
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
            gate.evaluate(contract)
    except (ValueError, TypeError, KeyError, IndexError, OSError, AttributeError, RecursionError) as exc:
        gate.need("FULLFLOW_STRUCTURE_ERROR", "contract", f"{type(exc).__name__}: {exc}")
    result.update(status="ACTION_REQUIRED" if gate.needs else "EVIDENCE_STRUCTURE_CONSISTENT",
                  needs=gate.needs, gate_summary=gate.summary)
    return result
