# ARS piping tests P1–P3: data sheet (draft, 2026-11-24)

The three tests are homogeneous embankments built at the USDA-ARS HERU outdoor laboratory in Stillwater, Oklahoma, in 2006–07. Piping was started by pulling a 40 mm steel pipe out through the downstream face. The reservoir was fed continuously, and a long-crested weir held its level.

Status labels used below:
- **M**: measured.
- **E**: estimated or model input taken from another study.
- **S**: scenario (we choose it).
- **—**: missing.

## 1. Geometry and boundary (shared by all three tests)

| Item | Value | Status | Source / note |
|---|---|---|---|
| Height H | 1.3 m (alternative 1.22 m) | M, conflict | 1.3 m: Hanson et al. 2010 and Chen et al. 2019. 4 ft: PAP-1017 |
| Crest width | 1.83 m | M | 6 ft, PAP-1017. GeoHazards 2024 uses 1.98 m (range 1.78–2.18) |
| Slopes | 3H:1V on both faces | M | PAP-1017 |
| Embankment length | — | — | Not in any source found |
| Pipe | 40 mm steel; upstream end capped while filling | M | Chen et al. 2019; PAP-1017 gives 1.5 in |
| Pipe elevation | — | — | PAP-1017 says only "lowest row of markers" on the downstream slope |
| Reservoir level | 1.1 m (P1 only) | M | Chen et al. 2019 |
| Reservoir behaviour | Held constant by a weir | S | The supply capacity is unknown, so the level may drop near the peak |

## 2. Soil, compaction and erodibility

| | P1 | P2 | P3 |
|---|---|---|---|
| USCS | SM, non-plastic | s(CL) | (CL)s |
| Sand / silt / clay (%) | 76 / 19 / 5 | 31 / 50 / 19 | 20 / 50 / 30 |
| LL / PI | NP | 25 / 9 | 36 / 24 |
| Optimum water content (%) | 12.5 | 12.2 | 14.2 |
| As-built water content (%) / dry density (g/cm³) | 11.49 / 1.696 | 12.67 / 1.746 | 15.06 / 1.776 (upper lifts) |
| **Field JET k_d (cm³/N·s) / τ_c (Pa)** | **150 / 0.0** | **2.0 / 2.5** | **1.2 / 4.6** (upper lifts) |
| Lab JET at ARS conditions, k_d | 274 – 309 | 0.19 – 0.39 | 0.05 – 0.19 |
| Lab HET at ARS conditions, k_d / τ_c | Not testable (specimens collapsed when wetted) | 0.04 – 0.22 / 231 – 357 | 0.007 – 0.02 / 203 – 346 |
| Undrained shear strength c_u | 5 kPa, tanφ 0.625 (E: GeoHazards model input) | — | — |

Sources:
- Gradation, Atterberg limits and optimum water content: DSO-08-05, Table 3.
- As-built state, field JET and lab tests: PAP-1017, Tables 4 and 6.

The classifications conflict between sources:
- **P2:** PAP-1017 Table 1 gives CL-ML (LL 21, PI 7); its Table 3 gives ML (LL 23, PI 3).
- **P3:** PAP-1017 Table 1 gives CL (LL 28, PI 13); the July 2008 resample gives LL 33, PI 19.

For P3, the lower three lifts are much more resistant (k_d 0.17, τ_c 22 Pa), and the observed failure ran through the upper lifts.

## 3. Observations

| | P1 | P2 | P3 |
|---|---|---|---|
| Time to roof collapse T_c | 0.23 h (828 s) | 17.2 h | 20.5 h |
| Peak outflow Q_p | 2.979 m³/s | — | — |
| Time to peak T_p | 1560 s | — | — |
| Maximum breach width | 6.46 m | — | — |

The T_c values come from PAP-1017, Table 1. The P1 peak values come from GeoHazards 2024, Table 2, which credits HERU for the data but does not cite a table. They should be checked against Hanson et al. 2010.

## 4. What this means for us

1. **P1** can be used with the field JET values. It has a full set of observations except the pipe elevation and the hydrograph.
2. **P2 and P3 can test only T_c for now.** That suits Part 5: a T_c of 17–20 h depends on how the pipe enlarges and on collapse (N_c from the stability table). It does not depend on routing the flow after the breach.
3. **Erodibility method matters.** For P2 and P3, the HET k_d is 10–100 times lower than the JET k_d. Using the field JET as the primary value is justified because it was measured on the embankment itself. The HET and lab JET values become the sensitivity band.
4. **The c_u of P2 and P3 is missing.** Without it, the collapse check cannot be run, so it would have to be a stated scenario. One option is an estimate from the compaction state and PI, labelled **E**.

## 5. Still to get (in order of value)

1. **Hanson, Tejral, Hunt & Temple (2010)**, "Internal erosion and impact of erosion resistance", USSD conference. This is the primary source: P1–P4 hydrographs, pipe elevation, reservoir level, possibly strength.
2. **Chen, Zhong & Shen (2019)**, Water Sci. Eng. 12(3) 169–178. Gives the full P1 condition table, including the pipe position.
3. **CEATI internal-erosion breach model review (2017, USU DigitalCommons dpao5)**. Explains how HERU measured the P1 data.
4. **Ali, Hunt & Tejral (2021)**, Trans. ASABE, doi 10.13031/trans.13701. Covers four tests; it may include the same embankments or later ones.
