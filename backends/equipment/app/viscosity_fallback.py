from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA = "equipment-design-viscosity-correlation-estimate-v1"
SHA256_PATTERN = re.compile(r"^[0-9A-Fa-f]{64}$")
SUPPORTED_PHASES = {"liquid", "vapor"}
TRACE_FRACTION_CUTOFF = 1.0e-10
FORMULA_SOURCES = {
    "SUTHERLAND": {
        "title": "The viscosity of gases and molecular force",
        "author": "William Sutherland",
        "year": 1893,
        "doi": "10.1080/14786449308620508",
    },
    "WILKE_GAS_MIXTURE": {
        "title": "A Viscosity Equation for Gas Mixtures",
        "author": "C. R. Wilke",
        "year": 1950,
        "doi": "10.1063/1.1747673",
    },
    "LIQUID_LOG_MIXING": {
        "title": "Mixture Law for Viscosity",
        "author": "L. Grunberg and A. H. Nissan",
        "year": 1949,
        "doi": "10.1038/164799b0",
        "implementation_boundary": (
            "The present no-interaction mole-fraction logarithmic rule is a "
            "screening form; "
            "binary interaction parameters are not silently set by evidence."
        ),
    },
}


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def _finite_positive(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number <= 0.0:
        return None
    return number


def _finite_nonnegative(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0.0:
        return None
    return number


def _blocked(
    code: str,
    *,
    missing_fields: Sequence[str] = (),
    detail: str,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "schema": SCHEMA,
        "status": "BLOCKED",
        "code": code,
        "missing_fields": sorted(set(str(item) for item in missing_fields)),
        "detail": detail,
        "origin": "INTERNAL_CORRELATION_ESTIMATE",
        "formal_design_evidence": False,
        "promotion_cap": "TYPE_SCREENING",
        "warning_codes": [
            "W_VISCOSITY_ESTIMATE_NOT_AVAILABLE",
            "W_ASPEN_VISCOSITY_NOT_REPLACED",
        ],
        "claim_boundary": (
            "A blocked correlation is not replaced by a default viscosity. "
            "Pipe Reynolds number and friction calculations remain open."
        ),
    }
    if context:
        result["context"] = dict(context)
    result["result_sha256"] = canonical_sha256(result)
    return result


def _validated_source(record: Mapping[str, Any], component_id: str) -> tuple[dict[str, Any] | None, str | None]:
    source = record.get("source")
    if not isinstance(source, Mapping):
        return None, f"correlation_records.{component_id}.source"
    source_id = str(source.get("source_id") or "").strip()
    citation = str(source.get("citation") or "").strip()
    source_sha256 = str(source.get("sha256") or "").strip().upper()
    if not source_id:
        return None, f"correlation_records.{component_id}.source.source_id"
    if not citation:
        return None, f"correlation_records.{component_id}.source.citation"
    if not SHA256_PATTERN.fullmatch(source_sha256):
        return None, f"correlation_records.{component_id}.source.sha256"
    return {
        "source_id": source_id,
        "citation": citation,
        "sha256": source_sha256,
        "verification_status": "DECLARED_SOURCE_HASH_FORMAT_VALID_ONLY",
        "verification_boundary": (
            "The enclosing Aspen export hash binds this coefficient record. "
            "This function does not open the external source asset, so the "
            "declared source hash is not independently verified here."
        ),
    }, None


def _evaluate_pure_model(
    model: Mapping[str, Any],
    temperature_k: float,
) -> tuple[float | None, dict[str, Any]]:
    model_id = str(model.get("model") or "").strip().upper()
    minimum_k = _finite_positive(model.get("temperature_min_k"))
    maximum_k = _finite_positive(model.get("temperature_max_k"))
    if minimum_k is None or maximum_k is None or minimum_k >= maximum_k:
        return None, {
            "status": "INVALID_MODEL_RANGE",
            "model": model_id,
        }
    if not minimum_k <= temperature_k <= maximum_k:
        return None, {
            "status": "TEMPERATURE_OUTSIDE_MODEL_RANGE",
            "model": model_id,
            "temperature_k": temperature_k,
            "temperature_min_k": minimum_k,
            "temperature_max_k": maximum_k,
        }

    if model_id == "SUTHERLAND":
        mu_ref = _finite_positive(model.get("mu_ref_pa_s"))
        temperature_ref_k = _finite_positive(model.get("temperature_ref_k"))
        sutherland_k = _finite_positive(model.get("sutherland_k"))
        if None in (mu_ref, temperature_ref_k, sutherland_k):
            return None, {"status": "INVALID_SUTHERLAND_COEFFICIENTS", "model": model_id}
        value = (
            mu_ref
            * (temperature_k / temperature_ref_k) ** 1.5
            * (temperature_ref_k + sutherland_k)
            / (temperature_k + sutherland_k)
        )
        formula = (
            "mu=mu_ref*(T/T_ref)^1.5*(T_ref+S)/(T+S)"
        )
        coefficients = {
            "mu_ref_pa_s": mu_ref,
            "temperature_ref_k": temperature_ref_k,
            "sutherland_k": sutherland_k,
        }
    elif model_id == "DIPPR_101":
        coefficients_raw = model.get("coefficients")
        if not isinstance(coefficients_raw, Mapping):
            return None, {"status": "INVALID_DIPPR_101_COEFFICIENTS", "model": model_id}
        coefficients: dict[str, float] = {}
        for name in ("A", "B", "C", "D", "E"):
            try:
                value_raw = float(coefficients_raw.get(name))
            except (TypeError, ValueError):
                return None, {"status": "INVALID_DIPPR_101_COEFFICIENTS", "model": model_id}
            if not math.isfinite(value_raw):
                return None, {"status": "INVALID_DIPPR_101_COEFFICIENTS", "model": model_id}
            coefficients[name] = value_raw
        exponent = (
            coefficients["A"]
            + coefficients["B"] / temperature_k
            + coefficients["C"] * math.log(temperature_k)
            + coefficients["D"] * temperature_k ** coefficients["E"]
        )
        try:
            value = math.exp(exponent)
        except OverflowError:
            return None, {"status": "MODEL_NUMERIC_OVERFLOW", "model": model_id}
        formula = "mu=exp(A+B/T+C*ln(T)+D*T^E)"
    elif model_id == "ARRHENIUS_TWO_CONSTANT":
        a_value = model.get("A")
        b_value = model.get("B_K")
        try:
            a_value = float(a_value)
            b_value = float(b_value)
        except (TypeError, ValueError):
            return None, {"status": "INVALID_ARRHENIUS_COEFFICIENTS", "model": model_id}
        if (
            not math.isfinite(a_value)
            or a_value <= 0.0
            or not math.isfinite(b_value)
        ):
            return None, {"status": "INVALID_ARRHENIUS_COEFFICIENTS", "model": model_id}
        try:
            value = a_value * math.exp(b_value / temperature_k)
        except OverflowError:
            return None, {"status": "MODEL_NUMERIC_OVERFLOW", "model": model_id}
        coefficients = {"A": a_value, "B_K": b_value}
        formula = "mu=A*exp(B/T)"
    else:
        return None, {"status": "UNSUPPORTED_PURE_COMPONENT_MODEL", "model": model_id}

    if not math.isfinite(value) or value <= 0.0:
        return None, {"status": "NON_PHYSICAL_MODEL_RESULT", "model": model_id}
    return value, {
        "status": "PASS",
        "model": model_id,
        "formula": formula,
        "coefficients": coefficients,
        "temperature_k": temperature_k,
        "temperature_min_k": minimum_k,
        "temperature_max_k": maximum_k,
        "dynamic_viscosity_pa_s": value,
    }


def _normalize_composition(
    composition: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]] | None, dict[str, Any] | None]:
    rows: list[dict[str, Any]] = []
    bases: set[str] = set()
    for item in composition:
        component_id = str(item.get("component_id") or "").strip()
        fraction = _finite_nonnegative(item.get("fraction"))
        basis = str(item.get("basis") or "").strip().casefold()
        if not component_id or fraction is None or basis not in {"mole_fraction", "mass_fraction"}:
            return None, {
                "code": "BLOCKED_INVALID_COMPOSITION_ROW",
                "missing_fields": ["closed nonnegative component_id/fraction/basis rows"],
            }
        rows.append({
            "component_id": component_id,
            "fraction": fraction,
            "basis": basis,
        })
        bases.add(basis)
    if not rows or len(bases) != 1:
        return None, {
            "code": "BLOCKED_INVALID_COMPOSITION_BASIS",
            "missing_fields": ["one closed composition basis"],
        }
    total = sum(item["fraction"] for item in rows)
    if not 0.995 <= total <= 1.005:
        return None, {
            "code": "BLOCKED_COMPOSITION_NOT_CLOSED",
            "missing_fields": ["composition sum within 0.5% of unity"],
            "composition_sum": total,
        }
    normalized_rows: list[dict[str, Any]] = []
    omitted_rows: list[dict[str, Any]] = []
    for item in rows:
        item["fraction"] /= total
        if item["fraction"] <= TRACE_FRACTION_CUTOFF:
            omitted_rows.append(item)
        else:
            normalized_rows.append(item)
    retained_total = sum(item["fraction"] for item in normalized_rows)
    if retained_total <= 0.0:
        return None, {
            "code": "BLOCKED_COMPOSITION_HAS_NO_RETAINED_COMPONENT",
            "missing_fields": ["at least one component above trace cutoff"],
        }
    for item in normalized_rows:
        item["fraction"] /= retained_total
    return normalized_rows, {
        "basis": next(iter(bases)),
        "raw_sum": total,
        "normalization_factor": 1.0 / total,
        "trace_fraction_cutoff": TRACE_FRACTION_CUTOFF,
        "omitted_trace_fraction": sum(item["fraction"] for item in omitted_rows),
        "omitted_trace_components": [
            {
                "component_id": item["component_id"],
                "normalized_fraction_before_trace_renormalization": item["fraction"],
            }
            for item in omitted_rows
        ],
        "retained_renormalization_factor": 1.0 / retained_total,
    }


