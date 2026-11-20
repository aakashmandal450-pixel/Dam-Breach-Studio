# Theory, Part 4 — Headcut migration (cohesive dams, overtopping)

*Lumped 1-D morphodynamic breach model · draft 1 · 2026-11-20 · status: for review*

Compacted cohesive embankments overtopped by water do not erode as a smooth surface. Rills grow into
cascading overfalls, these merge into one large headcut on the downstream slope, and the headcut
migrates upstream through the crest; once the crest is gone the breach flow rises sharply and the breach
widens (Hanson et al. 2005; Wu 2016, §2.1.2, Fig. 2.5). DL Breach therefore uses a headcut mode as the
default for cohesive embankments, with surface erosion (Parts 2–3) as the alternative (Wu 2016, §2.1.2,
§4.5). Equations below are read from Wu (2016, §4.5) unless marked "our derivation".

---

## 4.1 Geometry in headcut mode

Longitudinal section (Wu 2016, Figs. 4.12–4.13):

- **Flat top** at elevation z_b, from the upstream face x_u(z_b) to either the downstream crest edge
  (while the headcut is still on the downstream slope) or the headcut position x_h.
- **Downstream slope** between the crest edge and the headcut brink (only while x_h is downstream of
  the crest).
- **Headcut**: a vertical drop at x_h, from the brink down to the dam base. Downstream of it the breach
  channel runs at base level with bottom width b_d and the side slope of Part 3.
- The headcut **starts at the downstream toe** (x_h = x_T at t = 0) and migrates upstream (Wu 2016,
  §2.1.2).

Brink height: on the downstream slope h_x = z_dam(x_h) (the original face); once x_h is inside the flat
top, h_x = z_b. Headcut height at the crest: H_hc = z_b (base at z = 0).

The breach discharge is still controlled by the flat top (weir, Part 1) until the crest is gone.

---

## 4.2 Headcut migration rate

**Default — Temple (1992) (Wu 2016, Eq. 4.31; DL Breach default):**

    dx_h/dt = −C_T · q^(1/3) · H_e^(1/2) · k_early                                        (4.1)

- q: unit discharge over the headcut [m²/s]; H_e: drop in the energy grade line through the headcut,
  approximated by the overfall height H_hc (Wu 2016).
- C_T [m^(−1/6) s^(−2/3)]: material coefficient. DL Breach calibrated C_T = 0.0049 on E1S1 and 0.0025 on
  IMPACT field test 1, and used 0.0049 for its other cohesive cases (Wu 2016, Ch. 6).
- **Calibration factor C_h:** C_T = C_h · 0.0049. C_h = 1 is DL Breach's value.
- **Early-stage correction** k_early: the rate laws assume a headcut of constant height. On the downstream
  slope the eroding material is only the brink of height h_x < H_hc, so DL Breach multiplies the rate by
  H/h_x, "implemented as min(H/h_x, 0.01H)" so that it works at the toe (Wu 2016, §4.5). As printed this
  mixes a ratio with a length; we read it as a floor on h_x:

      k_early = H_hc / max(h_x, 0.01 H_hc)            (= 1 once the headcut is inside the flat top)   (4.2)

  (our reading of the source, made explicit).

**Options (Wu 2016, Eqs. 4.28–4.30, 4.32):**

| law | form | coefficients |
|---|---|---|
| `sites` | dx/dt = C1 [(qH)^(1/3) − A0], q in ft²/s, H in ft, rate in ft/h | C1 = −0.79 ln K_h + 3.04 (K_h < 18.2), 0.75 otherwise; A0 = 0 for K_h < 0.01, else [189 K_h^(1/2) e^(−3.23/ln(101 K_h))]^(1/3) |
| `temple2005` | dx/dt = C2 (qH)^(1/3) | C2 [s^(−2/3)] from the case file |

