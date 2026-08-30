import { useMemo, useRef, useState } from "react";
import { Code2, Download, Play, Settings2 } from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { DamSchematic } from "@/components/DamSchematic";
import { UncertaintyPanel } from "@/components/UncertaintyPanel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { downloadChartHtml, downloadResultExcel } from "@/lib/breach/exportExcel";
import {
  cellValue,
  computeBreachSummary,
  seriesColumns,
  type ColumnKey,
  type ExportKind,
} from "@/lib/breach/resultMetrics";
import type { SimResult, SimStep, StudioInputs } from "@/lib/breach/types";
import { cn, formatNumber } from "@/lib/utils";

type ResultTab = "summary" | "hydrograph" | "rating" | "breach" | "reservoir" | "diagnostics" | "export";

const TABS: { id: ResultTab; label: string }[] = [
  { id: "summary", label: "Summary" },
  { id: "hydrograph", label: "Hydrograph" },
  { id: "rating", label: "Rating curve" },
  { id: "breach", label: "Breach geometry" },
  { id: "reservoir", label: "Reservoir" },
  { id: "diagnostics", label: "Diagnostics" },
  { id: "export", label: "Export" },
];

interface Props {
  inputs: StudioInputs;
  result: SimResult;
  playIndex: number;
  running: boolean;
  setPlayIndex: (i: number) => void;
  setRunning: (v: boolean) => void;
  onEditInputs: () => void;
  onRerun: () => void;
}

