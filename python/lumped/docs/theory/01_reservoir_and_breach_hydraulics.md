# Theory, Part 1 — Reservoir and breach hydraulics

*Lumped 1-D morphodynamic breach model · draft 2 · 2026-11-20 · status: decisions made, source check open*

This part defines how water leaves the reservoir and how the flow through the breach is described.
Erosion (Part 2), widening and bank collapse (Part 3), headcut (Part 4), piping erosion (Part 5),
impulse waves (Part 6), moraine banks (Part 7) and numerics (Part 8) build on it.

Rule for every part: each equation has a source or a short derivation, and each coefficient is either
sourced, derived, or one of the three calibration factors (f_kd, C_h, f_t). No hydraulic coefficient in
this part is calibrated.

---

## 1.1 State variables and geometry

The dam is a trapezoidal embankment: height H_d, crest elevation z_cr, crest width W_cr (in the flow
direction), crest length L_cr (across the valley), upstream and downstream slopes. The breach is one
trapezoidal channel cut into it:

| symbol | meaning | unit |
|---|---|---|
| z_s | reservoir water-surface elevation | m |
| V | reservoir water volume | m³ |
| z_b | breach bottom elevation at the crest (flat breach top) | m |
| b | breach bottom width | m |
| m | breach side slope, horizontal : vertical | – |
| d = z_cr − z_b | breach depth | m |
| H = z_s − z_b | head on the breach bottom | m |
| z_t | tailwater elevation downstream of the breach | m |

Following Wu (2013) the overtopping breach is a flat broad-crested top (the control section),
connected downstream to a headcut (cohesive) or a straight downstream slope (non-cohesive); the
longitudinal evolution is defined in Parts 2 and 4.

**Reported width.** The model reports the average breach width

    B = b + m·d                                                     (1.1)

which is the mean of top and bottom width of a trapezoid. This is the definition behind the observed
widths in the breach databases used for calibration and validation (e.g. Castlewood 54.9 m), so model
and observation compare like with like. Top width B_top = b + 2m·d is also reported.

---

## 1.2 Reservoir water balance

    dV/dt = Q_in(t) − Q_b − Q_ov − Q_sp(z_s)                        (1.2)
    z_s = Z(V)                                                       (1.3)

Q_in: inflow (constant or hydrograph, from the case file); Q_b: breach outflow (1.5 or 1.9);
Q_ov: flow over the remaining intact crest (1.8); Q_sp: spillway or outlet flow where a case provides
a rating (none of the current cases do, so Q_sp = 0 for now). This is the same balance as Wu (2013,
Eq. 3.16) and the existing TypeScript and 2-D engines.

The stage–storage relation Z(V) is taken from the case file, which uses one of four forms:

| case `reservoir.type` | relation | cases |
|---|---|---|
| `power` | V(z) = V_full · ((z − z_0)/H_full)^e, i.e. surface area A_s ∝ (z − z_0)^(e−1) | Castlewood, GooseCreek, LaurelRun, SouthFork, Poerua, Yigong |
| `stage_volume` | tabulated V(z), linear interpolation | E2 series |
| `area_height` | tabulated A_s(z), V by trapezoidal integration | E1 series, IMPACT |
| `prismatic` | V = A · (z − z_base), constant area | Walsh series |

The power form is identical to Wu (2013, Eqs. 3.19–3.21) with e = m_r + 1. The 2-D engine's
`Reservoir` class already implements tabulated stage–volume interpolation and is reused unchanged;
the four case forms are converted to a stage–volume table once at start-up.

Water that enters storage by slide displacement (Part 6) is handled as in the 2-D engine: the
displaced volume shifts the stage–volume curve, it is not added as water.

---

## 1.3 Breach outflow — open breach (weir control)

Flow from the reservoir into the breach passes through critical depth on the flat breach top, so the
breach is a broad-crested weir with a trapezoidal section.

**Exact critical-flow form (default).** For a trapezoid with A(y) = (b + m y) y and top width
T(y) = b + 2 m y, critical flow and energy conservation from the reservoir (velocity head in the
reservoir neglected) give

    Q² T / (g A³) = 1                     (critical condition)
    H = y_c + A / (2T)                    (specific energy at critical depth)          (1.4)
    Q_b,free = C_d · √(g A(y_c)³ / T(y_c))                                              (1.5)

