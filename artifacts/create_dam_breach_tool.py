#!/usr/bin/env python3
"""
Dam Breach Computational Tool v1.0
Professional multi-sheet workbook modeled after VAW Impulse Wave Manual Computational Tool.
Integrates Break-1/2/3/5, Flood-1, SurfArea methodologies with linked sheets,
detailed parameter definitions, limitations, and schematic representations.
"""

from openpyxl import Workbook
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, NamedStyle, Protection
)
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage
from openpyxl.chart import LineChart, Reference
from openpyxl.formatting.rule import FormulaRule, ColorScaleRule
from openpyxl.comments import Comment
from openpyxl.worksheet.datavalidation import DataValidation
import math

wb = Workbook()

# ============================================================
# STYLES
# ============================================================
thin = Border(
    left=Side(style='thin', color='B0B0B0'),
    right=Side(style='thin', color='B0B0B0'),
    top=Side(style='thin', color='B0B0B0'),
    bottom=Side(style='thin', color='B0B0B0')
)
thick = Border(
    left=Side(style='medium', color='1F4E79'),
    right=Side(style='medium', color='1F4E79'),
    top=Side(style='medium', color='1F4E79'),
    bottom=Side(style='medium', color='1F4E79')
)

# Colors matching Impulse Wave style + engineering standards
fill_header = PatternFill('solid', fgColor='1F4E79')      # Dark blue header
fill_subheader = PatternFill('solid', fgColor='2E75B6')   # Medium blue
fill_section = PatternFill('solid', fgColor='D6EAF8')     # Light blue section
fill_input = PatternFill('solid', fgColor='FFF2CC')       # Yellow = user input
fill_calc = PatternFill('solid', fgColor='E2EFDA')        # Light green = calculated
fill_link = PatternFill('solid', fgColor='DDEBF7')        # Light blue = linked from other sheet
fill_limit = PatternFill('solid', fgColor='FCE4D6')       # Orange = limitations
fill_within = PatternFill('solid', fgColor='C6EFCE')      # Green = within limits
fill_outside = PatternFill('solid', fgColor='FFC7CE')     # Red = outside limits
fill_white = PatternFill('solid', fgColor='FFFFFF')
fill_gray = PatternFill('solid', fgColor='F2F2F2')
fill_title = PatternFill('solid', fgColor='0D3B66')
fill_note = PatternFill('solid', fgColor='FFF8E7')

font_white_bold = Font(name='Arial', bold=True, color='FFFFFF', size=12)
font_white = Font(name='Arial', color='FFFFFF', size=10)
font_header = Font(name='Arial', bold=True, color='FFFFFF', size=11)
font_title = Font(name='Arial', bold=True, color='1F4E79', size=16)
font_subtitle = Font(name='Arial', bold=True, color='1F4E79', size=13)
font_section = Font(name='Arial', bold=True, color='1F4E79', size=11)
font_normal = Font(name='Arial', size=10)
font_input = Font(name='Arial', size=10, color='0000FF')   # Blue text for inputs
font_calc = Font(name='Arial', size=10, color='000000')    # Black for formulas
font_link = Font(name='Arial', size=10, color='008000')    # Green for cross-sheet links
font_small = Font(name='Arial', size=9)
font_tiny = Font(name='Arial', size=8, italic=True)
font_eq = Font(name='Consolas', size=9)

align_c = Alignment(horizontal='center', vertical='center', wrap_text=True)
align_l = Alignment(horizontal='left', vertical='center', wrap_text=True)
align_r = Alignment(horizontal='right', vertical='center')

def style_header_row(ws, row, start_col, end_col, fill=fill_header):
    for col in range(start_col, end_col + 1):
        cell = ws.cell(row=row, column=col)
        cell.fill = fill
        cell.font = font_header
        cell.alignment = align_c
        cell.border = thin

def style_input_cell(cell):
    cell.fill = fill_input
    cell.font = font_input
    cell.alignment = align_c
    cell.border = thin

def style_calc_cell(cell):
    cell.fill = fill_calc
    cell.font = font_calc
    cell.alignment = align_c
    cell.border = thin

def style_link_cell(cell):
    cell.fill = fill_link
    cell.font = font_link
    cell.alignment = align_c
    cell.border = thin

