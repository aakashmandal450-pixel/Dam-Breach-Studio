# Dam Breach Studio

A process-based model of how earthen and moraine dams breach, from the trigger (piping, overtopping, or an ice/rock avalanche into the lake) to the outflow hydrograph.

Most glacial-lake (GLOF) hazard studies prescribe the breach: a final width, depth and formation time taken from regressions built on engineered dams. Dam Breach Studio computes breach growth instead, from reservoir continuity, breach hydraulics, sediment erosion and slope stability. Every coefficient is traced to a primary source.

> **Status (November 2026):** research code under active development. Verification suite: **57 / 60 passing**. All 25 impulse-wave checks match the VAW reference workbook. Historical validation is partial and reported with its known problems (see [Validation](#validation)).

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

**1-D engine: TypeScript, runs in the browser** (`src/lib/breach/engine.ts`, ~1,200 lines). The lake is treated as one storage and the breach as an evolving trapezoid. Time steps are adaptive and refine automatically during roof collapse and rapid discharge change. This engine powers the web dashboard.

**2-D engine: Python / NumPy** (`python/breach_engine_2d_v3_2.py`, ~1,000 lines). Finite-volume shallow-water equations on a dam "prism", using an HLL Riemann solver, Audusse hydrostatic reconstruction (well-balanced) and optional MUSCL/minmod second order. The hydraulics are coupled to multi-law sediment transport (Wu, MPM, van Rijn, Partheniades, Hanson), Exner bed updating, lateral erosion, headcut migration and Culmann bank collapse. Breach location and shape come out of the solution instead of being set as inputs. Every run reports water and solids mass-balance errors, a breakdown of eroded volume by source, and limiter activity. Restart checkpoints are written atomically.

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

2-D engine demo (Python 3.10+, NumPy):

```bash
python python/breach_engine_2d_v3_2.py
```

## Verification

Verification asks whether the code computes what the reference tools compute. Tests sit next to the code as `*.verification.test.ts` and run with `npm run test:verify`.

| Module | Checked against | Result |
|---|---|---|
| `impulse/gen2d.ts` | VAW workbook, 2-D sheet (19 quantities) | 19 / 19 |
| `impulse/gen3d.ts` | VAW workbook, 3-D sheet at γ = 20° | 6 / 6 |
| Erosion closures | Hand calculations and an independent re-implementation | 10 / 10 |
| Wave pulse, headcut laws | Hand values, scaling laws, guards | 17 / 17 |
| Engine integration | Closure wiring and regression safety | 5 / 8 (3 known failures, open) |

The VAW fixtures are not hand-typed. `validation/tools/extract_vaw_fixture.py` writes inputs into the reference workbook, recalculates it headlessly in LibreOffice and reads back the sheet's own results. Two coefficient errors in the earlier impulse-wave code were caught this way: an undocumented porosity factor in slide mass, and the wrong far-field decay exponent. Details are in [`validation/README.md`](validation/README.md).

## Validation

Validation asks whether the model reproduces real events. Every case file separates **sourced** inputs, each with its citation, from **placeholder** inputs, which are listed explicitly.

| Case | Mode | Observed Qpeak | Simulated | Error | Notes |
|---|---|---|---|---|---|
| Teton Dam, Idaho, 1976 | Piping | 65,100 m³/s | 60,186 m³/s | −7.5% | Time to peak is +252% too slow; traced to 17 placeholder erodibility and pipe inputs |
| Dig Tsho, Nepal, 1985 (wave-forced) | Wave-triggered moraine overtopping | 1,600 m³/s | 1,626 m³/s | +1.6% | **Not counted as validation.** The peak occurs during the wave pulse (t ≈ 10 s), not from breach enlargement |
| Dig Tsho, 1985 (no wave) | Overtopping | 1,600 m³/s | 0 | — | No breach without the wave trigger, as expected |

Current work: rebuild Dig Tsho from published moraine survey geometry and report the peak as a range over plausible erodibility. See [`validation/cases/README.md`](validation/cases/README.md).

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
python/              2-D engine
validation/          fixtures, extractor, historical case files and runner
```

Stack: TypeScript, React, TanStack Start, Vite, Recharts; Python, NumPy.

## Roadmap

- [ ] Fix open defects: piping τ–Q consistency, overtopping invert initialisation, deepening cap
- [ ] Dig Tsho rebuilt from published geometry, reported as a range
- [ ] DEM-driven lake bathymetry, stage–storage curve and dam cross-sections
- [ ] Coupled downstream routing along a DEM-derived flow path
- [ ] Monte Carlo uncertainty on erosion index I and critical shear τc
- [ ] More cases: Lawn Lake (1982), Laguna 513 (2010), Laguna Safuna Alta (2002)

## Author

Aakash Mandal, civil engineer (Pulchowk Campus, IOE, Tribhuvan University), Kathmandu, Nepal.
Related publication: first-author GLOF hydrodynamic modelling study, *Discover Civil Engineering* (Springer Nature, 2025), [doi:10.1007/s44290-025-00176-1](https://doi.org/10.1007/s44290-025-00176-1).

## Disclaimer

Research and teaching code, provided without warranty. Results depend strongly on erodibility inputs. This is not a substitute for a site-specific dam-safety study.
