from __future__ import annotations

import csv
import math
import os
import re
from pathlib import Path
from typing import Any
from cost_evidence_guard import EXCLUDED_SCOPES, KNOWN_SCOPES


DEFAULT_COMPARISON_INDEX = 816.0


def io_path(path: Path) -> Path:
    resolved = path.resolve()
    if os.name != "nt":
        return resolved
    value = str(resolved)
    if value.startswith("\\\\?\\"):
        return resolved
    if value.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + value[2:])
    return Path("\\\\?\\" + value)


def read_csv(path: Path) -> list[dict[str, str]]:
    with io_path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def positive(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def load_contract(reference_dir: Path) -> dict[str, Any]:
    policy_rows = read_csv(reference_dir / "comparison-cost-fallback-policy.csv")
    method_rows = read_csv(reference_dir / "replacement-cost-library.csv")
    service_path = reference_dir / "comparison-service-replacement-library.csv"
    service_rows = read_csv(service_path) if service_path.exists() else []
    return {
        "policy": {row["rule_id"]: row for row in policy_rows},
        "methods": {row["method_id"]: row for row in method_rows},
        "services": {normalized(row["service"]): row for row in service_rows},
    }


def _factor(policy: dict[str, dict[str, str]], rule_id: str, field: str) -> float:
    try:
        return float(policy[rule_id][field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"comparison policy missing {rule_id}.{field}") from exc


def _proxy(
    params: dict[str, Any],
    reference: dict[str, str],
) -> tuple[str, float | None, float | None, float | None]:
    explicit_ratio = positive(params.get("comparison_scale_ratio"))
    explicit_value = positive(params.get("comparison_proxy_value"))
    explicit_reference = positive(params.get("comparison_reference_proxy_value"))
    explicit_name = str(params.get("comparison_proxy_name", "")).strip()
    if explicit_ratio is not None:
        return explicit_name or "explicit_scale_ratio", explicit_value, explicit_reference, explicit_ratio

    reference_value = explicit_reference or positive(reference.get("reference_proxy_value"))
    priorities = [item.strip() for item in reference.get("proxy_priority", "").split(";") if item.strip()]
    for name in priorities:
        aliases = [name]
        if name == "duty_gcal_h_normalized":
            aliases.extend(["duty_gcal_h", "absolute_duty_gcal_h"])
        elif name == "work_kW":
            aliases.extend(["work_kw", "shaft_power_kw", "driver_power_kw"])
        for alias in aliases:
            value = positive(params.get(alias))
            if value is not None:
                local_reference = positive(params.get(f"{alias}_reference")) or reference_value
                ratio = value / local_reference if local_reference else None
                return alias, value, local_reference, ratio
    return explicit_name, explicit_value, reference_value, None


def _scaled_cost(
    reference_cost: float,
    exponent: float,
    ratio: float | None,
    quantity: int,
) -> tuple[float, float | None, int]:
    if ratio is None:
        return quantity * reference_cost, None, quantity
    if ratio < 0.25:
        effective_ratio = 0.25
        parallel_trains = 1
    elif ratio <= 4.0:
        effective_ratio = ratio
        parallel_trains = 1
    else:
        parallel_trains = math.ceil(ratio / 4.0)
        effective_ratio = ratio / parallel_trains
    return quantity * parallel_trains * reference_cost * effective_ratio**exponent, effective_ratio, quantity * parallel_trains


def complete_comparison_cost(
    strict_row: dict[str, Any],
    assignment: dict[str, str],
    params: dict[str, Any],
    case: dict[str, str],
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Apply the ordered comparison-only IF rules to one equipment row."""

    policy: dict[str, dict[str, str]] = contract["policy"]
    method_library: dict[str, dict[str, str]] = contract["methods"]
    service_library: dict[str, dict[str, str]] = contract["services"]
    method_id = assignment.get("method_id", "")
    scope = assignment.get("scope_class", "")
    if scope not in KNOWN_SCOPES:
        raise ValueError(f"scope unknown or unresolved: {scope!r}")
    service = assignment.get("service", "")
    raw_cost = positive(strict_row.get("candidate_purchased_cost_target_usd"))
    target_index = positive(case.get("target_cost_index")) or DEFAULT_COMPARISON_INDEX
    target_index_source = "case_manifest" if positive(case.get("target_cost_index")) else "comparison_default_816"

    base: dict[str, Any] = {
        "raw_engineering_cost_usd": raw_cost if raw_cost is not None else "",
        "comparison_cost_usd": "",
        "comparison_cost_low_usd": "",
        "comparison_cost_high_usd": "",
        "comparison_generation_tier": "",
        "comparison_rule_id": "",
        "comparison_replacement_method_id": "",
        "comparison_source_id": "",
        "comparison_source_locator": "",
        "comparison_reference_cost_usd": "",
        "comparison_target_cost_index": target_index,
        "comparison_target_index_source": target_index_source,
        "comparison_proxy_name": "",
        "comparison_proxy_value": "",
        "comparison_reference_proxy_value": "",
        "comparison_effective_ratio": "",
        "comparison_train_count": 1,
        "structural_zero": "no",
        "comparison_replacement_reason": "",
        "comparison_requires_review": "yes",
        "comparison_counting_role": "physical_item",
    }

    def finish(
        cost: float,
        rule_id: str,
        tier: str,
        source_id: str,
        source_locator: str,
        reason: str,
        *,
        replacement_method_id: str = "",
        reference_cost: float | str = "",
        proxy_name: str = "",
        proxy_value: float | str = "",
        reference_proxy_value: float | str = "",
        effective_ratio: float | str = "",
        train_count: int = 1,
        structural_zero: bool = False,
        requires_review: bool = True,
        counting_role: str = "physical_item",
    ) -> dict[str, Any]:
        if not math.isfinite(cost) or cost < 0:
            raise ValueError(f"comparison rule {rule_id} produced invalid cost: {cost}")
        low = cost * _factor(policy, rule_id, "low_factor")
        high = cost * _factor(policy, rule_id, "high_factor")
        base.update({
            "comparison_cost_usd": cost,
            "comparison_cost_low_usd": low,
            "comparison_cost_high_usd": high,
            "comparison_generation_tier": tier,
            "comparison_rule_id": rule_id,
            "comparison_replacement_method_id": replacement_method_id,
            "comparison_source_id": source_id,
            "comparison_source_locator": source_locator,
            "comparison_reference_cost_usd": reference_cost,
            "comparison_proxy_name": proxy_name,
            "comparison_proxy_value": proxy_value,
            "comparison_reference_proxy_value": reference_proxy_value,
            "comparison_effective_ratio": effective_ratio,
            "comparison_train_count": train_count,
            "structural_zero": "yes" if structural_zero else "no",
            "comparison_replacement_reason": reason,
            "comparison_requires_review": "yes" if requires_review else "no",
            "comparison_counting_role": counting_role,
        })
        return base

    # IF 1: scope exclusions and OPEX-only rows make a documented zero
    # contribution to purchased equipment, not an observed zero-price device.
    if (
        scope in EXCLUDED_SCOPES
        or method_id == "LOGICAL_OR_REACTOR_EXCLUSION"
        or method_id == "UTILITY_OPEX"
    ):
        role = "utility_opex_separate" if method_id == "UTILITY_OPEX" else "scope_exclusion"
        return finish(
            0.0,
            "IF_STRUCTURAL_ZERO",
            "S",
            "PROJECT_PHYSICAL_SCOPE_RULE",
            assignment.get("decision_gate", "equipment-method-assignment.csv"),
            "Outside ordinary purchased-equipment scope; retained as an explicit structural contribution.",
            structural_zero=True,
            requires_review=False,
            counting_role=role,
        )

    # IF 2: a non-positive pressure rise is letdown service, not a pump.
    inlet_pressure = positive(params.get("inlet_pressure_bar"))
    outlet_pressure = positive(params.get("outlet_pressure_bar"))
    if method_id == "PUMP_Q_H_NETL" and inlet_pressure is not None and outlet_pressure is not None and outlet_pressure <= inlet_pressure:
        return finish(
            0.0,
            "IF_PUMP_IS_LETDOWN",
            "S",
            "PROJECT_BULK_VALVE_SCOPE_RULE",
            "pump topology: outlet_pressure_bar <= inlet_pressure_bar",
            "Economically remapped to the current bulk letdown/control-valve boundary.",
            replacement_method_id="BULK_LETDOWN_BOUNDARY",
            structural_zero=True,
            requires_review=False,
            counting_role="economic_mapping_replacement",
        )

    # IF 3-4: preserve any source-backed numeric candidate before using a proxy.
    if raw_cost is not None and truthy(strict_row.get("selected_after_review")):
        return finish(
            raw_cost,
            "IF_REVIEWED_NUMERIC",
            "A",
            strict_row.get("source_ids", "") or "STRICT_METHOD_SOURCE",
            strict_row.get("method_id", ""),
            "Reviewed strict candidate reused without replacement.",
            replacement_method_id=method_id,
            requires_review=False,
        )
    if raw_cost is not None:
        return finish(
            raw_cost,
            "IF_NUMERIC_CANDIDATE",
            "B",
            strict_row.get("source_ids", "") or "STRICT_METHOD_SOURCE",
            strict_row.get("method_id", ""),
            "Unreviewed numeric strict candidate retained for comparison with an explicit uncertainty band.",
            replacement_method_id=method_id,
        )

    # IF 5-8: choose a service anchor, method anchor, or universal anchor.
    reference = service_library.get(normalized(service))
    reference_kind = "service" if reference else "method"
    if reference is None:
        reference = method_library.get(method_id)
    if reference is None:
        reference = method_library.get("*")
        reference_kind = "universal"
    if reference is None:
        raise ValueError(f"no comparison replacement exists for physical method {method_id!r}")

    reference_cost_raw = positive(reference.get("reference_cost_usd_at_index"))
    reference_index = positive(reference.get("reference_cost_index"))
    exponent = positive(reference.get("scaling_exponent"))
    if reference_cost_raw is None or reference_index is None or exponent is None:
        raise ValueError(f"invalid comparison replacement row for {method_id!r}")
    adjusted_reference = reference_cost_raw * target_index / reference_index
    proxy_name, proxy_value, reference_proxy_value, ratio = _proxy(params, reference)
    quantity_value = positive(params.get("quantity")) or 1.0
    quantity = max(1, int(math.ceil(quantity_value)))
    cost, effective_ratio, train_count = _scaled_cost(adjusted_reference, exponent, ratio, quantity)

    if ratio is not None:
        rule_id = "IF_CYCLONE_PROXY_AVAILABLE" if method_id == "CYCLONE_SOLIDS_PACKAGE" else "IF_METHOD_PROXY_AVAILABLE"
        tier = "D" if method_id == "CYCLONE_SOLIDS_PACKAGE" else "C"
        reason = f"{reference_kind}-matched reference scaled by explicit positive proxy ratio and exponent."
    elif method_id == "CYCLONE_SOLIDS_PACKAGE":
        rule_id = "IF_CYCLONE_NO_PROXY"
        tier = "D"
        reason = f"{reference_kind}-matched cyclone/solids reference used without size scaling because no reference proxy was available."
    elif reference_kind == "universal":
        rule_id = "IF_UNKNOWN_PHYSICAL"
        tier = "E"
        reason = "No service or method anchor was qualified; universal physical-equipment comparison anchor used."
    else:
        rule_id = "IF_METHOD_NO_PROXY"
        tier = "E"
        reason = f"{reference_kind}-matched reference used without size scaling because no reference proxy was available."

    return finish(
        cost,
        rule_id,
        tier,
        reference.get("source_id", ""),
        reference.get("source_locator", ""),
        reason,
        replacement_method_id=reference.get("method_id", method_id),
        reference_cost=adjusted_reference,
        proxy_name=proxy_name,
        proxy_value=proxy_value if proxy_value is not None else "",
        reference_proxy_value=reference_proxy_value if reference_proxy_value is not None else "",
        effective_ratio=effective_ratio if effective_ratio is not None else "",
        train_count=train_count,
    )


COMPARISON_FIELDS = [
    "raw_engineering_cost_usd",
    "comparison_cost_usd",
    "comparison_cost_low_usd",
    "comparison_cost_high_usd",
    "comparison_generation_tier",
    "comparison_rule_id",
    "comparison_replacement_method_id",
    "comparison_source_id",
    "comparison_source_locator",
    "comparison_reference_cost_usd",
    "comparison_target_cost_index",
    "comparison_target_index_source",
    "comparison_proxy_name",
    "comparison_proxy_value",
    "comparison_reference_proxy_value",
    "comparison_effective_ratio",
    "comparison_train_count",
    "structural_zero",
    "comparison_replacement_reason",
    "comparison_requires_review",
    "comparison_counting_role",
]
