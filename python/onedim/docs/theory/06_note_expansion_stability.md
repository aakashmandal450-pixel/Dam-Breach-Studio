# Part 6 — Note: stability of the first wide cell at an expansion (draft 1, 2026-11-28)

*Theory note for review. Context: phase B status §§6–11 (`docs/PHASE_B_STATUS_2026-11-26.md`). No
solver change is proposed until this note is reviewed. All numbers marked "hand" were evaluated by
hand from steady states reported in the logs; the check script (§7) recomputes them from the solver's
own wave speeds.*

## 1. The steady interface state

Cells j − 1 (narrow, area A_n, top width T_n) and j (wide, A_w, T_w), interface j − ½ whose section
is the narrow one (6.13), interface j + ½ wide | wide, flow from j − 1 into j (an expansion). Same bed,
so (6.14a) reduces to a pure width change:

    left state on j − ½:   A*_L = A_n(η_{j−1}),   Q*_L = Q_{j−1}
    right state on j − ½:  A*_R = A_∩(η_j) ≈ A_n,  Q*_R = Q_j          ((6.14a); (6.14) would give Q*_R = Q_j A*_R / A_w)

In steady expansion flow η_j > η_{j−1} (pressure recovery), so the loading closure (6.16b) puts the
receiving cell's left step face at η_f = min(η_j, η_{j−1}) = η_{j−1}. The steady state is correct:
the junction relation and Borda are reproduced (B12a expansions; B12d at CFL 0.1125, §7 of the status).
The failure is dynamic.

## 2. The conservative update of the two cells that carry the mode

The linearised mode (status §§9–11) lives in the discharge of the first wide cell and — measured in
stage rather than area — in the stage of the last narrow cell (M3: the conduit cell's stage runs a
sawtooth). So the minimal model keeps x = δA_{j−1} and y = δQ_j and freezes everything else:

    A_{j−1}^{n+1} = A_{j−1} − r (F^A_{j−½} − F^A_{j−3/2}),      r = Δt/Δs
    Q_j^{n+1}     = Q_j     − r (F^Q_{j+½} − F^Q_{j−½} − W_{j,L} + W_{j,R}),   W = g (I1_cell − I1_∩)(η_f)

## 3. Linearised HLL fluxes

Write the HLL flux (6.18) as F = ½(F_L + F_R) − ½ a₁ (F_R − F_L) + a₂ (U_R − U_L) with, at each
interface, a₁ = (S_R + S_L)/(S_R − S_L), a₂ = S_L S_R/(S_R − S_L) < 0, and the upwind weights
α = S_R/(S_R − S_L) (on the left flux), β = −S_L/(S_R − S_L) (on the right flux), α + β = 1. The wave
speeds are frozen (their derivatives multiply F_R − F_L and U_R − U_L, which are small at the steady
interface). With s_Q = ∂Q*_R/∂Q_j (= 1 for (6.14a), = A*_R/A_w for (6.14)) and U* = Q*_R/A*_R:

    ∂F^A_{j−½}/∂Q_j = β⁻ s_Q                  ∂F^A_{j−½}/∂A_{j−1} = −a₂⁻ = |a₂⁻|
    ∂F^A_{j−3/2}/∂A_{j−1} = a₂⁼                (cell j − 1 is the right state there)
    ∂F^Q_{j−½}/∂Q_j = s_Q (2 β⁻ U* + a₂⁻)      ∂F^Q_{j+½}/∂Q_j = 2 α⁺ U_w − a₂⁺
    ∂(F^Q_{j−½} − W_{j,L})/∂η_{j−1} = g (α⁻ A_n + (A_w − A_n)) = g (A_w − β⁻ A_n)     [face at η_{j−1}]

(superscripts: ⁼ interface j − 3/2, ⁻ interface j − ½, ⁺ interface j + ½). The last line has two parts:
the interface pressure of the left state, α⁻ g A_n, and the step face of the wide cell, g (A_w − A_n),
which (6.16b) loads at the narrow cell's stage. ∂η_{j−1}/∂A_{j−1} = 1/T_n.

## 4. Amplification factor and stability condition

The two-variable map is

    [x]ⁿ⁺¹   [ 1 − r D₁        −r β⁻ s_Q ] [x]ⁿ
    [y]    = [ r P̂ / T_n      1 − r D₂   ] [y]

    D₁ = |a₂⁻| + |a₂⁼|                                  (mass dissipation of the narrow cell)
    D₂ = |a₂⁺| + 2 α⁺ U_w + s_Q (|a₂⁻| − 2 β⁻ U*)        (momentum dissipation of the wide cell)
    P̂  = g (A_w − β⁻ A_n)                               (face + interface pressure of the narrow stage on cell j)

