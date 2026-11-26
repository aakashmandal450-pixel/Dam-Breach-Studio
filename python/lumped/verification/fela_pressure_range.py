"""Range test of the crown-pressure treatment (draft 4.6 §5.5b).
For each geometry: N0 = critical (sigma_s - p_cr)/c_u0 with a single pressure (exact for a uniform one),
N_full with the hydrostatic increase below the crown, N_part with a part-full pipe (y = 0.9 a_p, roof dry).
beta = (N - N0)/(gw*a_p/c_u0): the fraction of the invert-level hydrostatic increment that acts as support.
Expected 0 <= beta <= 1 (pressure everywhere between the crown value and the invert value)."""
import itertools, sys, time
from multiprocessing import Pool
import fela_v2 as f

def job(args):
    ap, C, gam, rho, gw = args
    h = 0.1 if C <= 2 else 0.15
    t = time.time()
    m = f.rect_mesh(C, ap, h)
    zc, zi = -C, -C - ap
    res = {}
    for name, pf in [("N0", f.no_pressure), ("full", f.hydrostatic(gw, zc)), ("part", f.hydrostatic(gw, zi + 0.9 * ap))]:
        if name == "N0" and gw != GW[0]:
            continue
        lb = f.lower_bound(m, gam, rho, pf); ub = f.upper_bound(m, gam, rho, pf)
        a, b = lb["audit"], ub["audit"]
        aud = max(a["equilibrium"], a["traction_and_bc"], a["yield_excess"], a["side_excess"], a["bottom_excess"],
                  b["incompressibility"], abs(b["recomputed"] - b["objective"]))
        res[name] = (lb["value"], ub["value"], aud)
    return args, res, time.time() - t

AP, CC, GAM, RHO, GW = (0.5, 1.0, 2.0), (0.5, 1, 2, 4, 8), (0.5, 2.0), (0.0, 0.5), (0.25, 1.0)
if __name__ == "__main__":
    out = open(sys.argv[1], "w")
    geos = list(itertools.product(AP, CC, GAM, RHO))
    jobs = [(ap, C, g, r, gw) for (ap, C, g, r) in geos for gw in GW]
    n0 = {}
    hdr = "a_p/b  C/b  gb/c  rho  gw*b/c | N0 lower-upper | N_full lower-upper | beta_full | N_part(0.9) lower-upper | beta_part | audit | s"
    print(hdr, flush=True); out.write(hdr + "\n"); out.flush()
    done = 0
    with Pool(2) as pool:
        for args, res, dt in pool.imap(job, jobs):
            done += 1
            ap, C, g, r, gw = args
            if "N0" in res: n0[(ap, C, g, r)] = res["N0"]
            N0 = n0.get((ap, C, g, r))
            if N0 is None:   # gw[0] job of this geometry not yet back (imap keeps order, so this cannot happen)
                N0 = f.run("rect", C, ap, g, 0.1 if C <= 2 else 0.15, rho=r)[0]["value"], None, 0
            mid0 = 0.5 * (N0[0] + N0[1])
            fu, pa = res["full"], res["part"]
            bf = (0.5 * (fu[0] + fu[1]) - mid0) / (gw * ap)
            bp = (0.5 * (pa[0] + pa[1]) - mid0) / (gw * ap)
            aud = max(fu[2], pa[2], N0[2] if len(N0) > 2 and N0[2] is not None else 0)
            s = (f"{ap:4.1f} {C:4.1f} {g:4.1f} {r:4.2f} {gw:5.2f} | {N0[0]:8.3f} {N0[1]:8.3f} | {fu[0]:8.3f} {fu[1]:8.3f} | "
                 f"{bf:6.3f} | {pa[0]:8.3f} {pa[1]:8.3f} | {bp:6.3f} | {aud:.0e} | {dt:4.0f}  [{done}/{len(jobs)}]")
            print(s, flush=True); out.write(s + "\n"); out.flush()
