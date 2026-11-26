# Part 5, §5.7b (draft for review): what happens to the collapsed roof debris

*Draft 5.11-D, revision 2 · 2026-11-26 · status: reviewed once; the qualifications of the review are
incorporated below. Not frozen. The four §5.7 comparison treatments are being implemented first. D1 is
not implemented.*

**Changes in revision 2.**
- D1 is stated as a provisional, event-based breakthrough criterion, not a removal law.
- The D1-b opening condition is corrected.
- Crater export is now distinguished from system export.
- D5 evaluates each plug with its own boundary conditions.
- Debris hydraulic conductivity is written K_hyd,d (k_d stays the erodibility).
- §2a now maps the comparison treatments to the crater framework.

## 1. Why this note

In every P1 run so far the collapsed roof stops the breach:
- k_d over the whole §5.4a band (0.88–150 cm³/(N·s));
- dt from 2 to 0.5 s;
- exit headcut off and on.

The chain, from the converged runs (P1, k_d = 150, dt = 0.5–2 s):
1. **The roof fails** at x ≈ 5.6–5.8 m, the corner where the crest meets the downstream slope. The
   pipe is then about 0.29 m wide.
2. **The debris layer forms.** The fallen roof becomes a level layer whose surface is
   z_d ≈ ground − a_p: 0.92–1.00 m, against a downstream crown at 0.37 m.
3. **The downstream entrance is buried**, (5.25) a_open = 0, so there is no outflow.
4. **The crater fills.** It is fed through the upstream reach and rises to the reservoir level, 1.100 m.
   The rim, at about 1.12 m, is just above it, so there is no spill.
5. **Nothing moves.** The inflow stops, no check fails, and the run ends `sealed`.

The observation differs. In the ARS piping experiment shown in Wu (2016, Fig. 2.14; Hanson et al.
2010), the piping roof collapsed at 13 min, and the breach was still widening at 60 min. Chen et al.
(2019, Fig. 6) report the measured P1 breach widening from about 0.6 m to 5.4 m between 0.13 h and
1 h. Wu (2016, §2.2) summarises the general process: after the crest collapses, overtopping-type
breaching dominates, with downcutting and widening. Laboratory piping tests on landslide dams report
the soil over the piping channel collapsing *and being washed away* (Sci. Rep. 2025, s41598-025-89464-5).
Okeke and Wang (2016), already cited in §5.7, report the lake rising until the flow dislodged the
collapsed sediment.

So the model reaches a stable blockage that the experiments do not show. The question for this note:
which physical process removes or bypasses the debris, and how is it represented?

## 2. What the current theory does, and where it is restrictive

| element | current rule | effect on P1 |
|---|---|---|
| deposit geometry (5.12b, 5.18–5.19) | level layer over the crater footprint, n_d = n by default | debris surface ≈ a_p below ground: always above the crown for P1 |
| downstream entrance (5.25) | open height a_open = clip(z_cr − max(z_d, z_inv), 0, a_p); no seepage | closed at once |
| upstream mouth | not obstructed (inconsistent with the level deposit, recorded in draft 5.8) | the crater keeps filling through it |
| debris erosion (5.7a.7) | only by "flow that actually crosses it"; V_exp = 0 otherwise | none once blocked |
| jet from the upstream pipe | "not represented, no assumed direction" (5.7a.7) | none |
| downstream reach | dimensions frozen at crater start | no erosion there |
| comparison modes (5.7) | uniform layer, mound at x*, instant removal, DL Breach virtual tank: **required on every piping case, not yet implemented** | not yet run |

The last row matters. The theory already requires the bounding comparisons to be run, and they need
no new physics.
- **Instant removal** gives the most open crater.
- **The DL Breach virtual tank** removes the roof block from the breach at once, stores its mass,
  and freezes the geometry until the stored mass is eroded (Wu 2016, §4.7).

Together with the uniform layer, they bracket how much the debris treatment controls the outcome.

## 2a. The comparison treatments in the crater framework (implemented first, revision 2)

§5.7 lists four treatments. In the crater framework of §5.7a they map as follows:
1. **The localised deposit at x*.** §5.7a.2 states that the crater footprint *is* the localised deposit
   at x*. The current level deposit over the crater is therefore this treatment, the baseline
   (`level`).
