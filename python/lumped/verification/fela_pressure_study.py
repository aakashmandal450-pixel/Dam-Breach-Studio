"""Pipe water pressure on the opening walls vs the single-pressure stability number.
Square opening B = D = 1, c_u0 = 1, gamma = 1 (gamma B/c_u0 = 1), gamma_w = 0.5 (gamma_w/gamma = 0.5).
Full pipe: p = p_cr + gw (z_cr - z); by the isotropic shift (Tresca), only sigma_s - p_cr matters, so
p_cr = 0 is used and N_full = (sigma_s - p_cr)/c_u0 at collapse.
Part-full: p = gw (z_ws - z) below the free surface z_ws = z_inv + y, zero above; roof dry."""
import fela_v2 as f, sys, time
gw = 0.5
out = []
def row(label, C, rho, pfun):
    t = time.time()
    lb, ub, m = f.run("rect", C, 1.0, 1.0, 0.1, rho=rho, pressure=pfun)
    a, b = lb["audit"], ub["audit"]
    aud = max(a["equilibrium"], a["traction_and_bc"], a["yield_excess"], b["incompressibility"],
              abs(b["recomputed"] - b["objective"]))
    s = f"{label:44s} [{lb['value']:7.3f}, {ub['value']:7.3f}]  audit {aud:.0e}  {time.time()-t:.0f}s"
    print(s, flush=True); out.append(s)
    return lb["value"], ub["value"]
for C, rho in [(1, 0.0), (2, 0.0), (4, 0.0), (2, 0.25)]:
    zc, zi = -C, -C - 1.0
    out.append(f"\n--- C/B = {C}, rho B/c_u0 = {rho}, gamma B/c_u0 = 1, gamma_w B/c_u0 = {gw}"); print(out[-1])
    row("dry / uniform sigma_t (N0)", C, rho, f.no_pressure)
    row("full, hydrostatic, p_cr = 0", C, rho, f.hydrostatic(gw, zc))
    row("part-full y = 0.5 D (roof dry)", C, rho, f.hydrostatic(gw, zi + 0.5))
    row("part-full y = 0.9 D (roof dry)", C, rho, f.hydrostatic(gw, zi + 0.9))
open(sys.argv[1], "w").write("\n".join(out) + "\n")
