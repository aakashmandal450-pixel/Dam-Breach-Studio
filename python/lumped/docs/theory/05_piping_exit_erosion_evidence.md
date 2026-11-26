# Part 5, investigation note R-2: erosion at the pipe exit, evidence and outlet flow conditions

*2026-11-26 · status: evidence only. **No erosion equation is adopted, no coefficient is chosen.**
Follows the review of draft F-1. G1/G2 slope instability does not explain P1 under the current
strength estimates, so priority 1 is exit-concentrated erosion, with non-uniform enlargement alongside.
The hypothesis is that downstream flow progressively erodes and enlarges the pipe exit. It is not
established.*

## 1. P1 soil properties relevant to erosion (data sheet status)

| property | value | status |
|---|---|---|
| field JET k_d / τ_c | 150 cm³/(N·s) / 0 Pa | M (PAP-1017 Table 6), on the embankment |
| lab JET k_d | 274–309 | M |
| lab HET | not testable: specimens collapsed when wetted | M (PAP-1017) |
| HET-equivalent k_d (§5.4a band) | 0.88–16.5, central 3.16 | E (frozen transfer, not a fit) |
| gradation, plasticity | SM, 76 / 19 / 5, non-plastic | M |
| foundation erodibility (sets the lowest bed level) | **unknown**; the model treats the base z = 0 as non-erodible | — |
| pipe elevation | 0.20 m above the base | **E** (Chen et al. 2019; "lowest marker row") |

## 2. Outlet flow conditions (model, P1, k_d = 3.16, dt = 2 s, start to roof collapse at 1520 s)

| t (s) | b (m) | Q (L/s) | U pipe (m/s) | τ pipe (Pa) | y_c (m) | face-channel τ (Pa) | τ face / τ pipe |
|---|---|---|---|---|---|---|---|
| 0 | 0.040 | 1.5 | 0.92 | 9.9 | 0.052 | 34 | 3.4 |
| 500 | 0.085 | 10.4 | 1.45 | 19.2 | 0.115 | 71 | 3.7 |
| 1000 | 0.164 | 55.9 | 2.08 | 31.4 | 0.228 | 133 | 4.2 |
| 1501 | 0.288 | 227.6 | 2.75 | 45.5 | 0.400 | 224 | 4.9 |

Notes on the table:
- The face channel is Manning normal flow in width b on the 3H:1V face, n = 0.016, as in §5.6.
- Erosion rates (k_d τ) at k_d = 3.16: pipe walls 1.9 → 8.6 mm/min; the face channel below the
  outlet 6.4 → 42 mm/min.

What the numbers say:
1. **The outlet runs full throughout.** The critical depth y_c exceeds the pipe height at every stage.
   There is no free-surface drop at the outlet and no supercritical acceleration inside the pipe near
   the exit. The in-pipe shear is uniform along the reach, so **non-uniform enlargement does not come
   from the pipe hydraulics** in this model.
2. **Wherever the exit flow runs on the face, it erodes 3.4–4.9 times faster than the pipe walls,**
   provided it stays confined to about the pipe width. That covers:
   - the face channel below the outlet;
   - the open notch between the crown daylight and the invert daylight (§F-1 §1: x 8.52–9.41 m at
     collapse).

## 3. Why the existing exit headcut (§5.6) never moves the outlet

§5.6 already lowers the face channel below the outlet at the face-flow rate (stage 1). It switches to
plunging and upstream migration (stage 2) when the drop H_h = z_inv − z_h exceeds d_c. Its channel
bed z_h stops at the dam base (z ≥ 0), so

    H_h ≤ z_inv(t) ≤ 0.20 m (start), 0.07 m at collapse (the pipe floor erodes too)

while d_c grows from 0.05 to 0.40 m. **For P1 the plunge condition is geometrically unreachable after
the first minutes**, whatever the erodibility. The outcome rests on two inputs that are not measured:
- the pipe elevation (estimated);
- the assumption of a non-erodible base. Wu (2016, Fig. 2.15) sketches a scour hole at the toe,
  below the ground.

## 4. What the present model does not represent at the exit (stated, not adopted)

