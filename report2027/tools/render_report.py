#!/usr/bin/env python3
"""Render the Budget Primer FY2026-27 as a single HTML document.

Reads data/report_data.json and emits web/index.html. All charts are inline SVG
generated here, so the screen version and the Chrome-printed PDF are identical;
web/primer.js layers tooltips/hover on top for the interactive build.
"""
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content import Content, ContentError          # noqa: E402

HERE = Path(__file__).resolve().parent.parent
# Authored prose + sources. Synced from the Google Doc via `make pull-doc`.
C = Content(HERE / "content.md")
DATA = json.loads((HERE / "data" / "report_data.json").read_text())
BUD = DATA["budget"]
RES = DATA["research"]
REV = DATA["tax_revenue_fy2027"]
# FY2026 companions for the year-picker figures (3/4/5). Same category logic as
# FY2027; validated to reproduce the published FY2025-26 primer numbers.
BUD26 = DATA["budget_fy2026"]
REV26 = DATA["tax_revenue_fy2026"]

# General-fund obligated ("fixed") costs FY2018-27, hand-sourced from each
# biennium's Budget in Brief (p.18); see manual/obligated_costs.json for sources.
OBLIG = json.loads((HERE / "manual" / "obligated_costs.json").read_text())

# --- budget tracker interlink (same repo, docs/ SPA on GitHub Pages) ---
TRACKER = "https://dtomkatsu.github.io/BudgetPrimerFinal/"
_dept_src = json.loads(
    (HERE.parent / "docs" / "js" / "departments_act175_fy2027.json").read_text())
_hist = json.loads(
    (HERE.parent / "docs" / "js" / "historical_trends.json").read_text())
_hist_by_dept = {d["dept_code"]: [round(p["nominal"] / 1e6) for p in d["series"]]
                 for d in _hist["by_department"]}
_hist_fys = [p["fy"] for p in _hist["by_department"][0]["series"]]

_SMALL_WORDS = {"a", "an", "and", "as", "at", "by", "for", "in", "of", "on",
                "or", "the", "to", "with"}
_ACRONYMS = {"UH", "OHA", "HHSC", "EUTF", "EMS", "IT", "TANF", "DNA", "ADA"}

def smart_title(name):
    """ALL-CAPS act program names -> title case with small words and acronyms."""
    def cap(word):
        if word.upper() in _ACRONYMS:
            return word.upper()
        return "-".join(w[:1].upper() + w[1:].lower() for w in word.split("-"))
    words = name.split()
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if 0 < i < len(words) - 1 and lw.strip(",") in _SMALL_WORDS:
            out.append(lw)
        else:
            out.append(cap(w))
    return " ".join(out)

# split on sentence-ending periods only — a period preceded by an uppercase
# letter (e.g. "John A. Burns", "U.S.") is almost always a mid-name initial or
# abbreviation, not a sentence boundary, so it's excluded from the split.
_SENTENCE_SPLIT = re.compile(r"(?<![A-Z])\.\s+(?=[A-Z])")

DEPT_INFO = {}
for _d in _dept_src:
    desc = _SENTENCE_SPLIT.split((_d.get("description") or "").strip())
    # aggregate fund-line rows into whole programs, mirroring the tracker's dept page
    progs = {}
    for _p in _d["programs"]:
        key = _p["program_id"]
        progs.setdefault(key, {"n": smart_title(_p["program_name"]), "v": 0})
        progs[key]["v"] += _p["amount"]
    top = sorted(progs.values(), key=lambda r: -r["v"])[:4]
    DEPT_INFO[_d["code"]] = {
        "name": _d["name"],
        "blurb": ". ".join(desc[:2]) + ("." if desc[:2] and not desc[1 if len(desc) > 1 else 0].endswith(".") else ""),
        "operating": _d.get("operating_budget", 0) or 0,
        "capital": _d.get("capital_budget", 0) or 0,
        "positions": round(_d.get("positions") or 0),
        "programs": [[r["n"], round(r["v"])] for r in top],
        "nprogs": len(progs),
        "hist": _hist_by_dept.get(_d["code"]),
        "url": f"{TRACKER}#/department/{_d['id']}",
    }
HIST_FY_SPAN = [_hist_fys[0], _hist_fys[-1]]

# ---------- palette (Hawaiʻi Appleseed brand) ----------
# Muted Teal (logo) / light teal / Ash Grey + light tints; Deep Teal, Dark Slate
# Grey, Charcoal Blue for the darks. Keep in sync with the vars in primer.css.
SAGE, SAGE_MID, SAGE_LIGHT, MINT, PALE = "#6B9E78", "#95B7A2", "#CAD2C5", "#E8EDE6", "#D6E0D2"
DARK, FOREST, DARKEST = "#52796F", "#354F52", "#2F3E46"
INK = "#2F3E46"
SERIES = {"operating": SAGE, "capital": SAGE_MID, "one_time": DARK, "emergency": DARKEST}

def is_light_bg(hexc):
    """True when a fill is light enough to need dark (not white) text. The brand's
    Muted Teal / Ash Grey tiles read best with charcoal text; only Deep Teal,
    Dark Slate, and Charcoal Blue take reversed (white) text."""
    h = hexc.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) > 130

# ---------- formatting ----------
def words(n):
    """$19.88 billion / $450.67 million / $684,385 / $0 — original Table 1 style."""
    if n == 0:
        return "$0"
    for div, unit in ((1e9, "billion"), (1e6, "million")):
        if n >= div:
            v = f"{n / div:.2f}".rstrip("0").rstrip(".")
            return f"${v} {unit}"
    return f"${n:,.0f}"

def short(n):
    """$4.8B / $659M / $80.7M / $2.56M — original chart-label style."""
    if n >= 1e9:
        return f"${n / 1e9:.1f}".rstrip("0").rstrip(".") + "B"
    m = n / 1e6
    if m >= 100:
        return f"${m:.0f}M"
    if m >= 10:
        return f"${m:.1f}".rstrip("0").rstrip(".") + "M"
    return f"${m:.2f}".rstrip("0").rstrip(".") + "M"

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")

