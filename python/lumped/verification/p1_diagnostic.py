"""ARS P1 diagnostic run of the piping driver (Theory Part 5; first run, no calibration).

Prints and writes the event timeline (failure location, type, pipe dimensions, retreat distances, crater
state, water and solids budgets) and a time series. Inputs from python/calibration/cases/piping_draft:
ARS_P1.json and ARS_PIPING_DATA.md, with the stated statuses:
  geometry      H 1.3 m, crest 1.83 m, 3H:1V (measured; H conflicts with 4 ft in PAP-1017)
  pipe          40 mm square at z_inv 0.2 m (pipe size measured, elevation estimated: Chen et al. 2019)
  reservoir     constant level 1.1 m (measured level; constant-head boundary is a scenario)
  erodibility   k_d 150 cm3/(N s), tau_c 0 (measured, field JET; no HET possible for P1)
  strength      c_u0 5 kPa, rho 0 (estimated: GeoHazards 2024 model input)
  unit weights  from the as-built dry density 1.696 g/cm3 and w 11.49 % (measured), G_s 2.65 (assumed)

Usage (from the python folder):  python lumped/verification/p1_diagnostic.py [dt] [kd_cm3Ns] [t_end_s]
Writes p1_diagnostic_timeline.txt and p1_diagnostic_series.csv next to this script.
"""
import csv
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from lumped import roof                                        # noqa: E402
from lumped.geometry import Dam                                # noqa: E402
from lumped.piping_run import PipingCase, PipingRun, timeline  # noqa: E402
from lumped.stability_table import StabilityTable              # noqa: E402

G = 9.81


def main():
    dt = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    kd = float(sys.argv[2]) * 1e-6 if len(sys.argv) > 2 else 150e-6
    t_end = float(sys.argv[3]) if len(sys.argv) > 3 else 3 * 3600.0
    rho_d, Gs, w = 1696.0, 2.65, 0.1149
    n = 1 - rho_d / (Gs * 1000)
    soil = roof.Soil(c_u0=5000.0, rho=0.0, gamma_sat=(rho_d + n * 1000) * G, gamma_moist=rho_d * (1 + w) * G)
    case = PipingCase(dam=Dam(1.3, 1.83, 3.0, 3.0, 100.0), soil=soil, kd=kd, tau_c=0.0, b0=0.04, D0=0.04,
                      z_inv0=0.2, z_s0=1.1, porosity=n)
    T = StabilityTable.from_csv(str(HERE / "stability_table.csv"))
    t0 = time.time()
    r = PipingRun(case, T, dt=dt, record_every=10.0).run(t_end)
    lines = [f"ARS P1 diagnostic: dt {dt} s, k_d {kd * 1e6:g} cm3/(N s), t_end {t_end:g} s, wall time "
             f"{time.time() - t0:.1f} s",
             f"stopped: {r.stopped}",
             f"max relative water-budget error {r.max_water_err:.1e}; max solids error {r.max_solids_err:.1e}; "
             f"most cascade passes {r.passes_max}",
             "observed (PAP-1017, Chen et al. 2019): roof (soil bridge) collapse 0.22-0.23 h = 790-830 s; "
             "peak 2.98 m3/s at 0.43 h", ""]
    for L in timeline(r):
        l = L["last"]
        s = (f"{L['type']:20s} t {L['t']:8.1f} - {L['t_end']:8.1f} s  x{L['n']:4d}  dist {L['dist']:6.3f} m | "
             f"b {l['b']:.3f} D {l['D']:.3f} z_inv {l['z_inv']:.3f} x_in {l['x_in']:.2f} x_o {l['x_o']:.2f} "
             f"water_err {l['water_err']:.1e}")
        if "cr_x1" in l:
            s += (f" | crater [{l['cr_x1']:.2f}, {l['cr_x2']:.2f}] W {l['cr_W']:.3f} z_d {l['z_d']:.3f} "
                  f"z_c {l['z_c']:.3f} W_c {l['W_c']:.3f} solids_err {l.get('solids_err', 0):.1e}")
        if l.get("why"):
            s += " | " + l["why"]
        lines.append(s)
    text = "\n".join(lines)
    print(text)
    (HERE / "p1_diagnostic_timeline.txt").write_text(text + "\n", encoding="utf-8")
    keys = sorted({k for row in r.series for k in row})
    with open(HERE / "p1_diagnostic_series.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=keys); wr.writeheader(); wr.writerows(r.series)
    return 0


if __name__ == "__main__":
    sys.exit(main())
