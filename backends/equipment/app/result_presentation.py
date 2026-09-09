from __future__ import annotations

import hashlib
import html
import json
import re
from typing import Any

import customer_delivery


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def _is_match_result(value: Any) -> bool:
    return isinstance(value, dict) and (
        value.get("schema") == "equipment-deterministic-match-result-v1"
        or "design_parameter_package" in value
    )


def extract_match_results(payload: Any) -> list[dict[str, Any]]:
    """Extract deterministic equipment results without merging different devices."""
    found: list[dict[str, Any]] = []
    seen: set[int] = set()

    def walk(value: Any) -> None:
        if id(value) in seen:
            return
        if isinstance(value, (dict, list)):
            seen.add(id(value))
        if isinstance(value, dict) and value.get("schema") == "equipment-design-hybrid-result-v2":
            # A hybrid envelope intentionally retains both the initial and the
            # replayed result.  The GUI/report must render the active replay
            # once, not show two cards with the same equipment ID and default
            # to the stale initial card.
            active = value.get("deterministic_recalculation") or value.get("deterministic_result")
            walk(active)
            return
        if _is_match_result(value):
            found.append(value)
            return
        if isinstance(value, list):
            for item in value:
                walk(item)
            return
        if not isinstance(value, dict):
            return
        if isinstance(value.get("match_result"), dict):
            walk(value["match_result"])
        for key in (
            "result", "value", "equipment", "items", "deterministic_result",
            "deterministic_recalculation", "llm_applied_draft",
        ):
            if key in value:
                walk(value[key])

    walk(payload)
    return found


def _predicate_summary(candidate: dict[str, Any]) -> dict[str, int]:
    counts = {"PASS": 0, "FAIL": 0, "UNKNOWN": 0}
    for predicate in candidate.get("predicate_trace", []):
        state = str(predicate.get("status", "UNKNOWN")).upper()
        counts[state if state in counts else "UNKNOWN"] += 1
    return counts


def _equipment_card(result: dict[str, Any], index: int) -> dict[str, Any]:
    match = result.get("match", {})
    package = result.get("design_parameter_package", {})
    executed_by_key = {
        (item.get("calculation_id"), item.get("target_field")): item
        for item in result.get("calculations", [])
        if isinstance(item, dict)
    }
    calculation_chain: list[dict[str, Any]] = []
    for packaged_item in package.get("calculation_chain", []):
        if not isinstance(packaged_item, dict):
            continue
        item = dict(packaged_item)
        executed = executed_by_key.get(
            (item.get("calculation_id"), item.get("target_field"))
        )
        if isinstance(executed, dict):
            for field in (
                "formula_trace",
                "calculation_notice",
                "canonical_value",
                "evidence_status",
            ):
                if field in executed:
                    item[field] = executed[field]
        calculation_chain.append(item)
    model = result.get("model_recommendation", {})
    decision = result.get("model_decision", {})
    normalized = result.get("normalized_input", {})
    candidates: list[dict[str, Any]] = []
    for candidate in model.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        candidate_missing_gates = candidate.get("missing_gates")
        if candidate_missing_gates is None:
            candidate_missing_gates = candidate.get("completeness", {}).get("missing_fields", [])
        candidate_formal_model_gate = candidate.get("formal_model_gate")
        if candidate_formal_model_gate is None:
            candidate_formal_model_gate = model.get("formal_model_gate")
        candidates.append({
            **candidate,
            "predicate_summary": _predicate_summary(candidate),
            "model_status_ceiling": (
                "final_model" if candidate.get("formal_model")
                else "vendor_candidate" if candidate.get("is_vendor_model")
                else "engineering_or_standard_candidate"
            ),
            "missing_gates": candidate_missing_gates,
            "formal_model_gate": candidate_formal_model_gate,
        })
    hard_blockers = [
        item for item in result.get("calculation_pending", [])
        if str(item.get("status", "")).startswith("BLOCKED_")
    ]
    conflicts = list(result.get("normalization_conflicts", []))
    conflicts.extend(result.get("parameter_errors", []))
    progress = result.get("progress", {})
    equipment_id = str(
        normalized.get("equipment_tag")
        or normalized.get("aspen_block_type")
        or f"equipment-{index + 1}"
    )
    model_status = decision.get("model_status") or model.get("formal_model_status") or "unknown"
    terminal_selection = model.get("terminal_selection", {})
    delivery = "READY" if model_status == "final_model" else "NOT_READY"
    customer_bundle = result.get("customer_delivery")
    if not isinstance(customer_bundle, dict):
        try:
            customer_bundle = customer_delivery.build_customer_delivery(result)
        except customer_delivery.CustomerDeliveryError:
            customer_bundle = None
    overview_rows = (
        customer_bundle.get("equipment_overview_table", {}).get("rows", [])
        if isinstance(customer_bundle, dict) else []
    )
    datasheet_rows = (
        customer_bundle.get("equipment_family_datasheet", {}).get("equipment", [])
        if isinstance(customer_bundle, dict) else []
    )
    evidence_records = (
        customer_bundle.get("equipment_evidence_index", {}).get("records", [])
        if isinstance(customer_bundle, dict) else []
    )
    model_estimate_inputs = [
        dict(item) for item in result.get("model_estimate_inputs", [])
        if isinstance(item, dict)
    ]
    estimate_fields = sorted({
        str(item.get("field_id")) for item in model_estimate_inputs if item.get("field_id")
    })
    applied_estimate_fields = sorted({
        str(item.get("field_id"))
        for item in model_estimate_inputs
        if item.get("field_id") and item.get("auto_applied") is True
        and not str(item.get("state") or "").startswith("SUPERSEDED_")
    })
    superseded_estimate_fields = sorted(set(estimate_fields) - set(applied_estimate_fields))
    model_estimate_disclosure = (
        datasheet_rows[0].get("model_estimate_disclosure")
        if datasheet_rows
        and isinstance(datasheet_rows[0].get("model_estimate_disclosure"), dict)
        else {
            "llm_used": bool(result.get("llm_used")) and bool(model_estimate_inputs),
            "status": "PROVISIONAL_ESTIMATES_USED" if applied_estimate_fields else (
                "MODEL_ESTIMATES_SUPERSEDED" if superseded_estimate_fields else "NOT_USED"
            ),
            "model_estimate_fields": estimate_fields,
            "applied_model_estimate_fields": applied_estimate_fields,
            "superseded_model_estimate_fields": superseded_estimate_fields,
            "estimates": model_estimate_inputs,
            "evidence_class": "J" if model_estimate_inputs else None,
            "promotion_cap": "TYPE_SCREENING" if applied_estimate_fields else None,
            "statement": (
                "含大模型 J/provisional 工程估算；仅限 TYPE_SCREENING，正式选型前必须替换并重算。"
                if model_estimate_inputs else "未使用大模型工程估算。"
            ),
        }
    )
    return {
        "equipment_id": equipment_id,
        "header": {
            "equipment_tag": normalized.get("equipment_tag"),
            "equipment_type": normalized.get("equipment_type"),
            "process_function": normalized.get("process_function"),
            "aspen_block_type": normalized.get("aspen_block_type"),
            "family_id": match.get("family_id"),
            "family_name": match.get("family_name"),
            "recommended_type": model.get("recommended_type"),
            "source_result_sha256": _canonical_sha256(result),
            "engine_version": result.get("engine_version"),
        },
        "status_axes": {
            "identity": result.get("status", "UNKNOWN"),
            "process_basis": result.get("input_provenance", {}).get("status", "UNKNOWN"),
            "calculation": package.get("status_axes", {}).get("calculation", "UNKNOWN"),
            "candidate_matching": package.get("status_axes", {}).get("candidate_matching", "UNKNOWN"),
            "model": model.get("status", "UNKNOWN"),
            "terminal_form": terminal_selection.get("status", "UNKNOWN"),
            "formal_model": model_status,
            "delivery": delivery,
        },
        "parameter_groups": package.get("groups", []),
        "terminal_selection": terminal_selection,
        "engineering_adjustment_plan": result.get(
            "engineering_adjustment_plan", {}
        ),
        "selection_agent_control": result.get(
            "selection_agent_control", {}
        ),
        "calculation_chain": calculation_chain,
        "constraint_checks": package.get("constraint_checks", []),
        "selection_feature_vector": package.get("selection_feature_vector", {}),
        "candidates": candidates,
        "issues": {
            "hard_blockers": hard_blockers,
            "conflicts": conflicts,
            "ignored_input_diagnostics": result.get("ignored_input_diagnostics", []),
            "ignored_parameter_diagnostics": result.get("ignored_parameter_diagnostics", []),
            "missing_by_goal": progress.get("next_fields", []),
            "minimum_missing_sets": progress.get("minimum_missing_sets", []),
            "evidence_gaps": decision.get("verification_missing_fields", []),
            "formal_promotion_blockers": model.get("formal_promotion_blockers", []),
            "calculation_notices": package.get("calculation_notices", []),
            "design_fallbacks": result.get("design_fallbacks", package.get("design_fallbacks", [])),
            "input_recommendations": result.get("input_recommendations", package.get("input_recommendations", {})),
            "model_estimate_inputs": model_estimate_inputs,
        },
        "formal_model_gate": model.get("formal_model_gate"),
        "prohibited_claim": model.get("prohibited_claim"),
        "customer_overview": overview_rows[0] if overview_rows else None,
        "customer_datasheet": datasheet_rows[0] if datasheet_rows else None,
        "customer_evidence_records": evidence_records,
        "llm_used": bool(model_estimate_disclosure.get("llm_used")),
        "model_estimate_inputs": model_estimate_inputs,
        "model_estimate_disclosure": model_estimate_disclosure,
    }


