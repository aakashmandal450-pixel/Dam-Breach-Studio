# Theory, Part 2 — Bed erosion

*Lumped 1-D morphodynamic breach model · draft 2 · 2026-11-20 · status: decisions made, source check open*

Part 1 gives the breach discharge Q_b and the bed shear τ_b on two reaches: the flat breach top and the
downstream slope. This part turns that flow into an eroded volume per reach and per time step. How the
eroded volume changes the breach shape (deepening, widening, bank collapse) is Part 3; headcut migration
for cohesive dams is Part 4.

---

## 2.1 Two material classes, two erosion mechanisms

The case file gives the material class. Each class has one erosion mechanism, and the model never
mixes them:

| class | mechanism | cases |
|---|---|---|
| **cohesive** | detachment-limited: erosion rate set by excess shear on the soil (2.2) | E1/E2 series, GooseCreek, LaurelRun, IMPACT_1-02 |
| **non-cohesive** | transport-limited: erosion set by the flow's capacity to carry sediment, approached over an adaptation length (2.3–2.4) | Castlewood, SouthFork, Poerua, Yigong, IMPACT_2C-02, Walsh series |

This replaces the TypeScript engine's HE/ME/LE erodibility classes and their rate multipliers
(×0.45 to ×2.8), which had no source. It also prevents a problem found in the 2-D law sweep: running a
detachment law on non-cohesive material with default soil values (τ_c = 1 Pa, n = 1) made Hanson and
Partheniades algebraically identical and produced meaningless runs.

---

## 2.2 Cohesive material — excess-shear detachment

    ε = f_kd · k_d · max(τ_b − τ_c, 0)^n                                              (2.1)

ε: erosion rate normal to the eroding surface [m/s]; k_d: erodibility [m³/(N·s)]; τ_c: critical shear
stress [Pa]; n = 1 (linear excess-shear law). Source: Partheniades (1965) form, with k_d and τ_c from
submerged jet (JET) tests (Hanson & Cook 2004). DL Breach uses the same law for cohesive breaches
(Wu 2013, Eq. 4.12).

- **Inputs from the case file:** `kd_cm3Ns` (converted × 1e-6 to m³/(N·s)) and `tauc_Pa`. Every
  current cohesive case has both.
- **Calibration factor f_kd:** multiplies k_d only where k_d is *measured* (case `kd_status` starts
  with "measured"), the rule already used in cal-1 and cal-2. Assumed k_d values are used as given.
- **Where it acts:** the same erosion thickness applies to the bed and the wetted side walls, because
  wall and bed shear are comparable in a narrow breach (Wu 2013). The eroded volume per reach is

      ΔV = ε · P_w · L_r · Δt                                                            (2.2)

  with P_w the wetted perimeter and L_r the reach length. Part 3 converts ΔV into bed lowering and
  side-wall retreat.
- **Partheniades form** ε = M (τ_b/τ_c − 1) is the same law with M = k_d τ_c; it is kept only as an
  alternative way of entering the input, not as a second physics option.

---

## 2.3 Non-cohesive material — transport capacity

**Default (decision 2.7-1): DL Breach combination — Wu, Wang & Jia (2000) bed load (2.3) plus
Zhang (1961) suspended load (2.4a), single size class, as in Wu (2013).**

Bed load:

    q_b* = f_t · 0.0053 · (τ_b′/τ_c − 1)^2.2 · √((s − 1) g d50³)                        (2.3)
    τ_c = θ_c (ρ_s − ρ) g d50,   θ_c = 0.03
    τ_b′ = (n′/n)^(3/2) τ_b,     n′ = d50^(1/6) / 20

Suspended load, default — Zhang (1961), as used in DL Breach (Wu 2013, Eq. 4.6):

    C_s* = f_t · Zhang (1961) suspended-load capacity                                    (2.4a)

The exact form and coefficients of (2.4a) are to be transcribed from the original sources (Zhang 1961,
as implemented in Wu 2013/2016); the online report copy was not legible. This is a blocking item for
coding Part 2.

