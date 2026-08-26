import { s as require_jsx_runtime } from "../_libs/@radix-ui/react-collection+[...].mjs";
import { a as CardDescription, i as CardContent, o as CardHeader, r as Card, s as CardTitle, t as AppShell } from "./card-C9FRDXWz.mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/theory-tSzl3Ytg.js
var import_jsx_runtime = require_jsx_runtime();
var PARAM_DOCS = [
	{
		symbol: "Hb",
		name: "Dam height",
		unit: "m",
		range: "project",
		meaning: "Crest elevation minus foundation / breach-base elevation.",
		equation: "Hb = Crest − Base"
	},
	{
		symbol: "C",
		name: "Crest width",
		unit: "m",
		range: "2–12 typical",
		meaning: "Horizontal width of the dam crest between the upstream and downstream edges.",
		equation: "Geometry of the eroded prism"
	},
	{
		symbol: "Z1, Z2",
		name: "Face slopes",
		unit: "H:1V",
		range: "2–4",
		meaning: "Upstream (Z1) and downstream (Z2) embankment slopes.",
		equation: "Used in the cross-section schematic and residual side slope"
	},
	{
		symbol: "L",
		name: "Pipe / core length",
		unit: "m",
		range: "≈ core thickness",
		meaning: "Seepage-path length of the concentrated leak through the core.",
		equation: "τ = ρ g R H / (2 L)"
	},
	{
		symbol: "Vw, y",
		name: "Reservoir volume & depth",
		unit: "m³, m",
		range: "project",
		meaning: "Storage is a power function of depth, calibrated at the initial pool.",
		equation: "V(y) = V0 (y / y0)^m"
	},
	{
		symbol: "I",
		name: "Erosion rate index",
		unit: "—",
		range: "0–6",
		meaning: "Wan & Fell index from the Hole Erosion Test. Higher I = more resistant soil.",
		equation: "Ce = 10^(−I)"
	},
	{
		symbol: "Ce",
		name: "Coefficient of soil erosion",
		unit: "s/m",
		range: "10⁻⁶ – 10⁻¹",
		meaning: "Converts excess shear stress into a volume erosion rate.",
		equation: "ε = (Ce / ρd) max(τ − τc, 0)"
	},
	{
		symbol: "τc",
		name: "Critical shear stress",
		unit: "Pa",
		range: "0–100+",
		meaning: "Shear stress below which erosion is taken as zero.",
		equation: "ε = 0 if τ ≤ τc"
	},
	{
		symbol: "τ",
		name: "Applied shear stress",
		unit: "Pa",
		range: "computed",
		meaning: "Pipe wall shear (piping) or Manning bed shear (open breach).",
		equation: "Open: τ = ρ g n² U² / Rh^{1/3}"
	},
	{
		symbol: "Q",
		name: "Breach discharge",
		unit: "m³/s",
		range: "computed",
		meaning: "Outflow through the current opening, plus any constant spillway flow.",
		equation: "Weir: Q = Cw Wavg h^{1.5} · Orifice: Q = Cd π R² √(2gH)"
	},
	{
		symbol: "Wb",
		name: "Breach base width",
		unit: "m",
		range: "grows",
		meaning: "Bottom width of the trapezoidal open breach after collapse or notch formation.",
		equation: "dWb/dt = 2 ε fs"
	},
	{
		symbol: "R",
		name: "Pipe radius",
		unit: "m",
		range: "grows",
		meaning: "Radius of the cylindrical concentrated leak before roof collapse.",
		equation: "dR/dt = ε"
	}
];
var EQUATIONS = [
	{
		title: "Reservoir continuity",
		latex: "dV/dt = Q_in − Q_out",
		note: "Water level follows from the power-function stage-storage curve. Falling head is fully coupled — unlike a constant-head pipe formula."
	},
	{
		title: "Open-breach weir",
		latex: "Q = C_w (W_b + Z_b h) h^{3/2}",
		note: "Broad-crested trapezoidal weir. Default Cw = 1.7 (metric). Head h is water surface minus current invert."
	},
	{
		title: "Piping orifice",
		latex: "Q = C_d π R² √(2 g H)",
		note: "Used until the pipe diameter reaches the collapse criterion, then the model switches to the weir."
	},
	{
		title: "Erosion rate",
		latex: "ε = (10^{−I} / ρ_d) max(τ − τ_c, 0)",
		note: "Wan & Fell coefficient of soil erosion. A change of 1 in I changes the rate by a factor of ten."
	},
	{
		title: "Open-channel shear",
		latex: "τ = ρ g n² U² / R_h^{1/3}",
		note: "Manning-derived bed shear on the breach channel. U = Q/A, Rh = A/P."
	},
	{
		title: "Pipe-wall shear",
		latex: "τ = ρ g R H / (2 L)",
		note: "Bonelli-type driving-pressure form. L is the core / pipe length."
	},
	{
		title: "Roof collapse",
		latex: "2 R ≥ κ · (crest − invert)",
		note: "When the pipe is large enough relative to remaining cover, the roof collapses and an open trapezoidal breach is born."
	}
];
var LIMITATIONS = [
	"Homogeneous fill is assumed. Zoned dams, filters, and cores are not resolved as separate materials.",
	"Headcut migration (typical of cohesive overtopping) is represented only through surface erosion, not as a discrete headcut module.",
	"Side-slope failure is a residual-friction rule, not a full limit-equilibrium search.",
	"The erosion-rate index I should come from a Hole Erosion Test or a carefully chosen typical value. It dominates the answer.",
	"Constant or slowly varying inflow. A full flood hydrograph can be added later as a boundary condition.",
	"This is a screening / teaching engine in the spirit of NWS BREACH, DLBreach and WinDAM — not a replacement for a site-specific numerical study."
];
var I_TABLE = [
	{
		i: "0 – 2",
		soil: "Dispersive clays, fine silts, SM with little plasticity",
		rate: "Extremely rapid"
	},
	{
		i: "2 – 3",
		soil: "Many SM, SC, ML, low-plasticity CL",
		rate: "Rapid (hours)"
	},
	{
		i: "3 – 4",
		soil: "CL, CH, MH of moderate plasticity",
		rate: "Moderate"
	},
	{
		i: "4 – 5",
		soil: "Higher-plasticity, well-compacted clays",
		rate: "Slow (days)"
	},
	{
		i: "5 – 6+",
		soil: "Extremely resistant / cemented",
		rate: "Very slow"
	}
];
function TheoryView() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "mx-auto flex w-full max-w-5xl flex-col gap-8 pb-16",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("header", {
				className: "flex flex-col gap-2",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs font-medium uppercase tracking-[0.16em] text-accent",
						children: "Mechanistic engine"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
						className: "font-display text-3xl font-medium tracking-tight md:text-4xl",
						children: "Equations, parameters, limits"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "max-w-2xl text-sm leading-relaxed text-muted-foreground",
						children: "Every symbol used in the formation model is defined here. The engine is a simplified physical model in the lineage of NWS BREACH, DLBreach and WinDAM — coupled hydraulics, excess-shear erosion, and a roof-collapse switch — not a regression on historic peaks."
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CardHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardTitle, { children: "Governing equations" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardDescription, { children: "Integrated at every time step with a falling reservoir head." })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardContent, {
				className: "grid gap-4",
				children: EQUATIONS.map((eq) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "rounded-md border border-border bg-background p-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "text-xs font-medium uppercase tracking-wide text-muted-foreground",
							children: eq.title
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-1 font-mono text-sm",
							children: eq.latex
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
							className: "mt-2 text-sm text-muted-foreground",
							children: eq.note
						})
					]
				}, eq.title))
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CardHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardTitle, { children: "Parameter catalogue" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardDescription, { children: "Units, typical ranges, and where each term appears." })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardContent, {
				className: "overflow-x-auto",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("table", {
					className: "w-full min-w-[40rem] text-left text-sm",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("thead", { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("tr", {
						className: "border-b border-border text-xs uppercase tracking-wide text-muted-foreground",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
								className: "py-2 pr-3 font-medium",
								children: "Symbol"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
								className: "py-2 pr-3 font-medium",
								children: "Name"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
								className: "py-2 pr-3 font-medium",
								children: "Unit"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
								className: "py-2 pr-3 font-medium",
								children: "Range"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
								className: "py-2 font-medium",
								children: "Meaning"
							})
						]
					}) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("tbody", { children: PARAM_DOCS.map((p) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("tr", {
						className: "border-b border-border/70 align-top",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
								className: "py-2 pr-3 font-mono text-xs",
								children: p.symbol
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
								className: "py-2 pr-3",
								children: p.name
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
								className: "py-2 pr-3 text-muted-foreground",
								children: p.unit
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
								className: "py-2 pr-3 text-muted-foreground",
								children: p.range
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("td", {
								className: "py-2 text-muted-foreground",
								children: [
									p.meaning,
									" ",
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
										className: "block font-mono text-[11px] text-foreground/70",
										children: p.equation
									})
								]
							})
						]
					}, p.symbol)) })]
				})
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CardHeader, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardTitle, { children: "Typical erosion-rate index" }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardDescription, { children: "Wan & Fell / ICOLD screening values. Prefer a Hole Erosion Test when you have one." })] }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardContent, {
				className: "overflow-x-auto",
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("table", {
					className: "w-full text-left text-sm",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("thead", { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("tr", {
						className: "border-b border-border text-xs uppercase tracking-wide text-muted-foreground",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
								className: "py-2 pr-3 font-medium",
								children: "I"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
								className: "py-2 pr-3 font-medium",
								children: "Soils"
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("th", {
								className: "py-2 font-medium",
								children: "Relative rate"
							})
						]
					}) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("tbody", { children: I_TABLE.map((row) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("tr", {
						className: "border-b border-border/70",
						children: [
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
								className: "py-2 pr-3 font-mono",
								children: row.i
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
								className: "py-2 pr-3",
								children: row.soil
							}),
							/* @__PURE__ */ (0, import_jsx_runtime.jsx)("td", {
								className: "py-2",
								children: row.rate
							})
						]
					}, row.i)) })]
				})
			})] }),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardHeader, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardTitle, { children: "Limitations" }) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardContent, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("ul", {
				className: "flex list-disc flex-col gap-2 pl-5 text-sm text-muted-foreground",
				children: LIMITATIONS.map((item) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("li", { children: item }, item))
			}) })] })
		]
	});
}
function TheoryPage() {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AppShell, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TheoryView, {}) });
}
//#endregion
export { TheoryPage as component };
