#!/usr/bin/env python3
"""Render the Budget Primer FY2026-27 as a single HTML document.

Reads data/report_data.json and emits web/index.html. All charts are inline SVG
generated here, so the screen version and the Chrome-printed PDF are identical;
web/primer.js layers tooltips/hover on top for the interactive build.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
DATA = json.loads((HERE / "data" / "report_data.json").read_text())
BUD = DATA["budget"]
RES = DATA["research"]
REV = DATA["tax_revenue_fy2027"]

# --- budget tracker interlink (same repo, docs/ SPA on GitHub Pages) ---
TRACKER = "https://dtomkatsu.github.io/BudgetPrimerFinal/"
_dept_src = json.loads(
    (HERE.parent / "docs" / "js" / "departments_act175_fy2027.json").read_text())
DEPT_INFO = {}
for _d in _dept_src:
    desc = (_d.get("description") or "").split(". ")
    DEPT_INFO[_d["code"]] = {
        "name": _d["name"],
        "blurb": ". ".join(desc[:2]) + ("." if desc[:2] and not desc[1 if len(desc) > 1 else 0].endswith(".") else ""),
        "operating": _d.get("operating_budget", 0) or 0,
        "capital": _d.get("capital_budget", 0) or 0,
        "positions": _d.get("positions", 0) or 0,
        "url": f"{TRACKER}#/department/{_d['id']}",
    }

# ---------- palette (sampled from the original PDF) ----------
SAGE, SAGE_MID, SAGE_LIGHT, MINT, PALE = "#6b9080", "#a4c3b2", "#cce3de", "#eaf4f4", "#d8f3dc"
DARK, FOREST, DARKEST = "#2d6a4f", "#1b4332", "#081c15"
INK = "#26332c"
SERIES = {"operating": SAGE, "capital": SAGE_MID, "one_time": DARK, "emergency": DARKEST}

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

def pie(slices, size=420, r=158, label_style="plain", start=0.0):
    """slices: [(name, value, color, label_lines)] clockwise from 12 o'clock.

    size leaves room around the r=150 disc for the outside labels of thin slices,
    which can sit ~46px beyond the rim plus their own text width.
    """
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
        lr = r * 0.62 if big else r + 26
        if sweep < 26:                       # stagger consecutive small-slice labels
            lr = r + (20 + 20 * (small_n % 2))
            small_n += 1
        lx, ly = cx + lr * math.cos(mid), cy + lr * math.sin(mid)
        anchor = "middle" if big else ("start" if math.cos(mid) > 0.25 else
                                       "end" if math.cos(mid) < -0.25 else "middle")
        ty = ly - (len(lab) - 1) * 8
        # keep multi-line labels inside the viewBox
        ty = min(max(ty, 13), size - 6 - (len(lab) - 1) * 16)
        lx = min(max(lx, 8), size - 8)
        t = "".join(f'<tspan x="{lx:.0f}" dy="{16 if i else 0}">{l}</tspan>'
                    for i, l in enumerate(lab))
        labels.append(f'<text x="{lx:.0f}" y="{ty:.0f}" text-anchor="{anchor}" '
                      f'class="pie-lab">{t}</text>')
        a += sweep
    return (f'<svg viewBox="0 0 {size} {size}" class="chart pie" '
            f'preserveAspectRatio="xMidYMid meet" role="img">'
            + "".join(paths) + "".join(labels) + "</svg>")

def legend(items):
    rows = "".join(
        f'<div class="lg"><span class="sw" style="background:{c}"></span>{esc(n)}</div>'
        for n, c in items)
    return f'<div class="legend">{rows}</div>'

def fig2_chart():
    rows = []
    # branch rows first, like the original (no tracker page -> code None)
    rows.append(("Judiciary", {"operating": JUD["operating_fy27"], "capital": JUD["cip_fy27"],
                               "one_time": JUD_ONE_TIME, "emergency": 0}, None))
    rows.append(("Legislature", {"operating": LEG["total_fy27_published_style"], "capital": 0,
                                 "one_time": 0, "emergency": 0}, None))
    rows.append(("OHA", {"operating": OHA["operating_fy27"], "capital": 0,
                         "one_time": OHA_ONE_TIME, "emergency": 0}, None))
    for d in BUD["figure2_departments"]:
        rows.append((d["label"], {"operating": d["operating"], "capital": d["capital"],
                                  "one_time": ONE_TIME_BY_DEPT.get(d["code"], 0),
                                  "emergency": EMERG_BY_DEPT.get(d["code"], 0)},
                     d["code"] if d["code"] in DEPT_INFO else None))
    W, LEFT, RH, GAP = 720, 150, 17, 7
    maxv = 5.5e9
    plot_w = W - LEFT - 60
    H = len(rows) * (RH + GAP) + 40
    out = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img">']
    for gx in range(0, 6):
        x = LEFT + plot_w * gx / 5.5
        out.append(f'<line x1="{x:.0f}" y1="0" x2="{x:.0f}" y2="{H-34}" stroke="#d9e4de" stroke-width="1"/>')
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

def fig1_lifecycle(size=560):
    cx = cy = size / 2
    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    ramp = ["#e7f3ec", "#d9ece1", "#c4dfd0", "#aed2bf", "#98c5ae", "#82b89d",
            "#6ba98b", "#5b997c", "#4c886d", "#3d775e", "#2d5545", "#122e20"]
    out = [f'<svg viewBox="0 0 {size} {size}" class="chart" role="img">']
    r1, r2 = 118, 168
    for i, m in enumerate(months):
        a0 = i * 30
        out.append(f'<path d="{arc_path(cx, cy, r1, r2, a0 + 1, a0 + 29)}" fill="{ramp[i]}"/>')
        ang = a0 + 15
        mid = math.radians(ang - 90)
        tx, ty = cx + 143 * math.cos(mid), cy + 143 * math.sin(mid)
        rot = ang - 180 if 90 < ang < 270 else ang   # tangential, never upside down
        fill = "#fff" if i >= 8 else INK
        out.append(f'<text x="{tx:.0f}" y="{ty+4:.0f}" class="mo" fill="{fill}" text-anchor="middle" '
                   f'transform="rotate({rot:.0f},{tx:.0f},{ty:.0f})">{m}</text>')
    # Arc spans are sized to the label that rides on them: at pr the arc length
    # must exceed the rendered text width, or textPath silently truncates.
    phases = [("Legislative consideration", 0, 150, SAGE),
              ("Planning and prep by B&amp;F Dept", 150, 258, SAGE_LIGHT),
              ("Prep of proposed exec budget", 258, 360, MINT)]
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
        tc = "#fff" if col == SAGE else INK
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
    W, H, BW = 720, 300, 74
    gap = (W - 40 - 7 * BW) / 6
    out = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img">']
    for i, (q, rng, v) in enumerate(data):
        x = 20 + i * (BW + gap)
        h = (v / 15) * 210
        y = 240 - h
        out.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{BW}" height="{h:.0f}" fill="{SAGE}" '
                   f'class="iv" data-tip="{q} ({rng}): {v}% of income"/>')
        out.append(f'<text x="{x+BW/2:.0f}" y="{y-8:.0f}" text-anchor="middle" class="vlab b">{v}%</text>')
        out.append(f'<text x="{x+BW/2:.0f}" y="262" text-anchor="middle" class="ax">{q}</text>')
        out.append(f'<text x="{x+BW/2:.0f}" y="277" text-anchor="middle" class="ax">{rng.split("–")[0] if "–" in rng else rng}</text>')
        if "–" in rng:
            out.append(f'<text x="{x+BW/2:.0f}" y="291" text-anchor="middle" class="ax">–{rng.split("–")[1]}</text>')
    out.append(f'<line x1="16" y1="240" x2="{W-16}" y2="240" stroke="{INK}" stroke-width="1"/></svg>')
    return "".join(out)

# ---------- figure data ----------
f3 = BUD["figure3_cip"]
FIG3_ORDER = ["Transportation", "Formal Education", "All Others", "Economic Development", "Health"]
FIG3_COLORS = [SAGE, SAGE_MID, SAGE_LIGHT, MINT, PALE]
fig3_slices = [(k, f3[k], c, [f"${f3[k]/1e6:,.0f}"]) for k, c in zip(FIG3_ORDER, FIG3_COLORS)]
CIP_TOTAL = sum(f3.values())

f4 = BUD["figure4_means_of_finance"]
FIG4_ORDER = ["General Funds", "Special Funds", "Federal Funds", "Other Funds"]
f4_total = sum(f4.values())
fig4_slices = [(k, f4[k], c, [f"${f4[k]/1e9:.1f}", f"({f4[k]/f4_total*100:.1f}%)"])
               for k, c in zip(FIG4_ORDER, FIG3_COLORS)]

get_, iit = REV["General Excise and Use Tax"], REV["Individual Income Tax"]
tat, corp = REV["Transient Accommodations Tax"], REV["Corporate Income Tax"]
other_tax = REV["GENERAL FUND TOTAL"] - get_ - iit - tat - corp
fig5_slices = [(n, v, c, [f"${v/1e9:.2f}", f"({v/REV['GENERAL FUND TOTAL']*100:.1f}%)"])
               for (n, v), c in zip(
        [("General Excise Tax", get_), ("Individual Income Tax", iit),
         ("Transient Accommodations Tax", tat), ("All Other Taxes", other_tax),
         ("Corporate Income Tax", corp)], FIG3_COLORS)]

# ---------- page shells ----------
def card(title, bullets, bg, light=False):
    cls = "card light" if light else "card"
    lis = "".join(f"<li>{b}</li>" for b in bullets)
    return f'<div class="{cls}" style="background:{bg}"><h4>{title}</h4><ul>{lis}</ul></div>'

def endnote_link(n, txt, url):
    return f'<li id="en{n}">{txt} <a href="{url}">{url}</a></li>'

ONE_TIME_BULLETS = [
    f"<b>Transportation &amp; Budget/Finance:</b> $700 million in Act 99 — $600 million in county-surcharge transit funding and a new $100 million major disaster fund.<sup>8</sup>",
    f"<b>Accounting, Transportation, Land:</b> $200 million in Maui wildfire insurance proceeds to rebuild King Kamehameha III Elementary and restore Lahaina's harbor.<sup>9</sup>",
    f"<b>DBEDT:</b> $49.5 million for the New Aloha Stadium district.<sup>10</sup>",
    f"<b>UH:</b> $28.5 million in revenue bonds for student housing.<sup>11</sup>",
    f"<b>Human Services:</b> $16.5 million to supplement health-plan premiums for residents losing ACA coverage.<sup>12</sup>",
    f"<b>Education:</b> $3.4 million to expand free school meals to all ALICE households — the FY27 expansion promised in Act 139 (2025).<sup>13</sup>",
]
EMERG_BULLETS = [
    f"<b>Various Executive Departments:</b> $2,871,954 in collective-bargaining cost items for Bargaining Unit 11 employees.<sup>14</sup>",
    "The 2026 session also passed roughly $110 million in <i>FY26</i> emergency appropriations — a $14.2 million backfill of funds redirected to food assistance during the 2025 federal shutdown, and $95.8 million for labor-grievance cost items.<sup>15</sup>",
]

TABLE1 = f"""
<table class="t1">
<thead><tr><th></th><th class="lk" data-dept="__all">Executive<sup>2</sup></th><th>Judiciary<sup>3</sup></th>
<th>Legislature<sup>4&thinsp;5</sup></th><th>OHA<sup>6</sup></th></tr></thead>
<tbody>
<tr><td>Operating Budget</td><td>{words(EXEC_OP)}</td><td>{words(JUD['operating_fy27'])}</td>
<td>{words(LEG['total_fy27_published_style'])}</td><td>{words(OHA['operating_fy27'])}</td></tr>
<tr><td>Capital Improvement Appropriations</td><td>{words(EXEC_CIP)}</td>
<td>{words(JUD['cip_fy27'])}</td><td>$0</td><td>$0</td></tr>
<tr><td>One-Time Appropriations</td><td>{words(EXEC_ONE_TIME)}</td><td>{words(JUD_ONE_TIME)}</td>
<td>$0</td><td>{words(OHA_ONE_TIME)}</td></tr>
<tr><td>Emergency Appropriations</td><td>{words(EXEC_EMERG)}</td><td>$0</td><td>$0</td><td>$0</td></tr>
<tr class="total"><td>Total</td>
<td>{words(EXEC_OP + EXEC_CIP + EXEC_ONE_TIME + EXEC_EMERG)}</td>
<td>{words(JUD['operating_fy27'] + JUD['cip_fy27'] + JUD_ONE_TIME)}</td>
<td>{words(LEG['total_fy27_published_style'])}</td>
<td>{words(OHA['operating_fy27'] + OHA_ONE_TIME)}</td></tr>
</tbody></table>"""

pages = []

# -- page 1: cover
pages.append(f"""
<section class="page cover">
 <div class="ribbon r1"></div><div class="ribbon r2"></div>
 <div class="ribbon r3"></div><div class="ribbon r4"></div>
 <div class="cover-inner">
  <div class="logo-lockup"><span class="logo-mark">☘</span>
   <div><div class="logo-name">HAWAIʻI APPLESEED</div>
   <div class="logo-sub">CENTER FOR LAW &amp; ECONOMIC JUSTICE</div></div></div>
  <h1 class="cover-title">HAWAIʻI<br>BUDGET<br>PRIMER</h1>
  <div class="cover-year">FY2026–27</div>
 </div>
