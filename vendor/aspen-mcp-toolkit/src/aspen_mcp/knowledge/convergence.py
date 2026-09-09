"""Convergence diagnostic knowledge base.

Seven common Aspen Plus convergence failure modes, their detectable
signals, and recommended fixes.  Used by the ``diagnose`` tool.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FailureMode:
    """One known convergence failure pattern."""

    id: str
    title: str
    description: str
    symptoms: list[str]
    checks: list[str]
    fixes: list[str]
    severity: str = "medium"


FAILURE_MODES: list[FailureMode] = [
    FailureMode(
        id="tear-stream",
        title="Tear Stream Not Converging",
        description="The recycle loop (tear stream) oscillates or diverges.",
        symptoms=[
            "Simulation terminates with 'Convergence iterations completed' but not converged",
            "Tear stream composition oscillates between iterations",
            "Convergence block shows 'Not converged to tolerance'",
            "Repeated 'Maximum number of iterations exceeded'",
        ],
        checks=[
            "Check convergence block iteration limit (default 30 -> try 200)",
            "Verify tear stream initial estimate is reasonable",
            "Check for nested recycles that may need simultaneous convergence",
        ],
        fixes=[
            "Increase maximum iterations to 200-500",
            "Enable damping (Wegstein damping factor 0.0 -> 0.3-0.7)",
            "Switch tear stream to a different location",
            "Use Direct method for difficult recycles",
        ],
        severity="high",
    ),
    FailureMode(
        id="bad-initial-guess",
        title="Poor Initial Estimates",
        description="Blocks converge from default guesses but fail from user guesses.",
        symptoms=[
            "Some blocks converge individually but the flowsheet does not",
            "Changing initial estimates dramatically changes convergence behavior",
        ],
        checks=[
            "Review block input specifications - are they realistic?",
            "Check that temperature/pressure guesses are within operating range",
            "Verify feed composition sums to 1.0",
        ],
        fixes=[
            "Remove user-specified estimates and let Aspen generate defaults",
            "Run a simplified model first, then add complexity",
        ],
        severity="medium",
    ),
    FailureMode(
        id="chemistry-reaction",
        title="Chemistry / Reaction Issues",
        description="Reactions are not proceeding as expected.",
        symptoms=[
            "Reaction conversion is far from expected",
            "Equilibrium reactor gives unrealistic product distribution",
        ],
        checks=[
            "Verify reaction stoichiometry and kinetics are consistent",
            "Ensure all required components are present",
        ],
        fixes=[
            "Review reaction stoichiometry for molar balance",
            "For electrolyte systems, verify ion pairs and salt formation",
            "Check for missing components",
        ],
        severity="high",
    ),
    FailureMode(
        id="property-method",
        title="Property Method Inappropriate",
        description="The selected thermodynamic model is unsuitable.",
        symptoms=[
            "Phase equilibrium calculations produce physically impossible results",
            "K-value/enthalpy calculations overflow",
        ],
        checks=[
            "Verify the property method is valid for the chemical system",
            "Check temperature/pressure are within the valid range",
        ],
        fixes=[
            "Switch to a more robust property method",
            "Add binary interaction parameters if missing",
            "Consider an electrolyte property method for ionic species",
        ],
        severity="high",
    ),
    FailureMode(
        id="column-design",
        title="Column / Distillation Design Issues",
        description="RadFrac or other column models fail to converge.",
        symptoms=[
            "Column does not converge, 'Column algorithms failed'",
            "Tray temperature profiles are non-monotonic",
            "Reflux ratio specifications are infeasible",
        ],
        checks=[
            "Verify number of stages is reasonable for the separation",
            "Check feed stage location",
        ],
        fixes=[
            "Increase number of stages",
            "Adjust feed location",
            "Start with simplified column (DSTWU -> RadFrac)",
        ],
        severity="medium",
    ),
    FailureMode(
        id="stream-flash",
        title="Stream Flash Calculation Failure",
        description="A stream flash calculation fails.",
        symptoms=[
            "Stream flash fails with 'Temperature out of valid range'",
            "Vapor fraction is exactly 0 or 1 at unexpected conditions",
        ],
        checks=[
            "Inspect stream temperature and pressure - are they physical?",
            "Check for water/hydrocarbon systems where three-phase flash is needed",
        ],
        fixes=[
            "Switch stream flash type to 'Vapor-Liquid-Liquid'",
            "Provide reasonable temperature/pressure estimate",
        ],
        severity="medium",
    ),
    FailureMode(
        id="solver-options",
        title="Solver / Convergence Block Options",
        description="Default convergence block settings are inadequate.",
        symptoms=[
            "Flowsheet converges very slowly (>100 iterations)",
            "Convergence oscillates without progress",
        ],
        checks=[
            "Inspect convergence block type",
            "Check if multiple convergence blocks interact",
            "Verify tolerance settings",
        ],
        fixes=[
            "Switch from Wegstein to Direct for unstable loops",
            "Increase Wegstein damping",
            "Use a single convergence block for coupled loops",
        ],
        severity="low",

    ),
]

# ── convergence method selection guide ──────────────────────────────────


# ── method-guide pseudo entry ────────────────────────────────────────


def _search_guide_and_table(keywords: list[str]) -> list[dict]:
    """Search CONVERGENCE_METHOD_GUIDE and COMMON_ERROR_TABLE for keywords.

    Returns entries formatted like search_failures() output.
    """
    hits = []
    kw_lower = {k.lower() for k in keywords}
    text = CONVERGENCE_METHOD_GUIDE.lower()
    if any(kw in text for kw in kw_lower):
        hits.append({
            "id": "convergence-method",
            "title": "Convergence Method Selection",
            "description": "Choosing between Wegstein/Broyden/Direct/Newton",
            "severity": "medium",
            "symptoms": ["Simulation converges slowly or oscillates",
                         "Default Wegstein method not working"],
            "fixes": [line.strip() for line in CONVERGENCE_METHOD_GUIDE.split("\n")
                      if line.strip() and not line.strip().startswith("Convergence")],
        })
    text = COMMON_ERROR_TABLE.lower()
    if any(kw in text for kw in kw_lower):
        hits.append({
            "id": "common-errors",
            "title": "Common Aspen Plus Errors",
            "description": "Quick reference for frequently encountered errors",
            "severity": "medium",
            "symptoms": ["One of the common error messages appeared",
                         "COLUMN DRIES UP, NOT IN MASS BALANCE, etc."],
            "fixes": [line.strip() for line in COMMON_ERROR_TABLE.split("\n")
                      if line.strip() and not line.strip().startswith("Common")],
        })
    return hits


CONVERGENCE_METHOD_GUIDE = r"""
Convergence Method Selection Guide:

  Wegstein (default)  — Simple single-loop recycles. Fast but may oscillate
                         on complex multi-loop systems.
  Broyden             — Best first choice when Wegstein fails. Handles
                         complex multi-loop systems well.
  Direct              — Most robust but slowest. Pure substitution,
                         no acceleration. Good for very unstable systems.
  Newton              — Full Jacobian update. Most powerful but most
                         expensive per iteration. Last resort.

