# Plan (draft for review): a true, spatially resolved 1-D breach engine

*2026-11-26 · status: plan for review. No code. Decided by the user (2026-11-26): build a genuinely
1-D (distributed) model, not a rename.*

## 0. Relationship to the lumped engine

- **The lumped engine (`python/lumped`, branch `lumped-1d`) is frozen as the reference baseline.**
  Its theory (Parts 1–5), tests and validation records (P1 band, c_u0 check, H1-a) stay reproducible
  and are never edited to suit the new engine. From here on it is named the **lumped 1-D (reference)**
  model, because it resolves only the longitudinal section.
- **The new engine is a separate package and a separate baseline.** Every comparison is new-versus-
  reference on identical inputs, reported side by side and never mixed.
- **Lesson from the 2-D V3.4 work, which was stopped 2026-11-20 after long iteration:** the scope is
  phased with hard gates. Each solver component passes analytic benchmarks before any breach physics
  is added on top.

## 1. What changes, and what it should buy

| | lumped (reference) | distributed 1-D (new) |
|---|---|---|
| flow | closed-form relations (weir, pipe inlet/outlet control, Manning normal depth), quasi-steady | 1-D shallow-water equations along the flow path; unsteady; the profile is computed, not assumed |
| pipe | one rectangle b × D | per cell b(s), D(s), z_inv(s); pressurised and free-surface flow in the same conduit |
| breach channel | a few numbers (width, bed, side slope, reach lengths) | per cell: bottom width B(s), bed z(s), side slope |
| erosion | uniform over each reach | local, from each cell's own shear |
| outlet / exit | a convention (5.3) with notch rules (H-1) | the exit is solved: free outfall, expansion and the face channel are cells |
| piping → open breach | a hand-over between stages | cells change from conduit to open channel as the roof fails; **one solver throughout** |
| event rules | per reach (crater box, end retreat) | per cell (roof collapse, wall failure, debris) |

**What it should buy, and what it will not:**
- Exit-concentrated, non-uniform enlargement can **emerge** where the local shear differs.
- The outlet-convention question (O-1) is answered by computing the exit rather than choosing a
  reference.
- The piping-to-overtopping transition is continuous.
- It **will not** resolve 2-D and 3-D features by itself: the expansion eddies (H1-d), the arched roof
  over a wide opening, and debris plugs shaped across the section. Cross-section averaging removes
  them. These stay stated limitations or closure terms. The plan does **not** assume that 1-D will
  resolve P1.

## 2. Governing equations (to be written in full as Part 6 before any code)

**1. Flow.** The 1-D shallow-water (Saint-Venant) equations in conservative form, for the wetted area
A(s, t) and discharge Q(s, t). Source terms: bed slope, friction (Manning), and lateral inflow or
outflow where needed.
- **Pressurised conduit flow** uses the **Preissmann slot** (Cunge and Wegner 1964). It is the standard
  way to carry pressurised and free-surface flow in one set of open-channel equations, and its slot
  width sets the pressure-wave speed.
- **Alternative, to compare before choosing:** the two-component pressure approach of Vasconcelos et
  al. (2006).
- **Decision needed:** the slot width, or the target wave speed.

**2. Reservoir.** The level-pool storage of Part 1, kept as the upstream boundary. The reservoir is
genuinely well mixed at these scales. Then the inflow and weir boundaries.

**3. Morphology.** Per cell, the Part 2 laws unchanged:
- cohesive excess-shear detachment, E = k_d max(τ − τ_c, 0);
- non-cohesive capacity and non-equilibrium adaptation (the DL Breach combination, as already adopted).

Plus an Exner-type sediment balance per cell, with transport between cells (eroded and fallen soil
is routed downstream, not exported by rule).

**4. Cross-section geometry per cell.**
- A conduit section (b, D, z_inv), or an open trapezoid (B, z_b, β).
- Widening by the Part 3 convention (walls retreat at the bed-erosion rate).
- Side slope from Part 3 bank stability, per cell.

**5. Geotechnical events per cell.**
- Roof collapse: the existing FELA stability table, already section-based.
- Crater and breach walls: (5.17) and Culmann, per cell.
- Fallen soil enters the cell's sediment store and is transported. This **replaces** the level crater
  box, the plugs (D1-a/D5) and the H1 rules with transport physics. They stay reference-only.

**6. Downstream boundary.** A free outfall at the toe, or a tailwater rating. The tailwater question
(O-1 §5) becomes an explicit input with a stated status.

