# Theory, Part 6 — The distributed 1-D breach engine

*Distributed 1-D morphodynamic breach model (`python/onedim`, branch `1D`) · draft 3.2 · 2026-11-26 ·
status: **theory architecture signed off by the user (2026-11-26)**; accepted decisions frozen, 6-11
accepted for v1. Draft 3.2 records the first phase B results and the user's decisions on them
(6-19 to 6-21, §6.0). The step-face closure (6.16b) remains conditional; the brink closure needs no
fallback for the tested cases (B12b passed). The reference claim audit (Appendix 6B) continues.*

*Decisions taken before this draft (plan §6, 2026-11-26): two tracks; Preissmann slot; explicit finite
volume with HLLC and hydrostatic reconstruction; debris by per-cell sediment transport; package
`python/onedim/`; phase A now; a gated 2-D exit/face patch later. The qualifications attached to
decisions 2–4 are written into §6.4, §6.5, §6.7 and §6.10. New decisions requested by this draft are
collected in §6.13.*

## 6.0 Changes

### Draft 3.2 (first phase B results, user decisions, 2026-11-26)

Baseline: quick run of `run_onedim_phaseB.ps1 -Quick`, 99 cases, 13 gates passed and 9 failed
(record: `python/onedim/docs/PHASE_B_STATUS_2026-11-26.md`).

| finding | decision (user, 2026-11-26) | where |
|---|---|---|
| with (6.14) every abrupt junction loses 3–7 × the junction relation, both directions, and gradual changes over 5 cells lose about twice the abrupt Borda head; the cause is the velocity-preserving reconstruction at a width change, which presents only part of the cell's discharge to the opening | **6-19 accepted**: discharge-preserving reconstruction at width changes, velocity-preserving at bed steps (6.14a); a reconstruction rule only, no loss coefficient; contraction and mixed-section cases stay as verification tests | §6.5.3, §6.13 |
| with (6.14a) expansions agree with the relation to 0.1 % and Borda to 2.6 %; contractions lose 76–90 % less than the relation | **6-16 stays open**; Borda–Carnot is not a contraction benchmark; contractions are compared against a geometry- and regime-matched open-channel relation or data set (sources named by the user, to be checked at source, Appendix 6B) | §6.5.3, §6.13 |
| conduit → open channel: no steady state in either reconstruction, loss 2.5 × (6.14a) and 28 × (6.14) the expected value | unresolved; dedicated steady-state tests (B12d) | §6.10, App. 6A |
| B2 front 13.4 % behind the exact Ritter front at the finest quick grid (first-order smearing of the thin tip) | **6-20**: accepted as a known first-order limitation; the exact comparison and its failed 1 % target stay in the report; a same-threshold front diagnostic added | §6.10, App. 6A |
| B12c local energy gains of millimetres in single cells in both reconstructions, shrinking as the change is spread | **6-21**: the strict per-cell test becomes a diagnostic; the gate becomes refinement-based | §6.10, App. 6A |
| B12b: interface flux within 1e-5 of the critical discharge, decreasing with refinement, Fr at the brink 1.002–1.003 | the HLL flux reproduces the critical limit for the tested cases; fallback 6-18 not needed for them | §6.8.4 |
| interface wave speeds exceed the cell speeds at dry fronts (S = U + Φ) | the time step also respects max(|S_L|, |S_R|) at every interface (6.21) | §6.5.5 |

### Draft 3.1 (sign-off, 2026-11-26)

| item | change |
|---|---|
| 6-11 accepted for v1, with five required definitions | §6.7.4 rewritten: solids and porosity, occupied width and height, entrainment and deposition, export, separation from intact soil |
| contact speed (6.19) | the source check found that Batten et al.'s pressure-form S* differs from the HLL star velocity used for the shallow-water HLLC (Toro 2001) by 20–55 % in test states. Since the mass and momentum fluxes are HLL, (6.19) is replaced by the HLL-consistent contact speed (Toro's form, written with A); Batten et al. is no longer needed for the scheme |
| Einfeldt et al. (1991) scope | the paper treats the Euler equations of gas dynamics; the shallow-water positivity result is its γ = 2 isentropic analogue, as used by Toro (2001). Wording corrected (§6.5.4) |
| three wording slips | B8 row, §6.4.2 slot test values, header note |

### Draft 3 (review of draft 2, 2026-11-26) — corrections only, no redesign

| review point | change |
|---|---|
| (6.16b) is a closure, not a consequence of the equations | called a **proposed loading closure (v1 candidate)**; required tests listed: both flow directions, rectangle, trapezoid and conduit-to-open junctions, gradual changes over several cells (§6.5.3; B12a, B12c) |
| 10 → 2 m contraction: 0.0368 m against ≈ 0.025 m is not agreement | table corrected: the estimate is a rough pressurised-pipe correlation, the 47 % difference is an open discrepancy for C2b (§6.5.3) |
| brink proof uses the exact rarefaction, but the solver's flux is HLL | proof split: (a) the physical result (exact Riemann: brink cell critical); (b) what HLL actually does (no subcritical steady brink state, but Fr ≥ 1 not fixed at 1, so the discharge is **not** proven); direct flux comparison added to B12b; fallback decision 6-18 (§6.8.4) |
| (found while checking (b)) dry-state wave speeds undefined | dry-side speeds U ± Φ(A) stated, replacing the Roe averages there (§6.5.4) |
| headcut and shear erosion must remove disjoint volumes | partition stated by elevation bands and section layers; open cells may hold a stacked (layered) section (§6.2.3, §6.8.4) |
| 6-1: order of tube widening and water transfer | sequence within the step stated (§6.6.1) |
| 6-9: resolved notch, remaining crest, spillway | three disjoint outflow paths defined; (1.8) covers exactly the complement of the notch (§6.6.3) |
| 6-17: per-step diagnostic undefined | defined mathematically; stated as a round-off diagnostic, not an accuracy criterion (§6.9.1) |
| 6-4 and 6-15 cannot be approved separately | joined in §6.13 |
| reference count | there are **18** † references (17 in draft 1, plus SWASHES); the "20" in the reply to the review was a miscount. Source-to-claim status table added (Appendix 6B) |

### Draft 2 (review of draft 1, 2026-11-26)

| review item | assessment | change |
|---|---|---|
| 1.1 (6.15) and (6.16) inconsistent | The two equations agree: (6.16) is the source part of the update, not the difference of corrected fluxes, and the reviewer's own algebra (corrected fluxes equal at rest) is the lake-at-rest result. But the derivation was not written with signs, and doing so exposed a real error at expansions (next row). | §6.5.3 rewritten from the integral momentum balance, every term and sign explicit |
| (found in re-derivation) | Draft 1 loaded the step face of an expansion with the receiving cell's own stage. In steady flow this gives Q(U₂ − U₁) = g[I1_∩(η₁) − I1_∩(η₂)], an energy **gain** of about (U₁ − U₂)²/2g at an abrupt expansion. Draft 1's claim of a Borda–Carnot loss was wrong. | step faces are loaded with the upwind stage, capped by the face cell's own stage (6.16b); checked numerically: Borda loss within 2.4 % (§6.5.3) |
| 1.2 I2 and the bed-slope part undefined | Agreed. | Cunge's I2 defined; identity g(I2 + A S₀) = g ∂I1/∂s at fixed stage derived (6.5a); three cases shown (§6.5.3) |
| 1.3 physical storage overlap | Agreed: a closed budget is not a correct storage. | the region over the upstream face is partitioned: the cells own the stream tube, the reservoir curve excludes it, and water claimed by a widening tube is transferred (§6.6.1); the 0.5 % threshold is withdrawn |
| 1.4 solids budget incomplete | Agreed. | full budget with initial stores, both boundaries, reservoir deposit, disposal by comparison modes, spoil, signs and normalisation (§6.9.3) |
| 1.5 rectangular critical depth; overfall flux assumed | Agreed on both. The overfall point is now derived, not assumed. | general-section critical condition; brink-flux derivation; free-overfall test B12b (§6.8.4) |
| §2 concerns (reverse transport, dry cells, partition, splitting, slot checks, scalar bounds, 2H:1V) | Agreed. | §6.7, §6.8, §6.10 |
| §3 gates not reproducible; Phase G missing; 10⁻¹² ambiguous | Agreed. | Appendix 6A specifies each benchmark; norms defined (§6.9); Phase G pointer (§6.10) |
| §5 small corrections (1–7) | Agreed. | (6.29) symbols, (6.13) at discontinuities, (6.25) sign, (6.31) cap, collapse ordering, §6.12.6 wording; references still † |

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