2. **Instant removal** (`instant`). Fallen soil leaves the model domain at once (system export). Its
   pore water leaves with it.
3. **The DL Breach virtual tank** (`tank`). Fallen soil is removed from the crater and stored in a tank
   inside the model. The crater geometry is the same as for instant removal. The flow's erosion
   capacity (the pipe-wall erosion it would otherwise do) empties the tank first, and the wall
   geometry is frozen until the tank is empty (Wu 2016, §4.7).
4. **A uniform layer along the whole pipe** (5.12b). Not implemented. It needs a rule this note has not
   defined: debris lying inside both pipe reaches reduces their open height, and the flow then
   crosses and erodes a debris floor. Proposed definition, for decision: a layer of uniform thickness
   t_d = V_db/(b_p L_pipe + A_c) over the whole floor, which reduces both reaches' open heights by
   t_d. Its erosion follows D4 (remoulded debris) once flow crosses it.

**Two corrections to §5.7a.3, found while implementing instant removal** (they apply to every
treatment):
- **Pipe void exposed by an end-wall retreat.** It is b_p · clip(z_d − z_inv, 0, a_p) · Δ, not
  b_p a_p Δ. Above the floor, the pipe lies inside the wedge column already. The two are equal
  while the debris is above the crown, as in every level-mode run so far.
- **Soil over the new strip of an end wall.** It is W ∫ (z_dam − z_d)₊ dx over the strip, exact for the
  profile. ½ H_w² W assumes level ground and over-counts on a sloping face. With instant removal on
  P1 it pushed the floor below the invert, breaking (5.18)–(5.19). On a level crest the two
  agree exactly, and side walls are unaffected.

## 3. Candidate mechanisms

Each candidate is set out with the seven points the review asked for:
- (a) driving hydraulic quantity;
- (b) erosion or transport law;
- (c) debris parameters;
- (d) how the debris surface and openings change;
- (e) how solids leave;
- (f) budgets;
- (g) evidence.

### D1. Seepage failure of the debris plug at a buried entrance (critical gradient)

The water in the crater stands above the debris, while the downstream pipe beyond the buried
entrance is empty and open to the air. Seepage through the debris over the entrance therefore runs
under a steep gradient.

- **(a) Driving quantity.** The mean gradient across the plug, i = (z_c − z_x) / ℓ_p.
  - z_x is the exit head: the crown z_cr of the buried entrance, since the empty pipe is at
    atmospheric pressure.
  - ℓ_p is the seepage path through the plug. In the first version, ℓ_p = z_d − z_cr, the
    vertical cover of debris over the opening, which is the shortest path.
- **(b) Law: a provisional failure trigger, not a removal law.** The plug fails when the seepage force
  exceeds its buoyant weight plus any cohesion.
  This is the same free-body argument and the same classical critical gradient as mechanism C (§5.6;
  Terzaghi 1943):

      i ≥ i_cr,d = (γ_sat,d − γ_w)/γ_w + 2 c_d /(γ_w b_p)                            (5.26, proposed)

  - The cohesion term is the vertical-plane shear on the two sides of a plug of width b_p, the
    form used for the roof prism.
  - c_d = 0 for a non-plastic debris.
  - This is a failure criterion, not a rate law. D1 is an **instantaneous, event-based plug
    breakthrough approximation**:
    1. evaluate i;
    2. compare it with i_cr,d;
    3. if it is reached, open the local pipe-sized channel (D1-a);
    4. record the event time and the removed volume;
    5. recompute the hydraulics and geometry.

    The failure rate and any progressive enlargement of the opening are **not resolved**. The
    assumed seepage path, the saturated unit weight and the negligible remoulded cohesion remain
    explicit assumptions.
- **(c) Parameters.**
  - γ_sat,d comes from n_d.
  - c_d is the debris cohesion: 0 for remoulded non-plastic soil; for cohesive soil, the
    remoulded c_u0/S_t of the §5.7a sensitivity. No case has a measured value.
