# Part 5, investigation note (draft for review): the roof-remnant geometry at collapse

*Draft R-1 · 2026-11-26 · status: for review. Nothing is implemented. Nothing is to be adjusted to
reach the P1 observation (§5.7b.4).*

## 1. Why this note

Under the frozen debris rules (§5.7b), P1 seals in every run (§5.7b.4). Whether fallen roof material
blocks the flow at all depends on where the roof fails and what is left standing on either side. The
plugs exist only because intact remnants hold the two mouths in place. So this question comes before
any seepage assumption is reconsidered.

## 2. What the model produces at collapse (P1; same at every k_d)

These values are from the converged P1 runs (k_d = 150, dt = 0.5 s); the geometry does not depend on k_d.

| quantity | model at roof collapse |
|---|---|
| pipe (uniform along its length) | b 0.29 m, D 0.30 m, invert 0.07 m (started at 0.20 m, 0.04 m square) |
| inlet | retreated from x = 0.66 to 1.60 m by upstream-end failures (cover over the crown there 0.16 m) |
| outlet | **never moved**: x = 8.97 m from start to collapse. No outlet retreat, no uplift (mechanism C), no headcut plunging (§5.6, drop below d_c) |
| first failure | interior, at x = 5.66–5.80 m, the corner of the crest and the downstream slope |
| crater after the cascade | x = 5.66 → 6.26 m, W = b_p |
| upstream remnant | 1.60 → 5.66 m (4.1 m; cover 0.16 → 0.93 m) |
| downstream remnant | 6.26 → 8.97 m (2.7 m; cover 0.76 → about 0 m at the outlet) |

So the model ends with a short crater between two long remnants: an asymmetric outcome in which the
inlet end retreats and the outlet end stays fixed.

## 3. What the observation shows

The sources on file:
- **Wu (2016), Fig. 2.14.** These are photographs of a HERU piping test credited to Hanson et al.
  (2010). They are taken from downstream, at 0, 5, 8, 13 (before and after the roof collapse) and
  60 min. The collapse at 13 min matches P1's T_c of 828 s (PAP-1017, Table 1). It is very likely P1,
  but the caption does not say so (**to confirm**).
  - **5 min:** a large opening at the downstream face, clearly larger than the 40 mm pipe, with
    eroded material spreading below it.
  - **8 and 13 min:** an arched cavern at the downstream face. It grows with time, spans several
    rows of the survey markers on the slope, and is wider than it is high.
  - **13 min, after collapse:** a full-height notch through the crest. Water flows through it
    freely; no blockage is visible.
  - **60 min:** a wide breach, still widening (consistent with Chen et al. 2019, Fig. 6).
- **Wu (2016), Fig. 2.15** (sketch "observed in experiments"). The pipe runs inclined toward the
  downstream face. The downstream face slumps above the exit, and a scour hole forms at the toe.
- **PAP-1017** (as cited in the debris note, §4). The bridge collapsed after an **inlet funnel**
  formed and the **downstream headcutting reached the base**.
- **Model practice.** DLBreach (Wu 2016, §4.7) and Chen et al. (2019, §2.5) both fail the roof over
  the **whole** pipe length, along vertical planes from the side walls. The failed block is removed:
  DLBreach stores it in a virtual tank, while Chen et al. remove it instantly. In our terms, this is
  the **maximum-spread** case of §5.7a.9 combined with the tank or instant treatment.

## 4. The gap, stated

| | model | observation |
|---|---|---|
| where enlargement concentrates | uniform along the pipe (lumped rectangle, §5.4) | at the **downstream exit**: a large cavern at the face by 5–13 min |
| downstream end before collapse | fixed; 2.7 m of intact cover remains at collapse | eroded back. The headcut reached the base (PAP-1017) and the face slumped (Fig. 2.15) |
| upstream end | retreats about 0.9 m (end failures) | inlet funnel (PAP-1017) |
| what is left at collapse | a short crater between long remnants | a short bridge that collapses into a through-going notch with free flow |

The model's downstream remnant, and with it the buried downstream mouth that §5.7b has to break
through, may not exist in the experiment by the time of collapse. If the exit had eroded back to the
crest corner, the roof debris would fall in front of an open face instead of over a buried pipe
entrance. **Caveat:** the photographs show only the downstream face. The upstream side, the bridge
length and the cavern dimensions are not measured in any source on file.

## 5. Candidate explanations (stated, not adopted)

- **R1. Exit-concentrated enlargement (non-uniform pipe).** The flow leaves the pipe onto the slope
  as a high-velocity free-surface jet, and the face erodes at and below the exit. The lumped uniform
  pipe cannot place this. The §5.6 exit headcut is the mechanism meant for it. It did not plunge for
  P1 because the drop at the estimated invert (0.20 m) stays below d_c. This makes it sensitive to
  the **pipe elevation**, which is an estimate (Chen et al. 2019, Table 1; "the lowest marker row on
  the d/s slope").
- **R2. Seepage exit at the downstream face (sapping and slumping).** This is the Fig. 2.15 sketch.
  It is a stability failure of the face above the exit, driven by the seepage gradient. It is related
  to mechanism C (uplift, §5.6) but acts on the face rather than the pipe roof. It is not in the
  model.
- **R3. Outlet-end roof failure under the exit flow.** The outlet reach has thin cover and the soffit
  pressure falls toward atmospheric there. The present check finds it stable. End lips (C < 0.25 b)
  are not checked.
- **R4. Whole-roof collapse (maximum spread, §5.7a.9).** This is already specified and reviewed, but
  not implemented. It is the DLBreach and Chen assumption. It reaches a hand-over at the first
  collapse by construction, so it bounds the effect of the remnants rather than explaining them.

## 6. Proposed order (for decision)

1. **No new physics first.**
   - (a) Implement the **maximum-spread** comparison case already required by §5.7a.9, as an option
     and off by default. Report it beside rule S, never averaged with it.
   - (b) Run the **invert scenarios** already planned (z_inv0 = 0.2, 0.3, 0.4 m), exit headcut on
     and off. They test whether R1, through the existing §5.6 machinery, shortens the downstream
     remnant before collapse.
2. **Quantify the observation where possible.**
   - Confirm that Fig. 2.14 is P1.
   - Obtain the survey-marker spacing (from Hanson et al. 2010 or the HERU photo records). That
     would turn the cavern size at 8 and 13 min into a measured, if rough, downstream-opening history
     to compare with the model's outlet.
3. **Only if 1–2 leave the gap open:** write theory for R1 and/or R2 (separately, each with
   (a)–(g) as for the debris candidates) for review before any code.

## Sources

- Wu, W. (2016). DL Breach technical report: §2.2, Figs. 2.14–2.16; §4.7. On file.
- Chen, S., Zhong, Q., Shen, G. (2019). *Water Sci. Eng.* 12(3), 169–178: §2.5, Table 1, Fig. 6.
  On file.
- Wahl, T. L. (2010). USBR PAP-1017, Table 1. As cited in the debris note §4.
- Hanson, G. J., Tejral, R. D., Hunt, S. L., Temple, D. M. (2010). Internal erosion and impact of
  erosion resistance. USSD. **Not obtained.**
