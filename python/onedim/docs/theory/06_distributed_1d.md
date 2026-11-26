# Theory, Part 6 — The distributed 1-D breach engine

*Distributed 1-D morphodynamic breach model (`python/onedim`, branch `onedim`) · draft 1 · 2026-11-26 ·
status: for review. No code until sign-off.*

*Decisions taken before this draft (plan §6, 2026-11-26): two tracks; Preissmann slot; explicit finite
volume with HLLC and hydrostatic reconstruction; debris by per-cell sediment transport; package
`python/onedim/`; phase A now; a gated 2-D exit/face patch later. The qualifications attached to
decisions 2–4 are written into §6.4, §6.5, §6.7 and §6.10. New decisions requested by this draft are
collected in §6.13.*

Rule, as for Parts 1–5: each equation has a source or a short derivation marked *ours*; each
coefficient is sourced, derived, a numerical parameter fixed by a convergence or insensitivity test,
or one of the calibration factors f_kd and f_t (Part 4 decision 2 dropped C_h). Nothing is tuned to
an observation. Numerical sources cited for the first time in this part are marked † in the
references; each is checked against the paper before sign-off, as was done for Wu (2016) in Parts 1–3.

---

## 6.1 Purpose and relationship with the frozen lumped reference

**What this part is.** The theory of a second engine that solves the breach flow, erosion and geometry
**cell by cell along the flow path**, with one solver from the first seepage pipe to the open breach.
Parts 1–5 remain the theory of the lumped engine; Part 6 reuses their *closures* (erosion laws, bank
stability, roof stability, headcut relations) and replaces their *reach-scale hydraulics and
reach-scale event rules*.

**Two tracks, kept apart.**
- The lumped engine (`python/lumped`, branch `lumped-1d`, commit `2b2ffb8`) is frozen and is named
  **lumped 1-D (reference)**. It is never edited to suit the new engine.
- The new engine is a separate package and a separate baseline. Every comparison runs both engines
  on identical case files and reports them side by side, never merged.
- The lumped validation records stay as they are: H1-a verified but not validated; the outlet
  convention reviewed but not resolved; P1 an unresolved validation finding.

**What is carried over unchanged, and what is replaced:**

| item | lumped (Parts 1–5) | distributed (Part 6) |
|---|---|---|
| reservoir | level pool (1.2)–(1.3) | **unchanged**, as the upstream boundary (§6.6.1) |
| intact-crest overflow | weir (1.8), non-eroding | **unchanged**, a direct reservoir loss (§6.6.3) |
| breach outflow | weir (1.5), pipe (5.2)–(5.4) | **computed** by the 1-D equations; the weir and the culvert relations become verification limits (§6.10) |
| bed shear | (1.12) on two reaches; (5.5) in the pipe | (1.12) = (5.5) **in every cell**, from the cell's own U and R |
| cohesive erosion | (2.1), (5.6)–(5.7) | **unchanged law**, per cell |
| non-cohesive capacity, steep slope | (2.3)–(2.5b) | **unchanged law**, per cell |
| non-equilibrium | exact reach integral (2.7) | the differential form (2.6), **unsteady, per cell** (§6.7) |
| widening, side slope | (3.1)–(3.5), (3.12)–(3.14) | **unchanged**, per cell |
| downstream separation c_b (3.6), slope rotation (App. 3A) | reach closures | **not used**: the profile and the width distribution are computed (decision 6-6) |
| headcut | Part 4 stages 1–4 | the Part 4 relations as a **sub-grid closure at a drop interface** (§6.8.4) |
| roof collapse and blow-out | §5.5b criterion (5.15), FELA table N_c, N_b | **unchanged criterion**, per cell, with the computed soffit pressure |
| crater walls | wet undrained cut (5.17) | **unchanged**, in collapsed cells (§6.8.3) |
| collapse spreading | §5.7a cascade, rule S | **not used**: each cell is checked on its own state every step (§6.8.2) |
| crater box, plugs D1-a/D5, exit headcut §5.6, H1-a | rules | **not active**; reference mechanisms and comparison cases only (§6.7.5) |
| outlet convention (5.3)/(5.8) | a chosen reference elevation | **not needed**: the exit is cells and an interface (§6.6.4) |

**What it is expected to buy, and what it is not.** Stated before any run, as in plan §1:
- Exit-concentrated enlargement can emerge where the local shear is higher.
- The outlet question (O-1) is answered by computation.
- The piping-to-open-breach transition is continuous.
- Cross-section averaging still removes expansion eddies, the arched roof and debris shaped across the
  section (§6.11). P1 may stay unresolved, and that outcome will be reported as such.

**Numbering.** Part 1 had reserved Parts 6–8 for the lumped engine; the clash is decision 6-13.

---

## 6.2 Spatial domain and distributed geometry

### 6.2.1 The flow path

The model is one-dimensional along a curvilinear coordinate s on the **breach axis**: the line
through the dam on which the pipe or the overtopping notch sits. The axis is straight in plan; s is
measured horizontally (plan distance), and elevations are vertical. The domain [0, L] is divided into
N cells of length Δs_i with centres s_i and interfaces s_{i±1/2}. Cells have **piecewise-constant
geometry** (prismatic within the cell); all geometric change between cells happens at interfaces.

The path depends on the initiating mode:

| mode | s = 0 (upstream boundary) | cells along the path | s = L (downstream boundary) |
|---|---|---|---|
| overtopping | upstream toe of the dam, on the axis | upstream face (submerged), crest, downstream face, downstream reach | outfall (toe or end of reach) |
| piping | pipe inlet on the upstream face, at x_up(z_inv) | conduit cells to the outlet, face cells down the downstream face, downstream reach | outfall |

In piping mode the upstream face below the inlet and above the pipe is not part of the path: it is
reservoir (level pool) or intact dam. When roof collapse reaches the inlet cell, that cell becomes an
open channel under the reservoir and the boundary is unchanged.

**Downstream reach.** Optional, of length L_ds and given section, fixed or erodible bed. Default for
flume cases: none, the outfall at the downstream toe (as in the lumped model). Field cases may supply
one.

### 6.2.2 The dam on the axis

The case geometry gives, on the axis, the dam surface z_g(s) (upstream face, crest, downstream face)
and the base or foundation top z_0(s). These do not change except through erosion, collapse and bank
failure. The cover over a conduit is C_i = z_g,i − z_cr,i (§6.2.3).

### 6.2.3 Cell types and section functions

Each cell holds one of three section types. Every section is described by its **bottom elevation**
z_i (the lowest wetted point) and its **width function** σ_i(η), the flow width at elevation η. From
σ follow, by integration in elevation, the section functions used everywhere below:

    A_i(η)  = ∫_{z_i}^{η} σ_i(η′) dη′                       wetted area below stage η
    T_i(η)  = σ_i(η)                                        top width
    I1_i(η) = ∫_{z_i}^{η} (η − η′) σ_i(η′) dη′              first moment (pressure force / ρg)       (6.1)
    P_i(η)                                                  wetted perimeter (friction surface)

with dI1/dη = A and dA/dη = T. Inverting A_i(η) gives the stage η_i from the stored area, and the
depth h_i = η_i − z_i.

**(a) Open channel cell** (overtopping notch, collapsed conduit, face, downstream reach). A trapezoid
of bottom width b_i, bed z_b,i and side-wall angle β_w,i (Part 3's β; m = cot β_w in Part 1's
notation), with n_loc erodible walls (Part 3), up to the dam surface z_g,i:

    σ_i(η) = b_i + n_loc (η − z_b,i) cot β_w,i                 z_b,i ≤ η ≤ z_g,i
    σ_i(η) = σ_i(z_g,i)                                        η > z_g,i   (vertical extension)    (6.2)

Above the dam surface the section continues as a **vertical-sided stream tube** of the notch's top
width: water standing above the ground is not allowed to spread across the dam. These fictitious walls
carry pressure but no friction (they are excluded from P_i). This is the no-lateral-spreading
closure (decision 6-5) and is the first place where the 2-D patch would act (§6.12). With a debris
layer (§6.7.4) the bottom elevation is the debris surface z_d,i and z_b,i stays as the intact bed.