# ---------- research-derived numbers ----------
JUD = RES["branches_fy2027"]["judiciary"]
LEG = RES["branches_fy2027"]["legislature"]
OHA = RES["branches_fy2027"]["oha"]
FEATURED = RES["one_time_fy2027"]["featured"]
EMERG27 = RES["emergency_fy2027"]

# featured acts only, like the FY26 edition; Act 32 ($55M PLT) counts in the OHA
# column, not Executive, so it is excluded here.
EXEC_ONE_TIME = sum(f["amount"] for f in FEATURED if not f["act"].startswith("Act 032"))
EXEC_EMERG = sum(e["amount_fy27"] for e in EMERG27)
JUD_ONE_TIME = 684385                                        # Act 126 juror pay
OHA_ONE_TIME = 55000000                                      # Act 32 PLT transfer

EXEC_OP = BUD["executive"]["operating"]
EXEC_CIP = BUD["executive"]["capital"] + BUD["executive"]["county_cip_grants"]

# one-time / emergency dept mapping for Figure 2 segments (featured acts)
ONE_TIME_BY_DEPT = {"TRN": 612e6, "AGS": 176e6, "LNR": 12e6, "BUF": 100e6,
                    "BED": 49.5e6, "UOH": 28.5e6, "HMS": 16.5e6, "EDN": 3.365e6}
EMERG_BY_DEPT = {"BUF": EXEC_EMERG}

# Per-branch figures by fiscal year, for Table 1 and Figure 2's branch rows.
# Executive op/cip come from the Budget Tracker (Act 175). Judiciary/Legislature/
# OHA op/cip are research-derived for FY2027; for FY2026 they are the published
# FY2025-26 primer figures (the tracker carries no branch data). One-time and
# emergency appropriations are researched totals.
BRANCHES_BY_FY = {
    2027: {
        "exec": {"op": EXEC_OP, "cip": EXEC_CIP, "one": EXEC_ONE_TIME, "emerg": EXEC_EMERG},
        "jud":  {"op": JUD["operating_fy27"], "cip": JUD["cip_fy27"], "one": JUD_ONE_TIME, "emerg": 0},
        "leg":  {"op": LEG["total_fy27_published_style"], "cip": 0, "one": 0, "emerg": 0},
        "oha":  {"op": OHA["operating_fy27"], "cip": 0, "one": OHA_ONE_TIME, "emerg": 0},
    },
    2026: {
        "exec": {"op": BUD26["executive"]["operating"],
                 "cip": BUD26["executive"]["capital"] + BUD26["executive"]["county_cip_grants"],
                 "one": 450_670_000, "emerg": 121_830_000},
        "jud":  {"op": 214_570_000, "cip": 12_900_000, "one": 0, "emerg": 4_700_000},
        "leg":  {"op": 51_630_000, "cip": 0, "one": 0, "emerg": 0},
        "oha":  {"op": 6_000_000, "cip": 0, "one": 0, "emerg": 0},
    },
}
FY_LABEL = {2026: "FY 2025–2026", 2027: "FY 2026–2027"}
# county CIP grants ride in the tracker's dept list but are footnoted, not charted
FIG2_COUNTY_CODES = {"COM", "COH", "CCH", "COK"}

# ---------- svg helpers ----------
def arc_path(cx, cy, r1, r2, a0, a1):
    """Annular sector path. Angles in degrees, 0 = 12 o'clock, clockwise."""
    def pt(r, a):
        rad = math.radians(a - 90)
        return cx + r * math.cos(rad), cy + r * math.sin(rad)
    large = 1 if (a1 - a0) > 180 else 0
    x0, y0 = pt(r2, a0); x1, y1 = pt(r2, a1)
    x2, y2 = pt(r1, a1); x3, y3 = pt(r1, a0)
    return (f"M{x0:.1f},{y0:.1f} A{r2},{r2} 0 {large} 1 {x1:.1f},{y1:.1f} "
            f"L{x2:.1f},{y2:.1f} A{r1},{r1} 0 {large} 0 {x3:.1f},{y3:.1f} Z")

def pie(slices, size=400, r=158, cls="", width_in=3.6, label_pt=14.0, start=0.0, attrs=""):
    """slices: [(name, value, color, label_lines)] clockwise from 12 o'clock.

    size leaves room around the r=158 disc for the outside labels of thin slices,
    which can sit ~40px beyond the rim plus their own text width.

    The SVG scales to width_in on the page, so a user unit is
    (width_in / size) inches. label_pt is converted into user units accordingly,
    which is how the original's per-figure label sizes (13.7-15.5pt) are matched.
    """
    unit_pt = width_in / size * 72.0
    lab_u = label_pt / unit_pt
    dy = lab_u * 1.08
    cx = cy = size / 2
    total = sum(s[1] for s in slices)
    a = start
    paths, labels = [], []
    small_n = 0
    for name, val, color, lab in slices:
        sweep = 360 * val / total
        paths.append(f'<path d="{arc_path(cx, cy, 0, r, a, a + sweep)}" fill="{color}" '
                     f'class="iv" data-tip="{esc(name)}: {short(val)}"/>')
        mid = math.radians(a + sweep / 2 - 90)
        big = sweep > 55
        lr = r * 0.62 if big else r + 18
        if sweep < 26:                       # stagger consecutive small-slice labels
            lr = r + (14 + 18 * (small_n % 2))
            small_n += 1
        lx, ly = cx + lr * math.cos(mid), cy + lr * math.sin(mid)
        anchor = "middle" if big else ("start" if math.cos(mid) > 0.25 else
                                       "end" if math.cos(mid) < -0.25 else "middle")
        ty = ly - (len(lab) - 1) * dy / 2
        # keep multi-line labels inside the viewBox
        ty = min(max(ty, lab_u), size - 4 - (len(lab) - 1) * dy)
        lx = min(max(lx, 6), size - 6)
        t = "".join(f'<tspan x="{lx:.0f}" dy="{dy:.0f}" >{l}</tspan>' if i else
                    f'<tspan x="{lx:.0f}">{l}</tspan>' for i, l in enumerate(lab))
        # a label sitting inside a dark slice needs reversed (white) text
        lab_fill = ' fill="#fff"' if (big and not is_light_bg(color)) else ''
        labels.append(f'<text x="{lx:.0f}" y="{ty:.0f}" text-anchor="{anchor}" '
                      f'class="pie-lab"{lab_fill} font-size="{lab_u:.1f}">{t}</text>')
        a += sweep
    return (f'<svg viewBox="0 0 {size} {size}" class="chart pie {cls}"{attrs} '
            f'preserveAspectRatio="xMidYMid meet" role="img">'
            + "".join(paths) + "".join(labels) + "</svg>")

