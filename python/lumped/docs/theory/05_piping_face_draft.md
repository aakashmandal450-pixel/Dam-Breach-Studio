# Part 5, §5.6b (draft for review): stability of the downstream face at the pipe outlet

*Draft F-1 · 2026-11-26 · **status after review (2026-11-26): screening complete; NOT coupled to the
driver.** The standalone module (`face.py`, `tests/test_face.py`) is kept for research comparison. The
static scan (`verification/face_static_scan.txt`) finds the P1 face stable in every scenario:
- G1 2.03 and G2 ≥ 2.1 dry or wetting;
- under steady seepage, 1.07–1.34 across the limit sensitivity, most critical before the pipe enlarges.

The minimum block sizes (0.25 b, b/2) are **numerical regularisation, not physical failure
dimensions**. Results on them are flagged, and their sensitivity is reported. The six-configuration
comparison is on hold. The investigation moves to exit erosion and non-uniform enlargement (note R-2).
Earlier status: for review. Nothing is implemented. An optional mechanism. It does
not change the crater-wall rule (5.17), the interior roof rule (§5.5b) or the frozen debris rules
(§5.7b). Nothing is adjusted to reach the P1 observation (§5.7b.4).*

## 0. Scope and what stays frozen

| item | status in this step |
|---|---|
| crater-wall rule (5.17) | unchanged |
| interior pipe-roof rule (§5.5b, FELA table) | unchanged |
| D1-a / D5 debris rules (§5.7b) and the three plug assumptions | unchanged |
| **downstream face at the outlet** | **new, optional (`face` = off / slab / wedge), off by default** |
| exit-gradient (seepage) erosion | documented in §6; **implementation deferred** |
| a pore-pressure-aware framework for the crater walls | future work, after this one is verified independently |

Why the face comes first: in the model, about 2.7 m of downstream remnant survives to roof collapse,
and the outlet never moves. The experimental descriptions show the downstream face slumping and a
headcut reaching the base before the roof collapsed (remnant note R-1). Whether the downstream plug
of §5.7b exists at all depends on this difference.

## 1. Geometry (established 2026-11-26, P1 values at roof collapse)

The section is longitudinal, with x downstream and z up. Downstream face:

    z_f(x) = (x_t − x)/m,   tan β = 1/m                                               (F.1)

P1: m = 3, so β = 18.4° (measured). The toe is at x_t = 9.63 m and the crest corner at x_c1 = 5.73 m.

The current pipe has crown z_cr, invert z_inv and width b. Its crown **daylights** where the face
reaches crown level:

    x_d = x_t − m z_cr                                                                (F.2)

The closed roof ends at x_d. Between x_d and the point where the invert daylights, the pipe is an
open notch in the face.

At P1 collapse: x_d = 8.52 m, the invert daylights at 9.41 m, and the cover over the crown is
C(x) = (x_d − x)/m (0.17 m at x = 8.0). The model's outlet x_o = 8.97 m (the original axis) is a
bookkeeping point, not a physical edge. §5 replaces it with the daylight point.

**Width across the dam (first version).** The face is 100 m long (estimated), but the pipe undermines
and wets it only locally. The failing block is taken as the column above the outlet, of width
**w = b** across the dam, bounded by vertical lateral planes in line with the pipe walls. This is the
same idealisation as the roof prism and DL Breach (Wu 2016, §4.7). Sensitivity: w = b + 2t.

## 2. Two alternative failure geometries

They are **alternatives, never combined**: a run uses one of them, and the two are reported side by
side. Only force equilibrium is used, as in the Culmann wedge and the infinite slope. Moment
equilibrium and toppling are not checked, which is stated as a limitation.

### 2.1 G1: finite face slab (parallel to the face)

The slab has vertical thickness t, its base is parallel to the face, its back scarp is a vertical
tension crack at x_b (carrying no resistance and, in the first version, no water), and its toe is at
the daylight point x_d.
- The base plane z = z_f(x) − t meets the crown level at x_u = x_d − m t.
- For x_u < x < x_d the base lies in the pipe void (width b = w), so it has **no support**: the outlet
  undermines the slab.