</section>""")

# -- page 2: about / TOC
pages.append(f"""
<section class="page toc-page">
 <div class="toc-head">
  <div class="logo-lockup light"><span class="logo-mark">☘</span>
   <div><div class="logo-name">HAWAIʻI APPLESEED</div>
   <div class="logo-sub">CENTER FOR LAW &amp; ECONOMIC JUSTICE</div></div></div>
  <p class="toc-link"><a href="https://hiappleseed.org">www.hiappleseed.org</a></p>
  <p class="toc-author">Author: Devin Thomas</p>
 </div>
 <p class="mission">Hawaiʻi Appleseed is committed to a more socially and economically just Hawaiʻi, where everyone
 has genuine opportunities to achieve economic security and fulfill their potential. We change systems to address
 inequity and foster greater opportunity by conducting data analysis and research to address income inequality,
 educating policymakers and the public, engaging in collaborative problem solving and coalition building, and
 advocating for policy and systems change.</p>
 <p class="mission">The work of Hawaiʻi Appleseed is about people. The issues we work on—housing, food, wages,
 mobility, the state budget and taxation, and racial and indigenous equity—are important because they ensure people
 have access to shelter, sustenance, and the means to survive and thrive individually and collectively. Addressing
 these issues requires the knowledge and expertise of the people that have first-hand experience and live with the
 adverse consequences of our flawed systems.</p>
 <h2 class="toc-title">TABLE OF CONTENTS</h2>
 <div class="toc-list">
  <div><span>Budget Basics</span><span>3</span></div>
  <div><span>How Money Is Spent</span><span>5</span></div>
  <div><span>Funding the Budget</span><span>9</span></div>
  <div><span>Endnotes</span><span>12</span></div>
 </div>
 <p class="copyright">Copyright © 2026 Hawaiʻi Appleseed Center for Law &amp; Economic Justice. All rights reserved.<br>
 733 Bishop Street, Suite 1180, Honolulu, HI 96813</p>
 <div class="folio">2 • BUDGET PRIMER</div>
