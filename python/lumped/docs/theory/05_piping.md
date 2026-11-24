# Theory, Part 5 — Breach initiated by internal erosion (piping): pipe enlargement and roof collapse

*Lumped 1-D morphodynamic breach model · draft 4.9 · 2026-11-24 · status: strength regime decided (undrained, c_u increasing with depth); roof criterion (§5.5b) and collapse-spreading rule (§5.7a) written for review; crater-wall height verified (5.17); 3-D crater-edge assumption stated as an unverified limitation, with a 3-D bound as a conditional pre-publication task (§5.8)*

*What is verified and what is not.* The limit-analysis code is verified as a numerical method: its bounds
bracket an exact solution and published bounds (§5.5a, §5.5b). That does not verify Part 5. Whether a
dam pipe roof behaves like the idealised plane-strain opening, and whether the hydraulics, erosion and
debris rules reproduce observed pipe growth, collapse timing, blockage and outflow, can only be shown
against the ARS experiments and field cases (§5.8).
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

*Validation target, not an assumption to defend.* (5.7) applies the same law to floor, walls and roof.
They may differ physically: eroded grains can settle back on the floor, and a wetted roof can also lose
soil by sloughing, not only by shear erosion. The ARS tests reported the evolving pipe shape, so the
ratio of height to width growth is a test of (5.7), not a tuning target.

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

   **Decided (draft 4.6): undrained, with c_u increasing with depth, c_u = c_u0 + ρ d** (§5.5b).
   Constant c_u is the case ρ = 0. A drained criterion is deferred until the model has a
   pore-pressure field around the pipe (arching consequence 4).
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

**Arching (checked 2026-11-24).** Terzaghi's (1943) arching analysis gives the vertical stress on the
base of a strip of half-width B = b_p/2 above an opening, with friction on its sides:

    σ_v(C) = B (γ − c/B)/(K tan φ) · (1 − e^(−K tan φ · C/B)) + q e^(−K tan φ · C/B)

The roof stands while σ_v(C) ≤ σ_t, the support at the soffit. Four consequences follow:
1. **No friction, no arching.** With φ = 0 (undrained, total stress) the formula becomes
   σ_v = (γ − c_u/B) C + q, which is exactly the two-plane block of mechanism A. Mechanism A is
   Terzaghi's undrained limit. It contains no arching.
2. **With friction, the load on the roof is capped.** For φ′ > 0, σ_v tends to B(γ − c′/B)/(K tan φ′)
   as cover grows, so a deep pipe does not carry more load than a shallow one. Example: b_p = 1 m,
   γ = 20 kN/m³, c′ = 5 kPa, φ′ = 30°, K = 1 caps the support needed at 8.7 kPa for any cover
   (17.3 kPa with c′ = 0).
3. **Arching does not hold an unsupported roof.** σ_v ≤ 0 still needs γB ≤ c, i.e. b_p ≤ 2c/γ, at
   any φ. Arching reduces the support a roof needs; it does not remove the need for cohesion,
   cementation or suction in an open void. That is "a pipe needs a roof" again.
4. **In a drained analysis the pipe water is not support by itself.** In effective stress, the water
   in the pipe matches the pore pressure at the soffit. It holds the roof only through the seepage
   field. Water flowing from the surrounding soil into a lower-pressure pipe drags the roof toward
   it, which destabilises it. A drained arching criterion therefore needs the pore-pressure field
   around the pipe, which the lumped model does not have yet.

Arching also depends on displacement: centrifuge tests of a yielding trapdoor measured how the load
changes as the door moves (Iglesia, Einstein and Whitman 2014). The arching that a slowly enlarging
pipe mobilises is therefore not fixed.

**The three idealisations disagree.** Same opening (b_p = a_p = 1 m, γ = 20 kN/m³, no support):

| cover C | block = Terzaghi φ = 0, c_u = 25 kPa | Terzaghi drained, c′ = 5 kPa, φ′ = 30° | undrained bounds, c_u = 25 kPa (circular fit) |
| --- | --- | --- | --- |
| 2 m | stable at any depth | collapses unless ≥ 7.8 kPa support | stable |
| 10 m | stable | collapses unless ≥ 8.7 kPa support | collapses |
| 40 m | stable | collapses unless ≥ 8.7 kPa support | collapses |

The undrained-bounds column uses the closed-form fit of Wilson et al. (2011) for a circular tunnel,
for illustration only; its coefficients are to be checked against the paper. The table shows why the
strength regime (consequence 1 above) must be settled first: it decides whether a deep pipe's roof is
stable, needs a few kPa of support, or collapses outright.

**Upper- and lower-bound limit analysis (computed here, 2026-11-24).** To check the rigid block
against the bound theorems directly, finite element limit analysis was written for this problem
(`verification/fela_roof.py`). The setup is a plane-strain section across the pipe; the ground
surface in that section is horizontal (along the crest), so the tunnel framework applies there
without a sloping-surface correction. The opening is rectangular, of width B and height D, under
cover C, in Tresca clay with self-weight, with no internal pressure (σ_t = 0).

- **Lower bound:** linear stress triangles with a statically admissible discontinuity on every edge,
  and Tresca yield as a second-order cone at every node. It maximises the surface surcharge.
- **Upper bound:** linear velocity triangles on a crossed mesh, which avoids incompressibility locking,
  with far boundaries fixed. It minimises dissipation minus gravity power for unit surface flux.

Both are solved by conic programming (Clarabel). The result is the stability number
N = (σ_s − σ_t)/c_u at collapse.

Mesh check, at C/B = 2, D/B = 1, γB/c_u = 1, as the mesh size h goes 0.2 → 0.15 → 0.1 → 0.07:
- lower bound 0.664 → 0.678 → 0.681 → 0.691;
- upper bound 0.908 → 0.874 → 0.846 → 0.835.

Results at h = 0.1 for a square opening (D/B = 1). An opening with nothing inside it (σ_s = σ_t = 0)
collapses when N < 0:

