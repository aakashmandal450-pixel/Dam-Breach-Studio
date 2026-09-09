import { useMemo } from "react";
import { Info, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { computeImpulse2D } from "@/lib/impulse/gen2d";
import { computeImpulse3D } from "@/lib/impulse/gen3d";
import { computeRunup } from "@/lib/impulse/runup";
import { impactVelocityFromFallHeight } from "@/lib/impulse/velocity";
import { applyAvalancheDisplacement } from "@/lib/breach/engine";
import type { Impulse2DInputs, Impulse2DResult, Impulse3DInputs, Impulse3DResult } from "@/lib/impulse/types";
import { formatNumber, cn } from "@/lib/utils";
import { Impulse2DSchematic } from "@/components/schematics/Impulse2DSchematic";
import { Impulse3DSchematic } from "@/components/schematics/Impulse3DSchematic";
import { useStudio } from "@/store/studio";

type DimMode = "2d" | "3d";

export function ImpulseWavePanel() {
  const { inputs: studio, setInput, impulse, setImpulse } = useStudio();
  const dim = impulse.dim;
  const p2 = impulse.p2;
  const p3 = impulse.p3;
  const r2 = impulse.r2;
  const r3 = impulse.r3;

  const freeboard = Math.max(0, studio.crestElev - studio.initialWL);
  const betaFromZ2 = Math.atan(1 / Math.max(studio.zDown, 0.1)) * (180 / Math.PI);

  function set2<K extends keyof Impulse2DInputs>(k: K, v: Impulse2DInputs[K]) {
    const next = { ...p2, [k]: v };
    if (k === "fallHeight" || (k === "autoVelocity" && v === true)) {
      if (next.autoVelocity) next.Vs = impactVelocityFromFallHeight(Number(next.fallHeight));
    }
    if (k === "Vs") next.autoVelocity = false;
    setImpulse({ p2: next });
  }

  function set3<K extends keyof Impulse3DInputs>(k: K, v: Impulse3DInputs[K]) {
    const next = { ...p3, [k]: v };
    if (k === "fallHeight" || (k === "autoVelocity" && v === true)) {
      if (next.autoVelocity) next.Vs = impactVelocityFromFallHeight(Number(next.fallHeight));
    }
    if (k === "Vs") next.autoVelocity = false;
    setImpulse({ p3: next });
  }

  function run() {
    if (dim === "2d") {
      const p = { ...p2 };
      if (p.autoVelocity) p.Vs = impactVelocityFromFallHeight(p.fallHeight);
      setImpulse({ p2: p, r2: computeImpulse2D(p) });
    } else {
      const p = { ...p3 };
      if (p.autoVelocity) p.Vs = impactVelocityFromFallHeight(p.fallHeight);
      setImpulse({ p3: p, r3: computeImpulse3D(p) });
    }
  }

  const activeAmp = dim === "2d" ? r2 : r3;
  const a = activeAmp?.aM ?? 0;
  const H = activeAmp?.HM ?? 0;
  const h = dim === "2d" ? p2.h : p3.h;
  const T = activeAmp?.TM ?? 8;

  const runup = useMemo(() => {
    if (!activeAmp) return null;
    return computeRunup({
      a,
      H,
      h,
      betaDeg: betaFromZ2,
      f: freeboard,
      bK: studio.crestWidth,
      T,
    });
  }, [activeAmp, a, H, h, betaFromZ2, freeboard, studio.crestWidth, T]);

  function passToBreach() {
    if (!runup) return;

    setInput("mode", "overtopping");
    setInput("headcutEnabled", true);

    // ── Step 1: ONE-TIME Archimedes displaced-volume bump ──────────────────
    // The slide mass permanently occupies volume in the lake — real stored water,
    // so it belongs on the reservoir side (volumeM3 / initialWL), applied once,
    // before the transient wave. Distinct from Step 2 below. Same mechanism
    // validated in validation/cases/run_digtsho_impulse_breach.ts.
    const slideVolume = dim === "2d" ? p2.slideVolume : p3.slideVolume;
    const displacement = applyAvalancheDisplacement({
      slideVolume,
      submergedFraction: studio.avalancheSubmergedFraction,
      volumeM3: studio.volumeM3,
      initialWL: studio.initialWL,
      baseElev: studio.baseElev,
      storageExponent: studio.storageExponent,
    });
    setInput("volumeM3", displacement.newVolumeM3);
    setInput("initialWL", displacement.newInitialWL);

    // ── Step 2: transient wave forcing, EROSION-ONLY (waveForcingEnabled) ──
    // Replaces the legacy fake-inflow hack entirely. The wave is a surge, not
    // new water, so it must never touch volumeM3/inflowM3s/inflowSeries — only
    // the erosion hydraulics via the validated wave-forcing mechanism. d0/tO
    // come straight from the Impulse module's own run-up result.
    if (runup.overtops) {
      setInput("waveForcingEnabled", true);
      setInput("waveOvertopDepth", Math.max(runup.d0, 0));
      setInput("waveOvertopDuration", Math.max(runup.tO, 1));
    }
    // Results stay in impulse store — do not clear r2/r3
  }

  function screeningPreset() {
    if (!runup) return;
    if (!runup.overtops) return;
    passToBreach();
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground leading-relaxed">
        Landslide-generated impulse waves (VAW style). Impact speed is computed from fall height
        as <span className="font-mono">Vs = √(2 g Hfall)</span> unless you override it. Prefer the{" "}
        <strong>3-D</strong> diagram to see slide thickness <span className="font-mono">s</span> and
        width <span className="font-mono">b</span> as a block. Wave results stay on this tab after
        Pass to breach (A3).
      </p>

      <div className="flex gap-1 rounded-md border border-border bg-muted/40 p-0.5 w-fit">
        {(["2d", "3d"] as DimMode[]).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setImpulse({ dim: m })}
            className={cn(
              "rounded px-3 py-1 text-xs font-medium",
              dim === m ? "bg-card text-foreground shadow-sm" : "text-muted-foreground",
            )}
          >
            {m === "2d" ? "2-D generation" : "3-D generation"}
          </button>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="flex flex-col gap-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Wave generation</p>
          <div className="grid grid-cols-2 gap-2.5">
            {dim === "2d" ? (
              <>
                <Field id="Hfall" label="Fall height" symbol="Hfall" unit="m" hint="Vertical drop of the slide centre of mass before it hits the water. Vs is computed as √(2 g Hfall). Typical rock/debris: tens to hundreds of metres." value={p2.fallHeight} onChange={(v) => set2("fallHeight", v)} />
                <Field id="Vs" label="Impact velocity (computed)" symbol="Vs" unit="m/s" hint="Auto: Vs = √(2 g Hfall). Edit only to override (disables auto). Difficult to measure in the field — prefer fall height." value={Number(p2.Vs.toFixed(2))} onChange={(v) => set2("Vs", v)} step={0.1} />
                <Field id="vol" label="Bulk slide volume" symbol="V" unit="m³" hint="Total bulk volume of the moving mass (solids + voids)." value={p2.slideVolume} onChange={(v) => set2("slideVolume", v)} step={100} />
                <Field id="s" label="Slide thickness" symbol="s" unit="m" hint="Thickness of the slide block perpendicular to the slope (how ‘deep’ the mass is). Prefer 3-D view to see s on the block. Relative S = s/h typically 0.09–1.64." value={p2.s} onChange={(v) => set2("s", v)} />
                <Field id="b" label="Slide width" symbol="b" unit="m" hint="Width of the slide across the slope (into the page in 2-D). Prefer 3-D view for the block width. Relative B = b/h typically 0.74–3.33." value={p2.b} onChange={(v) => set2("b", v)} />
                <Field id="rhoS" label="Bulk density" symbol="ρs" unit="kg/m³" hint="Bulk density of the slide mass (rock/debris + voids). Typical 1600–2200 kg/m³." value={p2.rhoS} onChange={(v) => set2("rhoS", v)} step={10} />
                <Field id="n" label="Bulk porosity" symbol="n" unit="%" hint="Void fraction of the bulk mass (%). VAW envelope ≈ 31–43%." value={p2.nPercent} onChange={(v) => set2("nPercent", v)} step={0.5} />
                <Field id="alpha" label="Impact angle" symbol="α" unit="°" hint="Angle between the slope face and the horizontal at the impact point (bed). 90° = vertical cliff; 30–45° = typical debris slope." value={p2.alphaDeg} onChange={(v) => set2("alphaDeg", v)} step={1} />
                <Field id="h" label="Still water depth" symbol="h" unit="m" hint="Undisturbed water depth at the impact zone." value={p2.h} onChange={(v) => set2("h", v)} />
                <Field id="x" label="Streamwise distance" symbol="x" unit="m" hint="Distance from impact to the gauge (e.g. dam) along the channel in 2-D." value={p2.x} onChange={(v) => set2("x", v)} step={10} />
              </>
            ) : (
              <>
                <Field id="Hfall3" label="Fall height" symbol="Hfall" unit="m" hint="Vertical drop of the slide centre of mass. Vs = √(2 g Hfall)." value={p3.fallHeight} onChange={(v) => set3("fallHeight", v)} />
                <Field id="Vs3" label="Impact velocity (computed)" symbol="Vs" unit="m/s" hint="Auto from fall height; edit to override." value={Number(p3.Vs.toFixed(2))} onChange={(v) => set3("Vs", v)} step={0.1} />
                <Field id="vol3" label="Bulk slide volume" symbol="V" unit="m³" hint="Bulk volume of the moving mass." value={p3.slideVolume} onChange={(v) => set3("slideVolume", v)} step={100} />
                <Field id="s3" label="Slide thickness" symbol="s" unit="m" hint="Thickness of the rectangular slide block (shown on the 3-D figure). Depth of the mass normal to the slope." value={p3.s} onChange={(v) => set3("s", v)} />
                <Field id="b3" label="Slide width" symbol="b" unit="m" hint="Width of the rectangular slide block across the slope (shown on the 3-D figure)." value={p3.b} onChange={(v) => set3("b", v)} />
                <Field id="rhoS3" label="Bulk density" symbol="ρs" unit="kg/m³" hint="Bulk density." value={p3.rhoS} onChange={(v) => set3("rhoS", v)} step={10} />
                <Field id="n3" label="Bulk porosity" symbol="n" unit="%" hint="Void fraction %." value={p3.nPercent} onChange={(v) => set3("nPercent", v)} step={0.5} />
                <Field id="alpha3" label="Impact angle" symbol="α" unit="°" hint="Slope angle from horizontal at impact." value={p3.alphaDeg} onChange={(v) => set3("alphaDeg", v)} step={1} />
                <Field id="h3" label="Still water depth" symbol="h" unit="m" hint="Still-water depth at impact." value={p3.h} onChange={(v) => set3("h", v)} />
                <Field id="r" label="Radial distance" symbol="r" unit="m" hint="Distance from impact point to the gauge (dam) in plan view." value={p3.r} onChange={(v) => set3("r", v)} step={10} />
                <Field id="gamma" label="Propagation angle" symbol="γ" unit="°" hint="Angle in plan between the slide axis (direction the mass enters the water) and the line from impact to the dam. γ = 0° means the dam lies on the main wave lobe (strongest waves). γ = 90° is sideways (much weaker). Use the map/bearing from landslide path to dam." value={p3.gammaDeg} onChange={(v) => set3("gammaDeg", v)} step={1} />
              </>
            )}
          </div>
          <p className="text-[11px] text-muted-foreground">
            Prefer the <strong>3-D</strong> tab to visualise the slide block with thickness s and width b.
          </p>
          <Button type="button" onClick={run} className="mt-1 w-fit">
            Compute impulse wave
          </Button>
        </div>

        <div className="flex flex-col gap-3">
          {dim === "2d" ? (
            <Impulse2DSchematic inputs={p2} result={r2} />
          ) : (
            <Impulse3DSchematic inputs={p3} result={r3} />
          )}

          {activeAmp && (
            <>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <Stat label="Impulse product P" value={formatNumber(activeAmp.P, 3)} />
                <Stat label="Max amplitude aM" value={`${formatNumber(a, 2)} m`} />
                <Stat label="Max height HM" value={`${formatNumber(H, 2)} m`} />
                {"xM" in activeAmp && (
                  <Stat label="Location of aM" value={`${formatNumber((activeAmp as Impulse2DResult).xM, 1)} m`} />
                )}
                {"rM" in activeAmp && (
                  <Stat label="Location of aM" value={`${formatNumber((activeAmp as Impulse3DResult).rM, 1)} m`} />
                )}
                <Stat label="Period TM" value={`${formatNumber(T, 2)} s`} />
                <Stat label="Impact Vs used" value={`${formatNumber(dim === "2d" ? p2.Vs : p3.Vs, 2)} m/s`} />
              </div>

              {runup && (
                <div className="rounded-md border border-border bg-muted/20 p-3 space-y-2">
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Run-up vs dam (project geometry)
                  </p>
                  <div className="grid grid-cols-2 gap-1.5 text-xs">
                    <span>{`R = ${runup.R.toFixed(2)} m`}</span>
                    <span>{`f = ${freeboard.toFixed(2)} m`}</span>
                    <span>{`β ≈ ${betaFromZ2.toFixed(0)}° (from Z2)`}</span>
                    <span className={runup.overtops ? "text-destructive font-medium" : ""}>
                      {runup.overtops ? "R > f — overtopping" : "R ≤ f — freeboard holds"}
                    </span>
                    <span>{`V = ${runup.V.toFixed(2)} m³/m`}</span>
                    <span>{`d0 = ${runup.d0.toFixed(2)} m`}</span>
                  </div>
                  <div className="flex flex-wrap gap-2 pt-1">
                    <Button type="button" size="sm" onClick={passToBreach}>
                      <ArrowRight className="size-3.5" />
                      Pass to breach (A3)
                    </Button>
                    <Button type="button" size="sm" variant="secondary" onClick={screeningPreset} disabled={!runup.overtops}>
                      Screening if R &gt; f (A1)
                    </Button>
                  </div>
                  <p className="text-[11px] text-muted-foreground">
                    A3 updates Inputs / Discharge but keeps these wave results on this tab.
                  </p>
                </div>
              )}

              {(dim === "2d" ? r2?.warnings : r3?.warnings)?.length ? (
                <div className="rounded-md border border-destructive/40 bg-destructive/5 p-2 text-xs text-destructive">
                  <ul className="list-disc pl-4 space-y-0.5">
                    {(dim === "2d" ? r2!.warnings : r3!.warnings).map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <div className="flex flex-wrap gap-1">
                {Object.entries(dim === "2d" ? r2!.limits : r3!.limits).map(([k, lim]) => (
                  <Badge key={k} tone={lim.ok ? "ok" : "warn"} className="font-mono text-[10px]">
                    {k}={lim.value.toFixed(2)}
                  </Badge>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({
  id,
  label,
  symbol,
  unit,
  hint,
  value,
  onChange,
  step = 0.1,
}: {
  id: string;
  label: string;
  symbol: string;
  unit: string;
  hint: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
}) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1">
        <Label htmlFor={id} className="text-xs leading-tight">
          {label} <span className="font-mono text-[10px] text-muted-foreground">({symbol})</span>
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
        <Input
          id={id}
          type="number"
          step={step}
          className="h-8 pr-12 text-sm"
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
        />
        <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 font-mono text-[10px] text-muted-foreground">
          {unit}
        </span>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-muted/30 px-2 py-1.5">
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p className="font-mono text-sm font-medium">{value}</p>
    </div>
  );
}
