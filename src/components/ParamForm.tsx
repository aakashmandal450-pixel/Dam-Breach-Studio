import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type FocusEvent,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { Info } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useStudio } from "@/store/studio";
import type { StudioInputs } from "@/lib/breach/types";
import { EXAMPLES } from "@/lib/breach/examples";
import { headcutDefaultsForStructure } from "@/lib/breach/headcutDefaults";
import { erosionDefaultsForStructure } from "@/lib/breach/erosionDefaults";
import { cn } from "@/lib/utils";
import { LakeVolumePanel } from "@/components/LakeVolumePanel";
import { InflowSeriesPanel } from "@/components/InflowSeriesPanel";
import { MorainePanel } from "@/components/MorainePanel";

type InputTab = "project" | "geometry" | "reservoir" | "discharge" | "soil" | "moraine" | "headcut" | "hydraulics" | "numerical";

const TABS: { id: InputTab; label: string }[] = [
  { id: "project", label: "Project" },
  { id: "geometry", label: "Geometry" },
  { id: "reservoir", label: "Reservoir" },
  { id: "discharge", label: "Discharge" },
  { id: "soil", label: "Dam properties" },
  { id: "moraine", label: "GLOF / ice" },
  { id: "headcut", label: "Headcut" },
  { id: "hydraulics", label: "Hydraulics" },
  { id: "numerical", label: "Numerical" },
];