def legend(items):
    rows = "".join(
        f'<div class="lg"><span class="sw" style="background:{c}"></span>{esc(n)}</div>'
        for n, c in items)
    return f'<div class="legend">{rows}</div>'

# Display bands for the obligated-costs stacked area, bottom -> top. Certificate
# of Participation (a lease-financing debt instrument, <0.1%) folds into Debt
# Service so the stack total equals the BIB "Fixed Sub-total" exactly.
OBLIG_BANDS = [
    ("Retirement (ERS)", ["Retirement System"], DARK),
    ("Health Benefits (EUTF)", ["Health Fund"], SAGE),
    ("Medicaid & Entitlements", ["Medicaid & Entitlements"], SAGE_MID),
    ("Debt Service", ["Debt Service", "Certificate of Participation"], SAGE_LIGHT),
]

def fig_obligated():
    """Stacked-area chart of general-fund obligated costs, FY2018-FY2027."""
    series = OBLIG["series"]
    years = sorted(int(y) for y in series)
    def val(fy, keys):
        return sum(series[str(fy)][k] for k in keys)
    def bill(n):
        return f"${n / 1e9:.2f}B"
    W, H, L, R, TM, BM = 720, 400, 60, 14, 22, 30
    pw, ph = W - L - R, H - TM - BM
    ymax = 5.5e9
    def X(i):
        return L + pw * i / (len(years) - 1)
    def Y(v):
        return TM + ph * (1 - v / ymax)
    out = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img">']
    for gb in range(0, 6):                                   # $0-$5B gridlines
        y = Y(gb * 1e9)
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" stroke="#D7DEDC" stroke-width="1"/>')
        out.append(f'<text x="{L-8}" y="{y+4:.1f}" text-anchor="end" class="ax">${gb}B</text>')
    for i, fy in enumerate(years):                           # x-axis year labels
        out.append(f'<text x="{X(i):.1f}" y="{H-10}" text-anchor="middle" class="ax">FY{str(fy)[2:]}</text>')
    cum = [0.0] * len(years)                                 # stacked bands
    band_tops = []
    for name, keys, color in OBLIG_BANDS:
        top = [cum[i] + val(fy, keys) for i, fy in enumerate(years)]
        pts = ([f"{X(i):.1f},{Y(top[i]):.1f}" for i in range(len(years))]
               + [f"{X(i):.1f},{Y(cum[i]):.1f}" for i in reversed(range(len(years)))])
        out.append(f'<polygon points="{" ".join(pts)}" fill="{color}" stroke="#fff" stroke-width="0.7"/>')
        band_tops.append(top)
        cum = top
    # data-point dots at each year on every band's top line
    for top in band_tops:
        for i in range(len(years)):
            out.append(f'<circle cx="{X(i):.1f}" cy="{Y(top[i]):.1f}" r="2.3" '
                       f'fill="#fff" stroke="{FOREST}" stroke-width="1"/>')
    all_keys = [k for _, ks, _ in OBLIG_BANDS for k in ks]
    total0, totalN = val(years[0], all_keys), val(years[-1], all_keys)
    # endpoint total labels (first year above stack, last year above stack)
    out.append(f'<text x="{X(0)+2:.1f}" y="{Y(total0)-7:.1f}" class="vlab">{bill(total0)}</text>')
    out.append(f'<text x="{X(len(years)-1)-2:.1f}" y="{Y(totalN)-7:.1f}" text-anchor="end" class="vlab">{bill(totalN)}</text>')
    for i, fy in enumerate(years):                           # per-year hover zones
        parts = " · ".join(f"{nm.split(' (')[0]} {bill(val(fy, ks))}" for nm, ks, _ in OBLIG_BANDS)
        tip = f"FY{fy} — Obligated total {bill(val(fy, all_keys))} · {parts}"
        out.append(f'<rect x="{X(i)-14:.1f}" y="{TM}" width="28" height="{ph}" fill="transparent" '
                   f'pointer-events="all" class="iv" data-tip="{esc(tip)}"/>')
    out.append("</svg>")
    return "".join(out)

def fig2_rows_for(year):
    """Branch + department rows for Figure 2. FY2027 carries per-department
    one-time/emergency overlays; FY2026 (tracker op/cap only) shows just
    operating + capital, since no FY2026 per-department overlay data exists."""
    b = BRANCHES_BY_FY[year]
    budget = BUD if year == 2027 else BUD26
    overlays = (year == 2027)
    j, l, o = b["jud"], b["leg"], b["oha"]
    rows = [  # branch rows first, like the original (no tracker page -> code None)
        ("Judiciary", {"operating": j["op"], "capital": j["cip"],
                       "one_time": j["one"] if overlays else 0, "emergency": 0}, None),
        ("Legislature", {"operating": l["op"], "capital": l["cip"],
                         "one_time": 0, "emergency": 0}, None),
        ("OHA", {"operating": o["op"], "capital": o["cip"],
                 "one_time": o["one"] if overlays else 0, "emergency": 0}, None),
    ]
    for d in budget["figure2_departments"]:
        if d["code"] in FIG2_COUNTY_CODES:
            continue
        rows.append((d["label"], {"operating": d["operating"], "capital": d["capital"],
                                  "one_time": ONE_TIME_BY_DEPT.get(d["code"], 0) if overlays else 0,
                                  "emergency": EMERG_BY_DEPT.get(d["code"], 0) if overlays else 0},
                     d["code"] if d["code"] in DEPT_INFO else None))
    return rows

def fig2_chart_for(year):
    return fig2_svg(fig2_rows_for(year), attrs=f' data-fig="fig2" data-fy="{year}"'
                    + ("" if year == 2027 else " hidden"))

