# Theory, Part 5 — Breach initiated by internal erosion (piping): pipe enlargement and roof collapse

*Lumped 1-D morphodynamic breach model · draft 1 · 2026-11-20 · status: for review*
*Built from the physical process (ARS piping tests, culvert hydraulics, hole-erosion-test mechanics,
Terzaghi's trapdoor problem). DL Breach, NWS BREACH, HR BREACH and WinDAM C are cited for what they do;
none is copied as the default where the physics points elsewhere.*

---

## 5.0 What the earlier TypeScript 1-D engine did

- Pipe invert forced to an estimated phreatic level; initial pipe radius 0.08 m.
- Flow: bare orifice C_d π R² √(2gH) with C_d = 0.6, so there was no pipe friction.
- Wall shear ρ g R_h (H/L), multiplied by 0.65 when the pipe was not full. Erosion was excess shear
  with material factors (×2.8 highly erodible, ×0.45 low erodible) and a non-equilibrium concentration.
- The eroded area was split 45 % to width and 55 % to height.
- Roof collapse when any of three rules fired: pipe height ≥ κ × (crest − invert) with κ = 0.55;
  width > 2.2 × cover with height > 0.25 × full height; or cover < an "arch need" term built from
  w²/8 and 0.35/tan φ. After collapse the open width was 1.0–1.2 × pipe width, opened gradually.

It used the hydraulic-gradient form of the wall shear, which is good physics (§5.3). Everything else
(0.6, 0.65, 45/55, 0.55, 2.2, 0.25, 0.35, gradual opening) was unsourced. The roof rules used no soil
strength at all.

---

## 5.1 The physical process

Piping-initiated breach tests on homogeneous cohesive embankments at the USDA-ARS laboratory
(Hanson et al. 2010a; Ali et al. 2021; photo sequence reproduced in Wu 2016, Fig. 2.14) show:

1. **Pipe enlargement.** Flow through a continuous defect erodes its walls. The pipe grows, and the
   flow grows with it — a positive feedback, so most of the growth happens at the end.
2. **Roof collapse.** When the pipe is wide enough, the soil bridge above it falls in. The roof can no
   longer carry its own weight across the opening.
3. **Open breach.** The flow now passes over the collapsed section as a weir. A deep notch has been
   cut from the crest down to the pipe invert, and the breach then develops as for overtopping
   (Parts 1–4).

The time to collapse varies by orders of magnitude with soil erodibility. The three ARS tests took
0.23 h (silty sand, non-plastic), 17.2 h (CL-ML) and 20.5 h (CL) (Hanson et al. 2010a, as tabulated in USBR PAP-1017, 2010).
Field cases often take days to weeks for the pipe stage and hours for the breach (Wu 2016, §2.2).

Two facts set the model:
- **A pipe needs a roof.** Internal erosion through an embankment progresses to breach only where the
  soil above can span the void (Reclamation/FERC internal-erosion best practice: "material to support
  a roof is present"). In a cohesionless soil the roof cannot stand. So roof strength (cohesion) is a
  physical input, not a tuning knob.
- **The 2019–2024 international model comparison found that the pipe and roof-collapse routines change
  peak outflow less than one might expect.** It covered AREBA, DL Breach, EMBREA, Rupro and WinDAM C on
  the ARS P1 test and the Big Bay dam failure. Peak flow is governed mostly by k_d and the roughness of
  the open breach (HR Wallingford FWR6124, 2025). The pipe stage mainly sets the **timing**, that is,
  when the open breach starts.

---

## 5.2 Pipe flow (extends Part 1, §1.4)

The pipe is a horizontal rectangular duct of width b_p and height a_p, with invert z_inv, crown
z_cr = z_inv + a_p and centreline z_bp = z_inv + a_p/2. Its length is the dam width at the
centreline, L_p = x_down(z_bp) − x_up(z_bp). A square of side D has the same R_h = D/4 as a circle of
diameter D, so the rectangle is hydraulically equivalent to the circular pipes of WinDAM C and the
hole erosion test. It also hands over directly to the rectangular open breach after collapse.

The discharge is the smaller of **inlet control** and **barrel (outlet) control**. This is standard
culvert hydraulics (Norman et al. 1985, FHWA HDS-5): the flow takes whichever control passes less
water.

    inlet, unsubmerged (z_s ≤ z_cr):  Q_in = 1.705 b_p (z_s − z_inv)^1.5          (critical depth, Part 1 (1.5))
    barrel, full (z_s > z_cr):        Q_br = A_p √( 2g (z_s − max(z_bp, z_t)) / (K_u + K_d + f L_p/(4R_h)) )   (1.9)
    Q_b = Q_in                     for z_s ≤ z_cr
    Q_b = min(Q_in, Q_br)          for z_s > z_cr                                          (5.1)

K_u ≈ 0.05 and K_d ≈ 1 (Part 1). With no tailwater model, z_t = 0, so the outlet is free and the
head is taken to the centreline of the outlet jet.

**Friction factor.** The default is the Manning-equivalent f = 8 g n² / R_h^(1/3) (Wu 2016, Eq. 3.15),
with the same n as the open breach. The option is Swamee–Jain with k_s = d50.

Why the Manning-equivalent is the default: an eroding soil wall is not a smooth pipe of roughness d50,
and using one roughness for the pipe and the open breach leaves one parameter instead of two.

The choice matters less than it seems, because of §5.3. In a long pipe, friction controls the flow,
and the wall shear does not depend on f.

---

## 5.3 Shear on the pipe wall

Momentum balance on the water in a full pipe gives the wall shear from the friction slope:

    τ_p = ρ g R_h S_f,     S_f = f U² / (8 g R_h)      ⇒   τ_p = ρ f U² / 8                (5.2)

In a long pipe, friction takes almost all the head, so S_f ≈ (z_s − z_bp)/L_p and

    τ_p ≈ ρ g R_h (z_s − z_bp) / L_p                                                       (5.3)

Equation (5.3) is the relation used to interpret the hole erosion test (Wan and Fell 2004). It is
independent of f. Equation (5.2) is the general form and is used in the model, because a short pipe
spends some of the head on entrance and exit losses. In a pipe that is not full, the shear is
Manning's at critical depth, as on the flat top in Part 1 (1.10).

---

## 5.4 Pipe enlargement

**Cohesive soils (detachment-limited).** The wall retreats normal to itself at the excess-shear rate,
uniformly around the perimeter and along the length. This is what NWS BREACH, DL Breach and WinDAM C
assume, and it matches the uniform shear of (5.2):

    ε = k_d (τ_p − τ_c)                                                                    (5.4)
    db_p/dt = 2ε,    da_p/dt = 2ε (ε for the crown only, once the invert reaches a hard base)
    dz_inv/dt = −ε (stops at the base)                                                     (5.5)

**Non-cohesive soils (transport-limited).** The outflow concentration follows Part 2:
C_out = C* + (0 − C*) exp(−L_p/L_s), with the capacity C* of the pipe flow (U, R_h, τ_p) and
L_s = λ b_p. The eroded bulk volume Q C_out dt/(1 − p) is spread uniformly over the wall area
2(a_p + b_p) L_p, which gives the same geometric update (5.5) with ε = dV/(2(a_p + b_p) L_p dt).

**Downstream-face cut-back (HR BREACH).** HR BREACH also lets the downstream face above the pipe exit
slump, which shortens the pipe. The ARS P1 test showed headcutting at the exit at the same time as the
pipe grew (USBR PAP-1017, 2010). This needs a second geometric state (an exit headcut) and is not in the default.
It is listed in §5.8 as an option for the sensitivity analysis.

---

## 5.5 Roof collapse — limit equilibrium of the soil bridge

Collapse is a soil-mechanics event. The roof is the soil between the pipe crown and the dam surface,
across the pipe width b_p, along the pipe length. Like DL Breach, the failure surfaces are taken as
the two vertical planes rising from the pipe walls. In the plane of the dam section, let A_r be the
longitudinal area of the roof: the dam section above z_cr, between x_up(z_cr) and x_down(z_cr).

**Vertical (fall-in) check, per pipe width.** The analysis uses total stress, undrained strength c_u:
collapse is fast, and the roof is a saturated cohesive soil.

    driving   = γ_t b_p A_r  +  W_w,top  −  p̄_i b_p L_cr,p
    resisting = 2 c_u A_r
    collapse when driving > resisting                                                     (5.6)

- **W_w,top** is the weight of reservoir water standing on the part of the roof under the upstream
  face: γ_w b_p × the area between z_s and the upstream face, above z_cr.
- **p̄_i** is the mean water pressure on the pipe soffit. The pressure head falls almost linearly
  along a friction-controlled pipe, from (z_s − z_cr − U²/2g·(1+K_u)) at the inlet to 0 at a free
  outlet, so p̄_i = ½ γ_w max(z_s − z_cr − (1+K_u) U²/2g, 0).
- **L_cr,p** is the length of the soffit, L_p.

**Why the water terms are both in.** DL Breach includes the water load on top but not the pressure in
the pipe. In a full pipe that pressure pushes up on the roof. Keeping one water term without the other
biases the roof toward early collapse. Both are included here, so the water action is consistent.
With them dropped, (5.6) reduces to

    b_p,crit = 2 c_u / γ_t                                                                 (5.7)

**Equation (5.7) is Terzaghi's trapdoor result.** A strip of half-width B over an unsupported opening
carries load at its base whenever γ B > c, at any depth (Terzaghi 1943, arching theory). So the
critical pipe width depends on the soil's strength and weight, not on the cover thickness. Examples:
- c_u = 10 kPa, γ_t = 20 kN/m³: b_crit = 1.0 m.
- Teton, c = 25 kPa: b_crit ≈ 2.5 m before water terms.
- Non-cohesive soil: b_crit → 0, so no pipe can stand. This is §5.1's "a pipe needs a roof", from the
  equations rather than a material label.

**Horizontal (push-out) check.** The reservoir pushes the roof downstream over the height above the
crown. Resistance is cohesion on the two side planes (DL Breach, Wu 2016 §4.7):

    ½ γ_w max(z_s − z_cr, 0)² b_p  >  2 c_u A_r                                            (5.8)

This rarely governs except for thin dams with a high reservoir. It is kept for completeness.

**Friction on the side planes (option).** A rigid roof block with at-rest earth pressure
K_0 = 1 − sin φ on its sides adds friction 2 K_0 tan φ γ_t ∫ s dA. That makes thicker roofs hold
wider pipes. Terzaghi's slice analysis shows the base of the strip still loads whenever γB > c, so
the rigid-block friction overstates the stability of a deep roof. It is offered only as a sensitivity
option.

---

## 5.6 After collapse — hand-over to the open breach

At collapse, the roof material falls into the opening. The breach becomes a notch from the crest down
to z_inv, with bottom width b_p. The walls are vertical while a vertical bank of height H − z_inv
stands (Part 3), otherwise at the Part 3 bank-stability angle. The flat top runs the full dam width at
z_inv, from x_up(z_inv) to x_down(z_inv). Below the pipe exit, the downstream face is intact.

That geometry is exactly the initial state Parts 1–4 already handle:
- **Cohesive soils with k_d**: the notch enters the Part 4 staged process at stage 1. Flow leaves the
  end of the notch invert onto the downstream face, erodes it and may plunge. This is the one process
  model of Part 4 decision 1, with no special post-piping rule.
- **Non-cohesive soils**: Parts 2–3 (flat top + slope reach, rotation about the toe).

**The fallen roof.** DL Breach, NWS BREACH and HR BREACH keep the collapsed block in the channel
until the flow has carried it away, pausing geometric change (DL Breach's "virtual tank"). Physically
the debris does sit in the opening. For a non-cohesive soil, the flow has to move it at transport
capacity. For a cohesive soil, the blocks are eroded at k_d(τ − τ_c) like any exposed surface.

The default proposed is that **the roof volume enters a debris store**. The store is emptied at the
current erosion rate of the breach before the bed and walls erode further, and outflow is computed on
the open geometry throughout. The alternative is instant removal. This choice moves the start of the
open-breach growth, so it is a decision (§5.8, item 5).

---

## 5.7 Inputs and the cases that test this part

**Inputs added to the case file (`mode: "piping"`):** initial pipe width and height, invert elevation
(given, never forced to an estimated phreatic level), and c_u for the roof. Where only c is given,
c_u = c, and Phase 4 records the source of each value.

**Cases (Phase 4 assembles; the blind subset is pre-registered before any scoring):**

| case | type | why | status |
|---|---|---|---|
| ARS P1, P2, P3 (Hanson et al. 2010a) | lab, ~1.3 m (P1), JET k_d | measured erodibility, collapse times 0.23–20.5 h | data to obtain |
| ARS intermediate-scale tests (Ali et al. 2021) | lab, 4 embankments | pipe enlargement rates over orders of magnitude | data to obtain |
| Big Bay, MS (2004) | field, 15.6 m | international benchmark case (FWR6124), DL Breach card on file | card on file |
| Teton, ID (1976) | field, 93 m | classic piping failure, DL Breach card on file | card on file |
| IMPACT field test 5 (2003) | field, 4.3 m, moraine | piping in a coarse cohesive soil; links to Part 7 | workbook on file |
| Wahl (1998) piping cases in Wu (2016) Table 6.8 | field | many parameters marked "assumed" in DL Breach | supporting only |

**Verification this part must pass (Phase 3):**

| test | expected |
|---|---|
| (5.1) | equals (1.5) for z_s ≤ z_cr; equals (1.9) for a long full pipe; Q non-decreasing in z_s |
| (5.2)–(5.3) | τ_p → ρ g R_h Δh / L_p for f L_p/4R_h ≫ K_u + K_d |
| (5.4)–(5.5) | zero growth below τ_c; eroded volume = perimeter × length × ε dt exactly |
| (5.7) | no-water limit of (5.6) gives b_crit = 2c_u/γ_t for any cover |
| hand-over | geometry after collapse = Part 4 initial notch; water balance < 1e-9 across collapse |
| dt convergence | Qp, Tp, collapse time with p ≈ 1 on the piping cases |

---

## 5.8 Decisions for review (physics-based)

1. **Pipe shape**: rectangle, square at the start, uniform wall retreat (5.5). It is hydraulically
   equal to a circle of the same R_h and hands over directly to the open breach.
2. **Pipe flow**: culvert rule (5.1), the smaller of inlet and barrel control, instead of DL Breach's
   switch at the crown. Friction is the **Manning-equivalent f with the breach n** (default), with
   Swamee–Jain (k_s = d50) as an option.
3. **Wall shear**: the momentum form τ_p = ρ f U²/8 (5.2), which tends to the hole-erosion-test form
   (5.3) in long pipes. Non-cohesive pipes use the Part 2 capacity and relaxation.
4. **Roof collapse**: limit equilibrium (5.6) with c_u and γ_t, **including both** the water load on
   top and the pressure in the pipe. The horizontal push-out (5.8) is also checked. Side-plane
   friction is a sensitivity option only (Terzaghi arching). The κ- and cover-ratio rules of the old
   engine are dropped.
5. **Fallen roof**: debris store emptied at the breach erosion rate before the geometry changes
   (default), with instant removal as the option.
6. **After collapse**: the notch hands over to Part 4 stage 1 (cohesive with k_d) or to Parts 2–3
   (non-cohesive). No post-piping rules of its own.
7. **Exit cut-back** (HR BREACH): not in the default; sensitivity option once an exit headcut state
   exists.
8. **Pipe location**: always a case input (invert and size), never estimated from a phreatic line.
   Where a source gives none (some Wahl 1998 cases), the case is marked and used only as supporting
   evidence.

---

## References

- Ali, A. K., Hunt, S. L., Tejral, R. D., et al. (2021). Embankment breach research: observed internal
  erosion processes. *Trans. ASABE*. doi:10.13031/trans.13701.
- Fread, D. L. (1988, rev. 1991). *BREACH: An erosion model for earthen dam failures*. NWS, Silver Spring.
- Hanson, G. J., Tejral, R. D., Hunt, S. L., and Temple, D. M. (2010a). Internal erosion and impact of
  erosion resistance. *Proc. 30th USSD Conf.*, Sacramento (as cited in DSO-2017-02).
- HR Wallingford (2025). *Breach Model Validation Programme — Internal erosion initiated breach: model
  performance review & validation*. FWR6124-RT001 R01-00.
- Hunt, S. L., Temple, D. M., Neilsen, M. L., Ali, A., and Tejral, R. D. (2021). WinDAM C: analysis
  tool for predicting breach erosion processes of embankment dams due to overtopping or internal
  erosion. *Appl. Eng. Agric.*, 37(3), 523–534.
- Norman, J. M., Houghtalen, R. J., and Johnston, W. J. (1985). *Hydraulic design of highway culverts*.
  HDS-5, FHWA.
- Terzaghi, K. (1943). *Theoretical Soil Mechanics*. Wiley, New York. Ch. 5 (arching, trapdoor).
- USBR PAP-1017 (2010). Analysis of the soils used in the ARS embankment piping erosion and breach
  tests. *Joint Federal Interagency Conf. on Sedimentation and Hydrologic Modeling*, Las Vegas
  (authors and full title to be confirmed from the PDF; the USBR server was down on 2026-11-20).
- Reclamation / FERC (2010). *Dam Safety Risk Analysis Best Practices — Internal Erosion* (slides).
- Atkinson, A., and Neilsen, M. (2024). Analysis of uncertainty in internal erosion simulations for
  DLBreach and WinDAM C. *GeoHazards*, 5(2), 18 (ARS P1 and Big Bay).
- Wahl, T. L., et al. (2017). DSO-2017-02, Bureau of Reclamation (NWS BREACH, HR BREACH, WinDAM C).
- Wan, C. F., and Fell, R. (2004). Laboratory tests on the rate of piping erosion of soils in
  embankment dams. *Geotech. Testing J.*, 27(3), 295–303.
- Wu, W. (2016). *Introduction to DLBreach*, v2016.4. §2.2, §3.2, §4.7, §6.4.
