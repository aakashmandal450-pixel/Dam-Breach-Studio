# Dam Breach Studio

**Mechanistic earthen-dam breach formation dashboard** — not a regression-only peak-flow calculator.

Dam Breach Studio couples reservoir continuity, orifice/weir hydraulics, and excess-shear erosion (Wan & Fell erosion-rate index) so you can watch a breach grow in time, inspect a labeled cross-section, and export a hydrograph. The design is in the same *family* of simplified physical models as NWS BREACH, DLBreach, and WinDAM — transparent equations, not a black box.

> **Scope today:** breach *formation* (geometry + outflow hydrograph). Downstream flood routing (FLDWAVE / HEC-RAS style) is out of scope for this module.

---

## Features

| Area | What you get |
|------|----------------|
| **Failure modes** | Overtopping and piping → roof collapse → open channel |
| **Hydraulics** | Broad-crested trapezoidal weir; orifice flow for piping |
| **Erosion** | \(C_e = 10^{-I}\); volume rate from excess shear |
| **Reservoir** | Falling head via power-function stage–storage |
| **UI** | Parameter forms with hints, schematic, playback, charts |
| **Theory** | Equations, parameter catalogue, typical \(I\) ranges, limitations |
| **Share** | Export / import project JSON; export hydrograph CSV |
| **Desktop** | Installable from Chrome/Edge as a site app (PWA-style) |

---

## Requirements

- **Node.js** 20+ (22 recommended)
- **npm** 10+
- Modern browser (Chrome or Edge recommended for “Install app”)

---

## Quick start

```bash
git clone https://github.com/aakashmandal450-pixel/Dam-Breach-Studio.git
cd Dam-Breach-Studio
npm install
npm run dev
```

Then open the URL printed in the terminal (by default the dev server binds to port **8080**).

### Other scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Local development server |
| `npm run build` | Production build |
| `npm run typecheck` | TypeScript check |
| `npm run preview` | Serve a production build locally |

---

## How to use the dashboard

1. Open **Simulate**.
2. Choose a **preset** (moderately erodible overtopping, piping, resistant clay, rapid silt) or edit inputs.
3. Set **failure mode**: Overtopping or Piping.
4. Pay special attention to **erosion-rate index \(I\)** and **\(\tau_c\)** — they dominate growth rate.
5. Click **Run formation**.
6. Use the **playback slider** on the cross-section; inspect **Peak Q**, times, final geometry, and charts.
7. **Export project** (JSON of all inputs) or **Export hydrograph CSV** for routing tools.

**Theory** — full equation list, symbol table, and limitations.  
**Install & share** — how colleagues can install the app and exchange project files.

---

## Engine overview (mechanistic core)

Implementation lives in `src/lib/breach/engine.ts`.

### Reservoir continuity

\[
\frac{dV}{dt} = Q_{\mathrm{in}} - Q_{\mathrm{out}}
\]

Storage is a power function calibrated at the initial pool:

\[
V(y) = V_0 \left(\frac{y}{y_0}\right)^m
\]

### Open breach (weir)

\[
Q = C_w \,(W_b + Z_b h)\, h^{3/2}
\]

Default \(C_w = 1.7\) (metric broad-crested style). Head \(h\) is water surface minus current invert.

### Piping (orifice)

\[
Q = C_d \,\pi R^2 \sqrt{2 g H}
\]

Used until the pipe is large enough relative to remaining cover; then the model switches to an open trapezoidal breach (roof collapse).

### Erosion rate (Wan & Fell)

\[
C_e = 10^{-I}, \qquad
\varepsilon = \frac{C_e}{\rho_d}\,\max(\tau - \tau_c,\, 0)
\]

- Open channel shear uses a Manning-derived bed stress.
- Pipe wall shear uses a Bonelli-type driving-pressure form involving pipe radius, head, and core length \(L\).

Deepening and widening advance with \(\varepsilon\); residual side slope is influenced by friction angle \(\phi\).

### What this is *not*