export function ResultsView({
  inputs,
  result,
  playIndex,
  running,
  setPlayIndex,
  setRunning,
  onEditInputs,
  onRerun,
}: Props) {
  const [tab, setTab] = useState<ResultTab>("summary");
  const [busy, setBusy] = useState<ExportKind | null>(null);
  const step = result.series[Math.min(playIndex, result.series.length - 1)] ?? null;
  const m = useMemo(() => computeBreachSummary(result, inputs), [result, inputs]);
  const spillwayQ = inputs.spillwayQ;

  const chartData = useMemo(
    () =>
      result.series.map((s) => {
        const depth = Math.max(s.WL - s.zb, 0);
        const Qbreach = Math.max(s.Q - spillwayQ, 0);
        const avgWidth = (s.Wb + s.Wtop) / 2;
        const area = avgWidth * depth;
        return {
          hr: Number((s.t / 3600).toFixed(4)),
          Q: Number(s.Q.toFixed(3)),
          Qbreach: Number(Qbreach.toFixed(3)),
          Qspillway: Number(Math.max(spillwayQ, 0).toFixed(3)),
          Wb: Number(s.Wb.toFixed(3)),
          Wtop: Number(s.Wtop.toFixed(3)),
          depth: Number(depth.toFixed(3)),
          head: Number(depth.toFixed(3)),
          WL: Number(s.WL.toFixed(3)),
          zb: Number(s.zb.toFixed(3)),
          V: Number((s.V / 1000).toFixed(3)),
          tau: Number(s.tau.toFixed(2)),
          xH: Number((s.xHeadcut ?? 0).toFixed(3)),
          R: Number(s.R.toFixed(4)),
          velocity: area > 0.01 ? Number((Qbreach / area).toFixed(3)) : 0,
          sideSlope: depth > 0.01 ? Number(((s.Wtop - s.Wb) / (2 * depth)).toFixed(3)) : 0,
        };
      }),
    [result.series, spillwayQ],
  );

  // Rating curve: same points, sorted by head so the plotted line reads as a
  // proper monotonic-ish rating curve rather than looping back on itself.
  const ratingData = useMemo(() => [...chartData].sort((a, b) => a.head - b.head), [chartData]);

  const peakIndex = useMemo(() => {
    let best = 0;
    let bestQ = -Infinity;
    result.series.forEach((s, i) => {
      if (s.Q > bestQ) {
        bestQ = s.Q;
        best = i;
      }
    });
    return best;
  }, [result.series]);

  async function exportKind(kind: ExportKind) {
    setBusy(kind);
    try {
      await downloadResultExcel(result, inputs, kind);
    } catch (e) {
      console.error(e);
      alert(
        "Excel export needs the exceljs package. Run: npm install exceljs\nThen restart npm run dev and try again.",
      );
    } finally {
      setBusy(null);
    }
  }

  function jumpTo(index: number) {
    setRunning(false);
    setPlayIndex(index);
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Cross-section playback — always visible */}
      <Card>
        <CardHeader className="flex-row items-center justify-between py-3">
          <CardTitle className="text-base">Simulation — cross-section</CardTitle>
          {step && <Badge tone="accent">{step.stage}</Badge>}
        </CardHeader>
        <CardContent>
          <DamSchematic inputs={inputs} step={step} />
          {result.series.length > 1 && (
            <div className="mt-3 flex flex-col gap-2">
              <Slider
                min={0}
                max={result.series.length - 1}
                step={1}
                value={[playIndex]}
                onValueChange={(v) => {
                  setRunning(false);
                  setPlayIndex(v[0] ?? 0);
                }}
              />
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{((step?.t ?? 0) / 60).toFixed(1)} min</span>
                <button type="button" className="text-accent" onClick={() => setRunning(!running)}>
                  {running ? "Pause" : "Play"}
                </button>
                <span>Q = {formatNumber(step?.Q ?? 0, 2)} m³/s</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Result sub-tabs */}
      <div
        role="tablist"
        aria-label="Result views"
        className="flex flex-wrap gap-0.5 rounded-md border border-border bg-muted/40 p-0.5"
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "rounded px-2.5 py-1.5 text-[11px] font-medium transition-colors",
              tab === t.id
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "summary" && (
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
            <Kpi label="Peak Qp" value={`${formatNumber(m.Qpeak, 2)} m³/s`} hint="BREACH QP" />
            <Kpi label="Time to peak TP" value={`${formatNumber(m.tPeak_min, 1)} min`} hint="BREACH TP" />
            <Kpi
              label="Failure start TB"
              value={m.tB_min != null ? `${formatNumber(m.tB_min, 1)} min` : "—"}
              hint="BREACH TB"
            />
            <Kpi
              label="Rising limb TRS"
              value={m.tRS_min != null ? `${formatNumber(m.tRS_min, 1)} min` : "—"}
              hint="TP − TB"
            />
            <Kpi label="Volume released" value={`${formatNumber(m.volumeReleased_m3, 0)} m³`} hint="" />
            <Kpi label="Final Wb" value={`${formatNumber(m.finalWb_m, 2)} m`} hint="BREACH BO" />
            <Kpi label="Final depth" value={`${formatNumber(m.finalDepth_m, 2)} m`} hint="BREACH BRD" />
            <Kpi label="Final Wtop" value={`${formatNumber(m.finalWtop_m, 2)} m`} hint="BREACH BT" />
            <Kpi
              label="Side slope at peak"
              value={m.peakSideSlope != null ? `${formatNumber(m.peakSideSlope, 2)} H:1V` : "—"}
              hint="BREACH Z"
            />
            <Kpi
              label="Velocity at peak"
              value={m.peakVelocity_ms != null ? `${formatNumber(m.peakVelocity_ms, 2)} m/s` : "—"}
              hint="breach opening check"
            />
            <Kpi
              label="Roof collapse"
              value={m.tCollapse_s != null ? `${formatNumber(m.tCollapse_s / 60, 1)} min` : "—"}
              hint="piping"
            />
            <Kpi
              label="Headcut through C"
              value={
                m.tHeadcutBreach_s != null ? `${formatNumber(m.tHeadcutBreach_s / 60, 1)} min` : "—"
              }
              hint="overtopping"
            />
            <Kpi
              label="Time to empty"
              value={m.tEmpty_s != null ? `${formatNumber(m.tEmpty_s / 60, 1)} min` : "—"}
              hint=""
            />
            <Kpi label="Q at t = 0" value={`${formatNumber(m.Q0_m3s, 2)} m³/s`} hint="BREACH QO" />
          </div>

          {result.warnings.length > 0 && (
            <div className="rounded-lg border border-border bg-card px-4 py-3 text-sm text-warn">
              {result.warnings.map((w) => (
                <p key={w}>{w}</p>
              ))}
            </div>
          )}

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Headcut status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm text-muted-foreground">
              <p>
                Module:{" "}
                <strong className="text-foreground">
                  {inputs.headcutEnabled && inputs.mode === "overtopping" ? "on" : "off / N/A"}
                </strong>
                {" · "}fh = {inputs.headcutAdvanceFactor} · hinit = {inputs.headcutInitDepth} m
              </p>
              <p>
                Breakthrough (xh = C):{" "}
                {result.tHeadcutBreach == null
                  ? "not reached in this run (or module off)"
                  : `${(result.tHeadcutBreach / 60).toFixed(1)} min`}
              </p>
            </CardContent>
          </Card>

          <UncertaintyPanel inputs={inputs} />

          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="outline" disabled={!!busy} onClick={() => exportKind("summary")}>
              <Download className="size-4" />
              {busy === "summary" ? "Writing…" : "Download summary Excel"}
            </Button>
            <Button size="sm" variant="secondary" onClick={onEditInputs}>
              <Settings2 className="size-4" />
              Edit inputs
            </Button>
            <Button size="sm" onClick={onRerun}>
              <Play className="size-4" />
              Re-run
            </Button>
          </div>
        </div>
      )}

      {tab === "hydrograph" && (
        <ResultPanel
          title="Outflow hydrograph"
          note="Total, breach-only, and spillway discharge. BREACH analogues: QTOT, QB, QTS."
          kind="hydrograph"
          exportKind={exportKind}
          busy={busy}
          projectName={inputs.projectName}
        >
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={chartData}>
              <CartesianGrid stroke="#d4cdc0" strokeDasharray="3 3" />
              <XAxis dataKey="hr" tick={{ fontSize: 11 }} tickLine={false} />
              <YAxis tick={{ fontSize: 11 }} tickLine={false} width={48} />
              <RTooltip
                contentStyle={{ background: "#fbf8f2", border: "1px solid #d4cdc0", fontSize: 12 }}
                formatter={(v, name) => [`${formatNumber(Number(v), 2)} m³/s`, name]}
              />
              <Line type="monotone" dataKey="Q" name="Q total" stroke="#245460" dot={false} strokeWidth={2} />
              <Line
                type="monotone"
                dataKey="Qbreach"
                name="Q breach"
                stroke="#b45309"
                dot={false}
                strokeWidth={1.6}
              />
              <Line
                type="monotone"
                dataKey="Qspillway"
                name="Q spillway"
                stroke="#6b6459"
                dot={false}
                strokeWidth={1.4}
                strokeDasharray="4 3"
              />
            </LineChart>
          </ResponsiveContainer>
          <DataTable
            columns={seriesColumns("hydrograph")}
            series={result.series}
            spillwayQ={spillwayQ}
            playIndex={playIndex}
            peakIndex={peakIndex}
            onRowClick={jumpTo}
          />
        </ResultPanel>
      )}

      {tab === "rating" && (
        <ResultPanel
          title="Rating curve"
          note="Head across the breach opening vs breach discharge — the classic head-vs-Q plot BRCH-J shows alongside its hydrograph."
          kind="rating"
          exportKind={exportKind}
          busy={busy}
          projectName={inputs.projectName}
        >
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={ratingData}>
              <CartesianGrid stroke="#d4cdc0" strokeDasharray="3 3" />
              <XAxis
                dataKey="head"
                type="number"
                domain={["auto", "auto"]}
                tick={{ fontSize: 11 }}
                tickLine={false}
                label={{ value: "head (m)", position: "insideBottom", offset: -4, fontSize: 11 }}
              />
              <YAxis
                tick={{ fontSize: 11 }}
                tickLine={false}
                width={48}
                label={{ value: "Q breach (m³/s)", angle: -90, position: "insideLeft", fontSize: 11 }}
              />
              <RTooltip
                contentStyle={{ background: "#fbf8f2", border: "1px solid #d4cdc0", fontSize: 12 }}
                formatter={(v, name) => [
                  name === "Qbreach" ? `${formatNumber(Number(v), 2)} m³/s` : `${formatNumber(Number(v), 2)} m`,
                  name === "Qbreach" ? "Q breach" : "head",
                ]}
              />
              <Line
                type="monotone"
                dataKey="Qbreach"
                name="Qbreach"
                stroke="#245460"
                dot={{ r: 1.5 }}
                strokeWidth={1.8}
              />
            </LineChart>
          </ResponsiveContainer>
          <DataTable
            columns={seriesColumns("rating")}
            series={result.series}
            spillwayQ={spillwayQ}
            playIndex={playIndex}
            peakIndex={peakIndex}
            onRowClick={jumpTo}
          />
        </ResultPanel>
      )}

      {tab === "breach" && (
        <ResultPanel
          title="Breach geometry"
          note="Wb, Wtop, invert zb, flow head, side slope Z, headcut xh, pipe R. BREACH analogues: BO, BT, HC."
          kind="breach"
          exportKind={exportKind}
          busy={busy}
          projectName={inputs.projectName}
        >
          <div className="grid gap-4 lg:grid-cols-2">
            <MiniChart title="Wb & head (m)">
              <LineChart data={chartData}>
                <CartesianGrid stroke="#d4cdc0" strokeDasharray="3 3" />
                <XAxis dataKey="hr" tick={{ fontSize: 11 }} tickLine={false} />
                <YAxis tick={{ fontSize: 11 }} tickLine={false} width={40} />
                <RTooltip contentStyle={{ background: "#fbf8f2", border: "1px solid #d4cdc0", fontSize: 12 }} />
                <Line type="monotone" dataKey="Wb" stroke="#1a1814" dot={false} strokeWidth={1.6} name="Wb" />
                <Line type="monotone" dataKey="depth" stroke="#245460" dot={false} strokeWidth={1.6} name="Head" />
              </LineChart>
            </MiniChart>
            <MiniChart title="Invert zb (m)">
              <LineChart data={chartData}>
                <CartesianGrid stroke="#d4cdc0" strokeDasharray="3 3" />
                <XAxis dataKey="hr" tick={{ fontSize: 11 }} tickLine={false} />
                <YAxis tick={{ fontSize: 11 }} tickLine={false} width={40} />
                <RTooltip contentStyle={{ background: "#fbf8f2", border: "1px solid #d4cdc0", fontSize: 12 }} />
                <Line type="monotone" dataKey="zb" stroke="#b45309" dot={false} strokeWidth={1.6} name="zb" />
              </LineChart>
            </MiniChart>
          </div>
          <DataTable
            columns={seriesColumns("breach")}
            series={result.series}
            spillwayQ={spillwayQ}
            playIndex={playIndex}
            peakIndex={peakIndex}
            onRowClick={jumpTo}
          />
        </ResultPanel>
      )}

      {tab === "reservoir" && (
        <ResultPanel
          title="Reservoir"
          note="Pool level and storage. BREACH: HY (water surface)."
          kind="reservoir"
          exportKind={exportKind}
          busy={busy}
          projectName={inputs.projectName}
        >
          <div className="grid gap-4 lg:grid-cols-2">
            <MiniChart title="WL (m)">
              <LineChart data={chartData}>
                <CartesianGrid stroke="#d4cdc0" strokeDasharray="3 3" />
                <XAxis dataKey="hr" tick={{ fontSize: 11 }} tickLine={false} />
                <YAxis tick={{ fontSize: 11 }} tickLine={false} width={40} />
                <RTooltip contentStyle={{ background: "#fbf8f2", border: "1px solid #d4cdc0", fontSize: 12 }} />
                <Line type="monotone" dataKey="WL" stroke="#245460" dot={false} strokeWidth={1.6} />
              </LineChart>
            </MiniChart>
            <MiniChart title="Volume (10³ m³)">
              <AreaChart data={chartData}>
                <CartesianGrid stroke="#d4cdc0" strokeDasharray="3 3" />
                <XAxis dataKey="hr" tick={{ fontSize: 11 }} tickLine={false} />
                <YAxis tick={{ fontSize: 11 }} tickLine={false} width={48} />
                <RTooltip contentStyle={{ background: "#fbf8f2", border: "1px solid #d4cdc0", fontSize: 12 }} />
                <Area type="monotone" dataKey="V" stroke="#1a1814" fill="#c4b49a" fillOpacity={0.35} strokeWidth={1.6} />
              </AreaChart>
            </MiniChart>
          </div>
          <DataTable
            columns={seriesColumns("reservoir")}
            series={result.series}
            spillwayQ={spillwayQ}
            playIndex={playIndex}
            peakIndex={peakIndex}
            onRowClick={jumpTo}
          />
        </ResultPanel>
      )}

      {tab === "diagnostics" && (
        <ResultPanel
          title="Diagnostics"
          note="Shear, velocity through the breach, pipe radius, headcut position — secondary physics and QA checks."
          kind="diagnostics"
          exportKind={exportKind}
          busy={busy}
          projectName={inputs.projectName}
        >
          <div className="grid gap-4 lg:grid-cols-2">
            <MiniChart title="τ (Pa)">
              <LineChart data={chartData}>
                <CartesianGrid stroke="#d4cdc0" strokeDasharray="3 3" />
                <XAxis dataKey="hr" tick={{ fontSize: 11 }} tickLine={false} />
                <YAxis tick={{ fontSize: 11 }} tickLine={false} width={48} />
                <RTooltip contentStyle={{ background: "#fbf8f2", border: "1px solid #d4cdc0", fontSize: 12 }} />
                <Line type="monotone" dataKey="tau" stroke="#7c2d12" dot={false} strokeWidth={1.6} />
              </LineChart>
            </MiniChart>
            <MiniChart title="Velocity through breach (m/s)">
              <LineChart data={chartData}>
                <CartesianGrid stroke="#d4cdc0" strokeDasharray="3 3" />
                <XAxis dataKey="hr" tick={{ fontSize: 11 }} tickLine={false} />
                <YAxis tick={{ fontSize: 11 }} tickLine={false} width={40} />
                <RTooltip contentStyle={{ background: "#fbf8f2", border: "1px solid #d4cdc0", fontSize: 12 }} />
                <Line type="monotone" dataKey="velocity" stroke="#245460" dot={false} strokeWidth={1.6} name="v" />
              </LineChart>
            </MiniChart>
            <MiniChart title="xh & R (m)">
              <LineChart data={chartData}>
                <CartesianGrid stroke="#d4cdc0" strokeDasharray="3 3" />
                <XAxis dataKey="hr" tick={{ fontSize: 11 }} tickLine={false} />
                <YAxis tick={{ fontSize: 11 }} tickLine={false} width={40} />
                <RTooltip contentStyle={{ background: "#fbf8f2", border: "1px solid #d4cdc0", fontSize: 12 }} />
                <Line type="monotone" dataKey="xH" stroke="#b45309" dot={false} strokeWidth={1.6} name="xh" />
                <Line type="monotone" dataKey="R" stroke="#245460" dot={false} strokeWidth={1.6} name="R" />
              </LineChart>
            </MiniChart>
          </div>
          <DataTable
            columns={seriesColumns("diagnostics")}
            series={result.series}
            spillwayQ={spillwayQ}
            playIndex={playIndex}
            peakIndex={peakIndex}
            onRowClick={jumpTo}
          />
        </ResultPanel>
      )}

      {tab === "export" && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Export Excel</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground leading-relaxed">
              Each download is an <strong className="text-foreground">.xlsx</strong> file with a{" "}
              <strong className="text-foreground">Data</strong> table (and Summary metrics where relevant) plus a{" "}
              <strong className="text-foreground">Chart</strong> sheet with an embedded graph image. Open the Data
              sheet in Excel to build a native editable chart (select columns → Insert → Line chart). Each result
              tab also has its own <strong className="text-foreground">Download HTML</strong> button next to
              "Download Excel" for a standalone, shareable copy of just that chart.
            </p>
            <p className="text-xs text-muted-foreground">
              Requires <code className="rounded bg-muted px-1">npm install exceljs</code> once in the project folder.
            </p>
            <div className="flex flex-wrap gap-2">
              {(
                [
                  ["summary", "Summary only"],
                  ["hydrograph", "Hydrograph Q(t)"],
                  ["rating", "Rating curve"],
                  ["breach", "Breach geometry"],
                  ["reservoir", "Reservoir WL / V"],
                  ["diagnostics", "Diagnostics"],
                  ["full", "Full time series"],
                ] as [ExportKind, string][]
              ).map(([k, label]) => (
                <Button
                  key={k}
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={!!busy}
                  onClick={() => exportKind(k)}
                >
                  <Download className="size-4" />
                  {busy === k ? "Writing…" : label}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Kpi({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2.5">
      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="font-mono text-sm tabular-nums text-foreground">{value}</p>
      {hint ? <p className="text-[10px] text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

function ResultPanel({
  title,
  note,
  kind,
  exportKind,
  busy,
  projectName,
  children,
}: {
  title: string;
  note: string;
  kind: ExportKind;
  exportKind: (k: ExportKind) => void;
  busy: ExportKind | null;
  projectName: string;
  children: React.ReactNode;
}) {
  const chartRef = useRef<HTMLDivElement>(null);
  const isBusy = busy === kind;

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2 pb-2">
        <div>
          <CardTitle className="text-base">{title}</CardTitle>
          <p className="mt-0.5 text-[11px] text-muted-foreground">{note}</p>
        </div>
        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={isBusy}
            onClick={() => downloadChartHtml(chartRef.current, title, projectName)}
          >
            <Code2 className="size-4" />
            Download HTML
          </Button>
          <Button type="button" size="sm" variant="outline" disabled={isBusy} onClick={() => exportKind(kind)}>
            <Download className="size-4" />
            {isBusy ? "Writing…" : "Download Excel"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div ref={chartRef}>{children}</div>
      </CardContent>
    </Card>
  );
}

function MiniChart({ title, children }: { title: string; children: React.ReactElement }) {
  return (
    <div>
      <p className="mb-1 text-xs font-medium text-muted-foreground">{title}</p>
      <ResponsiveContainer width="100%" height={220}>
        {children}
      </ResponsiveContainer>
    </div>
  );
}

/**
 * Synced, scrollable time-series table — the BRCH-J-style "table linked to
 * the animation": clicking a row jumps the cross-section slider to that
 * timestep. Header row and the leading time column stay pinned while the
 * rest scrolls horizontally, and the whole table scrolls vertically once
 * it grows past a comfortable height (a run at dt=2s over a few hours can
 * be thousands of rows).
 */
function DataTable({
  columns,
  series,
  spillwayQ,
  playIndex,
  peakIndex,
  onRowClick,
}: {
  columns: { key: ColumnKey; header: string; unit: string }[];
  series: SimStep[];
  spillwayQ: number;
  playIndex: number;
  peakIndex: number;
  onRowClick: (index: number) => void;
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <div className="max-h-80 overflow-auto">
        <table className="w-full border-collapse text-[11px]">
          <thead>
            <tr>
              {columns.map((c, i) => (
                <th
                  key={c.key}
                  className={cn(
                    "sticky top-0 z-10 whitespace-nowrap border-b border-border bg-muted px-2.5 py-1.5 text-left font-medium text-muted-foreground",
                    i === 0 && "sticky left-0 z-20",
                  )}
                >
                  {c.header} <span className="text-[9px] text-muted-foreground/70">({c.unit})</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {series.map((step, index) => {
              const isCurrent = index === playIndex;
              const isPeak = index === peakIndex;
              return (
                <tr
                  key={index}
                  onClick={() => onRowClick(index)}
                  className={cn(
                    "cursor-pointer border-b border-border/60 transition-colors hover:bg-accent/10",
                    isCurrent && "bg-accent/20",
                    isPeak && !isCurrent && "bg-warn/10",
                  )}
                >
                  {columns.map((c, i) => (
                    <td
                      key={c.key}
                      className={cn(
                        "whitespace-nowrap px-2.5 py-1 font-mono tabular-nums text-foreground",
                        i === 0 && "sticky left-0 z-[5] bg-card",
                        isCurrent && i === 0 && "bg-accent/20",
                        isPeak && !isCurrent && i === 0 && "bg-warn/10",
                      )}
                    >
                      {cellValue(step, c.key, spillwayQ)}
                      {isPeak && i === 0 && <span className="ml-1 text-[9px] text-warn">peak</span>}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
