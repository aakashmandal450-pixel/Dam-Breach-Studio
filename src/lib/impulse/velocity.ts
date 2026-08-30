/** Impact speed from free-fall vertical drop of the slide centre of mass. */
export function impactVelocityFromFallHeight(fallHeightM: number): number {
  const H = Math.max(fallHeightM, 0);
  return Math.sqrt(2 * 9.81 * H);
}

/**
 * Optional friction reduction along a slope of angle α (deg) with friction coeff μ.
 * Vs = √(2 g H (1 − μ / tan α)) when tan α > μ; else 0.
 */
export function impactVelocityWithFriction(
  fallHeightM: number,
  alphaDeg: number,
  mu = 0.3,
): number {
  const H = Math.max(fallHeightM, 0);
  const tanA = Math.tan((Math.max(alphaDeg, 1) * Math.PI) / 180);
  const factor = Math.max(0, 1 - mu / tanA);
  return Math.sqrt(2 * 9.81 * H * factor);
}