- Not Froehlich / Xu–Zhang / BFF **regression-only** peak discharge.
- Not a full zoned-dam FEM or 3-D CFD model.
- Not a downstream inundation mapper (export the hydrograph into HEC-RAS, FLDWAVE-class tools, etc.).

See the in-app **Theory** page for the full limitation list.

---

## Typical erosion-rate index \(I\)

| \(I\) | Soils (indicative) | Relative rate |
|------|---------------------|---------------|
| 0–2 | Dispersive clays, fine silts, weak SM | Extremely rapid |
| 2–3 | Many SM, SC, ML, low-plasticity CL | Rapid (hours) |
| 3–4 | CL, CH, MH of moderate plasticity | Moderate |
| 4–5 | Higher-plasticity, well-compacted clays | Slow |
| 5–6+ | Extremely resistant / cemented | Very slow |

Prefer a **Hole Erosion Test** (or equivalent) when available. Changing \(I\) by 1 changes \(C_e\) by a factor of ten.

---

## Project layout (main pieces)

```text
src/
  lib/breach/
    engine.ts      # time-stepping formation engine
    types.ts       # inputs / results
    examples.ts    # preset cases
    docs.ts        # theory content used by the UI
  routes/
    index.tsx      # Simulate workspace
    theory.tsx     # Equations & parameters
    install.tsx    # Install & share guidance
  components/      # schematic, forms, charts, shell
  store/studio.ts  # client state + localStorage
public/            # favicon, icons
```

Stack: **React**, **TanStack Start/Router**, **Tailwind CSS**, **Recharts**, **Zustand**, **Vite**.

---

## Sharing and desktop install

- **Share the repo or deployed URL** so others can run the same engine.
- **Export project** → JSON of every input; colleagues **Import** it.
- **Export hydrograph CSV** → `t`, `Q`, stages, geometry columns for external routing.
- **Install on a PC:** open in Chrome or Edge → browser install control (“Install app” / Apps → Install this site). No separate `.exe` is required for day-to-day use.

---

## References (engine lineage)

Primary concepts implemented or cited in the theory layer:

1. **Wan, C. F. & Fell, R. (2004).** Investigation of rate of erosion of soils in embankment dams. *Journal of Geotechnical and Geoenvironmental Engineering*, ASCE. (Erosion rate index \(I\), coefficient of soil erosion.)
2. **Fell, R., Wan, C. F., Cyganiewicz, J., & Foster, M.** Unified method / internal erosion guidance used widely in dam safety practice (progression and erodibility framing).
3. **Fread, D. L. (1988).** *BREACH: An erosion model for earthen dam failures.* National Weather Service. (Process-based breach formation: weir/orifice + sediment transport + geometry evolution.)
4. **Wu, W.** DLBreach — Dam and levee breach model (physically based formation, overtopping and piping).
5. **USDA-ARS / WinDAM** family — headcut and cohesive erosion practice for embankments (context for future headcut upgrades).
6. **Bonelli, S. (ed.)** and related pipe-erosion / time-to-failure formulations (driving pressure and characteristic times).

This application is an **engineering screening and teaching tool**. Always document assumptions, prefer site-specific erodibility data, and use established dam-safety review processes for decisions that affect public safety.

---

## Roadmap (planned)

- [x] Mechanistic formation engine + dashboard  
- [x] Theory page and parameter documentation  
- [x] Project JSON / hydrograph CSV exchange  
- [ ] README and public repo hygiene  
- [ ] Headcut module for cohesive overtopping  
- [ ] Sensitivity / Monte Carlo on \(I\) and \(\tau_c\)  
- [ ] Published validation cases  
- [ ] Optional native desktop shell (Electron/Tauri) if needed  

---

## License and disclaimer

Unless a `LICENSE` file states otherwise, treat the code as provided for research and educational use. **No warranty.** Results depend strongly on soil parameters; they are not a substitute for a site-specific study by a qualified dam safety professional.

---

## Repository

**https://github.com/aakashmandal450-pixel/Dam-Breach-Studio**
