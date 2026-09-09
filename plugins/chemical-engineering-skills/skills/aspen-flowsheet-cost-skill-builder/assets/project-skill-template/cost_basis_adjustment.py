from __future__ import annotations


def adjust_purchased_equipment_cost(
    base_cost_usd,
    *,
    base_cost_index,
    target_cost_index,
    index_name,
    base_period,
    target_period,
    index_source,
    material_factor=1.0,
    pressure_factor=1.0,
    design_factor=1.0,
    quantity=1,
    usd_to_target_currency=1.0,
    target_currency="USD",
):
    """Apply explicit, auditable adjustments to purchased equipment cost.

    This function deliberately does not calculate installed cost or total plant
    capital. Every multiplier remains visible in the returned record so a batch
    result can be traced back to its cost basis.
    """
    numeric = {
        "base_cost_usd": base_cost_usd,
        "base_cost_index": base_cost_index,
        "target_cost_index": target_cost_index,
        "material_factor": material_factor,
        "pressure_factor": pressure_factor,
        "design_factor": design_factor,
        "usd_to_target_currency": usd_to_target_currency,
    }
    for name, value in numeric.items():
        if float(value) <= 0:
            raise ValueError(f"{name} must be positive")
    if int(quantity) != quantity or quantity < 1:
        raise ValueError("quantity must be a positive integer")
    required_text = {
        "index_name": index_name,
        "base_period": base_period,
        "target_period": target_period,
        "index_source": index_source,
        "target_currency": target_currency,
    }
    missing = [name for name, value in required_text.items() if not str(value).strip()]
    if missing:
        raise ValueError(f"Adjustment provenance is incomplete: {missing}")

    index_ratio = float(target_cost_index) / float(base_cost_index)
    adjusted_single_usd = (
        float(base_cost_usd)
        * index_ratio
        * float(material_factor)
        * float(pressure_factor)
        * float(design_factor)
    )
    adjusted_total_usd = adjusted_single_usd * int(quantity)
    target_value = adjusted_total_usd * float(usd_to_target_currency)
    return {
        "base_purchased_equipment_cost_usd": float(base_cost_usd),
        "base_period": str(base_period),
        "target_period": str(target_period),
        "index_name": str(index_name),
        "base_cost_index": float(base_cost_index),
        "target_cost_index": float(target_cost_index),
        "index_ratio": index_ratio,
        "index_source": str(index_source),
        "material_factor": float(material_factor),
        "pressure_factor": float(pressure_factor),
        "design_factor": float(design_factor),
        "quantity": int(quantity),
        "adjusted_single_purchased_equipment_cost_usd": adjusted_single_usd,
        "adjusted_total_purchased_equipment_cost_usd": adjusted_total_usd,
        "usd_to_target_currency": float(usd_to_target_currency),
        "target_currency": str(target_currency),
        "adjusted_total_purchased_equipment_cost_target_currency": target_value,
        "cost_scope": "purchased_equipment_only",
        "status": "adjusted_with_explicit_factors",
    }
