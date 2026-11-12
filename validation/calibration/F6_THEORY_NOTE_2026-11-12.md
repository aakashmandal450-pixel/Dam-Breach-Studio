# F6 theory note (2026-11-12): sediment must move with the water (no sediment into dry cells)

Status: option B approved by the user on 2026-11-12; built as an option and unit-tested (section 9); dam runs
pending. Seen cases only (Laurel Run, Castlewood); any fix must be
pre-registered and tested on the split-6 hold-out.

## 1. The problem

The diagnostic run of 2026-11-12 (`runs/v34_diag_laurel/`, Laurel Run, neutral factors, F1 to F4) saved the bed.
Single cells beside the eroded slot rise far above the dam.

| Run | Highest rise of a cell above the starting bed | Cells risen more than 3 m | Volume in risen cells |
|---|---|---|---|
| bank collapse off, H/9 | 367 m | 15 | 2,808 m3 |
| bank collapse off, H/12 | 468 m | 31 | 3,916 m3 |
| Culmann on cell pairs, H/9 | 9.2 m | 11 | 193 m3 |
| Culmann on cell pairs, H/12 | 9.4 m | 22 | 215 m3 |
| Culmann on whole banks (F5), H/9 | 0.2 m | 0 | 12 m3 |
| Culmann on whole banks (F5), H/12 | 1.9 m | 2 | 28 m3 |

The dam is 12.8 m high. With bank collapse on, the towers do not grow as tall only because the collapse rule knocks
them down: about 10 m with the pair rule, 8.3 m with the whole-bank rule. In the F5 runs the first "bank failures"
(960 s at H/12, 1,523 s at H/9) are single-cell steps of exactly 8.3 m beside the slot, at a place where the dam face
is 2.7 m high, repeating every 60 to 90 s. They are towers falling, not banks.

Solids are conserved throughout, so no balance check sees this.

## 2. The physical principle

Suspended and bed-load sediment is carried by the water. Across any line, the sediment passing per second is

    sediment flux = (water passing per second) x (sediment concentration in that water)

So where no water crosses, no sediment crosses. In particular, sediment cannot enter a cell that water does not
enter.

## 3. What the engine does now

`Morphology._advect` moves the sediment store S between cells. For the face between cell A and cell B it uses

    face discharge = ( q_A + q_B ) / 2          (q = depth x velocity at the cell centres, averaged over the
                                                 morph interval)
    sediment flux  = face discharge x concentration of the upwind cell

The flow solver does not use this face discharge. It computes its own water flux at every face (the HLL flux), and
that flux is zero at a dry bank.

Two faults follow.

1. **Sediment enters dry cells.** Let A be a wet cell beside a dry bank cell B, and let the flow in A have a small
   component toward B (flow turning, or spreading at the toe). Then q_B = 0, but the face discharge is q_A / 2, not
   zero. Sediment is pushed into B although no water goes there.
2. **It cannot leave again.** The concentration in a dry cell is set to zero, so nothing flows out. At the end of
   the morph step, sediment in a dry cell is added to the bed. The cell is now higher, stays dry, and receives more
   in the next step. A tower grows.

There is a second, quieter consequence. The averaged face discharges do not balance the water in each cell, so even
between wet cells the sediment is not moved in step with the water. A uniform concentration does not stay uniform
in a flow that speeds up or slows down.

## 4. Two ways to fix it

**Option A: block the flux into dry cells.** Set the face discharge to zero when the receiving cell is dry.

- Simple: a few lines.
- It does not cure the cause. A cell with a film of water a few millimetres deep counts as wet, receives the same
  wrong flux, and dumps its sediment when the film dries. The towers would form more slowly, through film cells.

**Option B: use the water flux of the flow solver.** In every flow step the solver already computes the water flux
at every face. Add these up over the morph interval and use the mean as the face discharge for the sediment:

    face discharge = sum over the flow steps of ( water flux at the face x time step ) / morph interval
    sediment flux  = face discharge x concentration of the upwind cell

- The sediment moves with exactly the water the solver moved. Where the solver passes no water, no sediment passes.
- The water balance of each cell is satisfied by these discharges, so a uniform concentration stays uniform.
- No new parameter and no threshold.
- More work: the flow solver must hand its face fluxes to the engine (NumPy and Numba), the engine must add them up,
  and the sediment routine (NumPy and Numba) must accept them.

**Recommendation: option B.** It removes the cause and is the standard way to couple sediment to a finite-volume
flow solver.

## 5. Proposal (option B)

1. **Flow solver.** After each step, `Hydrodynamics` keeps the water flux at every x-face and y-face of that step
   (they exist already as `Fh` / `Gh` in both the NumPy and the Numba step).
