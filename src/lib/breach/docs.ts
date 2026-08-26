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
    range: "2–12 typical",
    meaning: "Horizontal width of the dam crest. Headcut must migrate this distance before full deepening.",
    equation: "x_h advances 0 → C",
  },
  {
    symbol: "Z1, Z2",
    name: "Face slopes",
    unit: "H:1V",
    range: "2–4",
    meaning: "Upstream (Z1) and downstream (Z2) embankment slopes.",
    equation: "Used in the cross-section schematic and residual side slope",
  },
  {
    symbol: "L",
    name: "Pipe / core length",
    unit: "m",
    range: "≈ core thickness",
    meaning: "Seepage-path length of the concentrated leak through the core.",
    equation: "τ = ρ g R H / (2 L)",
  },
  {
    symbol: "Vw, y",
    name: "Reservoir volume & depth",
    unit: "m³, m",
    range: "project",
    meaning: "Storage is a power function of depth, calibrated at the initial pool.",
    equation: "V(y) = V0 (y / y0)^m",
  },
  {
    symbol: "I",
    name: "Erosion rate index",
    unit: "—",
    range: "0–6",
    meaning: "Wan & Fell index from the Hole Erosion Test. Higher I = more resistant soil.",
    equation: "Ce = 10^(−I)",
  },
  {
    symbol: "Ce",
    name: "Coefficient of soil erosion",
    unit: "s/m",
    range: "10⁻⁶ – 10⁻¹",
    meaning: "Converts excess shear stress into a volume erosion rate.",
    equation: "ε = (Ce / ρd) max(τ − τc, 0)",
  },
  {
    symbol: "τc",
    name: "Critical shear stress",
    unit: "Pa",
    range: "0–100+",
    meaning: "Shear stress below which erosion is taken as zero.",
    equation: "ε = 0 if τ ≤ τc",
  },
  {
    symbol: "τ",
    name: "Applied shear stress",
    unit: "Pa",
    range: "computed",
    meaning: "Pipe wall shear, Manning bed shear, or hydrostatic headcut-face shear.",
    equation: "Open: τ = ρ g n² U² / Rh^{1/3}; Headcut face: τ ≈ ρ g h",
  },
  {
    symbol: "x_h",
    name: "Headcut position",
    unit: "m",
    range: "0 – C",
    meaning: "Distance the vertical scarp has migrated into the crest from the downstream edge.",
    equation: "dx_h/dt = f_h · ε(τ_face)",
  },
  {
    symbol: "f_h",
    name: "Headcut advance factor",
    unit: "—",
    range: "3–15",
    meaning: "Scales horizontal advance relative to the excess-shear rate (Temple-style calibration knob).",
    equation: "dx_h/dt = f_h · (Ce/ρd) max(τ_face − τc, 0)",
  },
  {
    symbol: "Q",
    name: "Breach discharge",
    unit: "m³/s",
    range: "computed",
    meaning: "Outflow through the current opening, plus any constant spillway flow.",
    equation: "Weir: Q = Cw Wavg h^{1.5} · Orifice: Q = Cd π R² √(2gH)",
  },
  {
    symbol: "Wb",
    name: "Breach base width",
    unit: "m",
    range: "grows",
    meaning: "Bottom width of the trapezoidal open breach after collapse or notch formation.",
    equation: "dWb/dt = 2 ε fs",
  },
  {
    symbol: "R",
    name: "Pipe radius",
    unit: "m",
    range: "grows",
    meaning: "Radius of the cylindrical concentrated leak before roof collapse.",
    equation: "dR/dt = ε",
  },
];

export const EQUATIONS = [
  {
    title: "Reservoir continuity",
    latex: "dV/dt = Q_in − Q_out",
    note: "Water level follows from the power-function stage-storage curve. Falling head is fully coupled — unlike a constant-head pipe formula.",
  },
  {
    title: "Open-breach weir",
    latex: "Q = C_w (W_b + Z_b h) h^{3/2}",
    note: "Broad-crested trapezoidal weir. Default Cw = 1.7 (metric). Head h is water surface minus current invert.",
  },
  {
    title: "Piping orifice",
    latex: "Q = C_d π R² √(2 g H)",
    note: "Used until the pipe diameter reaches the collapse criterion, then the model switches to the weir.",
  },
  {
    title: "Erosion rate",
    latex: "ε = (10^{−I} / ρ_d) max(τ − τ_c, 0)",
    note: "Wan & Fell coefficient of soil erosion. A change of 1 in I changes the rate by a factor of ten.",
  },
  {
    title: "Open-channel shear",
    latex: "τ = ρ g n² U² / R_h^{1/3}",
    note: "Manning-derived bed shear on the breach channel. U = Q/A, Rh = A/P.",
  },
  {
    title: "Pipe-wall shear",
    latex: "τ = ρ g R H / (2 L)",
    note: "Bonelli-type driving-pressure form. L is the core / pipe length.",
  },
  {
    title: "Headcut face shear & advance",
    latex: "τ_face ≈ ρ g h ,   dx_h/dt = f_h ε(τ_face)",
    note: "Temple / WinDAM-style discrete headcut. Deepening is throttled until x_h reaches the crest width C. After breakthrough, full bed-shear erosion applies.",
  },
  {
    title: "Roof collapse",
    latex: "2 R ≥ κ · (crest − invert)",
    note: "When the pipe is large enough relative to remaining cover, the roof collapses and an open trapezoidal breach is born.",
  },
  {
    title: "Residual side slope",
    latex: "Z_b ≥ cot(φ)",
    note: "The open-breach batter cannot stand steeper than the friction angle; the model snaps Zb to the residual if needed.",
  },
];

export const LIMITATIONS = [
  "Homogeneous fill is assumed. Zoned dams, filters, and cores are not resolved as separate materials.",
  "Headcut advance uses a hydrostatic face-shear driver scaled by f_h — not a full jet-impingement or SITES energy-dissipation formulation.",
  "Side-slope failure is a residual-friction rule, not a full limit-equilibrium search (no SLOPE/W-style slip surfaces).",
  "The erosion-rate index I should come from a Hole Erosion Test or a carefully chosen typical value. It dominates the answer.",
  "Constant or slowly varying inflow. A full flood hydrograph can be added later as a boundary condition.",
  "This is a screening / teaching engine in the spirit of NWS BREACH, DLBreach and WinDAM — not a replacement for a site-specific numerical study.",
];

export const I_TABLE = [
  { i: "0 – 2", soil: "Dispersive clays, fine silts, SM with little plasticity", rate: "Extremely rapid" },
  { i: "2 – 3", soil: "Many SM, SC, ML, low-plasticity CL", rate: "Rapid (hours)" },
  { i: "3 – 4", soil: "CL, CH, MH of moderate plasticity", rate: "Moderate" },
  { i: "4 – 5", soil: "Higher-plasticity, well-compacted clays", rate: "Slow (days)" },
  { i: "5 – 6+", soil: "Extremely resistant / cemented", rate: "Very slow" },
];
