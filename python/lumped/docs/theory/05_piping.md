# Theory, Part 5 — Breach initiated by internal erosion (piping): pipe enlargement and roof collapse

*Lumped 1-D morphodynamic breach model · draft 4.2 · 2026-11-24 · status: geotechnical review received; roof-collapse criterion under investigation (§5.5a); implementation on hold*
*Draft 1 (2026-11-20) proposed eight decisions. Draft 2 takes in the review of 2026-11-24:
continuous culvert-type hydraulics, erosion only on wetted walls, HET k_d preferred, roof
pressure integrated along the pipe, a separate uplift (heave) check, a debris layer that takes part in
the hydraulics, an optional exit headcut and stricter pipe-location inputs. Where the review and the
physics disagreed, the reasons are given (§5.9). Draft 3 takes in the second review: event location of
the collapse time, mechanism C named and bounded as exit uplift (not a piping criterion), debris
volume from solids and deposited porosity, an explicit deposition assumption, a solids budget, and
the blocking criterion that follows from it. Draft 4 settles the last three points: the 1.2 D
submergence threshold is removed (inlet control now follows from the maximum-discharge principle,
with no threshold); the "no uplift under the reservoir" result is derived from an energy bound and
is also computed, not assumed; and the blocking assumptions are stated, with self-healing under zero
inflow labelled a model prediction.*

---

## 5.0 What the earlier TypeScript 1-D engine did

- Pipe invert forced to an estimated phreatic level (`estimatePipeInvertPhreatic`), even when the
  input `pipeInvert` was given. The initial pipe radius was 0.08 m.
- Flow: bare orifice C_d π R² √(2gH) with C_d = 0.6, so there was no pipe friction.
- Wall shear ρ g R_h (H/L), multiplied by 0.65 when the pipe was not full. Erosion was excess shear
  with material factors (×2.8 highly erodible, ×0.45 low erodible) and a non-equilibrium concentration.
- The eroded area was split 45 % to width and 55 % to height.
- Roof collapse when any of three ratio rules fired (κ = 0.55; width > 2.2 × cover; an "arch need"
  term). After collapse the open width was 1.0–1.2 × pipe width, opened gradually over time.

Only the hydraulic-gradient wall shear is physics. The other numbers are unsourced, and the roof rules
used no soil strength. The Python engine replaces all of it; the TypeScript website port (later phase)
must remove the phreatic override.

---

## 5.1 The physical process

Piping-initiated breach tests on homogeneous cohesive embankments at the USDA-ARS laboratory
(Hanson et al. 2010a; Ali et al. 2021; photo sequence in Wu 2016, Fig. 2.14) show:

1. **Pipe enlargement.** Flow through a continuous defect erodes its walls. The pipe grows and the
   flow grows with it — a positive feedback, so most of the growth happens at the end.
2. **Roof collapse.** When the pipe is wide enough, the soil bridge above it falls in.
3. **Open breach.** The flow passes over the collapsed section and the breach develops as for
   overtopping (Parts 1–4).

Times to roof collapse in the three ARS tests: 0.23 h (silty sand, non-plastic), 17.2 h (CL-ML) and
20.5 h (CL) (as tabulated in Wahl 2010, USBR PAP-1017). In test P1 the exit cut down to the base while the
pipe was still growing. Field cases often take days to weeks for the pipe stage and hours for the
breach (Wu 2016, §2.2).

Two facts set the model:
- **A pipe needs a roof.** Internal erosion progresses to breach only where the soil above can span
  the void (Reclamation/FERC internal-erosion best practice). Roof strength is a physical input.
- **The pipe stage mainly sets the timing.** The 2019–2024 international comparison (AREBA,
  DL Breach, EMBREA, Rupro, WinDAM C; ARS P1 and Big Bay) found that the pipe and roof routines change
  peak outflow less than expected. Peak flow is governed mostly by k_d and the open-breach roughness
  (HR Wallingford FWR6124, 2025).

---

## 5.2 Pipe geometry

The pipe is a horizontal rectangular duct, width b_p and height a_p, invert z_inv, crown
z_cr = z_inv + a_p, centreline z_bp = z_inv + a_p/2. It runs from the upstream face to an outlet at
x_o. Initially x_o is the downstream face, x_down(z_bp); x_o moves upstream only through the exit
mechanisms of §5.6. The pipe length is

    L_p = x_o − x_up(z_bp)                                                                (5.1)

**Why a rectangle.** It is a manageable approximation whose hydraulics are computed from its actual
area and wetted perimeter, and it becomes the rectangular open breach after collapse with no
conversion. It is *not* hydraulically identical to a circle: a 0.2 m square and a 0.2 m circle have
the same R_h = 0.05 m but different areas (0.040 vs 0.031 m²), so they carry different flows.

---

## 5.3 Pipe flow — inlet control and outlet control, continuous in head

Culvert hydraulics (FHWA HDS-5, Norman et al. 1985) separate **inlet control** (the entrance limits
the flow) from **outlet control** (the energy needed for entrance, friction and exit losses limits
it). For a given headwater the discharge is the smaller of the two. This is the same as HDS-5's
"larger required headwater" rule when both use the same headwater and tailwater. It is a
culvert-inspired approximation for an eroding soil pipe: the entrance and roughness values below are
not concrete-culvert coefficients and must be tested.

Let HW = z_s − z_inv be the headwater above the invert, D = a_p and b = b_p.

