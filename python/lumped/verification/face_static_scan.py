"""Draft F-1, static scan (no driver coupling): the P1 downstream face at three pipe stages from the
converged P1 run (start, mid-growth, roof collapse), G1 and G2 under P0 / P1 / P2, suction c_s 0 / 1 / 3 kPa,
plus the global 2-D wedge (whole face, plane strain, no sides) for A3. Inputs per draft F-1 §4.
Writes face_static_scan.txt next to this script."""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
from lumped import face as fc            # noqa: E402
from lumped.geometry import Dam          # noqa: E402

G = 9.81
RHO_D, GS, W = 1696.0, 2.65, 0.1149
N = 1 - RHO_D / (GS * 1000)
GM, GSAT = RHO_D * (1 + W) * G, (RHO_D + N * 1000) * G
DAM = Dam(1.3, 1.83, 3.0, 3.0, 100.0)
BETA = math.atan(1 / DAM.zd)
STAGES = [("start (40 mm)", 0.040, 0.240), ("mid", 0.148, 0.296), ("roof collapse", 0.290, 0.369)]   # b, z_cr
D_THETA = N * (1 - W * GS / (GS / (RHO_D / 1000) - 1))
PSI_F, T_OBS = 0.11, 828.0


def main():
    L = [f"P1 downstream face, static scan (draft F-1). c' = 0, tan phi' = 0.625, gamma {GM/1e3:.2f}/{GSAT/1e3:.2f} kN/m3,"
         f" w = b, K0 = 1 - sin phi'; minimum blocks t >= 0.25 b, L >= b/2 ('*' = minimum on that limit)", ""]
    L.append("P1 wetting thickness above the crown after 828 s (Green-Ampt F.6, h_p = 0, psi_f 0.11 m, "
             f"d_theta {D_THETA:.3f}):")
    deltas = {}
    for K in (1e-7, 3e-6, 1e-5):
        deltas[K] = fc.green_ampt_up(1e-6, T_OBS, K, PSI_F, D_THETA)
        L.append(f"  K_s {K:.0e} m/s: delta = {deltas[K]:.3f} m")
    L.append("")
    prof = fc.Profile.from_dam(DAM)
    ph = fc.casagrande_phreatic(DAM, 1.1)
    xe, ze = fc.casagrande_exit(DAM, 1.1)
    L.append(f"P2 phreatic exit on the face (Casagrande): x {xe:.2f} m, z {ze:.3f} m")
    L.append("")
    hdr = f"{'stage':15s} {'b':>5s} {'x_d':>5s} | {'scenario':22s} | {'G1 FS':>8s} {'t':>5s} {'L':>5s} | {'G2 FS':>8s} {'alpha':>5s} {'L':>5s}"
    L.append(hdr); L.append("-" * len(hdr))
    for name, b, zcr in STAGES:
        x_d = prof.daylight(zcr)
        cases = []
        for cs in (0.0, 1000.0, 3000.0):
            cases.append((f"P0 c_s {cs/1e3:.0f} kPa", fc.Scenario("P0"), cs))
        for cs in (0.0, 3000.0):
            cases.append((f"P1 K 3e-6 c_s {cs/1e3:.0f} kPa", fc.Scenario("P1", delta=deltas[3e-6]), cs))
        cases.append(("P1 K 1e-5 c_s 3 kPa", fc.Scenario("P1", delta=deltas[1e-5]), 3000.0))
        for cs in (0.0, 3000.0):
            cases.append((f"P2 c_s {cs/1e3:.0f} kPa", fc.Scenario("P2", phreatic=ph), cs))
        for lab, sc, cs in cases:
            s = fc.FaceSoil(0.0, 0.625, cs, GM, GSAT, sides=True)
            g1 = fc.critical_G1(prof, zcr, BETA, DAM.x_c1, s, sc, b, t_max=DAM.H - zcr, nt=30, nb=30)
            g2 = fc.critical_G2(prof, zcr, BETA, DAM.x_c1, s, sc, b, na=30, nb=30)
            m1 = "*" if g1.info["at_limit"] else " "
            m2 = "*" if g2.info["at_limit"] else " "
            L.append(f"{name:15s} {b:5.3f} {x_d:5.2f} | {lab:22s} | {g1.FS:7.3f}{m1} {g1.t:5.3f} {g1.x_d - g1.x_b:5.2f} | "
                     f"{g2.FS:7.3f}{m2} {math.degrees(g2.theta):5.1f} {g2.x_d - g2.x_b:5.2f}")
        L.append("")
    L.append("A3 global check: G2 per unit width over the whole face (plane strain, no sides), toe at the "
             "collapse-stage outlet level:")
    zcr = STAGES[-1][2]
    for lab, sc, cs in (("P0 c_s 0", fc.Scenario("P0"), 0.0), ("P2 c_s 0", fc.Scenario("P2", phreatic=ph), 0.0),
                        ("P2 c_s 3 kPa", fc.Scenario("P2", phreatic=ph), 3000.0)):
        s = fc.FaceSoil(0.0, 0.625, cs, GM, GSAT, sides=False)
        g = fc.critical_G2(prof, zcr, BETA, DAM.x_c1, s, sc, 1.0, na=30, nb=30, b=0.29)
        L.append(f"  {lab:14s}: FS {g.FS:.3f}{'*' if g.info['at_limit'] else ''} at alpha {math.degrees(g.theta):.1f} deg, "
                 f"L {g.x_d - g.x_b:.2f} m")
    L += limit_sensitivity()
    text = "\n".join(L)
    print(text)
    (HERE / "face_static_scan.txt").write_text(text + "\n", encoding="utf-8")


def limit_sensitivity():
    """Review 2026-11-26: the minimum block sizes are numerical regularisation; report their effect."""
    prof = fc.Profile.from_dam(DAM)
    ph = fc.casagrande_phreatic(DAM, 1.1)
    L = ["", "Sensitivity to the numerical block limits (roof-collapse stage, b 0.29 m):",
         f"{'t_min/b':>7s} {'L_min/b':>7s} | {'P0 c_s 0 G1':>11s} {'G2':>7s} | {'P2 c_s 0 G1':>11s} {'G2':>7s}"]
    b, zcr = 0.29, 0.369
    for cm, lm in ((0.125, 0.25), (0.25, 0.5), (0.5, 1.0)):
        row = []
        for sc in (fc.Scenario("P0"), fc.Scenario("P2", phreatic=ph)):
            s = fc.FaceSoil(0.0, 0.625, 0.0, GM, GSAT, sides=True)
            g1 = fc.critical_G1(prof, zcr, BETA, DAM.x_c1, s, sc, b, t_max=DAM.H - zcr, nt=30, nb=30, c_min=cm, l_min=lm)
            g2 = fc.critical_G2(prof, zcr, BETA, DAM.x_c1, s, sc, b, na=30, nb=30, c_min=cm, l_min=lm)
            row += [f"{g1.FS:10.3f}{'*' if g1.info['at_limit'] else ' '}", f"{g2.FS:6.3f}{'*' if g2.info['at_limit'] else ' '}"]
        L.append(f"{cm:7.3f} {lm:7.3f} | {row[0]} {row[1]} | {row[2]} {row[3]}")
    return L


if __name__ == "__main__":
    main()