**(b) Conduit cell** (pipe stage). A rectangle of width b_p,i and height a_p,i with invert z_inv,i and
crown z_cr,i = z_inv,i + a_p,i (Part 5 §5.2; D = a_p in the FELA notation), with a Preissmann slot of
width T_s above the crown (§6.4):

    σ_i(η) = b_p,i       z_inv,i ≤ η < z_cr,i
    σ_i(η) = T_s,i       η ≥ z_cr,i                                                                  (6.3)
    P_i(η) = b_p,i + 2 min(h_i, a_p,i) + w_i b_p,i,     w_i = 1 if η_i ≥ z_cr,i, else 0

The slot walls are not friction surfaces. The roof joins the wetted perimeter when the conduit is
full, as in Part 5 (5.3). The pipe may now slope: z_inv,i is a cell value, initially from the case's
invert input (Part 5 §5.8) and changed only by erosion.

**(c) Collapsed cell.** A conduit cell whose roof has failed (§6.8.2). It is an open channel cell
(a) with b_i = b_p,i, β_w,i = 90° until Part 3 sets a slope, intact bed z_b,i = z_inv,i and a debris
layer on it. The conversion changes only the section type of that cell; the state (A_i, Q_i, C_i) is
carried over (§6.8.2). There is **no hand-over stage**: the same solver runs before and after.

**Reported width.** As Part 1 (1.1), B̄ = b + m d per cell, with d = z_g − z_b; the reported breach
width is B̄ at the control cell (the cell of highest bed on the path) and the maximum B̄ over the dam
cells.

### 6.2.4 Grid

Uniform Δs over the dam by default, with optional stretching in the downstream reach. Two resolution
requirements, both checked by the grid study (§6.10) rather than assumed:
- **Adaptation length.** Δs ≤ L_s/5, so the non-equilibrium relaxation (2.6) is resolved
  (L_s = λ b, Part 2 (2.8)).
- **Geometry.** At least ~20 cells over the shortest dam feature of interest (crest width, face below
  the outlet). For ARS P1 (crest 1.83 m, faces 3H:1V, H = 1.3 m, invert 0.20 m) the pipe is
  ≈ 8.3 m long and the face below the outlet ≈ 0.63 m along slope, so Δs ≤ 0.03 m on the face.

---

## 6.3 Governing 1-D flow equations

### 6.3.1 The Saint-Venant equations in conservative form

For the wetted area A(s, t) and discharge Q(s, t) in a channel of varying section (Cunge, Holly and
Verwey 1980, Ch. 2):

    ∂A/∂t + ∂Q/∂s = q_l                                                                             (6.4)
    ∂Q/∂t + ∂/∂s ( Q²/A + g I1 ) = g I2 − g A S_f                                                   (6.5)

- I1 from (6.1); I2 = ∫_{z}^{η} (η − η′) ∂σ/∂s|_{η′} dη′ + (bed-slope part) is the longitudinal
  pressure force of the walls and bed on the water. With piecewise-constant cells I2 is concentrated
  at the interfaces, and its discretisation is the well-balanced interface source of §6.5.3.
- Friction (Manning, as Part 1 (1.12) and Part 5 (5.3)):

      S_f = n² Q|Q| / (A² R^{4/3}),    R = A/P                                                       (6.6)

  with n the case's `manning_n` in open cells and n_p (default n, Part 5 §5.3) in conduit cells.
  Entrance, expansion and exit *losses* are not added as coefficients: they come out of the
  discretised momentum balance at section changes (§6.5.3), except the one sub-grid entrance loss of
  §6.6.1.
- q_l: lateral inflow per unit length. Zero in all current cases; kept for the future 2-D coupling
  and for a tributary inflow.
- The momentum correction coefficient is 1 (one velocity per section).

**Hydrostatic and small-slope assumption.** (6.4)–(6.5) assume hydrostatic pressure in the vertical
and a small bed slope (pressure and depth measured vertically, cos θ ≈ 1). On a 3H:1V face
(θ = 18.4°) cos² θ = 0.90; on 2H:1V, 0.80. The error is accepted in v1 and stated (§6.11); a
bed-normal formulation is a later option. At a headcut the flow is not hydrostatic at all, which is
why the headcut is a sub-grid closure (§6.8.4).

**Clear-water continuity.** (6.4) carries water only. Sediment volume and mixture density are
neglected in the flow equations (dilute assumption). Breach-flow concentrations reach ~100 kg/m³,
about 4 % by volume (Part 2 §2.3); the error is stated, and coupled mixture formulations (Cao et al.
2004†) are a later option (decision 6-12).

### 6.3.2 Wave speed

The celerity of small disturbances in a section is

    c = √( g A / T )                                                                                (6.7)

(Cunge et al. 1980). In an open trapezoid this is the gravity-wave speed; in a full conduit with a slot
it is the slot celerity a_s (§6.4.2). The Froude number is Fr = |U|/c with U = Q/A.

### 6.3.3 Characteristic form (used only for the boundaries)

For a locally prismatic section (6.4)–(6.5) are hyperbolic with characteristic speeds U ± c. Along
ds/dt = U ± c the Riemann quantities

    R± = U ± Φ(A),      Φ(A) = ∫_0^A c(A′)/A′ dA′ = ∫_0^A √( g / (A′ T(A′)) ) dA′                     (6.8)

are invariant in the absence of sources (for a rectangle Φ = 2√(gh)). Φ is evaluated numerically on
each cell's section, including the slot. (6.8) is used only to close the boundary conditions (§6.6);
the interior uses the conservative scheme.

---

## 6.4 Pressurised and free-surface conduit flow: the Preissmann slot

### 6.4.1 Idea

A narrow, frictionless slot of width T_s is placed on top of the conduit (6.3). When the water rises
above the crown, the extra water is stored in the slot, the stage η is the **piezometric level**, and
(6.4)–(6.5) describe pressurised flow with a pressure-wave speed set by T_s (Preissmann 1961; Cunge and
Wegner 1964; Chaudhry 2008†). One set of equations then covers free-surface flow, pressurised flow and
the moving front between them.

**The slot is a geometric device, not a numerical scheme.** It is unrelated to the implicit Preissmann
four-point scheme, which is not used (plan decision 3).

### 6.4.2 Slot width and target celerity

From (6.7) with A ≈ A_f = b_p a_p in a full conduit,

    T_s = g A_f / a_s²                                                                               (6.9)

where a_s is the target pressure-wave speed. The real wave speed in a water-filled soil pipe is of
order hundreds of m/s; using it would make the CFL step tiny. As in most slot applications, a_s is
reduced, which is acceptable only if the pressure transients do not matter for the breach. Two
conditions make that so, and a_s is chosen to satisfy them, never to fit an outcome:

    Ma = U_max / a_s ≤ 0.1                     (pressure field quasi-static relative to the flow)
    L_p / a_s ≤ 10⁻² · t_min                   (pressure adjustment ≪ the fastest physical time scale)    (6.10)

t_min is the shortest of the erosion and drawdown time scales (seconds to minutes in the cases at
hand). **Default a_s is fixed in phase C by the insensitivity test** (§6.10): the results (Q, crown
pressure, filling time, collapse time) change by less than 1 % when a_s is doubled. Starting value for
the test: a_s = 50 m/s. For P1 (40 mm square pipe, A_f = 1.6 × 10⁻³ m²) this gives T_s = 6.3 × 10⁻⁶ m.

**Slot storage.** The slot holds a fictitious water volume T_s (η − z_cr) Δs per cell. Relative to the
pipe volume it is g(η − z_cr)/a_s² (0.4 % for 1 m of pressure head at a_s = 50 m/s). It is inside A, so
the water budget stays exact; its size is reported.

### 6.4.3 Pressure on the conduit walls

With the slot, the pressure head at the crown of conduit cell i is

    p_cr,i / γ_w = max( η_i − z_cr,i , 0 )                                                         (6.11)

