# Dam Breach Studio

A process-based model of how earthen and moraine dams breach, from the trigger (piping, overtopping, or an ice/rock avalanche into the lake) to the outflow hydrograph.

Most glacial-lake (GLOF) hazard studies prescribe the breach: a final width, depth and formation time taken from regressions built on engineered dams. Dam Breach Studio computes breach growth instead, from reservoir continuity, breach hydraulics, sediment erosion and slope stability. Every coefficient is traced to a primary source.

> **Status (November 2026):** research code under active development. TypeScript verification suite: **67 / 67 passing**, including 25 impulse-wave checks against the VAW reference workbook. Python 2-D engine: **4 / 4 test suites passing** (conservation, restart, reservoir positivity and feature checks). Calibration follows a pre-registered protocol, and historical validation is reported with its known problems (see [Validation](#validation)).

**Technical report:** a full description of the equations, numerics, verification and validation is available on request. *(Replace with a link to the published PDF.)*

---

## What it does

| Process | Implementation | Source |
|---|---|---|
| Reservoir storage | Power-law stage–storage, `dV/dt = Qin − Qout` | — |
| Breach outflow | Broad-crested weir (open breach), orifice (pipe) | Fread (1988) lineage |
| Cohesive erosion | Excess shear `ε = kd (τ − τc)^n`, kd from erosion index I, Hanson JET, or direct input | Wan & Fell (2004); Hanson & Simon (2001); Chen & Anderson (1986) |
| Granular erosion | Meyer-Peter–Müller bed load with Smart gradation factor, Exner bed update, non-equilibrium adaptation | MPM (1948); Smart (1984) |
| Piping | Pipe enlargement, gradual roof collapse into an open breach | DLBreach / BREACH style |
| Headcut (overtopping) | Hydrostatic face-shear law or energy law `dX/dt = C (qH)^(1/3)` | Temple & Hanson (WinDAM/SITES) |
| Moraine banks | Discrete bank mass-wasting (1-D); Culmann factor-of-safety collapse (2-D) | Westoby et al. (2014) |
| Impulse waves | VAW 2-D and 3-D procedures (leading crest, trough, second crest) | Heller et al. (2009), VAW workbook |
| Avalanche into lake | One-time Archimedes displacement, kept separate from the transient wave so no water is counted twice | — |
| Comparison | Von Thun & Gillette, Froehlich, MacDonald–Langridge-Monopolis regressions printed alongside each run | — |

## Two engines

**1-D engine: TypeScript, runs in the browser** (`src/lib/breach/engine.ts`, ~1,300 lines). The lake is treated as one storage and the breach as an evolving trapezoid. Time steps are adaptive and refine automatically during roof collapse and rapid discharge change. This engine powers the web dashboard.

**2-D engine: Python / NumPy** (`python/breach_engine_2d_v3_2.py`, ~2,000 lines). Finite-volume shallow-water equations on a dam "prism", using an HLL Riemann solver, Audusse hydrostatic reconstruction (well-balanced) and optional MUSCL/minmod second order. The hydraulics are coupled to multi-law sediment transport (Wu, MPM, van Rijn, Partheniades, Hanson), Exner bed updating, lateral erosion, headcut migration and Culmann bank collapse. Breach location and shape come out of the solution instead of being set as inputs. Optional Wu, Wang & Jia (2000) suspended load uses Soulsby settling velocity. Every run reports water, reservoir and solids mass-balance errors, a breakdown of eroded volume by source, and limiter activity. Restart checkpoints are written atomically. Changes are logged in [`python/V3_2_CHANGELOG.md`](python/V3_2_CHANGELOG.md).

## Quick start

Requires Node.js 20+ (22 recommended).

```bash
git clone https://github.com/aakashmandal450-pixel/Dam-Breach-Studio.git
cd Dam-Breach-Studio
npm install
npm run dev            # dashboard at http://localhost:8080
```

Run the checks:

```bash
npm run test:verify                                            # verification suite
npm run validate:case -- validation/cases/teton-1976.json      # historical case
npm run validate:case -- validation/cases/dig-tsho-1985-wave.json
```

2-D engine (Python 3.10+, NumPy):

```bash
cd python
python breach_engine_2d_v3_2.py                 # small synthetic-dam demo
python tests/v3_engine_regression.py            # conservation, restart, wave, headcut, formulas
python tests/v3_2_feature_tests.py              # 16 feature checks
python tests/v3_2_1_reservoir_tests.py          # 6 reservoir positivity checks
python tests/v3_2_2_step0_tests.py              # 18 step-0 checks
```

On Windows, `python/run_v3_tests.ps1` runs all four suites and writes a log.

## Verification

Verification asks whether the code computes what the reference tools compute. Tests sit next to the code as `*.verification.test.ts` and run with `npm run test:verify`.

| Module | Checked against | Result |
|---|---|---|
| `impulse/gen2d.ts` | VAW workbook, 2-D sheet (19 quantities) | 19 / 19 |
| `impulse/gen3d.ts` | VAW workbook, 3-D sheet at γ = 20° | 6 / 6 |
| Erosion closures and engine integration | Hand calculations, an independent re-implementation, closure wiring | all pass |
| Wave forcing and headcut laws | Hand values, scaling laws, guards, regression safety | all pass |
| **Total** (`npm run test:verify`) | | **67 / 67** |
| Python 2-D engine | Water/solids conservation, restart equivalence, lake at rest, wave-boundary mass accounting, transport formulas | 4 / 4 suites |

The VAW fixtures are not hand-typed. `validation/tools/extract_vaw_fixture.py` writes inputs into the reference workbook, recalculates it headlessly in LibreOffice and reads back the sheet's own results. Two coefficient errors in the earlier impulse-wave code were caught this way: an undocumented porosity factor in slide mass, and the wrong far-field decay exponent. Details are in [`validation/README.md`](validation/README.md).

## Validation

Validation asks whether the model reproduces real events. Every case file separates **sourced** inputs, each with its citation, from **placeholder** inputs, which are listed explicitly.

**1-D engine, historical cases** (`npm run validate:case`):

| Case | Mode | Observed Qpeak | Simulated | Error | Notes |
|---|---|---|---|---|---|
| Teton Dam, Idaho, 1976 | Piping | 65,100 m³/s | 55,603 m³/s | −14.6% | Time to peak is +192% too slow; traced to 17 placeholder erodibility and pipe inputs |
| Dig Tsho, Nepal, 1985 (wave-forced) | Wave-triggered moraine overtopping | 1,600 m³/s | 2,674 m³/s | +67% | **Not counted as validation.** The peak occurs during the wave pulse (within the first minute), not from breach enlargement |

**2-D engine, Dig Tsho reconstruction.** The moraine is rebuilt with the Westoby et al. (2015) lake curve, and an erodibility and roughness sensitivity sweep was registered before running. Across that sweep, peak outflow ranges from about 1,500 to 4,500 m³/s, against published estimates of 1,375–2,000 m³/s. This is reported as sensitivity, not calibration. Every run is indexed in [`RUNS.md`](RUNS.md), and the comparison with the published HR BREACH study is in [`validation/DIGTSHO_WESTOBY_2015_CHECK.md`](validation/DIGTSHO_WESTOBY_2015_CHECK.md).

**Calibration protocol.** Calibration and validation cases (USDA-ARS and Reclamation jet-test embankments, DLBreach cases, IMPACT field tests, Queen Bess) are split by a rule written down before any case data were obtained ([`validation/calibration/SPLIT.md`](validation/calibration/SPLIT.md)). Three global factors are fitted with leave-one-out stability checks ([`CALIBRATION_PROTOCOL.md`](validation/calibration/CALIBRATION_PROTOCOL.md)). Dig Tsho is a reconstruction only and is never used to calibrate.

## Known limitations

- Spatially uniform material: no layered moraine, ice core or melt.
- Hydrostatic shallow-water equations only; no non-hydrostatic correction.
- Impulse-wave travel across the lake is a reduced travel-time and shoaling correction, not a full lake solver.
- The 2-D VAW wave formulation is outside its validated range for narrow-lake geometry such as Dig Tsho (B = 11.1 vs. 0.74–3.33); the 3-D formulation is used there.
- Bishop and Spencer bank methods are not implemented. Requesting them raises an error instead of silently falling back.
- Breach formation only. Export the hydrograph for downstream routing in HEC-RAS or similar.

Open defects and negative findings are listed in the technical report.

## Repository layout

```text
src/lib/breach/      1-D engine, input types, theory text, verification tests
src/lib/impulse/     VAW 2-D / 3-D impulse wave, run-up, velocity
src/lib/lake/        lake volume relations
src/lib/moraine/     moraine stability and ice helpers
src/components/      dashboard UI (React)
python/              2-D engine, tests, calibration runner
runs/                2-D run records (summary.json per run; index in RUNS.md)
validation/          VAW fixtures and extractor, historical cases, calibration register and split
```

Stack: TypeScript, React, TanStack Start, Vite, Recharts; Python, NumPy.

## Roadmap

- [ ] Fix open defects: piping τ–Q consistency, overtopping invert initialisation, deepening cap
- [ ] Grain-shear (skin friction) option so roughness affects erosion with the right sign
- [ ] Run calibration `cal-1` with leave-one-out; freeze and run the Dig Tsho ensemble
- [ ] DEM-driven lake bathymetry, stage–storage curve and dam cross-sections
- [ ] Coupled downstream routing along a DEM-derived flow path
- [ ] Monte Carlo uncertainty on erosion index I and critical shear τc
- [ ] More cases: Lawn Lake (1982), Laguna 513 (2010), Laguna Safuna Alta (2002)

## Author

Aakash Mandal, civil engineer (Pulchowk Campus, IOE, Tribhuvan University), Kathmandu, Nepal.
Related publication: first-author GLOF hydrodynamic modelling study, *Discover Civil Engineering* (Springer Nature, 2025), [doi:10.1007/s44290-025-00176-1](https://doi.org/10.1007/s44290-025-00176-1).

## Disclaimer

Research and teaching code under the MIT License (see `LICENSE`), provided without warranty. Results depend strongly on erodibility inputs. This is not a substitute for a site-specific dam-safety study.