- **E1. Widening of the open notch.** The section between the crown and invert daylight points
  carries face-channel shear (point 2) but keeps the pipe width b. Lateral erosion there at face-flow
  rates would make the exit wider than the pipe, which is a **local, exit-concentrated enlargement**.
  This is where A (exit erosion) and B (non-uniform pipe) meet.
- **E2. Erosion of the roof lip by the exiting flow** (the last 0.2 m of cover, below the end-lip
  limit), and expansion and impingement of the full-pipe jet at the exit.
- **E3. Headcut cut into the foundation, or a base scour hole**, if the base is erodible.
- **E4. Seepage particle mobilization at the face** (F-1 §6). Deferred: it needs a seepage face.

Any of these, once it removes support, can be followed by local collapse. The G1/G2 module stays
available for that check.

## 5. Experimental evidence to compare against

- **Wu (2016), Fig. 2.14** (P1 very likely, to confirm): an opening at the downstream face clearly
  larger than the 40 mm pipe at 5 min; an arched cavern, wider than high, growing at 8 and 13 min.
  These are qualitative until the survey-marker spacing is known.
- **Wu (2016), Fig. 2.15:** a scour hole at the toe and face slumping above the exit.
- **PAP-1017:** the downstream headcutting reached the base before the bridge collapsed.

Model comparison at P1 time scales: at k_d = 3.16 the pipe is 0.063 m wide at 300 s (the photo's
5 min). Even E1 at about 3.6 times the wall rate would add only a few centimetres per side by then.
Whether that matches the photographed opening cannot be judged without the marker spacing. The time
origin (§5.4a) adds a further caveat.

## 6. Data needed before any equation (in order of value)

1. The pipe elevation and outlet position (Hanson et al. 2010).
2. The survey-marker spacing in the HERU photographs, to turn the cavern into a measured
   exit-opening history.
3. Foundation material and erodibility at the HERU embankment site.
4. Confirmation that Fig. 2.14 is P1, and the times on the photographs relative to pulling the pipe
   (the time origin).

## 7. Decisions recorded (review 2026-11-26)

| item | decision |
|---|---|
| existing roof rule, crater-wall rule (5.17), D1-a/D5 | unchanged, frozen |
| G1/G2 module | kept for research comparison; not coupled |
| minimum block sizes | numerical regularisation only, flagged, with sensitivity reported |
| six-configuration comparison | on hold |
| exit erosion | next theory investigation (this note) |
| non-uniform pipe | investigated alongside; on present evidence it would be exit-concentrated (E1), not hydraulic along the pipe |
| erosion coefficients | not chosen to reproduce the retreat |

## 8. Review check of the existing exit headcut §5.6 (2026-11-26; `verification/exit_headcut_history.txt`)

The review asked which of three problems applies: the headcut never plunges, its erosion rate is too
low, or the experiment needs an outlet-widening mechanism. The checks, in the order requested:

