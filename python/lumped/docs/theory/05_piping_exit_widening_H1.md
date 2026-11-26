# Part 5, note H-1 (draft for review): widening of the pipe exit at the downstream face

*Draft H-1 · 2026-11-26 · status: for review. Nothing is implemented in the driver. It would be an
optional mechanism, separate from the exit headcut (§5.6) and the face-stability screening (F-1). No
coefficient is chosen to reproduce P1.*

**Frozen and unchanged by this note:**
- the roof rule (§5.5b);
- the crater-wall rule (5.17);
- the D1-a/D5 debris rules (§5.7b);
- the exit headcut (§5.6) and its P1 diagnostic (§5.6c);
- the F-1 module (not coupled).

## 1. What has to be explained

The evidence is note R-2, §9 (Wu 2016, Fig. 2.14, very likely P1). Sizes are given in marker
spacings s; the scale estimate is s ≳ 0.45 m, a lower bound limited by perspective.

1. **The opening at the downstream face widens steadily before the roof collapses:** about 1.1 s at
   5 min, 2.1 s at 8 min and 3.4 s at 13 min. At the scale estimate that is ≳ 0.5 m at 5 min and
   ≳ 1.5 m at collapse, against a model pipe 0.29 m wide at collapse.
2. **The height grows far less than the width.** The top of the arch rises about one row interval,
   roughly 0.14–0.19 m, while the width roughly triples.
3. **The opening is an arch-roofed cavern with free-surface flow at its floor,** not a full conduit:
   there is air above the water in panels (c) and (d).
4. **The flow leaving the opening spreads over the toe.**

In the model, the outlet stays the width of the pipe and never moves. The exit headcut never plunges
(§5.6c). The in-pipe shear is uniform along the pipe, because the pipe runs full to the outlet (R-2
§2). Any exit-concentrated enlargement must therefore come from processes at the face. Erosion rate is
not the limit: the face flow already erodes 3–5 times faster than the pipe walls.

## 2. Representation (proposed)

One new state variable, **the exit width B_e ≥ b**: the width of the open opening at the downstream
face, over the **open notch**. The notch is the reach from the crown daylight x_d (where the roof over
the pipe ends, F-1 (F.2)) down the face to where the channel meets the face.

- **The pipe inside the dam is unchanged:** a uniform rectangle b × D (§5.4).
- **Outlet hydraulics.**
  - The pipe flow Q is still set by the pipe relations (5.2)–(5.4) with the outlet at x_d.
  - The open notch is a free-surface channel of width B_e on the face slope, carrying Q, with Manning
    normal flow as in §5.6 stage 1 (same n).
  - Once B_e > b, the critical depth in the notch, (Q²/(g B_e²))^(1/3), falls below the pipe height:
    the flow leaves the pipe and runs free-surface in the wider notch. That is the cavern of evidence
    (3) with air above the flow.
- **Independent of §5.6.** The exit headcut keeps its own channel of width b, and the two are never
  run together in the first comparison.

## 3. Candidate mechanisms

Each is given with: (a) the driving quantity; (b) the law; (c) the parameters; (d) the geometry change;
(e) the solids; (f) the budgets; (g) the evidence.

### H1-a. Lateral retreat of the notch walls by the exit flow (primary candidate)

- **(a)** The bed shear of the notch flow, τ_e = ρ g R_e S_f: Manning normal flow of Q in width B_e on
  the face slope 1/m.
- **(b)** Each side wall retreats at the excess-shear rate of the soil, the same law and the same
  k_d and τ_c as the pipe walls (§5.4) and the exit headcut:

      dB_e/dt = 2 k_d (τ_e − τ_c)                                                        (H.1)

  - Applying the bed shear to the walls is the Part 3 / DL Breach convention: walls retreat at the
    bed-erosion rate, (3.3)–(3.5), Wu 2016 Eqs. 4.16–4.17. So **no new coefficient.**
  - A side-wall shear factor below 1 would be a sensitivity, not a default.