export function ParamForm() {
  const { inputs, setInput, setInputs } = useStudio();
  const [tab, setTab] = useState<InputTab>("project");
  const [areaUnit, setAreaUnit] = useState<"ha" | "m2">("ha");

  return (
    <div className="flex flex-col gap-3">
      <div
        role="tablist"
        aria-label="Input groups"
        className="flex flex-wrap gap-0.5 rounded-md border border-border bg-muted/40 p-0.5"
      >
        {TABS.map((t) => {
          const isGlofOff = t.id === "moraine" && inputs.glofIceEnabled === false;
          return (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={tab === t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                "rounded px-2 py-1 text-[11px] font-medium transition-colors",
                tab === t.id
                  ? "bg-card text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
                isGlofOff && "opacity-50",
              )}
              title={isGlofOff ? "GLOF / ice is off — open tab to re-enable" : undefined}
            >
              {t.label}
              {isGlofOff ? " (off)" : ""}
            </button>
          );
        })}
      </div>

      <div role="tabpanel" className="min-h-[10rem]">
        {tab === "project" && (
          <FieldGrid>
            <TextField
              id="projectName"
              label="Project name"
              value={inputs.projectName}
              onChange={(v) => setInput("projectName", v)}
            />
            <div className="flex flex-col gap-1">
              <Label htmlFor="mode" className="text-xs">Failure mode</Label>
              <select
                id="mode"
                className="h-8 rounded-md border border-border bg-input px-2 text-sm"
                value={inputs.mode}
                onChange={(e) => setInput("mode", e.target.value as StudioInputs["mode"])}
              >
                <option value="overtopping">Overtopping</option>
                <option value="piping">Piping / concentrated leak</option>
              </select>
            </div>
            <div className="flex flex-col gap-1 sm:col-span-2">
              <Label htmlFor="analysis-scope" className="text-xs">Analysis scope</Label>
              <select
                id="analysis-scope"
                className="h-8 rounded-md border border-border bg-input px-2 text-sm"
                value={inputs.glofIceEnabled !== false ? "glof" : "simple"}
                onChange={(e) => {
                  const simple = e.target.value === "simple";
                  setInput("glofIceEnabled", !simple);
                  if (simple) {
                    // Ordinary earthfill: no glacial-lake volume formulas, no moraine / ice-cored structure
                    setInput("lakeVolumeFormula", "manual");
                    if (
                      inputs.damStructure === "moraine" ||
                      inputs.damStructure === "ice_cored_moraine"
                    ) {
                      setInput("damStructure", "homogeneous");
                    }
                  }
                }}
              >
                <option value="simple">Simple dam breach (omit GLOF / ice)</option>
                <option value="glof">Include GLOF / ice screening</option>
              </select>
              <p className="text-[10px] text-muted-foreground leading-relaxed">
                <strong>Simple</strong> — homogeneous / zoned only; glacial-lake volume formulas and GLOF / ice are off.
                <strong> GLOF / ice</strong> — enables the GLOF tab, moraine / ice-cored structures, and lake-volume formulas.
              </p>
            </div>
            <div className="flex flex-col gap-1 sm:col-span-2">
              <Label htmlFor="example-preset" className="text-xs">Load example case</Label>
              <select
                id="example-preset"
                className="h-8 rounded-md border border-border bg-input px-2 text-sm"
                defaultValue="custom"
                onChange={(e) => {
                  const id = e.target.value;
                  if (id === "custom") return;
                  const ex = EXAMPLES.find((x) => x.id === id);
                  if (ex) setInputs({ ...inputs, ...ex.inputs });
                }}
              >
                <option value="custom">Custom (current values)</option>
                {EXAMPLES.map((ex) => (
                  <option key={ex.id} value={ex.id}>{ex.title}</option>
                ))}
              </select>
            </div>
          </FieldGrid>
        )}

        {tab === "geometry" && (
          <FieldGrid>
            <Num id="crestElev" label="Crest elevation" symbol="Crest" unit="m" hint="Top of dam crest elevation. Typical range: project-specific (a few m to >100 m)." k="crestElev" />
            <Num id="baseElev" label="Base elevation" symbol="BL" unit="m" hint="Foundation / breach invert floor. Usually 0 or surveyed foundation elevation." k="baseElev" />
            <Num id="crestWidth" label="Crest width" symbol="C" unit="m" hint="Horizontal crest thickness. Headcut migrates through C. Typical earthfill: 3–15 m." k="crestWidth" />
            <Num id="crestLength" label="Crest length" symbol="L_crest" unit="m" hint="Valley-crossing length of the crest. Caps final breach base width Wb. Project-specific." k="crestLength" />
            <Num id="zUp" label="Upstream face slope" symbol="Z₁" unit="H:1V" hint="Horizontal:vertical of the upstream face. Typical: 2–4. Steeper faces concentrate shear." k="zUp" />
            <Num id="zDown" label="Downstream face slope" symbol="Z₂" unit="H:1V" hint="Downstream face slope. Typical: 2–3. Steeper faces increase erosive shear on the breach." k="zDown" />
            <Num id="coreLength" label="Pipe / core length" symbol="L" unit="m" hint="Seepage path length used in pipe-wall shear τ ≈ ρg R H /(2L). Usually ≈ core thickness (5–50 m)." k="coreLength" />
          </FieldGrid>
        )}

        {tab === "reservoir" && (
          <div className="flex flex-col gap-3">
            <FieldGrid>
              <Num id="initialWL" label="Initial water level" symbol="WL" unit="m" hint="Pool elevation at t = 0. Must be ≥ base elevation. Freeboard f = crest − WL." k="initialWL" />
              <Num id="volumeM3" label="Storage at that level" symbol="V₀" unit="m³" hint="Reservoir volume at the initial WL. Calibrates V(y) = V₀ (y/y₀)^m. Can be filled from a glacial-lake formula below when GLOF scope is on." k="volumeM3" step={1} />
              <AreaField areaUnit={areaUnit} setAreaUnit={setAreaUnit} />
              <Num id="storageExponent" label="Storage exponent" symbol="m" unit="—" hint="Power in V(y) = V₀ (y/y₀)^m. Typical natural reservoirs: 2–3. Higher m → more volume near the top." k="storageExponent" />
            </FieldGrid>
            {inputs.glofIceEnabled !== false ? (
              <LakeVolumePanel />
            ) : (
              <p className="rounded-md border border-dashed border-border bg-muted/20 px-3 py-2 text-[11px] text-muted-foreground">
                Glacial-lake volume formulas are off (Analysis scope = Simple). Enter V₀ manually above, or switch scope to{" "}
                <strong className="text-foreground">Include GLOF / ice screening</strong> to use empirical lake V(A) formulas.
              </p>
            )}
          </div>
        )}

        {tab === "discharge" && (
          <div className="flex flex-col gap-3">
            <FieldGrid>
              <Num id="inflowM3s" label="Constant inflow" symbol="Qin" unit="m³/s" hint="Used when the series is off or empty. Range: ≥ 0." k="inflowM3s" />
              <Num id="spillwayQ" label="Spillway discharge" symbol="Qspill" unit="m³/s" hint="Constant additional outlet (optional). Range: ≥ 0." k="spillwayQ" />
            </FieldGrid>
            <InflowSeriesPanel />
          </div>
        )}

        {tab === "soil" && (
          <FieldGrid>
            <div className="flex flex-col gap-1 sm:col-span-2">
              <Label htmlFor="damStructure" className="text-xs">Dam structure</Label>
              <select
                id="damStructure"
                className="h-8 rounded-md border border-border bg-input px-2 text-sm"
                value={inputs.damStructure ?? "homogeneous"}
                onChange={(e) => {
                  const v = e.target.value as StudioInputs["damStructure"];
                  setInput("damStructure", v);
                  if (v === "moraine") {
                    setInput("erosionIndexI", 2.4);
                    setInput("tauC", 8);
                    setInput("phiDeg", 32);
                    setInput("zb", 0.7);
                    setInput("manningN", 0.038);
                    setInput("zUp", 2.2);
                    setInput("zDown", 2.0);
                  } else if (v === "ice_cored_moraine") {
                    setInput("erosionIndexI", 1.8);
                    setInput("tauC", 5);
                    setInput("phiDeg", 30);
                    setInput("zb", 0.8);
                    setInput("manningN", 0.04);
                    setInput("zUp", 2.0);
                    setInput("zDown", 1.8);
                  } else if (v === "homogeneous") {
                    setInput("erosionIndexI", 3.2);
                    setInput("tauC", 8);
                    setInput("zb", 0.5);
                    setInput("manningN", 0.03);
                  }
                  const hd = headcutDefaultsForStructure(v);
                  setInput("headcutEnabled", hd.headcutEnabled);
                  setInput("headcutInitDepth", hd.headcutInitDepth);
                  setInput("headcutAdvanceFactor", hd.headcutAdvanceFactor);
                  // Open-breach erosion closure: granular moraine/rockfill → transport-capacity;
                  // engineered homogeneous/zoned fills stay on detachment-limited excess-shear.
                  const ed = erosionDefaultsForStructure(v);
                  setInput("erosionModel", ed.erosionModel);
                  setInput("grainD50_m", ed.grainD50_m);
                  setInput("grainD90D30Ratio", ed.grainD90D30Ratio);
                }}
              >
                <option value="homogeneous">Homogeneous fill (one material)</option>
                <option value="zoned">Zoned (core + shell)</option>
                <option value="moraine" disabled={inputs.glofIceEnabled === false}>
                  Moraine dam (debris)
                  {inputs.glofIceEnabled === false ? " — deactivated (Simple scope)" : ""}
                </option>
                <option value="ice_cored_moraine" disabled={inputs.glofIceEnabled === false}>
                  Ice-cored moraine (thaw screening)
                  {inputs.glofIceEnabled === false ? " — deactivated (Simple scope)" : ""}
                </option>
              </select>
              <p className="text-[10px] text-muted-foreground leading-relaxed">
                Structure sets material and headcut defaults (editable).{" "}
                {inputs.glofIceEnabled === false
                  ? "Moraine / ice-cored remain visible but are deactivated under Simple scope — switch to Include GLOF / ice to use them."
                  : "Moraine / ice-cored are screening proxies — see GLOF / ice tab and Theory."}
              </p>
            </div>

            <Num id="erosionIndexI" label="Erosion rate index" symbol="I" unit="—" hint="Wan & Fell index. Ce = 10^(−I). I = 0–2 very rapid; 2–3 rapid; 3–4 moderate; 4–5 slow; 5–6+ very slow. Dominates growth rate." k="erosionIndexI" step={0.1} />
            <Num id="tauC" label="Critical shear stress" symbol="τc" unit="Pa" hint="No erosion below this wall/bed shear. Typical: 0–20 Pa for erodible fills; higher for resistant clays. From HET/JET preferred." k="tauC" />
            <Num id="rhoD" label="Dry bulk density" symbol="ρd" unit="kg/m³" hint="Converts Ce into a volume erosion rate. Typical compacted fill: 1400–2000 kg/m³." k="rhoD" step={10} />
            <Num id="phiDeg" label="Friction angle" symbol="φ" unit="°" hint="Sets residual side-slope floor: Zb ≥ cot(φ). Typical: 25–40° for embankment fills." k="phiDeg" />
            <Num id="manningN" label="Manning roughness" symbol="n" unit="—" hint="Roughness of the breach channel. Typical earth: 0.025–0.04." k="manningN" step={0.005} />
            <Num id="zb" label="Breach side slope" symbol="Zb" unit="H:1V" hint="Trapezoid batter of the open breach. Cohesionless ≈ 0.5–1; resistant ≈ 0.25–0.5." k="zb" step={0.05} />
            <Num id="sideErosionFactor" label="Side erosion factor" symbol="fs" unit="—" hint="Widening relative to deepening (≈ 1–2). Higher → faster lateral growth." k="sideErosionFactor" step={0.1} />
          
            {(inputs.damStructure ?? "homogeneous") === "zoned" && (
              <>
                <Num id="shellErosionIndexI" label="Shell erosion index" symbol="I,shell" unit="—" hint="Overtopping face / shell. Often more erodible (lower I) than the core." k="shellErosionIndexI" step={0.1} />
                <Num id="shellTauC" label="Shell critical shear" symbol="τc,shell" unit="Pa" hint="Critical shear for the shell material under overtopping flow." k="shellTauC" />
                <div className="sm:col-span-2">
                  <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Core geometry</p>
                  <p className="text-[10px] text-muted-foreground">
                    Drawn on the cross-section (ct / Zc / cb / Hc). Core height is set as a fraction of dam height, so it
                    always scales proportionally with the dam — edit crest or base elevation and the core resizes with it.
                  </p>
                </div>
                <Num id="coreTopWidth" label="Core top width" symbol="ct" unit="m" hint="Horizontal width across the top of the core. Typical: 1.5–5 m depending on dam size." k="coreTopWidth" step={0.1} />
                <Num id="coreSideSlope" label="Core side slope" symbol="Zc" unit="H:1V" hint="Batter of the core faces. Typical compacted clay core: 0.3–0.7 H:1V." k="coreSideSlope" step={0.05} />
                <Num id="coreHeightFraction" label="Core height fraction" symbol="Hc/Hb" unit="—" hint="Core height as a fraction of total dam height Hb (0–1). Typical: 0.7–0.95 — most cores run nearly the full dam height." k="coreHeightFraction" step={0.05} />
              </>
            )}

            <div className="sm:col-span-2 mt-1 border-t border-border pt-2">
              <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Open-breach erosion closure</p>
              <p className="text-[10px] text-muted-foreground leading-relaxed">
                Applies to open-breach deepening / widening only — piping and the headcut face always use excess-shear.
                See Theory → Erosion closure.
              </p>
            </div>

            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-1">
                <Label htmlFor="erosionModel" className="text-xs leading-tight">Erosion law</Label>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button type="button" className="text-muted-foreground" aria-label="About erosion law">
                      <Info className="size-3" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs text-xs leading-relaxed">
                    Excess-shear (default) is detachment-limited ε = kd(τ−τc)^n for cohesive fills.
                    Transport-capacity is Meyer-Peter–Müller + Smart (1984) → Exner for cohesionless
                    granular / moraine / rockfill (NWS BREACH lineage). Do not use transport-capacity for fine cohesive soils.
                  </TooltipContent>
                </Tooltip>
              </div>
              <select
                id="erosionModel"
                className="h-8 rounded-md border border-border bg-input px-2 text-sm"
                value={inputs.erosionModel ?? "excess_shear"}
                onChange={(e) => setInput("erosionModel", e.target.value as StudioInputs["erosionModel"])}
              >
                <option value="excess_shear">Excess-shear (detachment-limited)</option>
                <option value="transport_capacity">Transport-capacity (MPM / Smart → Exner)</option>
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-1">
                <Label htmlFor="kdMode" className="text-xs leading-tight">Erodibility kd source</Label>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button type="button" className="text-muted-foreground" aria-label="About kd source">
                      <Info className="size-3" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs text-xs leading-relaxed">
                    index (default): kd = 10^(−I)/ρd (legacy). hanson: kd = 2×10⁻⁷·τc^(−0.5) from Hanson &amp;
                    Simon (2001) JET regression, forces n = 1. direct: enter a measured JET kd in cm³/(N·s).
                    Applies wherever excess-shear is active.
                  </TooltipContent>
                </Tooltip>
              </div>
              <select
                id="kdMode"
                className="h-8 rounded-md border border-border bg-input px-2 text-sm"
                value={inputs.kdMode ?? "index"}
                onChange={(e) => setInput("kdMode", e.target.value as StudioInputs["kdMode"])}
              >
                <option value="index">Index — kd = 10^(−I)/ρd (legacy)</option>
                <option value="hanson">Hanson &amp; Simon JET — kd = 2e−7·τc^(−0.5)</option>
                <option value="direct">Direct — measured JET kd</option>
              </select>
            </div>

            {(inputs.kdMode ?? "index") === "direct" && (
              <Num id="kdDirect" label="Measured JET kd" symbol="kd" unit="cm³/(N·s)" hint="Site-measured detachment-rate coefficient from a Jet Erosion Test, in cm³/(N·s). Converted to SI ×10⁻⁶ internally. Typical: 0.1–10." k="kdDirect" step={0.01} />
            )}

            {(inputs.erosionModel ?? "excess_shear") === "transport_capacity" && (
              <>
                <Num id="grainD50_m" label="Median grain size" symbol="D₅₀" unit="m" hint="Median bed grain diameter. Moraine matrix ≈ 0.02–0.04 m; rockfill coarser. Transport-capacity only — Shields stress θ = τ/((s−1)ρg·D₅₀)." k="grainD50_m" step={0.005} />
                <Num id="grainD90D30Ratio" label="Gradation ratio" symbol="D₉₀/D₃₀" unit="—" hint="Smart (1984) gradation factor (D₉₀/D₃₀)^0.2. Well-graded moraine debris ≈ 8–12. Transport-capacity only." k="grainD90D30Ratio" step={0.5} />
                <Num id="grainDensity" label="Grain density" symbol="ρs" unit="kg/m³" hint="Sediment particle density. Default 2650 (quartz). Transport-capacity only." k="grainDensity" step={10} />
                <Num id="criticalShields" label="Critical Shields" symbol="θc" unit="—" hint="Critical Shields parameter for incipient motion. Default 0.047 (MPM); lower on steep / fine beds. Transport-capacity only." k="criticalShields" step={0.001} />
                <Num id="mpmCoefficient" label="MPM coefficient" symbol="Kt" unit="—" hint="Meyer-Peter–Müller transport coefficient. Default 8 (classic); Wong &amp; Parker (2006) recalibrate ≈3.97. Transport-capacity only." k="mpmCoefficient" step={0.5} />
                <Num id="porosity" label="Bed porosity" symbol="p" unit="—" hint="Bed porosity in the Exner conversion ε = qs/((1−p)·Lreach). Typical 0.25–0.45. Transport-capacity only." k="porosity" step={0.01} />
              </>
            )}

            </FieldGrid>
        )}

        {tab === "moraine" && (
          <MorainePanel />
        )}

        {tab === "headcut" && (
          <FieldGrid>
            <div className="flex flex-col gap-1 sm:col-span-2">
              <Label htmlFor="headcutEnabled" className="text-xs">Headcut module</Label>
              <select
                id="headcutEnabled"
                className="h-8 rounded-md border border-border bg-input px-2 text-sm"
                value={inputs.headcutEnabled ? "on" : "off"}
                onChange={(e) => setInput("headcutEnabled", e.target.value === "on")}
              >
                <option value="on">On — migrate scarp through crest width C</option>
                <option value="off">Off — pure surface erosion (legacy)</option>
              </select>
            </div>
            <Num id="headcutInitDepth" label="Initiation head" symbol="hinit" unit="m" hint="Overtopping depth on the crest before the discrete headcut is tracked. Defaults depend on dam structure (see Theory → Headcut). Typical 0.03–0.06 m." k="headcutInitDepth" step={0.01} />
            <Num id="headcutAdvanceFactor" label="Advance factor" symbol="fh" unit="—" hint="How fast the scarp migrates through crest width C. Moraine defaults ~4; zoned clay ~8; homogeneous ~6. Range 3–15. Deepening is limited until breakthrough. Used by the hydrostatic law only." k="headcutAdvanceFactor" step={0.5} />

            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-1">
                <Label htmlFor="headcutLaw" className="text-xs leading-tight">Migration law</Label>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button type="button" className="text-muted-foreground" aria-label="About headcut migration law">
                      <Info className="size-3" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-xs text-xs leading-relaxed">
                    Hydrostatic (default, legacy): dxh/dt = fh·ε(τface), τface ≈ ρg·hface. Energy: WinDAM /
                    USDA-SITES dissipation dX/dt = C·(q·H)^(1/3), q = unit overfall discharge, H = drop height.
                    Only affects overtopping; piping is unchanged.
                  </TooltipContent>
                </Tooltip>
              </div>
              <select
                id="headcutLaw"
                className="h-8 rounded-md border border-border bg-input px-2 text-sm"
                value={inputs.headcutLaw ?? "hydrostatic"}
                onChange={(e) => setInput("headcutLaw", e.target.value as StudioInputs["headcutLaw"])}
              >
                <option value="hydrostatic">Hydrostatic — dxh/dt = fh·ε(τface) (legacy)</option>
                <option value="energy">WinDAM energy — dX/dt = C·(q·H)^(1/3)</option>
              </select>
            </div>

            {(inputs.headcutLaw ?? "hydrostatic") === "energy" && (
              <Num id="headcutEnergyCoeff" label="Energy coefficient" symbol="C" unit="—" hint="WinDAM/SITES headcut erodibility in dX/dt = C·(q·H)^(1/3). Higher = faster scarp migration. Tie to the same material as kd; typical screening 0.5–2. Used by the energy law only." k="headcutEnergyCoeff" step={0.1} />
            )}

            <div className="sm:col-span-2 mt-1 border-t border-border pt-2">
              <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Deepening gate</p>
              <p className="text-[10px] text-muted-foreground leading-relaxed">
                While the scarp migrates through crest width C, invert lowering is throttled. Raise the fraction
                toward 1 to let a wide-crest moraine breach deepen closer to the full rate. See Theory → Headcut.
              </p>
            </div>
            <Num id="headcutGateDeepenFraction" label="Gate fraction" symbol="gf" unit="—" hint="Fraction of the excess-shear rate allowed to lower the invert while the headcut is still inside the crest. Legacy 0.25. Range 0.05–1." k="headcutGateDeepenFraction" step={0.05} />
            <Num id="headcutGateDeepenCap" label="Gate cap" symbol="—" unit="×Hb" hint="Per-step cap on gated deepening as a fraction of dam height Hb. Legacy 0.015. Range 0.005–0.1." k="headcutGateDeepenCap" step={0.005} />
            {inputs.mode === "overtopping" && (
              <>
                <div className="sm:col-span-2 mt-1 border-t border-border pt-2">
                  <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Wave-overtopping forcing (GLOF trigger)</p>
                  <p className="text-[10px] text-muted-foreground leading-relaxed">
                    Injects a transient displacement-wave overtopping pulse (peak depth d₀ over duration tO, from
                    Impulse → run-up) as erosive head only — not reservoir volume. Lets a lake sitting at/near its
                    rim (little or no freeboard) initiate a breach the standing head alone cannot. Off = legacy.
                    See Theory → Wave forcing.
                  </p>
                </div>
                <div className="flex flex-col gap-1 sm:col-span-2">
                  <Label htmlFor="waveForcingEnabled" className="text-xs">Wave forcing</Label>
                  <select
                    id="waveForcingEnabled"
                    className="h-8 rounded-md border border-border bg-input px-2 text-sm"
                    value={inputs.waveForcingEnabled ? "on" : "off"}
                    onChange={(e) => setInput("waveForcingEnabled", e.target.value === "on")}
                  >
                    <option value="off">Off — hydrostatic head only (legacy)</option>
                    <option value="on">On — add wave-overtopping pulse train</option>
                  </select>
                </div>
                {inputs.waveForcingEnabled && (
                  <>
                    <Num id="waveOvertopDepth" label="Peak overtop depth" symbol="d₀" unit="m" hint="Peak wave-overtopping depth on the crest, from the Impulse module's run-up result (RunupResult.d0)." k="waveOvertopDepth" step={0.1} />
                    <Num id="waveOvertopDuration" label="Overtop duration" symbol="tO" unit="s" hint="Duration of a single overtopping pulse, from run-up (RunupResult.tO)." k="waveOvertopDuration" step={1} />
                    <Num id="waveOvertopCount" label="Pulse count" symbol="N" unit="—" hint="Number of successive wave pulses (a GLOF wave train). Default 1; range 1–20." k="waveOvertopCount" step={1} />
                    <Num id="waveOvertopPeriod" label="Pulse spacing" symbol="T" unit="s" hint="Time between successive pulse starts. 0 → use the overtop duration as the spacing." k="waveOvertopPeriod" step={1} />
                  </>
                )}
              </>
            )}
          </FieldGrid>
        )}

        {tab === "hydraulics" && (
          <FieldGrid>
            <Num id="Cw" label="Weir coefficient" symbol="Cw" unit="m⁰·⁵/s" hint="Broad-crested trapezoidal weir. Default 1.7 (metric). Typical range: 1.4–1.8." k="Cw" step={0.05} />
            <Num id="CdOrifice" label="Orifice coefficient" symbol="Cd" unit="—" hint="Pipe discharge coefficient for piping stage. Typical: 0.5–0.7." k="CdOrifice" step={0.05} />
            <Num id="initialNotchWidth" label="Initial notch width" symbol="Wb0" unit="m" hint="Starter cut width for overtopping. Typical: 0.5–3 m." k="initialNotchWidth" />
            <Num id="initialPipeRadius" label="Initial pipe radius" symbol="Rd" unit="m" hint="Detected leak size at t = 0. Typical detection range: 0.01–0.25 m." k="initialPipeRadius" step={0.01} />
            <Num id="pipeInvert" label="Pipe invert elevation" symbol="zpipe" unit="m" hint="Elevation of the concentrated leak axis. Must lie between base and crest." k="pipeInvert" />
            <Num id="collapseRatio" label="Roof collapse ratio" symbol="κ" unit="—" hint="Roof fails when 2R ≥ κ × cover thickness. Typical: 0.4–0.7." k="collapseRatio" step={0.05} />
          </FieldGrid>
        )}

        {tab === "numerical" && (
          <FieldGrid>
            <div className="flex flex-col gap-1">
              <Label className="text-xs">Time step value</Label>
              <div className="flex gap-1">
                <UnitNumberField
                  step={0.1}
                  className="h-8 flex-1 text-sm"
                  value={displayFromStored(inputs.dt, inputs.dtUnit ?? "s")}
                  onCommit={(n) => {
                    const unit = inputs.dtUnit ?? "s";
                    setInput("dt", storedSeconds(n, unit));
                  }}
                />
                <select
                  className="h-8 rounded-md border border-border bg-input px-1.5 font-mono text-xs"
                  value={inputs.dtUnit ?? "s"}
                  onChange={(e) => {
                    const unit = e.target.value as "s" | "min" | "h";
                    // keep physical duration; only change unit label
                    setInput("dtUnit", unit);
                  }}
                  aria-label="Time step unit"
                >
                  <option value="s">s</option>
                  <option value="min">min</option>
                  <option value="h">h</option>
                </select>
              </div>
              <p className="text-[10px] text-muted-foreground">
                Stored as {inputs.dt} s for the engine. Prefer 1–5 s for rapid soils.
              </p>
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-xs">Max duration value</Label>
              <div className="flex gap-1">
                <UnitNumberField
                  step={0.1}
                  className="h-8 flex-1 text-sm"
                  value={displayFromStoredHours(inputs.tMaxHours, inputs.tMaxUnit ?? "h")}
                  onCommit={(n) => {
                    const unit = inputs.tMaxUnit ?? "h";
                    setInput("tMaxHours", storedHours(n, unit));
                  }}
                />
                <select
                  className="h-8 rounded-md border border-border bg-input px-1.5 font-mono text-xs"
                  value={inputs.tMaxUnit ?? "h"}
                  onChange={(e) => setInput("tMaxUnit", e.target.value as "s" | "min" | "h")}
                  aria-label="Max duration unit"
                >
                  <option value="s">s</option>
                  <option value="min">min</option>
                  <option value="h">h</option>
                </select>
              </div>
              <p className="text-[10px] text-muted-foreground">
                Stored as {inputs.tMaxHours} h for the engine.
              </p>
            </div>
            <Num
              id="uncertaintyDeltaI"
              label="Uncertainty ±I"
              symbol="ΔI"
              unit="—"
              hint="Half-width for Qp band on Results: runs at I−ΔI, I, I+ΔI. Typical 0.3–0.5."
              k="uncertaintyDeltaI"
              step={0.1}
            />
          </FieldGrid>
        )}
      </div>
    </div>
  );
}