- **(d) Geometry. Two options, for decision:**
  - **D1-a, "piped through the debris":** at failure, the entrance reopens through a channel of
    the pipe's size cut through the debris, a_open = a_p. The level debris surface z_d stays where
    it is. This represents a local failure, which the level deposit cannot resolve.
  - **D1-b, "lowering":** debris is removed until the entrance opens. Under (5.25),
    a_open = clip(z_cr − max(z_d, z_inv), 0, a_p) is still zero at z_d = z_cr. So D1-b would have to
    lower the surface by an arbitrary finite distance below the crown, or define a finite opening
    threshold. It also removes the whole layer, (z_d − z_cr) A_c and more, which is far more soil
    than a local failure would. **Decided (review): D1-a.**
- **(e) Solids: crater export versus system export.** The removed debris leaves the crater control
  volume (*crater export*, V_exp). Whether it also leaves the model domain (*system export*,
  V_exp,out) is a separate statement. The first-version assumption: the plug material is carried
  through the empty downstream pipe and out of its outlet by the released flow, so V_exp,out also
  increases. If a later version deposits it in the downstream reach, it becomes a transfer into that
  reach's floor, not an export. The removed volumes are:
  - D1-a: volume b_p a_p ℓ_p;
  - D1-b: volume (z_d − z_cr) A_c.

  In both cases V_exp increases by that amount, so the crater solids identity (5.18) still closes.
- **(f) Budgets.**
  - Solids: the crater identity (5.18) closes through V_exp, and the system balance closes through
    V_exp = V_tank + V_exp,out.
  - Water: the pore water of the removed debris (n_d × volume) is part of the crater water W_c until
    the plug fails. It is counted as outflow only when it leaves the water control volume, which here
    is through the downstream pipe to the outlet.
- **(g) Evidence.**
  - *P1 support (indicative).* P1 is a non-plastic silty sand whose specimens collapsed when wetted
    (PAP-1017, Table 5). Its remoulded debris has negligible cohesion.
  - *A check on the model's own sealed state* (k_d = 150, final state):
    - z_c = 1.100 m, z_d = 0.924 m, crown 0.371 m;
    - ℓ_p = 0.55 m and i = 0.73/0.55 = 1.32;
    - γ_sat,d = 20.2 kN/m³ at n_d = n = 0.36, so i_cr,d = 1.06.

    The plug is above the critical gradient, by a factor of 1.25, in the state the model calls sealed.
  - *Not supported directly.* No P1 observation documents the plug failure itself. The washing-away
    of the debris is observed only in the outcome.

### D2. Steady seepage through the debris (Darcy), without failure

- **(a)–(b)** A leak path Q_seep = K_hyd,d i A_p through an intact plug. K_hyd,d is the debris
  hydraulic conductivity (not k_d, which is the erodibility).
- **(c)** K_hyd,d for a loose silty sand is of order 10⁻⁶–10⁻⁵ m/s. No case has a measured value.
- **(d)** Geometry unchanged. **(e)** No solids. **(f)** A water-budget term only.
- **(g)** The flow it gives in P1 is about 10⁻⁶ m³/s, a thousandth of the pipe flows. It would end the
  "sealed" classification but not reopen anything. **Sensitivity only.**

### D3. Scour by the jet from the upstream pipe

- **(a)** The jet velocity U_in = Q_in/A_up at the crater's upstream end wall.
- **(b)** JET-type impingement erosion of the debris.
- **(c)** Debris k_d and τ_c.
- **(d)–(f)** Local scour, which the level deposit cannot place; exported through V_exp.
- **(g)** Self-limiting in the present geometry. Q_in falls to zero as the crater fills, a few seconds
  after the collapse in P1, so there is no sustained jet. §5.7a.7 already records it as having no
  assumed direction. **Sensitivity only**, unless an observation shows sustained inflow into a
  crater.

### D4. Remoulded debris erodibility (a modifier, not a mechanism)

- **(b)–(c)** Higher k_d,debris and lower τ_c,debris than the intact soil. For a non-plastic debris,
  Part 2 transport-limited erosion with τ_c from the grain size.
- **(g)** Plausible for P1, since its specimens collapsed when wetted. But it acts only where flow
  crosses the debris. It does nothing in the blocked state unless D1 reopens a flow path first.
  It stays the §5.7 sensitivity.

### D5. Both mouths treated alike (resolves the asymmetry)

With a level deposit above the crown, the upstream reach's mouth at x_1 is buried as well. Two
consistent choices:
1. **Both mouths obstructed alike by (5.25).** The crater is then fed only through D1 or D2 at the
   upstream mouth. The upstream plug is loaded from the reservoir side, so it is pushed *into* the
   crater, and the same criterion (5.26) applies with the reservoir head.
