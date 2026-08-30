import type { Impulse3DInputs, Impulse3DResult } from "@/lib/impulse/types";

interface Props {
  inputs: Impulse3DInputs;
  result: Impulse3DResult | null;
}

/** Plan view with explicit slide block: thickness s and width b. */
export function Impulse3DSchematic({ inputs, result }: Props) {
  const W = 660;
  const H = 300;
  const cx = 210;
  const cy = 160;
  const fmt = (v: number, d = 1) => (Number.isFinite(v) ? v.toFixed(d) : "—");
  const gammaRad = (inputs.gammaDeg * Math.PI) / 180;
  const rScale = 0.25;
  const rPx = Math.min(150, Math.max(40, inputs.r * rScale * 0.12));
  const rMpx = result ? Math.min(140, Math.max(30, result.rM * rScale * 0.12)) : 65;

  const lobeX = cx + rPx * Math.cos(gammaRad - Math.PI / 2);
  const lobeY = cy + rPx * Math.sin(gammaRad - Math.PI / 2);

  // Slide block in plan: width b across, thickness s along slope direction (schematic)
  const blockW = Math.min(70, Math.max(28, inputs.b * 0.35));
  const blockS = Math.min(40, Math.max(16, inputs.s * 0.4));
  const blockX = cx - 55;
  const blockY = cy - 35;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Impulse wave 3D definition sketch">
      <rect width={W} height={H} fill="#ffffff" />

      <ellipse cx={cx + 70} cy={cy + 8} rx={200} ry={105} fill="#8fc4dc" opacity="0.55" stroke="#1a5270" strokeWidth="1" />
      <path d={`M24,36 L${cx - 28},${cy - 85} L${cx - 14},${cy + 95} L24,268 Z`} fill="#6b6b6b" stroke="#1a1a1a" strokeWidth="1.2" />

      {/* Slide block with s and b */}
      <g transform={`rotate(${-18} ${blockX + blockW / 2} ${blockY + blockS / 2})`}>
        <rect x={blockX} y={blockY} width={blockW} height={blockS} fill="#a67c52" stroke="#3d2914" strokeWidth="1.2" rx="2" />
        {/* width b dimension */}
        <line x1={blockX} y1={blockY - 8} x2={blockX + blockW} y2={blockY - 8} stroke="#1a1a1a" strokeWidth="0.8" />
        <text x={blockX + blockW / 2} y={blockY - 12} textAnchor="middle" fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">
          {`b = ${fmt(inputs.b, 0)} m`}
        </text>
        {/* thickness s dimension */}
        <line x1={blockX + blockW + 8} y1={blockY} x2={blockX + blockW + 8} y2={blockY + blockS} stroke="#1a1a1a" strokeWidth="0.8" />
        <text x={blockX + blockW + 12} y={blockY + blockS / 2 + 3} fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">
          {`s = ${fmt(inputs.s, 1)} m`}
        </text>
      </g>
      <text x={blockX - 4} y={blockY + blockS + 28} fontSize="9" fontFamily="Georgia, serif" fill="#444">
        slide block
      </text>

      <circle cx={cx} cy={cy} r={4.5} fill="#fff" stroke="#1a1a1a" strokeWidth="1.4" />
      <text x={cx - 14} y={cy + 18} fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">impact</text>

      <circle cx={cx} cy={cy} r={rMpx} fill="none" stroke="#c0392b" strokeWidth="1" strokeDasharray="4 3" />
      <text x={cx + rMpx + 4} y={cy - 4} fontSize="10" fontFamily="Georgia, serif" fill="#c0392b">
        {`rM = ${fmt(result?.rM ?? 0, 0)} m`}
      </text>
      <circle cx={cx} cy={cy} r={rPx} fill="none" stroke="#1a1a1a" strokeWidth="1.1" />

      <line x1={cx} y1={cy} x2={cx} y2={cy - 120} stroke="#1a1a1a" strokeWidth="1" strokeDasharray="3 2" />
      <text x={cx + 6} y={cy - 110} fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">γ = 0° (main lobe)</text>

      <line x1={cx} y1={cy} x2={lobeX} y2={lobeY} stroke="#1a1a1a" strokeWidth="1.5" />
      <circle cx={lobeX} cy={lobeY} r={4} fill="#1a5270" />
      <text x={lobeX + 8} y={lobeY + 4} fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">
        {`r = ${fmt(inputs.r, 0)} m`}
      </text>

      <path
        d={`M ${cx} ${cy - 45} A 45 45 0 0 ${inputs.gammaDeg >= 0 ? 1 : 0} ${cx + 45 * Math.sin(gammaRad)} ${cy - 45 * Math.cos(gammaRad)}`}
        fill="none"
        stroke="#1a1a1a"
        strokeWidth="1"
      />
      <text x={cx + 20} y={cy - 50} fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">
        {`γ = ${fmt(inputs.gammaDeg, 0)}°`}
      </text>

      <g transform="translate(430, 36)">
        <text x={0} y={0} fontSize="11" fontFamily="Georgia, serif" fontWeight="600" fill="#1a1a1a">At gauge</text>
        <text x={0} y={20} fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">{`aM = ${fmt(result?.aM ?? 0, 2)} m`}</text>
        <text x={0} y={36} fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">{`HM = ${fmt(result?.HM ?? 0, 2)} m`}</text>
        <text x={0} y={52} fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">{`ar = ${fmt(result?.ar ?? 0, 2)} m`}</text>
        <text x={0} y={68} fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">{`Hr = ${fmt(result?.Hr ?? 0, 2)} m`}</text>
        <text x={0} y={90} fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">{`h = ${fmt(inputs.h, 1)} m`}</text>
        <text x={0} y={106} fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">{`α = ${fmt(inputs.alphaDeg, 0)}°`}</text>
        <text x={0} y={122} fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">{`Vs = ${fmt(inputs.Vs, 1)} m/s`}</text>
        <text x={0} y={138} fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">{`Hfall = ${fmt(inputs.fallHeight, 0)} m`}</text>
      </g>
    </svg>
  );
}
