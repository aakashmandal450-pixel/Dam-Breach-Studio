# Theory, Part 3 — Breach deepening, widening and side-slope stability

*Lumped 1-D morphodynamic breach model · draft 2 · 2026-11-20 · status: decisions made*

Part 2 gives an eroded bulk volume ΔV per reach (flat top, downstream slope) and time step. This part
turns that volume into new breach geometry — bed lowering, bottom and top widening — and sets the
breach side slope from bank stability. Headcut migration for cohesive dams is Part 4.

All equations below were read directly from the DL Breach technical report (Wu 2016, §4.3–4.4) unless
marked otherwise.

---

## 3.1 Why this replaces the TypeScript engine's width rule

The TypeScript engine split each eroded volume by a fixed share between bed and banks
(35–50 % to the bed, the rest to the banks, plus a ×1.25 widening factor and a width cap of
1.05 × crest length). None of these numbers had a source, and width is a primary output. Here the
width follows from geometry: the same erosion thickness acts on the bed and the side walls (Part 2),
and the side slope is set by slope stability.

---

## 3.2 Flat-top reach: from eroded volume to geometry

The eroded volume is spread over the whole erodible surface of the breach on that reach — the bed and
both side walls, including the part of the walls above the water, because material above the water
slides (non-cohesive) or fails (cohesive) into the channel as the toe is undercut (Wu 2016, Fig. 4.5).
The resulting normal erosion thickness is

    Δz_b = ΔV / A_e,tot                                                                (3.1)
    A_e,tot = A_bed + n_loc · A_side / sin β                                            (3.2)

- A_bed = b · L_top: breach bed area on the flat top (L_top: flat-top length in the flow direction).
- A_side: area of the breach side wall projected on the vertical plane normal to the dam axis, i.e. the
  area of the dam's longitudinal section that lies above z_b over the flat-top reach (Wu 2016, Fig. 4.6).
  Computed from the dam geometry (crest width, upstream and downstream slopes).
- sin β converts the projected area to the inclined side-wall area.
- n_loc: number of erodible sides — 2 for a breach in the middle of the crest, 1 for a breach against an
  abutment (Wu 2016). Default 2 unless the case says otherwise.

(Wu 2016, Eqs. 4.14–4.15.) Since A_e,tot is larger than the wetted area A_e used in Part 2, the actual
thickness Δz_b is smaller than the erosion thickness Δε of the wetted surface: the difference is the
slid or failed material that refills the undercut toe.

**Geometry update.** With the side slope β fixed during the step:

    z_b  ←  z_b − Δz_b                                                                  (3.3)
    ΔB   =  n_loc · Δz_b / sin β              (width at water surface / crest)            (3.4)
    Δb   =  n_loc · Δz_b · (1/sin β − 1/tan β)    (bottom width)                          (3.5)

(Wu 2016, Eqs. 4.16–4.17.) Each side wall retreats by Δz_b normal to itself; 1/sin β converts that to a
horizontal shift at the crest, and the bottom corner moves by the difference.

**Cohesive material.** Part 2 gives ΔV = Δε · A_e for the wetted surface (Wu 2016, §4.2.1); (3.1)–(3.5)
then apply unchanged ("surface erosion" mode). Mass failure of cohesive banks is handled by the side
slope (§3.4), which DL Breach releases gradually rather than as discrete blocks (Wu 2016, §4.3.1).

---

## 3.3 Downstream-slope reach

**Width.** If the breach on the downstream slope is much wider than on the flat top, the flow separates
along the downstream walls and widens them less. DL Breach reduces the widening there by

    c_b = min[ 1, max( 0, 1.8 · b_up / b_down − 0.8 ) ]                                  (3.6)
    ΔB_down = n_loc · c_b · Δz_b / sin β                                                  (3.7)
    Δb_down = n_loc · Δz_b · [ max( c_b / sin β, 1/tan β ) − 1/tan β ]                    (3.8)

b_up, b_down: bottom widths of the flat-top and downstream-slope reaches (Wu 2016, Eqs. 4.18–4.20).