and below the crown the pressure is hydrostatic about η_i. This **replaces** the lumped soffit
pressure (5.8), which assumed a linear friction gradient from a fixed entrance loss: here the soffit
pressure is computed from the solved piezometric level, including the exit and any partial filling.
In the long, steady, full-pipe limit (6.11) reduces to (5.8); that is a phase C test. When the conduit
is part full the crown pressure is zero, as in Part 5.

### 6.4.4 Known weaknesses and what is done about them

1. **Oscillations behind a pressurisation front.** Slot models with shock-capturing schemes produce
   spurious oscillations behind a filling bore (Vasconcelos et al. 2009†). Phase C measures them on a
   filling benchmark. No artificial damping is added to pass the test; if the oscillations exceed the
   gate (§6.10) at first order with Einfeldt wave speeds, the two-component pressure approach
   (Vasconcelos et al. 2006) is investigated (plan qualification 1).
2. **Sub-atmospheric pressure.** A slot cannot represent pressure below atmospheric: a conduit
   draining below the crown becomes free-surface flow. Negative slots exist (Kerger et al. 2011†) but
   are not needed for a free-outfall pipe through a dam; they would be for a siphoning reach. Stated
   limitation.
3. **Air.** Entrapped air, air pockets and the air phase are not represented. The ARS pipe exits freely
   to atmosphere, so air can leave at the outlet. Stated limitation.
4. **The priming jump.** Part 5 found a physical step in discharge when the pipe primes (the roof
   joins the wetted perimeter and the control moves). In the slot model this is not a rule: it
   emerges from the computed filling of the conduit. Phase C compares the emergent priming with the
   lumped step size and direction (up for F < 1.05, down otherwise).

---

## 6.5 Numerical solution: finite volume, HLLC and hydrostatic reconstruction

### 6.5.1 Conserved variables and update

For each cell the conserved state is U_i = (A_i, Q_i, A_i C_i), with C the depth-averaged volumetric
sediment concentration (§6.7). The explicit first-order update (forward Euler) is

    U_i^{n+1} = U_i^n − (Δt/Δs_i) ( F_{i+1/2}^− − F_{i−1/2}^+ ) + Δt S_i                           (6.12)

where F^∓ are the numerical fluxes seen from the cell on each side (they differ only by the
well-balanced pressure correction of §6.5.3), and S_i holds the cell sources (friction, solved
point-implicitly, §6.5.5; sediment exchange, §6.7).

**First order is the v1 baseline.** It carries the positivity and well-balance properties below
without limiter choices. A second-order MUSCL reconstruction (on stage and velocity) with a two-stage
SSP Runge–Kutta step is an option, adopted only if it passes the same phase B and C gates; the
observed order is reported either way (decision 6-3).

### 6.5.2 Interface sections: the intersection rule *(ours)*

The interface between cells i and i+1 is given its own section, the **intersection** of the two
adjacent sections (both lie on the same axis):

    σ_{i+1/2}(η) = min( σ_i(η), σ_{i+1}(η) )   for η above  z_{i+1/2} = max( z_i, z_{i+1} )          (6.13)

(width taken where both sections are open). This is the cross-section generalisation of Audusse et
al.'s (2004) interface bed max(z_L, z_R): for a rectangular channel of equal widths it reduces to it
exactly. Two consequences matter:
- **Positivity.** The interface section is contained in each neighbour's section, so the reconstructed
  area on it never exceeds the cell's own area (6.14). This is the property Audusse et al. use to prove
  positivity of depth, here extended to area (to be verified in phase B, not only argued).
- **Conduits.** The intersection of a conduit and an open cell is the conduit (with its slot): water
  passes from a pressurised conduit into an open cell through the conduit's own opening. At the
  outlet this is the physical opening of the pipe.

### 6.5.3 Hydrostatic reconstruction and the well-balanced source *(ours, after Audusse et al. 2004)*

**Reconstructed states.** Each cell's stage and velocity are carried to the interface section:

    A*_{i,R} = A_{i+1/2}(η_i),     Q*_{i,R} = A*_{i,R} · U_i                (left state at i+1/2)
    A*_{i+1,L} = A_{i+1/2}(η_{i+1}), Q*_{i+1,L} = A*_{i+1,L} · U_{i+1}      (right state at i+1/2)    (6.14)

with A_{i+1/2}(η) the area of the intersection section below η (zero if η ≤ z_{i+1/2}). A cell whose
stage is below the interface bottom contributes a dry state, which is what makes wetting, drying and
a debris barrier (§6.7.4) work without special cases.

**Flux.** F_{i+1/2} = F_HLLC(U*_L, U*_R) on the interface section (§6.5.4).

**Well-balanced pressure correction.** The momentum flux seen by each cell is corrected by the pressure
of the cell's own water on the part of the interface plane that is not open (the step between the two
sections):

    F^{Q,−}_{i+1/2} = F^Q_{i+1/2} + g [ I1_i(η_i) − I1_{i+1/2}(η_i) ]           (seen by cell i)
    F^{Q,+}_{i+1/2} = F^Q_{i+1/2} + g [ I1_{i+1}(η_{i+1}) − I1_{i+1/2}(η_{i+1}) ] (seen by cell i+1)     (6.15)

with I1 evaluated on the section indicated and the mass flux uncorrected. Substituting (6.15) into
(6.12) gives, for cell i, the net wall-and-bed force

    g [ I1_{i+1/2}(η_i) − I1_{i−1/2}(η_i) ]                                                          (6.16)

which is the discrete form of g I2 in (6.5): the bed and wall steps at the two ends of the cell, each
loaded by the cell's own hydrostatic pressure.

**Properties.**
- **Lake at rest.** If η is uniform and Q = 0, the reconstructed states on each interface are equal, the
  HLLC flux is the pure pressure g I1_{i+1/2}(η), and (6.15)–(6.16) cancel it exactly. The scheme
  preserves still water over any bed *and any width* variation, to round-off. Phase B test B1.
- **Abrupt expansions.** At a sudden enlargement the step pressure in (6.15) is the pressure of the
  downstream (larger) cell's water. That is the Borda–Carnot assumption, so the expansion head loss
  (U₁ − U₂)²/2g follows from the momentum balance without a loss coefficient. **This is how the pipe
  exit is computed** (§6.6.4), and it is the answer to the outlet-convention question O-1. Phase C
  test C2 checks it against the Borda–Carnot loss.
- **Contractions** are nearly loss-free in the 1-D equations. That is physically right for a smooth
  contraction and wrong for a sharp entrance; the one sharp entrance on the path, the reservoir into
  the pipe, carries Part 1's sub-grid entrance loss K_u at the boundary (§6.6.1).

Ours, built from Audusse et al. (2004) and the irregular-section treatments of Vázquez-Cendón
(1999)† and Hernández-Dueñas and Karni (2011)†; verified, not trusted, in phase B.

### 6.5.4 The HLLC flux

The physical flux on a section is F(U) = (Q, Q²/A + g I1(A), Q C), with I1 as a function of A on the
interface section.

**Wave-speed estimates** (Einfeldt 1988; Einfeldt et al. 1991†), with Roe-type averages
Ũ = (√A_L U_L + √A_R U_R)/(√A_L + √A_R) and c̃ = c on the interface section at the mean area:

    S_L = min( U_L − c_L, Ũ − c̃ ),    S_R = max( U_R + c_R, Ũ + c̃ )                                (6.17)

Einfeldt speeds are chosen because they make the HLL family positivity-preserving near dry states.
In a full conduit c = a_s, so the speeds include the slot celerity automatically.

**Mass and momentum flux: HLL.** In one dimension the shallow-water system has only the two acoustic
waves, so the HLLC mass and momentum fluxes are the HLL ones (Toro 2001, Ch. 10):

    F_HLL = [ S_R F(U_L) − S_L F(U_R) + S_L S_R (U_R − U_L) ] / (S_R − S_L)    for S_L < 0 < S_R      (6.18)

(and F(U_L) or F(U_R) when both speeds have one sign).

