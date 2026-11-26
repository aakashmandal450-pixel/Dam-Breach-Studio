# Plan: a true, spatially resolved 1-D breach engine

*2026-11-26 · status: **decisions made (§6), phase A started.** No code. Decided by the user
(2026-11-26): build a genuinely 1-D (distributed) model, not a rename. Review of 2026-11-26 adopted:
all seven decisions approved with qualifications (§6), and a gated 2-D extension added (§7).*

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

## 2. Governing equations (written in full as Part 6 before any code)

**1. Flow.** The 1-D shallow-water (Saint-Venant) equations in conservative form, for the wetted area
A(s, t) and discharge Q(s, t). Source terms: bed slope, friction (Manning), and lateral inflow or
outflow where needed.
- **Pressurised conduit flow** uses the **Preissmann slot** (Cunge and Wegner 1964). The slot is a
  conduit-geometry device. It is unrelated to the implicit Preissmann four-point *numerical scheme*,
  which is not used (decision 3).
- **Alternative, held in reserve:** the two-component pressure approach of Vasconcelos et al. (2006),
  investigated only if the phase C slot tests fail (decision 2).

**2. Reservoir.** The level-pool storage of Part 1, kept as the upstream boundary.

**3. Morphology.** Per cell, the Part 2 laws unchanged, plus an Exner-type sediment balance per cell,
with transport between cells (eroded and fallen soil is routed downstream, not exported by rule).

**4. Cross-section geometry per cell.** A conduit section (b, D, z_inv), or an open trapezoid
(B, z_b, β). Widening by the Part 3 convention; side slope from Part 3 bank stability, per cell.

**5. Geotechnical events per cell.** Roof collapse from the existing FELA stability table; wall
stability per cell; fallen soil enters the cell's sediment store and is transported. This **replaces**
the level crater box, the plugs (D1-a/D5) and the H1 rules with transport physics. They stay
reference-only.

**6. Downstream boundary.** A free outfall at the toe, or a tailwater rating. The tailwater question
(O-1 §5) becomes an explicit input with a stated status.

## 3. Numerics

- **Finite volume,** HLLC flux (Toro 2001) with hydrostatic reconstruction (Audusse et al. 2004).
- **Explicit time stepping** under a CFL limit.
- **Flow and morphology** by operator splitting. No morphological acceleration in the first version.
- **Convergence:** grid (Δs, Δs/2, Δs/4) and time step; observed order and GCI for the peak discharge,
  its time and the final width.

## 4. Phases and gates (no breach physics before the solver gates pass)

| phase | content | gate |
|---|---|---|
| **A. Part 6 theory** | equations, boundary conditions, slot, numerics, every coefficient with its source, the future 2-D interface | sign-off, as for Parts 1–5 |
| **B. Open-channel solver** | SWE with fixed geometry | lake at rest over irregular bed *and* width; Ritter / Stoker dam break; steady GVF profiles; hydraulic jump (conjugate depths, conservation across the jump); positivity of A; wetting and drying; stability near steep bed changes and near-dry cells; grid and dt convergence |
| **C. Conduit (slot)** | pressurised and mixed flow | full-pipe steady flow; surge celerity against the slot design value; pipe filling; pressurised ↔ free-surface transition; slot-induced oscillations; sensitivity to slot width; **HLLC stability with the slot established here — passing phase B alone is insufficient** |
| **D. Morphology** | Part 2 laws per cell, Exner transport, Part 3 widening | exact solids budget; non-equilibrium relaxation against the analytic solution; uniform-flow limit reproducing the lumped erosion rate |
| **E. Overtopping cases** | full breach, no piping | the lumped reference cases, new against reference side by side, then the case database |
| **F. Piping** | conduit cells, per-cell roof collapse, conduit → channel conversion | P1 against the lumped baseline and the photo evidence (ratios, scale caveat), with no tuning |
| **G.** | resume the main roadmap (blind set, sensitivity, calibration, validation) with the 1-D engine as the candidate | as in the roadmap |

## 5. Risks, stated now

1. **Mixed-flow numerics.** Slot-induced oscillations at the pressurisation front are well known.
   They are tested in phase C before any piping run.
2. **Rule proliferation per cell.** Keep only rules that physics requires; transport replaces most of
   the crater and debris rules.
3. **Run time.** CFL-limited steps on fine grids. Budget it, and keep the lumped engine for screening
   and ensembles.