An open cell may hold a **stack of such layers**, each a trapezoid with its own bottom width and wall
angle (for example a vertical-walled headcut slot under the earlier trapezoid, §6.8.4). σ_i(η) is then
piecewise linear in η, and A, T and I1 are integrated exactly layer by layer.

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
- In Cunge's form (Cunge et al. 1980) the momentum equation is written

      ∂Q/∂t + ∂/∂s ( Q²/A + g I1 ) = g I2 + g A ( S₀ − S_f ),     S₀ = −∂z/∂s                  (6.5)

  with I1 from (6.1) and I2 the longitudinal force of the walls at fixed height y above the bed:

      I2 = ∫_0^h ( h − y ) ∂σ(s, z + y)/∂s |_y dy                                                  (6.5b)

  g A S₀ is the bed part and g I2 the width part. **Identity used for the discretisation** (ours, by
  Leibniz's rule and one integration by parts):

      g ( I2 + A S₀ ) = g ∂I1(s, η)/∂s |_η          (derivative at fixed stage η)                    (6.5a)

  so the whole geometric source is the change of I1 along s at constant stage. With
  piecewise-constant cells this change happens only at interfaces, as forces on step faces (§6.5.3).
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
Wegner 1964; Chaudhry 2008†, chapter to be cited at the source check; Kerger et al. 2011† for the
slot with an explicit Godunov scheme). One set of equations then covers free-surface flow, pressurised flow and
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
hand). **Default a_s is fixed in phase C by the insensitivity test** (§6.10, C6): the results (Q, crown
pressure, filling time, collapse time) change by less than 1 % between the two highest of a_s, 2a_s and
4a_s. Starting value for
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

(width taken where both sections are open). Width functions are right-continuous: at a level where σ
jumps (the conduit crown, where it drops from b_p to the slot width T_s; the dam surface) the value
above the jump applies from that level up, so the intersection of a conduit and an open cell is
b_p below the crown and min(T_s, σ_open) above it. I1 and A of every section are integrated exactly,
piece by piece. This is the cross-section generalisation of Audusse et
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

**Discharge at a width change (decision 6-19, draft 3.2).** (6.14) carries the cell velocity to the
interface. Where the interface is narrower than the cell, this presents only the part of the cell's
discharge that lies in line with the opening, A*·U_i < Q_i, although in steady flow the whole cell
discharge passes the opening. Phase B (B12a) showed that the resulting jump in Q between the two
reconstructed states makes the HLL flux dissipate 3–7 times the junction head. The discharge is
therefore carried instead, reduced only by the part of the cell's flow area that lies below the
interface bottom (blocked by a bed step):

    Q*_{i,R} = Q_i · A^b_{i,R} / A_i,   A^b_{i,R} = A_i(η_i) − A_i(z_{i+1/2}) ≥ 0,   U*_{i,R} = Q*_{i,R} / A*_{i,R}     (6.14a)

and likewise for the right state. A*_{i,R} is unchanged from (6.14). Limits: a pure bed step (equal
widths) gives A^b = A*, so (6.14a) reduces to (6.14) and Audusse et al.'s scheme; a pure width change
(equal beds) gives Q* = Q_i; at rest Q = 0 and both forms vanish, so the lake-at-rest argument below
is unchanged. What it is and is not: a reconstruction rule, not a loss model. No empirical loss
coefficient is attached; losses come out of the flux and the face loading (6.16b) as before. The
reconstructed velocity U* can exceed U_i by the width ratio; the time step (6.21) uses the interface
wave speeds, which contain it. No cap on U* is set in v1; narrow openings are tested (B12a conduit,
B12d). Positivity rests, as before, on A* ≤ A_i and the Einfeldt speeds, and is tested (B9, B13).

**Flux.** F_{i+1/2} = F_HLLC(U*_L, U*_R) on the interface section (§6.5.4).

**Integral momentum balance of cell i (signs explicit).** Take +s downstream. The water in cell i
exchanges momentum through the open part of each interface (the intersection section) and is pushed
by the solid step faces: the part of cell i's own section that is not open at that interface. Over
one step,

    Δ(Q_i Δs_i)/Δt = Φ_{i−1/2} − Φ_{i+1/2} + W_{i,L} − W_{i,R} − g A_i S_f,i Δs_i                     (6.15)

- Φ_{i±1/2}: the numerical momentum flux through the open section, F^Q_HLLC (§6.5.4); the same number
  for both neighbours.
- W_{i,L}: force (positive downstream) of the step face at the **left** interface on cell i's water.
  It faces downstream, so it pushes in +s. W_{i,R}: magnitude of the force of the step face at the
  **right** interface; it faces upstream and pushes in −s, hence the minus sign.
- Both are hydrostatic: W = g J_i(η_f) with

      J_i(η) = I1_i(η) − I1_{i±1/2}(η)                                                              (6.16)

  the first moment, about stage η, of the area of cell i's section that lies outside the interface
  section (6.13). It includes the strip below the interface bottom (a bed step) and any width in
  excess of the neighbour's (a wall step), so bed and width steps are one term.
- η_f, the stage that loads the face, is a **proposed loading closure (v1 candidate)**. It is not a
  consequence of the Saint-Venant equations, which say nothing about the pressure on a step inside a
  cell-averaged model; it is a hydrostatic model of the separation zone, set by the flow direction at
  that interface:

      η_f = η_i                       if the interface mass flux leaves cell i (or is zero)
      η_f = min( η_i, η_nb )          if it enters cell i from the neighbour nb                      (6.16b)

  When water leaves cell i through a narrower opening (a contraction seen from cell i) the face is
  loaded by cell i's own, slower water. When water enters cell i through a narrower opening (an
  expansion seen from cell i) the face is in the separation zone beside the entering jet and carries
  the jet's stage, capped by the cell's own water level so that a dry or free-jet face carries no
  pressure. This is the Borda assumption in hydrostatic form.

In flux form (the update (6.12) with F^∓ ≡ Φ ± face terms):
F^{Q,−}_{i+1/2} = Φ_{i+1/2} + g J_{i,R}(η_f) seen by cell i, and F^{Q,+}_{i−1/2} = Φ_{i−1/2} + g J_{i,L}(η_f).

**Three checks.**

1. *Lake at rest.* η uniform, Q = 0: the reconstructed states (6.14) on each interface are equal, so
   Φ = g I1_{i±1/2}(η) exactly and η_f = η. Then
   Φ_{i−1/2} − Φ_{i+1/2} + W_{i,L} − W_{i,R}
   = g I1_{i−1/2} − g I1_{i+1/2} + g(I1_i − I1_{i−1/2}) − g(I1_i − I1_{i+1/2}) = 0,
   for any bed and any width variation. (This is the reviewer's observation: the corrected fluxes
   seen by cell i are equal at rest. The geometric source in the update is the face pair,
   W_{i,L} − W_{i,R} = g[I1_{i+1/2}(η) − I1_{i−1/2}(η)], which is what draft 1 called (6.16).)
2. *Bed step, constant width B (rectangle).* J_i = B(η_i − z_i)²/2 − B(η_i − z_{i+1/2})²/2, which is
   Audusse et al.'s (2004) correction g(h_i² − h*²)/2 per unit width. The scheme reduces to theirs.
3. *Width step, constant bed; and both together.* J_i is the moment of the excess width
   (σ_i − σ_nb)⁺ below η, plus the bed strip when the bed also steps; the two are disjoint parts of
   the same area, so they add. For smooth geometry cut into small cells, the face pair of a cell is
   g[I1_{i+1/2}(η_i) − I1_{i−1/2}(η_i)] → g ∂I1/∂s|_η Δs = g(I2 + A S₀)Δs by (6.5a): the scheme is
   consistent with (6.5). The choice (6.16b) changes the face force only by O((ΔU)²) at a step and
   does not affect consistency or the lake at rest.

**Steady flow through an abrupt section change** (rectangles, same bed, Q = 2 m³/s, h₁ = 1 m; the
steady cell balance across the step solved exactly; `verification` script to be committed with phase
B):

