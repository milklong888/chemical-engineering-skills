"""Small intent-to-existing-method contract; never builds, runs or accepts Aspen.

Natural-language matches are finite hints, not a semantic classifier. Native
cards, execution and same-case evidence remain the domain workflow's work.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re

from backends.process.selector_analysis import canonical_sha

INTENTS = ("read_value", "derive_once", "live_relation", "scan_range", "match_target",
           "optimize", "fit_data", "discrete_scenarios", "diagnose")
FIELDS = {"question", "intents", "external_request", "fit_data", "fit_authority", "study_context", "objective"}
OBJECTIVE_DIRECTIONS = ("minimize", "maximize")
STUDY_MODES = ("unspecified", "fixed_controls", "same_targets")
STUDY_LISTS = ("varied_variables", "fixed_conditions", "maintained_targets", "inner_controls")
STUDY_INTENTS = {"scan_range", "match_target", "optimize", "discrete_scenarios"}
REFERENCES = (
    "aspen-document-driven-flowsheet/references/aspen_builtin_solve_fit_tools.md",
    "aspen-plus-operations/references/operation_graph.md",
    "aspen-plus-operations/references/operations_workflow.md",
)
# These patterns suggest a review route; they never prove the user's meaning.
HINTS = {
    "read_value": r"(?:查询|读取|查看|提取).{0,16}(?:结果|物性|数值|特定值|特殊值|温度|压力|流量|焓|密度)|第\s*\d+\s*(?:板|级).{0,8}(?:温度|压力).{0,8}多少|read (?:an? |the )?(?:value|output)|property lookup",
    "derive_once": r"(?:单次|一次|仅做|只做).{0,12}(?:计算|代数|推算|换算)|one[- ]off|unit conversion",
    "live_relation": r"(?:每次|随|跟随).{0,16}(?:运行|流股|进料|物流).{0,16}(?:更新|联动|变|补)|(?:进料|流股).{0,12}(?:变化|改变).{0,12}(?:自动|联动).{0,12}(?:补|调整)|live relation|feed[- ]forward",
    "scan_range": r"扫描|扫参|扫范围|可行范围|变化规律|灵敏度|敏感性|sensitivity|scan (?:a )?range",
    "match_target": r"匹配.{0,10}(?:目标|特定值)|达到.{0,12}(?:纯度|浓度|转化率|温度|压力)|维持.{0,12}(?:纯度|产品)|(?:找到|调到).{0,10}(?:刚好|满足).{0,20}(?:回流|温度|压力|流量|目标)|target match|design[- ]?spec",
    "optimize": r"优化|最小化|最大化|最低.{0,8}(?:能耗|公用工程|成本)|optimi[sz]|minimi[sz]|maximi[sz]",
    "fit_data": r"拟合|回归|regression|fit data",
    "discrete_scenarios": r"离散|不同.{0,6}(?:拓扑|结构|流程路线|并联台数)|比较.{0,8}(?:两种|几种|不同).{0,8}流程|方案枚举|discrete|topolog(?:y|ies) comparison",
    "diagnose": r"不收敛|收敛失败|报错|诊断|控制变量.{0,6}(?:缺失|没配|不对)|参数.{0,8}(?:不适应|没跟着变)|diagnos|nonconvergen",
}
ROUTES = {
    "read_value": {
        "tools": ["EXISTING_OUTPUT_READBACK", "DEFINE_OR_PROPERTY_ANALYSIS_READ_ONLY"],
        "purpose": "先读同案现有结果与单位；需要时使用变量引用或物性分析，不为读值插入控制器。",
        "requires": ["current case/result identity", "actual output path or property definition", "unit and basis"],
        "evidence": ["same-case output/property results with path and units"],
    },
    "derive_once": {
        "tools": ["DETERMINISTIC_DERIVATION"],
        "purpose": "单次代数或单位换算直接推导，不为一次计算向模型插入 Calculator。",
        "requires": ["source quantities and units", "equation and applicability"],
        "evidence": ["source-to-equation-to-result calculation trace"],
    },
    "live_relation": {
        "tools": ["NATIVE_CALCULATOR"],
        "purpose": "随同次运行更新的物料/能量/流股关系放入原生 Calculator，先审读写依赖和执行顺序。",
        "requires": ["read/write variables", "physical formula", "execution point", "no duplicate control or circular stale dependency"],
        "evidence": ["exported CALCULATOR/DEFINE/READ-VARS/WRITE-VARS/EXECUTE", "same-run read and written values", "convergence order"],
    },
    "scan_range": {
        "tools": ["NATIVE_SENSITIVITY"],
        "purpose": "用 Aspen 原生 Sensitivity 观察范围、趋势和可行区间；不用外部逐点循环冒充原生分析。",
        "requires": ["physical varied variables", "source-bounded range", "tabulated outputs", "failed-point handling"],
        "evidence": ["exported SENSITIVITY/VARY/TABULATE", "same-run table and failed points", "downstream product and feasibility checks"],
    },
    "match_target": {
        "tools": ["REUSE_SAME_CASE_BRACKET_OR_NATIVE_SENSITIVITY", "NATIVE_DESIGN_SPEC_VARY"],
        "purpose": "先复用已核验且未失效的同案区间，否则用原生 Sensitivity 定界；再以原生 Design Spec/Vary 匹配目标。",
        "requires": ["target expression/unit and equality vs minimum meaning", "independent physical manipulated variable", "current feasible bracket and bounds", "no Calculator/fixed-card duplicate control"],
        "evidence": ["current bracket applicability or new SENSITIVITY results", "exported DESIGN-SPEC/VARY or RadFrac SPEC/VARY", "target residual/status", "same-run downstream gates"],
    },
    "optimize": {
        "tools": ["NATIVE_OPTIMIZATION", "INNER_DESIGN_SPECS_WHEN_REQUIRED"],
        "purpose": "可行模型上按目标、约束和连续变量进行原生 Optimization；需要时内层 Design Spec 保持相同产品基准。多变量本身不是外部优化的理由。",
        "requires": ["feasible current model", "objective components", "constraints and continuous degrees of freedom", "physical bounds", "same-product basis"],
        "evidence": ["exported OPTIMIZATION and any inner DS/VARY", "objective and active constraints", "same-candidate residuals and downstream gates"],
    },
    "fit_data": {
        "tools": ["REGRESSION_OR_PROPERTY_DATA_REGRESSION"],
        "purpose": "仅在有原始数据与当前授权时拟合可辨识参数；不靠调动力学或物性常数凑目标。",
        "requires": ["primary data, units and uncertainty", "current fitting authority", "identifiable parameters and bounds", "residual weighting and validity range"],
        "evidence": ["source-bound data and authority", "fit residuals and parameter uncertainty", "exported fitted cards and same-case rerun"],
    },
    "discrete_scenarios": {
        "tools": ["EXTERNAL_DISCRETE_ORCHESTRATION", "APPLICABLE_NATIVE_TOOLS_WITHIN_EACH_SCENARIO"],
        "purpose": "离散结构/路线场景可由外部程序编排；各工况内部仍使用适用原生工具，结构变化与执行授权另行确认。",
        "requires": ["explicit discrete alternatives and authorization", "common comparison basis", "per-scenario native tool assessment", "failure and final rerun policy"],
        "evidence": ["scenario-to-native-case lineage", "same-basis result table including failures", "exact selected native case rerun"],
    },
    "diagnose": {
        "tools": ["CURRENT_RUN_DIAGNOSTICS_AND_DOMAIN_REPAIR"],
        "purpose": "先定位当前真实诊断和首个失效原因，不能用扫参数掩盖错误物性、拓扑、单位或控制冲突。",
        "requires": ["current raw history and block status", "source authority", "first failing dependency"],
        "evidence": ["same-case diagnostic lines", "attributable repair and unchanged acceptance gates"],
    },
}


def objective_contract(value, intents):
    """Require a declared preference for optimize, not a semantic or source proof."""
    if not isinstance(value, dict) or set(value) - {"definition", "direction"}:
        raise ValueError("objective accepts only definition and direction")
    if "definition" in value and (not isinstance(value["definition"], str) or not value["definition"].strip()):
        raise ValueError("objective definition must be a nonempty string")
    if "direction" in value and (not isinstance(value["direction"], str) or value["direction"] not in OBJECTIVE_DIRECTIONS):
        raise ValueError("objective direction must be minimize or maximize")
    applicable = "optimize" in intents
    return {"applicable": applicable, "declaration": value,
        "missing_parts": [field for field in ("definition", "direction") if field not in value] if applicable else [],
        "semantic_verified": False,
        "boundary": "Caller declaration only, not a source, user-scope, objective-function, feasibility or execution proof. Target matching alone does not supply a preference objective; never invent one to make a route available."}


def study_contract(value, intents):
    """Preserve declared experiment roles, never certify their physical meaning."""
    if not isinstance(value, dict) or set(value) - {"mode", *STUDY_LISTS}:
        raise ValueError("study_context accepts only mode and declared variable-role lists")
    mode = value.get("mode", "unspecified")
    if not isinstance(mode, str) or mode not in STUDY_MODES:
        raise ValueError("Unknown study_context mode")
    for field in STUDY_LISTS:
        items = value.get(field, [])
        if not isinstance(items, list) or any(not isinstance(x, str) or not x.strip() for x in items):
            raise ValueError("study_context variable roles must be arrays of nonempty strings")
    applicable = bool(set(intents) & STUDY_INTENTS)
    missing = []
    policy = "NOT_APPLICABLE"
    if applicable:
        if mode == "unspecified":
            missing.append("comparison_mode")
        missing.extend(field for field in ("varied_variables", "fixed_conditions") if not value.get(field))
        policy = {"unspecified": "CLASSIFY_COMPARISON_FIRST", "fixed_controls": "KEEP_DECLARED_SETTINGS",
                  "same_targets": "RE_SOLVE_AUTHORIZED_TARGET_CONTROLS"}[mode]
        if mode == "same_targets":
            if not value.get("maintained_targets"):
                missing.append("maintained_targets")
            if not value.get("inner_controls"):
                missing.append("inner_controls_or_passive_target_justification")
            if not value.get("maintained_targets") or not value.get("inner_controls"):
                policy = "CLASSIFY_COMPARISON_FIRST"
    return {"status": "AGENT_REVIEW_REQUIRED" if applicable else "NOT_APPLICABLE",
        "comparison_mode": mode, "declaration": value, "missing_parts": missing,
        "inner_control_policy": policy, "semantic_verified": False,
        "boundary": "Declared names are not a degree-of-freedom, unit, control, or same-case proof. Empty inner controls may be justified by naturally satisfied targets; never invent a controller to fill a field."}


def decision_chain(intents, study):
    """Observable next-action guidance, not hidden reasoning or an executed plan."""
    selected = set(intents)
    steps = [{"id": "define_engineering_question", "action": "先用工程含义说明要查值、研究响应、匹配目标还是找更优点；控制变量先按物理作用理解，不先等同界面槽位。"}]
    feedback = []
    if not selected:
        steps.append({"id": "classify_next_action", "action": "从当前请求与资料确认任务意图；有限关键词未命中不是工具不可用，不自行开始试算。"})
    elif selected <= {"read_value", "derive_once"}:
        steps.append({"id": "use_current_results_or_derive", "action": "读取当前有效结果或做有据的一次推导；只补影响该结论的缺项，不加控制器、扫描或全流程审计。"})
    else:
        if "diagnose" in selected:
            steps.append({"id": "classify_failure_before_interface_probe", "action": "先依据当前报错分清物理/输入/控制关系与接口问题；识别变量影响谁、由谁维持指标，再针对性查映射、单位和卡片，不盲扫掩盖根因。"})
        if selected & STUDY_INTENTS:
            steps.extend([
                {"id": "define_comparison_basis", "action": "确认研究条件：fixed_controls保持约定操作设置看响应，不强开内层控制；same_targets按约定目标逐点重解必要的授权控制，或核实目标自然满足。不能算前者却宣称后者最优。", "policy": study["inner_control_policy"]},
                {"id": "derive_seed_or_reuse_valid_bracket", "action": "用当前可行基准、守恒/代数关系给初值；有未失效的同案区间就复用，未知响应才有界稀疏扫描。初值不是永久固定规格。"},
                {"id": "map_controls_and_degrees_of_freedom", "action": "分清研究变量、保持条件、目标和授权操纵量；检查目标—操纵量配对、自由度和唯一主写入者。接口字段检查实现这个关系，不能替代它。"},
            ])
        if "live_relation" in selected:
            steps.append({"id": "audit_live_dependency_and_writer", "action": "显式关系才用Calculator；列出本轮读值、公式、写入者和下游消费者，区分初始化与每轮执行，不覆盖Design Spec的操纵量。"})
        if "fit_data" in selected:
            steps.append({"id": "verify_fit_authority_and_identifiability", "action": "先核实原始数据、当前拟合授权、单位与可辨识性，不能为达标任意改模型常数。"})
        steps.extend([
            {"id": "select_existing_method", "action": "按已确认问题使用现有方法owner和routes；先解决diagnose分支的相关前置问题，多个工具标签不是要求全部同时执行。"},
            {"id": "verify_native_definition_and_current_execution", "action": "在保护候选通过既有操作路径建立适用对象，核对当前版本导出、执行顺序与结果；工具名、哈希、旧检索缺口都不证明执行或能力。"},
        ])
        if selected & STUDY_INTENTS:
            steps.append({"id": "evaluate_result_and_restore_selected_case", "action": "逐点核对约定比较基准、控制残差/状态及相关全流程约束，再比较目标；保留失败点。恢复选定工况并说明分析启停状态，交付时复验精确文件。"})
            feedback = [
                {"signal": "response_flat_or_controls_unchanged", "next_action": "先核对真实写入、当前读值、控制残差和状态；数值不变既不证明未求解，也不证明已求解。"},
                {"signal": "local_objective_improves_but_required_gate_fails", "next_action": "该点不进入可行优选；回查目标完整性、物理机制和受影响下游，不只扩大变量边界。"},
                {"signal": "best_sample_near_failed_boundary", "next_action": "识别物理或数值失败原因，再按需要局部细化；声明实际范围和分辨率，不把采样优选说成全局最优。"},
                {"signal": "feed_property_topology_or_basis_changed", "next_action": "只使受影响的区间、控制和结果证据失效并重算；未受影响证据可继续复用。"},
            ]
    return {"status": "AGENT_REVIEW_REQUIRED", "steps": steps, "feedback_triggers": feedback,
            "execution_proven": False, "feedback_events_evaluated": False}


def reference_inventory(intents):
    from tools.product_contract import skill_location
    location = skill_location()
    root = Path(location["path"]).parent.parent if location.get("available") else None
    result = []
    selected = REFERENCES[:2] if set(intents) <= {"read_value", "derive_once"} else REFERENCES
    for relative in selected:
        path = root / relative if root else None
        available = bool(path and path.is_file())
        result.append({"logical_path": relative, "path": str(path) if path else None,
            "available": available, "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if available else None,
            "reading_status": "AGENT_READING_REQUIRED_NOT_PROVEN_BY_HASH", "reading_scope": "RELEVANT_SECTION"})
    return result


def inspect_reference(reference, root):
    """Check referenced bytes only; neither technical applicability nor authority."""
    result = {"reference": reference, "hash_verified": False, "semantic_review": "NOT_PERFORMED"}
    if not isinstance(reference, dict) or set(reference) != {"path", "sha256"}:
        return {**result, "issue": "Provide only path and sha256"}
    if not isinstance(reference["path"], str) or not reference["path"].strip() or not isinstance(reference["sha256"], str) or not re.fullmatch(r"[0-9a-fA-F]{64}", reference["sha256"]):
        return {**result, "issue": "Invalid path or SHA-256"}
    path = Path(reference["path"])
    if not path.is_absolute():
        path = Path(root) / path
    try:
        data = path.read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        result.update(path=str(path.resolve()), actual_sha256=actual, size=len(data),
                      hash_verified=bool(data) and actual.lower() == reference["sha256"].lower())
        if not result["hash_verified"]:
            result["issue"] = "Missing contents or SHA-256 mismatch"
    except OSError as exc:
        result["issue"] = str(exc)
    return result


def solve_route(payload, evidence_root):
    if not isinstance(payload, dict) or set(payload) - FIELDS:
        raise ValueError("solve-route accepts only declared routing inputs; PASS/skip/execution claims are forbidden")
    question = payload.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("solve-route requires a nonempty question")
    explicit = payload.get("intents", [])
    if not isinstance(explicit, list) or any(not isinstance(item, str) or item not in INTENTS for item in explicit):
        raise ValueError("intents must be an array of registered strings")
    hints = [{"intent": name, "matched_text": match.group(0)} for name, pattern in HINTS.items()
             if (match := re.search(pattern, question, re.I))]
    hinted = [row["intent"] for row in hints]
    # Explicit classification does not erase a conflicting strong hint. The
    # domain agent must resolve that ambiguity, rather than silently bypass it.
    conflicts = sorted(set(hinted) - set(explicit)) if explicit else []
    intents = list(dict.fromkeys([*explicit, *hinted]))
    objective = objective_contract(payload.get("objective", {}), intents)
    classification_required = not intents or bool(conflicts) or bool(objective["missing_parts"])
    study = study_contract(payload.get("study_context", {}), intents)
    ambiguous_multivariable = bool(re.search(r"多变量|多个连续变量|多参数|几个参数|multivariable|multiple variables", question, re.I)) and not intents
    needs = []
    if classification_required:
        needs.append({"code": "AGENT_CLASSIFICATION_REQUIRED",
            "detail": "尚未形成可采用的工具路线。对照原请求核查显式意图与关键词冲突；否定句或背景提及也可能命中。保留当前回执，按已核实的实际任务重述后再调用，或明确报告仍待分类。不要把候选意图转述为已经选定的路线。",
            "conflicting_hints": conflicts})
    if objective["missing_parts"]:
        needs.append({"code": "OPTIMIZATION_OBJECTIVE_DECLARATION_REQUIRED", "scope": "objective",
            "detail": "候选含 optimize，但尚未声明优选目标及方向。核对原问题和当前来源：确有优选目标才补 definition 与 minimize/maximize；只有达标任务则更正错传意图后重调。保留原请求和回执，不为填字段编造目标或删去真实任务；声明不替代来源、用户范围或工程核验。",
            "missing_parts": objective["missing_parts"]})
    if study["missing_parts"]:
        needs.append({"code": "STUDY_CONTEXT_REVIEW_REQUIRED", "scope": "study_context", "detail": "Resolve only the relevant comparison roles from current authority; do not invent missing controls or block unrelated work", "missing_parts": study["missing_parts"]})
    # An unresolved interpretation must not simultaneously emit a selected
    # domain route or its execution steps. Preserve raw candidates below so the
    # agent can inspect and resolve the conflict without hiding the first receipt.
    routed_intents = [] if classification_required else intents
    plans = [{"intent": intent, **ROUTES[intent], "execution_status": "NOT_EXECUTED_BY_ROUTER"} for intent in routed_intents]
    for plan in plans:
        needs.append({"code": "DOMAIN_TOOL_ACTION_REQUIRED", "intent": plan["intent"], "detail": plan["purpose"]})
    refs = reference_inventory(intents)
    for item in refs:
        if not item["available"]:
            needs.append({"code": "DOMAIN_REFERENCE_UNAVAILABLE", "detail": item["logical_path"]})

    fitting = None
    if "fit_data" in intents:
        fitting = {name: inspect_reference(payload.get(name), evidence_root) for name in ("fit_data", "fit_authority")}
        fitting["authorized"] = False
        fitting["status"] = "DATA_AND_AUTHORITY_SEMANTIC_REVIEW_REQUIRED"
        if not all(fitting[name]["hash_verified"] for name in ("fit_data", "fit_authority")):
            needs.append({"code": "FIT_DATA_AND_AUTHORITY_REQUIRED", "detail": "Provide source data and current fitting authorization; hash checks never prove their meaning"})

    external = {"requested": "external_request" in payload, "execution_authorized": False,
        "status": "NOT_REQUESTED", "native_assessment_required": True,
        "policy": "Preserve an explicit current user method; document native applicability and real acceptance. A reason string or hash is not authorization."}
    if external["requested"]:
        request = payload["external_request"]
        if not isinstance(request, dict) or set(request) != {"reason", "evidence"} or not isinstance(request["reason"], str) or not request["reason"].strip() or not isinstance(request["evidence"], list):
            raise ValueError("external_request requires only a nonempty reason and evidence array; no caller approval flags")
        evidence = [inspect_reference(item, evidence_root) for item in request["evidence"]]
        external.update(reason=request["reason"], evidence=evidence, status="DOMAIN_REVIEW_REQUIRED")
        needs.append({"code": "EXTERNAL_NATIVE_APPLICABILITY_REVIEW_REQUIRED", "detail": "Assess specific native limitations and current method authority; router grants no substitution or execution permission"})
        if not evidence or not all(item["hash_verified"] for item in evidence):
            needs.append({"code": "EXTERNAL_LIMITATION_EVIDENCE_REQUIRED", "detail": "Submit inspectable evidence for the specific native limitation; convenience or variable count is insufficient"})

    result = {"schema": "aspen-solve-route-v1", "question": question, "input_sha256": canonical_sha(payload),
        "status": "AGENT_CLASSIFICATION_REQUIRED" if classification_required else "ACTION_REQUIRED",
        "classification": {"explicit_intents": explicit, "finite_hints": hints, "intents": intents,
            "semantic_completeness": False, "conflicts": conflicts, "ambiguous_multivariable": ambiguous_multivariable,
            "routing_ready": not classification_required},
        "strong_trigger": bool(intents or ambiguous_multivariable or external["requested"]),
        "routes": plans, "pending_route_intents": intents if classification_required else [],
        "needs": needs, "required_reading": refs, "fitting": fitting, "external_request": external,
        "study": study, "objective": objective, "decision_chain": decision_chain(routed_intents, study),
        "vendor_sensitivity": {"classification": "EXTERNAL_POINT_SWEEP_NOT_NATIVE", "native_sensitivity_evidence": False,
            "implementation": "vendor/aspen-mcp-toolkit/src/aspen_mcp/tools/sensitivity_advanced.py",
            "boundary": "Python values loop writes parameters and reruns; it does not create native SENSITIVITY or DESIGN-SPEC objects"},
        "native_execution_interface": "No new native builder or executor in this router; use existing domain workflow and version-verified paths",
        "native_tools_created": False, "native_tools_executed": False, "native_evidence_verified": False,
        "engineering_accepted": False, "flowsheet_modified": False, "stage_advanced": False}
    result["receipt_sha256"] = canonical_sha(result)
    return result