- The base is supported on soil only over x_b ≤ x ≤ x_u.

Profile area and weight per block:

    A_S = t (x_d − x_b) − m t²/2,    W = w ∫ γ dA                                          (F.3)

γ is moist or wetted (saturated) by zone (§3). The supported base length along the slope is
L_s = (x_u − x_b)/cos β.

    D = W sin β
    R = w ∫_Ls (c′ + c_s) ds + (W cos β − U) tan φ′ + 2 S_side                              (F.4)
    FS_S = R / D,    M_S = R − D

The terms of R:
- U = w ∫_Ls u ds is the pore-water force on the supported base. The rigid block carries the whole
  normal component through its supported base.
- c_s is the **apparent cohesion from suction**: zero where the soil is wetted (§3).
- S_side, the resistance on each lateral plane, is

      S_side = ∫∫_A [ (c′ + c_s) + K₀ (σ_v − u) tan φ′ ] dA,   K₀ = 1 − sin φ′ (Jaky)        (F.5)

  This is an assumption, shown openly. Sensitivity: K₀ = 0, so cohesion only on the sides.

**Search.** min FS over t ∈ (t_min, C_max] and x_b ∈ [x_c1, x_u). The block stays on the downstream
face. The grid is stated, and the result is checked for grid independence.

**Check, the infinite-slope limit** (w → ∞, no sides, a long slab):
FS = [c′ + c_s + (γ t cos²β − u) tan φ′] / (γ t sin β cos β), the classical form. Hand values for P1
(tan φ′ = 0.625, c′ = c_s = 0):

| case | FS |
|---|---|
| dry | 1.88 |
| face-parallel seepage, u = γ_w t cos²β | 0.96 |

### 2.2 G2: Culmann wedge with pore pressure (comparison geometry)

A plane through the toe point (x_d, z_cr) rising upslope at angle α < β, under the face, with a
vertical tension crack at x_b. The wedge is the soil between the plane and the ground surface (face,
then crest) from x_b to x_d. Both resistance terms follow (F.4)–(F.5), with β replaced by α in the
weight components and U taken on the plane. Search over α and x_b.

The plane lies above the crown, so it is not undermined. The opening acts only by putting the toe at
the daylight point.

**Check:** with u = 0, c_s = 0, no sides and no crack, G2 reduces to the planar wedge (3.9)–(3.10) of
Part 3 (Culmann; Wu 2016, Eqs. 4.21–4.26) for a bank of face angle β. With c′ = 0 and β < φ′ (P1),
no frictional wedge fails without pore pressure.

**Global (2-D) check.** The same wedge per unit width across the whole face (w → ∞, no sides),
under the same pore-pressure field away from the pipe. If it fails, the model predicts the whole
downstream face failing, which was not observed. That outcome rules the scenario out as an
explanation (acceptance test A3).

## 3. Pore pressure and strength: three scenarios, documented separately

The 5 kPa undrained c_u of the roof check is **not** carried into this drained analysis. Drained
c′ and φ′, the suction term c_s, and the pore pressure are separate inputs, each with its own status.

| scenario | role | u on the planes | c_s | γ |
|---|---|---|---|---|
| **P0, initial (unsaturated) face** | lower-loading reference | 0 | c_s everywhere | moist |
| **P1, transient wetting** | working scenario | from the wetted zone (below) | 0 inside the wetted zone, c_s outside | wetted (saturated) inside, moist outside |
| **P2, steady seepage** | upper-bound reference; not assumed to represent the test | from a Casagrande phreatic line | 0 below the phreatic line | saturated below, moist above |

**P1, wetting from the pipe (and from the reservoir).** The wetted zone grows outward from the pipe
wall. Its thickness above the crown, δ(t), follows Green–Ampt with the gravity term opposing upward
wetting:

    dδ/dt = K_s (h_p + ψ_f − δ) / (Δθ δ) − dz_cr/dt                                        (F.6)

