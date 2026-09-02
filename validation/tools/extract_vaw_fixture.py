#!/usr/bin/env python3
"""
Extract a ground-truth reference fixture from the live VAW workbook
(attachments/BFE_VAW_Impulse_Wave_Manual_Computational_Tool_v1-0.xlsm).

This does NOT read the file's cached values (they're blank in the shipped
template). It writes real inputs into a scratch copy, forces LibreOffice to
recalculate every formula, and reads back what the workbook's own formulas
compute. That gives a fixture that is provably what the reference tool
outputs for a given input set -- not a hand re-derivation of the paper
equations, which is exactly the failure mode that produced the Phase 11B
bugs (garbled PDF -> wrong coefficients).

Requires: openpyxl, LibreOffice (soffice) headless.

Usage:
    python3 extract_vaw_fixture.py --sheet 2d --out fixtures/2d_case_a.json \
        Vs=20 Vsbulk=50000 s=10 b=80 rhoS=1900 n=35 alpha=45 h=40 x=300

    python3 extract_vaw_fixture.py --sheet 3d --out fixtures/3d_case_a.json \
        Vs=20 Vsbulk=50000 s=10 b=80 rhoS=1900 n=35 alpha=45 h=40 r=300 gamma=0
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import openpyxl

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_XLSM = REPO_ROOT / "attachments" / "BFE_VAW_Impulse_Wave_Manual_Computational_Tool_v1-0.xlsm"

SHEET_NAMES = {
    "2d": "Generation | Propagation (2D)",
    "3d": "Generation | Propagation (3D)",
}

# input label -> (cell, sheet key it applies to)
INPUT_CELLS_2D = {
    "Vs": "F6", "Vsbulk": "F7", "s": "F8", "b": "F9", "rhoS": "F10",
    "n": "F11", "alpha": "F12", "h": "F13", "x": "F15",
}
INPUT_CELLS_3D = {
    "Vs": "F6", "Vsbulk": "F7", "s": "F8", "b": "F9", "rhoS": "F10",
    "n": "F11", "alpha": "F12", "h": "F13", "r": "F15", "gamma": "F16",
}

# result row -> label, per sheet (F column = main result, M column = dimensionless group)
RESULT_ROWS_2D = {
    "F_row16": 16, "S_row17": 17, "HM": 18, "aM": 19, "xM": 20, "TM": 21,
    "cXM": 22, "LM": 23, "Hx": 24, "ax": 25, "Tx": 26, "cx": 27, "Lx": 28,
}
RESULT_ROWS_3D = {
    "F_row18": 18, "r0_0": 19, "S_row19": 19, "r0_90": 20, "M_row20": 20,
    "r0_gamma": 21, "rstar": 22, "a0c1": 23, "a0t1": 24, "a0c2": 25,
    "ac1": 26, "at1": 27, "ac2": 28, "cc1": 29, "cc2": 30, "T1": 31,
}


def run(sheet_key: str, inputs: dict, out_path: Path) -> None:
    scratch = REPO_ROOT / "validation" / "tools" / "_scratch.xlsm"
    scratch_xlsx = scratch.with_suffix(".xlsx")
    shutil.copy(SOURCE_XLSM, scratch)

    wb = openpyxl.load_workbook(scratch, keep_vba=True)
    for ws in wb.worksheets:
        ws._images = []  # avoid CMYK-PNG save bug in openpyxl, images irrelevant to computation
    ws = wb[SHEET_NAMES[sheet_key]]
    cell_map = INPUT_CELLS_2D if sheet_key == "2d" else INPUT_CELLS_3D
    for key, cell in cell_map.items():
        if key in inputs:
            ws[cell] = inputs[key]
    wb.save(scratch)

    subprocess.run(
        ["soffice", "--headless", "--norestore", "--convert-to",
         "xlsx:Calc MS Excel 2007 XML", str(scratch)],
        cwd=scratch.parent, check=True, capture_output=True, timeout=90,
    )

    wb2 = openpyxl.load_workbook(scratch_xlsx, data_only=True)
    ws2 = wb2[SHEET_NAMES[sheet_key]]

    rows = RESULT_ROWS_2D if sheet_key == "2d" else RESULT_ROWS_3D
    results = {}
    for label, row in rows.items():
        results[f"{label}_F"] = ws2[f"F{row}"].value
        results[f"{label}_M"] = ws2[f"M{row}"].value

    fixture = {
        "source": "BFE_VAW_Impulse_Wave_Manual_Computational_Tool_v1-0.xlsm",
        "sheet": SHEET_NAMES[sheet_key],
        "inputs": inputs,
        "raw_cells": results,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(fixture, indent=2))
    print(f"Wrote {out_path}")

    scratch.unlink(missing_ok=True)
    scratch_xlsx.unlink(missing_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", choices=["2d", "3d"], required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("kv", nargs="+", help="key=value pairs, e.g. Vs=20 h=40")
    args = ap.parse_args()

    inputs = {}
    for pair in args.kv:
        k, v = pair.split("=")
        inputs[k] = float(v)

    run(args.sheet, inputs, Path(args.out))


if __name__ == "__main__":
    main()
