# Calibration and validation case register (stage 2)

Status as of 2026-10-31. Every entry is a CANDIDATE until its data are in `validation/sources/` and checked.
Tiers are assigned only by the rule in `SPLIT.md`, never by looking at how the engine does on a case.

| ID | Group | Case(s) | Scale, material, mode | Measured | Source | Access | Status |
|---|---|---|---|---|---|---|---|
| G1 | Lab, cohesive, JET | USDA-ARS Stillwater overtopping tests, 7 embankments 1.5-2.3 m, 3 soils (2 SM silty sand, 1 CL lean clay) | Large lab, homogeneous cohesive, overtopping | JET kd and tau_c, headcut migration, widening, outflow | Hanson, Cook & Hunt (2005), Trans. ASAE 48(5):1783-1794, doi:10.13031/2013.20012 | Paywalled paper; ask for data or use library access | To obtain |
| G2 | Large lab, zoned/rockfill, JET | Reclamation dam breach test facility, 3 tests 2015-2017 (1 homogeneous internal erosion, 1 zoned overtopping, 1 zoned internal erosion) | Large lab | JET kd, kd back-estimated from photos, discharge | Wahl, PFHA 2019 presentation (sources/), NRC ML19156A480 | Public | Obtained; all three excluded (EXCLUDED.md) |
| G3 | Lab and field, mixed | DLBreach test set: 50 dam + 4 levee/barrier cases | Lab and field; non-cohesive, cohesive, composite; overtopping and piping | Geometry, soil, peak, breach size (varies) | Wu (2016) DLBreach report + test-case zip, webspace.clarkson.edu/~wwu/DLBreach.html | Public | To download (shell is blocked; browser download) |
| G4 | Field, 4-6 m | IMPACT field tests, Norway (5 tests) | Field, homogeneous and composite, overtopping and piping | Breach growth, flow, soil data | FLOODsite report T04-08-04 (corrected data sets released with it) | Public; documented data issues, use corrected sets | To download |
| G5 | Historic failures | Wahl (1998) database, 108 embankment failures (Table A1) | Field, mixed | Height, volume, peak, breach width, time (no erodibility) | Reclamation DSO-98-004 | Public PDF | To download; screening use only |
| G6 | Moraine, wave-triggered | Queen Bess Lake 1997, BC: ice avalanche -> displacement waves overtop and breach the moraine; lake fell about 8 m | Field, moraine, overtopping | Lake drop, breach geometry, empirical peak estimates (two-phase flood) | Kershaw, Clague & Evans (2005) ESPL 30(1):1-25, doi:10.1002/esp.1122 | Paywalled | To obtain |
| G7 | Reconstruction | Dig Tsho 1985 | Field, moraine, wave-triggered overtopping | Lake lowering 16 +/- 2 m, breach today, anecdotal timing, peak estimates | Westoby et al. (2015) ESurf 3:171-199 (open access) | Public | Geometry rebuilt (V3.2.2); Fig. 2 lake curve still to read |

Engine fit notes: the 2-D prism engine handles overtopping only (no piping), so piping cases in G3/G4 are excluded.
G1 and G2 are the only groups with measured erodibility; they are the core of calibration.

Update 2026-10-31: sources obtained; see EXCLUDED.md and ASSIGNMENT.md. DSO-2017-02 file in sources/ is an unrelated UK document with the same number.

## G5 screening result (2026-11-01): option to use Wahl (1998) as a calibration tier
Table A1 parsed to `wahl1998_tableA1.csv` (108 cases, parser `parse_wahl1998.py`). 41 are overtopping failures.
Applying the split rules: 23 lack dam height or reservoir volume, 13 are zoned or have core walls/facings, several have
fewer than two observations, and 4 are already in G3 (Castlewood, Goose Creek, Laurel Run, Johnstown/South Fork).
Only 3 remain: Euclides da Cunha and Salles Oliveira (Brazil, 1977 cascade; both overtopped by a flood whose inflow
is not given, Salles by the Euclides failure) and Lake Barcroft (no peak; inflow not given). None states soil type
beyond "earthfill", so no erodibility class can be assigned. Decision: G5 stays screening-only; split unchanged.
