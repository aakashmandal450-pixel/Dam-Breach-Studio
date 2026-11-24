"""Range check of the partial-water wall formula (5.17):
   lam_formula = (3.776 + 2 rho') / (1 - r xi^2),  lam = gamma*H/c_u0, rho' = rho*H/c_u0, r = gamma_w/gamma.
Compared with our rigorous lower bound (h = 0.05) in two ways:
 (a) ratio form (mesh error removed): F_ratio = [(1 - r xi^2)^-1 * LB_dry(rho')] / LB_wet  <= 1 means safe side
 (b) absolute: lam_formula / LB_wet (LB is ~0.8 % below the converged value at this mesh)."""
import sys, fela_cut as fc, fela_cut_wet as fw
out = []
dry = {}
for rho in (0.0, 0.5):
    dry[rho] = fc.lower(0.05, rho)[0]
for r in (0.4, 0.5, 0.6):
    for rho in (0.0, 0.5):
        for xi in (0.25, 0.5, 0.75):
            lb, aud, ye = fw.lower_wet(0.05, xi, gw_hat=r, rho=rho)
            form = (3.776 + 2 * rho) / (1 - r * xi * xi)
            ratio_pred = dry[rho] / (1 - r * xi * xi)
            s = (f"r={r:.1f} rho'={rho:.2f} xi={xi:.2f}: LB_wet {lb:.4f}  ratio-form/LB {ratio_pred/lb:.4f}  "
                 f"formula {form:.4f}  formula/LB {form/lb:.4f}  audit {aud:.0e} yield+ {ye:.0e}")
            print(s, flush=True); out.append(s)
open(sys.argv[1], "w").write("\n".join(out) + "\n")
