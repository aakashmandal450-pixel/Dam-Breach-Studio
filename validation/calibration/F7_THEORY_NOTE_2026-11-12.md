# F7 theory note (2026-11-12): a headcut that does not depend on the cell size

Status: theory only; code pending user go-ahead. Seen cases only (Laurel Run, Castlewood); any fix must be
pre-registered and tested on the split-6 hold-out.

## 1. The problem

Laurel Run, neutral factors, F1 to F6 on, `collapse_mode = "bank_wedge"`: peak 348 m³/s at H/9 and 430 m³/s at
H/12 (+23.5 %). With F1 to F6 on, the bank collapse rule moves nothing (all "bank failures" in earlier runs were
towers, now removed by F6). So the remaining grid dependence is in the headcut.

Two tests show what goes wrong.

### 1a. Headcut-check test (isolated scarp)

A single 3 m vertical step, flat bed on both sides, with a steady unit discharge q = 3 m²/s. The headcut law
says the face retreats at R = C (q H)^(1/3) = 0.05 × (3 × 3)^(1/3) = 0.105 m/s. In 520 s the face should move
54.5 m.

| Cell size | Retreat in 520 s | Law says |
|---|---|---|
| 2.13 m (H/6 of Laurel Run) | 0.6 m | 54.5 m |
| 1.42 m (H/9) | 1.8 m | 54.5 m |
| 1.07 m (H/12) | 1.9 m | 54.5 m |
| 0.50 m | 4.6 m | 54.5 m |
| 0.25 m | 9.8 m | 54.5 m |

The rule under-retreats by a factor of 6 to 90, and it depends on the cell size.

### 1b. Headcut log (Laurel Run diagnostic)

The headcut log tracks every scarp on the breach axis. The only scarp it finds is the entire downstream face of the
dam: 12.4 m high, 18 to 29 cells long.

- The face slope starts at about 0.40 (a 1V:2.5H downstream slope).
- The flow erodes the toe and steepens the face.
- The rule's threshold is 0.5 (from CAL2_AMENDMENT_1). Before the slope reaches 0.5, the rule does nothing.
- H/12 reaches slope 0.5 about 300 s before H/9 does. That 300 s sets the difference in when the crest is breached.
- Once the rule acts, it holds the face near a slope of 0.5, switching on and off in about 10 to 17 % of the samples.

## 2. The physical picture

A headcut is a near-vertical step in the bed. Water falls over the brink and lands at the base. The plunge erodes
the foot of the step, the overhanging lip collapses, and the step retreats upstream.

Three things make a headcut different from a sloping channel:

1. **The drop is local.** One or two cells, not the whole dam face.
2. **The water falls freely.** It leaves the brink and does not press on the face.
3. **The retreat is in metres, not in bed levels.** The scarp moves back as a feature; it does not diffuse.

## 3. The two faults

### Fault 1: the rule treats a whole dam face as one headcut

The engine finds a scarp like this: starting from the downstream end, it collects a "run" of consecutive drops
whose cell-to-cell slope is at least `headcut_seg_slope` (0.1). It then checks whether the overall slope
(total height / total length) is at least `headcut_min_slope` (0.5).

On Laurel Run, the downstream face is about 12.4 m high and its natural slope is 1V:2.5H, which is about 0.40.
Every cell-to-cell drop on the face exceeds 0.1, so the whole face is one run. But 0.40 < 0.5, so the rule does
not act until the toe is eroded enough to steepen the average to 0.5.

A real headcut does not wait for the average slope of a 12 m face to reach a threshold. It acts on a local
near-vertical step of a few metres or less.

### Fault 2: the upwind shift smears the face

When the rule acts, it "retreats" the scarp by shifting bed values between neighbouring cells (an upwind finite-
difference shift). This has two consequences:

1. **The face is smeared across more cells at each step.** A vertical step becomes a slope, which then falls below
   the 0.5 threshold, and the rule stops. That is why the rule holds the face near slope 0.5 instead of retreating
   it at the law's rate.
2. **The amount moved per step depends on the cell size.** A one-cell shift at 2.13 m cells moves 2.13 m of face
   in one go; at 0.25 m cells it moves 0.25 m. But the smearing also makes the face milder faster on the coarser
   grid. The two effects compete, and neither gives the right answer.

