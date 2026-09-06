export interface ParamDoc {
  symbol: string;
  name: string;
  unit: string;
  range: string;
  meaning: string;
  equation: string;
}

export const PARAM_DOCS: ParamDoc[] = [
  {
    symbol: "Hb",
    name: "Dam height",
    unit: "m",
    range: "project",
    meaning: "Crest elevation minus foundation / breach-base elevation.",
    equation: "Hb = Crest − Base",
  },
  {
    symbol: "C",
    name: "Crest width",
    unit: "m",
    range: "2–15 typical earth; moraine often irregular",
    meaning: "Horizontal width of the dam crest. Headcut must migrate this distance before full deepening is allowed.",
    equation: "xh advances 0 → C",
  },
  {
    symbol: "Z1, Z2",
    name: "Dam face slopes",
    unit: "H:1V",
    range: "engineered 2–3.5; moraine often 1.5–3+",
    meaning: "Upstream (Z1) and downstream (Z2) outer embankment slopes (horizontal run per 1 vertical).",
    equation: "Geometry + residual Zb floor",
  },
  {
    symbol: "Zc",
    name: "Core side slope",
    unit: "H:1V",
    range: "0.3–1 typical",
    meaning: "Batter of the impervious core faces in a zoned dam (not the outer shell). Together with core top width and height it sets the core footprint.",
    equation: "core base ≈ top + 2 Zc Hc",
  },
  {
    symbol: "Zb",
    name: "Breach channel side slope",
    unit: "H:1V",
    range: "0.25–1 (see Theory)",
    meaning:
      "NOT the dam outer slope. It is the side slope of the eroded breach CHANNEL after the dam has opened — the trapezoid cut through the embankment. Cohesionless fills stand flatter (higher Zb); resistant clays steeper (lower Zb). Floored by friction angle: Zb ≥ cot(φ).",
    equation: "Wtop = Wb + 2 Zb h",
  },
  {
    symbol: "L",
    name: "Pipe / seepage path length",
    unit: "m",
    range: "≈ average core thickness",
    meaning: "Length of the concentrated leak through the core used in pipe-wall shear.",
    equation: "τ = ρ g R H / (2 L)",
  },
  {
    symbol: "V(y), m",
    name: "Reservoir stage-storage",
    unit: "m³",
    range: "project; m ≈ 2–3",
    meaning: "Storage as a power of depth, calibrated at the initial pool.",
    equation: "V(y) = V0 (y / y0)^m",
  },
  {
    symbol: "Qin(t)",
    name: "Inflow hydrograph",
    unit: "m³/s",
    range: "≥ 0",
    meaning: "Constant inflow or discrete series from the Discharge tab (cascade, wave pulse, measured flood).",
    equation: "dV/dt = Qin(t) − Q",
  },
  {
    symbol: "I",
    name: "Erosion rate index",
    unit: "—",
    range: "0–6 (Wan & Fell)",
    meaning: "From Hole Erosion Test when possible. Dominates growth rate. Moraine / ice-cored: often low I (very erodible) once thawed.",
    equation: "Ce = 10^(−I)",
  },
  {
    symbol: "Ce",
    name: "Coefficient of soil erosion",
    unit: "s/m",
    range: "10⁻⁶ – 10⁻¹",
    meaning: "Converts excess shear into a volume erosion rate.",
    equation: "ε = (Ce / ρd) max(τ − τc, 0)^nε",
  },
  {
    symbol: "nε",
    name: "Erosion exponent",
    unit: "—",
    range: "0.8 – 1.6 (default 1)",
    meaning:
      "Material-dependent exponent on excess shear. n=1 (default, unchanged behaviour) fits cohesive/fine soils. n≈1.3 fits cohesionless sand/gravel (Chen & Anderson 1986). n≈1.5 matches Meyer-Peter–Müller-style transport-capacity scaling (NWS BREACH lineage). Same formula family as ε — not a separate erosion law. Set per zone: core/homogeneous (erosionExponent) and zoned shell (shellErosionExponent).",
    equation: "ε = kd (τ − τc)^nε",
  },
  {
    symbol: "τc",
    name: "Critical shear stress",
    unit: "Pa",
    range: "0–20 erodible; higher for resistant clay",
    meaning: "No erosion below this shear. Prefer HET/JET. Moraine silts: often few Pa to ~20 Pa in weak cases.",
    equation: "ε = 0 if τ ≤ τc",
  },
  {
    symbol: "n",
    name: "Manning roughness",
    unit: "—",
    range: "0.02–0.05 (see typical table)",
    meaning: "Roughness of the breach channel for Manning bed shear.",
    equation: "τ = ρ g n² U² / Rh^{1/3}",
  },
  {
    symbol: "xh, fh",
    name: "Headcut position & factor",
    unit: "m, —",
    range: "xh: 0–C; fh: 3–15",
    meaning: "See Headcut module in Theory. Discrete scarp migrates upstream through the crest before full deepening.",
    equation: "dxh/dt = fh · ε(τ_face)",
  },
  {
    symbol: "Q",
    name: "Breach discharge",
    unit: "m³/s",
    range: "computed",
    meaning: "Outflow through the current opening plus spillway.",
    equation: "Weir: Cw Wavg h^{1.5}; Orifice: Cd π R² √(2gH)",
  },
  {
    symbol: "Wb, R",
    name: "Breach base width / pipe radius",
    unit: "m",
    range: "grows",
    meaning: "Open-breach bottom width after collapse, or pipe radius before collapse.",
    equation: "dWb/dt = 2 ε fs;  dR/dt = ε",
  },
];