**Concentration flux: the contact wave.** The third wave of HLLC is the contact that carries the
concentration. Its speed, for a general pressure p = g I1 (Batten et al. 1997†),

    S* = [ p_R − p_L + A_L U_L (S_L − U_L) − A_R U_R (S_R − U_R) ] / [ A_L (S_L − U_L) − A_R (S_R − U_R) ]   (6.19)

and the sediment flux is the HLL mass flux times the upwind concentration:

    F^{AC} = F^A_HLL · ( C_L if S* ≥ 0, else C_R )                                                   (6.20)

This contact is the extra wave structure HLLC resolves and HLL smears: a sediment front (debris
released by a collapse) stays sharp, and C gains no new extrema under the CFL condition. For the
water alone HLLC and HLL are identical, so the choice does not change the hydraulics.

### 6.5.5 Time step, friction and dry cells

**CFL step.**

    Δt = CFL · min_i Δs_i / ( |U_i| + c_i ),     CFL = 0.9 (first order)                              (6.21)

CFL is a numerical parameter; the dt-convergence study repeats each case at CFL/2. In full conduit
cells c_i = a_s, so the slot sets Δt there. P1 estimate: Δs = 0.03 m, a_s = 50 m/s → Δt ≈ 5 × 10⁻⁴ s,
about 3 × 10⁶ steps to 1560 s over ~300 cells — feasible in compiled numerics, and budgeted as plan
risk 3.

**Friction, point-implicit.** After the flux update, the friction source is integrated implicitly in
Q over the step (Liang and Marche 2009†):

    Q_i^{n+1} = Q_i^* / ( 1 + Δt g n² |Q_i^*| / ( A_i R_i^{4/3} ) )                                   (6.22)

which cannot reverse the flow and stays stable in shallow cells, where the explicit form would not.

**Dry cells.** A cell is dry when h_i < h_dry; its velocity is set to zero and it is excluded from the
CFL minimum. h_dry is a numerical parameter (default 10⁻⁶ m), tested by halving and doubling it; it is
not a physical depth.

### 6.5.6 Operator splitting and the morphological step

Each step: (1) flow update (6.12) with friction (6.22); (2) sediment exchange and bed change (§6.7);
(3) geometry update and events (§6.8). No morphological acceleration in v1.

**Geometry update conserves water.** When a cell's section changes (erosion, collapse, bank failure),
its stored water volume A_i Δs_i is kept and the stage is recomputed on the new section from A_i. The
stage is not kept, because that would create or destroy water. This keeps the water budget exact
through every geometric event.

**Events within a step.** Event margins (roof, bank, block sliding) are evaluated at the end of each
step and the event is applied there. The CFL step (milliseconds in P1) is many orders of magnitude
below the time scales of the events, so the lumped engine's event location by interpolation is not
needed for accuracy; the timing error is at most Δt and is reported. The dt study (CFL, CFL/2) confirms
it.

---

## 6.6 Boundary conditions and hydraulic transitions

### 6.6.1 Upstream: the level-pool reservoir

The reservoir obeys Part 1 (1.2)–(1.3) unchanged, with the breach outflow Q_b now the boundary flux at
s = 0:

    dV/dt = Q_in − F^A_{1/2} − Q_ov − Q_sp,      z_s = Z(V)                                           (6.23)

integrated with the same Δt. The boundary state at the first interface is found from two equations:

- **Energy from the still reservoir**, with Part 1's entrance loss where the boundary is a sharp
  entrance (the pipe inlet; K_u ≈ 0.05, Part 1 §1.4) and none where it is a deep-water stream tube
  (overtopping, toe boundary, K_u = 0):

      z_s = η_b + (1 + K_u) U_b² / 2g                                                                (6.24)