def build_presentation(payload: Any) -> dict[str, Any]:
    results = extract_match_results(payload)
    cards = [_equipment_card(result, index) for index, result in enumerate(results)]
    llm_used = any(bool(card.get("llm_used")) for card in cards)
    disclosure_equipment = [
        {
            "equipment_id": card.get("equipment_id"),
            **card.get("model_estimate_disclosure", {}),
        }
        for card in cards
        if card.get("model_estimate_disclosure", {}).get("model_estimate_fields")
        or card.get("model_estimate_disclosure", {}).get("equipment")
    ]
    disclosure_status = (
        "PROVISIONAL_ESTIMATES_USED"
        if any(item.get("applied_model_estimate_fields") for item in disclosure_equipment)
        else "MODEL_ESTIMATES_SUPERSEDED"
        if any(item.get("superseded_model_estimate_fields") for item in disclosure_equipment)
        else "NOT_USED"
    )
    return {
        "schema": "equipment-design-presentation-v1",
        "source_payload_sha256": _canonical_sha256(payload),
        "equipment_count": len(cards),
        "equipment": cards,
        "status_color_policy": {
            "green": ["final_model", "same_equipment_verified", "READY"],
            "blue": ["MATCHED", "READY_FOR_CANDIDATE_MATCHING", "type_selected"],
            "yellow": ["PARTIAL", "INCOMPLETE", "NOT_READY", "UNKNOWN"],
            "red": ["BLOCKED", "FAIL", "CONFLICT"],
            "grey": ["NOT_APPLICABLE"],
        },
        "deterministic": True,
        "llm_used": llm_used,
        "model_estimate_disclosure": {
            "llm_used": llm_used,
            "status": disclosure_status,
            "equipment": disclosure_equipment,
            "statement": (
                "本展示含已披露的大模型 J/provisional 工程估算；仅限 TYPE_SCREENING，正式选型前必须替换并重算。"
                if llm_used else "本展示未使用大模型工程估算。"
            ),
        },
    }