| junction | draft-1 face rule (receiving cell's stage) | rule (6.16b) | reference |
|---|---|---|---|
| expansion 2 → 4 m | energy **gain** 0.0127 m | loss 0.0131 m | Borda (U₁ − U₂)²/2g = 0.0134 m |
| expansion 2 → 10 m | gain 0.0307 m | loss 0.0328 m | Borda 0.0329 m |
| contraction 4 → 2 m | loss 0.0143 m | loss 0.0143 m (same rule) | rough estimate 0.014 m* |
| contraction 10 → 2 m | loss 0.0368 m | loss 0.0368 m | rough estimate 0.025 m*: **47 % lower, unresolved** |

\* K ≈ 0.5 (1 − A₂/A₁) U₂²/2g, a pressurised-pipe correlation used only for scale; open-channel
contraction-loss data are to be identified at the source check.

What the table shows, and no more: with (6.16b) the two abrupt expansions lose the Borda head to within
2.4 %, and no junction gains energy. The contractions lose a head of the right order, but the strong one
loses about 47 % more than the rough estimate; that discrepancy is open, not agreement. Gradual changes
resolved over many cells should lose only O((ΔU)²) per cell, which vanishes with refinement; that is a
claim to be tested (B12c), not shown here. The contraction result matters where a collapsed cell drains
into the next conduit, where the frozen lumped engine uses a rounded entrance K_u ≈ 0.05 (decision 6-16,
measured in C2b before anything is done about it).

**Required before (6.16b) is accepted** (with the intersection rule, decision 6-4/6-15): the junction
tests B12a in **both flow directions**, for rectangle, trapezoid and conduit-to-open junctions, and B12c
(gradual expansion and contraction over 5–50 cells: no energy gain anywhere, and a total loss that falls
towards zero as the change is spread over more cells).

**Positivity.** The interface section is contained in each neighbour's section (6.13), so the
reconstructed area never exceeds the cell's own area. With Einfeldt wave speeds this gives the
Audusse et al. positivity argument for the mass update, which does not involve the face forces. It
is an argument, not a proof for this extension, and is tested (B9, B13).

Ours. It is built from Audusse et al. (2004) (hydrostatic reconstruction over non-flat beds), Cunge et
al. (1980), Vázquez-Cendón (1999)† (source terms for locally rectangular irregular channels) and
Hernández-Dueñas and Karni (2011)† (balance laws for arbitrary cross-sections). None of these proves
the intersection rule or the step-face loading (6.16b); they are verified, not trusted, in phases B and C.

### 6.5.4 The HLLC flux

The physical flux on a section is F(U) = (Q, Q²/A + g I1(A), Q C), with I1 as a function of A on the
interface section.

**Wave-speed estimates** (Einfeldt 1988; Einfeldt et al. 1991†), with Roe-type averages
Ũ = (√A_L U_L + √A_R U_R)/(√A_L + √A_R) and c̃ = c on the interface section at the mean area:

    S_L = min( U_L − c_L, Ũ − c̃ ),    S_R = max( U_R + c_R, Ũ + c̃ )                                (6.17)

Einfeldt speeds are chosen because, with them, the HLLE flux is positively conservative under
conditions on the wave speeds. Einfeldt et al. (1991) prove this for the Euler equations of gas
dynamics; the shallow-water equations in a rectangular channel are their γ = 2 isentropic analogue, and
the result is used for them in that form (Toro 2001). That result does not by itself
cover this scheme (intersection sections, step faces, slot): positivity here rests on the argument of
§6.5.3 and on tests B9 and B13.
In a full conduit c = a_s, so the speeds include the slot celerity automatically.

**Dry side.** If one reconstructed state is dry, the Roe averages degenerate and are not used. The
speeds are those of the dry-front rarefaction (Toro 2001, Ch. 5, generalised to a section through
(6.8)): with the left side wet and the right dry, S_L = U_L − c_L and S_R = U_L + Φ_L(A_L); mirrored
for a dry left side. For a rectangle Φ = 2c, Toro's U_L + 2c_L.

**Mass and momentum flux: HLL.** In one dimension the shallow-water system has only the two acoustic
waves, so the HLLC mass and momentum fluxes are the HLL ones (Toro 2001, Ch. 10):

    F_HLL = [ S_R F(U_L) − S_L F(U_R) + S_L S_R (U_R − U_L) ] / (S_R − S_L)    for S_L < 0 < S_R      (6.18)

(and F(U_L) or F(U_R) when both speeds have one sign).

**Concentration flux: the contact wave.** The third wave of HLLC is the contact that carries the
concentration. Its speed is the velocity of the HLL intermediate state, the form used for the
shallow-water HLLC with a passive scalar (Toro 2001), written here with the flow area in place of the
depth:

    S* = [ S_L A_R (U_R − S_R) − S_R A_L (U_L − S_L) ] / [ A_R (U_R − S_R) − A_L (U_L − S_L) ]          (6.19)

This choice is consistent with the HLL mass and momentum fluxes the scheme actually uses. (Draft 3 used
the pressure form of Batten et al. (1997)†, derived for the Euler equations; in test states it differs
from (6.19) by 20–55 %, so it is not used.)

and the sediment flux is the HLL mass flux times the upwind concentration:

    F^{AC} = F^A_HLL · ( C_L if S* ≥ 0, else C_R )                                                   (6.20)

This contact is the extra wave structure HLLC resolves and HLL smears: a sediment front (debris
released by a collapse) stays sharp, and C gains no new extrema under the CFL condition. For the
water alone HLLC and HLL are identical, so the choice does not change the hydraulics.

### 6.5.5 Time step, friction and dry cells

**CFL step.**

    Δt = CFL · min( min_i Δs_i / ( |U_i| + c_i ),  min_{i+1/2} Δs_{i+1/2} / max(|S_L|, |S_R|) ),   CFL = 0.9 (first order)   (6.21)

with Δs_{i+1/2} the smaller of the two cells. The second term (draft 3.2) is the condition of the
Audusse et al. positivity argument; it matters at dry fronts, where S_R = U_L + Φ_L exceeds |U| + c,
and at narrow openings under (6.14a).

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

    dV_r/dt = Q_in − F^A_{1/2} − Q_ov − Q_sp − Q_tr,      z_s = Z_r(V_r)                              (6.23)

integrated with the same Δt (Q_tr: the tube transfer below; Z_r = Z in piping mode). The boundary state at the first interface is found from two equations:

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

**Approach section, overtopping: one owner for every parcel of water (decision 6-1).** The toe
boundary uses a **stream tube of the notch width** over the submerged upstream face: cells there have
the notch section, with the face surface as bed where the notch has not cut it. The space is
partitioned so that no water is counted twice:

- The 1-D cells own the stream tube Ω_t(t): the space above the dam surface (or the notch bed) inside
  the notch top width, from the upstream toe to the upstream crest edge.
- The reservoir owns everything else. Its stage–volume relation is the case curve minus the tube:

      V_r(z) = V(z) − V_t(z),     V_t(z) = Σ_{upstream-face cells} A_i(z) Δs_i                       (6.23a)

  where A_i(z) is the cell's area below z. V_r is recomputed whenever the tube's geometry changes. The
  reservoir's state variable is its own water volume V_r, and z_s = Z_r(V_r).
- **Exchange when the tube changes.** Erosion of the bed inside the tube enlarges the cells only (the
  stored water is kept, §6.5.6). Widening of the tube takes a strip from the reservoir's space: the
  water in that strip below z_s is moved from V_r to the cell, as one recorded transfer, so both
  budgets close and the total physical storage is counted once.
- **Order within the step** (after the flow update has set z_s^{n+1} and the cell states):
  (1) the cell geometry is updated (§6.8.1); (2) the newly claimed strip of each upstream-face cell is
  computed between its old and new top widths; (3) the strip's water volume below z_s^{n+1},
  ΔV_tr,i, is computed on the new geometry; (4) ΔV_tr,i is added to A_i Δs_i and removed from V_r;
  (5) V_t(z) and hence Z_r are rebuilt. Since the removed volume equals the strip volume below z_s^{n+1},
  Z_r(V_r) returns z_s^{n+1} unchanged: no water is created and the stage does not jump. The cell's
  stage is then recomputed from its new A_i.
- **Piping mode has no overlap**: the boundary is the pipe inlet, and the upstream face is not part of
  the path.

Total storage is then V_r + Σ A_i Δs_i with no double count, which is the physical statement the
budget (6.33) checks. The alternative, a boundary at the upstream crest edge with no cells on the
upstream face, is kept as an option; it avoids the partition but does not resolve the notch cut into
the upstream face. The draft-1 0.5 % threshold is withdrawn.

### 6.6.2 Downstream: free outfall or tailwater rating

- **Free outfall (default, TW = 0 as in O-1, an assumption with that status).** If the last cell's flow
  is supercritical leaving the domain, the boundary is transmissive (zero gradient). If subcritical,
  the boundary state is critical, Fr_b = 1, together with the incoming invariant R⁺_b = R⁺_N. This is
  the standard free-overfall closure (critical depth just upstream of the brink).
- **Tailwater rating (option).** A stage–discharge relation η_b = f_TW(Q_b) (Manning normal depth in a
  prismatic downstream channel, or a stage series) with R⁺_b = R⁺_N. Its source and status are
  recorded in the case file.

### 6.6.3 Intact-crest overflow

**Three disjoint outflow paths.** (i) The **resolved notch**: all flow within the notch top width
B_top,cr at crest level goes through the 1-D cells and erodes them. (ii) The **remaining intact crest**,
of length max(L_cr − B_top,cr, 0): Part 1 (1.8), non-eroding. (iii) A **spillway or outlet**, Q_sp, from
its own rating. Because (1.8) uses exactly the crest length outside B_top,cr, no part of the crest is
counted in two paths.

**On the breach axis, overtopping is in the domain.** In overtopping mode the notch cells lie along the
axis, so all flow through the notch is solved and erodes the cells. Part 1 (1.8) is used only for the
crest length **outside** the notch top width: a direct, non-eroding reservoir loss Q_ov with B_top,cr the
notch top width at the upstream crest edge, exactly as in the lumped engine.

**Piping mode with the reservoir above the crest is out of scope in v1.** There the path is the pipe, so
crest overflow above the conduit would bypass the domain and its erosion would not be modelled. Rather
than remove that water silently, a piping run in which z_s rises above the crest stops with an
out-of-scope flag. ARS P1 is not affected (z_s = 1.10 m, crest 1.30 m). A second resolved surface path
over the crest, joining the face cells, is the later option.

### 6.6.4 Hydraulic transitions inside the domain


| transition | treatment |
|---|---|
| critical control (weir crest, start of the face) | emerges where the bed is highest; transcritical rarefaction resolved by the Riemann solver (phase B test B5) |
| hydraulic jump on the face or at the toe | shock, mass and momentum conserved, energy dissipated (test B6) |
| pipe inlet | §6.6.1, energy with K_u, then the conduit section |
| pipe outlet, free jet onto the face | interface between the last conduit cell and the first face cell; flux through the conduit opening (6.13); expansion loss from the step-face balance (6.15)–(6.16b) (Borda). With a free outfall at the toe and no tailwater, the jet's velocity head is lost downstream, which is the lumped K_d ≈ 1 recovered as a result (test C2) |
| pressurisation front | moving front between part-full and slot states, resolved by the scheme (test C4) |
| conduit beside a collapsed cell | the collapsed cell is open; the conduit discharges into it through its opening; the collapsed cell's stage is free (atmospheric) |
| water above the dam surface in any cell | allowed in the stream tube (6.2); flagged and reported, since it means water would spill across the dam (a 2-D effect) |
| bed drop larger than the critical depth (headcut) | sub-grid closure §6.8.4 |

---

## 6.7 Local erosion and sediment transport

### 6.7.1 Bed shear, in every cell

    τ_i = ρ g n² U_i |U_i| / R_i^{1/3}                                                               (6.25)

the signed form of Part 1 (1.12), identical to Part 5 (5.5) (τ = ρ f U²/8 with f = 8gn²/R^{1/3}).
The erosion laws use the magnitude |τ_i|; the sign only says which way the flow, and the transported
sediment, goes.
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

    Ė_i − Ḋ_i = |Q_i| ( C_cap,i − C_i ) / L_s,i,     L_s,i = λ b_i,     λ = 6 field, 3 lab (2.8)          (6.28)

with C_cap,i the Part 2 total-load capacity (2.3)–(2.4b) evaluated with |U_i| and |τ_i|, DL Breach
combination by default, and f_t applied once. The steep-slope correction (2.5a–b) uses the bed angle
**in the direction of flow**, θ_i = atan[sgn(U_i)(z_{i−1} − z_{i+1})/(Δs_{i−1/2} + Δs_{i+1/2})], so
reverse flow sees the slope it actually runs down or up. Positive values erode, negative deposit.

**Concentration bound.** Volumetric C cannot exceed C_max = 1 − n_d (packed bed). A step in which the
source would push C past a much lower dense-flow limit, taken as 0.1 (beyond the dilute assumption of
§6.3.1), is flagged in the output; C is not clipped, because clipping would create or destroy solids.

**Relation to the lumped form.** For steady uniform flow over a reach, (6.26) with (6.28) integrates
to Part 2 (2.7) exactly. That is phase D test D2: the distributed model reproduces the lumped
non-equilibrium solution in its own limit, so the two engines differ only where the flow does.

**Integration of the source.** The relaxation (6.28) is stiff when Δs ≪ L_s is not met or U is large.
It is integrated exactly over the step (as (2.7) integrates it over a reach):

    C_i^{n+1} = C_cap,i + ( C_adv,i − C_cap,i ) exp( −|U_i| Δt / L_s,i )                             (6.29)

with C_adv,i the concentration after advection. The solids exchanged, (C_i^{n+1} − C_adv,i) A_i Δs_i,
are taken from the bed (positive) or added to it (negative) (§6.7.3). For erosion the exchange is
limited to what the mobile store and the intact soil above the base can supply.

### 6.7.3 Exner: from exchanged solids to bed change

The bulk volume eroded (or deposited) in cell i during the step is

    ΔV_i = ( Ė_i − Ḋ_i ) Δs_i Δt / (1 − p)                                                           (6.30)

(Part 2 (2.9), per cell). Eroded volume is taken first from the cell's mobile store (§6.7.4), then from
intact soil. Deposited volume goes to the mobile store. How ΔV changes the section is §6.8.1.

### 6.7.4 The mobile store: debris and deposits *(decision 6-11, accepted for v1)*

**What is represented.** Each cell carries one **mobile store**: loose solids lying on its intact bed as
a level layer. This is a v1 representation of a debris deposit in a cross-section-averaged model; it does
not attempt the three-dimensional shape of a real deposit, a plug with a gap beside it, or debris-flow
behaviour (§6.7.5, §6.11). The five definitions required at sign-off follow.

**1. Solids volume and porosity.** The state variable is the **solids volume** M_i (m³ of grains), never a
bulk volume. Material enters as solids: a fallen roof of intact porosity n contributes (1 − n) × its
bulk volume (§6.8.2); a failed wall wedge likewise; deposited sediment arrives as solids from (6.28);
the suspended solids of a drying cell arrive as (A C)_i Δs_i. In the store the solids sit at the
deposited porosity n_d (default n_d = n, sensitivity n_d > n, Part 5 (5.12a)), so the store's **bulk
volume** is M_i/(1 − n_d).

**2. Occupied width and height.** The layer fills the cell's section from its intact bed z_b,i upward,
following the walls: its surface z_d,i is the level at which the section's area below z_d,i holds the
bulk volume,

    Δs_i ∫_{z_b,i}^{z_d,i} σ_i^bed(η) dη = M_i / (1 − n_d)                                            (6.31)

with σ_i^bed the width of the cell's soil section (the trapezoid or layer stack of §6.2.3, without the
water stream tube above z_g). The occupied width at height η is σ_i^bed(η); the top width of the layer
is σ_i^bed(z_d,i). For a vertical-walled cell this is z_d,i = z_b,i + M_i/((1 − n_d) b_i Δs_i), the
draft-2 form. The surface z_d,i is the cell's bottom elevation for the hydraulics, so a layer obstructs
the flow from the instant it forms.