</section>""")

# -- page 3: budget basics
branch_cards = [
    ("Legislature", SAGE, "branch-0.jpg", True,
     ["Creates laws and decides how the state's money is spent.",
      "Consists of the State Senate and House of Representatives, Office of the Auditor, Office of the Ombudsman, and the Legislative Reference Bureau."]),
    ("Judiciary", SAGE_MID, "branch-1.jpg", False,
     ["Interprets laws and resolves legal cases through the court system.",
      "Consists of the Hawaiʻi Supreme Court, Intermediate Court of Appeals, Land Court, Tax Appeal Court, Circuit Courts, Family Courts, District Courts, Environmental Courts, and Office of the Administrative Director of the Courts."]),
    ("Executive", SAGE_LIGHT, "branch-2.jpg", False,
     ["Enforces state laws and manages the daily operations of the government.",
      "Consists of the Governor, Lieutenant Governor, State Departments, and the University of Hawaiʻi System."]),
    ("Office of Hawaiian Affairs", MINT, "branch-3.jpg", False,
     ["A semi-autonomous state agency responsible for improving the wellbeing of Native Hawaiians.",
      "Legislative appropriations represent only a small portion of OHA's resources."]),
]
bc = "".join(
    f'<div class="branch"><img src="assets/{img}" alt="{t}">'
    f'<div class="branch-card{" onlight" if not lt else ""}" style="background:{bg}">'
    f'<h4>{t}</h4><ul>' + "".join(f"<li>{b}</li>" for b in bl) + "</ul></div></div>"
    for t, bg, img, lt, bl in branch_cards)
pages.append(f"""
<section class="page">
 <h1>BUDGET BASICS</h1>
 <p><b>THE INVESTMENTS</b> that Hawaiʻi's government makes in its people through the state budget should reflect
 our shared priorities and values. This budget primer is intended to help readers understand how our state budget
 works and to encourage budget and policy decisions that improve the lives of Hawaiʻi's people.</p>
 <p>The state budget funds Hawaiʻi's three government branches: the Legislature; the Judiciary; and the Executive.
 A small portion funds the Office of Hawaiian Affairs (OHA) as well. More than 99 percent of the state budget goes
 toward funding the executive branch.</p>
 {bc}
 <div class="folio r">BUDGET PRIMER • 3</div>