- h_p is the pressure head in the pipe at the crown, from (5.8).
- ψ_f is the wetting-front suction.
- Δθ = n(1 − S_r,0) = 0.36 × 0.46 = 0.166 for P1 as built.
- The last term removes wetted soil as the crown erodes upward.

Inside the wetted zone, u = γ_w h_p at the crown, falling linearly to 0 at the front.

Near the outlet h_p ≈ 0 (computed 2026-11-26: at most 0.09 m of head 1 m inside the outlet, at t = 0,
and zero from about 25 s). So **near the outlet, wetting acts mainly through the loss of suction and
the added weight, not through positive pore pressure.** This is consistent with P1 specimens collapsing
when wetted (PAP-1017). The front from the reservoir is followed the same way, in 1-D from the
upstream face. For P1 it does not reach the downstream face within 13 min at any plausible K_s.

**P2.** The phreatic line is a Kozeny parabola with the Casagrande exit correction (Casagrande 1937).
For P1 it exits on the face at z ≈ 0.26 m, x ≈ 8.84 m.

Pressure head on a plane below the line: h = (z_ph − z) cos²θ_ph, with θ_ph the local slope of the
phreatic line. This is exact for parallel seepage and an approximation elsewhere, stated as such.

Steady state is unlikely in the test. The fill-up time scale n_e L²/(K h) is about 6 days at
K = 10⁻⁵ m/s, 56 at 10⁻⁶ and 560 at 10⁻⁷. P2 is kept only as a bound.

## 4. Inputs (P1)

| input | value | status |
|---|---|---|
| β, x_t, crest | 18.4°, 9.63 m, 1.83 m | M |
| n, S_r,0, γ_moist, γ_sat | 0.36, 0.54, 18.55, 20.17 kN/m³ | M (from the as-built w and ρ_d) |
| φ′ | tan φ′ = 0.625 (32°) | E: the GeoHazards 2024 model input; not confirmed as a drained value |
| c′ | 0 | E: non-plastic SM |
| c_s (suction, as built) | **missing**; scenarios 0 / 1 / 3 kPa | S |
| K_s | **missing**; texture-class estimate for sandy loam ≈ 3 × 10⁻⁶ m/s, bracket 10⁻⁷–10⁻⁵ | E (Rawls et al. 1983; to verify) |
| ψ_f | **missing**; texture-class estimate ≈ 0.11 m | E (Rawls et al. 1983; to verify) |
| how long the reservoir stood before the pipe was pulled | **missing** | (Hanson et al. 2010, not obtained) |
| w | b (first version); b + 2t (sensitivity) | S |

## 5. At failure: the geometry and volume update

1. **Event.** M ≤ −M_tol at the critical geometry, event-located like every other margin (§5.7a.6).
2. **Removed block.** The critical block only (G1 slab or G2 wedge), volume V_F = w A. It is exported
   as end debris at the outlet, the same first-version assumption as the end retreats (§5.5b,
   `ends.py`), with its own budget term V_face.
3. **Local face profile.** Over the pipe column (width w) the face is no longer the original slope.
   The model keeps a **local face polyline** z_loc(x) over the column, equal to (F.1) until the first
   failure. Each failure cuts the block out of it: the vertical scarp at x_b, then the slab base (G1)
   or the plane (G2).
   - The roof check (§5.5b, rule unchanged) and the next face check both read the cover from z_loc in
     this column.
   - The outlet is where z_loc meets the crown. This replaces the bookkeeping x_o, and the pipe or
     downstream reach shortens to it.
4. **No sweep removal.** Each further failure must be its own located event, with its own FS ≤ 1 on
   the updated geometry. No rule removes the remnant as a whole. A retrogressive sequence is allowed
   only as a chain of such events, and is reported event by event with t, FS, t or α, x_b and V_F.
5. **Budgets.** Solids: V_face joins the end-debris terms. Water: unchanged, as the block's pore water
   is not in the water budget (as for end retreats).

## 6. Exit-gradient (seepage) erosion: documented, deferred

Where seepage leaves a face, two things can happen (Chu-Agor et al. 2008, J. Hydrol. 359):
- **pop-out (tension) failures**, when the seepage force exceeds the soil's resistance, which wetting
  is lowering at the same time;