export const EQUATIONS = [
  {
    title: "Reservoir continuity",
    latex: "dV/dt = Qin(t) − Q",
    note: "Qin may be constant or a discrete hydrograph (Discharge tab). Water level follows the power-function stage-storage curve with fully coupled falling head.",
  },
  {
    title: "Open-breach weir",
    latex: "Q = Cw (Wb + Zb h) h^{3/2}",
    note: "Averaged-width simplification of a broad-crested trapezoidal weir (not the rigorous compound trapezoidal-section formula). Default Cw = 1.7 (metric). Head h = WL − invert. Zb is the BREACH channel side slope, not the dam face slope.",
  },
  {
    title: "Piping orifice",
    latex: "Q = Cd π R² √(2 g H)",
    note: "Used until roof collapse (2R ≥ κ · cover), then the model switches to the open weir.",
  },
  {
    title: "Erosion rate (excess-shear, inspired by Wan & Fell)",
    latex: "ε = (10^{−I} / ρd) max(τ − τc, 0)^{nε}",
    note: "Screening-level excess-shear erodibility relationship in the spirit of Wan & Fell's erosion-index framework — kd = 10^{−I}/ρd does not dimensionally reduce to their literal published erosion-rate coefficient, so treat this as inspired-by rather than a direct citation of the Wan & Fell (2004) equation. A change of 1 in I changes the rate by a factor of ten. Zoned dams: core I for piping; shell I for open-breach / overtopping erosion. Exponent nε defaults to 1 (unchanged, cohesive/fine soils); nε≈1.3 (Chen & Anderson 1986, cohesionless sand/gravel) or nε≈1.5 (Meyer-Peter–Müller-style transport capacity) can be set per zone for coarser material — same formula, sourced exponent range, not a separate law.",
  },
  {
    title: "Open-channel (Manning) shear",
    latex: "τ = ρ g n² U² / Rh^{1/3}",
    note: "Bed shear on the open breach. U = Q/A, Rh = A/P. Typical n: see table below.",
  },
  {
    title: "Pipe-wall shear",
    latex: "τ = ρ g R H / (2 L)",
    note: "Bonelli-type form along the seepage path L (core length).",
  },
  {
    title: "Headcut face shear & advance (hydrostatic law, default)",
    latex: "τ_face ≈ ρ g h ,   dxh/dt = fh · ε(τ_face)",
    note: "Temple / WinDAM-style discrete headcut on overtopping (headcutLaw = 'hydrostatic', default). Deepening is limited by the deepening gate until xh reaches crest width C; then full bed-shear erosion applies.",
  },
  {
    title: "Headcut migration (WinDAM / USDA-SITES energy law)",
    latex: "dX/dt = C · (q · H)^{1/3}",
    note: "Optional energy-dissipation migration law (headcutLaw = 'energy'), the WinDAM / USDA-SITES lineage. q = unit overfall discharge = Cw·h_eff^{3/2} [m²/s], H = drop height = (crest − invert) + approach head over the crest, C = headcutEnergyCoeff (material headcut erodibility, tie to the same anchor as kd; screening 0.5–2). Replaces the hydrostatic dxh/dt only; the deepening gate, breakthrough, and piping are unchanged. Selected per run; default stays hydrostatic so legacy results are byte-identical.",
  },
  {
    title: "Wave-overtopping transient forcing (GLOF trigger)",
    latex: "h_eff(t) = h + d₀ sin(π (t−t_k)/tO)  over N pulses;   Q_reservoir uses h only",
    note: "Opt-in (waveForcingEnabled, overtopping only). A displacement/impulse wave from the Impulse module's run-up rides over the crest as a half-sine pulse train — peak depth d₀ (waveOvertopDepth) for duration tO (waveOvertopDuration), repeated waveOvertopCount times at waveOvertopPeriod spacing (0 → = tO). The wave head augments the EROSION hydraulics only (effective depth h_eff drives shear, the headcut face, and overfall q); the reservoir mass balance keeps the REAL standing head h, because a surface surge is not stored volume. This lets a lake sitting at/near its rim (little or no freeboard) initiate incision the standing head alone cannot — the classic moraine-GLOF trigger. Once the invert cuts below still-water level the lake self-drains; if incision never reaches lake level the breach arrests. Off by default → engine behaviour is unchanged.",
  },
  {
    title: "Roof collapse",
    latex: "2 R ≥ κ · (crest − invert)",
    note: "Pipe becomes an open trapezoidal breach when diameter is large relative to remaining cover.",
  },
  {
    title: "Residual breach side slope",
    latex: "Zb ≥ cot(φ)",
    note: "The eroded channel cannot stand steeper than the material friction angle. This floors Zb; it does not set the outer dam slopes Z1/Z2.",
  },
  {
    title: "Core geometry (zoned)",
    latex: "cb ≈ ct + 2 Zc Hc",
    note: "Trapezoidal core: top width ct, height Hc, side slope Zc (H:1V). Drawn in a distinct colour on the cross-section.",
  },
  {
    title: "Moraine bank mass-wasting (moraine / ice-cored moraine only)",
    latex: "collapse when Σdz ≥ κb·Hb;   Wb += 2·(Σdz)·fb",
    note: "Screening proxy for the fluvial-erosion + geotechnical bank-collapse coupling documented for moraine breaches (Westoby et al. 2014, HR-BREACH — validated against Dig Tsho): smooth excess-shear widening alone under-widens moraine channels because real banks fail in discrete undercut-then-slump events, not a steady curve. Tracks exposed unsupported bank height (Σdz, from both incremental deepening and the headcut-breakthrough invert drop) and triggers a one-time Wb widening once it exceeds κb (bankCollapseHeightFraction) times dam height. fb = bankCollapseWidthFactor. Not a limit-equilibrium (Culmann) solver — a tunable screening trigger.",
  },
  {
    title: "Transport-capacity bedload (Meyer-Peter–Müller + Smart 1984)",
    latex: "θ = τ / ((s−1) ρ g D50);   Φ = Kt (D90/D30)^{0.2} (θ − θc)^{1.5}",
    note: "Alternative OPEN-BREACH erosion closure for cohesionless / granular / moraine / rockfill material — the NWS BREACH lineage (Fread 1988). θ is the Shields stress on the D50 grain (s = ρs/ρ the specific gravity), Φ the dimensionless Einstein bedload intensity. Kt = 8 is the classic Meyer-Peter–Müller coefficient (Wong & Parker 2006 recalibrate to ≈3.97; adjustable), θc ≈ 0.047 the critical Shields number, and (D90/D30)^{0.2} the Smart (1984) gradation factor for well-graded steep-channel beds. NOT for fine cohesive soils: as D50→0 the Shields stress diverges and MPM over-predicts wildly near threshold — those stay on the excess-shear law. Selected via erosionModel = 'transport_capacity'; piping and the headcut face always remain on excess-shear.",
  },
  {
    title: "Exner continuity (bedload → invert-lowering rate)",
    latex: "qs = Φ √((s−1) g D50³);   ε = qs / ((1 − p) Lreach)",
    note: "Volumetric bedload per unit width qs [m²/s] converted to a breach-invert lowering rate ε [m/s] over the erodible flow-path length Lreach = C + Hb√(1+Z2²), with bed porosity p (Exner). Clear-water reservoir inflow is assumed, so the transport capacity is fully sourced by eroding the breach. Steep-slope enhancement is carried by the boundary shear τ (Manning), NOT an explicit Smart S^{0.6} multiplier — this avoids double-counting the slope dependence that already enters through τ.",
  },
  {
    title: "Re-anchored erodibility kd (Hanson & Simon 2001, JET)",
    latex: "kd = 0.2 τc^{−0.5} [cm³/(N·s)] = 2×10^{−7} τc^{−0.5} [m³/(N·s)];   ε = kd (τ − τc)",
    note: "Optional physically-anchored excess-shear coefficient from Jet Erosion Test regression (Hanson & Simon 2001), replacing the dimensionally-lumped index kd = 10^{−I}/ρd. Selected via kdMode = 'hanson'; forces linear detachment (nε = 1). kdMode = 'direct' instead takes a site-measured JET kd entered in cm³/(N·s) (converted to SI ×10⁻⁶). Applies wherever excess-shear is active — piping, the headcut face, and the open breach when erosionModel = 'excess_shear'. Default kdMode = 'index' leaves legacy behaviour unchanged.",
  },
];

