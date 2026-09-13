"""Discover this product's real interfaces without guessing a user's home paths."""
from __future__ import annotations

import inspect
import json
from pathlib import Path

from backends.process import pressure
from tools.equipment_gateway import describe_policy

ROOT = Path(__file__).resolve().parents[1]
PRESSURE_METHODS = ("liquid_pipe_loss", "series_pressure", "compressor_train",
                    "equal_ratio_initializer", "parallel_distribution")


def skill_location():
    relative = "equipment-design-app/SKILL.md"
    bundled = ROOT / "plugins/chemical-engineering-skills/skills" / relative
    if bundled.is_file():
        return {"available": True, "path": str(bundled), "basis": "bundled_product_skill"}
    receipt = ROOT.parent / "CHEMICAL_SKILLS_INSTALLATION.json"
    if receipt.is_file():
        paths = json.loads(receipt.read_text(encoding="utf-8-sig"))
        if (paths.get("schema") == "chemical-skills-installation-paths-v1"
                and Path(paths.get("runtime_root", "")).resolve() == ROOT.resolve()
                and Path(paths.get("workspace_root", "")).resolve() == ROOT.parent.resolve()):
            candidate = Path(paths["skills_root"]) / relative
            return {"available": candidate.is_file(), "path": str(candidate),
                    "basis": "explicit_installation_paths", "receipt": str(receipt)}
    return {"available": False, "path": None, "basis": "no_explicit_product_skill_path",
            "effect": "Skill guidance unavailable; bundled deterministic backend remains callable"}


def backend_request(operation, payload=None):
    return {"schema": "equipment-design-agent-request-v1", "request_id": "PRODUCT-DISCOVERY",
            "operation": operation, "payload": payload or {}}


def describe(runner):
    original = runner(backend_request("capabilities"))
    return {"schema": "chemical-engineering-product-capabilities-v1",
            "product": "chemical-engineering-skills", "standalone_product": True,
            "other_repositories_required": False, "gui_required": False,
            "skill": skill_location(), "equipment_gateway": describe_policy(),
            "original_backend_capabilities": original,
            "backend_skill_path_notice": "The original backend's legacy global_skill_installed field describes its old layout; this product's skill object above uses the explicit installed layout.",
            "operations": ["search", "equipment", "equipment_batch", "pressure", "feedback", "replay_audit", "design_stage", "solve_route", "capabilities", "schema"],
            "product_schema_ids": ["expert-request", "process-feedback", "pressure-methods", "process-replay-audit", "design-stage", "solve-route"],
            "knowledge": {"corpora": ["all", "chemical_principles", "sun_lanyi", "aspen_v10", "equipment", "equipment_standards"],
                          "query_modes": ["lexical", "hash_vector", "exact_node_id"],
                          "detail": True, "full_text": True, "knowledge_update_entry": "knowledge/scripts/build_knowledge_version.py"},
            "examples": ["examples/heat_exchanger_request.json", "examples/parallel_pressure_request.json", "examples/prepare_feedback_case.py"],
            "runtime_boundary": {"python_required": True, "core_calculation_network_required": False,
                                 "vector_requires_numpy": True, "mcp_requires_bundled_dependencies": True,
                                 "licensed_software_needed_for_actual_Aspen_EDR_SW6": True},
            "engineering_accepted": False}


