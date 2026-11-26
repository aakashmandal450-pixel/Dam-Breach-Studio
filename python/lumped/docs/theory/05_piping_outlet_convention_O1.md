# Part 5, note O-1 (review, documentation only): the free-discharge outlet convention

*2026-11-26 · status: opened by the decision recorded in §5.9. **No change to the frozen baseline**:
(5.3) and (5.8) are unchanged until this comparison has been reviewed. The question is separate from
H1-d and from the H1-a verification record.*

## 1. The two conventions

**Model, (5.3)–(5.4).** Outlet control with a free outfall:

    Q_o = A √( 2g (HW − h_o) / (K_u + K_d + fL/(4R)) ),   h_o = max(y/2, h_t)

- Heads are above the pipe invert. For a full barrel, y = D, so **h_o = D/2: the hydraulic grade at
  the exit is at the pipe centreline.**
- (5.8) then gives a crown pressure of −γ_w D/2 at the exit, rising upstream with the friction slope,
  and clipped to 0.

**FHWA HDS-5, culvert outlet control.** h_o = max(TW, (d_c + D)/2), with d_c taken no greater than D.
Full barrels are distinguished from partly full ones, using tailwater or critical depth and, where
needed, a backwater calculation. **For P1 (d_c ≥ D throughout), h_o = D: the hydraulic grade at the
exit is at the crown.** The crown pressure is 0 at the exit and positive upstream.

**Caveat (from the decision).** HDS-5 is a culvert-design reference, and the model represents an
evolving breach pipe. The question is not which convention is "right" in general. It is which one is
appropriate for the model's stated assumptions, and whether it stays consistent as the outlet geometry
changes.

## 2. Effect on P1 (same geometry; no re-run; `verification/outlet_convention_check.txt`)

| t (s) | D (m) | h_o model / HDS-5 (m) | Q_o model / HDS-5 (L/s) | ratio | crown pressure head at the exit, model / HDS-5 (m) |
|---|---|---|---|---|---|
| 0 | 0.040 | 0.020 / 0.040 | 1.47 / 1.45 | 0.989 | −0.020 / 0 |
| 800 | 0.128 | 0.064 / 0.128 | 29.7 / 28.6 | 0.963 | −0.064 / 0 |
| 1501 | 0.288 | 0.144 / 0.288 | 227.6 / 208.2 | 0.914 | −0.144 / 0 |

- The discharge differs by 1% at the start and 9% at roof collapse. The model passes more flow, so it
  has a higher velocity and, for the same geometry, up to about 16% more wall shear late in the pipe
  stage. The collapse time would shift accordingly, but it is **not computed here**, because computing
  it would mean changing the frozen code.
- **The crown pressure near the exit changes sign.** The model's sub-atmospheric crown (up to 2.2 m
  long at collapse, note H-1 §11) exists only under its convention. It feeds the roof check through
  (5.8), clipped to 0, and reduces the soffit support near the outlet.

## 3. Consistency questions for the review

1. **Full barrel with d_c ≥ D at a free exit.** Is the centreline reference defensible for P1? The
   physical exit-plane pressure of a free jet is roughly atmospheric across the section, which is
   closer to the HDS-5 grade at the crown than to the centreline.
2. **Tailwater.** In the photos (Wu 2016, Fig. 2.14, panels (c) and (d)), flowing water covers the toe
   in front of the opening. If that water stands above the exit invert, then h_t > 0 in both
   conventions. Its depth is not measured, so TW = 0 is an assumption.
3. **A changing outlet geometry.** With H1-a, the exit widens into a free-surface notch (note H-1 §11).
   Does the outlet condition still hold once the expansion is at the exit plane? Both conventions
   treat the exit as a fixed-width barrel end.
4. **Partly full barrels.** The model switches to a part-full section below HW = 1.5 D through (5.2).
   HDS-5 would use (d_c + D)/2 for a partly full outlet. That is not relevant to P1, where the barrel
   is full from the start, but it is relevant to other cases.

## 4. Options (for decision after review; none is taken now)

- **(a)** Keep (5.3) as it is, with its basis stated (a centreline reference for a free jet) and the
  sub-atmospheric crown reported as a convention effect.
- **(b)** Adopt the HDS-5 outlet head, h_o = max(h_t, (min(d_c, D) + D)/2). This would require
  re-running every frozen P1 record as a new baseline, never mixed with the old.
- **(c)** Treat the exit grade explicitly from a jet-exit or backwater analysis, if (a) and (b) are
  both judged inadequate for an evolving breach outlet.

**Whatever is chosen:** the present baseline stays reproducible, and any change gives a new,
separately labelled baseline. The H1-a tests and the P1 records stay as recorded.

## 5. Review recommendation (2026-11-26)

**Status: reviewed, not resolved. The baseline stays frozen.**

1. **The comparison is a sensitivity assessment at identical geometry, not a replacement
   simulation.** The 9% lower discharge at roof collapse, and up to about 16% less wall shear, are
   meaningful. They are not evidence that either convention is correct, and **no collapse-time
   correction is inferred from them.** Their effect on breach timing has not been established.
2. **The pressure reference needs justification either way.** The centreline reference of (5.3)
   needs a clear physical basis for a pipe that discharges freely, with its jet exposed to atmospheric
   pressure. The HDS-5 crown reference has to be assessed within its culvert assumptions, not adopted
   by default.
3. **Tailwater is an independent uncertainty.** The photographs show water covering the downstream
   toe. They do not show the tailwater depth at the outlet. TW = 0 is an **assumption, not an
   observed condition.**
4. **The widened notch is a different hydraulic geometry.** Neither convention carries over
   automatically from the original full-pipe outlet once H1-a produces a free-surface opening.
   Widened-outlet hydraulics stay an unresolved question.
5. **Part-full flow** stays in the scope of the general review, though it does not affect P1.

**Actions:**
- (5.3) and (5.8) are retained.
- The HDS-5 comparison is recorded as a sensitivity (`verification/outlet_convention_check.txt`).
- Tailwater and widened-outlet hydraulics are recorded as unresolved.
- **If option (b) or (c) is selected:** create a separately labelled hydraulic baseline and re-run
  the relevant validation cases. Never mix it with the present baseline.
