"""Print where the eroded dam material ended up, from a run's final_bed.npz.

Usage:  python validation\\inspect_digtsho_bed.py dt_wave7200\\final_bed.npz
Reports bed change along flow (transverse mean), eroded and deposited bulk volumes, the highest bed
elevation downstream of the original dam, and the transverse spread of the final lowering.
"""
import sys
import numpy as np

d = np.load(sys.argv[1])
zb, z0, x, y = d["z_b"], d["z0"], d["x"], d["y"]
dx, dy = float(x[1] - x[0]), float(y[1] - y[0])
chg = zb - z0
eroded = float(np.sum(np.maximum(-chg, 0.0)) * dx * dy)
deposited = float(np.sum(np.maximum(chg, 0.0)) * dx * dy)
print(f"grid {x.size} x {y.size}, dx={dx:g} m, dy={dy:g} m")
print(f"bulk eroded {eroded:,.0f} m3, bulk deposited inside the domain {deposited:,.0f} m3, "
      f"net {deposited - eroded:+,.0f} m3 (negative = material left through the downstream boundary)")
crest_end = x[np.argmax(z0.mean(axis=1) >= 0.99 * z0.max())]
print(f"\n{'x [m]':>8s} {'z0 mean':>9s} {'z final mean':>13s} {'change':>8s} {'z final max':>12s}")
for i in range(0, x.size, max(1, x.size // 24)):
    print(f"{x[i]:8.1f} {z0[i].mean():9.2f} {zb[i].mean():13.2f} {chg[i].mean():+8.2f} {zb[i].max():12.2f}")
down = x > x[np.argmax(z0.mean(axis=1))] + 25.0
print(f"\nhighest final bed downstream of the original crest: {zb[down].max():.2f} m "
      f"(original downstream bed max {z0[down].max():.2f} m)")
low = np.max(np.maximum(-chg, 0.0), axis=0)
print(f"transverse max lowering: min {low.min():.2f} m, mean {low.mean():.2f} m, max {low.max():.2f} m")