def schema(schema_id, runner):
    if schema_id == "expert-request":
        return {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object",
                "required": ["operation", "payload"], "properties": {
                    "operation": {"enum": ["search", "equipment", "equipment_batch", "pressure", "feedback", "replay_audit", "design_stage", "solve_route", "capabilities", "schema"]},
                    "payload": {"type": "object"}},
                "description": "equipment payload is an original Agent request; equipment_batch payload has requests[]. Use original schema_get IDs for detailed backend inputs."}
    if schema_id == "pressure-methods":
        methods = {}
        for name in PRESSURE_METHODS:
            function = getattr(pressure, name)
            signature = inspect.signature(function)
            methods[name] = {"signature": str(signature), "description": inspect.getdoc(function),
                             "required_inputs": [key for key, parameter in signature.parameters.items()
                                                 if parameter.default is inspect.Parameter.empty]}
        return {"schema": schema_id, "operation": "pressure", "payload": {"method": "registered method name", "inputs": "named parameters in the signatures"},
                "methods": methods, "source": "backends/process/pressure.py", "acceptance": "declared-basis calculation, not equipment rating or actual process simulation"}
    if schema_id == "process-feedback":
        return {"schema": schema_id, "operation": "feedback", "required_payload": ["selector_request", "context"],
                "selector_request": "Original equipment Agent request; same-case canonical source/authority must bind its values, units and equipment family.",
                "context": {"case_id": "current case identity", "run_id": "current export run identity",
                    "source_export": {"path": "canonical-export.json", "sha256": "actual file SHA-256"},
                    "authority": {"path": "authority.json", "sha256": "actual file SHA-256"},
                    "equipment_map": "Optional physical equipment identity mapping when required by the project; unique equipment_tag binding does not require this field",
                    "topology": "Declared nodes and directed edges; pressure/recycle effects can propagate both ways",
                    "constraint_evidence": "Per-equipment hash-bound reviewed constraints with exact current value and applicable limit sources",
                    "configuration_checks": "Per-equipment registered pressure methods with explicit input_basis"},
                "source_schemas": ["equipment-process-canonical-export-v1", "equipment-process-authority-v1", "equipment-process-limit-v1"],
                "example_generator": "examples/prepare_feedback_case.py --output-dir <new-directory>",
                "validator_owner": "backends/process/feedback.py", "engineering_accepted": False,
                "scope": "Discovery contract, not a substitute for source-binding/applicability validators. Missing engineering evidence stays local; no automatic model mutation."}
    if schema_id == "process-replay-audit":
        return {"schema": schema_id, "operation": "replay_audit", "required_payload": ["plan", "replay"],
                "evidence_root": "Explicit directory of hash-bound current model and domain receipts",
                "validator_owner": "backends/process/feedback.py:audit_replay",
                "boundary": "Only registered validators verify a gate. Labels, synthetic examples and self-declared passed booleans do not prove a real flowsheet passed."}
    if schema_id == "solve-route":
        from tools.aspen_tool_router import INTENTS, OBJECTIVE_DIRECTIONS, STUDY_LISTS, STUDY_MODES
        reference = {"type": "object", "additionalProperties": False, "required": ["path", "sha256"],
            "properties": {"path": {"type": "string", "minLength": 1}, "sha256": {"type": "string", "pattern": "^[0-9a-fA-F]{64}$"}}}
        study_context = {"type": "object", "additionalProperties": False,
            "properties": {
                "mode": {"enum": list(STUDY_MODES)},
                **{field: {"type": "array", "items": {"type": "string", "minLength": 1, "pattern": r"\S"}} for field in STUDY_LISTS},
            }, "description": "Optional declared study roles; not a physical or execution proof. Fixed-control response and same-target comparison are distinct. Only relevant study needs are reported."}
        return {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object", "additionalProperties": False,
            "required": ["question"], "properties": {"question": {"type": "string", "minLength": 1},
                "intents": {"type": "array", "items": {"enum": list(INTENTS)}},
                "study_context": study_context,
                "objective": {"type": "object", "additionalProperties": False,
                    "properties": {"definition": {"type": "string", "minLength": 1, "pattern": r"\S"},
                        "direction": {"enum": list(OBJECTIVE_DIRECTIONS)}},
                    "description": "Declared preference objective. Both definition and direction are needed before optimize can be routed; partial declarations remain classification pending. Other intents do not require it. Never invent an objective; this input does not prove its source, user scope, feasibility or execution."},
                "fit_data": reference, "fit_authority": reference,
                "external_request": {"type": "object", "additionalProperties": False, "required": ["reason", "evidence"],
                    "properties": {"reason": {"type": "string", "minLength": 1}, "evidence": {"type": "array", "items": reference}}}},
            "operation": "solve_route", "mcp_tool": "aspen_solve_route",
            "description": "Payload only. No equipment inventory needed. Finite language hints need agent judgment; hashes bind bytes, never authorize substitution or prove native execution.",
            "example": {"operation": "solve_route", "payload": {"question": "读取当前物流的焓", "intents": ["read_value"]}},
            "state_boundary": "AGENT_CLASSIFICATION_REQUIRED or ACTION_REQUIRED; never native creation/execution or engineering acceptance"}
    if schema_id == "design-stage":
        from tools.design_stage import STAGES
        return {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object",
            "additionalProperties": False, "required": ["stage", "question"],
            "properties": {
                "stage": {"enum": list(STAGES)}, "question": {"type": "string", "minLength": 1},
                "case_id": {"type": "string"}, "run_id": {"type": "string"},
                "source_export": {"$ref": "#/$defs/reference"}, "authority": {"$ref": "#/$defs/reference"},
                "detail": {"type": "boolean", "description": "Source-stage detail opt-in; later stages retrieve implementation methods automatically"},
                "equipment_requests": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                    "required": ["equipment_id", "request"], "properties": {"equipment_id": {"type": "string", "minLength": 1},
                    "request": {"type": "object", "description": "Original manual_match or auto_match request for one current physical device"}}}},
                "context": {"type": "object", "description": "Optional process-feedback constraints/topology; identity must agree with the stage"},
                "solve_request": {"type": "object", "description": "Optional solve-route inputs; stage question is supplied automatically and cannot be replaced. Tool action needs do not erase equipment calculations.",
                    "additionalProperties": False, "properties": schema("solve-route", runner)["properties"]},
                "pressure_checks": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["method", "input_basis", "inputs"],
                    "properties": {"method": {"enum": list(PRESSURE_METHODS)}, "input_basis": {"type": "string", "minLength": 1}, "inputs": {"type": "object"}}}},
                "plan": {"type": "object"}, "replay": {"type": "object"}},
            "$defs": {"reference": {"type": "object", "required": ["path", "sha256"],
                "properties": {"path": {"type": "string"}, "sha256": {"type": "string", "pattern": "^[0-9a-fA-F]{64}$"}}}},
            "operation": "design_stage", "description": "This schema describes the payload of an expert request. Source needs no invented equipment inputs. Later stages expose local needs when current references or device requests are absent.",
            "example": {"operation": "design_stage", "payload": {"stage": "source", "question": "预热与压缩如何减少高温公用工程"}},
            "state_boundary": "Only MODULE_CHECKS_EXECUTED or ACTION_REQUIRED; engineering_accepted=false, no implicit stage advance or real inventory certification",
            "implementation": "tools/design_stage.py"}
    return runner(backend_request("schema_get", {"schema_id": schema_id}))