</section>""")

# -- page 4: budget process
pages.append(f"""
<section class="page">
 <h2 class="sub">Budget Process</h2>
 <p>Hawaiʻi uses a two-year (biennial) budget cycle. The full budget is passed in odd-numbered years, and
 adjustments can be made in the second year. Fiscal Years (FY) cover July 1 through June 30, labeled by the
 calendar year in which they end (e.g. FY 2027 runs from July 2026 through June 2027).</p>
 <p class="figcap"><b>Figure 1.</b> Hawaiʻi Budget Lifecycle</p>
 <div class="lifecycle-wrap">
  {fig1_lifecycle()}
  <div class="lc lc-dec">The governor submits the executive budget proposal to the legislature.</div>
  <div class="lc lc-jan">The legislature reviews, amends and passes the budget bill.</div>
  <div class="lc lc-may">Emergency and supplemental appropriations are added if any are needed.</div>
  <div class="lc lc-jun">The governor signs the budget bill into law, with line-item veto power.</div>
  <div class="lc lc-jul">Funds are released to executive departments and agencies.</div>
  <div class="lc lc-aug">Agencies carry out spending.</div>
  <div class="lc lc-oct">Budget proposals are drafted by each branch.</div>
 </div>
 <div class="folio">4 • BUDGET PRIMER</div>