def fig2_svg(rows, attrs=""):
    W, LEFT, RH, GAP = 720, 150, 17, 7
    maxv = 5.5e9
    plot_w = W - LEFT - 60
    H = len(rows) * (RH + GAP) + 40
    out = [f'<svg viewBox="0 0 {W} {H}" class="chart"{attrs} role="img">']
    for gx in range(0, 6):
        x = LEFT + plot_w * gx / 5.5
        out.append(f'<line x1="{x:.0f}" y1="0" x2="{x:.0f}" y2="{H-34}" stroke="#D7DEDC" stroke-width="1"/>')
        out.append(f'<text x="{x:.0f}" y="{H-18}" text-anchor="middle" class="ax">${gx}B</text>')
    y = 4
    for label, seg, code in rows:
        total = sum(seg.values())
        dept_attr = f' data-dept="{code}"' if code else ""
        out.append(f'<text x="{LEFT-8}" y="{y+RH-4}" text-anchor="end" '
                   f'class="ylab{" lk" if code else ""}"{dept_attr}>{esc(label)}</text>')
        x = LEFT
        for key in ("operating", "capital", "one_time", "emergency"):
            v = seg[key]
            if v <= 0:
                continue
            w = plot_w * v / maxv
            tip = f"{label} — {key.replace('_', '-').title()}: {short(v)}"
            if code:
                tip += " · click for tracker link"
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{max(w,0.8):.1f}" height="{RH}" '
                       f'fill="{SERIES[key]}" class="iv" data-tip="{esc(tip)}"{dept_attr}/>')
            x += w
        if x + 44 > W:                        # widest bars: label inside, white
            out.append(f'<text x="{x-6:.0f}" y="{y+RH-4}" text-anchor="end" class="vlab" '
                       f'fill="#fff">{short(total)}</text>')
        else:
            out.append(f'<text x="{x+5:.0f}" y="{y+RH-4}" class="vlab">{short(total)}</text>')
        y += RH + GAP
    out.append("</svg>")
    return "".join(out)

# Each lifecycle callout owns a contiguous run of months; brackets outside the
# month ring make that span explicit rather than leaving it to proximity.
LIFECYCLE_SPANS = [
    # key, label, first month, last month, text, side  (label/text from content.md)
    (k, C.text(f"process.lifecycle.{k}.label"), m0, m1,
     C(f"process.lifecycle.{k}.text"), side)
    for k, m0, m1, side in [
        ("dec", 11, 11, "top"), ("jan", 0, 3, "right"), ("may", 4, 4, "right"),
        ("jun", 5, 5, "bottom"), ("jul", 6, 6, "left"), ("aug", 7, 8, "left"),
        ("oct", 9, 10, "left"),
    ]
]

# Geometry shared by the wheel SVG and the callout placement, so the text always
# sits at the end of its bracket stub rather than at a hand-tuned coordinate.
LC_VIEWBOX = 560            # svg user units
LC_SVG_IN = 5.8             # rendered width  (see .lifecycle-wrap svg)
LC_WRAP_IN = 6.9            # containing block width
LC_MARGIN_IN = 0.28         # svg's vertical margin inside the wrap
LC_STUB_U = 178 + 13        # bracket radius + stub length, in user units
LC_CALLOUT_IN = 1.58        # .lc width
LC_PAD_IN = 0.12            # gap past the stub end, measured along the stub
LC_TOP_PAD_IN = 0.38        # DEC grows upward into the wheel; give it more room
LC_EDGE_IN = 0.16           # top/bottom blocks overhang their stub by this much


def lifecycle_callouts():
    """Place each callout just past the end of its bracket stub.

    The offset is applied along the stub's own radial direction, not horizontally:
    a fixed x-offset leaves the diagonal callouts (MAY, AUG-SEP, OCT-NOV) visibly
    farther from their brackets than the ones due N/E/S/W.
    """
    unit = LC_SVG_IN / LC_VIEWBOX
    cx = (LC_WRAP_IN - LC_SVG_IN) / 2 + LC_SVG_IN / 2
    cy = LC_MARGIN_IN + LC_SVG_IN / 2
    out = []
    for key, lab, m0, m1, txt, side in LIFECYCLE_SPANS:
        amid = (m0 * 30 + 2 + (m1 + 1) * 30 - 2) / 2
        rad = math.radians(amid - 90)
        pad = LC_TOP_PAD_IN if side == "top" else LC_PAD_IN
        r = LC_STUB_U * unit + pad
        x, y = cx + r * math.cos(rad), cy + r * math.sin(rad)
        if side == "right":
            style = f"left:{x:.2f}in;top:{y:.2f}in"
        elif side == "left":                       # text is right-aligned to x
            style = f"left:{x - LC_CALLOUT_IN:.2f}in;top:{y:.2f}in"
        else:
            # top/bottom text is left-aligned, so start the block at the stub
            # rather than centring the box on it — a centred box puts its visual
            # mass (and its bold month label) to the left of the bracket.
            style = f"left:{x - LC_EDGE_IN:.2f}in;top:{y:.2f}in"
        out.append(f'<div class="lc lc-{side}" style="{style}">'
                   f'<span class="lc-mo">{lab}</span>{txt}</div>')
    return "".join(out)