export const LIMITATIONS = [
  "Screening / teaching engine (NWS BREACH– / WinDAM-style lineage), not a substitute for site-specific numerical modelling or peer review.",
  "Zoned option uses two material sets (core for piping, shell for open/overtopping). Filters, transition zones, and full 3-D seepage are not resolved.",
  "Moraine and ice-cored modes apply literature-informed default ranges; they do not simulate ice melt, thermokarst, or time-varying strength as temperature rises.",
  "Moraine bank-collapse module is a discrete screening trigger (exposed-height threshold → one-time widening), not a limit-equilibrium slope-stability solver. Validated directionally against Dig Tsho (1985): folding the headcut-breakthrough invert drop into the same collapse event narrowed Qpeak error from -91%/-93% to -86%/-89% for the 2D/3D wave chains respectively — a real, evidenced improvement, not a full closure of the gap. Remaining error is likely still dominated by screening-level erosion-rate parameters (I, τc) and the single-event (vs. repeated-pulse) collapse structure.",
  "Erosion exponent nε defaults to 1 (unchanged Wan & Fell-style linear behaviour) for both core/homogeneous and shell zones; nε>1 (cohesionless dial, Chen & Anderson 1986 / MPM-style) is opt-in per zone, not yet calibrated against a live case.",
  "Open-breach erosion is a SELECTABLE dual closure. Default 'excess_shear' (detachment-limited ε = kd(τ−τc)^nε) is unchanged. 'transport_capacity' (Meyer-Peter–Müller + Smart 1984 gradation → Exner) is a sediment-transport-limited alternative for cohesionless / granular / moraine / rockfill only; it is deliberately NOT applied to fine cohesive soils (Shields stress diverges as D50→0), nor to piping or the headcut face, which always stay on excess-shear. Transport capacity assumes clear-water reservoir inflow and a single erodible reach length Lreach = C + Hb√(1+Z2²); it does not resolve armouring, suspended load, or downstream deposition/backfill.",
  "Erodibility kd has three provenances: 'index' (default, kd = 10^{−I}/ρd — legacy, dimensionally lumped), 'hanson' (kd = 2×10⁻⁷·τc^{−0.5} from Hanson & Simon 2001 JET regression, forces nε=1), and 'direct' (site-measured JET value in cm³/(N·s)). The JET-anchored modes are physically grounded but assume the JET regression transfers to the field material; site testing is preferred over any of the three.",
  "Headcut migration is a SELECTABLE law: 'hydrostatic' (default, dxh/dt = fh·ε(τface), τface ≈ ρgh — legacy) or 'energy' (WinDAM/USDA-SITES dX/dt = C·(q·H)^{1/3}). Neither resolves full jet-impingement plunge-pool scour; both feed the same deepening gate and breakthrough logic. The gate throttles (fraction, cap) are now exposed for calibration.",
  "Breach side slope Zb is a residual channel batter rule (with friction floor), not a limit-equilibrium slip-surface search.",
  "Erosion index I dominates results; prefer Hole Erosion Test (HET) or Jet Erosion Test (JET). D10 is optional context, not required if I and τc are known.",
  "Inflow may be constant or a user discrete series. The wave→breach hand-off is a SELECTABLE engine-level transient: an opt-in half-sine overtopping pulse train (peak d₀, duration tO, N pulses) from the Impulse run-up result, applied to the erosion hydraulics only (not reservoir volume). It is a screening surge, not full 3-D CFD of wave run-up/overtopping, and does not model wave reflection, set-up, or air entrainment.",
  "Impulse-wave amplitudes follow VAW / Heller–Hager-style closed forms inside published envelopes; outside envelopes are flagged as extrapolation.",
  "No downstream flood routing, sediment concentration, or debris-flow rheology in the formation engine.",
];

