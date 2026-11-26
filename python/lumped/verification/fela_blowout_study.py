"""Blow-out (passive) bounds: critical (sigma_s - p_cr)/c_u0 at upward failure, square opening, dry-equivalent
(uniform internal pressure; by the shift result only sigma_s - p_cr matters). Compared with the rigid prism
(mechanism C in section form): uplift when p - sigma_s > gamma*C + 2*(c_u0*C + rho*C^2/2)/B."""
import fela_v2 as f, sys
out = []
for C, g, r in [(1, 1, 0), (2, 1, 0), (4, 1, 0), (2, 1, 0.25), (2, 2, 0)]:
    lb, ub, m = f.run("rect", C, 1.0, float(g), 0.1, rho=r, passive=True)
    prism = -(g * C + 2 * (C + r * C * C / 2))
    s = f"C/B={C} gB/c={g} rhoB/c={r}: blow-out bounds [{ub['value']:7.3f}, {lb['value']:7.3f}]  rigid prism {prism:7.3f}"
    print(s, flush=True); out.append(s)
open(sys.argv[1], "w").write("\n".join(out) + "\n")