- **(c)** k_d, τ_c and n: the existing values, unchanged.
- **(d)**
  - B_e grows. The walls are the soil of the face beside the notch, with height h_w(x) from the notch
    floor up to the face.
  - The notch floor is the pipe floor continued, or the exit-headcut bed where that model is on.
  - Under the roof, upstream of x_d, nothing changes in H1-a.
- **(e)** The volume eroded from both walls,

      dV_e = ∫ h_w(x) dx · dB_e

  over the notch length, is exported with the outflow (crater and system export, as the other end
  terms). It has its own budget term, V_exit.
- **(f)** The solids identity gains V_exit. The water budget is unchanged: no storage in the notch,
  which is quasi-steady.
- **(g)** Evidence (1), (2), (4). Pre-screen: §5.

**Self-limiting.** As B_e grows, the unit discharge Q/B_e falls, and so do the depth and the shear.
Widening slows at a constant Q.

**Height control without a rule.** The notch flow is shallow: 0.06 m at collapse in the pre-screen,
against a crown at 0.37 m. The roof lip over the opening is therefore not wetted and does not erode by
(H.1). The width grows while the height does not, as observed.

### H1-b. Erosion of the roof lip by the outflow (secondary, conditional)

- **(a)** It acts only where the outflow wets the soffit of the lip: notch flow depth ≥ the local lip
  height, or a pressurised outlet with B_e = b.
- **(b)** The same law, E = k_d(τ − τ_c). The lip rises like the pipe roof.
- **(c)–(f)** As H1-a.
- **(g)** Evidence (2): the arch top rises a little.

H1-b is expected to be active only early, while the outlet is still pressurised. It caps how fast the
height can grow. It is not a separate driver.

### H1-c. Failure of the roof over the widened opening (uses existing rules)

- **(a)** With B_e > b, the roof at the outlet end spans B_e, not b.
- **(b)** The **existing roof rule** (§5.5b, FELA table) is applied to the end sections over the
  widened reach, with span B_e. If it fails, the **existing end-failure rule** (`ends.py`) retreats the
  outlet to the zero crossing and exports the roof volume.
  - Nothing new is added to either rule. **Only their geometry input changes:** a local span at the
    outlet end. This is the same kind of change as F-1 question 6, to be decided in review.
  - G1/G2 (F-1) may be run beside it as a comparison, as before. They are not coupled.
- **(c)** The existing c_u, γ, etc.
- **(d)**
  - The outlet retreats to x_d′. The new notch reach starts there with the current B_e.
  - **The widening of the reach just exposed is not assumed.** It starts from b, so B_e is tracked
    per notch section, or as a minimum over it (decision 2).
- **(e)–(f)** The roof volume is end debris, as now.
- **(g)** Evidence (1): an arch spanning the widened opening before the bridge collapses.

H1-a widens the exit, and H1-c lets a wide exit's roof fail and the outlet retreat. Together they would
form a progressive, cavern-like enlargement of the exit, without any rule that removes the remnant as
a whole.

## 4. Not adopted (benchmark only)

- **Culvert-outlet scour relations,** cohesive soils: Abt and Ruff (1982), J. Hydraulics Div.
  108(1), with depth, width, length and volume of scour against the culvert diameter, outlet
  velocity, PI, shear strength and fluid density; HEC-14 ch. 5. These are the closest established
  analogue, for a jet from a full conduit eroding the soil at its exit.
  - They are empirical and fitted to a horizontal bed below a culvert apron, not a 3H:1V dam face.
    The cohesive tests used SC-type soil; P1 is a non-plastic SM.
  - They are kept as an order-of-magnitude check on B_e, never as the law.
- **A tuned side-wall factor, or an erosion multiplier at the exit.** Not adopted.

## 5. Pre-screen (one-way; not a result)

Script `verification/h1_widening_prescreen.py`: (H.1) integrated with the outlet discharge of the
existing P1 runs, with no feedback on the pipe flow.