export const I_TABLE = [
  { i: "0 – 2", soil: "Dispersive clays, fine silts, loose SM; many thawing moraine fines", rate: "Extremely rapid" },
  { i: "2 – 3", soil: "SM, SC, ML, low-plasticity CL; typical non-ice moraine matrix", rate: "Rapid (hours)" },
  { i: "3 – 4", soil: "CL, CH, MH moderate plasticity; engineered well-compacted fills", rate: "Moderate" },
  { i: "4 – 5", soil: "Higher-plasticity, dense clays", rate: "Slow (days)" },
  { i: "5 – 6+", soil: "Extremely resistant / cemented", rate: "Very slow" },
];

/** Typical Manning n for breach / embankment channels */
export const MANNING_TABLE = [
  { n: "0.020 – 0.025", surface: "Smooth earth, fine material, little vegetation" },
  { n: "0.025 – 0.035", surface: "Typical engineered earthfill breach channel (default ~0.030)" },
  { n: "0.035 – 0.045", surface: "Coarse gravel, cobbles, irregular moraine debris" },
  { n: "0.045 – 0.060", surface: "Very rough, boulder-strewn, vegetated or blocked" },
];

export const HEADCUT_DOCS = {
  title: "Headcut module",
  summary:
    "On overtopping, many earth and rockfill dams do not lower the crest uniformly. A nearly vertical scarp (headcut) forms on the downstream face and migrates upstream through the crest width C. Until the headcut breaks through to the reservoir, deepening of the invert is limited — the model throttles bed erosion so the breach does not unrealistically “drill down” while the crest is still intact.",
  effects: [
    "Initiation: overtopping depth must reach the initiation head (hinit) before the discrete headcut is tracked.",
    "Advance — selectable law. Hydrostatic (default): dxh/dt = fh · ε(τ_face) with τ_face ≈ ρ g h on the scarp face. Energy (WinDAM/USDA-SITES): dX/dt = C · (q · H)^{1/3}, q = unit overfall discharge, H = drop height, C = headcutEnergyCoeff. Both migrate the scarp through crest width C.",
    "Factor fh (typically 3–15, hydrostatic law): how fast the scarp eats through C relative to the excess-shear rate. Coefficient C (typically 0.5–2, energy law): the WinDAM material headcut erodibility.",
    "Deepening gate: while the headcut is still inside the crest, invert lowering is throttled to (gate fraction × excess-shear rate), capped at (gate cap × dam height) per step. Legacy 0.25 and 0.015 — both now exposed so a wide-crest moraine breach, long suspected of being over-throttled, can be re-examined.",
    "Breakthrough: when xh reaches C, full bed-shear deepening and widening apply (open-breach stage).",
    "Clay-rich fills often show a clearer headcut; cohesionless sand/gravel may erode more smoothly — lower fh or turn the module off for a pure surface-erosion idealisation.",
  ],
  whenOff:
    "Legacy pure surface erosion: invert and width grow whenever bed shear exceeds τc, without waiting for crest breakthrough.",
};