- **particle mobilization**, which undercuts the face.

Undercutting can quickly destabilise a bank that is otherwise stable (Chu-Agor, Fox and Wilson 2008,
J. Hydrol. Eng. 13(12); Fox, Chu-Agor and Wilson 2007).

For P1, an outward seepage face near the outlet exists only under P2. Under P1 the head near the outlet
is about zero. So this mechanism is recorded, with its criterion (exit gradient against the critical
gradient of the face soil, with the Chu-Agor pop-out condition), and **not implemented** until a
scenario that actually produces a seepage face is supported by evidence.

## 7. Acceptance tests (set before any run)

| test | requirement |
|---|---|
| A1 initial stability | at t = 0 (40 mm pipe, δ = 0) the face is stable (FS > 1) in every scenario offered as an explanation. A scenario that fails at t = 0 is rejected for P1 |
| A2 timing | if the mechanism is relevant to P1, failure is possible within the observed window, roof collapse at 828 s, read with the P1 time-origin caveat (§5.4a) |
| A3 locality | in the scenario used, the global 2-D wedge (w → ∞) stays stable: the failure is local to the outlet |
| A4 consistency | each failure gives a physically consistent outlet change and block volume; the solids and water budgets close to round-off |
| A5 no artificial removal | the remnant is never removed as a whole; every retreat is a located event with FS ≤ 1 |
| A6 convergence | the same outcome at dt = 2, 1 and 0.5 s, and a grid-independent minimum FS |
| A7 frozen rules intact | with `face` off, every existing run is reproduced exactly (bit-identical events) |

**Verification before any P1 run:**
- the infinite-slope limit (hand values in §2.1);
- G2 reproducing Part 3 (3.9)–(3.13) with u = 0;
- the block volume against direct integration of the profile;
- (F.6) against the analytic Green–Ampt solution for h_p constant and dz_cr/dt = 0.

## 8. Questions for review

1. The block width: w = b, with sides from (F.5)? Or no side resistance, or w = b + 2t?
2. Side friction with K₀ = 1 − sin φ′, or cohesion only on the sides?
3. A dry tension crack at the back scarp in P0 and P1, and a water-filled crack only in P2 above the
   phreatic line?
4. The c_s scenario values (0 / 1 / 3 kPa), pending a suction measurement or an estimate from the
   soil-water characteristic.
5. Is Green–Ampt (F.6) acceptable as the P1 working wetting model, with the gravity term and the
   crown-erosion correction?
6. The local face polyline over the pipe column (§5.3): it changes what the unchanged roof rule reads
   as cover in that column. Is that acceptable as a geometry input, not a rule change?

## Sources

- Wu, W. (2016). DL Breach technical report, §4.7 (roof block on vertical planes), Eqs. 4.21–4.27.
- Part 3 of this theory, §3.4 (planar wedge (3.9)–(3.13)).
- Casagrande, A. (1937). Seepage through dams. J. New England Water Works Assoc. 51(2).
- Green, W. H., Ampt, G. A. (1911). Studies on soil physics I. J. Agric. Sci. 4.
- Rawls, W. J., Brakensiek, D. L., Miller, N. (1983). Green–Ampt infiltration parameters from soils
  data. J. Hydraul. Eng. 109(1). *(values to verify)*
- Chu-Agor, M. L., Fox, G. A., Cancienne, R. M., Wilson, G. V. (2008). Seepage caused tension
  failures and erosion undercutting of hillslopes. J. Hydrol. 359(3–4), 247–259.
- Chu-Agor, M. L., Fox, G. A., Wilson, G. V. (2008). Numerical modeling of bank instability by
  seepage erosion undercutting of layered streambanks. J. Hydrol. Eng. 13(12), 1133–1145.
- Fox, G. A., Chu-Agor, M. L., Wilson, G. V. (2007). Seepage erosion: a significant mechanism of
  stream bank failure.
- Wahl, T. L. (2010). USBR PAP-1017 (P1 specimens collapsed when wetted).
