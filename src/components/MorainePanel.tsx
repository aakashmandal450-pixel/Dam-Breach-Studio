import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { computeIceThermal } from "@/lib/moraine/iceThermal";
import { computeMoraineStability } from "@/lib/moraine/stability";
import {
  DEFAULT_ICE_THERMAL,
  DEFAULT_MORAINE_STABILITY,
  type IceThermalInputs,
  type MoraineStabilityInputs,
} from "@/lib/moraine/types";
import { useStudio } from "@/store/studio";
import { formatNumber } from "@/lib/utils";
import { Info, ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export function MorainePanel() {
  const { inputs, setInput } = useStudio();
  const enabled = inputs.glofIceEnabled !== false;

  const Hb = Math.max(inputs.crestElev - inputs.baseElev, 1);
  const freeboard0 = Math.max(0, inputs.crestElev - inputs.initialWL);

  const [ice, setIce] = useState<IceThermalInputs>({
    ...DEFAULT_ICE_THERMAL,
    freeboard0,
    I_frozen: Math.max(inputs.erosionIndexI, 2.5),
    I_thawed: Math.min(inputs.erosionIndexI, 2.2),
  });
  const [stab, setStab] = useState<MoraineStabilityInputs>({
    ...DEFAULT_MORAINE_STABILITY,
    height: Hb,
    zDown: inputs.zDown,
    phiDeg: inputs.phiDeg,
    widthToHeight: inputs.crestWidth / Hb,
    freeboardRatio: freeboard0 / Hb,
    iceCored: inputs.damStructure === "ice_cored_moraine",
  });

  const [iceInfoOpen, setIceInfoOpen] = useState(false);
  const [stabInfoOpen, setStabInfoOpen] = useState(false);

  const iceRes = useMemo(() => computeIceThermal(ice), [ice]);
  const stabRes = useMemo(
    () =>
      computeMoraineStability({
        ...stab,
        height: Hb,
        zDown: inputs.zDown,
        thawFraction: iceRes.thawFraction,
        iceCored: inputs.damStructure === "ice_cored_moraine" || inputs.damStructure === "moraine",
        freeboardRatio: Math.max(0, iceRes.freeboardRemaining) / Hb,
        widthToHeight: inputs.crestWidth / Hb,
        phiDeg: inputs.phiDeg,
      }),
    [stab, Hb, inputs.zDown, inputs.crestWidth, inputs.phiDeg, inputs.damStructure, iceRes],
  );

  function setI<K extends keyof IceThermalInputs>(k: K, v: IceThermalInputs[K]) {
    setIce((s) => ({ ...s, [k]: v }));
  }
  function setS<K extends keyof MoraineStabilityInputs>(k: K, v: MoraineStabilityInputs[K]) {
    setStab((s) => ({ ...s, [k]: v }));
  }

  function applyToBreach() {
    if (!enabled) return;
    setInput("erosionIndexI", Number(iceRes.I_eff.toFixed(2)));
    setInput("tauC", Number(iceRes.tauC_eff.toFixed(1)));
    if (iceRes.freeboardLoss > 0) {
      const newWL = Math.min(inputs.crestElev + 0.05, inputs.initialWL + iceRes.freeboardLoss);
      setInput("initialWL", Number(newWL.toFixed(3)));
    }
    if (iceRes.overspillRisk) {
      setInput("mode", "overtopping");
      setInput("headcutEnabled", true);
    }
    if (inputs.damStructure !== "ice_cored_moraine" && inputs.damStructure !== "moraine") {
      setInput("damStructure", "ice_cored_moraine");
    }
  }

  return (
    <div className="flex flex-col gap-5">
      {/* Master enable */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2.5">
        <div className="flex flex-col gap-0.5">
          <p className="text-sm font-medium">GLOF / ice influence</p>
          <p className="text-[11px] text-muted-foreground leading-snug">
            Turn off for ordinary homogeneous / zoned earthfill runs. When off, this module is ignored by the engine.
          </p>
        </div>
        <select
          className="h-8 rounded-md border border-border bg-input px-2 text-sm"
          value={enabled ? "on" : "off"}
          onChange={(e) => setInput("glofIceEnabled", e.target.value === "on")}
          aria-label="Enable GLOF / ice module"
        >
          <option value="on">On — include thaw &amp; stability screening</option>
          <option value="off">Off — omit (simple dam breach)</option>
        </select>
      </div>

      {!enabled && (
        <p className="rounded-md border border-dashed border-border bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
          Module disabled. Parameters below are inactive and will not change breach inputs or results. Switch to{" "}
          <strong className="text-foreground">On</strong> when you need ice-core thaw or moraine FoS screening.
        </p>
      )}

      <div className={cn("flex flex-col gap-5 transition-opacity", !enabled && "pointer-events-none opacity-45")}>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Screening GLOF tools for ice-cored / moraine dams: degree-day thaw, freeboard loss, effective I/τc, and a distal-face
          infinite-slope factor of safety. These are <strong className="text-foreground">not</strong> full thermo-hydro-mechanical
          FEM models — use them to set breach inputs, then Run formation.
        </p>

        {/* Ice-core thermal */}
        <section className="space-y-3 rounded-lg border border-border bg-muted/20 p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Ice-core thermal (degree-day)</p>
            <button
              type="button"
              onClick={() => setIceInfoOpen((v) => !v)}
              className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <Info className="size-3" />
              Info
              {iceInfoOpen ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
            </button>
          </div>

          {iceInfoOpen && (
            <div className="rounded-md border border-border/80 bg-background px-3 py-2.5 text-[11px] leading-relaxed text-muted-foreground space-y-1.5">
              <p>
                <strong className="text-foreground">Purpose.</strong> Estimate how much ice in an ice-cored moraine melts over a warm
                season, how much freeboard is lost to settlement, and the resulting effective erodibility (I_eff, τc_eff).
              </p>
              <p>
                <strong className="text-foreground">Melt depth.</strong> d_melt = (DDF · PDD) / 1000 (m), capped by ice-core thickness.
                DDF is typically 3–8 mm/°C·d for debris-covered ice; PDD is the seasonal positive degree-day total.
              </p>
              <p>
                <strong className="text-foreground">Thaw fraction.</strong> Fraction of the ice content that has melted. Used to mix
                frozen and thawed material properties: I_eff and τc_eff are linear blends.
              </p>
              <p>
                <strong className="text-foreground">Freeboard loss.</strong> ≈ settlement factor × melt depth × ice content. If loss
                exceeds initial freeboard, overspill risk is flagged and Apply can switch mode to overtopping.
              </p>
              <p>
                <strong className="text-foreground">Limits.</strong> Screening only — no multi-year climate series, no full thermal
                FEM, no coupled seepage. See Theory → Ice-core thermal.
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-2.5">
            <Field label="Ice content" unit="—" value={ice.iceContent} step={0.05} onChange={(v) => setI("iceContent", v)} hint="0–0.4+ volumetric" />
            <Field label="Ice-core thickness" unit="m" value={ice.iceCoreThickness} onChange={(v) => setI("iceCoreThickness", v)} />
            <Field label="Depth to ice (from crest)" unit="m" value={ice.iceCoreDepth} onChange={(v) => setI("iceCoreDepth", v)} />
            <Field label="Positive degree-days" unit="°C·d" value={ice.positiveDegreeDays} step={10} onChange={(v) => setI("positiveDegreeDays", v)} />
            <Field label="Degree-day factor" unit="mm/°C·d" value={ice.degreeDayFactorMm} step={0.1} onChange={(v) => setI("degreeDayFactorMm", v)} />
            <Field label="Settlement factor" unit="—" value={ice.settlementFactor} step={0.05} onChange={(v) => setI("settlementFactor", v)} />
            <Field label="I frozen" unit="—" value={ice.I_frozen} step={0.1} onChange={(v) => setI("I_frozen", v)} />
            <Field label="I thawed" unit="—" value={ice.I_thawed} step={0.1} onChange={(v) => setI("I_thawed", v)} />
            <Field label="τc frozen" unit="Pa" value={ice.tauC_frozen} onChange={(v) => setI("tauC_frozen", v)} />
            <Field label="τc thawed" unit="Pa" value={ice.tauC_thawed} onChange={(v) => setI("tauC_thawed", v)} />
            <Field label="Initial freeboard" unit="m" value={ice.freeboard0} step={0.1} onChange={(v) => setI("freeboard0", v)} />
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
            <Stat label="Melt depth" value={`${formatNumber(iceRes.meltDepth, 2)} m`} />
            <Stat label="Thaw fraction" value={formatNumber(iceRes.thawFraction, 2)} />
            <Stat label="Freeboard loss" value={`${formatNumber(iceRes.freeboardLoss, 2)} m`} />
            <Stat label="Freeboard left" value={`${formatNumber(iceRes.freeboardRemaining, 2)} m`} />
            <Stat label="I effective" value={formatNumber(iceRes.I_eff, 2)} />
            <Stat label="τc effective" value={`${formatNumber(iceRes.tauC_eff, 1)} Pa`} />
          </div>
          {iceRes.overspillRisk && (
            <p className="text-xs text-destructive">Overspill risk: estimated settlement consumes freeboard.</p>
          )}
          {iceRes.warnings.map((w) => (
            <p key={w} className="text-[11px] text-destructive">
              {w}
            </p>
          ))}
        </section>

        {/* Moraine stability */}
        <section className="space-y-3 rounded-lg border border-border bg-muted/20 p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Moraine distal-face stability</p>
            <button
              type="button"
              onClick={() => setStabInfoOpen((v) => !v)}
              className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <Info className="size-3" />
              Info
              {stabInfoOpen ? <ChevronDown className="size-3" /> : <ChevronRight className="size-3" />}
            </button>
          </div>

          {stabInfoOpen && (
            <div className="rounded-md border border-border/80 bg-background px-3 py-2.5 text-[11px] leading-relaxed text-muted-foreground space-y-1.5">
              <p>
                <strong className="text-foreground">Purpose.</strong> Infinite-slope factor of safety on the distal (downstream)
                face, softened by thaw when the dam is ice-cored.
              </p>
              <p>
                <strong className="text-foreground">FoS.</strong> FoS = [c′/(γ H cos²β) + (1−Ru) tan φ′] / tan β. Values &lt; 1.0
                indicate likely instability; 1.0–1.3 marginal; &gt; 1.5 usually acceptable for screening.
              </p>
              <p>
                <strong className="text-foreground">Thaw effect.</strong> As thaw fraction rises, effective cohesion and friction
                are reduced, lowering FoS. Geometry risk uses width/height; freeboard risk uses remaining freeboard ratio.
              </p>
              <p>
                <strong className="text-foreground">Composite hazard.</strong> Combines FoS class, geometry, freeboard and ice
                presence into a single screening label (low → very high). Not a probabilistic GLOF rate.
              </p>
              <p>
                <strong className="text-foreground">Limits.</strong> 2-D infinite slope only — no 3-D slip surface, no strength
                reduction FEM. See Theory → Moraine stability.
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-2.5">
            <Field label="Unit weight γ" unit="kN/m³" value={stab.gamma} onChange={(v) => setS("gamma", v)} />
            <Field label="Cohesion c′" unit="kPa" value={stab.cohesion} step={0.5} onChange={(v) => setS("cohesion", v)} />
            <Field label="Pore ratio Ru" unit="—" value={stab.ru} step={0.05} onChange={(v) => setS("ru", v)} />
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
            <Stat label="Slope β" value={`${formatNumber(stabRes.betaDeg, 1)}°`} />
            <Stat label="FoS" value={formatNumber(stabRes.FoS, 2)} />
            <Stat label="FoS class" value={stabRes.FoS_class} />
            <Stat label="Geometry risk" value={stabRes.geometryRisk} />
            <Stat label="Freeboard risk" value={stabRes.freeboardRisk} />
            <Stat label="Composite hazard" value={stabRes.compositeClass} />
          </div>
          <p className="text-[11px] text-muted-foreground">
            Composite score {formatNumber(stabRes.compositeScore, 2)} (0 low – 1 very high). Uses project Hb, Z₂, crest width, φ, and thaw
            fraction from the ice block above.
          </p>
        </section>

        <div className="flex flex-wrap gap-2">
          <Button type="button" size="sm" onClick={applyToBreach} disabled={!enabled}>
            Apply I_eff, τc_eff &amp; freeboard to breach inputs
          </Button>
        </div>
        <p className="text-[11px] text-muted-foreground leading-relaxed">
          Applying writes effective erodibility and raises WL by freeboard loss (screening). Then use Run formation. Full ice
          thermal FEM and 3-D strength reduction remain outside this studio.
        </p>
      </div>
    </div>
  );
}

function Field({
  label,
  unit,
  value,
  onChange,
  step = 0.1,
  hint,
}: {
  label: string;
  unit: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  hint?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <Label className="text-xs">
        {label} {hint ? <span className="text-muted-foreground font-normal">({hint})</span> : null}
      </Label>
      <div className="relative">
        <Input
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
    <div className="rounded-md border border-border bg-background px-2 py-1.5">
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p className="font-mono text-sm font-medium">{value}</p>
    </div>
  );
}