Together: the rule acts on too large a feature, at the wrong rate, and stops itself by destroying the feature it
is meant to move.

## 4. Why the threshold cannot simply be lowered

CAL2_AMENDMENT_1 raised `headcut_min_slope` from 0.1 to 0.5 because at 0.1 the rule treated every dam face as a
headcut from the start. Lowering it back would reintroduce that problem on every dam.

The threshold is not the disease. The disease is that the rule finds one long run where there is no local step,
and then smears whatever step it makes.

## 5. Proposal

Two changes. Both are options; the defaults reproduce V3.3 bit for bit.

### Change A: find local headcuts, not whole-face averages

**Current rule:** a run of drops each steeper than 0.1, with an overall slope ≥ 0.5.

**Proposed rule:** a headcut is a short, steep segment at the downstream end of a run of drops. Walk upstream
from the foot of the run. Add each cell-to-cell drop to a candidate scarp as long as the cell-to-cell slope is
at least `headcut_face_slope` (default 1.0, i.e. 45°). Stop at the first drop that is flatter.

The scarp's height H_s is the sum of the steep drops collected. Its length L_s is (n − 1) × cell size (the same
convention as F5: a single drop is a vertical wall). The scarp is active when:

- H_s ≥ some minimum height (proposed: `headcut_min_height`, default 0.3 m, same as the current minimum);
- the foot of the scarp is wet and there is flow (q > 0);
- F2 free-overfall check: tailwater is below the scarp top.

**Why this helps.** On a smooth 1V:2.5H slope no cell-to-cell drop reaches slope 1.0, so no headcut is found.
The rule acts only when there is an actual near-vertical step, which is what it is meant to model.

**Why 1.0.** A headcut is a near-vertical or overhanging feature. A threshold of 1.0 (45°) is the lowest slope
that could reasonably be called a headcut. A cell pair at slope 1.0 with cell size ds has a step of ds metres,
which is a real step on any grid. The current 0.1 picks up 6° slopes.

**No change to the segment collection itself.** The run of drops (slope ≥ 0.1) is still collected to give context
(the face above and below the headcut). Only the part that counts as the active scarp changes.

### Change B: retreat by volume, not by upwind shift

**Current rule:** the bed in each cell of the scarp is shifted one cell upstream: Z[i] = Z[i+1] (or the upwind
equivalent), scaled by f = R × dt / ds. This is a finite-difference advection that smears the face.

**Proposed rule:** the retreat is applied as a volume removal from the brink cell and a volume addition at the
foot.

1. The law gives a retreat rate R = C (q H_s)^(1/3) in m/s, where q is the unit discharge at the brink.
2. In one morph step dt, the face retreats R × dt metres.
3. The volume eroded is R × dt × H_s × cell width (m³). This is the rectangular slab behind the face that the
   retreat uncovers.
4. That volume is removed from the brink cell (the top of the scarp). If the brink cell does not hold enough bed
   above the scarp base, the remainder comes from the next cell upstream, and so on.
5. The same volume is added to the foot cell as sediment. In the flow it enters the sediment store (as the engine
   does for collapsed soil); dry, it goes onto the bed.
6. The brink cell's bed drops. If it drops to the level of the cell behind it, the headcut has retreated past
   one cell. The next cell becomes the new brink, and the scarp is one cell shorter at the foot (its base has
   risen by the deposited volume).

**Why this helps.** The face is not smeared. The brink cell drops and the foot cell rises. The face stays steep
because only the brink is cut, not a band of cells. The retreat rate is R m/s regardless of cell size, because
the volume is R × dt × H_s × dw, and the brink cell receives exactly that volume. The face does not destroy
itself.

**Worked example.** A 3 m vertical step, q = 3 m²/s, ds = 1.42 m, dw = 1.42 m, dt = 0.64 s (one morph step).

- R = 0.05 × (3 × 3)^(1/3) = 0.105 m/s.
- Retreat in one step: 0.105 × 0.64 = 0.067 m.
- Volume eroded: 0.067 × 3.0 × 1.42 = 0.286 m³.
- The brink cell (1.42 × 1.42 m plan area) drops by 0.286 / (1.42 × 1.42) = 0.142 m.
- The foot cell rises by 0.142 m.
- After 0.067 / 1.42 ≈ 21 morph steps the brink cell is cut through and the scarp has moved one cell upstream.
- After 520 s the face has retreated 0.105 × 520 = 54.6 m, matching the law, on every grid.

