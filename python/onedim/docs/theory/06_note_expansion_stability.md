# Part 6 — Note: stability of the first wide cell at an expansion (draft 2.1, 2026-11-28)

*Theory note for review. Context: phase B status §§6–12 (`docs/PHASE_B_STATUS_2026-11-26.md`). No
solver change is made until this note is reviewed. Draft 2 adds §§9–12: the derivation of candidate C2
(user's preferred candidate, 2026-11-28), its amplification factor, the six required properties, the
four additional analysis checks, and the verification plan; C1 (relaxation) and C3 (local subcycling)
are kept as comparison methods only. Draft 2.1 answers the review of draft 2 (user, 2026-11-28):
§9.3a full two-cell water budget, §9.4a the CFL bound on |a| and |d|, §9.5 fallback for both cells and
the treatment of successive expansions, §10 energy and nonlinear behaviour as acceptance tests, V5b.
The stability proof is for the reduced two-variable model only; C2 is a solver-wide solution only once
the full-system tests of §12 pass. (6.14a) and (6.16b) are not changed while C2 is tested. All numbers
marked "hand" were evaluated by
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
    ∂(F^Q_{j−½} + W_{j,L})/∂η_{j−1} = g (α⁻ A_n + (A_w − A_n)) = g (A_w − β⁻ A_n)     [face at η_{j−1}]

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

## 7a. Results of the verification matrix (user's PC, 2026-11-28, 867 s)

Log: `docs/logs/onedim_b12d_theory_check_20261128_110210.log`. (N.1) evaluated with the solver's own
speeds, areas and widths at each steady state.

| test | result |
|---|---|
| V1 prediction (10 cases) | **pass**: within −9.2 % to +8.9 % of the linearised Δt_crit; six of the ten within 4 % (conduit → 2 m −0.2 %, h 1.0 −0.6 %, conduit → 1 m −1.9 %). The B12a 2 → 10 m case is predicted at CFL 0.99 and measured stable to 1.0 (ρ = 0.999), consistent |
| V2 grid spacing | **pass**: linearised CFL_crit identical at Δs = 0.5, 0.25, 0.125 m (0.2072 and 0.4884, spread 0.0 %); (N.1) identical too. The defect is a property of the interface update, not of resolution |
| V3 direction (contractions) | **pass**: predicted limit CFL ≈ 1.99 (above the ordinary CFL); linearisation stable to 1.0 at 0.3, 1 and 5 m |
| V4 reconstruction (6.14) | **pass**: s_Q = 0.091 cuts P from 1.77e4 to 57.5; predicted stable (the ordinary limit binds, CFL 2.05); linearisation stable to 1.0 |

The largest errors (±9 %) are in the free-surface and the 0.3 m case, where the neglected
neighbours (Q_{j−1}, A_j) carry more of the mode (§8). The note's mechanism is confirmed.

## 8. Open points

- The two-variable model neglects Q_{j−1} and A_j; their share in the measured modes is small
  (≤ 0.18 in Q, 1–25 % in A), and V1 measures the resulting error.
- The wave speeds are frozen; this is exact at a uniform steady state and approximate at the junction.
- Nothing here concerns contractions (6-16): they are stable and their loss is a separate question.


---

# Draft 2

## 9. Candidate C2: locally implicit coupling at an expansion interface

Naming from draft 2 on (user, 2026-11-28): **C2** locally implicit coupling (this section); **C1**
interface-flux relaxation and **C3** local subcycling of the two cells, both comparison methods only.
The draft-1 table of §6 used C1 for the (N.1) time-step limit and C3 for a reduced sensitivity s_Q;
those two are not pursued.

### 9.1 Where it applies

At an interface j − ½ where, in the current step, (6.16b) loads the receiving cell's step face at the
neighbour's stage: mass flux enters cell j (F^A_{j−½} > 0 for flow to the right), η_{j−1} < η_j, and the
interface section is narrower than cell j (A_j(η) > A_∩(η)). These are exactly the interfaces where the
feedback gain P of §4 carries the factor A_w − β A_n. Elsewhere (contractions, uniform reaches, bed steps
without a width change, dry or near-dry cells: h ≤ h_C2, §9.5) the update is the present explicit one.
For flow to the left the roles of the two cells are mirrored.

### 9.2 The two coupling terms and their implicit form

The loop of §4 has exactly two links. In the explicit update both are evaluated at time n:

    link a (narrow cell's mass):    the part β⁻ s_Q Q_j of F^A_{j−½}, which depends on the wide cell's discharge
    link b (wide cell's momentum):  the part P̂ η_{j−1} of F^Q_{j−½} + W_{j,L}, which depends on the narrow
                                    cell's stage; P̂ = g(α⁻ A_∩ + (A_j − A_∩)) at η_f = η_{j−1}

C2 evaluates both links at n + 1 and leaves every other term explicit. With the explicit increments
ΔA^E = A^E_{j−1} − Aⁿ_{j−1} and ΔQ^E = Q^E_j − Qⁿ_j from the present scheme (6.12), and
ΔA = A^{n+1}_{j−1} − Aⁿ_{j−1}, ΔQ = Q^{n+1}_j − Qⁿ_j:

    ΔA = ΔA^E − r β⁻ s_Q ΔQ
    ΔQ = ΔQ^E + (r P̂ / T_n) ΔA

a 2 × 2 linear system per interface, solved in closed form:

    ΔQ = (ΔQ^E + (r P̂/T_n) ΔA^E) / (1 + r² P),     ΔA = ΔA^E − r β⁻ s_Q ΔQ,      P = β⁻ s_Q P̂ / T_n     (C2.1)

The coefficients β⁻, s_Q, P̂ and T_n are those of §4, evaluated at time n from the same quantities the
flux uses; they are the derivatives of the update, not tuning parameters. The block is linearised about
time n (one Newton step), so no iteration is needed.

### 9.3 Conservative form

The two corrections are written as corrections to the shared interface fluxes, applied with opposite
signs to both cells, so the scheme stays conservative:

    F^{A,C2}_{j−½} = F^A_{j−½} + β⁻ s_Q ΔQ                        (used by cells j − 1 and j)
    F^{Q,C2}_{j−½} = F^Q_{j−½} + α⁻ g A_∩ Δη_{j−1}                 (interface pressure part; used by both cells)
    W^{C2}_{j,L}   = W_{j,L}   + g (A_j − A_∩) Δη_{j−1}             (step-face part; cell j only, as W itself)

with Δη_{j−1} = ΔA / T_n. Sign convention as in the solver: cell j receives F^Q_{j−½} + W_{j,L} through
its left face (§2), so both momentum corrections raise Q_j when the narrow stage rises. Water: whatever the narrow cell loses through F^{A,C2} the wide cell gains, so
the water budget (6.33) is exact. Momentum: the interface part is shared; the step-face part is a wall
force, as in the present scheme, and is not a flux. The wide cell's mass update and the narrow cell's
momentum update receive the shared corrections too; they are outside the two-variable block, so their
effect on stability is measured, not assumed (§12).

### 9.3a The complete two-cell water budget

All corrections are made to interface fluxes before any cell is updated; each cell is then updated once
with (6.12). For the two cells of the block:

    A^{n+1}_{j−1} Δs_{j−1} = Aⁿ_{j−1} Δs_{j−1} − Δt ( F^{A,C2}_{j−½} − F^A_{j−3/2} )
    A^{n+1}_j     Δs_j     = Aⁿ_j     Δs_j     + Δt ( F^{A,C2}_{j−½} − F^A_{j+½} )

with F^{A,C2}_{j−½} = F^A_{j−½} + β⁻ s_Q ΔQ. Adding the two:

    (A^{n+1}_{j−1} − Aⁿ_{j−1}) Δs_{j−1} + (A^{n+1}_j − Aⁿ_j) Δs_j = Δt ( F^A_{j−3/2} − F^A_{j+½} )

The correction cancels exactly; the two-cell volume changes only through the outer, unmodified fluxes,
and the global budget (6.33) is the same sum as for the explicit scheme. The ΔA of (C2.1) is, by
construction, the narrow cell's update with F^{A,C2}; the wide cell's mass receives the same correction
with the opposite sign (outside the reduced model). The suspended-solids flux uses the corrected mass
flux, F^{C,C2}_{j−½} = F^{A,C2}_{j−½} C_up (6.20), so the solids budget (6.34) is exact in the same way.
Momentum: F^{Q,C2}_{j−½} is shared by both cells; the step-face correction acts on cell j only, as W does
in the present scheme.

### 9.4 Amplification factor

With the two-variable model of §4 (x = δA_{j−1}, y = δQ_j, a = 1 − r D₁, d = 1 − r D₂):

    [1     r β⁻ s_Q] [x]ⁿ⁺¹   [a  0] [x]ⁿ                     1        [ a      −r β⁻ s_Q d ]
    [−rP̂/T_n   1  ] [y]    = [0  d] [y]      ⇒   G_C2 = ————————— [                     ]
                                                             1 + r²P   [ a rP̂/T_n     d     ]

    det G_C2 = a d / (1 + r² P),        tr G_C2 = (a + d) / (1 + r² P)                                  (C2.2)

For a real 2 × 2 map, |λ| < 1 for both eigenvalues if and only if |det| < 1 and |tr| < 1 + det (Jury).
With |a| ≤ 1 and |d| ≤ 1:

- |det| = |a d| / (1 + r²P) < 1 for P > 0 (and = |ad| ≤ 1 at P = 0);
- 1 + det − tr = ((1 − a)(1 − d) + r²P) / (1 + r²P) > 0, and 1 + det + tr = ((1 + a)(1 + d) + r²P) / (1 + r²P) > 0.

So **G_C2 is stable for every feedback gain P ≥ 0 whenever |1 − r D₁| ≤ 1 and |1 − r D₂| ≤ 1**, i.e. under
the ordinary CFL condition r ≤ 2 / max(D₁, D₂) alone. The area-ratio restriction of (N.1) disappears. For
comparison, the explicit scheme has det = a d + r²P (§4), and the simpler sequential (Gauss–Seidel)
variant — taking the narrow stage predicted from its new mass but keeping Q_j at n in link a — has
det = a d and tr = a + d − r²P, which is unstable once r²P > (1 + a)(1 + d), i.e. CFL ≈ 0.60 for the
conduit outlet (hand: 6.25 c² + 2.93 c − 4 = 0) and lower for larger area ratios: it is not sufficient,
and is not proposed.

### 9.4a Does the solver's CFL condition guarantee |a| ≤ 1 and |d| ≤ 1?

At an interface with S_L < 0 < S_R, |a₂| = |S_L| S_R / (S_R − S_L) ≤ ½ max(|S_L|, S_R). The solver's step
(6.21) satisfies r ≤ CFL / S_max with S_max the largest |S| over all interfaces. Hence:

- **a**: r D₁ = r (|a₂⁻| + |a₂⁼|) ≤ CFL, so 0 ≤ r D₁ ≤ 0.9 and a = 1 − r D₁ ∈ [0.1, 1]. Guaranteed.
- **d**: write D₂ = α⁺ (2 U_w − S_L⁺) + s_Q β⁻ (S_R⁻ − 2 U*), using |a₂⁺| = −α⁺ S_L⁺ and |a₂⁻| = β⁻ S_R⁻.
  *Upper bound*: the first term is ≤ α⁺ S_R⁺ ≤ S_max whenever 2 U_w − S_L⁺ ≤ S_R⁺, which holds when the
  Einfeldt speeds bracket U_w ± c_w symmetrically (S_L⁺ ≈ U_w − c_w, S_R⁺ ≈ U_w + c_w); the second term is
  ≤ β⁻ S_R⁻ ≤ ½ S_max. So r D₂ ≤ 1.5 CFL = 1.35 < 2 and d ≥ −0.35. *Lower bound*: D₂ ≥ 0 requires
  S_R⁻ ≥ 2 U* in the second term, i.e. roughly that the wide cell's state reconstructed on the narrow
  interface is subcritical (U* ≤ c*), since S_R⁻ ≥ U* + c*. If U* > c* there, d may exceed 1 — the explicit
  wide-cell momentum update is then itself anti-dissipative, independently of C2.
- So the CFL condition guarantees |a| ≤ 1 always, and |d| ≤ 1 for subcritical reconstructed states with
  near-symmetric wave-speed estimates. It is **not** a guarantee for every configuration. C2 therefore
  computes a and d at each eligible interface in each step (they are by-products of the flux) and is
  applied only where |a| ≤ 1 and |d| ≤ 1; elsewhere the interface stays explicit and the event is
  counted. In the ten measured cases a ∈ [0.12, 0.57] and d ∈ [0.14, 0.62] at CFL 0.9 (from the D₁, D₂
  and Δt of §7a). For supercritical flow into the wide cell (S_L⁻ ≥ 0) β⁻ = 0, so P = 0 and C2 is
  inactive: there is no loop.

For the conduit → 1 m outlet at CFL 0.9 (r = 0.9/51.3 s m⁻¹, D₁ = 50.0, D₂ = 25.1, P = 1.77e4, hand):
a = 0.123, d = 0.560, r²P = 5.45, so det = 0.0107 and tr = 0.106: |λ| ≈ 0.10, against 2.31 for the
explicit scheme.

### 9.5 Limits of the closed form

- Near dry: T_n → small free-surface width or A_∩ → 0 makes the coefficients ill-defined; C2 is not
  applied when either cell has h ≤ h_C2 = 10 h_dry, or when the face rule does not use the neighbour's
  stage (§9.1). Positivity there rests on the explicit scheme as now.
- Positivity elsewhere: before the update, the corrected fluxes of each block are checked against both
  cells that share them: A^{n+1}_{j−1} ≥ A_dry and A^{n+1}_j ≥ A_dry, with all corrections that touch those
  cells included. If either fails, **the whole block reverts to the explicit fluxes for both cells**
  (F^A, F^Q and W of that interface together); a correction is never applied to one cell of a shared
  flux only. The event is counted; it is expected to be zero in the tests.
- Slot state: η_{j−1} is recomputed from A^{n+1}_{j−1} by the section inverse, so a pressurised cell stays
  on its slot branch or crosses the crown consistently; T_n is the width at time n (§10, property 6).
- Successive expansions: a cell can be the wide cell of one block and the narrow cell of the next, so the
  blocks overlap. A one-pass treatment (blocks solved independently from the explicit increments, or in
  sequence along the flow) may not be adequate. Two forms are tested in V13: (i) independent blocks; (ii)
  a coupled solve of the whole chain of consecutive eligible interfaces — each cell carries at most two
  links, so the chain is a block-tridiagonal system of size 2 × (number of cells in the chain), solved
  directly at O(n) cost. (ii) is adopted if (i) fails V13; the choice is reported, not assumed.

## 10. The six required properties

| property (user, 2026-11-28) | status in this draft |
|---|---|
| 1 steady-state preservation | **proved**: at a steady state ΔA^E = ΔQ^E = 0, so (C2.1) gives ΔA = ΔQ = 0 and every correction in §9.3 vanishes; B12a/B12d steady results are unchanged by construction. Tested (V8 null test) |
| 2 conservation | **proved for water** (the correction is a shared interface flux, §9.3); momentum: shared interface part, step-face part a wall force as now. Tested to round-off (V6) |
| 3 stability | **proved for the two-variable model** under the ordinary CFL (§9.4); the full system is tested by linearisation at CFL 0.9 for all ten N.1 cases, both directions, three grid spacings (V9–V11) |
| 4 consistency | **proved**: the corrections are r β s_Q ΔQ and r P̂ ΔA/T_n with ΔQ, ΔA = O(Δt), i.e. O(Δt²) per step; the scheme stays first order and tends to the 6-19 update as Δt → 0. Tested by a Δt series at fixed Δs (V12) |
| 5 energy behaviour | **not proved**; the largest open physical question. C2 damps the coupled mode, which is desirable only if the mode is numerical. Acceptance (not diagnostic) tests V7 and V14 separate interface-flux work, step-face work, and the physical expansion loss, and require the latter to keep its Borda value (§11) |
| 6 positivity, valid slot state | by the limits of §9.5 (fallback of the whole block, counted); tested on B9, B13 and the near-dry B12d free outlet (V14) |

The proofs of properties 1–4 are for the reduced two-variable block. The full system adds the
neighbouring cells, the shared momentum correction, section transitions and overlapping blocks; C2 is
called a solver-wide solution only after V5–V14 pass.

## 11. Additional analysis checks (user, 2026-11-28)

Applied to the present explicit scheme (to characterise the failure) and to C2 (to accept it):

- **V5 nonlinear amplitude**: start the conduit → 1 m and free 0.0667 → 1 m cases from the steady state
  plus the computed unstable eigenvector scaled to 10⁻⁶, 10⁻³ and 10⁻¹ of the local state; run 2000 steps
  at CFL 0.9 and at 0.9 × the (N.1) limit; report the growth rate against |λ| and the saturated amplitude.
- **V5b physical disturbances** (not along the eigenvector): from the converged steady states of the
  conduit → 1 m and free 0.0667 → 1 m cases, (1) a 10 % step in the inflow discharge, (2) a 5 cm step in
  the tailwater stage, (3) a local stage bump of 2 cm in the last narrow cell. Run C2 at CFL 0.9 and the
  explicit scheme at a stable step (CFL 0.1 for the free case; 0.1 × the (N.1) limit for the conduit),
  over 200 s. Track the oscillation amplitude in the two block cells, total energy, water budget, and the
  final steady state. Pass: no growing oscillation; the final steady states agree to 10⁻⁶ relative; the
  transient difference falls with Δt (first order, by V12).
- **V6 conservation under the unstable mode**: water and solids budgets (6.33)–(6.34) per step during V5;
  the mode must redistribute, not create, water (|δ_w| < 10⁻¹²).
- **V7 energy decomposition (acceptance test)**: per step and per cell around the junction, the change
  of E = ∫(g η + U²/2) A ds split into three parts: (i) interface-flux work, the energy transferred through
  the shared interfaces; (ii) step-face work, the work of the pressure on the unshared face; (iii) the
  physical expansion loss, the steady head change across the junction times ρ g Q. Pass: (a) at the
  steady state, (iii) agrees with Borda and the junction relation within 1 % for C2 at CFL 0.9 and for the
  explicit scheme at a stable step; (b) in a closed, frictionless, sloshing reach containing an expansion
  (no inflow or outflow), total energy with C2 at CFL 0.9 never increases from one step to the next by
  more than 10⁻¹² relative, and its decay rate agrees with the C3 reference within 20 %; (c) for the
  unstable mode of the explicit scheme, report which of (i) or (ii) supplies the energy.
- **V8 steady-state null test**: one step of C2 from the converged steady states of all ten N.1 cases:
  max |correction| / |flux| below 10⁻¹².

The two-variable model neglects the neighbours Q_{j−1} and A_j; its error (±9 %, §7a) is documented
here and measured again for C2 by the full linearisation. No full-domain analytical stability analysis is
attempted.

## 12. Verification plan for C2 (after review of this draft)

Implementation as an experimental option (`interface_coupling="c2"`), after review of this draft; the
explicit solver stays the default until the plan passes. Acceptance order (user, 2026-11-28): algebra
and CFL condition (§9.4, §9.4a); V5–V8; V9–V13; V14; V15–V16.

| test | content | pass condition |
|---|---|---|
| V5, V5b–V8 | §11, explicit scheme and C2 | as stated in §11 |
| V9 linearisation | the ten N.1 cases with C2 | ρ ≤ 1 at CFL 0.9 in all ten |
| V10 grid spacing | Δs = 0.5, 0.25, 0.125 m | ρ ≤ 1 at CFL 0.9 at every spacing |
| V11 direction | contractions and reverse flow | unchanged from the explicit scheme (C2 inactive) |
| V12 consistency | conduit → 1 m transient from a perturbed state at Δt, Δt/2, Δt/4 (fixed Δs) | C2 and the explicit scheme (stable at the smallest Δt) converge to the same solution, first order |
| V13 successive expansions | 0.2 → 0.6 → 2 m in two steps, and a conduit → 0.6 m → 2 m; independent blocks (i) and chain solve (ii) | ρ ≤ 1 at CFL 0.9; (ii) adopted if (i) fails |
| V14 benchmarks at CFL 0.9 (acceptance) | B12a (relation 1 %, Borda 3 %), B12b, B12d submerged and free (steady; relation and Borda within 1 %), B12c refinement gates, B1, B9, B13 | all pass; fallback and |d| > 1 counts 0; expansion losses equal to those of the explicit scheme at a stable step within 1 % |
| V15 comparisons | C3 local subcycling of the two cells (reference) and C1 relaxation | C2 within the C3 transient to first order; C1 reported only |
| V16 cost | wall time per step with and without C2 | reported |

The target, in the user's words: stable at the intended time step, conservative, steady-state preserving,
and still accurate for the expansion and conduit-outlet benchmarks.