## 3. Numerics (proposal)

- **Finite volume,** with a Godunov-type flux (HLL, Harten, Lax and van Leer 1983, or HLLC) and
  hydrostatic reconstruction (Audusse et al. 2004). This gives a well-balanced still water and robust
  wetting and drying.
- **Explicit time stepping** under a CFL limit.
- **Alternative:** the implicit Preissmann four-point scheme (as in HEC-RAS). It allows larger steps
  but is weak for the transcritical and mixed flows that piping produces. The proposal is the explicit
  finite-volume scheme first.
- **Flow and morphology** by operator splitting: a flow step, then a bed and geometry step. No
  morphological acceleration in the first version.
- **Convergence:** grid convergence (Δs, Δs/2, Δs/4) on top of time-step convergence. The observed
  order is reported, with the GCI for the peak discharge, its time and the final width.

## 4. Phases and gates (no breach physics before the solver gates pass)

| phase | content | gate |
|---|---|---|
| **A. Part 6 theory** | equations, boundary conditions, slot, numerics, every coefficient with its source | sign-off, as for Parts 1–5 |
| **B. Open-channel solver** | SWE with fixed geometry | analytic benchmarks: lake at rest (well-balanced), Ritter / Stoker dam break, steady gradually varied flow profiles against direct-step solutions, a hydraulic jump against the conjugate depths; grid and dt convergence |
| **C. Conduit (slot)** | pressurised and mixed flow | a full-pipe steady flow against the Darcy-Weisbach / outlet-control solution, a pressure-surge celerity against the slot design value, a filling-pipe transition benchmark |
| **D. Morphology** | Part 2 laws per cell, Exner transport, Part 3 widening | aggradation/degradation against analytic or published solutions; exact solids budget; a uniform-flow limit reproducing the lumped erosion rate |
| **E. Overtopping cases** | full breach, no piping | the lumped reference cases, new against reference side by side, then the case database |
| **F. Piping** | conduit cells, per-cell roof collapse, conduit → channel conversion | P1 against the lumped baseline and the photo evidence (ratios, scale caveat), with no tuning |
| **G.** | resume the main roadmap (blind set, sensitivity, calibration, validation) with the 1-D engine as the candidate | as in the roadmap |

## 5. Risks, stated now

1. **Mixed-flow numerics.** Slot-induced oscillations at the pressurisation front are well known.
   They are tested in phase C before any piping run.
2. **Rule proliferation per cell.** Every event rule needs neighbour handling. Keep only rules that
   physics requires; transport replaces most of the crater and debris rules.
3. **Run time.** CFL-limited steps on fine grids. Budget it, and keep the lumped engine for screening
   and ensembles.
4. **Scope creep.** The same failure mode as V3.4. The gates are hard, and nothing from phase F is
   attempted before phases B–D pass.
5. **P1 may stay unresolved,** for the 2-D and 3-D reasons in §1. That is an acceptable outcome, to be
   reported as such.

## 6. Decisions requested

1. Approve the two-track arrangement: the lumped engine frozen as the reference, the 1-D engine as a
   new package and baseline.
2. Preissmann slot (proposal) or the two-component pressure approach for the conduit.
3. Explicit finite volume with HLL/HLLC (proposal) or implicit Preissmann.
4. Debris by per-cell sediment transport, replacing the crater box, plugs and H1 rules (proposal), or
   keep rule-based debris in the first version.
5. Package name and location (proposal: `python/onedim/`, branch `onedim`).
6. Start with phase A (the Part 6 theory) now.

## Sources (to be completed in Part 6)

- Cunge, J. A., Wegner, M. (1964). Intégration numérique des équations d'écoulement de Barré de
  Saint-Venant par un schéma implicite de différences finies. *La Houille Blanche* (Preissmann slot).
- Vasconcelos, J. G., Wright, S. J., Roe, P. L. (2006). Improved simulation of flow regime transition
  in sewers: two-component pressure approach. *J. Hydraul. Eng.* 132(6).
- Harten, A., Lax, P. D., van Leer, B. (1983). On upstream differencing and Godunov-type schemes for
  hyperbolic conservation laws. *SIAM Review* 25(1).
- Audusse, E., Bouchut, F., Bristeau, M.-O., Klein, R., Perthame, B. (2004). A fast and stable
  well-balanced scheme with hydrostatic reconstruction for shallow water flows. *SIAM J. Sci. Comput.*
  25(6).
- Parts 1–5 of this theory (closures carried over unchanged).