2. **Both mouths left open**, with the difference justified. For example, the jet from the upstream
   reach keeps its mouth clear while it flows (D3). That justification holds only while Q_in > 0.

Recommended (review): choice 1, **where the deposit actually covers the mouth**. It is the only
treatment consistent with the level deposit. Each plug is evaluated with its own hydraulic boundary
conditions, never failed automatically together:
- **The downstream plug** has the crater water above it and the empty, atmospheric pipe beyond it.
- **The upstream plug** has the reservoir on one side and the crater on the other. Its driving head
  is the level difference z_s − z_c, with the seepage direction set by its sign. In the sealed P1
  state both levels are 1.100 m, so the upstream plug carries almost no gradient while the downstream
  plug exceeds its critical gradient.

## 4. Is the debris the only gap? (stated, not resolved)

PAP-1017 describes the bridge collapsing after the inlet funnel and the downstream headcutting to the
base. In the model the collapse is at the crest's downstream corner, with long intact remnants on
both sides:
- upstream: x 1.6 → 5.6 m;
- downstream: 6.3 → 9.0 m.

If the real bridge was short when it fell, the debris would have fallen straight into the flow path
between the funnel and the headcut. Either one bridge-collapse picture or the other could explain the
observed outcome. The note therefore keeps open that the roof-remnant geometry, not only the debris,
differs from P1. Measured pipe-length or funnel data from Hanson et al. (2010), not obtained, would
decide it.

## 5. Proposed order (revision 2, as decided in review)

1. Implement and validate the comparison treatments (in progress: level, instant, tank). Check
   geometry, event logging and budgets.
2. Compare them across the §5.4a band with identical inputs and time steps. Report the crater level,
   downstream reopening, geometry, collapse and hand-over times, pipe-stage peak and budget closure.
3. Review the results.
4. Revise and freeze D1 (event-based, D1-a) and D5 (per-plug boundary conditions).
5. Only then implement D1-a.

No progressive debris erosion, jet scour or new transport law is added before this.

## 5 (original). Proposed order (for decision)

1. **Implement the comparison modes §5.7 already requires.** These are instant removal, the DL
   Breach virtual tank and the mound at x*, alongside the uniform layer. They are theory already
   reviewed, they bound the debris effect, and they show whether any debris treatment leads P1 to a
   hand-over.
2. **Freeze D1 and D5 (choice 1)** as the candidate physical mechanism. One open decision: D1-a
   (piped through the debris, recommended because it is local and removes the least soil) or D1-b
   (lowering).
3. **Keep D2, D3 and D4 as sensitivities**, off by default.
4. **Re-run P1** across the §5.4a band, with the exit headcut off and on, for each debris treatment.
   The comparison is made with the observed sequence. It stays provisional while the time origin is
   open.

## 6. Decisions requested

1. Implement the four §5.7 comparison modes first? (recommended)
2. Adopt D1 as the primary candidate mechanism, with criterion (5.26)?
3. D1-a or D1-b for the geometry after plug failure?
4. Resolve the asymmetry by D5 choice 1 (both mouths obstructed, D1 at both)?
5. D2, D3, D4 as sensitivities only?

## Sources

- Wu, W. (2016). *A Simplified Physically-Based Dam/Levee Breach Model (DL Breach)*, technical report,
  §2.2, Fig. 2.14 (experiment by Hanson et al. 2010), §4.7 (virtual tank). On file:
  `validation/sources/DLBreach Test cases/Technical Report of DLBreach Apr-2016.pdf`.
- Wahl, T. L. (2010). USBR PAP-1017, Tables 4–6 (P1 HET not possible: specimens collapsed when wetted).
- Chen, S., Zhong, Q., Shen, G. (2019). Numerical modeling of earthen dam breach due to piping
  failure. *Water Science and Engineering* 12(3), 169–178, Fig. 6.
- Experimental investigation on failure processes and characteristics of landslide dams with
  different inflow conditions. *Scientific Reports* (2025), s41598-025-89464-5.
- Okeke, A. C. U., Wang, F. (2016), as cited in §5.7.
- Terzaghi, K. (1943). *Theoretical Soil Mechanics* (critical gradient), as cited in §5.6.
