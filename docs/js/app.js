// ---------------------------------------------------------------------------
// Global data
// ---------------------------------------------------------------------------
let departmentsData = [];
let summaryStats = null;
let programsData = [];
let fyComparisonData = [];
let draftComparisonData = null;     // FY2026 comparison
let draftComparisonDataFY27 = null; // FY2027 comparison
let projectsDataFY26 = null;        // Section 14 CIP projects FY26
let projectsDataFY27 = null;        // Section 14 CIP projects FY27
let governorProjectsData = null;    // Governor's supplemental capital projects (S78)
let historicalTrendsData = null;    // 10-year history of biennial budget acts

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------

window.loadDepartments = async function () {
    try {
        const response = await fetch('./js/departments.json');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        departmentsData = data.filter(d => !d.name.includes('County') && !d.name.includes('Judiciary'));
        console.log(`Loaded ${departmentsData.length} departments`);
        return departmentsData;
    } catch (e) {
        console.error('Error loading departments:', e);
        document.getElementById('app').innerHTML = `<div class="error-message"><h2>Error Loading Data</h2><p>${e.message}</p></div>`;
        return [];
    }
};

window.loadSummaryStats = async function () {
    try {
        const response = await fetch('./js/summary_stats.json');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        summaryStats = await response.json();
        return summaryStats;
    } catch (e) {
        console.error('Error loading summary stats:', e);
        return null;
    }
};

window.loadPrograms = async function () {
    try {
        const response = await fetch('./js/programs.json');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        programsData = await response.json();
        return programsData;
    } catch (e) {
        console.error('Error loading programs:', e);
        return [];
    }
};

window.loadFYComparison = async function () {
    try {
        const response = await fetch('./js/fy_comparison.json?v=' + Date.now());
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        fyComparisonData = await response.json();
        return fyComparisonData;
    } catch (e) {
        console.error('Error loading FY comparison:', e);
        return [];
    }
};

let governorRequestData = [];
window.loadGovernorRequest = async function () {
    try {
        const response = await fetch('./js/governor_request.json?v=' + Date.now());
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        governorRequestData = await response.json();
        return governorRequestData;
    } catch (e) {
        console.error('Error loading Governor request:', e);
        return [];
    }
};

window.loadHistoricalTrends = async function () {
    try {
        const response = await fetch('./js/historical_trends.json?v=' + Date.now());
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        historicalTrendsData = await response.json();
        console.log(`Loaded historical trends: ${historicalTrendsData.totals_by_fy.length} FYs, ` +
                    `${historicalTrendsData.by_department.length} depts`);
        return historicalTrendsData;
    } catch (e) {
        console.error('Error loading historical trends:', e);
        return null;
    }
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const fmt = (amount) => {
    if (amount == null) return '$0';
    if (Math.abs(amount) >= 1e9) return `$${(amount / 1e9).toFixed(2)} billion`;
    if (Math.abs(amount) >= 1e6) return `$${(amount / 1e6).toFixed(2)} million`;
    if (Math.abs(amount) >= 1e3) return `$${(amount / 1e3).toFixed(0)}K`;
    return `$${amount.toLocaleString()}`;
};

// HTML-aware version: wraps number and unit in separate spans for styling
// Short form (M/B/K) — used in table chips
const fmtHtml = (amount) => {
    if (amount == null) return '<span class="fmt-num">$0</span>';
    const abs = Math.abs(amount);
    const sign = amount < 0 ? '-' : '';
    if (abs >= 1e9) return `<span class="fmt-num">${sign}$${(abs / 1e9).toFixed(2)}</span><span class="fmt-unit">B</span>`;
    if (abs >= 1e6) return `<span class="fmt-num">${sign}$${(abs / 1e6).toFixed(2)}</span><span class="fmt-unit">M</span>`;
    if (abs >= 1e3) return `<span class="fmt-num">${sign}$${(abs / 1e3).toFixed(0)}</span><span class="fmt-unit">K</span>`;
    return `<span class="fmt-num">${sign}$${abs.toLocaleString()}</span>`;
};
// Summary-card form: 1 decimal place, short unit (B/M/K)
const fmtHtmlCard = (amount) => {
    if (amount == null) return '<span class="fmt-num">$0</span>';
    const abs = Math.abs(amount);
    const sign = amount < 0 ? '-' : '';
    if (abs >= 1e9) return `<span class="fmt-num">${sign}$${(abs / 1e9).toFixed(1)}</span><span class="fmt-unit">B</span>`;
    if (abs >= 1e6) return `<span class="fmt-num">${sign}$${(abs / 1e6).toFixed(1)}</span><span class="fmt-unit">M</span>`;
    if (abs >= 1e3) return `<span class="fmt-num">${sign}$${(abs / 1e3).toFixed(0)}</span><span class="fmt-unit">K</span>`;
    return `<span class="fmt-num">${sign}$${abs.toLocaleString()}</span>`;
};
// Full-word form — used in summary cards
const fmtHtmlFull = (amount) => {
    if (amount == null) return '<span class="fmt-num">$0</span>';
    const abs = Math.abs(amount);
    const sign = amount < 0 ? '-' : '';
    if (abs >= 1e9) return `<span class="fmt-num">${sign}$${(abs / 1e9).toFixed(2)}</span><span class="fmt-unit"> billion</span>`;
    if (abs >= 1e6) return `<span class="fmt-num">${sign}$${(abs / 1e6).toFixed(2)}</span><span class="fmt-unit"> million</span>`;
    if (abs >= 1e3) return `<span class="fmt-num">${sign}$${(abs / 1e3).toFixed(0)}</span><span class="fmt-unit">K</span>`;
    return `<span class="fmt-num">${sign}$${abs.toLocaleString()}</span>`;
};

const fmtPct = (v) => v != null ? `${v > 0 ? '+' : ''}${v.toFixed(1)}%` : '—';

// Highlight occurrences of `query` within `text` by wrapping each match in
// <mark>. Used to make table rows self-evidently match the current search.
// Escapes HTML in the input AND in any literal regex meta characters in the
// query so we never inject user-controlled markup.
const escapeHtml = (s) => String(s ?? '').replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const highlight = (text, query) => {
    const safe = escapeHtml(text);
    if (!query) return safe;
    const esc = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return safe.replace(new RegExp(esc, 'gi'), m => `<mark>${m}</mark>`);
};

// Tiny SVG sparkline showing the Gov → HD1 → SD1 trajectory for a single row.
// `values` is an array of 2 or 3 numbers. Width 52px, height 18px.
// Colour reflects the delta sign of last vs first value.
const sparklineSvg = (values) => {
    const pts = values.filter(v => v != null && !Number.isNaN(v));
    if (pts.length < 2) return '';
    // Skip sparkline when all values are identical (no change to show)
    if (pts.every(v => v === pts[0])) return '';
    const min = Math.min(...pts);
    const max = Math.max(...pts);
    const range = max - min;
    const w = 52, h = 18, padX = 2, padY = 3;
    const innerW = w - padX * 2;
    const innerH = h - padY * 2;
    const xStep = pts.length > 1 ? innerW / (pts.length - 1) : 0;
    const y = (v) => range === 0 ? h / 2 : padY + innerH - ((v - min) / range) * innerH;
    const coords = pts.map((v, i) => [padX + i * xStep, y(v)]);
    const path = coords.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ');
    const delta = pts[pts.length - 1] - pts[0];
    const colour = delta > 0 ? '#2e7d32' : delta < 0 ? '#c62828' : '#889';
    const dots = coords.map(p =>
        `<circle cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}" r="1.6" fill="${colour}"/>`).join('');
    return `<svg class="row-sparkline" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true">`
         + `<path d="${path}" fill="none" stroke="${colour}" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>`
         + dots + `</svg>`;
};

// Stacked horizontal bar showing top-N programs' share of a group total.
// `segments` is an array of { label, value }. Renders up to 6 segments and
// rolls the rest into an "other" slice.
//
// Returns a full HTML wrapper with:
//   - inline caption ("share by program")
//   - stacked bar (14px tall, 1px white gaps between segments, sage outline)
//   - top-program annotation (largest program's id + percentage)
//   - hover popover with full segment legend (swatches + names + % + amounts)
const stackedBarSvg = (segments, total) => {
    if (!total || total <= 0 || !segments.length) return '';
    const W = 90, H = 14, GAP = 1;
    const sorted = [...segments].sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
    const top = sorted.slice(0, 6);
    const restVal = sorted.slice(6).reduce((s, x) => s + Math.abs(x.value), 0);
    const restCount = sorted.length - 6;
    const parts = top.map(s => ({ label: s.label, value: Math.abs(s.value) }));
    if (restVal > 0) parts.push({ label: `+${restCount} more program${restCount === 1 ? '' : 's'}`, value: restVal });
    // Muted sage-aligned palette
    const palette = ['#5a7b68', '#7da48d', '#a5bfae', '#c8cfa8', '#c9a87b', '#a68c68', '#cdd3d8'];
    const sumParts = parts.reduce((s, p) => s + p.value, 0) || 1;

    // Drawable width minus inter-segment gaps
    const gapTotal = Math.max(0, parts.length - 1) * GAP;
    const drawableW = Math.max(0, W - gapTotal);

    // Compute per-segment metadata (width, fill, percent of group total)
    const enriched = parts.map((p, i) => {
        const pct = (p.value / sumParts) * 100;
        return {
            label: p.label,
            value: p.value,
            pct,
            fill: palette[i % palette.length],
            w: (p.value / sumParts) * drawableW,
        };
    });

    // Build SVG with 1px gaps between segments
    let x = 0;
    let svg = `<svg class="stacked-bar" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" aria-hidden="true">`;
    enriched.forEach((p, i) => {
        const tipPct = p.pct >= 1 ? `${p.pct.toFixed(0)}%` : `<1%`;
        svg += `<rect x="${x.toFixed(1)}" y="0" width="${p.w.toFixed(1)}" height="${H}" fill="${p.fill}"><title>${escapeHtml(p.label)} — ${tipPct} — ${fmt(p.value)}</title></rect>`;
        x += p.w + GAP;
    });
    svg += `</svg>`;

    // Leader caption: small label sitting ABOVE the bar identifying the
    // largest contributing program (program_id + pct). Replaces the previous
    // "share by program" kicker, which repeated identical text on every fund
    // row. Skip if the leader is the "+N more" rollup.
    const leader = enriched[0];
    let leaderCaption = '';
    if (leader && !leader.label.startsWith('+')) {
        const leaderId = (leader.label.split(/\s+/)[0] || '').trim();
        const leaderPct = leader.pct >= 1 ? `${leader.pct.toFixed(0)}%` : `<1%`;
        if (leaderId) {
            leaderCaption = `<span class="stacked-bar-caption">Largest: <span class="stacked-bar-caption-id">${escapeHtml(leaderId)}</span> <span class="stacked-bar-caption-pct">${leaderPct}</span></span>`;
        }
    }

    // Hover popover legend: swatch + label + % + amount for each segment
    let legendRows = '';
    enriched.forEach(p => {
        const pPct = p.pct >= 1 ? `${p.pct.toFixed(0)}%` : `<1%`;
        legendRows += `<li class="stacked-bar-legend-row">
            <span class="legend-swatch" style="background:${p.fill}"></span>
            <span class="legend-label">${escapeHtml(p.label)}</span>
            <span class="legend-pct">${pPct}</span>
            <span class="legend-amt">${fmt(p.value)}</span>
        </li>`;
    });
    const popover = `<div class="stacked-bar-popover" role="tooltip">
        <div class="stacked-bar-popover-title">Share by program</div>
        <ul class="stacked-bar-legend">${legendRows}</ul>
    </div>`;

    return `<span class="stacked-bar-wrap" tabindex="0">
        <span class="stacked-bar-stack">
            ${leaderCaption}
            <span class="stacked-bar-track">${svg}</span>
        </span>
        ${popover}
    </span>`;
};

// Title-case a program/department name while preserving parenthesized acronyms
// like (HYCF), (DHS), and keeping short articles lowercase ("County of Kauai").
const SMALL_WORDS = new Set(['of', 'and', 'the', 'for', 'to', 'in', 'on', 'at', 'a', 'an', 'or', 'by', 'with', 'from', 'vs']);
const prettyName = (name) => {
    if (!name) return '';
    return name.split(/(\s+|[-–—]|\s?&\s?)/).map((token, i, arr) => {
        if (!token.trim()) return token; // preserve whitespace/separators
        if (/^\([A-Z]+\)$/.test(token)) return token; // preserve (AGS) style acronyms
        if (/^[IVX]+$/i.test(token) && token.length <= 4) return token.toUpperCase(); // Roman numerals
        const lower = token.toLowerCase();
        // Keep articles lowercase unless they're the first token
        const firstTokenIdx = arr.findIndex(t => t.trim().length > 0);
        if (i !== firstTokenIdx && SMALL_WORDS.has(lower)) return lower;
        return lower.charAt(0).toUpperCase() + lower.slice(1);
    }).join('');
};

function sortDepartments(direction = 'desc') {
    if (!departmentsData?.length) return [];
    return [...departmentsData].sort((a, b) => {
        const tA = (a.operating_budget || 0) + (a.capital_budget || 0) + (a.one_time_appropriations || 0);
        const tB = (b.operating_budget || 0) + (b.capital_budget || 0) + (b.one_time_appropriations || 0);
        return direction === 'asc' ? tA - tB : tB - tA;
    });
}

function downloadCSV(rows, filename) {
    if (!rows.length) return;
    const keys = Object.keys(rows[0]);
    const csv = [keys.join(','), ...rows.map(r => keys.map(k => {
        const v = r[k];
        if (v == null) return '';
        if (typeof v === 'string' && (v.includes(',') || v.includes('"'))) return `"${v.replace(/"/g, '""')}"`;
        return v;
    }).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
}

// ---------------------------------------------------------------------------
// Year-aware historical helpers (drive the FY dropdown + per-dept sparklines
// on the HB300 tab — the History tab is now merged into this page)
// ---------------------------------------------------------------------------

// Per-fiscal-year department totals (nominal + real) sourced from
// historical_trends.json. Returns Map<dept_code, {nominal, real}>.
function deptTotalsForFy(fy) {
    const out = new Map();
    const depts = historicalTrendsData?.by_department || [];
    for (const d of depts) {
        const e = d.series.find(s => s.fy === fy);
        if (e) out.set(d.dept_code, { nominal: e.nominal, real: e.real });
    }
    return out;
}

// State-wide totals row (operating/capital/total, both nominal and real)
// for the given fiscal year, or null if the year is out of range.
function stateTotalsForFy(fy) {
    return (historicalTrendsData?.totals_by_fy || []).find(r => r.fy === fy) || null;
}

// Wider sparkline for the department cards / dropdown summary.
// `points` is an array of { fy, value }. Renders a 12-year mini-trend with
// a baseline, an end-marker, and a subtle gradient fill — sized for a
// summary card (180×42). Returns '' if data is too sparse to be meaningful.
function deptHistorySparkline(points, opts = {}) {
    const pts = (points || []).filter(p => p && p.value != null && !Number.isNaN(p.value));
    if (pts.length < 3) return '';
    const W = opts.width  || 180;
    const H = opts.height || 42;
    const padX = 4, padY = 5;
    const innerW = W - padX * 2;
    const innerH = H - padY * 2;
    const values = pts.map(p => p.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const xStep = innerW / (pts.length - 1);
    const y = (v) => padY + innerH - ((v - min) / range) * innerH;
    const coords = pts.map((p, i) => [padX + i * xStep, y(p.value)]);
    const path = coords
        .map((c, i) => `${i === 0 ? 'M' : 'L'}${c[0].toFixed(1)} ${c[1].toFixed(1)}`)
        .join(' ');
    // Area fill anchored at baseline
    const area = `${path} L${coords[coords.length - 1][0].toFixed(1)} ${(H - padY).toFixed(1)} `
               + `L${coords[0][0].toFixed(1)} ${(H - padY).toFixed(1)} Z`;
    const delta = values[values.length - 1] - values[0];
    // Sage-aligned palette consistent with the rest of the dashboard
    const colour = delta > 0 ? '#5a7b68' : delta < 0 ? '#a06868' : '#6a7370';
    const fill   = delta > 0 ? 'rgba(90,123,104,0.16)'
                 : delta < 0 ? 'rgba(160,104,104,0.16)'
                 :             'rgba(106,115,112,0.12)';
    const last = coords[coords.length - 1];
    const firstFy = pts[0].fy;
    const lastFy  = pts[pts.length - 1].fy;
    return `
        <svg class="dept-card-sparkline" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}"
             aria-label="Funding trend FY${firstFy}–FY${lastFy}" role="img">
            <path d="${area}" fill="${fill}" stroke="none"/>
            <path d="${path}" fill="none" stroke="${colour}" stroke-width="1.6"
                  stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="2.4"
                    fill="${colour}"/>
        </svg>
        <div class="dept-card-sparkline-legend">
            <span>FY${String(firstFy).slice(-2)}</span>
            <span>FY${String(lastFy).slice(-2)}</span>
        </div>`;
}

// ---------------------------------------------------------------------------
// Home Page
// ---------------------------------------------------------------------------

window.homePage = async function () {
    if (!departmentsData?.length || !summaryStats) {
        return `<section class="home-page"><div class="loading"><div class="spinner"></div><p>Loading...</p></div></section>`;
    }

    // Year selector range — from historical_trends metadata when available,
    // else fall back to FY2026 only.  "Current" detail year (operating /
    // capital / positions / programs) is FY2026; older years show totals
    // sourced from the historical series.
    const meta   = historicalTrendsData?.metadata || null;
    const fyMin  = meta?.fy_range?.[0] ?? 2026;
    const fyMax  = meta?.fy_range?.[1] ?? 2026;
    const DETAIL_FY = 2026;
    const projected = new Set(meta?.projected_fys || []);

    // FY options — newest first, with badges for projected years
    const yearOptions = [];
    for (let y = fyMax; y >= fyMin; y--) {
        const isProj = projected.has(y);
        const isDetail = y === DETAIL_FY;
        const label = `FY${y}` + (isProj ? ' (projected)' : '') + (isDetail ? ' — full detail' : '');
        yearOptions.push(`<option value="${y}"${isDetail ? ' selected' : ''}>${label}</option>`);
    }

    const html = `
        <section class="home-page">
            <div class="context-banner">
                <strong>Enacted budgets.</strong> Pick a fiscal year below.
                FY${DETAIL_FY} carries the full operating/capital/program detail from HB300 (Act 250, SLH 2025).
                Earlier years show totals from the corresponding biennial appropriations act.
                For the current FY2026–27 supplemental budget draft, see <a href="#/">HB1800 →</a>
            </div>

            <div class="hb300-year-bar">
                <label for="hb300-fy-select"><strong>Fiscal year:</strong></label>
                <select id="hb300-fy-select" class="hb300-fy-select">${yearOptions.join('')}</select>
                <span class="hb300-fy-help" id="hb300-fy-help"></span>
            </div>

            <div class="summary-cards-grid" id="hb300-summary-cards"></div>

            ${meta ? `
            <div class="hb300-history-section">
                <div class="hb300-history-head">
                    <h3>State Appropriations · FY${fyMin}–FY${fyMax}</h3>
                    <div class="hist-toggle" role="tablist" aria-label="Display mode">
                        <button class="hist-toggle-btn active" data-mode="nominal" type="button">Nominal $</button>
                        <button class="hist-toggle-btn" data-mode="real" type="button">Real (FY${meta.base_fy} $)</button>
                    </div>
                </div>
                <p class="hb300-history-sub">Operating + Capital combined across ${meta.acts.length} biennial appropriations acts.</p>
                <div class="hb300-history-chart-wrap"><canvas id="hb300-history-chart"></canvas></div>
            </div>` : ''}

            <div class="controls-bar">
                <div class="sort-controls">
                    <span>Sort: </span>
                    <button class="sort-btn active" data-sort="desc">High→Low</button>
                    <button class="sort-btn" data-sort="asc">Low→High</button>
                </div>
                <div class="action-links">
                    <a href="#/search" class="action-link">🔍 Search Programs</a>
                    <a href="#/compare" class="action-link">📊 FY Comparison</a>
                    <button class="action-link export-btn" id="export-depts">⬇ Export CSV</button>
                </div>
            </div>

            <div class="department-grid" id="dept-grid"></div>
        </section>`;

    return html;
};

// ---------------------------------------------------------------------------
// Department Detail Page (with program drill-down)
// ---------------------------------------------------------------------------

window.departmentDetailPage = async function (params) {
    const deptId = params?.id;
    if (!deptId) return window.notFoundPage();

    const dept = departmentsData.find(d => d.id === deptId);
    if (!dept) return window.notFoundPage();

    const total = (dept.operating_budget || 0) + (dept.capital_budget || 0) + (dept.one_time_appropriations || 0);
    const programs = dept.programs || [];

    // Group programs by program_id for aggregation
    const progMap = {};
    programs.forEach(p => {
        const key = `${p.program_id}|${p.section}`;
        if (!progMap[key]) {
            progMap[key] = { ...p, fund_details: [] };
        }
        progMap[key].fund_details.push({ fund: p.fund_category, amount: p.amount, positions: p.positions });
        progMap[key].amount = (progMap[key].amount || 0);
    });

    // Aggregate by program_id only (combine sections)
    const byProg = {};
    programs.forEach(p => {
        if (!byProg[p.program_id]) {
            byProg[p.program_id] = { id: p.program_id, name: p.program_name, total: 0, operating: 0, capital: 0, positions: null, funds: {} };
        }
        const bp = byProg[p.program_id];
        bp.total += p.amount;
        if (p.section === 'Operating') bp.operating += p.amount;
        else if (p.section === 'Capital Improvement') bp.capital += p.amount;
        if (p.positions) bp.positions = (bp.positions || 0) + p.positions;
        bp.funds[p.fund_category] = (bp.funds[p.fund_category] || 0) + p.amount;
    });

    const progList = Object.values(byProg).sort((a, b) => b.total - a.total);

    // Fund breakdown for this department — sorted desc, used by the
    // doughnut chart + matching swatch legend.
    const fundBreakdown = dept.fund_breakdown || {};
    const fundEntries = Object.entries(fundBreakdown)
        .sort(([, a], [, b]) => b - a);
    // Sage-aligned palette (matches sparklines + history chart). Repeats
    // softly if a dept has more than `palette.length` distinct fund types.
    const fundPalette = [
        '#5a7b68', '#a08e58', '#7d97a3', '#b07560', '#8b6c8e',
        '#6f8d70', '#c2924a', '#5e7d96', '#a87575', '#8b8158',
        '#789689', '#a39378', '#7e93a8', '#b58472', '#928298',
    ];
    const fundLegendHtml = fundEntries.map(([fund, amt], i) => {
        const pct = total ? (amt / total * 100) : 0;
        const colour = fundPalette[i % fundPalette.length];
        return `
            <div class="fund-legend-row" data-fund-idx="${i}">
                <span class="fund-legend-swatch" style="background:${colour}"></span>
                <span class="fund-legend-name">${fund}</span>
                <span class="fund-legend-amt">${fmt(amt)}</span>
                <span class="fund-legend-pct">${pct.toFixed(1)}%</span>
            </div>`;
    }).join('');
    // Stash data for initDepartmentDetailPage so it can build the chart.
    window.__deptFundData = {
        labels: fundEntries.map(([f]) => f),
        values: fundEntries.map(([, a]) => a),
        colors: fundEntries.map((_, i) => fundPalette[i % fundPalette.length]),
        total,
    };

    // Programs — rendered as visual cards instead of a flat table. Each
    // card shows id-as-chip, name, an inline "share of dept" bar, and
    // operating/capital/positions stats with the total on the right.
    const programCardsHtml = progList.map(p => {
        const sharePct = total ? (p.total / total * 100) : 0;
        const opPct  = p.total ? (p.operating / p.total * 100) : 0;
        const opWidth  = sharePct * (opPct / 100);
        const capWidth = sharePct - opWidth;
        const stats = [];
        if (p.operating > 0) stats.push(`<span class="prog-stat"><span class="prog-stat-dot prog-stat-op"></span>Operating <strong>${fmt(p.operating)}</strong></span>`);
        if (p.capital > 0)   stats.push(`<span class="prog-stat"><span class="prog-stat-dot prog-stat-cap"></span>Capital <strong>${fmt(p.capital)}</strong></span>`);
        if (p.positions)     stats.push(`<span class="prog-stat"><span class="prog-stat-dot prog-stat-pos"></span><strong>${p.positions.toLocaleString(undefined,{maximumFractionDigits:0})}</strong> positions</span>`);
        return `
            <article class="program-card">
                <div class="program-card-head">
                    <span class="program-card-id">${p.id}</span>
                    <span class="program-card-name">${prettyName(p.name)}</span>
                    <span class="program-card-total">${fmt(p.total)}</span>
                </div>
                <div class="program-card-bar" title="${sharePct.toFixed(1)}% of department total">
                    <div class="program-card-bar-track">
                        <div class="program-card-bar-op"  style="width: ${opWidth.toFixed(2)}%"></div>
                        <div class="program-card-bar-cap" style="width: ${capWidth.toFixed(2)}%"></div>
                    </div>
                    <span class="program-card-bar-label">${sharePct.toFixed(1)}% of dept</span>
                </div>
                <div class="program-card-stats">${stats.join('')}</div>
            </article>`;
    }).join('');

    // Historical context — pull this department's 12-yr series if available
    const histDept = (historicalTrendsData?.by_department || [])
        .find(d => d.dept_code === dept.code);
    const histSection = histDept ? `
        <section class="dept-history-section">
            <div class="dept-history-head">
                <h3>Funding History · FY${histDept.series[0].fy}–FY${histDept.series[histDept.series.length-1].fy}</h3>
                <div class="hist-toggle" role="tablist" aria-label="Display mode">
                    <button class="hist-toggle-btn active" data-mode="nominal" type="button">Nominal $</button>
                    <button class="hist-toggle-btn" data-mode="real" type="button">Real (FY${historicalTrendsData.metadata.base_fy} $)</button>
                </div>
            </div>
            <p class="dept-history-sub">Combined operating + capital appropriations across each biennial budget act.</p>
            <div class="dept-history-chart-wrap"><canvas id="dept-history-chart"></canvas></div>
        </section>` : '';

    return `
        <section class="department-detail">
            <a href="#/enacted" class="back-button">← Back to HB300 Budget</a>
            <div class="department-header">
                <h2>${dept.name} (${dept.code})</h2>
                ${dept.description ? `<p class="dept-desc">${dept.description}</p>` : ''}
            </div>

            <div class="summary-cards-grid">
                <div class="summary-card"><div class="amount">${fmtHtmlCard(total)}</div><div class="label">Total</div><div class="label-sub">FY2026</div></div>
                <div class="summary-card"><div class="amount">${fmtHtmlCard(dept.operating_budget)}</div><div class="label">Operating</div></div>
                <div class="summary-card"><div class="amount">${fmtHtmlCard(dept.capital_budget)}</div><div class="label">Capital</div></div>
                ${dept.positions ? `<div class="summary-card"><div class="amount">${dept.positions.toLocaleString(undefined,{maximumFractionDigits:0})}</div><div class="label">Positions</div></div>` : ''}
            </div>

            ${histSection}

            <section class="fund-breakdown-section">
                <div class="fund-breakdown-head">
                    <h3>Fund Type Breakdown</h3>
                    <p class="fund-breakdown-sub">Where ${dept.code}'s FY2026 budget comes from. ${fundEntries.length} fund type${fundEntries.length === 1 ? '' : 's'}.</p>
                </div>
                <div class="fund-breakdown-body">
                    <div class="fund-doughnut-wrap">
                        <canvas id="fund-doughnut-chart" width="240" height="240"></canvas>
                        <div class="fund-doughnut-center">
                            <span class="fund-doughnut-total">${fmt(total)}</span>
                            <span class="fund-doughnut-total-lbl">Total · FY2026</span>
                        </div>
                    </div>
                    <div class="fund-legend-list">${fundLegendHtml}</div>
                </div>
            </section>

            <section class="programs-section">
                <div class="programs-head">
                    <h3>Programs <span class="programs-count">${progList.length}</span></h3>
                    <button class="action-link export-btn" id="export-programs">⬇ Export CSV</button>
                </div>
                <div class="programs-legend">
                    <span class="prog-legend-item"><span class="prog-stat-dot prog-stat-op"></span>Operating</span>
                    <span class="prog-legend-item"><span class="prog-stat-dot prog-stat-cap"></span>Capital</span>
                    <span class="prog-legend-item"><span class="prog-stat-dot prog-stat-pos"></span>Positions</span>
                </div>
                <div class="programs-card-list">
                    ${programCardsHtml}
                </div>
            </section>
        </section>`;
};

window.initDepartmentDetailPage = async function () {
    document.getElementById('export-programs')?.addEventListener('click', () => {
        const deptId = window.location.hash.split('/').pop();
        const dept = departmentsData.find(d => d.id === deptId);
        if (!dept) return;
        const rows = (dept.programs || []).map(p => ({
            program_id: p.program_id, program_name: p.program_name,
            section: p.section, fund_type: p.fund_type,
            fund_category: p.fund_category, amount: p.amount,
            positions: p.positions || '',
        }));
        downloadCSV(rows, `${deptId}_programs_fy2026.csv`);
    });

    // ---- Fund Type doughnut chart ---------------------------------------
    // Data is staged on window.__deptFundData by departmentDetailPage().
    // Renders a Chart.js doughnut alongside the matching swatch legend
    // built directly in the template.  Hovering a slice highlights its
    // legend row and vice versa.
    const fundCanvas = document.getElementById('fund-doughnut-chart');
    if (fundCanvas && typeof Chart !== 'undefined' && window.__deptFundData) {
        const fd = window.__deptFundData;
        const fmtFund = (v) => {
            if (Math.abs(v) >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
            if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
            if (Math.abs(v) >= 1e3) return `$${(v / 1e3).toFixed(0)}K`;
            return `$${v.toLocaleString()}`;
        };
        const fundChart = new Chart(fundCanvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: fd.labels,
                datasets: [{
                    data: fd.values,
                    backgroundColor: fd.colors,
                    borderColor: '#fff',
                    borderWidth: 2,
                    hoverOffset: 8,
                }],
            },
            options: {
                cutout: '62%',
                maintainAspectRatio: false,
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => {
                                const pct = fd.total ? (ctx.parsed / fd.total * 100).toFixed(1) : 0;
                                return `${ctx.label}: ${fmtFund(ctx.parsed)} (${pct}%)`;
                            },
                        },
                    },
                    datalabels: { display: false },
                },
                onHover: (evt, elements) => {
                    document.querySelectorAll('.fund-legend-row.active')
                        .forEach(r => r.classList.remove('active'));
                    if (elements?.length) {
                        const idx = elements[0].index;
                        document.querySelector(`.fund-legend-row[data-fund-idx="${idx}"]`)
                            ?.classList.add('active');
                    }
                },
            },
        });
        // Reverse interaction — hovering a legend row highlights the slice
        document.querySelectorAll('.fund-legend-row').forEach(row => {
            row.addEventListener('mouseenter', () => {
                const idx = parseInt(row.dataset.fundIdx, 10);
                fundChart.setActiveElements([{ datasetIndex: 0, index: idx }]);
                fundChart.tooltip.setActiveElements([{ datasetIndex: 0, index: idx }],
                    { x: fundCanvas.width / 2, y: fundCanvas.height / 2 });
                fundChart.update();
                document.querySelectorAll('.fund-legend-row.active')
                    .forEach(r => r.classList.remove('active'));
                row.classList.add('active');
            });
            row.addEventListener('mouseleave', () => {
                fundChart.setActiveElements([]);
                fundChart.tooltip.setActiveElements([], {x:0, y:0});
                fundChart.update();
                row.classList.remove('active');
            });
        });
    }

    // ---- Historical chart for this department ---------------------------
    const canvas = document.getElementById('dept-history-chart');
    if (!canvas || typeof Chart === 'undefined' || !historicalTrendsData) return;

    const deptId = window.location.hash.split('/').pop();
    const dept = departmentsData.find(d => d.id === deptId);
    if (!dept) return;
    const histDept = historicalTrendsData.by_department.find(d => d.dept_code === dept.code);
    if (!histDept) return;

    const baseFy = historicalTrendsData.metadata.base_fy;
    const labels = histDept.series.map(s => `FY${s.fy}`);
    const fmtBillions = (v) => Math.abs(v) >= 1e9
        ? `$${(v / 1e9).toFixed(2)}B`
        : `$${(v / 1e6).toFixed(0)}M`;

    let mode = 'nominal';
    let chart = null;

    const renderChart = () => {
        if (chart) chart.destroy();
        const data = histDept.series.map(s => mode === 'real' ? s.real : s.nominal);
        chart = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: `${dept.code} — ${dept.name}`,
                    data,
                    borderColor: '#5a7b68',
                    backgroundColor: 'rgba(90, 123, 104, 0.20)',
                    tension: 0.25,
                    fill: true,
                    borderWidth: 2.5,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                }],
            },
            options: {
                maintainAspectRatio: false,
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => fmtBillions(ctx.parsed.y),
                        },
                    },
                    datalabels: { display: false },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (v) => Math.abs(v) >= 1e9
                                ? `$${(v / 1e9).toFixed(1)}B`
                                : `$${(v / 1e6).toFixed(0)}M`,
                        },
                        title: {
                            display: true,
                            text: mode === 'real' ? `Constant FY${baseFy} dollars` : 'Nominal dollars',
                        },
                    },
                    x: { grid: { display: false } },
                },
            },
        });
    };

    document.querySelectorAll('.dept-history-section .hist-toggle-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const m = this.dataset.mode;
            if (m === mode) return;
            mode = m;
            document.querySelectorAll('.dept-history-section .hist-toggle-btn').forEach(b =>
                b.classList.toggle('active', b.dataset.mode === mode));
            renderChart();
        });
    });

    renderChart();
};

