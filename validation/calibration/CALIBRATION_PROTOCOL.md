# Calibration protocol (stage 3), including leave-one-out (written 2026-11-01, before any calibration run)

## Factors calibrated (global, one value each, never per case)
- f_kd: multiplier converting jet-test kd to the engine's kd (only cases with measured kd inform it: E1S1, E1S3, E2S2).
- C_h: headcut coefficient (all calibration cases).
- f_t: non-cohesive transport multiplier (Castlewood, South Fork).
Everything else stays at the values written into `cal-1` before the first run (grain shear, transport law per material,
bank method, grid rule, time step, Manning n from the case source or the DLBreach rule).

## Objective
Sum over cases of squared errors in log space: ln(Qp_model/Qp_obs), ln(Tp_model/Tp_obs) (or stage times where Tp is not reported),
and (B_model - B_obs)/B_obs; equal weights, terms missing from a case are left out.
No-breach cases (E1S3): penalty 1 if the model breaches (crest lowered below the notch invert by more than 50 % of the notch depth
within the test duration), 0 otherwise; plus the width term.

## Leave-one-out (LOO)
1. Run the full calibration on all 6 cases -> factor set F_all.
2. For each case i (6 times): calibrate on the other 5 -> F_-i, then run case i with F_-i and record its errors.
3. Report: the range of each factor across the 6 LOO fits, and the held-out errors.
4. Stability rule (fixed now): a factor is "stable" if max/min across LOO fits <= 3; otherwise "unstable".
   An unstable factor is still frozen at F_all, but cal-1 records it as unstable and the Dig Tsho ensemble samples
   the full LOO range for it instead of the calibration spread.
5. Removing one of the three jet-test cases leaves only two to set f_kd; that is expected and is what LOO is meant to expose.

## Freeze
Commit, tag `cal-1`, write factor values, LOO ranges and stability flags to `python/calibration/cal-1.json`.