def _mole_to_mass_fractions(
    rows: Sequence[Mapping[str, Any]],
    molecular_weights: Mapping[str, float],
) -> list[float]:
    weighted = [
        float(item["fraction"]) * molecular_weights[str(item["component_id"])]
        for item in rows
    ]
    total = sum(weighted)
    return [value / total for value in weighted]


def _mass_to_mole_fractions(
    rows: Sequence[Mapping[str, Any]],
    molecular_weights: Mapping[str, float],
) -> list[float]:
    molar = [
        float(item["fraction"]) / molecular_weights[str(item["component_id"])]
        for item in rows
    ]
    total = sum(molar)
    return [value / total for value in molar]


def _wilke(
    mole_fractions: Sequence[float],
    viscosities_pa_s: Sequence[float],
    molecular_weights: Sequence[float],
) -> tuple[float, list[list[float]]]:
    count = len(mole_fractions)
    phi: list[list[float]] = [[0.0] * count for _ in range(count)]
    for i in range(count):
        for j in range(count):
            numerator = (
                1.0
                + math.sqrt(viscosities_pa_s[i] / viscosities_pa_s[j])
                * (molecular_weights[j] / molecular_weights[i]) ** 0.25
            ) ** 2
            denominator = math.sqrt(
                8.0 * (1.0 + molecular_weights[i] / molecular_weights[j])
            )
            phi[i][j] = numerator / denominator
    mixture = 0.0
    for i in range(count):
        denominator = sum(
            mole_fractions[j] * phi[i][j]
            for j in range(count)
        )
        mixture += mole_fractions[i] * viscosities_pa_s[i] / denominator
    return mixture, phi