function FieldGrid({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">{children}</div>;
}

function Num({
  id,
  label,
  symbol,
  unit,
  hint,
  k,
  step = 0.1,
}: {
  id: string;
  label: string;
  symbol?: string;
  unit: string;
  hint: string;
  k: keyof StudioInputs;
  step?: number;
}) {
  const { inputs, setInput } = useStudio();
  const value = inputs[k];
  const numericField = useNumericField(typeof value === "number" ? value : 0, (n) => setInput(k, n as never));
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1">
        <Label htmlFor={id} className="text-xs leading-tight">
          {label}
          {symbol ? <span className="ml-1 font-mono text-[10px] text-muted-foreground">({symbol})</span> : null}
        </Label>
        <Tooltip>
          <TooltipTrigger asChild>
            <button type="button" className="text-muted-foreground" aria-label={`About ${label}`}>
              <Info className="size-3" />
            </button>
          </TooltipTrigger>
          <TooltipContent className="max-w-xs text-xs leading-relaxed">{hint}</TooltipContent>
        </Tooltip>
      </div>
      <div className="relative">
        <Input id={id} step={step} className="h-8 pr-12 text-sm" {...numericField} />
        <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 font-mono text-[10px] text-muted-foreground">
          {unit}
        </span>
      </div>
    </div>
  );
}