**Inlet control — maximum discharge through the entrance section.** The entrance is a rectangle of
width b and height D. Flow enters from still water with energy HW above the invert and loses K_u of
its velocity head. With a free surface at depth y in the entrance, the energy equation gives
Q(y) = b y √(2g (HW − y)/(1 + K_u)). For a given energy, the section passes the largest discharge
this allows at critical depth (the maximum-discharge principle; Chow 1959, Ch. 3) — limited here by
the roof:

    HW ≤ 1.5 D:   y_e = 2HW/3,  Q_i = b y_e √( 2g (HW − y_e) / (1 + K_u) ) = 1.705 b HW^1.5/√(1 + K_u)
    HW > 1.5 D:   entrance full and pressurised,  Q_i = b D √( 2g (HW − D/2) / (1 + K_u) )       (5.2)

- **Below HW = 1.5 D** this is the critical-depth weir, i.e. Part 1 (1.5) with the entrance loss.
- **At HW = 1.5 D** the free surface reaches the roof at the entrance.
- **Above it** the entrance is a rounded, pressurised opening with loss K_u, and its head is measured
  to the centroid.

There is no empirical submergence threshold. (The draft 3 interpolation over D–1.2 D is withdrawn:
it was not shown to apply to an eroding soil pipe.) A sharp-edged entrance (contraction coefficient)
is a later option, to be tested on the ARS cases.

**Once full, outlet control always governs.** For a full pipe the pressurised entrance (5.2) has loss
1 + K_u and outlet control (5.3) has K_u + K_d + f L_p/(4R), with K_d ≈ 1. So Q_o ≤ Q_i always, and
Q_b = Q_o once the entrance is full.

**Outlet control** (energy equation from the reservoir to the outlet):

    y = y_e;   w = 1 if y_e = D (pipe full, roof wetted), else 0
    A = b y,   P = b + 2y + w b,   R = A/P,   f = 8 g n_p² / R^(1/3)
    Q_o = A √( 2g (HW − max(y/2, h_t)) / (K_u + K_d + f L_p/(4R)) )                       (5.3)

    Q_b = min(Q_i, Q_o)                                                                   (5.4)

**Priming — a real, reported jump.** At HW = 1.5 D the pipe changes from part-full to full flow.
Two things change in one step: the roof joins the wetted perimeter, and the control passes from the
entrance to the barrel. The size and direction of the step depend on F = f L_p/(4R):
- **Long pipes, F > K_u + K_d ≈ 1.05:** the barrel already controlled just before priming, and the
  only change is the wetted roof, a small drop in Q.
- **Short or wide pipes, F < 1.05:** the part-full flow was entrance-controlled, and the full barrel
  passes more, so Q jumps up — at most by √2, as F → 0.

Since R ≈ D/4, F < 1.05 means L_p/D below about 20–35 for f = 0.03–0.05. That happens mainly late in
the pipe stage of a thin dam.

This is the culvert priming transition, which is physically abrupt. It is the reason HDS-5 has a
transition zone, for which no band applicable to soil pipes is available. The model does not smooth
it. It is event-located in time like the collapse, and its time, F and the size of the step are
reported. Everywhere else Q_b is continuous and non-decreasing in HW.

*Correction from draft 4:* draft 4 stated that the barrel governs once full whenever F > 0.05. The
denominator was miscounted (K_u + K_d is 1.05, not 2.05). The independent numerical check found
counter-examples. The statement is replaced by the exact result above: Q_o ≤ Q_i always once full,
and an upward jump at priming when F < 1.05.

- **Losses:** K_u ≈ 0.05 (entrance) and K_d ≈ 1 (exit velocity head) from Part 1, §1.4. Entrance,
  friction and exit losses are separate terms.
- **Tailwater:** h_t is the tailwater above the invert. There is no tailwater model yet, so h_t = 0
  and the outlet is free; the term is in place for later.
- **Roughness:** the pipe has its own Manning n_p, which defaults to the open-breach n so that no
  calibrated parameter is added. It is tested in the sensitivity analysis and constrained by
  hole-erosion data where a case has them.
- **Slope and crest flow:** the pipe is horizontal, as the lumped model has no pipe slope. If the
  reservoir rises above the crest during the pipe stage, crest overflow (1.8) is added.

---

## 5.4 Wall shear and pipe enlargement

**Shear.** A momentum balance on the water gives the wall shear from the *friction* part of the loss
only, so entrance and exit losses do not erode the wall:

    τ_p = ρ g R S_f = ρ f U²/8,    U = Q_b/A                                               (5.5)

In a long pipe, friction takes almost all the head, and (5.5) tends to the hole-erosion-test relation
τ_p ≈ ρ g R (HW − D/2)/L_p (Wan and Fell 2004). The two differ in short pipes. Example (0.2 m pipe,
10 m head, n = 0.016):

| pipe | (5.5) | ρgRΔh/L |
|---|---|---|
| 50 m long | 91 Pa | 98 Pa |
| 5 m long | 554 Pa | 981 Pa |

The same formula is used whether the pipe is full or partly full. It is recomputed every step from
the current geometry.

**Erosion, cohesive soils (detachment-limited).** Only wetted surfaces erode:

    ε = k_d (τ_p − τ_c)                                                                   (5.6)
    floor:  dz_inv/dt = −ε      (stops at the base)
    sides:  db_p/dt   = 2ε
    roof:   dz_cr/dt  = w ε     (only when the roof is wetted)                                (5.7)

Width and height therefore evolve independently: a partly full pipe deepens and widens but does not
raise its roof. The dimensions only grow, so no minimum-size guard is needed.