1. **Initial state.** `ExitHeadcut(x_h = x_o, z_h = z_inv0)`: the channel bed starts at the pipe
   invert, so H_h = 0 at t = 0 (the review's reading is correct). H_h then grows by the difference
   between the face-channel and invert erosion rates.
2. **Hydraulic consistency.** The driver passes the actual outlet discharge: the pipe flow before the
   crater, then the crater's Q_out. Before the crater, the R-2 diagnostic's reconstructed flow is the
   same calculation, so its numbers agree for that period.
3. **Equations** (`sediment.py`, `headcut.py`):
   - Erosion: E = k_d (τ − τ_c)^n, with n = 1.
   - Critical depth: d_c = (q²/g)^(1/3), q = Q/b.
   - Face stress: Robinson (4.3)–(4.7), with no tailwater (d_bw = d_c).
   - Advance: (4.9), with the undercut at failure (4.8), capped at the 0.5H:1V surface rate.

   Two remarks:
   - (a) The `stage` label stays 2 once reached, while the rates follow the current condition.
     Cosmetic; nothing here reached stage 2.
   - (b) The trigger H_h > d_c and the Robinson relations assume a free overfall at critical depth,
     but the outlet here runs full, faster than critical. This approximation is already stated in §5.6.
4. **P1 time history** (k_d 3.16, dt 2 s, all 1708 flowing steps):

| t (s) | H_h (m) | d_c (m) | H_h − d_c (m) |
|---|---|---|---|
| 0 | 0.000 | 0.052 | −0.052 |
| 424 | 0.045 | 0.103 | −0.058 |
| 848 | 0.130 | 0.188 | −0.058 |
| 908 | the channel bed reaches the dam base, z_h = 0 | | |
| 1483 | 0.078 | 0.392 | −0.314 |

   Results:
   - **No plunging step, and the outlet never moves.**
   - **Counterfactual, with no base cap** (diagnostic arithmetic only, the bed keeps eroding below
     z = 0): H_h − d_c rises only to −0.003 m at roof collapse. **The base cap is not the main
     obstacle.** H_h and d_c grow almost exactly together, both driven by the same rising Q, so the
     trigger stays marginal throughout.

**Answer to the review's question:** the existing model fails to move the outlet because its plunging
headcut never activates, and it would barely activate even with an erodible base. Erosion rate is not
the limiting factor: the face channel already erodes 3–5 times faster than the pipe walls. Whether P1
needs a different exit mechanism (E1, widening of the open notch; E2, erosion of the roof lip by the
exit jet) is the open question. No code is changed.

## 9. The experimental opening, quantified from Wu (2016) Fig. 2.14 (2026-11-26)

**Method.** The photos are extracted from the DL Breach report PDF at native resolution, with each
panel enlarged 2 times. The survey markers (white crosses) form a regular grid on the downstream face,
so sizes are measured in **marker spacings s** along the row nearest the opening. That avoids
assuming s. The horizontal spacing reads 72–73 px in panels (b), (c) and (d) alike, which suggests a
similar camera position.

| panel | time | opening width | top of the opening | notes |
|---|---|---|---|---|
| (a) | initiation | a narrow crack only | — | a thin erosion channel runs down the face from the lowest marker row |
| (b) | 5 min | ≈ 1.1 s | at the lowest row | a single hole; the flow spreads over the toe |
| (c) | 8 min | ≈ 2.1 s | ≈ 0.4 of a row interval above the lowest row | arch-shaped, wider than high |
| (d) | 13 min, before collapse | ≈ 3.4 s | at the next row up | arch-shaped, wider than high; the toe is under flowing water |

**Scale (estimate, S).** In panel (a), two people stand in front of the face. Each spans about 3.8
marker spacings (≈ 277 px against ≈ 72 px). The markers are farther from the camera than the people,
so this is a lower bound: **s ≳ 0.45 m**, for a person height of 1.75 m (assumed). A 2 ft grid
(0.61 m) would fit. On that basis:

| time | observed opening width | model pipe width (k_d 3.16) |
|---|---|---|
| 5 min | ≳ 0.5 m | 0.063 m (at 300 s) |
| 13 min, roof collapse | ≳ 1.5 m | 0.29 m (at collapse) |

**Comparison that does not depend on the time origin (§5.4a):** at roof collapse, the observed exit
opening is at least about 5 times wider than the model's pipe.

**Height.** The arch top rises from the lowest row (5 min) to about one row interval above it
(13 min). If s is measured along the slope, one interval is s sin β ≈ 0.14–0.19 m of height. The
height of the opening therefore grows far less than its width. The model's square pipe has a crown
at 0.37 m at collapse, so it is comparable in height but not in width.

**What this supports, and what it does not:**
- **It supports** exit-concentrated, predominantly **lateral** enlargement at the downstream face,
  well before the roof collapses. That is mechanism E1 (widening of the open notch, cavern
  formation), possibly with E2 (erosion of the roof lip). Lateral collapse of the cavern walls once
  undercut can follow; the G1/G2 module is available for that check.
- **It does not establish** the rate law, the pipe geometry inside the dam (the photos show only the
  face), or the exact scale. s is a perspective-limited lower bound, and the photo times relative to
  pulling the pipe are not stated.

**Data that would firm this up:**
1. The actual marker spacing (Hanson et al. 2010 or HERU records).
2. The photo times relative to pulling the pipe.
3. Any measured outlet dimensions.

**Next (not started): outlet-widening hypothesis H-1.** It is developed separately from §5.6, with the
same discipline as the debris and face notes: (a)–(g) for each candidate, no coefficient chosen to
match, and acceptance tests set before any run. One acceptance target follows from this section: the
exit opening at roof collapse should be several times wider than the pipe (≳ 5 times, scale-limited),
with the height growing much less than the width.