/**
 * Shared numeric-input behaviour used by every number field in this form.
 *
 * Fixes the "01.58" leading-zero glitch: a plain controlled `type="number"`
 * input bound straight to a numeric store value can desync from what's on
 * screen, because some browsers skip re-rendering the DOM text when the
 * *numeric* value hasn't changed (1.58 === 1.58) even though the *string*
 * has ("01.58" !== "1.58"). Using `type="text"` with our own display state
 * sidesteps that entirely — we always own what's shown.
 *
 * Also makes Enter behave like Tab (advance to the next field), and only
 * re-syncs the displayed text from the store while the field is unfocused,
 * so programmatic updates (e.g. a dam-structure preset autofilling values)
 * still show up without fighting whatever the user is mid-typing elsewhere.
 */
function useNumericField(value: number, onCommit: (n: number) => void) {
  const [text, setText] = useState<string>(() => formatNum(value));
  const focusedRef = useRef(false);

  useEffect(() => {
    if (!focusedRef.current) setText(formatNum(value));
  }, [value]);

  return {
    value: text,
    type: "text" as const,
    inputMode: "decimal" as const,
    onFocus: () => {
      focusedRef.current = true;
    },
    onChange: (e: ChangeEvent<HTMLInputElement>) => {
      const raw = e.target.value;
      // Allow free typing of intermediate states ("", "-", "1.", "-0.")
      // without forcing a reformat that would fight the user's cursor.
      if (raw !== "" && !/^-?\d*\.?\d*$/.test(raw)) return;
      setText(raw);
      if (raw !== "" && raw !== "-" && !raw.endsWith(".")) {
        const n = Number(raw);
        if (Number.isFinite(n)) onCommit(n);
      }
    },
    onBlur: (e: FocusEvent<HTMLInputElement>) => {
      focusedRef.current = false;
      const n = Number(e.target.value);
      const finalVal = Number.isFinite(n) ? n : 0;
      onCommit(finalVal);
      setText(formatNum(finalVal));
    },
    onKeyDown: (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const target = e.currentTarget;
        target.blur();
        focusNextField(target);
      }
    },
  };
}

