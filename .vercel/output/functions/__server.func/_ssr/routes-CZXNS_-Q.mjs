import { i as __toESM } from "../_runtime.mjs";
import { u as require_react } from "../_libs/@floating-ui/react-dom+[...].mjs";
import { s as require_jsx_runtime } from "../_libs/@radix-ui/react-collection+[...].mjs";
import { l as Info, o as Play, r as Upload, u as Download } from "../_libs/lucide-react.mjs";
import { i as CardContent, n as Button, o as CardHeader, r as Card, s as CardTitle, t as AppShell } from "./card-C9FRDXWz.mjs";
import { a as cn, i as TooltipTrigger, n as Tooltip, o as downloadText, r as TooltipContent, s as formatNumber } from "./router-jkfTBY6q.mjs";
import { t as Root } from "../_libs/radix-ui__react-label.mjs";
import { t as create } from "../_libs/zustand.mjs";
import { a as Area, c as ResponsiveContainer, i as XAxis, l as Tooltip$1, n as LineChart, o as Line, r as YAxis, s as CartesianGrid, t as AreaChart } from "../_libs/recharts+[...].mjs";
import { i as SliderTrack, n as SliderRange, r as SliderThumb, t as Slider$1 } from "../_libs/@radix-ui/react-slider+[...].mjs";
//#region node_modules/.nitro/vite/services/ssr/assets/routes-CZXNS_-Q.js
var import_react = /* @__PURE__ */ __toESM(require_react());
var import_jsx_runtime = require_jsx_runtime();
function DamSchematic({ inputs, step }) {
	const Hb = Math.max(inputs.crestElev - inputs.baseElev, .1);
	const W = 720;
	const H = 340;
	const ground = 300;
	const crestY = 70;
	const damH = 230;
	const crestW = 70;
	const upRun = inputs.zUp * damH * .35;
	const dnRun = inputs.zDown * damH * .35;
	const cx = 400;
	const crestL = cx - crestW / 2;
	const crestR = 435;
	const toeL = crestL - upRun;
	const toeR = crestR + dnRun;
	const elevToY = (elev) => {
		const t = (inputs.crestElev - elev) / Hb;
		return crestY + t * damH;
	};
	const WL = step?.WL ?? inputs.initialWL;
	const waterY = elevToY(WL);
	const zbY = elevToY(step?.zb ?? (inputs.mode === "piping" ? inputs.pipeInvert : inputs.crestElev));
	const WbPx = Math.min(180, Math.max(8, (step?.Wb ?? inputs.initialNotchWidth) / Math.max(inputs.crestLength, 1) * 220));
	const pipeR = Math.max(4, (step?.R ?? inputs.initialPipeRadius) / Hb * damH * 2.2);
	const pipeY = elevToY(inputs.pipeInvert);
	const open = !step || step.stage === "open" || step.stage === "empty" || inputs.mode === "overtopping";
	const waterPoly = `${toeL - 160},${ground} ${toeL - 160},${Math.min(waterY, ground)} ${open && waterY < zbY + 2 ? `${cx - WbPx / 2},${Math.min(waterY, zbY)} ${cx + WbPx / 2},${Math.min(waterY, zbY)}` : `${crestL},${Math.min(waterY, ground)}`} ${toeL},${ground}`;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("svg", {
		viewBox: `0 0 ${W} ${H}`,
		className: "h-auto w-full",
		role: "img",
		"aria-label": "Dam cross-section schematic",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("rect", {
				width: W,
				height: H,
				fill: "#f2eee6"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("line", {
				x1: "24",
				y1: ground,
				x2: "696",
				y2: ground,
				stroke: "#1a1814",
				strokeWidth: "1.2"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("polygon", {
				points: `${toeL},${ground} ${crestL},${crestY} ${crestR},${crestY} ${toeR},${ground}`,
				fill: "#c4b49a",
				stroke: "#1a1814",
				strokeWidth: "1.4"
			}),
			open && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("polygon", {
				points: `${cx - WbPx / 2},${zbY} ${cx + WbPx / 2},${zbY} ${cx + WbPx / 2 + (ground - zbY) * .25},${ground} ${cx - WbPx / 2 - (ground - zbY) * .25},${ground}`,
				fill: "#f2eee6",
				stroke: "#245460",
				strokeWidth: "1.2"
			}),
			WL > inputs.baseElev && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("polygon", {
				points: waterPoly,
				fill: "#3d6f82",
				fillOpacity: "0.35",
				stroke: "#245460",
				strokeWidth: "1"
			}),
			!open && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
				cx,
				cy: pipeY,
				r: pipeR,
				fill: "#3d6f82",
				fillOpacity: "0.55",
				stroke: "#245460",
				strokeWidth: "1.2"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("polyline", {
				points: `${crestL},${crestY} ${crestR},${crestY}`,
				stroke: "#1a1814",
				strokeWidth: "2.2"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dim, {
				x1: crestL,
				x2: crestR,
				y: 52,
				label: `C = ${inputs.crestWidth} m`
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dim, {
				v: true,
				x1: 24,
				y1: crestY,
				y2: ground,
				label: `Hb = ${Hb.toFixed(1)} m`
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("text", {
				x: toeL + 8,
				y: 290,
				className: "fill-foreground",
				fontSize: "10",
				fontFamily: "IBM Plex Sans",
				children: [
					"Z1 = ",
					inputs.zUp,
					" H:1V"
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("text", {
				x: 447,
				y: 290,
				className: "fill-foreground",
				fontSize: "10",
				fontFamily: "IBM Plex Sans",
				children: [
					"Z2 = ",
					inputs.zDown,
					" H:1V"
				]
			}),
			open && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("text", {
				x: cx,
				y: zbY - 8,
				textAnchor: "middle",
				fontSize: "10",
				fontFamily: "IBM Plex Sans",
				fill: "#245460",
				children: [
					"Wb = ",
					(step?.Wb ?? inputs.initialNotchWidth).toFixed(2),
					" m"
				]
			}),
			!open && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("text", {
				x: cx + pipeR + 10,
				y: pipeY + 4,
				fontSize: "10",
				fontFamily: "IBM Plex Sans",
				fill: "#245460",
				children: [
					"R = ",
					(step?.R ?? inputs.initialPipeRadius).toFixed(3),
					" m"
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("text", {
				x: 40,
				y: Math.min(waterY, ground) - 8,
				fontSize: "10",
				fontFamily: "IBM Plex Sans",
				fill: "#245460",
				children: [
					"WL = ",
					WL.toFixed(2),
					" m"
				]
			})
		]
	});
}
function Dim({ x1, x2, y, y1, y2, label, v }) {
	if (v && x1 != null && y1 != null && y2 != null) return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("g", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("line", {
		x1,
		y1,
		x2: x1,
		y2,
		stroke: "#6b6560",
		strokeWidth: "0.8"
	}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("text", {
		x: x1 + 6,
		y: (y1 + y2) / 2,
		fontSize: "10",
		fontFamily: "IBM Plex Sans",
		fill: "#6b6560",
		children: label
	})] });
	if (x1 == null || x2 == null || y == null) return null;
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("g", { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("line", {
		x1,
		y1: y,
		x2,
		y2: y,
		stroke: "#6b6560",
		strokeWidth: "0.8"
	}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("text", {
		x: (x1 + x2) / 2,
		y: y - 4,
		textAnchor: "middle",
		fontSize: "10",
		fontFamily: "IBM Plex Sans",
		fill: "#6b6560",
		children: label
	})] });
}
var Input = import_react.forwardRef(({ className, type, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
	type,
	className: cn("flex h-10 w-full rounded-md border border-border bg-input px-3 text-sm text-foreground tabular-nums shadow-none transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50", className),
	ref,
	...props
}));
Input.displayName = "Input";
var Label = import_react.forwardRef(({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Root, {
	ref,
	className: cn("text-xs font-medium tracking-wide text-muted-foreground", className),
	...props
}));
Label.displayName = "Label";
var DEFAULT_INPUTS = {
	projectName: "Homogeneous earthfill — overtopping",
	mode: "overtopping",
	crestElev: 12,
	baseElev: 0,
	crestWidth: 4,
	crestLength: 80,
	zUp: 3,
	zDown: 2.5,
	coreLength: 18,
	initialWL: 12.15,
	volumeM3: 18e4,
	surfaceAreaHa: 3.2,
	inflowM3s: 2,
	storageExponent: 2,
	spillwayQ: 0,
	rhoD: 1800,
	phiDeg: 32,
	tauC: 8,
	erosionIndexI: 3.2,
	manningN: .03,
	zb: .5,
	sideErosionFactor: 1.2,
	CdOrifice: .6,
	Cw: 1.7,
	initialNotchWidth: 1.2,
	initialPipeRadius: .08,
	pipeInvert: 4,
	collapseRatio: .55,
	dt: 2,
	tMaxHours: 6
};
var STORAGE_KEY = "dam-breach-studio-v1";
function loadInputs() {
	if (typeof window === "undefined") return DEFAULT_INPUTS;
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		if (!raw) return DEFAULT_INPUTS;
		return {
			...DEFAULT_INPUTS,
			...JSON.parse(raw)
		};
	} catch {
		return DEFAULT_INPUTS;
	}
}
var useStudio = create((set) => ({
	inputs: loadInputs(),
	result: null,
	playIndex: 0,
	running: false,
	setInput: (key, value) => set((s) => {
		const inputs = {
			...s.inputs,
			[key]: value
		};
		try {
			localStorage.setItem(STORAGE_KEY, JSON.stringify(inputs));
		} catch {}
		return { inputs };
	}),
	setInputs: (inputs) => {
		try {
			localStorage.setItem(STORAGE_KEY, JSON.stringify(inputs));
		} catch {}
		set({
			inputs,
			result: null,
			playIndex: 0
		});
	},
	setResult: (result) => set({
		result,
		playIndex: result ? result.series.length - 1 : 0
	}),
	setPlayIndex: (playIndex) => set({ playIndex }),
	setRunning: (running) => set({ running })
}));
function ParamForm() {
	const { inputs, setInput } = useStudio();
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-col gap-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldGroup, {
				title: "Project",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TextField, {
					id: "projectName",
					label: "Project name",
					value: inputs.projectName,
					onChange: (v) => setInput("projectName", v)
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex flex-col gap-1.5",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, {
						htmlFor: "mode",
						children: "Failure mode"
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("select", {
						id: "mode",
						className: "h-10 rounded-md border border-border bg-input px-3 text-sm",
						value: inputs.mode,
						onChange: (e) => setInput("mode", e.target.value),
						children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
							value: "overtopping",
							children: "Overtopping"
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("option", {
							value: "piping",
							children: "Piping / concentrated leak"
						})]
					})]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldGroup, {
				title: "Dam geometry",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "crestElev",
						label: "Crest elevation",
						unit: "m",
						hint: "Top of dam.",
						k: "crestElev"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "baseElev",
						label: "Base elevation",
						unit: "m",
						hint: "Foundation / breach invert floor.",
						k: "baseElev"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "crestWidth",
						label: "Crest width C",
						unit: "m",
						hint: "Horizontal crest thickness.",
						k: "crestWidth"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "crestLength",
						label: "Crest length",
						unit: "m",
						hint: "Valley-crossing length. Caps final Wb.",
						k: "crestLength"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "zUp",
						label: "Upstream slope Z1",
						unit: "H:1V",
						hint: "Horizontal:vertical of the upstream face.",
						k: "zUp"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "zDown",
						label: "Downstream slope Z2",
						unit: "H:1V",
						hint: "Downstream face. Steeper faces concentrate shear.",
						k: "zDown"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "coreLength",
						label: "Pipe / core length L",
						unit: "m",
						hint: "Seepage path used in pipe-wall shear.",
						k: "coreLength"
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldGroup, {
				title: "Reservoir",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "initialWL",
						label: "Initial water level",
						unit: "m",
						hint: "Pool elevation at t = 0.",
						k: "initialWL"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "volumeM3",
						label: "Storage at that level",
						unit: "m³",
						hint: "Calibrates V(y) = V0 (y/y0)^m.",
						k: "volumeM3"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "surfaceAreaHa",
						label: "Surface area",
						unit: "ha",
						hint: "Informational; volume curve uses V0 and m.",
						k: "surfaceAreaHa"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "inflowM3s",
						label: "Inflow Qin",
						unit: "m³/s",
						hint: "Constant inflow during the run.",
						k: "inflowM3s"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "storageExponent",
						label: "Storage exponent m",
						unit: "—",
						hint: "Typically 2–3. Higher m = more volume near the top.",
						k: "storageExponent"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "spillwayQ",
						label: "Spillway discharge",
						unit: "m³/s",
						hint: "Constant additional outlet (optional).",
						k: "spillwayQ"
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldGroup, {
				title: "Soil / erosion",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "erosionIndexI",
						label: "Erosion rate index I",
						unit: "—",
						hint: "Wan & Fell. 2 = rapid, 4 = slow. Dominates the answer.",
						k: "erosionIndexI",
						step: .1
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "tauC",
						label: "Critical shear τc",
						unit: "Pa",
						hint: "No erosion below this shear.",
						k: "tauC"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "rhoD",
						label: "Dry density ρd",
						unit: "kg/m³",
						hint: "Used to convert Ce into a volume rate.",
						k: "rhoD"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "phiDeg",
						label: "Friction angle φ",
						unit: "°",
						hint: "Sets a residual side-slope floor after collapse.",
						k: "phiDeg"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "manningN",
						label: "Manning n",
						unit: "—",
						hint: "Roughness of the breach channel.",
						k: "manningN",
						step: .005
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "zb",
						label: "Breach side slope Zb",
						unit: "H:1V",
						hint: "Trapezoid batter of the open breach.",
						k: "zb",
						step: .05
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "sideErosionFactor",
						label: "Side erosion factor",
						unit: "—",
						hint: "Widening relative to deepening (≈ 1–2).",
						k: "sideErosionFactor",
						step: .1
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldGroup, {
				title: "Hydraulics & initiation",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "Cw",
						label: "Weir coefficient Cw",
						unit: "m^0.5/s",
						hint: "Broad-crested weir. Default 1.7 metric.",
						k: "Cw",
						step: .05
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "CdOrifice",
						label: "Orifice Cd",
						unit: "—",
						hint: "Pipe discharge coefficient.",
						k: "CdOrifice",
						step: .05
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "initialNotchWidth",
						label: "Initial notch width",
						unit: "m",
						hint: "Starter cut for overtopping.",
						k: "initialNotchWidth"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "initialPipeRadius",
						label: "Initial pipe radius",
						unit: "m",
						hint: "Detected leak size at t = 0.",
						k: "initialPipeRadius",
						step: .01
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "pipeInvert",
						label: "Pipe invert",
						unit: "m",
						hint: "Elevation of the concentrated leak.",
						k: "pipeInvert"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
						id: "collapseRatio",
						label: "Collapse ratio κ",
						unit: "—",
						hint: "Roof fails when 2R ≥ κ × cover.",
						k: "collapseRatio",
						step: .05
					})
				]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(FieldGroup, {
				title: "Numerical",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
					id: "dt",
					label: "Time step",
					unit: "s",
					hint: "2 s is a good default.",
					k: "dt"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Num, {
					id: "tMaxHours",
					label: "Max duration",
					unit: "h",
					hint: "Stops earlier if the reservoir empties.",
					k: "tMaxHours"
				})]
			})
		]
	});
}
function FieldGroup({ title, children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("section", {
		className: "flex flex-col gap-3",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
			className: "font-display text-base font-medium tracking-tight",
			children: title
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
			className: "grid grid-cols-1 gap-3 sm:grid-cols-2",
			children
		})]
	});
}
function Num({ id, label, unit, hint, k, step = .1 }) {
	const { inputs, setInput } = useStudio();
	const value = inputs[k];
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-col gap-1.5",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "flex items-center gap-1",
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, {
					htmlFor: id,
					children: label
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Tooltip, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(TooltipTrigger, {
					asChild: true,
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
						type: "button",
						className: "text-muted-foreground",
						"aria-label": `About ${label}`,
						children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Info, { className: "size-3.5" })
					})
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(TooltipContent, { children: hint })] }),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
					className: "ml-auto font-mono text-[10px] text-muted-foreground",
					children: unit
				})
			]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
			id,
			type: "number",
			step,
			value: typeof value === "number" ? value : 0,
			onChange: (e) => setInput(k, Number(e.target.value))
		})]
	});
}
function TextField({ id, label, value, onChange }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-col gap-1.5 sm:col-span-2",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Label, {
			htmlFor: id,
			children: label
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Input, {
			id,
			value,
			onChange: (e) => onChange(e.target.value)
		})]
	});
}
function ResultCharts({ result, playIndex }) {
	const data = result.series.map((s) => ({
		hr: Number((s.t / 3600).toFixed(4)),
		Q: Number(s.Q.toFixed(3)),
		Wb: Number(s.Wb.toFixed(3)),
		depth: Number((s.WL - s.zb > 0 ? s.WL - s.zb : 0).toFixed(3))
	}));
	const cursor = data[Math.min(playIndex, data.length - 1)];
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "grid gap-4 lg:grid-cols-2",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(ChartCard, {
			title: "Outflow hydrograph",
			unit: "m³/s",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ResponsiveContainer, {
				width: "100%",
				height: 220,
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(AreaChart, {
					data,
					margin: {
						top: 8,
						right: 8,
						left: 0,
						bottom: 0
					},
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CartesianGrid, {
							stroke: "#d4cdc0",
							strokeDasharray: "3 3"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(XAxis, {
							dataKey: "hr",
							tick: { fontSize: 11 },
							tickLine: false
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(YAxis, {
							tick: { fontSize: 11 },
							tickLine: false,
							width: 48
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Tooltip$1, {
							contentStyle: {
								background: "#fbf8f2",
								border: "1px solid #d4cdc0",
								fontSize: 12
							},
							formatter: (v) => [`${formatNumber(Number(v), 2)} m³/s`, "Q"]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Area, {
							type: "monotone",
							dataKey: "Q",
							stroke: "#245460",
							fill: "#3d6f82",
							fillOpacity: .25,
							strokeWidth: 1.6
						})
					]
				})
			}), cursor && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("p", {
				className: "mt-1 text-xs text-muted-foreground",
				children: [
					"Cursor ",
					cursor.hr.toFixed(3),
					" h · Q = ",
					formatNumber(cursor.Q, 2),
					" m³/s"
				]
			})]
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(ChartCard, {
			title: "Breach growth",
			unit: "m",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ResponsiveContainer, {
				width: "100%",
				height: 220,
				children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(LineChart, {
					data,
					margin: {
						top: 8,
						right: 8,
						left: 0,
						bottom: 0
					},
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CartesianGrid, {
							stroke: "#d4cdc0",
							strokeDasharray: "3 3"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(XAxis, {
							dataKey: "hr",
							tick: { fontSize: 11 },
							tickLine: false
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(YAxis, {
							tick: { fontSize: 11 },
							tickLine: false,
							width: 40
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Tooltip$1, { contentStyle: {
							background: "#fbf8f2",
							border: "1px solid #d4cdc0",
							fontSize: 12
						} }),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Line, {
							type: "monotone",
							dataKey: "Wb",
							stroke: "#1a1814",
							dot: false,
							strokeWidth: 1.6,
							name: "Wb"
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Line, {
							type: "monotone",
							dataKey: "depth",
							stroke: "#245460",
							dot: false,
							strokeWidth: 1.6,
							name: "Head"
						})
					]
				})
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
				className: "mt-1 text-xs text-muted-foreground",
				children: "Black = base width Wb · Teal = flow head over invert"
			})]
		})]
	});
}
function ChartCard({ title, unit, children }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "rounded-lg border border-border bg-card p-4",
		children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "mb-2 flex items-baseline justify-between",
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h3", {
				className: "font-display text-base font-medium",
				children: title
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
				className: "font-mono text-[10px] text-muted-foreground",
				children: unit
			})]
		}), children]
	});
}
function Badge({ className, tone = "neutral", ...props }) {
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", {
		className: cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium tracking-wide", tone === "neutral" && "bg-muted text-muted-foreground", tone === "accent" && "bg-accent/15 text-accent", tone === "warn" && "bg-warn/15 text-warn", tone === "ok" && "bg-ok/15 text-ok", className),
		...props
	});
}
var Slider = import_react.forwardRef(({ className, ...props }, ref) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Slider$1, {
	ref,
	className: cn("relative flex w-full touch-none select-none items-center", className),
	...props,
	children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(SliderTrack, {
		className: "relative h-1.5 w-full grow overflow-hidden rounded-full bg-muted",
		children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SliderRange, { className: "absolute h-full bg-accent" })
	}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(SliderThumb, { className: "block size-4 rounded-full border border-border bg-card shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" })]
}));
Slider.displayName = "Slider";
var EXAMPLES = [
	{
		id: "overtop-moderate",
		title: "Overtopping — moderately erodible fill",
		blurb: "12 m homogeneous earthfill, pool just above the crest. I = 3.2 (CL/SM range).",
		inputs: { ...DEFAULT_INPUTS }
	},
	{
		id: "piping-moderate",
		title: "Piping — concentrated leak through the core",
		blurb: "Same dam, pool 1 m below crest. Pipe starts at 8 cm radius and enlarges until roof collapse.",
		inputs: {
			...DEFAULT_INPUTS,
			projectName: "Homogeneous earthfill — piping",
			mode: "piping",
			initialWL: 11,
			volumeM3: 15e4,
			inflowM3s: .4,
			pipeInvert: 4,
			initialPipeRadius: .08,
			erosionIndexI: 3
		}
	},
	{
		id: "overtop-resistant",
		title: "Overtopping — erosion-resistant clay",
		blurb: "Higher plasticity core (I = 4.6). Breach grows slowly; useful contrast on soil control.",
		inputs: {
			...DEFAULT_INPUTS,
			projectName: "Resistant clay — overtopping",
			erosionIndexI: 4.6,
			tauC: 25,
			phiDeg: 28,
			tMaxHours: 12,
			initialWL: 12.2
		}
	},
	{
		id: "overtop-rapid",
		title: "Overtopping — rapidly erodible silt",
		blurb: "Low I = 2.2. Expect a short, sharp hydrograph — typical of SM/ML fills.",
		inputs: {
			...DEFAULT_INPUTS,
			projectName: "Rapid silt — overtopping",
			erosionIndexI: 2.2,
			tauC: 2,
			phiDeg: 34,
			tMaxHours: 3,
			initialNotchWidth: .8
		}
	}
];
var G = 9.81;
var RHO = 1e3;
function clamp(v, lo, hi) {
	return Math.min(hi, Math.max(lo, v));
}
/**
* Mechanistic breach-formation engine (simplified physical model).
*
* Hydraulics
*   Open breach:  Q = Cw · Wavg · h^1.5     (broad-crested trapezoidal weir)
*   Piping:       Q = Cd · π R² √(2 g H)     (orifice)
*
* Erosion (Wan & Fell / excess shear)
*   Ce = 10^(−I)
*   ε  = (Ce / ρd) · max(τ − τc, 0)         [m/s]
*
* Bed shear (open channel, Manning)
*   τ = ρ g n² U² / Rh^(1/3)
*
* Pipe wall shear (Bonelli-type driving pressure)
*   τ = ρ g R H / (2 L)
*
* Geometry
*   Deepening: zb ← zb − ε Δt
*   Widening:  Wb ← Wb + 2 ε fs Δt
*   Roof collapse when 2R ≥ collapseRatio · cover
*
* Reservoir
*   V(y) = V0 (y / y0)^m
*   dV/dt = Qin − Q
*/
function runBreachSimulation(p) {
	const t0 = performance.now();
	const warnings = [];
	const dt = Math.max(p.dt, .2);
	const tMax = Math.max(p.tMaxHours, .1) * 3600;
	const nSteps = Math.ceil(tMax / dt);
	const recordEvery = Math.max(1, Math.round(nSteps / 600));
	const Hb = p.crestElev - p.baseElev;
	if (Hb <= 0) return emptyResult(t0, ["Dam height must be positive (crest > base)."]);
	const y0 = Math.max(p.initialWL - p.baseElev, .05);
	const V0 = Math.max(p.volumeM3, 1);
	const m = clamp(p.storageExponent, 1.2, 3.5);
	const volumeFromY = (yy) => V0 * Math.pow(Math.max(yy, 0) / y0, m);
	const yFromVolume = (vol) => y0 * Math.pow(Math.max(vol, 0) / V0, 1 / m);
	const kd = Math.pow(10, -p.erosionIndexI) / Math.max(p.rhoD, 200);
	let y = y0;
	let V = volumeFromY(y);
	let zb = p.mode === "piping" ? p.pipeInvert : p.crestElev - .04;
	let Wb = p.mode === "piping" ? 0 : Math.max(p.initialNotchWidth, .2);
	let R = Math.max(p.initialPipeRadius, .02);
	let Zb = Math.max(p.zb, .05);
	let collapsed = p.mode === "overtopping";
	let tCollapse = p.mode === "overtopping" ? 0 : null;
	let tEmpty = null;
	const phiRad = p.phiDeg * Math.PI / 180;
	const zPhi = 1 / Math.tan(Math.max(phiRad, .15));
	const series = [];
	let Qpeak = 0;
	let tPeak = 0;
	if (p.mode === "overtopping" && p.initialWL < p.crestElev) warnings.push("Initial water level is below the crest — overtopping waits until the pool rises.");
	if (p.erosionIndexI < 1.5) warnings.push("Very low erosion-rate index (I < 1.5): enlargement will be extremely rapid.");
	if (p.erosionIndexI > 5.5) warnings.push("Very high erosion-rate index (I > 5.5): the breach may barely grow within the run window.");
	for (let i = 0; i <= nSteps; i++) {
		const t = i * dt;
		const WL = p.baseElev + y;
		let Q = Math.max(p.spillwayQ, 0);
		let tau = 0;
		let stage = collapsed ? "open" : "piping";
		if (!collapsed) {
			const Hpipe = Math.max(WL - p.pipeInvert, 0);
			if (Hpipe > 0) {
				const area = Math.PI * R * R;
				Q += p.CdOrifice * area * Math.sqrt(2 * G * Hpipe);
				tau = RHO * G * R * Hpipe / (2 * Math.max(p.coreLength, .5));
				R += kd * Math.max(tau - p.tauC, 0) * dt;
				const cover = Math.max(p.crestElev - p.pipeInvert, .2);
				if (2 * R >= p.collapseRatio * cover) {
					collapsed = true;
					tCollapse = t;
					Wb = Math.max(2 * R, p.initialNotchWidth);
					zb = clamp(p.pipeInvert - R, p.baseElev, p.crestElev);
					stage = "open";
				}
			} else stage = "filling";
		}
		if (collapsed) {
			const h = Math.max(WL - zb, 0);
			if (h > 1e-4 && WL >= zb) {
				const Wavg = Wb + Zb * h;
				const qWeir = p.Cw * Wavg * Math.pow(h, 1.5);
				Q += qWeir;
				const A = Math.max(h * (Wb + Zb * h), 1e-6);
				const Pw = Wb + 2 * h * Math.sqrt(1 + Zb * Zb);
				const Rh = A / Math.max(Pw, 1e-6);
				const U = qWeir / A;
				tau = RHO * G * p.manningN * p.manningN * U * U / Math.pow(Math.max(Rh, .03), 1 / 3);
				const er = kd * Math.max(tau - p.tauC, 0);
				const dz = Math.min(er * dt, .04 * Hb);
				zb = Math.max(zb - dz, p.baseElev);
				Wb = Math.min(Wb + 2 * er * p.sideErosionFactor * dt, p.crestLength * 1.05);
				Zb = Math.max(Zb, zPhi * .45);
				stage = "open";
			} else if (WL < p.crestElev - .02 && p.mode === "overtopping" && i < 3) stage = "filling";
		}
		const dV = (p.inflowM3s - Q) * dt;
		if (V + dV < 0) {
			Q = V / dt + p.inflowM3s;
			V = 0;
		} else V = V + dV;
		y = yFromVolume(V);
		if (y > Hb + 8) {
			y = Hb + 8;
			V = volumeFromY(y);
			warnings.push("Pool rose more than 8 m above the crest — check inflow versus spillway capacity.");
		}
		if (Q > Qpeak) {
			Qpeak = Q;
			tPeak = t;
		}
		const hNow = Math.max(p.baseElev + y - zb, 0);
		const Wtop = Wb + 2 * Zb * hNow;
		const step = {
			t,
			Q: Math.max(Q, 0),
			WL: p.baseElev + y,
			zb,
			Wb,
			Wtop,
			R,
			tau,
			V,
			stage
		};
		if (i % recordEvery === 0 || i === nSteps) series.push(step);
		if (V <= .002 * V0 && Q < .02 * Math.max(Qpeak, 1) && t > 30) {
			tEmpty = t;
			step.stage = "empty";
			if (series[series.length - 1] !== step) series.push(step);
			break;
		}
	}
	const last = series[series.length - 1];
	return {
		series,
		Qpeak,
		tPeak,
		tCollapse,
		tEmpty,
		finalWb: last?.Wb ?? 0,
		finalDepth: last ? p.crestElev - last.zb : 0,
		elapsedMs: performance.now() - t0,
		warnings: [...new Set(warnings)]
	};
}
function emptyResult(t0, warnings) {
	return {
		series: [],
		Qpeak: 0,
		tPeak: 0,
		tCollapse: null,
		tEmpty: null,
		finalWb: 0,
		finalDepth: 0,
		elapsedMs: performance.now() - t0,
		warnings
	};
}
function resultToCsv(result) {
	return ["t_s,t_hr,Q_m3s,WL_m,zb_m,Wb_m,Wtop_m,R_m,tau_Pa,V_m3,stage", ...result.series.map((s) => [
		s.t.toFixed(1),
		(s.t / 3600).toFixed(5),
		s.Q.toFixed(4),
		s.WL.toFixed(4),
		s.zb.toFixed(4),
		s.Wb.toFixed(4),
		s.Wtop.toFixed(4),
		s.R.toFixed(4),
		s.tau.toFixed(3),
		s.V.toFixed(2),
		s.stage
	].join(","))].join("\n");
}
function SimulatePage() {
	const { inputs, result, playIndex, running, setResult, setPlayIndex, setRunning, setInputs } = useStudio();
	const fileRef = (0, import_react.useRef)(null);
	const step = result?.series[Math.min(playIndex, (result?.series.length ?? 1) - 1)] ?? null;
	const stats = (0, import_react.useMemo)(() => {
		if (!result) return null;
		return [
			{
				k: "Peak Q",
				v: `${formatNumber(result.Qpeak, 2)} m³/s`
			},
			{
				k: "Time to peak",
				v: `${formatNumber(result.tPeak / 60, 1)} min`
			},
			{
				k: "Final Wb",
				v: `${formatNumber(result.finalWb, 2)} m`
			},
			{
				k: "Breach depth",
				v: `${formatNumber(result.finalDepth, 2)} m`
			},
			{
				k: "Roof collapse",
				v: result.tCollapse == null ? "—" : `${formatNumber(result.tCollapse / 60, 1)} min`
			},
			{
				k: "Compute",
				v: `${formatNumber(result.elapsedMs, 0)} ms`
			}
		];
	}, [result]);
	(0, import_react.useEffect)(() => {
		if (!running || !result) return;
		const id = window.setInterval(() => {
			useStudio.setState((s) => {
				if (!s.result) return { running: false };
				const next = Math.min(s.playIndex + 1, s.result.series.length - 1);
				return {
					playIndex: next,
					running: next < s.result.series.length - 1
				};
			});
		}, 40);
		return () => window.clearInterval(id);
	}, [running, result]);
	function run() {
		const next = runBreachSimulation(inputs);
		setResult(next);
		setPlayIndex(0);
		setRunning(true);
	}
	function exportProject() {
		downloadText(`${slug(inputs.projectName)}.json`, JSON.stringify(inputs, null, 2), "application/json");
	}
	function exportCsv() {
		if (!result) return;
		downloadText(`${slug(inputs.projectName)}-hydrograph.csv`, resultToCsv(result), "text/csv");
	}
	function onImport(file) {
		const reader = new FileReader();
		reader.onload = () => {
			try {
				const parsed = JSON.parse(String(reader.result));
				setInputs({
					...inputs,
					...parsed
				});
			} catch {}
		};
		reader.readAsText(file);
	}
	return /* @__PURE__ */ (0, import_jsx_runtime.jsx)(AppShell, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
		className: "flex flex-col gap-6",
		children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "flex flex-col gap-3 md:flex-row md:items-end md:justify-between",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", { children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "text-xs font-medium uppercase tracking-[0.16em] text-accent",
						children: "Formation engine"
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("h1", {
						className: "font-display text-3xl font-medium tracking-tight",
						children: inputs.projectName
					}),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
						className: "mt-1 max-w-xl text-sm text-muted-foreground",
						children: "Physically based breach growth — weir / orifice hydraulics, Wan–Fell erosion, falling reservoir. Not an empirical peak-flow formula."
					})
				] }), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex flex-wrap gap-2",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
							onClick: run,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Play, { className: "size-4" }), "Run formation"]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
							variant: "secondary",
							onClick: exportProject,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Download, { className: "size-4" }), "Export project"]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
							variant: "outline",
							onClick: () => fileRef.current?.click(),
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Upload, { className: "size-4" }), "Import"]
						}),
						/* @__PURE__ */ (0, import_jsx_runtime.jsx)("input", {
							ref: fileRef,
							type: "file",
							accept: "application/json",
							className: "hidden",
							onChange: (e) => {
								const f = e.target.files?.[0];
								if (f) onImport(f);
								e.target.value = "";
							}
						})
					]
				})]
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
				className: "flex flex-wrap gap-2",
				children: EXAMPLES.map((ex) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
					type: "button",
					onClick: () => setInputs(ex.inputs),
					className: "rounded-full border border-border bg-card px-3 py-1.5 text-left text-xs text-muted-foreground hover:border-accent hover:text-foreground",
					children: ex.title
				}, ex.id))
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
				className: "grid gap-6 xl:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]",
				children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, {
					className: "h-fit",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardHeader, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardTitle, { children: "Inputs" }) }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardContent, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(ParamForm, {}) })]
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
					className: "flex flex-col gap-4",
					children: [
						/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Card, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CardHeader, {
							className: "flex-row items-center justify-between",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(CardTitle, { children: "Cross-section" }), step && /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Badge, {
								tone: "accent",
								children: step.stage
							})]
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(CardContent, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(DamSchematic, {
							inputs,
							step
						}), result && result.series.length > 1 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
							className: "mt-4 flex flex-col gap-2",
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Slider, {
								min: 0,
								max: result.series.length - 1,
								step: 1,
								value: [playIndex],
								onValueChange: (v) => {
									setRunning(false);
									setPlayIndex(v[0] ?? 0);
								}
							}), /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "flex items-center justify-between text-xs text-muted-foreground",
								children: [
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [((step?.t ?? 0) / 60).toFixed(1), " min"] }),
									/* @__PURE__ */ (0, import_jsx_runtime.jsx)("button", {
										type: "button",
										className: "text-accent",
										onClick: () => setRunning(!running),
										children: running ? "Pause" : "Play"
									}),
									/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("span", { children: [
										"Q = ",
										formatNumber(step?.Q ?? 0, 2),
										" m³/s"
									] })
								]
							})]
						})] })] }),
						stats && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "grid grid-cols-2 gap-2 sm:grid-cols-3",
							children: stats.map((s) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
								className: "rounded-lg border border-border bg-card px-3 py-3",
								children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "text-[11px] uppercase tracking-wide text-muted-foreground",
									children: s.k
								}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", {
									className: "font-mono text-sm tabular-nums",
									children: s.v
								})]
							}, s.k))
						}),
						result && result.warnings.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", {
							className: "rounded-lg border border-border bg-card px-4 py-3 text-sm text-warn",
							children: result.warnings.map((w) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("p", { children: w }, w))
						}),
						result && result.series.length > 0 && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(ResultCharts, {
							result,
							playIndex
						}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("div", { children: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(Button, {
							variant: "outline",
							size: "sm",
							onClick: exportCsv,
							children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Download, { className: "size-4" }), "Export hydrograph CSV"]
						}) })] })
					]
				})]
			})
		]
	}) });
}
function slug(name) {
	return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "project";
}
//#endregion
export { SimulatePage as component };