export const WAVE_FORCING_DOC = {
  title: "Wave-overtopping forcing (GLOF wave→breach chain)",
  summary:
    "The classic moraine-dam GLOF is not triggered by rising water — the lake already sits at its rim with little or no freeboard. It is triggered by a displacement wave (an ice or rock avalanche, or a calving glacier front plunging into the lake) that surges over the crest and carves the first incision. This opt-in module takes that wave from the Impulse module's run-up result and drives it into the breach engine as a transient overtopping pulse, so a lake at its rim can actually initiate a breach the standing head alone never would.",
  effects: [
    "Enable per run (Headcut tab → Wave forcing). Applies in overtopping mode only; off by default so all legacy and non-GLOF results are unchanged.",
    "The wave is a half-sine pulse train: peak crest depth d₀ (waveOvertopDepth) over duration tO (waveOvertopDuration), repeated N times (waveOvertopCount) at spacing T (waveOvertopPeriod; 0 → uses tO). Take d₀ and tO straight from the Impulse module's run-up result (RunupResult.d0 / .tO).",
    "It augments the EROSION hydraulics only — the effective flow depth h_eff = h + wave head drives bed shear, the headcut face, and the overfall discharge q. The reservoir mass balance keeps the REAL standing head h, because a surface surge adds erosive energy, not stored volume.",
    "Emergent behaviour: the pulse initiates crest incision; once the invert cuts below still-water level the lake self-drains (runaway); if incision never reaches lake level within the wave train the breach arrests — the physically correct outcome for a wave too small to breach.",
    "The wave is the trigger, not the magnitude driver: once the crest is cut through, peak discharge is governed by the reservoir volume and the material erodibility (I / transport closure), so calibrate erodibility to the observed peak, not the wave.",
  ],
  whenOff:
    "Legacy behaviour: overtopping erosion is driven by the standing head only, so a lake exactly at its rim with no inflow never breaches (the pre-chain Dig Tsho result).",
};

