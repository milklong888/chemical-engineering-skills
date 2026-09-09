# Empty-Column VRC Replacement Workflow

## 1. Select A Candidate Tower

Good candidates have most of these traits:

- the tower has a large condenser/reboiler duty;
- the top/bottom temperature lift is small enough for compression to be
  plausible;
- the overhead stream can be compressed as vapor after a dry-vapor guard check;
- the original separation can be represented by a small number of product or
  key-component metrics;
- the tower boundary belongs to a separable section island.

Avoid promoting a replacement when the tower is reactive, strongly
three-phase, hydraulically constrained, or product-critical unless the base
tower target ledger is already accepted.

## 2. Baseline And Boundary Freeze

Before any mutation, create a baseline table:

```text
section inputs:
section outputs:
tower feed streams:
tower product streams:
internal recycle / tear candidates:
key product metrics:
original condenser duty:
original reboiler duty:
top pressure / bottom pressure:
top temperature / bottom temperature:
property method:
accepted tolerance:
```

Run both the single-tower island and the large section island when possible.
The single tower helps tune the heat-pump loop; the section island proves the
real reconnect boundary.

Fast path: freeze the original feed and boundary streams before tuning. Do not
let feed drift, recycle startup values, or downstream towers become hidden
degrees of freedom while matching the replaced tower.

For a full-flow candidate, prove portability separately from the first
successful session: reopen the saved BKP without post-import/card-normalizing
mutations, run it, and export the same topology and boundary results. This
guards against accepting a branch that only worked because automation silently
repaired HeatX or recycle fields during reopen.

## 3. Empty The Tower First

This is the first mutation.

```text
BLOCK <TOWER> RADFRAC
    PARAM NSTAGE=<empty_stage_count> ...
    COL-CONFIG CONDENSER=NONE REBOILER=NONE
    FEEDS <main_feed> <feed_stage> / <reflux> 1 / <vap_return> <nstage+1>
    PRODUCTS <ovhd_vapor> 1 V / <bottom_liquid> <nstage> L
```

Practical stage rule:

- if the original RadFrac counted condenser and reboiler as stages, start with
  `empty_stage_count = original_stage_count - 2`;
- feed stage may need an offset after the stage count changes;
- reflux enters stage 1;
- flash vapor return enters below the bottom tray, often stage `NSTAGE+1`;
- tower bottom liquid product is the stream sent to the HeatX cold side, not
  the final bottoms product.

## 4. Insert The Heat-Pump Loop

Preferred topology:

```text
<ovhd_vapor> -> optional dry-vapor guard heater -> COMPR -> <hp_vapor>
<hp_vapor> + <bottom_liquid> -> HEATX -> <hot_out> + <reb_out>
<hot_out> -> trim cooler -> valve -> FSPLIT -> distillate + reflux
<reb_out> -> FLASH2 -> vapor_return + bottoms_product
```

The compressor is the heat pump. The HeatX is the external reboiler/condenser
coupling. Flash blocks define how much vapor returns to the tower and how much
liquid leaves as product. A single reflux/product splitter normally replaces
the original tower reflux/distillate draw relation. Do not stack an overhead
flash plus mixer plus heater around the splitter unless the source topology or
fresh exported evidence proves a real physical drum/mixer duty; otherwise keep
that branch as diagnostic evidence only.

Do not count the retrofit as heat-pump distillation if the original RadFrac
internal condenser/reboiler remain the main heat sources.

Do not begin parameter polishing until the exported INP shows all structural
objects: empty tower, compressor, HeatX, valve or pressure letdown, flash or
drum, reflux/product splitter, reflux return, and vapor return. A runnable
compressor/heater branch without this exported structure is only a VRC
supplement.

## 5. Initial Values

Start from the baseline tower:

- tower stage count equal to the baseline theoretical stages after removing
  only true condenser/reboiler stages, or unchanged when the baseline stage
  count is already tray-like;
- feed stage at the same relative position as the baseline; reflux enters the
  first stage, and flash vapor returns just below the last tray or to the
  documented vapor-return stage;