def fig1_lifecycle(size=560):
    cx = cy = size / 2
    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    ramp = ["#EAEFEA", "#D9E3DB", "#C6D6CB", "#B2C7BA", "#9EB8A8", "#89AB94",
            "#6B9E78", "#5C8A70", "#4F7865", "#44645B", "#3A5254", "#2F3E46"]
    out = [f'<svg viewBox="0 0 {size} {size}" class="chart" role="img">']
    r1, r2 = 118, 168

    def polar(r, a):
        rad = math.radians(a - 90)
        return cx + r * math.cos(rad), cy + r * math.sin(rad)
    for i, m in enumerate(months):
        a0 = i * 30
        out.append(f'<path d="{arc_path(cx, cy, r1, r2, a0 + 1, a0 + 29)}" fill="{ramp[i]}"/>')
        ang = a0 + 15
        mid = math.radians(ang - 90)
        tx, ty = cx + 143 * math.cos(mid), cy + 143 * math.sin(mid)
        rot = ang - 180 if 90 < ang < 270 else ang   # tangential, never upside down
        fill = "#fff" if i >= 8 else INK
        # Center the glyphs on (tx,ty) and rotate about that same point: a baseline
        # nudge applied before the rotation gets rotated with it, which threw the
        # flipped labels (APR-SEP, worst at MAY) off-center inside their segments.
        out.append(f'<text x="{tx:.0f}" y="{ty:.0f}" class="mo" fill="{fill}" '
                   f'text-anchor="middle" dominant-baseline="central" '
                   f'transform="rotate({rot:.0f},{tx:.0f},{ty:.0f})">{m}</text>')

    # brackets: arc over the span, inward end ticks, outward stub toward the text
    br = r2 + 10
    for _key, _lab, m0, m1, _txt, _side in LIFECYCLE_SPANS:
        a0, a1 = m0 * 30 + 2, (m1 + 1) * 30 - 2
        amid = (a0 + a1) / 2
        large = 1 if (a1 - a0) > 180 else 0
        x0, y0 = polar(br, a0); x1, y1 = polar(br, a1)
        out.append(f'<path d="M{x0:.1f},{y0:.1f} A{br},{br} 0 {large} 1 {x1:.1f},{y1:.1f}" class="brk"/>')
        for a in (a0, a1):
            ix, iy = polar(br - 6, a); ox, oy = polar(br, a)
            out.append(f'<line x1="{ix:.1f}" y1="{iy:.1f}" x2="{ox:.1f}" y2="{oy:.1f}" class="brk"/>')
        sx, sy = polar(br, amid); ex, ey = polar(br + 13, amid)
        out.append(f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" class="brk"/>')

    # Arc spans are sized to the label that rides on them: at pr the arc length
    # must exceed the rendered text width, or textPath silently truncates.
    phases = [(esc(C.text("process.ring.legislative")), 0, 150, DARK),
              (esc(C.text("process.ring.planning")), 150, 258, SAGE_LIGHT),
              (esc(C.text("process.ring.prep")), 258, 360, MINT)]
    for i, (name, a0, a1, col) in enumerate(phases):
        out.append(f'<path d="{arc_path(cx, cy, 72, 116, a0 + 1, a1 - 1)}" fill="{col}"/>')
        pr = 100
        # curved phase label
        f0, f1 = (a0 + 3, a1 - 3)
        p0 = (cx + pr * math.cos(math.radians(f0 - 90)), cy + pr * math.sin(math.radians(f0 - 90)))
        p1 = (cx + pr * math.cos(math.radians(f1 - 90)), cy + pr * math.sin(math.radians(f1 - 90)))
        large = 1 if (f1 - f0) > 180 else 0
        flip = 90 < (a0 + a1) / 2 < 270
        d = (f"M{p1[0]:.0f},{p1[1]:.0f} A{pr},{pr} 0 {large} 0 {p0[0]:.0f},{p0[1]:.0f}" if flip
             else f"M{p0[0]:.0f},{p0[1]:.0f} A{pr},{pr} 0 {large} 1 {p1[0]:.0f},{p1[1]:.0f}")
        tc = INK if is_light_bg(col) else "#fff"
        out.append(f'<defs><path id="ph{i}" d="{d}"/></defs>'
                   f'<text class="ph" fill="{tc}"><textPath href="#ph{i}" startOffset="50%" '
                   f'text-anchor="middle">{name}</textPath></text>')
    out.append("</svg>")
    return "".join(out)

def fig6_chart():
    data = [("Lowest 20%", "Less than $21,900", 14.1), ("Second 20%", "$21,900–$44,200", 13.7),
            ("Middle 20%", "$44,200–$80,100", 14.2), ("Fourth 20%", "$80,100–$136,600", 13.4),
            ("Next 15%", "$136,600–$278,200", 11.8), ("Next 4%", "$278,200–$594,900", 10.2),
            ("Top 1%", "Over $594,900", 10.1)]
    # Geometry matched to the original: bar width 58.6pt, tallest bar 195.8pt,
    # value 14pt / quintile 11.9pt / range 10.6pt. The SVG renders 720u across
    # the 7.26in text column, so 1u = 0.726pt.
    W, H, BW = 720, 390, 80
    BASE, MAXH = 300, 285          # 285u = 207pt tall for the 15% gridline
    gap = (W - 40 - 7 * BW) / 6
    out = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img">']
    for i, (q, rng, v) in enumerate(data):
        x = 20 + i * (BW + gap)
        h = (v / 15) * MAXH
        y = BASE - h
        out.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{BW}" height="{h:.0f}" fill="{SAGE}" '
                   f'class="iv" data-tip="{q} ({rng}): {v}% of income"/>')
        out.append(f'<text x="{x+BW/2:.0f}" y="{y-10:.0f}" text-anchor="middle" class="vlab b">{v}%</text>')
        # quintile name reads as the category; the income range is secondary detail
        out.append(f'<text x="{x+BW/2:.0f}" y="{BASE+24:.0f}" text-anchor="middle" class="qlab">{q}</text>')
        out.append(f'<text x="{x+BW/2:.0f}" y="{BASE+43:.0f}" text-anchor="middle" class="rlab">{rng.split("–")[0] if "–" in rng else rng}</text>')
        if "–" in rng:
            out.append(f'<text x="{x+BW/2:.0f}" y="{BASE+60:.0f}" text-anchor="middle" class="rlab">–{rng.split("–")[1]}</text>')
    out.append(f'<line x1="16" y1="{BASE}" x2="{W-16}" y2="{BASE}" stroke="{INK}" stroke-width="1"/></svg>')
    return "".join(out)

# ---------- figure data (year-parameterized for the FY26/FY27 picker) ----------
FIG3_ORDER = ["Transportation", "Formal Education", "All Others", "Economic Development", "Health"]
FIG3_COLORS = [DARK, SAGE_MID, SAGE_LIGHT, MINT, PALE]
FIG4_ORDER = ["General Funds", "Special Funds", "Federal Funds", "Other Funds"]

def fig3_slices_for(budget):
    f3 = budget["figure3_cip"]
    return [(k, f3[k], c, [f"${f3[k]/1e6:,.0f}"]) for k, c in zip(FIG3_ORDER, FIG3_COLORS)]