export const EROSION_MODEL_DOC = {
  title: "Erosion closure — dual law (excess-shear vs transport-capacity)",
  summary:
    "The open breach can be eroded by one of two physically distinct laws. The choice matters: cohesive fills are detachment-limited (a particle-by-particle scour rate set by excess shear), while cohesionless granular / moraine / rockfill material is transport-limited (the invert lowers only as fast as the flow can carry the mobilised bedload away). Using the wrong one is a leading source of breach-hydrograph error. Default is excess-shear so existing projects are unchanged; piping and the headcut face always use excess-shear regardless of this setting.",
  models: [
    "excess_shear (default) — detachment-limited ε = kd·(τ − τc)^nε. Best for engineered cohesive fills and clay cores. kd provenance is set separately by kdMode (index / hanson / direct).",
    "transport_capacity — sediment-transport-limited Meyer-Peter–Müller bedload with the Smart (1984) gradation factor, closed by Exner continuity. Best for cohesionless sand/gravel, moraine debris, and rockfill (NWS BREACH lineage). Requires grain inputs: D50, D90/D30, ρs, θc, Kt, porosity.",
  ],
  kdModes: [
    "index (default) — kd = 10^(−I)/ρd. Legacy Wan & Fell-style erosion index; dimensionally lumped but familiar and driven by the HET index I.",
    "hanson — kd = 2×10⁻⁷·τc^(−0.5) m³/(N·s) from the Hanson & Simon (2001) JET regression. Physically anchored; forces linear detachment nε = 1.",
    "direct — enter a site-measured JET kd in cm³/(N·s) (converted to SI). Use when you have a real jet-test result for the material.",
  ],
  whyNotSmartSlope:
    "The Smart (1984) steep-channel relation includes an explicit S^0.6 slope term. This engine deliberately omits that multiplier and lets slope enter through the Manning boundary shear τ instead, so the slope dependence is represented once, not twice. This is a conscious screening-level simplification, documented so results are not mistaken for the full Smart transport formula.",
  guidance:
    "Rule of thumb: if the material is fine and cohesive (clay/silt, high I, measurable τc from HET), keep excess-shear — the Shields stress on a tiny D50 diverges and MPM will massively over-erode. If it is clearly granular and non-cohesive (gravel-cobble moraine, rockfill), transport-capacity is the more faithful physics. Structure defaults wire moraine / ice-cored moraine to transport-capacity and homogeneous / zoned to excess-shear automatically.",
};

export const BREACH_SIDE_SLOPE_DOC = {
  title: "Breach side slope Zb (not the dam slope)",
  body: `Z1 and Z2 are the outer faces of the dam as built. Zb is different: it is the side slope of the hole (breach channel) that erosion cuts through the dam.

• Shape: open breach is a trapezoid. Top width = Wb + 2 Zb h, where h is flow depth in the breach.
• Material: cohesionless rockfill / moraine often stands at Zb ≈ 0.5–1 (H:1V). Stiffer clay can hold Zb ≈ 0.25–0.5 until it collapses toward residual friction.
• Friction floor: the engine enforces Zb ≥ cot(φ) so the channel is not steeper than the soil can sustain.
• Do not set Zb equal to Z2 unless you have a reason — they answer different geometric questions.`,
};

