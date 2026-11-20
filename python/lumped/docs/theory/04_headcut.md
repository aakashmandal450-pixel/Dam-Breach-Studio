# Theory, Part 4 — Overtopping breach of cohesive embankments: surface erosion, headcut formation and advance

*Lumped 1-D morphodynamic breach model · draft 2 · 2026-11-20 · status: for review*
*Draft 1 followed DL Breach (Temple 1992 law with a calibrated C_T). Draft 2 rebuilds the part from the
physical process as observed in large-scale tests and as modelled by the USDA-ARS SIMBA/WinDAM
stress-based model; DL Breach's formulas are kept as options for the benchmark.*

---

## 4.0 What the earlier TypeScript 1-D engine did

- A headcut "started" when the water over the crest reached 4 cm, at the crest, and only had to cross
  the crest width.
- Default advance rate: 6 × k_d (ρ g h_F − τ_c), with h_F = 0.35 × reservoir head, capped at H/2 h, then
  multiplied by 0.75 (0.55 highly erodible, 0.22 moraine). Option: 0.5 (qH)^(1/3).
- Breach deepening during the headcut was capped at crest − 0.35 H; widening came from the fixed
  bed/bank volume split.
- No surface-erosion stage before the headcut, no plunging-flow condition, no use of soil strength,
  no failure of the remaining crest.

It had the right sequence of stages, but every number deciding speed and depth (6, 0.35, 0.75, 0.55,
0.22, 2 h, 0.35 H) was unsourced.

---

## 4.1 The physical process

Large-scale overtopping tests on compacted cohesive embankments (Hanson et al. 2005; the E-series in our
case set) show four stages (Hanson et al. 2003, as described in Wahl et al. 2017, DSO-2017-02, App. A1):

1. **Surface erosion and headcut formation.** Overtopping flow on the bare downstream face erodes the
   soil (rills, cascading small overfalls) until a drop forms near the downstream edge of the crest.
2. **Headcut advance through the crest.** Once the drop is deeper than the critical depth of the flow,
   the flow plunges. The impinging jet scours the base of the drop and undercuts the face, and the face
   fails in blocks — so the headcut moves upstream through the crest while it deepens and widens.
3. **Breach formation.** When the headcut passes the upstream edge of the crest the hydraulic control
   is lowered and outflow rises sharply, until the embankment is removed down to its base.
4. **Widening** of the breach at the base while the reservoir drains.

Two facts set what physics the model needs:
- The headcut moves by **erosion at its base plus mass failure of the face**. Its speed therefore
  depends on the soil's erodibility (k_d, τ_c — measured by jet tests for our cohesive cases) and on its
  strength (undrained shear strength c_u), not on a separately fitted migration coefficient.
- **Whether a headcut forms at all is a property of the soil**, not of its label. Soils with enough
  cohesion stand in near-vertical faces and fail by headcutting; decidedly non-cohesive soils erode
  along the bed; in between there is a zone of uncertainty (Wahl et al. 2017, conclusions). Reclamation's
  own overtopping test of a cohesive embankment showed surface erosion and crest lowering, not a headcut,
  and the headcut-only WinDAM C did not reproduce it (Wahl 2019, PFHA workshop). A model that switches to
  headcut mode by material label would get such dams wrong.

---

## 4.2 Stage 1 — surface erosion until the flow plunges

The downstream face erodes by excess shear (Part 2, (2.1)) under normal-depth flow on the slope
(Part 1, (1.11)–(1.12)), as in SIMBA/WinDAM (DSO-2017-02, App. A1, Eq. 1):

    E_r = k_d (τ_e − τ_c),     τ_e = total bed shear on bare soil                               (4.1)

The eroding area forms at the downstream edge of the crest (the most upstream point of the face, where
discharge is largest and the distance a headcut must travel is least — DSO-2017-02, App. A1). Its depth
H_h grows at E_r; its width grows by side-wall erosion (Part 3; see decision 4).

**Transition to stage 2 (physical criterion):** the flow plunges when

    H_h > d_c = (q²/g)^(1/3)      and the tailwater is below the top of the drop                (4.2)

with q the unit discharge over the drop (SIMBA treats it as uniform across the breach width, q = Q_b/b).
This is a hydraulic condition — a nappe separates only when the drop exceeds the critical depth — and
replaces DL Breach's assumption that the headcut starts at the toe and its H/h_x speed-up factor.

---

## 4.3 Stage 2 — headcut advance by base scour and face failure (default)