def fig4_slices_for(budget):
    f4 = budget["figure4_means_of_finance"]
    tot = sum(f4.values())
    return [(k, f4[k], c, [f"${f4[k]/1e9:.1f}", f"({f4[k]/tot*100:.1f}%)"])
            for k, c in zip(FIG4_ORDER, FIG3_COLORS)]

def fig5_slices_for(rev):
    get_, iit = rev["General Excise and Use Tax"], rev["Individual Income Tax"]
    tat, corp = rev["Transient Accommodations Tax"], rev["Corporate Income Tax"]
    other_tax = rev["GENERAL FUND TOTAL"] - get_ - iit - tat - corp
    return [(n, v, c, [f"${v/1e9:.2f}", f"({v/rev['GENERAL FUND TOTAL']*100:.1f}%)"])
            for (n, v), c in zip(
        [("General Excise Tax", get_), ("Individual Income Tax", iit),
         ("Transient Accommodations Tax", tat), ("All Other Taxes", other_tax),
         ("Corporate Income Tax", corp)], FIG3_COLORS)]

def cip_total_for(budget):
    return sum(budget["figure3_cip"].values())

# ---------- year-picker plumbing (Figures 2/3/4/5 + Table 1) ----------
def fy_picker(fig_id, label27="FY2027", label26="FY2026"):
    """Inline FY selector that replaces a hard-coded year in a figure caption."""
    return (f'<select class="fy-pick" data-fig="{fig_id}" aria-label="Fiscal year">'
            f'<option value="2027">{label27}</option>'
            f'<option value="2026">{label26}</option></select>')

def fy_pie_swap(fig_id, slices27, slices26, **kw):
    """Both years' pies as sibling flex items; FY2026 starts hidden."""
    return (pie(slices27, attrs=f' data-fig="{fig_id}" data-fy="2027"', **kw)
            + pie(slices26, attrs=f' data-fig="{fig_id}" data-fy="2026" hidden', **kw))

# ---------- page shells ----------
def card(title, bullets, bg, light=None):
    if light is None:                       # auto: dark text on light tiles
        light = is_light_bg(bg)
    cls = "card light" if light else "card"
    lis = "".join(f"<li>{b}</li>" for b in bullets)
    return f'<div class="{cls}" style="background:{bg}"><h4>{title}</h4><ul>{lis}</ul></div>'

def endnote_link(n, txt, url):
    return f'<li id="en{n}">{txt} <a href="{url}">{url}</a></li>'

ONE_TIME_BULLETS = C.list("onetime.cards.onetime.bullets")
EMERG_BULLETS = C.list("onetime.cards.emergency.bullets")

def table1_for(year):
    b = BRANCHES_BY_FY[year]
    e, j, l, o = b["exec"], b["jud"], b["leg"], b["oha"]
    def tot(c):
        return c["op"] + c["cip"] + c["one"] + c["emerg"]
    hidden = "" if year == 2027 else " hidden"
    return f"""<table class="t1" data-fig="table1" data-fy="{year}"{hidden}>
<thead><tr><th></th><th class="lk" data-dept="__all">{C("table1.header.executive")}</th><th>{C("table1.header.judiciary")}</th>
<th>{C("table1.header.legislature")}</th><th>{C("table1.header.oha")}</th></tr></thead>
<tbody>
<tr><td>Operating Budget</td><td>{words(e['op'])}</td><td>{words(j['op'])}</td>
<td>{words(l['op'])}</td><td>{words(o['op'])}</td></tr>
<tr><td>Capital Improvement Appropriations</td><td>{words(e['cip'])}</td>
<td>{words(j['cip'])}</td><td>{words(l['cip'])}</td><td>{words(o['cip'])}</td></tr>
<tr><td>One-Time Appropriations</td><td>{words(e['one'])}</td><td>{words(j['one'])}</td>
<td>{words(l['one'])}</td><td>{words(o['one'])}</td></tr>
<tr><td>Emergency Appropriations</td><td>{words(e['emerg'])}</td><td>{words(j['emerg'])}</td>
<td>{words(l['emerg'])}</td><td>{words(o['emerg'])}</td></tr>
<tr class="total"><td>Total</td>
<td>{words(tot(e))}</td><td>{words(tot(j))}</td>
<td>{words(tot(l))}</td><td>{words(tot(o))}</td></tr>
</tbody></table>"""

pages = []

# -- page 1: cover
pages.append(f"""
<section class="page cover">
 <div class="ribbon r1"></div><div class="ribbon r2"></div>
 <div class="ribbon r3"></div><div class="ribbon r4"></div>
 <div class="cover-inner">
  <div class="logo-lockup"><img class="logo-img" src="assets/appleseed-logo.svg"
   alt="Hawaiʻi Appleseed — Center for Law &amp; Economic Justice"></div>
  <h1 class="cover-title">HAWAIʻI<br>BUDGET<br>PRIMER</h1>
  <div class="cover-year">FY2026–27</div>
 </div>
</section>""")

# -- page 2: about / TOC
pages.append(f"""
<section class="page toc-page">
 <div class="toc-head">
  <div class="logo-lockup light"><img class="logo-img" src="assets/appleseed-logo-white.svg"
   alt="Hawaiʻi Appleseed — Center for Law &amp; Economic Justice"></div>
  <p class="toc-link"><a href="https://hiappleseed.org">www.hiappleseed.org</a></p>
  <p class="toc-author">{C.text("toc.author")}</p>
 </div>
 {C.html("toc.mission1", "mission")}
 {C.html("toc.mission2", "mission")}
 <h2 class="toc-title">{C.text("toc.title")}</h2>
 <div class="toc-list">
  <div><span>Budget Basics</span><span>3</span></div>
  <div><span>How Money Is Spent</span><span>5</span></div>
  <div><span>Funding the Budget</span><span>9</span></div>
  <div><span>Endnotes</span><span>12</span></div>
 </div>
 <p class="copyright">{"<br>".join(esc(l) for l in C.lines("toc.copyright"))}</p>
 <div class="folio">2 • BUDGET PRIMER</div>
</section>""")