// ---------------------------------------------------------------------------
// Search / Filter Page
// ---------------------------------------------------------------------------

window.searchPage = async function () {
    if (!programsData.length) await window.loadPrograms();

    const fundTypes = [...new Set(programsData.map(p => p.fund_category))].filter(Boolean).sort();
    const sections = [...new Set(programsData.map(p => p.section))].filter(Boolean).sort();
    const deptCodes = [...new Set(programsData.map(p => p.program_id?.slice(0, 3)))].filter(Boolean).sort();

    const fundOpts = fundTypes.map(f => `<option value="${f}">${f}</option>`).join('');
    const secOpts = sections.map(s => `<option value="${s}">${s}</option>`).join('');
    const deptOpts = deptCodes.map(d => `<option value="${d}">${d}</option>`).join('');

    return `
        <section class="search-page">
            <a href="#/" class="back-button">← Home</a>
            <h2>Search & Filter Programs</h2>
            <div class="filter-bar">
                <input type="text" id="search-input" placeholder="Search by program name or ID..." class="search-input">
                <select id="filter-fund" class="filter-select"><option value="">All Fund Types</option>${fundOpts}</select>
                <select id="filter-section" class="filter-select"><option value="">All Sections</option>${secOpts}</select>
                <select id="filter-dept" class="filter-select"><option value="">All Departments</option>${deptOpts}</select>
                <button class="action-link export-btn" id="export-search">⬇ Export Results</button>
            </div>
            <div class="search-summary" id="search-summary"></div>
            <div class="search-results" id="search-results"></div>
        </section>`;
};

window.initSearchPage = async function () {
    const render = () => {
        const q = (document.getElementById('search-input')?.value || '').toLowerCase();
        const fund = document.getElementById('filter-fund')?.value || '';
        const sec = document.getElementById('filter-section')?.value || '';
        const dept = document.getElementById('filter-dept')?.value || '';

        let filtered = programsData;
        if (q) filtered = filtered.filter(p =>
            (p.program_name || '').toLowerCase().includes(q) ||
            (p.program_id || '').toLowerCase().includes(q));
        if (fund) filtered = filtered.filter(p => p.fund_category === fund);
        if (sec) filtered = filtered.filter(p => p.section === sec);
        if (dept) filtered = filtered.filter(p => p.program_id?.startsWith(dept));

        const totalAmt = filtered.reduce((s, p) => s + (p.amount || 0), 0);
        document.getElementById('search-summary').innerHTML =
            `<strong>${filtered.length}</strong> results — Total: <strong>${fmt(totalAmt)}</strong>`;

        const top200 = filtered.sort((a, b) => (b.amount || 0) - (a.amount || 0)).slice(0, 200);
        document.getElementById('search-results').innerHTML = `
            <table class="data-table">
                <thead><tr><th>ID</th><th>Program</th><th>Section</th><th>Fund</th><th>Amount</th><th>Positions</th></tr></thead>
                <tbody>${top200.map(p => `
                    <tr>
                        <td><a href="#/department/${(p.program_id||'').slice(0,3).toLowerCase()}">${p.program_id}</a></td>
                        <td>${p.program_name}</td>
                        <td>${p.section}</td>
                        <td>${p.fund_category}</td>
                        <td class="amount-cell">${fmt(p.amount)}</td>
                        <td class="amount-cell">${p.positions ? p.positions.toLocaleString(undefined,{maximumFractionDigits:0}) : '—'}</td>
                    </tr>`).join('')}
                </tbody>
            </table>
            ${filtered.length > 200 ? `<p class="muted">Showing top 200 of ${filtered.length} results</p>` : ''}`;

        // Store for export
        window._lastSearchResults = filtered;
    };

    ['search-input', 'filter-fund', 'filter-section', 'filter-dept'].forEach(id => {
        document.getElementById(id)?.addEventListener('input', render);
        document.getElementById(id)?.addEventListener('change', render);
    });

    document.getElementById('export-search')?.addEventListener('click', () => {
        const rows = (window._lastSearchResults || programsData).map(p => ({
            program_id: p.program_id, program_name: p.program_name,
            section: p.section, fund_type: p.fund_type,
            fund_category: p.fund_category, amount: p.amount,
            positions: p.positions || '',
        }));
        downloadCSV(rows, 'budget_search_results.csv');
    });

    render();
};

// ---------------------------------------------------------------------------
// FY Comparison Page
// ---------------------------------------------------------------------------

window.comparePage = async function () {
    if (!fyComparisonData.length) await window.loadFYComparison();

    return `
        <section class="compare-page">
            <a href="#/enacted" class="back-button">← Back to HB300 Budget</a>
            <h2>FY2026 vs FY2027 Comparison</h2>
            <div class="filter-bar">
                <select id="compare-filter" class="filter-select">
                    <option value="all">All Changes</option>
                    <option value="increases">Increases Only</option>
                    <option value="decreases">Decreases Only</option>
                    <option value="new">New in FY2027</option>
                    <option value="removed">Removed in FY2027</option>
                </select>
                <select id="compare-section" class="filter-select">
                    <option value="">All Sections</option>
                    <option value="Operating">Operating</option>
                    <option value="Capital Improvement">Capital Improvement</option>
                </select>
                <button class="action-link export-btn" id="export-compare">⬇ Export CSV</button>
            </div>
            <div class="search-summary" id="compare-summary"></div>
            <div id="compare-results"></div>
        </section>`;
};

window.initComparePage = async function () {
    const render = () => {
        const mode = document.getElementById('compare-filter')?.value || 'all';
        const sec = document.getElementById('compare-section')?.value || '';

        let data = [...fyComparisonData];
        if (sec) data = data.filter(r => r.section === sec);

        if (mode === 'increases') data = data.filter(r => r.delta > 0);
        else if (mode === 'decreases') data = data.filter(r => r.delta < 0);
        else if (mode === 'new') data = data.filter(r => (r.amount_fy2026 || 0) === 0 && (r.amount_fy2027 || 0) > 0);
        else if (mode === 'removed') data = data.filter(r => (r.amount_fy2026 || 0) > 0 && (r.amount_fy2027 || 0) === 0);

        data.sort((a, b) => (a.delta || 0) - (b.delta || 0));

        const totalDelta = data.reduce((s, r) => s + (r.delta || 0), 0);
        document.getElementById('compare-summary').innerHTML =
            `<strong>${data.length}</strong> line items — Net change: <strong>${fmt(totalDelta)}</strong>`;

        const top200 = data.slice(0, 200);
        document.getElementById('compare-results').innerHTML = `
            <table class="data-table">
                <thead><tr><th>Program</th><th>Section</th><th>Fund</th><th>FY2026</th><th>FY2027</th><th>Change</th><th>%</th></tr></thead>
                <tbody>${top200.map(r => {
                    const delta = r.delta || 0;
                    const cls = delta > 0 ? 'positive' : delta < 0 ? 'negative' : '';
                    return `<tr>
                        <td><a href="#/department/${(r.program_id||'').slice(0,3).toLowerCase()}">${r.program_id}</a> ${r.program_name || ''}</td>
                        <td>${r.section || ''}</td>
                        <td>${r.fund_category || ''}</td>
                        <td class="amount-cell">${fmt(r.amount_fy2026)}</td>
                        <td class="amount-cell">${fmt(r.amount_fy2027)}</td>
                        <td class="amount-cell ${cls}">${fmt(delta)}</td>
                        <td class="amount-cell ${cls}">${r.pct_change != null ? fmtPct(r.pct_change) : '—'}</td>
                    </tr>`;
                }).join('')}</tbody>
            </table>
            ${data.length > 200 ? `<p class="muted">Showing top 200 of ${data.length}</p>` : ''}`;

        window._lastCompareResults = data;
    };

    ['compare-filter', 'compare-section'].forEach(id => {
        document.getElementById(id)?.addEventListener('change', render);
    });

    document.getElementById('export-compare')?.addEventListener('click', () => {
        const rows = (window._lastCompareResults || fyComparisonData).map(r => ({
            program_id: r.program_id, program_name: r.program_name,
            section: r.section, fund_type: r.fund_type, fund_category: r.fund_category,
            amount_fy2026: r.amount_fy2026, amount_fy2027: r.amount_fy2027,
            delta: r.delta, pct_change: r.pct_change,
        }));
        downloadCSV(rows, 'fy2026_vs_fy2027_comparison.csv');
    });

    render();
};

// ---------------------------------------------------------------------------
// Historical Trends — 10 years of biennial budget acts, inflation-adjusted
// ---------------------------------------------------------------------------

window.historicalTrendsPage = async function () {
    if (!historicalTrendsData) {
        return `
            <section class="historical-page">
                <div class="error-message">
                    <h2>Historical data unavailable</h2>
                    <p>The <code>historical_trends.json</code> file could not be loaded. Try refreshing the page.</p>
                </div>
            </section>`;
    }

    const meta = historicalTrendsData.metadata;
    const totals = historicalTrendsData.totals_by_fy;
    const fyMin = meta.fy_range[0];
    const fyMax = meta.fy_range[1];
    const baseFy = meta.base_fy;
    const projected = (meta.projected_fys || []);
    const projectedNote = projected.length
        ? `<span class="hist-meta-note">FY${projected.join(', FY')} CPI projected from recent trend.</span>`
        : '';
    const billNotesHtml = (meta.bill_notes || []).map(n =>
        `<li><strong>${n.session}:</strong> ${n.note}</li>`
    ).join('');

    // Act cards, chronological.  Most sessions contribute one card; 2019
    // contributes two (HB2 operating + HB1259 capital) since the biennium
    // was enacted as two separate bills.
    const uniqueSessions = new Set(meta.acts.map(a => a.session)).size;
    const scopeLabel = (scope) => {
        if (scope === 'operating') return 'Operating';
        if (scope === 'capital')   return 'CIP';
        return '';  // combined — no badge
    };
    const actCardsHtml = meta.acts.map(a => {
        const badge = scopeLabel(a.scope);
        const badgeHtml = badge ? `<span class="hist-act-scope">${badge}</span>` : '';
        return `
        <a class="hist-act-card" href="${a.source_url}" target="_blank" rel="noopener" title="${a.act}">
            <span class="hist-act-year">${a.session}</span>
            <span class="hist-act-bill">${a.bill}${badgeHtml}</span>
            <span class="hist-act-fy">FY${a.fy_covered[0]}–${String(a.fy_covered[1]).slice(-2)}</span>
        </a>`;
    }).join('');

    return `
        <section class="historical-page">
            <header class="hist-hero">
                <h2>10 Years of Hawaiʻi's Budget</h2>
                <p class="hist-lead">
                    ${uniqueSessions} biennial appropriations, FY${fyMin}–FY${fyMax}.
                    Toggle <strong>Real (FY${baseFy} $)</strong> to see budget growth net of inflation.
                </p>
                <div class="hist-meta">
                    <span><strong>Source:</strong> ${meta.acts.length} acts across ${uniqueSessions} biennia (CD1, as passed by the Legislature)</span>
                    <span><strong>Inflation index:</strong> ${meta.cpi_source}</span>
                    ${projectedNote}
                </div>
            </header>

            <div class="hist-acts">
                ${actCardsHtml}
            </div>

            <div class="hist-controls">
                <div class="hist-toggle" role="tablist" aria-label="Display mode">
                    <button id="hist-mode-nominal" class="hist-toggle-btn active" data-mode="nominal" type="button">Nominal $</button>
                    <button id="hist-mode-real" class="hist-toggle-btn" data-mode="real" type="button">Real (FY${baseFy} $)</button>
                </div>
                <button id="hist-export-btn" class="hist-export-btn" type="button">Export CSV</button>
            </div>

            <div class="hist-section">
                <h3>Total Appropriations by Fiscal Year</h3>
                <p class="hist-section-sub">Operating + Capital Improvement combined.</p>
                <div class="hist-chart-wrap">
                    <canvas id="hist-totals-chart"></canvas>
                </div>
            </div>

            <div class="hist-section">
                <h3>Composition by Fund Source</h3>
                <p class="hist-section-sub">General Fund vs Special, Federal, Bonds, and other sources.</p>
                <div class="hist-chart-wrap">
                    <canvas id="hist-funds-chart"></canvas>
                </div>
            </div>

            <div class="hist-section">
                <h3>By Department</h3>
                <p class="hist-section-sub">Pick a department to see its 10-year trajectory.</p>
                <div class="hist-dept-controls">
                    <label for="hist-dept-select">Department:</label>
                    <select id="hist-dept-select"></select>
                </div>
                <div class="hist-chart-wrap">
                    <canvas id="hist-dept-chart"></canvas>
                </div>
            </div>

            <div class="hist-section">
                <h3>Year-by-Year Detail</h3>
                <p class="hist-section-sub">Nominal and real-dollar totals with year-over-year change in real dollars.</p>
                <div class="hist-table-wrap">
                    <table class="hist-table">
                        <thead>
                            <tr>
                                <th>Fiscal Year</th>
                                <th class="num">Operating</th>
                                <th class="num">Capital</th>
                                <th class="num">Total (nominal)</th>
                                <th class="num">Total (real, FY${baseFy} $)</th>
                                <th class="num">YoY (real)</th>
                            </tr>
                        </thead>
                        <tbody id="hist-table-body"></tbody>
                    </table>
                </div>
            </div>

            ${billNotesHtml ? `
            <div class="hist-section hist-notes">
                <h4>Coverage notes</h4>
                <ul>${billNotesHtml}</ul>
                <p class="hist-footnote">${meta.notes}</p>
            </div>` : `
            <p class="hist-footnote">${meta.notes}</p>`}
        </section>`;
};

window.initHistoricalTrendsPage = async function () {
    if (!historicalTrendsData) return;

    const data = historicalTrendsData;
    const totals = data.totals_by_fy;
    const baseFy = data.metadata.base_fy;
    const fyLabels = totals.map(t => `FY${t.fy}`);
    const fys = totals.map(t => t.fy);

    let mode = 'nominal';        // 'nominal' | 'real'
    let selectedDept = (data.by_department[0] || {}).dept_code || '';

    let totalsChart = null;
    let fundsChart = null;
    let deptChart = null;

    // Helpers: pull series data based on current mode
    const pickAmount = (entry) => mode === 'real' ? entry.real : entry.nominal;
    const totalKey = () => mode === 'real' ? 'total_real' : 'total_nominal';
    const opKey = () => mode === 'real' ? 'operating_real' : 'operating_nominal';
    const capKey = () => mode === 'real' ? 'capital_real' : 'capital_nominal';

    const fmtBillions = (v) => `$${(v / 1e9).toFixed(2)}B`;

    // Soft palette consistent with the rest of the dashboard
    const palette = [
        '#5a7b68', '#a08e58', '#7d97a3', '#b07560', '#8b6c8e',
        '#6f8d70', '#c2924a', '#5e7d96', '#a87575', '#8b8158',
        '#789689', '#a39378', '#7e93a8', '#b58472', '#928298',
    ];

    // ─── Totals chart (line) ───────────────────────────────────────────
    const renderTotalsChart = () => {
        const canvas = document.getElementById('hist-totals-chart');
        if (!canvas) return;
        if (totalsChart) totalsChart.destroy();

        totalsChart = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: fyLabels,
                datasets: [
                    {
                        label: 'Operating',
                        data: totals.map(t => t[opKey()]),
                        borderColor: '#5a7b68',
                        backgroundColor: 'rgba(90, 123, 104, 0.15)',
                        tension: 0.25,
                        fill: false,
                        borderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                    },
                    {
                        label: 'Capital Improvement',
                        data: totals.map(t => t[capKey()]),
                        borderColor: '#a08e58',
                        backgroundColor: 'rgba(160, 142, 88, 0.15)',
                        tension: 0.25,
                        fill: false,
                        borderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                    },
                    {
                        label: 'Total',
                        data: totals.map(t => t[totalKey()]),
                        borderColor: '#3d4a45',
                        backgroundColor: 'rgba(61, 74, 69, 0.10)',
                        tension: 0.25,
                        fill: false,
                        borderWidth: 3,
                        pointRadius: 5,
                        pointHoverRadius: 7,
                        borderDash: [],
                    },
                ],
            },
            options: {
                maintainAspectRatio: false,
                responsive: true,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${fmtBillions(ctx.parsed.y)}`,
                        },
                    },
                    datalabels: { display: false },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { callback: (v) => `$${(v / 1e9).toFixed(0)}B` },
                        title: { display: true, text: mode === 'real' ? `Constant FY${baseFy} dollars` : 'Nominal dollars' },
                    },
                    x: { grid: { display: false } },
                },
            },
        });
    };

    // ─── Funds chart (stacked bar, top 6 fund categories) ──────────────
    const renderFundsChart = () => {
        const canvas = document.getElementById('hist-funds-chart');
        if (!canvas) return;
        if (fundsChart) fundsChart.destroy();

        const TOP_N = 6;
        const top = data.by_fund_category.slice(0, TOP_N);
        const rest = data.by_fund_category.slice(TOP_N);

        const datasets = top.map((f, i) => ({
            label: f.fund_category,
            data: fys.map(fy => {
                const e = f.series.find(s => s.fy === fy);
                return e ? pickAmount(e) : 0;
            }),
            backgroundColor: palette[i % palette.length],
            borderWidth: 0,
        }));

        if (rest.length) {
            const otherData = fys.map(fy => {
                let sum = 0;
                for (const f of rest) {
                    const e = f.series.find(s => s.fy === fy);
                    if (e) sum += pickAmount(e);
                }
                return sum;
            });
            if (otherData.some(v => v > 0)) {
                datasets.push({
                    label: 'Other',
                    data: otherData,
                    backgroundColor: '#c8c8c8',
                    borderWidth: 0,
                });
            }
        }

        fundsChart = new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: { labels: fyLabels, datasets },
            options: {
                maintainAspectRatio: false,
                responsive: true,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${fmtBillions(ctx.parsed.y)}`,
                        },
                    },
                    datalabels: { display: false },
                },
                scales: {
                    x: { stacked: true, grid: { display: false } },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        ticks: { callback: (v) => `$${(v / 1e9).toFixed(0)}B` },
                    },
                },
            },
        });
    };

    // ─── Department chart (line) ───────────────────────────────────────
    const renderDeptChart = () => {
        const canvas = document.getElementById('hist-dept-chart');
        if (!canvas) return;
        if (deptChart) deptChart.destroy();

        const dept = data.by_department.find(d => d.dept_code === selectedDept);
        if (!dept) return;
        const seriesByFy = new Map(dept.series.map(s => [s.fy, s]));
        const dataPts = fys.map(fy => {
            const e = seriesByFy.get(fy);
            return e ? pickAmount(e) : null;
        });

        deptChart = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: fyLabels,
                datasets: [{
                    label: `${dept.dept_code} — ${dept.dept_name}`,
                    data: dataPts,
                    borderColor: '#5a7b68',
                    backgroundColor: 'rgba(90, 123, 104, 0.18)',
                    tension: 0.25,
                    fill: true,
                    borderWidth: 2.5,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    spanGaps: false,
                }],
            },
            options: {
                maintainAspectRatio: false,
                responsive: true,
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => fmtBillions(ctx.parsed.y),
                        },
                    },
                    datalabels: { display: false },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { callback: (v) => `$${(v / 1e9).toFixed(2)}B` },
                    },
                    x: { grid: { display: false } },
                },
            },
        });
    };

    // ─── Detail table ─────────────────────────────────────────────────
    const renderTable = () => {
        const tbody = document.getElementById('hist-table-body');
        if (!tbody) return;
        const rows = totals.map((t, i) => {
            const prevReal = i > 0 ? totals[i - 1].total_real : null;
            const yoyReal = prevReal ? (t.total_real - prevReal) / prevReal * 100 : null;
            const yoyCls = yoyReal == null ? '' : (yoyReal > 0 ? 'positive' : yoyReal < 0 ? 'negative' : '');
            const yoyTxt = yoyReal == null ? '—' : `${yoyReal > 0 ? '+' : ''}${yoyReal.toFixed(1)}%`;
            return `
                <tr>
                    <td>FY${t.fy}</td>
                    <td class="num">${fmtBillions(t.operating_nominal)}</td>
                    <td class="num">${fmtBillions(t.capital_nominal)}</td>
                    <td class="num">${fmtBillions(t.total_nominal)}</td>
                    <td class="num">${fmtBillions(t.total_real)}</td>
                    <td class="num ${yoyCls}">${yoyTxt}</td>
                </tr>`;
        }).join('');
        tbody.innerHTML = rows;
    };

    // Populate department selector
    const sel = document.getElementById('hist-dept-select');
    if (sel) {
        sel.innerHTML = data.by_department.map(d =>
            `<option value="${d.dept_code}">${d.dept_code} — ${d.dept_name}</option>`
        ).join('');
        sel.value = selectedDept;
        sel.addEventListener('change', () => {
            selectedDept = sel.value;
            renderDeptChart();
        });
    }

    // Mode toggle
    const renderAll = () => {
        renderTotalsChart();
        renderFundsChart();
        renderDeptChart();
    };
    document.querySelectorAll('.hist-toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const newMode = btn.dataset.mode;
            if (newMode === mode) return;
            mode = newMode;
            document.querySelectorAll('.hist-toggle-btn').forEach(b =>
                b.classList.toggle('active', b.dataset.mode === mode)
            );
            renderAll();
        });
    });

    // CSV export
    const exportBtn = document.getElementById('hist-export-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            const rows = totals.map(t => ({
                fiscal_year: t.fy,
                operating_nominal: Math.round(t.operating_nominal),
                operating_real: Math.round(t.operating_real),
                capital_nominal: Math.round(t.capital_nominal),
                capital_real: Math.round(t.capital_real),
                total_nominal: Math.round(t.total_nominal),
                total_real: Math.round(t.total_real),
                deflator: t.deflator,
            }));
            downloadCSV(rows, `hawaii_budget_history_FY${fys[0]}-FY${fys[fys.length - 1]}.csv`);
        });
    }

    renderAll();
    renderTable();
};