- **The outgoing characteristic** from cell 1: R⁻_b = R⁻_1, i.e. U_b − Φ_b(A_b) = U_1 − Φ_1(A_1)
  (6.8), on the boundary section (the first cell's section).

If the solution has Fr_b > 1, the inflow is choked at the boundary and the critical state from (6.24)
with Fr_b = 1 is used instead: this is exactly Part 1's critical-flow weir (1.4)–(1.5), and with the
pipe inlet it is Part 5's inlet control (5.2). Outflow back into the reservoir (Q < 0) is allowed and
adds to V. Both roots are found by bracketed solves, as in Parts 1 and 5.

**Approach section, overtopping (decision 6-1).** The toe boundary uses a **stream tube of the notch
width** over the submerged upstream face: cells there have the notch section, with the face surface as
bed where the notch has not cut it. Water over the upstream face outside the notch is reservoir.
The water in those upstream-face cells is also inside the level-pool volume; this overlap is a
geometric approximation, not a budget error, and it is reported as a fraction of V (expected well
below 1 %). If a case exceeds 0.5 %, the boundary is moved to the upstream crest edge (option).

### 6.6.2 Downstream: free outfall or tailwater rating

- **Free outfall (default, TW = 0 as in O-1, an assumption with that status).** If the last cell's flow
  is supercritical leaving the domain, the boundary is transmissive (zero gradient). If subcritical,
  the boundary state is critical, Fr_b = 1, together with the incoming invariant R⁺_b = R⁺_N. This is
  the standard free-overfall closure (critical depth just upstream of the brink).
- **Tailwater rating (option).** A stage–discharge relation η_b = f_TW(Q_b) (Manning normal depth in a
  prismatic downstream channel, or a stage series) with R⁺_b = R⁺_N. Its source and status are
  recorded in the case file.

### 6.6.3 Intact-crest overflow

Flow over the intact part of the crest is Part 1 (1.8) unchanged: a direct reservoir loss Q_ov with
B_top,cr the notch top width at the upstream crest edge. It bypasses the 1-D domain and erodes
nothing, exactly as in the lumped engine. This covers crest overflow during the pipe stage too
(Part 5 §5.3). A second resolved path over the crest is a later option.

### 6.6.4 Hydraulic transitions inside the domain


| transition | treatment |
|---|---|
| critical control (weir crest, start of the face) | emerges where the bed is highest; transcritical rarefaction resolved by the Riemann solver (phase B test B5) |
| hydraulic jump on the face or at the toe | shock, mass and momentum conserved, energy dissipated (test B6) |
| pipe inlet | §6.6.1, energy with K_u, then the conduit section |
| pipe outlet, free jet onto the face | interface between the last conduit cell and the first face cell; flux through the conduit opening (6.13); expansion loss from (6.15) (Borda–Carnot). With a free outfall at the toe and no tailwater, the jet's velocity head is lost downstream, which is the lumped K_d ≈ 1 recovered as a result (test C2) |
| pressurisation front | moving front between part-full and slot states, resolved by the scheme (test C4) |
| conduit beside a collapsed cell | the collapsed cell is open; the conduit discharges into it through its opening; the collapsed cell's stage is free (atmospheric) |
| water above the dam surface in any cell | allowed in the stream tube (6.2); flagged and reported, since it means water would spill across the dam (a 2-D effect) |
| bed drop larger than the critical depth (headcut) | sub-grid closure §6.8.4 |

---

## 6.7 Local erosion and sediment transport

### 6.7.1 Bed shear, in every cell

    τ_i = ρ g n² U_i |U_i| / R_i^{1/3}                                                               (6.25)

the signed form of Part 1 (1.12), identical to Part 5 (5.5) (τ = ρ f U²/8 with f = 8gn²/R^{1/3}).
Shear acts uniformly on the wetted perimeter: bed, walls and, in a full conduit, the roof (Part 4
decision 4, wall shear = bed shear; 0.7 × bed for sensitivity). It is the shear of the cell's own
solved flow, so the entrance and exit losses do not erode (Part 5 §5.4), and the downstream face is no
longer "normal depth" but whatever the 1-D solution gives.

### 6.7.2 Transport equation

Depth-averaged volumetric concentration C (solids volume per water volume), one size class (Part 2 §2.5):

    ∂(A C)/∂t + ∂(Q C)/∂s = Ė_i − Ḋ_i                                                                (6.26)

Ė and Ḋ are solids volumes per unit length per unit time entering and leaving the flow at the cell.
The advective flux is (6.20). The source depends on the material class, never mixed (Part 2 §2.1):

**Cohesive (detachment-limited).** Part 2 (2.1) per cell:

    ε_i = f_kd k_d max(τ_i − τ_c, 0),     Ė_i = (1 − p) ε_i P_e,i,     Ḋ_i = 0                        (6.27)

P_e,i is the wetted erodible perimeter (bed and walls below the water; the roof when the conduit is
full). Detached fines are wash load, as in Parts 2 and 5: they do not redeposit.

**Non-cohesive (transport-limited, non-equilibrium).** The differential form of Part 2 (2.6), unsteady:

    Ė_i − Ḋ_i = |Q_i| ( C*_i − C_i ) / L_s,i,     L_s,i = λ b_i,     λ = 6 field, 3 lab (2.8)          (6.28)

with C*_i the Part 2 total-load capacity (2.3)–(2.4b), DL Breach combination by default, steep-slope
correction (2.5a–b) with the local bed angle θ_i = atan[(z_{i−1} − z_{i+1})/(Δs_{i−1/2} + Δs_{i+1/2})],
and f_t applied once to C*. Positive values erode, negative deposit.

**Relation to the lumped form.** For steady uniform flow over a reach, (6.26) with (6.28) integrates
to Part 2 (2.7) exactly. That is phase D test D2: the distributed model reproduces the lumped
non-equilibrium solution in its own limit, so the two engines differ only where the flow does.

**Integration of the source.** The relaxation (6.28) is stiff when Δs ≪ L_s is not met or U is large.
It is integrated exactly over the step (as (2.7) integrates it over a reach):

    C_i^{n+1} = C*_i + ( C_i^* − C*_i ) exp( −|U_i| Δt / L_s,i )                                      (6.29)

with C_i^* the concentration after advection. The solids exchanged, (C_i^* − C_i^{n+1}) A_i Δs_i, are
taken from or added to the bed (§6.7.3).

### 6.7.3 Exner: from exchanged solids to bed change

The bulk volume eroded (or deposited) in cell i during the step is

    ΔV_i = ( Ė_i − Ḋ_i ) Δs_i Δt / (1 − p)                                                           (6.30)

(Part 2 (2.9), per cell). Eroded volume is taken first from the cell's mobile store (§6.7.4), then from
intact soil. Deposited volume goes to the mobile store. How ΔV changes the section is §6.8.1.

### 6.7.4 The mobile store: debris and deposits *(plan decision 4)*

Each cell has one **mobile store** of solids volume M_i, lying on the intact bed z_b,i as a layer of
uniform thickness across the bottom width (the first-version deposition assumption of Part 5 (5.12b),
now per cell):

    z_d,i = z_b,i + M_i / ( (1 − n_d) b_i Δs_i )                                                     (6.31)

It receives:
- the fallen roof of a collapsed conduit cell (§6.8.2);
- bank-failure wedges (§6.8.3);
- deposited sediment (non-cohesive, (6.28) negative).

It erodes before the intact soil below it, with the debris erodibility: k_d,debris and τ_c,debris
(cohesive; default the intact values, Part 5 §5.7) or the Part 2 capacity (non-cohesive). Porosity n_d
defaults to n. Its surface z_d,i is the cell's bottom elevation for the hydraulics (§6.2.3), so a debris
layer obstructs the flow from the instant it forms.

**Blocking is no longer a rule.** If the reservoir stage is below a debris surface, the hydrostatic
reconstruction (6.14) gives a dry interface and no water passes. The lumped "sealed" outcome (Part 5
§5.7) therefore emerges, or does not, from the hydraulics. Its two assumptions remain and are stated:
the debris is impermeable (no seepage through it) and there is no other water supply.

### 6.7.5 What the distributed transport does and does not represent *(plan qualification 3)*

It represents: erosion, deposition, storage and export per cell, with an exactly closed solids budget
(§6.9); movement of fallen soil downstream at the speed of the flow; and redeposition of non-cohesive
material where capacity drops (for example in the expansion below the outlet).

It does **not** represent, and the model does not claim it does:
- debris plugs with a shape across the section (arching debris, a plug that leaves a gap beside it);
- lateral collapse and its spreading across the section;
- seepage through debris and re-piping;
- graded sediment and armouring.

The lumped crater box, the plugs D1-a/D5, the exit headcut §5.6 and the exit widening H1-a are
**not active** in the new solver. Two of them are kept as **comparison modes** only, never on by
default, to show how much the debris treatment matters: `debris_mode = "export"` (fallen soil removed
at once, the lumped instant mode) and `debris_mode = "level"` (the default, (6.31)).

---

## 6.8 Breach geometry evolution and roof failure

### 6.8.1 Open cells: deepening and widening (Part 3, per cell)

The eroded bulk volume ΔV_i (6.30) is spread over the cell's whole erodible surface, bed plus walls up
to the dam surface, as in Part 3 (3.1)–(3.2):

    Δz_i = ΔV_i / A_e,tot,i,     A_e,tot,i = b_i Δs_i + n_loc (z_g,i − z_b,i) Δs_i / sin β_w,i          (6.32)

and the section updates by Part 3 (3.3)–(3.5) unchanged (bed lowers by Δz, top width grows by
n_loc Δz / sin β_w, bottom width by n_loc Δz (1/sin β_w − 1/tan β_w)). Deposition raises the mobile
store, not the walls. The bed stops at the base or non-erodible foundation (Part 3 §3.5-1) and widening
continues; the erodible-foundation option (c_b = 1.6) and the abutment limit (§3.5-2, -3) apply per
cell.

**Not used:** the downstream separation factor c_b (3.6) and the slope rotation about the toe
(Appendix 3A). Both are reach-scale closures for what the distributed model computes: the width of
each face cell follows its own shear, and the longitudinal profile is the set of cell beds
(decision 6-6). (3.6) is kept as an interface option for comparison only.

### 6.8.2 Conduit cells: enlargement and roof collapse

**Enlargement.** Part 5 (5.6)–(5.7) per cell, with the cell's τ_i from (6.25): the invert lowers at ε,
the width grows at 2ε, and the crown rises at ε only while the cell is full (w_i = 1). Non-cohesive
conduits use (6.28) with L_s = λ b_p and spread the eroded volume over the wetted perimeter (Part 5
§5.4). The eroded solids enter the flow (6.26).

**Roof criterion.** The §5.5b criterion of the lumped engine is used **unchanged**, cell by cell:

    stable while   c_u0 · N_b  <  σ_s,i − p_s,i  <  c_u0 · N_c                                  (5.15)

with N_c (collapse) and N_b (blow-out) interpolated from the FELA table
(`verification/stability_table.csv`) in C/b_p, a_p/b_p, γ b_p/c_u0, ρ b_p/c_u0 and, for a full pipe,
γ_w b_p/c_u0, and c_u = c_u0 + ρ d (5.14). Each cell supplies its own values:

| §5.5b input | cell value |
|---|---|
| b_p, a_p | b_p,i, a_p,i |
| cover C | z_g,i − z_cr,i |
| soffit pressure p_s | p_cr,i from (6.11): the computed crown pressure (full pipe); 0 part full, with the band (5.16) on the wetted depth as in §5.5b |
| surface load σ_s | γ_w max(z_s − z_g,i, 0) on the upstream face, 0 on the crest and downstream face (the §5.5b piecewise condition) |
| strength | c_u0, ρ and unit weights as in the case file |

End-lip cells with C < 0.25 b_p (below the table) are not checked, as in §5.5b. The band (5.16) is
used in the uncertainty runs, as in the lumped engine.
The criterion is frozen (handoff §3): it is not re-derived, re-fitted or given a different threshold
here. The plane-strain section ignores support from neighbouring cells, which is conservative for a
short collapse length (Part 5 §5.5a); every other §5.5b convention (overburden shift (5.15b),
full-pipe identity (5.16b)) is applied exactly as there.

**Collapse of cell i.** When the margin crosses zero:
1. The roof solids V_s,i = (1 − n) b_p,i (z_g,i − z_cr,i) Δs_i go into the cell's mobile store M_i.
2. The cell becomes a collapsed cell (§6.2.3(c)): open, width b_p,i, vertical walls from the intact bed
   z_inv,i to z_g,i, debris surface z_d,i from (6.31). With n_d = n, z_d,i = z_g,i − a_p,i, the
   per-cell form of Part 5's z_d ≈ H − a_p.
3. The water in the cell is kept (A_i Δs_i), so the stage is recomputed on the new section
   (§6.5.6). The water now stands in an open cell, at atmospheric pressure.
4. Neighbouring cells are not changed by rule. They lose nothing they were credited with (no end
   support), and they respond to the new hydraulics on the next step.

**Collapse length and grid dependence.** The lumped §5.7a spreading cascade and its collapsed-length
rule S are not used: a neighbour's inputs do not change until the hydraulics responds, so each cell is
simply re-checked on its own state every step. Collapse is decided per cell, so its length is a
multiple of Δs. The debris surface (6.31) does not depend on Δs, but the sequence in which neighbouring cells fail
might. The grid study (§6.10, F-tests) checks that the collapse location and time converge as Δs is
halved. If they do not, a physical minimum collapse length would be needed; it would have to come with
a source (for example the cover or the opening width from 3-D analyses), and it is not introduced in
advance (decision 6-14).

**Blow-out and exit uplift.** Blow-out is the lower bound N_b of (5.15), checked in every conduit cell,
as in §5.5b, which also uses it for the exit uplift. The prism free body (5.11) stays a reported
comparison. Part 5 found that neither acts under the reservoir; the distributed model is expected to
confirm it, not assume it.

**Face stability (F-1)** stays a standalone screening, evaluated on the outlet cell and reported; it is
not coupled (as in the lumped engine).

### 6.8.3 Wall stability in open and collapsed cells

**Collapsed (piping) cells: the frozen wet undrained cut (5.17).** The walls of a collapsed cell are
the same undrained, short-term cut as the lumped crater walls, so the lumped criterion is used
unchanged, per cell:

    H_w ≤ H_c = 3.776 c_u0 / ( γ − γ_w (h_w/H_w)² − 2ρ )                                    (5.17)

with H_w = z_g,i − z_b,i and h_w the cell's water depth against the wall (wet wall default, dry wall
for sensitivity, as in §5.7a). A failed wall retreats by the area-equivalent ½ H_w per side, as in the
lumped engine, and the wedge solids go into the cell's mobile store. Outside the checked range of
(5.17) it is a domain error, not a stability result.