def estimate_stream_viscosity(
    *,
    phase: str,
    temperature_k: Any,
    composition: Sequence[Mapping[str, Any]],
    correlation_records: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Estimate one single-phase stream viscosity without hiding evidence gaps.

    The equations are built in, while every component coefficient record must
    carry its own source identity and SHA-256.  No extrapolation, arbitrary
    default viscosity, or two-phase effective viscosity is permitted.
    """

    normalized_phase = str(phase or "").strip().casefold()
    if normalized_phase not in SUPPORTED_PHASES:
        return _blocked(
            "BLOCKED_VISCOSITY_CORRELATION_PHASE",
            missing_fields=["unambiguous single phase: liquid or vapor"],
            detail=(
                "The internal correlation is not valid for two-phase, "
                "solid-bearing, unknown, or supercritical phase labels."
            ),
            context={"phase": normalized_phase},
        )
    temperature = _finite_positive(temperature_k)
    if temperature is None:
        return _blocked(
            "BLOCKED_VISCOSITY_CORRELATION_TEMPERATURE",
            missing_fields=["temperature_k"],
            detail="A finite positive absolute temperature is required.",
        )
    if not isinstance(composition, Sequence) or isinstance(composition, (str, bytes)):
        return _blocked(
            "BLOCKED_VISCOSITY_CORRELATION_COMPOSITION",
            missing_fields=["closed composition"],
            detail="A closed component composition is required.",
        )
    normalized, normalization = _normalize_composition(composition)
    if normalized is None:
        assert normalization is not None
        return _blocked(
            str(normalization["code"]),
            missing_fields=normalization.get("missing_fields", []),
            detail="Component fractions must be nonnegative, use one basis, and close to unity.",
            context={
                key: value
                for key, value in normalization.items()
                if key not in {"code", "missing_fields"}
            },
        )

    phase_record_key = "liquid" if normalized_phase == "liquid" else "vapor"
    pure_rows: list[dict[str, Any]] = []
    missing: list[str] = []
    molecular_weights: dict[str, float] = {}
    for item in normalized:
        component_id = str(item["component_id"])
        record = correlation_records.get(component_id)
        if not isinstance(record, Mapping):
            missing.append(f"correlation_records.{component_id}")
            continue
        source, source_missing = _validated_source(record, component_id)
        if source_missing:
            missing.append(source_missing)
            continue
        molecular_weight = _finite_positive(record.get("molecular_weight_kg_kmol"))
        if molecular_weight is None:
            missing.append(f"correlation_records.{component_id}.molecular_weight_kg_kmol")
            continue
        model = record.get(phase_record_key)
        if not isinstance(model, Mapping):
            missing.append(f"correlation_records.{component_id}.{phase_record_key}")
            continue
        viscosity, calculation = _evaluate_pure_model(model, temperature)
        if viscosity is None:
            missing.append(
                f"correlation_records.{component_id}.{phase_record_key}:"
                f"{calculation.get('status')}"
            )
            continue
        molecular_weights[component_id] = molecular_weight
        pure_rows.append({
            "component_id": component_id,
            "input_fraction": item["fraction"],
            "input_basis": item["basis"],
            "molecular_weight_kg_kmol": molecular_weight,
            "source": source,
            "source_record_sha256": canonical_sha256(record),
            "calculation": calculation,
        })
    if missing:
        return _blocked(
            "BLOCKED_INCOMPLETE_VISCOSITY_CORRELATION_COVERAGE",
            missing_fields=missing,
            detail=(
                "Every positive component needs a source-bound pure-component "
                "correlation covering the actual temperature."
            ),
            context={
                "phase": normalized_phase,
                "temperature_k": temperature,
                "component_ids": [item["component_id"] for item in normalized],
            },
        )

    input_basis = str(normalization["basis"])
    component_ids = [str(item["component_id"]) for item in normalized]
    pure_viscosities = [
        float(item["calculation"]["dynamic_viscosity_pa_s"])
        for item in pure_rows
    ]
    pure_model_ids = sorted({
        str(item["calculation"]["model"])
        for item in pure_rows
    })
    warning_codes = [
        "W_VISCOSITY_INTERNAL_CORRELATION_ESTIMATE",
        "W_VISCOSITY_NOT_ASPEN_EXTRACTED",
        "W_VISCOSITY_PRELIMINARY_HYDRAULICS_ONLY",
        "W_CORRELATION_SOURCE_ASSET_HASH_NOT_LOCALLY_VERIFIED",
    ]
    if normalization.get("omitted_trace_components"):
        warning_codes.append("W_TRACE_COMPONENTS_BELOW_VISCOSITY_THRESHOLD_OMITTED")
    if normalized_phase == "vapor":
        if input_basis == "mole_fraction":
            mixing_fractions = [float(item["fraction"]) for item in normalized]
            conversion = "identity_mole_fraction"
        else:
            mixing_fractions = _mass_to_mole_fractions(normalized, molecular_weights)
            conversion = "x_i=(w_i/MW_i)/sum(w_j/MW_j)"
        mixture_pa_s, phi = _wilke(
            mixing_fractions,
            pure_viscosities,
            [molecular_weights[item] for item in component_ids],
        )
        mixing_rule = "WILKE_GAS_MIXTURE"
        mixing_formula = (
            "mu_mix=sum_i[x_i*mu_i/sum_j(x_j*phi_ij)]; "
            "phi_ij=[1+sqrt(mu_i/mu_j)*(MW_j/MW_i)^0.25]^2/"
            "sqrt(8*(1+MW_i/MW_j))"
        )
        mixing_detail: dict[str, Any] = {"phi_matrix": phi}
        warning_codes.append("W_WILKE_LOW_PRESSURE_GAS_MIXING_RULE")
    else:
        if input_basis == "mole_fraction":
            mixing_fractions = [float(item["fraction"]) for item in normalized]
            conversion = "identity_mole_fraction"
        else:
            mixing_fractions = _mass_to_mole_fractions(normalized, molecular_weights)
            conversion = "x_i=(w_i/MW_i)/sum(w_j/MW_j)"
        mixture_pa_s = math.exp(sum(
            fraction * math.log(viscosity)
            for fraction, viscosity in zip(mixing_fractions, pure_viscosities)
        ))
        mixing_rule = "GRUNBERG_NISSAN_IDEAL_MOLE_LOG_LIQUID"
        mixing_formula = "ln(mu_mix)=sum_i[x_i*ln(mu_i)] (G_ij terms omitted)"
        mixing_detail = {}
        warning_codes.append(
            "W_GRUNBERG_NISSAN_BINARY_INTERACTION_PARAMETERS_NOT_APPLIED"
        )

    result = {
        "schema": SCHEMA,
        "status": "PASS_WITH_WARNING",
        "origin": "INTERNAL_CORRELATION_ESTIMATE",
        "evidence_class": "J",
        "formal_design_evidence": False,
        "promotion_cap": "TYPE_SCREENING",
        "phase": normalized_phase,
        "temperature_k": temperature,
        "dynamic_viscosity_pa_s": mixture_pa_s,
        "dynamic_viscosity_mpa_s": mixture_pa_s * 1000.0,
        "composition_normalization": normalization,
        "component_ids": component_ids,
        "pure_component_calculations": pure_rows,
        "pure_component_model_ids": pure_model_ids,
        "mixing_rule": mixing_rule,
        "mixing_formula": mixing_formula,
        "mixing_fraction_basis": (
            "mole_fraction"
        ),
        "mixing_fractions": dict(zip(component_ids, mixing_fractions)),
        "basis_conversion": conversion,
        "mixing_detail": mixing_detail,
        "formula_sources": [
            *(
                [FORMULA_SOURCES["SUTHERLAND"]]
                if "SUTHERLAND" in pure_model_ids
                else []
            ),
            *(
                [FORMULA_SOURCES["WILKE_GAS_MIXTURE"]]
                if normalized_phase == "vapor"
                else [FORMULA_SOURCES["LIQUID_LOG_MIXING"]]
            ),
        ],
        "source_bundle_sha256": canonical_sha256([
            {
                "component_id": item["component_id"],
                "source_record_sha256": item["source_record_sha256"],
            }
            for item in pure_rows
        ]),
        "warning_codes": warning_codes,
        "claim_boundary": (
            "This value is a deterministic source-bound correlation estimate "
            "for preliminary single-phase hydraulics. It is not an Aspen "
            "property observation, does not define two-phase effective "
            "viscosity, and cannot by itself release a formal line class, "
            "pressure drop, material, or equipment selection."
        ),
    }
    result["result_sha256"] = canonical_sha256(result)
    return result