| C/B | γB/c_u | FELA lower bound | FELA upper bound | rigid block (= Terzaghi φ = 0) |
| --- | --- | --- | --- | --- |
| 0.5 | 1 | 0.44 | 0.60 | 0.50 |
| 1 | 1 | 0.83 | 0.96 | 1.00 |
| 2 | 1 | 0.68 | 0.85 | 2.00 |
| 4 | 1 | −0.26 | −0.07 | 4.00 |
| 8 | 1 | −3.02 | −2.81 | 8.00 |
| 1 | 0 | 1.90 | 2.08 | 2.00 |
| 4 | 0 | 4.07 | 4.26 | 8.00 |
| 8 | 0 | 5.38 | 5.58 | 16.00 |
| 4 | 0.5 | 1.91 | 2.10 | 6.00 |
| 8 | 2 | −11.53 | −11.31 | 0.00 |

The full sweep (C/B = 0.5–8, γB/c_u = 0–2, D/B = 1 and 0.5) is in
`verification/fela_roof_sweep.txt`. Findings:
1. **Shallow cover (C/B ≤ 1):** the rigid block falls inside the bounds, so it is a good mechanism there.
2. **Deeper cover:** the block grossly overstates the roof's strength. At C/B = 4 and γB/c_u = 1 the
   block gives N = 4, a stable unsupported roof, while the bounds give −0.26 to −0.07: the roof
   collapses unless supported.