Suspended load, option `wu2000` — Wu, Wang & Jia (2000):

    q_s* = f_t · 2.62e-5 · [ (τ_b/τ_c − 1) U / ω_s ]^1.74 · √((s − 1) g d50³)            (2.4)

ω_s: settling velocity of d50 (Soulsby 1997). s = ρ_s/ρ. Total capacity q_t* = q_b* + q_s* per unit
width, and as a volumetric concentration C_t* = q_t* · B_w / Q_b, with B_w the water-surface width.
The Wu (2000) bed-load formula is used with its own θ_c = 0.03 and grain roughness n′, not with the
2-D engine's θ_c = 0.047.

**Calibration factor f_t:** multiplies the capacity, as `transport_capacity_factor` did in cal-2.

**Options (for sensitivity and comparison only):**

| law | form | source |
|---|---|---|
| `mpm` | q_b* = f_t · 8 (θ′ − 0.047)^1.5 √((s−1) g d50³) | Meyer-Peter & Müller (1948) |
| `vanrijn` | q_b* = f_t · 0.053 √((s−1) g) d50^1.5 T^2.1 / D*^0.3 | van Rijn (1984) |
| `wu2000` | Wu (2000) bed load + Wu (2000) suspended load (2.4), one paper fitted together | Wu, Wang & Jia (2000) |

Each law uses its own published grain-shear definition and θ_c. This refines Part 1's decision 3
("Strickler n′ for grain shear"): the grain shear is law-specific, and Strickler applies only where the
law itself used it.

**Steep slope.** On the downstream face the bed slope β (tan β = S_0) helps gravity move grains
downslope, so the critical shear is lower:

    τ_c,β = τ_c · sin(φ − β) / sin φ                                                     (2.5)

φ: friction angle of the dam material (case `tan_phi`). Source: Chiew & Parker (1994) for streamwise
slopes. (2.5) is 1 × τ_c on a flat bed and 0 at β = φ (the slope fails, Part 3). DL Breach uses an
effective-shear correction for the same effect (Wu 2013, Eqs. 4.8–4.9); the equation in the copy we
read was not legible, so (2.5) is used and the two will be compared once the original is checked.

---

## 2.4 Non-equilibrium: approach to capacity along each reach

The breach is short, so the sediment load usually does not reach capacity by the time the flow leaves
it (Wu 2013). Along each reach the load relaxes towards capacity:

    ∂(Q C_t)/∂x = Q (C_t* − C_t) / L_s                                                   (2.6)

With Q and C_t* constant along a reach within one time step, (2.6) integrates exactly to

    C_t,out = C_t* − (C_t* − C_t,in) · exp(−L_r / L_s)                                  (2.7)

(Wu 2013, Eq. 4.3). Water from the reservoir enters clear (C_t,in = 0 on the breach top); the breach-top
outflow is the inflow to the downstream slope.

**Adaptation length:**

    L_s = λ · B_w,   λ = 6 for field cases, 3 for laboratory cases                        (2.8)

(Wu 2013/2016 default values). λ is a sourced parameter, not calibrated; it is a candidate for the
Phase 5 sensitivity analysis.

**Eroded volume per reach (Exner, bulk volume):**

    ΔV = Q_b (C_t,out − C_t,in) Δt / (1 − p)                                              (2.9)

p: porosity (case file). A negative ΔV is deposition. (Wu 2013, Eq. 4.5.)

This replaces three TypeScript-engine shortcuts: the non-equilibrium floor that kept transport above
half of capacity, the transport reach set to the crest width only, and the per-step erosion caps.

---

## 2.5 What is deliberately not included

1. **Chen erosion cap.** The 2-D engine has a hyperbolic cap E = scale · k · ex / (a + b · ex) with
   k = 100, a = 1, b = 0.5 and a scale of 1e-3 marked "calibration scale". No published source for these
   values was found, so under the sourcing rule it is left out. It can come back if a source is found.
2. **Multiple grain-size classes.** Single d50 class, as in DL Breach's default. Graded transport is a
   later option.
