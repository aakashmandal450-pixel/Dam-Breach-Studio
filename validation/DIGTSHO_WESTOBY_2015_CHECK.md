# Dig Tsho 1985: Python 2D engine (v3.2.1) vs Westoby et al. (2015)

Westoby, M. J. et al. (2015) Numerical modelling of glacial lake outburst floods using physically based
dam-breach models. Earth Surf. Dynam. 3, 171-199. https://doi.org/10.5194/esurf-3-171-2015
HR BREACH, 1000 Monte Carlo runs per scenario, GLUE. Values below as reported in the paper (section/table given).
Ours: runs 2026-10-31_dt_dip_*_v321 and S1 sweep (5 kPa unless noted). Screening comparison, not validation.

## Erodibility / material
| Item | Ours | Westoby 2015 |
|---|---|---|
| Erosion law | Hanson excess shear, kd = 10^-1.17/1900 m/s/Pa (TS erosion index I = 1.17, UNSOURCED) x 0.1-1 | Non-cohesive sediment transport with flow factor 0.8-1.2 (Table 1); no kd |
| D50 | 30 mm | 28-200 mm (Table 1) |
| Manning n | 0.025 / 0.035 / 0.05 | sampled 0.02-0.05; behavioural 0.020-0.029, which the authors judge unrealistically low for a bouldery moraine (Sect. 7.1) |
| Roughness effect on peak | higher n -> HIGHER peak (4,502 vs 2,402 m3/s) | higher n -> LOWER peak (Fig. 7, Sect. 6.1.1) |
| Cohesion | 0 / 5 / 20 kPa | 0-100 kPa (Table 1), weak influence |
| Friction angle | 34 deg | 25-42 deg |
Erodibility cannot be compared directly (different laws). The roughness sign is opposite: our bed shear uses total
roughness n for erosion, so rougher = more erosive. Needs a grain-shear (skin friction) option before any roughness calibration.

## Formation time
| Item | Ours | Westoby 2015 |
|---|---|---|
| Observed | - | 4-6 h, anecdotal (Vuichard & Zimmermann 1987), not observed (Sect. 4) |
| Time to peak | 19 min (n 0.05) to 108 min (kd 0.25); kd 0.1 not peaked by 4 h | behavioural Tp clusters about 60-270 min (Sect. 6.1.3) |
| Lake empty | 51 min (n 0.05) to 184 min (kd 0.25) | - |

## Peak discharge
| Item | Ours | Westoby 2015 |
|---|---|---|
| Published | 1,600 (1,375-2,000) used as context | modelled values agree with Cenderelli & Wohl (2001) estimates |
| Range | 1,484-4,502 m3/s across S1 (kd 0.1 excluded) | behavioural 542-2,082; scenario medians 1,352-1,605; optimal runs 882-1,505 (Table 3) |
| Wave/overtopping input | VAW wave, HM 4.29 m; wave-window peak 2,941 m3/s | overtopping discharge 3,171 m3/s for the 1.5e5 m3 avalanche (mid scenario, Sect. 5.2.2) |
| Released volume | 5.7e6 m3 (whole 5.5e6 lake + prism water) | about 7.3e6 m3 revised (Sect. 4); median modelled 6.0-7.3e6 (Table 4) |

## Geometry
| Item | Ours (from TS chain script) | Westoby 2015 (SfM DTM) | Other in repo |
|---|---|---|---|
| Dam height | 18 m ("active water column" = lake depth) | crest 4356 m, foundation 4316 m -> 40 m implied (Table 1) | dig-tsho-1985.json: 60 m at lowest point (Vuichard & Zimmermann via Bajracharya 2007) |
| Crest length | 220 m | 250 m | |
| Crest width | 25 m | 30 m | |
| Downstream (distal) face | 1:2.5 | 1:3.1 | |
| Upstream (proximal) face | 1:1.8 | 1:15.2 | |
| Lake volume | 5.5e6 m3, storage exponent 1.8 | hypsometry Fig. 2; 5e6 earlier estimate, 7.3e6 revised | dig-tsho-1985.json: 5e6 |
| Freeboard | 0 | 0 | |
| Lake lowering (event) | 15.8 m (18.27 -> 2.43) | 16 +/- 2 m, the likelihood target (Sect. 5.4.1) | |
| Breach today | w50 50-120 m | about 200 m wide, 400 m long, up to 60 m deep (2010 survey, includes post-event change) | |

Key point: our 18 m erodible column with a rigid floor at the lake bed fixes the maximum lowering at about 16 m
(18 m less the debris-top stage). The 16 m match is therefore built in, not predicted.
