import {
  EQUATIONS,
  I_TABLE,
  LIMITATIONS,
  PARAM_DOCS,
  MANNING_TABLE,
  HEADCUT_DOCS,
  BREACH_SIDE_SLOPE_DOC,
  MORAINE_DOC,
  TYPICAL_VALUES,
  ICE_THERMAL_DOC,
  MORAINE_STABILITY_DOC,
  MODULE_SCOPE_DOC,
} from "@/lib/breach/docs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function TheoryView() {
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8 pb-16">
      <header className="flex flex-col gap-2">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-accent">Mechanistic engine</p>
        <h1 className="font-display text-3xl font-medium tracking-tight md:text-4xl">Equations, parameters, limits</h1>
        <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
          Every symbol used in the formation model is defined here. The engine is a simplified physical model in the
          lineage of NWS BREACH, DLBreach and WinDAM — coupled hydraulics, excess-shear erosion, and a roof-collapse
          switch — not a regression on historic peaks.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>{MODULE_SCOPE_DOC.title}</CardTitle>
          <CardDescription>{MODULE_SCOPE_DOC.summary}</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="list-disc space-y-1.5 pl-5 text-sm text-muted-foreground">
            {MODULE_SCOPE_DOC.points.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Governing equations</CardTitle>
          <CardDescription>Integrated at every time step with a falling reservoir head.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          {EQUATIONS.map((eq) => (
            <div key={eq.title} className="rounded-md border border-border bg-background p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{eq.title}</p>
              <p className="mt-1 font-mono text-sm">{eq.latex}</p>
              <p className="mt-2 text-sm text-muted-foreground">{eq.note}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Parameter catalogue</CardTitle>
          <CardDescription>Units, typical ranges, and where each term appears. Match symbols on the input schematic.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs uppercase tracking-wide text-muted-foreground">
                <th className="py-2 pr-3 font-medium">Symbol</th>
                <th className="py-2 pr-3 font-medium">Name</th>
                <th className="py-2 pr-3 font-medium">Unit</th>
                <th className="py-2 pr-3 font-medium">Range</th>
                <th className="py-2 font-medium">Meaning</th>
              </tr>
            </thead>
            <tbody>
              {PARAM_DOCS.map((p) => (
                <tr key={p.symbol} className="border-b border-border/70 align-top">
                  <td className="py-2 pr-3 font-mono text-xs">{p.symbol}</td>
                  <td className="py-2 pr-3">{p.name}</td>
                  <td className="py-2 pr-3 text-muted-foreground">{p.unit}</td>
                  <td className="py-2 pr-3 text-muted-foreground">{p.range}</td>
                  <td className="py-2 text-muted-foreground">
                    {p.meaning}{" "}
                    <span className="block font-mono text-[11px] text-foreground/70">{p.equation}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Typical erosion-rate index</CardTitle>
          <CardDescription>Wan & Fell / ICOLD screening values. Prefer a Hole Erosion Test when you have one.</CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs uppercase tracking-wide text-muted-foreground">
                <th className="py-2 pr-3 font-medium">I</th>
                <th className="py-2 pr-3 font-medium">Soils</th>
                <th className="py-2 font-medium">Relative rate</th>
              </tr>
            </thead>
            <tbody>
              {I_TABLE.map((row) => (
                <tr key={row.i} className="border-b border-border/70">
                  <td className="py-2 pr-3 font-mono">{row.i}</td>
                  <td className="py-2 pr-3">{row.soil}</td>
                  <td className="py-2">{row.rate}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Glacial / moraine lake volume from area</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>
            When bathymetry is unavailable, inventory-style power laws estimate storage from surface
            area. The Reservoir tab offers Sakai (Himalaya), Cook &amp; Quincey (global), Huggel
            (Alpine), Evans, and O’Connor (Cascades). Units follow the source papers (typically{" "}
            <span className="font-mono">A</span> in km² and <span className="font-mono">V</span> in
            10⁶ m³, or SI forms for O’Connor / Cook–Quincey). These are screening relations with
            large scatter — always prefer a surveyed stage–storage curve for design-level work.
          </p>
          <p>
            Freeboard <span className="font-mono">f = crest − WL</span> is shown alongside the
            estimate so you can see whether the pool is already overtopping before a wave or breach
            run.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{ICE_THERMAL_DOC.title}</CardTitle>
          <CardDescription>{ICE_THERMAL_DOC.summary}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          {ICE_THERMAL_DOC.equations.map((eq) => (
            <div key={eq.title} className="rounded-md border border-border bg-background p-3">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{eq.title}</p>
              <p className="mt-1 font-mono text-sm text-foreground">{eq.latex}</p>
              <p className="mt-1 text-xs">{eq.note}</p>
            </div>
          ))}
          <ul className="list-disc space-y-1 pl-5 text-xs">
            {ICE_THERMAL_DOC.limits.map((l) => (
              <li key={l.slice(0, 40)}>{l}</li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{MORAINE_STABILITY_DOC.title}</CardTitle>
          <CardDescription>{MORAINE_STABILITY_DOC.summary}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          {MORAINE_STABILITY_DOC.equations.map((eq) => (
            <div key={eq.title} className="rounded-md border border-border bg-background p-3">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{eq.title}</p>
              <p className="mt-1 font-mono text-sm text-foreground">{eq.latex}</p>
              <p className="mt-1 text-xs">{eq.note}</p>
            </div>
          ))}
          <ul className="list-disc space-y-1 pl-5 text-xs">
            {MORAINE_STABILITY_DOC.classes.map((l) => (
              <li key={l.slice(0, 40)}>{l}</li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Limitations</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="flex list-disc flex-col gap-2 pl-5 text-sm text-muted-foreground">
            {LIMITATIONS.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
