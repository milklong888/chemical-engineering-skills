# Recycle Scale, Root, And Live-Control Repair

Use this reference for Aspen cases where the flowsheet is connected and
runnable but exhibits scale drift, makeup runaway, multiple stable recycle
roots, startup-only warnings, loop-basis ratio errors, or suspicious conversion
claims.

## Authority Freeze

Before mutation, record these as separate invariants:

```text
independent fresh feeds: total and component flows, basis, T, P, phase
physical recycle streams: source block -> stream -> destination block
numerical tears: stream, state, tolerance, method
loop-basis control streams and written variables
recovery pools, products, vents, purges, and treatment boundaries
reaction conversion/selectivity definitions and all outlet phases
residence-time or space-velocity target and actual Aspen result field
Control Panel/history and product hard gates
```

Do not infer plant scale from one fresh stream. Restoring one feed while another
independent feed remains scaled is an incomplete scale repair. Conversely, a
large reactor inlet can be correct when it contains internal recycle; compare
fresh boundaries with source values and loop inventory with the accepted
recycle design.

## Diagnose In This Order

1. **Boundary scale**: compare every independent fresh stream with the original
   run/export, including component-flow rows. Use the source BKP's own export or
   same-source run CSV when possible.
2. **Physical topology**: prove which streams are actually connected. Classify
   each terminal stream as product, recovery pool, purge, vent, treatment feed,
   or true loss before calling it waste.
3. **Numerical topology**: list explicit tears separately. Removing an explicit
   tear changes the solver surface, not physical connectivity.
4. **Material metrics**: calculate conversion and selectivity from all phases.
5. **Control dependency**: trace Calculator reads/writes and the exported
   computation order inside the recycle loop.
6. **Root fingerprint**: compare loop inventory, key intermediates, limiting
   reactants, recovery split, purge, and guard actuation against accepted and
   rejected roots.
7. **History path**: distinguish final physical infeasibility from a bad startup
   trajectory by reading the first problem context and the final state.

## Multiphase Reaction Metrics

For reactant `A` with one inlet and several physical outlets:

```text
X_A = 1 - sum(outlet A molar flow across every phase) / inlet A molar flow
```

For product `P` already present in a seed or recycle inlet:

```text
net P formed = sum(outlet P across every phase) - inlet P
selectivity to P = net P formed / A reacted
```

Do not use only the liquid outlet when vapor outlets carry reactant. The
difference between liquid disappearance and total-phase disappearance is phase
transfer, not reaction.

## Calculator And Input-Basis Rules

- A ratio specified on the recycle inlet must read the recycle-closed stream,
  not only fresh makeup.
- Execute the Calculator before the first dependent block inside the live
  recycle order. Verify this in exported computation-order evidence.
- Preserve the stream's existing input basis. If the stream is entered by
  component mole flows, write the intended component flow; do not mix total
  flow plus stale component rows or mass/mole bases.
- Use one manipulated quantity for one primary control role when possible.
- Record the final Calculator output. A protective formula is not accepted if
  it silently changes the steady-state capacity.

### Transient Feasibility Guard

A bounded guard can prevent a stoichiometric reactant from disappearing during
early recycle iterations:

```text
makeup = max(source_floor, safety_margin * live_limiting_intermediate)
```

The source floor and safety margin require current-case evidence. Acceptance
requires:

```text
final makeup == source floor
limiting reactant remains positive during accepted iteration path
guard executes before the dependent pump/mixer/reactor
fresh-feed composition and component basis remain source-faithful
```

If the guard is active at the final point, the current recycle inventory or
root is incompatible with the frozen scale. Do not call the larger guard output
the restored plant scale.

## Trial-Variable Control Classification

Before sweeping a trial value, classify its process role:

```text
independent boundary -> retain a fixed source/design value
algebraically correlated variable -> use a Calculator with units and bounds
target-closing manipulated variable -> use a Design Spec with one scalar target
unknown feasible window -> bracket first with bounded manual or Sensitivity points
```