2. **Engine.** Alongside the time-averaged depth and discharge, the engine adds up face flux x time step over the
   morph interval and divides by the interval.
3. **Sediment routine.** `Morphology._advect` uses these face discharges instead of the cell-centre average. The
   upwind concentration, the positivity limiter and the boundary treatment (clear water in, sediment out) stay as
   they are.
4. **Option name.** `sediment_face_flux = "hydro"`; the default `"centred"` reproduces V3.3 bit for bit.
5. **Unchanged.** Pickup and deposition laws, the adaptation length, the rule that sediment left in a cell that
   dries out goes onto the bed (that is physical: the water left it behind).

## 6. Known limits (stated before any run)

1. **The face discharge is an average over the morph interval** (about 0.6 s for Laurel Run), as the depth and
   velocity already are.
2. **Upwind, first order.** The sediment front is smeared by about one cell, as now.
3. **All transport results change a little**, not only at dry banks, because the face discharges differ wherever
   the flow speeds up or slows down. This is intended, but it means earlier numbers are not comparable one to one.
4. **It does not address the timing of the headcut breaking through the crest**, where H/9 and H/12 part by about
   300 s in the run with collapse off. That is a separate item.
5. **cal-1, cal-2 and stage 4 were run with the old sediment routine.** Those runs saved no beds, so how much the
   towers affected them is unknown.

## 7. How it will be checked

Unit tests (NumPy and Numba), before any dam run:

1. **Dry bank.** A wet cell with flow partly toward a dry neighbour, face water flux zero: no sediment enters the
   dry cell. The current routine moves sediment in (documents the defect).
2. **Uniform flow.** In a uniform steady flow the new routine gives the same result as the current one (to
   round-off), because both face discharges equal q.
3. **Uniform concentration stays uniform.** A steady flow through a contraction, run with the real flow solver,
   starting with the same concentration everywhere: the concentration stays the same everywhere (to round-off) with
   the solver's fluxes, and drifts with the centred average (documents the defect).
4. **Conservation.** The change of sediment in the grid equals what crossed the open boundaries.
5. **No towers in a short breach run.** A small dam with a pilot notch, run for a short time: no cell ends more than
   a few centimetres above its starting bed unless water stood in it.
6. **Default off = V3.3 bit for bit; Numba kernel = NumPy.**

Then the dam runs:

- Repeat the diagnostic run (Laurel Run, H/9 and H/12, three bank variants) with F6. Report the table of section 1
  again: highest rise, cells risen more than 3 m, volume in risen cells.
- Repeat the grid check (Laurel Run and Castlewood, H/6, H/9, H/12) with F1 to F6, with the pair rule and with the
  whole-bank rule. Target: peak within 10 % between H/9 and H/12.
- Castlewood: a time series of the bed, to separate real deposits at the toe from towers.

## 8. Decisions

1. **Option B** (use the flow solver's water flux) instead of option A (block flux into dry cells). Approved by
   the user on 2026-11-12 ("choose option B").
2. **Scope:** only the sediment advection changes; pickup, deposition and the dry-cell settling rule stay. Built
   this way; the user did not comment on it separately.

## 9. Unit-test result (2026-11-12)

Option `sediment_face_flux = "hydro"`; `python/tests/v3_4_tests.py`, 8 F6 checks with NumPy and 9 with Numba. All
pass, and all earlier suites still pass with the default.

| Check | Centred average (V3.3) | Flow solver's flux (F6) |
|---|---|---|
| Sediment entering a dry cell beside a wet one, per step | 1.0e-3 m | 0 |
| Uniform flow, sediment blob | reference | identical |
| Steady flow over a hump: change of a uniform concentration in one 0.02 s step | 3.6e-3 | 4.4e-16 |
| Conservation, relative error | 2.5e-16 | 7.5e-17 |
| Demo dam (3 m), 200 s breach run: highest rise of a cell | 1.92 m (6 cells above 0.3 m) | 0.005 m |
| Demo dam: deepest cut | 2.60 m | 2.64 m |

- The Numba kernel equals the NumPy reference on 20 random fields.
- A coarse Laurel Run trial (H/4, bank collapse off) gave a highest rise of 13.7 m with the centred average and
  0.00 m with F6, at the same run time and with closed balances. This only shows the code runs in a full case.
- Test 5 of section 7 uses the engine's demo dam with a pickup coefficient chosen to make the defect show within
  200 s. It is a test value, not a calibrated one.

Dam runs: launcher `python/run_v34_f6.ps1` (diagnostic variants `*_f6`, grid-check setups `F12346` and `F123456`).
Not committed yet.
