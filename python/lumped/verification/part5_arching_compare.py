import math
g=20e3  # gamma_t N/m3
def terzaghi_sv(C,b,c,phi,K=1.0,q=0.0):
    B=b/2
    if phi==0: return (g-c/B)*C+q
    k=K*math.tan(phi)
    return B*(g-c/B)/k*(1-math.exp(-k*C/B))+q*math.exp(-k*C/B)
def fela_proxy_collapse(C,D,cu):   # Wilson et al. 2011 circular fit, homogeneous, sigma_s=sigma_t=0
    N0=1.5*math.log(C/D)+2.4; Ng=-1.05*(C/D)
    return N0+(g*D/cu)*Ng   # N_crit; unsupported opening collapses if N_crit<0
b=1.0
print("b = D = 1 m, gamma = 20 kN/m3; required roof support (kPa) / FELA-proxy N_crit")
print(" C(m) | block/Terzaghi phi=0 cu=25 | Terzaghi drained c'=5 phi'=30 | drained c'=0 phi'=30 | FELA proxy cu=25 N_crit")
for C in [2,5,10,20,40]:
    a=terzaghi_sv(C,b,25e3,0)/1e3; d=terzaghi_sv(C,b,5e3,math.radians(30))/1e3; e=terzaghi_sv(C,b,0,math.radians(30))/1e3
    f=fela_proxy_collapse(C,1.0,25e3)
    print("%5d | %26.1f | %29.2f | %20.2f | %+8.2f"%(C,a,d,e,f))