**Longitudinal profile.** The downstream slope rotates about the downstream toe: the erosion thickness
is zero at the toe and grows linearly up the slope, so the flat top shortens from downstream as its
downstream edge advances, until the flat top disappears and the profile is a single slope (Wu 2016,
§4.3.2, Figs. 4.8–4.9). DL Breach gives no equations for this step ("details are not given here because
of the complex geometry"), so **we derive them ourselves** in Appendix 3A (to be written with the
geometry code): the eroded volume on the slope reach ΔV_down, distributed with a linear thickness
profile, fixes the rotation angle; the new slope intersects the flat top at the new edge position.
The derivation is checked by volume closure (verification table).

**Side slope** on the downstream reach is taken equal to that on the flat top (Wu 2016).

---

## 3.4 Side slope from bank stability (planar failure)

The breach side wall of height H (taken as the breach depth below the crest, H = z_cr − z_b) fails on a
plane through its toe at angle α. Driving and resisting forces per unit length:

    F_d = ½ γ_b H² (1/tan α − 1/tan β) sin α                                              (3.9)
    F_r = ½ γ_b H² (1/tan α − 1/tan β) cos α tan φ + C H / sin α                          (3.10)

with the bulk unit weight

    γ_b = (1 − p) γ_s + f_w p γ_w,   f_w = 0.5                                            (3.11)

(f_w: fraction of the pores filled with water; Wu 2016 takes 0.5 for partly submerged breach walls.
Water pressures from breach flow and groundwater are assumed to balance.) Stability (F_d ≤ F_r for every
α) gives the steepest stable slope β_s:

    1/tan β_s = 1/tan φ + (1/tan² φ) · [ 4C/(γ_b H) − √( (16C²/(γ_b² H²) + 8C tan φ/(γ_b H)) (1 + tan² φ) ) ]
                                                                                           (3.12)
and the corresponding failure-plane angle

    tan α_s = ½ (1 + tan φ / tan β_s) / ( 2C/(γ_b H) + 1/tan β_s )                        (3.13)

(Wu 2016, Eqs. 4.21–4.26; planar wedge after Culmann.) For C = 0 both reduce to β_s = α_s = φ.

**Check against the 2-D engine.** (3.12) is the Culmann critical-height relation solved for the slope:
for C > 0, the 2-D engine's `BankStability.critical_height(β_s)` = 4C sin β_s cos φ / (γ_b (1 − cos(β_s − φ)))
returns exactly H. Verified numerically for four (C, H, φ) combinations (e.g. C = 25 kPa, H = 12.8 m,
φ = 28.8° → β_s = 80.1°, H_c = 12.800 m). So the lumped model uses the same bank physics as the 2-D
engine, without its per-cell triggers.

**Side slope used in the model:**

    β = (α_s + β_s) / 2                                                                    (3.14)

(Wu 2016, Eq. 4.27.) While even a vertical wall of the current height is stable — (3.12) has no real
solution with β_s < 90° — no failure has happened yet and the wall stays vertical (β = 90°), as Wu (2016,
§4.4) describes for a shallow pilot breach. Averaging with the α_s of (3.13) in that range would make β
*rise* with H, which is not physical; this is our reading of the source, made explicit.

The slope lies between the steepest stable angle and the angle after failure;
DL Breach takes the average. Consequences: non-cohesive soil → β ≈ φ; more cohesion → steeper β; a
higher bank → flatter β. β is recomputed every step from the current H, so it changes smoothly as the
breach deepens — there is no on/off failure trigger.

**Mass failure.** When β decreases between steps, the soil between the old and new slope lines fails.
Because (3.14) uses the average angle, that wedge is half of the actual failure block; DL Breach washes it
downstream immediately and lets the other half come down gradually through the sliding mechanism of
§3.2 (Wu 2016, §4.4). In the model the wedge volume is added to the sediment leaving the breach in that
step, so the sediment balance closes.

---

## 3.5 Limits on the breach

1. **Bottom of the dam.** When z_b reaches the dam base (or the top of a non-erodible foundation) the bed
   stops lowering; A_bed is removed from A_e,tot (the bed is no longer erodible), and erosion continues as
   widening only (Wu 2016, §4.2.1, Fig. 4.11).
2. **Erodible foundation (option).** If a case has an erodible base, DL Breach lets erosion continue into
   it with widening 1.6 × deepening, i.e. (3.7) with c_b = 1.6 (Wu 2016, §4.3.2).
