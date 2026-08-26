#!/usr/bin/env python3
"""
Erosion Rate Index – Time-to-Breach Computational Tool v1.0
Transparent, equation-based implementation of pipe-enlargement time
following Wan & Fell (2004) Erosion Rate Index and Bonelli-type
closed-form solutions for concentrated-leak / piping enlargement.
Citations provided on the Cover and Equations sheets.
"""

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import FormulaRule
from openpyxl.chart import LineChart, Reference

wb = Workbook()

# Styles
thin = Border(
    left=Side(style='thin', color='B0B0B0'),
    right=Side(style='thin', color='B0B0B0'),
    top=Side(style='thin', color='B0B0B0'),
    bottom=Side(style='thin', color='B0B0B0')
)
fill_title = PatternFill('solid', fgColor='0D3B66')
fill_header = PatternFill('solid', fgColor='1F4E79')
fill_subheader = PatternFill('solid', fgColor='2E75B6')
fill_section = PatternFill('solid', fgColor='D6EAF8')
fill_input = PatternFill('solid', fgColor='FFF2CC')
fill_calc = PatternFill('solid', fgColor='E2EFDA')
fill_link = PatternFill('solid', fgColor='DDEBF7')
fill_limit = PatternFill('solid', fgColor='FCE4D6')
fill_note = PatternFill('solid', fgColor='FFF8E7')
fill_gray = PatternFill('solid', fgColor='F2F2F2')
fill_within = PatternFill('solid', fgColor='C6EFCE')
fill_outside = PatternFill('solid', fgColor='FFC7CE')

font_white_bold = Font(name='Arial', bold=True, color='FFFFFF', size=14)
font_white = Font(name='Arial', color='FFFFFF', size=10)
font_header = Font(name='Arial', bold=True, color='FFFFFF', size=11)
font_title = Font(name='Arial', bold=True, color='1F4E79', size=16)
font_section = Font(name='Arial', bold=True, color='1F4E79', size=11)
font_normal = Font(name='Arial', size=10)
font_input = Font(name='Arial', size=10, color='0000FF')
font_calc = Font(name='Arial', size=10, color='000000')
font_small = Font(name='Arial', size=9)
font_tiny = Font(name='Arial', size=8, italic=True)
font_eq = Font(name='Consolas', size=9)

align_c = Alignment(horizontal='center', vertical='center', wrap_text=True)
align_l = Alignment(horizontal='left', vertical='center', wrap_text=True)
align_t = Alignment(horizontal='left', vertical='top', wrap_text=True)

def style_header_row(ws, row, sc, ec, fill=fill_header):
    for c in range(sc, ec+1):
        cell = ws.cell(row=row, column=c)
        cell.fill = fill
        cell.font = font_header
        cell.alignment = align_c
        cell.border = thin

def style_input(cell):
    cell.fill = fill_input
    cell.font = font_input
    cell.alignment = align_c
    cell.border = thin

def style_calc(cell):
    cell.fill = fill_calc
    cell.font = font_calc
    cell.alignment = align_c
    cell.border = thin