Stress-based model of Hanson et al. (2001), as implemented in SIMBA/WinDAM and printed in DSO-2017-02
(App. A1, Eqs. 2–8). Geometry (DSO-2017-02, Fig. A1-12): headcut of height H_h, critical depth d_c over
the brink, backwater depth d_bw at the base (taken ≥ d_c); the jet undercuts the face by E_v before a
block of width H_h/2 fails on a 45° plane.

**Stress on the face from the impinging jet** (Robinson 1992):

    C_n  = 0.146 + 27.5 [(H_h − d_bw)/H_h] (d_c/H_h)^0.852 · exp(−6.1 (H_h − d_bw)/H_h)        (4.3)
    X_ws = d_c [ (0.823 + (H_h − d_bw)/d_c) / 0.483 ]^(1/(C_n + 1.6))                         (4.4)
    S_ws = −0.483 (C_n + 1.6) (X_ws/d_c)^(C_n + 0.6)                                          (4.5)
    X_p  = X_ws − d_bw/S_ws − 0.411 d_c                                                       (4.6)
    τ_hf = 0.025 γ d_c (H_h/d_c)^0.026 (d_c/X_p)^1.06 (d_bw/d_c)^0.221                        (4.7)

**Undercut at which the face fails** (force balance, soil tensile strength neglected):

    E_v = (−b − √(b² − 4ac)) / (2a),   a = γ_t/2,   b = γ d_c − γ_t H_h/2 − 2 c_u,
    c = c_u H_h + (γ/2) d_bw² − 0.375 γ_t H_h² − (γ/2) d_c H_h                                (4.8)

γ: unit weight of water; γ_t: total unit weight of the soil; c_u: undrained shear strength.

**Advance rate:**

    dX/dt = (H_h / (2 E_v)) · k_d (τ_hf − τ_c),    0 if τ_hf ≤ τ_c                              (4.9)

Valid while E_v > 0. **E_v ≤ 0 means the soil cannot stand an undercut vertical face of that height**:
the flow then cascades down an unstable face, and WinDAM caps the advance at the erosion rate E_r of
normal-depth flow on a 0.5H:1V slope (DSO-2017-02, App. A1). The same cap is used here.

**Why this is the physics-based default.** Every quantity in (4.3)–(4.9) is either hydraulics
(d_c, d_bw, H_h) or a measured soil property (k_d, τ_c from jet tests; c_u, γ_t). There is no
migration coefficient to calibrate: f_kd, which already scales the measured k_d, also scales the
headcut speed consistently. In the Reclamation/CEATI evaluation of breach models this stress-based
model "performed very well and exhibited appropriate sensitivity to soil parameters" (DSO-2017-02).
It also contains the mode switch of §4.1 by itself: a soil with c_u ≈ 0 gives E_v ≤ 0 and erodes as
cascading surface flow.

**Base deepening and widening during stage 2** (DSO-2017-02, App. A1): the base lowers at
k_d (τ − τ_c) with τ the larger of the slope stress below the drop and the jet stress; it stops at the
dam base. Width grows by the larger of the plunging-flow change (taken equal to the headcut advance,
half to each side — the plunge pool scours sideways as fast as upstream) and the wall erosion of
approach and exit flow (Part 3).

**Inputs for our cases:** c_u = q_u/2 where the case gives unconfined compressive strength (E-series);
otherwise the case's cohesion (GooseCreek 13.2 kPa, LaurelRun 25 kPa, IMPACT_1-02 4.9 kPa) — Phase 4
records the source of each value. γ_t = (1 − p) ρ_s g + S_r p ρ_w g with saturation S_r = 1 at the face.

---

## 4.4 Stage 3 — headcut in the crest, control lowered

When the headcut passes the upstream edge of the crest, the hydraulic control is at the headcut crest.
The control lowers by whichever is faster (DSO-2017-02, App. A1): continued headcut advance (4.9), or
downcutting of the control by the friction stress of critical flow, k_d (τ_c,flow − τ_c). Breach
outflow is the weir of Part 1 at the current control elevation and width.

**Residual-block sliding (option).** DL Breach also checks the crest block upstream of the headcut for
horizontal sliding on the dam base (Wu 2016, §4.5, Fig. 4.14); WinDAM has no such mechanism. Our
force balance per unit breach width, including the uplift that a saturated base carries:

    F_drive  = ½ γ z_s² + τ_top L_top                                                         (4.10)
    F_resist = c L_base + (W − U) tan φ + 2 c A_blk / b,   U = ½ γ (z_s + z_t⁺) L_base           (4.11)

