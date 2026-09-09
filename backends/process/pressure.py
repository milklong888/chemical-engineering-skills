"""Explicit-basis hydraulic identities; no property or design-limit defaults.

SI inputs, absolute pressures, finite values. These calculations screen a
declared model; they do not substitute for exchanger/column/vendor rating.
"""
from __future__ import annotations

import math


def number(value, name, *, positive=False, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError(f"{name}: a finite number is required")
    if positive and value <= 0 or nonnegative and value < 0:
        raise ValueError(f"{name}: outside the required numeric domain")
    return float(value)


def liquid_pipe_loss(*, density_kg_m3, viscosity_pa_s, flow_m3_s,
                     diameter_m, length_m, minor_k, elevation_change_m,
                     friction_factor=None, friction_basis=None):
    """Darcy-Weisbach, round constant-D pipe, incompressible Newtonian liquid.

    Laminar Darcy f=64/Re only below Re 2000. Transitional/turbulent flow needs
    the caller's sourced Darcy factor; no hidden roughness/correlation. Static
    elevation is separate from irreversible loss. Zero flow has zero friction.
    """
    rho = number(density_kg_m3, "density_kg_m3", positive=True)
    mu = number(viscosity_pa_s, "viscosity_pa_s", positive=True)
    q = number(flow_m3_s, "flow_m3_s", nonnegative=True)
    d = number(diameter_m, "diameter_m", positive=True)
    length = number(length_m, "length_m", nonnegative=True)
    k = number(minor_k, "minor_k", nonnegative=True)
    dz = number(elevation_change_m, "elevation_change_m")
    u = q / (math.pi * d * d / 4)
    re = rho * u * d / mu
    if re == 0:
        f, basis = 0.0, "zero_flow_limit"
    elif friction_factor is None and re < 2000:
        f, basis = 64 / re, "Darcy_laminar_64_over_Re"
    elif friction_factor is not None and friction_basis:
        f = number(friction_factor, "Darcy_friction_factor", positive=True)
        basis = friction_basis
    else:
        raise ValueError("At Re >= 2000 supply a sourced Darcy (not Fanning) factor")
    dynamic = rho * u * u / 2
    friction = f * length / d * dynamic
    minor = k * dynamic
    static = rho * 9.80665 * dz
    return {"status": "DECLARED_MODEL_CALCULATED", "velocity_m_s": u,
            "reynolds": re, "darcy_f": f, "friction_basis": basis,
            "friction_pa": friction, "minor_loss_pa": minor,
            "irreversible_loss_pa": friction + minor, "static_pressure_pa": static,
            "inlet_minus_outlet_pressure_pa": friction + minor + static,
            "equation": "deltaP=(f_D*L/D+sum(K))*rho*u^2/2+rho*g*delta_z",
            "boundary": "constant-density liquid; equal inlet/outlet area; no two-phase/gas acceleration model"}


def series_pressure(inlet_pressure_pa, losses_pa):
    pressure = number(inlet_pressure_pa, "inlet_pressure_pa", positive=True)
    initial = pressure
    stages = []
    for index, loss in enumerate(losses_pa):
        loss = number(loss, f"losses_pa[{index}]", nonnegative=True)
        outlet = pressure - loss
        if outlet <= 0:
            raise ValueError("Series loss consumes the entire absolute pressure")
        stages.append({"index": index, "inlet_pressure_pa": pressure,
                       "outlet_pressure_pa": outlet, "loss_pa": loss})
        pressure = outlet
    return {"inlet_pressure_pa": initial, "outlet_pressure_pa": pressure,
            "total_loss_pa": initial - pressure, "stages": stages}


def compressor_train(*, inlet_pressure_pa, stages, mass_flow_kg_s,
                     cp_j_kg_k, heat_capacity_ratio, property_basis):
    """Ideal-gas constant-cp screening, explicit suction T/eta/ratio each stage.

    Cooler/separator/piping losses belong to each stage's after_loss_pa. Its
    successor suction T is an explicit cooler condition, not a free optimum.
    Valid only under the caller's declared ideal-gas/constant-cp approximation.
    """
    if not property_basis or not stages:
        raise ValueError("Explicit property approximation basis and stages required")
    pressure = number(inlet_pressure_pa, "inlet_pressure_pa", positive=True)
    mass = number(mass_flow_kg_s, "mass_flow_kg_s", positive=True)
    cp = number(cp_j_kg_k, "cp_j_kg_k", positive=True)
    gamma = number(heat_capacity_ratio, "heat_capacity_ratio", positive=True)
    if gamma <= 1:
        raise ValueError("heat_capacity_ratio must exceed one")
    result, total = [], 0.0
    for index, stage in enumerate(stages):
        temp = number(stage["suction_temperature_k"], "suction_temperature_k", positive=True)
        eta = number(stage["isentropic_efficiency"], "isentropic_efficiency", positive=True)
        ratio = number(stage["pressure_ratio"], "pressure_ratio", positive=True)
        loss = number(stage["after_loss_pa"], "after_loss_pa", nonnegative=True)
        if eta > 1 or ratio <= 1:
            raise ValueError("Require 0 < isentropic efficiency <= 1 and ratio > 1")
        if stage.get("phase") != "vapor":
            raise ValueError("Ideal-gas screen does not implement wet/multiphase compression")
        tis = temp * ratio ** ((gamma - 1) / gamma)
        tout = temp + (tis - temp) / eta
        power = mass * cp * (tout - temp)
        discharge = pressure * ratio
        next_pressure = discharge - loss
        if next_pressure <= 0:
            raise ValueError("Interstage loss makes next absolute pressure nonpositive")
        result.append({"index": index, "suction_pressure_pa": pressure,
                       "discharge_pressure_pa": discharge, "after_loss_pa": loss,
                       "next_pressure_pa": next_pressure, "suction_temperature_k": temp,
                       "discharge_temperature_k": tout, "gas_power_w": power})
        if index + 1 < len(stages):
            following_temp = number(stages[index + 1]["suction_temperature_k"], "next_suction_temperature_k", positive=True)
            result[-1]["interstage_heat_removed_w"] = mass * cp * (tout - following_temp)
            result[-1]["interstage_thermal_duty"] = "cooling" if tout >= following_temp else "heating_required"
        pressure, total = next_pressure, total + power
    return {"status": "IDEAL_GAS_SCREENING_NOT_RATING", "property_basis": property_basis,
            "stages": result, "delivery_pressure_pa": pressure, "gas_power_w": total,
            "mechanical_motor_efficiency_included": False,
            "equations": ["T2s=T1*r^((gamma-1)/gamma)", "T2=T1+(T2s-T1)/eta_s",
                          "Wgas=m*cp*(T2-T1)", "Pnext=Psuction*r-deltaP_interstage"],
            "required_formal_check": "same-gas enthalpy/phase and vendor envelope; rerun the real process"}


def equal_ratio_initializer(*, inlet_pressure_pa, delivery_pressure_pa, after_losses_pa):
    """Solve one common ratio including declared fixed losses; not an optimum."""
    pin = number(inlet_pressure_pa, "inlet_pressure_pa", positive=True)
    target = number(delivery_pressure_pa, "delivery_pressure_pa", positive=True)
    losses = [number(x, "after_loss_pa", nonnegative=True) for x in after_losses_pa]
    if target <= pin or not losses:
        raise ValueError("A pressure-rise target and one loss per stage are required")
    def outlet(ratio):
        p = pin
        for loss in losses:
            p = p * ratio - loss
        return p
    low, high = 1.0, 2.0
    for _ in range(128):
        if outlet(high) >= target:
            break
        high *= 2
    else:
        raise ValueError("Unable to bracket a finite common ratio")
    for _ in range(120):
        mid = (low + high) / 2
        if outlet(mid) < target:
            low = mid
        else:
            high = mid
    ratio = (low + high) / 2
    p = pin
    for loss in losses:
        p = p * ratio - loss
        if p <= 0:
            raise ValueError("Equal-ratio initializer has a nonphysical interstage pressure")
    return {"stage_count": len(losses), "common_pressure_ratio": ratio,
            "delivery_pressure_pa": p, "status": "INITIAL_GUESS_NOT_OPTIMUM"}


def parallel_distribution(total_flow, branch_curves, *, flow_unit, tolerance=1e-9):
    """Common-boundary branch pressure solve from audited monotonic (Q, dP) data.

    Piecewise linear interpolation; no extrapolation; no assumed equal split.
    Curves must include each branch's equipment, fittings and static terms on
    one basis. Units of Q are explicit in the caller's contract and consistent.
    """
    total = number(total_flow, "total_flow", positive=True)
    if flow_unit not in {"m3/s", "m3/h", "kg/s", "kg/h", "kmol/s", "kmol/h"}:
        raise ValueError("Declare one supported, identical flow unit for every branch and total")
    tol = number(tolerance, "tolerance", positive=True)
    curves = []
    for branch in branch_curves:
        if not branch.get("source"):
            raise ValueError("A source/basis is required for each branch curve")
        points = [(number(p[0], "flow", nonnegative=True), number(p[1], "deltaP"))
                  for p in branch["points"]]
        if len(points) < 2 or any(b[0] <= a[0] or b[1] <= a[1] for a, b in zip(points, points[1:])):
            raise ValueError("Branch curves must be strictly increasing in flow and pressure difference")
        curves.append((branch, points))
    if len(curves) < 2:
        raise ValueError("At least two branches required")
    lower = max(p[0][1] for _, p in curves)
    upper = min(p[-1][1] for _, p in curves)
    if lower > upper:
        raise ValueError("No common pressure interval without extrapolation")
    def flow(points, pressure):
        for (q0, p0), (q1, p1) in zip(points, points[1:]):
            if p0 - tol <= pressure <= p1 + tol:
                return q0 + (q1 - q0) * (pressure - p0) / (p1 - p0)
        raise ValueError("Curve extrapolation refused")
    def total_at(pressure):
        return sum(flow(p, pressure) for _, p in curves)
    if not total_at(lower) - tol <= total <= total_at(upper) + tol:
        raise ValueError("Total flow outside the common curve coverage")
    for _ in range(120):
        mid = (lower + upper) / 2
        if total_at(mid) < total:
            lower = mid
        else:
            upper = mid
    dp = (lower + upper) / 2
    branches = [{"id": b["id"], "flow": flow(p, dp), "pressure_difference_pa": dp,
                 "source": b["source"]} for b, p in curves]
    return {"status": "SOURCE_CURVE_INTERPOLATION", "flow_unit": flow_unit, "common_pressure_difference_pa": dp,
            "branches": branches, "flow_residual": sum(b["flow"] for b in branches) - total,
            "equations": ["sum(Q_branch)=Q_total", "deltaP_branch=Pin_common-Pout_common"],
            "boundary": "curves must use the same phases/composition/temperature/boundaries; not column rating"}