</section>""")

# -- page 5: how money is spent
pages.append(f"""
<section class="page">
 <h1>HOW MONEY IS SPENT</h1>
 <p>Government spending is essential for the economy, especially in times of crisis. The executive branch alone
 employs over 47,000 workers, not including contractors.<sup>1</sup> These workers are responsible for running
 Hawaiʻi's departments and agencies—a task that is only made possible with billions of dollars in funding.</p>
 <p>There are three types of spending: operating, capital improvement, and one-time/emergency appropriations.</p>
 <div class="cards3">
  {card("Operating Budget", ["Regular funding for state agencies, public services, and programs."], SAGE)}
  {card("Capital Improvement Appropriations", ["Funds to build, maintain, or improve infrastructure, such as roads, schools, and hospitals."], SAGE_MID)}
  {card("One-Time &amp; Emergency Appropriations", ["Temporary funding for unexpected needs, such as disaster response or special projects."], SAGE_LIGHT, light=True)}
 </div>
 <p>Since it manages the state's departments and agencies, the Executive Branch receives almost all of the funds
 in each spending category.</p>
 <p class="figcap"><b>Table 1.</b> Budget Breakdown by Branch and Spending Category, Hawaiʻi, FY 2026–27</p>
 {TABLE1}
 <div class="folio r">BUDGET PRIMER • 5</div>
</section>""")

# -- page 6: figure 2
pages.append(f"""
<section class="page">
 <h2 class="sub">Spending Categories</h2>
 <h3 class="sub2">Operating Budget</h3>
 <p class="figcap"><b>Figure 2.</b> Hawaiʻi State Budget by Branch and Department, FY2027
 <span class="noprint figcap-hint">— click a department for details &amp; tracker link</span></p>
 {fig2_chart()}
 {legend([("Operating Budget", SAGE), ("Capital Improvement Appr", SAGE_MID),
          ("One-Time Appr", DARK), ("Emergency Appr", DARKEST)])}
 <div class="explore noprint">Want program-level detail, veto changes, and historical trends?
  <a href="{TRACKER}#/enacted" target="_blank" rel="noopener">Explore the interactive Budget
  Tracker&nbsp;→</a></div>
 <p>The Executive departments with the largest overall budgets are the Departments of Human Services,
 Transportation, Budget and Finance, and Education. The Department of Transportation's Capital Improvement
 Appropriations budget is larger than its operating budget—the state's airports, harbors, and highways are
 in the middle of a multi-year construction cycle. The Department of Health has a larger operating budget than
 all but four departments, and the DOE operating budget covers K–12 public school teacher salaries statewide.</p>
 <div class="folio">6 • BUDGET PRIMER</div>