# -- page 3: budget basics
branch_cards = [
    (C.text(f"basics.branch.{k}.title"), bg, img, lt, C.list(f"basics.branch.{k}.bullets"))
    for k, bg, img, lt in [
        ("legislature", DARK, "branch-0.jpg", True),
        ("judiciary", SAGE_MID, "branch-1.jpg", False),
        ("executive", SAGE_LIGHT, "branch-2.jpg", False),
        ("oha", MINT, "branch-3.jpg", False),
    ]
]
bc = "".join(
    f'<div class="branch"><img src="assets/{img}" alt="{t}">'
    f'<div class="branch-card{" onlight" if is_light_bg(bg) else ""}" style="background:{bg}">'
    f'<h4>{t}</h4><ul>' + "".join(f"<li>{b}</li>" for b in bl) + "</ul></div></div>"
    for t, bg, img, lt, bl in branch_cards)
pages.append(f"""
<section class="page">
 <h1>{C.text("basics.h1")}</h1>
 {C.html("basics.p1")}
 {C.html("basics.p2")}
 {bc}
 <div class="folio r">BUDGET PRIMER • 3</div>
</section>""")

# -- page 4: budget process
pages.append(f"""
<section class="page">
 <h2 class="sub">{C.text("process.h2")}</h2>
 {C.html("process.p1")}
 <p class="figcap"><b>Figure 1.</b> {C.text("process.fig1.caption")}</p>
 <div class="lifecycle-wrap">
  {fig1_lifecycle()}
  {lifecycle_callouts()}
 </div>
 <div class="folio">4 • BUDGET PRIMER</div>
</section>""")

# -- page 5: how money is spent
pages.append(f"""
<section class="page">
 <h1>{C.text("spent.h1")}</h1>
 {C.html("spent.p1")}
 {C.html("spent.p2")}
 <div class="cards3">
  {card(C.text("spent.cards.operating.title"), C.list("spent.cards.operating.bullets"), DARK)}
  {card(C.text("spent.cards.capital.title"), C.list("spent.cards.capital.bullets"), SAGE_MID)}
  {card(esc(C.text("spent.cards.onetime.title")), C.list("spent.cards.onetime.bullets"), SAGE_LIGHT, light=True)}
 </div>
 {C.html("spent.p3")}
 <p class="figcap"><b>Table 1.</b> {C.text("spent.table1.caption")} {fy_picker("table1", FY_LABEL[2027], FY_LABEL[2026])}</p>
 {table1_for(2027)}
 {table1_for(2026)}
 <div class="folio r">BUDGET PRIMER • 5</div>
</section>""")

# -- page 6: figure 2
pages.append(f"""
<section class="page">
 <h2 class="sub">{C.text("categories.h2")}</h2>
 <h3 class="sub2">{C.text("categories.h3")}</h3>
 <p class="figcap"><b>Figure 2.</b> {C.text("categories.fig2.caption")} {fy_picker("fig2")}
 <span class="noprint figcap-hint">{esc(C.text("categories.fig2.hint"))}</span></p>
 {fig2_chart_for(2027)}
 {fig2_chart_for(2026)}
 {legend([(C.text("categories.legend.operating"), SAGE), (C.text("categories.legend.capital"), SAGE_MID),
          (C.text("categories.legend.onetime"), DARK), (C.text("categories.legend.emergency"), DARKEST)])}
 <div class="explore noprint">{C.text("categories.explore")}
  <a href="{TRACKER}#/enacted" target="_blank" rel="noopener">{C.text("categories.explore.link").replace(" →", "&nbsp;→")}</a></div>
 {C.html("categories.p1")}
 <div class="folio">6 • BUDGET PRIMER</div>
</section>""")

# -- page 7: obligated costs + fig 3
pages.append(f"""
<section class="page">
 <div class="callout">
  <h4>{C.text("obligated.title")}</h4>
  {C.html("obligated.p1")}
  {C.html("obligated.p2")}
 </div>
 <details class="obligated noprint">
  <summary>{C.text("obligated.summary")}</summary>
  <div class="obligated-panel">
   <p class="figcap"><b>{C("obligated.panel.caption").split("[^")[0].strip()}</b>{"[^" + C("obligated.panel.caption").split("[^")[1]}<span class="noprint">
   {C.text("obligated.panel.hint")}</span></p>
   {fig_obligated()}
   {legend([(n, c) for n, _k, c in OBLIG_BANDS])}
   <p class="obligated-note">{C("obligated.panel.note").format(oblig_first=f"${OBLIG['series']['2018']['_printed_subtotal']/1e9:.2f}", oblig_last=f"${OBLIG['series']['2027']['_printed_subtotal']/1e9:.2f}")}</p>
  </div>
 </details>
 <h3 class="sub2">{C.text("cip.h3")}</h3>
 <p class="figcap"><b>Figure 3.</b> {C.text("cip.fig3.caption")} {fy_picker("fig3")} ($Millions)</p>
 <div class="pie-row">{fy_pie_swap("fig3", fig3_slices_for(BUD), fig3_slices_for(BUD26), cls="pie-cip", width_in=5.10, label_pt=13.7)}{legend(list(zip(FIG3_ORDER, FIG3_COLORS)))}</div>
 <p data-fig="fig3" data-fy="2027">{C("cip.body").format(fy=2027, cip_total=words(cip_total_for(BUD)))}</p>
 <p data-fig="fig3" data-fy="2026" hidden>{C("cip.body").format(fy=2026, cip_total=words(cip_total_for(BUD26)))}</p>
 <div class="folio r">BUDGET PRIMER • 7</div>
</section>""")

# -- page 8: photo + one-time/emergency
pages.append(f"""
<section class="page">
 <img class="photo" src="assets/hb2296-signing.jpg" alt="{esc(C.text("onetime.photo.alt"))}">
 {C.html("onetime.photo.caption", "photocap")}
 <h3 class="sub2">{C.text("onetime.h3")}</h3>
 <div class="cards2">
  {card(C.text("onetime.cards.onetime.title"), ONE_TIME_BULLETS, DARK)}
  {card(C.text("onetime.cards.emergency.title"), EMERG_BULLETS, DARKEST)}
 </div>
 <div class="folio">8 • BUDGET PRIMER</div>
</section>""")

