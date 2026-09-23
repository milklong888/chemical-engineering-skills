"""Execute existing knowledge/equipment modules at a declared design stage.

This is a small coordinator, not a simulator, equipment matcher, or acceptance
authority. Internal runners support testing and resident sessions; JSON cannot
inject them or provide a completed/skip flag.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
from pathlib import Path
import re
import subprocess
import uuid

from backends.process.feedback import (audit_replay, build_plan, configuration_checks,
                                       read_reference)
from backends.process.selector_analysis import canonical_sha, equipment_records

STAGES = ("source", "scaffold", "island", "reconnect", "change", "delivery")
FIELDS = {"stage", "question", "case_id", "run_id", "source_export", "authority",
          "equipment_requests", "context", "pressure_checks", "plan", "replay", "detail", "solve_request",
          "fullflow_contract", "source_work", "planning_handoff"}
IDENTITY_FIELDS = ("case_id", "run_id", "source_export", "authority")
CALCULATIONS = {"manual_match", "auto_match", "equipment.match"}
ROOT = Path(__file__).resolve().parents[1]


def domain_reads(stage, question, source_work=None):
    """Resolve current paths; reading/using the domain instructions remains work."""
    from tools.product_contract import skill_location
    location = skill_location()
    skills = Path(location["path"]).parent.parent if location.get("available") else None
    names = ["chemical-engineering-expert/SKILL.md", "aspen-document-driven-flowsheet/SKILL.md",
             "chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md"]
    if source_work == "expert_plan":
        names += ["aspen-document-driven-flowsheet/references/fullflow_generation_workflow.md",
                  "aspen-document-driven-flowsheet/references/source_scaffold_handoff.md",
                  "aspen-pressure-pfd-delivery/SKILL.md"]
    if stage != "source":
        names += ["equipment-design-app/SKILL.md", "chemical-engineering-expert/references/PROCESS_EQUIPMENT_FEEDBACK.md"]
    if stage in {"reconnect", "change"}:
        names.append("aspen-pressure-pfd-delivery/SKILL.md")
    if stage == "delivery":
        names += ["aspen-plus-operations/SKILL.md", "chemical-engineering-expert/references/STRICT_ACCEPTANCE_AND_LEARNING.md"]
    lowered = question.casefold()
    # Whole-plant questions may mention distillation and unrelated MVR evaporation.
    # Route the replacement specialist only for explicit service phrases, never
    # distant word co-occurrence or the generic English word "column".
    distillation_heat_pump_hint = bool(re.search(
        r"热泵\s*精馏|精馏\s*热泵|塔顶\s*蒸[汽气]\s*再压缩|"
        r"(?:mvr|vrc)\s*精馏|精馏\s*(?:mvr|vrc)|"
        r"\b(?:mvr|vrc)(?:\s*/\s*(?:mvr|vrc))?[\s-]+distillation\b|"
        r"\bheat[\s-]+pump[\s-]+distillation\b|"
        r"\bdistillation[\s-]+(?:heat[\s-]+pump|mvr|vrc)\b|"
        r"\bvapou?r[\s-]+recompression[\s-]+distillation\b", lowered))
    column_hint = distillation_heat_pump_hint or any(word in lowered for word in ("精馏", "塔优化", "distillation", "radfrac"))
    heat_pump_hint = distillation_heat_pump_hint or any(word in lowered for word in ("热泵", "vrc", "mvr", "heat pump", "heat-pump"))
    if column_hint:
        names.append("aspen-tower-optimization-workflow/SKILL.md")
    if heat_pump_hint:
        names += ["chemical-engineering-expert/references/MACRO_DESIGN_QUALITY.md",
                  "aspen-pressure-pfd-delivery/SKILL.md"]
        if distillation_heat_pump_hint:
            names.append("aspen-heat-pump-distillation-replacement/SKILL.md")
    result = []
    for name in dict.fromkeys(names):
        path = skills / name if skills else None
        exists = bool(path and path.is_file())
        result.append({"logical_path": name, "path": str(path) if path else None,
            "available": exists, "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if exists else None,
            "reading_status": "AGENT_READING_REQUIRED_NOT_PROVEN_BY_HASH",
            "routing_boundary": "Explicit service phrases and keywords are reading hints only; the agent must classify the actual service and applicability."})
    return result


def check_expert_planning(reference, root, identity):
    """Execute the registered owner's declaration checker, never a caller's code."""
    if (not isinstance(reference, dict) or set(reference) != {"path", "sha256"}
            or not isinstance(reference["path"], str) or not reference["path"].strip()
            or not isinstance(reference["sha256"], str)
            or not re.fullmatch(r"[a-fA-F0-9]{64}", reference["sha256"])):
        raise ValueError("planning_handoff requires only a nonempty path and exact SHA-256")
    data = read_reference(root, reference)
    if not isinstance(data, dict) or data.get("schema") != "document-flow-handoff-v1" or data.get("stage") != "source":
        raise ValueError("planning_handoff must be document-flow-handoff-v1 at source stage")
    from tools.product_contract import skill_location
    location = skill_location()
    skills = Path(location["path"]).parent.parent if location.get("available") else None
    logical_path = "aspen-document-driven-flowsheet/scripts/check_flow_handoff.py"
    owner = skills / logical_path if skills else None
    if not owner or not owner.is_file():
        raise ValueError("Registered source handoff checker is unavailable; no caller or alternate checker is allowed")
    spec = importlib.util.spec_from_file_location("source_existing_handoff_checker", owner)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    checked = checker.check(data, require_expert_plan=True, require_named_methods=True,
                            require_plan_actions=True, require_reaction_math=True,
                            require_source_review=True, source_root=root)
    if (not isinstance(checked, dict) or checked.get("schema") != "document-flow-handoff-check-v1"
            or not isinstance(checked.get("errors"), list) or not isinstance(checked.get("unresolved"), list)):
        raise ValueError("Existing checker returned an invalid declaration-check result")
    if not checked["errors"]:
        if not (checked.get("expert_plan_checked") is True
                and checked.get("named_method_declarations_checked") is True
                and checked.get("plan_action_declarations_checked") is True
                and checked.get("reaction_derivations_checked") is True
                and checked.get("source_review_checked") is True):
            raise ValueError("Existing checker did not perform all required source-review, planning declaration and reaction-math checks")
        source_review = checked.get("source_review")
        if (not isinstance(source_review, dict) or source_review.get("errors") != []
                or not isinstance(source_review.get("inventory"), list) or not source_review["inventory"]
                or not isinstance(source_review.get("rows"), list)
                or len(source_review["rows"]) != len(source_review["inventory"])
                or any(source_review.get(flag) is not False for flag in
                       ("source_inventory_verified", "source_truth_verified", "engineering_accepted", "execution_verified"))):
            raise ValueError("Existing checker returned an invalid bounded source-review receipt")
        reaction_math = checked.get("reaction_math")
        math_result = reaction_math.get("result") if isinstance(reaction_math, dict) else None
        helper = reaction_math.get("helper") if isinstance(reaction_math, dict) else None
        if (not isinstance(helper, dict) or not isinstance(helper.get("path"), str)
                or not helper["path"].strip() or not isinstance(helper.get("sha256"), str)
                or not re.fullmatch(r"[a-fA-F0-9]{64}", helper["sha256"])
                or not isinstance(math_result, dict)
                or math_result.get("schema") != "reaction-derivations-check-v1"
                or math_result.get("errors") != []
                or any(math_result.get(flag) is not False for flag in
                       ("source_verified", "engineering_accepted", "reaction_feasible"))):
            raise ValueError("Existing checker returned an invalid reaction-arithmetic receipt")
        explicit_na = (
            math_result.get("status") == "not_applicable"
            and math_result.get("applicable") is False
            and math_result.get("math_checked") is False
            and math_result.get("math_valid") is False
            and math_result.get("reactions") == []
            and isinstance(math_result.get("none_reason"), str)
            and bool(math_result["none_reason"].strip()))
        checked_math = (
            math_result.get("status") == "checked"
            and math_result.get("applicable") is True
            and math_result.get("math_checked") is True
            and math_result.get("math_valid") is True
            and isinstance(math_result.get("reactions"), list)
            and bool(math_result["reactions"]))
        if not (explicit_na or checked_math):
            raise ValueError("Reaction arithmetic requires a checked valid result or explicit justified not_applicable")
    input_path = Path(reference["path"])
    input_path = input_path if input_path.is_absolute() else Path(root) / input_path
    return {
        "status": "STRUCTURE_INVALID" if checked["errors"] else "DECLARATIONS_CHECKED_WITH_UNRESOLVED" if checked["unresolved"] else "DECLARATIONS_CHECKED",
        "checker_execution_status": "EXECUTED", "input_identity": copy.deepcopy(identity),
        "input_reference": {"path": str(input_path.resolve()), "sha256": reference["sha256"].lower()},
        "declared_authority_reference": data.get("authority_reference"),
        "skill_location": location,
        "checker": {"logical_path": logical_path, "path": str(owner.resolve()),
                    "sha256": hashlib.sha256(owner.read_bytes()).hexdigest(),
                    "flags": {"require_expert_plan": True, "require_named_methods": True, "require_plan_actions": True,
                              "require_reaction_math": True, "require_source_review": True}},
        "source_review": checked.get("source_review"),
        "named_method_catalog": checked.get("named_method_catalog"),
        "reaction_math": checked.get("reaction_math"),
        "catalog_boundary": "Hash is reported only if the original checker loaded its fixed catalog; source-defined names need no catalog load.",
        "check_result": checked, "errors": checked["errors"], "unresolved": checked["unresolved"],
        "engineering_accepted": False, "execution_verified": False, "source_truth_verified": False,
        "planning_complete": False,
        "boundary": "The registered checker executed. Source-review checks bind only the explicitly supplied text documents and require one disposition per generated paragraph with registered-stream references; they do not verify the document set, extraction completeness, source meaning or correctness of dispositions. Helper execution/status is only as separately reported. Reaction arithmetic has its finite boundary. Source/body alignment, method applicability and physical judgments still need review; no reaction feasibility, Aspen execution or planning completion is certified.",
    }


def change_planning_requirements(receipt, documents):
    """Preserve handoff obligations; this does not choose or execute a repair."""
    return {
        "schema": "change-stage-planning-requirements-v1",
        "status": "PLANNING_REQUIREMENTS_ONLY", "execution_status": "NOT_EXECUTED",
        "authorization_granted_by_receipt": False, "project_specific_plan_complete": False,
        "stage_execution_id": receipt["execution_id"],
        "input_identity": copy.deepcopy(receipt["identity"]),
        "identity_status": receipt["identity_status"],
        "hash_bound_reference_names": sorted(documents),
        "unresolved_needs": copy.deepcopy(receipt["needs"]),
        "needs_sha256": canonical_sha(receipt["needs"]),
        "native_baseline": None, "protected_candidate": None, "selected_change": None,
        "consumer_scopes_to_assess": list(receipt["recalculation"]["consumers"]),
        "steps": [
            {"id": "protect_current_baseline_and_candidate", "action":
             "先定位实际当前模型、路径、哈希和运行身份，并在已有授权范围内准备受保护候选。"
             "原模型及原始诊断保留；缺文件时明确列为待补，不称已定位、复制或保护。"},
            {"id": "select_one_evidenced_change", "action":
             "根据当前故障原件或拟变更目标，选择一项有证据支持的修改并说明作用对象、理由与允许范围。"
             "没有故障不编造故障，没有依据不选择修复动作；保留未受影响的已接受部分。"},
            {"id": "replay_same_case_before_and_after", "action":
             "沿同一当前工况的基线—候选版本谱系，记录唯一声明的修改，保持其余约定输入和比较基准。"
             "按既有操作路径重放修改前后，比较原故障或变更目标、物料/产品、残差与状态及实际受影响消费者。"
             "绑定各次真实输入、输出、日志和文件身份；本字段不证明已重放。"},
            {"id": "review_differences_and_rollback_if_needed", "action":
             "核对差异是否由声明修改造成；原问题未消除或必要约束退化时，保留失败证据，"
             "在受保护候选上回退到已保存的前一版本，再决定下一项有据修改。不得覆盖原基线或隐藏失败。"},
        ],
        "boundary": "Generic handoff requirements only. Canonical references and hashes do not identify or verify a native model, "
                    "authorize edits, prove a copy/replay/rollback, or supply a project-specific repair. "
                    "The agent must fill the actual candidate, evidence-dependent change and comparison outputs. "
                    "Existing stage, engineering acceptance and strict delivery gates remain authoritative.",
    }


def check_stage(payload, evidence_root, *, search_runner, equipment_runner):
    if not isinstance(payload, dict) or set(payload) - FIELDS:
        raise ValueError("design-stage accepts declared inputs only; unknown/skip/PASS/runner fields are forbidden")
    stage, question = payload.get("stage"), payload.get("question")
    if stage not in STAGES or not isinstance(question, str) or not question.strip():
        raise ValueError("design-stage requires a registered stage and nonempty current question")
    if "detail" in payload and type(payload["detail"]) is not bool:
        raise ValueError("detail must be boolean")
    source_work = payload.get("source_work")
    if "source_work" in payload and (stage != "source" or source_work != "expert_plan"):
        raise ValueError("source_work supports only expert_plan at stage=source; omit it for a narrow source query")
    if "planning_handoff" in payload and (stage != "source" or source_work != "expert_plan"):
        raise ValueError("planning_handoff is permitted only for source_work=expert_plan at stage=source")
    root = Path(evidence_root)
    needs, queries, equipment, calls, pressure = [], [], [], [], []

    def gap(code, scope, detail):
        needs.append({"code": code, "scope": scope, "detail": detail})

    def call(kind, request, function):
        row = {"kind": kind, "request": request, "request_sha256": canonical_sha(request)}
        try:
            value = function()
            if not isinstance(value, dict):
                raise ValueError("Existing module did not return a JSON object")
            row.update(status="EXECUTED", result=value, result_sha256=canonical_sha(value))
        except (ValueError, TypeError, KeyError, AttributeError, IndexError, OSError, RuntimeError, ImportError, SyntaxError, TimeoutError, subprocess.TimeoutExpired) as exc:
            row.update(status="FAILED", error={"type": type(exc).__name__, "message": str(exc)})
            gap("MODULE_CALL_FAILED", kind, row["error"])
        calls.append(row)
        return row

    # A task question can itself contain numerical/detail keywords. Use the
    # existing exact-node API for an honest L3 system anchor, then search the
    # real question without replacing the query engine's inferred mode.
    query_requests = [{"node_id": "L3-03", "corpus": "chemical_principles", "limit": 1, "detail": False, "full_text": False},
        {"query": question, "corpus": "chemical_principles" if stage == "source" else "all",
         "limit": 5, "detail": stage != "source", "full_text": False}]
    if stage == "source" and payload.get("detail"):
        query_requests.append({"query": question, "corpus": "all", "limit": 5, "detail": True, "full_text": False})
    for request in query_requests:
        query = call("knowledge_search", request, lambda request=request: search_runner(**request))
        value = query.get("result", {})
        rows = (value.get("knowledge") or {}).get("results", [])
        query["returned_nodes"] = [{key: row.get(key) for key in
            ("node_id", "corpus", "knowledge_layer", "knowledge_status", "content_available", "text_is_excerpt", "public_path")}
            for row in rows if isinstance(row, dict)]
        query["retrieval_mode"] = (value.get("knowledge") or {}).get("mode")
        query["purpose"] = "L3_SYSTEM_PRINCIPLE_ANCHOR" if request.get("node_id") else "CURRENT_TASK_QUESTION"
        if query["status"] == "EXECUTED" and not rows:
            gap("NO_KNOWLEDGE_NODE_HITS", "knowledge", request)
        if request.get("node_id") and not any(row.get("node_id") == "L3-03" and row.get("knowledge_layer") == "L3" for row in rows):
            gap("UPPER_LAYER_ANCHOR_UNAVAILABLE", "knowledge", "The requested L3 system node was not returned")
        if value.get("equipment") is not None and value["equipment"].get("backend_exit_code") != 0:
            gap("EQUIPMENT_KNOWLEDGE_QUERY_FAILED", "knowledge", value["equipment"])
        queries.append(query)

    from tools.aspen_tool_router import solve_route
    solve_action_required = False
    solve_input = payload.get("solve_request", {})
    if not isinstance(solve_input, dict):
        solve = {"status": "FAILED", "error": "solve_request must be an object"}
        gap("SOLVE_REQUEST_INVALID", "solve_route", solve["error"])
    elif "question" in solve_input and solve_input["question"] != question:
        conflict = {"current_stage_question": question,
                    "nested_solve_question": copy.deepcopy(solve_input["question"]),
                    "repair_hint": "保留本次失败回执；删除嵌套solve_request中的重复question以继承当前阶段问题，"
                                   "或核实为同一实际问题后更正并重新调用。程序没有改写请求或自动重试。"}
        solve = {"status": "FAILED", "error": "solve_request.question differs from the current stage question",
                 "request_conflict": conflict}
        gap("SOLVE_REQUEST_INVALID", "solve_route", {"error": solve["error"], **copy.deepcopy(conflict)})
    else:
        solve_input = {**solve_input, "question": question}
        solve = call("aspen_solve_route", solve_input, lambda: solve_route(solve_input, root))
        decision = solve.get("result", {})
        if decision.get("strong_trigger") or "solve_request" in payload:
            solve_action_required = True
            gap("SOLVE_TOOL_ACTION_REQUIRED", "solve_route", {
                "status": decision.get("status"), "needs": decision.get("needs", []),
                "boundary": "Route is not native creation/execution; continue existing computations and resolve the domain action"})

    if stage == "source":
        request = {"schema": "equipment-design-agent-request-v1", "request_id": "DESIGN-STAGE-DISCOVERY",
                   "operation": "capabilities", "payload": {}}
        discovery = call("equipment_capabilities", request, lambda: equipment_runner(request))
        if discovery.get("result", {}).get("backend_exit_code") != 0:
            gap("EQUIPMENT_CAPABILITY_DISCOVERY_FAILED", "equipment", discovery.get("result"))

    identity = {name: payload.get(name) for name in IDENTITY_FIELDS}
    documents = {}
    for name, schema in (("source_export", "equipment-process-canonical-export-v1"),
                         ("authority", "equipment-process-authority-v1")):
        if not identity[name]:
            if stage != "source": gap("CURRENT_REFERENCE_REQUIRED", name, "Supply a current path and exact SHA-256")
            continue
        try:
            document = read_reference(root, identity[name])
            if not isinstance(document, dict) or document.get("schema") != schema:
                raise ValueError("Current canonical document schema required")
            if any(not identity[key] or document.get(key) != identity[key] for key in ("case_id", "run_id")):
                raise ValueError("Current case/run identity differs or is missing")
            if name == "source_export" and not isinstance(document.get("equipment"), dict):
                raise ValueError("Current canonical equipment inventory must be an object")
            if name == "authority" and (not isinstance(document.get("required_method"), str)
                    or not document["required_method"].strip()
                    or not isinstance(document.get("acceptance_criteria"), (list, dict)) or not document["acceptance_criteria"]):
                raise ValueError("Freeze a named method and explicit criteria, not a boolean PASS")
            documents[name] = document
        except (ValueError, TypeError, KeyError, OSError) as exc:
            gap("CURRENT_REFERENCE_NOT_BOUND", name, str(exc))
    if stage != "source":
        for name in ("case_id", "run_id"):
            if not isinstance(identity[name], str) or not identity[name].strip():
                gap("CURRENT_IDENTITY_REQUIRED", name, "Supply the current case/run, not a prior result")

    requests = payload.get("equipment_requests", [])
    if not isinstance(requests, list):
        gap("EQUIPMENT_LIST_INVALID", "equipment", "equipment_requests must be an array")
        requests = []
    if stage != "source" and not requests:
        gap("PHYSICAL_EQUIPMENT_LIST_REQUIRED", "equipment", "Supply each declared physical device and its current request")
    declared = set()
    for index, entry in enumerate(requests):
        row = {"index": index, "declared_input": entry}
        equipment.append(row)
        if (not isinstance(entry, dict) or set(entry) != {"equipment_id", "request"}
                or not isinstance(entry.get("equipment_id"), str) or not entry["equipment_id"].strip()
                or not isinstance(entry.get("request"), dict)):
            row["status"] = "INVALID_DECLARED_DEVICE"
            gap("PHYSICAL_DEVICE_REQUEST_INVALID", f"equipment[{index}]", "Need equipment_id and one original request object")
            continue
        tag, request = entry["equipment_id"], entry["request"]
        row["equipment_id"] = tag
        if tag in declared:
            gap("DUPLICATE_DECLARED_DEVICE", tag, "Duplicate IDs cannot prove inventory coverage")
        declared.add(tag)
        if not isinstance(request.get("operation"), str) or request["operation"] not in CALCULATIONS:
            row["status"] = "NOT_CALCULATED_OPERATION_NOT_ALLOWED"
            gap("PER_DEVICE_CALCULATION_REQUIRED", tag, "Use manual_match or auto_match, not a lookup/result/render operation")
            continue
        executed = call("equipment_calculation", request, lambda request=request: equipment_runner(request))
        row.update(executed)
        calculation = executed.get("result", {})
        if calculation.get("backend_exit_code") != 0:
            gap("EQUIPMENT_CALCULATION_FAILED", tag, calculation)
            continue
        records = list(equipment_records((calculation.get("response") or {}).get("result", {})))
        if len(records) != 1:
            gap("ONE_PHYSICAL_RECORD_REQUIRED", tag, "Calculation did not return exactly one identifiable record")
            continue
        _, wrapper, core = records[0]
        returned_tag = (core.get("normalized_input") or wrapper.get("input") or {}).get("equipment_tag") or core.get("equipment_tag") or wrapper.get("equipment_tag")
        if returned_tag != tag:
            gap("EQUIPMENT_IDENTITY_MISMATCH", tag, {"returned_equipment_id": returned_tag})
        row["calculation_pending"] = core.get("calculation_pending", [])
        # Reuse feedback's current-input binding even without extra constraints.
        if len(documents) == 2:
            context = payload.get("context", {})
            if not isinstance(context, dict) or any(key in context and context[key] != identity[key] for key in IDENTITY_FIELDS):
                gap("CONTEXT_IDENTITY_MISMATCH", tag, "Context cannot silently replace the frozen identity")
                continue
            bound_context = {**context, **identity}
            feedback = call("process_feedback", {"selector_response_sha256": executed["result_sha256"], "context": bound_context},
                            lambda calculation=calculation: build_plan(calculation["response"], bound_context, root))
            row["feedback"] = feedback
            for item in feedback.get("result", {}).get("equipment", []):
                for problem in item.get("binding_gaps", []): gap("EQUIPMENT_CURRENT_INPUT_GAP", tag, problem)

    export_ids = set((documents.get("source_export") or {}).get("equipment", {}))
    from tools.fullflow_gate import check_fullflow
    fullflow = check_fullflow(payload, root, documents=documents)
    for item in fullflow.get("needs", []):
        gap(item.get("code", "FULLFLOW_EVIDENCE_REQUIRED"),
            item.get("scope", "fullflow"), item.get("detail", item))
    whole_flow = bool(fullflow.get("gate_summary", {}).get("equipment_scope", {}).get("whole_flow_required"))
    if whole_flow:
        if not export_ids:
            gap("WHOLE_FLOW_INVENTORY_REQUIRED", "equipment", "A current nonempty physical-equipment export is required")
        if export_ids - declared:
            gap("EXPORTED_DEVICES_NOT_REQUESTED", "equipment", sorted(export_ids - declared))
        if declared - export_ids:
            gap("REQUESTED_DEVICES_NOT_IN_EXPORT", "equipment", sorted(declared - export_ids))

    expert_planning = None
    if source_work == "expert_plan":
        expert_planning = {
            "schema": "source-expert-planning-stage-v1", "status": "HANDOFF_REQUIRED",
            "checker_execution_status": "NOT_EXECUTED", "engineering_accepted": False,
            "execution_verified": False, "source_truth_verified": False, "planning_complete": False,
            "requirements": [
                "先在原handoff.source_review登记当前UTF-8来源文本及哈希，执行原checker的source-inventory取得真实段落；按原步骤逐段对应原streams，最后逆查各分支，不能用聚合区名或一个已映射分支代替整段来源。",
                "逐服务给出命名物性方法/候选、相态、依据和适用边界；候选与缺参保持未验证。",
                "按真实连接接口表达压力关系、适用计算与输入缺口，不能把无数据写成零压降。",
                "循环计划交代撕裂边的临时边界替代、先算顺序与原接口接回；不是已执行或已收敛声明。",
            ],
            "boundary": "Read and apply the existing fullflow/source-handoff workflow. These short obligations and the checker do not certify source truth, formula/physics correctness or completion, and never waive the original fullflow gates.",
        }
        if "planning_handoff" not in payload:
            gap("EXPERT_PLAN_HANDOFF_REQUIRED", "expert_planning",
                "Continue the routed source planning workflow; first inventory its explicitly supplied source_review.documents under the declared evidence root, then submit the hash-bound document-flow-handoff-v1 with paragraph dispositions and current graph")
        else:
            checked = call("source_expert_planning", {"planning_handoff": payload["planning_handoff"], "identity": identity},
                           lambda: check_expert_planning(payload["planning_handoff"], root, identity))
            if checked["status"] == "FAILED":
                expert_planning.update(status="CHECK_FAILED", checker_execution_status="FAILED", error=checked["error"],
                                       input_reference=copy.deepcopy(payload["planning_handoff"]), input_identity=copy.deepcopy(identity))
                gap("EXPERT_PLAN_HANDOFF_INVALID", "expert_planning", checked["error"])
            else:
                expert_planning.update(checked["result"])
                if expert_planning["errors"]:
                    gap("EXPERT_PLAN_STRUCTURE_INVALID", "expert_planning", expert_planning["errors"])

    checks = payload.get("pressure_checks", [])
    if not isinstance(checks, list):
        gap("PRESSURE_CHECKS_INVALID", "pressure", "Supply an array of registered method/input_basis/inputs checks")
        checks = []
    from tools.product_contract import PRESSURE_METHODS
    for check in checks:
        if (not isinstance(check, dict) or set(check) != {"method", "input_basis", "inputs"}
                or not isinstance(check.get("method"), str) or check["method"] not in PRESSURE_METHODS
                or not isinstance(check.get("input_basis"), str) or not check["input_basis"].strip()
                or not isinstance(check.get("inputs"), dict)):
            message = "Each check requires only a registered method string, nonempty input_basis string and inputs object"
            pressure.append({"kind": "pressure_calculation", "request": check,
                "request_sha256": canonical_sha(check), "status": "NOT_EXECUTED_INVALID_INPUT", "reason": message})
            gap("PRESSURE_CHECK_INVALID", "pressure", message)
            continue
        current = call("pressure_calculation", check, lambda check=check: {"checks": configuration_checks([check])})
        pressure.append(current)
        calculated = current.get("result", {}).get("checks", [])
        if not calculated or "result" not in calculated[0]:
            gap("PRESSURE_CALCULATION_NOT_COMPLETED", "pressure", current.get("result"))
    pressure_required = stage in {"reconnect", "change"}
    if pressure_required and not checks:
        gap("CURRENT_PRESSURE_RECALCULATION_REQUIRED", "pressure", "Supply current pressure checks; all unaffected calculations remain available")

    replay_result = None
    if stage == "delivery":
        if "plan" not in payload and "replay" not in payload:
            replay_result = {"status": "NOT_REQUESTED", "reason": "No process-change plan supplied; continue the original strict delivery workflow without inventing one"}
        elif not isinstance(payload.get("plan"), dict) or not isinstance(payload.get("replay"), dict):
            gap("CURRENT_DOMAIN_REPLAY_REQUIRED", "delivery", "Supply the current plan and real same-candidate domain receipts")
        else:
            plan, replay = payload["plan"], payload["replay"]
            if (any(plan.get(key) != identity[key] for key in ("case_id", "run_id", "source_export", "authority"))
                    or any(replay.get(key) != identity[key] for key in ("case_id", "run_id", "source_export"))):
                gap("REPLAY_CURRENT_IDENTITY_MISMATCH", "delivery", "A prior plan/replay cannot certify this stage")
            replay_result = call("process_replay_audit", {"plan": plan, "replay": replay}, lambda: audit_replay(plan, replay, root))
            if not replay_result.get("result", {}).get("evidence_chain_complete"):
                gap("DOMAIN_REPLAY_INCOMPLETE", "delivery", replay_result.get("result"))

    reads = domain_reads(stage, question, source_work)
    for required in fullflow.get("required_reading", []):
        if required["logical_path"] not in {item["logical_path"] for item in reads}:
            reads.append(required)
    for required in solve.get("result", {}).get("required_reading", []) if solve_action_required else []:
        if required["logical_path"] not in {item["logical_path"] for item in reads}:
            reads.append(required)
    for item in reads:
        if not item["available"]: gap("DOMAIN_INSTRUCTIONS_UNAVAILABLE", "domain", item["logical_path"])
    receipt = {"schema": "chemical-design-stage-receipt-v1", "execution_id": str(uuid.uuid4()),
        "executed_at": datetime.now(timezone.utc).isoformat(), "stage": stage, "question": question,
        "input_sha256": canonical_sha(payload), "identity": identity,
        "identity_status": "HASH_BOUND_CURRENT_CANONICAL_DOCUMENTS" if len(documents) == 2 else "INCOMPLETE_OR_SOURCE_STAGE",
        "frozen_method": documents.get("authority", {}).get("required_method"),
        "status": "ACTION_REQUIRED" if needs else "MODULE_CHECKS_EXECUTED", "needs": needs,
        "queries": queries, "equipment": equipment, "pressure": pressure, "replay": replay_result, "solve_route": solve,
        "calls": calls, "domain_reads": reads, "fullflow_gate": fullflow,
        "inventory_coverage": {"declared_count": len(requests), "declared_ids": sorted(declared),
            "export_declared_ids": sorted(export_ids), "exported_not_requested": sorted(export_ids - declared),
            "scope": "WHOLE_EXPORTED_PHYSICAL_INVENTORY" if whole_flow else "DECLARED_DEVICES_ONLY",
            "export_request_set_equal": export_ids == declared,
            "independently_verified_complete": False,
            "boundary": "Neither caller inventory nor canonical projection proves all real physical devices are covered"},
        "recalculation": {"required": pressure_required, "state": "NATIVE_FLOWSHEET_RERUN_REQUIRED" if pressure_required else "DOMAIN_WORKFLOW_REQUIRED",
            "consumers": ["affected streams", "upstream/downstream devices", "recycle/Design Specs", "heat network", "utilities and costs"] if pressure_required else [],
            "pressure_scope": "Declared-basis calculation only; no native model was changed or rerun"},
        "next_action": "Read the routed domain instructions, resolve item-local needs, and continue the authorized current model/section; do not restart accepted work or change the required method",
        "engineering_accepted": False, "flowsheet_modified": False, "stage_advanced": False,
        "acceptance_boundary": "Module execution and hashes are not engineering acceptance, real Aspen provenance, or proof of inventory completeness"}
    if stage == "change":
        receipt["planning_requirements"] = change_planning_requirements(receipt, documents)
    if expert_planning is not None:
        receipt["source_work"] = source_work
        receipt["expert_planning"] = expert_planning
        receipt["next_action"] = (
            "按已路由的 docflow fullflow_generation_workflow.md 与 source_scaffold_handoff.md 完成source_review逐段落点与来源反查、"
            "逐服务命名选法、真实接口压力关系和撕裂边临时替代—先算—接回计划；"
            "提交/修正 planning_handoff 后重查，保留候选和缺口供逐项判断。"
            "原 fullflow_contract/source 独立复核门继续有效；本回执不证明规划完成或授权越过用户停止阶段。")
    solve_result = solve.get("result") if isinstance(solve.get("result"), dict) else {}
    pressure_summary = []
    for index, row in enumerate(pressure):
        request = row.get("request") if isinstance(row.get("request"), dict) else {}
        checks = (row.get("result") or {}).get("checks", [])
        pressure_summary.append({"index": index, "method": copy.deepcopy(request.get("method")),
            "call_status": row.get("status") or "NOT_AVAILABLE",
            "call_error": copy.deepcopy(row.get("error", row.get("reason"))),
            "check_results": [{"method": item.get("method"), "status": item.get("status"),
                               "reason": item.get("reason"), "result_present": "result" in item}
                              for item in checks]})
    receipt["execution_summary"] = {
        "stage": receipt["stage"], "stage_status": receipt["status"],
        "solve_call_status": solve.get("status") or "NOT_AVAILABLE",
        "solve_result_status": solve_result.get("status") or "NOT_AVAILABLE",
        "solve_call_error": copy.deepcopy(solve.get("error")),
        "solve_result_error": copy.deepcopy(solve_result.get("error")),
        "pressure_checks": pressure_summary,
    }
    from tools import product_contract
    implementations = {name: ROOT / name for name in (
        "tools/design_stage.py", "tools/product_contract.py", "tools/fullflow_gate.py", "tools/aspen_tool_router.py",
        "tools/expert_cli.py", "tools/equipment_gateway.py", "backends/process/feedback.py", "backends/process/pressure.py")}
    implementations["tools/design_stage.py"] = Path(__file__)
    implementations["tools/product_contract.py"] = Path(product_contract.__file__)
    receipt["implementation"] = [{"path": name, "resolved_path": str(path.resolve()),
                                  "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                                 for name, path in implementations.items()]
    receipt["receipt_sha256"] = canonical_sha(receipt)
    return receipt