</section>""")

# -- page 7: obligated costs + fig 3
pages.append(f"""
<section class="page">
 <div class="callout">
  <h4>Obligated Costs</h4>
  <p>Before the state can consider any other spending, the Hawaiʻi constitution says it must pay its
  non-negotiable obligated costs. These costs include pensions, health benefits, Medicaid, and debt
  payments—and they are worth roughly $5 billion, or a quarter of the state's operating budget. The share of the
  operating budget that these costs consume is increasing each year, limiting the state's flexibility for new
  investments in areas like housing, schools, economic development and climate resilience.</p>
  <p>Except for Medicaid expenses, which are included in the budget for the Department of Human Services,
  the costs named above are covered by the Department of Budget and Finance. These two departments have the
  largest operating budgets, and obligated costs are a significant share for each.</p>
 </div>
 <h3 class="sub2">Capital Improvement Appropriations</h3>
 <p class="figcap"><b>Figure 3.</b> Distribution of Capital Improvement Project Funding, FY2027 ($Millions)</p>
 <div class="pie-row">{pie(fig3_slices)}{legend(list(zip(FIG3_ORDER, FIG3_COLORS)))}</div>
 <p>The total budget for Capital Improvement Projects (CIP) in FY2027 is {words(CIP_TOTAL)}. Transportation-related
 projects usually take up more than half of the CIP budget. This money is necessary for maintaining, among other
 things, the state's airports, harbors, and its 2,433 miles of roads and highways.<sup>7</sup></p>
 <div class="folio r">BUDGET PRIMER • 7</div>
</section>""")

# -- page 8: photo + one-time/emergency
pages.append(f"""
<section class="page">
 <img class="photo" src="assets/signing.jpg" alt="Bill signing at Washington Place">
 <p class="photocap">On May 30, 2025, advocates and lawmakers joined Governor Josh Green at Washington Place as he
 signed <a href="https://www.capitol.hawaii.gov/session/measure_indiv.aspx?billtype=SB&billnumber=1300&year=2025">Senate
 Bill (SB) 1300</a> into law as <a href="https://www.capitol.hawaii.gov/sessions/session2025/bills/GM1239_.PDF">Act
 139</a>. The law's FY27 appropriations take effect this year, expanding subsidized meal access to public school
 students from households in the Asset-Limited, Income-Constrained, Employed (ALICE) category. // Will Caron,
 Hawaiʻi Appleseed</p>
 <h3 class="sub2">One-Time and Emergency Appropriations</h3>
 <div class="cards2">
  {card("FY27 One-Time Appropriations", ONE_TIME_BULLETS, DARK)}
  {card("FY27 Emergency Appropriations", EMERG_BULLETS, DARKEST)}
 </div>
 <div class="folio">8 • BUDGET PRIMER</div>
</section>""")

# -- page 9: funding the budget
pages.append(f"""
<section class="page">
 <h1>FUNDING THE BUDGET</h1>
 <p class="figcap"><b>Figure 4.</b> Hawaiʻi Budget Means of Finance, FY2027 ($Billions)<sup>16</sup></p>
 <div class="pie-row">{pie(fig4_slices)}{legend(list(zip(FIG4_ORDER, FIG3_COLORS)))}</div>
 <p>The state's spending primarily falls under three main categories: general funds, special funds and federal funds.</p>
 <div class="cards3">
  {card("General Funds", ["General funds are mostly made up of tax revenue. The main pot of state money, these funds can be used for almost any state need."], SAGE)}
  {card("Special Funds", ["Money from tuition, fees, settlements, etc., special funds can only be spent on a specific purpose, often related to the revenue source."], SAGE_MID)}
  {card("Federal Funds", ["Federal funds are monies provided to the state by the federal government, almost always in the form of grants."], SAGE_LIGHT, light=True)}
 </div>
 <div class="folio r">BUDGET PRIMER • 9</div>