Failure moves the block volume into the eroded-sediment budget ("virtual tank", Wu 2016) and the control
drops to the base.

---

## 4.5 Stage 4 — widening at the base

Parts 2–3 on the fixed bed: wall erosion by the breach flow, side slope from bank stability (vertical
while a vertical wall is stable — matching the near-vertical breach sides seen in cohesive tests),
limited by the valley width.

---

## 4.6 DL Breach headcut laws (options, for the benchmark)

Temple (1992) dx/dt = C_T q^(1/3) H^(1/2), C_T = 0.0049 m^(−1/6) s^(−2/3) (DL Breach default, calibrated
on E1S1); SITES; Temple et al. (2005) — Wu (2016, Eqs. 4.28–4.32), with DL Breach's toe start, H/h_x
factor and α_c = 0.165 widening. Used only for the like-for-like DL Breach comparison.

---

## 4.7 Verification this part must pass (Phase 3)

| test | expected |
|---|---|
| (4.3)–(4.7) | reproduce a hand calculation of τ_hf for a set (H_h, d_c, d_bw) |
| (4.8) | E_v > 0 for low drops in strong soil; E_v ≤ 0 when H_h exceeds the vertical-cut height (~4 c_u/γ_t) |
| (4.9) | zero below τ_c; capped at the 0.5H:1V surface-erosion rate when E_v ≤ 0 |
| stage switch | stage 2 begins exactly when H_h > d_c; never for c_u = 0 |
| mass balance | water and sediment balances < 1e-9 relative across all stage switches |
| dt convergence | Qp, Tp, B with p ≈ 1 on E1S1, E2S2, GooseCreek, LaurelRun |
| benchmark option | DL Breach option reproduces DL Breach's published E1S1 result within its reported accuracy |

---

## 4.8 Decisions for review (physics-based)

1. **One process model for all soils**: stage 1 surface erosion → stage 2 headcut only when the flow
   plunges (4.2), with the soil's ability to hold a face entering through E_v (4.8). No mode switch by
   material label.
2. **Headcut advance: stress-based Hanson et al. (2001) / Robinson (1992) model (4.3)–(4.9)**, driven by
   measured k_d, τ_c, c_u. No separate migration coefficient: **C_h is dropped as a calibration factor**
   (kept only as a sensitivity multiplier on (4.9), fixed at 1). Calibration factors become f_kd and f_t.
3. **Widening from processes**: plunge-pool widening equal to headcut advance (SIMBA) plus wall erosion
   by the flow (Parts 2–3); no fitted α_c.
4. **Wall shear = bed shear** for side-wall erosion (narrow breach; Knight et al. via Wu 2016), as in
   Parts 2–3. SIMBA uses 0.7 × bed (Lane 1955, wide rectangular channel). Proposed: keep 1 now, test 0.7
   in the sensitivity analysis.
5. **Start location**: downstream crest edge (observed in the E-series and used by SIMBA), not the toe.
6. **Residual-block sliding**: on, with uplift (4.10)–(4.11).
7. **DL Breach laws** kept only as the benchmark option.

---

## References

- Hanson, G. J., Robinson, K. M., and Cook, K. R. (2001). Prediction of headcut migration using a
  deterministic approach. *Trans. ASAE*, 44(3), 525–531 (as given in DSO-2017-02).
- Hanson, G. J., Cook, K. R., and Hunt, S. L. (2005). Physical modeling of overtopping erosion and breach
  formation of cohesive embankments. *Trans. ASAE*, 48(5), 1783–1794.
- Lane, E. W. (1955). Design of stable channels. *Trans. ASCE*, 120, 1234–1279 (as cited in DSO-2017-02).
- Robinson, K. M. (1992). Predicting stress and pressure at an overfall. *Trans. ASAE*, 35(2), 561–569.
- Wahl, T. L., et al. (2017). *Evaluation of Numerical Models for Simulating Embankment Dam Erosion and
  Breach Processes*. DSO-2017-02, Bureau of Reclamation, Denver. App. A1 (SIMBA).
- Wahl, T. L. (2019). Breach modeling with WinDAM and DL Breach. PFHA workshop presentation.
- Wu, W. (2016). *Introduction to DLBreach*, v2016.4. Clarkson University. §2.1.2, §4.5.