def set_widths(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

# ============================================================
# 00 COVER
# ============================================================
ws = wb.active
ws.title = "00_Cover"
set_widths(ws, [3, 55, 25, 25, 20, 20])

ws.merge_cells('B2:F2')
ws['B2'] = "EROSION RATE INDEX – TIME-TO-BREACH TOOL"
ws['B2'].font = Font(name='Arial', bold=True, color='FFFFFF', size=18)
ws['B2'].fill = fill_title
ws['B2'].alignment = align_c

ws.merge_cells('B3:F3')
ws['B3'] = "Pipe Enlargement Time via Wan & Fell (2004) Erosion Rate Index and Bonelli-type closed-form solutions"
ws['B3'].font = font_white
ws['B3'].fill = fill_header
ws['B3'].alignment = align_c

ws.merge_cells('B4:F4')
ws['B4'] = "Version 1.0  |  Metric Units  |  Transparent equation-based implementation (not a port of proprietary toolboxes)"
ws['B4'].font = font_white
ws['B4'].fill = fill_subheader
ws['B4'].alignment = align_c

ws.merge_cells('B6:F6')
ws['B6'] = "PURPOSE & SCOPE"
ws['B6'].font = font_header
ws['B6'].fill = fill_header
ws['B6'].alignment = align_c

ws.merge_cells('B7:F10')
ws['B7'] = (
    "This workbook estimates the time required for a concentrated leak (pipe or crack) to enlarge "
    "from a detected / initial radius to a size at which roof collapse or gross enlargement leads to breach. "
    "It sits logically UPSTREAM of empirical breach-parameter methods (BFF / Tech Note 1 / Froehlich). "
    "Once a credible time-to-breach (or time-to-gross-enlargement) is obtained, that value can be used as "
    "T.Fail or t in the Dam Breach Computational Tool (or any other hydrograph generator).\n\n"
    "The calculation is intentionally transparent: every equation is shown, every assumption is stated, "
    "and typical ranges of the Erosion Rate Index are tabulated from published sources."
)
ws['B7'].font = font_small
ws['B7'].alignment = align_t
ws['B7'].fill = fill_note

ws.merge_cells('B12:F12')
ws['B12'] = "PRIMARY CITATIONS"
ws['B12'].font = font_header
ws['B12'].fill = fill_header
ws['B12'].alignment = align_c

cites = [
    "1. Wan, C.F. & Fell, R. (2004). Laboratory Tests on the Rate of Piping Erosion of Soils in Embankment Dams. Geotechnical Testing Journal, 27(3), 295–303. (Defines the Erosion Rate Index I and Hole/Slot Erosion Tests.)",
    "2. Wan, C.F. & Fell, R. (2004). Investigation of Rate of Erosion of Soils in Embankment Dams. J. Geotech. Geoenviron. Eng., 130(4), 373–380.",
    "3. Bonelli, S. et al. (various). Closed-form solutions for the evolution of a cylindrical pipe under constant head; characteristic time ter and remaining time Δtu ≈ ter · ln(Ru/Rd).",
    "4. Fell, R., Foster, M., et al. – USACE/USBR Unified Method for Internal Erosion (guidance documents and RMC Internal Erosion Suite).",
    "5. ICOLD Bulletin 164 (and related) – representative values of erosion rate index by soil type; graphical time-to-enlargement charts.",
    "6. USACE RMC Internal Erosion Suite (Breach Toolbox – gross enlargement worksheet) – practical implementation of excess-shear-stress pipe enlargement.",
]
for i, c in enumerate(cites):
    r = 13 + i
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
    ws.cell(row=r, column=2, value=c).font = font_small
    ws.cell(row=r, column=2).alignment = align_l
    if i % 2 == 0:
        ws.cell(row=r, column=2).fill = fill_gray

ws.merge_cells('B20:F20')
ws['B20'] = "COLOUR CODING"
ws['B20'].font = font_header
ws['B20'].fill = fill_header
ws['B20'].alignment = align_c

ws['B21'] = "Yellow + blue text"
ws['C21'] = "User input"
ws['B21'].fill = fill_input
ws['B22'] = "Light green + black text"
ws['C22'] = "Calculated result"
ws['B22'].fill = fill_calc
ws['B23'] = "Orange panel"
ws['C23'] = "Limitations / applicability"
ws['B23'].fill = fill_limit
ws['B24'] = "Light blue section"
ws['C24'] = "Section header"
ws['B24'].fill = fill_section

ws.merge_cells('B26:F26')
ws['B26'] = "IMPORTANT DISCLAIMER"
ws['B26'].font = font_header
ws['B26'].fill = fill_header
ws['B26'].alignment = align_c

ws.merge_cells('B27:F29')
ws['B27'] = (
    "This is an engineering calculation aid for Professional Engineers. It implements published equations "
    "for educational and screening purposes. Real dam-safety assessments of internal erosion require "
    "site-specific soil testing (HET/JET), filter evaluation, full event-tree treatment, and engineering judgement. "
    "The simplified closed-form solutions assume constant head, cylindrical pipe, and constant Ce; they do not "
    "replace the more comprehensive RMC Internal Erosion Suite or a full numerical model. "
    "The user retains full professional responsibility for application to any real structure."
)
ws['B27'].font = font_small
ws['B27'].alignment = align_t
ws['B27'].fill = fill_note

# ============================================================
# 01 PARAMETER DEFINITIONS & SCHEMATIC
# ============================================================
ws1 = wb.create_sheet("01_Parameters_Schematic")
set_widths(ws1, [3, 14, 12, 14, 50, 40])

ws1.merge_cells('B2:F2')
ws1['B2'] = "PARAMETER DEFINITIONS, UNITS, TYPICAL RANGES & SCHEMATIC"
ws1['B2'].font = font_white_bold
ws1['B2'].fill = fill_title
ws1['B2'].alignment = align_c

ws1.merge_cells('B4:F4')
ws1['B4'] = "A. SOIL EROSION PARAMETERS"
ws1['B4'].font = font_header
ws1['B4'].fill = fill_header
ws1['B4'].alignment = align_c

headers = ["Symbol", "Unit", "Typical Range", "Definition / Physical Meaning", "Source / Note"]
for i, h in enumerate(headers, 2):
    ws1.cell(row=5, column=i, value=h)
style_header_row(ws1, 5, 2, 6)

params = [
    ("I", "—", "0 – 6", "Erosion Rate Index = –log10(Ce). Higher I = more erosion-resistant soil. Defined by Wan & Fell from HET/SET.", "Wan & Fell 2004"),
    ("Ce", "s/m  (or m²/s per Pa)", "10⁻⁶ – 10⁻¹", "Coefficient of soil erosion. Volume (or mass) erosion rate per unit area per unit excess shear stress.", "Ce = 10^(–I)"),
    ("τc  (tau_c)", "Pa", "0 – ~100+", "Critical hydraulic shear stress below which erosion does not occur (or is negligible).", "From HET / JET"),
    ("ρd", "kg/m³", "1400 – 2000", "Dry bulk density of the eroding soil.", "Typical compacted fill"),
    ("I (soil class)", "—", "see table", "Representative values by USCS / soil description (ICOLD / Wan & Fell tables).", "Screening only"),
]

for i, (sym, unit, rng, defin, note) in enumerate(params):
    r = 6 + i
    ws1.cell(row=r, column=2, value=sym).font = Font(name='Arial', bold=True, size=10)
    ws1.cell(row=r, column=3, value=unit).font = font_normal
    ws1.cell(row=r, column=4, value=rng).font = font_small
    ws1.cell(row=r, column=5, value=defin).font = font_small
    ws1.cell(row=r, column=6, value=note).font = font_tiny
    for c in range(2, 7):
        ws1.cell(row=r, column=c).border = thin
        ws1.cell(row=r, column=c).alignment = align_l
        if i % 2 == 0:
            ws1.cell(row=r, column=c).fill = fill_gray

ws1.merge_cells('B12:F12')
ws1['B12'] = "B. GEOMETRIC & HYDRAULIC PARAMETERS OF THE PIPE"
ws1['B12'].font = font_header
ws1['B12'].fill = fill_header
ws1['B12'].alignment = align_c

for i, h in enumerate(headers, 2):
    ws1.cell(row=13, column=i, value=h)
style_header_row(ws1, 13, 2, 6)

params2 = [
    ("L", "m", "core thickness", "Length of the pipe / seepage path through the core (or along the concentrated leak).", "Usually ≈ core width"),
    ("Δp  or  Δh", "Pa  or  m", "ρg·H", "Pressure (or head) drop driving flow through the pipe. For constant reservoir level Δp = ρw·g·H.", "H = reservoir head on core"),
    ("Rd", "m", "0.01 – 0.25", "Pipe radius at detection (or assumed initial radius when progression begins).", "Eyewitness / assumption"),
    ("Ru", "m", "~ Hb/3 – Hb/2", "Ultimate / collapse radius at which roof collapses or gross enlargement is deemed to have occurred.", "Often Hb/3"),
    ("Hb", "m", "dam height", "Relevant embankment / core height used to set Ru.", "From dam geometry"),
    ("τb", "Pa", "calculated", "Boundary shear stress exerted by the flow on the pipe wall.", "τ = f(Δp, R, L) or simplified"),
]

for i, (sym, unit, rng, defin, note) in enumerate(params2):
    r = 14 + i
    ws1.cell(row=r, column=2, value=sym).font = Font(name='Arial', bold=True, size=10)
    ws1.cell(row=r, column=3, value=unit).font = font_normal
    ws1.cell(row=r, column=4, value=rng).font = font_small
    ws1.cell(row=r, column=5, value=defin).font = font_small
    ws1.cell(row=r, column=6, value=note).font = font_tiny
    for c in range(2, 7):
        ws1.cell(row=r, column=c).border = thin
        ws1.cell(row=r, column=c).alignment = align_l
        if i % 2 == 0:
            ws1.cell(row=r, column=c).fill = fill_gray

# Schematic
ws1.merge_cells('B21:F21')
ws1['B21'] = "C. SCHEMATIC – PIPE ENLARGEMENT UNDER CONSTANT HEAD"
ws1['B21'].font = font_header
ws1['B21'].fill = fill_header
ws1['B21'].alignment = align_c

schematic = """
  Upstream reservoir                          Downstream
  (head H)                                    (tailwater ≈ 0)

       |                                         |
       |   Core / embankment (length L)          |
       |   ===================================== |
       |   |                                   | |
       |   |     cylindrical pipe of radius R(t)| |
       |   |     <----- growing by erosion ---->| |
       |   |                                   | |
       |   ===================================== |
       |                                         |

  Governing idea (Bonelli-type):
    Excess shear stress τ – τc drives radial erosion.
    Under constant pressure drop Δp the radius evolves exponentially:
        R(t) / R0  ≈  (τc/P0) + (1 – τc/P0) · exp(t / ter)

  Characteristic time of piping:
        ter  =  2 · ρd · L  /  (Ce · Δp)          [or close variants]

  Remaining time from detection (Rd) to collapse (Ru), simplified (τc ≈ 0 or small):
        Δtu  ≈  ter · ln(Ru / Rd)

  Practical screening form used in this workbook:
        Δt   =  (2 · ρd · L / (Ce · ρw · g · H)) · ln(Ru / Rd)

  Where Ce = 10^(–I)
"""
ws1.merge_cells('B22:F38')
ws1['B22'] = schematic
ws1['B22'].font = Font(name='Consolas', size=9)
ws1['B22'].alignment = align_t
ws1['B22'].fill = fill_gray
ws1['B22'].border = thin
ws1.row_dimensions[22].height = 260

# ============================================================
# 02 TYPICAL VALUES TABLE
# ============================================================
ws2 = wb.create_sheet("02_Typical_I_Values")
set_widths(ws2, [3, 35, 12, 18, 40])

ws2.merge_cells('B2:E2')
ws2['B2'] = "REPRESENTATIVE EROSION RATE INDEX VALUES BY SOIL TYPE"
ws2['B2'].font = font_white_bold
ws2['B2'].fill = fill_title
ws2['B2'].alignment = align_c

ws2.merge_cells('B3:E3')
ws2['B3'] = "Compiled from Wan & Fell (2004), ICOLD Bulletin guidance, and related summaries. Use only for screening; site-specific HET/JET preferred."
ws2['B3'].font = font_small
ws2['B3'].fill = fill_section

headers2 = ["Soil Description / USCS", "Typical I", "Relative Erodibility", "Notes"]
for i, h in enumerate(headers2, 2):
    ws2.cell(row=5, column=i, value=h)
style_header_row(ws2, 5, 2, 5)

soils = [
    ("Very rapidly erodible (e.g. dispersive clays, fine silts, SM with little plasticity)", "0 – 2", "Extremely rapid", "Failure possible in minutes to a few hours"),
    ("Rapidly erodible (many SM, SC, ML, CL with low plasticity)", "2 – 3", "Rapid", "Hours"),
    ("Moderately erodible (CL, CH, MH of moderate plasticity)", "3 – 4", "Moderate", "Many hours to a day"),
    ("Slowly erodible (higher plasticity clays, well-compacted)", "4 – 5", "Slow", "Days"),
    ("Very slowly erodible / extremely resistant", "5 – 6+", "Very slow", "Many days; may self-heal or not progress"),
    ("Coarse cohesionless (clean SP, GP) – different mechanism", "N/A (use BEP models)", "Backward erosion piping", "Sellmeijer / Schmertmann / RMC BEP tools"),
]

for i, (desc, I, rel, note) in enumerate(soils):
    r = 6 + i
    ws2.cell(row=r, column=2, value=desc).font = font_small
    ws2.cell(row=r, column=3, value=I).font = Font(name='Arial', bold=True, size=10)
    ws2.cell(row=r, column=3).alignment = align_c
    ws2.cell(row=r, column=4, value=rel).font = font_small
    ws2.cell(row=r, column=5, value=note).font = font_tiny
    for c in range(2, 6):
        ws2.cell(row=r, column=c).border = thin
        ws2.cell(row=r, column=c).alignment = align_l
        if i % 2 == 0:
            ws2.cell(row=r, column=c).fill = fill_gray

ws2.merge_cells('B13:E15')
ws2['B13'] = (
    "NOTE: The Erosion Rate Index I is defined such that a change of 1 unit in I corresponds to a factor-of-10 change in Ce. "
    "Thus soils with I = 2 erode ~100 times faster than soils with I = 4 under the same excess shear stress. "
    "Always prefer laboratory HET or JET results for the actual core material when available."
)
ws2['B13'].font = font_small
ws2['B13'].fill = fill_note
ws2['B13'].alignment = align_t

# ============================================================
# 03 TIME-TO-BREACH CALCULATION
# ============================================================
ws3 = wb.create_sheet("03_Time_to_Breach")
set_widths(ws3, [3, 42, 12, 14, 12, 14, 18])

ws3.merge_cells('B2:G2')
ws3['B2'] = "03  |  TIME-TO-BREACH CALCULATION  (Simplified Bonelli / Wan–Fell form)"
ws3['B2'].font = font_white_bold
ws3['B2'].fill = fill_title
ws3['B2'].alignment = align_c

ws3.merge_cells('B3:G3')
ws3['B3'] = "Δt ≈ ter · ln(Ru / Rd)    with    ter = 2 · ρd · L / (Ce · ρw · g · H)    and    Ce = 10^(–I)"
ws3['B3'].font = font_small
ws3['B3'].fill = fill_section

# Inputs
ws3.merge_cells('B5:E5')
ws3['B5'] = "USER INPUTS"
ws3['B5'].font = font_header
ws3['B5'].fill = fill_header
ws3['B5'].alignment = align_c

ws3['B6'] = "Parameter"
ws3['C6'] = "Symbol"
ws3['D6'] = "Value"
ws3['E6'] = "Unit"
style_header_row(ws3, 6, 2, 5)

inputs = [
    ("Erosion Rate Index (from HET or typical table)", "I", 3.0, "—"),
    ("Dry bulk density of core soil", "ρd", 1800, "kg/m³"),
    ("Length of pipe / core thickness", "L", 20.0, "m"),
    ("Reservoir head on the core (driving head)", "H", 15.0, "m"),
    ("Pipe radius at detection / start of progression", "Rd", 0.05, "m"),
    ("Ultimate / collapse radius (e.g. Hb/3)", "Ru", 3.0, "m"),
    ("Critical shear stress (optional; 0 for simplified)", "τc", 0.0, "Pa"),
    ("Water density", "ρw", 1000, "kg/m³"),
    ("Gravity", "g", 9.81, "m/s²"),
]

for i, (name, sym, val, unit) in enumerate(inputs):
    r = 7 + i
    ws3.cell(row=r, column=2, value=name).font = font_normal
    ws3.cell(row=r, column=3, value=sym).font = Font(name='Arial', bold=True, size=9)
    cell = ws3.cell(row=r, column=4, value=val)
    style_input(cell)
    ws3.cell(row=r, column=5, value=unit).font = font_normal
    for c in range(2, 6):
        ws3.cell(row=r, column=c).border = thin

# Calculated
ws3.merge_cells('B17:E17')
ws3['B17'] = "CALCULATED RESULTS"
ws3['B17'].font = font_header
ws3['B17'].fill = fill_header
ws3['B17'].alignment = align_c

ws3['B18'] = "Coefficient of soil erosion Ce = 10^(–I)"
ws3['C18'] = "Ce"
ws3['D18'] = '=10^(-D7)'
style_calc(ws3['D18'])
ws3['E18'] = "s/m"
ws3['D18'].number_format = '0.00E+00'

ws3['B19'] = "Driving pressure Δp = ρw · g · H"
ws3['C19'] = "Δp"
ws3['D19'] = '=D14*D15*D10'
style_calc(ws3['D19'])
ws3['E19'] = "Pa"

ws3['B20'] = "Characteristic time ter = 2·ρd·L / (Ce·Δp)"
ws3['C20'] = "ter"
ws3['D20'] = '=2*D8*D9/(D18*D19)'
style_calc(ws3['D20'])
ws3['E20'] = "s"
ws3['F20'] = '=D20/3600'
style_calc(ws3['F20'])
ws3['G20'] = "hours"

ws3['B21'] = "Radius ratio Ru / Rd"
ws3['C21'] = "Ru/Rd"
ws3['D21'] = '=D12/D11'
style_calc(ws3['D21'])
ws3['E21'] = "—"

ws3['B22'] = "ln(Ru / Rd)"
ws3['C22'] = "ln"
ws3['D22'] = '=LN(D21)'
style_calc(ws3['D22'])
ws3['E22'] = "—"

ws3['B23'] = "REMAINING TIME TO BREACH  Δt = ter · ln(Ru/Rd)"
ws3['C23'] = "Δt"
ws3['D23'] = '=D20*D22'
style_calc(ws3['D23'])
ws3['E23'] = "s"
ws3['F23'] = '=D23/3600'
style_calc(ws3['F23'])
ws3['G23'] = "hours"
ws3['D23'].font = Font(name='Arial', bold=True, size=12, color='000000')
ws3['F23'].font = Font(name='Arial', bold=True, size=12, color='000000')

ws3['B24'] = "Δt in minutes"
ws3['C24'] = "Δt_min"
ws3['D24'] = '=D23/60'
style_calc(ws3['D24'])
ws3['E24'] = "min"

ws3['B25'] = "Δt in days"
ws3['C25'] = "Δt_day"
ws3['D25'] = '=D23/86400'
style_calc(ws3['D25'])
ws3['E25'] = "days"

for r in range(18, 26):
    for c in range(2, 8):
        if ws3.cell(row=r, column=c).value is not None:
            ws3.cell(row=r, column=c).border = thin

# Interpretation
ws3.merge_cells('B27:G27')
ws3['B27'] = "INTERPRETATION AID"
ws3['B27'].font = font_header
ws3['B27'].fill = fill_header
ws3['B27'].alignment = align_c

ws3.merge_cells('B28:G30')
ws3['B28'] = (
    "• Δt < 1–2 hours  →  extremely rapid progression; intervention window is very short.\n"
    "• Δt of several hours  →  rapid; emergency drawdown or intervention may still be possible if detection is early.\n"
    "• Δt of days  →  slower soils; more time for surveillance and response, but still a serious failure mode.\n"
    "• Always compare with the duration of the critical loading (flood hydrograph, seismic aftershocks, etc.).\n"
    "• This Δt can be used as a rational estimate of T.Fail (or a lower-bound on it) when feeding the empirical breach hydrograph tools."
)
ws3['B28'].font = font_small
ws3['B28'].alignment = align_t
ws3['B28'].fill = fill_note

# Limitations
ws3.merge_cells('B32:G32')
ws3['B32'] = "LIMITATIONS & ASSUMPTIONS (read carefully)"
ws3['B32'].font = font_header
ws3['B32'].fill = fill_limit
ws3['B32'].alignment = align_c

ws3.merge_cells('B33:G37')
ws3['B33'] = (
    "1. Constant reservoir head (Δp constant). Falling head lengthens the real time.\n"
    "2. Cylindrical pipe of uniform radius; real pipes are irregular and may meander.\n"
    "3. Constant Ce (no self-healing, no filter action, no change of soil properties).\n"
    "4. Simplified form often neglects τc; if τc is significant relative to wall shear the process may arrest.\n"
    "5. Ru is an engineering assumption (commonly Hb/3 or a diameter at which roof collapse is judged likely).\n"
    "6. Does not replace a full event-tree internal-erosion assessment or the RMC toolboxes for initiation/continuation/progression probability.\n"
    "7. For cohesionless foundation soils the governing mechanism is usually Backward Erosion Piping (Sellmeijer / Schmertmann), not this concentrated-leak enlargement model."
)
ws3['B33'].font = font_small
ws3['B33'].alignment = align_t
ws3['B33'].fill = fill_note

# ============================================================
# 04 SENSITIVITY TABLE
# ============================================================
ws4 = wb.create_sheet("04_Sensitivity")
set_widths(ws4, [12, 12, 12, 12, 12, 12, 12, 12, 12])

ws4.merge_cells('A1:I1')
ws4['A1'] = "04  |  SENSITIVITY OF TIME-TO-BREACH TO EROSION RATE INDEX AND RADIUS RATIO"
ws4['A1'].font = font_white_bold
ws4['A1'].fill = fill_title
ws4['A1'].alignment = align_c

ws4.merge_cells('A2:I2')
ws4['A2'] = "Fixed parameters taken from Sheet 03 inputs (ρd, L, H). Vary I and Ru/Rd to see order-of-magnitude changes."
ws4['A2'].font = font_small
ws4['A2'].fill = fill_section

ws4['A4'] = "Fixed from Sheet 03:"
ws4['B4'] = "ρd ="
ws4['C4'] = "='03_Time_to_Breach'!D8"
style_calc(ws4['C4'])
ws4['D4'] = "L ="
ws4['E4'] = "='03_Time_to_Breach'!D9"
style_calc(ws4['E4'])
ws4['F4'] = "H ="
ws4['G4'] = "='03_Time_to_Breach'!D10"
style_calc(ws4['G4'])

ws4['A6'] = "Δt (hours) for different I and Ru/Rd"
ws4['A6'].font = font_section
ws4.merge_cells('A6:I6')

# Header row for Ru/Rd
ws4['A7'] = "I \\ Ru/Rd"
style_header_row(ws4, 7, 1, 1)
ratios = [10, 20, 50, 100, 200, 500, 1000]
for i, ratio in enumerate(ratios):
    cell = ws4.cell(row=7, column=2+i, value=ratio)
    cell.fill = fill_header
    cell.font = font_header
    cell.alignment = align_c
    cell.border = thin

# I values 1 to 6
for j, Ival in enumerate([1, 2, 2.5, 3, 3.5, 4, 5, 6]):
    r = 8 + j
    ws4.cell(row=r, column=1, value=Ival).font = Font(name='Arial', bold=True, size=10)
    ws4.cell(row=r, column=1).fill = fill_header
    ws4.cell(row=r, column=1).font = font_header
    ws4.cell(row=r, column=1).alignment = align_c
    ws4.cell(row=r, column=1).border = thin
    for i, ratio in enumerate(ratios):
        # Δt (hr) = [2*ρd*L / (10^(-I) * ρw*g*H)] * ln(ratio) / 3600
        # Use fixed refs
        formula = f'=(2*$C$4*$E$4/(10^(-$A{r})*1000*9.81*$G$4))*LN({ratio})/3600'
        cell = ws4.cell(row=r, column=2+i, value=formula)
        style_calc(cell)
        cell.number_format = '0.00'

ws4.merge_cells('A17:I19')
ws4['A17'] = (
    "Reading the table: each column is a different enlargement ratio (Ru/Rd). Each row is a different Erosion Rate Index. "
    "Values are in hours. Notice that a change of only 1 unit in I changes Δt by a factor of ~10. "
    "This is why laboratory determination of I (or Ce) is far more important than precise knowledge of the exact final radius."
)
ws4['A17'].font = font_small
ws4['A17'].fill = fill_note
ws4['A17'].alignment = align_t

# ============================================================
# 05 LINK TO DAM BREACH TOOL
# ============================================================
ws5 = wb.create_sheet("05_Link_to_Breach_Tool")
set_widths(ws5, [3, 50, 20, 20])

ws5.merge_cells('B2:D2')
ws5['B2'] = "HOW TO USE THIS RESULT WITH THE DAM BREACH COMPUTATIONAL TOOL"
ws5['B2'].font = font_white_bold
ws5['B2'].fill = fill_title
ws5['B2'].alignment = align_c

ws5.merge_cells('B4:D8')
ws5['B4'] = (
    "1. Compute Δt (hours or minutes) on Sheet 03 of this workbook.\n\n"
    "2. Open the Dam Breach Computational Tool v1.0 (or the original Break-1 / Break-3 sheets).\n\n"
    "3. On the Breach Characteristics or Timestep Hydrograph sheet, replace (or sensitivity-test) the "
    "empirical breach-development time t (or T.Fail) with the value of Δt obtained here.\n\n"
    "4. Re-compute peak discharge and the outflow hydrograph. The hydrograph volume is still controlled "
    "by reservoir volume + inflow; only the rising-limb timing and the attenuation factor K3 change.\n\n"
    "5. Document both the empirical Tech-Note-1 t and the erosion-rate-index Δt so that the range of "
    "possible breach timings is visible to reviewers."
)
ws5['B4'].font = font_small
ws5['B4'].alignment = align_t
ws5['B4'].fill = fill_note

ws5.merge_cells('B10:D10')
ws5['B10'] = "RECOMMENDED WORKFLOW"
ws5['B10'].font = font_header
ws5['B10'].fill = fill_header
ws5['B10'].alignment = align_c

ws5.merge_cells('B11:D14')
ws5['B11'] = (
    "Soil testing (HET/JET) → obtain I or Ce and τc\n"
    "→ this workbook → Δt (time to gross enlargement)\n"
    "→ Dam Breach Tool (Sheet 03 or 05) → set t or T.Fail = Δt\n"
    "→ obtain Qp and full hydrograph → route downstream (Sheet 07)\n"
    "→ sensitivity on I and Ru/Rd (Sheet 04 of this workbook)"
)
ws5['B11'].font = font_small
ws5['B11'].alignment = align_t
ws5['B11'].fill = fill_section

# Save
wb.save('/home/workdir/artifacts/Erosion_Rate_Index_Time_to_Breach_Tool_v1.0.xlsx')
print("Created: Erosion_Rate_Index_Time_to_Breach_Tool_v1.0.xlsx")
print("Sheets:", wb.sheetnames)