// ---------------------------------------------------------------------------
// About / Not Found
// ---------------------------------------------------------------------------

window.aboutPage = async function () {
    return `
        <section class="about-page">
            <div class="about-hero">
                <h2>About This Tracker</h2>
                <p class="about-lead">This dashboard tracks <strong>HB1800</strong>, Hawaiʻi's supplemental appropriations bill for the FY 2026–2027 biennium. It compares the House Draft (HD1) against the Senate Draft (SD1) to show how proposed spending changes as the bill moves through the legislature.</p>
                <p class="about-lead">For historical reference, the <strong>HB300</strong> tab shows the enacted FY2025–26 budget — the appropriations bill that was passed and signed into law last year. HB300 reflects what was actually funded for the current year and serves as a baseline for understanding what HB1800 is building on top of.</p>
                <hr style="margin: 1.5rem 0; border: none; border-top: 1px solid #ddd;">
            </div>

            <div class="about-section">
                <h3>What are HD1 and SD1?</h3>
                <p><strong>HD1</strong> is the bill as amended by the House. <strong>SD1</strong> is the Senate's version. Comparing them reveals which programs gained or lost funding during crossover.</p>
            </div>

            <div class="about-section">
                <h3>Features</h3>
                <ul>
                    <li>HD1 vs SD1 draft comparison with Operating/Capital breakdown</li>
                    <li>Collapsible department grouping with fund-type detail tables</li>
                    <li>Multi-select filters for Section, Fund, and change type</li>
                    <li>Sortable columns and full-text search across programs</li>
                    <li>Export filtered data as CSV</li>
                </ul>
            </div>

            <div class="about-section about-section-process">
                <h3>Hawaiʻi's Budget Process</h3>
                <p>Hawaiʻi's budget bill is a <strong><a href="https://lrb.hawaii.gov/par/overview-of-the-legislative-process/the-budget-process/" target="_blank" rel="noopener">biennial process</a></strong>: the governor prepares a two-year executive budget, the Legislature reviews and amends it, and then it must pass both chambers and be signed into law. In odd-numbered years the governor submits the main budget for the next two fiscal years, and in even-numbered years a supplemental budget can adjust the current biennium.</p>

                <h4>How it starts</h4>
                <p>The process begins inside the executive branch, where state departments <a href="https://budget.hawaii.gov/budget/about-budget/general-budget-process-and-timetable/" target="_blank" rel="noopener">submit spending requests and the Department of Budget and Finance helps shape recommendations before the governor finalizes the proposal</a>. The governor is required to consider the Council on Revenues' forecasts when preparing the budget, because those forecasts help determine how much money the state expects to have.</p>

                <h4>What the Legislature does</h4>
                <p>Once the budget bill reaches the Legislature, it goes through committee hearings, amendments, and the normal lawmaking process. Like other bills, it must receive three readings in each house on separate days, and the House and Senate must agree on the final version before it can move forward.</p>

                <h4>Timing</h4>
                <p>Hawaiʻi's fiscal year runs from July 1 to June 30, and the governor must submit the main budget at least 30 days before the Legislature convenes in an odd-numbered year. The Legislature then works through hearings during session, and the final budget is usually completed near the end of the regular session in spring.</p>

                <h4>Final step</h4>
                <p>After the Legislature passes the bill, it goes to the governor for approval. If the governor signs it, it becomes law; if the governor vetoes it, the Legislature may try to override or revise it under the state's constitutional process.</p>

                <p class="about-summary"><strong>Departments request → the governor proposes → lawmakers revise → the governor signs or vetoes</strong></p>
            </div>

            <a href="#/" class="button primary">← Back to Home</a>
        </section>`;
};

window.notFoundPage = async function () {
    return `
        <section class="not-found-page">
            <h2>Page Not Found</h2>
            <p>The page you're looking for doesn't exist.</p>
            <a href="#/" class="button primary">← Back to Home</a>
        </section>`;
};

// ---------------------------------------------------------------------------
// Draft Comparison Data Loader
// ---------------------------------------------------------------------------

window.loadProjects = async function () {
    try {
        const [r26, r27, rGov] = await Promise.all([
            fetch('./js/projects_fy26.json?v=' + Date.now()).catch(() => null),
            fetch('./js/projects_fy27.json?v=' + Date.now()).catch(() => null),
            fetch('./js/governor_projects.json?v=' + Date.now()).catch(() => null),
        ]);
        if (r26 && r26.ok) projectsDataFY26 = await r26.json();
        if (r27 && r27.ok) projectsDataFY27 = await r27.json();
        if (rGov && rGov.ok) governorProjectsData = await rGov.json();
        return { fy26: projectsDataFY26, fy27: projectsDataFY27, gov: governorProjectsData };
    } catch (e) {
        console.warn('Projects data not available:', e.message);
        return null;
    }
};

window.loadDraftComparison = async function () {
    try {
        const [r26, r27] = await Promise.all([
            fetch('./js/draft_comparison_fy26.json?v=' + Date.now()),
            fetch('./js/draft_comparison_fy27.json?v=' + Date.now()),
        ]);
        if (r26.ok) draftComparisonData = await r26.json();
        if (r27.ok) draftComparisonDataFY27 = await r27.json();
        return draftComparisonData;
    } catch (e) {
        console.warn('Draft comparison data not available:', e.message);
        return null;
    }
};

// Program purposes — short "Program Objective" text harvested from the
// Governor's Executive Budget PDFs (supplemental FY27 → biennial FY25-27 →
// biennial FY23-25 fallback).  Powers the hover tooltip on program-ID rows
// in the HB1800 draft-comparison table.
let programPurposesData = {};
window.loadProgramPurposes = async function () {
    try {
        const r = await fetch('./js/program_purposes.json?v=' + Date.now());
        if (r.ok) {
            const json = await r.json();
            programPurposesData = json.purposes || {};
        }
    } catch (e) {
        console.warn('Program purposes unavailable:', e.message);
    }
};

// Build the class + data-tooltip attributes for a program-ID element.
// Returns an empty string when no objective exists for the ID so the
// markup stays clean (no empty data-tooltip).  Normalizes whitespace in
// the ID (HB1800 uses "AGR122", some sources emit "AGR 122").
// Structure and display helpers for program-objective popovers.
// The raw text comes from program_purposes.json (Governor's budget PDFs).
// Three cases:
//   1. "To [verb]…" multi-sentence stack → each goal as a <li>
//   2. Long plain prose (3+ sentences, >280 chars) → sentence-split <li>s
//   3. Short / single sentence → plain <p>
function _structurePurposeText(text) {
    if (!text) return '';
    // Case 1: "To [verb]..." pattern — already the most common structure
    const toCount = (text.match(/(?:^|\.\s+)To\s+[a-z]/g) || []).length;
    if (toCount >= 2) {
        const parts = text.replace(/\.\s*$/, '').split(/\.\s+(?=To\b)/);
        return '<ul class="purpose-list">' +
            parts.map(p => `<li>${_escHtml(p.trim())}.</li>`).join('') +
            '</ul>';
    }
    // Case 2: Long prose — split on sentence boundaries into scannable bullets
    const sentences = (text.match(/[^.!?]+[.!?]+/g) || []).map(s => s.trim()).filter(Boolean);
    if (sentences.length >= 3 && text.length > 280) {
        return '<ul class="purpose-list">' +
            sentences.map(s => `<li>${_escHtml(s)}</li>`).join('') +
            '</ul>';
    }
    // Case 3: Short or single-sentence — paragraph is fine
    return `<p class="purpose-text">${_escHtml(text)}</p>`;
}

function _buildPurposePopoverHtml(el) {
    const raw = el.getAttribute('data-purpose') || '';
    if (!raw) return '';
    const programId   = el.getAttribute('data-purpose-id')   || el.textContent?.trim() || '';
    const programName = el.getAttribute('data-purpose-name') || '';
    // Flag truncated descriptions (JSON source caps around 500 chars)
    const isTruncated = raw.length >= 498 || !raw.match(/[.!?]\s*$/);
    const body = _structurePurposeText(raw);
    const header = `<div class="reason-pop-header purpose-pop-header">
        <strong>${_escHtml(programId)}</strong>
        <span class="reason-pop-prog-name">${_escHtml(programName)}</span>
    </div>`;
    const truncNote = isTruncated
        ? `<p class="purpose-truncated">See official budget documents for full text.</p>` : '';
    return `${header}<div class="reason-section reason-purpose">
        <div class="reason-chamber-label">Program Objective</div>
        ${body}${truncNote}
    </div>`;
}