Its eigenvalues satisfy λ² − (2 − r(D₁ + D₂)) λ + det = 0 with

    det = (1 − r D₁)(1 − r D₂) + r² P,      P = β⁻ s_Q g (A_w − β⁻ A_n) / T_n      (feedback gain)

When the pair is complex (it is, in every measured case), |λ|² = det, and the mode grows once det > 1:

    r_crit = Δt_crit / Δs = (D₁ + D₂) / (D₁ D₂ + P)                                    (N.1)

(The real-eigenvalue limit r < 2/max(D₁, D₂) is the ordinary CFL condition and is never the binding one
here.) G = λ is the amplification factor asked for; (N.1) is |G| = 1.

**Hand check against the linearisation** (speeds estimated from the steady states in the logs):

| case | D₁ | D₂ | P | predicted Δt_crit | measured Δt_crit | difference |
|---|---|---|---|---|---|---|
| pressurised → free, conduit 0.2 → 1 m | 50.0 | 25.1 | 1.80e4 | 9.8e-4 s | 1.010e-3 s | −3 % |
| pressurised → pressurised, → 1.0 × 0.55 | 50.0 | 48.8 | 1.62e4 | 1.33e-3 s | 1.362e-3 s | −2 % |
| pressurised → pressurised, → 1.0 × 0.40 | 50.0 | 48.8 | 1.16e4 | 1.76e-3 s | 1.829e-3 s | −4 % |
| free → free, 0.0667 → 1 m | 1.79 | 1.59 | 21.6 | 3.46e-2 s | 3.27e-2 s | +6 % |
| free → free, 0.2 → 1 m | 2.36 | 2.13 | 11.2 | 6.9e-2 s | 7.55e-2 s | −9 % |
| free → free, 2 → 10 m (B12a) | 2.81 | 2.51 | 15.8 | 5.8e-2 s (CFL 0.98) | stable to CFL 1.0 (ρ = 0.999) | marginal, consistent |

The predicted eigenvalue for the conduit outlet at CFL 0.218 is 0.840 + 0.568i (|λ| = 1.014); the
linearisation gave 0.843 + 0.552i (|λ| = 1.008).

## 5. What the condition explains

- **Two separate sources of amplification**, as the reviewer asked: the *geometric* factor
  s_Q (A_w − β A_n) — how much of the wide cell's discharge reaches the narrow cell's mass balance,
  times the face area on which the narrow cell's stage then pushes — and the *wave-speed / storage*
  factor g/T_n set against the dissipation D₁ D₂ ∝ (interface speeds)².
- **The 3.1 relation of status §10.** For a full rectangular conduit T_n = T_s = g A_n / a_s², and
  with U ≪ a_s: D₁ ≈ a_s, D₂ ≈ a_s/2, β⁻ ≈ ½, S_max ≈ a_s, so D₁ + D₂ ≈ 1.5 a_s, D₁ D₂ ≈ a_s²/2 and
  P ≈ ½ a_s² A_w/A_n. (N.1) gives r_crit ≈ 3 / (a_s (1 + A_w/A_n)), i.e.
  CFL_crit = r_crit S_max ≈ 3 / (1 + A_w/A_n) ≈ 3 A_n/A_w. The coefficient follows from the
  dissipation of the two cells (1.5 a_s against a_s²/2); it is not a fit.
- **Independence of a_s**: P ∝ a_s² and D ∝ a_s, so Δt_crit ∝ 1/a_s and CFL_crit is unchanged
  (0.207 vs 0.203, status §9).
- **Why the slot worsens it but is not needed**: the loop exists in free-surface flow too (0.488 at
  A_n/A_w = 0.066, 0.862 at 0.2). In the slot the narrow cell is at very low Froude number
  (U/a_s ≈ 0.025), so β⁻ → ½ and the gain P takes its largest value relative to D₁ D₂. In the
  free-surface 0.0667 m channel (Fr ≈ 0.5) the flow speed skews the waves: β⁻ ≈ 0.25 halves P, and
  S_max = U + c exceeds c, so the same area ratio gives a larger critical CFL.
- **Direction.** In a contraction the wide cell is upstream and loses mass at the narrow interface; by
  (6.16b) its face is loaded at its own stage, so the narrow cell's stage reaches it only through the
  interface pressure, β g A_n. The A_w term disappears, P is of uniform-channel size, and the step is
  stable (reverse cases, status §10).
- **Why (6.14) was stable but wrong**: s_Q = A_n/A_w cuts P by A_n/A_w, back to uniform-channel size —
  and the same factor is what made its steady junction losses 3–7 × too large (status §2).
- **Why the draft-1 face rule damped it**: loading the face at η_j removes the (A_w − A_n) part of P̂
  — and is what produced energy gains.
