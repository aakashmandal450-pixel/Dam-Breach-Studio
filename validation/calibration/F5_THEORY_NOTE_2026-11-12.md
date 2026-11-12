# F5 theory note (2026-11-12): cohesive bank failure that does not depend on the cell size

Status: built as an option and unit-tested; dam runs pending (section 9). Seen cases only (Laurel Run, Castlewood); any fix must be
pre-registered and tested on the split-6 hold-out.

## 1. The problem

Laurel Run (cohesive), neutral factors, F1 to F4 on: peak 401 m3/s at H/9 and 512 m3/s at H/12 (+28 %). With bank
collapse switched off: 389 and 391 m3/s (+0.6 %). The cohesive bank-collapse rule carries the grid dependence
(`runs/v34_isolation_laurel/`).

## 2. The physical law (unchanged)

Culmann planar-wedge failure. A bank of height H and face angle beta, in soil with cohesion c, friction angle phi and
unit weight gamma, stands up to the critical height

    Hc(beta) = 4 c sin(beta) cos(phi) / ( gamma (1 - cos(beta - phi)) )        for beta > phi

- A bank flatter than phi never fails by this law.
- The bank fails when H > Hc(beta). The soil slides on a plane through the toe at the angle

      alpha = (beta + phi) / 2

- After the failure the bank face is that plane.

Laurel Run values: c = 25 kPa, tan(phi) = 0.55 (phi = 28.8 deg), gamma = 20.3 kN/m3 (the engine's saturated unit
weight: grain density 2,650 kg/m3, porosity 0.35).

| Bank angle beta | Critical height Hc |
|---|---|
| 90 deg (vertical) | 8.3 m |
| 80 deg | 11.4 m |
| 70 deg | 16.4 m |
| 60 deg | 25.8 m |

## 3. What the engine does now, and why it depends on the cell size

The engine applies the law to each pair of neighbouring cells:

- height = the step between the two cells;
- angle = atan(step / cell size).

Three faults follow.

1. **The angle contains the cell size.** A vertical wall is read as 82 deg at H/9 (1.42 m cells) and 84 deg at H/12
   (1.07 m cells). It fails at 10.5 m on the medium grid and 10.0 m on the fine grid. The law says 8.3 m.
2. **A bank spread over two or more cells is never seen as one bank.** A 12 m bank over two cells is two 6 m steps,
   and neither fails.
3. **The amount that falls is a numerical recipe.** A failing pair moves half of its excess height to the lower cell
   per pass. That is not the Culmann wedge, and its size depends on the cell size.