**3. Entrainment and deposition.** The wetted perimeter of the cell is split at z_d,i: the part in contact
with the layer (its top surface, width σ_i^bed(z_d,i)) and the intact walls above it.
- **On the layer:** cohesive debris detaches at f_kd k_d,debris (|τ_i| − τ_c,debris)⁺ (defaults: the intact
  values, Part 5 §5.7); non-cohesive debris supplies the transport-limited exchange (6.28). Solids leave
  M_i and enter (A C)_i.
- **On the intact walls above the layer:** the intact law and the intact porosity p, as in §6.8.1.
- **Deposition** (non-cohesive, (6.28) negative): solids leave (A C)_i and enter M_i; the bed of intact
  soil does not rise.
- If the layer is used up within a step, the remaining erosion capacity of that step acts on the intact
  bed below, by the intact law.

**4. Export.** Debris leaves the domain only **as suspended sediment**: it is entrained into (A C)_i,
advected by (6.20), and counted in S_out when it crosses the outfall (or S_res if reverse flow carries it
into the reservoir). There is no direct transfer from a store to the boundary. The comparison mode
`debris_mode = "export"` is the one exception: it removes fallen solids at once and books them as S_disp,
separately from S_out (§6.9.3).

**5. Separation from the intact soil (no double counting).** The intact geometry (bed z_b,i, walls, layer
stack) and the store M_i are separate state variables:
- the intact geometry changes only by intact erosion (§6.8.1, walls and, once the layer is gone, bed),
  roof collapse, wall failure and headcut crossing (§6.8.4); each of these books its solids once in
  S_int;
- the store changes only by its inputs (fallen roof, failed walls, deposition, drying) and by
  entrainment from its surface;
- solids moved from intact soil into the store are booked in S_int when they leave the intact soil and
  counted afterwards only in S_M, never again in S_int;
- the solids budget (6.34) checks the sum every step.

**Cap.** The debris surface cannot rise above the dam surface: z_d,i ≤ z_g,i. Solids beyond that go
to a per-cell **spoil** store, counted in the budget (6.34) and hydraulically inactive, as the spoil
beside the slot in Part 5 (5.12b).

**Dry cells and suspended sediment.** The conserved quantity is (A C)_i; C_i = (A C)_i / A_i is formed
only when A_i > A_dry (the area at h_dry). When a cell dries (A_i ≤ A_dry), its suspended solids
(A C)_i Δs_i are deposited into M_i and (A C)_i is set to 0, conserving solids; a cell that wets
starts with C = 0 and receives sediment only by advection. The advective flux (6.20) uses the upwind
C only from a wet side.

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

