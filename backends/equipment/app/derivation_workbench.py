from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any


FIELD_OPTION_CATALOG: dict[str, tuple[tuple[str, str], ...]] = {
    "phase": (
        ("liquid", "液相"),
        ("gas", "气相"),
        ("vapor", "蒸气"),
        ("two_phase", "气液两相"),
        ("solid", "固相"),
        ("slurry", "浆液"),
    ),
    "pressure_basis": (
        ("absolute", "绝对压力"),
        ("gauge", "表压"),
    ),
    "design_pressure_basis": (
        ("absolute", "绝对压力"),
        ("gauge", "表压"),
    ),
    "orientation": (
        ("horizontal", "卧式"),
        ("vertical", "立式"),
    ),
    "operating_mode": (
        ("continuous", "连续运行"),
        ("batch", "间歇运行"),
    ),
    "head_type": (
        ("ellipsoidal_2_to_1", "2:1 椭圆形封头"),
        ("hemispherical", "半球形封头"),
        ("torispherical", "碟形封头"),
        ("flat", "平盖"),
    ),
}


BLOCK_TYPE_ZH = {
    "PUMP": "泵",
    "COMPR": "压缩机",
    "COMPRESSOR": "压缩机",
    "HEATER": "加热器",
    "COOLER": "冷却器",
    "HEATX": "换热器",
    "MHEATX": "多物流换热器",
    "COLUMN": "塔器",
    "RADFRAC": "严格精馏塔",
    "DSTWU": "简捷精馏塔",
    "FLASH2": "闪蒸分离器",
    "SEP": "分离器",
    "REACTOR": "反应器",
    "RPLUG": "管式反应器",
    "RCSTR": "釜式反应器",
    "VALVE": "阀门",
    "PIPE": "管线",
    "MIXER": "混合器",
    "FSPLIT": "分流器",
}


NODE_TITLES = {
    "source": "① 数据来源与工况",
    "template": "② 设备族与计算模板",
    "calculation": "③ 公式计算与交叉核对",
    "terminal": "④ 型式、材料与部件选择",
    "adjustment": "⑤ 型号候选与非标修改",
    "delivery": "⑥ 客户交付与证据门",
}


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _present(value: Any) -> bool:
    return value not in (None, "", [], {})