# -- page 9: funding the budget
pages.append(f"""
<section class="page">
 <h1>{C.text("funding.h1")}</h1>
 <p class="figcap"><b>Figure 4.</b> {C.text("funding.fig4.caption")} {fy_picker("fig4")} {C.text("funding.fig4.caption.suffix")}</p>
 <div class="pie-row">{fy_pie_swap("fig4", fig4_slices_for(BUD), fig4_slices_for(BUD26), cls="pie-mof", width_in=5.45, label_pt=15.5)}{legend(list(zip(FIG4_ORDER, FIG3_COLORS)))}</div>
 {C.html("funding.p1")}
 <div class="cards3">
  {card(C.text("funding.cards.general.title"), C.list("funding.cards.general.bullets"), DARK)}
  {card(C.text("funding.cards.special.title"), C.list("funding.cards.special.bullets"), SAGE_MID)}
  {card(C.text("funding.cards.federal.title"), C.list("funding.cards.federal.bullets"), SAGE_LIGHT, light=True)}
 </div>
 <div class="folio r">BUDGET PRIMER • 9</div>
</section>""")

# -- page 10: taxes
pages.append(f"""
<section class="page">
 <h2 class="sub">{C.text("taxes.h2")}</h2>
 <p class="figcap"><b>Figure 5.</b> {C.text("taxes.fig5.caption")} {fy_picker("fig5")} {C.text("taxes.fig5.caption.suffix")}</p>
 <div class="pie-row">{fy_pie_swap("fig5", fig5_slices_for(REV), fig5_slices_for(REV26), cls="pie-tax", width_in=4.80, label_pt=13.1)}{legend([(n, c) for (n, _v, c, _l) in fig5_slices_for(REV)])}</div>
 <div class="cards3">
  {card(C.text("taxes.cards.get.title"), C.list("taxes.cards.get.bullets"), DARK)}
  {card(C.text("taxes.cards.iit.title"), C.list("taxes.cards.iit.bullets"), SAGE_MID)}
  {card(C.text("taxes.cards.tat.title"), C.list("taxes.cards.tat.bullets"), SAGE_LIGHT, light=True)}
 </div>
 <div class="folio">10 • BUDGET PRIMER</div>
</section>""")

# -- page 11: who pays
pages.append(f"""
<section class="page">
 <h3 class="sub2">{C.text("whopays.h3")}</h3>
 <p class="figcap"><b>Figure 6.</b> {C("whopays.fig6.caption")}</p>
 {fig6_chart()}
 {C.html("whopays.p1")}
 <div class="callout">
  <h4>{C.text("whopays.callout.title")}</h4>
  {C.html("whopays.callout.p1")}
  {C.html("whopays.callout.p2")}
 </div>
 <div class="folio r">BUDGET PRIMER • 11</div>
</section>""")

# -- page 12: endnotes ------------------------------------------------------
# Footnote refs live in the prose as stable [^id] tokens. Resolve them across the
# assembled body FIRST so numbering follows document order, then build the
# endnotes page from the order that produced.
body = C.fn.resolve("".join(pages))

missing_src = C.fn.unused()
if missing_src:
    raise ContentError(
        "content.md declares sources never cited in the prose: "
        + ", ".join(f"[{s}]" for s in missing_src))

en = "".join(endnote_link(i + 1, t, u) for i, (t, u) in enumerate(C.fn.endnotes()))
notes = C.fn.endnotes()

def linkify_footnotes(markup):
    """Turn every <sup>N</sup> marker into a clickable ref the JS can pop.

    Handles multi-note markers like <sup>4&thinsp;5</sup>. The href still points
    at the endnote anchor, so the marker works without JS and in print.
    """
    def repl(m):
        inner = m.group(1)
        nums = re.findall(r"\d+", inner)
        if not nums:
            return m.group(0)
        out = []
        for n in nums:
            i = int(n)
            if 1 <= i <= len(notes):
                out.append(f'<a class="fn" href="#en{i}" data-fn="{i}">{n}</a>')
            else:
                out.append(n)
        return "<sup>" + "&thinsp;".join(out) + "</sup>"
    return re.sub(r"<sup>(.*?)</sup>", repl, markup, flags=re.S)

body += f"""
<section class="page">
 <h1>{C.text("endnotes.h1")}</h1>
 <ol class="endnotes">{en}</ol>
 <div class="folio">12 • BUDGET PRIMER</div>
</section>"""

unused = C.unused_keys()
if unused:
    raise ContentError("content.md has keys the report never uses: " + ", ".join(unused))

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- Unlisted: reachable only via direct link while in review. Remove once ready to publish. -->
<meta name="robots" content="noindex, nofollow">
<title>Hawaiʻi Budget Primer FY2026–27 — Hawaiʻi Appleseed</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@800;900&family=Source+Sans+3:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="primer.css">
</head>
<body>
<div class="toolbar noprint">
 <span>Hawaiʻi Budget Primer FY2026–27</span>
 <span class="tb-actions">
  <a class="tb-link" href="{TRACKER}" target="_blank" rel="noopener">Budget Tracker ↗</a>
  <button onclick="window.print()">Download PDF</button>
 </span>
</div>
{linkify_footnotes(body)}
<div id="tip" class="noprint"></div>
<script>window.PRIMER_NOTES = {json.dumps([{"t": t, "u": u} for t, u in notes], separators=(",", ":"))};
window.PRIMER_FY_SPAN = {json.dumps(HIST_FY_SPAN)};
window.PRIMER_LINKS = {json.dumps({
    **DEPT_INFO,
    "__all": {"name": "Hawaiʻi Budget Tracker",
              "blurb": "Interactive companion to this primer: every executive department and program in Act 175, governor's request vs. enacted, veto changes, positions, and historical trends back a decade.",
              "operating": EXEC_OP, "capital": EXEC_CIP,
              "hist": [round(t["total_nominal"] / 1e6) for t in _hist["totals_by_fy"]],
              "url": TRACKER + "#/enacted"},
}, separators=(",", ":"))};</script>
<script src="primer.js"></script>
</body>
</html>"""

(HERE / "web" / "index.html").write_text(html)
print(f"wrote web/index.html ({len(html):,} bytes, {len(pages)} pages)")