- FSPLIT reflux fraction estimated from original `L/(L+D)` or from the
  baseline reflux ratio `RR/(RR+1)` when that is the only available reflux
  scale;
- liquid-side flash temperature near the original bottom/reboiler-side
  temperature, with pressure near the original column bottom pressure;
- compressor outlet pressure high enough to make the hot side warmer than the
  bottom/flash target, but not so high that it creates unnecessary temperature
  lift or compressor work;
- HeatX cold outlet near but slightly below the desired liquid flash
  temperature, with a modest positive approach;
- trim cooler near the old condenser outlet/drum temperature;
- valve outlet near tower top pressure;
- flash duty or vapor fraction only as an initialization experiment, then keep
  the physically stable temperature/pressure form when possible.

Keep convergence tolerance at project defaults. Do not tighten tear tolerances
until the loop has a stable root.

## 6. Design Specs

Use the fewest specs that preserve the original duty:

- key product total mole/mass flow;
- key component flow or recovery in distillate/bottoms;
- impurity leakage in the product stream;
- section output total flow where the downstream reconnect needs it.

Common manipulated variables:

- `FSPLIT FRAC` for product/reflux split;
- tower stage count, feed stage, or vapor-return stage when topology is stable
  but separation is off;
- `FLASH2 PARAM TEMP` or pressure on the liquid-side flash that controls vapor
  return;
- `HEATX PARAM T-COLD` after the tower split is close;
- `COMPR PARAM PRES`;
- trim cooler/heater temperature.

Preferred tuning order for empty-column VRC replacements:

1. Freeze the feed boundary and verify the topology tokens in the exported INP.
2. Recover the tower split with the tower-equivalence knobs first: stage/tray
   count or feed/vapor-return stage, one `FSPLIT` reflux fraction, and the
   liquid-side `FLASH2` temperature or pressure.
3. Use the user's practical tolerance only for local bracketing of the replaced
   tower. For example, a 3% instruction means the replaced local tower can stop
   coarse polishing once its own outlets are close; it does not license drift
   across the connected tower system.
4. Once the tower outlets are recovered, check the downstream or tower-system
   boundary at default/design-rule precision. Do not retune downstream towers to
   compensate for a bad heat-pump island unless the project authority changes
   the downstream design.
   If the connected tower system still shows startup or mass-balance history
   dirt after the local heat-pump island is equivalent, inspect the tear
   boundary before changing products. Prefer tearing a stable downstream
   tower-system feed or mixer outlet that carries the combined material into
   the next tower, plus the local reflux and vapor-return recycles, instead of
   tearing final downstream product streams. This is a convergence-boundary
   repair only; it must not change downstream tower specs, final product
   standards, or default tolerances.
5. Only after separation equivalence, polish the heat-pump layer: compressor
   pressure, HeatX cold outlet/approach, and small trim temperatures. HeatX may
   be micro-adjusted here; it should carry the main exchange, not the trim
   heaters/coolers.
6. Use a second heater/cooler only as a small trim. If this trim block provides
   the main heat duty, the candidate is not an accepted heat-pump replacement.

Fast equivalence loop for strict-product towers:

1. Prove what the original tower used to separate: reflux scale, boilup/vapor
   flow, pressure/temperature profile, feed stage, product flow, and impurity
   leakage. Treat these as targets, not hints.
2. Use the overhead splitter and liquid-side flash as the first two degrees of
   freedom. The splitter recovers reflux/product allocation; the flash recovers
   the original boilup or vapor-return scale.
3. If product purity fails while the original single tower passed, suspect a
   missing equivalence variable before adding equipment. Check vapor-return
   amount, return stage, feed-stage offset, and reflux fraction.
4. If a temperature-only flash branch gives low purity or a heavy-impurity
   false root, run a narrow `VFRAC` or pressure sensitivity to locate the
   original boilup scale. Keep the accepted actuator project-specific and
   documented.
5. Once purity and flow are close, polish compressor pressure and HeatX cold
   outlet so `HX_DUTY` is nonzero and plausible. A zero-duty HeatX branch is
   diagnostic, not accepted.