</section>""")

# -- page 10: taxes
pages.append(f"""
<section class="page">
 <h2 class="sub">Taxes</h2>
 <p class="figcap"><b>Figure 5.</b> Projected Hawaiʻi State Tax Revenue, FY2027 ($Billions)<sup>17</sup></p>
 <div class="pie-row">{pie(fig5_slices)}{legend([(n, c) for (n, _v, c, _l) in fig5_slices])}</div>
 <div class="cards3">
  {card("General Excise Tax", ["The GET is a tax on the sale of goods and services such as retail purchases and rent. Hawaiʻi relies on the GET for half of the state's tax revenue, but the tax increases the cost of living and hits low-income families the hardest."], SAGE)}
  {card("Individual Income Tax", ["Hawaiʻi taxes those with high incomes at a higher marginal rate. Act 46 (2024) reduced income taxes for most people. However, these tax cuts cost the state budget $240.3 million in FY25. By FY32, the cuts will cost $1.45 billion annually.<sup>18</sup>"], SAGE_MID)}
  {card("Transient Accomodations Tax", ["The TAT is a tax on hotel rooms, short-term rentals and cruise ships. It is paid mainly by tourists and supports the general fund and special funds for tourism promotion, resource management, climate resiliency and economic development."], SAGE_LIGHT, light=True)}
 </div>
 <div class="folio">10 • BUDGET PRIMER</div>
</section>""")

# -- page 11: who pays
pages.append(f"""
<section class="page">
 <h3 class="sub2">Who Pays These Taxes?</h3>
 <p class="figcap"><b>Figure 6.</b> Percentage of Income Paid in State and Local Taxes by Household Income
 Quintile (2024)<sup>19</sup></p>
 {fig6_chart()}
 <p>In Hawaiʻi, low- and middle-income families spend a larger share of their already stretched-thin income on
 state and local taxes compared to wealthy families. This is due almost entirely to the General Excise Tax, which
 is charged on basic needs like food, clothes and rent. When a low-income person and a wealthy person purchase
 the same groceries, they pay the same dollar amount of tax. However, that dollar amount represents a much larger
 chunk of the low-income person's paycheck, making it much harder to budget for—and too often keeping low-income
 families trapped in cycles of poverty, debt and income insecurity.</p>
 <div class="callout">
  <h4>Tax Credits</h4>
  <p>Tax credits are an effective tool available to lawmakers that are designed to lower or even eliminate the
  tax liability owed to the state by people or businesses. The purpose of these tax credits is to stimulate the
  economy by reducing costs either for businesses or struggling families that need help purchasing their basic
  necessities.</p>
  <p>In 2022, the state gave out $433.9 million in tax credits.<sup>20</sup> Out of this amount, only $111 million
  went to tax credits for lower-income households, such as the Earned Income Tax Credit and Refundable Food/Excise
  Tax Credit. A larger amount—$168 million—went to tax credits for wealthier taxpayers and businesses, such as the
  Renewable Energy Technologies Tax Credit and Film/Media Production Credit.</p>
 </div>
 <div class="folio r">BUDGET PRIMER • 11</div>