3. **Abutments (our addition, geometric).** The breach cannot be wider than the valley at crest level.
   When one breach edge reaches an abutment, that side stops eroding (n_loc drops by 1). This replaces the
   TypeScript cap of 1.05 × crest length. It is a geometric constraint, not a coefficient.

---

## Appendix 3A — Rotation of the downstream slope about the toe (our derivation)

Longitudinal coordinate x from the upstream toe; dam base at z = 0; downstream toe at x_T. The flat top
is at z_b between the upstream face x_u(z_b) = z_u z_b and its downstream edge x_e; the downstream-slope
reach is the straight line from (x_e, z_b) to (x_T, 0), length L_s = √((x_T − x_e)² + z_b²).

1. **Flat-top lowering moves the edge downstream.** When the top lowers from z_b to z_b′ (3.3) with no
   slope erosion, the new edge is where the unchanged slope line reaches z_b′:
   x_e′ = x_T − (x_T − x_e) z_b′/z_b.
2. **Slope erosion rotates the line about the toe.** With mean normal thickness δ = ΔV_down / A_e,tot,down
   (A_e,tot,down = b_down L_s + n_loc A_side,down / sin β) and a thickness growing linearly from 0 at the
   toe, the longitudinal area removed is δ · L_s. The removed region is the triangle (toe, old edge, new
   edge) at elevation z_b, so
       x_e′ = x_e − 2 δ L_s / z_b.
3. **Flat top consumed.** If x_e′ would fall upstream of x_u(z_b), the flat top is gone; the rest of the
   area lowers the slope's upper end along the upstream face to the elevation z″ that makes the triangle
   (toe, (x_u(z_b), z_b), (x_u(z″), z″)) equal to the remaining area (solved by bisection).
4. **Base reached.** When z_b = 0 the slope reach vanishes, the breach floor is the dam base
   (x from 0 to x_T), and erosion continues as widening only (§3.5-1).

Volume closure is checked numerically (§3.6): the geometric breach volume and ∫ΔV agree to first
order and converge as Δt → 0.

---

## 3.6 Verification this part must pass (Phase 3)

| test | expected |
|---|---|
| (3.3)–(3.5) | breach volume from geometry vs ∫ΔV: first-order consistent, gap → 0 as Δt → 0 |
| (3.1)–(3.2) | ΔV distributed over A_e,tot returns ΔV when integrated back over the new geometry |
| (3.12) at C = 0 | β_s = φ exactly |
| (3.12) vs 2-D Culmann | critical_height(β_s) = H to 1e-9 for a grid of (C, H, φ) |
| (3.14) trends | β decreases with H, increases with C (monotonic over the test grid) |
| (3.6) | c_b = 1 for b_down ≤ b_up; 0 for b_down ≥ 2.25 b_up |
| mass failure | wedge volume added to sediment outflow; sediment balance < 1e-9 relative |
| downstream rotation (App. 3A) | eroded volume on the slope reach = volume between old and new profiles |
| abutment limit | B never exceeds the valley width; n_loc drops to 1 at the first abutment |

---

## 3.7 Decisions (Aakash, 2026-11-20 — all five proposals accepted)

1. **Water fraction f_w = 0.5** in the bulk unit weight (Wu 2016).
2. **Downstream-slope rotation:** we write our own derivation (Appendix 3A), since DL Breach does not give
   one, and verify it by volume closure.
3. **Foundation:** non-erodible base by default; erodible base with c_b = 1.6 only where a case says so. (None of the current case files specifies the foundation; Phase 4 checks each source.)
4. **Abutment limit** as in §3.5-3 (our addition).
5. **Breach location:** n_loc = 2 (mid-crest) unless the case states an abutment breach.

---

## References

- Culmann, K. (1866). *Die graphische Statik*. Meyer & Zeller, Zürich.
- Wu, W. (2016). *Introduction to DLBreach — a simplified physically-based dam/levee breach model*,
  version 2016.4, technical report, Clarkson University. §4.3–4.4, Eqs. 4.14–4.27.
- Wu, W. (2013). Simplified physically based model of earthen embankment breaching. *J. Hydraul. Eng.*,
  139(8), 837–851.