Both multiply by k_early and by C_h. (Note: the 2-D engine's SITES threshold A0 is a different formula
from Wu's Eq. 4.30; the lumped model follows Wu, and the 2-D discrepancy is recorded for the 2-D notes.)

---

## 4.3 Widening and lowering during migration

- **Downstream of the headcut** the channel widens in proportion to the migration
  (Wu 2016, §4.5):

      Δb_d = α_c · n_loc · |Δx_h|,     α_c = 0.165                                         (4.3)

  α_c is DL Breach's tested value; it "may vary for different soils". It is a sourced constant here,
  not a calibration factor.
- **Flat top upstream of the headcut** is lowered and widened by the cohesive surface-erosion model of
  Parts 2–3 (Wu 2016, §4.5), with the flat-top length L_top = min(x_h, x_c1) − x_u(z_b).
- **Downstream-slope segment** between the crest edge and the brink: DL Breach describes erosion only
  on the flat top and the headcut, so this segment is not eroded in headcut mode (our reading).

---

## 4.4 End of the crest: failure of the remaining block

As the headcut approaches the upstream face the block of embankment between them gets shorter.
DL Breach checks it for **horizontal sliding along the dam base** (Wu 2016, §4.5, Fig. 4.14): driving
forces are the water pressure on the upstream slope and the flow shear on the breach top; resisting
forces are cohesion and friction on the base and on the two sides of the block, plus tailwater pressure.
DL Breach does not print the equations, so **our derivation**, per breach (block width b):

    F_drive  = ½ γ_w z_s² · b  +  τ_top · L_top · b                                        (4.4)
    F_resist = (C · L_base + W tan φ) · b  +  2 C · A_blk  +  ½ γ_w max(z_t, 0)² · b        (4.5)

with A_blk the longitudinal area of the block (dam section between the upstream toe and x_h, below z_b),
L_base its base length, W = γ_b A_blk its weight per unit width (γ_b from Part 3), and n_loc = 2 side
planes (2C·A_blk; one plane if n_loc = 1). Pore pressure on the base is neglected, as in Part 3. Failure
when F_drive > F_resist.

**After failure** the block is not washed out at once: its volume goes into a "virtual tank"; erosion
computed afterwards first empties the tank and changes the geometry only when the tank is empty
(Wu 2016, §4.5). The breach floor is then the base, with bottom width b_d, and widening continues by
Parts 2–3 on the fixed bed (§3.5-1). If the block never fails, the crest disappears when x_h reaches
x_u(z_b), with the same result.

---

## 4.5 Verification this part must pass (Phase 3)

| test | expected |
|---|---|
| (4.1) units | C_T 0.0049, q = 1 m²/s, H = 1 m, k_early = 1 → 0.0049 m/s |
| (4.2) | k_early = 1 inside the flat top; finite at the toe (h_x = 0) |
| SITES option | reproduces a hand value in ft/h converted to m/s |
| (4.3) | b_d − b_d,0 = α_c n_loc (x_T − x_h) at all times |
| (4.4)–(4.5) | hand example; failure flag switches once, monotonically, as x_h moves upstream |
| virtual tank | sediment balance closes across the failure (< 1e-9 relative) |
| mode switch | headcut mode and surface mode give identical results while Q_b = 0 |
| dt convergence | Qp, Tp, B converge with p ≈ 1 on E1S1, E2S2, GooseCreek |

---

## 4.6 Decisions for review

1. **Headcut mode is the default for cohesive overtopping cases** (DL Breach default); surface erosion
   (current code) stays as an option — proposed.
2. **Default law Temple (1992), C_T = C_h × 0.0049** — proposed. Note: the 2-D engine used a different law
   and base value (energy law, 0.05 × C_h), so cal-2's C_h = 10 does not carry over.
3. **α_c = 0.165 fixed** (DL Breach tested value) — proposed.
4. **Early-stage correction read as H/max(h_x, 0.01H)** — proposed.
5. **Unit discharge q = Q_b / b_d** (flow over the headcut, whose width is the downstream channel bottom
   width) — proposed; DL Breach does not state which width.
6. **Block failure:** use our horizontal-sliding derivation (4.4)–(4.5) with the virtual tank — proposed;
   alternative: no block check, crest disappears when the headcut reaches the upstream face.
7. **No erosion on the downstream-slope segment above the brink** in headcut mode — proposed.

---

## References

- Hanson, G. J., Cook, K. R., and Hunt, S. L. (2005). Physical modeling of overtopping erosion and breach
  formation of cohesive embankments. *Trans. ASAE*, 48(5), 1783–1794.
- Temple, D. M. (1992). Estimating flood damage to vegetated deep soil spillways. *Appl. Eng. Agric.*,
  8(2), 237–242 (as cited in Wu 2016).
- Temple, D. M., Hanson, G. J., Neilsen, M. L., and Cook, K. R. (2005). Simplified breach analysis model
  for homogeneous embankments: Part 1, background and model components. *USSD Conference*, Salt Lake
  City (as cited in Wu 2016).
- USDA-NRCS (1997). *SITES water resource site analysis computer program, user's guide* (as cited in
  Wu 2016).
- Wu, W. (2016). *Introduction to DLBreach*, version 2016.4, technical report, Clarkson University.
  §2.1.2, §4.5, Ch. 6.