6. Delete diagnostic bypasses before delivery. The only default liquid splitter
   is the overhead condensate reflux/product splitter.

For Aspen `HEATX`, verify both exported INP and the COM tree. A card that
prints `T-COLD` can still carry a stale internal side selector or value. Before
promoting a candidate, prove the actual cold outlet stream temperature, hot
outlet temperature, `HX_DUTY`, `HX_AREAP`, and required block statuses from the
after-run results.

Treat HeatX polishing as the second pass after outlet equivalence, not the first
target. HeatX may be micro-adjusted after the products are close, but it must
carry the main exchange and must not be replaced in practice by trim heaters or
coolers.

Avoid Design Specs that vary flash duty as the first promoted solution. A flash
duty spec can create mass/energy inconsistencies or a wrong root; keep it as a
diagnostic branch unless it is the only physically documented actuator.

## 7. Convergence Strategy

Run order:

```text
baseline single tower
-> baseline large section
-> empty tower without strict specs
-> VRC loop with fixed guesses
-> one Design Spec
-> second Design Spec only if needed
-> large section island with same boundary
-> reconnect seed export
-> if downstream history remains dirty, move tears to stable section feed
   boundaries before touching final products
```

If the candidate fails:

- read the first history/control-panel blocker before editing;
- check phase at compressor inlet;
- check HeatX temperature crossing and pressure-drop signs;
- check flash vapor fraction and product liquid availability;
- loosen only initialization, tear location, damping, or iteration strategy;
- do not relax product/spec tolerances as the accepted fix.
- if product streams are being used as downstream tear streams, test whether a
  stable upstream feed to the downstream tower system is the correct tear
  boundary; accept this only when no-mutation reopen evidence preserves all
  final product standards.

## 8. Acceptance Gate

A candidate can be handed off only when evidence files show:

```text
baseline_run_ok = true
candidate_run_ok = true
history_fatal_count = 0
wet_compression_hit_count = 0
required heat-pump blocks present = true
bad required heat-pump block count = 0
boundary_bad_count = 0
after-run INP contains condenser/reboiler NONE
after-run INP contains COMPR, HEATX, FLASH2, FSPLIT, VALVE
reconnect stream seed CSV/INP exported
accepted BKP saved after the accepted run
```

Warnings may be accepted only when they are unrelated to the required
heat-pump blocks and are named explicitly in the handoff.
Treat property-data warnings separately from topology/process acceptance. A
candidate with clean process history but a missing-property-parameter warning
may be a repaired topology candidate, but not a zero-warning delivery; clear it
only through a property/databank gate and same-candidate rerun, not by retuning
separation targets.

Use two acceptance labels:

- `topology_equivalent_candidate`: exported structure is complete, final
  required blocks are clean, no final wet compression remains, and
  boundary/downstream streams meet the accepted tolerance. This is enough to
  stop tuning when the user asked for a practical design topology.
- `zero_warning_delivery`: the exact delivered BKP/APW is reopened, rerun, and
  its current Control Panel/history has zero terminal/severe/errors/warnings
  under the project delivery policy. Startup/recycle history cleanup belongs
  here; do not change accepted product targets merely to clean history text.

If local reflux/vapor-return streams are real connected recycles but Aspen does
not export them on the `TEAR` card after COM insertion attempts, classify that
as a convergence/export-persistence cleanup item. It blocks
`zero_warning_delivery` only; it should not force extra overhead flash/mixer/
heater units or downstream tower retuning once no-mutation reopen evidence and
boundary equivalence are already in hand.

## 9. Handoff Payload

For a full-flow reconnect thread or agent, send:

```text
accepted BKP path and SHA256:
after-run INP path and SHA256:
boundary compare CSV path:
boundary failed rows:
connectivity CSV path:
reconnect seed CSV path:
reconnect seed INP path:
required heat-pump blocks:
empty-tower proof:
Design Specs retained:
known warnings:
branches rejected and why:
```

Do not send only a ZIP if the receiver must inspect or reconnect immediately;
give direct file paths first, then package paths if needed.