3. **The critical width depends on cover.** For an unsupported square opening the bounds put collapse
   at about:
   - C ≈ 0.5 B when γB/c_u = 2 (the block's own limit, b = 2c_u/γ);
   - C ≈ 3.7 B when γB/c_u = 1;
   - beyond 8 B when γB/c_u = 0.5.

   The block predicts no dependence on cover.
4. **Limitations.** The first code (`fela_roof.py`) left the lower bound's far boundaries free, so its
   lower bounds were not rigorous. Version 2 (`fela_v2.py`, below) corrects this and is validated.
   The numbers in the table above are unchanged by the correction to the reported precision. The
   upper bound has no velocity discontinuities, so the bracket is 10–25 % wide for the square
   opening, and in shallow cases the rigid block is the better upper bound.
5. **Path to the engine.** Precompute N_crit(C/B, D/B, γB/c_u) with this code over the parameter
   space, tighten it (velocity discontinuities, adaptive mesh), validate it against the published
   bounds, and interpolate the table in the engine. The roof criterion is then evaluated section by
   section along the pipe, with σ_t the water pressure acting on all walls of the full pipe. Each
   case takes about 1–8 s, so the table is cheap to build. A drained (Mohr–Coulomb) version is
   possible with the same machinery, since its yield condition is also a second-order cone, but it
   needs the seepage pore pressures (arching consequence 4 above).

**Verification of the bound code (version 2, 2026-11-24).** After review, the code was audited
against the bound theorems themselves, not only by mesh convergence.

*Review of the formulation.*
- **Upper bound: correct as written.**
  - Velocity is zero on the far boundary, so the field extends by zero to the infinite domain.
  - Incompressibility holds exactly in every element.
  - The dissipation is c_u·√((ε̇_xx − ε̇_zz)² + γ̇_xz²) per unit area, the Tresca plane-strain value.
  - The surcharge and gravity powers have the right signs.
- **Lower bound: the far field was not admissible.** Version 1 left the side and bottom boundaries
  traction-free. A static field is a lower bound only if it can be extended to the whole half-space
  in equilibrium and within yield, and a free boundary does not guarantee that.
- **Fix: an exact extension, built analytically.** Beyond the side x = X:
  σ_zz = γz − σ_ext, σ_xz = 0, σ_xx = g(z). Below the bottom z = −Z:
  σ_zz = γz − σ_ext + f(x), σ_xz = 0, σ_xx = γz − σ_ext + k. Here σ_ext is the surcharge beyond the
  mesh. Both fields satisfy equilibrium identically, and they stay within yield to infinite depth if:
  - **side:** σ_xz = 0 and |σ_xx − (γz − σ_ext)| ≤ 2c_u;
  - **bottom:** σ_xz = 0, |σ_zz + γZ + σ_ext − k| ≤ 2c_u and |k| ≤ 2c_u.

  The bottom band lets the base carry the weight missing from the opening. These conditions,
  imposed at the boundary nodes, make the lower bound rigorous without extension elements.
- **Yield margin.** Yield is imposed at (1 − 10⁻⁵)c_u, so the solver's feasibility error cannot carry
  the field past c_u.
- **Redundant equations.** Wherever two straight element edges cross at a node, one
  traction-continuity equation follows from the others, because the stress tensor is symmetric. Every
  crossed-quad centre has such a node. The redundant rows made the interior-point solve unstable:
  with the solver's backup, some cases took 13–53 min. They are now removed node by node with a
  pivoted QR; the continuity rows at a node involve only the stresses at that node. Each case then
  solves in 1–30 s.

*Independent audit of every solution.* After each solve the returned fields are checked directly,
without using the optimiser's objective or constraint matrices:
- **Lower bound:** element equilibrium; the traction jump on every interior edge at every node;
  every boundary condition; yield at every node; the far-field bands.
- **Upper bound:** volumetric strain rate; boundary velocities; the bound recomputed from the
  velocity field.

All residuals are below 3·10⁻¹⁰, and there is no yield excess.

*Benchmarks* (`verification/fela_benchmarks.py`, results in `fela_benchmarks.txt`, h = 0.1):

| Problem | Our lower bound | Our upper bound | Reference |
| --- | --- | --- | --- |
| Smooth strip footing, weightless (h = 0.05) | 4.469 | 5.241 | exact 2 + π = 5.142 (Prandtl 1920) |
| Circle, C/D = 1, γD/c_u = 0 | 2.424 | 2.456 | 2.43–2.45 (Wilson et al. 2011) |
| Circle, C/D = 2, γD/c_u = 0 | 3.440 | 3.486 | 3.45–3.48 |
| Circle, C/D = 3, γD/c_u = 0 | 4.109 | 4.176 | 4.12–4.16 |
| Circle, C/D = 1, γD/c_u = 1 | 1.243 | 1.272 | 1.25–1.26 |
| Circle, C/D = 2, γD/c_u = 1 | 1.165 | 1.213 | 1.17–1.20 |
| Circle, C/D = 3, γD/c_u = 1 | 0.782 | 0.846 | 0.79–0.84 |
| Circle, C/D = 1, γD/c_u = 2 | 0.008 | 0.041 | 0.01–0.03 |
| Circle, C/D = 2, γD/c_u = 2 | −1.180 | −1.134 | −1.17 to −1.15 |
| Circle, C/D = 3, γD/c_u = 2 | −2.622 | −2.561 | −2.62 to −2.57 |

- **Pass criterion.** Two valid pairs of bounds must overlap: our lower bound must not exceed theirs
  as an upper bound, and our upper bound must not fall below theirs as a lower bound. All ten cases
  pass, and our bounds lie within 0.1–2 % outside Wilson et al.'s. Their meshes carry about 10⁵
  elements with velocity discontinuities; ours carry 4–8·10³.
- **H read as the cover.** Wilson et al. write H for the "tunnel depth". The agreement confirms they
  mean the cover above the crown.
- **The circular tunnel tests the same code as the square opening.** It uses the same element
  formulation, boundary conditions and far field; only the mesh differs. So the square-opening
  results above stand on validated code.
- **Square opening, rerun with version 2.**
  - Lower bounds: 0.442, 0.833, 0.681 and −0.261 at C/B = 0.5, 1, 2 and 4 (γB/c_u = 1).
  - These are the same as version 1 to three decimals, so the free far boundary happened not to
    matter in these domains.
  - At C/B = 2 with h = 0.05: lower bound 0.697, upper bound 0.827.
- **Still to do.** Compare with a published *square* table once Abbo et al. (2013) or Wilson et al.
  (2013) is obtained.

*Where the plane-strain section applies in the embankment.* The section is cut across the pipe, so it
lies parallel to the dam axis, and there its ground surface is horizontal. The trapezoidal shape of
the embankment enters in three other ways:
1. **Cover changes along the pipe**, from full crest cover to the thin cover under the slopes. Each
   section is checked with its own cover. This ignores support from neighbouring sections (3-D end
   effects), which is expected, but not shown, to be conservative for a short collapse length while the
   neighbours are intact (see §5.7a, route 2, for a crater edge).
2. **Out-of-plane shear under the slopes.** Under a slope of angle β, gravity sets up an in-situ shear
   stress along the pipe axis, about γ·z·sin β·cos β at depth z below the surface. It uses up part of
   the undrained strength before the section is loaded, and the plane-strain analysis does not see
   it. This is unconservative. A first correction is to reduce c_u in the section to
   √(c_u² − τ_axial²), the Tresca strength left for in-plane shear. It is to be checked against a
   3-D or generalised plane-strain analysis before use.
3. **The outlet face.** Near the downstream exit the mechanism becomes three-dimensional (face
   collapse, Jafari and Fahimifar 2022), and the section analysis does not apply there. That zone is
   covered by the exit mechanisms of §5.6.

Jafari and Fahimifar (2022) treat the *face* (heading) stability of rectangular shield tunnels, a 3-D
problem. They are relevant to the method but not to the cross-section collapse of the roof.

---

## 5.5b Roof collapse criterion — undrained, c_u increasing with depth (draft 4.6, for review)

**Strength profile.** In each cross-section the undrained strength increases linearly with depth d
below that section's ground surface:

    c_u(d) = c_u0 + ρ d                                                                   (5.14)

- c_u0 is the strength at the surface and ρ (kPa/m) the rate of increase. Both are case inputs with
  their source recorded (§5.5 "Which strength"). ρ = 0 recovers constant c_u.
- **Why depth-dependent.** In compacted fill, confinement grows with depth and undrained strength
  with it. With constant c_u every deep pipe is predicted to collapse early (§5.5a, consequence 1).
- **Dimensionless form.** The section is described by C/b_p, a_p/b_p, γ b_p/c_u0 and ρ b_p/c_u0
  (Wilson et al. 2011, 2013, 2017 use the same set).

**c_u(z) in the bound code** (`verification/fela_v2.py`, functions `lower_bound` and `upper_bound` with
`rho`):
- **Lower bound:** the yield limit at each node is c_u(d) at that node. The far-field conditions of
  §5.5a use c_u(d) beyond the side. Below the bottom they use c_u at the bottom, which is the weakest
  point of that region since ρ ≥ 0.
- **Upper bound:** the dissipation in each element is c_u(d) × the constant shear-strain rate,
  integrated exactly (c_u is linear in d, so the element integral is the area × c_u at the centroid).

Benchmark against Wilson et al. (2011), Table A1/A2 (circular tunnel; their r D/c_u0 = our ρ D/c_u0;
mesh h = 0.1; `verification/fela_rho_benchmark.py`, results in `fela_rho_benchmark.txt`):

| C/D | ρD/c_u0 | γD/c_u0 | our lower–upper | Wilson et al. lower–upper |
| --- | --- | --- | --- | --- |
| 1 | 0.25 | 0 | 2.918–2.965 | 2.93–2.95 |
| 1 | 0.25 | 2 | 0.602–0.638 | 0.61–0.63 |
| 1 | 1.00 | 0 | 4.318–4.406 | 4.33–4.37 |
| 1 | 1.00 | 2 | 2.082–2.161 | 2.10–2.13 |
| 2 | 0.25 | 0 | 4.829–4.892 | 4.83–4.88 |
| 2 | 0.25 | 2 | 0.381–0.445 | 0.39–0.43 |
| 2 | 0.50 | 1 | 3.983–4.062 | 3.99–4.04 |
| 2 | 1.00 | 0 | 8.793–8.914 | 8.80–8.87 |
| 2 | 1.00 | 2 | 4.455–4.571 | 4.46–4.54 |
| 3 | 0.25 | 0 | 6.594–6.691 | 6.60–6.68 |
| 3 | 0.25 | 2 | 0.078–0.183 | 0.09–0.17 |
| 3 | 0.50 | 3 | −0.707 to −0.576 | −0.70 to −0.59 |
| 3 | 1.00 | 0 | 13.747–13.916 | 13.75–13.91 |
| 3 | 1.00 | 2 | 7.344–7.513 | 7.34–7.51 |

All 14 overlap (pass). Our brackets enclose theirs, slightly wider, and every independent audit
residual is below 2·10⁻⁸. The strength gradient matters a great deal: at C/D = 3 and γD/c_u0 = 2,
raising ρD/c_u0 from 0 to 1 lifts the stability number from about −2.6 to about +7.4.

**The pipe water pressure on the walls.** The stability number uses one internal pressure σ_t. A real
pipe section does not have one:
- **full:** the pressure increases hydrostatically from the crown to the invert, by γ_w a_p;
- **part-full:** the water presses on the floor and the wetted walls, and the roof is dry.

The bound code now applies the actual pressure as a traction on the opening walls:
- **Lower bound:** σ·n = −p n on each opening edge, with n the outward normal of the soil.
- **Upper bound:** the power of the water, −∫ p (n·v) ds, integrated exactly along each edge.

Checks:
- A uniform pressure q shifts both bounds by exactly q (C/B = 2: 0.681 → 1.181 and 0.846 → 1.346).
- With a crown pressure of 3 c_u0 added to the hydrostatic profile, both bounds shift by exactly 3.

**Two different statements, one exact and one approximate (review of draft 4.6).**

*Exact: the shift.* Adding the same pressure q to the surface and to every opening wall adds −q I to
the stress field. That changes neither equilibrium nor Tresca yield, because undrained Tresca strength
does not depend on mean stress. So the collapse condition depends on σ_s − p_cr only, for any crown
pressure, however large it is relative to c_u0. Checked numerically, with the hydrostatic profile
included (C/B = 4, γB/c_u0 = 2, γ_w B/c_u0 = 1): p_cr = 0, 10 and 50 c_u0 give the same bounds on
σ_s − p_cr, −4.2766 to −4.0356, to four decimals (`pcr_check.txt`). The exactness rests on the
undrained Tresca model. It would not hold for a drained (Mohr–Coulomb) analysis, whose strength grows
with mean stress, nor for hydraulic fracturing, which depends on the absolute minor principal stress.

*Approximate: replacing the hydrostatic profile by its crown value.* The pressure on the walls lies
between p_cr (crown) and p_cr + γ_w a_p (invert). Using p_cr alone leaves out the support of the
increase below the crown. Write that support as β γ_w a_p, with β the fraction of the invert-level
increment that acts as support.

Results for a square opening (D/B = 1), γB/c_u0 = 1, γ_w B/c_u0 = 0.5 (`verification/
fela_pressure_study.py`, results in `fela_pressure_study.txt`): critical (σ_s − p_cr)/c_u0, lower–upper:

| C/B | ρB/c_u0 | single σ_t = p_cr | full, hydrostatic | part-full, y = 0.5 D | part-full, y = 0.9 D |
| --- | --- | --- | --- | --- | --- |
| 1 | 0 | 0.833–0.963 | 0.903–1.045 | 0.856–0.983 | 0.896–1.029 |
| 2 | 0 | 0.681–0.846 | 0.849–1.001 | 0.727–0.883 | 0.819–0.972 |
| 4 | 0 | −0.261 to −0.065 | −0.092 to 0.104 | −0.214 to −0.019 | −0.122 to 0.074 |
| 2 | 0.25 | 2.018–2.227 | 2.139–2.344 | 2.050–2.252 | 2.117–2.320 |

(For part-full pipes p_cr = 0.)

**Range test (review of draft 4.6).** 120 cases (`verification/fela_pressure_range.py`, results in
`fela_pressure_range.txt`), every combination of:
- a_p/b_p = 0.5, 1, 2;
- C/b_p = 0.5, 1, 2, 4, 8;
- γ b_p/c_u0 = 0.5, 2;
- ρ b_p/c_u0 = 0, 0.5;
- γ_w b_p/c_u0 = 0.25, 1 (weak soil under a high head is the second value);

each run full (hydrostatic) and part-full (y = 0.9 a_p, roof dry). Every audit was below 6·10⁻⁶. Results:

| | β, full pipe | β, part-full (y = 0.9 a_p) |
| --- | --- | --- |
| all 120 cases | 0.00–0.64 | 0.00–0.56 |
| a_p/b_p = 0.5 / 1 / 2 | up to 0.47 / 0.54 / 0.64 | up to 0.41 / 0.47 / 0.56 |
| C/b_p = 0.5 | 0.00–0.44 | |
| C/b_p = 8 | 0.19–0.64 | |

1. **The support is never negative and never exceeds the invert-level increment.** In every case
   0 ≤ β < 1, and the critical load rises when water pressure is added (monotone). So a guaranteed
   band holds without any further table:

       N_0 ≤ N_true ≤ N_0 + γ_w a_p / c_u0                                                   (5.16)

   where N_0 is the critical value with the single crown pressure.
2. **It is not always small.** It is near zero at shallow cover, where only the roof moves. It is
   largest for deep cover, heavy soil and tall pipes, where the mechanism also moves the walls and
   floor. Example: a_p = 2 b_p with γ_w b_p/c_u0 = 1 (a weak soil) gives up to 0.64 × 2 = 1.3 c_u0.
   That is comparable to N itself in many cases.
3. **The centroid or mean pressure would overstate the support** (β < 0.5 in most cases, while the
   centroid assumes 0.5). It is not used.
4. **Proposal for review.**
   - Full pipe: the hydrostatic profile enters exactly, with γ_w b_p/c_u0 as a fifth table dimension.
     The solver already handles it, and β barely depends on γ_w b_p/c_u0 (for example 0.206 and 0.197),
     so a coarse grid in that dimension suffices.
   - Part-full pipe: σ_t = 0 with the band (5.16), using the wetted depth y in place of a_p.
   - The uncertainty runs use the band.
5. **One pressure for both regimes.** p_cr is the soffit pressure p_s(x) of (5.8), which is zero for a
   part-full pipe. The roof criterion and the hydraulics use the same pressure, so they stay
   consistent.

**Pressure-driven failure is a separate mechanism: blow-out.** A high internal pressure can fail the
cover upward. This is the passive limit of the same opening, and it is kept apart from roof collapse
(fall-in):
- **Bounds.** The bound code computes it with the sense reversed (`passive=True`). The static bound
  gives the smallest surface load that is still safe. The kinematic bound uses a unit upward flux.
  (`verification/fela_blowout_study.py`, results in `fela_blowout_study.txt`.) A uniform internal
  pressure shifts both bounds exactly, as for collapse.
- **Results**, critical (σ_s − p_cr)/c_u0 at blow-out, square opening:

| C/B | γB/c_u0 | ρB/c_u0 | blow-out bounds | rigid prism (mechanism C form) |
| --- | --- | --- | --- | --- |
| 1 | 1 | 0 | −3.10 to −2.90 | −3.00 |
| 2 | 1 | 0 | −5.37 to −5.22 | −6.00 |
| 4 | 1 | 0 | −8.53 to −8.35 | −12.00 |
| 2 | 1 | 0.25 | −6.59 to −6.38 | −7.00 |
| 2 | 2 | 0 | −7.50 to −7.34 | −8.00 |

- **What it means for mechanism C.** The rigid prism of §5.6 is the rigid-block version of this
  failure.
  - It is adequate at shallow cover: at C/B = 1 its value lies inside the bounds.
  - It overstates the resistance at deeper cover (−12 against about −8.4 at C/B = 4). This is the same
    artefact as the rigid block for collapse.

  So the exit-uplift check uses the blow-out value N_b from the same table. The prism stays as a
  reported comparison.
- **The energy argument still holds.** In every case |N_b| exceeds γC/c_u0, the weight of the cover
  column. So the energy argument of §5.6 (p_s − p_top < γ_w t ≤ γ_t t under the reservoir, under its
  stated assumptions) still excludes blow-out there. This is observed in all cases computed, not
  proved in general.
- **Hydraulic fracturing** (pressure exceeding the minor principal stress plus the tensile strength) is
  a different, non-plastic mechanism. It needs the absolute stress state and the tensile strength. It is
  not covered and is listed as a limitation.

**The criterion.** At each section x along the pipe, with cover C(x) above the crown:

    stable while   c_u0 · N_b  <  σ_s(x) − p_s(x)  <  c_u0 · N_c                               (5.15)
    N_c, N_b = f( C(x)/b_p, a_p/b_p, γ b_p/c_u0, ρ b_p/c_u0, γ_w b_p/c_u0 )

N_c is the collapse (fall-in) value and N_b < 0 the blow-out value. They are two separate mechanisms,
reported separately. The fifth argument enters for a full pipe (above).

- **Surface load:** σ_s(x) = γ_w max(z_s − z_dam(x), 0), the water standing on the section under the
  reservoir; zero elsewhere.
- **Soffit pressure:** p_s(x) from (5.8).
- **Margins:** collapse M(x) = c_u0 N_c − (σ_s − p_s), and blow-out M_b(x) = (σ_s − p_s) − c_u0 N_b,
  both computed along the pipe every step. A blow-out is handled as mechanism C (§5.6). The rest of
  this list concerns M. Collapse is the first
  instant at which min_x M(x) reaches 0. It is event-located in time as in §5.5, and its location x* is
  reported.
- **Where it can start.** Under the reservoir a full pipe gives σ_s − p_s ≈ −γ_w t + (head losses), so
  the margin there is large. Collapse is therefore expected under the crest or the downstream slope,
  where σ_s = 0 and p_s has fallen with friction. That matches where piping sinkholes are reported, and
  it follows from the criterion; nothing imposes it.
- **N_c and N_b from both bounds.**
  - The central value is the mean of the lower and upper bounds.
  - Runs with each bound give the uncertainty band.
  - The width of the bracket (10–25 % for the square opening now) is reported. It narrows when velocity
    discontinuities are added to the upper bound.
- **Unit weight.** The table takes one γ per section. The first version uses the cover-weighted mean of
  γ_moist and γ_sat (§5.5) over the section's cover; a layered γ is possible in the same code.
- **Table.** N_c and N_b are precomputed offline with `fela_v2.py` over:
  - C/b_p from 0.25 to 20;
  - a_p/b_p from 0.5 to 2;
  - γ b_p/c_u0 from 0 to 3;
  - ρ b_p/c_u0 from 0 to 1;
  - γ_w b_p/c_u0 from 0 to 2 (coarse; full pipe only).

  It is interpolated in the engine. A section outside the table is an error, not an extrapolation.
- **What the criterion replaces.** It replaces mechanism A as the collapse criterion. Mechanism A stays
  as a reported comparison. Mechanism B (horizontal push-out) is a different, longitudinal mechanism and
  stays as a separate check. The blow-out value N_b replaces the rigid prism in the uplift check of
  mechanism C (§5.6).
- **Applicability.** The limits of §5.5a apply: plane strain per section; out-of-plane shear under the
  slopes, with the c_u reduction to be checked; the outlet face is covered by §5.6.

---

## 5.6 Exit mechanisms — the pipe shortens from the downstream end

**Mechanism C — downstream exit uplift (heave) of the cover.** This is the uplift of a defined soil
prism: the cover above the pipe, width b_p, thickness t(x) = z_dam(x) − z_cr, per unit length along the
pipe. It is *not* a criterion for backward erosion piping and does not predict its progression
(FEMA P-1032, 2015, warns against using the heave factor of safety that way).

*Draft 4.7.* The rigid prism below is kept for its free-body reasoning and as a comparison. The
uplift check itself uses the blow-out value N_b of §5.5b: uplift at x when σ_s − p_s ≤ c_u0 N_b, with
σ_s from p_top. The prism overstates the resistance once the cover exceeds about the pipe width
(§5.5b, blow-out table). The conclusions below, which rest on the energy argument, are unchanged.

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
    reservoir. This is derived under the stated assumptions; it does not show that uplift under the
    reservoir is impossible in general. v_top < U is a flow-field assumption, not a guaranteed condition, so the model uses
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
flow carries off at once. A wedge is a later option. With n_d = n and a slot of
nearly constant length, the slot column loses exactly the pipe volume, so z_d ≈ H − a_p. This is a
consequence of the geometry, not a general rule. If loose debris would rise above the crest, z_d is
capped at H and the excess is set beside the slot as spoil (counted in the solids budget).

**Required comparison: a localised mound (draft 4.6).** The criterion (5.15) makes the roof fail first
at one section x*, a sinkhole, not along the whole pipe. Spreading that debris uniformly along the
slot then contradicts the collapse criterion itself. Every piping case is therefore run with three
debris treatments, and the hydrograph sensitivity is reported:
1. uniform layer (5.12b);
2. a localised mound centred on x*, holding the same solids volume;
3. instant removal.

DL Breach's virtual tank remains a further comparison mode.

**How far collapse spreads along the pipe** sets the debris volume and where it lies. The proposed rule
is set out in §5.7a, for review.

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
- **Localised mound at x*** (required on every case, above).
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

## 5.7a Collapse spreading — from a local collapse to a collapsed reach (draft 4.7, for review)

**Why it matters.** The criterion (5.15) makes the roof fail first at one section x*. How long the
collapsed reach becomes sets three things: the debris volume, where that debris lies, and when the
reservoir connects to an open breach. Through these it affects blockage, discharge and the hydrograph.

**Four physical routes by which collapse can spread, and what the model does with each.**

*Route 1 — loss of water support (in the model already).* When x* falls, the pipe is cut at the
crater.
- **Upstream reach.** Its outlet moves to the upstream edge of the crater: x_o, the existing outlet
  state of §5.2, moves there. The soffit pressure along this reach falls towards the crater water
  level, so the sections next to the crater lose the pressure that held them, and M(x) falls.
- **Downstream reach.** It is fed only through the crater. It runs part-full or not at all, so p_s = 0
  and M takes its dry value.

Both follow from the existing hydraulics with the new outlet. No new rule is needed.

*Route 2 — loss of three-dimensional support from the fallen neighbour (not represented; a stated
limitation).* M(x) is a plane-strain value: it is the stability of an infinitely long unsupported
opening, which gives a section no help from its neighbours. The plane-strain criterion is used as the
local roof criterion. Any further loss of support at a crater edge is **not represented**, and this
assumption has **not been independently verified**. The comparison below suggests it is reasonable. It
does not show that plane strain is conservative at a crater edge, and no such claim is made. For a
square opening with cover equal to its height, weightless:
- **cross-section** (our bounds): N = 1.90–2.08;
- **plane-strain heading** (a face supported along the tunnel): 4.17–4.33 (Shiau and Al-Asadi 2018, as
  tabulated in Shiau et al. 2024);
- **3-D square heading**: 6.77–7.15 (Shiau et al. 2024).

Shiau et al. report that the 3-D analysis gives critical stability numbers about 1.7–1.9 times the
plane-strain heading values. In those configurations, the extra 3-D support adds strength rather than
removing it.

*Why that is not a proof here.* A heading has intact soil ahead of its face. A crater edge has open
void beyond it, with the open pipe continuing beneath. A mechanism that moves partly into the pipe and
partly into the crater is not covered by either comparison.

*Decision (2026-11-24): not verified now.* The reasons:
- The maximum-spread bracket (whole roof) already shows the consequences of extensive collapse.
- A 3-D bound might not settle the question. With von Mises criteria inscribed in and circumscribed
  about Tresca, the 3-D bounds may differ by up to 15 % and could straddle the plane-strain value.

The 3-D calculation becomes a pre-publication task, done only if the spread cases show that the
assumption matters to the breach (§5.8, "Spread sensitivity before publication").

*Route 3 — failure of the crater's end walls (added).* Each end of the collapsed reach is a wall of
exposed height H_w, from the ground surface down to the debris surface at that end. An undrained wall
stands while

    H_w ≤ H_c = 3.776 c_u0 / (γ − 2ρ)        (no limit if γ ≤ 2ρ)                          (5.17)

- **Where (5.17) comes from (revised in draft 4.8).** Draft 4.7 used the Culmann wedge of Part 3 (3.12)
  with φ = 0, i.e. 4 c_u0/(γ − 2ρ). Culmann's value is a kinematic (upper-bound) estimate and is about
  6 % too high. For constant strength, the rigorous bounds on an undrained vertical cut are
  3.77522 ≤ γH_c/c_u ≤ 3.77649 (Pastor, Loute and Pastor 2009, as cited by Salençon 2024).
- **Our own bounds** (`verification/fela_cut.py`, results in `fela_cut.txt`). The rigorous lower bound
  converges to that value as the mesh refines, and the independent audits are below 4·10⁻¹⁰:

  | case | lower bound | reference or formula |
  | --- | --- | --- |
  | ρ = 0, h = 0.1 / 0.05 / 0.025 | 3.718 / 3.744 / 3.755 | 3.7752–3.7765 |
  | ρ = 0, domain doubled | 3.744 | (domain size does not matter) |
  | ρH/c_u0 = 0.25 | 4.279 | (5.17): 4.276 |
  | ρH/c_u0 = 0.50 | 4.804 | (5.17): 4.776 |

  Our continuous-velocity upper bound (4.1–4.2) is valid but weaker than Culmann's 4, because it cannot
  represent the slip lines at the toe. So the published 3.7765 is the upper bound used.
- **Strength increasing with depth.** No published bound was found for this case. (5.17), which scales
  the mean strength over the wall height, lies 0.1–0.6 % below our rigorous lower bounds, so it is on
  the safe side.
- **Two distinct wall cases, kept separate.**
  - **With tensile resistance (the default):** H_c = 3.776 c_u0/(γ − 2ρ). The soil carries the tension
    that develops near the top of the wall.
  - **Tension cut-off (sensitivity):** H_c = 2 c_u0/(γ − 2ρ). With zero tensile strength the critical
    height falls to 2 c_u/γ (Drucker and Prager; Salençon 2024).

  Real fill lies in between, and tension cracks are common at crater edges. The two are reported as
  separate cases, not averaged.
- **Part 3, flagged.** Part 3 uses Culmann for vertical cohesive banks. For φ = 0 that is 6 % too
  high, which should be corrected there too.
- **Consistency.** The crater walls obey the same physics as the breach walls after hand-over.
- **What happens when it is exceeded.** The wall fails as the Part 3 wedge: the failure plane is at
  45° for φ = 0, and the top of the wall moves back by H_w. The roof over the pipe within that retreat
  is gone, and the wedge (½ H_w² per unit width) is added to the debris at that end.
- **The retreat limits itself.** Each wedge raises the debris surface at the toe, which lowers H_w. The
  wall stops caving once H_w ≤ H_c, or once it reaches thinner cover under a slope.
- **Example.** c_u0 = 20 kPa, γ = 20 kN/m³ and ρ = 0 give H_c = 3.78 m (2.0 m with zero tensile
  strength). A crater exposing more wall than that keeps caving until its own debris or the slope
  brings the exposed height down to it. With ρ = 2 kPa/m, H_c = 4.72 m.

*Route 4 — loss of strength near the failure (sensitivity only).* Real clays lose strength when
sheared and remoulded (sensitivity S_t), which can drive progressive failure. Perfect plasticity does
not represent it. It is tested by reducing c_u0 to c_u0/S_t within one cover depth of each crater edge.

**Proposed rule S (for review).** At each collapse event:
1. **Initial reach:** the contiguous reach around x* where M(x) ≤ 0.
2. **Cascade at the same instant:**
   - recompute the hydraulics with the crater (route 1);
   - check M(x) along both remaining reaches;
   - check both end walls with (5.17) (route 3);
   - add every section that fails and every wall wedge, depositing its debris where it falls;
   - repeat until a full pass changes nothing, as in the Part 3 bank sweeps. The passes are counted;
     the cap is a safeguard only.
3. **In time:** M(x), the wall heights and the debris are tracked. Pipe enlargement, debris erosion
   (which re-exposes the walls) and further failures continue, each event-located.

Additional 3-D loss of support at the crater edge (route 2) is not represented. That is a stated,
unverified limitation (above).

**Three spread cases, run and reported separately on every case:**
- **minimum spread:** step 1 only, frozen;
- **intermediate:** rule S;
- **maximum spread:** the whole roof (the draft-4 assumption).

Further sensitivities are run with rule S: remoulding (route 4) and the tension cut-off on the crater
walls (5.17). The hydrographs are reported case by case. How much they differ is itself a result
(§5.8).

**First-version simplifications, stated.**
- The crater has the pipe width b_p while it is a sinkhole. Its side walls are handled by Part 3 after
  hand-over.
- The crater drains freely, so its water level is the debris surface. A crater storage, which would
  give the upstream reach a tailwater h_t, is a later option.
- The crater walls are taken dry.

**Hand-over to the open breach.** Until the collapsed reach reaches the upstream face, the reservoir
reaches the crater only through the upstream pipe. The flow path is upstream pipe → crater → over the
debris and the downstream reach. Parts 2–4 take over when the collapsed reach reaches the upstream
face, in one of two ways:
- through the cascade;
- through push-out of the shortening upstream roof (mechanism B), whose resistance 2 c_u A_r falls as
  the remaining roof shortens.

Every roof piece and wall wedge enters the solids budget (5.13).

---

## 5.8 Inputs, safeguards and the cases that test this part

**Case-file inputs (`mode: "piping"`):**
- pipe width and height;
- invert elevation **above the dam base** — converted from depth below the crest if the source gives
  depth;
- `invert_source`: `measured` | `estimated` | `scenario`;
- c_u0 and ρ for the roof (5.14), with test, saturation state and density recorded; ρ = 0 allowed;
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

**Spread sensitivity before publication (decision of 2026-11-24).** Required before any piping result is
published:
1. The three spread cases (minimum, rule S, maximum) are kept separate on every case. Their
   hydrographs (peak, time to peak, volume released by a given time) are reported side by side, with
   both crater-wall cases.
2. The text states that the 3-D support assumption at a crater edge has not been independently
   verified. It does not claim that plane-strain stability is conservative there.
3. **Trigger for the 3-D bound.** If the hydrograph changes materially between rule S and the maximum
   spread, the 3-D lower and upper bounds of the crater-edge configuration (§5.7a, route 2) are
   computed before publication. "Materially" means beyond the spread of the uncertainty runs on the
   same case. If the cases show little difference, the limitation is stated and the 3-D calculation
   is not needed for the conclusions.

**Verification this part must pass (Phase 3):**

| test | expected |
|---|---|
| (5.2) | equals 1.705 b HW^1.5/√(1+K_u) for HW ≤ 1.5 D |
| (5.3)–(5.4) | Q_b non-decreasing in HW except the reported priming step; Q_o ≤ Q_i always once full; priming step down for F > 1.05, up (≤ √2) for F < 1.05; (5.3) → (1.9) for a long full pipe |
| (5.5) | τ_p → ρ g R Δh/L_p when f L_p/4R ≫ K_u + K_d |
| (5.6)–(5.7) | no growth below τ_c; roof fixed while w = 0; eroded volume = wetted area × ε dt exactly |
| (5.9) | dry limit gives b_crit = 2c_u/γ_t for any cover; FS_A written every step (comparison only) |
| bound code | brackets 2 + π (Prandtl) and overlaps Wilson et al. (2011) for ρ = 0 and ρ > 0; audits < 1e-6 (done, `fela_benchmarks.py`, `fela_rho_benchmark.py`) |
| (5.15) | uniform pressure shifts N by exactly q; table interpolation reproduces direct solves to the bracket width; out-of-table section raises an error; M(x) and x* written every step |
| debris modes | uniform, mound at x* and instant removal run on every piping case; solids budget closes in each |
| pressure | shift exact for any p_cr (done); 0 ≤ β < 1 and monotone over the range (done, 120 cases); band (5.16) used in the uncertainty runs |
| blow-out | N_b bounds bracket the rigid prism at C/B ≤ 1; uniform-pressure shift exact; uplift check uses N_b |
| spreading (§5.7a) | cascade terminates; collapsed length: minimum bracket ≤ rule S ≤ whole roof; (5.17) gives 3.776 c_u0/γ for ρ = 0 (bounds done, `fela_cut.py`); tension cut-off run uses 2 c_u0/(γ − 2ρ); wall-wedge volume ½ H_w² per unit width; spread converges in dt |
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

## 5.9 Decisions (draft 4.6, after the reviews of 2026-11-24)

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
4. **Roof stability**: *criterion written for review (§5.5b).* Undrained, with c_u = c_u0 + ρ d
   (constant c_u is ρ = 0); drained deferred until a pore-pressure field exists. Collapse at the first
   section where σ_s − p_s reaches c_u0 N_c (5.15). N_c comes from our own verified bound code,
   tabulated offline, with the mean of the bounds as the central value and each bound as the band.
   The uniform-pressure shift is exact. The crown-pressure treatment of the hydrostatic profile is an
   approximation with a guaranteed band (5.16), so a full pipe enters exactly as a fifth table
   dimension. Blow-out (N_b) is a separate, pressure-driven mechanism, and it replaces the rigid prism
   in the uplift check. The rigid block (A) stays as a comparison and push-out (B) as a separate check. As reviewed: soffit pressure integrated along the pipe with no double counting; water force resolved
   into its vertical (A) and horizontal (B) components. FS = 1 at collapse, event-located inside the step, with FS and its
   minimum reported. FS_crit ≠ 1 for sensitivity only. c_u from the state the roof is in, with its
   source recorded. Tension cracks later; side friction for sensitivity only. *(Both reviews agree.)*
5. **Downstream exit uplift (heave)**: a separate mechanism C, defined by a free body of the cover
   prism. An energy bound shows it does not act under the reservoir under stated flow assumptions
   (v_top < U, p_top ≥ 0). The code computes F_C along the whole pipe and does not rely on that. It shortens the pipe from the outlet. It is named and bounded
   as prism uplift, not a backward-erosion-piping criterion. Independent check of the free body
   before publication. *(Reviews adopted.)*
6. **Fallen roof**: a debris layer from conserved solids, V_d = (1 − n) b_p A_r/(1 − n_d), settled
   uniformly in the slot (an explicit assumption). Its surface is the new weir control, so it obstructs
   the flow from the first step. It blocks the flow when z_s ≤ z_d; the reservoir must rise to
   overtop it, and with no inflow the run ends sealed (a labelled model prediction, under stated
   impermeability and no-other-supply assumptions; no seepage mechanism before the Teton
   inspection). It erodes by the bed laws, and the solids budget is closed every
   step. n_d = n and debris erodibility = intact by default, all tested. A localised mound at the
   collapse section and instant removal are required comparisons on every case; the virtual tank is
   kept as a further mode. How far collapse spreads follows rule S (§5.7a, for review). *(Second review's solids/porosity, deposition and budget
   adopted; blocking criterion added.)*
7. **Exit headcut**: optional, cohesive only, off by default until the ARS P1 on/off test. It reuses
   the Part 4 relations with the pipe discharge and moves the outlet x_o. *(As reviewed.)*
8. **Pipe location**: always an input with a recorded source, checked for positive cover. A missing
   location gives three `scenario` runs kept out of primary validation. The base is not assumed
   worst-case. *(As reviewed.)*
9. **Collapse spreading** *(proposed, for review; §5.7a)*: rule S.
   - The initial reach is where M(x) ≤ 0.
   - A cascade at the same instant follows, driven by two routes: the loss of water support, through
     the recomputed hydraulics, and crater end-wall failure by the rigorous undrained cut height (5.17), with a tension cut-off sensitivity.
   - Failures continue in time and are event-located.
   - Additional 3-D loss of support at a crater edge is not represented. This is stated as an
     unverified limitation; plane strain is not claimed to be conservative there. *(Decision of
     2026-11-24: the 3-D bound is deferred, and becomes a pre-publication task only if the spread
     cases show the assumption matters.)*
   - Three spread cases reported separately: minimum (frozen initial reach), rule S, and maximum (whole
     roof). Sensitivities: remoulding, and the tension cut-off on the crater walls.
   - Hand-over to the open breach when the collapsed reach reaches the upstream face, by the cascade or
     by push-out of the remaining upstream roof.

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
- Prandtl, L. (1920). Über die Härte plastischer Körper. *Nachrichten der Gesellschaft der Wissenschaften zu Göttingen*, 74–85.
- Salençon, J. (2024). About the critical height of a vertical cut. *Comptes Rendus. Mécanique*, 352,
  269–275. doi:10.5802/crmeca.276 (cites the bounds of Pastor, Loute and Pastor 2009).
- Shiau, J., Keawsawasvong, S., Lai, V. Q., Promwichai, T., Kamchoom, V., and Banyong, R. (2024).
  Rectangular tunnel heading stability in three dimensions and its predictive machine learning models.
  *J. Rock Mech. Geotech. Eng.*, 16, 4683–4696. doi:10.1016/j.jrmge.2023.12.035 (their Tables 3–4
  also give the plane-strain heading values of Shiau and Al-Asadi 2018).
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
- Iglesia, G. R., Einstein, H. H., and Whitman, R. V. (2014). Investigation of soil arching with
  centrifuge tests. *J. Geotech. Geoenviron. Eng.*, 140(2).
- Jafari, P., and Fahimifar, A. (2022). Upper-bound face stability analysis of rectangular
  shield-driven tunnels in undrained clays. *Computers and Geotechnics*, 146.
- Wilson, D. W., Abbo, A. J., Sloan, S. W., and Lyamin, A. V. (2011). Undrained stability of a circular
  tunnel where the shear strength increases linearly with depth. *Can. Geotech. J.*, 48(9), 1328–1342.
  doi:10.1139/t11-041 (Table A1: FELA bounds used as the circular-tunnel benchmark).
- Wilson, D. W., Abbo, A. J., Sloan, S. W., and Lyamin, A. V. (2013). Undrained stability of a square
  tunnel where the shear strength increases linearly with depth. *Computers and Geotechnics*, 49,
  314–325. doi:10.1016/j.compgeo.2012.09.005.
- Wilson, D. W., Abbo, A. J., and Sloan, S. W. (2014). Undrained stability of tall tunnels. *Proc. 14th
  IACMAG*, Kyoto, 447–452.
- Wilson, D. W., Abbo, A. J., Sloan, S. W., and Yamamoto, K. (2017). Undrained stability of rectangular
  tunnels where shear strength increases linearly with depth. *Can. Geotech. J.*, 54(4), 469–480.
- Wu, W. (2016). *Introduction to DLBreach*, v2016.4. §2.2, §3.2, §4.7, §6.4.