Solve (1.4) for y_c ∈ (0, H) — the right-hand side increases monotonically with y, so a bracketed root
always exists and is unique — then evaluate (1.5). Source: standard critical-flow theory for prismatic
channels (Chow 1959; Henderson 1966). C_d = 1 is the ideal broad-crested weir; it is the only
coefficient, and it is fixed, not calibrated.

**Checks that tie (1.5) to the published weir formula.** Two exact limits:

- Rectangle (m = 0): y_c = 2H/3, Q = √g·(2/3)^1.5·b H^1.5 = **1.705 b H^1.5**
- Triangle (b = 0): y_c = 0.8H, Q = √(g/2)·0.8^2.5·m H^2.5 = **1.268 m H^2.5**

The weir formula used by NWS BREACH (Fread 1988) and DL Breach (Wu 2013, Eq. 3.1; Singh 1996),

    Q_b,free = c1 b H^1.5 + c2 m H^2.5,   c1 = 1.7,  c2 = 1.3 (Wu) / 1.35 (Fread)        (1.6)

is the sum of these two limits with rounded coefficients. (1.6) is kept as an option (`weir="dlbreach"`)
so the model can be run exactly as DL Breach for the benchmark, and the two forms are compared in the
verification suite.

**Tailwater submergence.** With S = (z_t − z_b)/(z_s − z_b),

    k_sm = 1                              for S ≤ 0.67
    k_sm = 1 − 27.8 (S − 0.67)³           for S > 0.67                                 (1.7)
    Q_b = k_sm · Q_b,free

Source: Fread (1988), as used in Wu (2013, Eq. 3.2). None of the current cases supplies a downstream
channel, so z_t ≤ z_b and k_sm = 1 by default; (1.7) becomes active when a case gives a tailwater
rating (Manning normal depth in a prismatic downstream channel, or a stage series).

**Intact-crest overtopping.** Before and during breaching, water above the crest also spills over the
part of the crest that is not yet breached, as a rectangular broad-crested weir:

    Q_ov = 1.705 · max(L_cr − B_top,cr, 0) · max(z_s − z_cr, 0)^1.5                   (1.8)

with B_top,cr the breach width at crest level. Same critical-flow basis as (1.5), C_d = 1.

---

## 1.4 Breach outflow — pipe (piping mode)

Before roof collapse (Part 5) the breach is a pipe of width a, height c and length L_p, invert z_bp:

    Q_b = A_p √( 2g (max(z_s, z_t) − z_bp) / (K_u + K_d + f L_p / (4 R_h)) )          (1.9)

A_p = a·c, R_h = a c / (2(a + c)); entrance and exit losses K_u, K_d; friction factor f from
Swamee–Jain with k_s = d50, or f = 8 g n² / R_h^(1/3) (Manning). Source: Wu (2013/2016, Eqs. 3.13–3.15).
This replaces the TypeScript engine's bare orifice (Cd·A·√(2gH)), which ignores pipe friction — for a
long, narrow early pipe friction dominates and the bare orifice overpredicts flow.

---

## 1.5 Flow through the breach — depth, velocity and bed shear

Erosion is driven by the bed shear stress, so it must be computed on the section where erosion
happens, not from the reservoir head. Two sections are used (Wu 2013):

**Breach top (control section).** Representative depth = critical depth from (1.4), or, with
tailwater, the larger of critical depth and the mean stage above the bed:

    h_top = max( y_c ,  (z_s + z_t)/2 − z_b )                                          (1.10)

(Wu 2013, Eq. 3.4, generalised from the rectangle's 2H/3 to the trapezoid's exact y_c.)

**Downstream slope.** Uniform (normal) flow on the downstream face, slope S_0, from Manning:

    Q_b = (1/n) A R^(2/3) S_0^(1/2),   A = (b + m h) h,   R = A / (b + 2h√(1 + m²))       (1.11)

solved for h by a bracketed root (Wu 2013, Eq. 3.10). If the normal depth comes out above critical
(mild slope), critical depth is used instead.

**Velocity and shear on either section:**

    U = Q_b / A,    τ_b = ρ g n² U² / R^(1/3)                                           (1.12)