Do not leave a correlated variable as an independent knob merely because a
fixed-value probe runs. In particular, stronger raw-material recovery should
normally displace fresh makeup. Holding makeup fixed while increasing recycle
recovery can force a high-inventory root even when every physical connection is
valid. Close the material inventory with a bounded fresh-feed Design Spec, and
use a Calculator for ratios defined on the recycle-closed inlet, such as
once-through gas per loop reactant.

Place rigorous recovery equipment on the smallest physically meaningful waste
boundary when that preserves the source main-loop service. Replacing a simple
main-loop purge divider with a rigorous tower can make the entire recycle solve
needlessly brittle; a real recovery tower on the smaller purge stream may
recover the same raw material while retaining a concentrated impurity outlet.
This is a topology decision, not permission to use an ideal `SEP` surrogate.

## Root Selection And Positive Feedback

Typical positive feedback is:

```text
recovery increases -> loop inventory/intermediate increases
-> protective makeup increases -> downstream production/recycle increases
-> recovery increases again
```

Fingerprint roots with a compact tuple:

```text
(fresh boundaries, loop reactant inventory, key intermediate,
 limiting reactant, recovery split, purge, guard output, product rate)
```

Treat a clean but wrong-root run as rejected. Use bounded inventory controls,
recovery/purge roles, or an authorized physical target to make the desired root
stable. Do not cut recycle, recycle a once-through gas, or starve a feed merely
to force the lower root.

## Initialization Strategy

Same-case final results are numerical estimates, not process specifications.

1. Seed only the failed tear or immediate upstream/downstream path.
2. If the path is overwritten before the failed block, seed the true direct
   upstream source instead.
3. Watch for a root change after each seed expansion.
4. Broaden to a connected-island warm start only after a bounded process
   variable makes the desired root unique.
5. Never seed independent once-through feeds in a way that changes their input
   basis or bypasses live controls.

Broad warm starts can remove startup transients, but they can also select a
high-inventory root. Keep separate evidence for physical cards and initial
estimates.

## Retained Zero-Flow Branches

When source topology requires a block/outlet that becomes exactly zero at the
restored scale, first determine whether zero flow is physically valid and
whether the block can remain clean. If Aspen marks the retained block bad, a
documented trace split may be used only when:

- topology must remain;
- the trace is many orders below process flow;
- its material loss is explicitly quantified;
- product/recovery gates are unchanged;
- copied-delivery history and block statuses are clean.

Do not use trace flows to hide a missing process route or meaningful loss.

## Bounded Tuning

Use response evidence to choose the next probe. For a monotonic local response,
interpolate or bracket the target and take the smallest practical step. Update
the change-offset table before each process mutation. One branch should test
one repair family.

Reject branches that:

- restore one fresh feed but leave another scaled;
- produce a clean run on the wrong root;
- keep a protective guard active at the final point;
- remove a warning by changing global precision or product targets;
- count phase transfer as reaction;
- disconnect physical recycle when only a numerical tear change was intended;
- reduce recovery without classifying the resulting boundary stream.

## Promotion Gates

Apply gates in this order:

1. Reopen the candidate with no model edits and run it.
2. Capture direct Control Panel summary counts and raw `.his` from that run.
3. Require terminal, severe, error, and warning counts to satisfy the project
   first criterion; scan actual problem lines as well.
4. Verify all final block/Calculator/spec statuses.
5. Verify every fresh boundary, component basis, physical recycle connection,
   guard final state, loop ratio, total-phase conversion/selectivity, residence
   time, recovery/purge, and product gates.
6. Copy the accepted file to the delivery path, hash it, reopen that exact copy
   without edits, rerun, and repeat gates 2-5.

Use an operation packet like:

```text
source candidate and hash:
frozen boundary vector:
physical recycle map:
explicit tear map:
accepted root fingerprint:
Calculator dependency/order:
initial estimates changed:
first problem before/after:
Control Panel counts:
raw history counts:
same-run process metrics:
delivery-copy hash and reopen evidence:
```