export const MORAINE_DOC = {
  title: "Moraine and ice-cored dams",
  physics: [
    "Moraine dams are accumulations of glacial debris (poorly sorted silt, sand, gravel, boulders), often loosely consolidated and highly permeable compared with engineered clay cores.",
    "Failure is commonly triggered by overtopping from avalanche- or landslide-generated impulse waves, or by rising lake level — not by classical design floods alone.",
    "Ice-cored (or ice-rich) moraines contain buried ice or permafrost. While frozen, strength can be relatively high; thaw reduces cohesion and can cause settlement, crest lowering, piping along melt paths, and sudden loss of freeboard (Richardson & Reynolds-type mechanisms).",
    "Buried ice content can increase peak breach discharge in process-based studies (e.g. multi-peak hydrographs with surge then overflow stages); this studio does not yet melt ice in time — use lower I / τc and reduced freeboard as a screening proxy.",
  ],
  screeningValues: [
    { param: "I (thawed matrix)", value: "1.5 – 3.0", note: "Often rapid once thawed; site-specific HET preferred" },
    { param: "τc", value: "2 – 15 Pa", note: "Weak silty matrices; higher if gravel-armoured" },
    { param: "φ", value: "28 – 36°", note: "Friction angle for residual Zb floor" },
    { param: "Zb", value: "0.5 – 1.0", note: "Breach channel in cohesionless debris" },
    { param: "n (Manning)", value: "0.035 – 0.045", note: "Coarse irregular breach" },
    { param: "Z1, Z2", value: "1.5 – 3+", note: "Steep natural faces common" },
    { param: "Ice content (literature)", value: "0 – 40%+", note: "Process models show higher Qp with high ice; treat as uncertainty, not a single switch" },
  ],
  structureModes: [
    "Homogeneous — single material (engineered fill or simplified uniform embankment).",
    "Zoned — clay/silt core + shell; core I/τc for piping, shell for overtopping; core geometry (ct, cb, Hc, Zc).",
    "Moraine — non-engineered debris dam; applies screening defaults toward erodible matrix.",
    "Ice-cored moraine — same as moraine with more conservative (lower) I/τc defaults as a thawed-ice proxy; document freeboard uncertainty.",
  ],
};

export const TYPICAL_VALUES = [
  { item: "Cw (metric weir)", value: "1.4 – 1.8", note: "Default 1.7" },
  { item: "Cd (orifice)", value: "0.5 – 0.7", note: "Default 0.6" },
  { item: "κ (collapse ratio)", value: "0.4 – 0.7", note: "Default 0.55" },
  { item: "fs (side erosion factor)", value: "1 – 2", note: "Widening vs deepening" },
  { item: "fh (headcut factor)", value: "3 – 15", note: "Default ~6. Hydrostatic migration law only" },
  { item: "C (energy headcut coeff)", value: "0.5 – 2", note: "WinDAM/SITES dX/dt = C·(q·H)^{1/3}. Energy law only; higher = faster scarp migration" },
  { item: "gate fraction", value: "0.05 – 1", note: "Invert-deepening throttle while headcut is in the crest. Legacy 0.25; raise toward 1 for wide-crest moraine" },
  { item: "gate cap", value: "0.005 – 0.1 ×Hb", note: "Per-step cap on gated deepening. Legacy 0.015 × dam height" },
  { item: "d₀ (wave overtop depth)", value: "from run-up", note: "Peak crest-overtopping depth; take RunupResult.d0 from the Impulse module. Wave forcing only" },
  { item: "tO (wave overtop duration)", value: "from run-up", note: "Overtopping pulse duration; take RunupResult.tO. Wave forcing only" },
  { item: "N (wave pulse count)", value: "1 – 20", note: "Successive wave pulses (GLOF wave train). Default 1. Wave forcing only" },
  { item: "ρd", value: "1400 – 2000 kg/m³", note: "Compacted fill; moraine variable" },
  { item: "Storage exponent m", value: "2 – 3", note: "Natural basins often ~2–2.5" },
  { item: "nε (erosion exponent)", value: "0.8 – 1.6", note: "Default 1 (cohesive/fine); ~1.3 cohesionless sand/gravel; ~1.5 MPM-style transport-capacity" },
  { item: "κb (bank-collapse height fraction)", value: "0.08 – 0.20", note: "Moraine only. Default 0.12 × Hb. Lower triggers collapse sooner/smaller" },
  { item: "fb (bank-collapse width factor)", value: "1 – 3", note: "Moraine only. Default 1.5" },
  { item: "D50 (transport-capacity)", value: "0.005 – 0.20 m", note: "Median grain size. Moraine matrix ~0.02–0.04; rockfill coarser. transport_capacity only" },
  { item: "D90/D30 (gradation)", value: "3 – 20", note: "Smart (1984) factor (D90/D30)^0.2. Well-graded moraine debris ~8–12. transport_capacity only" },
  { item: "ρs (grain density)", value: "2600 – 2700 kg/m³", note: "Default 2650 (quartz). transport_capacity only" },
  { item: "θc (critical Shields)", value: "0.03 – 0.06", note: "Default 0.047 (MPM). Lower for steep slopes / fine beds. transport_capacity only" },
  { item: "Kt (MPM coefficient)", value: "4 – 8", note: "Default 8 (classic MPM); Wong & Parker 2006 ≈3.97 calibrated. transport_capacity only" },
  { item: "p (bed porosity)", value: "0.25 – 0.45", note: "Default 0.35 in the Exner conversion. transport_capacity only" },
  { item: "kd (JET, Hanson & Simon)", value: "2×10⁻⁷·τc^⁻⁰·⁵ m³/(N·s)", note: "kdMode='hanson'; or enter a measured JET kd in cm³/(N·s) with kdMode='direct'" },
];