(Wu 2013, Eq. 3.11; Manning friction). Two options for n, as in the 2-D engine:

- total shear: n from the case file (`manning_n`);
- grain shear: n' = d50^(1/6) / 21.1 (Strickler 1923, d50 in m), used for bed-load capacity laws.

This fixes the TypeScript engine's shear (review item C1), which used the reservoir-side velocity
Q/(W·H) with R from the full head and so underestimated the channel shear.

---

## 1.6 Assumptions and limits of Part 1

1. Quasi-steady flow through the breach: the breach adjusts slowly compared with the travel time of
   water through it. Standard for lumped breach models; it fails for very fast impulse-wave overtopping,
   which Part 6 treats separately.
2. Reservoir velocity head neglected (large reservoir). For the small Walsh flume reservoirs this is
   checked in verification.
3. One breach, symmetric trapezoid (n_loc = 2 sides) unless the case states a breach at an abutment
   (n_loc = 1, Part 3).
4. No tailwater unless a case provides it (k_sm = 1).
5. Keulegan (energy-loss) breach flow for low-head levee breaches (Wu 2013, Eq. 3.3) is not included in
   v1; all dam cases use weir control for the whole event, as in DL Breach's default option.

---

## 1.7 Verification this part must pass (Phase 3)

| test | expected |
|---|---|
| (1.5) at m = 0 | 1.705 b H^1.5 to 1e-6 |
| (1.5) at b = 0 | 1.268 m H^2.5 to 1e-6 |
| (1.5) vs (1.6) over b/(mH) from 0.1 to 100 | difference reported (expected a few per cent, largest near b ≈ mH) |
| (1.7) | k_sm = 1 at S ≤ 0.67, continuous at 0.67, 0 at S ≈ 1.0 |
| Fixed breach, prismatic reservoir, no inflow | drawdown z_s(t) matches the closed-form solution of dV/dt = −c1 b (z_s − z_b)^1.5 |
| Reservoir forms | each case curve → stage–volume table → inverse gives back z to 1e-9 |
| Water balance | V(0) + ∫Q_in − ∫(Q_b + Q_ov) − V(t) < 1e-9 relative |
| (1.11) | normal depth recovers Manning Q for random (b, m, n, S_0) |
| (1.9) | reduces to the bare orifice when f L_p → 0 and K_u + K_d = 1 |

---

## 1.8 Decisions (Aakash, 2026-11-20)

1. **Default weir form: exact critical flow (1.5) with C_d = 1.** The DL Breach formula (1.6) is an
   option, used for the benchmark runs.
2. **c2 = 1.3** in the DL Breach option (Wu 2013), to match the benchmark.
3. **Manning n:** keep the case files' `manning_n` for total shear and Strickler n' for grain shear;
   the uniform 0.016 values are checked in Phase 4 (case database).

Still open:

- **Source check:** the copy of Wu (2016) read for this draft had garbled equation layout.
   The submergence formula (1.7), c2 = 1.3, and the pipe-loss terms in (1.9) are to be confirmed against
   the original PDFs (Wu 2013 paper, Fread 1988) before this part is signed off. The entrance/exit loss
   values K_u, K_d are set in Part 5 (piping).

---

## References

- Chow, V. T. (1959). *Open-Channel Hydraulics*. McGraw-Hill.
- Fread, D. L. (1988). *BREACH: An erosion model for earthen dam failures*. NOAA/NWS, Silver Spring, MD.
- Henderson, F. M. (1966). *Open Channel Flow*. Macmillan.
- Singh, V. P. (1996). *Dam Breach Modeling Technology*. Kluwer.
- Strickler, A. (1923). Beiträge zur Frage der Geschwindigkeitsformel und der Rauhigkeitszahlen für
  Ströme, Kanäle und geschlossene Leitungen. Eidg. Amt für Wasserwirtschaft, Bern.
- Swamee, P. K., and Jain, A. K. (1976). Explicit equations for pipe-flow problems. *J. Hydraul. Div.*,
  102(5), 657–664.
- Wu, W. (2013). Simplified physically based model of earthen embankment breaching. *J. Hydraul. Eng.*,
  139(8), 837–851.
- Wu, W. (2016). *Introduction to DLBreach — a simplified physically-based dam/levee breach model*,
  version 2016.4, technical report, Clarkson University.