(An earlier message gave 11.6 / 11.1 / 9.6 m for fault 1. Those used an assumed unit weight of 18 kN/m3; the values
here use the engine's 20.3 kN/m3.)

## 4. Why measuring the whole bank is not enough on its own

The first idea was F5a = measure the whole bank, keep the rest. Working it through shows this cannot be separated
from how the failed soil is moved.

Example: a vertical wall 9 m high. The law says it fails (9 > 8.3 m). After the failure the top of the bank has
moved back by H / tan(alpha) = 5.3 m. If instead the bank only needed to move back 0.6 m, that is less than one cell,
and a rule that moves soil cell by cell cannot do it. The old cell-size dependence comes back through the action.

So the trigger and the action must both be written in real quantities: a height and an angle for the trigger, a
volume of soil for the action. The lateral-erosion law in the engine already works this way (a wall retreat in metres
is turned into a volume).

## 5. Proposal

**Step 1. Find each bank.** Along x and along y, in both directions, a bank is a run of consecutive cell-to-cell
drops that are each steeper than tan(phi). This is how the scarp headcut (C1) finds scarps. The threshold is phi
because the law says flatter ground is always stable; no new parameter.

**Step 2. Measure it as one bank.**

- Height H_b = the sum of the drops in the run (toe to top).
- Horizontal length L_b = (n - 1) x cell size, where n is the number of drops.
- Angle beta_b = atan(H_b / L_b); 90 deg when n = 1.

Reason for (n - 1): the stored bed is flat inside each cell with vertical faces between cells. A run of n drops has
n - 1 cells on the face, so the face is (n - 1) cells long. A single step is a vertical wall on every grid. For a
sloping bank the length is known to within one cell, and the error shrinks as the cells get smaller.

**Step 3. Test it.** Factor of safety FS = Hc(beta_b) / H_b. The bank fails when FS < `bank_fs_trigger` (1.0, as now).
The existing dry / submerged friction-angle rule is kept, applied to the bank's top and toe cells.

**Step 4. Remove the Culmann wedge.** The failure plane starts at the toe of the bank (the cell face at the foot of
the run) and rises at alpha = (beta_b + phi) / 2. Every cell behind the face is cut down to that plane. The cut
volume is computed from the cells, so nothing is lost.

**Step 5. Lay the soil down as a talus at the toe.** The fallen soil forms a heap that leans against the new face
and falls away from it at the friction angle phi. Its size is set so that it holds exactly the cut volume. In each
cell the soil goes onto the bed if the cell is dry and into its sediment store if it is wet, as the engine does now
with collapsed soil. Solids are conserved exactly.

Change from the first draft: the draft put all the soil in the one toe cell. That is 23.9 m3 per metre into a cell
1.42 m wide, a column 16.8 m high, taller than the bank itself. The talus avoids this and adds no parameter.

**Step 6. Repeat until no bank fails.** One failure can expose another bank. Within one morph step the engine
sweeps the four directions again and again until a full sweep moves nothing. `collapse_max_passes` is a safety cap
only, and the sweeps used and the cap hits are counted (as F4 does). One bank per grid line fails per sweep; the
others wait for the next sweep, so each is measured on the current bed.

Worked example, the 9 m vertical wall: alpha = 59.4 deg; the top moves back 5.3 m; 23.9 m3 of soil falls per metre of
bank; the new face (59.4 deg) can stand 26.6 m, so it is stable. These numbers are the same on every grid. Only the
position of the toe is rounded to a cell face.

## 6. What does not change

- The Culmann law, c, phi, gamma and the trigger value.
- Non-cohesive soil (c = 0): F4, collapse to the repose angle. For c = 0 the law reduces to "steeper than phi fails".
- Default behaviour: F5 is an option (proposed name `collapse_mode = "bank_wedge"`); the defaults reproduce V3.3.
- No Bishop or Spencer, no pore pressure, no tension crack. These stay deferred.

## 7. Known limits (stated before any run)

1. **Sloping banks are measured to within one cell.** Vertical walls are exact.
2. **The toe position is rounded to a cell face.** The error is at most one cell and shrinks with the cell size.
3. **Failures become events.** A wall fails in one block when it passes 8.3 m, instead of shaving off a little each
   step. The time of the first failure can shift the peak. This is physical, but it can make results jumpy.
4. **Banks are found along x and y only.** A bank running diagonally is seen as two shorter banks. The order of the
   four sweeps can matter; the tests must show how much.
5. **The talus becomes ordinary bed.** Once laid down it has the cohesion of the dam soil again, although real
   debris is loose. In wet cells the soil goes to the sediment store, so the flow is not blocked by it.
6. **Culmann ignores tension cracks**, so real banks fail somewhat earlier than 8.3 m. Not addressed here.
7. **Cohesion 25 kPa is an assumed value** (DLBreach) for Laurel Run. F5 makes the rule consistent; it does not make
   the input better.

## 8. How it will be checked

Unit tests (NumPy and Numba), before any dam run:

1. One vertical wall, cells of 2.13 / 1.42 / 1.07 / 0.5 m: it stands at 8.0 m and fails at 8.6 m on every grid.
2. The same wall at 9 m after failure: top retreat 5.3 m and fallen volume 23.9 m3 per metre, within one cell, on
   every grid; face angle 59.4 deg.
3. A 14 m bank spread over 2, 3 and 4 cells: fails (the current rule does not). The test uses 14 m, not the 12 m
   of the first draft: a 12 m bank over 4 cells is 75 deg steep, and a 75 deg bank stands higher than 12 m by the law.
4. A bank flatter than phi, and a bank lower than Hc: nothing moves.
5. Solids conserved to round-off; dry toe and wet toe.
6. c = 0 gives no steeper-than-phi face after the call.
7. Default option off = V3.3 bit for bit; Numba kernel = NumPy.

Sweeps (iterations):

8. One wall settles in one sweep; the second sweep finds nothing to move.
9. A chain (two 9 m walls on one line) stops by itself, and every bank left has a factor of safety of at least 1.
10. The same result with a cap of 50 and of 500; a call that ends at the cap is counted.
11. The sweeps needed do not grow on a finer grid.

Result on 2026-11-12 (`python/tests/v3_4_tests.py`, 15 F5 checks with NumPy, 16 with Numba; all pass, and all
earlier suites still pass):

| Check | Cells 2.13 m | 1.42 m | 1.07 m | 0.5 m |
|---|---|---|---|---|
| 8.0 m wall | stands | stands | stands | stands |
| 8.6 m wall | fails | fails | fails | fails |
| 9 m wall, fallen volume (exact 23.946 m3/m) | 23.946 | 23.946 | 23.946 | 23.946 |
| 9 m wall, top retreat (exact 5.32 m) | 6.13 | 5.07 | 5.60 | 5.25 |
| 9 m wall, sweeps | 2 | 2 | 2 | 2 |
| Two-wall chain, sweeps | - | 3 | 3 | 3 |
| Two-wall chain, fallen volume, m3/m | - | 56.0 | 56.5 | 58.1 |

- A 14 m bank over 2, 3 and 4 cells fails as one bank; the pair rule moves nothing.
- Solids are conserved to 2e-16 (dry and wet toe). The four bank directions give identical results.
- The whole-bank rule runs in NumPy. With the Numba backend on, the call is passed to the NumPy code, so the two
  agree exactly. Failures are rare events, so the cost is small.

Then the dam runs:

- Laurel Run at H/6, H/9, H/12 with F1 to F5. Target: peak within 10 % between H/9 and H/12.
- Recorded besides the peak: time to peak, width, time of the first bank failure, number of failures, fallen volume,
  smallest factor of safety, balance errors, and one saved bed per run (to settle the 154 m width question).
- Castlewood re-run to confirm F5 does not touch the non-cohesive case.

## 9. Decisions

The user asked for the code on 2026-11-12 ("add it to the note, write the code and tests"), so the note was built
as proposed, with one change.

1. **Trigger geometry:** whole bank, with length (n - 1) cells so that a single step is a vertical wall. Built.
2. **Action:** cut to the Culmann failure plane alpha = (beta + phi) / 2, instead of the half-excess recipe. Built.
3. **Debris:** built as a talus at the friction angle (step 5), not "all to the toe cell" as first proposed. This
   still needs the user's confirmation.
4. **Sweeps:** repeat until no bank fails, with a counted safety cap (step 6). Built.

Status: option `collapse_mode = "bank_wedge"`, staged in `_f5/`, launcher `python/run_v34_f5.ps1`. Not committed;
the dam runs are still to do.