def _cell(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return html.escape(str(value))


_CODE_LABELS = {
    "normalized_input": "输入值",
    "deterministic_calculation": "内置公式计算 ⚠",
    "provisional_screening_calculation": "内置初筛公式 ⚠",
    "not_available": "待补充",
    "PROVIDED": "已提供",
    "CALCULATED": "已计算",
    "MISSING": "待补充",
    "EXTERNAL_REQUIRED": "需外部证据",
    "MATCHED": "身份已匹配",
    "AMBIGUOUS": "待消歧",
    "UNMATCHED": "未匹配",
    "BLOCKED_CALCULATION": "计算已阻断",
    "PARTIAL": "部分闭合",
    "READY": "已具备",
    "NOT_READY": "未闭合",
    "type_selected": "型式已确定",
    "EXPLICIT_TERMINAL_TYPE_SELECTED": "已指定型式",
    "CONDITIONED_TERMINAL_TYPE_SELECTED": "条件选定",
    "DEFAULTED_TERMINAL_TYPE_SELECTED": "默认选定",
    "controlled_registered_condition_rule": "登记条件规则",
    "condition_rule": "确定性条件规则",
    "condition_rule_with_registered_default": "条件默认规则",
    "aspen_block_registered_default": "Aspen 模块登记默认",
    "registered_default": "设备族登记默认",
    "same_equipment_verified": "同设备已验证",
    "calculation_blocked": "计算已阻断",
    "custom_equipment_no_universal_model": "非通用定制设备",
    "candidate": "候选",
    "vendor_candidate": "厂家候选",
    "standard_candidate": "标准候选",
    "final_model": "正式型号",
    "NOT_ESTABLISHED_BY_MATCHER_INPUT": "流程依据待核",
    "READY_FOR_CANDIDATE_MATCHING": "可执行候选匹配",
    "STANDARD_MARKING_CANDIDATES": "标准标记候选",
    "standard_marking": "标准规格",
    "engineered_designation": "具体工程型式（非厂家型号）",
    "component_marking": "具体部件规格（非厂家型号）",
    "generic_type_placeholder": "旧版泛型占位（不合格）",
    "NEAR_STANDARD_DESIGN_POINT": "旧版近标准设计点（已停用）",
    "HEURISTIC_NEAREST_STANDARD_REFERENCE_POINT": "启发式最近标准参考点（非性能曲线适配）",
    "RANKED_STANDARD_REFERENCE_POINT": "标准参考点",
    "ENGINEERING_CANDIDATE_READY": "工程候选已就绪",
    "PARTIAL_ENGINEERING_CANDIDATE": "工程候选待补充",
    "SATISFIED_BY_PROVIDED_VALUE": "已采用输入值",
    "ENGINEERING_SPEC_CANDIDATES": "工程规格候选",
    "VENDOR_CANDIDATES": "厂家型号候选",
    "WAITING_CALCULATED_PARAMETERS": "等待参数闭合",
    "CALCULATED_WITH_EXPLICIT_INPUTS": "已按显式输入计算",
    "PROVISIONAL_SCREENING_CROSSCHECK_PASS": "初筛交叉核对一致",
    "PROVISIONAL_SCREENING_DIFFERENCE": "初筛值与提供值不同",
    "WARNING_PROVISIONAL_SCREENING_DIFFERENCE": "初筛差异（不覆盖提供值）",
    "MISSING_INPUTS": "缺少输入",
    "PASS": "通过",
    "BLOCKED": "未通过",
    "COMPLETE": "完整",
    "PROVISIONAL_WITH_VISIBLE_GAPS": "有明确缺项",
    "NOT_APPLICABLE": "不适用（流程逻辑节点）",
    "NOT_APPLICABLE_SIMULATION_LOGIC_NODE": "Aspen 流程逻辑节点不对应独立设备型号",
    "RECOMMENDED_ALGORITHMIC_MODIFICATION": "程序已给出非标/多台组合修改方案",
    "REVIEW_REQUIRED_NO_SAFE_AUTOMATIC_CONFIGURATION": "程序已给出评审路线，尚无安全自动配置",
    "NOT_TRIGGERED_WITHIN_SCREENING_POLICY": "未触发程序非标拆分阈值",
    "CONTROLLED_WITH_ADJUSTMENT_WARNING": "已执行计算后选型并强制显示修改警告",
    "CONTROLLED_CALCULATE_THEN_SELECT": "已执行计算后选型控制",
    "algorithmic_modification_screening_only": "算法多台/非标方案（仅初筛）",
    "algorithmic_configuration_review_required": "算法配置需专项评审",
}

_AXIS_LABELS = {
    "identity": "设备身份",
    "process_basis": "流程依据",
    "calculation": "计算闭合",
    "candidate_matching": "候选匹配",
    "model": "型号状态",
    "terminal_form": "终选型式来源",
    "formal_model": "正式状态",
    "delivery": "交付状态",
}


# One shared, user-facing contract is consumed by both the HTML report and the
# desktop GUI.  Keeping this list here prevents either view from silently
# reducing the authoritative overview to a handful of convenient fields.
CUSTOMER_OVERVIEW_DISPLAY_FIELDS = (
    ("sequence_number", "序号"),
    ("process_section", "工艺段 / 装置"),
    ("equipment_tag", "设备位号 / 管线号"),
    ("equipment_name", "设备名称"),
    ("quantity_and_standby", "数量及备用"),
    ("equipment_type", "型式 / 结构"),
    ("model_or_specification", "型号 / 工程规格"),
    ("model_or_specification_status", "型号状态"),
    ("engineering_adjustment_status", "非标/多台修改状态"),
    ("engineering_adjustment_plan", "程序修改方案"),
    ("algorithmic_selection_warning", "算法选型强制警告"),
    ("selection_agent_control_status", "Agent计算后选型控制"),
    ("authority_structural_completeness", "权威表结构完整性"),
    ("authority_information_coverage", "权威表信息覆盖"),
    ("customer_information_coverage", "客户信息覆盖"),
    ("selection_specificity_gate", "具体选型门"),
    ("formal_readiness_gate", "正式就绪门"),
    ("standards_and_versions", "采用标准及版本"),
    ("evidence_ids", "计算书 / 软件 / 厂家证据号"),
    ("evidence_level", "证据等级"),
    ("customer_table_missing_fields", "客户表缺项"),
    ("algorithm_evidence_missing_fields", "算法 / 证据门缺项"),
    ("model_estimate_disclosure", "大模型工程估算披露"),
    ("delivery_state", "交付状态"),
)


def _code_label(value: Any) -> str:
    text = str(value or "")
    return _CODE_LABELS.get(text, text.replace("_", " "))


def code_label(value: Any) -> str:
    """Return a compact human label while preserving canonical codes in JSON."""
    return _code_label(value)


def _overview_gate_display(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    parts = [f"状态：{_code_label(value.get('state') or 'UNKNOWN')}"]
    required = value.get("required")
    covered = value.get("covered")
    emitted = value.get("emitted")
    resolved = value.get("resolved_fields")
    if isinstance(required, int) and isinstance(covered, int):
        parts.append(f"已覆盖 {covered}/{required}")
    elif isinstance(required, int) and isinstance(emitted, int):
        parts.append(f"已输出 {emitted}/{required}")
    if isinstance(resolved, list) and resolved:
        parts.append("已解析：" + "、".join(map(str, resolved)))
    for key, label in (
        ("blocking_fields", "待补字段"),
        ("blocking_reasons", "阻断原因"),
        ("explicit_open_gate_fields", "显式开放门"),
    ):
        entries = value.get(key)
        if isinstance(entries, list) and entries:
            parts.append(f"{label}：" + "、".join(map(str, entries)))
    if value.get("model_status"):
        parts.append(f"型号状态：{_code_label(value.get('model_status'))}")
    return "；".join(parts)


def customer_overview_display_rows(overview: Any) -> list[dict[str, Any]]:
    """Return the shared, backwards-compatible authoritative overview rows."""
    source = overview if isinstance(overview, dict) else {}
    gate_fields = {
        "authority_structural_completeness",
        "authority_information_coverage",
        "customer_information_coverage",
        "selection_specificity_gate",
        "formal_readiness_gate",
    }
    code_fields = {"model_or_specification_status", "delivery_state"}
    rows: list[dict[str, Any]] = []
    for field_id, label in CUSTOMER_OVERVIEW_DISPLAY_FIELDS:
        value = source.get(field_id)
        if field_id in gate_fields:
            display_value = _overview_gate_display(value)
        elif field_id in code_fields:
            display_value = _code_label(value)
        else:
            display_value = value
        rows.append({
            "field_id": field_id,
            "label": label,
            "value": display_value,
        })
    return rows


def _pretty_unit(value: Any) -> str:
    text = str(value or "—")
    return (
        text.replace("m3", "m³")
        .replace("m2", "m²")
        .replace("degC", "°C")
        .replace("kg/m³", "kg·m⁻³")
        .replace("W/m²/K", "W·m⁻²·K⁻¹")
    )


def _pretty_number_html(row: dict[str, Any]) -> str:
    raw = row.get("raw_value")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return _cell(row.get("display_value"))
    value = float(raw)
    if value == 0:
        return "0"
    rendered = format(value, ".5g")
    if "e" not in rendered.casefold():
        return html.escape(rendered)
    mantissa, exponent = re.split("[eE]", rendered, maxsplit=1)
    return f"{html.escape(mantissa)} × 10<sup>{int(exponent)}</sup>"


def _symbol_html(value: Any) -> str:
    symbol = str(value or "")
    known = {
        "Ph": "P<sub>h</sub>",
        "Ps": "P<sub>s</sub>",
        "Pd": "P<sub>d</sub>",
        "Pin": "P<sub>in</sub>",
        "Pout": "P<sub>out</sub>",
        "NPSHa": "NPSH<sub>a</sub>",
        "NPSHr": "NPSH<sub>r</sub>",
        "rho": "ρ",
        "eta": "η",
    }
    return known.get(symbol, html.escape(symbol))


def _math_html(value: Any) -> str:
    text = html.escape(str(value or ""))
    for token, replacement in (
        ("NPSHa", "NPSH<sub>a</sub>"),
        ("NPSHr", "NPSH<sub>r</sub>"),
        ("Pout", "P<sub>out</sub>"),
        ("Pin", "P<sub>in</sub>"),
        ("rho", "ρ"),
        ("eta", "η"),
    ):
        text = text.replace(token, replacement)
    text = re.sub(r"\^(-?\d+(?:\.\d+)?)", r"<sup>\1</sup>", text)
    return text.replace("*", " · ")


def _equation_html(item: dict[str, Any], symbols: dict[str, str]) -> str:
    chain = item.get("formula_chain")
    if not isinstance(chain, dict):
        return "—"
    target_field = str(item.get("target_field") or chain.get("target") or "")
    target_symbol = symbols.get(target_field) or target_field
    parts = (
        f"<span class='eq-target'>{_symbol_html(target_symbol)}</span>",
        f"<span>{_math_html(chain.get('formula'))}</span>",
        f"<span>{_math_html(chain.get('substitution'))}</span>",
        f"<span class='eq-answer'>{_math_html(chain.get('answer'))}</span>",
    )
    return "<span class='eq-sep'> = </span>".join(parts)


def _formula_trace_html(item: dict[str, Any]) -> str:
    trace = item.get("formula_trace")
    if not isinstance(trace, dict):
        return "<span class='state missing'>未生成机器公式追溯记录</span>"
    definition = trace.get("formula_definition")
    definition = definition if isinstance(definition, dict) else {}
    implementation = definition.get("implementation_binding")
    implementation = implementation if isinstance(implementation, dict) else {}
    input_rows = "".join(
        "<tr>"
        f"<td>{_cell(binding.get('field_id'))}</td>"
        f"<td>{_cell(binding.get('value'))}</td>"
        f"<td>{_cell(_pretty_unit(binding.get('unit')))}</td>"
        f"<td>{_cell(_code_label(binding.get('source_kind')))}</td>"
        f"<td>{_cell(_code_label(binding.get('binding_status')))}</td>"
        f"<td class='meta'>{_cell(binding.get('field_value_sha256'))}</td>"
        "</tr>"
        for binding in trace.get("input_bindings", [])
        if isinstance(binding, dict)
    )
    source_rows = "".join(
        "<tr>"
        f"<td>{_cell(binding.get('reference'))}</td>"
        f"<td>{_cell(_code_label(binding.get('binding_status')))}</td>"
        f"<td>{_cell(binding.get('locator_line_1based'))}</td>"
        f"<td class='meta'>{_cell(binding.get('source_file_sha256'))}</td>"
        "</tr>"
        for binding in definition.get("source_bindings", [])
        if isinstance(binding, dict)
    )
    gaps = trace.get("open_traceability_gaps", [])
    return (
        "<div class='formula-trace'>"
        f"<p><strong>{_cell(trace.get('formula_id'))}</strong> · "
        f"{_cell(_code_label(trace.get('traceability_status')))}</p>"
        f"<p class='meta'>公式定义 SHA-256={_cell(trace.get('formula_definition_sha256'))}<br>"
        f"本次计算追溯 SHA-256={_cell(trace.get('calculation_trace_sha256'))}</p>"
        f"<p>实现：{_cell(implementation.get('implementation_ref'))} · "
        f"{_cell(_code_label(implementation.get('binding_status')))}<br>"
        f"<span class='meta'>源码 SHA-256={_cell(implementation.get('source_file_sha256'))}<br>"
        f"源码集合 SHA-256={_cell(implementation.get('source_code_set_sha256'))}</span></p>"
        "<h4>输入绑定</h4>"
        "<table><thead><tr><th>字段</th><th>值</th><th>单位</th><th>来源类型</th><th>绑定状态</th><th>值 SHA-256</th></tr></thead>"
        f"<tbody>{input_rows}</tbody></table>"
        "<h4>公式来源绑定</h4>"
        "<table><thead><tr><th>来源</th><th>绑定状态</th><th>定位行</th><th>源文件 SHA-256</th></tr></thead>"
        f"<tbody>{source_rows}</tbody></table>"
        f"<p class='warn'><strong>尚未闭合的追溯缺口：</strong>{_cell(gaps or ['无'])}</p>"
        "</div>"
    )


def build_organized_answer(payload: Any) -> dict[str, Any]:
    """Organize immutable program facts into a fixed Agent answer contract."""

    presentation = (
        payload
        if isinstance(payload, dict)
        and payload.get("schema") == "equipment-design-presentation-v1"
        else build_presentation(payload)
    )
    organized_equipment: list[dict[str, Any]] = []
    for card in presentation.get("equipment", []):
        header = card.get("header", {})
        overview = card.get("customer_overview") or {}
        plan = card.get("engineering_adjustment_plan") or {}
        control = card.get("selection_agent_control") or {}
        configuration = (
            plan.get("configuration", {})
            if isinstance(plan, dict)
            else {}
        )
        warnings: list[str] = []
        if isinstance(plan, dict):
            if plan.get("algorithmic_selection_warning"):
                warnings.append(
                    str(plan["algorithmic_selection_warning"])
                )
            warnings.extend(
                str(item.get("message"))
                for item in plan.get("warnings", [])
                if isinstance(item, dict) and item.get("message")
            )
        warnings = list(dict.fromkeys(warnings))
        calculations = [
            {
                "calculation_id": item.get("calculation_id"),
                "target_field": item.get("target_field"),
                "status": item.get("status"),
                "equation_chain": item.get("equation_chain"),
                "evidence_class": (
                    item.get("calculation_notice", {}).get(
                        "evidence_class"
                    )
                    if isinstance(
                        item.get("calculation_notice"), dict
                    )
                    else None
                ),
                "promotion_cap": (
                    item.get("calculation_notice", {}).get(
                        "promotion_cap"
                    )
                    if isinstance(
                        item.get("calculation_notice"), dict
                    )
                    else None
                ),
                "formula_id": (
                    item.get("formula_trace", {}).get("formula_id")
                    if isinstance(item.get("formula_trace"), dict)
                    else None
                ),
                "traceability_status": (
                    item.get("formula_trace", {}).get("traceability_status")
                    if isinstance(item.get("formula_trace"), dict)
                    else None
                ),
                "formula_definition_sha256": (
                    item.get("formula_trace", {}).get("formula_definition_sha256")
                    if isinstance(item.get("formula_trace"), dict)
                    else None
                ),
                "calculation_trace_sha256": (
                    item.get("formula_trace", {}).get("calculation_trace_sha256")
                    if isinstance(item.get("formula_trace"), dict)
                    else None
                ),
                "formula_trace": item.get("formula_trace"),
            }
            for item in card.get("calculation_chain", [])
            if isinstance(item, dict)
        ]
        issues = card.get("issues", {})
        pending_evidence = sorted({
            str(value)
            for key in (
                "evidence_gaps",
                "formal_promotion_blockers",
                "missing_by_goal",
            )
            for value in (
                issues.get(key, [])
                if isinstance(issues.get(key), list)
                else []
            )
            if value not in (None, "")
        })
        next_actions = [
            {
                "action_code": item.get("action_code"),
                "action": item.get("action"),
            }
            for item in (
                plan.get("required_actions", [])
                if isinstance(plan, dict)
                else []
            )
            if isinstance(item, dict)
        ]
        next_actions.extend(
            {
                "action_code": (
                    f"SUPPLY_{str(item.get('field_id') or 'FIELD').upper()}"
                ),
                "action": item.get("reason")
                or item.get("recommended_action"),
            }
            for item in (
                issues.get("input_recommendations", {}).get(
                    "items", []
                )
                if isinstance(
                    issues.get("input_recommendations"), dict
                )
                else []
            )
            if isinstance(item, dict)
            and item.get("status") == "RECOMMENDATION_OPEN"
        )
        organized_equipment.append({
            "equipment_id": card.get("equipment_id"),
            "conclusion": {
                "family": header.get("family_name")
                or header.get("family_id"),
                "recommended_type": header.get("recommended_type"),
                "model_or_specification": overview.get(
                    "model_or_specification"
                ),
                "model_or_specification_status": overview.get(
                    "model_or_specification_status"
                ),
                "delivery_state": overview.get("delivery_state"),
                "engineering_adjustment_status": (
                    plan.get("status")
                    if isinstance(plan, dict)
                    else None
                ),
            },
            "calculations": calculations,
            "candidates_and_system_plan": {
                "configuration": configuration,
                "top_candidates": [
                    {
                        "rank": item.get("rank"),
                        "candidate_kind": item.get("candidate_kind"),
                        "designation": item.get("designation"),
                        "status": item.get("status"),
                    }
                    for item in card.get("candidates", [])[:5]
                    if isinstance(item, dict)
                ],
            },
            "mandatory_warnings": warnings,
            "pending_evidence": pending_evidence,
            "next_actions": next_actions,
            "agent_control": {
                "status": control.get("status")
                if isinstance(control, dict)
                else None,
                "calculate_before_select": (
                    control.get("calculate_before_select", {})
                    if isinstance(control, dict)
                    else {}
                ),
                "agent_control_sha256": (
                    control.get("agent_control_sha256")
                    if isinstance(control, dict)
                    else None
                ),
            },
            "fact_binding": {
                "source_result_sha256": header.get(
                    "source_result_sha256"
                ),
                "engineering_adjustment_plan_sha256": (
                    plan.get("plan_sha256")
                    if isinstance(plan, dict)
                    else None
                ),
            },
        })
    answer = {
        "schema": "equipment-agent-organized-answer-v1",
        "section_order": [
            "结论",
            "计算",
            "候选与系统修改方案",
            "强制警告",
            "待补证据",
            "下一步",
        ],
        "equipment_count": len(organized_equipment),
        "equipment": organized_equipment,
        "authority": {
            "deterministic_facts_immutable": True,
            "llm_may_organize_language_only": True,
            "llm_may_change_counts_models_or_open_gates": False,
            "program_generated": True,
            "llm_used": False,
        },
        "source_presentation_sha256": _canonical_sha256(
            presentation
        ),
    }
    answer["organized_answer_sha256"] = _canonical_sha256(answer)
    return answer


def render_organized_markdown(answer: dict[str, Any]) -> str:
    """Render the fixed organized-answer contract as a readable report."""

    lines = [
        "# 设备设计选型报告",
        "",
        (
            f"程序组织答案 SHA-256："
            f"`{answer.get('organized_answer_sha256', '—')}`"
        ),
        "",
    ]
    for item in answer.get("equipment", []):
        conclusion = item.get("conclusion", {})
        system = item.get("candidates_and_system_plan", {})
        configuration = system.get("configuration", {})
        lines.extend([
            f"## {item.get('equipment_id') or '未命名设备'}",
            "",
            "### 结论",
            "",
            f"- 设备族：{conclusion.get('family') or 'OPEN'}",
            f"- 推荐型式：{conclusion.get('recommended_type') or 'OPEN'}",
            (
                "- 型号/工程规格："
                f"{conclusion.get('model_or_specification') or 'OPEN'}"
            ),
            (
                "- 型号状态："
                f"{conclusion.get('model_or_specification_status') or 'OPEN'}"
            ),
            (
                "- 非标/多台修改状态："
                f"{conclusion.get('engineering_adjustment_status') or '未触发'}"
            ),
            "",
            "### 计算",
            "",
        ])
        calculations = item.get("calculations", [])
        if calculations:
            for calculation in calculations:
                lines.append(
                    "- "
                    + str(
                        calculation.get("equation_chain")
                        or calculation.get("calculation_id")
                        or "未执行计算"
                    )
                    + f"（{calculation.get('status') or 'UNKNOWN'}）"
                )
                trace = calculation.get("formula_trace")
                if isinstance(trace, dict):
                    definition = trace.get("formula_definition")
                    definition = definition if isinstance(definition, dict) else {}
                    implementation = definition.get("implementation_binding")
                    implementation = implementation if isinstance(implementation, dict) else {}
                    lines.extend([
                        f"  - 公式 ID：`{trace.get('formula_id') or 'OPEN'}`",
                        f"  - 追溯状态：`{trace.get('traceability_status') or 'OPEN'}`",
                        f"  - 公式定义 SHA-256：`{trace.get('formula_definition_sha256') or 'OPEN'}`",
                        f"  - 本次计算追溯 SHA-256：`{trace.get('calculation_trace_sha256') or 'OPEN'}`",
                        (
                            "  - 实现绑定："
                            f"`{implementation.get('implementation_ref') or 'OPEN'}` / "
                            f"`{implementation.get('source_file_sha256') or 'OPEN'}`"
                        ),
                        (
                            "  - 输入绑定："
                            + json.dumps(
                                trace.get("input_bindings", []),
                                ensure_ascii=False,
                                sort_keys=True,
                            )
                        ),
                        (
                            "  - 公式来源："
                            + json.dumps(
                                definition.get("source_bindings", []),
                                ensure_ascii=False,
                                sort_keys=True,
                            )
                        ),
                        (
                            "  - 追溯缺口："
                            + json.dumps(
                                trace.get("open_traceability_gaps", []),
                                ensure_ascii=False,
                                sort_keys=True,
                            )
                        ),
                    ])
        else:
            lines.append("- 当前设备没有已执行的内置计算。")
        lines.extend([
            "",
            "### 候选与系统修改方案",
            "",
            (
                "- 系统标记："
                f"{configuration.get('candidate_model_or_designation') or 'OPEN'}"
            ),
            (
                "- 组合方式："
                f"{configuration.get('arrangement_code') or 'OPEN'}"
            ),
            (
                "- 并联列数 / 每列串联台数 / 估算安装总数："
                f"{configuration.get('parallel_train_count_estimate', 'OPEN')} / "
                f"{configuration.get('series_units_per_train_estimate', 'OPEN')} / "
                f"{configuration.get('installed_unit_count_estimate', 'OPEN')}"
            ),
            (
                "- 单台目标："
                + json.dumps(
                    configuration.get("per_unit_target", {}),
                    ensure_ascii=False,
                    sort_keys=True,
                )
            ),
            "",
            "### 强制警告",
            "",
        ])
        warnings = item.get("mandatory_warnings", [])
        lines.extend(
            [f"- {warning}" for warning in warnings]
            if warnings
            else ["- 当前未触发额外算法拆分警告；正式证据门仍然有效。"]
        )
        lines.extend(["", "### 待补证据", ""])
        pending = item.get("pending_evidence", [])
        lines.extend(
            [f"- {entry}" for entry in pending]
            if pending else ["- 当前程序记录中无新增待补项。"]
        )
        lines.extend(["", "### 下一步", ""])
        actions = item.get("next_actions", [])
        lines.extend(
            [
                f"- {action.get('action_code') or 'ACTION'}："
                f"{action.get('action') or '按项目要求复核'}"
                for action in actions
            ]
            if actions
            else ["- 按正式证据门完成同设备复核。"]
        )
        binding = item.get("fact_binding", {})
        lines.extend([
            "",
            (
                "事实绑定："
                f"result={binding.get('source_result_sha256') or '—'}；"
                f"plan={binding.get('engineering_adjustment_plan_sha256') or '—'}"
            ),
            "",
        ])
    lines.extend([
        "---",
        "",
        "本报告由程序按固定章节组织。后续大模型仅可改写表达，不能更改程序计算值、台数、型号/系统标记、警告或 OPEN 证据门。",
        "",
    ])
    return "\n".join(lines)


def render_markdown(presentation: dict[str, Any]) -> str:
    return render_organized_markdown(
        build_organized_answer(presentation)
    )


def render_html(presentation: dict[str, Any]) -> str:
    """Render a self-contained engineering parameter/candidate report."""
    sections: list[str] = []
    for equipment in presentation.get("equipment", []):
        header = equipment.get("header", {})
        axes = equipment.get("status_axes", {})
        terminal = equipment.get("terminal_selection", {})
        adjustment_plan = equipment.get(
            "engineering_adjustment_plan", {}
        )
        agent_control = equipment.get(
            "selection_agent_control", {}
        )
        adjustment_line = ""
        if (
            isinstance(adjustment_plan, dict)
            and adjustment_plan.get("triggered") is True
        ):
            adjustment_line = (
                "<div class='algorithmic-adjustment-warning'>"
                "<strong>非标/多台组合方案（程序算法初筛）</strong><br>"
                f"{_cell(adjustment_plan.get('algorithmic_selection_warning'))}"
                "<pre>"
                f"{_cell(adjustment_plan.get('configuration', {}))}"
                "</pre>"
                "<strong>必须执行的复核：</strong>"
                f"{_cell(adjustment_plan.get('required_actions', []))}"
                "</div>"
            )
        agent_control_line = (
            "<p class='agent-control-line'>"
            "<strong>Agent 控制：</strong>"
            f"{_cell(_code_label(agent_control.get('status')))}"
            " · 先计算后选型="
            f"{_cell(agent_control.get('calculate_before_select', {}).get('calculation_execution_satisfied'))}"
            " · SHA-256="
            f"{_cell(agent_control.get('agent_control_sha256'))}"
            "</p>"
            if isinstance(agent_control, dict) and agent_control
            else ""
        )
        estimate_disclosure = equipment.get("model_estimate_disclosure", {})
        estimate_line = (
            "<div class='model-estimate-warning'>"
            "<strong>大模型工程估算披露（J / provisional / TYPE_SCREENING）</strong><br>"
            f"{_cell(estimate_disclosure.get('statement'))}"
            "</div>"
            if isinstance(estimate_disclosure, dict)
            and estimate_disclosure.get("model_estimate_fields")
            else ""
        )
        terminal_line = (
            "<p class='terminal-line'>"
            f"<strong>终选型式：{_cell(_code_label(terminal.get('status')))}</strong>"
            f" · {_cell(_code_label(terminal.get('selection_basis')))}"
            f" · rule={_cell(terminal.get('rule_id'))}"
            f"<br><span>{_cell(terminal.get('assumption'))}</span>"
            "</p>"
            if isinstance(terminal, dict) and terminal else ""
        )
        axis_html = "".join(
            f"<div class='axis'><span>{_cell(_AXIS_LABELS.get(name, name))}</span><strong>{_cell(_code_label(value))}</strong></div>"
            for name, value in axes.items()
        )
        symbols = {
            str(row.get("field_id")): str(row.get("symbol") or "")
            for group in equipment.get("parameter_groups", [])
            for row in group.get("rows", [])
            if row.get("field_id")
        }
        group_html: list[str] = []
        for group in equipment.get("parameter_groups", []):
            rows = "".join(
                "<tr>"
                f"<td>{_cell(row.get('label'))}</td>"
                f"<td class='symbol'>{_symbol_html(row.get('symbol'))}</td>"
                f"<td class='num'>{_pretty_number_html(row)}</td>"
                f"<td>{_cell(_pretty_unit(row.get('unit')))}</td>"
                f"<td>{_cell(_code_label(row.get('source', {}).get('kind')))}</td>"
                f"<td><span class='state {_cell(row.get('state')).lower()}'>{_cell(_code_label(row.get('state')))}</span></td>"
                f"<td class='equation'>{_equation_html(row, symbols)}</td>"
                "</tr>"
                for row in group.get("rows", [])
            )
            group_html.append(
                f"<h3>{_cell(group.get('title'))}</h3>"
                "<table><thead><tr><th>参数</th><th>符号</th><th>值</th><th>单位</th><th>来源</th><th>状态</th><th>公式链</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>"
            )
        calculation_rows = "".join(
            "<tr>"
            f"<td class='symbol'>{_symbol_html(symbols.get(str(item.get('target_field'))) or item.get('target_field'))}</td>"
            f"<td>{_cell(_code_label(item.get('status')))}</td>"
            f"<td class='equation equation-chain'>{_equation_html(item, symbols)}</td>"
            f"<td>{_cell((item.get('calculation_notice') or {}).get('title'))}<br><small>{_cell((item.get('calculation_notice') or {}).get('applicability'))}</small></td>"
            f"<td>{_cell(item.get('missing_fields'))}</td>"
            "</tr>"
            for item in equipment.get("calculation_chain", [])
        )
        traceability_rows = "".join(
            "<tr>"
            f"<td>{_cell(item.get('calculation_id'))}</td>"
            f"<td>{_formula_trace_html(item)}</td>"
            "</tr>"
            for item in equipment.get("calculation_chain", [])
            if isinstance(item, dict)
        )
        fallback_rows = "".join(
            "<tr>"
            f"<td>{_cell(item.get('field_id'))}</td>"
            f"<td>{_cell(item.get('value'))}</td>"
            f"<td>{_cell(_code_label(item.get('state')))}</td>"
            f"<td>{_cell(_code_label(item.get('tier')))}</td>"
            f"<td>{_cell(item.get('reason'))}</td>"
            f"<td>{_cell(item.get('warning'))}</td>"
            "</tr>"
            for item in equipment.get("issues", {}).get("design_fallbacks", [])
        )
        recommendation_rows = "".join(
            "<tr>"
            f"<td>{_cell(item.get('field_id'))}</td>"
            f"<td>{_cell(item.get('label'))}</td>"
            f"<td>{_cell(_code_label(item.get('priority')))}</td>"
            f"<td>{_cell(_code_label(item.get('recommended_action')))}</td>"
            f"<td>{_cell(item.get('reason'))}</td>"
            "</tr>"
            for item in equipment.get("issues", {}).get("input_recommendations", {}).get("items", [])
            if item.get("status") == "RECOMMENDATION_OPEN"
        )
        candidate_rows = "".join(
            "<tr>"
            f"<td>{_cell(item.get('rank'))}</td>"
            f"<td>{_cell(item.get('candidate_kind'))}</td>"
            f"<td>{_cell(item.get('designation'))}</td>"
            f"<td>{_cell(item.get('status'))}</td>"
            f"<td>{_cell(item.get('ranking_score'))}</td>"
            f"<td>{_cell(item.get('predicate_summary'))}</td>"
            f"<td>{_cell(item.get('missing_gates'))}</td>"
            "</tr>"
            for item in equipment.get("candidates", [])
        )
        customer_overview = equipment.get("customer_overview") or {}
        customer_datasheet = equipment.get("customer_datasheet") or {}
        customer_overview_rows = "".join(
            "<tr>"
            f"<th>{_cell(item.get('label'))}</th><td>{_cell(item.get('value'))}</td>"
            "</tr>"
            for item in customer_overview_display_rows(customer_overview)
        )
        customer_field_rows = "".join(
            "<tr>"
            f"<td>{_cell(item.get('label'))}</td>"
            f"<td>{_cell(item.get('value'))}</td>"
            f"<td>{_cell(_pretty_unit(item.get('unit')))}</td>"
            f"<td>{_cell(_code_label(item.get('state')))}</td>"
            f"<td>{_cell(item.get('evidence_gate'))}</td>"
            f"<td>{_cell(item.get('profile_ids'))}</td>"
            "</tr>"
            for item in customer_datasheet.get("fields", [])
        )
        issues = equipment.get("issues", {})
        sections.append(
            "<section>"
            f"<h1>{_cell(equipment.get('equipment_id'))} · {_cell(header.get('recommended_type') or header.get('family_name'))}</h1>"
            f"<p class='meta'>family={_cell(header.get('family_id'))} · engine={_cell(header.get('engine_version'))} · result SHA-256={_cell(header.get('source_result_sha256'))}</p>"
            f"{estimate_line}"
            f"{adjustment_line}"
            f"{agent_control_line}"
            f"{terminal_line}"
            f"<div class='axes'>{axis_html}</div>"
            "<h2>客户权威一览表输出</h2>"
            "<table class='overview'><tbody>" + customer_overview_rows + "</tbody></table>"
            "<h3>族数据表字段</h3>"
            "<table><thead><tr><th>字段</th><th>值</th><th>单位</th><th>状态</th><th>证据门</th><th>Profile</th></tr></thead>"
            f"<tbody>{customer_field_rows}</tbody></table>"
            "<h2>参数卡</h2>"
            + "".join(group_html)
            + "<h2>保底值与未给条件推荐</h2><p class='warn'><strong>边界：</strong>保底值会让预设计和设备候选继续输出，但全部保持 J/provisional；同工况数据到位后必须自动重算，不能据此宣称正式定型。</p>"
            + "<h3>已应用的保底值</h3><table><thead><tr><th>字段</th><th>值</th><th>状态</th><th>层级</th><th>依据</th><th>警告</th></tr></thead><tbody>" + fallback_rows + "</tbody></table>"
            + "<h3>仍需闭合但不阻断其他结果</h3><table><thead><tr><th>字段</th><th>名称</th><th>优先级</th><th>推荐动作</th><th>原因</th></tr></thead><tbody>" + recommendation_rows + "</tbody></table>"
            + "<h2>算法链</h2><p class='warn'><strong>提示：</strong>带公式的值由本应用生成，不是 Aspen / 用户直接输出；B 类结果仅供暂定初筛。</p><table><thead><tr><th>目标量</th><th>状态</th><th>目标量 = 公式 = 代入式 = 答案</th><th>适用边界</th><th>缺失</th></tr></thead>"
            f"<tbody>{calculation_rows}</tbody></table>"
            + "<h2>公式可追溯性</h2><p class='warn'><strong>判定：</strong>公式、输入值和代码哈希齐全只证明可复算；输入来源或外部标准未绑定时，仍会明确列为开放缺口。</p>"
            + "<table><thead><tr><th>计算 ID</th><th>机器追溯记录</th></tr></thead>"
            f"<tbody>{traceability_rows}</tbody></table>"
            "<h2>候选型号 / 工程规格</h2><table><thead><tr><th>排名</th><th>类别</th><th>候选</th><th>状态</th><th>评分</th><th>谓词</th><th>待闭合</th></tr></thead>"
            f"<tbody>{candidate_rows}</tbody></table>"
            f"<h2>问题与证据门</h2><pre>{_cell(issues)}</pre>"
            f"<p class='gate'><strong>正式门：</strong>{_cell(equipment.get('formal_model_gate'))}</p>"
            f"<p class='warn'><strong>禁止声称：</strong>{_cell(equipment.get('prohibited_claim'))}</p>"
            "</section>"
        )
    body = "".join(sections) or "<p>没有可展示的确定性设备结果。</p>"
    return """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>设备设计参数与选型报告</title>
<style>
:root{--ink:#172630;--muted:#60717d;--line:#d8e0e5;--blue:#0f6275;--paper:#fff;--bg:#eef2f4;--amber:#a76300;--red:#a52a2a;--green:#1f6a43}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 "Microsoft YaHei UI","Noto Sans CJK SC",sans-serif}main{max-width:1500px;margin:28px auto;padding:0 24px}section{background:var(--paper);padding:28px 32px;margin:0 0 24px;border:1px solid var(--line);box-shadow:0 8px 24px rgba(20,40,50,.06)}h1{font-size:24px;margin:0 0 4px}h2{font-size:18px;margin:28px 0 10px;border-bottom:2px solid var(--blue);padding-bottom:6px}h3{font-size:15px;margin:20px 0 7px}.meta{color:var(--muted);font-family:Consolas,monospace;font-size:12px;overflow-wrap:anywhere}.terminal-line{margin:10px 0 4px;padding-left:10px;border-left:3px solid var(--amber)}.terminal-line span{color:var(--muted)}.axes{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:16px 0}.axis{border-top:2px solid var(--blue);padding:8px 2px 5px}.axis span{display:block;color:var(--muted);font-size:11px}.axis strong{display:block;margin-top:3px;font-weight:600}table{width:100%;border-collapse:collapse;table-layout:auto}th,td{border:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}th{background:#edf4f6;white-space:nowrap}.num{text-align:right;font-family:"Segoe UI",Arial,sans-serif;font-variant-numeric:tabular-nums;font-feature-settings:"tnum"}.symbol{text-align:center;white-space:nowrap;font-family:"Cambria Math","Times New Roman",serif;font-style:italic}.equation{font-family:"Cambria Math","Times New Roman",serif;min-width:300px;line-height:1.75}.equation-chain{white-space:nowrap}.eq-target{font-style:italic;font-weight:600}.eq-sep{padding:0 .28em;color:#4f626e}.eq-answer{font-weight:700;color:#123e4a;white-space:nowrap}.state{font-size:11px;font-weight:700}.state.calculated{color:var(--green)}.state.provided{color:var(--blue)}.state.recommended{color:var(--amber)}.state.defaulted{color:var(--red)}.state.missing,.state.external_required{color:var(--amber)}pre{white-space:pre-wrap;background:#f7f8f9;border:1px solid var(--line);padding:12px}.gate{border-left:4px solid var(--blue);padding-left:10px}.warn{border-left:4px solid var(--amber);padding-left:10px}@media print{body{background:#fff}main{max-width:none;margin:0;padding:0}section{box-shadow:none;border:0;page-break-after:always}}
.model-estimate-warning{margin:14px 0;padding:10px 12px;border:1px solid #e1b75b;border-left:5px solid var(--amber);background:#fff8e8;color:#6f4300}
.algorithmic-adjustment-warning{margin:14px 0;padding:12px 14px;border:2px solid #d58b16;border-left:7px solid var(--red);background:#fff2d8;color:#663800}.algorithmic-adjustment-warning pre{background:#fffaf0}.algorithmic-adjustment-warning strong{color:#8b2600}
.agent-control-line{padding:8px 10px;background:#edf7f4;border-left:4px solid var(--green);overflow-wrap:anywhere}
.formula-trace{min-width:760px}.formula-trace h4{margin:12px 0 5px}.formula-trace table{font-size:12px}.formula-trace .meta{word-break:break-all}
</style></head><body><main>""" + body + "</main></body></html>"
