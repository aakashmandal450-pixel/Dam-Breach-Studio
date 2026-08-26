import type { ReactNode } from "react";
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
import type { SimResult } from "@/lib/breach/types";
import { formatNumber } from "@/lib/utils";

export function ResultCharts({ result, playIndex }: { result: SimResult; playIndex: number }) {
  const data = result.series.map((s) => ({
    hr: Number((s.t / 3600).toFixed(4)),
    Q: Number(s.Q.toFixed(3)),
    Wb: Number(s.Wb.toFixed(3)),
    depth: Number((s.WL - s.zb > 0 ? s.WL - s.zb : 0).toFixed(3)),
  }));
  const cursor = data[Math.min(playIndex, data.length - 1)];

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ChartCard title="Outflow hydrograph" unit="m³/s">
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#d4cdc0" strokeDasharray="3 3" />
            <XAxis dataKey="hr" tick={{ fontSize: 11 }} tickLine={false} />
            <YAxis tick={{ fontSize: 11 }} tickLine={false} width={48} />
            <RTooltip
              contentStyle={{ background: "#fbf8f2", border: "1px solid #d4cdc0", fontSize: 12 }}
              formatter={(v) => [`${formatNumber(Number(v), 2)} m³/s`, "Q"]}
            />
            <Area type="monotone" dataKey="Q" stroke="#245460" fill="#3d6f82" fillOpacity={0.25} strokeWidth={1.6} />
          </AreaChart>
        </ResponsiveContainer>
        {cursor && (
          <p className="mt-1 text-xs text-muted-foreground">
            Cursor {cursor.hr.toFixed(3)} h · Q = {formatNumber(cursor.Q, 2)} m³/s
          </p>
        )}
      </ChartCard>
      <ChartCard title="Breach growth" unit="m">
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#d4cdc0" strokeDasharray="3 3" />
            <XAxis dataKey="hr" tick={{ fontSize: 11 }} tickLine={false} />
            <YAxis tick={{ fontSize: 11 }} tickLine={false} width={40} />
            <RTooltip contentStyle={{ background: "#fbf8f2", border: "1px solid #d4cdc0", fontSize: 12 }} />
            <Line type="monotone" dataKey="Wb" stroke="#1a1814" dot={false} strokeWidth={1.6} name="Wb" />
            <Line type="monotone" dataKey="depth" stroke="#245460" dot={false} strokeWidth={1.6} name="Head" />
          </LineChart>
        </ResponsiveContainer>
        <p className="mt-1 text-xs text-muted-foreground">Black = base width Wb · Teal = flow head over invert</p>
      </ChartCard>
    </div>
  );
}

function ChartCard({ title, unit, children }: { title: string; unit: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="mb-2 flex items-baseline justify-between">
        <h3 className="font-display text-base font-medium">{title}</h3>
        <span className="font-mono text-[10px] text-muted-foreground">{unit}</span>
      </div>
      {children}
    </div>
  );
}
