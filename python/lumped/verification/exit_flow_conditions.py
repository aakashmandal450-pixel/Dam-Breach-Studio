"""Note R-2: outlet flow conditions over the P1 pipe stage (k_d 3.16, dt 2 s): pipe vs face-channel shear,
critical depth at the outlet. Evidence only; no erosion law adopted."""
import sys, math; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lumped.tests.test_piping_run import p1_case, TABLE
from lumped.piping_run import PipingRun
from lumped import piping as pp
from lumped.stability_table import StabilityTable
T=StabilityTable.from_csv(str(TABLE))
r=PipingRun(p1_case(kd=3.16e-6),T,dt=2.0,record_every=100.0).run(1520)
g=9.81; S=1/3.; kd=3.16e-6
def normal_depth(Q,b,n):
    lo,hi=1e-6,5.0
    for _ in range(100):
        y=0.5*(lo+hi); A=b*y; R=A/(b+2*y)
        if A*R**(2/3)*S**0.5/n<Q: lo=y
        else: hi=y
    return y
print(f"{'t':>5} {'b':>6} {'D':>6} {'Q L/s':>7} {'U pipe':>6} {'tau pipe':>8} {'yc':>6} {'Uc':>5} {'brink':>6} | face: {'y_n':>6} {'U':>5} {'tau':>6} {'ratio':>5} | eps_pipe mm/min  eps_face mm/min")
for x in r.series:
    p=pp.Pipe(x['b'],x['D'],x['z_inv'],x['x_o']-x['x_in'])
    fl=pp.pipe_flow(1.1-x['z_inv'],p.b,p.D,p.L,0.016)
    tp=pp.wall_shear(fl); Q=fl.Q
    yc=(Q*Q/(g*p.b*p.b))**(1/3); Uc=Q/(p.b*min(yc,p.D))
    yn=normal_depth(Q,p.b,0.016); Rn=p.b*yn/(p.b+2*yn); tf=1000*g*Rn*S; Un=Q/(p.b*yn)
    print(f"{x['t']:5.0f} {p.b:6.3f} {p.D:6.3f} {Q*1e3:7.2f} {fl.U:6.2f} {tp:8.2f} {yc:6.3f} {Uc:5.2f} {'free' if yc<p.D else 'full':>6} | {yn:12.4f} {Un:5.2f} {tf:6.1f} {tf/max(tp,1e-9):5.1f} | {kd*tp*6e4:8.2f}  {kd*tf*6e4:8.2f}")
cra=[e for e in r.events if e['type']=='crater_start']; print('crater', cra[0]['t'] if cra else None)