With ds = 2.13 m: the same volume per step (the cell is wider, but the drop per step is smaller by the same
factor because the plan area is larger). The brink cell takes longer to cut through, but the face retreats at
the same rate.

## 6. What does not change

- The headcut law R = C (q H)^(1/3), the coefficient C = 0.05, and the exponent 1/3.
- The F2 free-overfall check (tailwater below the scarp top).
- The segment collection (a run of drops steeper than 0.1). Only how the active scarp is extracted from it changes.
- Non-cohesive and cohesive bank collapse (F4, F5). Those are gravity-driven; the headcut is flow-driven.
- Default behaviour: both changes are options; the defaults reproduce V3.3 bit for bit.

## 7. Known limits (stated before any run)

1. **The face slope threshold (1.0) is a parameter.** A sensitivity test at 0.75 and 1.5 should be run after the
   main check, not before.
2. **The volume removal cuts from the brink cell only.** If the brink cell is very thin (e.g. a sliver at the
   edge of the step), one morph step may cut through it entirely, and the excess volume must spill to the next
   cell. The code must handle this without losing mass.
3. **The deposit at the foot is dumped in one cell.** For a tall headcut and a fast retreat this could build a
   column (the same problem as F5's first draft). If this happens in practice, the deposit should be spread as a
   talus at the friction angle, as F5 does for bank collapse. We will check the first runs before adding this.
4. **Headcuts are found along x and y only**, as with banks. A headcut running diagonally is seen as two shorter
   ones.
5. **The law's coefficient C = 0.05 was set to the current rule's behaviour.** It may need recalibration after
   the rule changes. That belongs to cal-3, not to F7.
6. **Interaction with bank collapse.** A headcut retreat lowers the brink cell, which may expose a bank on a
   cross-section. F5 handles that bank. The two rules run in the same morph step (headcut first, then bank
   collapse), so they see each other's changes within one step.
7. **Only one scarp per grid line.** The rule finds the steepest segment at the downstream end of each run. A
   second headcut further upstream on the same line is not modelled. This matches the current rule.

## 8. How it will be checked

Unit tests (NumPy and Numba), before any dam run:

1. **Smooth slope.** A 1V:2.5H face (the Laurel Run downstream slope): no headcut found. The current rule
   finds the whole face.
2. **Vertical step.** A 3 m vertical step with q = 3 m²/s, cells of 2.13 / 1.42 / 1.07 / 0.5 m: retreat in
   520 s within 5 % of the law (54.5 m) on every grid.
3. **Step on a slope.** A 2 m vertical step sitting on top of a 1V:3H slope: only the 2 m step is the headcut,
   not the slope below it.
4. **No flow, dry foot, tailwater above top.** Each suppresses the headcut (as now).
5. **Mass conservation.** Volume removed from the brink equals volume added at the foot, to round-off.
6. **Brink cut-through.** A 1 m step at 0.5 m cells with a high retreat rate: the brink cell is cut through in
   one step and the excess goes to the next cell. No mass lost.
7. **Default off = V3.3 bit for bit; Numba kernel = NumPy.**

Then the dam runs:

- Laurel Run at H/6, H/9, H/12 with F1 to F7. Target: peak within 10 % between H/9 and H/12.
- Castlewood re-run to confirm F7 does not change the non-cohesive case (Castlewood has no headcut in the
  current calibration).
- Compare the headcut log before and after: the log should show a local scarp of a few metres, not a 12 m
  whole-face average.

## 9. Decisions

None yet. The note is for discussion before any code is written.

### Questions for the user

1. **Change A (local scarp detection):** is a face slope threshold of 1.0 (45°) reasonable, or should it be
   steeper (e.g. 2.0, which is 63°)?
2. **Change B (volume retreat):** the deposit goes to the foot cell. Should we spread it as a talus (as F5 does)
   from the start, or try the simple version first and add talus if needed?
3. **Interaction order:** headcut first, then bank collapse. Any concern?