4. **Scope creep.** The same failure mode as V3.4. The gates are hard, and nothing from phase F is
   attempted before phases B–D pass. The 2-D patch (§7) is outside phases B–F.
5. **P1 may stay unresolved,** for the 2-D and 3-D reasons in §1. That is an acceptable outcome, to be
   reported as such.

## 6. Decisions (user, 2026-11-26, after review)

| no. | decision | outcome |
|---|---|---|
| 1 | two independent tracks: lumped frozen as reference, 1-D as a new package and baseline | **approved** |
| 2 | conduit formulation | **Preissmann slot** |
| 3 | numerical scheme | **explicit finite volume, HLLC with hydrostatic reconstruction** |
| 4 | debris | **per-cell sediment transport** |
| 5 | package and branch | **`python/onedim/`, branch `onedim`** |
| 6 | start phase A | **approved** |
| 7 | 2-D extension | **gated exit/face patch (§7)** |

**Qualifications attached to the decisions (to be carried into Part 6):**

1. **Slot.** The initial pressurised-flow representation. Phase C tests pressure-wave speed,
   slot-induced oscillations, pipe filling, the pressurised ↔ free-surface transition and the
   sensitivity to slot width. If these tests fail, the two-component pressure approach is
   investigated. The method is not switched because one produces a more favourable breach result.
2. **HLLC with hydrostatic reconstruction.** Phase B tests positivity of depth and flow area, wetting
   and drying, conservation across hydraulic jumps, still water over irregular beds, and stability
   near steep bed changes and near-dry cells. Phase C must separately establish that HLLC remains
   stable with the slot. The Preissmann *slot* and the implicit Preissmann four-point *scheme* are
   different concepts.
3. **Per-cell sediment transport.** Each cell tracks erosion, deposition, sediment storage and exported
   solids, and the solids budget is conserved. The crater, plug and exit-widening rules remain
   reference mechanisms and comparison cases, not active mechanisms in the new solver by default. The
   model does not claim that 1-D sediment transport reproduces debris plugs or lateral collapse.

## 7. Future 2-D extension: gated hybrid 1-D/2-D model

The initial development focuses entirely on a distributed 1-D model. A limited 2-D extension may be
considered later, restricted to the downstream pipe exit and dam face.

The 2-D extension is not included in the initial solver or in phase B. Part 6 defines the intended
coupling interface between the 1-D and 2-D domains — where the domains meet, the exchange of water,
momentum and sediment fluxes, the consistency of the water and solids budgets, how boundary
information passes between them and how changing geometry is handled — so that the architecture
remains open to it.

The 2-D patch is activated only after phase E, and only after the 1-D results show that an important
modelling error is concentrated in the downstream exit or face region. The need for it must be
supported by comparison with experimental or historical evidence. If the discrepancy is specifically
associated with the P1 exit, the phase F results can help establish that case.

The purpose of the patch would be to represent local lateral flow, exit expansion, scour and sediment
movement that a 1-D model cannot resolve adequately. The reservoir, the conduit and the downstream
channel remain in the 1-D domain. A depth-averaged patch cannot represent pressurised flow, the
arched roof or debris shaped across the conduit section; those stay 1-D limitations.

The extension is a separate development stage with its own verification and conservation
requirements. It does not delay or alter the initial 1-D solver development. P1 may remain unresolved
even after this extension; a 2-D model will not be developed simply to force agreement with one
experiment.

## Sources

- Audusse, E., Bouchut, F., Bristeau, M.-O., Klein, R., Perthame, B. (2004). A fast and stable
  well-balanced scheme with hydrostatic reconstruction for shallow water flows. *SIAM J. Sci. Comput.*
  25(6).
- Cunge, J. A., Wegner, M. (1964). Intégration numérique des équations d'écoulement de Barré de
  Saint-Venant par un schéma implicite de différences finies. *La Houille Blanche* (Preissmann slot).
- Harten, A., Lax, P. D., van Leer, B. (1983). On upstream differencing and Godunov-type schemes for
  hyperbolic conservation laws. *SIAM Review* 25(1).
- Toro, E. F. (2001). *Shock-Capturing Methods for Free-Surface Shallow Flows*. Wiley.
- Vasconcelos, J. G., Wright, S. J., Roe, P. L. (2006). Improved simulation of flow regime transition
  in sewers: two-component pressure approach. *J. Hydraul. Eng.* 132(6).
- Parts 1–5 of this theory (closures carried over unchanged); Part 6 for the full source list.
