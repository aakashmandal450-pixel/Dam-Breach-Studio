# Excluded cases (rules in SPLIT.md, split-2)

| Case | Source | Rule | Reason |
|---|---|---|---|
| All 26 DLBreach piping cases (#25-50) | Wu 2016, Tables 6.8-6.9 | 1 | Piping |
| IMPACT field 2-03, 3-03 | Hassan & Morris 2008 | 1 | Piping |
| Reclamation homogeneous CL-ML test (2015) | Wahl, PFHA 2019 | 1 | Internal erosion |
| Lijiaju, China (#18) | Wu 2016, Table 6.4 | 2 | Only peak outflow observed |
| IMPACT lab #2, #4, #5, #6, #7 (#1-5), #10, #15, #16 (#11-13) | Wu 2016, Tables 6.1, 6.3 | 3 | Reservoir given only as an area-height curve that is not published in the sources we hold. Re-admit before the first calibration run if the IMPACT lab data are obtained |
| USDA-ARS embankment 3 (E3S2) | Hanson et al. 2005 | 3 | No stage-storage curve for the embankment 3 reservoir (Fig. 2 covers embankments 1 and 2 only) |
| Chinnarasri C1-C3 (#19-21), Banqiao (#23), Oros (#24) | Wu 2016, Tables 6.5-6.7 | 4 | Zoned or clay-covered embankments |
| IMPACT field 1-03 (#22) | Wu 2016; Hassan & Morris 2008 | 4 | Rockfill with moraine core |
| Reclamation zoned embankment overtopping test (2017) | Wahl, PFHA 2019 | 4 | Zoned rockfill embankment |
| Queen Bess Lake 1997 | Kershaw, Clague & Evans 2005 | 3 | No dam height or slopes reported (only lake lowering 8 m, release 6.5e6 m3). Re-admit before the first calibration run if Clague & Evans (2000) or a DEM supplies the moraine geometry |
| Wahl (1998) historic database | DSO-98-004 Table A1 | G5 | Screening only by split rule; to be extracted separately, never calibration |
| Walsh (2019) S1-S6, W1-W5 | Walsh 2019 MASc | split-4 | Engine limits found by the Walsh diagnostics (`diag_walsh.py`, 2026-11-03; see RUNS.md): (a) initiation from the 6 cm notch is controlled by grid and threshold artefacts, not physics: the sub-cell notch is widened to one cell, its walls collapse at c = 0 on fine grids, flow on the face falls below `h_dry` = 1 mm and spreads as a sheet, and the scour step never reaches the 0.5 headcut slope; (b) started at Walsh's stage 3 with a 0.37 m pilot channel, erosion and widening at the upstream breach lip are too weak (H/16: 13 L/s at 300 s and still rising, vs 0.24 m3/s observed at 73 s; strongly grid-dependent). split-5 (2026-11-07): S1, S3, S5 return as seen validation (SPLIT.md); S2, S4, S6 and W1-W5 stay excluded |