function formatNum(v: number): string {
  return Number.isFinite(v) ? String(v) : "0";
}

/** Thin wrapper so the numeric-field hook can be used for one-off inline inputs. */
function UnitNumberField({
  step,
  className,
  value,
  onCommit,
}: {
  step?: number;
  className?: string;
  value: number;
  onCommit: (n: number) => void;
}) {
  const numericField = useNumericField(value, onCommit);
  return <Input step={step} className={className} {...numericField} />;
}

/** Enter-to-advance: move focus to the next focusable field, mirroring Tab. */
function focusNextField(current: HTMLElement) {
  const focusable = Array.from(
    document.querySelectorAll<HTMLElement>(
      'input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  ).filter((el) => el.tabIndex !== -1 && el.offsetParent !== null);
  const idx = focusable.indexOf(current);
  if (idx > -1 && idx < focusable.length - 1) {
    focusable[idx + 1].focus();
  }
}

function AreaField({
  areaUnit,
  setAreaUnit,
}: {
  areaUnit: "ha" | "m2";
  setAreaUnit: (u: "ha" | "m2") => void;
}) {
  const { inputs, setInput } = useStudio();
  const display =
    areaUnit === "ha" ? inputs.surfaceAreaHa : inputs.surfaceAreaHa * 10_000;
  const numericField = useNumericField(Number.isFinite(display) ? display : 0, (v) => {
    const ha = areaUnit === "ha" ? v : v / 10_000;
    setInput("surfaceAreaHa", ha);
  });

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1">
        <Label htmlFor="surfaceArea" className="text-xs leading-tight">
          Surface area <span className="font-mono text-[10px] text-muted-foreground">(A)</span>
        </Label>
        <Tooltip>
          <TooltipTrigger asChild>
            <button type="button" className="text-muted-foreground" aria-label="About surface area">
              <Info className="size-3" />
            </button>
          </TooltipTrigger>
          <TooltipContent className="max-w-xs text-xs leading-relaxed">
            Reservoir / lake surface area at the initial water level. Used by empirical glacial-lake
            V(A) formulas and for context. Switch between hectares (ha) and square metres (m²).
            1 ha = 10 000 m². Typical small ponds: &lt; 10 ha; glacial lakes: often 1–100+ ha.
          </TooltipContent>
        </Tooltip>
      </div>
      <div className="relative flex">
        <Input
          id="surfaceArea"
          step={areaUnit === "ha" ? 0.01 : 100}
          className="h-8 rounded-r-none border-r-0 pr-2 text-sm"
          {...numericField}
        />
        <select
          aria-label="Area unit"
          className="h-8 rounded-l-none rounded-r-md border border-border bg-muted px-1.5 font-mono text-[10px] text-muted-foreground"
          value={areaUnit}
          onChange={(e) => setAreaUnit(e.target.value as "ha" | "m2")}
        >
          <option value="ha">ha</option>
          <option value="m2">m²</option>
        </select>
      </div>
    </div>
  );
}

function TextField({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1 sm:col-span-2">
      <Label htmlFor={id} className="text-xs">{label}</Label>
      <Input id={id} className="h-8 text-sm" value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}


function displayFromStored(sec: number, unit: "s" | "min" | "h"): number {
  if (unit === "min") return Number((sec / 60).toFixed(4));
  if (unit === "h") return Number((sec / 3600).toFixed(6));
  return sec;
}
function storedSeconds(value: number, unit: "s" | "min" | "h"): number {
  if (unit === "min") return value * 60;
  if (unit === "h") return value * 3600;
  return value;
}
function displayFromStoredHours(hours: number, unit: "s" | "min" | "h"): number {
  if (unit === "s") return Number((hours * 3600).toFixed(2));
  if (unit === "min") return Number((hours * 60).toFixed(3));
  return hours;
}
function storedHours(value: number, unit: "s" | "min" | "h"): number {
  if (unit === "s") return value / 3600;
  if (unit === "min") return value / 60;
  return value;
}