**Erodibility source.** The jet erosion test (JET) and the hole erosion test (HET) give systematically
different k_d and τ_c for the same soil. In Reclamation's direct comparison the JET indicated much
greater erodibility (Wahl, Regazzoni and Erdogan 2008, DSO-08-05; USBR PAP-1000), and the ARS piping
soils were tested both ways (USBR PAP-1017). The HET is a
small pipe flow, so the **HET k_d and τ_c are preferred** for the pipe stage. Where a case has only
JET values, they are used, the source is recorded, and a JET→HET conversion is tested in the
uncertainty analysis. τ_c is a separate soil parameter, never folded into k_d.

**Erosion, non-cohesive soils (transport-limited).** The Part 2 capacity of the pipe flow, with the
relaxation C_out = C*(1 − exp(−L_p/L_s)) and L_s = λ b_p. The eroded bulk volume
Q_b C_out dt/(1 − p) is spread over the wetted wall area P L_p, which gives ε for (5.7).

**Backward erosion piping in sands** (Sellmeijer) is a different mechanism — a pipe growing from
the downstream side toward the reservoir — and would be a separate future module. Part 5 assumes a
concentrated leak that already crosses the dam.

---

## 5.5 Roof stability — two mechanisms, both checked every step

Assumptions, stated: soil above the pipe is homogeneous, with uniform undrained strength c_u;
total-stress analysis (failure is fast); the roof is a rigid block with vertical undrained shear
surfaces above the two pipe walls (as in DL Breach), with the full c_u mobilised on both. This is a
rigid-block approximation, not a soil-arching solution. A_r is the longitudinal area of the roof —
the dam section above z_cr between x_up(z_cr) and x_o.

**Unit weight by saturation state (review, 2026-11-24).** The roof is saturated below the phreatic
surface and moist above it, so it takes γ_sat below and γ_moist above. As a first-version assumption
the phreatic surface is taken at the reservoir level z_s over the roof; both unit weights are case
inputs. In a total-stress analysis the pore pressure inside the block is not subtracted again.

**Water pressure on the soffit.** When the pipe flows full, the piezometric head along the soffit
falls with the entrance loss and then linearly with friction:

    p_s(x) = γ_w · max( z_s − (1 + K_u + f ξ/(4R)) U²/2g − z_cr , 0 ),   ξ = x − x_up(z_bp)   (5.8)

and p_s = 0 while the pipe is part-full (w = 0). The pressure is integrated exactly along the pipe;
it is not taken as uniform.

Only the soffit pressure acts on the roof block. Pressure on the side walls loads the intact soil
beside the pipe, and pressure on the floor loads the soil below, so neither is counted against the
roof — no hydraulic force is counted twice.

**Mechanism A — fall-in (roof collapse):**

    driving   D_A = γ_t b_p A_r + γ_w b_p A_w − b_p ∫ p_s dx
    resisting R_A = 2 c_u A_r
    FS_A = R_A / D_A;    collapse when FS_A ≤ 1                                            (5.9)

A_w is the area of the water wedge above the wetted part of the upstream face over the roof.
γ_w A_w is the vertical component of the hydrostatic force on that inclined face, used only in
mechanism A. Its horizontal component is the driving force of mechanism B. The resultant is never
counted in both.

**What the dry limit says.** Without the water terms, (5.9) gives

    b_p,crit = 2 c_u / γ_t

for any cover thickness, because both weight and side resistance grow with cover. This is the
cohesion-controlled, zero-friction limiting result of the simplified vertical-plane trapdoor
formulation. It does not reproduce Terzaghi's (1943) full arching solution, which includes friction
and stress redistribution, and §5.5a shows that its independence of cover is an artefact of the
mechanism.

Example: c_u = 10 kPa and γ_t = 20 kN/m³ give 1.0 m dry. With 10 m of cover and the soffit pressure
falling from 10 m of water at the inlet to zero at the outlet (mean 49 kPa), it rises to about 1.3 m,
before adding the water standing on the upstream face.

**Mechanism B — push-out (horizontal sliding of the roof block):**

    ½ γ_w max(z_s − z_cr, 0)² b_p  >  2 c_u A_r                                            (5.10)

**Factor of safety and signed imbalance.** Collapse is at FS = 1, the limit-equilibrium condition.
The event is decided from the signed force balance, not from the ratio: the margin M = resisting −
driving is computed and written every step with FS, and collapse occurs when M ≤ 0 with the driving
force acting in the mechanism's direction. If the soffit pressure exceeds the downward forces in
mechanism A, D_A ≤ 0 and FS_A is not defined. The roof is then pushed upward, which is mechanism C
over the whole roof, checked by F_C. A threshold other than 1 is
not a physical quantity — the uncertainty belongs in c_u — so FS_crit ≠ 1 is offered only in the
sensitivity analysis.

**Collapse time independent of the step.** The crossing FS = 1 is located inside the step by
linear interpolation of the margin (FS − 1), the step is redone to that instant, the collapse is
applied there and the step is finished on the new geometry — the event location already used for the
Part 4 residual block. The minimum FS before collapse is reported.

**Which strength.** c_u must represent the roof soil's moisture state, density, stress state and
loading rate at failure.
- Below the phreatic surface, a saturated undrained strength is used where measured.
- Above it, an as-compacted or unsaturated strength is used where available.
- Residual strength is not used: it applies to surfaces already sheared, not a new roof failure.

The case file records, for each c_u, the test (UCS, vane, triaxial UU, …), the saturation state and
the density. One value per saturation zone is the first-version simplification.

