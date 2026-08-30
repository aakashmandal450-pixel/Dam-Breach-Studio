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
    equation: "ε = (Ce / ρd) max(τ − τc, 0)",
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
    note: "Broad-crested trapezoidal weir. Default Cw = 1.7 (metric). Head h = WL − invert. Zb is the BREACH channel side slope, not the dam face slope.",
  },
  {
    title: "Piping orifice",
    latex: "Q = Cd π R² √(2 g H)",
    note: "Used until roof collapse (2R ≥ κ · cover), then the model switches to the open weir.",
  },
  {
    title: "Erosion rate (Wan & Fell)",
    latex: "ε = (10^{−I} / ρd) max(τ − τc, 0)",
    note: "A change of 1 in I changes the rate by a factor of ten. Zoned dams: core I for piping; shell I for open-breach / overtopping erosion.",
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
    title: "Headcut face shear & advance",
    latex: "τ_face ≈ ρ g h ,   dxh/dt = fh · ε(τ_face)",
    note: "Temple / WinDAM-style discrete headcut on overtopping. Deepening is limited until xh reaches crest width C; then full bed-shear erosion applies.",
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
];

export const LIMITATIONS = [
  "Screening / teaching engine (NWS BREACH– / WinDAM-style lineage), not a substitute for site-specific numerical modelling or peer review.",
  "Zoned option uses two material sets (core for piping, shell for open/overtopping). Filters, transition zones, and full 3-D seepage are not resolved.",
  "Moraine and ice-cored modes apply literature-informed default ranges; they do not simulate ice melt, thermokarst, or time-varying strength as temperature rises.",
  "Headcut uses hydrostatic face shear scaled by fh — not full jet-impingement or USDA SITES energy dissipation.",
  "Breach side slope Zb is a residual channel batter rule (with friction floor), not a limit-equilibrium slip-surface search.",
  "Erosion index I dominates results; prefer Hole Erosion Test (HET) or Jet Erosion Test (JET). D10 is optional context, not required if I and τc are known.",
  "Inflow may be constant or a user discrete series; wave→breach hand-off uses a screening overtopping pulse, not full 3-D CFD.",
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
    "Advance: horizontal migration dxh/dt = fh · ε(τ_face) with τ_face ≈ ρ g h on the scarp face.",
    "Factor fh (typically 3–15): calibration knob for how fast the scarp eats through C relative to the excess-shear rate.",
    "Breakthrough: when xh reaches C, full bed-shear deepening and widening apply (open-breach stage).",
    "Clay-rich fills often show a clearer headcut; cohesionless sand/gravel may erode more smoothly — lower fh or turn the module off for a pure surface-erosion idealisation.",
  ],
  whenOff:
    "Legacy pure surface erosion: invert and width grow whenever bed shear exceeds τc, without waiting for crest breakthrough.",
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
  { item: "fh (headcut factor)", value: "3 – 15", note: "Default ~6" },
  { item: "ρd", value: "1400 – 2000 kg/m³", note: "Compacted fill; moraine variable" },
  { item: "Storage exponent m", value: "2 – 3", note: "Natural basins often ~2–2.5" },
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