def _field_rows(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    package = result.get("design_parameter_package", {})
    rows: list[dict[str, Any]] = []
    if not isinstance(package, Mapping):
        return rows
    for group in package.get("groups", []):
        if not isinstance(group, Mapping):
            continue
        for row in group.get("rows", []):
            if not isinstance(row, Mapping) or not row.get("field_id"):
                continue
            rows.append({
                **dict(row),
                "group_id": group.get("group_id")
                or group.get("id"),
                "group_title": group.get("title")
                or group.get("group_title"),
            })
    return rows


def _effective_defaults(
    result: Mapping[str, Any],
) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for source_key in (
        "normalized_input",
        "effective_normalized_input",
        "derived_parameters",
    ):
        source = result.get(source_key)
        if isinstance(source, Mapping):
            values.update({
                str(key): value
                for key, value in source.items()
                if _present(value)
            })
    for row in _field_rows(result):
        field_id = str(row["field_id"])
        raw_value = row.get("raw_value")
        if _present(raw_value):
            values[field_id] = raw_value
    return values


def _terminal_type_options(
    result: Mapping[str, Any],
    model_rules: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    model = result.get("model_recommendation", {})
    family_id = (
        result.get("match", {}).get("family_id")
        if isinstance(result.get("match"), Mapping)
        else None
    )
    values: list[str] = []
    if isinstance(model, Mapping):
        for value in (
            model.get("recommended_type"),
            model.get("generic_type"),
        ):
            if _present(value):
                values.append(str(value))
    if isinstance(model_rules, Mapping):
        for family in model_rules.get("families", []):
            if not isinstance(family, Mapping):
                continue
            if str(family.get("family_id") or "") != str(
                family_id or ""
            ):
                continue
            for value in (
                family.get("terminal_default_type"),
                family.get("generic_type"),
            ):
                if _present(value):
                    values.append(str(value))
            for rule in family.get("terminal_type_rules", []):
                if (
                    isinstance(rule, Mapping)
                    and _present(rule.get("recommended_type"))
                ):
                    values.append(str(rule["recommended_type"]))
    return [
        {
            "value": value,
            "label": value,
            "internal_code": value,
        }
        for value in dict.fromkeys(values)
    ]


def _template_options(
    catalog: Mapping[str, Any],
) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    for selection in catalog.get("selections", []):
        if not isinstance(selection, Mapping):
            continue
        block_type = str(selection.get("block_type") or "").upper()
        family_name = str(
            selection.get("family_name")
            or selection.get("display_name")
            or "设备"
        )
        block_zh = BLOCK_TYPE_ZH.get(block_type)
        label = (
            f"{family_name}（Aspen {block_zh}模块）"
            if block_zh
            else family_name
        )
        options.append({
            "value": str(selection.get("selection_id") or ""),
            "label": label,
            "internal_code": str(
                selection.get("selection_id") or ""
            ),
            "family_id": selection.get("family_id"),
            "block_type": selection.get("block_type"),
        })
    return sorted(
        options,
        key=lambda item: (
            str(item["label"]),
            str(item["value"]),
        ),
    )


def _current_selection_id(
    result: Mapping[str, Any],
    catalog: Mapping[str, Any],
    supplied_selection_id: str | None,
) -> str | None:
    if supplied_selection_id:
        return supplied_selection_id
    normalized = result.get("normalized_input", {})
    block_type = (
        str(normalized.get("aspen_block_type") or "").upper()
        if isinstance(normalized, Mapping)
        else ""
    )
    family_id = (
        str(result.get("match", {}).get("family_id") or "")
        if isinstance(result.get("match"), Mapping)
        else ""
    )
    selections = [
        item
        for item in catalog.get("selections", [])
        if isinstance(item, Mapping)
    ]
    if block_type:
        exact = next(
            (
                str(item.get("selection_id"))
                for item in selections
                if str(item.get("block_type") or "").upper()
                == block_type
            ),
            None,
        )
        if exact:
            return exact
    return next(
        (
            str(item.get("selection_id"))
            for item in selections
            if str(item.get("family_id") or "") == family_id
        ),
        None,
    )


def _editable_fields(
    result: Mapping[str, Any],
    *,
    overrides: Mapping[str, Any],
    terminal_options: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    defaults = _effective_defaults(result)
    fields: list[dict[str, Any]] = []
    seen: set[str] = set()
    protected_suffixes = (
        "_sha256",
        "_path",
    )
    protected_fields = {
        "input_sha256",
        "selection_context",
        "formal_model",
        "vendor_model",
        "candidate_model",
        "approval_status",
    }
    for row in _field_rows(result):
        field_id = str(row["field_id"])
        if field_id in seen:
            continue
        seen.add(field_id)
        protected = (
            field_id in protected_fields
            or field_id.endswith(protected_suffixes)
        )
        option_source = FIELD_OPTION_CATALOG.get(field_id, ())
        if field_id == "equipment_type":
            options = [dict(item) for item in terminal_options]
        else:
            options = [
                {
                    "value": value,
                    "label": label,
                    "internal_code": value,
                }
                for value, label in option_source
            ]
        default_value = defaults.get(field_id)
        current_value = overrides.get(field_id, default_value)
        fields.append({
            "field_id": field_id,
            "label": row.get("label") or field_id,
            "symbol": row.get("symbol"),
            "unit": row.get("unit"),
            "group_id": row.get("group_id"),
            "group_title": row.get("group_title"),
            "source_kind": (
                row.get("source", {}).get("kind")
                if isinstance(row.get("source"), Mapping)
                else None
            ),
            "state": row.get("state"),
            "default_value": default_value,
            "current_value": current_value,
            "override_active": field_id in overrides,
            "editable": not protected,
            "edit_kind": "select" if options else "text",
            "options": options,
            "warning": (
                "修改后将作为用户场景输入重算，并保留程序默认值；"
                "它不会自动升级为正式证据。"
                if not protected
                else "该字段属于哈希、审批或正式身份门，界面不允许直接修改。"
            ),
        })
    for field_id, value in defaults.items():
        if field_id in seen or field_id in protected_fields:
            continue
        if field_id.endswith(protected_suffixes):
            continue
        options = [
            {
                "value": internal,
                "label": label,
                "internal_code": internal,
            }
            for internal, label in FIELD_OPTION_CATALOG.get(
                field_id, ()
            )
        ]
        fields.append({
            "field_id": field_id,
            "label": field_id.replace("_", " "),
            "symbol": None,
            "unit": None,
            "group_id": "additional",
            "group_title": "补充输入",
            "source_kind": "normalized_input",
            "state": "PROVIDED",
            "default_value": value,
            "current_value": overrides.get(field_id, value),
            "override_active": field_id in overrides,
            "editable": True,
            "edit_kind": "select" if options else "text",
            "options": options,
            "warning": (
                "修改后将作为用户场景输入重算，并保留程序默认值；"
                "它不会自动升级为正式证据。"
            ),
        })
    return sorted(
        fields,
        key=lambda item: (
            str(item.get("group_title") or ""),
            str(item.get("label") or ""),
            str(item["field_id"]),
        ),
    )


def build_workbench(
    result: Mapping[str, Any],
    catalog: Mapping[str, Any],
    *,
    model_rules: Mapping[str, Any] | None = None,
    selection_id: str | None = None,
    overrides: Mapping[str, Any] | None = None,
    active_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if (
        result.get("schema")
        != "equipment-deterministic-match-result-v1"
    ):
        raise ValueError("推导工作台需要单设备确定性匹配结果。")
    overrides = dict(overrides or {})
    working_result = (
        active_result
        if isinstance(active_result, Mapping)
        and active_result.get("schema")
        == "equipment-deterministic-match-result-v1"
        else result
    )
    current_selection_id = _current_selection_id(
        result,
        catalog,
        selection_id,
    )
    template_options = _template_options(catalog)
    terminal_options = _terminal_type_options(
        working_result,
        model_rules,
    )
    fields = _editable_fields(
        result,
        overrides=overrides,
        terminal_options=terminal_options,
    )
    package = working_result.get(
        "design_parameter_package", {}
    )
    model = working_result.get("model_recommendation", {})
    plan = working_result.get(
        "engineering_adjustment_plan", {}
    )
    control = working_result.get(
        "selection_agent_control", {}
    )
    delivery = working_result.get("customer_delivery", {})
    overview_rows = (
        delivery.get("equipment_overview_table", {}).get(
            "rows", []
        )
        if isinstance(delivery, Mapping)
        else []
    )
    current_template = next(
        (
            item
            for item in template_options
            if item["value"] == current_selection_id
        ),
        None,
    )
    nodes = [
        {
            "node_id": "source",
            "title": NODE_TITLES["source"],
            "status": working_result.get("status"),
            "summary": (
                f"已读取 {len(fields)} 个可显示参数；"
                f"{sum(1 for item in fields if item['override_active'])} 项人工覆盖"
            ),
            "editable_fields": fields,
        },
        {
            "node_id": "template",
            "title": NODE_TITLES["template"],
            "status": (
                working_result.get("match", {}).get("family_id")
                if isinstance(
                    working_result.get("match"), Mapping
                )
                else "OPEN"
            ),
            "summary": (
                current_template.get("label")
                if isinstance(current_template, Mapping)
                else "模板待确认"
            ),
            "editable_fields": [{
                "field_id": "__selection_id__",
                "label": "计算模板",
                "default_value": current_selection_id,
                "current_value": overrides.get(
                    "__selection_id__",
                    current_selection_id,
                ),
                "override_active": "__selection_id__" in overrides,
                "editable": True,
                "edit_kind": "select",
                "options": template_options,
                "warning": (
                    "更换模板会按新设备族重新执行完整计算和选型；"
                    "原结果仅作为默认场景保留。"
                ),
            }],
        },
        {
            "node_id": "calculation",
            "title": NODE_TITLES["calculation"],
            "status": (
                package.get("status_axes", {}).get("calculation")
                if isinstance(package, Mapping)
                else "UNKNOWN"
            ),
            "summary": (
                f"{len(working_result.get('calculations', []))} 项已执行，"
                f"{len(working_result.get('calculation_pending', []))} 项等待/阻断"
            ),
            "editable_fields": [
                item for item in fields
                if item.get("group_id")
                in {
                    "process",
                    "operating",
                    "thermal",
                    "hydraulic",
                    "calculated_design",
                    "advanced_design",
                }
                or item.get("state") in {"CALCULATED", "PROVIDED"}
            ],
            "details": {
                "calculations": working_result.get(
                    "calculations", []
                ),
                "pending": working_result.get(
                    "calculation_pending", []
                ),
            },
        },
        {
            "node_id": "terminal",
            "title": NODE_TITLES["terminal"],
            "status": (
                model.get("terminal_selection", {}).get("status")
                if isinstance(model, Mapping)
                and isinstance(
                    model.get("terminal_selection"), Mapping
                )
                else "UNKNOWN"
            ),
            "summary": (
                model.get("recommended_type")
                if isinstance(model, Mapping)
                else "OPEN"
            ),
            "editable_fields": [
                item for item in fields
                if item["field_id"] in {
                    "equipment_type",
                    "material",
                    "seal_type",
                    "head_type",
                    "orientation",
                    "operating_mode",
                    "standby_configuration",
                    "flange_face",
                    "gasket_material",
                    "pressure_class",
                }
            ],
            "details": {
                "terminal_selection": (
                    model.get("terminal_selection", {})
                    if isinstance(model, Mapping)
                    else {}
                ),
                "agent_choice_resolution": (
                    control.get(
                        "ambiguous_choice_resolution", {}
                    )
                    if isinstance(control, Mapping)
                    else {}
                ),
            },
        },
        {
            "node_id": "adjustment",
            "title": NODE_TITLES["adjustment"],
            "status": (
                plan.get("status")
                if isinstance(plan, Mapping)
                else "NOT_AVAILABLE"
            ),
            "summary": (
                plan.get("configuration", {}).get(
                    "candidate_model_or_designation"
                )
                if isinstance(plan, Mapping)
                and isinstance(
                    plan.get("configuration"), Mapping
                )
                else "候选与修改方案待计算"
            ),
            "editable_fields": [],
            "details": {
                "candidates": (
                    model.get("candidates", [])
                    if isinstance(model, Mapping)
                    else []
                ),
                "engineering_adjustment_plan": plan,
            },
        },
        {
            "node_id": "delivery",
            "title": NODE_TITLES["delivery"],
            "status": (
                overview_rows[0].get("delivery_state")
                if overview_rows
                and isinstance(overview_rows[0], Mapping)
                else "NOT_READY"
            ),
            "summary": (
                overview_rows[0].get(
                    "model_or_specification"
                )
                if overview_rows
                and isinstance(overview_rows[0], Mapping)
                else "客户交付待生成"
            ),
            "editable_fields": [],
            "details": {
                "customer_overview": (
                    overview_rows[0] if overview_rows else {}
                ),
                "agent_control": control,
            },
        },
    ]
    workbench = {
        "schema": "equipment-derivation-workbench-v1",
        "equipment_id": (
            result.get("normalized_input", {}).get("equipment_tag")
            if isinstance(
                result.get("normalized_input"), Mapping
            )
            else None
        ),
        "source_result_sha256": canonical_sha256(result),
        "active_result_sha256": canonical_sha256(working_result),
        "default_selection_id": current_selection_id,
        "current_selection_id": overrides.get(
            "__selection_id__",
            current_selection_id,
        ),
        "overrides": overrides,
        "override_count": len(overrides),
        "nodes": nodes,
        "controls": {
            "single_equipment_recalculate": True,
            "restore_program_defaults": True,
            "formal_evidence_gate_overridable": False,
            "program_default_values_preserved": True,
        },
        "deterministic_baseline": True,
        "user_scenario_active": bool(overrides),
        "llm_used": False,
    }
    workbench["workbench_sha256"] = canonical_sha256(workbench)
    return workbench


def build_override_audit(
    baseline_result: Mapping[str, Any],
    overrides: Mapping[str, Any],
    recalculated_result: Mapping[str, Any],
) -> dict[str, Any]:
    defaults = _effective_defaults(baseline_result)
    changes = [
        {
            "field_id": field_id,
            "program_default_value": defaults.get(field_id),
            "user_override_value": value,
            "changed": defaults.get(field_id) != value,
        }
        for field_id, value in sorted(overrides.items())
        if field_id != "__selection_id__"
    ]
    audit = {
        "schema": "equipment-user-derivation-override-audit-v1",
        "status": (
            "USER_SCENARIO_RECALCULATED"
            if overrides
            else "PROGRAM_DEFAULTS_RESTORED"
        ),
        "baseline_result_sha256": canonical_sha256(
            baseline_result
        ),
        "recalculated_result_sha256": canonical_sha256(
            recalculated_result
        ),
        "selection_template_override": overrides.get(
            "__selection_id__"
        ),
        "changes": changes,
        "user_override_count": len(changes),
        "input_provenance": (
            "USER_EDITED_SCENARIO_NOT_FORMAL_EVIDENCE"
        ),
        "formal_model_promotion_allowed_by_override_alone": False,
        "source_baseline_modified": False,
        "llm_used": False,
    }
    audit["override_audit_sha256"] = canonical_sha256(audit)
    return audit


__all__ = [
    "BLOCK_TYPE_ZH",
    "FIELD_OPTION_CATALOG",
    "NODE_TITLES",
    "build_override_audit",
    "build_workbench",
    "canonical_sha256",
]
