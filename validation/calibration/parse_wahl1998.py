"""Parse Wahl (1998) DSO-98-004 Table A1 (pages 62-65) into CSV by word positions."""
import csv, re, sys
import pdfplumber

PDF = sys.argv[1]
OUT = sys.argv[2]
pdf = pdfplumber.open(PDF)

def lines(pageno):
    p = pdf.pages[pageno - 1]
    ws = p.extract_words(x_tolerance=1.5)
    d = {}
    for w in ws:
        d.setdefault(round(w["top"] / 2), []).append(w)
    return [sorted(d[k], key=lambda w: w["x0"]) for k in sorted(d)]

def unit_row(L, key):
    for idx, l in enumerate(L):
        for w in l:
            if w["text"] == key:
                top = w["top"]
                band = [x for ll in L for x in ll if abs(x["top"] - top) < 4]
                return sorted(band, key=lambda x: x["x0"]), idx
    raise RuntimeError(key)

def parse_half(pages, unit_key, numeric_cols, text_cols, num_x_min):
    rows = {}
    for pg in pages:
        L = lines(pg)
        ur, ur_idx = unit_row(L, unit_key)
        # numeric column centres from the unit row, in order, right of num_x_min
        units = [w for w in ur if (w["x0"] + w["x1"]) / 2 > num_x_min]
        # merge 'Z:1' + '(h:v)' pairs
        merged = []
        for w in units:
            if merged and w["text"] == "(h:v)":
                merged[-1] = dict(merged[-1], x1=w["x1"])
            else:
                merged.append(w)
        centres = [(w["x0"] + w["x1"]) / 2 for w in merged]
        assert len(centres) == len(numeric_cols), (pg, [w["text"] for w in merged])
        started, cur = False, None
        for li, l in enumerate(L):
            if li <= ur_idx + 0:
                continue
            l = [w for w in l if all(abs(w["top"] - u["top"]) >= 4 for u in ur[:1])]
            if not l:
                continue
            first = l[0]
            if re.fullmatch(r"\d{1,3}", first["text"]) and first["x0"] < 90:
                cur = int(first["text"])
                rows[cur] = {c: "" for c in numeric_cols + list(text_cols)}
                words = l[1:]
            elif cur is None:
                continue
            else:
                words = l
            for w in words:
                c = (w["x0"] + w["x1"]) / 2
                placed = False
                for name, (lo, hi) in text_cols.items():
                    if lo <= w["x0"] < hi:
                        rows[cur][name] = (rows[cur][name] + " " + w["text"]).strip()
                        placed = True
                        break
                if placed or c < num_x_min:
                    continue
                k = min(range(len(centres)), key=lambda i: abs(centres[i] - c))
                rows[cur][numeric_cols[k]] = (rows[cur][numeric_cols[k]] + " " + w["text"]).strip()
    return rows

A = parse_half((62, 63), "m3/s",
               ["hd_m", "Wc_m", "Wb_m", "W_m", "Zu", "Zd", "L_m", "Qp_m3s"],
               {"name": (56, 160), "built": (160, 180), "failed": (180, 204), "mode": (204, 280),
                "construction": (280, 395), "refs": (395, 430), "Qp_method": (648, 800)}, 425)
B = parse_half((64, 65), "m4",
               ["S_m3", "A_m2", "Vw_m3", "hw_m", "Vwhw_m4", "shape", "hb_m", "Btop_m", "Bbot_m", "B_m", "Z", "Ver_m3",
                "tf1_h", "tf2_h", "tf3_h", "tf4_h"],
               {"name_b": (85, 190)}, 190)
ids = sorted(set(A) | set(B))
cols = ["id"] + list(next(iter(A.values())).keys()) + [k for k in next(iter(B.values())).keys() if k != "name_b"]
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for i in ids:
        r = {"id": i, **A.get(i, {}), **{k: v for k, v in B.get(i, {}).items() if k != "name_b"}}
        w.writerow(r)
print(len(ids), "rows; first/last", ids[0], ids[-1])