3. **Sediment from collapsed banks.** Bank failure volume (Part 3) is added to the load or deposited at
   the toe; it is accounted for in Part 3 so the sediment balance closes.

---

## 2.6 Verification this part must pass (Phase 3)

| test | expected |
|---|---|
| (2.1) at τ_b ≤ τ_c | ε = 0 exactly |
| (2.1) units | k_d 1 cm³/(N·s), τ_b − τ_c = 1 Pa → ε = 1e-6 m/s |
| (2.3), (2.4) | hand values for three grain sizes (sand, gravel, cobble) match to 1e-9 |
| MPM, van Rijn options | match the 2-D engine's implementations for the same τ′ |
| (2.5) | 1 at β = 0, 0 at β = φ, monotonic between |
| (2.7) | L_r/L_s → ∞ gives C_t*; → 0 gives C_t,in; matches numerical integration of (2.6) |
| sediment balance | eroded bulk volume × (1 − p) = solids carried out, < 1e-9 relative |
| class guard | a detachment law requested for a non-cohesive case raises an error |

---

## 2.7 Decisions (Aakash, 2026-11-20)

1. **Default non-cohesive law: DL Breach combination** — Wu (2000) bed load + Zhang (1961) suspended
   load. Wu (2000) bed + suspended is kept as option `wu2000`.
2. **Chen cap: left out** (no published source for the 2-D values).
3. **Adaptation length: λ = 6 field, 3 lab** (Wu 2013/2016).
4. **Steep-slope critical shear: Chiew & Parker (2.5) for now**; compare with DL Breach's Eqs. 4.8–4.9
   when the original is available.
5. **Grain shear: law-specific, as published.** Supersedes the Strickler-for-all wording of Part 1
   decision 3.

Still open (source check, before coding Part 2): exact Zhang (1961) suspended-load formula and
coefficients as implemented in DL Breach; DL Breach steep-slope Eqs. 4.8–4.9.

## 2.8 Flags for Phase 4 (case database)

- **GooseCreek and LaurelRun k_d are DL Breach-calibrated values** (`kd_status`: "assumed (DLBreach
  calibrated)"). Using them and then comparing our model to DL Breach on those two dams is not an
  independent comparison. Options: find independent k_d estimates, or report those two dams separately
  in the benchmark.
- Castlewood (d50 = 100 mm) and Yigong have non-zero `cohesion_kPa` but are non-cohesive for erosion;
  cohesion is used only in bank stability (Part 3). Confirm this is intended.

---

## References

- Chiew, Y. M., and Parker, G. (1994). Incipient sediment motion on non-horizontal slopes.
  *J. Hydraul. Res.*, 32(5), 649–660.
- Hanson, G. J., and Cook, K. R. (2004). Apparatus, test procedures, and analytical methods to measure
  soil erodibility in situ. *Appl. Eng. Agric.*, 20(4), 455–462.
- Meyer-Peter, E., and Müller, R. (1948). Formulas for bed-load transport. *Proc. 2nd IAHR Congress*,
  Stockholm, 39–64.
- Partheniades, E. (1965). Erosion and deposition of cohesive soils. *J. Hydraul. Div.*, 91(1), 105–139.
- Soulsby, R. L. (1997). *Dynamics of Marine Sands*. Thomas Telford.
- van Rijn, L. C. (1984). Sediment transport, part I: bed load transport. *J. Hydraul. Eng.*, 110(10),
  1431–1456.
- Wu, W., Wang, S. S. Y., and Jia, Y. (2000). Nonuniform sediment transport in alluvial rivers.
  *J. Hydraul. Res.*, 38(6), 427–434.
- Wu, W. (2013). Simplified physically based model of earthen embankment breaching. *J. Hydraul. Eng.*,
  139(8), 837–851.
- Wu, W. (2016). *Introduction to DLBreach*, version 2016.4, technical report, Clarkson University.
- Zhang, R. J. (1961). *River Dynamics*. Industry Press, Beijing (in Chinese).