</section>""")

# -- page 12: endnotes
CAP26 = "https://www.capitol.hawaii.gov/sessions/session2026/bills"
CAP25 = "https://www.capitol.hawaii.gov/sessions/session2025/bills"
notes = [
    ('"State of Hawaiʻi Executive Branch Workforce Profile," Hawaiʻi State Department of Human Resources Development, p. 5, December 16, 2024.',
     "https://dhrd.hawaii.gov/wp-content/uploads/2024/12/Workforce-Profile_06302024_FINAL.pdf"),
    ('"Act 175," State of Hawaiʻi, June 26, 2026 (HB1800 CD1).', f"{CAP26}/HB1800_CD1_.HTM"),
    ('"Act 178," State of Hawaiʻi, 2026 (HB2095 CD1), amending Act 227, Session Laws of Hawaiʻi 2025.', f"{CAP26}/HB2095_CD1_.HTM"),
    ('"Act 1," State of Hawaiʻi, 2026 (HB2240 HD1).', f"{CAP26}/HB2240_HD1_.HTM"),
    ('"Act 127," State of Hawaiʻi, May 29, 2025 (HB1439 CD1), FY2026–27 legislative cost items.', f"{CAP25}/GM1227_.PDF"),
    ('"Act 248," State of Hawaiʻi, June 30, 2025 (HB410 CD1).', f"{CAP25}/GM1351_.PDF"),
    ('"Visitor Info," Hawaiʻi Department of Transportation.', "https://hidot.hawaii.gov/highways/visitor"),
    ('"Act 99," State of Hawaiʻi, June 5, 2026 (HB2275 CD2).', f"{CAP26}/HB2275_CD2_.HTM"),
    ('"Act 123," State of Hawaiʻi, June 8, 2026 (SB2930 CD1).', f"{CAP26}/SB2930_CD1_.HTM"),
    ('"Act 184," State of Hawaiʻi, July 6, 2026 (SB2599 CD1).', f"{CAP26}/SB2599_CD1_.HTM"),
    ('"Act 80," State of Hawaiʻi, June 4, 2026 (HB2339 CD1).', f"{CAP26}/HB2339_CD1_.HTM"),
    ('"Act 21," State of Hawaiʻi, May 21, 2026 (HB2310 CD1), Part II.', f"{CAP26}/HB2310_CD1_.HTM"),
    ('"Act 139," State of Hawaiʻi, May 30, 2025 (SB1300 CD1), §3–4.', f"{CAP25}/GM1239_.PDF"),
    ('"Act 26," State of Hawaiʻi, May 22, 2026 (HB2272 CD1).', f"{CAP26}/HB2272_CD1_.HTM"),
    ('"Act 21" Part I and "Act 33," State of Hawaiʻi, May 2026 (HB2310 CD1; HB2271 CD1).', f"{CAP26}/HB2271_CD1_.HTM"),
    ('"Act 175," State of Hawaiʻi, June 26, 2026 (HB1800 CD1).', f"{CAP26}/HB1800_CD1_.HTM"),
    ('"State Receipt and Revenue Plans FB25–27," Department of Budget and Finance, September 2024.',
     "https://budget.hawaii.gov/wp-content/uploads/2024/12/05.-State-Receipt-and-Revenue-Plans-FB25-27-PFP7Lt.pdf"),
    ('Kawafuchi, Kurt, "General Fund Forecast," Council on Revenues, March 12, 2025.',
     "https://files.hawaii.gov/tax/useful/cor/2025gf03-12_with0416_Rpt2Gov.pdf"),
    ('"Hawaiʻi: Who Pays? 7th Edition," Institute on Taxation and Economic Policy, 2024. Note: Includes all family sizes.',
     "https://itep.org/whopays/hawaii-who-pays-7th-edition"),
    ('"Tax Credits Claimed by Hawaiʻi Taxpayers: Tax Year 2022," Hawaiʻi Department of Taxation, p. 5, December 2024.',
     "https://files.hawaii.gov/tax/stats/stats/credits/2022credit.pdf"),
]
en = "".join(endnote_link(i + 1, f"{i + 1}.&emsp;{esc(t)}" if False else f"{t}", u)
             for i, (t, u) in enumerate(notes))
pages.append(f"""
<section class="page">
 <h1>ENDNOTES</h1>
 <ol class="endnotes">{en}</ol>
 <div class="folio">12 • BUDGET PRIMER</div>
</section>""")

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hawaiʻi Budget Primer FY2026–27 — Hawaiʻi Appleseed</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Abril+Fatface&family=Archivo+Black&family=Source+Sans+3:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap" rel="stylesheet">
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
{"".join(pages)}
<div id="tip" class="noprint"></div>
<script>window.PRIMER_LINKS = {json.dumps({
    **DEPT_INFO,
    "__all": {"name": "Hawaiʻi Budget Tracker",
              "blurb": "Interactive companion to this primer: every executive department and program in Act 175, governor's request vs. enacted, veto changes, positions, and historical trends back a decade.",
              "operating": EXEC_OP, "capital": EXEC_CIP,
              "url": TRACKER + "#/enacted"},
}, separators=(",", ":"))};</script>
<script src="primer.js"></script>
</body>
</html>"""

(HERE / "web" / "index.html").write_text(html)
print(f"wrote web/index.html ({len(html):,} bytes, {len(pages)} pages)")
