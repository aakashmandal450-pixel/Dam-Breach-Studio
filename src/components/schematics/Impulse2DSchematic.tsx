import type { Impulse2DInputs, Impulse2DResult } from "@/lib/impulse/types";

interface Props {
  inputs: Impulse2DInputs;
  result: Impulse2DResult | null;
}

export function Impulse2DSchematic({ inputs, result }: Props) {
  const W = 660;
  const H = 290;
  const bed = 255;
  const waterY = 165;
  const impactX = 175;
  const shoreLeft = 18;
  const alphaRad = (Math.min(Math.max(inputs.alphaDeg, 15), 80) * Math.PI) / 180;
  const slopeTopX = shoreLeft + 8;
  const slopeTopY = 30;
  const impactY = waterY;
  // Place slide higher on the slope so it does not cover α
  const slideAlong = 95;
  const sx = impactX - Math.cos(alphaRad) * slideAlong;
  const sy = impactY - Math.sin(alphaRad) * slideAlong;
  const waveStart = impactX + 12;
  const waveEnd = W - 36;
  const aMpx = result ? Math.min(50, (result.aM / Math.max(inputs.h, 0.1)) * (bed - waterY) * 1.0) : 24;
  const HMpx = result ? Math.min(60, (result.HM / Math.max(inputs.h, 0.1)) * (bed - waterY) * 1.0) : 36;
  const crest1x = waveStart + 100;
  const crest2x = waveStart + 215;
  const troughX = waveStart + 155;
  const fmt = (v: number, d = 1) => (Number.isFinite(v) ? v.toFixed(d) : "—");

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Impulse wave 2D definition sketch">
      <defs>
        <linearGradient id="waterGrad2d" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#8fc4dc" />
          <stop offset="100%" stopColor="#5a9bb8" />
        </linearGradient>
        <linearGradient id="slideGrad2d" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#a67c52" />
          <stop offset="100%" stopColor="#6b4f35" />
        </linearGradient>
        <marker id="arr2d" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
          <polygon points="0 0, 7 2.5, 0 5" fill="#1a1a1a" />
        </marker>
      </defs>

      <rect width={W} height={H} fill="#ffffff" />
      <rect x={0} y={bed} width={W} height={H - bed} fill="#1a1a1a" />
      <line x1={0} y1={bed} x2={W} y2={bed} stroke="#111" strokeWidth="1.5" />

      <polygon
        points={`${shoreLeft},${bed} ${slopeTopX},${slopeTopY} ${impactX},${impactY} ${impactX},${bed}`}
        fill="#6b6b6b"
        stroke="#1a1a1a"
        strokeWidth="1.2"
      />

      <path d={`M${impactX},${waterY} L${W},${waterY} L${W},${bed} L${impactX},${bed} Z`} fill="url(#waterGrad2d)" opacity="0.95" />
      <line x1={impactX} y1={waterY} x2={W - 10} y2={waterY} stroke="#1a5270" strokeWidth="1.3" strokeDasharray="6 3" />

      {/* Slide mass — higher on slope */}
      <ellipse
        cx={(sx + impactX) / 2 - 8}
        cy={(sy + impactY) / 2 - 14}
        rx={36}
        ry={16}
        fill="url(#slideGrad2d)"
        stroke="#3d2914"
        strokeWidth="1"
        transform={`rotate(${-inputs.alphaDeg * 0.4} ${(sx + impactX) / 2 - 8} ${(sy + impactY) / 2 - 14})`}
      />

      {/* Thickness s (small dimension tick on the mass) */}
      <text x={sx - 28} y={sy - 22} fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">
        {`s = ${fmt(inputs.s, 1)} m`}
      </text>
      <text x={sx - 28} y={sy - 8} fontSize="9" fontFamily="Georgia, serif" fill="#666">
        (prefer 3-D for b)
      </text>

      {/* Vs arrow */}
      <line
        x1={sx + 4}
        y1={sy - 10}
        x2={sx + 4 + Math.cos(alphaRad) * 36}
        y2={sy - 10 + Math.sin(alphaRad) * 36}
        stroke="#1a1a1a"
        strokeWidth="1.3"
        markerEnd="url(#arr2d)"
      />
      <text x={sx + 16 + Math.cos(alphaRad) * 18} y={sy - 18 + Math.sin(alphaRad) * 14} fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">
        {`Vs = ${fmt(inputs.Vs, 1)} m/s`}
      </text>

      {/* Origin */}
      <circle cx={impactX} cy={impactY} r={3.2} fill="#fff" stroke="#1a1a1a" strokeWidth="1.2" />
      <line x1={impactX} y1={impactY} x2={impactX + 44} y2={impactY} stroke="#1a1a1a" strokeWidth="1" markerEnd="url(#arr2d)" />
      <text x={impactX + 48} y={impactY - 4} fontSize="11" fontFamily="Georgia, serif" fill="#1a1a1a">x</text>
      <line x1={impactX} y1={impactY} x2={impactX} y2={impactY - 38} stroke="#1a1a1a" strokeWidth="1" markerEnd="url(#arr2d)" />
      <text x={impactX + 5} y={impactY - 40} fontSize="11" fontFamily="Georgia, serif" fill="#1a1a1a">z</text>

      {/* Compact α arc near toe only — small radius so it does not hit the slide */}
      {(() => {
        const arcR = 28;
        const x1 = impactX - arcR;
        const y1 = impactY;
        const x2 = impactX - arcR * Math.cos(alphaRad);
        const y2 = impactY - arcR * Math.sin(alphaRad);
        return (
          <g>
            <path d={`M ${x1} ${y1} A ${arcR} ${arcR} 0 0 1 ${x2} ${y2}`} fill="none" stroke="#1a1a1a" strokeWidth="1" />
            <text x={impactX - arcR - 8} y={impactY + 14} fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">
              {`α = ${fmt(inputs.alphaDeg, 0)}°`}
            </text>
          </g>
        );
      })()}

      <path
        d={`M${waveStart},${waterY}
            C${waveStart + 28},${waterY} ${crest1x - 32},${waterY - aMpx} ${crest1x},${waterY - aMpx}
            C${crest1x + 22},${waterY - aMpx} ${troughX - 12},${waterY + 7} ${troughX},${waterY + 5}
            C${troughX + 18},${waterY + 3} ${crest2x - 28},${waterY - aMpx * 0.85} ${crest2x},${waterY - aMpx * 0.85}
            C${crest2x + 32},${waterY - aMpx * 0.85} ${waveEnd - 36},${waterY} ${waveEnd},${waterY}`}
        fill="none"
        stroke="#1a5270"
        strokeWidth="1.7"
      />

      <line x1={crest1x + 10} y1={waterY - HMpx} x2={crest1x + 10} y2={waterY + 5} stroke="#1a1a1a" strokeWidth="0.8" />
      <text x={crest1x + 15} y={waterY - HMpx / 2 + 3} fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">
        {`HM = ${fmt(result?.HM ?? 0, 2)} m`}
      </text>
      <line x1={crest1x - 10} y1={waterY - aMpx} x2={crest1x - 10} y2={waterY} stroke="#1a1a1a" strokeWidth="0.8" strokeDasharray="3 2" />
      <text x={crest1x - 70} y={waterY - aMpx / 2 + 3} fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">
        {`aM = ${fmt(result?.aM ?? 0, 2)} m`}
      </text>

      <line x1={W - 24} y1={waterY} x2={W - 24} y2={bed} stroke="#1a1a1a" strokeWidth="0.8" />
      <text x={W - 20} y={(waterY + bed) / 2 + 3} fontSize="10" fontFamily="Georgia, serif" fill="#1a1a1a">
        {`h = ${fmt(inputs.h, 1)} m`}
      </text>
      {result && (
        <text x={waveStart + 36} y={bed - 8} fontSize="10" fontFamily="Georgia, serif" fill="#444">
          {`x = ${fmt(inputs.x, 0)} m`}
        </text>
      )}
    </svg>
  );
}