**Open-breach (overtopping) cells: Part 3.** The side angle comes from (3.12)–(3.14) with
H_i = z_g,i − z_b,i, vertical while a vertical bank of that height stands. When β_w,i decreases, the
failed wedge goes into the cell's mobile store (Part 3 §3.4, half the block at once as in Wu 2016).

Which criterion a cell uses is set by how it opened (collapse or erosion from the surface), never by
the outcome. Decision 6-8.

### 6.8.4 Headcut: a sub-grid closure at a drop interface (cohesive soils)

The 1-D hydrostatic equations cannot represent a plunging overfall. Part 4's physics is therefore kept
as a **sub-grid closure on an interface**, for soils with a detachment law (Part 4 §4.3):

1. **Drop interface.** An interface i+1/2 whose bed drop z_i − z_{i+1} exceeds the critical depth of the
   flow over it, d_c = (q²/g)^{1/3} with q = Q/b, while the downstream stage is below the upstream bed
   (the plunging condition (4.2)), is a drop interface. Its flux is the free overfall the hydrostatic
   reconstruction already gives (a dry or low downstream side); no extra hydraulic rule is added.
2. **Advance.** The brink retreats at Part 4 (4.3)–(4.9) with H_h = z_i − z_{i+1}, d_bw = max(d_c,
   h_{i+1}) and the soil's k_d, τ_c, c_u, γ_t. The retreat accumulates as a brink position inside
   cell i; when it crosses the cell, cell i's bed drops to the base of the drop and the solids
   (1 − p) b_i (z_i − z_{i+1}) Δs_i enter the flow. E_v ≤ 0 caps the advance at the cascading-face
   rate, as in Part 4.
3. **Base scour** at the larger of the downstream cell's own shear (6.25) and the jet stress τ_hf (4.7),
   as in Part 4 §4.3.
4. **What is dropped.** SIMBA's erosion-resistant crest during stages 1–2 (Part 4 §4.3) is not used:
   the crest erodes by its own computed shear. The stage numbers are not state variables; a drop
   interface either exists or not. The residual-block sliding check (4.10)–(4.11) is kept, on the
   block of cells upstream of the most upstream brink (decision 6-10).

The same closure is the distributed form of the lumped exit headcut (§5.6): a drop that forms below the
pipe outlet on the face is a drop interface like any other. It applies only where the plunging
condition is met; the lumped finding that the P1 exit "never plunges" is therefore testable, not built
in.

---

## 6.9 Water, momentum and solids conservation

### 6.9.1 Water

    V(t) + Σ_i A_i Δs_i  =  V(0) + Σ_i A_i(0) Δs_i + ∫ ( Q_in − Q_ov − Q_sp − F^A_{N+1/2} ) dt        (6.33)

The finite-volume update is conservative, the reservoir is integrated with the boundary flux, and
geometric events keep A_i Δs_i (§6.5.6), so (6.33) closes to round-off: **gate 10⁻¹² relative**,
checked every output step. Reported alongside: the slot storage (§6.4.2) and the approach-overlap volume
(§6.6.1), which are modelling approximations, not budget terms.

### 6.9.2 Momentum

Momentum is not conserved (bed, walls and friction act on it). A momentum budget is computed as a
diagnostic in phases B and C: the change of Σ Q_i Δs_i equals the boundary fluxes plus the summed
interface wall forces (6.16) plus friction, to round-off. Across a hydraulic jump the conjugate depths
are checked (test B6).

### 6.9.3 Solids

Tracked as solids volumes, every step:

    S_removed(t)  =  Σ_i A_i C_i Δs_i  +  Σ_i M_i  +  S_exported(t)                                  (6.34)

S_removed: intact soil removed by erosion, roof collapse and bank failure (solids); S_exported:
∫ F^{AC}_{N+1/2} dt at the outfall. Solids in the store are counted once, whether they arrived by
collapse, bank failure or deposition. **Gate 10⁻¹² relative.** This is the per-cell form of Part 5
(5.13), with "exported" now meaning carried past the outfall, not removed by rule.

---

## 6.10 Verification and validation requirements

Gates are hard: a phase does not start until the previous one passes. Pass criteria are written here,
before any run. All tests run in both water-only form and, where relevant, with the passive
concentration.

**Phase B — open-channel solver, fixed geometry.**

| test | setup | pass criterion |
|---|---|---|
| B1 lake at rest | irregular bed *and* irregular widths, trapezoids and rectangles, wet and partly dry | |U| < 10⁻¹² m/s and η constant to 10⁻¹² m after 10⁵ steps |
| B2 Ritter dam break | dry downstream bed, rectangle | L1 error in h and U → 0 with Δs; observed order reported (≈ 1 expected at first order); front position within 1 % at the finest grid |
| B3 Stoker dam break | wet downstream, rectangle | as B2; shock speed and intermediate state within 1 % |
| B4 dam break in a trapezoid | variable section | conservation to 10⁻¹²; convergence with Δs |
| B5 transcritical flow over a bump | Goutal and Maurel (1997)† cases (subcritical, transcritical with and without shock) | steady profiles within 1 % of the analytic Bernoulli/conjugate solution |
| B6 hydraulic jump | supercritical inflow, subcritical tailwater | conjugate depths (Bélanger) within 1 %; momentum flux continuous across the jump to the grid error |
| B7 GVF profiles | M1, M2, S2 in prismatic and non-prismatic channels with Manning friction | within 1 % of a direct-step solution at the finest grid |
| B8 wetting and drying | Thacker (1981)† parabolic bowl, 1-D | shoreline and h converge; positivity never violated |
| B9 positivity | two strong rarefactions leaving a near-dry middle (Toro 2001) | A ≥ 0 every step; no NaN; mass to 10⁻¹² |
| B10 steep bed steps and near-dry cells | flow down a 1:2 face onto a flat apron; step-up and step-down beds | stable; mass to 10⁻¹²; profile converges with Δs |
| B11 grid and dt convergence | B2, B6, B7 at Δs, Δs/2, Δs/4 and CFL, CFL/2 | observed order and GCI (Roache 1998; Celik et al. 2008†) reported |