- **Grid spacing.** r_crit = Δt/Δs contains no length, so Δt_crit ∝ Δs and **CFL_crit should not
  change with Δs**. The Δs/2 run (status §6: oscillation 0.70 vs 0.74 m) is consistent; the check of
  §7 tests it directly. If confirmed, the defect is a property of the interface update at any
  resolution, not a spatial-accuracy problem that refinement would remove.

## 6. Steady consistency versus perturbation stability: design criterion

The two properties are separate. B12a/B12d test the first; the linearisation tests the second.

The loop has two links: (a) the wide cell's discharge enters the narrow cell's mass balance with
sensitivity β⁻ s_Q; (b) the narrow cell's stage enters the wide cell's momentum through a face of area
A_w − β⁻ A_n. (6.14a) sets (a) to its full value (needed for the steady discharge: requirement 2);
(6.16b) sets (b) to its full value (needed for Borda: requirement 2). Their product, divided by the
narrow cell's storage width T_n, is the gain P.

**Criterion.** A replacement must keep the steady values of both links (requirements 1 and 2) and make
the explicit feedback gain no larger than in a uniform channel of the narrow section,

    P ≤ P_uniform = β g A_n / T_n,   equivalently the stable step of the interface is not smaller than
    the ordinary CFL step,                                                                     (N.2)

for every area ratio, flow regime and Δs (requirements 3 and 4). (6.14) meets (N.2) but breaks
requirement 2; (6.14a) + (6.16b) meets requirement 2 but violates (N.2) by A_w/A_n.

Candidates, judged against requirements 1–4 (none adopted):

| candidate | 1 mass | 2 steady relation | 3 no feedback | 4 all regimes, Δs | remarks |
|---|---|---|---|---|---|
| C1 interface time-step limit from (N.1) (amend 6.21) | ✓ | ✓ | ✓ (by restricting Δt) | ✓ | exact, but Δt ∝ A_n/A_w: 22 × slower at 5 m, 10²–10³ × for breach-scale piping |
| C2 point-implicit coupling of the two links: in the wide cell's face force use the narrow stage predicted at n + 1 from its own mass update (or, equivalently, take Q_j at n + 1 in the narrow cell's mass flux), solved locally for the 2 × 2 block | ✓ (fluxes unchanged in form) | ✓ (at a steady state the predictor equals the current value) | to be shown: the implicit block removes the r² P term from det | to be shown | local; no change to 6-19 or 6.16b at steady state; needs its own amplification factor and an energy check |
| C3 a reduced perturbation sensitivity s_Q < 1 with Q*_R = Q_j in the mean | ✓ | ✓ only if it does not move the steady state | ✓ if s_Q ≤ A_n/A_w | — | requires a free parameter or a split of mean and perturbation; rejected unless it follows from a derivation |
| C4 face stage from the reconstructed interface state instead of the neighbour's stage | ✓ | unknown (Borda depends on the face stage) | partly | — | the draft-1 rule (η_f = η_j) is the extreme case and gained energy |

C2 is the only candidate that targets the loop itself without changing either steady link; it is
proposed for derivation in the next draft, not for implementation.

## 7. Verification matrix (before any implementation)

Check script `onedim/verification/b12d_theory_check.py` (`run_b12d_theory_check.ps1`):

| test | cases | pass condition |
|---|---|---|
| V1 prediction | the six expansion cases, four sweep cases (0.3 m, 2 m, h 0.4, h 1.0) | Δt_crit from (N.1), with the solver's own S_L, S_R, U, A, T at the steady state, within 10 % of the linearised Δt_crit |
| V2 grid spacing | conduit → 1 m and free 0.0667 → 1 m at Δs = 0.5, 0.25, 0.125 m (same 20 m reaches) | linearised CFL_crit unchanged within 5 %; (N.1) tracks it |
| V3 direction | reverse cases 0.3, 1, 5 m | (N.1) with the contraction loading predicts no instability below the ordinary CFL |
| V4 reconstruction | conduit → 1 m with (6.14) | (N.1) with s_Q = A_n/A_w predicts stability to CFL 1 |

For a candidate (after review): its own amplification factor; the linearisation at CFL 0.9 for every
case above (ρ ≤ 1); B12a (expansions within 1 % of the relation, 3 % of Borda), B12d submerged (steady,
relation and Borda within 1 %), B12c refinement gates, B1 lake at rest, B13; and a full phase B run.

## 8. Open points

- The two-variable model neglects Q_{j−1} and A_j; their share in the measured modes is small
  (≤ 0.18 in Q, 1–25 % in A), and V1 measures the resulting error.
- The wave speeds are frozen; this is exact at a uniform steady state and approximate at the junction.
- Nothing here concerns contractions (6-16): they are stable and their loss is a separate question.