| k_d (cm³/(N·s)) | roof collapse (s) | pipe b (m) | exit B_e (m) | B_e / b | exit flow depth (m) |
|---|---|---|---|---|---|
| 16.5 | 293 | 0.291 | 0.866 | 2.98 | 0.056 |
| 3.16 | 1519 | 0.293 | 0.866 | 2.96 | 0.056 |
| 0.88 | 5448 | 0.293 | 0.865 | 2.95 | 0.056 |

1. **The ratio B_e/b at collapse does not depend on k_d** (2.95–2.98 across the whole band). The pipe
   walls and the notch walls erode with the same k_d, so the ratio is set by the hydraulics and the
   geometry, not by the erodibility. There is nothing to tune, and none of the k_d uncertainty
   (§5.4a) enters this comparison.
2. **H1-a alone gives about 3 times the pipe width;** the evidence suggests ≳ 5 times, limited by the
   scale estimate. If that holds, H1-a is not sufficient alone and H1-c, or another process, is
   needed. If s were nearer 0.3 m, H1-a alone would fit. **The scale decides this, and no source for
   it is available** (Hanson et al. 2010 is not obtainable). The comparison must therefore be reported
   as a ratio with its scale caveat.
3. **The exit flow stays shallow** (0.06 m against a 0.37 m crown). This is consistent with the height
   growing much less than the width.

## 6. Acceptance tests (set before any coupled run)

| test | requirement |
|---|---|
| H-A1 | no widening without flow; B_e = b at t = 0 |
| H-A2 | **target (validation, not fit):** at roof collapse B_e/b is several times 1. Reported as a ratio against ≳ 5 with the scale caveat; never tuned toward it |
| H-A3 | the height of the opening grows much less than its width |
| H-A4 | widening is self-limiting at a constant Q (no unbounded growth) |
| H-A5 | solids and water budgets close to round-off, with V_exit as its own term |
| H-A6 | the same outcome at dt = 2, 1 and 0.5 s |
| H-A7 | with the option off, every existing run is reproduced exactly (bit-identical events) |
| H-A8 | H1-c retreats are located events with FS ≤ 1, each on the updated geometry; no sweep removal of the remnant |

**Verification before any P1 run:**
- (H.1) at a constant Q against its own quadrature;
- the volume dV_e against direct integration over the notch;
- the notch hydraulics in the limit B_e = b reduces to the §5.6 stage-1 channel exactly.

## 7. Decisions requested

1. Adopt H1-a as the primary candidate, with the Part 3 convention that walls retreat at the
   bed-erosion rate (no side-wall factor by default)?
2. Track B_e as one value for the notch (first version), or per section so that a freshly exposed
   reach starts at b (needed once H1-c retreats the outlet)?
3. H1-c: allow the existing roof rule to read a local span B_e at the outlet end (geometry input
   only, the rule unchanged)?
4. Keep H1-b as a conditional term (lip wetted only), not a separate driver?
5. Run order: H1-a alone first (coupled, with feedback on the outlet hydraulics), then H1-a with H1-c,
   each against H-A1–A8, reported separately and never averaged?

## Sources

- Wu, W. (2016). DL Breach technical report, Fig. 2.14 (Hanson et al. 2010 experiment), Eqs.
  4.16–4.17. On file.
- Part 3 of this theory, (3.3)–(3.5); §5.4, §5.5b, §5.6, §5.6c; notes R-2 and F-1.
- Abt, S. R., Ruff, J. F. (1982). Estimating culvert scour in cohesive material. *J. Hydraulics
  Div.* 108(1).
- Ruff, J. F., Abt, S. R., Mendoza, C., Shaikh, A., Kloberdanz, R. (1982). *Scour at Culvert Outlets
  in Mixed Bed Materials*, FHWA report.
- FHWA HEC-14, *Hydraulic Design of Energy Dissipators for Culverts and Channels*, ch. 5.