The same normal thickness Δz acts on the bed and on the walls (Part 3 §3.2), so the partition follows
the geometry: the bed takes b_i Δs_i Δz and the walls the rest. The section then updates by Part 3
(3.3)–(3.5) unchanged (bed lowers by Δz, top width grows by
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

**Collapse of cell i.** The roof check reads the state after the flow and erosion updates of the
step (§6.5.6). When the margin crosses zero, in this order:
1. The roof solids V_s,i = (1 − n) b_p,i (z_g,i − z_cr,i) Δs_i go into the cell's mobile store M_i.
2. The cell becomes a collapsed cell (§6.2.3(c)): open, width b_p,i, vertical walls from the intact bed
   z_inv,i to z_g,i, debris surface z_d,i from (6.31). With n_d = n, z_d,i = z_g,i − a_p,i, the
   per-cell form of Part 5's z_d ≈ H − a_p.
3. The water in the cell is kept (A_i Δs_i), and the stage is recomputed on the new section, with the
   debris surface as its bottom (§6.5.6). The water now stands in an open cell, at atmospheric
   pressure. Pore water of the fallen roof (partly saturated) is not added to the cell's water; the
   omission is stated, and its size, n S_r V_roof, is reported.
4. The suspended concentration of the cell is unchanged (the debris enters the store, not the flow).
5. Neighbouring cells are not changed by rule. They lose nothing they were credited with (no end
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

1. **Critical depth on the actual section.** The brink cell is cell i (upstream of the drop). Its
   critical depth y_c,i solves the general condition Q_i² T_i / (g A_i³) = 1 on cell i's own section
   (Part 1 (1.4)); A, T and Q all come from cell i. The rectangular d_c = (q²/g)^{1/3} is used only
   where that section is rectangular.
2. **Drop interface (plunging condition (4.2)).** Interface i+1/2 is a drop interface when
   z_i − z_{i+1} > y_c,i and the downstream stage is below the brink, η_{i+1} < z_i.
3. **The overfall discharge: physical result and numerical flux, kept apart** *(ours)*.
   - **(a) Physical result (exact Riemann flux).** With the downstream side dry, the exact interface
     flux is the sonic state of the left rarefaction from cell i's state. Along it R⁺ = U + Φ(A) is
     constant (6.8), so Q(A) = A [R⁺ − Φ(A)] and dQ/dA = U − c: the flux is largest at the sonic point.
     In steady flow cell i's own discharge must equal that maximum, which happens only if cell i is
     sonic: **the brink cell is critical, Q²T/(gA³) = 1**, for any section shape, and the discharge is
     the critical-flow discharge for the brink cell's energy (Part 1 (1.4)–(1.5)).
   - **(b) What the HLL flux actually does.** The solver does not use the exact flux. With the dry-side
     speeds of §6.5.4 (S_L = U − c, S_R = U + Φ), the HLL mass flux for a wet left state and a dry
     right state is F = S_R (Q − S_L A)/(S_R − S_L) when S_L < 0. Setting F = Q gives
     S_L (Q − S_R A) = 0, which requires U = U + Φ: impossible. So **HLL admits no subcritical steady
     brink state**: the brink cell is driven to Fr ≥ 1 (when S_L ≥ 0 the flux is the cell's own, and any
     supercritical state is steady-compatible). HLL therefore does not by itself select Fr = 1, and
     the transonic jump between the subcritical approach cell and the brink cell does not shrink with
     the grid. **The discharge over a drop is not proven** to converge to the critical-flow value.
   - **(c) Verification.** B12b compares the computed interface flux directly with the independently
     computed critical discharge for the same upstream energy, at N, 2N, 4N and 8N, and reports the
     brink-cell Froude number. Pass: the flux error falls below 1 % and decreases with refinement.
   - **(d) If B12b fails**, the fallback (decision 6-18) is the exact sonic flux of (a) at drop
     interfaces only, with HLL everywhere else. It is decided by the test, not in advance.
4. **Advance.** The brink retreats at Part 4 (4.3)–(4.9) with H_h = z_i − z_{i+1}, d_c = y_c,i,
   d_bw = max(y_c,i, h_{i+1}) and the soil's k_d, τ_c, c_u, γ_t. Robinson's relations were derived for
   a rectangular overfall: they are used with q = Q/b where the notch walls are vertical (the usual
   cohesive case, Part 3 §3.4), and with q = Q/T(y_c) where they slope, an approximation flagged in
   the output and tested in the sensitivity analysis. E_v ≤ 0 caps the advance at the cascading-face
   rate, as in Part 4.
5. **Disjoint volumes, by construction.** Within a step, in this order:
   - Shear erosion (§6.8.1) removes, from each cell, the layer of normal thickness Δz from its bed and
     walls: on cell i everything **above** the updated bed z′_i, on cell i+1 everything above z′_{i+1}.
   - The headcut crossing then removes, from cell i only, the prism **between z′_{i+1} and z′_i** over
     the updated bottom width b′_i: V_s = (1 − p) b′_i (z′_i − z′_{i+1}) Δs_i. Cell i's section gains a
     vertical-walled layer of width b′_i from z′_{i+1} to z′_i under its existing layers (the Part 4
     vertical headcut slot, §4.9); its walls above z′_i are untouched.
   - The three volumes lie in different cells or different elevation bands, so they cannot overlap,
     and the solids budget (6.34) checks the sum. If the new, taller wall is unstable, §6.8.3 fails it
     on the next check and the wedge goes to the store: a separate, recorded volume.
   - The water in cell i is kept (§6.5.6). Until the brink crosses it, cell i erodes by its own shear
     over its whole bed; this sub-cell error is at most one cell and should vanish with Δs (grid study).
6. **Base scour** at the larger of the downstream cell's own shear (6.25) and the jet stress τ_hf (4.7),
   as in Part 4 §4.3.
7. **What is dropped.** SIMBA's erosion-resistant crest during stages 1–2 (Part 4 §4.3) is not used:
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

    E_w(t) = [ V_r(t) + Σ_i A_i Δs_i ] − [ V_r(0) + Σ_i A_i(0) Δs_i ] − ∫_0^t ( Q_in − Q_ov − Q_sp − F^A_{N+1/2} ) dt   (6.33)

The reservoir–domain flux F^A_{1/2} and the tube transfer Q_tr are internal and cancel. The finite-volume
update is conservative, and geometric events keep A_i Δs_i (§6.5.6), so E_w is round-off only.

**Norm and gate.** ε_w = |E_w(t)| / max( V_r(0) + Σ A_i(0) Δs_i + ∫ Q_in dt , V_floor ), V_floor = 10⁻⁹ m³
(so a dry or empty test does not divide by zero). It is the **cumulative** error, evaluated at every
output step. Gate: ε_w < 10⁻¹⁰ in every run. The draft-1 value 10⁻¹² is kept only as a **per-step**
check in the phase B tests: over 10⁶–10⁷ steps, round-off of order 10⁻¹⁶ per step can accumulate past
10⁻¹², which is not a conservation fault.

**Per-step diagnostic (defined).** For step n, with W = V_r + Σ A_i Δs_i,

    δ_w^n = | (W^{n+1} − W^n) − Δt (Q_in − Q_ov − Q_sp − F^A_{N+1/2})^n | / max( Σ_i |ΔA_i| Δs_i + Δt (|Q_in| + |Q_ov| + |Q_sp| + |F^A_{N+1/2}|) , V_floor )

the step's imbalance relative to the step's total turnover. Phase B requires δ_w^n < 10⁻¹² in every step;
the same definition with solids terms gives δ_s^n. It is a round-off diagnostic that detects a
non-conservative operation in one step; it is not a measure of physical accuracy. Reported alongside, as modelling approximations and not budget
terms: the slot storage (§6.4.2) and the omitted debris pore water (§6.8.2).

### 6.9.2 Momentum

Momentum is not conserved (bed, walls and friction act on it). In phases B and C a momentum budget is
computed as a diagnostic: the change of Σ Q_i Δs_i equals the boundary fluxes plus the step-face forces
of (6.15) plus friction, to round-off. Across a hydraulic jump the conjugate depths are checked (test B6).

### 6.9.3 Solids

All terms are solids volumes, ≥ 0, cumulative from t = 0:

    S_susp(t) + S_M(t) + S_sp(t) + S_res(t) + S_out(t) + S_disp(t)
        = S_susp(0) + S_M(0) + S_sp(0) + S_int(t)                                                (6.34)

| term | definition |
|---|---|
| S_susp | Σ (A C)_i Δs_i, suspended in the cells |
| S_M | Σ M_i, mobile stores (fallen roof, failed walls, deposits, solids of dried cells) |
| S_sp | Σ spoil, solids above the dam-surface cap (6.31), hydraulically inactive |
| S_res | −∫ min(F^{AC}_{1/2}, 0) dt: solids carried **into the reservoir** by reverse flow. The reservoir delivers clear water (C = 0), so F^{AC}_{1/2} ≤ 0 always; solids that enter it are taken to settle there and are not re-entrained |
| S_out | ∫ F^{AC}_{N+1/2} dt: solids carried past the outfall. A tailwater rating also returns clear water, so this term never decreases |
| S_disp | solids removed by a comparison mode (`debris_mode = "export"`), kept separate from S_out because they are not transported |
| S_int | solids removed from intact soil by erosion, roof collapse, wall failure and headcut retreat |

**Norm and gate.** ε_s = |LHS − RHS| / max( S_int(t) + S_susp(0) + S_M(0) + S_sp(0), S_floor ),
S_floor = 10⁻¹² m³, cumulative, every output step; gate ε_s < 10⁻¹⁰, as for water. This is the per-cell
form of Part 5 (5.13), with "exported" now split into what was carried out (S_out, S_res) and what a
comparison mode removed (S_disp).

---

## 6.10 Verification and validation requirements

Gates are hard: a phase does not start until the previous one passes. Pass criteria are written here,
before any run. All tests run in both water-only form and, where relevant, with the passive
concentration. **Exact setups (domain, initial and boundary conditions, reference solution, grid
sequence, error norm) are in Appendix 6A**, so that the tests can be reproduced by someone other than
the author of the solver. Every run also reports ε_w and ε_s (§6.9).

**Phase B — open-channel solver, fixed geometry.**

| test | setup | pass criterion |
|---|---|---|
| B1 lake at rest | irregular bed *and* irregular widths, trapezoids and rectangles, wet and partly dry | |U| < 10⁻¹² m/s and η constant to 10⁻¹² m after 10⁵ steps |
| B2 Ritter dam break | dry downstream bed, rectangle | L1 error in h and U → 0 with Δs; observed order reported (≈ 1 expected at first order); front position within 1 % at the finest grid (kept and reported; a failure is a known first-order limitation, decision 6-20); diagnostic: numerical and exact front at the same depth threshold h_th = 10⁻³ m, error reported at every grid and required to fall with refinement |
| B3 Stoker dam break | wet downstream, rectangle | as B2; shock speed and intermediate state within 1 % |
| B4 variable section | manufactured smooth solution in a trapezoid with varying width, side slope and bed (Appendix 6A) | observed order p ≥ 0.9; conservation to the gate |
| B5 transcritical flow over a bump | the three SWASHES bump cases after Goutal and Maurel (1997)† (subcritical, transcritical with and without shock) | steady profiles within 1 % of the **analytic** Bernoulli/conjugate solution (not of the workshop's numerical results) |
| B6 hydraulic jump | supercritical inflow, subcritical tailwater | conjugate depths (Bélanger) within 1 %; momentum flux continuous across the jump to the grid error |
| B7 GVF profiles | M1, M2, S2 in prismatic and non-prismatic channels with Manning friction | within 1 % of a direct-step solution at the finest grid |
| B8 wetting and drying | SWASHES planar surface in a parabola (1-D reduction of Thacker 1981†), Appendix 6A | shoreline and h converge; positivity never violated |
| B9 positivity | two strong rarefactions leaving a near-dry middle (Toro 2001) | A ≥ 0 every step; no NaN; mass to 10⁻¹² |
| B10 steep bed steps and near-dry cells | flow down a 1:2 face onto a flat apron; step-up and step-down beds | stable; mass to 10⁻¹²; profile converges with Δs |
| B12a steady abrupt junctions | expansions and contractions, rectangles, trapezoids and conduit → open, **in both flow directions** | steady head change within 1 % of the junction relation of §6.5.3; Borda within 3 % for expansions; contraction losses reported against data; no energy gain at any junction |
| B12b free overfall | subcritical approach to a drop onto a dry apron, N to 8N | computed interface flux against the independently computed critical discharge for the same upstream energy: error < 1 % and decreasing with refinement; brink-cell Fr reported; failure triggers decision 6-18 |
| B12c gradual junctions | the B12a changes spread over 5, 10, 20, 50 cells, both directions; and a transition of fixed length at Δs, Δs/2, Δs/4 (decision 6-21) | gate: (1) the largest local energy gain falls with grid refinement; (2) no gain at the transition persists or grows with refinement; (3) the net head change across the transition is a loss at every grid; (4) the total transition loss converges with refinement. Diagnostics: the strict per-cell test (no gain > 10⁻⁶ m) and the loss against the number of cells used for the change |
| B12d conduit outlet | full conduit (slot) discharging into an open channel, submerged and free outlet, both directions | a steady state is reached (change < 10⁻¹⁰ over 500 steps); head change reported against the junction relation and Borda; required before C2b |
| B13 passive scalar | contact discontinuity in C advected through uniform, varying-section and wet/dry reaches | 0 ≤ C ≤ max C(0) every step; (A C) ≥ 0; no new extrema; solids to the ε_s gate |
| B11 grid and dt convergence | B2, B6, B7 at Δs, Δs/2, Δs/4 and CFL, CFL/2 | observed order and GCI (Roache 1998; Celik et al. 2008†) reported |

**Phase C — conduit with the slot.**

| test | pass criterion |
|---|---|
| C1 steady full pipe | reservoir to reservoir through a full conduit (both ends submerged, Appendix 6A): discharge within 0.5 % of Q = A √(2gΔH/(K_u + 1 + fL/4R)); crown pressure along the pipe within 0.5 % of the linear friction profile, i.e. (5.8) |
| C2b contraction into a conduit | open cell draining into a conduit (the collapsed-cell case): head loss reported against K_u = 0.05 (Part 1) and the sharp-edged value; no pass threshold, it decides decision 6-16 |
| C2 free outlet and expansion | head loss at the outlet within 1 % of Borda–Carnot; with a free outfall the computed outflow matches (5.3) with K_d = 1 within 1 % (the lumped outlet convention recovered or not, reported either way) |
| C3 surge celerity | a pressure step travels at a_s within 1 % |
| C4 pipe filling | the filling bore speed and the pressurisation time against the mass and momentum jump conditions; oscillations behind the front measured and reported (peak-to-peak pressure); comparison with the Trajkovic et al. (1999)† or an equivalent filling experiment |
| C5 pressurised ↔ free surface | emptying and refilling cycle; mass to 10⁻¹²; no spurious pressurisation |
| C6 slot sensitivity | (i) both conditions (6.10) hold in every C test and every case run later (checked and logged each run); (ii) a_s, 2a_s and 4a_s: Q, the crown-pressure distribution along the pipe, the pressurisation time and the filling-front position change < 1 % between the two highest values used. Together these fix the default a_s; 50 m/s is only the starting value |
| C7 HLLC with the slot | C1–C6 run with the HLLC flux; stable at CFL 0.9 and 0.45; **the slot is accepted only if C1–C7 pass** |
| C8 priming | the emergent priming of a growing pipe compared with the lumped step (size and direction, F < 1.05 up, F > 1.05 down); reported |

If C4 oscillations or C7 stability fail at first order with Einfeldt speeds, the two-component pressure
approach is investigated (plan qualification 1). The choice is never made on breach results.

**Phase D — morphology.**

| test | pass criterion |
|---|---|
| D1 solids budget | (6.34) within the gate of §6.9.3 through erosion, deposition, collapse, bank failure and drying |
| D2 non-equilibrium relaxation | steady uniform flow, clear inflow: C(s) = C_cap(1 − exp(−s/L_s)) within 0.5 % at Δs ≤ L_s/5 |
| D3 uniform-flow limit | a prismatic erodible reach in uniform flow: per-cell erosion rate and widening equal the lumped (2.1)/(2.3)–(2.9) and (3.1)–(3.5) for the same τ to 10⁻⁹ |
| D4 aggradation/degradation | a published mobile-bed benchmark, chosen at review (candidates: clear-water degradation below a dam; Spinewine and Zech 2007† dam break over a mobile bed), qualitative and order-of-magnitude |
| D5 bank and wall failure | per-cell wedge volume into the store; β_w trends as Part 3 §3.6; (5.17) reproduces the lumped wall check on identical states |
| D7 splitting error | a coupled erosion case (uniform reach eroding under constant inflow) at CFL, CFL/2, CFL/4: bed elevation, width and Q converge with observed order reported |
| D6 roof collapse in isolation | a fixed-flow conduit reaching the §5.5b margin: collapse at the margin crossing; debris surface (6.31); water kept; grid independence of the collapse time |

**Phase E — overtopping cases.** The lumped reference cases, both engines on identical case files,
side by side, with the reporting protocol of Appendix 6A (E). Then the case database. Differences are
reported and explained by the flow, never removed by adjustment. Sensitivity runs: a 2H:1V face case
with the hydrostatic error of §6.3.1 quantified (vertical against bed-normal pressure at the same
Q), and wall shear 0.7 × bed.

**Phase F — piping, P1.** Both engines, identical inputs, frozen soil parameters (k_d band, c_u, τ_c),
no tuning, with the reporting protocol of Appendix 6A (F). Compared with the lumped baseline and with
the photo evidence as ratios with the scale caveat (handoff §3–4). Reported whether or not P1 breaches.
Grid convergence of the collapse location and time (decision 6-14).

**Phase G.** Part 6 stops at phase F. From phase G the existing roadmap (`ROADMAP_LUMPED_1D_2026-11-20`)
takes over unchanged — pre-registered blind set, sensitivity, calibration of f_kd and f_t, validation —
with the distributed engine as the candidate and the lumped engine as the reference.

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
11. **Approach.** Notch-width stream tube over the submerged upstream face (partitioned from the reservoir, §6.6.1); no flow converging laterally into the notch.
12. **Abrupt contractions** lose a head of the sharp-edged order from the step-face balance (§6.5.3), which can differ from the rounded-entrance K_u of the lumped engine (decision 6-16).

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
- The 2-D cells k along the interface edge (widths Δy_k, depths h_k, normal velocities u_k, stages η_k,
  concentrations C_k) form the 2-D side of the 1-D interface s_c. Their width-integrated state is
  A = Σ h_k Δy_k, Q = Σ h_k u_k Δy_k, A C = Σ h_k C_k Δy_k, with the stage η defined by A_s(η) = A on the
  interface section (so that a level 2-D edge gives exactly its own stage).
- **One flux per interface, computed once**, by the same HLLC/hydrostatic-reconstruction rule (6.13)–
  (6.20). The 1-D cell receives it in full; the 2-D boundary edges receive it distributed over the edge
  in proportion to their share of the interface section's flow area (mass, normal momentum and
  sediment). The 1-D and 2-D budgets therefore see the same number, so water and solids are
  conserved across the interface exactly.
- The flux split must keep a 2-D lake at rest across the interface: the pressure part is given to each
  edge as its own hydrostatic pressure at the common stage, and the advective parts (mass, normal
  momentum, sediment) in proportion to the edge's share of the flow area. Transverse momentum on the
  2-D side is zero at entry (the 1-D side has none).
- This defines the exchange to the level needed to keep the architecture open. The full derivation and
  its tests (a level interface, a dam break across the interface, a steady flow entering the patch) are
  part of the patch's own development stage, when it is activated.

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

- Each interface is an object that carries its own section (built in v1 by the intersection rule
  (6.13)), so a 2-D edge can stand in for a 1-D neighbour.
- The downstream boundary is an interface object (flux in, state out), not hard-coded.
- Budgets are closed through interface fluxes, so a second domain adds terms, not exceptions.
- q_l in (6.4) is kept for lateral exchange.

---

## 6.13 Decisions

Draft 3.2 (user, 2026-11-26): 6-19, 6-20 and 6-21 accepted; 6-16 kept open; 6-18 not needed for the
B12b cases. Status at sign-off (user, 2026-11-26): 6-1, 6-3, 6-5, 6-6, 6-8, 6-9, 6-10, 6-11, 6-12, 6-13, 6-14,
6-16 (test first) and 6-17 accepted and frozen; 6-2, 6-4 + 6-15, 6-7 and 6-18 conditional on their phase B
and C tests.

| no. | question | proposal |
|---|---|---|
| 6-1 | approach over the submerged upstream face (overtopping) | stream tube of notch width from the upstream toe, with the space partitioned between cells and reservoir (6.23a) and a recorded transfer when the tube widens; crest-edge boundary as an option |
| 6-2 | slot celerity | fixed in phase C by the insensitivity criteria (6.10) and test C6 (a_s, 2a_s, 4a_s); 50 m/s is only the starting value |
| 6-3 | order of accuracy | first order is the v1 baseline; MUSCL + SSP-RK2 only if it passes the same gates |
| 6-4 + 6-15 | interface sections **and** step-face loading, approved together | the intersection rule (6.13) fixes what is open to flow, the loading closure (6.16b) the force on what is not; both v1 candidates, ours, conditional on B1, B12a–c and C2/C2b |
| 6-5 | lateral spreading on the face and above the ground | none (stream tube); stated limitation and the first 2-D activation candidate |
| 6-6 | Part 3 reach closures c_b (3.6) and Appendix 3A | not used; (3.6) kept as an option for comparison |
| 6-7 | headcut | Part 4 relations as a drop-interface closure (§6.8.4); SIMBA's erosion-resistant crest dropped |
| 6-8 | wall criteria | collapsed cells: the frozen wet undrained cut (5.17), retreat ½ H_w; open-breach cells: Part 3 (3.12)–(3.14) |
| 6-9 | intact-crest overflow | three disjoint paths: resolved notch (domain, erodes), remaining crest max(L_cr − B_top,cr, 0) by (1.8), spillway Q_sp; a piping run with z_s above the crest stops with an out-of-scope flag in v1 |
| 6-10 | residual-block sliding (4.10)–(4.11) | kept, on the block upstream of the most upstream brink |
| 6-11 | debris | **accepted for v1 (user, 2026-11-26)**: per-cell mobile store of solids, a level layer filling the section from the intact bed (6.31), with the five definitions of §6.7.4; `export` as a comparison mode only; not a model of 3-D deposits or debris flow |
| 6-12 | mixture effects | clear-water continuity in v1 |
| 6-13 | numbering | call this Part 6 of the distributed engine's own theory (`python/onedim/docs/theory/06_…`), and renumber the lumped plan's future parts (impulse waves, moraine) as 7 and 8 when they are written |
| 6-14 | minimum collapse length | none in advance; introduced only if the grid study shows non-convergence, and then with a source |
| 6-16 | contraction loss where an open cell drains into a conduit | the step-face result as it comes; measured in C2b against K_u = 0.05; no closure added before that evidence. **Kept open (user, 2026-11-26)**: Borda–Carnot is not a contraction benchmark; compare with a geometry- and regime-matched open-channel relation or data set (candidates named by the user, unchecked: HEC-RAS Hydraulic Reference Manual contraction coefficients; Chaudhry, *Open-Channel Flow*, experimental contraction coefficients; Wu and Molinas, short lateral contractions) |
| 6-17 | conservation gates | cumulative relative error < 10⁻¹⁰ (water and solids) every run; per-step diagnostic δ^n < 10⁻¹² in phase B, as defined in §6.9.1 |
| 6-18 | brink flux if B12b fails | exact sonic flux of §6.8.4(a) at drop interfaces only; HLL elsewhere; used only if B12b fails. **Phase B: B12b passed (rectangle and trapezoid, N to 8N); not needed for the tested cases** |
| 6-19 | reconstruction at a width change | **accepted (user, 2026-11-26)**: (6.14a), discharge carried through a width change, velocity through a bed step; a reconstruction rule only, no loss coefficient; verified further in B12a–d |
| 6-20 | B2 dry front | **accepted (user, 2026-11-26)**: the exact-front 1 % target stays and its failure is reported as a known first-order limitation; same-threshold front diagnostic added; B2 does not block the phase B baseline |
| 6-21 | B12c energy criterion | **accepted (user, 2026-11-26)**: refinement-based gate (§6.10); the strict per-cell test kept as a diagnostic |

---

## Appendix 6A — Benchmark specifications (phases B–F)

Common rules. g = 9.81 m/s². Error norms are relative L1 over wet cells,
e(φ) = Σ|φ − φ_ref| Δs / Σ|φ_ref| Δs; observed order p = log₂(e_N / e_2N); GCI after Celik et al.
(2008)†. Unless stated, grids N, 2N, 4N, CFL 0.9 and 0.45, h_dry = 10⁻⁶ m. Where a setup is taken from
the SWASHES collection (Delestre et al. 2013†), its parameters are used exactly as published there and
cited by case name, so the reference solution is independent of this project.

**Phase B**

| test | setup | reference |
|---|---|---|
| B1 | L = 10 m, N = 50; piecewise-constant bed z ∈ [0, 0.4] m and sections drawn with a fixed seed (rectangles 0.5–3 m wide, trapezoids cot β_w 0–2, one 5-cell conduit 0.2 × 0.2 m); η = 0.5 m, Q = 0; closed ends; 10⁵ steps | η = 0.5, U = 0 |
| B2 | rectangle b = 1 m, flat, frictionless, s ∈ [−1000, 1000] m, h = 1 m for s < 0, dry for s > 0, t = 50 s; N = 400, 800, 1600, 3200 | Ritter (1892); front at 2√(g h₀) t |
| B3 | as B2 with h_R = 0.1 m | Stoker (1957); shock speed from the jump conditions |
| B4 | trapezoid with σ(s, y) = b(s) + 2y cot β(s), b(s) = 1 + 0.5 sin(2πs/L), cot β(s) = 1 + 0.5 cos(2πs/L), z(s) = 0.1 sin(2πs/L), L = 10 m, periodic; manufactured smooth A(s, t), Q(s, t) with the source terms derived analytically from (6.4)–(6.5) | the manufactured solution; p ≥ 0.9 required |
| B5 | Goutal and Maurel (1997)† bump, L = 25 m, z = 0.2 − 0.05(s − 10)² on 8 < s < 12, unit width, frictionless; subcritical (q = 4.42 m²/s, h_out = 2 m), transcritical without shock (q = 1.53 m²/s, h_out = 0.66 m), with shock (q = 0.18 m²/s, h_out = 0.33 m), as in SWASHES | Bernoulli and the jump conditions (analytic) |
| B6 | rectangle b = 1 m, flat, frictionless, L = 50 m; inflow h₁ = 0.1 m, U₁ = 3.0 m/s (Fr₁ = 3.03); outlet stage at the conjugate depth h₂ = (h₁/2)(√(1 + 8Fr₁²) − 1) | Bélanger; jump location steady to one cell |
| B7 | rectangle b = 5 m, n = 0.02, Q = 10 m³/s, L = 1000 m: M1 (S₀ = 0.001, h_out = 3 m), M2 (free overfall at the end), S2 (S₀ = 0.02 from a critical break); repeated with b varying linearly 5 → 3 m | direct-step integration of the steady GVF equation with 10⁴ sub-steps |
| B8 | SWASHES §4.2.1 "planar surface in a parabola without friction", the 1-D reduction of Thacker's (1981)† parabolic-channel solution: z(x) = h₀((x − L/2)²/a² − 1), a = 1 m, h₀ = 0.5 m, L = 4 m, B = √(2gh₀)/(2a), u(0) = 0, five periods (T = 10.0303 s) | h(t, x) = −h₀[((x − L/2)/a + (B/√(2gh₀)) cos ωt)² − 1] on the wet interval, u = B sin ωt, ω = √(2gh₀)/a; shoreline position and h |
| B9 | rectangle, flat, frictionless; h = 1 m, U = −5 m/s for s < 0 and +5 m/s for s > 0 (two rarefactions, near-dry centre) | Toro (2001) exact Riemann solver |
| B10 | rectangle b = 1 m, n = 0.016, Q = 0.5 m³/s: 2 m flat crest at z = 2 m, 1:2 face to z = 0, 10 m apron; tailwater rating at the end | critical at the crest edge; S2 profile on the face by direct step on the same hydrostatic equations; jump on the apron at the Bélanger location (profile within 2 %, jump within 2 cells at 4N) |
| B11 | B2, B6, B7 at N, 2N, 4N and both CFL values | observed order and GCI reported |
| B12a | rectangles 2 → 4, 2 → 10, 4 → 2, 10 → 2 m and trapezoid equivalents, same bed, Q = 2 m³/s, h₁ = 1 m; conduit 0.2 × 0.2 m → open 1 m | the steady junction relation of §6.5.3, solved independently; Borda for expansions |
| B12b | flat crest z = 1 m, b = 1 m, then a 1 m drop onto a dry apron; upstream energy E = 0.5 m above the crest; repeated with a trapezoid (cot β_w = 1); N, 2N, 4N, 8N | Q = √g (2E/3)^{3/2} b (rectangle) or the general critical solution (1.4)–(1.5); interface flux compared directly; brink-cell Fr |
| B12c | as B12a, with the width change spread linearly over 5, 10, 20 and 50 cells; refinement series: 2 → 4 and 2 → 10 m expansions and their reverse spread over a fixed length of 2.5 m at Δs = 0.25, 0.125, 0.0625 m | energy per cell; total loss against the abrupt case; for the series, the four gate items of §6.10 |
| B12d | conduit 0.2 × 0.2 m (a_s = 50 m/s) → rectangle 1 m, Q = 0.05 m³/s; submerged (h = 0.6 m) and free (dry apron) outlet; both directions; run until steady or 10⁴ s, with the history of the outlet flux | steady state; junction relation and Borda |
| B13 | rectangle, U = 1 m/s uniform; C = 1 on 4 ≤ s ≤ 6 m, 0 elsewhere; then the same (a) through B4's sections, (b) across a wetting front, (c) with the flow reversed mid-run, (d) with a wet cell draining into a dry one, (e) with a large solids source in a cell of small water volume | 0 ≤ C ≤ max C(0); positivity of A C; sediment moves with the flow direction; no solids created on drying (they go to the store); exact solids total in every sub-case |

**Phase C**

| test | setup | reference |
|---|---|---|
| C1 | square conduit 0.04 m, L = 8.31 m, n_p = 0.016, invert 0.20 m; upstream reservoir 1.10 m, downstream reservoir 0.30 m (outlet submerged above the crown); K_u = 0.05 | Q = A √(2gΔH/(K_u + 1 + fL/4R)), f = 8gn_p²/R^{1/3}; linear crown-pressure profile |
| C2 | the same conduit discharging freely onto a 3H:1V face, TW = 0 | lumped (5.3) with K_d = 1, reported (O-1) |
| C2b | a 0.5 m wide open cell draining into the 0.04 m conduit | K_u = 0.05 and the sharp-edged value, reported |
| C3 | full conduit at rest; inlet stage raised by 0.1 m at t = 0 | front speed a_s |
| C4a | pipe-filling Riemann problem: part-full conduit (h = 0.5 a_p, U = 0) meeting a pressurised state (piezometric head 0.5 m above the crown) | exact Riemann solution of the slot system (Kerger et al. 2011†): front speed and states within 1 % |
| C4b | Trajkovic et al. (1999)† experiment reproduced in its own configuration (circular pipe, gates, hydraulic jump), not as a generic filling bore; circular section supported for this test | measured front speed and pressures; reported; data to obtain |
| C5 | C1 conduit; upstream level lowered below the crown and raised again over 60 s | mass to the gate; no spurious pressurisation |
| C6 | C1–C5 at a_s, 2a_s and 4a_s | < 1 % in Q, the pressure distribution, the pressurisation time and the front position; both (6.10) conditions logged |
| C7, C8 | as in §6.10 | as in §6.10 |

**Phase D.** D4 is fixed as (a) a manufactured coupled flow–Exner solution on B4's channel with a
smooth erodible bed and an analytic capacity law (quantitative: p ≥ 0.9, error at 4N below 1 %), and
(b) one laboratory mobile-bed case, qualitative and order of magnitude only, chosen at review from
data on file (candidates: Spinewine and Zech 2007†; a non-cohesive Walsh flume run). D1–D3 and D5–D7
as in §6.10.

**Phase E protocol (overtopping).** For each case and both engines: Q_p; T_p measured from the same
reference event as the lumped records; the final average width B̄ (1.1) at the control cell and its
maximum over the dam; the final control-bed elevation; the outflow volume at 25, 50, 75 and 100 % of the
event; the hydrograph. Report new, reference and observation, (new − ref)/ref and (new − obs)/obs. A
distributed result is reported as converged only if the GCI of Q_p, T_p and B̄ is below 5 %; otherwise
it is reported as not converged, with the GCI.

**Phase F protocol (P1).** Report: time and position of the first collapse; the sequence of collapsed
cells in time; b_p and a_p of the outlet cell in time, and their ratios at the photo times (5, 8 and
13 min after the same reference event as R-2 §9); the outcome class (open breach, sealed, or water
above the dam surface flagged); Q(t), and Q_p and T_p if it breaches. Runs: k_d = 0.88, 3.16 and
16.5 (the frozen §5.4a band) × c_u0 4–7 kPa as in the lumped records; Δs and Δs/2; CFL 0.9 and 0.45.
No parameter outside these is changed.

---

## Appendix 6B — Source-to-claim status of the † references

"Bibliographic" means the reference exists and is relevant; "claim" means the specific statement in
Part 6 has been checked against the paper. No reference is marked fully verified until its claim is
checked. Priority for the claim check: Batten, Einfeldt et al., SWASHES, Goutal and Maurel, Kerger.

| reference | claim in Part 6 | status |
|---|---|---|
| Batten et al. (1997) | none in the scheme since draft 3.1 (the pressure-form S* is replaced by (6.19)) | abstract and the commonly cited S* form checked; retained only as background for HLLC wave speeds |
| Bladé et al. (2012) | conservative 1-D/2-D frontal coupling | bibliographic; the area-weighted split of §6.12.2 is ours |
| Cao et al. (2004) | coupled mixture formulation exists (later option) | bibliographic |
| Celik et al. (2008) | GCI procedure | bibliographic; article-number formatting to confirm |
| Chaudhry (2008) | slot equations | bibliographic; chapter to be cited |
| Delestre et al. (2013), SWASHES | B5, B8 setups and solutions | **B5 and B8 parameters and the B8 solution checked against the arXiv version** (1110.0288); B2, B3, B7 to check |
| Einfeldt (1988) | wave-speed estimates | bibliographic; adaptation to sections ours |
| Einfeldt et al. (1991) | HLLE positively conservative under wave-speed conditions | abstract checked: Godunov is positively conservative, HLLE is so under conditions on the wave speeds; the paper is for the Euler equations, the SWE use is the analogue (corrected in §6.5.4); full text pending |
| Goutal and Maurel (1997) | bump benchmarks | case values confirmed through SWASHES, which cites the EDF report HE-43/97/016/B with Goutal and Maurel as authors; the report itself is not online; role (authors or editors) unconfirmed. B5 rests on the analytic solution, so its pass criterion does not depend on the report |
| Hernández-Dueñas and Karni (2011) | balance laws for arbitrary sections | bibliographic; does not prove (6.13)/(6.16b) |
| Kerger et al. (2011) | slot with Godunov scheme; exact Riemann solution for C4a; negative slot not used | abstract checked: unified Preissmann-slot model, first-order explicit Godunov finite volumes, a negative slot for sub-atmospheric flow, an exact Riemann solver; oscillations after the transition remain at large celerities. Supports §6.4.1, §6.4.4 and C4a; full text pending |
| Liang and Marche (2009) | implicit friction (6.22) | bibliographic; (6.22) to be checked under our section and friction definitions |
| Morales-Hernández et al. (2013) | conservative 1-D/2-D coupling | bibliographic; sediment and moving-interface parts ours |
| Spinewine and Zech (2007) | D4(b) candidate | bibliographic; experiment and measurements to select |
| Thacker (1981) | origin of B8 | B8 now uses the SWASHES 1-D reduction (checked) |
| Trajkovic et al. (1999) | C4b experiment | bibliographic; configuration to reproduce, data to obtain |
| Vasconcelos et al. (2009) | slot oscillations at filling bores | bibliographic; central to C4, C6 |
| Vázquez-Cendón (1999) | source terms, locally rectangular channels | bibliographic; applicability scoped in §6.5.3 |

---

## References

New in this part (†: to be checked against the paper before sign-off):

- Audusse, E., Bouchut, F., Bristeau, M.-O., Klein, R., and Perthame, B. (2004). A fast and stable
  well-balanced scheme with hydrostatic reconstruction for shallow water flows. *SIAM J. Sci. Comput.*,
  25(6), 2050–2065.
- † Batten, P., Clarke, N., Lambert, C., and Causon, D. M. (1997). (Background only since draft 3.1.) On the choice of wavespeeds for the
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
- † Delestre, O., Lucas, C., Ksinant, P.-A., Darboux, F., Laguerre, C., Vo, T. N. T., James, F., and
  Cordier, S. (2013). SWASHES: a compilation of shallow water analytic solutions for hydraulic and
  environmental studies. *Int. J. Numer. Methods Fluids*, 72(3), 269–300.
- † Einfeldt, B. (1988). On Godunov-type methods for gas dynamics. *SIAM J. Numer. Anal.*, 25(2),
  294–318.
- † Einfeldt, B., Munz, C.-D., Roe, P. L., and Sjögreen, B. (1991). On Godunov-type methods near low
  densities. *J. Comput. Phys.*, 92(2), 273–295.
- † Goutal, N., and Maurel, F. (eds.) (1997). *Proceedings of the 2nd Workshop on Dam-Break Wave
  Simulation*. Technical Report HE-43/97/016/B, Électricité de France, Direction des Études et
  Recherches. (Cited this way in SWASHES; one catalogue lists N. Goutal as editor. Author and editor
  roles to be confirmed against the report.)
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
