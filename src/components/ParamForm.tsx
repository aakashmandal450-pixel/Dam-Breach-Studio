import type { ReactNode } from "react";
import { Info } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useStudio } from "@/store/studio";
import type { StudioInputs } from "@/lib/breach/types";

export function ParamForm() {
  const { inputs, setInput } = useStudio();

  return (
    <div className="flex flex-col gap-6">
      <FieldGroup title="Project">
        <TextField id="projectName" label="Project name" value={inputs.projectName} onChange={(v) => setInput("projectName", v)} />
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="mode">Failure mode</Label>
          <select
            id="mode"
            className="h-10 rounded-md border border-border bg-input px-3 text-sm"
            value={inputs.mode}
            onChange={(e) => setInput("mode", e.target.value as StudioInputs["mode"])}
          >
            <option value="overtopping">Overtopping</option>
            <option value="piping">Piping / concentrated leak</option>
          </select>
        </div>
      </FieldGroup>

      <FieldGroup title="Dam geometry">
        <Num id="crestElev" label="Crest elevation" unit="m" hint="Top of dam." k="crestElev" />
        <Num id="baseElev" label="Base elevation" unit="m" hint="Foundation / breach invert floor." k="baseElev" />
        <Num id="crestWidth" label="Crest width C" unit="m" hint="Horizontal crest thickness." k="crestWidth" />
        <Num id="crestLength" label="Crest length" unit="m" hint="Valley-crossing length. Caps final Wb." k="crestLength" />
        <Num id="zUp" label="Upstream slope Z1" unit="H:1V" hint="Horizontal:vertical of the upstream face." k="zUp" />
        <Num id="zDown" label="Downstream slope Z2" unit="H:1V" hint="Downstream face. Steeper faces concentrate shear." k="zDown" />
        <Num id="coreLength" label="Pipe / core length L" unit="m" hint="Seepage path used in pipe-wall shear." k="coreLength" />
      </FieldGroup>

      <FieldGroup title="Reservoir">
        <Num id="initialWL" label="Initial water level" unit="m" hint="Pool elevation at t = 0." k="initialWL" />
        <Num id="volumeM3" label="Storage at that level" unit="m³" hint="Calibrates V(y) = V0 (y/y0)^m." k="volumeM3" />
        <Num id="surfaceAreaHa" label="Surface area" unit="ha" hint="Informational; volume curve uses V0 and m." k="surfaceAreaHa" />
        <Num id="inflowM3s" label="Inflow Qin" unit="m³/s" hint="Constant inflow during the run." k="inflowM3s" />
        <Num id="storageExponent" label="Storage exponent m" unit="—" hint="Typically 2–3. Higher m = more volume near the top." k="storageExponent" />
        <Num id="spillwayQ" label="Spillway discharge" unit="m³/s" hint="Constant additional outlet (optional)." k="spillwayQ" />
      </FieldGroup>

      <FieldGroup title="Soil / erosion">
        <Num id="erosionIndexI" label="Erosion rate index I" unit="—" hint="Wan & Fell. 2 = rapid, 4 = slow. Dominates the answer." k="erosionIndexI" step={0.1} />
        <Num id="tauC" label="Critical shear τc" unit="Pa" hint="No erosion below this shear." k="tauC" />
        <Num id="rhoD" label="Dry density ρd" unit="kg/m³" hint="Used to convert Ce into a volume rate." k="rhoD" />
        <Num id="phiDeg" label="Friction angle φ" unit="°" hint="Sets a residual side-slope floor after collapse." k="phiDeg" />
        <Num id="manningN" label="Manning n" unit="—" hint="Roughness of the breach channel." k="manningN" step={0.005} />
        <Num id="zb" label="Breach side slope Zb" unit="H:1V" hint="Trapezoid batter of the open breach." k="zb" step={0.05} />
        <Num id="sideErosionFactor" label="Side erosion factor" unit="—" hint="Widening relative to deepening (≈ 1–2)." k="sideErosionFactor" step={0.1} />
      </FieldGroup>

      <FieldGroup title="Hydraulics & initiation">
        <Num id="Cw" label="Weir coefficient Cw" unit="m^0.5/s" hint="Broad-crested weir. Default 1.7 metric." k="Cw" step={0.05} />
        <Num id="CdOrifice" label="Orifice Cd" unit="—" hint="Pipe discharge coefficient." k="CdOrifice" step={0.05} />
        <Num id="initialNotchWidth" label="Initial notch width" unit="m" hint="Starter cut for overtopping." k="initialNotchWidth" />
        <Num id="initialPipeRadius" label="Initial pipe radius" unit="m" hint="Detected leak size at t = 0." k="initialPipeRadius" step={0.01} />
        <Num id="pipeInvert" label="Pipe invert" unit="m" hint="Elevation of the concentrated leak." k="pipeInvert" />
        <Num id="collapseRatio" label="Collapse ratio κ" unit="—" hint="Roof fails when 2R ≥ κ × cover." k="collapseRatio" step={0.05} />
      </FieldGroup>

      <FieldGroup title="Numerical">
        <Num id="dt" label="Time step" unit="s" hint="2 s is a good default." k="dt" />
        <Num id="tMaxHours" label="Max duration" unit="h" hint="Stops earlier if the reservoir empties." k="tMaxHours" />
      </FieldGroup>
    </div>
  );
}

function FieldGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h3 className="font-display text-base font-medium tracking-tight">{title}</h3>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">{children}</div>
    </section>
  );
}

function Num({
  id,
  label,
  unit,
  hint,
  k,
  step = 0.1,
}: {
  id: string;
  label: string;
  unit: string;
  hint: string;
  k: keyof StudioInputs;
  step?: number;
}) {
  const { inputs, setInput } = useStudio();
  const value = inputs[k];
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-1">
        <Label htmlFor={id}>{label}</Label>
        <Tooltip>
          <TooltipTrigger asChild>
            <button type="button" className="text-muted-foreground" aria-label={`About ${label}`}>
              <Info className="size-3.5" />
            </button>
          </TooltipTrigger>
          <TooltipContent>{hint}</TooltipContent>
        </Tooltip>
        <span className="ml-auto font-mono text-[10px] text-muted-foreground">{unit}</span>
      </div>
      <Input
        id={id}
        type="number"
        step={step}
        value={typeof value === "number" ? value : 0}
        onChange={(e) => setInput(k, Number(e.target.value) as never)}
      />
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
    <div className="flex flex-col gap-1.5 sm:col-span-2">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