**Phase C — conduit with the slot.**

| test | pass criterion |
|---|---|
| C1 steady full pipe | discharge within 0.5 % of the closed-form outlet-control solution with the same losses; crown pressure along the pipe matches (5.8) in the long-pipe limit |
| C2 free outlet and expansion | head loss at the outlet within 1 % of Borda–Carnot; with a free outfall the computed outflow matches (5.3) with K_d = 1 within 1 % (the lumped outlet convention recovered or not, reported either way) |
| C3 surge celerity | a pressure step travels at a_s within 1 % |
| C4 pipe filling | the filling bore speed and the pressurisation time against the mass and momentum jump conditions; oscillations behind the front measured and reported (peak-to-peak pressure); comparison with the Trajkovic et al. (1999)† or an equivalent filling experiment |
| C5 pressurised ↔ free surface | emptying and refilling cycle; mass to 10⁻¹²; no spurious pressurisation |
| C6 slot sensitivity | a_s and 2a_s: Q, crown pressure, filling time change < 1 % (this fixes the default a_s) |
| C7 HLLC with the slot | C1–C6 run with the HLLC flux; stable at CFL 0.9 and 0.45; **the slot is accepted only if C1–C7 pass** |
| C8 priming | the emergent priming of a growing pipe compared with the lumped step (size and direction, F < 1.05 up, F > 1.05 down); reported |

If C4 oscillations or C7 stability fail at first order with Einfeldt speeds, the two-component pressure
approach is investigated (plan qualification 1). The choice is never made on breach results.

**Phase D — morphology.**

| test | pass criterion |
|---|---|
| D1 solids budget | (6.34) to 10⁻¹² through erosion, deposition, collapse and bank failure |
| D2 non-equilibrium relaxation | steady uniform flow, clear inflow: C(s) = C*(1 − exp(−s/L_s)) within 0.5 % at Δs ≤ L_s/5 |
| D3 uniform-flow limit | a prismatic erodible reach in uniform flow: per-cell erosion rate and widening equal the lumped (2.1)/(2.3)–(2.9) and (3.1)–(3.5) for the same τ to 10⁻⁹ |
| D4 aggradation/degradation | a published mobile-bed benchmark, chosen at review (candidates: clear-water degradation below a dam; Spinewine and Zech 2007† dam break over a mobile bed), qualitative and order-of-magnitude |
| D5 bank and wall failure | per-cell wedge volume into the store; β_w trends as Part 3 §3.6; (5.17) reproduces the lumped wall check on identical states |
| D6 roof collapse in isolation | a fixed-flow conduit reaching the §5.5b margin: collapse at the margin crossing; debris surface (6.31); water kept; grid independence of the collapse time |

**Phase E — overtopping cases.** The lumped reference cases, both engines on identical case files,
side by side: Q_p, T_p, final width, hydrograph shape. Then the case database. Differences are
reported and explained by the flow, never removed by adjustment.

**Phase F — piping, P1.** Both engines, identical inputs, frozen soil parameters (k_d band, c_u, τ_c),
no tuning. Compared with the lumped baseline and with the photo evidence as ratios with the scale
caveat (handoff §3–4). Reported whether or not P1 breaches. Grid convergence of the collapse location
and time (decision 6-14).

---

## 6.11 Limitations of the 1-D model

Stated now, before results:

1. **Cross-section averaging.** One velocity per section: no lateral flow, no secondary currents, no
   expansion eddies (H1-d), no flow separation along walls.
2. **No lateral spreading.** Flow is confined to the notch stream tube (6.2), including on the
   downstream face below a pipe outlet and above the ground. Real flow spreads.
3. **Hydrostatic, small slope.** Errors of order 10–20 % in pressure on 3H:1V to 2H:1V faces; no
   non-hydrostatic jet at a headcut (sub-grid closure instead).
4. **Single path.** One axis; intact-crest overflow is a non-eroding lumped loss (1.8).
5. **Rectangular conduit section.** No arched roof; the roof criterion is per section and plane strain.
6. **Debris** as a uniform layer per cell; no plug shape, no seepage through debris, no re-piping.
7. **Slot.** Reduced celerity; no water hammer physics; no sub-atmospheric pressure; no air.
8. **Clear-water continuity**; single grain size; wash load for cohesive fines.
9. **3-D roof and face effects** (end support, face collapse near the outlet) are not in the section
   criterion; F-1 remains a screening.
10. **Boundaries.** Level-pool reservoir (no waves in the reservoir); TW = 0 unless a rating is given.
11. **Approach.** Notch-width stream tube over the submerged upstream face, overlapping the level pool.

---

## 6.12 Future 2-D coupling interface and activation criteria

Not implemented in phases B–F. Defined here so that the 1-D architecture does not close the route
(plan §7).

### 6.12.1 Where the domains meet

The patch covers the **downstream exit and dam face**: from an interface section s_c on the breach axis
to the toe and a short apron downstream. The reservoir, the conduit and any downstream channel stay
1-D.
- **Pipe stage:** s_c is the conduit outlet. A depth-averaged 2-D model cannot carry pressurised flow,
  so the interface cannot lie inside the conduit.
- **Open breach:** s_c is a fixed section at the downstream crest edge or on the upper face, chosen per
  case and held fixed during the run.
- Upstream of s_c everything is 1-D; downstream of s_c the face, the expansion below the outlet and the
  toe are 2-D cells on the dam surface.

### 6.12.2 Exchange of water, momentum and sediment

Frontal coupling through one interface (after Bladé et al. 2012† and Morales-Hernández et al. 2013†):
- The 2-D cells along the interface edge form the 2-D side of the 1-D interface s_c. Their states are
  width-integrated into a 1-D right state (A, Q, C) on the interface section.
- **One flux per interface, computed once**, by the same HLLC/hydrostatic-reconstruction rule (6.13)–
  (6.20). The 1-D cell receives it in full; the 2-D boundary edges receive it distributed over the edge
  in proportion to their share of the interface section's flow area (mass, normal momentum and
  sediment). The 1-D and 2-D budgets therefore see the same number, so water and solids are
  conserved across the interface exactly.
- Transverse momentum on the 2-D side of the interface is zero at entry (the 1-D side has none).

### 6.12.3 Boundary information and time stepping

No separate boundary condition is imposed on either domain: the flux is the boundary condition. Both
domains advance with the same Δt (the smaller of the two CFL limits), so the fluxes match step by step;
subcycling with flux accumulation is a later option.

### 6.12.4 Changing geometry

The 1-D interface section must be the lateral profile of the 2-D bed along the interface edge. When
either side erodes, the interface section is rebuilt from the 2-D edge beds, and the adjacent 1-D cell
keeps its own section; the intersection rule (6.13) then handles any mismatch. Roof collapse that
reaches s_c in the pipe stage moves the interface to the open-breach position, with the water and
solids in the affected cells transferred by volume.

### 6.12.5 Activation criteria

The patch is considered only when all of these hold:
1. Phases B–E have passed and phase F has run.
2. A comparison with experimental or historical evidence shows an important error **concentrated in
   the exit or face region**, larger than the input-uncertainty band.
3. A specific 2-D mechanism (lateral spreading, expansion eddies, 2-D scour pattern) is identified as
   the likely cause, with a source.
4. The patch passes its own 2-D verification (lake at rest, dam break, wetting and drying, solids
   budget) before coupling, and the coupled model passes interface conservation tests (10⁻¹²)
   before any breach run.