Path: \Data\Convergence\Conv-Options\Input\TEAR_METHOD
Values: WEGSTEIN, BROYDEN, DIRECT, NEWTON

Max iterations: \Data\Convergence\Conv-Options\Input\{WEG|BR|DIR}_MAXIT
Tolerance: \Data\Convergence\Conv-Options\Input\TOL (default 0.0001)

NOTE: TEAR_METHOD controls tear stream iteration, NOT COMB_METHOD
(combined convergence method, default BROYDEN).
"""

COMMON_ERROR_TABLE = r"""
Common Aspen Plus Errors Quick Reference:

  Error                              Cause                              Fix
  ─────────────────────────────────────────────────────────────────────────────
  COLUMN DRIES UP                   Feed fully vaporized/condensed    Adjust feed T/P, reduce heat duty
  COLUMN NOT IN MASS BALANCE        Product flows exceed total feed   Check D + side draw + B = Feed
  Petroleum/Wide-boiling not allowed VLL incompatible with petroleum   Set ALGORITHM=STANDARD
  INCONSISTENT PROPERTIES DETECTED   Block OPSETNAME != global        Check every block's OPSETNAME
  Recycle loop not converging        Tear method or max iter insufficient Switch to Broyden, increase max iter
  Block incomplete                   Missing required inputs          Use find_incomplete_inputs()
  Oscillating convergence            Wegstein struggling on complex    Switch to Broyden or Newton
"""



def search_failures(keywords: list[str]) -> list[dict]:
    """Return failure modes matching *any* keyword (includes guide + table)."""
    kw_lower = {k.lower() for k in keywords}
    hits: list[dict] = []
    for fm in FAILURE_MODES:
        text = (
            fm.title.lower() + " " + fm.description.lower()
            + " " + " ".join(fm.symptoms).lower()
        )
        if any(kw in text for kw in kw_lower):
            hits.append({
                "id": fm.id,
                "title": fm.title,
                "description": fm.description,
                "severity": fm.severity,
                "symptoms": fm.symptoms,
                "fixes": fm.fixes,
            })
    # Also search the method guide and error table
    hits.extend(_search_guide_and_table(keywords))
    return hits if hits else [{"note": "No matching failure modes found."}]