export const ICE_THERMAL_DOC = {
  title: "Ice-core thermal screening (GLOF)",
  summary:
    "Buried ice and ice-rich moraine lose strength and can settle as the climate warms. This studio uses a degree-day screening model — not a coupled thermo-hydro-mechanical FEM.",
  equations: [
    {
      title: "Melt depth (degree-day)",
      latex: "d_melt = (DDF · PDD) / 1000   [m]",
      note: "DDF in mm/(°C·d); PDD positive degree-days. Capped by ice-core thickness.",
    },
    {
      title: "Thaw fraction",
      latex: "f_thaw = min(1, d_melt / H_ice)",
      note: "Fraction of the ice-rich zone that is treated as thawed for strength mixing.",
    },
    {
      title: "Freeboard loss",
      latex: "Δf ≈ α_s · d_melt · θ_ice",
      note: "Settlement factor α_s times melt depth times volumetric ice content — void collapse proxy.",
    },
    {
      title: "Effective erodibility",
      latex: "I_eff = I_fr + (I_th − I_fr) f_thaw",
      note: "Same linear mix for τc. Pass I_eff and τc_eff into the breach engine.",
    },
  ],
  limits: [
    "No latent-heat mesh, debris-cover conductivity, or seepage–thermal feedback.",
    "Ice content and DDF are highly uncertain without site geophysics and climate data.",
    "Process models show ice content can change peak discharge; treat linked breach Qp as a band, not a single truth.",
  ],
};

export const MORAINE_STABILITY_DOC = {
  title: "Moraine distal-face stability screening",
  summary:
    "Infinite-slope factor of safety on the downstream face with pore-pressure ratio Ru, plus geometry and freeboard risk flags used in GLOF literature.",
  equations: [
    {
      title: "Infinite-slope FoS",
      latex: "FoS = [c′/(γ H cos²β) + (1 − Ru) tan φ′] / tan β",
      note: "β from Z2 (H:1V). Characteristic depth H ≈ dam height. Screening only.",
    },
    {
      title: "Thaw knockdown (ice-cored)",
      latex: "c′ → c′(1 − 0.7 f_thaw),  φ → φ(1 − 0.15 f_thaw)",
      note: "Simple strength loss with thaw fraction from the ice-thermal block.",
    },
  ],
  classes: [
    "FoS ≥ 1.3 stable · 1.0–1.3 marginal · < 1.0 unstable (screening thresholds).",
    "Width/height < 0.15 and freeboard/height < 0.05 raise geometry/freeboard risk.",
    "Composite hazard blends FoS, geometry, freeboard, and ice/thaw — not a probabilistic GLOF rate.",
  ],
};

/** How optional modules are switched off for simple runs. */
export const MODULE_SCOPE_DOC = {
  title: "Analysis scope & optional modules",
  summary:
    "New users can omit GLOF / ice entirely. Project → Analysis scope = Simple dam breach turns the module off; the GLOF / ice tab still opens so you can re-enable it. When off, thaw and FoS results are ignored and Apply is disabled.",
  points: [
    "Simple dam breach — homogeneous or zoned earthfill, no ice-core thaw, no moraine FoS.",
    "Include GLOF / ice — degree-day thaw, freeboard loss, I_eff / τc_eff, distal-face FoS.",
    "Per-module Off switch inside the GLOF / ice tab is the same flag; both places stay in sync.",
    "Dam structure still controls material defaults (I, τc, headcut fh). Choosing Simple does not delete your ice numbers; it only stops them from affecting the run.",
  ],
};
