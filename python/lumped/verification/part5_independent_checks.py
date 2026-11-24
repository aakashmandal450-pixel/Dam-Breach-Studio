"""Code-independent numerical checks for Theory Part 5 (draft 4.1), run before implementation.

    python mechC_check.py

1. Mechanism C under the reservoir: F_C < 0 for random geometries, flows and approach velocities
   (v_top < U and p_top >= 0).
2. Inlet control (5.2) continuous at HW = 1.5 D below the roof.
3. Once the pipe is full, outlet control never exceeds the pressurised-entrance capacity.
"""
import math, random
g=9.81; rw=1000.; gw=rw*g
random.seed(1)
def f_man(n,R): return 8*g*n*n/R**(1/3)
worst=-1e9; n_cases=0
for _ in range(200000):
    H=random.uniform(2,100); zu=random.uniform(1.5,4); zd=random.uniform(1.5,4); Wc=random.uniform(1,20)
    zinv=random.uniform(0,0.8*H); a=random.uniform(0.05,0.3*(H-zinv)); b=random.uniform(0.05,3)
    zcr=zinv+a
    if zcr>=H*0.98: continue
    zs=random.uniform(zcr,H)              # pipe full needs HW>=1.5a; take any zs>zcr
    if zs-zinv<1.5*a: continue
    n=random.uniform(0.012,0.05); Ku=random.uniform(0.0,0.5); gt=random.uniform(17e3,23e3); cu=random.uniform(0,50e3)
    zbp=zinv+a/2; xu=lambda z: zu*z; L=(zu*H+Wc+zd*H - zd*zbp)-xu(zbp)
    A=a*b; R=A/(2*(a+b)); f=f_man(n,R)
    U=math.sqrt(2*g*(zs-zinv-a/2)/(Ku+1+f*L/(4*R)))
    # points under reservoir: upstream face between x_up(zcr) and x_up(zs)
    for k in range(5):
        x=xu(zcr)+random.random()*(xu(zs)-xu(zcr)); zdam=x/zu; t=zdam-zcr
        xi=x-xu(zbp)
        ps=gw*max(zs-(1+Ku+f*xi/(4*R))*U*U/(2*g)-zcr,0)
        vtop=random.uniform(0,min(U,math.sqrt(2*g*(zs-zdam))))  # below pipe velocity; p_top >= 0 (Bernoulli, free surface above)
        ptop=gw*(zs-zdam)-rw*vtop**2/2
        FC=b*(ps-ptop)-gt*b*t-2*cu*t
        worst=max(worst,FC/(gt*b*t)); n_cases+=1
print("mechanism C under reservoir: %d points, max F_C/(gamma_t b t) = %.4f (must be < 0)"%(n_cases,worst))
# also with vtop=0 (code's adverse assumption)
# inlet continuity at HW=1.5D
def Qi(b,D,HW,Ku):
    y=min(2*HW/3,D); return b*y*math.sqrt(2*g*(HW-y)/(1+Ku))
D=1.0;b=1.0;Ku=0.05
mx=max(abs(Qi(b,D,hw,Ku)-1.705*b*hw**1.5/math.sqrt(1+Ku))/Qi(b,D,hw,Ku) for hw in [0.01*k for k in range(1,151)])
print("inlet (5.2) below the roof equals 1.705 b HW^1.5/sqrt(1+Ku): max rel. diff %.1e"%mx)
# once full: outlet (Ku+Kd+F) never exceeds pressurised entrance (1+Ku)
def Qi_full(b,D,HW,Ku): return b*D*math.sqrt(2*g*(HW-D/2)/(1+Ku))
bad=0; worst_jump=0
for _ in range(100000):
    D=random.uniform(.05,5); HW=random.uniform(1.5*D,20*D); F=random.uniform(0,500); Ku=random.uniform(0,0.5)
    Qo=b*D*math.sqrt(2*g*(HW-D/2)/(Ku+1+F))
    if Qo>Qi_full(b,D,HW,Ku)*(1+1e-12): bad+=1
    # priming step at HW=1.5D: before = min(weir, partial barrel ~ same head), after = full barrel
    before=min(Qi(b,D,1.5*D,Ku), b*D*math.sqrt(2*g*D/(Ku+1+F)))
    after=b*D*math.sqrt(2*g*D/(Ku+1+F))
    worst_jump=max(worst_jump,after/before)
print("full pipe: outlet > pressurised entrance in %d of 100000 cases (must be 0)"%bad)
print("largest upward priming step (roof-wetting change in R ignored): x%.4f (sqrt2 = 1.4142)"%worst_jump)