function purposeTooltipAttrs(programId) {
    const key = String(programId || '').replace(/\s+/g, '');
    const rec = programPurposesData[key];
    if (!rec || !rec.objective) return '';
    const safe = rec.objective
        .replace(/&/g, '&amp;').replace(/"/g, '&quot;')
        .replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return ` class="has-purpose" data-purpose="${safe}" data-purpose-id="${_escAttr(key)}" tabindex="0"`;
}

// Build the full attribute block (`class="…" data-tooltip="…"`) for a
// row's change-cell explaining WHY the legislature changed the program's
// funding from the Governor's supplemental.  The change-cell `<td>`
// already carries `amount-cell ${cls}` (positive/negative tint), so the
// helper takes those base classes and emits a SINGLE merged `class`
// attribute — emitting two would let HTML drop the second silently and
// strip our hover hook.
//
// Sources are the HB1800 Senate worksheet (EXEC) and the SD-HD
// DISAGREE worksheet, parsed by `scripts/extract_worksheet_reasons.py`
// and merged into draft_comparison_fy*.json as `reason_sd_change` /
// `reason_hd_change`.  When both chambers' reasons exist we label them
// so the reader can tell whose decision drove which delta; the CSS
// uses `white-space: pre-line` to keep the line break between paragraphs.
// HTML-attribute escape (single helper used by all the popover data-* attrs
// below).  Single-quoted attrs are not in play, so escaping `&"<>` is enough.
function _escAttr(s) {
    return String(s == null ? '' : s)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

// Pull the HD1 / SD1 amounts from either an aggregated `p` object (which
// uses `hd1` / `d2` summed fields) or a raw `r` row (which uses
// `amount_hd1` / `amount_sd1`).  Returns [hd, sd] — null when missing.
//
// Note: sd1Active is a closure variable scoped to initDraftComparePage and
// NOT accessible here.  We rely on the fact that when SD1 is toggled OFF,
// d2Key === hd1Key, so p.d2 === p.hd1 and the delta is 0 — correct behaviour
// (no divergence chip when we're only showing one draft column).
function _hdSdAmounts(row) {
    if (!row) return [null, null];
    const hd = row.hd1 != null ? row.hd1 : (row.amount_hd1 != null ? row.amount_hd1 : null);
    // Raw comparison rows carry amount_sd1 directly.  Aggregated `p` objects
    // carry the column sum in `d2` (which equals amount_sd1 totals when SD1
    // is active, or amount_hd1 totals when SD1 is toggled off → delta = 0).
    let sd = null;
    if (row.amount_sd1 != null) sd = row.amount_sd1;
    else if (row.d2 != null) sd = row.d2;
    return [hd, sd];
}

// Cell attrs for the change cell.  Emits a `has-reason` class plus the
// data-* attrs the popover handler reads on hover.  The popover element
// is created on-demand by ensureReasonPopover() and shared across all
// cells (no per-cell DOM bloat).
function changeReasonCellAttrs(row, baseClass) {
    const base = baseClass ? ` class="${baseClass}"` : '';
    if (!row) return base;
    // Don't surface a reason tooltip when this fiscal year has no net
    // change — the worksheet reasons cover both FY26 and FY27 and can
    // otherwise leak onto rows where the delta is $0 for that year.
    if (!row.change || Math.abs(row.change) < 1) return base;
    const sd = row.reason_sd_change || '';
    const hd = row.reason_hd_change || '';
    if (!sd && !hd) return base;
    const [hdAmt, sdAmt] = _hdSdAmounts(row);
    const cls = `${baseClass ? baseClass + ' ' : ''}has-reason`;
    const attrs = [
        ` class="${cls}"`,
        ` data-reason-sd="${_escAttr(sd)}"`,
        ` data-reason-hd="${_escAttr(hd)}"`,
        ` data-program-id="${_escAttr(row.program_id || '')}"`,
        ` data-program-name="${_escAttr(row.program_name || '')}"`,
        hdAmt != null ? ` data-amt-hd="${hdAmt}"` : '',
        sdAmt != null ? ` data-amt-sd="${sdAmt}"` : '',
        ` tabindex="0"`,
    ];
    return attrs.join('');
}

// Inline HD↔SD divergence chip.  Returns `<span>` markup when the two
// chambers landed on different numbers for this row; empty string
// otherwise.  Reads HD/SD via _hdSdAmounts() so it works for both
// aggregated `p` and raw `r`.  Threshold of $1 absorbs floating-point
// noise without losing real divergences.
function divergenceChipHtml(row) {
    if (!row) return '';
    if (typeof sd1Active !== 'undefined' && !sd1Active) return '';
    const [hdAmt, sdAmt] = _hdSdAmounts(row);
    if (hdAmt == null || sdAmt == null) return '';
    const delta = sdAmt - hdAmt;
    if (Math.abs(delta) < 1) return '';
    const sign = delta > 0 ? '+' : '−';
    const abs = Math.abs(delta);
    let short;
    if (abs >= 1e9) short = `$${(abs / 1e9).toFixed(2)}B`;
    else if (abs >= 1e6) short = `$${(abs / 1e6).toFixed(2)}M`;
    else if (abs >= 1e3) short = `$${(abs / 1e3).toFixed(0)}K`;
    else short = `$${Math.round(abs).toLocaleString()}`;
    const dirClass = delta > 0 ? 'pos' : 'neg';
    const tipText = delta > 0
        ? `Senate added ${short} vs House`
        : `Senate cut ${short} vs House`;
    return ` <span class="hd-sd-pill ${dirClass}" title="${_escAttr(tipText)}">SD ${sign}${short} <span class="hd-sd-pill-meta">vs HD</span></span>`;
}

// ---------------------------------------------------------------------------
// Reason popover — formatted hover/focus card for change-cell tooltips.
// One shared element on the body; cells declare their content via data-*
// attrs on the cell.  Keeps DOM weight small even with hundreds of rows.
// ---------------------------------------------------------------------------

// Hawaii-government acronyms + short tokens worth keeping uppercase in the
// soft-cased reason text.  Worksheets are screamy ALL CAPS; lowercasing
// makes them readable, but program IDs and acronyms still need to pop.
const _REASON_ACRONYMS = new Set([
    'CIP', 'MOF', 'POS', 'FTP', 'FTS', 'FY', 'GO', 'GE', 'EA', 'HD', 'SD',
    'HMS', 'EDN', 'AGR', 'BED', 'TRN', 'LNR', 'UOH', 'DEF', 'PSD', 'AGS',
    'LBR', 'TAX', 'BUF', 'HRD', 'HTH', 'LAW', 'JUD', 'CCA', 'ATG', 'GOV',
    'LTG', 'OHA', 'SUB', 'COH', 'STA', 'DOH', 'DOE', 'DOT', 'DLNR'
]);

// Title-ish-case the screamy worksheet titles.  Goal: readable sentence
// case, but program IDs (3-letter prefix + 3–4 digits) and known
// acronyms stay uppercase.  Hawaii / Hawaiian get title-cased explicitly.
function _softCaseReason(text) {
    if (!text) return '';
    // Full lowercase first, then re-capitalize selectively.
    let out = text.toLowerCase();
    // Program IDs: XXX###[#] — always uppercase
    out = out.replace(/\b([a-z]{3}\d{3,4})\b/g, m => m.toUpperCase());
    // Known acronyms — case-insensitive, restore upper case
    out = out.replace(/\b([a-z]{2,5})\b/g, (m) => {
        const upper = m.toUpperCase();
        return _REASON_ACRONYMS.has(upper) ? upper : m;
    });
    // Hawaii / Hawaiian title-cased
    out = out.replace(/\bhawaii\b/g, 'Hawaii').replace(/\bhawaiian\b/g, 'Hawaiian');
    // Capitalize the very first letter
    out = out.charAt(0).toUpperCase() + out.slice(1);
    return out;
}

// Split the joined reason sentence ("ACTION ONE; ACTION TWO; ACTION THREE.")
// back into its constituent SEQ # actions.  The extractor joins with `; `
// and ends with `.`; we strip the trailing period and split.
function _bulletizeReason(text) {
    if (!text) return [];
    return text.replace(/\.\s*$/, '').split(/;\s+/).filter(s => s.trim());
}

// Compact short-form formatter used for chamber-amount badges in the
// popover.  Mirrors fmtHtml() output but returns plain text.
function _fmtShort(amount) {
    if (amount == null) return '$0';
    const abs = Math.abs(amount);
    const sign = amount < 0 ? '-' : '';
    if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}B`;
    if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(2)}M`;
    if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(0)}K`;
    return `${sign}$${Math.round(abs).toLocaleString()}`;
}

// Lazily create the singleton popover element.  Detached body child so
// it can sit above any overflow-hidden ancestor without z-index fights.
function _ensureReasonPopover() {
    let pop = document.getElementById('reason-popover');
    if (pop) return pop;
    pop = document.createElement('div');
    pop.id = 'reason-popover';
    pop.className = 'reason-popover';
    pop.setAttribute('role', 'tooltip');
    pop.style.display = 'none';
    document.body.appendChild(pop);
    return pop;
}

// HTML escape for the popover body content (going into innerHTML).
function _escHtml(s) {
    return String(s == null ? '' : s)
        .replace(/&/g, '&amp;').replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Build the popover inner HTML for a given cell.  Reads data-* attrs;
// returns an empty string if neither chamber has reason text (caller
// suppresses the show in that case).
function _buildReasonPopoverHtml(cell) {
    const sd = cell.getAttribute('data-reason-sd') || '';
    const hd = cell.getAttribute('data-reason-hd') || '';
    if (!sd && !hd) return '';
    const programId = cell.getAttribute('data-program-id') || '';
    const programName = cell.getAttribute('data-program-name') || '';
    const hdAmt = parseFloat(cell.getAttribute('data-amt-hd'));
    const sdAmt = parseFloat(cell.getAttribute('data-amt-sd'));

    // Net delta vs the other chamber — resolves apparent contradictions like
    // "Reduce funds; Add funds" which just means a fund-source reallocation.
    // Show "+$1.1M vs HD" or "−$26.8M vs SD" so the reader can verify the
    // net result without doing the mental arithmetic across fund rows.
    const sdDelta = isFinite(sdAmt) && isFinite(hdAmt) ? sdAmt - hdAmt : NaN;
    const hdDelta = isFinite(hdAmt) && isFinite(sdAmt) ? hdAmt - sdAmt : NaN;
    const _signedFmt = (n) => (n > 0 ? '+' : '') + _fmtShort(n);

    const buildSection = (label, raw, amt, klass, delta) => {
        if (!raw) return '';
        const items = _bulletizeReason(raw)
            .map(p => `<li>${_escHtml(_softCaseReason(p))}.</li>`)
            .join('');
        const vsLabel = klass === 'senate' ? 'vs HD' : 'vs SD';
        // Amount badge: show the chamber's total, plus a "net ±$X vs <other>"
        // suffix when there's a computable delta.  Resolves contradictions like
        // "Reduce funds; Add funds" (= fund reallocation, net may be near-zero).
        const amtBadge = isFinite(amt)
            ? `<span class="reason-amt">${_fmtShort(amt)}</span>` : '';
        const deltaChip = (isFinite(delta) && Math.abs(delta) >= 1)
            ? `<span class="reason-net ${delta >= 0 ? 'pos' : 'neg'}">${_signedFmt(delta)} ${vsLabel}</span>`
            : '';
        return `<div class="reason-section reason-${klass}">
            <div class="reason-chamber-label">${label}${amtBadge}${deltaChip}</div>
            <ul class="reason-list">${items}</ul>
        </div>`;
    };

    const header = programId
        ? `<div class="reason-pop-header">
             <strong>${_escHtml(programId)}</strong>
             <span class="reason-pop-prog-name">${_escHtml(programName)}</span>
           </div>` : '';

    const hdSection = buildSection('House', hd, hdAmt, 'house', hdDelta);
    const sdSection = buildSection('Senate', sd, sdAmt, 'senate', sdDelta);
    // House on top when both — chronological order (House drafts first,
    // Senate amends).  When only one chamber has text, just show that one.
    return header + hdSection + sdSection;
}

// Position the popover relative to the triggering cell.  Three-step
// fallback to keep tall popovers fully on-screen:
//   1. Try below-right of the cell.
//   2. If it overflows the bottom and there's more room above, flip up.
//   3. If it still overflows (popover is taller than the available
//      vertical slot), pin to the larger slot and let the popover's
//      max-height + overflow-y CSS rule scroll the content internally.
function _positionReasonPopover(pop, cell) {
    const r = cell.getBoundingClientRect();
    const margin = 8;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    // Reset any prior pinned max-height so we measure the natural size.
    pop.style.maxHeight = '';
    pop.style.display = 'block';
    pop.style.visibility = 'hidden';
    pop.style.left = '0px';
    pop.style.top = '0px';
    const popRect = pop.getBoundingClientRect();
    const popH = popRect.height;
    const popW = popRect.width;

    // Horizontal: right-anchored, clamped to viewport.
    let left = r.right + window.scrollX - popW;
    if (left < window.scrollX + margin) left = r.left + window.scrollX;
    left = Math.max(window.scrollX + margin,
                    Math.min(left, window.scrollX + vw - popW - margin));

    // Vertical: prefer below the cell, but fall back to above when below
    // overflows.  If neither fits, anchor to whichever side has more room
    // and cap height so the popover scrolls instead of clipping.
    const spaceBelow = vh - r.bottom - margin;
    const spaceAbove = r.top - margin;
    const gap = 6;
    let top;
    if (popH + gap <= spaceBelow) {
        top = r.bottom + window.scrollY + gap;
    } else if (popH + gap <= spaceAbove) {
        top = r.top + window.scrollY - popH - gap;
    } else if (spaceBelow >= spaceAbove) {
        top = r.bottom + window.scrollY + gap;
        pop.style.maxHeight = `${Math.max(160, spaceBelow - gap)}px`;
    } else {
        const cap = Math.max(160, spaceAbove - gap);
        top = r.top + window.scrollY - cap - gap;
        pop.style.maxHeight = `${cap}px`;
    }

    pop.style.left = `${left}px`;
    pop.style.top  = `${top}px`;
    pop.style.visibility = 'visible';
}

// One-time wire-up of delegated hover/focus handlers.  Idempotent: a
// flag on the body avoids double-binding when the page re-renders.
function initReasonPopoverHandlers() {
    if (document.body.dataset.reasonPopBound === '1') return;
    document.body.dataset.reasonPopBound = '1';
    const pop = _ensureReasonPopover();
    let activeCell = null;
    let hideTimer = null;

    // Find the nearest triggering element — either a change-reason cell
    // or a program-objective ID.  Both share the same popover element.
    const _triggerEl = (target) =>
        target.closest('.has-reason') || target.closest('.has-purpose');

    const show = (cell) => {
        if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
        if (activeCell === cell) return;
        const html = cell.classList.contains('has-purpose')
            ? _buildPurposePopoverHtml(cell)
            : _buildReasonPopoverHtml(cell);
        if (!html) return;
        // Tag popover type so CSS can style accordingly
        pop.dataset.popType = cell.classList.contains('has-purpose') ? 'purpose' : 'reason';
        activeCell = cell;
        pop.innerHTML = html;
        _positionReasonPopover(pop, cell);
    };
    const hideSoon = () => {
        hideTimer = setTimeout(() => {
            pop.style.display = 'none';
            activeCell = null;
        }, 80);  // small grace so the user can move into the popover itself
    };
    const cancelHide = () => {
        if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
    };

    document.addEventListener('mouseover', (e) => {
        const cell = _triggerEl(e.target);
        if (cell) show(cell);
        else if (e.target.closest('#reason-popover')) cancelHide();
    });
    document.addEventListener('mouseout', (e) => {
        const cell = _triggerEl(e.target);
        if (cell && !cell.contains(e.relatedTarget) && !pop.contains(e.relatedTarget)) {
            hideSoon();
        } else if (e.target.closest('#reason-popover') &&
                   !pop.contains(e.relatedTarget) &&
                   (!activeCell || !activeCell.contains(e.relatedTarget))) {
            hideSoon();
        }
    });
    document.addEventListener('focusin', (e) => {
        const cell = _triggerEl(e.target);
        if (cell) show(cell);
    });
    document.addEventListener('focusout', (e) => {
        const cell = _triggerEl(e.target);
        if (cell && !cell.contains(e.relatedTarget)) hideSoon();
    });
    // Hide on scroll/resize — repositioning during scroll feels janky.
    window.addEventListener('scroll', () => {
        if (activeCell) { pop.style.display = 'none'; activeCell = null; }
    }, { passive: true });
    window.addEventListener('resize', () => {
        if (activeCell) { pop.style.display = 'none'; activeCell = null; }
    });
}

// ---------------------------------------------------------------------------
// Draft Comparison Page
// ---------------------------------------------------------------------------

window.draftComparePage = async function () {
    const hasData = (draftComparisonData && draftComparisonData.comparisons) ||
                    (draftComparisonDataFY27 && draftComparisonDataFY27.comparisons);
    if (!hasData) {
        return `
            <section class="compare-page">
                <h2>Draft Comparison</h2>
                <div class="empty-state">
                    <p>No draft comparison data available yet.</p>
                    <p>To generate a comparison, run:</p>
                    <pre>python scripts/download_bill.py HB1800 --all
python scripts/compare_drafts.py --draft1 HD1 --draft2 SD1 --fy 2026 --output docs/js/draft_comparison_fy26.json
python scripts/compare_drafts.py --draft1 HD1 --draft2 SD1 --fy 2027 --output docs/js/draft_comparison_fy27.json</pre>
                </div>
            </section>`;
    }

    const initData = draftComparisonData || draftComparisonDataFY27;
    const meta = initData.metadata;

    const fyToggle = (draftComparisonData && draftComparisonDataFY27) ? `
        <div class="fy-seg-ctrl" data-active="26">
            <button id="fy-btn-26" data-fy="26" class="active">FY2026</button>
            <button id="fy-btn-27" data-fy="27">FY2027</button>
        </div>` : (draftComparisonDataFY27 ? '<div class="fy-seg-ctrl" data-active="27"><button class="active" data-fy="27">FY2027</button></div>' : '');

    return `
        <section class="compare-page">
            <div class="compare-controls-bar">
                <div class="compare-scope-row">
                    <span class="compare-scope-label">Viewing</span>
                    ${fyToggle}
                </div>
                <div class="compare-timeline" id="compare-timeline">
                    <!-- Row 1: column labels -->
                    <div class="tl-corner tl-corner-labels"></div>
                    <span class="tl-label" data-col="gov" data-row="labels">Gov.</span>
                    <span class="tl-label" data-col="hd1" data-row="labels">HD1</span>
                    <span class="tl-label" data-col="sd1" data-row="labels">SD1</span>
                    <span class="tl-label" data-col="net" data-row="labels">Net Change</span>

                    <!-- Row 2: dots and sparkline -->
                    <div class="tl-corner tl-corner-dots"></div>
                    <div class="tl-dot-row" data-col="gov" data-row="dots">
                        <span class="tl-seg tl-seg-before"></span>
                        <label class="tl-dot-lbl" for="tl-gov"><span class="tl-dot"></span></label>
                        <span class="tl-seg tl-seg-after"></span>
                    </div>
                    <div class="tl-dot-row" data-col="hd1" data-row="dots">
                        <span class="tl-seg tl-seg-before"></span>
                        <label class="tl-dot-lbl" for="tl-hd1"><span class="tl-dot"></span></label>
                        <span class="tl-seg tl-seg-after"></span>
                    </div>
                    <div class="tl-dot-row" data-col="sd1" data-row="dots">
                        <span class="tl-seg tl-seg-before"></span>
                        <label class="tl-dot-lbl" for="tl-sd1"><span class="tl-dot"></span></label>
                        <span class="tl-seg tl-seg-after"></span>
                    </div>
                    <div class="tl-net-spark-row" data-col="net" data-row="dots">
                        <svg class="tl-net-spark" id="tl-net-spark" viewBox="0 0 60 20" aria-hidden="true"></svg>
                    </div>

                    <!-- Row 3: total amounts; caret sits in the left rail -->
                    <div class="tl-corner tl-corner-caret">
                        <button class="tl-expand-caret" id="tl-expand-btn" aria-label="Show breakdown">▾</button>
                    </div>
                    <span class="tl-amt" id="tl-amt-gov" data-col="gov" data-row="totals"></span>
                    <span class="tl-amt" id="tl-amt-hd1" data-col="hd1" data-row="totals"></span>
                    <span class="tl-amt" id="tl-amt-sd1" data-col="sd1" data-row="totals"></span>
                    <span class="tl-amt tl-net-chip" id="tl-amt-net" data-col="net" data-row="totals"></span>

                    <!-- Row 4: Operating breakdown (toggled).
                         The .tl-band spans all 5 columns and paints the
                         zebra tint as one continuous rectangle regardless
                         of per-cell width. Values sit above it via z-index. -->
                    <div class="tl-band" data-row="op" hidden></div>
                    <div class="tl-bd-label has-tooltip" data-row="op" data-tooltip="The operating budget pays for the state&rsquo;s ongoing, day-to-day services like salaries, programs, and utilities each year." hidden>Operating</div>
                    <span class="tl-bd-cell" id="tl-bd-op-gov" data-col="gov" data-row="op" hidden></span>
                    <span class="tl-bd-cell" id="tl-bd-op-hd1" data-col="hd1" data-row="op" hidden></span>
                    <span class="tl-bd-cell" id="tl-bd-op-sd1" data-col="sd1" data-row="op" hidden></span>
                    <span class="tl-bd-cell" id="tl-bd-op-net" data-col="net" data-row="op" hidden></span>

                    <!-- Row 5: Capital breakdown (toggled) -->
                    <div class="tl-band" data-row="cap" hidden></div>
                    <div class="tl-bd-label has-tooltip" data-row="cap" data-tooltip="The capital budget pays for building and fixing long-term physical projects like schools, roads, and other facilities." hidden>Capital</div>
                    <span class="tl-bd-cell" id="tl-bd-cap-gov" data-col="gov" data-row="cap" hidden></span>
                    <span class="tl-bd-cell" id="tl-bd-cap-hd1" data-col="hd1" data-row="cap" hidden></span>
                    <span class="tl-bd-cell" id="tl-bd-cap-sd1" data-col="sd1" data-row="cap" hidden></span>
                    <span class="tl-bd-cell" id="tl-bd-cap-net" data-col="net" data-row="cap" hidden></span>

                    <!-- Hidden checkboxes (state toggles; labels for these are the dots above) -->
                    <input type="checkbox" class="tl-cb" id="tl-gov" checked>
                    <input type="checkbox" class="tl-cb" id="tl-hd1" checked>
                    <input type="checkbox" class="tl-cb" id="tl-sd1" checked>
                </div>
            </div>

            <div id="draft-cards"></div>

            <div class="search-row">
                <div class="search-summary" id="draft-summary"></div>
            </div>
            <div id="draft-results"></div>

            <div id="projects-section" class="projects-section">
                <h3>Capital Projects</h3>
                <p class="section-desc">Project-level detail for capital appropriations. Click a <span class="section-chip section-chip-link" style="pointer-events:none;">Capital Improvement →</span> chip on any program row to jump to that program's projects.</p>
                <div id="projects-list"></div>
            </div>

            <div id="fund-detail-section"></div>

            <div class="draft-meta-bar">
                <span>See also: <a href="https://hiappleseed.org/publications/hawaii-budget-primer-fy202526" target="_blank" rel="noopener">Hawaiʻi Budget Primer FY2025–26</a></span>
            </div>
        </section>`;
};

window.initDraftComparePage = async function () {
    initReasonPopoverHandlers();
    const hasData = (draftComparisonData && draftComparisonData.comparisons) ||
                    (draftComparisonDataFY27 && draftComparisonDataFY27.comparisons);
    if (!hasData) return;

    let activeData = draftComparisonData || draftComparisonDataFY27;
    let activeProjects = draftComparisonData ? projectsDataFY26 : projectsDataFY27;
    let expandedProjectPrograms = new Set();
    let sortCol = 'change';
    let sortDir = 'asc';
    let projSortCol = 'change'; // capital projects table sort
    let projSortDir = 'desc';
    // Frozen order — captured on FY toggle so rows don't reshuffle around the
    // anchor. Cleared when the user explicitly clicks a sort column header.
    let frozenDeptOrder = null;        // Array<string> | null — dept codes, main table
    let frozenProgOrder = null;        // Map<deptCode, Array<program_id>> | null
    let frozenProjDeptOrder = null;    // Array<string> | null — capital projects table
    let frozenFundOrder = null;        // Array<string> | null — fund detail table
    let checkedSections = null; // null = all
    let checkedFunds = null;    // null = all
    let expandedDepts = new Set();
    let expandedFundTypes = new Set();
    let expandedPrograms = new Set();
    let expandedFunds = new Set();
    // Timeline state: which nodes are active (all true = Gov's Request → HD1 → SD1)
    let govActive = true;
    let hd1Active = true;
    let sd1Active = true;
    let showBreakdown = false; // whether Op/Cap sub-chips are visible under each node

    // Build baseline lookup from governorRequestData.
    // Key includes department_code + section so that a program which exists
    // under dept A in the governor's request but was moved/added under dept B
    // in the legislature's drafts doesn't inherit dept A's baseline value.
    const baselineLookup = new Map();
    for (const r of (governorRequestData || [])) {
        baselineLookup.set(`${r.department_code}_${r.program_id}_${r.fund_type}_${r.section}`, r);
    }

    // Inject amount_baseline into each comparison record (once at init)
    const injectBaseline = (dataset) => {
        const fyKey = dataset.metadata.fiscal_year === 2026 ? 'amount_fy2026' : 'amount_fy2027';
        for (const r of dataset.comparisons) {
            const match = baselineLookup.get(`${r.department_code}_${r.program_id}_${r.fund_type}_${r.section}`);
            r.amount_baseline = match ? (match[fyKey] || 0) : 0;
        }
    };
    if (draftComparisonData) injectBaseline(draftComparisonData);
    if (draftComparisonDataFY27) injectBaseline(draftComparisonDataFY27);

    // Inject "orphan" Gov records: programs that exist in the Gov request under
    // dept A but are absent entirely from HD1/SD1 under dept A (typically because
    // the program was moved to dept B in the legislature's drafts). Without this,
    // those Gov dollars are dropped from the tables — the table totals drift
    // from the timeline totals by exactly that amount. By injecting a synthetic
    // "removed" comparison row at dept A carrying the Gov amount as baseline and
    // zeros for HD1/SD1, the dept-A total now reflects the actual dept A → dept B
    // flow and the paired program row under dept B is recognized as the sibling.
    const injectOrphans = (dataset) => {
        if (!dataset || !governorRequestData) return;
        const fyKey = dataset.metadata.fiscal_year === 2026 ? 'amount_fy2026' : 'amount_fy2027';
        const hd1Key = 'amount_' + dataset.metadata.draft1.toLowerCase();
        const sd1Key = 'amount_' + dataset.metadata.draft2.toLowerCase();
        const present = new Set();
        for (const r of dataset.comparisons) {
            present.add(`${r.department_code}_${r.program_id}_${r.fund_type}_${r.section}`);
        }
        for (const g of governorRequestData) {
            const key = `${g.department_code}_${g.program_id}_${g.fund_type}_${g.section}`;
            if (present.has(key)) continue;
            const amt = g[fyKey] || 0;
            if (amt === 0) continue;
            dataset.comparisons.push({
                program_id: g.program_id,
                program_name: g.program_name || '',
                department_code: g.department_code,
                department_name: g.department_name || '',
                fund_type: g.fund_type,
                fund_category: g.fund_category || '',
                section: g.section,
                [hd1Key]: 0,
                [sd1Key]: 0,
                change: 0,
                pct_change: 0,
                change_type: 'removed',
                amount_baseline: amt,
                _govOrphan: true,
            });
        }
    };
    if (draftComparisonData) injectOrphans(draftComparisonData);
    if (draftComparisonDataFY27) injectOrphans(draftComparisonDataFY27);

    // Derived getters: leftmost active = d1, rightmost active = d2
    const getD1Key = () => govActive ? 'amount_baseline' : 'amount_' + activeData.metadata.draft1.toLowerCase();
    const getD2Key = () => sd1Active ? 'amount_' + activeData.metadata.draft2.toLowerCase() : 'amount_' + activeData.metadata.draft1.toLowerCase();
    const getD1Label = () => govActive ? "Gov's Request" : activeData.metadata.draft1;
    const getD2Label = () => sd1Active ? activeData.metadata.draft2 : activeData.metadata.draft1;
    const getChangeLabel = (sortArrowHtml = '') => {
        const from = govActive ? 'Gov.' : 'HD1';
        const to = sd1Active ? 'SD1' : 'HD1';
        return `Change${sortArrowHtml}<span class="th-sub">${from} → ${to}</span>`;
    };
    // HD1 is a visible middle column only when it is active AND is not itself an endpoint
    const showHD1Col = () => hd1Active && govActive && sd1Active;

    // Shorten fund category names for display (e.g., "General Funds" → "General")
    const shortFund = (cat) => {
        if (!cat) return '';
        const map = {
            'General Funds': 'General',
            'Special Funds': 'Special',
            'Federal Funds': 'Federal',
            'Other Federal Funds': 'Other Federal',
            'General Obligation Bond Fund': 'GO Bond',
            'Revenue Bond Funds': 'Revenue Bond',
            'Revolving Funds': 'Revolving',
            'Trust Funds': 'Trust',
            'Interdepartmental Transfers': 'Interdept',
            'Private Contributions': 'Private',
            'County Funds': 'County',
            'Other Funds': 'Other',
        };
        return map[cat] || cat.replace(/ Funds?$/, '');
    };

    // --- Summary cards ---

    const updateSummaryCards = () => {
        const meta = activeData.metadata;
        const d2Key = getD2Key();
        const d2Label = getD2Label();
        const recs = activeData.comparisons;
        const fyKey = meta.fiscal_year === 2026 ? 'amount_fy2026' : 'amount_fy2027';

        const sumBy = (section) => {
            const sr = recs.filter(r => r.section === section);
            const hd1AmtKey = 'amount_' + meta.draft1.toLowerCase(); // always amount_hd1
            const hd1 = sr.reduce((s, r) => s + (r[hd1AmtKey] || 0), 0);
            const d2 = sr.reduce((s, r) => s + (r[d2Key] || 0), 0);
            // Baseline totals from governorRequestData (full, not joined — avoids missing programs)
            const baseline = (governorRequestData || [])
                .filter(r => r.section === section)
                .reduce((s, r) => s + (r[fyKey] || 0), 0);
            // d1 is either Gov's Request (full baseline) or HD1 depending on leftmost active node
            const d1 = govActive ? baseline : hd1;
            return { d1, d2, delta: d2 - d1, baseline, hd1 };
        };
        const op  = sumBy('Operating');
        const cap = sumBy('Capital Improvement');

        // Totals (always shown in main chips)
        const totGov = op.baseline + cap.baseline;
        const totHD1 = op.hd1 + cap.hd1;
        const totSD1 = op.d2 + cap.d2;
        const totD1  = op.d1 + cap.d1;
        const totNet = totSD1 - totD1;
        const netCls = totNet > 0 ? 'positive' : totNet < 0 ? 'negative' : '';
        const netPct = totD1 !== 0 ? (totNet / Math.abs(totD1)) * 100 : (totNet !== 0 ? 100 : 0);

        // Keep aliases so the rest of the function (Net node, etc.) stays readable
        const tabNet = totNet;

        const cardsEl = document.getElementById('draft-cards');
        if (!cardsEl) return;

        // Build node list with total values
        const nodes = [];
        if (govActive) nodes.push({ val: totGov, label: "Gov's Request" });
        if (hd1Active) nodes.push({ val: totHD1, label: 'HD1' });
        if (sd1Active) nodes.push({ val: totSD1, label: d2Label });

        // Compact format for amounts shown directly under each timeline dot
        const fmtShort = (n) => {
            if (n == null) return '';
            const abs = Math.abs(n);
            const sign = n < 0 ? '-' : '';
            if (abs >= 1e9) return `${sign}$${+(abs / 1e9).toFixed(1)}B`;
            if (abs >= 1e6) return `${sign}$${+(abs / 1e6).toFixed(0)}M`;
            if (abs >= 1e3) return `${sign}$${+(abs / 1e3).toFixed(0)}K`;
            return `${sign}$${abs.toFixed(0)}`;
        };

        // Two-tone HTML rendering: prominent number + smaller, dimmer
        // currency suffix (B / M / K). Visual hero is the number itself.
        const fmtShortHTML = (n) => {
            const s = fmtShort(n);
            if (!s) return '';
            const m = s.match(/^([-−]?\$[0-9.]+)([BMK]?)$/);
            if (!m) return s;
            const [, num, suffix] = m;
            return `<span class="tl-amt-num">${num}</span>` +
                (suffix ? `<span class="tl-amt-suffix">${suffix}</span>` : '');
        };

        // Update main Total amounts directly under each dot
        [
            { id: 'tl-amt-gov', val: totGov },
            { id: 'tl-amt-hd1', val: totHD1 },
            { id: 'tl-amt-sd1', val: totSD1 },
        ].forEach(({ id, val }) => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = fmtShortHTML(val);
        });

        // Populate per-cell Operating / Capital breakdown values (grid layout).
        // IDs follow the pattern tl-bd-{op|cap}-{gov|hd1|sd1|net}.
        const signed = (n) => (n > 0 ? '+' : '') + fmtShort(n);
        const cells = [
            { col: 'gov', opV: op.baseline,         capV: cap.baseline,         fmt: fmtShort },
            { col: 'hd1', opV: op.hd1,              capV: cap.hd1,              fmt: fmtShort },
            { col: 'sd1', opV: op.d2,               capV: cap.d2,               fmt: fmtShort },
            { col: 'net', opV: op.d2 - op.d1,       capV: cap.d2 - cap.d1,      fmt: signed   },
        ];
        cells.forEach(({ col, opV, capV, fmt }) => {
            const opEl  = document.getElementById(`tl-bd-op-${col}`);
            const capEl = document.getElementById(`tl-bd-cap-${col}`);
            if (opEl)  opEl.textContent  = fmt(opV);
            if (capEl) capEl.textContent = fmt(capV);
        });
        // Toggle visibility of every breakdown cell + the two row labels.
        document.querySelectorAll('.compare-timeline [data-row="op"], .compare-timeline [data-row="cap"]').forEach(el => {
            el.hidden = !showBreakdown;
        });

        // Net-direction state — lives on .compare-timeline and cascades
        // to all [data-col="net"] cells (sparkline + chip + breakdown).
        const tlCmp = document.getElementById('compare-timeline');
        if (tlCmp) {
            tlCmp.classList.toggle('net-positive', netCls === 'positive');
            tlCmp.classList.toggle('net-negative', netCls === 'negative');
        }
        // Inline arrow + amount + percentage inside a single chip.
        // The arrow replaces the old circle-in-dot-row marker.
        const netAmtEl  = document.getElementById('tl-amt-net');
        if (netAmtEl) {
            const sign = tabNet > 0 ? '+' : '';
            const arrow = tabNet > 0 ? '▲' : tabNet < 0 ? '▼' : '●';
            const pct = Math.abs(netPct) < 0.01 && tabNet === 0
                ? '0%'
                : `${sign}${netPct.toFixed(netPct > -10 && netPct < 10 ? 2 : 1)}%`;
            netAmtEl.innerHTML =
                `<span class="tl-net-val">${sign}${fmtShort(tabNet)}</span>`;
        }
        // Sparkline: three dots (Gov / HD1 / SD1) with the last highlighted.
        // Vertically scales to the range of the three totals so visually-tiny
        // deltas still show a slope.
        const spark = document.getElementById('tl-net-spark');
        if (spark) {
            const vs = [totGov, totHD1, totSD1];
            const mn = Math.min(...vs), mx = Math.max(...vs);
            const range = mx - mn || 1;
            const y = v => (15 - ((v - mn) / range) * 10).toFixed(1);
            const xs = [6, 30, 54];
            const pts = vs.map((v, i) => `${xs[i]},${y(v)}`).join(' ');
            spark.innerHTML =
                `<polyline class="tl-spark-line" points="${pts}"/>` +
                `<circle class="tl-spark-dot" cx="${xs[0]}" cy="${y(vs[0])}" r="1.7"/>` +
                `<circle class="tl-spark-dot" cx="${xs[1]}" cy="${y(vs[1])}" r="1.7"/>` +
                `<circle class="tl-spark-dot tl-spark-dot-end" cx="${xs[2]}" cy="${y(vs[2])}" r="2.7"/>`;
        }
        // Update expand caret on Gov amount row
        const expandBtn = document.getElementById('tl-expand-btn');
        if (expandBtn) expandBtn.classList.toggle('open', showBreakdown);

        // draft-cards is now empty (toggle lives on the Net Change label)
        cardsEl.innerHTML = '';
    };

    // --- Build checkbox options from data ---

    const getAllSections = () => [...new Set(activeData.comparisons.map(r => r.section))].filter(Boolean).sort();
    const getAllFunds = () => [...new Set(activeData.comparisons.map(r => r.fund_category))].filter(Boolean).sort();

    // --- Main render: flat table with header dropdowns ---

    const render = () => {
        const meta = activeData.metadata;
        const d1Key = getD1Key(), d2Key = getD2Key();
        const hd1Key = 'amount_' + meta.draft1.toLowerCase(); // always 'amount_hd1'
        const mode = document.getElementById('draft-filter')?.value || 'all';
        const q = (document.getElementById('draft-search')?.value || '').toLowerCase();

        let data = [...activeData.comparisons];

        // Checkbox filters (null = all selected)
        if (checkedSections) data = data.filter(r => checkedSections.has(r.section));
        if (checkedFunds) data = data.filter(r => checkedFunds.has(r.fund_category));

        // Search
        if (q) data = data.filter(r =>
            (r.program_name || '').toLowerCase().includes(q) ||
            (r.program_id || '').toLowerCase().includes(q) ||
            (r.department_name || '').toLowerCase().includes(q));

        // Change type filter
        if (mode === 'modified') data = data.filter(r => r.change_type === 'modified' && r.change !== 0);
        else if (mode === 'increases') data = data.filter(r => (r.change || 0) > 0);
        else if (mode === 'decreases') data = data.filter(r => (r.change || 0) < 0);
        else if (mode === 'added') data = data.filter(r => r.change_type === 'added');
        else if (mode === 'removed') data = data.filter(r => r.change_type === 'removed');

        // Sort
        const resolveSort = (r) => {
            if (sortCol === 'd1') return r[d1Key] || 0;
            if (sortCol === 'd2') return r[d2Key] || 0;
            if (sortCol === 'hd1') return r[hd1Key] || 0;
            if (sortCol === 'program_name') return (r.program_name || '').toLowerCase();
            return r[sortCol] ?? 0;
        };
        data.sort((a, b) => {
            if (frozenDeptOrder) {
                const ra = rankIn(frozenDeptOrder, a.department_code);
                const rb = rankIn(frozenDeptOrder, b.department_code);
                if (ra !== rb) return ra - rb;
            }
            if (frozenProgOrder && a.department_code === b.department_code) {
                const ord = frozenProgOrder.get(a.department_code);
                if (ord && ord.length) {
                    const ra = rankIn(ord, a.program_id);
                    const rb = rankIn(ord, b.program_id);
                    if (ra !== rb) return ra - rb;
                }
            }
            const va = resolveSort(a), vb = resolveSort(b);
            if (typeof va === 'string') return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
            return sortDir === 'asc' ? va - vb : vb - va;
        });

        // Summary line
        const totalDelta = data.reduce((s, r) => s + (r.change || 0), 0);
        const netCls2 = totalDelta > 0 ? 'positive' : totalDelta < 0 ? 'negative' : '';
        const filterVal = document.getElementById('draft-filter')?.value || 'all';
        const searchVal = document.getElementById('draft-search')?.value || '';
        const searchWasFocused = document.activeElement?.id === 'draft-search';
        const searchSelStart = document.getElementById('draft-search')?.selectionStart;
        const searchSelEnd = document.getElementById('draft-search')?.selectionEnd;
        document.getElementById('draft-summary').innerHTML =
            `<span class="stat-tag stat-tag-neutral items-filter-tag">
                <strong>${data.length}</strong> items ▾
                <select id="draft-filter" class="items-filter-select">
                    <option value="all"${filterVal==='all'?' selected':''}>All Changes</option>
                    <option value="modified"${filterVal==='modified'?' selected':''}>Modified Only</option>
                </select>
             </span>`
            + `<input type="text" id="draft-search" class="search-input search-inline" placeholder="Search..." value="${searchVal.replace(/"/g, '&quot;')}">
             <span class="compare-info-icon reading-guide-pill" id="reading-guide-box" tabindex="0">
                 <svg class="rg-info-svg" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.4"/><circle cx="8" cy="4.6" r="0.95" fill="currentColor"/><rect x="7.15" y="6.8" width="1.7" height="5.2" rx="0.6" fill="currentColor"/></svg> How to read this
                 <div class="reading-guide-panel">
                     <p class="reading-guide-summary">Not every change is a real cut or increase — some reflect <strong>funds being reshuffled between departments</strong>.</p>
                     <p>In the House draft (HD1), capital projects are sometimes listed under <strong>AGS</strong> (Accounting &amp; General Services) as a placeholder. Some programs, like Rental Housing, receive funding from multiple departments (e.g., <strong>HMS</strong> and <strong>BED</strong>).</p>
                     <div class="rg-chips">
                         <p class="rg-chips-title">Chips next to a program name</p>
                         <dl class="rg-chips-defs">
                             <dt><span class="pair-chip pair-chip-out" style="pointer-events:none;">→ AGS</span></dt>
                             <dd>funds moved <em>out</em> of this dept</dd>
                             <dt><span class="pair-chip pair-chip-in" style="pointer-events:none;">← BED</span></dt>
                             <dd>funds moved <em>into</em> this dept</dd>
                             <dt><span class="pair-chip pair-chip-neutral" style="pointer-events:none;">↔ EDN</span></dt>
                             <dd>program appears in both depts (no clear direction)</dd>
                             <dt><span class="data-note" style="pointer-events:none;">⚠</span></dt>
                             <dd>known data anomaly — hover for details</dd>
                             <dt><span class="fund-note" style="pointer-events:none;">ℹ bond-financed</span></dt>
                             <dd>capital projects in the Fund Detail section below</dd>
                         </dl>
                         <p class="rg-chips-help">Hover a chip to highlight paired rows; click to jump.</p>
                     </div>
                     <div class="rg-chips rg-funds">
                         <p class="rg-chips-title">Fund-chip colors — where the money comes from</p>
                         <dl class="rg-chips-defs rg-funds-defs">
                             <dt><span class="fund-chip" data-fund-cat="General Funds" style="pointer-events:none;">A</span></dt>
                             <dd><strong>State General</strong> — tax revenue, flexible spending</dd>
                             <dt><span class="fund-chip" data-fund-cat="Special Funds" style="pointer-events:none;">B T W</span></dt>
                             <dd><strong>State Dedicated</strong> — state-collected money set aside for a specific purpose</dd>
                             <dt><span class="fund-chip" data-fund-cat="Federal Funds" style="pointer-events:none;">N P</span></dt>
                             <dd><strong>Federal</strong> — money from the US government</dd>
                             <dt><span class="fund-chip" data-fund-cat="General Obligation Bond Fund" style="pointer-events:none;">C E</span></dt>
                             <dd><strong>Borrowed</strong> — state takes on bond debt</dd>
                             <dt><span class="fund-chip" data-fund-cat="Interdepartmental Transfers" style="pointer-events:none;">U S R X</span></dt>
                             <dd><strong>Transfers / Other</strong> — inter-agency, county, private, misc</dd>
                         </dl>
                     </div>
                 </div>
             </span>`;
        // Re-attach filter/search listeners after re-render
        document.getElementById('draft-filter')?.addEventListener('change', render);
        document.getElementById('draft-search')?.addEventListener('input', render);
        // Restore focus and cursor position if search was active before re-render
        if (searchWasFocused) {
            const newSearch = document.getElementById('draft-search');
            newSearch?.focus();
            newSearch?.setSelectionRange(searchSelStart, searchSelEnd);
        }

        // Build Section header checkbox dropdown
        const allSecs = getAllSections();
        const secChecks = allSecs.map(s => {
            const checked = !checkedSections || checkedSections.has(s) ? ' checked' : '';
            return `<label><input type="checkbox" value="${s}"${checked}> ${s}</label>`;
        }).join('');
        const secLabel = !checkedSections ? 'Section ▾' : `Section (${checkedSections.size}/${allSecs.length}) ▾`;

        // Build Fund header checkbox dropdown
        const allFds = getAllFunds();
        const fundChecks = allFds.map(f => {
            const checked = !checkedFunds || checkedFunds.has(f) ? ' checked' : '';
            return `<label><input type="checkbox" value="${f}"${checked}> ${f}</label>`;
        }).join('');
        const fundLabel = !checkedFunds ? 'Fund ▾' : `Fund (${checkedFunds.size}/${allFds.length}) ▾`;

        const sortArrow = (col) => {
            if (sortCol === col) {
                return `<span class="sort-ind">${sortDir === 'asc' ? '▲' : '▼'}</span>`;
            }
            // Faint hint that appears on header hover
            return `<span class="sort-hint">▲</span>`;
        };

        // Group by department
        const deptMap = new Map();
        for (const r of data) {
            const key = r.department_code || 'OTHER';
            if (!deptMap.has(key)) deptMap.set(key, { code: key, name: r.department_name || key, rows: [] });
            deptMap.get(key).rows.push(r);
        }
        // Pre-compute dept aggregates, then sort by active sortCol/sortDir
        const depts = [...deptMap.values()].map(d => {
            d.d1 = d.rows.reduce((s, r) => s + (r[d1Key] || 0), 0);
            d.d2 = d.rows.reduce((s, r) => s + (r[d2Key] || 0), 0);
            d.hd1 = d.rows.reduce((s, r) => s + (r[hd1Key] || 0), 0);
            d.delta = d.d2 - d.d1;
            return d;
        }).sort((a, b) => {
            if (frozenDeptOrder) {
                const ra = rankIn(frozenDeptOrder, a.code);
                const rb = rankIn(frozenDeptOrder, b.code);
                if (ra !== rb) return ra - rb;
            }
            let va, vb;
            if (sortCol === 'program_name') { va = a.code.toLowerCase(); vb = b.code.toLowerCase(); }
            else if (sortCol === 'd1') { va = a.d1; vb = b.d1; }
            else if (sortCol === 'd2') { va = a.d2; vb = b.d2; }
            else { va = a.delta; vb = b.delta; } // change, pct_change, default
            if (typeof va === 'string') return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
            return sortDir === 'asc' ? va - vb : vb - va;
        });

        // Build cross-reference map: program_id → Map<deptCode, {d1, d2, delta}>
        // Uses the active d1Key/d2Key so reallocation detection works correctly
        // in any comparison mode (Gov→SD1, HD1→SD1, etc.). The baseline lookup
        // keys on {dept+program+fund+section}, so per-dept baseline values
        // differ — a placeholder row with no governor entry gets $0, while the
        // originating dept keeps the full Gov amount. That's exactly what's
        // needed to detect a legislative split like PSD900 (all in PSD under
        // Gov, split into AGS placeholder + PSD under HD1/SD1).
        const splitPrograms = new Map();
        for (const r of activeData.comparisons) {
            const pid = r.program_id;
            const dept = r.department_code;
            if (!pid || !dept) continue;
            if (!splitPrograms.has(pid)) splitPrograms.set(pid, new Map());
            const deptMap = splitPrograms.get(pid);
            if (!deptMap.has(dept)) deptMap.set(dept, { d1: 0, d2: 0 });
            const entry = deptMap.get(dept);
            entry.d1 += r[d1Key] || 0;
            entry.d2 += r[d2Key] || 0;
        }
        // Only keep programs that appear in 2+ departments; compute delta
        for (const [pid, deptMap] of splitPrograms) {
            if (deptMap.size < 2) { splitPrograms.delete(pid); continue; }
            for (const vals of deptMap.values()) vals.delta = vals.d2 - vals.d1;
        }

        // Auto-expand departments when searching
        const autoExpand = q.length > 0;

        // Active fiscal year for inline toggle
        const activeYear = (activeData === draftComparisonData) ? 26 : 27;

        // --- Data-quality annotations ---
        // Known bill-drafting anomalies surfaced as inline ⚠ tooltips.
        const DATA_NOTES = {
            // UOH100 FY27 HD1: Part II explicitly zeroes Revenue Bond (E) capital
            // via a continuation override not present in Section 14, which still
            // records $28.5M. Both parsers are correct; the bill disagrees with
            // itself. Part II is the authoritative appropriation.
            'UOH100': {
                fy27: 'HD1 Part II sets Revenue Bond capital (fund E) to $0 via an explicit zero override. Section 14 project detail still records $28.5M — an apparent bill-drafting omission. HD1 E figures above follow Part II.'
            },
            // SUB501: "Subsidies" is a cross-departmental accounting roll-up in
            // Part II. Capital projects funded through SUB are physically listed
            // under the originating departments in Section 14, so SUB501 will
            // appear short relative to Part II in any project-level comparison.
            'SUB501': {
                any: 'Subsidies (SUB501) is a cross-departmental accounting code. Capital project detail is listed under the originating departments in Section 14, not under SUB — so project-level totals will appear lower than the Part II appropriation.'
            },
        };

        /**
         * Returns an HTML badge string for known data-quality notes on a program,
         * or '' if none apply.
         */
        const buildDataNote = (programId, fy) => {
            const entry = DATA_NOTES[programId];
            if (!entry) return '';
            const msg = entry[`fy${fy}`] || entry.any || '';
            if (!msg) return '';
            const escaped = msg.replace(/"/g, '&quot;');
            return ` <span class="data-note" title="${escaped}" aria-label="Data note: ${escaped}">⚠</span>`;
        };

        // Aggregate records by program_id within each department
        const aggregatePrograms = (rows) => {
            const pMap = new Map();
            for (const r of rows) {
                const pid = r.program_id || '';
                if (!pMap.has(pid)) {
                    pMap.set(pid, {
                        program_id: pid, program_name: r.program_name || '',
                        department_code: r.department_code, department_name: r.department_name,
                        d1: 0, d2: 0, hd1: 0, funds: new Set(), sections: new Set(),
                        hasAdded: false, hasRemoved: false, rawRows: [],
                        // Worksheet reasons (from extract_worksheet_reasons.py) live on
                        // every raw row of a program; copy onto the aggregated view so
                        // changeReasonTooltipAttrs(p) can read them at render time.
                        reason_sd_change: r.reason_sd_change || '',
                        reason_hd_change: r.reason_hd_change || '',
                    });
                }
                const p = pMap.get(pid);
                p.d1 += r[d1Key] || 0;
                p.d2 += r[d2Key] || 0;
                p.hd1 += r[hd1Key] || 0;
                if (r.fund_category) p.funds.add(r.fund_category);
                if (r.section) p.sections.add(r.section);
                if (r.change_type === 'added') p.hasAdded = true;
                if (r.change_type === 'removed') p.hasRemoved = true;
                p.rawRows.push(r);
            }
            // For split programs (appear in multiple departments), augment this dept's
            // aggregation with records from other departments — but only for sections
            // that the current dept already has. This ensures the section/fund sub-rows
            // (and the program-level total) reflect the FULL program allocation, not just
            // the slice booked to this dept in the current draft.
            // Example: HMS220 Capital Improvement under HMS was $0 HD1 because the $68M
            // was booked under BED in HD1 and only transferred to HMS in SD1. With this
            // augmentation, HMS/HMS220 Capital now correctly shows $68M HD1.
            for (const p of pMap.values()) {
                if (!splitPrograms.has(p.program_id)) continue;
                // Save pre-augmentation (dept-scoped) totals so we can later compute
                // each program's individual contribution to the dept-vs-program mismatch.
                p.d1DeptScope = p.d1;
                p.d2DeptScope = p.d2;
                const mySections = new Set(p.rawRows.map(r => r.section));
                p.crossDeptAugmented = new Set(); // other depts pulled in
                for (const r of activeData.comparisons) {
                    if (r.program_id !== p.program_id) continue;
                    if (r.department_code === p.department_code) continue;
                    if (!mySections.has(r.section)) continue;
                    p.d1  += r[d1Key]  || 0;
                    p.d2  += r[d2Key]  || 0;
                    p.hd1 += r[hd1Key] || 0;
                    if (r.fund_category) p.funds.add(r.fund_category);
                    p.rawRows.push(r);
                    p.crossDeptAugmented.add(r.department_code);
                }
            }
            return [...pMap.values()].map(p => {
                p.change = p.d2 - p.d1;
                p.pct_change = p.d1 !== 0 ? ((p.d2 - p.d1) / Math.abs(p.d1)) * 100 : (p.d2 !== 0 ? 100 : 0);
                p.change_type = p.hasAdded && p.d1 === 0 ? 'added' : p.hasRemoved && p.d2 === 0 ? 'removed' : 'modified';
                p.isMixed = p.sections.size > 1;
                p.section = p.isMixed ? 'Mixed' : [...p.sections][0] || '';
                p.fundLabel = p.funds.size === 1 ? [...p.funds][0] : `${p.funds.size} funds`;
                p.fundShort = p.funds.size === 1 ? shortFund([...p.funds][0]) : `${p.funds.size} funds`;
                p.fundTitle = p.funds.size > 1 ? [...p.funds].join(' · ') : '';
                return p;
            });
        };

        let bodyHtml = '';
        for (const dept of depts) {
            bodyHtml += `<tbody class="dept-block" data-dept-block="${dept.code}">`;
            const deptD1 = dept.d1;
            const deptD2 = dept.d2;
            const deptDelta = dept.delta;
            const deptCls = deptDelta > 0 ? 'positive' : deptDelta < 0 ? 'negative' : '';
            const isOpen = autoExpand || expandedDepts.has(dept.code);
            const arrow = isOpen ? '▼' : '▶';

            const programs = aggregatePrograms(dept.rows);

            // Dept-level pairing is now communicated via paired ↔ DEPT chips on
            // individual program rows, so no dept-level transfer badge is needed.
            bodyHtml += `<tr class="dept-group-row${isOpen ? ' open' : ''}" data-dept="${dept.code}">
                <td><span class="dept-arrow">${arrow}</span> <span class="dept-chip">${highlight(dept.code, q)}</span> ${highlight(dept.name, q)} <span class="dept-count">(${programs.length} programs)</span></td>
                <td></td><td></td>
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(deptD1)}</span></td>
                ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(dept.hd1)}</span></td>` : ''}
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(deptD2)}</span></td>
                <td class="amount-cell ${deptCls}"><span class="figure-chip">${fmtHtml(deptDelta)}</span></td>
            </tr>`;

            for (const p of programs) {
                const cls = p.change > 0 ? 'positive' : p.change < 0 ? 'negative' : '';
                const typeBadge = p.change_type === 'added' ? '<span class="badge badge-add">new</span>'
                    : p.change_type === 'removed' ? '<span class="badge badge-remove">removed</span>' : '';
                const progKey = `${dept.code}:${p.program_id}`;
                const progOpen = autoExpand || expandedPrograms.has(progKey);

                // Paired-dept chips: a unified signal that replaces the older
                // "also in EDN" cross-ref note, the "→ Moved to AGS" transfer
                // badge, and the "↔ routed through this dept" dept-level note.
                // Renders one compact chip per sibling dept where the same
                // program_id also appears. Hovering a chip (or the row itself)
                // highlights the paired row(s) across the table. Clicking
                // scrolls to the sibling dept.
                const splitDeptMap = splitPrograms.get(p.program_id);
                let pairChips = '';
                if (splitDeptMap) {
                    const otherDepts = [...splitDeptMap.keys()].filter(d => d !== dept.code);
                    if (otherDepts.length > 0) {
                        const thisDelta = splitDeptMap.get(dept.code)?.delta || 0;
                        const fmtShort = (v) => {
                            const sign = v < 0 ? '−' : v > 0 ? '+' : '';
                            const abs = Math.abs(v);
                            if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(1)}B`;
                            if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`;
                            if (abs >= 1e3) return `${sign}$${Math.round(abs / 1e3)}K`;
                            return `${sign}$${abs}`;
                        };
                        pairChips = ' ' + otherDepts.map(d => {
                            const od = splitDeptMap.get(d)?.delta || 0;
                            // Direction: this dept LOST while other GAINED → outgoing (→)
                            //            this dept GAINED while other LOST → incoming (←)
                            //            both same sign or near-zero → neutral (↔)
                            let arrow, cls;
                            const SIG = 100000; // $100K significance threshold per side
                            if (Math.abs(thisDelta) > SIG && Math.abs(od) > SIG && ((thisDelta < 0) !== (od < 0))) {
                                arrow = thisDelta < 0 ? '→' : '←';
                                cls = thisDelta < 0 ? 'pair-chip-out' : 'pair-chip-in';
                            } else {
                                arrow = '↔';
                                cls = 'pair-chip-neutral';
                            }
                            const tip = `This program also appears under ${d}. ${d}'s change on this program: ${fmtShort(od)}. Hover to highlight the paired row; click to jump there.`;
                            const tipEsc = tip.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
                            return `<a class="pair-chip ${cls}" href="javascript:void(0)" data-scroll-dept="${d}" data-pair-key="${p.program_id}" title="${tipEsc}">${arrow}&nbsp;${d}</a>`;
                        }).join('');
                    }
                }
                const pairKeyAttr = splitDeptMap ? ` data-pair-key="${p.program_id}"` : '';
                const dataNoteHtml = buildDataNote(p.program_id, activeYear);

                if (p.isMixed) {
                    const progArrow = progOpen ? '▼' : '▶';
                    bodyHtml += `<tr class="dept-detail-row prog-group-row${isOpen ? '' : ' hidden'}" data-dept="${dept.code}" data-prog="${progKey}"${pairKeyAttr}>
                        <td class="detail-indent"><span class="dept-arrow">${progArrow}</span> <strong${purposeTooltipAttrs(p.program_id)}>${highlight(p.program_id, q)}</strong> ${highlight(p.program_name, q)}${sparklineSvg([p.d1, p.hd1, p.d2])}${pairChips}${dataNoteHtml}</td>
                        <td><span class="section-chip">Mixed</span></td>
                        <td>${p.fundShort ? `<span class="fund-chip${p.fundTitle ? ' fund-chip-multi' : ''}"${p.fundTitle ? ` data-funds="${p.fundTitle}"` : ''}${p.funds.size === 1 ? ` data-fund-cat="${[...p.funds][0]}"` : ''}>${p.fundShort}</span>` : ''}</td>
                        <td class="amount-cell"><span class="figure-chip">${fmtHtml(p.d1)}</span></td>
                        ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(p.hd1)}</span></td>` : ''}
                        <td class="amount-cell"><span class="figure-chip">${fmtHtml(p.d2)}</span></td>
                        <td${changeReasonCellAttrs(p, `amount-cell ${cls}`)}><span class="figure-chip">${fmtHtml(p.change)}</span>${divergenceChipHtml(p)}</td>
                    </tr>`;
                    for (const sec of [...p.sections].sort()) {
                        const secRows = p.rawRows.filter(r => r.section === sec);
                        const secD1 = secRows.reduce((s, r) => s + (r[d1Key] || 0), 0);
                        const secD2 = secRows.reduce((s, r) => s + (r[d2Key] || 0), 0);
                        const secHD1 = secRows.reduce((s, r) => s + (r[hd1Key] || 0), 0);
                        const secDelta = secD2 - secD1;
                        const secCls = secDelta > 0 ? 'positive' : secDelta < 0 ? 'negative' : '';
                        const secPct = secD1 !== 0 ? ((secD2 - secD1) / Math.abs(secD1)) * 100 : (secD2 !== 0 ? 100 : 0);
                        const secFunds = new Set(secRows.map(r => r.fund_category).filter(Boolean));
                        const secFundLabel = secFunds.size === 1 ? shortFund([...secFunds][0]) : (secFunds.size > 1 ? `${secFunds.size} funds` : '');
                        const secFundTitle = secFunds.size > 1 ? [...secFunds].join(' · ') : '';
                        const secHasProjects = sec === 'Capital Improvement'
                            && activeProjects?.projects_by_program?.[p.program_id]?.length > 0;
                        const secChipHtml = secHasProjects
                            ? `<a class="section-chip section-chip-link" href="javascript:void(0)" data-scroll-projects="${dept.code}">${sec} →</a>`
                            : `<span class="section-chip">${sec}</span>`;
                        const isSecFundGroup = secFunds.size > 1;
                        const secFundKey = `${dept.code}:${p.program_id}:${sec}`;
                        const secFundOpen = expandedFunds.has(secFundKey);
                        const secFundArrow = secFundOpen ? '▼' : '▶';
                        bodyHtml += `<tr class="prog-section-row${isSecFundGroup ? ' prog-fund-group' : ''}${isOpen && progOpen ? '' : ' hidden'}" data-dept="${dept.code}" data-prog="${progKey}"${isSecFundGroup ? ` data-fund-key="${secFundKey}"` : ''}>
                            <td class="section-indent">${isSecFundGroup ? `<span class="dept-arrow">${secFundArrow}</span> ` : ''}${secChipHtml}</td>
                            <td></td>
                            <td>${secFundLabel ? `<span class="fund-chip${secFundTitle ? ' fund-chip-multi' : ''}"${secFundTitle ? ` data-funds="${secFundTitle}"` : ''}>${secFundLabel}</span>` : ''}</td>
                            <td class="amount-cell"><span class="figure-chip">${fmtHtml(secD1)}</span></td>
                            ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(secHD1)}</span></td>` : ''}
                            <td class="amount-cell"><span class="figure-chip">${fmtHtml(secD2)}</span></td>
                            <td class="amount-cell ${secCls}"><span class="figure-chip">${fmtHtml(secDelta)}</span></td>
                        </tr>`;
                        if (isSecFundGroup) {
                            const byFund = new Map();
                            for (const r of secRows) {
                                const fc = r.fund_category || '(unknown)';
                                if (!byFund.has(fc)) byFund.set(fc, { d1: 0, d2: 0, hd1: 0 });
                                const f = byFund.get(fc);
                                f.d1  += r[d1Key]  || 0;
                                f.d2  += r[d2Key]  || 0;
                                f.hd1 += r[hd1Key] || 0;
                            }
                            for (const [fc, f] of byFund) {
                                const fDelta = f.d2 - f.d1;
                                const fCls = fDelta > 0 ? 'positive' : fDelta < 0 ? 'negative' : '';
                                const fPct = f.d1 !== 0 ? ((f.d2 - f.d1) / Math.abs(f.d1)) * 100 : (f.d2 !== 0 ? 100 : 0);
                                bodyHtml += `<tr class="prog-fund-row${isOpen && progOpen && secFundOpen ? '' : ' hidden'}" data-dept="${dept.code}" data-prog="${progKey}" data-fund-key="${secFundKey}">
                                    <td class="fund-indent fund-indent-deep"><span class="fund-chip" data-fund-cat="${fc}">${shortFund(fc)}</span> <span class="fund-name-full">${fc}</span></td>
                                    <td></td><td></td>
                                    <td class="amount-cell"><span class="figure-chip">${fmtHtml(f.d1)}</span></td>
                                    ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(f.hd1)}</span></td>` : ''}
                                    <td class="amount-cell"><span class="figure-chip">${fmtHtml(f.d2)}</span></td>
                                    <td class="amount-cell ${fCls}"><span class="figure-chip">${fmtHtml(fDelta)}</span></td>
                                </tr>`;
                            }
                        }
                    }
                } else if (p.funds.size > 1) {
                    // Non-mixed multi-fund: render as expandable fund-group with fund sub-rows nested inside
                    const progHasProjects = p.section === 'Capital Improvement'
                        && activeProjects?.projects_by_program?.[p.program_id]?.length > 0;
                    const progChipHtml = progHasProjects
                        ? `<a class="section-chip section-chip-link" href="javascript:void(0)" data-scroll-projects="${dept.code}">${p.section} →</a>`
                        : `<span class="section-chip">${p.section}</span>`;
                    const fundKey = `${dept.code}:${p.program_id}:${p.section}`;
                    const fundOpen = expandedFunds.has(fundKey);
                    const fundArrow = fundOpen ? '▼' : '▶';
                    bodyHtml += `<tr class="dept-detail-row prog-fund-group${isOpen ? '' : ' hidden'}" data-dept="${dept.code}" data-fund-key="${fundKey}"${pairKeyAttr}>
                        <td class="detail-indent"><span class="dept-arrow">${fundArrow}</span> <strong${purposeTooltipAttrs(p.program_id)}>${highlight(p.program_id, q)}</strong> ${highlight(p.program_name, q)}${sparklineSvg([p.d1, p.hd1, p.d2])}${pairChips}${dataNoteHtml}</td>
                        <td>${progChipHtml}</td>
                        <td><span class="fund-chip fund-chip-multi" data-funds="${p.fundTitle}">${p.fundShort}</span></td>
                        <td class="amount-cell"><span class="figure-chip">${fmtHtml(p.d1)}</span></td>
                        ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(p.hd1)}</span></td>` : ''}
                        <td class="amount-cell"><span class="figure-chip">${fmtHtml(p.d2)}</span></td>
                        <td${changeReasonCellAttrs(p, `amount-cell ${cls}`)}><span class="figure-chip">${fmtHtml(p.change)}</span>${divergenceChipHtml(p)}</td>
                    </tr>`;
                    const byFund = new Map();
                    for (const r of p.rawRows) {
                        const fc = r.fund_category || '(unknown)';
                        if (!byFund.has(fc)) byFund.set(fc, { d1: 0, d2: 0, hd1: 0 });
                        const f = byFund.get(fc);
                        f.d1  += r[d1Key]  || 0;
                        f.d2  += r[d2Key]  || 0;
                        f.hd1 += r[hd1Key] || 0;
                    }
                    for (const [fc, f] of byFund) {
                        const fDelta = f.d2 - f.d1;
                        const fCls = fDelta > 0 ? 'positive' : fDelta < 0 ? 'negative' : '';
                        const fPct = f.d1 !== 0 ? ((f.d2 - f.d1) / Math.abs(f.d1)) * 100 : (f.d2 !== 0 ? 100 : 0);
                        bodyHtml += `<tr class="prog-fund-row${isOpen && fundOpen ? '' : ' hidden'}" data-dept="${dept.code}" data-fund-key="${fundKey}">
                            <td class="fund-indent"><span class="fund-chip" data-fund-cat="${fc}">${shortFund(fc)}</span> <span class="fund-name-full">${fc}</span></td>
                            <td></td><td></td>
                            <td class="amount-cell"><span class="figure-chip">${fmtHtml(f.d1)}</span></td>
                            ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(f.hd1)}</span></td>` : ''}
                            <td class="amount-cell"><span class="figure-chip">${fmtHtml(f.d2)}</span></td>
                            <td class="amount-cell ${fCls}"><span class="figure-chip">${fmtHtml(fDelta)}</span></td>
                        </tr>`;
                    }
                } else {
                    // Single-fund: plain leaf row
                    const progHasProjects = p.section === 'Capital Improvement'
                        && activeProjects?.projects_by_program?.[p.program_id]?.length > 0;
                    const progChipHtml = progHasProjects
                        ? `<a class="section-chip section-chip-link" href="javascript:void(0)" data-scroll-projects="${dept.code}">${p.section} →</a>`
                        : `<span class="section-chip">${p.section}</span>`;
                    bodyHtml += `<tr class="dept-detail-row${isOpen ? '' : ' hidden'}" data-dept="${dept.code}"${pairKeyAttr}>
                        <td class="detail-indent"><strong${purposeTooltipAttrs(p.program_id)}>${highlight(p.program_id, q)}</strong> ${highlight(p.program_name, q)}${sparklineSvg([p.d1, p.hd1, p.d2])}${pairChips}${dataNoteHtml}</td>
                        <td>${progChipHtml}</td>
                        <td>${p.fundShort ? `<span class="fund-chip${p.fundTitle ? ' fund-chip-multi' : ''}"${p.fundTitle ? ` data-funds="${p.fundTitle}"` : ''}${p.funds.size === 1 ? ` data-fund-cat="${[...p.funds][0]}"` : ''}>${p.fundShort}</span>` : ''}</td>
                        <td class="amount-cell"><span class="figure-chip">${fmtHtml(p.d1)}</span></td>
                        ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(p.hd1)}</span></td>` : ''}
                        <td class="amount-cell"><span class="figure-chip">${fmtHtml(p.d2)}</span></td>
                        <td${changeReasonCellAttrs(p, `amount-cell ${cls}`)}><span class="figure-chip">${fmtHtml(p.change)}</span>${divergenceChipHtml(p)}</td>
                    </tr>`;
                }
            }
            bodyHtml += `</tbody>`;
        }

        // Grand totals row for main table
        {
            const gD1 = depts.reduce((s, d) => s + d.d1, 0);
            const gD2 = depts.reduce((s, d) => s + d.d2, 0);
            const gHD1 = depts.reduce((s, d) => s + d.hd1, 0);
            const gDelta = gD2 - gD1;
            const gCls = gDelta > 0 ? 'positive' : gDelta < 0 ? 'negative' : '';
            const gArrow = gDelta > 0 ? '▲' : gDelta < 0 ? '▼' : '';
            const gPct = gD1 !== 0 ? ((gDelta / Math.abs(gD1)) * 100) : (gDelta !== 0 ? 100 : 0);
            const gPctStr = fmtPct(gPct).replace(/^\+/, '');
            bodyHtml += `<tbody class="totals-block"><tr class="totals-row">
                <td>Total <span class="totals-meta">${depts.length} depts</span></td>
                <td></td><td></td>
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(gD1)}</span></td>
                ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(gHD1)}</span></td>` : ''}
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(gD2)}</span></td>
                <td class="amount-cell change-cell ${gCls}">
                    <span class="change-main">${gArrow ? `<span class="change-arrow">${gArrow}</span>` : ''}<span class="figure-chip">${fmtHtml(gDelta)}</span></span>
                    ${gArrow ? `<span class="change-pct">${gPctStr}</span>` : ''}
                </td>
            </tr></tbody>`;
        }

        // Fund detail table — grouped by fund type
        const fundTypeMap = new Map();
        for (const r of data) {
            const ft = r.fund_type || '?';
            if (!fundTypeMap.has(ft)) fundTypeMap.set(ft, { type: ft, category: r.fund_category || ft, rows: [] });
            fundTypeMap.get(ft).rows.push(r);
        }
        const fundGroups = [...fundTypeMap.values()].sort((a, b) => {
            if (frozenFundOrder) {
                const ra = rankIn(frozenFundOrder, a.type);
                const rb = rankIn(frozenFundOrder, b.type);
                if (ra !== rb) return ra - rb;
            }
            const aTotal = a.rows.reduce((s, r) => s + Math.abs(r.change || 0), 0);
            const bTotal = b.rows.reduce((s, r) => s + Math.abs(r.change || 0), 0);
            return bTotal - aTotal;
        });

        const autoExpandFunds = q.length > 0;
        let fundHtml = '';
        for (const fg of fundGroups) {
            fundHtml += `<tbody class="fund-block" data-fund-block="${fg.type}">`;
            const fgD1 = fg.rows.reduce((s, r) => s + (r[d1Key] || 0), 0);
            const fgD2 = fg.rows.reduce((s, r) => s + (r[d2Key] || 0), 0);
            const fgHD1 = fg.rows.reduce((s, r) => s + (r[hd1Key] || 0), 0);
            const fgDelta = fgD2 - fgD1;
            const fgCls = fgDelta > 0 ? 'positive' : fgDelta < 0 ? 'negative' : '';
            const isOpen = autoExpandFunds || expandedFundTypes.has(fg.type);
            const arrow = isOpen ? '▼' : '▶';

            const fundNote = fg.type === 'C'
                ? ` <span class="fund-note" title="General obligation bonds are loans the state repays over time. Changes here reflect shifts in which capital projects get bond financing — not cuts to the underlying programs.">ℹ bond-financed capital projects</span>`
                : '';
            const fgArrowSign = fgDelta > 0 ? '▲' : fgDelta < 0 ? '▼' : '';
            const fgDynPct = fgD1 !== 0 ? ((fgDelta / Math.abs(fgD1)) * 100) : (fgDelta !== 0 ? 100 : 0);
            const fgPctStr = fmtPct(fgDynPct).replace(/^\+/, '');
            // Build stacked bar: each program's share of this fund's d2 total
            const fgStackSegs = fg.rows.map(r => ({
                label: `${r.program_id || ''} ${r.program_name || ''}`.trim(),
                value: Math.abs(r[d2Key] || 0),
            }));
            const fgStackBar = stackedBarSvg(fgStackSegs, fgD2);
            fundHtml += `<tr class="fund-group-row${isOpen ? ' open' : ''}" data-fund-type="${fg.type}">
                <td><span class="dept-arrow">${arrow}</span> <span class="fund-chip" data-fund-cat="${fg.category}">${fg.type}</span> ${fg.category}${fundNote} <span class="dept-count">(${fg.rows.length})</span>${fgStackBar ? ` ${fgStackBar}` : ''}</td>
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(fgD1)}</span></td>
                ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(fgHD1)}</span></td>` : ''}
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(fgD2)}</span></td>
                <td class="amount-cell change-cell ${fgCls}">
                    <span class="change-main">${fgArrowSign ? `<span class="change-arrow">${fgArrowSign}</span>` : ''}<span class="figure-chip">${fmtHtml(fgDelta)}</span></span>
                    ${fgArrowSign ? `<span class="change-pct">${fgPctStr}</span>` : ''}
                </td>
            </tr>`;

            for (const r of fg.rows) {
                const delta = r[d2Key] - r[d1Key];
                const cls = delta > 0 ? 'positive' : delta < 0 ? 'negative' : '';
                const dynPct = r[d1Key] !== 0 ? ((delta / Math.abs(r[d1Key])) * 100) : (delta !== 0 ? 100 : 0);
                const arrow = delta > 0 ? '▲' : delta < 0 ? '▼' : '';
                const pctStr = fmtPct(dynPct).replace(/^\+/, '');
                fundHtml += `<tr class="fund-detail-row${isOpen ? '' : ' hidden'}" data-fund-type="${fg.type}">
                    <td class="detail-indent"><strong${purposeTooltipAttrs(r.program_id)}>${highlight(r.program_id || '', q)}</strong> ${highlight(r.program_name || '', q)}</td>
                    <td class="amount-cell"><span class="figure-chip">${fmtHtml(r[d1Key])}</span></td>
                    ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(r[hd1Key] || 0)}</span></td>` : ''}
                    <td class="amount-cell"><span class="figure-chip">${fmtHtml(r[d2Key])}</span></td>
                    <td${changeReasonCellAttrs(delta !== 0 ? r : null, `amount-cell change-cell ${cls}`)}>
                        <span class="change-main">${arrow ? `<span class="change-arrow">${arrow}</span>` : ''}<span class="figure-chip">${fmtHtml(delta)}</span></span>
                        ${arrow ? `<span class="change-pct">${pctStr}</span>` : ''}
                        ${divergenceChipHtml(r)}
                    </td>
                </tr>`;
            }
            fundHtml += `</tbody>`;
        }

        // Grand totals row for fund detail table
        {
            const fgD1 = data.reduce((s, r) => s + (r[d1Key] || 0), 0);
            const fgD2 = data.reduce((s, r) => s + (r[d2Key] || 0), 0);
            const fgHD1 = data.reduce((s, r) => s + (r[hd1Key] || 0), 0);
            const fgDelta = fgD2 - fgD1;
            const fgCls = fgDelta > 0 ? 'positive' : fgDelta < 0 ? 'negative' : '';
            const fgArrow = fgDelta > 0 ? '▲' : fgDelta < 0 ? '▼' : '';
            const fgPct = fgD1 !== 0 ? ((fgDelta / Math.abs(fgD1)) * 100) : (fgDelta !== 0 ? 100 : 0);
            const fgPctStr = fmtPct(fgPct).replace(/^\+/, '');
            fundHtml += `<tbody class="totals-block"><tr class="totals-row">
                <td>Total <span class="totals-meta">${fundGroups.length} fund types</span></td>
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(fgD1)}</span></td>
                ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(fgHD1)}</span></td>` : ''}
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(fgD2)}</span></td>
                <td class="amount-cell change-cell ${fgCls}">
                    <span class="change-main">${fgArrow ? `<span class="change-arrow">${fgArrow}</span>` : ''}<span class="figure-chip">${fmtHtml(fgDelta)}</span></span>
                    ${fgArrow ? `<span class="change-pct">${fgPctStr}</span>` : ''}
                </td>
            </tr></tbody>`;
        }

        document.getElementById('draft-results').innerHTML = `
            <table class="data-table" id="draft-table">
                <thead><tr>
                    <th class="sortable th-program-col" data-sort="program_name"><div class="th-program-inner"><span class="th-program-label">Program${sortArrow('program_name')}</span>${(draftComparisonData && draftComparisonDataFY27) ? `<span class="fy-inline-toggle" id="fy-inline-toggle"><button class="fy-inline-btn${activeYear === 26 ? ' active' : ''}" data-fy-inline="26">2026</button><button class="fy-inline-btn${activeYear === 27 ? ' active' : ''}" data-fy-inline="27">2027</button></span>` : ''}</div></th>
                    <th class="th-dropdown" id="th-section"><span class="th-dropdown-btn">${secLabel}</span>
                        <div class="th-dropdown-menu">${secChecks}</div></th>
                    <th class="th-dropdown" id="th-fund"><span class="th-dropdown-btn">${fundLabel}</span>
                        <div class="th-dropdown-menu">${fundChecks}</div></th>
                    <th class="sortable amount-cell" data-sort="d1">${getD1Label()}${sortArrow('d1')}</th>
                    ${showHD1Col() ? `<th class="sortable amount-cell" data-sort="hd1">HD1${sortArrow('hd1')}</th>` : ''}
                    <th class="sortable amount-cell" data-sort="d2">${getD2Label()}${sortArrow('d2')}</th>
                    <th class="sortable amount-cell" data-sort="change">${getChangeLabel(sortArrow('change'))}</th>
                </tr></thead>
                ${bodyHtml}
            </table>
            <div class="table-export-row"><button class="action-link export-btn" id="export-drafts">⬇ Export CSV</button></div>`;

        document.getElementById('fund-detail-section').innerHTML = `
            <h3 class="fund-detail-heading"><span class="has-tooltip" data-tooltip="Chip color = where the money comes from:&#10;&#10;● State General — A (general fund tax revenue)&#10;● State Dedicated — B, T, W (state funds set aside for a purpose)&#10;● Federal — N, P (US government money)&#10;● Borrowed — C, E (state takes on bond debt)&#10;● Transfers / Other — U, S, R, X&#10;&#10;Letter codes:&#10;A — General funds for everyday state spending&#10;B — Special funds set aside for specific purposes&#10;C — General obligation bond funds for public projects&#10;E — Revenue bond funds repaid from project earnings&#10;N/P — Federal aid from the U.S. government&#10;S — County funds from county governments&#10;T — Trust funds held for specific long-term purposes&#10;U — Interdepartmental transfers between state agencies&#10;W — Revolving funds replenished by program revenue&#10;R — Private contributions and grants&#10;X — Miscellaneous other funds">Fund Detail</span></h3>
            <table class="data-table" id="fund-detail-table">
                <thead><tr>
                    <th>Fund / Program</th>
                    <th class="amount-cell">${getD1Label()}</th>
                    ${showHD1Col() ? '<th class="amount-cell">HD1</th>' : ''}
                    <th class="amount-cell">${getD2Label()}</th>
                    <th class="amount-cell">${getChangeLabel()}</th>
                </tr></thead>
                ${fundHtml}
            </table>
            <div class="table-export-row"><button class="action-link export-btn" id="export-fund-detail">⬇ Export CSV</button></div>`;

        // Re-attach header dropdown events after render
        attachHeaderDropdowns();

        window._lastDraftResults = data;
        window._lastDraftMeta = meta;

        renderProjects();
    };

    // --- Render Section 14 capital projects section ---

    // Normalize a project name for cross-source matching:
    // Normalise project names for Gov PDF ↔ HD1/SD1 matching.
    // Handles: "LUMP SUM" prefix, leading numeric codes ("009 ", "- "),
    // trailing island/statewide suffixes (", OAHU" etc.), "&" → "AND",
    // ", AND" → " AND", and common abbreviations used in the Gov PDF.
    const normProjectName = (s) => {
        const ABBR = {
            // Common
            PLNS:'PLANS', DSGN:'DESIGN', CONSTR:'CONSTRUCTION', EQUIP:'EQUIPMENT',
            INFSN:'INFUSION', RNTL:'RENTAL', HSING:'HOUSING', HSNG:'HOUSING',
            RVLVING:'REVOLVING', RVLVNG:'REVOLVING', FND:'FUND',
            RENVTNS:'RENOVATIONS', UPGRDS:'UPGRADES',
            DEPT:'DEPARTMENT', DVLPMNT:'DEVELOPMENT', PRDVLPMNT:'PREDEVELOPMENT',
            // Added for better gov-PDF matching
            LND:'LAND', ACQSTN:'ACQUISITION', DIV:'DIVISION',
            CNSERVTN:'CONSERVATION', CNTR:'CENTER', CORR:'CORRECTIONAL',
            RENOV:'RENOVATION', RENOVN:'RENOVATION', UPGR:'UPGRADES',
            IMPS:'IMPROVEMENTS', IMPRVMNT:'IMPROVEMENT', INCL:'INCLUDING',
            MED:'MEDICAL', HLTH:'HEALTH', FAC:'FACILITY', FACS:'FACILITIES',
            BLDG:'BUILDING', BLDGS:'BUILDINGS',
        };
        const ABBR_KEYS = Object.keys(ABBR).join('|');
        const LOC = /,\s*(OAHU|HAWAII|MAUI|KAUAI|MOLOKAI|LANAI|STATEWIDE|ALL ISLANDS)\s*$/i;
        let n = (s || '')
            .replace(/^LUMP\s+SUM\s+/i, '')   // "LUMP SUM …"
            .replace(/^\d+\s+/,        '')    // "009 …", "1 …"
            .replace(/^-\s+/,          '')    // "- …"
            .trim().toUpperCase().replace(/\s+/g, ' ')
            .replace(LOC, '')                 // trailing location
            .replace(/,\s*AND\b/g, ' AND')    // ", AND" → " AND"
            .replace(/\s*&\s*/g, ' AND ')     // "&" → "AND"
            .replace(/,/g, '');                // drop remaining commas (punctuation varies)
        // Expand abbreviations (whole-word only)
        n = n.replace(new RegExp('\\b(' + ABBR_KEYS + ')\\b', 'g'), m => ABBR[m] || m);
        // "FAC-WIDE" → "FACILITY-WIDE" (hyphen compound)
        n = n.replace(/\bFAC-WIDE\b/g, 'FACILITY-WIDE');
        return n.replace(/\s+/g, ' ').trim();
    };

    const renderProjects = () => {
        const listEl = document.getElementById('projects-list');
        const sectionEl = document.getElementById('projects-section');
        if (!listEl || !sectionEl) return;

        if (!activeProjects || !activeProjects.projects_by_program) {
            sectionEl.style.display = 'none';
            return;
        }
        sectionEl.style.display = '';

        const meta = activeProjects.metadata;
        // Always keep HD1/SD1 keys for the bill-draft comparison columns
        const hd1Key = `amount_${meta.draft1.toLowerCase()}`; // 'amount_hd1'
        const sd1Key = `amount_${meta.draft2.toLowerCase()}`; // 'amount_sd1'

        // Which fiscal year are we displaying? (drives the gov amount key)
        const govFyKey = activeData.metadata.fiscal_year === 2026 ? 'amount_fy2026' : 'amount_fy2027';

        // Build gov lookup: "(program_id):(normed_name):(fund_category)" → gov amount
        // Only populated when govActive and governor_projects data is loaded.
        const govMap = new Map();
        // Secondary lookup: "(program_id):(normed_name)" → {fund_category → amount}
        // Used as fallback when fund_category differs between gov and HD1.
        const govByProgName = new Map();
        if (govActive && governorProjectsData && governorProjectsData.projects_by_program) {
            for (const projs of Object.values(governorProjectsData.projects_by_program)) {
                for (const p of projs) {
                    const nm = normProjectName(p.project_name);
                    const k = `${p.program_id}:${nm}:${p.fund_category}`;
                    const amt = p[govFyKey] || 0;
                    govMap.set(k, (govMap.get(k) || 0) + amt);
                    const pk = `${p.program_id}:${nm}`;
                    if (!govByProgName.has(pk)) govByProgName.set(pk, new Map());
                    const fm = govByProgName.get(pk);
                    fm.set(p.fund_category, (fm.get(p.fund_category) || 0) + amt);
                }
            }
        }

        // Program-level Gov CIP totals from governor_request.json.
        // Used as the authoritative d1 for dept-level summary rows when govActive,
        // because project-name mismatches (abbreviations, truncation) cause govMap
        // lookups to return null for many projects, making the summed total show $0.
        const govCipProgTotals = new Map(); // program_id → total for govFyKey
        if (govActive && governorRequestData) {
            for (const r of governorRequestData) {
                if (r.section !== 'Capital Improvement') continue;
                govCipProgTotals.set(r.program_id,
                    (govCipProgTotals.get(r.program_id) || 0) + (r[govFyKey] || 0));
            }
        }

        // Determine the effective d1/d2 labels matching the program-level comparison table
        const projD1Label = govActive ? "Gov's Req." : meta.draft1;
        const projD2Label = sd1Active ? meta.draft2 : meta.draft1;
        const showProjHD1 = govActive && hd1Active && sd1Active; // middle HD1 column
        // Total colspan for dept summary row
        // Columns: Program + # + Project + Fund + [1 "d1" col: Gov or HD1] + [optional HD1 middle] + d2 + Change
        const totalCols = 4 + 1 + (showProjHD1 ? 1 : 0) + 2;

        // Build dept name lookup from comparison data
        const deptNameMap = new Map();
        for (const r of activeData.comparisons) {
            if (r.department_code && !deptNameMap.has(r.department_code)) {
                deptNameMap.set(r.department_code, r.department_name || r.department_code);
            }
        }

        // Flatten all projects and group by department_code
        const deptMap = new Map(); // deptCode → { code, name, projects[] }
        for (const projects of Object.values(activeProjects.projects_by_program)) {
            for (const pr of projects) {
                const dc = pr.department_code || '(unknown)';
                if (!deptMap.has(dc)) {
                    deptMap.set(dc, {
                        code: dc,
                        name: deptNameMap.get(dc) || pr.department_name || dc,
                        projects: [],
                    });
                }
                deptMap.get(dc).projects.push(pr);
            }
        }

        // Helper functions hoisted before loop so they can be used for dept-level sorting
        const getGovAmt = (pr) => {
            if (!govActive || govMap.size === 0) return null;
            const hName = normProjectName(pr.project_name);
            const k = `${pr.program_id}:${hName}:${pr.fund_category}`;
            if (govMap.has(k)) return govMap.get(k);
            // Bidirectional prefix match (min 25 chars overlap).
            // Covers both gov PDF truncation and HD1 truncation cases.
            const prefix = `${pr.program_id}:`;
            const suffix = `:${pr.fund_category}`;
            for (const [gk, val] of govMap) {
                if (!gk.startsWith(prefix) || !gk.endsWith(suffix)) continue;
                const gName = gk.slice(prefix.length, gk.length - suffix.length);
                if (gName.length >= 25 && hName.startsWith(gName)) return val;
                if (hName.length >= 25 && gName.startsWith(hName)) return val;
            }
            // Name-only fallback: same program + same normed name, but fund_category
            // differs. Returns the largest non-zero amount under that (program,name) key.
            // Covers cases like TRN501 where HD1 lists a project under one fund and the
            // gov splits it across multiple funds (Federal vs Revenue Bond etc.).
            const pk = `${pr.program_id}:${hName}`;
            if (govByProgName.has(pk)) {
                let best = 0;
                for (const v of govByProgName.get(pk).values()) {
                    if (v > best) best = v;
                }
                return best;
            }
            return null;
        };
        // Note: getD1Amt is used for per-project sorting before the fallback
        // map is populated, so it falls back to 0 on unmatched projects.
        // The render loop uses resolveGovAmt() below for the actual display value.
        const getD1Amt = (pr) => govActive ? (getGovAmt(pr) ?? 0) : (pr[hd1Key] || 0);
        const getD2Amt = (pr) => sd1Active ? (pr[sd1Key] || 0) : (pr[hd1Key] || 0);

        // Helper: program-level gov total for a set of projects (uses govCipProgTotals)
        const govD1ForProjects = (projects) => {
            const seen = new Set();
            let total = 0;
            for (const pr of projects) {
                if (!seen.has(pr.program_id)) {
                    seen.add(pr.program_id);
                    total += govCipProgTotals.get(pr.program_id) || 0;
                }
            }
            return total;
        };

        // Pro-rata Gov fallback: for projects whose names don't match the
        // governor's project list (abbreviations, truncation, Section 14 /
        // worksheet wording differences), distribute the program's Gov total
        // across unmatched projects proportional to their HD1 amount. This
        // preserves program totals and surfaces a Gov figure for every row
        // instead of showing "—" on nearly every project in a program.
        const govFallback = new Map(); // pr → fallback amount
        if (govActive && govCipProgTotals.size > 0) {
            const byProg = new Map();
            for (const d of deptMap.values()) {
                for (const pr of d.projects) {
                    if (!byProg.has(pr.program_id)) byProg.set(pr.program_id, []);
                    byProg.get(pr.program_id).push(pr);
                }
            }
            for (const [pid, projs] of byProg) {
                const progTotal = govCipProgTotals.get(pid) || 0;
                if (progTotal <= 0) continue;
                let matchedSum = 0;
                const unmatched = [];
                for (const pr of projs) {
                    const m = getGovAmt(pr);
                    if (m !== null) matchedSum += m;
                    else unmatched.push(pr);
                }
                if (unmatched.length === 0) continue;
                const leftover = progTotal - matchedSum;
                if (leftover <= 0) continue;
                const unmatchedHd1Sum = unmatched.reduce((s, pr) => s + (pr[hd1Key] || 0), 0);
                if (unmatchedHd1Sum > 0) {
                    for (const pr of unmatched) {
                        govFallback.set(pr, leftover * ((pr[hd1Key] || 0) / unmatchedHd1Sum));
                    }
                } else {
                    const each = leftover / unmatched.length;
                    for (const pr of unmatched) govFallback.set(pr, each);
                }
            }
        }
        // Resolve a project's Gov amount, preferring the exact/fuzzy name match
        // and falling back to the pro-rata estimate when no name match exists.
        const resolveGovAmt = (pr) => {
            const direct = getGovAmt(pr);
            if (direct !== null) return direct;
            if (govFallback.has(pr)) return govFallback.get(pr);
            return null;
        };

        // Sort depts by projSortCol using pre-computed aggregate totals
        const depts = [...deptMap.values()].map(d => {
            // Use program-level gov totals for d1 so sorting is correct even when
            // individual project names don't match govMap (abbreviations, truncation)
            const d1  = govActive ? govD1ForProjects(d.projects)
                                  : d.projects.reduce((s, pr) => s + (pr[hd1Key] || 0), 0);
            const d2  = d.projects.reduce((s, pr) => s + getD2Amt(pr), 0);
            const hd1 = d.projects.reduce((s, pr) => s + (pr[hd1Key] || 0), 0);
            return { ...d, _d1: d1, _d2: d2, _hd1: hd1, _delta: d2 - d1 };
        }).sort((a, b) => {
            if (frozenProjDeptOrder) {
                const ra = rankIn(frozenProjDeptOrder, a.code);
                const rb = rankIn(frozenProjDeptOrder, b.code);
                if (ra !== rb) return ra - rb;
            }
            const getVal = (d) => {
                if (projSortCol === 'd1')     return d._d1;
                if (projSortCol === 'd2')     return d._d2;
                if (projSortCol === 'hd1')    return d._hd1;
                if (projSortCol === 'change') return d._delta;
                return d.code.toLowerCase(); // program / project / default → by dept code
            };
            const va = getVal(a), vb = getVal(b);
            if (typeof va === 'string') return projSortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
            return projSortDir === 'asc' ? va - vb : vb - va;
        });

        // Filter by current search query
        const q = (document.getElementById('draft-search')?.value || '').toLowerCase();

        let bodyRows = '';
        let visibleCount = 0;
        let totalsD1 = 0, totalsD2 = 0, totalsHD1 = 0, totalsProjCount = 0;
        // For govActive footer: programs may appear under multiple depts (e.g.
        // BED170 → BED+AGS). Per-dept d1Total uses program-level rollup, so
        // summing it across depts double-counts cross-dept programs. Track which
        // programs we've already counted globally to dedupe the footer total.
        const globalProgsSeenForD1 = new Set();

        for (const dept of depts) {
            // Apply search filter per project
            const filteredProjects = q
                ? dept.projects.filter(pr =>
                    dept.code.toLowerCase().includes(q) ||
                    dept.name.toLowerCase().includes(q) ||
                    (pr.program_id || '').toLowerCase().includes(q) ||
                    (pr.program_name || '').toLowerCase().includes(q) ||
                    (pr.project_name || '').toLowerCase().includes(q))
                : [...dept.projects];

            if (filteredProjects.length === 0) continue;
            visibleCount++;
            bodyRows += `<tbody class="dept-block" data-dept-block="${dept.code}">`;

            // Sort by user-selected column. For Gov d1, use the resolved
            // amount (incl. pro-rata fallback) so sort order matches display.
            const sortD1 = (pr) => govActive ? (resolveGovAmt(pr) ?? 0) : (pr[hd1Key] || 0);
            filteredProjects.sort((a, b) => {
                const getVal = (pr) => {
                    if (projSortCol === 'd1')      return sortD1(pr);
                    if (projSortCol === 'd2')      return getD2Amt(pr);
                    if (projSortCol === 'hd1')     return pr[hd1Key] || 0;
                    if (projSortCol === 'change')  return getD2Amt(pr) - sortD1(pr);
                    if (projSortCol === 'program') return (pr.program_id || '').toLowerCase();
                    if (projSortCol === 'project') return (pr.project_name || '').toLowerCase();
                    return Number(pr.project_id) || 0;
                };
                const va = getVal(a), vb = getVal(b);
                if (typeof va === 'string')
                    return projSortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
                return projSortDir === 'asc' ? va - vb : vb - va;
            });

            // Gov d1 uses program-level governor_request.json totals so the dept summary
            // row is correct even when individual project names don't match govMap.
            const d1Total = govActive ? govD1ForProjects(filteredProjects)
                                      : filteredProjects.reduce((s, pr) => s + (pr[hd1Key] || 0), 0);
            const d2Total  = filteredProjects.reduce((s, pr) => s + getD2Amt(pr), 0);
            const hd1Total = filteredProjects.reduce((s, pr) => s + (pr[hd1Key] || 0), 0);
            // For govActive, dedupe program_id GLOBALLY across depts in the
            // footer total — three CIP programs (BED170, PSD900, HMS220) own
            // projects under multiple depts and would otherwise be summed twice.
            if (govActive) {
                for (const pr of filteredProjects) {
                    if (!globalProgsSeenForD1.has(pr.program_id)) {
                        globalProgsSeenForD1.add(pr.program_id);
                        totalsD1 += govCipProgTotals.get(pr.program_id) || 0;
                    }
                }
            } else {
                totalsD1 += d1Total;
            }
            totalsD2 += d2Total;
            totalsHD1 += hd1Total;
            totalsProjCount += filteredProjects.length;
            const delta = d2Total - d1Total;
            const deltaCls = delta > 0 ? 'positive' : delta < 0 ? 'negative' : '';
            const isOpen = expandedProjectPrograms.has(dept.code);
            const arrow = isOpen ? '▼' : '▶';

            // Dept group row — individual cells matching first table's dept row pattern
            bodyRows += `<tr class="dept-group-row project-dept-row${isOpen ? ' open' : ''}" data-project-dept="${dept.code}">
                <td colspan="3"><span class="dept-arrow">${arrow}</span> <span class="dept-chip">${highlight(dept.code, q)}</span> ${highlight(dept.name, q)} <span class="dept-count">(${filteredProjects.length} project${filteredProjects.length === 1 ? '' : 's'})</span></td>
                <td></td>
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(d1Total)}</span></td>
                ${showProjHD1 ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(hd1Total)}</span></td>` : ''}
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(d2Total)}</span></td>
                <td class="amount-cell ${deltaCls}"><span class="figure-chip">${fmtHtml(delta)}</span></td>
            </tr>`;

            // Individual project rows (hidden until dept expanded)
            for (const pr of filteredProjects) {
                const govAmt = resolveGovAmt(pr);
                const d1Amt = govActive ? (govAmt ?? 0) : (pr[hd1Key] || 0);
                const d2Amt = getD2Amt(pr);
                const hd1Amt = pr[hd1Key] || 0;
                const change = d2Amt - d1Amt;
                const cls = change > 0 ? 'positive' : change < 0 ? 'negative' : '';
                const badge = pr.change_type === 'added' ? '<span class="badge badge-add">new</span>'
                    : pr.change_type === 'removed' ? '<span class="badge badge-remove">removed</span>' : '';
                const scope = pr.scope ? `<div class="project-scope">${pr.scope}</div>` : '';
                const progName = pr.program_name || '';
                const govCell = govActive
                    ? `<td class="amount-cell"><span class="figure-chip${govAmt === null ? ' fig-na' : ''}">${govAmt !== null ? fmtHtml(govAmt) : '—'}</span></td>`
                    : '';
                const hd1Cell = showProjHD1
                    ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(hd1Amt)}</span></td>`
                    : '';
                bodyRows += `<tr class="project-row change-${pr.change_type}${isOpen ? '' : ' hidden'}" data-project-dept="${dept.code}">
                    <td class="project-program-cell"><strong${purposeTooltipAttrs(pr.program_id)}>${highlight(pr.program_id, q)}</strong><div class="project-prog-name">${highlight(progName, q)}</div></td>
                    <td class="project-num">${pr.project_id}</td>
                    <td><div class="project-name">${highlight(pr.project_name, q)}</div>${scope}</td>
                    <td><span class="fund-chip" data-fund-cat="${pr.fund_category || ''}">${shortFund(pr.fund_category)}</span></td>
                    ${govCell}
                    ${hd1Cell}
                    <td class="amount-cell"><span class="figure-chip">${fmtHtml(d2Amt)}</span></td>
                    <td class="amount-cell ${cls}"><span class="figure-chip">${fmtHtml(change)}</span> ${badge}</td>
                </tr>`;
            }
            bodyRows += `</tbody>`;
        }

        // Grand totals row for projects table
        if (visibleCount > 0) {
            const tDelta = totalsD2 - totalsD1;
            const tCls = tDelta > 0 ? 'positive' : tDelta < 0 ? 'negative' : '';
            const tArrow = tDelta > 0 ? '▲' : tDelta < 0 ? '▼' : '';
            const tPct = totalsD1 !== 0 ? ((tDelta / Math.abs(totalsD1)) * 100) : (tDelta !== 0 ? 100 : 0);
            const tPctStr = fmtPct(tPct).replace(/^\+/, '');
            const govCell = govActive ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(totalsD1)}</span></td>` : '';
            const d1Cell = govActive ? '' : `<td class="amount-cell"><span class="figure-chip">${fmtHtml(totalsD1)}</span></td>`;
            const hd1Cell = showProjHD1 ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(totalsHD1)}</span></td>` : '';
            bodyRows += `<tbody class="totals-block"><tr class="totals-row">
                <td colspan="3">Total <span class="totals-meta">${totalsProjCount} project${totalsProjCount === 1 ? '' : 's'} · ${visibleCount} dept${visibleCount === 1 ? '' : 's'}</span></td>
                <td></td>
                ${d1Cell}
                ${govCell}
                ${hd1Cell}
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(totalsD2)}</span></td>
                <td class="amount-cell change-cell ${tCls}">
                    <span class="change-main">${tArrow ? `<span class="change-arrow">${tArrow}</span>` : ''}<span class="figure-chip">${fmtHtml(tDelta)}</span></span>
                    ${tArrow ? `<span class="change-pct">${tPctStr}</span>` : ''}
                </td>
            </tr></tbody>`;
        }

        let html;
        if (visibleCount === 0) {
            html = `<div class="empty-state"><p>No capital projects match the current filter.</p></div>`;
        } else {
            const projSortArrow = (col) => {
                if (projSortCol === col) {
                    return `<span class="sort-ind">${projSortDir === 'asc' ? '▲' : '▼'}</span>`;
                }
                return `<span class="sort-hint">▲</span>`;
            };
            const govTh = govActive ? `<th class="sortable amount-cell" data-sort-proj="d1">${projD1Label}${projSortArrow('d1')}</th>` : '';
            const hd1Th = showProjHD1 ? `<th class="sortable amount-cell" data-sort-proj="hd1">HD1${projSortArrow('hd1')}</th>` : '';
            const d2Th = `<th class="sortable amount-cell" data-sort-proj="d2">${projD2Label}${projSortArrow('d2')}</th>`;
            const changeTh = `<th class="sortable amount-cell" data-sort-proj="change">Change<span class="th-sub">${projD1Label} → ${projD2Label}</span>${projSortArrow('change')}</th>`;
            const activeProjYear = (activeProjects === projectsDataFY26) ? 26 : 27;
            const projFyToggle = (projectsDataFY26 && projectsDataFY27)
                ? `<span class="fy-inline-toggle" id="fy-inline-toggle-proj"><button class="fy-inline-btn${activeProjYear === 26 ? ' active' : ''}" data-fy-inline="26">2026</button><button class="fy-inline-btn${activeProjYear === 27 ? ' active' : ''}" data-fy-inline="27">2027</button></span>`
                : '';
            html = `<table class="data-table project-table">
                <thead><tr>
                    <th class="sortable th-program-col" data-sort-proj="program"><div class="th-program-inner"><span class="th-program-label">Program${projSortArrow('program')}</span>${projFyToggle}</div></th>
                    <th>#</th>
                    <th class="sortable" data-sort-proj="project">Project${projSortArrow('project')}</th>
                    <th>Fund</th>
                    ${govActive ? '' : `<th class="sortable amount-cell" data-sort-proj="d1">${meta.draft1}${projSortArrow('d1')}</th>`}
                    ${govTh}
                    ${hd1Th}
                    ${d2Th}
                    ${changeTh}
                </tr></thead>
                ${bodyRows}
            </table>`;
        }

        listEl.innerHTML = html;
    };

    // --- Header dropdown logic (inside table headers) ---

    const attachHeaderDropdowns = () => {
        document.querySelectorAll('.th-dropdown-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const th = btn.closest('.th-dropdown');
                document.querySelectorAll('.th-dropdown.open').forEach(el => {
                    if (el !== th) el.classList.remove('open');
                });
                th.classList.toggle('open');
            });
        });
        document.querySelectorAll('.th-dropdown-menu').forEach(menu => {
            menu.addEventListener('click', (e) => e.stopPropagation());
            menu.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                cb.addEventListener('change', () => {
                    const th = cb.closest('.th-dropdown');
                    const allBoxes = th.querySelectorAll('input[type="checkbox"]');
                    const checked = [...allBoxes].filter(c => c.checked).map(c => c.value);
                    if (th.id === 'th-section') {
                        checkedSections = checked.length === allBoxes.length ? null : new Set(checked);
                    } else if (th.id === 'th-fund') {
                        checkedFunds = checked.length === allBoxes.length ? null : new Set(checked);
                    }
                    render();
                });
            });
        });
    };

    // Close header dropdowns on outside click
    document.addEventListener('click', () => {
        document.querySelectorAll('.th-dropdown.open').forEach(el => el.classList.remove('open'));
    });

    // --- Sortable column headers + department expand/collapse ---

    // --- Project section: scroll-to-projects chips + panel toggles ---

    document.addEventListener('click', (e) => {
        // FY year toggle inside capital projects table header
        const fyProjBtn = e.target.closest('[data-fy-inline]');
        if (fyProjBtn && fyProjBtn.closest('#projects-list')) {
            e.stopPropagation();
            const fy = fyProjBtn.dataset.fyInline;
            document.getElementById(`fy-btn-${fy}`)?.click();
            return;
        }
        // Capital projects table — sortable column headers
        const projTh = e.target.closest('th.sortable[data-sort-proj]');
        if (projTh) {
            const col = projTh.dataset.sortProj;
            if (projSortCol === col) { projSortDir = projSortDir === 'asc' ? 'desc' : 'asc'; }
            else { projSortCol = col; projSortDir = (col === 'program' || col === 'project') ? 'asc' : 'desc'; }
            frozenProjDeptOrder = null;
            renderProjects();
            return;
        }
        const chip = e.target.closest('[data-scroll-projects]');
        if (chip) {
            e.preventDefault();
            e.stopPropagation();
            const deptCode = chip.dataset.scrollProjects;
            expandedProjectPrograms.add(deptCode);
            renderProjects();
            requestAnimationFrame(() => {
                const row = document.querySelector(`.project-dept-row[data-project-dept="${deptCode}"]`);
                if (row) row.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
            return;
        }
        const deptRow = e.target.closest('.project-dept-row');
        if (deptRow) {
            const deptCode = deptRow.dataset.projectDept;
            if (expandedProjectPrograms.has(deptCode)) expandedProjectPrograms.delete(deptCode);
            else expandedProjectPrograms.add(deptCode);
            const isOpen = expandedProjectPrograms.has(deptCode);
            const arrow = deptRow.querySelector('.dept-arrow');
            if (arrow) arrow.textContent = isOpen ? '▼' : '▶';
            deptRow.classList.toggle('open', isOpen);
            document.querySelectorAll(`.project-row[data-project-dept="${deptCode}"]`)
                .forEach(r => r.classList.toggle('hidden', !isOpen));
        }
    });

    // Hover highlight: light up all rows that share a data-pair-key. Works
    // whether the user hovers the chip itself or the row it lives on.
    const draftResultsEl = document.getElementById('draft-results');
    const clearPairHighlight = () => {
        document.querySelectorAll('.pair-highlight').forEach(el => el.classList.remove('pair-highlight'));
    };
    const applyPairHighlight = (pairKey) => {
        if (!pairKey) return;
        document.querySelectorAll(`[data-pair-key="${pairKey}"]`).forEach(el => {
            // Apply to rows only (skip the chip itself to avoid self-glow)
            if (el.tagName === 'TR') el.classList.add('pair-highlight');
        });
    };
    draftResultsEl?.addEventListener('mouseover', (e) => {
        const chip = e.target.closest('.pair-chip');
        if (chip) {
            clearPairHighlight();
            applyPairHighlight(chip.dataset.pairKey);
        }
    });
    draftResultsEl?.addEventListener('mouseout', (e) => {
        const chip = e.target.closest('.pair-chip');
        if (chip) clearPairHighlight();
    });

    draftResultsEl?.addEventListener('click', (e) => {
        // Paired-dept chip: scroll to sibling dept and expand it
        const pairChip = e.target.closest('.pair-chip');
        if (pairChip) {
            e.preventDefault();
            e.stopPropagation();
            const targetDept = pairChip.dataset.scrollDept;
            if (targetDept) {
                expandedDepts.add(targetDept);
                render();
                requestAnimationFrame(() => {
                    const row = document.querySelector(`.dept-group-row[data-dept="${targetDept}"]`);
                    if (row) row.scrollIntoView({ behavior: 'smooth', block: 'start' });
                });
            }
            return;
        }
        // Cross-reference split-dept link (legacy .split-link — now unused but kept for safety)
        const splitLink = e.target.closest('.split-link');
        if (splitLink) {
            e.preventDefault();
            const targetDept = splitLink.dataset.scrollDept;
            if (targetDept) {
                expandedDepts.add(targetDept);
                render();
                // Scroll to the target dept row after render
                requestAnimationFrame(() => {
                    const row = document.querySelector(`.dept-group-row[data-dept="${targetDept}"]`);
                    if (row) row.scrollIntoView({ behavior: 'smooth', block: 'start' });
                });
            }
            return;
        }
        // Inline year toggle inside Program header
        const fyInlineBtn = e.target.closest('[data-fy-inline]');
        if (fyInlineBtn) {
            e.stopPropagation();
            const fy = fyInlineBtn.dataset.fyInline;
            document.getElementById(`fy-btn-${fy}`)?.click();
            return;
        }
        // Sortable headers
        const th = e.target.closest('th.sortable');
        if (th) {
            const col = th.dataset.sort;
            if (sortCol === col) { sortDir = sortDir === 'asc' ? 'desc' : 'asc'; }
            else { sortCol = col; sortDir = col === 'program_name' ? 'asc' : 'desc'; }
            frozenDeptOrder = null;
            frozenProgOrder = null;
            render();
            return;
        }
        // Department group row expand/collapse
        const groupRow = e.target.closest('.dept-group-row:not(.prog-group-row)');
        if (groupRow) {
            const dept = groupRow.dataset.dept;
            if (expandedDepts.has(dept)) expandedDepts.delete(dept);
            else expandedDepts.add(dept);
            const arrow = groupRow.querySelector('.dept-arrow');
            const isOpen = expandedDepts.has(dept);
            if (arrow) arrow.textContent = isOpen ? '▼' : '▶';
            groupRow.classList.toggle('open', isOpen);
            document.querySelectorAll(`.dept-detail-row[data-dept="${dept}"]`).forEach(row => {
                row.classList.toggle('hidden', !isOpen);
            });
            if (!isOpen) {
                document.querySelectorAll(`.prog-section-row[data-dept="${dept}"]`).forEach(row => row.classList.add('hidden'));
                document.querySelectorAll(`.prog-fund-row[data-dept="${dept}"]`).forEach(row => row.classList.add('hidden'));
            } else {
                document.querySelectorAll(`.prog-section-row[data-dept="${dept}"]`).forEach(row => {
                    row.classList.toggle('hidden', !expandedPrograms.has(row.dataset.prog));
                });
                document.querySelectorAll(`.prog-fund-row[data-dept="${dept}"]`).forEach(row => {
                    const fkOpen = expandedFunds.has(row.dataset.fundKey);
                    const pgOpen = row.dataset.prog ? expandedPrograms.has(row.dataset.prog) : true;
                    row.classList.toggle('hidden', !(fkOpen && pgOpen));
                });
            }
            return;
        }
        // Fund group row expand/collapse (multi-fund program or section rows)
        const fundGroupRow = e.target.closest('.prog-fund-group');
        if (fundGroupRow) {
            const fk = fundGroupRow.dataset.fundKey;
            if (expandedFunds.has(fk)) expandedFunds.delete(fk);
            else expandedFunds.add(fk);
            const arrow = fundGroupRow.querySelector('.dept-arrow');
            const isOpen = expandedFunds.has(fk);
            if (arrow) arrow.textContent = isOpen ? '▼' : '▶';
            document.querySelectorAll(`.prog-fund-row[data-fund-key="${fk}"]`).forEach(row => {
                row.classList.toggle('hidden', !isOpen);
            });
            return;
        }
        // Program group row expand/collapse (mixed section)
        const progRow = e.target.closest('.prog-group-row');
        if (progRow) {
            const progKey = progRow.dataset.prog;
            if (expandedPrograms.has(progKey)) expandedPrograms.delete(progKey);
            else expandedPrograms.add(progKey);
            const arrow = progRow.querySelector('.dept-arrow');
            const isOpen = expandedPrograms.has(progKey);
            if (arrow) arrow.textContent = isOpen ? '▼' : '▶';
            document.querySelectorAll(`.prog-section-row[data-prog="${progKey}"]`).forEach(row => {
                row.classList.toggle('hidden', !isOpen);
            });
            // Also cascade to fund sub-rows under this program's sections
            document.querySelectorAll(`.prog-fund-row[data-prog="${progKey}"]`).forEach(row => {
                row.classList.toggle('hidden', !isOpen || !expandedFunds.has(row.dataset.fundKey));
            });
            return;
        }
    });

    // --- Fund detail section: expand/collapse + export ---
    document.getElementById('fund-detail-section')?.addEventListener('click', (e) => {
        const fundRow = e.target.closest('.fund-group-row');
        if (fundRow) {
            const ft = fundRow.dataset.fundType;
            if (expandedFundTypes.has(ft)) expandedFundTypes.delete(ft);
            else expandedFundTypes.add(ft);
            const arrow = fundRow.querySelector('.dept-arrow');
            const isOpen = expandedFundTypes.has(ft);
            if (arrow) arrow.textContent = isOpen ? '▼' : '▶';
            fundRow.classList.toggle('open', isOpen);
            document.querySelectorAll(`.fund-detail-row[data-fund-type="${ft}"]`).forEach(row => {
                row.classList.toggle('hidden', !isOpen);
            });
        }
    });

    // --- FY toggle ---

    // Capture the topmost expanded parent row currently in the viewport so
    // we can re-anchor scroll position after the cross-FY re-render. Without
    // this the user loses their place because row heights / ordering change
    // between FY26 and FY27. Expanded-state Sets are intentionally NOT reset
    // on FY toggle — their keys (dept code, program id, fund key, fund type)
    // are stable across years.
    // Capture current row order from the DOM so we can freeze it across the
    // FY toggle. Order is preserved until the user explicitly re-sorts by
    // clicking a column header (see the sort-click handlers below, which
    // call clearFrozenOrder).
    const captureFrozenOrder = () => {
        frozenDeptOrder = Array.from(
            document.querySelectorAll('#draft-table .dept-group-row[data-dept]')
        ).map(r => r.dataset.dept);
        frozenProgOrder = new Map();
        for (const code of frozenDeptOrder) {
            const seen = new Set();
            const order = [];
            const rows = document.querySelectorAll(
                `#draft-table .dept-detail-row[data-dept="${code}"]`);
            for (const r of rows) {
                const pid = r.querySelector('.detail-indent strong')?.textContent.trim()
                         || r.querySelector('strong')?.textContent.trim();
                if (pid && !seen.has(pid)) { seen.add(pid); order.push(pid); }
            }
            frozenProgOrder.set(code, order);
        }
        frozenProjDeptOrder = Array.from(
            document.querySelectorAll('.project-table .project-dept-row[data-project-dept]')
        ).map(r => r.dataset.projectDept);
        frozenFundOrder = Array.from(
            document.querySelectorAll('.fund-group-row[data-fund-type]')
        ).map(r => r.dataset.fundType);
    };
    const clearFrozenOrder = () => {
        frozenDeptOrder = null;
        frozenProgOrder = null;
        frozenProjDeptOrder = null;
        frozenFundOrder = null;
    };
    // Comparator helper: rank by position in a frozen order array (missing
    // entries sink to the end). Returns 0 when equally ranked.
    const rankIn = (arr, key) => {
        const i = arr ? arr.indexOf(key) : -1;
        return i < 0 ? Infinity : i;
    };

    const captureFYAnchor = () => {
        const rows = document.querySelectorAll(
            '.dept-group-row.open, .project-dept-row.open, .fund-group-row.open');
        let anchor = null;
        for (const r of rows) {
            const top = r.getBoundingClientRect().top;
            if (top >= 0) { anchor = r; break; }
        }
        if (!anchor) return null;
        const kind = anchor.classList.contains('fund-group-row') ? 'fund'
                   : anchor.classList.contains('project-dept-row') ? 'proj'
                   : 'dept';
        const key = kind === 'fund' ? anchor.dataset.fundType
                  : kind === 'proj' ? anchor.dataset.projectDept
                  : anchor.dataset.dept;
        return { kind, key, offset: anchor.getBoundingClientRect().top };
    };
    // Replay the refresh animation on the Net Change node so the user gets a
    // soft cross-fade confirming the FY swap updated the headline.
    const playNetRefresh = () => {
        const tl = document.getElementById('compare-timeline');
        if (!tl) return;
        tl.classList.remove('net-refresh');
        void tl.offsetWidth; // force reflow so re-adding the class restarts the animation
        tl.classList.add('net-refresh');
    };

    const restoreFYAnchor = (a) => {
        if (!a) return;
        requestAnimationFrame(() => {
            const sel = a.kind === 'fund' ? `.fund-group-row[data-fund-type="${a.key}"]`
                      : a.kind === 'proj' ? `.project-dept-row[data-project-dept="${a.key}"]`
                      :                     `.dept-group-row[data-dept="${a.key}"]`;
            const el = document.querySelector(sel);
            if (!el) return;
            const newTop = el.getBoundingClientRect().top;
            window.scrollBy(0, newTop - a.offset);
        });
    };

    document.getElementById('fy-btn-26')?.addEventListener('click', () => {
        if (!draftComparisonData) return;
        if (activeData === draftComparisonData) return;
        const anchor = captureFYAnchor();
        captureFrozenOrder();
        activeData = draftComparisonData;
        activeProjects = projectsDataFY26;
        document.getElementById('fy-btn-26').classList.add('active');
        document.getElementById('fy-btn-27')?.classList.remove('active');
        document.querySelector('.fy-seg-ctrl')?.setAttribute('data-active', '26');
        updateSummaryCards();
        playNetRefresh();
        render();
        restoreFYAnchor(anchor);
    });
    document.getElementById('fy-btn-27')?.addEventListener('click', () => {
        if (!draftComparisonDataFY27) return;
        if (activeData === draftComparisonDataFY27) return;
        const anchor = captureFYAnchor();
        captureFrozenOrder();
        activeData = draftComparisonDataFY27;
        activeProjects = projectsDataFY27;
        document.getElementById('fy-btn-27').classList.add('active');
        document.getElementById('fy-btn-26')?.classList.remove('active');
        document.querySelector('.fy-seg-ctrl')?.setAttribute('data-active', '27');
        updateSummaryCards();
        playNetRefresh();
        render();
        restoreFYAnchor(anchor);
    });

    // --- Compare timeline: Gov's Request / HD1 / SD1 checkboxes ---
    const updateTimeline = () => {
        govActive  = document.getElementById('tl-gov')?.checked  ?? true;
        hd1Active  = document.getElementById('tl-hd1')?.checked  ?? true;
        sd1Active  = document.getElementById('tl-sd1')?.checked  ?? true;

        // Enforce minimum two active nodes: disable a checkbox if unchecking it
        // would leave only one node active.
        const activeCount = [govActive, hd1Active, sd1Active].filter(Boolean).length;
        ['gov', 'hd1', 'sd1'].forEach(node => {
            const cb = document.getElementById(`tl-${node}`);
            if (!cb) return;
            const nodeActive = node === 'gov' ? govActive : node === 'hd1' ? hd1Active : sd1Active;
            // Disable this checkbox if it's currently checked and is the only one keeping count ≥ 2
            cb.disabled = nodeActive && activeCount <= 2;
        });

        // Reflect inactive state on the timeline container (keyed per-column);
        // CSS drives the visual change by selecting cells that carry the matching
        // data-col attribute.
        const tl = document.getElementById('compare-timeline');
        if (tl) {
            ['gov', 'hd1', 'sd1'].forEach(node => {
                const cb = document.getElementById(`tl-${node}`);
                tl.classList.toggle(`col-${node}-inactive`, !(cb?.checked));
            });
        }

        updateSummaryCards();
        render();
    };
    document.querySelectorAll('.tl-cb').forEach(cb => cb.addEventListener('change', updateTimeline));

    // Expand caret (left of Gov amount) — toggle Op/Cap breakdown
    const expandBtn = document.getElementById('tl-expand-btn');
    if (expandBtn) {
        expandBtn.addEventListener('click', () => {
            showBreakdown = !showBreakdown;
            updateSummaryCards();
        });
    }

    // --- Reading guide toggle ---

    const readingGuideToggle = document.getElementById('reading-guide-toggle');
    const readingGuideContent = document.getElementById('reading-guide-content');
    if (readingGuideToggle && readingGuideContent) {
        readingGuideToggle.addEventListener('click', () => {
            const isExpanded = readingGuideContent.style.display !== 'none';
            readingGuideContent.style.display = isExpanded ? 'none' : 'block';
            readingGuideToggle.textContent = isExpanded ? 'More' : 'Less';
            readingGuideToggle.setAttribute('aria-expanded', !isExpanded);
        });
    }

    // --- Fund chip tooltip (JS-rendered, appended to body to escape table clipping) ---
    (() => {
        let tip = null;
        document.getElementById('draft-results').addEventListener('mouseover', (e) => {
            const chip = e.target.closest('.fund-chip-multi');
            if (!chip || !chip.dataset.funds) return;
            if (!tip) {
                tip = document.createElement('div');
                tip.className = 'fund-tooltip';
                document.body.appendChild(tip);
            }
            tip.textContent = chip.dataset.funds.split(' · ').join('\n');
            const r = chip.getBoundingClientRect();
            tip.style.display = 'block';
            const tw = tip.offsetWidth;
            let left = r.left + r.width / 2 - tw / 2 + window.scrollX;
            left = Math.max(8, Math.min(left, window.innerWidth - tw - 8));
            tip.style.left = left + 'px';
            tip.style.top = (r.bottom + window.scrollY + 6) + 'px';
        });
        document.getElementById('draft-results').addEventListener('mouseout', (e) => {
            const chip = e.target.closest('.fund-chip-multi');
            if (chip && tip) tip.style.display = 'none';
        });
    })();

    // --- Other controls ---

    document.getElementById('draft-results')?.addEventListener('click', (e) => {
        const btn = e.target.closest('button.export-btn');
        if (!btn) return;
        const meta = window._lastDraftMeta || activeData.metadata;
        const d1Key = getD1Key(), d2Key = getD2Key();
        if (btn.id === 'export-drafts') {
            const rows = (window._lastDraftResults || activeData.comparisons).map(r => ({
                program_id: r.program_id, program_name: r.program_name,
                department_code: r.department_code, department_name: r.department_name,
                section: r.section, fund_type: r.fund_type, fund_category: r.fund_category,
                [meta.draft1]: r[d1Key], [meta.draft2]: r[d2Key],
                change: r.change, pct_change: r.pct_change, change_type: r.change_type,
            }));
            downloadCSV(rows, `${meta.bill_number}_${meta.draft1}_vs_${meta.draft2}_FY${meta.fiscal_year}.csv`);
        }
    });

    document.getElementById('fund-detail-section')?.addEventListener('click', (e) => {
        const btn = e.target.closest('button.export-btn');
        if (!btn || btn.id !== 'export-fund-detail') return;
        const meta = window._lastDraftMeta || activeData.metadata;
        const d1Key = getD1Key(), d2Key = getD2Key();
        const rows = activeData.comparisons.map(r => ({
            fund_type: r.fund_type, fund_category: r.fund_category,
            program_id: r.program_id, program_name: r.program_name,
            department_code: r.department_code, department_name: r.department_name,
            section: r.section,
            [meta.draft1]: r[d1Key], [meta.draft2]: r[d2Key],
            change: r.change, pct_change: r.pct_change,
        }));
        downloadCSV(rows, `${meta.bill_number}_fund_detail_FY${meta.fiscal_year}.csv`);
    });

    // --- Initial render ---
    updateSummaryCards();
    render();
};

// ---------------------------------------------------------------------------
// Init hooks
// ---------------------------------------------------------------------------
window.initHomePage = async function () {
    if (!departmentsData?.length) return;

    const DETAIL_FY = 2026;
    let selectedFy = DETAIL_FY;
    let sortDir    = 'desc';
    let histMode   = 'nominal';   // 'nominal' | 'real' — drives top history chart

    // ---- Department grid -------------------------------------------------
    // Each card: dept name + "FY{year} total" + (when DETAIL_FY) full
    // operating/capital/positions breakdown + 12-yr nominal sparkline.
    // Non-detail years collapse to total + sparkline.
    const renderDeptCard = (dept, totalForFy, sparkSvg) => {
        const isDetail = selectedFy === DETAIL_FY;
        const op  = dept.operating_budget || 0;
        const cap = dept.capital_budget || 0;
        const ot  = dept.one_time_appropriations || 0;
        const pos = dept.positions;
        const detailRows = isDetail ? `
            <div class="budget-row"><span>Operating</span><span>${fmt(op)}</span></div>
            ${cap > 0 ? `<div class="budget-row"><span>Capital</span><span>${fmt(cap)}</span></div>` : ''}
            ${ot > 0 ? `<div class="budget-row"><span>One-Time</span><span>${fmt(ot)}</span></div>` : ''}
            ${pos ? `<div class="budget-row"><span>Positions</span><span>${pos.toLocaleString(undefined,{maximumFractionDigits:0})}</span></div>` : ''}
        ` : '';
        const totalDisplay = totalForFy != null ? fmt(totalForFy) : '—';
        return `
            <a href="#/department/${dept.id}" class="department-card">
                <h3>${dept.name}</h3>
                <div class="card-content">
                    <div class="budget-total">
                        <span>Total Budget · FY${selectedFy}</span>
                        <strong>${totalDisplay}</strong>
                    </div>
                    ${sparkSvg ? `<div class="dept-card-spark-wrap">${sparkSvg}</div>` : ''}
                    ${detailRows ? `<div class="budget-breakdown">${detailRows}</div>` : ''}
                </div>
            </a>`;
    };

    const renderGrid = () => {
        const fyTotals = deptTotalsForFy(selectedFy); // Map<code, {nominal,real}>

        // Build list with year-specific totals attached, then sort.
        const rows = departmentsData.map(d => {
            const histRow = fyTotals.get(d.code);
            const total = histRow
                ? histRow.nominal
                : (selectedFy === DETAIL_FY
                    ? (d.operating_budget||0) + (d.capital_budget||0) + (d.one_time_appropriations||0)
                    : null);
            return { dept: d, total };
        });

        rows.sort((a, b) => {
            const tA = a.total ?? -Infinity;
            const tB = b.total ?? -Infinity;
            return sortDir === 'asc' ? tA - tB : tB - tA;
        });

        // Pre-compute sparkline points per dept once (12-yr nominal series)
        const grid = document.getElementById('dept-grid');
        if (!grid) return;
        const histDepts = historicalTrendsData?.by_department || [];
        const histByCode = new Map(histDepts.map(d => [d.dept_code, d]));
        const cards = rows.map(({ dept, total }) => {
            const hist = histByCode.get(dept.code);
            const points = hist
                ? hist.series.map(s => ({ fy: s.fy, value: s.nominal }))
                : [];
            const spark = deptHistorySparkline(points);
            return renderDeptCard(dept, total, spark);
        });
        grid.innerHTML = cards.join('');
    };

    // ---- Summary cards (state-wide totals for selected year) ------------
    const renderSummaryCards = () => {
        const wrap = document.getElementById('hb300-summary-cards');
        if (!wrap) return;
        const t = stateTotalsForFy(selectedFy);
        const totalAmt = t ? t.total_nominal
                           : (selectedFy === DETAIL_FY ? summaryStats.total_budget : null);
        const opAmt    = t ? t.operating_nominal
                           : (selectedFy === DETAIL_FY ? summaryStats.operating_budget : null);
        const capAmt   = t ? t.capital_nominal
                           : (selectedFy === DETAIL_FY ? summaryStats.capital_budget : null);
        const posAmt   = (selectedFy === DETAIL_FY) ? summaryStats.total_positions : null;
        wrap.innerHTML = `
            <div class="summary-card">
                <div class="amount">${totalAmt != null ? fmtHtmlCard(totalAmt) : '—'}</div>
                <div class="label">Total Budget</div>
                <div class="label-sub">FY${selectedFy}</div>
            </div>
            <div class="summary-card">
                <div class="amount">${opAmt != null ? fmtHtmlCard(opAmt) : '—'}</div>
                <div class="label">Operating</div>
            </div>
            <div class="summary-card">
                <div class="amount">${capAmt != null ? fmtHtmlCard(capAmt) : '—'}</div>
                <div class="label">Capital</div>
            </div>
            ${posAmt ? `<div class="summary-card">
                <div class="amount">${posAmt.toLocaleString(undefined,{maximumFractionDigits:0})}</div>
                <div class="label">Total Positions</div>
                <div class="label-sub">FY${selectedFy}</div>
            </div>` : ''}`;

        // Help line below the year selector — explains what the user will see
        const help = document.getElementById('hb300-fy-help');
        if (help) {
            if (selectedFy === DETAIL_FY) {
                help.textContent = 'Showing the full FY2026 enacted budget — operating, capital, and program-level detail.';
            } else if (historicalTrendsData?.metadata?.projected_fys?.includes(selectedFy)) {
                help.textContent = `FY${selectedFy} is projected by the FY2026–27 biennial bill (HB300, Act 250 SLH 2025). Department totals only.`;
            } else {
                help.textContent = `Department totals only — FY${selectedFy} is from the corresponding biennial appropriations act.`;
            }
        }
    };

    // ---- State-wide history chart (line) --------------------------------
    let historyChart = null;
    const renderHistoryChart = () => {
        const canvas = document.getElementById('hb300-history-chart');
        if (!canvas || typeof Chart === 'undefined' || !historicalTrendsData) return;
        if (historyChart) historyChart.destroy();

        const totals = historicalTrendsData.totals_by_fy;
        const baseFy = historicalTrendsData.metadata.base_fy;
        const labels = totals.map(t => `FY${t.fy}`);
        const opK    = histMode === 'real' ? 'operating_real' : 'operating_nominal';
        const capK   = histMode === 'real' ? 'capital_real'   : 'capital_nominal';
        const totK   = histMode === 'real' ? 'total_real'     : 'total_nominal';
        const fmtB   = (v) => `$${(v / 1e9).toFixed(2)}B`;

        // Highlight the currently-selected year by tinting the matching point.
        const highlightIndex = totals.findIndex(t => t.fy === selectedFy);
        const pointBg = totals.map((_t, i) => i === highlightIndex ? '#3d4a45' : '#88a194');
        const pointRadii = totals.map((_t, i) => i === highlightIndex ? 7 : 4);

        historyChart = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Operating',
                        data: totals.map(t => t[opK]),
                        borderColor: '#5a7b68',
                        backgroundColor: 'rgba(90, 123, 104, 0.15)',
                        tension: 0.25, fill: false, borderWidth: 2,
                        pointRadius: 3, pointHoverRadius: 5,
                    },
                    {
                        label: 'Capital',
                        data: totals.map(t => t[capK]),
                        borderColor: '#a08e58',
                        backgroundColor: 'rgba(160, 142, 88, 0.15)',
                        tension: 0.25, fill: false, borderWidth: 2,
                        pointRadius: 3, pointHoverRadius: 5,
                    },
                    {
                        label: 'Total',
                        data: totals.map(t => t[totK]),
                        borderColor: '#3d4a45',
                        backgroundColor: 'rgba(61, 74, 69, 0.10)',
                        tension: 0.25, fill: false, borderWidth: 3,
                        pointRadius: pointRadii,
                        pointHoverRadius: 7,
                        pointBackgroundColor: pointBg,
                        pointBorderColor: pointBg,
                    },
                ],
            },
            options: {
                maintainAspectRatio: false,
                responsive: true,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: true, position: 'top', labels: { boxWidth: 14 } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${fmtB(ctx.parsed.y)}`,
                        },
                    },
                    datalabels: { display: false },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { callback: (v) => `$${(v / 1e9).toFixed(0)}B` },
                        title: { display: true, text: histMode === 'real' ? `Constant FY${baseFy} dollars` : 'Nominal dollars' },
                    },
                    x: { grid: { display: false } },
                },
                onClick: (_evt, els) => {
                    if (!els?.length) return;
                    const idx = els[0].index;
                    const fy = totals[idx]?.fy;
                    const sel = document.getElementById('hb300-fy-select');
                    if (sel && fy != null) {
                        sel.value = String(fy);
                        sel.dispatchEvent(new Event('change'));
                    }
                },
            },
        });
    };

    const renderAll = () => {
        renderSummaryCards();
        renderHistoryChart();
        renderGrid();
    };

    // ---- Wire up controls ------------------------------------------------
    document.getElementById('hb300-fy-select')?.addEventListener('change', (e) => {
        const v = parseInt(e.target.value, 10);
        if (Number.isFinite(v)) {
            selectedFy = v;
            renderAll();
        }
    });

    document.querySelectorAll('.sort-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            sortDir = this.dataset.sort;
            document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            renderGrid();
        });
    });

    document.querySelectorAll('.hist-toggle-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const m = this.dataset.mode;
            if (m === histMode) return;
            histMode = m;
            document.querySelectorAll('.hist-toggle-btn').forEach(b =>
                b.classList.toggle('active', b.dataset.mode === histMode));
            renderHistoryChart();
        });
    });

    document.getElementById('export-depts')?.addEventListener('click', () => {
        // Always export FY2026 detail rows — that's the only year with
        // operating/capital/position breakdown in `departmentsData`.
        const rows = departmentsData.map(d => {
            const hist = historicalTrendsData?.by_department.find(x => x.dept_code === d.code);
            const yrTotal = hist?.series.find(s => s.fy === selectedFy)?.nominal ?? null;
            return {
                code: d.code,
                name: d.name,
                fy: selectedFy,
                total: yrTotal != null
                    ? yrTotal
                    : (selectedFy === DETAIL_FY
                        ? (d.operating_budget || 0) + (d.capital_budget || 0) + (d.one_time_appropriations || 0)
                        : ''),
                operating_fy2026: d.operating_budget,
                capital_fy2026:   d.capital_budget,
                one_time_fy2026:  d.one_time_appropriations,
                positions_fy2026: d.positions || '',
            };
        });
        downloadCSV(rows, `departments_fy${selectedFy}.csv`);
    });

    // Initial render
    renderAll();
};

// ===========================================================================
// Tax Calculator Page ("Where Do My Taxes Go?")
// ===========================================================================

// Hawaii income tax brackets (tax year 2025) — [bracket_top, marginal_rate]
// Single / Married filing separately
const HI_TAX_BRACKETS = {
    single: [
        [2400, 0.014], [4800, 0.032], [9600, 0.055], [14400, 0.064],
        [19200, 0.068], [24000, 0.072], [36000, 0.076], [48000, 0.079],
        [150000, 0.0825], [175000, 0.09], [200000, 0.10], [Infinity, 0.11],
    ],
    // Married filing jointly / qualifying widow(er): all thresholds doubled
    mfj: [
        [4800, 0.014], [9600, 0.032], [19200, 0.055], [28800, 0.064],
        [38400, 0.068], [48000, 0.072], [72000, 0.076], [96000, 0.079],
        [300000, 0.0825], [350000, 0.09], [400000, 0.10], [Infinity, 0.11],
    ],
    // Head of household: thresholds 1.5x single
    hoh: [
        [3600, 0.014], [7200, 0.032], [14400, 0.055], [21600, 0.064],
        [28800, 0.068], [36000, 0.072], [54000, 0.076], [72000, 0.079],
        [225000, 0.0825], [262500, 0.09], [300000, 0.10], [Infinity, 0.11],
    ],
};
const HI_STANDARD_DEDUCTION = { single: 4400, mfj: 8800, hoh: 6424 };

function computeHawaiiTax(grossIncome, filingStatus) {
    const fs = HI_TAX_BRACKETS[filingStatus] ? filingStatus : 'single';
    const taxable = Math.max(0, (grossIncome || 0) - HI_STANDARD_DEDUCTION[fs]);
    const brackets = HI_TAX_BRACKETS[fs];
    let tax = 0, prev = 0;
    for (const [top, rate] of brackets) {
        if (taxable <= top) { tax += (taxable - prev) * rate; break; }
        tax += (top - prev) * rate;
        prev = top;
    }
    return Math.round(tax);
}

// Aggregate already-loaded fyComparisonData by department (+ programs within each)
function aggregateByDepartment(fy) {
    const key = `amount_fy${fy}`;
    const byDept = new Map();
    for (const r of (fyComparisonData || [])) {
        if (!r.department_code) continue;
        if (r.fund_category !== 'General Funds') continue; // tax dollars → general fund only
        const amt = r[key] || 0;
        if (amt === 0) continue;
        if (!byDept.has(r.department_code)) {
            byDept.set(r.department_code, {
                code: r.department_code,
                name: r.department_name || r.department_code,
                total: 0,
                programs: new Map(),
            });
        }
        const d = byDept.get(r.department_code);
        d.total += amt;
        const pid = r.program_id || 'UNKNOWN';
        if (!d.programs.has(pid)) {
            d.programs.set(pid, {
                program_id: pid,
                program_name: r.program_name || pid,
                total: 0,
            });
        }
        d.programs.get(pid).total += amt;
    }
    const depts = [...byDept.values()].map(d => ({
        code: d.code,
        name: d.name,
        total: d.total,
        programs: [...d.programs.values()].sort((a, b) => b.total - a.total),
    })).sort((a, b) => b.total - a.total);
    const grandTotal = depts.reduce((s, d) => s + d.total, 0);
    return { depts, grandTotal };
}

window.taxCalculatorPage = async function () {
    return `
        <section class="tax-calc-page">
            <h2>Where Do My Taxes Go?</h2>
            <p class="page-desc">Hawaiʻi income tax funds the state General Fund — about $10.6B of the total budget. Enter what you paid to see how your dollars were proportionally allocated across state agencies.</p>

            <div class="tax-input-card">
                <div class="income-inputs-row">
                    <div class="income-field">
                        <label for="tax-helper-income">Annual income</label>
                        <div class="input-with-prefix">
                            <span class="prefix">$</span>
                            <input type="number" id="tax-helper-income" placeholder="75,000" min="0" step="1000" inputmode="numeric" autocomplete="off">
                        </div>
                    </div>
                    <div class="filing-field">
                        <label for="tax-helper-filing">Filing status</label>
                        <select id="tax-helper-filing">
                            <option value="single">Single</option>
                            <option value="mfj">Married filing jointly</option>
                            <option value="hoh">Head of household</option>
                        </select>
                    </div>
                </div>
                <div class="tax-paid-row">
                    <label for="tax-input" class="tax-input-label">Hawaiʻi state tax paid <span class="auto-label" id="tax-auto-label"></span></label>
                    <div class="input-with-prefix">
                        <span class="prefix">$</span>
                        <input type="number" id="tax-input" placeholder="0" min="0" step="100" inputmode="numeric" autocomplete="off">
                    </div>
                </div>
                <p class="helper-note">Estimate uses 2025 Hawaiʻi income tax brackets and standard deduction. Actual tax may vary.</p>
            </div>

            <div class="fy-toggle" id="calc-fy-toggle">
                <button class="sort-btn active" data-fy="2026">FY2026</button>
                <button class="sort-btn" data-fy="2027">FY2027</button>
            </div>

            <div class="summary-cards-grid tax-summary-grid" id="tax-summary"></div>

            <p class="calc-note">This calculator shows only General Fund appropriations — the portion of the state budget funded by taxes like income tax, general excise tax, and other state revenues. Federal grants, bond proceeds, and special funds are excluded.</p>

            <div class="treemap-breadcrumb" id="treemap-breadcrumb">
                <span class="crumb-root">All departments</span>
            </div>
            <div class="treemap-container"><canvas id="tax-treemap"></canvas></div>
            <p class="treemap-hint">Click a department tile to see its programs.</p>

            <div class="table-search-bar">
                <h3>Breakdown by department</h3>
                <div class="search-input-wrap">
                    <span class="search-icon">🔍</span>
                    <input type="text" id="tax-program-search" placeholder="Search programs…" autocomplete="off">
                    <button class="search-clear" id="tax-search-clear" style="display:none;" type="button" aria-label="Clear search">✕</button>
                </div>
            </div>
            <div id="tax-search-status" class="search-status" style="display:none;"></div>
            <table class="data-table" id="tax-detail-table">
                <thead><tr>
                    <th>Department</th>
                    <th class="amount-cell">% of your taxes</th>
                    <th class="amount-cell">Your share</th>
                    <th class="amount-cell">Total budget</th>
                </tr></thead>
                <tbody id="tax-detail-body"></tbody>
            </table>
        </section>`;
};

window.initTaxCalculatorPage = async function () {
    let activeFY = 2026;
    let drillDept = null;     // null = top-level, otherwise dept code
    let showMore = false;     // true = showing <1% departments tier
    let taxAmount = 0;
    let chart = null;
    let expandedDetailDept = null;  // for table drill-down (mirrors treemap)
    let searchTerm = '';             // program search filter

    // Format "your share" amounts as readable dollars (no abbreviation for personal scale)
    const fmtYour = (amount) => {
        if (amount == null || !isFinite(amount)) return '$0';
        const abs = Math.abs(amount);
        if (abs >= 1 || abs === 0) {
            return '$' + amount.toLocaleString('en-US', { maximumFractionDigits: 2, minimumFractionDigits: 0 });
        }
        // Sub-dollar amounts: show cents
        return '$' + amount.toLocaleString('en-US', { maximumFractionDigits: 2, minimumFractionDigits: 2 });
    };

    const palette = [
        '#4c78a8', '#f58518', '#54a24b', '#e45756', '#72b7b2',
        '#eeca3b', '#b279a2', '#ff9da7', '#9d755d', '#bab0ac',
        '#69b3a2', '#c77dff', '#80b918', '#f4a261', '#2a9d8f',
        '#e76f51', '#457b9d', '#a8dadc', '#ffb4a2', '#b5838d',
        '#606c38', '#bc6c25', '#6a4c93', '#8ecae6',
    ];

    const colorForIndex = (i) => palette[i % palette.length];

    const recompute = () => {
        const { depts, grandTotal } = aggregateByDepartment(activeFY);
        const ratio = grandTotal > 0 ? (taxAmount / grandTotal) : 0;

        renderSummaryCards(depts, grandTotal, ratio);
        renderTreemap(depts, grandTotal, ratio);
        renderDetailTable(depts, grandTotal, ratio);
    };

    const renderSummaryCards = (depts, grandTotal, ratio) => {
        const el = document.getElementById('tax-summary');
        if (!el) return;
        const top3 = depts.slice(0, 3);
        const top3Html = top3.map(d => {
            const pct = grandTotal > 0 ? (d.total / grandTotal * 100) : 0;
            if (taxAmount > 0) {
                const yourDollars = d.total * ratio;
                return `<div class="summary-card dept-summary-card">
                    <div class="amount">${fmtYour(yourDollars)}</div>
                    <div class="label">${d.code} — ${d.name.replace(/^Department of /, '')}</div>
                    <div class="dept-pct-row">
                        <div class="dept-bar-wrap"><div class="dept-bar" style="width:${pct.toFixed(2)}%"></div></div>
                        <span class="dept-pct-label">${pct.toFixed(1)}% of your taxes</span>
                    </div>
                </div>`;
            } else {
                return `<div class="summary-card dept-summary-card">
                    <div class="amount">${pct.toFixed(1)}%</div>
                    <div class="label">${d.code} — ${d.name.replace(/^Department of /, '')}</div>
                    <div class="dept-pct-row">
                        <div class="dept-bar-wrap"><div class="dept-bar" style="width:${pct.toFixed(2)}%"></div></div>
                        <span class="dept-pct-label">of General Fund</span>
                    </div>
                </div>`;
            }
        }).join('');
        const taxPaidCard = taxAmount > 0
            ? `<div class="summary-card"><div class="amount">${fmtYour(taxAmount)}</div><div class="label">Your tax paid</div></div>`
            : `<div class="summary-card empty-state"><div class="amount">—</div><div class="label">Your tax paid</div><div class="card-sub">Enter above ↑</div></div>`;
        el.innerHTML = `
            ${taxPaidCard}
            <div class="summary-card"><div class="amount">${fmtHtml(grandTotal)}</div><div class="label">FY${activeFY} General Fund</div></div>
            ${top3Html}
        `;
    };

    const renderTreemap = (depts, grandTotal, ratio) => {
        const canvas = document.getElementById('tax-treemap');
        if (!canvas || !window.Chart) return;

        // Split departments into main (>=1%) and small (<1%)
        const mainDepts = depts.filter(d => d.total / grandTotal >= 0.01);
        const moreDepts = depts.filter(d => d.total / grandTotal < 0.01);
        const moreTotal = moreDepts.reduce((s, d) => s + d.total, 0);

        // Determine dataset based on current view state
        let tree, isDrill = false, isMore = false;
        if (drillDept) {
            const dept = depts.find(d => d.code === drillDept);
            if (!dept) { drillDept = null; return renderTreemap(depts, grandTotal, ratio); }
            isDrill = true;
            tree = dept.programs.map((p, i) => ({
                code: p.program_id,
                name: p.program_name,
                value: p.total,
                yourShare: p.total * ratio,
                color: colorForIndex(i),
            }));
        } else if (showMore) {
            isMore = true;
            tree = moreDepts.map((d, i) => ({
                code: d.code,
                name: d.name,
                value: d.total,
                yourShare: d.total * ratio,
                color: colorForIndex(mainDepts.length + i),
            }));
        } else {
            // Top-level: main depts + synthetic "More" tile
            tree = mainDepts.map((d, i) => ({
                code: d.code,
                name: d.name,
                value: d.total,
                yourShare: d.total * ratio,
                color: colorForIndex(i),
                isSynthetic: false,
            }));
            if (moreDepts.length > 0) {
                tree.push({
                    code: 'MORE',
                    name: `More (${moreDepts.length} depts <1%)`,
                    value: moreTotal,
                    yourShare: moreTotal * ratio,
                    color: '#adb5bd',
                    isSynthetic: true,
                });
            }
        }

        // Update breadcrumb
        const crumb = document.getElementById('treemap-breadcrumb');
        if (crumb) {
            if (isDrill) {
                const dept = depts.find(d => d.code === drillDept);
                const fromMore = moreDepts.some(d => d.code === drillDept);
                if (fromMore) {
                    crumb.innerHTML = `<span class="crumb-root" data-crumb="root">All departments</span> <span class="crumb-sep">▶</span> <span class="crumb-root" data-crumb="more">More (&lt;1%)</span> <span class="crumb-sep">▶</span> <span class="crumb-current">${drillDept} — ${dept?.name || ''}</span>`;
                } else {
                    crumb.innerHTML = `<span class="crumb-root" data-crumb="root">All departments</span> <span class="crumb-sep">▶</span> <span class="crumb-current">${drillDept} — ${dept?.name || ''}</span>`;
                }
            } else if (isMore) {
                crumb.innerHTML = `<span class="crumb-root" data-crumb="root">All departments</span> <span class="crumb-sep">▶</span> <span class="crumb-current">More (&lt;1%)</span>`;
            } else {
                crumb.innerHTML = `<span class="crumb-root-active">All departments</span>`;
            }
            crumb.querySelectorAll('[data-crumb]').forEach(el => {
                el.addEventListener('click', () => {
                    if (el.dataset.crumb === 'root') { drillDept = null; showMore = false; }
                    if (el.dataset.crumb === 'more') { drillDept = null; showMore = true; }
                    recompute();
                });
            });
        }

        if (chart) { chart.destroy(); chart = null; }

        chart = new Chart(canvas.getContext('2d'), {
            type: 'treemap',
            data: {
                datasets: [{
                    tree: tree,
                    key: 'value',
                    borderWidth: 1,
                    borderColor: '#fff',
                    spacing: 1,
                    backgroundColor: (ctx) => ctx?.raw?._data?.color || '#ccc',
                    labels: {
                        display: true,
                        formatter: (ctx) => {
                            const d = ctx?.raw?._data;
                            if (!d) return '';
                            const shareStr = taxAmount > 0 ? fmtYour(d.yourShare) : fmt(d.value);
                            // Show full name if available, fall back to code
                            const nameStr = d.name && d.name !== d.code ? d.name.replace(/^Department of /, '') : d.code;
                            return [nameStr, shareStr];
                        },
                        color: '#fff',
                        font: { size: 11, weight: '600' },
                        align: 'center',
                        position: 'middle',
                    },
                }],
            },
            options: {
                maintainAspectRatio: false,
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: (items) => {
                                const d = items[0]?.raw?._data;
                                return d ? `${d.code} — ${d.name}` : '';
                            },
                            label: (ctx) => {
                                const d = ctx?.raw?._data;
                                if (!d) return '';
                                const pct = grandTotal > 0 ? (d.value / grandTotal * 100).toFixed(2) : '0';
                                const lines = [
                                    `Total budget: ${fmt(d.value)} (${pct}%)`,
                                ];
                                if (taxAmount > 0) lines.push(`Your share: ${fmtYour(d.yourShare)}`);
                                return lines;
                            },
                        },
                    },
                },
                onClick: (evt, elements) => {
                    if (!elements.length) return;
                    const idx = elements[0].index;
                    const d = chart.data.datasets[0].tree[idx];
                    if (!isDrill && d?.code) {
                        if (d.code === 'MORE') {
                            showMore = true;
                            drillDept = null;
                        } else {
                            drillDept = d.code;
                        }
                        recompute();
                    } else if (isMore && d?.code) {
                        drillDept = d.code;
                        recompute();
                    }
                },
            },
        });
    };

    const renderDetailTable = (depts, grandTotal, ratio) => {
        const body = document.getElementById('tax-detail-body');
        const statusEl = document.getElementById('tax-search-status');
        if (!body) return;

        const q = searchTerm.trim().toLowerCase();
        const isSearching = q.length > 0;

        // Highlight matching text
        const highlight = (text) => {
            if (!isSearching) return text;
            const idx = text.toLowerCase().indexOf(q);
            if (idx === -1) return text;
            return text.slice(0, idx) + `<mark class="search-highlight">${text.slice(idx, idx + q.length)}</mark>` + text.slice(idx + q.length);
        };

        let totalMatchCount = 0;
        const rowsHtml = depts.map(d => {
            const pct = grandTotal > 0 ? (d.total / grandTotal * 100) : 0;
            const your = d.total * ratio;

            if (isSearching) {
                // Filter programs matching query
                const matchedProgs = d.programs.filter(p =>
                    p.program_id.toLowerCase().includes(q) ||
                    p.program_name.toLowerCase().includes(q)
                );
                // Also match if the dept name/code matches
                const deptMatches = d.code.toLowerCase().includes(q) || d.name.toLowerCase().includes(q);
                const progsToShow = deptMatches ? d.programs : matchedProgs;
                if (progsToShow.length === 0) return '';
                totalMatchCount += progsToShow.length;

                let html = `<tr class="tax-dept-row search-dept-header" data-dept="${d.code}">
                    <td><strong>${d.code}</strong> ${d.name}</td>
                    <td class="amount-cell">${pct.toFixed(2)}%</td>
                    <td class="amount-cell"><span class="figure-chip">${fmtYour(your)}</span></td>
                    <td class="amount-cell">${fmt(d.total)}</td>
                </tr>`;
                html += progsToShow.map(p => {
                    const pPct = grandTotal > 0 ? (p.total / grandTotal * 100) : 0;
                    const pYour = p.total * ratio;
                    return `<tr class="tax-prog-row" data-parent="${d.code}">
                        <td class="detail-indent">${highlight(`${p.program_id} ${p.program_name}`)}</td>
                        <td class="amount-cell">${pPct.toFixed(3)}%</td>
                        <td class="amount-cell">${fmtYour(pYour)}</td>
                        <td class="amount-cell">${fmt(p.total)}</td>
                    </tr>`;
                }).join('');
                return html;
            } else {
                // Normal expand/collapse mode
                const isExpanded = expandedDetailDept === d.code;
                const arrow = isExpanded ? '▼' : '▶';
                let html = `<tr class="tax-dept-row" data-dept="${d.code}">
                    <td><span class="dept-arrow">${arrow}</span> <strong>${d.code}</strong> ${d.name}</td>
                    <td class="amount-cell">${pct.toFixed(2)}%</td>
                    <td class="amount-cell"><span class="figure-chip">${fmtYour(your)}</span></td>
                    <td class="amount-cell">${fmt(d.total)}</td>
                </tr>`;
                if (isExpanded) {
                    html += d.programs.map(p => {
                        const pPct = grandTotal > 0 ? (p.total / grandTotal * 100) : 0;
                        const pYour = p.total * ratio;
                        return `<tr class="tax-prog-row" data-parent="${d.code}">
                            <td class="detail-indent"><strong>${p.program_id}</strong> ${p.program_name}</td>
                            <td class="amount-cell">${pPct.toFixed(3)}%</td>
                            <td class="amount-cell">${fmtYour(pYour)}</td>
                            <td class="amount-cell">${fmt(p.total)}</td>
                        </tr>`;
                    }).join('');
                }
                return html;
            }
        }).join('');

        body.innerHTML = rowsHtml || `<tr><td colspan="4" class="empty-search">No programs found matching "<strong>${q}</strong>"</td></tr>`;

        if (statusEl) {
            if (isSearching) {
                statusEl.style.display = '';
                statusEl.textContent = totalMatchCount === 0
                    ? `No results for "${q}"`
                    : `${totalMatchCount} program${totalMatchCount !== 1 ? 's' : ''} matching "${q}"`;
            } else {
                statusEl.style.display = 'none';
            }
        }
    };

    // --- Wire up controls ---

    const taxInput = document.getElementById('tax-input');

    // Helper: auto-compute tax from income field and push to tax input
    const autoComputeFromIncome = () => {
        const income = parseFloat(document.getElementById('tax-helper-income')?.value) || 0;
        const filing = document.getElementById('tax-helper-filing')?.value || 'single';
        const autoLabel = document.getElementById('tax-auto-label');
        if (income > 0) {
            const tax = computeHawaiiTax(income, filing);
            if (taxInput) {
                taxInput.value = tax;
                taxAmount = tax;
            }
            if (autoLabel) autoLabel.textContent = '(estimated)';
        } else {
            if (autoLabel) autoLabel.textContent = '';
        }
        recompute();
    };

    document.getElementById('tax-helper-income')?.addEventListener('input', autoComputeFromIncome);
    document.getElementById('tax-helper-filing')?.addEventListener('change', autoComputeFromIncome);

    // Manual override of tax paid field clears the "estimated" label
    taxInput?.addEventListener('input', (e) => {
        taxAmount = parseFloat(e.target.value) || 0;
        const autoLabel = document.getElementById('tax-auto-label');
        if (autoLabel) autoLabel.textContent = '';
        recompute();
    });

    // FY toggle
    document.getElementById('calc-fy-toggle')?.addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-fy]');
        if (!btn) return;
        const fy = parseInt(btn.dataset.fy, 10);
        if (fy === activeFY) return;
        activeFY = fy;
        drillDept = null;
        showMore = false;
        expandedDetailDept = null;
        document.querySelectorAll('#calc-fy-toggle button').forEach(b =>
            b.classList.toggle('active', parseInt(b.dataset.fy, 10) === activeFY));
        recompute();
    });

    // Breadcrumb clicks handled inside renderTreemap via data-crumb attributes

    // Program search
    const searchInput = document.getElementById('tax-program-search');
    const searchClear = document.getElementById('tax-search-clear');
    searchInput?.addEventListener('input', (e) => {
        searchTerm = e.target.value;
        searchClear.style.display = searchTerm ? 'inline-flex' : 'none';
        recompute();
    });
    searchClear?.addEventListener('click', () => {
        searchTerm = '';
        searchInput.value = '';
        searchClear.style.display = 'none';
        searchInput.focus();
        recompute();
    });

    // Detail table expand/collapse per row (disabled while searching)
    document.getElementById('tax-detail-body')?.addEventListener('click', (e) => {
        if (searchTerm) return;  // search mode: rows are already expanded
        const row = e.target.closest('.tax-dept-row');
        if (!row) return;
        const dept = row.dataset.dept;
        expandedDetailDept = (expandedDetailDept === dept) ? null : dept;
        recompute();
    });

    // Initial render
    recompute();
};

// ─────────────────────────────────────────────────────────────────────────
// Stacked-bar popover collision handling
//
// The popover defaults to opening ABOVE the bar (`bottom: 100%`). On the
// first row of any data table, that puts it behind the sticky <thead>. On
// pointer/focus enter we measure the bar against the nearest sticky thead
// (or the viewport top) and flip the popover BELOW the bar when needed.
// ─────────────────────────────────────────────────────────────────────────
(function setupStackedBarPopoverFlip() {
    if (window.__stackedBarFlipBound) return;
    window.__stackedBarFlipBound = true;

    const decideFlip = (wrap) => {
        const pop = wrap.querySelector('.stacked-bar-popover');
        if (!pop) return;
        // Measure popover height even while hidden (visibility:hidden keeps layout).
        const popH = pop.offsetHeight || 180;
        const wrapRect = wrap.getBoundingClientRect();
        // Top-of-content cutoff: bottom edge of nearest sticky thead, else 0.
        const table = wrap.closest('table');
        let cutoff = 0;
        if (table) {
            const thead = table.querySelector('thead');
            if (thead) {
                const tr = thead.getBoundingClientRect();
                cutoff = tr.bottom;
            }
        }
        const projectedTop = wrapRect.top - 8 - popH;
        const wouldClip = projectedTop < cutoff + 4;
        pop.classList.toggle('stacked-bar-popover--below', wouldClip);
    };

    const handler = (e) => {
        const wrap = e.target.closest && e.target.closest('.stacked-bar-wrap');
        if (!wrap) return;
        decideFlip(wrap);
    };

    document.addEventListener('pointerenter', handler, true);
    document.addEventListener('focusin', handler, true);
})();