**What the patch cannot do.** It cannot represent pressurised flow, the arched roof, or debris shaped
across the conduit section. Those stay 1-D limitations (§6.11). P1 may remain unresolved after the
patch; it is not built to force agreement with one experiment.

### 6.12.6 What the 1-D design keeps open for it

- Interfaces carry their own section (6.13), so a 2-D edge can stand in for a 1-D neighbour.
- The downstream boundary is an interface object (flux in, state out), not hard-coded.
- Budgets are closed through interface fluxes, so a second domain adds terms, not exceptions.
- q_l in (6.4) is kept for lateral exchange.

---

## 6.13 Decisions requested by this draft

| no. | question | proposal |
|---|---|---|
| 6-1 | approach over the submerged upstream face (overtopping) | stream tube of notch width from the upstream toe; overlap volume reported; boundary moved to the crest edge if overlap > 0.5 % |
| 6-2 | slot celerity | fixed in phase C by the insensitivity criteria (6.10) and test C6; start at 50 m/s |
| 6-3 | order of accuracy | first order is the v1 baseline; MUSCL + SSP-RK2 only if it passes the same gates |
| 6-4 | interface sections | the intersection rule (6.13) with the well-balanced correction (6.15), ours, verified in phase B |
| 6-5 | lateral spreading on the face and above the ground | none (stream tube); stated limitation and the first 2-D activation candidate |
| 6-6 | Part 3 reach closures c_b (3.6) and Appendix 3A | not used; (3.6) kept as an option for comparison |
| 6-7 | headcut | Part 4 relations as a drop-interface closure (§6.8.4); SIMBA's erosion-resistant crest dropped |
| 6-8 | wall criteria | collapsed cells: the frozen wet undrained cut (5.17), retreat ½ H_w; open-breach cells: Part 3 (3.12)–(3.14) |
| 6-9 | intact-crest overflow | Part 1 (1.8) as a non-eroding reservoir loss, as in the lumped engine |
| 6-10 | residual-block sliding (4.10)–(4.11) | kept, on the block upstream of the most upstream brink |
| 6-11 | debris | per-cell mobile store as a level layer (6.31); `export` as a comparison mode only |
| 6-12 | mixture effects | clear-water continuity in v1 |
| 6-13 | numbering | call this Part 6 of the distributed engine's own theory (`python/onedim/docs/theory/06_…`), and renumber the lumped plan's future parts (impulse waves, moraine) as 7 and 8 when they are written |
| 6-14 | minimum collapse length | none in advance; introduced only if the grid study shows non-convergence, and then with a source |

---

## References

New in this part (†: to be checked against the paper before sign-off):

- Audusse, E., Bouchut, F., Bristeau, M.-O., Klein, R., and Perthame, B. (2004). A fast and stable
  well-balanced scheme with hydrostatic reconstruction for shallow water flows. *SIAM J. Sci. Comput.*,
  25(6), 2050–2065.
- † Batten, P., Clarke, N., Lambert, C., and Causon, D. M. (1997). On the choice of wavespeeds for the
  HLLC Riemann solver. *SIAM J. Sci. Comput.*, 18(6), 1553–1570.
- † Bladé, E., Gómez-Valentín, M., Dolz, J., Aragón-Hernández, J. L., Corestein, G., and Sánchez-Juny,
  M. (2012). Integration of 1D and 2D finite volume schemes for computations of water flow in natural
  channels. *Adv. Water Resour.*, 42, 17–29.
- † Cao, Z., Pender, G., Wallis, S., and Carling, P. (2004). Computational dam-break hydraulics over
  erodible sediment bed. *J. Hydraul. Eng.*, 130(7), 689–703.
- † Celik, I. B., Ghia, U., Roache, P. J., Freitas, C. J., Coleman, H., and Raad, P. E. (2008).
  Procedure for estimation and reporting of uncertainty due to discretization in CFD applications.
  *J. Fluids Eng.*, 130(7), 078001.
- † Chaudhry, M. H. (2008). *Open-Channel Flow*, 2nd ed. Springer.
- Cunge, J. A., Holly, F. M., and Verwey, A. (1980). *Practical Aspects of Computational River
  Hydraulics*. Pitman.
- Cunge, J. A., and Wegner, M. (1964). Intégration numérique des équations d'écoulement de Barré de
  Saint-Venant par un schéma implicite de différences finies. *La Houille Blanche*, 1, 33–39.
- † Einfeldt, B. (1988). On Godunov-type methods for gas dynamics. *SIAM J. Numer. Anal.*, 25(2),
  294–318.
- † Einfeldt, B., Munz, C.-D., Roe, P. L., and Sjögreen, B. (1991). On Godunov-type methods near low
  densities. *J. Comput. Phys.*, 92(2), 273–295.
- † Goutal, N., and Maurel, F. (1997). *Proceedings of the 2nd Workshop on Dam-Break Wave Simulation*.
  EDF-DER report HE-43/97/016/B.
- Harten, A., Lax, P. D., and van Leer, B. (1983). On upstream differencing and Godunov-type schemes
  for hyperbolic conservation laws. *SIAM Review*, 25(1), 35–61.
- † Hernández-Dueñas, G., and Karni, S. (2011). Shallow water flows in channels. *J. Sci. Comput.*,
  48, 190–208.
- † Kerger, F., Archambeau, P., Erpicum, S., Dewals, B. J., and Pirotton, M. (2011). An exact Riemann
  solver and a Godunov scheme for simulating highly transient mixed flows. *J. Comput. Appl. Math.*,
  235(8), 2030–2040.
- † Liang, Q., and Marche, F. (2009). Numerical resolution of well-balanced shallow water equations
  with complex source terms. *Adv. Water Resour.*, 32(6), 873–884.
- † Morales-Hernández, M., García-Navarro, P., Burguete, J., and Brufau, P. (2013). A conservative
  strategy to couple 1D and 2D models for shallow water flow simulation. *Computers & Fluids*, 81,
  26–44.
- Preissmann, A. (1961). Propagation des intumescences dans les canaux et rivières. *1st Congress of
  the French Association for Computation*, Grenoble (as cited in Cunge et al. 1980).
- Ritter, A. (1892). Die Fortpflanzung der Wasserwellen. *Zeitschrift des Vereines Deutscher
  Ingenieure*, 36(33), 947–954.
- Roache, P. J. (1998). *Verification and Validation in Computational Science and Engineering*.
  Hermosa.
- † Spinewine, B., and Zech, Y. (2007). Small-scale laboratory dam-break waves on movable beds.
  *J. Hydraul. Res.*, 45(sup1), 73–86.
- Stoker, J. J. (1957). *Water Waves*. Interscience.
- † Thacker, W. C. (1981). Some exact solutions to the nonlinear shallow-water wave equations.
  *J. Fluid Mech.*, 107, 499–508.
- Toro, E. F. (2001). *Shock-Capturing Methods for Free-Surface Shallow Flows*. Wiley.
- † Trajkovic, B., Ivetic, M., Calomino, F., and D'Ippolito, A. (1999). Investigation of transition from
  free surface to pressurized flow in a circular pipe. *Water Sci. Technol.*, 39(9), 105–112.
- † Vasconcelos, J. G., Wright, S. J., and Roe, P. L. (2009). Numerical oscillations in pipe-filling
  bore predictions by shock-capturing models. *J. Hydraul. Eng.*, 135(4), 296–305.
- Vasconcelos, J. G., Wright, S. J., and Roe, P. L. (2006). Improved simulation of flow regime
  transition in sewers: two-component pressure approach. *J. Hydraul. Eng.*, 132(6), 553–562.
- † Vázquez-Cendón, M. E. (1999). Improved treatment of source terms in upwind schemes for the shallow
  water equations in channels with irregular geometry. *J. Comput. Phys.*, 148(2), 497–526.

Carried over (closures used unchanged): Parts 1–5 of this theory and their references — in particular
Wu (2013, 2016) for the weir, erosion, transport, widening and bank stability; Hanson et al. (2001) and
Robinson (1992) for the headcut; the FELA roof table of §5.5b and its sources (Wilson et al. 2011, 2017;
Abbo et al. 2013).