**Later, not now:** tension cracking of the roof (needs tensile strength, rarely available) and
friction on the side planes (a rigid block with K_0 friction overstates deep-roof stability compared
with Terzaghi's slice analysis).

---

## 5.5a Roof collapse — investigation before implementation (2026-11-24)

The rigid two-plane block (mechanism A) is kept only as a benchmark. Before a collapse criterion is
coded, the undrained stability of shallow openings in clay is being reviewed, because that literature
answers the same question — when does the soil over a void collapse — with rigorous bounds.

**The established framework.** For a plane-strain opening of width B and height D under cover C in
undrained clay, with surface surcharge σ_s and internal pressure σ_t, collapse is governed by the
stability number

    N = (σ_s − σ_t)/c_u  compared with  N_crit = f(C/B, D/B, γB/c_u)

following Broms and Bennermark (1967) and Davis et al. (1980). Upper and lower bounds on N_crit come
from finite element limit analysis and bracket the true collapse load within a few per cent:
- square tunnels: Assadi and Sloan (1991);
- wide rectangular tunnels: Abbo et al. (2013);
- tall tunnels: Wilson et al. (2014);
- rectangular tunnels with c_u increasing with depth: Wilson et al. (2017).

The mapping to the roof is direct: σ_t is the soffit water pressure p_s, σ_s is the water standing on
a submerged roof, B = b_p, D = a_p, and C is the cover.

**What this shows about the rigid block.** In the same terms, the two-plane block gives

    N_block = 2C/b_p − γC/c_u.

Its strength term grows linearly with cover. In the bounds, the weightless term grows only about
logarithmically with cover (circular tunnel fit: N_0 ≈ 1.5 ln(C/D) + 2.4; Wilson et al. 2011),
because a deep failure stays near the opening and does not shear the full height to the surface.
So for deep cover the block overstates the roof's strength. Its cover-independent critical width
2c_u/γ_t is an artefact of the mechanism. The bounds instead show that, with constant c_u, a deep
opening collapses once (γC − σ_t)/c_u exceeds the critical stability number, largely whatever its
width.

**Consequences to settle before coding:**
1. **Strength regime.** With constant c_u, any deep pipe is predicted to collapse early unless the
   pipe water pressure supports it. Example: 40 m of cover, c_u = 25 kPa and γ = 20 kN/m³ give
   γC/c_u = 32, far above typical critical values. The real fill strength increases with
   confinement. Three options:
   - c_u increasing with depth (covered by Wilson et al. 2017);
   - a drained (c′, φ′) analysis for pipes that develop over days in coarser soils, where friction
     and arching support the roof;
   - a time-scale criterion (consolidation time a_p²/c_v against pipe development time) that
     selects between them.
2. **Where collapse starts.** Cover varies along the pipe. The criterion is evaluated section by
   section, so the first section to reach its limit marks a local collapse (sinkhole) and its
   location. This is closer to observed piping failures than a full-length roof failure, and it
   affects the debris geometry (§5.7).
3. **Bounds data.** The FELA bounds are published as charts and tables. Using them needs either those
   tables (Abbo et al. 2013; Wilson et al. 2017; drained equivalents) interpolated in the code, or a
   rigid multi-block upper-bound mechanism derived and optimised here. An upper bound alone is on the
   unsafe side for a collapse prediction.
4. **Geometry differences.** The tunnel solutions assume a horizontal ground surface and plane strain
   across the pipe. The embankment's sloping faces and the variable cover must be handled by applying
   the solution at each section with its local cover, and the error of doing so stated.

Jafari and Fahimifar (2022) treat the *face* (heading) stability of rectangular shield tunnels, a 3-D
problem. They are relevant to the method but not to the cross-section collapse of the roof.

---

## 5.6 Exit mechanisms — the pipe shortens from the downstream end

**Mechanism C — downstream exit uplift (heave) of the cover.** This is the uplift of a defined soil
prism: the cover above the pipe, width b_p, thickness t(x) = z_dam(x) − z_cr, per unit length along the
pipe. It is *not* a criterion for backward erosion piping and does not predict its progression
(FEMA P-1032, 2015, warns against using the heave factor of safety that way).

**Free body of the prism (total stress).** The forces on the prism are:
- its weight γ_t b_p t;
- the water pressure on its top surface, p_top b_p;
- the soffit pressure from below, p_s b_p;
- shear on its two vertical sides, at most c_u t each.

Pore pressures inside the prism are internal forces in a total-stress free body, so they do not enter.
It lifts when

    F_C(x) = b_p (p_s(x) − p_top(x)) − γ_t b_p t(x) − 2 c_u t(x)  >  0                         (5.11)

- **Top boundary condition (review, 2026-11-24).** p_top is the external pressure on the prism's
  actual top surface:
  - hydrostatic, γ_w (z_s − z_dam), where that surface is the upstream face below the reservoir;
  - 0 where it is exposed to air — the crest and the downstream face, and the upstream face above
    z_s.

  The code uses exactly this piecewise boundary condition along the whole pipe.
- **Under the reservoir.** Two pressures act on the prism.
  - *On top* the water is still or slowly moving toward the inlet, with velocity v_top. By Bernoulli
    from the reservoir, p_top = γ_w (z_s − z_dam(x)) − ρ v_top²/2.
  - *Underneath*, (5.8) gives p_s = γ_w (z_s − z_cr) − ρ U²/2 · (1 + K_u + f ξ/(4R)).
  - Subtracting: p_s − p_top = γ_w t − ρ/2 [ U² (1 + K_u + f ξ/(4R)) − v_top² ].
  - If the velocity over the face is smaller than the velocity in the pipe (v_top < U), the bracket
    is positive. Hence p_s − p_top < γ_w t < γ_t t, and F_C < 0 at every point under the
    reservoir. v_top < U is a flow-field assumption, not a guaranteed condition, so the model uses
    v_top = 0 (hydrostatic top), and the local pressure drop in the approach flow right at the inlet is
    not represented.
  - Where (5.8) would give a negative soffit pressure, p_s is set to 0, a lower bound on a
    cavitating or separated flow. With p_top ≥ 0 that case gives p_s − p_top ≤ 0, so the bound still
    holds.

  The bound rests on four things: energy conservation (no point has more head than the reservoir),
  the loss terms in the pipe, v_top < U, and p_top ≥ 0 — the approach-velocity head over the face
  cannot exceed the water depth there. It does not rest on comparing γ_t with γ_w alone.

  **Numerical check, independent of the engine:** 905 300 random points (H 2–100 m, slopes, pipe
  size and position, n, K_u 0–0.5, c_u 0–50 kPa, γ_t 17–23 kN/m³, any v_top within the two limits)
  gave max F_C/(γ_t b_p t) = −0.49, i.e. no uplift anywhere. A first version of the check that let
  v_top exceed √(2g × water depth) produced spurious positive values from negative top pressures. That
  is why p_top ≥ 0 is listed as an assumption.

  Upstream "blow-out" is therefore the horizontal push-out of mechanism B, not uplift. The code does
  not rely on this result: F_C(x) is computed along the whole pipe, under the reservoir included,
  with v_top = 0 (the most adverse case for the prism). The free-body diagram is listed for an
  independent geotechnical check before publication.
- **Where the top is dry** (crest, downstream face): p_top = 0. Since p_s ≤ γ_w (z_s − z_cr) everywhere,
  uplift needs cover t < (γ_w/γ_t)(z_s − z_cr). Under the crest t = H − z_cr ≥ z_s − z_cr, so the crest
  cannot lift while the reservoir is below it. Near the outlet both p_s and t fall to zero. Uplift
  starts there only if the friction slope in the pipe exceeds the cover gradient:

      S_f = f U²/(8 g R)  >  (γ_t + 2 c_u/b_p) / (γ_w z_d)

  For c_u = 0 and z_d = 2, this needs S_f > 1, which is possible only in a very short or steep pipe.

  **Numerical check with this boundary condition (rerun, 2026-11-24):** 1.2 million points sampled
  over the upstream face, crest and downstream face of random dams. No point lifted (largest
  F_C/(γ_t b_p t): −0.45 upstream, −0.57 crest, −0.65 downstream). Mechanism C is therefore kept, but
  for dam-scale pipes it is expected to be rare.

With c_u = 0 and p_top = 0, (5.11) reads p_s > γ_t t. Writing p_s = γ_w (t + Δh), with Δh the excess
head over hydrostatic, this is Δh/t > (γ_t − γ_w)/γ_w = γ′/γ_w = i_cr. That is the classical
critical gradient for upward flow through a saturated cohesionless prism (Terzaghi 1943). The
correspondence holds for this prism geometry only.

γ_t is the unit weight of the cover as it is; saturated is the default, because the cover over a
flowing pipe is wetted from below.

Near the outlet both p_s and t fall to zero. Heave starts there if the pressure falls more slowly
along the pipe than the cover thins. When F_C > 0 over a reach ending at x_o, the cover over that reach
is removed (its volume enters the eroded budget, carried away by the jet). The outlet moves to the
upstream end of the reach (x_o decreases), and L_p shortens through (5.1).

**Exit headcut (optional, off by default; cohesive soils only).** The jet leaving the pipe erodes the
downstream face below the outlet, as in ARS P1. When switched on, the Part 4 machinery runs at the
outlet: surface erosion of the face below z_inv, then a plunging headcut once the drop exceeds d_c,
with q = Q_b/b_p. When the headcut brink passes x_o, the outlet moves with it, x_o = x_h.

Caution: the Robinson/Hanson relations were derived for a free overfall with critical depth at the
brink. A pipe jet leaves faster than critical. Using them here is an approximation that must be
tested.

- **Test case:** ARS P1, comparing headcut depth and retreat, pipe length over time, and time to
  collapse, with the mechanism on and off.
- **Not applied yet:** sandy soils and moraine. Their exclusion is a first-version choice, not a claim
  that exit scour cannot occur there.

**One geometry.** Mechanism C and the exit headcut both act only through x_o and the face downstream
of it. Pipe erosion acts only inside the pipe. After collapse, all erosion is handed to Parts 2–4. No
soil volume is eroded by two routines.

---

## 5.7 Collapse, the debris layer and the hand-over

**Where the roof goes.** At collapse (A or B) the roof block drops into the pipe below it. The block is
much larger than the pipe (cover ≫ pipe height), so the debris does **not** leave a clear notch down
to the pipe invert. Laboratory piping tests on landslide dams show the same thing: after the roof
collapsed, the lake rose until the flow could dislodge and carry the collapsed sediment (Okeke and
Wang 2016).

**Volume from solids.** The roof's solids volume is conserved:

    V_s = (1 − n) b_p A_r                     (intact roof, porosity n)
    V_d = V_s / (1 − n_d)                     (deposited debris, porosity n_d)                (5.12a)

n_d defaults to n, the block falling as intact pieces, so V_d = b_p A_r. Looser packing, n_d > n, is
part of the sensitivity analysis. Example: 10 m³ of solids at n_d = 0.40 occupy 16.7 m³.

**Deposition geometry — an explicit first-version assumption.** The debris is taken to settle as a
layer of uniform thickness along the slot of width b_p, filling it from z_inv up to z_d:

    b_p ∫_{z_inv}^{z_d} L(z) dz = V_d,    L(z) = x_down(z) − x_up(z),    z_d ≤ H            (5.12b)

The real deposit depends on where the roof breaks, whether it piles near the break, and how much the
flow carries off at once. A wedge or a local mound are later options. With n_d = n and a slot of
nearly constant length, the slot column loses exactly the pipe volume, so z_d ≈ H − a_p. This is a
consequence of the geometry, not a general rule. If loose debris would rise above the crest, z_d is
capped at H and the excess is set beside the slot as spoil (counted in the solids budget).

**The debris is part of the hydraulics from the first step.** The breach after collapse is a notch of
width b_p from the crest down to the debris surface z_d. The debris layer z_inv–z_d is the notch's
bed, and the weir control sits on it. Flow area, hydraulic radius, resistance, discharge and the
exposed (wetted) debris area all come from that geometry. The reservoir first sees a shallow opening —
the "temporary dam" — which deepens as the flow erodes the debris. No separate timer or virtual tank
is needed.

**Blocking criterion.** The same geometry decides whether the collapse blocks the flow:
- **z_s > z_d:** flow continues over the debris as a weir.
- **z_s ≤ z_d:** the collapsed roof has closed the open flow path.

What happens next depends on the boundary conditions:
- **With inflow** the reservoir rises until it overtops the debris. Okeke and Wang (2016) observed
  this in landslide-dam piping experiments, which had a continuous upstream supply.
- **With a constant-head supply** — the ARS tests held the reservoir level steady (USBR PAP-1017) —
  the level stays put, so the opening stays closed unless z_s > z_d.
- **Without inflow** the breach stops, and the run reports a "sealed" outcome.

Sealing under zero inflow is a **model prediction**, not an observed result: no experiment cited here
tested it. It rests on two stated assumptions:
- the debris is impermeable enough that seepage through it cannot re-form a pipe;
- there is no other water supply.

Internal-erosion guidance recognises that collapse can temporarily stop pipe development
(Reclamation/FERC 2010), which makes the prediction plausible but does not test it.

Since z_d ≈ H − a_p (with n_d = n), the outcome follows from comparing the pipe height at collapse
with the freeboard H − z_s.

**Protocol if a historical breach comes out sealed (e.g. Teton).** No seepage mechanism is added first.
The run's collapse time, pipe height, debris elevation and reservoir level are compared with the
historical evidence, to find which assumption fails. Seepage-driven re-piping through the debris
remains a later option, to be added only if that inspection points to it.

**Erosion of the debris.** It follows the bed laws:

- **Cohesive:** detachment-limited, k_d(τ − τ_c). Detached fines travel as wash load (Part 2).
- **Non-cohesive:** transport-limited by the Part 2 capacity, so material detached beyond capacity
  stays in place. That is the "mobile store" the review asked for, already built into a
  capacity-limited law.

Detachment and transport are therefore separate where they need to be: cohesive debris is
detachment-limited, and non-cohesive debris is transport-limited. A separate "mobile sediment" store
would only matter where detached material lingers in the breach. Here it is either carried as wash
load (cohesive) or never detached beyond capacity (non-cohesive).

**Applicability caution.** The bed laws were set for intact, compacted soil. A loose, freshly collapsed
deposit is not the same material. Debris erodibility defaults to the intact soil's, because no case
has debris data. Remoulded soil is usually more erodible, so k_d,debris higher, τ_c,debris lower and
n_d higher are tested in the sensitivity analysis. Below z_inv the bed is intact soil again.

**Solids budget.** Tracked as solids volumes, closed to round-off every step:

    V_s,collapsed = V_s,debris remaining + V_s,exported (+ V_s,spoil)                         (5.13)

"Exported" means carried out of the breach. Deposition downstream is outside the model (there is no
downstream reach), so exported material is not followed further.

**Discharge at the collapse.** Outflow changes at the collapse instant because the controlling
geometry changes: pipe flow before, weir over the debris after. That change is physical, not a
numerical artefact, so it is not smoothed or ramped. The collapse instant is event-located (§5.5), so
the hydrograph does not depend on the step. After the collapse, the discharge varies continuously as
the debris erodes.

**Comparison modes.** These show how much the collapse treatment matters:
- **DL Breach's virtual tank** opens the notch to the invert at once but freezes the geometry until
  the tank is emptied.
- **Instant removal** gives the most open passage at first. It is not necessarily an upper bound on
  every output, because peak flow and timing also depend on drawdown and later erosion.

**Hand-over state.** These carry over unchanged (same engine state):
- reservoir volume, level and inflow;
- cumulative water and sediment balances;
- time;
- the pipe width as notch width b = b_p;
- notch bed z_b = z_d, with the debris layer down to z_inv and its solids budget;
- the intact walls.

Wall angles come from Part 3: vertical only while a vertical bank of that height stands, otherwise
the bank-stability angle. Then:
- **cohesive soils with k_d** enter Part 4 at stage 1 (notch bed z_d, brink at x_down(z_d));
- **non-cohesive soils** enter Parts 2–3.

There are no post-piping erosion rules and no width ramp.

---

## 5.8 Inputs, safeguards and the cases that test this part

**Case-file inputs (`mode: "piping"`):**
- pipe width and height;
- invert elevation **above the dam base** — converted from depth below the crest if the source gives
  depth;
- `invert_source`: `measured` | `estimated` | `scenario`;
- c_u for the roof;
- k_d and τ_c with `erodibility_test`: `HET` | `JET`;
- optional n_p, n_d (debris porosity), k_d,debris, τ_c,debris.

**Safeguards (errors, not warnings):**
- 0 ≤ z_inv;
- z_inv + a_p < H − (minimum cover), so the roof cover is positive;
- a given invert is used exactly — no estimate may replace it.

**Missing location.** Where the source gives no invert, the case runs at base, mid-height and upper
positions. Its source is recorded as `scenario`, and it stays out of primary validation (supporting
evidence only). The base position is not assumed to be the worst case: a lower pipe has more head but
more cover and a different collapse time, so the largest peak can come from any position.

**Cases (Phase 4 assembles; the blind subset is pre-registered before any scoring):**

| case | type | why | status |
|---|---|---|---|
| ARS P1, P2, P3 (Hanson et al. 2010a) | lab, ~1.3 m (P1), JET and HET k_d (Wahl 2010) | measured erodibility, collapse 0.23–20.5 h, P1 exit headcut | data to obtain |
| ARS intermediate-scale tests (Ali et al. 2021) | lab, 4 embankments | pipe enlargement rates over orders of magnitude | data to obtain |
| Big Bay, MS (2004) | field, 15.6 m | international benchmark (FWR6124), DL Breach card on file | card on file |
| Teton, ID (1976) | field, 93 m | classic piping failure, DL Breach card on file | card on file |
| IMPACT field test 5 (2003) | field, 4.3 m, moraine | piping in a coarse cohesive soil; links to Part 7 | workbook on file |
| Wahl (1998) cases in Wu (2016) Table 6.8 | field | many values "assumed" in DL Breach | supporting only |

**Verification this part must pass (Phase 3):**

| test | expected |
|---|---|
| (5.2) | equals 1.705 b HW^1.5/√(1+K_u) for HW ≤ 1.5 D |
| (5.3)–(5.4) | Q_b non-decreasing in HW except the reported priming step; Q_o ≤ Q_i always once full; priming step down for F > 1.05, up (≤ √2) for F < 1.05; (5.3) → (1.9) for a long full pipe |
| (5.5) | τ_p → ρ g R Δh/L_p when f L_p/4R ≫ K_u + K_d |
| (5.6)–(5.7) | no growth below τ_c; roof fixed while w = 0; eroded volume = wetted area × ε dt exactly |
| (5.9) | dry limit gives b_crit = 2c_u/γ_t for any cover; FS_A written every step |
| (5.11) | F_C computed along the whole pipe; < 0 everywhere under the reservoir for random geometries and flows (property test); c_u = 0, p_top = 0 gives Δh/t > γ′/γ_w |
| (5.12) | solids conserved: V_d (1 − n_d) = (1 − n) b_p A_r to 1e-12; z_d ≈ H − a_p for n_d = n, constant L |
| (5.13) | solids budget closes every step to 1e-12 |
| blocking | z_s ≤ z_d: no inflow → zero outflow, reported as sealed; inflow → reservoir rises and overtops the debris |
| collapse time | event-located; collapse time converges with p ≈ 1 in dt |
| hand-over | Part 4/Parts 2–3 start from z_d with no change in reservoir state; water balance < 1e-9 |
| locations | supplied invert used exactly; `scenario` cases excluded from primary validation |
| dt convergence | Qp, Tp and collapse time with p ≈ 1 on the piping cases |
| exit headcut | on/off comparison on ARS P1 (pipe length, headcut retreat, collapse time) |

---

## 5.9 Decisions (draft 4, after the reviews of 2026-11-24)

1. **Pipe shape**: rectangle, starting square. Hydraulics from actual area and wetted perimeter.
   Erosion only on wetted surfaces, so width and height evolve independently. *(Review adopted; the
   draft-1 claim "same R_h ⇒ same flow" withdrawn.)*
2. **Pipe flow**: inlet control from the maximum-discharge principle at the entrance below the roof,
   and a rounded pressurised entrance above it (no submergence threshold), and outlet control
   (entrance + friction + exit losses, tailwater term), taking the smaller; outlet control always
   governs once full. Priming is a physical step, event-located and reported, upward for short pipes
   (F < 1.05). Pipe n_p defaults to the breach n and is
   tested separately. *(Reviews adopted; the 1.2 D threshold and the draft-1 weir-for-submerged-inlet
   example withdrawn.)*
3. **Wall shear and erodibility**: friction-only momentum shear (5.5), recomputed every step. HET k_d
   and τ_c preferred, JET used with its source recorded and a conversion tested. τ_c kept separate.
   Sellmeijer is a future module. *(As reviewed.)*
4. **Roof stability**: *under investigation (§5.5a).* The rigid two-plane block (A) and push-out (B)
   are kept as benchmarks; the collapse criterion to be coded will come from the undrained (and,
   where justified, drained) stability-number framework with published limit-analysis bounds. As
   reviewed: soffit pressure integrated along the pipe with no double counting; water force resolved
   into its vertical (A) and horizontal (B) components. FS = 1 at collapse, event-located inside the step, with FS and its
   minimum reported. FS_crit ≠ 1 for sensitivity only. c_u from the state the roof is in, with its
   source recorded. Tension cracks later; side friction for sensitivity only. *(Both reviews agree.)*
5. **Downstream exit uplift (heave)**: a separate mechanism C, defined by a free body of the cover
   prism. An energy bound shows it cannot act under the reservoir, but the code computes F_C along the
   whole pipe and does not rely on that. It shortens the pipe from the outlet. It is named and bounded
   as prism uplift, not a backward-erosion-piping criterion. Independent check of the free body
   before publication. *(Reviews adopted.)*
6. **Fallen roof**: a debris layer from conserved solids, V_d = (1 − n) b_p A_r/(1 − n_d), settled
   uniformly in the slot (an explicit assumption). Its surface is the new weir control, so it obstructs
   the flow from the first step. It blocks the flow when z_s ≤ z_d; the reservoir must rise to
   overtop it, and with no inflow the run ends sealed (a labelled model prediction, under stated
   impermeability and no-other-supply assumptions; no seepage mechanism before the Teton
   inspection). It erodes by the bed laws, and the solids budget is closed every
   step. n_d = n and debris erodibility = intact by default, all tested. Virtual tank and instant
   removal are kept as comparison modes. *(Second review's solids/porosity, deposition and budget
   adopted; blocking criterion added.)*
7. **Exit headcut**: optional, cohesive only, off by default until the ARS P1 on/off test. It reuses
   the Part 4 relations with the pipe discharge and moves the outlet x_o. *(As reviewed.)*
8. **Pipe location**: always an input with a recorded source, checked for positive cover. A missing
   location gives three `scenario` runs kept out of primary validation. The base is not assumed
   worst-case. *(As reviewed.)*

---

## References

- Ali, A. K., Hunt, S. L., Tejral, R. D., et al. (2021). Embankment breach research: observed internal
  erosion processes. *Trans. ASABE*. doi:10.13031/trans.13701.
- Atkinson, A., and Neilsen, M. (2024). Analysis of uncertainty in internal erosion simulations for
  DLBreach and WinDAM C. *GeoHazards*, 5(2), 18.
- Fread, D. L. (1988, rev. 1991). *BREACH: An erosion model for earthen dam failures*. NWS.
- Hanson, G. J., Tejral, R. D., Hunt, S. L., and Temple, D. M. (2010a). Internal erosion and impact of
  erosion resistance. *Proc. 30th USSD Conf.* (as cited in DSO-2017-02).
- HR Wallingford (2025). *Breach Model Validation Programme — Internal erosion initiated breach*.
  FWR6124-RT001 R01-00.
- Hunt, S. L., Temple, D. M., Neilsen, M. L., Ali, A., and Tejral, R. D. (2021). WinDAM C. *Appl. Eng.
  Agric.*, 37(3), 523–534.
- Davis, E. H., Gunn, M. J., Mair, R. J., and Seneviratne, H. N. (1980). The stability of shallow
  tunnels and underground openings in cohesive material. *Géotechnique*, 30(4), 397–416.
- FEMA (2015). *Evaluation and Monitoring of Seepage and Internal Erosion*. FEMA P-1032 (heave vs
  backward erosion piping).
- Abbo, A. J., Wilson, D. W., Sloan, S. W., and Lyamin, A. V. (2013). Undrained stability of wide
  rectangular tunnels. *Computers and Geotechnics*, 53, 46–59. doi:10.1016/j.compgeo.2013.04.005.
- Assadi, A., and Sloan, S. W. (1991). Undrained stability of shallow square tunnel. *J. Geotech. Eng.*,
  117(8), 1152–1173.
- Broms, B. B., and Bennermark, H. (1967). Stability of clay at vertical openings. *J. Soil Mech.
  Found. Div.*, ASCE, 93(SM1), 71–94.
- Chow, V. T. (1959). *Open-Channel Hydraulics*. McGraw-Hill. Ch. 3 (specific energy, critical flow,
  maximum discharge).
- Norman, J. M., Houghtalen, R. J., and Johnston, W. J. (1985). *Hydraulic design of highway
  culverts*. HDS-5, FHWA (inlet and outlet control concepts).
- Okeke, A. C.-U., and Wang, F. (2016). Hydromechanical constraints on piping failure of landslide
  dams: an experimental investigation. *Geoenvironmental Disasters*, 3, 4.
  doi:10.1186/s40677-016-0038-9.
- Reclamation / FERC (2010). *Dam Safety Risk Analysis Best Practices — Internal Erosion*.
- Terzaghi, K. (1943). *Theoretical Soil Mechanics*. Wiley. Arching (trapdoor) and heave.
- USBR (2019). *Best Practices in Dam and Levee Safety Risk Analysis*, Ch. D-6 Internal Erosion
  Risks for Embankments and Foundations (roof support, progression, heave).
- USBR PAP-1000. Wahl, T. L., Hanson, G. J., and Regazzoni, P.-L. Quantifying erodibility of
  embankment materials for the modeling of dam breach processes (JET vs HET).
- Wahl, T. L. (2010). Relating HET and JET test results to internal erosion field tests. *Joint
  Federal Interagency Conf. on Sedimentation and Hydrologic Modeling*, Las Vegas. USBR PAP-1017.
- Wahl, T. L., Regazzoni, P.-L., and Erdogan, Z. (2008). *Determining erosion indices of cohesive
  soils with the hole erosion test and jet erosion test*. DSO-08-05, Bureau of Reclamation.
- Wahl, T. L., et al. (2017). DSO-2017-02, Bureau of Reclamation.
- Wan, C. F., and Fell, R. (2004). Laboratory tests on the rate of piping erosion of soils in
  embankment dams. *Geotech. Testing J.*, 27(3), 295–303.
- Jafari, P., and Fahimifar, A. (2022). Upper-bound face stability analysis of rectangular
  shield-driven tunnels in undrained clays. *Computers and Geotechnics*, 146.
- Wilson, D. W., Abbo, A. J., Sloan, S. W., and Lyamin, A. V. (2011). Undrained stability of a circular
  tunnel where the shear strength increases linearly with depth. *Can. Geotech. J.*, 48.
- Wilson, D. W., Abbo, A. J., and Sloan, S. W. (2014). Undrained stability of tall tunnels. *Proc. 14th
  IACMAG*, Kyoto, 447–452.
- Wilson, D. W., Abbo, A. J., Sloan, S. W., and Yamamoto, K. (2017). Undrained stability of rectangular
  tunnels where shear strength increases linearly with depth. *Can. Geotech. J.*, 54(4), 469–480.
- Wu, W. (2016). *Introduction to DLBreach*, v2016.4. §2.2, §3.2, §4.7, §6.4.
