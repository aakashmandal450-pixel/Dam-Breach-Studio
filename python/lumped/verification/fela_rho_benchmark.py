import fela_v2 as f, time, sys
W = {  # (H, rho, g): (LB, UB) Wilson et al. 2011 Table A1/A2
 (1,0.25,0):(2.93,2.95),(1,0.25,2):(0.61,0.63),(1,1.0,0):(4.33,4.37),(1,1.0,2):(2.10,2.13),
 (2,0.25,0):(4.83,4.88),(2,0.25,2):(0.39,0.43),(2,1.0,0):(8.80,8.87),(2,1.0,2):(4.46,4.54),
 (3,0.25,0):(6.60,6.68),(3,0.25,2):(0.09,0.17),(3,1.0,0):(13.75,13.91),(3,1.0,2):(7.34,7.51),
 (2,0.5,1):(3.99,4.04),(3,0.5,3):(-0.70,-0.59)}
out=[]; nf=0
for (H,r,g),(wl,wu) in W.items():
    t=time.time(); lb,ub,m=f.run("circle",float(H),1.0,float(g),0.1,rho=r)
    a,b=lb['audit'],ub['audit']
    aud=max(a['equilibrium'],a['traction_and_bc'],a['yield_excess'],a['side_excess'],a['bottom_excess'],b['incompressibility'],b['far_bc'])
    ok = lb['value']<=wu+0.01 and ub['value']>=wl-0.01 and aud<1e-6 and abs(b['recomputed']-b['objective'])<1e-3*max(1,abs(b['objective']))
    nf += (not ok)
    s=f"H/D={H} rhoD/c={r:4.2f} gD/c={g}: ours [{lb['value']:7.3f}, {ub['value']:7.3f}]  Wilson [{wl:6.2f}, {wu:6.2f}]  audit {aud:.0e}  {'PASS' if ok else 'FAIL'}  {time.time()-t:.0f}s"
    print(s,flush=True); out.append(s)
out.append("RESULT: "+("ALL PASS" if nf==0 else f"{nf} FAIL"))
print(out[-1]); open(sys.argv[1],"w").write("\n".join(out)+"\n")