def set_col_widths(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

def add_comment(cell, text, author="Dam Breach Tool"):
    cell.comment = Comment(text, author, width=300, height=80)

# ============================================================
# SHEET 0: COVER / INDEX
# ============================================================
ws = wb.active
ws.title = "00_Cover"

set_col_widths(ws, [4, 35, 45, 25, 20, 20, 15])

ws.merge_cells('B2:F2')
ws['B2'] = "DAM BREACH COMPUTATIONAL TOOL"
ws['B2'].font = Font(name='Arial', bold=True, color='FFFFFF', size=22)
ws['B2'].fill = fill_title
ws['B2'].alignment = align_c

ws.merge_cells('B3:F3')
ws['B3'] = "Earthfill Dam Breach Characteristics, Hydrographs & Downstream Flood Routing"
ws['B3'].font = Font(name='Arial', bold=True, color='FFFFFF', size=12)
ws['B3'].fill = fill_header
ws['B3'].alignment = align_c

ws.merge_cells('B4:F4')
ws['B4'] = "Version 1.0  |  Metric Units  |  Based on Washington State Dam Safety Technical Note 1 (2007) & related methodologies"
ws['B4'].font = font_white
ws['B4'].fill = fill_subheader
ws['B4'].alignment = align_c

ws.merge_cells('B6:F6')
ws['B6'] = "PROJECT INFORMATION"
ws['B6'].font = font_header
ws['B6'].fill = fill_header
ws['B6'].alignment = align_c

ws['B7'] = "Dam Name / Owner:"
ws['C7'] = ""
style_input_cell(ws['C7'])
ws['D7'] = "Dam Safety File No.:"
ws['E7'] = ""
style_input_cell(ws['E7'])

ws['B8'] = "Prepared by:"
ws['C8'] = ""
style_input_cell(ws['C8'])
ws['D8'] = "Date:"
ws['E8'] = ""
style_input_cell(ws['E8'])

ws['B9'] = "Checked by:"
ws['C9'] = ""
style_input_cell(ws['C9'])
ws['D9'] = "Revision:"
ws['E9'] = "1.0"
style_input_cell(ws['E9'])

ws.merge_cells('B11:F11')
ws['B11'] = "MODULE INDEX & WORKFLOW"
ws['B11'].font = font_header
ws['B11'].fill = fill_header
ws['B11'].alignment = align_c

headers = ["Sheet", "Module", "Description", "Primary Inputs", "Key Outputs"]
for i, h in enumerate(headers, 2):
    ws.cell(row=12, column=i, value=h)
style_header_row(ws, 12, 2, 6)

modules = [
    ("01_Parameter_Definitions", "Parameter Catalogue & Schematics",
     "Detailed definitions, units, typical ranges, governing equations and schematic diagrams for every parameter used in the tool.",
     "—", "Reference only"),
    ("02_Reservoir_Stage_Storage", "Reservoir Geometry (SurfArea)",
     "Stage–surface area–storage relationship. Calibrates power-function approximation from known pool data.",
     "Normal pool y, A, V; crest elev.", "Stage-Storage table, Ao, k, m"),
    ("03_Breach_Characteristics", "Breach Geometry & Peak Discharge (Break-1)",
     "Breach Formation Factor method for cohesionless/resistant materials. Piping and Overtopping scenarios.",
     "Hb, Hw, Vw, Sa, C, Z1, Z2, Zb, erosion factors", "Wb, Wavg, Wcr, t, Qp (mod. weir & Froehlich)"),
    ("04_Constrained_Breach", "Width-Constrained Breach (Break-2)",
     "When physical setting or crest length limits breach width. User specifies Wb within upper-limit Vm.",
     "Wb (user), Hb, Hw, Vw, Sa, Zb", "Vm check, Wavg, t, Qp"),
    ("05_Timestep_Hydrograph", "Time-Step Breach Hydrograph (Break-3)",
     "HEC-1 style progressive breach development. Computes full outflow hydrograph by time stepping.",
     "Wb, T.Fail, Zb, stage-storage, Qin", "Full Q(t) hydrograph, Qp, T.Peak, T.Base"),
    ("06_Dimensionless_Hydrograph", "Dimensionless Hydrograph (Break-5)",
     "Haan et al. dimensionless hydrograph scaled to reservoir volume + inflow. Suitable for larger reservoirs.",
     "Q.Peak, T.Peak, Vol, K", "Full dimensionless Q(t) table"),
    ("07_Downstream_Flood", "Flood Attenuation & Travel Time (Flood-1)",
     "Hydraulic profile of valley, peak attenuation estimation, flood-wave travel time window.",
     "Qp, valley profile, channel type", "Qx/Qp, Qx, Vw, travel time min/max"),
]

for i, (sheet, mod, desc, inp, out) in enumerate(modules):
    r = 13 + i
    ws.cell(row=r, column=2, value=sheet).font = Font(name='Arial', bold=True, size=9, color='1F4E79')
    ws.cell(row=r, column=3, value=mod).font = font_normal
    ws.cell(row=r, column=4, value=desc).font = font_small
    ws.cell(row=r, column=5, value=inp).font = font_small
    ws.cell(row=r, column=6, value=out).font = font_small
    for c in range(2, 7):
        ws.cell(row=r, column=c).border = thin
        ws.cell(row=r, column=c).alignment = align_l
        if i % 2 == 0:
            ws.cell(row=r, column=c).fill = fill_gray

ws.merge_cells('B21:F21')
ws['B21'] = "COLOUR CODING (consistent with Impulse Wave Tool convention)"
ws['B21'].font = font_header
ws['B21'].fill = fill_header
ws['B21'].alignment = align_c

ws['B22'] = "Colour"
ws['C22'] = "Meaning"
ws['D22'] = "Usage"
style_header_row(ws, 22, 2, 4)

colour_rows = [
    (fill_input, "Yellow background + Blue text", "User input required – enter value here"),
    (fill_calc, "Light green background + Black text", "Calculated result (formula driven)"),
    (fill_link, "Light blue background + Green text", "Value linked from another sheet"),
    (fill_within, "Green background", "Parameter within validated limitation range"),
    (fill_outside, "Red / pink background", "Parameter outside validated limitation range – caution"),
    (fill_limit, "Orange background", "Limitation / applicability range table"),
    (fill_section, "Light blue section header", "Section divider"),
]

for i, (fill, meaning, usage) in enumerate(colour_rows):
    r = 23 + i
    ws.cell(row=r, column=2).fill = fill
    ws.cell(row=r, column=2).border = thin
    ws.cell(row=r, column=3, value=meaning).font = font_small
    ws.cell(row=r, column=3).border = thin
    ws.cell(row=r, column=4, value=usage).font = font_small
    ws.cell(row=r, column=4).border = thin

ws.merge_cells('B31:F31')
ws['B31'] = "IMPORTANT NOTES & DISCLAIMER"
ws['B31'].font = font_header
ws['B31'].fill = fill_header
ws['B31'].alignment = align_c

notes = [
    "1. This workbook is intended for use by Professional Engineers only, or by junior engineers under the supervision of a Professional Engineer.",
    "2. Engineers using this spreadsheet must ensure that the calculations are correctly applied to their specific project. Dam owners and design engineers retain full responsibility for the safety of their structures.",
    "3. Methodology follows Washington State Department of Ecology Dam Safety Office Technical Note 1 (2007) and related guidance (Break-1/2/3/5, Flood-1, SurfArea).",
    "4. Always verify that input parameters lie within the stated limitation ranges. Extrapolation outside validated ranges requires engineering judgement and additional verification.",
    "5. Cross-sheet links are shown in green text on light-blue background. Changing an upstream input automatically updates downstream calculations after recalculation.",
    "6. Schematics on sheet 01 illustrate the geometric meaning of every parameter appearing in the governing equations.",
    "7. All calculations are in metric (SI) units unless otherwise noted. Conversion factors are provided where legacy US-unit equations are used internally.",
]

for i, note in enumerate(notes):
    r = 32 + i
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
    ws.cell(row=r, column=2, value=note).font = font_small
    ws.cell(row=r, column=2).alignment = align_l
    ws.cell(row=r, column=2).fill = fill_note

ws.row_dimensions[2].height = 30
ws.row_dimensions[3].height = 20
for r in range(13, 20):
    ws.row_dimensions[r].height = 45

# ============================================================
# SHEET 1: PARAMETER DEFINITIONS & SCHEMATICS
# ============================================================
ws1 = wb.create_sheet("01_Parameter_Definitions")

set_col_widths(ws1, [4, 18, 12, 12, 55, 45, 30])

ws1.merge_cells('B2:G2')
ws1['B2'] = "PARAMETER DEFINITIONS, UNITS, RANGES & SCHEMATIC REPRESENTATIONS"
ws1['B2'].font = Font(name='Arial', bold=True, color='FFFFFF', size=14)
ws1['B2'].fill = fill_title
ws1['B2'].alignment = align_c

ws1.merge_cells('B3:G3')
ws1['B3'] = "Every parameter used in the governing equations is defined below. Schematics show geometric meaning relative to the dam and reservoir."
ws1['B3'].font = font_small
ws1['B3'].fill = fill_section
ws1['B3'].alignment = align_l

# --- Section A: Reservoir & Water Parameters ---
ws1.merge_cells('B5:G5')
ws1['B5'] = "A. RESERVOIR & WATER SURFACE PARAMETERS"
ws1['B5'].font = font_header
ws1['B5'].fill = fill_header
ws1['B5'].alignment = align_c

headers1 = ["Symbol", "Unit", "Typical Range", "Definition / Physical Meaning", "Appears in Equation(s)", "Schematic Note"]
for i, h in enumerate(headers1, 2):
    ws1.cell(row=6, column=i, value=h)
style_header_row(ws1, 6, 2, 7)

params_A = [
    ("y", "m", "0 – Hb", "Water depth above reservoir base elevation at a given stage. Used to define stage-storage curve.", "V = Ao·y + k·y^m ; A = Ao + m·k·y^(m-1)", "Vertical distance from base to WL"),
    ("WL", "m", "—", "Water surface elevation (absolute). WL = base elev. + y.", "Head H = WL – BL", "Horizontal free surface line"),
    ("Vw / Vol", "m³", "project specific", "Volume of water in reservoir at the time of breach initiation (or volume to be released).", "BFF = Vw · Hw ; T.Base = 2·(Vw+Qin)/Qp", "Area under stage-storage curve up to Hw"),
    ("Sa / A", "ha or m²", "project specific", "Reservoir surface area at the water surface elevation corresponding to Hw (or current WL).", "A = 23.4·Sa / Wavg (US units internal); dWL = dVol / Sa", "Plan-view water surface area"),
    ("Qin", "m³/s", "≥ 0", "Average inflow rate into the reservoir during the breach development period.", "Vol.Inflow = Qin · t ; hydrograph volume balance", "Arrow into reservoir from upstream"),
    ("f", "m", "≥ 0", "Freeboard = dam crest elevation – water surface elevation (positive when WL below crest).", "Used in overtopping initiation checks", "Vertical distance crest → WL"),
]

for i, (sym, unit, rng, defin, eq, note) in enumerate(params_A):
    r = 7 + i
    ws1.cell(row=r, column=2, value=sym).font = Font(name='Arial', bold=True, size=10)
    ws1.cell(row=r, column=3, value=unit).font = font_normal
    ws1.cell(row=r, column=4, value=rng).font = font_small
    ws1.cell(row=r, column=5, value=defin).font = font_small
    ws1.cell(row=r, column=6, value=eq).font = font_eq
    ws1.cell(row=r, column=7, value=note).font = font_tiny
    for c in range(2, 8):
        ws1.cell(row=r, column=c).border = thin
        ws1.cell(row=r, column=c).alignment = align_l
        if i % 2 == 0:
            ws1.cell(row=r, column=c).fill = fill_gray

# --- Section B: Dam Geometry ---
ws1.merge_cells('B14:G14')
ws1['B14'] = "B. DAM GEOMETRY PARAMETERS"
ws1['B14'].font = font_header
ws1['B14'].fill = fill_header
ws1['B14'].alignment = align_c

for i, h in enumerate(headers1, 2):
    ws1.cell(row=15, column=i, value=h)
style_header_row(ws1, 15, 2, 7)

params_B = [
    ("Hb", "m", "project specific", "Height (depth) of breach = Dam crest elevation – Breach base elevation (BL). Full structural height if breach reaches foundation.", "K1 = Hb·[C + (Hb·Z3)/2] ; K2 = Hb²·[(C·Zb)+(Hb·Zb·Z3)/3]", "Vertical distance crest → breach invert"),
    ("Hw", "m", "≤ Hb", "Height of water above breach base elevation at failure. For overtopping Hw ≈ Hb; for piping Hw < Hb.", "BFF = Vw · Hw ; Qp ∝ Hw^1.5 or Hw^1.24", "Vertical distance WL → breach invert"),
    ("C", "m", "typically 3–10 m", "Crest width of the dam (horizontal distance between upstream and downstream crest edges).", "K1, K2 volume integrals", "Horizontal top width of dam section"),
    ("Z1", "H:1V", "typically 2–4", "Slope of upstream face of dam (horizontal:vertical).", "Z3 = Z1 + Z2", "Upstream embankment slope"),
    ("Z2", "H:1V", "typically 2–3", "Slope of downstream face of dam (horizontal:vertical).", "Z3 = Z1 + Z2", "Downstream embankment slope"),
    ("Z3", "H:1V", "Z1+Z2", "Sum of upstream and downstream face slopes. Used in eroded-volume calculation.", "K1, K2", "Combined face slope factor"),
    ("Crest Length", "m", "project specific", "Total length of dam crest (across the valley). Used to compute % of crest breached.", "Breach % = Wcr / Crest Length × 100", "Plan length of dam"),
    ("BL", "m", "usually 0 (foundation)", "Breach base (invert) elevation. Usually set at foundation or selected piping elevation.", "H = WL – BL ; Db = Crest – BL", "Horizontal line at breach invert"),
]

for i, (sym, unit, rng, defin, eq, note) in enumerate(params_B):
    r = 16 + i
    ws1.cell(row=r, column=2, value=sym).font = Font(name='Arial', bold=True, size=10)
    ws1.cell(row=r, column=3, value=unit).font = font_normal
    ws1.cell(row=r, column=4, value=rng).font = font_small
    ws1.cell(row=r, column=5, value=defin).font = font_small
    ws1.cell(row=r, column=6, value=eq).font = font_eq
    ws1.cell(row=r, column=7, value=note).font = font_tiny
    for c in range(2, 8):
        ws1.cell(row=r, column=c).border = thin
        ws1.cell(row=r, column=c).alignment = align_l
        if i % 2 == 0:
            ws1.cell(row=r, column=c).fill = fill_gray

# --- Section C: Breach Geometry ---
ws1.merge_cells('B25:G25')
ws1['B25'] = "C. BREACH GEOMETRY PARAMETERS (see Schematic on right / below)"
ws1['B25'].font = font_header
ws1['B25'].fill = fill_header
ws1['B25'].alignment = align_c

for i, h in enumerate(headers1, 2):
    ws1.cell(row=26, column=i, value=h)
style_header_row(ws1, 26, 2, 7)

params_C = [
    ("Wb", "m", "0.5–3 × Hb typical", "Base (bottom) width of the trapezoidal breach. Calculated from eroded volume or user-specified when constrained.", "27·Vm = Wb·K1 + K2 ; Wavg = Wb + Zb·Hw", "Bottom width of breach opening"),
    ("Wavg", "m", "—", "Average width of flow through the breach (at the water surface during peak).", "Qp = 3.1 · Wavg · Hw^1.5 · K3³ (US units)", "Width at mid-depth of flow"),
    ("Wtop", "m", "—", "Top width of the flowing water surface inside the breach.", "Wtop = Wb + 2·Zb·Hw", "Water-surface width in breach"),
    ("Wcr", "m", "—", "Top width of the breach at dam crest level.", "Wcr = Wb + 2·Zb·Hb", "Crest-level breach width"),
    ("Zb", "H:1V", "0.25–1.0 typical", "Side slope of the breach (horizontal:vertical). Cohesionless ≈ 0.5–1; resistant ≈ 0.25–0.5.", "All width & volume equations", "Batter of breach sidewalls"),
    ("Vm", "m³ or yd³", "from BFF", "Volume of dam material eroded to form the final breach. Function of BFF and material type.", "Vm = 3.75·BFF^0.77 (cohesionless, US) or 2.50·BFF^0.77 (resistant)", "Eroded embankment prism"),
    ("BFF", "— (US units)", "—", "Breach Formation Factor = Vw · Hw (both in US customary units for the regression).", "Vm = f(BFF)", "Product of volume and head"),
    ("t / T.Fail", "hr or min", "0.1–4 hr typical", "Time for full breach development (from initiation to final geometry).", "t = 0.020·Vm^0.36 (cohesionless) or 0.036·Vm^0.36 (resistant)", "Duration of progressive erosion"),
]

for i, (sym, unit, rng, defin, eq, note) in enumerate(params_C):
    r = 27 + i
    ws1.cell(row=r, column=2, value=sym).font = Font(name='Arial', bold=True, size=10)
    ws1.cell(row=r, column=3, value=unit).font = font_normal
    ws1.cell(row=r, column=4, value=rng).font = font_small
    ws1.cell(row=r, column=5, value=defin).font = font_small
    ws1.cell(row=r, column=6, value=eq).font = font_eq
    ws1.cell(row=r, column=7, value=note).font = font_tiny
    for c in range(2, 8):
        ws1.cell(row=r, column=c).border = thin
        ws1.cell(row=r, column=c).alignment = align_l
        if i % 2 == 0:
            ws1.cell(row=r, column=c).fill = fill_gray

# --- Section D: Discharge & Hydrograph ---
ws1.merge_cells('B36:G36')
ws1['B36'] = "D. DISCHARGE, HYDROGRAPH & ROUTING PARAMETERS"
ws1['B36'].font = font_header
ws1['B36'].fill = fill_header
ws1['B36'].alignment = align_c

for i, h in enumerate(headers1, 2):
    ws1.cell(row=37, column=i, value=h)
style_header_row(ws1, 37, 2, 7)

params_D = [
    ("Qp", "m³/s", "project specific", "Peak breach outflow discharge. Computed by modified weir equation or Froehlich regression.", "Qp = 3.1·Wavg·Hw^1.5·K3³ ; Qp = 40.1·Vw^0.295·Hw^1.24 (US)", "Maximum of outflow hydrograph"),
    ("K3", "—", "0–1", "Storage attenuation factor for the modified weir equation. Accounts for reservoir drawdown during breach formation.", "K3 = A / (A + t·√Hw)", "Reduction factor on weir discharge"),
    ("T.Peak", "hr", "≈ t or from timestep", "Time from breach initiation to peak discharge.", "Used to construct triangular or dimensionless hydrograph", "Time coordinate of Qp"),
    ("T.Base", "hr", "—", "Total duration of the outflow hydrograph (time to empty reservoir + inflows).", "T.Base = 2·(Vw + Vol.Inflow) / Qp", "Base of triangular hydrograph"),
    ("K (dimless)", "—", "1.5–5.0 typical", "Shape factor for the dimensionless hydrograph of Haan et al.", "Q(t)/Qp = [ (t/Tp)·exp(1 – t/Tp) ]^K", "Controls hydrograph peakedness"),
    ("Qx", "m³/s", "≤ Qp", "Attenuated peak discharge at a downstream distance x.", "Qx/Qp from attenuation curves or engineering judgement", "Peak at downstream station"),
    ("Vw (wave)", "m/s", "≈ 1.0–1.5 × V", "Flood-wave celerity (propagation speed of the breach flood wave).", "Travel time = distance / Vw", "Speed of flood front"),
]

for i, (sym, unit, rng, defin, eq, note) in enumerate(params_D):
    r = 38 + i
    ws1.cell(row=r, column=2, value=sym).font = Font(name='Arial', bold=True, size=10)
    ws1.cell(row=r, column=3, value=unit).font = font_normal
    ws1.cell(row=r, column=4, value=rng).font = font_small
    ws1.cell(row=r, column=5, value=defin).font = font_small
    ws1.cell(row=r, column=6, value=eq).font = font_eq
    ws1.cell(row=r, column=7, value=note).font = font_tiny
    for c in range(2, 8):
        ws1.cell(row=r, column=c).border = thin
        ws1.cell(row=r, column=c).alignment = align_l
        if i % 2 == 0:
            ws1.cell(row=r, column=c).fill = fill_gray

# --- SCHEMATIC SECTION (text-based high-quality diagrams) ---
ws1.merge_cells('B46:G46')
ws1['B46'] = "E. SCHEMATIC DIAGRAMS OF KEY PARAMETERS (textual representation of geometry used in equations)"
ws1['B46'].font = font_header
ws1['B46'].fill = fill_header
ws1['B46'].alignment = align_c

# Dam cross-section schematic
ws1.merge_cells('B48:D48')
ws1['B48'] = "FIGURE E-1  —  Dam Cross-Section & Breach Geometry Parameters"
ws1['B48'].font = font_section
ws1['B48'].fill = fill_section

schematic1 = """
                    Dam Crest (elev. = Crest)
         <---------------- C ---------------->
         |                                    |
    Z1   |                                    |   Z2
   (H:1V)|                                    |  (H:1V)
         \\                                  /
          \\          BREACH                /
           \\    <--- Wcr at crest --->    /
            \\  /                      \\  /
             \\/     Wtop (at WL)       \\/
              |<-Wb->|                  |
              |      |                  |
         BL --+------+------------------+----  Breach Base Elevation (BL)
              |      |
              <------>
                Wb = base width of breach

    Vertical dimensions:
      Hb = Crest elev. – BL
      Hw = WL elev. – BL          (Hw ≤ Hb)
      Freeboard f = Crest – WL    (if positive)

    Side slopes of breach: Zb (H:1V) on both sides
    Z3 = Z1 + Z2
"""
ws1.merge_cells('B49:D62')
ws1['B49'] = schematic1
ws1['B49'].font = Font(name='Consolas', size=8)
ws1['B49'].alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
ws1['B49'].fill = fill_gray
ws1['B49'].border = thin

# Plan view / volume schematic
ws1.merge_cells('E48:G48')
ws1['E48'] = "FIGURE E-2  —  Breach Formation Factor & Eroded Volume Concept"
ws1['E48'].font = font_section
ws1['E48'].fill = fill_section

schematic2 = """
  Reservoir volume Vw (at Hw)
  ===========================
  |                         |
  |     Water surface       |  Hw
  |                         |
  +-------------------------+  Breach invert (BL)
           Dam body
  ===========================
         Eroded volume Vm
         (shaded prism)

  BFF = Vw × Hw          (US customary units for regression)

  Vm = 3.75 × BFF^0.77   (cohesionless / erodible)
  Vm = 2.50 × BFF^0.77   (erosion-resistant)

  Volume identity (metric conversion applied):
  27·Vm = Wb·K1 + K2

  where
  K1 = Hb · [C + (Hb·Z3)/2]
  K2 = Hb² · [(C·Zb) + (Hb·Zb·Z3)/3]
"""
ws1.merge_cells('E49:G62')
ws1['E49'] = schematic2
ws1['E49'].font = Font(name='Consolas', size=8)
ws1['E49'].alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
ws1['E49'].fill = fill_gray
ws1['E49'].border = thin

# Hydrograph schematic
ws1.merge_cells('B64:D64')
ws1['B64'] = "FIGURE E-3  —  Triangular & Dimensionless Hydrograph Parameters"
ws1['B64'].font = font_section
ws1['B64'].fill = fill_section

schematic3 = """
  Q
  |           Qp
  |          /\\
  |         /  \\
  |        /    \\
  |       /      \\
  |      /        \\
  |     /          \\
  |    /            \\
  +---+------+-------+---- t
      0   T.Peak  T.Base

  Triangular hydrograph volume balance:
  (Vw + Vol.Inflow) = (1/2) · Qp · T.Base
  ⇒  T.Base = 2·(Vw + Vol.Inflow) / Qp

  Dimensionless form (Haan et al.):
  Q(t)/Qp = [ (t/T.Peak) · exp(1 – t/T.Peak) ] ^ K

  K ≈ 6.5 · [(Qp·T.Peak)/Vol ]^1.92
  (then adjusted so integrated volume matches)
"""
ws1.merge_cells('B65:D78')
ws1['B65'] = schematic3
ws1['B65'].font = Font(name='Consolas', size=8)
ws1['B65'].alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
ws1['B65'].fill = fill_gray
ws1['B65'].border = thin

# Downstream routing schematic
ws1.merge_cells('E64:G64')
ws1['E64'] = "FIGURE E-4  —  Downstream Valley Profile & Flood Wave Travel"
ws1['E64'].font = font_section
ws1['E64'].fill = fill_section

schematic4 = """
  Elevation
  |
  |  Dam
  |  /\\
  | /  \\________     Valley profile
  |/          \\    /
  +------------\\--/------------ Distance from dam
  0            x1  x2         x_end

  At each station x:
    Channel gradient S = ΔElev / Δx
    Flow velocity V estimated from S & channel type
    Flood-wave celerity Vw ≈ (1.0 – 1.5) × V

  Travel time window (min → max):
    t_min = Σ (Δx / Vw_max)
    t_max = Σ (Δx / Vw_min)

  Peak attenuation:
    Qx / Qp  from attenuation curves
    (function of distance and reservoir volume)
"""
ws1.merge_cells('E65:G78')
ws1['E65'] = schematic4
ws1['E65'].font = Font(name='Consolas', size=8)
ws1['E65'].alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
ws1['E65'].fill = fill_gray
ws1['E65'].border = thin

ws1.row_dimensions[49].height = 200
ws1.row_dimensions[65].height = 200

# ============================================================
# SHEET 2: RESERVOIR STAGE-STORAGE
# ============================================================
ws2 = wb.create_sheet("02_Reservoir_Stage_Storage")

set_col_widths(ws2, [4, 22, 14, 14, 14, 14, 14, 14, 18, 18])

ws2.merge_cells('B2:I2')
ws2['B2'] = "02  |  RESERVOIR STAGE – SURFACE AREA – STORAGE RELATIONSHIP"
ws2['B2'].font = Font(name='Arial', bold=True, color='FFFFFF', size=14)
ws2['B2'].fill = fill_title
ws2['B2'].alignment = align_c

ws2.merge_cells('B3:I3')
ws2['B3'] = "Power-function approximation:  V = Ao·y + k·y^m    ;    A = Ao + m·k·y^(m-1)     |     Calibrated from known (y, A, V) at normal pool"
ws2['B3'].font = font_small
ws2['B3'].fill = fill_section

# Inputs
ws2.merge_cells('B5:E5')
ws2['B5'] = "GOVERNING INPUTS (user entry)"
ws2['B5'].font = font_header
ws2['B5'].fill = fill_header
ws2['B5'].alignment = align_c

ws2['B6'] = "Parameter"
ws2['C6'] = "Symbol"
ws2['D6'] = "Value"
ws2['E6'] = "Unit"
style_header_row(ws2, 6, 2, 5)

inputs_ss = [
    ("Normal pool depth", "y_np", 3.0, "m"),
    ("Surface area at normal pool", "A_np", 0.7, "ha"),
    ("Storage volume at normal pool", "V_np", 10500, "m³"),
    ("Reservoir base elevation", "Base", 0.0, "m"),
    ("Dam crest elevation", "Crest", 3.5, "m"),
    ("Stage increment for table", "Δy", 0.1, "m"),
    ("Power exponent (m > yA/V)", "m", 2.0, "—"),
]

for i, (name, sym, val, unit) in enumerate(inputs_ss):
    r = 7 + i
    ws2.cell(row=r, column=2, value=name).font = font_normal
    ws2.cell(row=r, column=3, value=sym).font = Font(name='Arial', bold=True, size=10)
    cell = ws2.cell(row=r, column=4, value=val)
    style_input_cell(cell)
    ws2.cell(row=r, column=5, value=unit).font = font_normal
    for c in range(2, 6):
        ws2.cell(row=r, column=c).border = thin

# Calculated coefficients
ws2.merge_cells('B15:E15')
ws2['B15'] = "CALCULATED COEFFICIENTS"
ws2['B15'].font = font_header
ws2['B15'].fill = fill_header
ws2['B15'].alignment = align_c

ws2['B16'] = "Coefficient"
ws2['C16'] = "Symbol"
ws2['D16'] = "Value"
ws2['E16'] = "Unit / Note"
style_header_row(ws2, 16, 2, 5)

ws2['B17'] = "Shape coefficient"
ws2['C17'] = "k"
ws2['D17'] = '=(D8*D7-D9)/((D13-1)*D7^D13)'  # k = (A*y - V)/((m-1)*y^m)
style_calc_cell(ws2['D17'])
ws2['E17'] = "ha / m^(m-1)  (A in ha)"
ws2['E17'].font = font_tiny

ws2['B18'] = "Base area coefficient"
ws2['C18'] = "Ao"
ws2['D18'] = '=(D9/D7)*(D13/(D13-1)) - D8*((D13/(D13-1))-1)'
style_calc_cell(ws2['D18'])
ws2['E18'] = "ha"
ws2['E18'].font = font_tiny

ws2['B19'] = "Check: m > y·A/V ?"
ws2['C19'] = "yA/V"
ws2['D19'] = '=D7*D8/D9'
style_calc_cell(ws2['D19'])
ws2['E19'] = "must be < m"
ws2['E19'].font = font_tiny

for r in range(17, 20):
    for c in range(2, 6):
        ws2.cell(row=r, column=c).border = thin

# Limitations
ws2.merge_cells('G5:I5')
ws2['G5'] = "LIMITATIONS / GUIDANCE"
ws2['G5'].font = font_header
ws2['G5'].fill = fill_limit
ws2['G5'].alignment = align_c

ws2.merge_cells('G6:I12')
ws2['G6'] = (
    "• Typically 2 < m < 3 for natural reservoirs.\n"
    "• For Ao > 0 require m > (y·A / V) > 2.\n"
    "• If detailed survey data exist, replace the power-function table with surveyed stage-storage values.\n"
    "• Surface area A must be in hectares when volume is in m³ for the coefficient formulas shown (consistent internal unit handling).\n"
    "• Crest elevation defines the upper limit of the generated table."
)
ws2['G6'].font = font_small
ws2['G6'].alignment = Alignment(wrap_text=True, vertical='top')
ws2['G6'].fill = fill_note
ws2['G6'].border = thin

# Stage-Storage Table
ws2.merge_cells('B21:F21')
ws2['B21'] = "STAGE – SURFACE AREA – STORAGE TABLE  (auto-generated from coefficients)"
ws2['B21'].font = font_header
ws2['B21'].fill = fill_header
ws2['B21'].alignment = align_c

headers_ss = ["Stage y (m)", "Elevation (m)", "Surface Area A (ha)", "Cum. Volume V (m³)", "Notes"]
for i, h in enumerate(headers_ss, 2):
    ws2.cell(row=22, column=i, value=h)
style_header_row(ws2, 22, 2, 6)

# Generate rows for y = 0 to crest (assume crest-base = 3.5 → 36 rows of 0.1)
# We use formulas that reference the input cells
for i in range(0, 36):
    r = 23 + i
    # y
    if i == 0:
        ws2.cell(row=r, column=2, value=0.0)
    else:
        ws2.cell(row=r, column=2, value=f'=B{r-1}+$D$12')
    style_calc_cell(ws2.cell(row=r, column=2))
    # Elevation = Base + y
    ws2.cell(row=r, column=3, value=f'=$D$10+B{r}')
    style_calc_cell(ws2.cell(row=r, column=3))
    # A = Ao + m*k*y^(m-1)
    ws2.cell(row=r, column=4, value=f'=$D$18+$D$13*$D$17*B{r}^($D$13-1)')
    style_calc_cell(ws2.cell(row=r, column=4))
    # V = Ao*y + k*y^m
    ws2.cell(row=r, column=5, value=f'=$D$18*B{r}+$D$17*B{r}^$D$13')
    style_calc_cell(ws2.cell(row=r, column=5))
    # Note
    if i == 0:
        ws2.cell(row=r, column=6, value="Base")
    else:
        ws2.cell(row=r, column=6, value=f'=IF(C{r}>=$D$11,"Crest or above","")')
    ws2.cell(row=r, column=6).font = font_tiny
    for c in range(2, 7):
        ws2.cell(row=r, column=c).border = thin

# Key output cells for linking
ws2['B60'] = "KEY OUTPUTS FOR LINKING TO OTHER SHEETS"
ws2['B60'].font = font_header
ws2['B60'].fill = fill_header
ws2.merge_cells('B60:E60')

ws2['B61'] = "Volume at crest (approx)"
ws2['C61'] = '=INDEX(E23:E58,MATCH($D$11,C23:C58,1))'
style_link_cell(ws2['C61'])
ws2['D61'] = "m³"

ws2['B62'] = "Surface area at crest"
ws2['C62'] = '=INDEX(D23:D58,MATCH($D$11,C23:C58,1))'
style_link_cell(ws2['C62'])
ws2['D62'] = "ha"

ws2['B63'] = "Volume at normal pool (input)"
ws2['C63'] = '=D9'
style_link_cell(ws2['C63'])
ws2['D63'] = "m³"

ws2['B64'] = "Sa at normal pool (input)"
ws2['C64'] = '=D8'
style_link_cell(ws2['C64'])
ws2['D64'] = "ha"

# ============================================================
# SHEET 3: BREACH CHARACTERISTICS (Break-1 style)
# ============================================================
ws3 = wb.create_sheet("03_Breach_Characteristics")

set_col_widths(ws3, [3, 38, 12, 14, 12, 14, 14, 14, 14, 14, 18])

ws3.merge_cells('B2:J2')
ws3['B2'] = "03  |  BREACH GEOMETRY & PEAK DISCHARGE  (Break Formation Factor Method – Tech Note 1)"
ws3['B2'].font = Font(name='Arial', bold=True, color='FFFFFF', size=13)
ws3['B2'].fill = fill_title
ws3['B2'].alignment = align_c

ws3.merge_cells('B3:J3')
ws3['B3'] = "Two scenarios: (1) Piping failure at normal / spillway pool   (2) Overtopping failure at dam crest / PMP pool.  All core equations shown."
ws3['B3'].font = font_small
ws3['B3'].fill = fill_section

# --- Common Geometry Inputs ---
ws3.merge_cells('B5:E5')
ws3['B5'] = "COMMON DAM GEOMETRY (shared by both scenarios)"
ws3['B5'].font = font_header
ws3['B5'].fill = fill_header
ws3['B5'].alignment = align_c

ws3['B6'] = "Parameter"
ws3['C6'] = "Symbol"
ws3['D6'] = "Value"
ws3['E6'] = "Unit"
style_header_row(ws3, 6, 2, 5)

geom = [
    ("Dam crest elevation", "Crest", 3.5, "m"),
    ("Breach base elevation", "BL", 0.0, "m"),
    ("Crest width", "C", 3.0, "m"),
    ("Crest length", "Lcrest", 100.0, "m"),
    ("Upstream face slope", "Z1", 3.0, "H:1V"),
    ("Downstream face slope", "Z2", 2.0, "H:1V"),
    ("Breach side slope (piping)", "Zb_p", 0.5, "H:1V"),
    ("Breach side slope (overtop)", "Zb_o", 0.5, "H:1V"),
    ("Vm factor (cohesionless=3.75 / resist=2.5)", "f_Vm", 3.75, "US units"),
    ("t factor (cohesionless=0.02 / resist=0.036)", "f_t", 0.02, "US units"),
]

for i, (name, sym, val, unit) in enumerate(geom):
    r = 7 + i
    ws3.cell(row=r, column=2, value=name).font = font_normal
    ws3.cell(row=r, column=3, value=sym).font = Font(name='Arial', bold=True, size=9)
    cell = ws3.cell(row=r, column=4, value=val)
    style_input_cell(cell)
    ws3.cell(row=r, column=5, value=unit).font = font_normal
    for c in range(2, 6):
        ws3.cell(row=r, column=c).border = thin

# Derived
ws3['B17'] = "Height of breach Hb"
ws3['C17'] = "Hb"
ws3['D17'] = '=D7-D8'
style_calc_cell(ws3['D17'])
ws3['E17'] = "m"
ws3['B18'] = "Z3 = Z1+Z2"
ws3['C18'] = "Z3"
ws3['D18'] = '=D11+D12'
style_calc_cell(ws3['D18'])
ws3['E18'] = "H:1V"

# --- Scenario 1: Piping ---
ws3.merge_cells('B20:G20')
ws3['B20'] = "SCENARIO 1 — PIPING FAILURE  (WL at overflow spillway / normal pool / 100-yr storm)"
ws3['B20'].font = font_header
ws3['B20'].fill = fill_subheader
ws3['B20'].alignment = align_c

ws3['B21'] = "Parameter"
ws3['C21'] = "Symbol"
ws3['D21'] = "Value"
ws3['E21'] = "Unit"
ws3['F21'] = "US equiv."
ws3['G21'] = "Notes"
style_header_row(ws3, 21, 2, 7)

# Inputs for piping
ws3['B22'] = "Water surface elevation"
ws3['C22'] = "WL_p"
ws3['D22'] = 3.0
style_input_cell(ws3['D22'])
ws3['E22'] = "m"

ws3['B23'] = "Height over breach elev. Hw"
ws3['C23'] = "Hw_p"
ws3['D23'] = '=D22-D8'
style_calc_cell(ws3['D23'])
ws3['E23'] = "m"

ws3['B24'] = "Volume of water Vw"
ws3['C24'] = "Vw_p"
ws3['D24'] = 10000
style_input_cell(ws3['D24'])
ws3['E24'] = "m³"
ws3['F24'] = '=D24/1233.48183754752'  # ac-ft
style_calc_cell(ws3['F24'])
ws3['G24'] = "ac-ft"

ws3['B25'] = "Surface area Sa"
ws3['C25'] = "Sa_p"
ws3['D25'] = 0.7
style_input_cell(ws3['D25'])
ws3['E25'] = "ha"
ws3['F25'] = '=D25/0.40468564224'
style_calc_cell(ws3['F25'])
ws3['G25'] = "ac"

# Calculations piping
ws3['B27'] = "CALCULATED RESULTS — PIPING"
ws3['B27'].font = font_section
ws3.merge_cells('B27:G27')
ws3['B27'].fill = fill_section

ws3['B28'] = "Breach Formation Factor BFF"
ws3['C28'] = "BFF_p"
ws3['D28'] = '=F24*(D23/0.3048)'  # Vw(ac-ft)*Hw(ft)
style_calc_cell(ws3['D28'])
ws3['E28'] = "US units"

ws3['B29'] = "Volume eroded Vm"
ws3['C29'] = "Vm_p"
ws3['D29'] = '=$D$15*D28^0.77'  # cu.yd
style_calc_cell(ws3['D29'])
ws3['E29'] = "cu.yd"
ws3['F29'] = '=D29*0.764554857984'
style_calc_cell(ws3['F29'])
ws3['G29'] = "m³"

ws3['B30'] = "K1"
ws3['C30'] = "K1_p"
ws3['D30'] = '=(D17/0.3048)*((D9/0.3048)+(D17/0.3048)*D18/2)'
style_calc_cell(ws3['D30'])
ws3['E30'] = "ft²"

ws3['B31'] = "K2"
ws3['C31'] = "K2_p"
ws3['D31'] = '=(D17/0.3048)^2*((D9/0.3048)*D13+(D17/0.3048)*D13*D18/3)'
style_calc_cell(ws3['D31'])
ws3['E31'] = "ft³"

ws3['B32'] = "Base width Wb"
ws3['C32'] = "Wb_p"
ws3['D32'] = '=(27*D29 - D31)/D30'  # ft
style_calc_cell(ws3['D32'])
ws3['E32'] = "ft"
ws3['F32'] = '=D32*0.3048'
style_calc_cell(ws3['F32'])
ws3['G32'] = "m"

ws3['B33'] = "Average width Wavg"
ws3['C33'] = "Wavg_p"
ws3['D33'] = '=D32 + D13*(D23/0.3048)'
style_calc_cell(ws3['D33'])
ws3['E33'] = "ft"
ws3['F33'] = '=D33*0.3048'
style_calc_cell(ws3['F33'])
ws3['G33'] = "m"

ws3['B34'] = "Top width (flow) Wtop"
ws3['C34'] = "Wtop_p"
ws3['D34'] = '=D32 + 2*D13*(D23/0.3048)'
style_calc_cell(ws3['D34'])
ws3['E34'] = "ft"
ws3['F34'] = '=D34*0.3048'
style_calc_cell(ws3['F34'])
ws3['G34'] = "m"

ws3['B35'] = "Top width (crest) Wcr"
ws3['C35'] = "Wcr_p"
ws3['D35'] = '=D32 + 2*D13*(D17/0.3048)'
style_calc_cell(ws3['D35'])
ws3['E35'] = "ft"
ws3['F35'] = '=D35*0.3048'
style_calc_cell(ws3['F35'])
ws3['G35'] = "m"

ws3['B36'] = "Breach % of crest length"
ws3['C36'] = "%_p"
ws3['D36'] = '=F35/D10*100'
style_calc_cell(ws3['D36'])
ws3['E36'] = "%"

ws3['B37'] = "Time of breach development t"
ws3['C37'] = "t_p"
ws3['D37'] = '=$D$16*D29^0.36'
style_calc_cell(ws3['D37'])
ws3['E37'] = "hr"
ws3['F37'] = '=D37*60'
style_calc_cell(ws3['F37'])
ws3['G37'] = "min"

ws3['B38'] = "A (storage factor)"
ws3['C38'] = "A_p"
ws3['D38'] = '=23.4*F25/D33'
style_calc_cell(ws3['D38'])
ws3['E38'] = "US"

ws3['B39'] = "K3"
ws3['C39'] = "K3_p"
ws3['D39'] = '=D38/(D38+D37*SQRT(D23/0.3048))'
style_calc_cell(ws3['D39'])
ws3['E39'] = "—"

ws3['B40'] = "Mod. weir peak discharge Qp"
ws3['C40'] = "Qp_weir_p"
ws3['D40'] = '=3.1*D33*(D23/0.3048)^1.5*(D39^3)'
style_calc_cell(ws3['D40'])
ws3['E40'] = "cfs"
ws3['F40'] = '=D40*0.028316846592'
style_calc_cell(ws3['F40'])
ws3['G40'] = "m³/s"

ws3['B41'] = "Froehlich peak discharge Qp"
ws3['C41'] = "Qp_Fr_p"
ws3['D41'] = '=40.1*F24^0.295*(D23/0.3048)^1.24'
style_calc_cell(ws3['D41'])
ws3['E41'] = "cfs"
ws3['F41'] = '=D41*0.028316846592'
style_calc_cell(ws3['F41'])
ws3['G41'] = "m³/s"

ws3['B42'] = "SELECTED Qp (mod. weir recommended)"
ws3['C42'] = "Qp_p"
ws3['D42'] = '=D40'
style_link_cell(ws3['D42'])
ws3['E42'] = "cfs"
ws3['F42'] = '=F40'
style_link_cell(ws3['F42'])
ws3['G42'] = "m³/s"

ws3['B43'] = "T.Base (triangular)"
ws3['C43'] = "Tbase_p"
ws3['D43'] = '=2*(D24)/(F42*3600)'  # hours, no extra inflow assumed for piping base case
style_calc_cell(ws3['D43'])
ws3['E43'] = "hr"
ws3['F43'] = '=D43*60'
style_calc_cell(ws3['F43'])
ws3['G43'] = "min"

for r in range(22, 44):
    for c in range(2, 8):
        if ws3.cell(row=r, column=c).border.left.style is None:
            ws3.cell(row=r, column=c).border = thin

# --- Scenario 2: Overtopping ---
ws3.merge_cells('B45:G45')
ws3['B45'] = "SCENARIO 2 — OVERTOPPING FAILURE  (WL at dam crest / PMP max pool)"
ws3['B45'].font = font_header
ws3['B45'].fill = fill_subheader
ws3['B45'].alignment = align_c

ws3['B46'] = "Parameter"
ws3['C46'] = "Symbol"
ws3['D46'] = "Value"
ws3['E46'] = "Unit"
ws3['F46'] = "US equiv."
ws3['G46'] = "Notes"
style_header_row(ws3, 46, 2, 7)

ws3['B47'] = "Water surface elevation"
ws3['C47'] = "WL_o"
ws3['D47'] = 3.5
style_input_cell(ws3['D47'])
ws3['E47'] = "m"

ws3['B48'] = "Height over breach elev. Hw"
ws3['C48'] = "Hw_o"
ws3['D48'] = '=D47-D8'
style_calc_cell(ws3['D48'])
ws3['E48'] = "m"

ws3['B49'] = "Volume of water Vw"
ws3['C49'] = "Vw_o"
ws3['D49'] = 13000
style_input_cell(ws3['D49'])
ws3['E49'] = "m³"
ws3['F49'] = '=D49/1233.48183754752'
style_calc_cell(ws3['F49'])
ws3['G49'] = "ac-ft"

ws3['B50'] = "Surface area Sa"
ws3['C50'] = "Sa_o"
ws3['D50'] = 0.8
style_input_cell(ws3['D50'])
ws3['E50'] = "ha"
ws3['F50'] = '=D50/0.40468564224'
style_calc_cell(ws3['F50'])
ws3['G50'] = "ac"

ws3['B51'] = "Volume inflow during breach"
ws3['C51'] = "Vin_o"
ws3['D51'] = 1300
style_input_cell(ws3['D51'])
ws3['E51'] = "m³"

ws3['B52'] = "Sa adjusted for inflow"
ws3['C52'] = "Sa_adj"
ws3['D52'] = '=D50 + (D51/10000)'  # simple approx; user can override
style_input_cell(ws3['D52'])
ws3['E52'] = "ha"

# Results overtopping
ws3['B54'] = "CALCULATED RESULTS — OVERTOPPING"
ws3['B54'].font = font_section
ws3.merge_cells('B54:G54')
ws3['B54'].fill = fill_section

ws3['B55'] = "Breach Formation Factor BFF"
ws3['C55'] = "BFF_o"
ws3['D55'] = '=F49*(D48/0.3048)'
style_calc_cell(ws3['D55'])
ws3['E55'] = "US units"

ws3['B56'] = "Volume eroded Vm"
ws3['C56'] = "Vm_o"
ws3['D56'] = '=$D$15*D55^0.77'
style_calc_cell(ws3['D56'])
ws3['E56'] = "cu.yd"
ws3['F56'] = '=D56*0.764554857984'
style_calc_cell(ws3['F56'])
ws3['G56'] = "m³"

ws3['B57'] = "K1"
ws3['C57'] = "K1_o"
ws3['D57'] = '=(D17/0.3048)*((D9/0.3048)+(D17/0.3048)*D18/2)'
style_calc_cell(ws3['D57'])
ws3['E57'] = "ft²"

ws3['B58'] = "K2"
ws3['C58'] = "K2_o"
ws3['D58'] = '=(D17/0.3048)^2*((D9/0.3048)*D14+(D17/0.3048)*D14*D18/3)'
style_calc_cell(ws3['D58'])
ws3['E58'] = "ft³"

ws3['B59'] = "Base width Wb"
ws3['C59'] = "Wb_o"
ws3['D59'] = '=(27*D56 - D58)/D57'
style_calc_cell(ws3['D59'])
ws3['E59'] = "ft"
ws3['F59'] = '=D59*0.3048'
style_calc_cell(ws3['F59'])
ws3['G59'] = "m"

ws3['B60'] = "Average width Wavg"
ws3['C60'] = "Wavg_o"
ws3['D60'] = '=D59 + D14*(D48/0.3048)'
style_calc_cell(ws3['D60'])
ws3['E60'] = "ft"
ws3['F60'] = '=D60*0.3048'
style_calc_cell(ws3['F60'])
ws3['G60'] = "m"

ws3['B61'] = "Top width (flow) Wtop"
ws3['C61'] = "Wtop_o"
ws3['D61'] = '=D59 + 2*D14*(D48/0.3048)'
style_calc_cell(ws3['D61'])
ws3['E61'] = "ft"
ws3['F61'] = '=D61*0.3048'
style_calc_cell(ws3['F61'])
ws3['G61'] = "m"

ws3['B62'] = "Top width (crest) Wcr"
ws3['C62'] = "Wcr_o"
ws3['D62'] = '=D59 + 2*D14*(D17/0.3048)'
style_calc_cell(ws3['D62'])
ws3['E62'] = "ft"
ws3['F62'] = '=D62*0.3048'
style_calc_cell(ws3['F62'])
ws3['G62'] = "m"

ws3['B63'] = "Breach % of crest length"
ws3['C63'] = "%_o"
ws3['D63'] = '=F62/D10*100'
style_calc_cell(ws3['D63'])
ws3['E63'] = "%"

ws3['B64'] = "Time of breach development t"
ws3['C64'] = "t_o"
ws3['D64'] = '=$D$16*D56^0.36'
style_calc_cell(ws3['D64'])
ws3['E64'] = "hr"
ws3['F64'] = '=D64*60'
style_calc_cell(ws3['F64'])
ws3['G64'] = "min"

ws3['B65'] = "A (storage factor)"
ws3['C65'] = "A_o"
ws3['D65'] = '=23.4*(D52/0.40468564224)/D60'
style_calc_cell(ws3['D65'])
ws3['E65'] = "US"

ws3['B66'] = "K3"
ws3['C66'] = "K3_o"
ws3['D66'] = '=D65/(D65+D64*SQRT(D48/0.3048))'
style_calc_cell(ws3['D66'])
ws3['E66'] = "—"

ws3['B67'] = "Mod. weir peak discharge Qp"
ws3['C67'] = "Qp_weir_o"
ws3['D67'] = '=3.1*D60*(D48/0.3048)^1.5*(D66^3)'
style_calc_cell(ws3['D67'])
ws3['E67'] = "cfs"
ws3['F67'] = '=D67*0.028316846592'
style_calc_cell(ws3['F67'])
ws3['G67'] = "m³/s"

ws3['B68'] = "Froehlich peak discharge Qp"
ws3['C68'] = "Qp_Fr_o"
ws3['D68'] = '=40.1*F49^0.295*(D48/0.3048)^1.24'
style_calc_cell(ws3['D68'])
ws3['E68'] = "cfs"
ws3['F68'] = '=D68*0.028316846592'
style_calc_cell(ws3['F68'])
ws3['G68'] = "m³/s"

ws3['B69'] = "SELECTED Qp (mod. weir recommended)"
ws3['C69'] = "Qp_o"
ws3['D69'] = '=D67'
style_link_cell(ws3['D69'])
ws3['E69'] = "cfs"
ws3['F69'] = '=F67'
style_link_cell(ws3['F69'])
ws3['G69'] = "m³/s"

ws3['B70'] = "T.Base (triangular, with inflow)"
ws3['C70'] = "Tbase_o"
ws3['D70'] = '=2*(D49+D51)/(F69*3600)'
style_calc_cell(ws3['D70'])
ws3['E70'] = "hr"
ws3['F70'] = '=D70*60'
style_calc_cell(ws3['F70'])
ws3['G70'] = "min"

for r in range(47, 71):
    for c in range(2, 8):
        if ws3.cell(row=r, column=c).border.left.style is None:
            ws3.cell(row=r, column=c).border = thin

# Limitations box
ws3.merge_cells('I5:K5')
ws3['I5'] = "LIMITATIONS (Tech Note 1)"
ws3['I5'].font = font_header
ws3['I5'].fill = fill_limit
ws3['I5'].alignment = align_c

ws3.merge_cells('I6:K16')
ws3['I6'] = (
    "Breach width / height ratio:\n  typical 0.5 – 3.0\n\n"
    "Failure time t:\n  typical 0.2 – 4.0 hr\n\n"
    "Material factors (US units):\n"
    "  Cohesionless: f_Vm=3.75, f_t=0.02\n"
    "  Resistant:    f_Vm=2.50, f_t=0.036\n\n"
    "Side slopes Zb:\n"
    "  Cohesionless ≈ 0.5 – 1.0\n"
    "  Resistant    ≈ 0.25 – 0.5\n\n"
    "Select Qp from mod. weir when\n"
    "T.Peak / T.Base < 0.5; otherwise\n"
    "consider Froehlich or timestep method."
)
ws3['I6'].font = font_small
ws3['I6'].alignment = Alignment(wrap_text=True, vertical='top')
ws3['I6'].fill = fill_note
ws3['I6'].border = thin

# ============================================================
# SHEET 4: CONSTRAINED BREACH (Break-2)
# ============================================================
ws4 = wb.create_sheet("04_Constrained_Breach")

set_col_widths(ws4, [3, 40, 12, 14, 12, 14, 14, 14])

ws4.merge_cells('B2:G2')
ws4['B2'] = "04  |  WIDTH-CONSTRAINED BREACH  (Physical setting or short crest length limits Wb)"
ws4['B2'].font = Font(name='Arial', bold=True, color='FFFFFF', size=13)
ws4['B2'].fill = fill_title
ws4['B2'].alignment = align_c

ws4.merge_cells('B3:G3')
ws4['B3'] = "Use when calculated Wb from sheet 03 exceeds available crest length or a known geologic/structural constraint.  User supplies Wb; Vm is checked against upper-limit regression."
ws4['B3'].font = font_small
ws4['B3'].fill = fill_section

ws4.merge_cells('B5:E5')
ws4['B5'] = "INPUTS (many linked from Sheet 03 – Overtopping scenario as default)"
ws4['B5'].font = font_header
ws4['B5'].fill = fill_header
ws4['B5'].alignment = align_c

ws4['B6'] = "Parameter"
ws4['C6'] = "Symbol"
ws4['D6'] = "Value"
ws4['E6'] = "Unit"
style_header_row(ws4, 6, 2, 5)

# Linked / input cells
link_inputs = [
    ("Dam crest elevation", "Crest", "='03_Breach_Characteristics'!D7", "m"),
    ("Breach base elevation", "BL", "='03_Breach_Characteristics'!D8", "m"),
    ("Height of breach Hb", "Hb", "='03_Breach_Characteristics'!D17", "m"),
    ("Crest width C", "C", "='03_Breach_Characteristics'!D9", "m"),
    ("Z3 = Z1+Z2", "Z3", "='03_Breach_Characteristics'!D18", "H:1V"),
    ("Breach side slope Zb", "Zb", 0.8, "H:1V"),  # user can change
    ("Water surface elev. (failure)", "WL", "='03_Breach_Characteristics'!D47", "m"),
    ("Hw", "Hw", "='03_Breach_Characteristics'!D48", "m"),
    ("Volume of water Vw", "Vw", "='03_Breach_Characteristics'!D49", "m³"),
    ("Surface area Sa", "Sa", "='03_Breach_Characteristics'!D50", "ha"),
    ("Volume inflow", "Vin", "='03_Breach_Characteristics'!D51", "m³"),
    ("Vm factor f_Vm", "f_Vm", "='03_Breach_Characteristics'!D15", "US"),
    ("t factor f_t", "f_t", "='03_Breach_Characteristics'!D16", "US"),
    ("USER-SPECIFIED base width Wb", "Wb_user", 0.5, "m"),
]

for i, (name, sym, val, unit) in enumerate(link_inputs):
    r = 7 + i
    ws4.cell(row=r, column=2, value=name).font = font_normal
    ws4.cell(row=r, column=3, value=sym).font = Font(name='Arial', bold=True, size=9)
    cell = ws4.cell(row=r, column=4, value=val)
    if isinstance(val, str) and val.startswith("="):
        style_link_cell(cell)
    else:
        style_input_cell(cell)
    ws4.cell(row=r, column=5, value=unit).font = font_normal
    for c in range(2, 6):
        ws4.cell(row=r, column=c).border = thin

# Upper limit check
ws4.merge_cells('B23:E23')
ws4['B23'] = "UPPER-LIMIT CHECK ON ERODED VOLUME"
ws4['B23'].font = font_header
ws4['B23'].fill = fill_header
ws4['B23'].alignment = align_c

ws4['B24'] = "BFF (US units)"
ws4['C24'] = "BFF"
ws4['D24'] = '=(D15/1233.48183754752)*(D14/0.3048)'
style_calc_cell(ws4['D24'])
ws4['E24'] = "US"

ws4['B25'] = "Vm upper limit (regression)"
ws4['C25'] = "Vm_max"
ws4['D25'] = '=D18*D24^0.77'  # cu.yd
style_calc_cell(ws4['D25'])
ws4['E25'] = "cu.yd"
ws4['F25'] = '=D25*0.764554857984'
style_calc_cell(ws4['F25'])
ws4['G25'] = "m³"

ws4['B26'] = "K1"
ws4['C26'] = "K1"
ws4['D26'] = '=(D9/0.3048)*((D10/0.3048)+(D9/0.3048)*D11/2)'
style_calc_cell(ws4['D26'])
ws4['E26'] = "ft²"

ws4['B27'] = "K2"
ws4['C27'] = "K2"
ws4['D27'] = '=(D9/0.3048)^2*((D10/0.3048)*D12+(D9/0.3048)*D12*D11/3)'
style_calc_cell(ws4['D27'])
ws4['E27'] = "ft³"

ws4['B28'] = "Vm corresponding to user Wb"
ws4['C28'] = "Vm_user"
ws4['D28'] = '=(D20/0.3048 * D26 + D27)/27'  # cu.yd
style_calc_cell(ws4['D28'])
ws4['E28'] = "cu.yd"
ws4['F28'] = '=D28*0.764554857984'
style_calc_cell(ws4['F28'])
ws4['G28'] = "m³"

ws4['B29'] = "Vm_user < Vm_max ?"
ws4['C29'] = "Check"
ws4['D29'] = '=IF(D28<=D25,"OK – within upper limit","EXCEEDS – reduce Wb or review")'
style_calc_cell(ws4['D29'])
ws4.merge_cells('D29:G29')

# Geometry & discharge with user Wb
ws4.merge_cells('B31:E31')
ws4['B31'] = "BREACH GEOMETRY & PEAK DISCHARGE WITH USER Wb"
ws4['B31'].font = font_header
ws4['B31'].fill = fill_header
ws4['B31'].alignment = align_c

ws4['B32'] = "Average width Wavg"
ws4['C32'] = "Wavg"
ws4['D32'] = '=D20 + D12*D14'
style_calc_cell(ws4['D32'])
ws4['E32'] = "m"

ws4['B33'] = "Top width (flow) Wtop"
ws4['C33'] = "Wtop"
ws4['D33'] = '=D20 + 2*D12*D14'
style_calc_cell(ws4['D33'])
ws4['E33'] = "m"

ws4['B34'] = "Top width (crest) Wcr"
ws4['C34'] = "Wcr"
ws4['D34'] = '=D20 + 2*D12*D9'
style_calc_cell(ws4['D34'])
ws4['E34'] = "m"

ws4['B35'] = "Time of development t"
ws4['C35'] = "t"
ws4['D35'] = '=D19*D28^0.36'
style_calc_cell(ws4['D35'])
ws4['E35'] = "hr"
ws4['F35'] = '=D35*60'
style_calc_cell(ws4['F35'])
ws4['G35'] = "min"

ws4['B36'] = "A (storage factor, US)"
ws4['C36'] = "A"
ws4['D36'] = '=23.4*(D16/0.40468564224)/(D32/0.3048)'
style_calc_cell(ws4['D36'])
ws4['E36'] = "US"

ws4['B37'] = "K3"
ws4['C37'] = "K3"
ws4['D37'] = '=D36/(D36+D35*SQRT(D14/0.3048))'
style_calc_cell(ws4['D37'])
ws4['E37'] = "—"

ws4['B38'] = "Mod. weir Qp"
ws4['C38'] = "Qp_weir"
ws4['D38'] = '=3.1*(D32/0.3048)*(D14/0.3048)^1.5*(D37^3)*0.028316846592'
style_calc_cell(ws4['D38'])
ws4['E38'] = "m³/s"

ws4['B39'] = "Froehlich Qp"
ws4['C39'] = "Qp_Fr"
ws4['D39'] = '=40.1*(D15/1233.48183754752)^0.295*(D14/0.3048)^1.24*0.028316846592'
style_calc_cell(ws4['D39'])
ws4['E39'] = "m³/s"

ws4['B40'] = "SELECTED Qp"
ws4['C40'] = "Qp"
ws4['D40'] = '=D38'
style_link_cell(ws4['D40'])
ws4['E40'] = "m³/s"

ws4['B41'] = "T.Base"
ws4['C41'] = "Tbase"
ws4['D41'] = '=2*(D15+D17)/(D40*3600)'
style_calc_cell(ws4['D41'])
ws4['E41'] = "hr"

for r in range(24, 42):
    for c in range(2, 8):
        if ws4.cell(row=r, column=c).value is not None:
            ws4.cell(row=r, column=c).border = thin

# ============================================================
# SHEET 5: TIMESTEP HYDROGRAPH (simplified Break-3)
# ============================================================
ws5 = wb.create_sheet("05_Timestep_Hydrograph")

set_col_widths(ws5, [8, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 14])

ws5.merge_cells('A1:L1')
ws5['A1'] = "05  |  TIME-STEP BREACH HYDROGRAPH  (Progressive breach development – HEC-1 style)"
ws5['A1'].font = Font(name='Arial', bold=True, color='FFFFFF', size=13)
ws5['A1'].fill = fill_title
ws5['A1'].alignment = align_c

ws5.merge_cells('A2:L2')
ws5['A2'] = "Breach grows linearly in time up to T.Fail.  Outflow computed each step from current Wb(t), H(t) using weir formulas.  Reservoir drawdown from continuity."
ws5['A2'].font = font_small
ws5['A2'].fill = fill_section

# Key inputs (linked + user)
ws5['A4'] = "KEY INPUTS"
ws5['A4'].font = font_header
ws5['A4'].fill = fill_header
ws5.merge_cells('A4:D4')

ws5['A5'] = "Hb (m)"
ws5['B5'] = "='03_Breach_Characteristics'!D17"
style_link_cell(ws5['B5'])
ws5['C5'] = "Wb final (m)"
ws5['D5'] = "='03_Breach_Characteristics'!F59"  # overtopping Wb
style_link_cell(ws5['D5'])

ws5['A6'] = "Zb"
ws5['B6'] = "='03_Breach_Characteristics'!D14"
style_link_cell(ws5['B6'])
ws5['C6'] = "T.Fail (min)"
ws5['D6'] = "='03_Breach_Characteristics'!F64"
style_link_cell(ws5['D6'])

ws5['A7'] = "Initial WL (m)"
ws5['B7'] = "='03_Breach_Characteristics'!D47"
style_link_cell(ws5['B7'])
ws5['C7'] = "BL (m)"
ws5['D7'] = "='03_Breach_Characteristics'!D8"
style_link_cell(ws5['D7'])

ws5['A8'] = "Vw (m³)"
ws5['B8'] = "='03_Breach_Characteristics'!D49"
style_link_cell(ws5['B8'])
ws5['C8'] = "Qin avg (m³/s)"
ws5['D8'] = 1.0
style_input_cell(ws5['D8'])

ws5['A9'] = "dt (min)"
ws5['B9'] = 1.0
style_input_cell(ws5['B9'])
ws5['C9'] = "Crect (metric)"
ws5['D9'] = 1.70
style_input_cell(ws5['D9'])

ws5['A10'] = "Ctri (metric)"
ws5['B10'] = 1.35
style_input_cell(ws5['B10'])

# Note on full timestep
ws5.merge_cells('A12:L12')
ws5['A12'] = (
    "NOTE: A full minute-by-minute time-step table (as in original Break-3) contains 40+ rows of progressive Wb, H, Qtri, Qrect, dVol, dWL. "
    "For practicality this sheet provides the governing inputs (linked) and a summary of the triangular hydrograph constructed from Qp & T.Peak. "
    "For detailed step-by-step simulation the original Break-3 spreadsheet or a dedicated numerical model is recommended. "
    "The triangular hydrograph below is volume-conserving and suitable for most routing applications."
)
ws5['A12'].font = font_small
ws5['A12'].fill = fill_note
ws5['A12'].alignment = Alignment(wrap_text=True)
ws5.row_dimensions[12].height = 50

# Triangular hydrograph summary
ws5.merge_cells('A14:F14')
ws5['A14'] = "TRIANGULAR HYDROGRAPH SUMMARY (volume-conserving)"
ws5['A14'].font = font_header
ws5['A14'].fill = fill_header
ws5['A14'].alignment = align_c

ws5['A15'] = "Qp (m³/s)"
ws5['B15'] = "='03_Breach_Characteristics'!F69"
style_link_cell(ws5['B15'])
ws5['C15'] = "T.Peak (hr)"
ws5['D15'] = "='03_Breach_Characteristics'!D64"
style_link_cell(ws5['D15'])

ws5['A16'] = "Vol + Inflow (m³)"
ws5['B16'] = "='03_Breach_Characteristics'!D49+'03_Breach_Characteristics'!D51"
style_calc_cell(ws5['B16'])
ws5['C16'] = "T.Base (hr)"
ws5['D16'] = "='03_Breach_Characteristics'!D70"
style_link_cell(ws5['D16'])

# Coordinates
ws5.merge_cells('A18:D18')
ws5['A18'] = "HYDROGRAPH COORDINATES (triangular)"
ws5['A18'].font = font_header
ws5['A18'].fill = fill_header

ws5['A19'] = "Time (hr)"
ws5['B19'] = "Q (m³/s)"
ws5['C19'] = "Time (min)"
style_header_row(ws5, 19, 1, 3)

# 5-point triangular
ws5['A20'] = 0.0
ws5['B20'] = 0.0
ws5['C20'] = 0.0

ws5['A21'] = '=D15/2'
ws5['B21'] = '=B15/2'
ws5['C21'] = '=A21*60'

ws5['A22'] = '=D15'
ws5['B22'] = '=B15'
ws5['C22'] = '=A22*60'

ws5['A23'] = '=(D15+D16)/2'
ws5['B23'] = '=B15/2'
ws5['C23'] = '=A23*60'

ws5['A24'] = '=D16'
ws5['B24'] = 0.0
ws5['C24'] = '=A24*60'

for r in range(20, 25):
    for c in range(1, 4):
        style_calc_cell(ws5.cell(row=r, column=c))
        ws5.cell(row=r, column=c).border = thin

# ============================================================
# SHEET 6: DIMENSIONLESS HYDROGRAPH (Break-5)
# ============================================================
ws6 = wb.create_sheet("06_Dimensionless_Hydrograph")

set_col_widths(ws6, [10, 12, 14, 14, 14, 12, 12, 14])

ws6.merge_cells('A1:H1')
ws6['A1'] = "06  |  DIMENSIONLESS HYDROGRAPH  (Haan, Barfield & Hayes method)"
ws6['A1'].font = Font(name='Arial', bold=True, color='FFFFFF', size=13)
ws6['A1'].fill = fill_title
ws6['A1'].alignment = align_c

ws6.merge_cells('A2:H2')
ws6['A2'] = "Q(t)/Qp = [ (t/T.Peak)·exp(1 – t/T.Peak) ]^K     |     K adjusted so that integrated volume = reservoir volume + inflows"
ws6['A2'].font = font_small
ws6['A2'].fill = fill_section

ws6['A4'] = "INPUTS"
ws6['A4'].font = font_header
ws6['A4'].fill = fill_header
ws6.merge_cells('A4:D4')

ws6['A5'] = "Reservoir volume (m³)"
ws6['B5'] = 130000
style_input_cell(ws6['B5'])
ws6['C5'] = "Inflow volume (m³)"
ws6['D5'] = 50000
style_input_cell(ws6['D5'])

ws6['A6'] = "Q.Peak (m³/s)"
ws6['B6'] = 100
style_input_cell(ws6['B6'])
ws6['C6'] = "T.Peak (min)"
ws6['D6'] = 21
style_input_cell(ws6['D6'])

ws6['A7'] = "Time increment (min)"
ws6['B7'] = 3
style_input_cell(ws6['B7'])
ws6['C7'] = "T.Peak (hr)"
ws6['D7'] = '=D6/60'
style_calc_cell(ws6['D7'])

ws6['A8'] = "Total volume (m³)"
ws6['B8'] = '=B5+D5'
style_calc_cell(ws6['B8'])
ws6['C8'] = "Initial K estimate"
ws6['D8'] = '=6.5*((B6*D7*3600)/B8)^1.92'
style_calc_cell(ws6['D8'])

ws6['A9'] = "Revised K (user adjust)"
ws6['B9'] = 3.24
style_input_cell(ws6['B9'])
ws6['C9'] = "Typical range"
ws6['D9'] = "1.5 – 5.0"
ws6['D9'].font = font_tiny

# Table header
ws6.merge_cells('A11:G11')
ws6['A11'] = "DIMENSIONLESS HYDROGRAPH TABLE"
ws6['A11'].font = font_header
ws6['A11'].fill = fill_header
ws6['A11'].alignment = align_c

headers6 = ["Time (hr)", "t/T.Peak", "exp(1-t/Tp)", "[…] ^K", "Q (m³/hr)", "Incr. Vol (m³)", "Q (m³/s)"]
for i, h in enumerate(headers6, 1):
    ws6.cell(row=12, column=i, value=h)
style_header_row(ws6, 12, 1, 7)

# Generate ~40 rows of hydrograph (formulas)
# t from 0 to ~5*T.Peak
for i in range(0, 40):
    r = 13 + i
    if i == 0:
        ws6.cell(row=r, column=1, value=0.0)
    else:
        ws6.cell(row=r, column=1, value=f'=A{r-1}+$B$7/60')
    style_calc_cell(ws6.cell(row=r, column=1))
    # t/Tp
    ws6.cell(row=r, column=2, value=f'=A{r}/$D$7')
    style_calc_cell(ws6.cell(row=r, column=2))
    # exp(1 - t/Tp)
    ws6.cell(row=r, column=3, value=f'=EXP(1-B{r})')
    style_calc_cell(ws6.cell(row=r, column=3))
    # (t/Tp * exp)^K
    ws6.cell(row=r, column=4, value=f'=IF(B{r}=0,0,(B{r}*C{r})^$B$9)')
    style_calc_cell(ws6.cell(row=r, column=4))
    # Q m3/hr
    ws6.cell(row=r, column=5, value=f'=D{r}*$B$6*3600')
    style_calc_cell(ws6.cell(row=r, column=5))
    # incr vol (trapezoidal approx)
    if i == 0:
        ws6.cell(row=r, column=6, value=0.0)
    else:
        ws6.cell(row=r, column=6, value=f'=0.5*(E{r}+E{r-1})*($B$7/60)')
    style_calc_cell(ws6.cell(row=r, column=6))
    # Q m3/s
    ws6.cell(row=r, column=7, value=f'=E{r}/3600')
    style_calc_cell(ws6.cell(row=r, column=7))
    for c in range(1, 8):
        ws6.cell(row=r, column=c).border = thin

ws6['A54'] = "Cumulative volume check"
ws6['B54'] = '=SUM(F13:F52)'
style_calc_cell(ws6['B54'])
ws6['C54'] = "Target volume"
ws6['D54'] = '=B8'
style_calc_cell(ws6['D54'])
ws6['E54'] = "% difference"
ws6['F54'] = '=(B54-D54)/D54'
style_calc_cell(ws6['F54'])
ws6['F54'].number_format = '0.00%'

# ============================================================
# SHEET 7: DOWNSTREAM FLOOD PROFILE
# ============================================================
ws7 = wb.create_sheet("07_Downstream_Flood")

set_col_widths(ws7, [10, 14, 12, 12, 12, 12, 12, 12, 12, 14, 14])

ws7.merge_cells('A1:K1')
ws7['A1'] = "07  |  DOWNSTREAM FLOOD ATTENUATION & TRAVEL TIME  (Valley profile method)"
ws7['A1'].font = Font(name='Arial', bold=True, color='FFFFFF', size=13)
ws7['A1'].fill = fill_title
ws7['A1'].alignment = align_c

ws7.merge_cells('A2:K2')
ws7['A2'] = "Hydraulic profile of the drainage path below the dam.  Peak attenuation estimated from distance & reservoir volume class.  Flood-wave travel-time window from channel velocity × 1.0–1.5 factor."
ws7['A2'].font = font_small
ws7['A2'].fill = fill_section

ws7['A4'] = "SCENARIO & PEAK DISCHARGE"
ws7['A4'].font = font_header
ws7['A4'].fill = fill_header
ws7.merge_cells('A4:D4')

ws7['A5'] = "Selected Qp (m³/s)"
ws7['B5'] = "='03_Breach_Characteristics'!F69"
style_link_cell(ws7['B5'])
ws7['C5'] = "Reservoir volume class"
ws7['D5'] = "Small (<50 ac-ft)"
style_input_cell(ws7['D5'])

ws7['A6'] = "Initial reservoir vol (m³)"
ws7['B6'] = "='03_Breach_Characteristics'!D49"
style_link_cell(ws7['B6'])

# Valley profile table
ws7.merge_cells('A8:K8')
ws7['A8'] = "VALLEY / CHANNEL PROFILE  (enter stations from dam downstream)"
ws7['A8'].font = font_header
ws7['A8'].fill = fill_header
ws7['A8'].alignment = align_c

headers7 = ["Station ID", "Dist. from dam (m)", "Elevation (m)", "Δx (m)", "Gradient (m/m)",
            "Grad. (m/km)", "Flow vel. V (m/s)", "Qx/Qp", "Qx (m³/s)",
            "t_min incr (min)", "t_max incr (min)"]
for i, h in enumerate(headers7, 1):
    ws7.cell(row=9, column=i, value=h)
style_header_row(ws7, 9, 1, 11)

# Sample profile data (from Flood-1 example)
profile = [
    (1.5, 0, 20),
    (1.4, 100, 18),
    (1.3, 200, 16),
    (1.1, 400, 14),
    (1.0, 500, 12),
    (0.9, 600, 10),
    (0.7, 800, 8),
    (0.6, 900, 6),
    (0.5, 1000, 4),
    (0.3, 1200, 2),
    (0.0, 1500, 1),
]

for i, (sta, dist, elev) in enumerate(profile):
    r = 10 + i
    ws7.cell(row=r, column=1, value=sta)
    style_input_cell(ws7.cell(row=r, column=1))
    ws7.cell(row=r, column=2, value=dist)
    style_input_cell(ws7.cell(row=r, column=2))
    ws7.cell(row=r, column=3, value=elev)
    style_input_cell(ws7.cell(row=r, column=3))
    if i == 0:
        ws7.cell(row=r, column=4, value=0)
        ws7.cell(row=r, column=5, value=0)
        ws7.cell(row=r, column=6, value=0)
        ws7.cell(row=r, column=7, value=0)
        ws7.cell(row=r, column=8, value=1.0)
        ws7.cell(row=r, column=9, value=f'=$B$5')
        ws7.cell(row=r, column=10, value=0)
        ws7.cell(row=r, column=11, value=0)
    else:
        ws7.cell(row=r, column=4, value=f'=B{r}-B{r-1}')
        ws7.cell(row=r, column=5, value=f'=IF(D{r}=0,0,(C{r-1}-C{r})/D{r})')
        ws7.cell(row=r, column=6, value=f'=E{r}*1000')
        # Simple velocity estimate: rough from gradient (user should override with proper Manning/channel type)
        ws7.cell(row=r, column=7, value=f'=IF(E{r}>=0.02,3.05,IF(E{r}>=0.01,1.52,0.91))')
        ws7.cell(row=r, column=8, value=1.0)  # default no attenuation for short steep reach; user edits
        style_input_cell(ws7.cell(row=r, column=8))
        ws7.cell(row=r, column=9, value=f'=H{r}*$B$5')
        # t_min = dx / (1.5 V) ; t_max = dx / V   in minutes
        ws7.cell(row=r, column=10, value=f'=IF(G{r}=0,0,D{r}/(1.5*G{r})/60)')
        ws7.cell(row=r, column=11, value=f'=IF(G{r}=0,0,D{r}/G{r}/60)')
    for c in range(1, 12):
        if c not in (1, 2, 3, 8):
            style_calc_cell(ws7.cell(row=r, column=c))
        ws7.cell(row=r, column=c).border = thin

# Summary travel time
ws7['A22'] = "CUMULATIVE TRAVEL TIME WINDOW"
ws7['A22'].font = font_header
ws7['A22'].fill = fill_header
ws7.merge_cells('A22:D22')

ws7['A23'] = "Total t_min (min)"
ws7['B23'] = '=SUM(J10:J20)'
style_calc_cell(ws7['B23'])
ws7['C23'] = "Total t_max (min)"
ws7['D23'] = '=SUM(K10:K20)'
style_calc_cell(ws7['D23'])

ws7['A24'] = "Total t_min (hr)"
ws7['B24'] = '=B23/60'
style_calc_cell(ws7['B24'])
ws7['C24'] = "Total t_max (hr)"
ws7['D24'] = '=D23/60'
style_calc_cell(ws7['D24'])

ws7.merge_cells('A26:K26')
ws7['A26'] = (
    "GUIDANCE:  Qx/Qp attenuation factors should be taken from published dam-break attenuation curves (function of distance and reservoir volume). "
    "For steep, narrow canyons attenuation may be negligible (Qx/Qp ≈ 1).  Flow velocities above are simplified placeholders – replace with Manning or observed values appropriate to the channel type (Tech Note 1 Table 7)."
)
ws7['A26'].font = font_small
ws7['A26'].fill = fill_note
ws7['A26'].alignment = Alignment(wrap_text=True)
ws7.row_dimensions[26].height = 40

# ============================================================
# Final adjustments & save
# ============================================================
# Freeze panes on key sheets
for ws in [ws1, ws2, ws3, ws4, ws5, ws6, ws7]:
    ws.freeze_panes = 'A2'

# Set print areas / page setup lightly
for ws in wb.worksheets:
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0

wb.save('/home/workdir/artifacts/Dam_Breach_Computational_Tool_v1.0.xlsx')
print("Workbook created successfully: Dam_Breach_Computational_Tool_v1.0.xlsx")
print("Sheets:", wb.sheetnames)