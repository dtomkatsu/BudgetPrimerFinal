// ---------------------------------------------------------------------------
// Global data
// ---------------------------------------------------------------------------
let departmentsData = [];
let summaryStats = null;
let programsData = [];
let fyComparisonData = [];
let draftComparisonData = null;       // FY2026 CD1 comparison (HD1→CD1)
let draftComparisonDataFY27 = null;   // FY2027 CD1 comparison (HD1→CD1)
let draftComparisonDataSD1 = null;    // FY2026 SD1 comparison (HD1→SD1)
let draftComparisonDataSD1FY27 = null;// FY2027 SD1 comparison (HD1→SD1)
let projectsDataFY26 = null;          // Section 14 CIP projects FY26 (CD1)
let projectsDataFY27 = null;          // Section 14 CIP projects FY27 (CD1)
let projectsDataSD1FY26 = null;       // Section 14 CIP projects FY26 (SD1)
let projectsDataSD1FY27 = null;       // Section 14 CIP projects FY27 (SD1)
let governorProjectsData = null;      // Governor's supplemental capital projects (S78)
let historicalTrendsData = null;    // 10-year history of biennial budget acts
let obligatedData = null;           // general-fund obligated (fixed) costs FY2018-27

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

// Current-biennium "By Department" detail datasets, keyed by fiscal year.
// FY2026–27 show the enacted supplemental budget (Act 175, SLH 2026 = HB1800
// CD1) with full program detail. Earlier years (FY2016–2025) are totals-only
// from historical_trends.json.
let byDeptDatasets = {};   // { '2026': [...departments], '2027': [...] }
window.loadByDeptDatasets = async function () {
    const files = {
        '2026': 'departments_act175_fy2026.json',
        '2027': 'departments_act175_fy2027.json',
    };
    await Promise.all(Object.entries(files).map(async ([key, fname]) => {
        try {
            const r = await fetch('./js/' + fname + '?v=' + Date.now());
            if (r.ok) byDeptDatasets[key] = await r.json();
            else console.error(`By-dept dataset ${fname}: HTTP ${r.status}`);
        } catch (e) { console.error(`Error loading ${fname}:`, e); }
    }));
    return byDeptDatasets;
};

// General-fund obligated ("fixed") costs FY2018-27, sourced from each biennium's
// Budget in Brief (p.18). Mirrors report2027/manual/obligated_costs.json.
window.loadObligatedCosts = async function () {
    try {
        const r = await fetch('./js/obligated_costs.json?v=' + Date.now());
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        obligatedData = await r.json();
        return obligatedData;
    } catch (e) {
        console.error('Error loading obligated costs:', e);
        return null;
    }
};

// FY2025 actual spending (budgetary basis) by department — ACFR source.
let actualsData = null;
window.loadActuals = async function () {
    try {
        const response = await fetch('./js/actuals_fy2025.json?v=' + Date.now());
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        actualsData = await response.json();
        return actualsData;
    } catch (e) {
        console.error('Error loading actuals:', e);
        return null;
    }
};

window.actualsPage = async function () {
    if (!actualsData || !actualsData.departments) {
        return `
            <section class="compare-page">
                <h2>Actual Spending</h2>
                <div class="empty-state">
                    <p>No actuals data available yet.</p>
                    <p>To generate it, run:</p>
                    <pre>python scripts/extract_actuals.py</pre>
                </div>
            </section>`;
    }
    const m = actualsData.metadata;
    return `
        <section class="compare-page actuals-page">
            <div class="summary-cards-grid" id="actuals-cards"></div>
            <p class="actuals-caveat">FY2025 spending on a <strong>budgetary basis</strong>, combining the
                General Fund and four special revenue funds — i.e. <strong>appropriated funds</strong> under
                legislative budgetary control (excludes federal aid and most special funds). A completed year,
                separate from the FY2026–27 bills. Source:
                <a href="https://ags.hawaii.gov/wp-content/uploads/2026/02/acfr2025.pdf" target="_blank" rel="noopener">${_escHtml(m.source)}</a>.</p>
            <div id="actuals-results"></div>
        </section>`;
};

window.initActualsPage = function () {
    if (!actualsData || !actualsData.departments) return;
    const m = actualsData.metadata;
    let sortCol = 'actual';
    let sortDir = 'desc';

    const arrow = (col) => sortCol === col
        ? `<span class="sort-ind">${sortDir === 'asc' ? '▲' : '▼'}</span>` : '';
    const varClass = (v) => v > 0 ? 'variance-under' : v < 0 ? 'variance-over' : '';
    const varWord = (v) => v > 0 ? 'under' : v < 0 ? 'over' : '';

    const render = () => {
        const rows = [...actualsData.departments].sort((a, b) => {
            let va, vb;
            if (sortCol === 'dept') { va = (a.department_name || '').toLowerCase(); vb = (b.department_name || '').toLowerCase(); }
            else { va = a[sortCol === 'final' ? 'final_budget' : sortCol] || 0; vb = b[sortCol === 'final' ? 'final_budget' : sortCol] || 0; }
            if (typeof va === 'string') return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
            return sortDir === 'asc' ? va - vb : vb - va;
        });

        // Summary cards
        const pctSpent = m.total_final_budget ? (m.total_actual / m.total_final_budget * 100) : 0;
        const cardsEl = document.getElementById('actuals-cards');
        if (cardsEl) cardsEl.innerHTML = `
            <div class="summary-card"><div class="amount">${fmtHtmlCard(m.total_final_budget)}</div><div class="label">Final Budget</div><div class="label-sub">FY2025</div></div>
            <div class="summary-card"><div class="amount">${fmtHtmlCard(m.total_actual)}</div><div class="label">Actually Spent</div><div class="label-sub">${pctSpent.toFixed(0)}% of budget</div></div>
            <div class="summary-card"><div class="amount">${fmtHtmlCard(m.total_variance)}</div><div class="label">Left Unspent</div><div class="label-sub">under budget</div></div>`;

        let body = '<tbody>';
        for (const r of rows) {
            const v = r.variance || 0;
            const chip = r.department_code
                ? `<span class="dept-chip">${r.department_code}</span> ` : '';
            body += `<tr>
                <td>${chip}${highlight(r.department_name || '', '')}</td>
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(r.final_budget)}</span></td>
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(r.actual)}</span></td>
                <td class="amount-cell ${varClass(v)}"><span class="figure-chip">${fmtHtml(Math.abs(v))}</span>${v ? `<span class="var-word">${varWord(v)}${r.pct_variance != null ? ` ${Math.abs(r.pct_variance).toFixed(0)}%` : ''}</span>` : ''}</td>
            </tr>`;
        }
        body += '</tbody>';

        // Totals row
        const tv = m.total_variance || 0;
        const totals = `<tbody class="totals-block"><tr class="totals-row">
            <td>Total <span class="totals-meta">${rows.length} departments</span></td>
            <td class="amount-cell"><span class="figure-chip">${fmtHtml(m.total_final_budget)}</span></td>
            <td class="amount-cell"><span class="figure-chip">${fmtHtml(m.total_actual)}</span></td>
            <td class="amount-cell ${varClass(tv)}"><span class="figure-chip">${fmtHtml(Math.abs(tv))}</span><span class="var-word">${varWord(tv)}</span></td>
        </tr></tbody>`;

        const el = document.getElementById('actuals-results');
        if (el) el.innerHTML = `
            <table class="data-table actuals-table">
                <thead><tr>
                    <th class="sortable" data-sort="dept">Department${arrow('dept')}</th>
                    <th class="sortable amount-cell" data-sort="final">Final Budget${arrow('final')}</th>
                    <th class="sortable amount-cell" data-sort="actual">Actually Spent${arrow('actual')}</th>
                    <th class="sortable amount-cell" data-sort="variance">Variance${arrow('variance')}</th>
                </tr></thead>
                ${body}
                ${totals}
            </table>`;
    };

    render();

    const resultsEl = document.getElementById('actuals-results');
    resultsEl?.addEventListener('click', (e) => {
        const th = e.target.closest('th.sortable');
        if (!th) return;
        const col = th.getAttribute('data-sort');
        if (sortCol === col) sortDir = sortDir === 'asc' ? 'desc' : 'asc';
        else { sortCol = col; sortDir = col === 'dept' ? 'asc' : 'desc'; }
        render();
    });
};

// ---------------------------------------------------------------------------
// School Food Service — revenues vs expenditures (HIDOE, cash basis).
// Linked only from the DOE department page. Source: school_food_service.json.
// ---------------------------------------------------------------------------
let schoolFoodServiceData = null;
window.loadSchoolFoodService = async function () {
    try {
        const response = await fetch('./js/school_food_service.json?v=' + Date.now());
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        schoolFoodServiceData = await response.json();
        return schoolFoodServiceData;
    } catch (e) {
        console.error('Error loading school food service data:', e);
        return null;
    }
};

window.schoolFoodServicePage = async function () {
    if (!schoolFoodServiceData || !schoolFoodServiceData.rows) {
        return `
            <section class="compare-page">
                <a href="#/department/edn" class="back-button">← Back to Department of Education</a>
                <h2>School Food Service</h2>
                <div class="empty-state">
                    <p>No School Food Service data available yet.</p>
                    <pre>python scripts/extract_school_food_service.py</pre>
                </div>
            </section>`;
    }
    const m = schoolFoodServiceData.metadata;
    return `
        <section class="compare-page sfs-page">
            <a href="#/department/edn" class="back-button">← Back to Department of Education</a>
            <div class="department-header">
                <h2>School Food Service — Revenues vs. Expenditures</h2>
                <p class="dept-desc">Hawaiʻi Department of Education school meal programs.</p>
                <div class="sfs-source-card">
                    <span class="sfs-source-icon" aria-hidden="true">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                    </span>
                    <div class="sfs-source-body">
                        <span class="sfs-source-label">Data Source</span>
                        <a class="sfs-source-name" href="https://hawaiipublicschools.org/data-reports/fiscal/" target="_blank" rel="noopener">
                            HIDOE School Food Services
                            <svg class="sfs-source-ext" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
                        </a>
                        <div class="sfs-source-badges">
                            <span class="sfs-badge">${_escHtml(m.fy_range)}</span>
                            <span class="sfs-badge">Cash basis</span>
                            <span class="sfs-badge">As of June 30, 2025</span>
                        </div>
                    </div>
                </div>
            </div>
            <div class="summary-cards-grid" id="sfs-cards"></div>
            <div class="seg-ctrl sfs-fund-ctrl" id="sfs-fund-ctrl">
                <button class="active" data-fund="All">All Funds</button>
                <button data-fund="General">General</button>
                <button data-fund="Federal">Federal</button>
                <button data-fund="Special">Special</button>
            </div>
            <div class="dept-history-chart-wrap"><canvas id="sfs-chart"></canvas></div>
            <div id="sfs-results"></div>
        </section>`;
};

window.initSchoolFoodServicePage = function () {
    if (!schoolFoodServiceData || !schoolFoodServiceData.rows) return;
    const m = schoolFoodServiceData.metadata;
    const years = schoolFoodServiceData.years;
    let fund = 'All';
    let chart = null;

    const row = (fy, fnd) => schoolFoodServiceData.rows.find(r => r.fy === fy && r.fund === fnd);
    const subLine = (cell) => {
        if (cell.payroll == null && cell.other == null) return '';
        const p = cell.payroll || 0, o = cell.other || 0;
        return `<span class="sfs-breakdown">
            <span class="sfs-mini-badge"><span class="sfs-mini-label">Payroll</span><span class="sfs-mini-val">${fmt(p)}</span></span>
            <span class="sfs-mini-badge"><span class="sfs-mini-label">Other</span><span class="sfs-mini-val">${fmt(o)}</span></span>
        </span>`;
    };

    const renderCards = () => {
        const r = row(2025, fund);
        const net = r.net.total || 0;
        const netCls = net >= 0 ? 'positive' : 'negative';
        const netLbl = net >= 0 ? 'surplus' : 'deficit';
        document.getElementById('sfs-cards').innerHTML = `
            <div class="summary-card"><div class="amount">${fmtHtmlCard(r.revenue.total)}</div><div class="label">Revenues</div><div class="label-sub">FY2025 · ${fund}</div></div>
            <div class="summary-card"><div class="amount">${fmtHtmlCard(r.expenditure.total)}</div><div class="label">Expenditures</div><div class="label-sub">FY2025 · ${fund}</div></div>
            <div class="summary-card sfs-net-card ${netCls}"><div class="amount">${fmtHtmlCard(net)}</div><div class="label">Net ${netLbl}</div><div class="label-sub">FY2025</div></div>`;
    };

    const renderChart = () => {
        const canvas = document.getElementById('sfs-chart');
        if (!canvas) return;
        if (chart) chart.destroy();
        const labels = years.map(y => `FY${y}`);
        const rev = years.map(y => row(y, fund).revenue.total || 0);
        const exp = years.map(y => row(y, fund).expenditure.total || 0);
        chart = new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: { labels, datasets: [
                { label: 'Revenues', data: rev, backgroundColor: '#5a7b68', borderWidth: 0 },
                { label: 'Expenditures', data: exp, backgroundColor: '#b07560', borderWidth: 0 },
            ]},
            options: {
                maintainAspectRatio: false, responsive: true,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: true, position: 'top' },
                    tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${fmt(ctx.parsed.y)}` } },
                    datalabels: { display: false },
                },
                scales: {
                    x: { grid: { display: false } },
                    y: { beginAtZero: true, ticks: { callback: (v) => `$${(v / 1e6).toFixed(0)}M` } },
                },
            },
        });
    };

    const renderTable = () => {
        let body = '<tbody>';
        for (const y of years) {
            const r = row(y, fund);
            const net = r.net.total || 0;
            const netCls = net >= 0 ? 'variance-under' : 'variance-over';
            body += `<tr>
                <td><strong>FY${y}</strong></td>
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(r.revenue.total)}</span>${subLine(r.revenue)}</td>
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(r.expenditure.total)}</span>${subLine(r.expenditure)}</td>
                <td class="amount-cell ${netCls}"><span class="figure-chip">${fmtHtml(net)}</span><span class="var-word">${net >= 0 ? 'surplus' : 'deficit'}</span></td>
            </tr>`;
        }
        body += '</tbody>';

        // Cash rollforward (Federal & Special) — only meaningful for those funds / All.
        const cf = schoolFoodServiceData.cash_rollforward || {};
        let cashHtml = '';
        const cashFunds = fund === 'All' ? ['Federal', 'Special'] : (cf[fund] ? [fund] : []);
        if (cashFunds.length) {
            // Sign-prefixed formatter so negatives read "−$3.27 million"
            // rather than the global fmt's "$-3.27 million".
            const fmtSigned = (v) => (v < 0 ? '−' : '') + fmt(Math.abs(v));
            const cards = cashFunds.map((cfn) => {
                const data = cf[cfn];
                const avail = data.available || 0;
                const availCls = avail >= 0 ? 'positive' : 'negative';
                const steps = data.series.map((s) => {
                    const endCls = s.cash_end >= 0 ? 'positive' : 'negative';
                    const netCls = s.net >= 0 ? 'positive' : 'negative';
                    const netSign = s.net >= 0 ? '+' : '−';
                    return `<div class="sfs-cf-step">
                        <span class="sfs-cf-fy">FY${s.fy}</span>
                        <span class="sfs-cf-net ${netCls}">${netSign}${fmt(Math.abs(s.net))}</span>
                        <span class="sfs-cf-end ${endCls}">${fmtSigned(s.cash_end)}</span>
                    </div>`;
                }).join('');
                return `<div class="sfs-cf-card">
                    <div class="sfs-cf-card-head">
                        <span class="sfs-cf-fund">${cfn} Fund</span>
                        <span class="sfs-cf-avail-block">
                            <span class="sfs-cf-avail-label">Available cash (FY2025)</span>
                            <span class="sfs-cf-avail-val ${availCls}">${fmtSigned(avail)}</span>
                        </span>
                    </div>
                    <div class="sfs-cf-steps-head">
                        <span class="sfs-cf-fy">Year</span>
                        <span class="sfs-cf-net">Net change</span>
                        <span class="sfs-cf-end">Year-end cash</span>
                    </div>
                    <div class="sfs-cf-steps">${steps}</div>
                </div>`;
            }).join('');
            cashHtml = `
                <div class="sfs-cash-block">
                    <h3 class="sfs-cash-head">Cash Rollforward</h3>
                    <p class="sfs-cash-intro">Each year's net change carried forward into the year-end cash balance. <strong>Available cash</strong> is the FY2025 year-end balance net of encumbrances.</p>
                    <div class="sfs-cf-grid">${cards}</div>
                </div>`;
        }

        document.getElementById('sfs-results').innerHTML = `
            <table class="data-table sfs-table">
                <thead><tr>
                    <th>Fiscal Year</th>
                    <th class="amount-cell">Revenues</th>
                    <th class="amount-cell">Expenditures</th>
                    <th class="amount-cell">Net</th>
                </tr></thead>
                ${body}
            </table>
            ${cashHtml}
            <ul class="sfs-notes">${(m.notes || []).map(n => `<li>${_escHtml(n)}</li>`).join('')}</ul>`;
    };

    const renderAll = () => { renderCards(); renderChart(); renderTable(); };
    renderAll();

    document.getElementById('sfs-fund-ctrl')?.addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-fund]');
        if (!btn) return;
        fund = btn.getAttribute('data-fund');
        document.querySelectorAll('#sfs-fund-ctrl button').forEach(b => b.classList.toggle('active', b === btn));
        document.getElementById('sfs-fund-ctrl').setAttribute('data-active', fund);
        renderAll();
    });
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
// Per-stage position count, rendered as a small sub-figure under a dollar cell.
// `temp` is the temporary portion of the total `v`; permanent and temporary are
// shown inline (e.g. "10 perm · 1 temp"). Temp is omitted when zero. Returns ''
// for null/0 so programs without positions show nothing extra.
const posChip = (v, temp) => {
    if (v == null || v === '' || Number(v) === 0 || Number.isNaN(Number(v))) return '';
    const total = Math.round(Number(v));
    const t = (temp == null || temp === '' || Number.isNaN(Number(temp))) ? 0 : Math.round(Number(temp));
    const perm = total - t;
    const fmtN = (n) => n.toLocaleString();
    const permPart = `<span class="pos-perm">${fmtN(perm)}<span class="pos-unit">perm</span></span>`;
    const tempPart = t > 0 ? `<span class="pos-sep">·</span><span class="pos-temp">${fmtN(t)}<span class="pos-unit">temp</span></span>` : '';
    return `<span class="pos-sub">${permPart}${tempPart}</span>`;
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

    // ── Multi-year "By Department" page ──────────────────────────────────────
    // Year dropdown over the enacted-budget history (FY2016–FY2027); FY2026–27
    // carry the enacted supplemental (Act 175). Formerly gated behind ?dev.
    // Year selector range — from historical_trends metadata when available,
    // else fall back to FY2026 only.  "Current" detail year (operating /
    // capital / positions / programs) is FY2026; older years show totals
    // sourced from the historical series.
    const meta   = historicalTrendsData?.metadata || null;
    const fyMin  = meta?.fy_range?.[0] ?? 2026;
    const fyMax  = meta?.fy_range?.[1] ?? 2026;

    // FY options — newest first, one entry per year. FY2026–27 carry the
    // enacted supplemental (Act 175) figures; earlier years are totals-only.
    // Default = FY2026 (first year of the current biennium).
    const yearOptions = [];
    for (let y = fyMax; y >= fyMin; y--) {
        yearOptions.push(`<option value="${y}"${y === 2026 ? ' selected' : ''}>FY${y}</option>`);
    }

    const html = `
        <section class="home-page">
            <div class="context-banner">
                <strong>Enacted budgets by department.</strong> Pick a fiscal year below.
                FY2016–FY2025 show department totals from each year's enacted appropriations act.
                FY2026–27 reflect the enacted supplemental budget (Act 175, SLH 2026 — the same
                figures the HB1800 tab tracks), with full program detail. For how HB1800 moved
                from request to Act 175, see <a href="#/">HB1800 →</a>
            </div>

            <div class="year-picker-bar">
                <span class="year-picker-label">Fiscal year</span>
                <div class="year-picker" role="group" aria-label="Choose fiscal year">
                    <button type="button" class="year-picker-step" id="hb300-fy-prev" aria-label="Previous year">
                        <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
                            <path d="M10 3 L5 8 L10 13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </button>
                    <div class="year-picker-select-wrap">
                        <select id="hb300-fy-select" class="year-picker-select">${yearOptions.join('')}</select>
                        <svg class="year-picker-chev" viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
                            <path d="M3 6 L8 11 L13 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>
                    <button type="button" class="year-picker-step" id="hb300-fy-next" aria-label="Next year">
                        <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
                            <path d="M6 3 L11 8 L6 13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </button>
                </div>
                <span class="year-picker-help" id="hb300-fy-help"></span>
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

            ${obligatedData ? `
            <div class="hb300-history-section obligated-section">
                <div class="hb300-history-head">
                    <h3>Obligated Costs · FY2018–FY2027</h3>
                </div>
                <p class="hb300-history-sub">Non-negotiable general-fund “fixed” costs.</p>
                <div class="hb300-history-chart-wrap"><canvas id="obligated-chart"></canvas></div>
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

// Sage-aligned palette for the fund doughnut + legend (module scope so the
// initial render and the per-year re-render use identical colors).
const DEPT_FUND_PALETTE = [
    '#5a7b68', '#a08e58', '#7d97a3', '#b07560', '#8b6c8e',
    '#6f8d70', '#c2924a', '#5e7d96', '#a87575', '#8b8158',
    '#789689', '#a39378', '#7e93a8', '#b58472', '#928298',
];

// Compute the swappable "detail" parts (program cards, fund legend, doughnut
// data) for a department-detail object — the shape shared by departments.json
// and the Act 175/250 datasets. Used for the initial render AND when the year
// picker switches year, so the program/fund detail tracks the selection.
window.buildDeptDetailParts = function (d) {
    const programs = d.programs || [];
    const total = (d.operating_budget || 0) + (d.capital_budget || 0) + (d.one_time_appropriations || 0);

    // Aggregate by program_id (combine sections/funds).
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

    const fundEntries = Object.entries(d.fund_breakdown || {}).sort(([, a], [, b]) => b - a);
    const fundLegendHtml = fundEntries.map(([fund, amt], i) => {
        const pct = total ? (amt / total * 100) : 0;
        const colour = DEPT_FUND_PALETTE[i % DEPT_FUND_PALETTE.length];
        return `
            <div class="fund-legend-row" data-fund-idx="${i}">
                <span class="fund-legend-swatch" style="background:${colour}"></span>
                <span class="fund-legend-name">${fund}</span>
                <span class="fund-legend-amt">${fmt(amt)}</span>
                <span class="fund-legend-pct">${pct.toFixed(1)}%</span>
            </div>`;
    }).join('');

    // Program cards: id-chip, name, "share of dept" bar, op/cap/positions stats.
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

    const fundData = {
        labels: fundEntries.map(([f]) => f),
        values: fundEntries.map(([, a]) => a),
        colors: fundEntries.map((_, i) => DEPT_FUND_PALETTE[i % DEPT_FUND_PALETTE.length]),
        total,
    };

    return { total, progList, fundEntries, fundLegendHtml, programCardsHtml, fundData };
};

window.departmentDetailPage = async function (params) {
    const deptId = params?.id;
    if (!deptId) return window.notFoundPage();

    const dept = departmentsData.find(d => d.id === deptId);
    if (!dept) return window.notFoundPage();

    // Default view = FY2026 enacted supplemental (Act 175). `dept` (from
    // departmentsData) supplies the header metadata; the budget figures come
    // from the Act 175 FY2026 dataset for this department.
    const detailSrc = (byDeptDatasets['2026'] || []).find(d => d.code === dept.code) || dept;
    const { total, progList, fundEntries, fundLegendHtml, programCardsHtml, fundData } = window.buildDeptDetailParts(detailSrc);
    // Stash fund data for initDepartmentDetailPage's doughnut chart.
    window.__deptFundData = fundData;

    // Historical context — pull this department's 12-yr series if available.
    // The chart and year picker are dev-only; public page shows FY2026 only.
    const histDept = (historicalTrendsData?.by_department || [])
        .find(d => d.dept_code === dept.code);
    const histSection = (histDept) ? `
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

    // Year picker — same component as the home page, scoped to this dept's
    // historical series.  When the user picks an earlier year we recompute
    // the summary cards from historical_trends.json (the FY2026 detail
    // sections below stay static — no dept-level program detail exists
    // for older years).
    const deptYearOptions = (histDept) ? (() => {
        const opts = [];
        const yrs = histDept.series.map(s => s.fy).sort((a, b) => b - a);
        for (const y of yrs) {
            opts.push(`<option value="${y}"${y === 2026 ? ' selected' : ''}>FY${y}</option>`);
        }
        return opts.join('');
    })() : '';
    const deptYearPicker = (histDept) ? `
        <div class="year-picker-bar dept-year-bar">
            <span class="year-picker-label">Fiscal year</span>
            <div class="year-picker" role="group" aria-label="Choose fiscal year">
                <button type="button" class="year-picker-step" id="dept-fy-prev" aria-label="Previous year">
                    <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
                        <path d="M10 3 L5 8 L10 13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </button>
                <div class="year-picker-select-wrap">
                    <select id="dept-fy-select" class="year-picker-select">${deptYearOptions}</select>
                    <svg class="year-picker-chev" viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
                        <path d="M3 6 L8 11 L13 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </div>
                <button type="button" class="year-picker-step" id="dept-fy-next" aria-label="Next year">
                    <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
                        <path d="M6 3 L11 8 L6 13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </button>
            </div>
            <span class="year-picker-help" id="dept-fy-help"></span>
        </div>` : '';

    return `
        <section class="department-detail">
            <a href="#/enacted" class="back-button">← Back to By Department</a>
            <div class="department-header">
                <h2>${dept.name} (${dept.code})</h2>
                ${dept.description ? `<p class="dept-desc">${dept.description}</p>` : ''}
            </div>

            ${dept.code === 'EDN' ? `
            <a href="#/school-food-service" class="sfs-link-card">
                <span class="sfs-link-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="3" y1="21" x2="21" y2="21"/>
                        <rect x="5" y="11" width="3.5" height="8"/>
                        <rect x="10.25" y="6" width="3.5" height="13"/>
                        <rect x="15.5" y="14" width="3.5" height="5"/>
                    </svg>
                </span>
                <span class="sfs-link-text">
                    <strong>School Food Service — Revenues vs. Expenditures</strong>
                    <span class="sfs-link-sub">Cash-basis revenues, expenditures &amp; net by fund, FY2021–FY2025</span>
                </span>
                <span class="sfs-link-arrow">→</span>
            </a>` : ''}

            ${deptYearPicker}

            <div class="summary-cards-grid" id="dept-summary-cards">
                <div class="summary-card"><div class="amount">${fmtHtmlCard(total)}</div><div class="label">Total</div><div class="label-sub">${histDept ? 'FY2026 · Act 175' : 'FY2026'}</div></div>
                <div class="summary-card"><div class="amount">${fmtHtmlCard(detailSrc.operating_budget)}</div><div class="label">Operating</div></div>
                <div class="summary-card"><div class="amount">${fmtHtmlCard(detailSrc.capital_budget)}</div><div class="label">Capital</div></div>
                ${detailSrc.positions ? `<div class="summary-card"><div class="amount">${detailSrc.positions.toLocaleString(undefined,{maximumFractionDigits:0})}</div><div class="label">Positions</div></div>` : ''}
            </div>

            ${histSection}

            <section class="fund-breakdown-section">
                <div class="fund-breakdown-head">
                    <h3>Fund Type Breakdown</h3>
                    <p class="fund-breakdown-sub" id="dept-fund-sub">Where ${dept.code}'s ${histDept ? 'FY2026 · Act 175' : 'FY2026'} budget comes from. ${fundEntries.length} fund type${fundEntries.length === 1 ? '' : 's'}.</p>
                </div>
                <div class="fund-breakdown-body">
                    <div class="fund-doughnut-wrap">
                        <canvas id="fund-doughnut-chart" width="240" height="240"></canvas>
                        <div class="fund-doughnut-center">
                            <span class="fund-doughnut-total" id="dept-fund-center-total">${fmt(total)}</span>
                            <span class="fund-doughnut-total-lbl" id="dept-fund-center-label">Total · ${histDept ? 'FY2026 · Act 175' : 'FY2026'}</span>
                        </div>
                    </div>
                    <div class="fund-legend-list" id="dept-fund-legend">${fundLegendHtml}</div>
                </div>
            </section>

            <section class="programs-section">
                <div class="programs-head">
                    <h3>Programs <span class="programs-count" id="dept-programs-count">${progList.length}</span></h3>
                    <button class="action-link export-btn" id="export-programs">⬇ Export CSV</button>
                </div>
                <div class="programs-legend">
                    <span class="prog-legend-item"><span class="prog-stat-dot prog-stat-op"></span>Operating</span>
                    <span class="prog-legend-item"><span class="prog-stat-dot prog-stat-cap"></span>Capital</span>
                    <span class="prog-legend-item"><span class="prog-stat-dot prog-stat-pos"></span>Positions</span>
                </div>
                <div class="programs-card-list" id="dept-programs-list">
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
        // Export the FY2026 enacted supplemental (Act 175) program detail.
        const src = (byDeptDatasets['2026'] || []).find(d => d.code === dept.code) || dept;
        const rows = (src.programs || []).map(p => ({
            program_id: p.program_id, program_name: p.program_name,
            section: p.section, fund_type: p.fund_type,
            fund_category: p.fund_category, amount: p.amount,
            positions: p.positions || '',
        }));
        downloadCSV(rows, `${deptId}_programs_fy2026.csv`);
    });

    // ---- Fund Type doughnut chart ---------------------------------------
    // Rebuildable: the year picker can swap the program/fund detail to another year,
    // so the doughnut + legend re-render from new fund data.
    const fundCanvas = document.getElementById('fund-doughnut-chart');
    const fmtFund = (v) => {
        if (Math.abs(v) >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
        if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
        if (Math.abs(v) >= 1e3) return `$${(v / 1e3).toFixed(0)}K`;
        return `$${v.toLocaleString()}`;
    };
    let fundChart = null;
    // Legend-row → slice highlight; re-bound after each (re)render.
    const bindFundLegendHover = () => {
        document.querySelectorAll('#dept-fund-legend .fund-legend-row').forEach(row => {
            row.addEventListener('mouseenter', () => {
                if (!fundChart) return;
                const idx = parseInt(row.dataset.fundIdx, 10);
                fundChart.setActiveElements([{ datasetIndex: 0, index: idx }]);
                fundChart.tooltip.setActiveElements([{ datasetIndex: 0, index: idx }],
                    { x: fundCanvas.width / 2, y: fundCanvas.height / 2 });
                fundChart.update();
                document.querySelectorAll('.fund-legend-row.active').forEach(r => r.classList.remove('active'));
                row.classList.add('active');
            });
            row.addEventListener('mouseleave', () => {
                if (!fundChart) return;
                fundChart.setActiveElements([]);
                fundChart.tooltip.setActiveElements([], { x: 0, y: 0 });
                fundChart.update();
                row.classList.remove('active');
            });
        });
    };
    const renderFundChart = (fd) => {
        if (!fundCanvas || typeof Chart === 'undefined' || !fd) return;
        if (fundChart) fundChart.destroy();
        fundChart = new Chart(fundCanvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: fd.labels,
                datasets: [{ data: fd.values, backgroundColor: fd.colors, borderColor: '#fff', borderWidth: 2, hoverOffset: 8 }],
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
                    document.querySelectorAll('.fund-legend-row.active').forEach(r => r.classList.remove('active'));
                    if (elements?.length) {
                        const idx = elements[0].index;
                        document.querySelector(`.fund-legend-row[data-fund-idx="${idx}"]`)?.classList.add('active');
                    }
                },
            },
        });
        bindFundLegendHover();
    };
    renderFundChart(window.__deptFundData);

    // ---- Historical chart + year picker --------------------------------
    // Renders whenever this department has a historical series; bails cleanly
    // (no chart, no picker) when the canvas or data is absent.
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
    const fmtAxis = (v) => Math.abs(v) >= 1e9
        ? `$${(v / 1e9).toFixed(1)}B`
        : `$${(v / 1e6).toFixed(0)}M`;

    let mode = 'nominal';
    let chart = null;

    const renderChart = () => {
        if (chart) chart.destroy();
        // Operating + capital filled areas, stacked.  Stack silhouette =
        // total appropriation per FY for this department.
        const opData  = histDept.series.map(s => mode === 'real'
            ? s.operating_real  : s.operating_nominal);
        const capData = histDept.series.map(s => mode === 'real'
            ? s.capital_real    : s.capital_nominal);
        const hasCapital = capData.some(v => v > 0);

        const datasets = [
            {
                label: 'Operating',
                data: opData,
                borderColor: '#5a7b68',
                backgroundColor: 'rgba(90, 123, 104, 0.55)',
                tension: 0.25,
                fill: 'origin',
                borderWidth: 1.6,
                pointRadius: 3, pointHoverRadius: 6,
                pointBackgroundColor: '#5a7b68',
            },
        ];
        if (hasCapital) {
            datasets.push({
                label: 'Capital',
                data: capData,
                borderColor: '#a08e58',
                backgroundColor: 'rgba(160, 142, 88, 0.55)',
                tension: 0.25,
                fill: '-1',
                borderWidth: 1.6,
                pointRadius: 3, pointHoverRadius: 6,
                pointBackgroundColor: '#a08e58',
            });
        }

        chart = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: { labels, datasets },
            options: {
                maintainAspectRatio: false,
                responsive: true,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: hasCapital, position: 'top', labels: { boxWidth: 14 } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${fmtBillions(ctx.parsed.y)}`,
                            footer: (items) => {
                                if (items.length < 2) return '';
                                const sum = items.reduce((s, it) => s + (it.parsed.y || 0), 0);
                                return `Total: ${fmtBillions(sum)}`;
                            },
                        },
                    },
                    datalabels: { display: false },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        stacked: true,
                        ticks: { callback: fmtAxis },
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

    // ---- Dept-page year picker -----------------------------------------
    // Drives the summary cards.  FY2026 is the only year with the full
    // operating/capital/positions detail (sourced from departments.json);
    // earlier and projected years collapse to a Total card pulled from the
    // historical series for this department.
    const deptSel  = document.getElementById('dept-fy-select');
    const deptPrev = document.getElementById('dept-fy-prev');
    const deptNext = document.getElementById('dept-fy-next');
    const deptHelp = document.getElementById('dept-fy-help');
    const cardsWrap = document.getElementById('dept-summary-cards');
    if (!deptSel || !cardsWrap) return;

    // Locate this department inside a current-biennium (Act 175) dataset,
    // keyed by fiscal year. baseDept = FY2026 Act 175 (the detail-section
    // fallback for totals-only historical years).
    const deptIn = (fy) => (byDeptDatasets[String(fy)] || []).find(d => d.code === dept.code) || null;
    const baseDept = deptIn(2026) || dept;

    const renderDeptCards = (fy) => {
        const seriesEntry = histDept.series.find(s => s.fy === fy);
        const detailDept = (fy === 2026 || fy === 2027) ? deptIn(fy) : null;
        if (detailDept) {
            const op  = detailDept.operating_budget || 0;
            const cap = detailDept.capital_budget || 0;
            const tot = op + cap + (detailDept.one_time_appropriations || 0);
            const pos = detailDept.positions;
            cardsWrap.innerHTML = `
                <div class="summary-card"><div class="amount">${fmtHtmlCard(tot)}</div><div class="label">Total</div><div class="label-sub">FY${fy} · Act 175</div></div>
                <div class="summary-card"><div class="amount">${fmtHtmlCard(op)}</div><div class="label">Operating</div></div>
                <div class="summary-card"><div class="amount">${cap > 0 ? fmtHtmlCard(cap) : '<span class="fmt-num">—</span>'}</div><div class="label">Capital</div></div>
                ${pos ? `<div class="summary-card"><div class="amount">${pos.toLocaleString(undefined,{maximumFractionDigits:0})}</div><div class="label">Positions</div></div>` : ''}`;
            if (deptHelp) deptHelp.textContent = '';
        } else if (seriesEntry) {
            // Use historical op/cap split (added by the new aggregator)
            const totalNom = seriesEntry.nominal;
            const opNom = seriesEntry.operating_nominal;
            const capNom = seriesEntry.capital_nominal;
            cardsWrap.innerHTML = `
                <div class="summary-card"><div class="amount">${fmtHtmlCard(totalNom)}</div><div class="label">Total</div><div class="label-sub">FY${fy}</div></div>
                <div class="summary-card"><div class="amount">${fmtHtmlCard(opNom)}</div><div class="label">Operating</div></div>
                <div class="summary-card"><div class="amount">${capNom > 0 ? fmtHtmlCard(capNom) : '<span class="fmt-num">—</span>'}</div><div class="label">Capital</div></div>`;
            if (deptHelp) {
                deptHelp.textContent = `FY${fy} totals from the corresponding biennial appropriations act. Program and fund detail below reflect FY2026 · Act 175.`;
            }
        } else {
            cardsWrap.innerHTML = `
                <div class="summary-card"><div class="amount">—</div><div class="label">Total</div><div class="label-sub">FY${fy}</div></div>`;
            if (deptHelp) deptHelp.textContent = `No data for FY${fy}.`;
        }
    };

    // Swap the program cards + fund breakdown to the selected year's data.
    // FY2016–2025 have no per-year program detail, so they fall back to the
    // FY2026 · Act 175 base (the summary card note explains this).
    const updateDetailSections = (fy) => {
        const dd = (fy === 2026 || fy === 2027) ? deptIn(fy) : null;
        const detailDept = dd || baseDept;
        const labelText = dd ? `FY${fy} · Act 175` : 'FY2026 · Act 175';
        const parts = window.buildDeptDetailParts(detailDept);
        const set = (id, html, prop = 'innerHTML') => { const el = document.getElementById(id); if (el) el[prop] = html; };
        set('dept-fund-legend', parts.fundLegendHtml);
        set('dept-programs-list', parts.programCardsHtml);
        set('dept-programs-count', String(parts.progList.length), 'textContent');
        set('dept-fund-sub', `Where ${dept.code}'s ${labelText} budget comes from. ${parts.fundEntries.length} fund type${parts.fundEntries.length === 1 ? '' : 's'}.`, 'textContent');
        set('dept-fund-center-total', fmt(parts.total), 'textContent');
        set('dept-fund-center-label', `Total · ${labelText}`, 'textContent');
        renderFundChart(parts.fundData);
    };

    const syncDeptStepperButtons = () => {
        const idx = deptSel.selectedIndex;
        const last = deptSel.options.length - 1;
        if (deptPrev) deptPrev.disabled = idx <= 0;
        if (deptNext) deptNext.disabled = idx >= last;
    };

    deptSel.addEventListener('change', () => {
        const fy = parseInt(deptSel.value, 10);
        if (!Number.isFinite(fy)) return;
        renderDeptCards(fy);
        updateDetailSections(fy);
        syncDeptStepperButtons();
    });
    deptPrev?.addEventListener('click', () => {
        if (deptSel.selectedIndex <= 0) return;
        deptSel.selectedIndex -= 1;
        deptSel.dispatchEvent(new Event('change'));
    });
    deptNext?.addEventListener('click', () => {
        if (deptSel.selectedIndex >= deptSel.options.length - 1) return;
        deptSel.selectedIndex += 1;
        deptSel.dispatchEvent(new Event('change'));
    });

    syncDeptStepperButtons();
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
            <a href="#/enacted" class="back-button">← Back to By Department</a>
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
                <p class="about-lead">This dashboard tracks <strong>HB1800</strong>, Hawaiʻi's supplemental appropriations bill for the FY 2026–2027 biennium. It follows the bill from the Governor's request through the House Draft (HD1), Senate Draft (SD1), and Conference Draft (CD1) to show how proposed spending changed through the legislative process. On June 26, 2026 the Governor signed the bill into law as <strong>Act 175</strong> with no line-item vetoes, so the Enacted budget matches CD1.</p>
                <p class="about-lead">The <strong>By Department</strong> tab shows enacted appropriations by department across fiscal years 2016–2027. A year picker steps through each year's enacted budget; FY2026–27 reflect the enacted supplemental (<strong>Act 175</strong>, SLH 2026 — the same figures the HB1800 tab tracks), with full program-level detail. It provides the multi-year context for what HB1800 changed.</p>
                <hr style="margin: 1.5rem 0; border: none; border-top: 1px solid #ddd;">
            </div>

            <div class="about-section">
                <h3>What are HD1, CD1, and Enacted?</h3>
                <p><strong>HD1</strong> is the bill as amended by the House. <strong>SD1</strong> is the Senate's version. <strong>CD1</strong> is the Conference Committee's final version, passed by both chambers. <strong>Enacted</strong> is the bill as signed into law (Act 175, June 26, 2026) — the Governor signed CD1 without any line-item vetoes, so the enacted figures are identical to CD1. Comparing the stages reveals which programs gained or lost funding along the way.</p>
            </div>

            <div class="about-section">
                <h3>Features</h3>
                <ul>
                    <li>HD1 vs CD1 draft comparison with Operating/Capital breakdown</li>
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
        const [r26, r27, rGov, r26sd1, r27sd1] = await Promise.all([
            fetch('./js/projects_fy26.json?v=' + Date.now()).catch(() => null),
            fetch('./js/projects_fy27.json?v=' + Date.now()).catch(() => null),
            fetch('./js/governor_projects.json?v=' + Date.now()).catch(() => null),
            fetch('./js/projects_fy26_sd1.json?v=' + Date.now()).catch(() => null),
            fetch('./js/projects_fy27_sd1.json?v=' + Date.now()).catch(() => null),
        ]);
        if (r26 && r26.ok) projectsDataFY26 = await r26.json();
        if (r27 && r27.ok) projectsDataFY27 = await r27.json();
        if (rGov && rGov.ok) governorProjectsData = await rGov.json();
        if (r26sd1 && r26sd1.ok) projectsDataSD1FY26 = await r26sd1.json();
        if (r27sd1 && r27sd1.ok) projectsDataSD1FY27 = await r27sd1.json();
        return { fy26: projectsDataFY26, fy27: projectsDataFY27, gov: governorProjectsData };
    } catch (e) {
        console.warn('Projects data not available:', e.message);
        return null;
    }
};

// Merge amount_sd1 from the HD1→SD1 comparison into matching records of the
// HD1→CD1 comparison.  Match key uses the same identity columns the parser
// uses (program_id + dept + fund_type + fund_category + section + category).
// Records with no SD1 match keep amount_sd1 == null (rendered as em-dash).
function _mergeSD1Amounts(cdData, sdData) {
    if (!cdData || !cdData.comparisons || !sdData || !sdData.comparisons) return;
    const keyOf = r => [
        r.program_id || '', r.department_code || '', r.fund_type || '',
        r.fund_category || '', r.section || '', r.category || '',
    ].join('|');
    const sdMap = new Map();
    for (const r of sdData.comparisons) sdMap.set(keyOf(r), { amt: r.amount_sd1, pos: r.positions_sd1, posTemp: r.positions_temp_sd1 });
    for (const r of cdData.comparisons) {
        const v = sdMap.get(keyOf(r));
        if (v !== undefined) {
            r.amount_sd1 = v.amt;
            r.positions_sd1 = v.pos;
            r.positions_temp_sd1 = v.posTemp;
        }
    }
    // Append SD1-only records (programs SD1 changed that CD1 dropped or didn't touch)
    const cdKeys = new Set(cdData.comparisons.map(keyOf));
    for (const r of sdData.comparisons) {
        if (cdKeys.has(keyOf(r))) continue;
        cdData.comparisons.push({
            program_id: r.program_id, department_code: r.department_code,
            fund_type: r.fund_type, fund_category: r.fund_category,
            section: r.section, category: r.category,
            program_name: r.program_name, department_name: r.department_name,
            amount_hd1: r.amount_hd1, amount_sd1: r.amount_sd1, amount_cd1: null,
            positions_hd1: r.positions_hd1, positions_sd1: r.positions_sd1, positions_cd1: null,
            positions_temp_hd1: r.positions_temp_hd1, positions_temp_sd1: r.positions_temp_sd1, positions_temp_cd1: null,
            change: 0, pct_change: null, change_type: 'unchanged_in_cd1',
        });
    }
}

window.loadDraftComparison = async function () {
    try {
        const [r26, r27, r26sd1, r27sd1] = await Promise.all([
            fetch('./js/draft_comparison_fy26.json?v=' + Date.now()),
            fetch('./js/draft_comparison_fy27.json?v=' + Date.now()),
            fetch('./js/draft_comparison_fy26_sd1.json?v=' + Date.now()).catch(() => null),
            fetch('./js/draft_comparison_fy27_sd1.json?v=' + Date.now()).catch(() => null),
        ]);
        if (r26.ok) draftComparisonData = await r26.json();
        if (r27.ok) draftComparisonDataFY27 = await r27.json();
        if (r26sd1 && r26sd1.ok) draftComparisonDataSD1 = await r26sd1.json();
        if (r27sd1 && r27sd1.ok) draftComparisonDataSD1FY27 = await r27sd1.json();
        _mergeSD1Amounts(draftComparisonData, draftComparisonDataSD1);
        _mergeSD1Amounts(draftComparisonDataFY27, draftComparisonDataSD1FY27);
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

// First sentence of a department description, for tight hover surfaces that can't
// hold the full paragraph (e.g. the homepage cards' .has-tooltip box). A few
// departments (PSD, LAW) open with reorg/creation history rather than what they
// do, so skip that opener to the next sentence. Returns '' for empty descriptions.
const _REORG_OPENER = /formerly|was renamed|authorized the creation|during the \d{4} session/i;
function deptSummary(description) {
    const text = String(description || '').trim();
    if (!text) return '';
    const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
    let first = sentences[0].trim();
    if (_REORG_OPENER.test(first) && sentences[1]) first = sentences[1].trim();
    return first;
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
    if (row.amount_cd1 != null) sd = row.amount_cd1;
    else if (row.amount_sd1 != null) sd = row.amount_sd1;
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
        ? `Conference added ${short} vs House`
        : `Conference cut ${short} vs House`;
    return ` <span class="hd-sd-pill ${dirClass}" title="${_escAttr(tipText)}">CD ${sign}${short} <span class="hd-sd-pill-meta">vs HD</span></span>`;
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
        const vsLabel = klass === 'cd1' ? 'vs HD' : 'vs CD';
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
    const sdSection = buildSection('Conference', sd, sdAmt, 'cd1', sdDelta);
    // House on top when both — chronological order (House drafts first,
    // Senate amends).  When only one chamber has text, just show that one.
    return header + hdSection + sdSection;
}

// Build the Governor's-Message popover for a Gov's Request cell.  Reads the
// detail items + concurrence status (from extract_governor_message.py) off
// the cell's data-* attrs.  Mirrors the reason popover's card structure.
function _buildGovPopoverHtml(cell) {
    const detail = cell.getAttribute('data-gov') || '';
    if (!detail) return '';
    const title = cell.getAttribute('data-gov-title') || '';
    const programId = cell.getAttribute('data-program-id') || '';
    const programName = cell.getAttribute('data-program-name') || '';
    const items = _bulletizeReason(detail)
        .map(s => `<li>${_escHtml(_softCaseReason(s))}.</li>`).join('');
    const titleHtml = title
        ? `<p class="gov-pop-title">${_escHtml(_softCaseReason(title))}</p>` : '';
    const header = programId
        ? `<div class="reason-pop-header">
             <strong>${_escHtml(programId)}</strong>
             <span class="reason-pop-prog-name">${_escHtml(programName)}</span>
           </div>` : '';
    return `${header}<div class="reason-section reason-gov">
        <div class="reason-chamber-label">Governor's Request</div>
        ${titleHtml}<ul class="reason-list">${items}</ul>
    </div>`;
}

// Build the CD1 "crossed out" popover — the Governor's-Message items the
// Legislature declined to fund, rendered struck through.
function _buildGovCutPopoverHtml(cell) {
    const detail = cell.getAttribute('data-cut') || '';
    if (!detail) return '';
    const title = cell.getAttribute('data-cut-title') || '';
    const programId = cell.getAttribute('data-program-id') || '';
    const programName = cell.getAttribute('data-program-name') || '';
    const items = _bulletizeReason(detail)
        .map(s => `<li><s>${_escHtml(_softCaseReason(s))}.</s></li>`).join('');
    const titleHtml = title
        ? `<p class="gov-pop-title"><s>${_escHtml(_softCaseReason(title))}</s></p>` : '';
    const header = programId
        ? `<div class="reason-pop-header">
             <strong>${_escHtml(programId)}</strong>
             <span class="reason-pop-prog-name">${_escHtml(programName)}</span>
           </div>` : '';
    return `${header}<div class="reason-section reason-govcut">
        <div class="reason-chamber-label gov-cut-label">Crossed out in CD1</div>
        <p class="gov-cut-note">Requested by the Governor, not funded by the Legislature:</p>
        ${titleHtml}<ul class="reason-list gov-cut-list">${items}</ul>
    </div>`;
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
        target.closest('.has-reason') || target.closest('.has-purpose')
        || target.closest('.has-gov') || target.closest('.has-govcut');

    const show = (cell) => {
        if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
        if (activeCell === cell) return;
        const html = cell.classList.contains('has-purpose')
            ? _buildPurposePopoverHtml(cell)
            : cell.classList.contains('has-govcut')
                ? _buildGovCutPopoverHtml(cell)
                : cell.classList.contains('has-gov')
                    ? _buildGovPopoverHtml(cell)
                    : _buildReasonPopoverHtml(cell);
        if (!html) return;
        // Tag popover type so CSS can style accordingly
        pop.dataset.popType = cell.classList.contains('has-purpose') ? 'purpose'
            : cell.classList.contains('has-govcut') ? 'govcut'
            : cell.classList.contains('has-gov') ? 'gov' : 'reason';
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
// Department Breakdown Hover Card
// ---------------------------------------------------------------------------

// Build the inner HTML for the dept-level change breakdown card.
// Groups programs into Transfers / Increases / Reductions; skips unchanged.
// Pre-computed at render time and stored in data-dept-bd="..." so the card
// just reads the attribute on mouseenter — no runtime state lookup needed.
function buildDeptBreakdownHTML(deptCode, deptName, programs, splitProgramsMap) {
    const fmt = (v) => {
        const sign = v < 0 ? '−' : v > 0 ? '+' : '';
        const abs = Math.abs(v);
        if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}B`;
        if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(2)}M`;
        if (abs >= 1e3) return `${sign}$${Math.round(abs / 1e3)}K`;
        return `${sign}$${abs.toLocaleString()}`;
    };
    const fmtAbs = (v) => {
        const a = Math.abs(v);
        if (a >= 1e9) return `$${(a / 1e9).toFixed(2)}B`;
        if (a >= 1e6) return `$${(a / 1e6).toFixed(2)}M`;
        if (a >= 1e3) return `$${Math.round(a / 1e3)}K`;
        return `$${a.toLocaleString()}`;
    };

    const transfers = [], increases = [], reductions = [];
    for (const p of programs) {
        if (!p.change) continue;
        if (p.isTransfer) transfers.push(p);
        else if (p.change > 0) increases.push(p);
        else reductions.push(p);
    }
    const byAbs = (a, b) => Math.abs(b.change) - Math.abs(a.change);
    transfers.sort(byAbs); increases.sort(byAbs); reductions.sort(byAbs);

    // Split transfers by direction so we can render two distinct sub-sections
    // (Moving OUT / Moving IN) instead of one mixed bucket.
    const transfersOut = transfers.filter(p => p.change < 0);
    const transfersIn  = transfers.filter(p => p.change > 0);

    // Group transfer rows by counterpart dept (via splitProgramsMap). The result
    // is an array of [counterpartLabel, programs[]] entries, sorted by gross size.
    const groupByCounterpart = (bucket) => {
        const groups = new Map();
        for (const p of bucket) {
            const sm = splitProgramsMap ? splitProgramsMap.get(p.program_id) : null;
            const counterparts = sm ? [...sm.keys()].filter(d => d !== deptCode) : [];
            const key = counterparts.length ? counterparts.join(', ') : '—';
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key).push(p);
        }
        const entries = [...groups.entries()];
        entries.forEach(([, v]) => v.sort(byAbs));
        entries.sort((a, b) => {
            const sa = a[1].reduce((s, p) => s + Math.abs(p.change || 0), 0);
            const sb = b[1].reduce((s, p) => s + Math.abs(p.change || 0), 0);
            return sb - sa;
        });
        return entries;
    };

    // Single row: PID chip · name · amount (right-rail, tabular) · destination.
    // Transfer rows pick up a directional class (`-xfer-out` / `-xfer-in`) so the
    // CSS can paint a colored left edge — peripheral cue that mirrors the prose
    // "to/from DEPT" label. Rows carry data-jump-* attributes so a click jumps
    // to the matching row in the main table (handler in init...CardHandlers).
    const renderRow = (p, cls, opts = {}) => {
        const splitMap = splitProgramsMap ? splitProgramsMap.get(p.program_id) : null;
        const dest = splitMap ? [...splitMap.keys()].filter(d => d !== deptCode) : [];
        const isXfer = !!p.isTransfer;
        const xferDir = isXfer ? (p.change < 0 ? 'out' : 'in') : '';
        const destPrefix = xferDir === 'out' ? 'to' : xferDir === 'in' ? 'from' : '';
        // Hide dest in grouped transfer sections — counterpart already shown in subgroup head.
        const destStr = (!opts.hideDest && dest.length)
            ? `${destPrefix ? destPrefix + ' ' : ''}${dest.join(', ')}`
            : '';
        const rawName = p.program_name || '';
        const shortName = rawName.length > 40 ? rawName.slice(0, 38) + '…' : rawName;
        const rowCls = xferDir      ? `dept-bd-row dept-bd-row-xfer-${xferDir}`
                     : cls === 'positive' ? 'dept-bd-row dept-bd-row-pos'
                     : cls === 'negative' ? 'dept-bd-row dept-bd-row-neg'
                     : 'dept-bd-row';
        return `<div class="${rowCls} dept-bd-row-clickable" role="button" tabindex="0"
                     data-jump-dept="${_escAttr(deptCode)}"
                     data-jump-prog="${_escAttr(p.program_id)}"
                     aria-label="Jump to ${_escAttr(p.program_id)} in the table">
            <span class="dept-bd-pid">${_escHtml(p.program_id)}</span>
            <span class="dept-bd-name" title="${_escAttr(rawName)}">${_escHtml(shortName)}</span>
            <span class="dept-bd-amt ${cls}">${fmt(p.change)}</span>
            ${destStr ? `<span class="dept-bd-dest">${_escHtml(destStr)}</span>` : '<span></span>'}
        </div>`;
    };

    // Section: header (icon + label + subtotal) followed by rows. Used for
    // Increases and Reductions — straight list, no counterpart grouping.
    const ICONS = { up: '▲', down: '▼', xferOut: '↗', xferIn: '↙' };
    const renderSection = (label, iconKey, bucket, cls) => {
        if (!bucket.length) return '';
        const subtotal = bucket.reduce((s, p) => s + (p.change || 0), 0);
        return `<div class="dept-bd-section">
            <div class="dept-bd-section-head">
                <span class="dept-bd-section-icon dept-bd-icon-${iconKey}">${ICONS[iconKey]}</span>
                <span class="dept-bd-section-label">${label}</span>
                <span class="dept-bd-section-total ${cls}">${fmt(subtotal)}</span>
            </div>
            ${bucket.map(p => renderRow(p, cls)).join('')}
        </div>`;
    };

    // Transfer section: section header + counterpart sub-groups + rows.
    // `prefix` is the prose label ("to" / "from") shown on each subgroup head.
    const renderTransferSection = (label, iconKey, bucket, prefix) => {
        if (!bucket.length) return '';
        const grossTotal = bucket.reduce((s, p) => s + Math.abs(p.change || 0), 0);
        let html = `<div class="dept-bd-section dept-bd-section-xfer-${iconKey === 'xferOut' ? 'out' : 'in'}">
            <div class="dept-bd-section-head">
                <span class="dept-bd-section-icon dept-bd-icon-${iconKey}">${ICONS[iconKey]}</span>
                <span class="dept-bd-section-label">${label}</span>
                <span class="dept-bd-section-total transferred">${fmtAbs(grossTotal)}</span>
            </div>`;
        for (const [counterpart, progs] of groupByCounterpart(bucket)) {
            const groupTotal = progs.reduce((s, p) => s + Math.abs(p.change || 0), 0);
            const word = progs.length === 1 ? 'program' : 'programs';
            html += `<div class="dept-bd-subgroup">
                <div class="dept-bd-subgroup-head">
                    <span class="dept-bd-subgroup-label">${_escHtml(prefix)} <span class="dept-bd-subgroup-dept">${_escHtml(counterpart)}</span></span>
                    <span class="dept-bd-subgroup-meta">${fmtAbs(groupTotal)} · ${progs.length} ${word}</span>
                </div>
                ${progs.map(p => renderRow(p, 'transferred', { hideDest: true })).join('')}
            </div>`;
        }
        html += `</div>`;
        return html;
    };

    // Header: dept chip + dept name, then the department's description (same copy
    // the detail page shows at line ~1004). Empty for county pass-throughs and the
    // few departments without a description — omit the line in that case.
    const deptDesc = (departmentsData.find(d => d.code === deptCode) || {}).description || '';
    let html = `<div class="dept-bd-header">
        <span class="dept-bd-dept-chip">${_escHtml(deptCode)}</span>
        <span class="dept-bd-dept-name" title="${_escAttr(deptName)}">${_escHtml(deptName)}</span>
    </div>`;
    if (deptDesc) html += `<p class="dept-bd-desc">${_escHtml(deptDesc)}</p>`;

    // Body: real changes first, then transfers split into OUT and IN sections.
    let body = '';
    body += renderSection('Increases', 'up', increases, 'positive');
    body += renderSection('Reductions', 'down', reductions, 'negative');
    body += renderTransferSection('Moving OUT', 'xferOut', transfersOut, 'to');
    body += renderTransferSection('Moving IN',  'xferIn',  transfersIn,  'from');
    if (!body) {
        body = `<div class="dept-bd-empty">No program-level changes</div>`;
    }
    html += `<div class="dept-bd-body">${body}</div>`;

    // Sticky footer: net change (excl. transfers)
    const realNet = programs.reduce((s, p) => s + (p.isTransfer ? 0 : (p.change || 0)), 0);
    const netCls = realNet > 0 ? 'positive' : realNet < 0 ? 'negative' : '';
    html += `<div class="dept-bd-net">
        <span class="dept-bd-net-label">Net Change</span>
        <span class="dept-bd-net-value ${netCls}">${fmt(realNet)}</span>
    </div>`;

    return html;
}

function _ensureDeptBreakdownCard() {
    let card = document.getElementById('dept-breakdown-card');
    if (card) return card;
    card = document.createElement('div');
    card.id = 'dept-breakdown-card';
    card.setAttribute('role', 'tooltip');
    card.style.display = 'none';
    document.body.appendChild(card);
    return card;
}

// One-time wire-up of delegated hover handlers for the dept change cell.
// Idempotent: a flag on the body prevents double-binding on re-renders.
// Card is interactive (no pointer-events: none) so users can scroll its
// internal contents — that's why hide is delayed and cancelled when the
// mouse moves into the card itself.
function initDeptBreakdownCardHandlers() {
    if (document.body.dataset.deptBdBound === '1') return;
    document.body.dataset.deptBdBound = '1';
    const card = _ensureDeptBreakdownCard();
    let activeCell = null;
    let hideTimer = null;

    const show = (cell) => {
        if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
        if (activeCell === cell) return;
        activeCell = cell;
        card.innerHTML = cell.getAttribute('data-dept-bd') || '';
        // Reset scroll position to top whenever a new dept is shown
        card.scrollTop = 0;
        _positionReasonPopover(card, cell);
    };
    const hideSoon = () => {
        if (hideTimer) clearTimeout(hideTimer);
        hideTimer = setTimeout(() => {
            card.style.display = 'none';
            activeCell = null;
            hideTimer = null;
        }, 120);
    };
    const cancelHide = () => {
        if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
    };

    document.addEventListener('mouseover', (e) => {
        const cell = e.target.closest('[data-dept-bd]');
        if (cell) {
            show(cell);
        } else if (e.target.closest('#dept-breakdown-card')) {
            cancelHide();
        }
    });
    document.addEventListener('mouseout', (e) => {
        const cell = e.target.closest('[data-dept-bd]');
        const inCard = card.contains(e.relatedTarget);
        if (cell && !cell.contains(e.relatedTarget) && !inCard) {
            hideSoon();
        } else if (e.target.closest('#dept-breakdown-card') &&
                   !inCard &&
                   (!activeCell || !activeCell.contains(e.relatedTarget))) {
            hideSoon();
        }
    });

    // Click on a row inside the card → jump to the matching row in the main
    // table. The page-level handler (window._deptBdJumpToRow) lives in
    // initDraftComparePage's closure where it can mutate expandedDepts and
    // trigger render(). Keyboard (Enter/Space) gets the same treatment so the
    // tooltip is operable without a mouse.
    const tryJump = (target) => {
        const row = target?.closest?.('[data-jump-prog]');
        if (!row) return false;
        const dept = row.getAttribute('data-jump-dept');
        const prog = row.getAttribute('data-jump-prog');
        if (typeof window._deptBdJumpToRow !== 'function') return false;
        // Hide card BEFORE jumping so it doesn't follow scroll/render.
        card.style.display = 'none';
        activeCell = null;
        window._deptBdJumpToRow(dept, prog);
        return true;
    };
    card.addEventListener('click', (e) => {
        if (tryJump(e.target)) {
            e.preventDefault();
            e.stopPropagation();
        }
    });
    card.addEventListener('keydown', (e) => {
        if (e.key !== 'Enter' && e.key !== ' ') return;
        if (tryJump(e.target)) {
            e.preventDefault();
            e.stopPropagation();
        }
    });

    // Hide on page scroll (but NOT on scroll inside the card — that bubbles
    // to document via wheel events but doesn't fire window 'scroll').
    window.addEventListener('scroll', () => {
        if (activeCell) { card.style.display = 'none'; activeCell = null; }
    }, { passive: true });
    window.addEventListener('resize', () => {
        if (activeCell) { card.style.display = 'none'; activeCell = null; }
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
            <div class="compare-scope-row">
                <span class="compare-scope-label">Viewing</span>
                ${fyToggle}
            </div>
            <div class="compare-controls-bar">
                <!-- Mobile-only stage picker. Hidden ≥640px (the dots are the
                     toggle on desktop). Pinned via position:sticky so it stays
                     put while the timeline scrolls horizontally beneath it.
                     Each chip proxies the matching hidden #tl-* checkbox, so
                     all downstream state (col-*-inactive, captions, URL
                     persistence, scroll fades) flows from the existing change
                     event — no separate state machine. -->
                <div class="tl-stage-picker" role="group" aria-label="Choose which budget stages to compare">
                    <button type="button" class="tl-stage-chip" data-node="gov">Gov.</button>
                    <button type="button" class="tl-stage-chip" data-node="hd1">HD1</button>
                    <button type="button" class="tl-stage-chip" data-node="sd1">SD1</button>
                    <button type="button" class="tl-stage-chip" data-node="cd1">CD1</button>
                    <button type="button" class="tl-stage-chip" data-node="enacted">Enacted</button>
                </div>
                <div class="compare-timeline" id="compare-timeline">
                    <!-- Row 1: column labels -->
                    <div class="tl-corner tl-corner-labels"></div>
                    <span class="tl-label has-tooltip" data-col="gov" data-row="labels" data-tooltip="The original budget proposed by the Governor">Gov.</span>
                    <span class="tl-label has-tooltip" data-col="hd1" data-row="labels" data-tooltip="The House version of the budget bill">HD1</span>
                    <span class="tl-label has-tooltip" data-col="sd1" data-row="labels" data-tooltip="The Senate version of the budget bill">SD1</span>
                    <span class="tl-label has-tooltip" data-col="cd1" data-row="labels" data-tooltip="The budget agreed on by the House and Senate.">CD1</span>
                    <span class="tl-label has-tooltip" data-col="enacted" data-row="labels" data-tooltip="Signed into law by the Governor as Act 175 on June 26, 2026 — identical to CD1 (no line-item vetoes).">Enacted</span>
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
                    <div class="tl-dot-row" data-col="cd1" data-row="dots">
                        <span class="tl-seg tl-seg-before"></span>
                        <label class="tl-dot-lbl" for="tl-cd1"><span class="tl-dot"></span></label>
                        <span class="tl-seg tl-seg-after"></span>
                    </div>
                    <div class="tl-dot-row" data-col="enacted" data-row="dots">
                        <span class="tl-seg tl-seg-before"></span>
                        <label class="tl-dot-lbl" for="tl-enacted"><span class="tl-dot"></span></label>
                        <span class="tl-seg tl-seg-after"></span>
                    </div>
                    <div class="tl-net-spark-row" data-col="net" data-row="dots">
                        <svg class="tl-net-spark" id="tl-net-spark" viewBox="0 0 60 20" aria-hidden="true"></svg>
                    </div>

                    <!-- Row 3: total amounts; caret sits in the left rail -->
                    <div class="tl-corner tl-corner-caret">
                        <button class="tl-expand-btn" id="tl-expand-btn" aria-expanded="false" aria-label="Show operating and capital breakdown">
                            <span class="tl-expand-kicker">Breakdown</span>
                            <span class="tl-expand-caret" aria-hidden="true"><svg width="12" height="12" viewBox="0 0 12 12"><path d="M2.5 4.25 6 7.75l3.5-3.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
                        </button>
                    </div>
                    <span class="tl-amt" id="tl-amt-gov" data-col="gov" data-row="totals"></span>
                    <span class="tl-amt" id="tl-amt-hd1" data-col="hd1" data-row="totals"></span>
                    <span class="tl-amt" id="tl-amt-sd1" data-col="sd1" data-row="totals"></span>
                    <span class="tl-amt" id="tl-amt-cd1" data-col="cd1" data-row="totals"></span>
                    <span class="tl-amt" id="tl-amt-enacted" data-col="enacted" data-row="totals"></span>
                    <span class="tl-amt tl-net-chip" id="tl-amt-net" data-col="net" data-row="totals"></span>

                    <!-- Row 4: context captions — the totals all round to the same
                         $23.1B, so the captions carry the story (anchor word /
                         stage-to-stage delta / destination word / net scope). -->
                    <span class="tl-sub" id="tl-sub-gov" data-col="gov" data-row="subs"></span>
                    <span class="tl-sub" id="tl-sub-hd1" data-col="hd1" data-row="subs"></span>
                    <span class="tl-sub" id="tl-sub-sd1" data-col="sd1" data-row="subs"></span>
                    <span class="tl-sub" id="tl-sub-cd1" data-col="cd1" data-row="subs"></span>
                    <span class="tl-sub" id="tl-sub-enacted" data-col="enacted" data-row="subs"></span>
                    <span class="tl-sub" id="tl-sub-net" data-col="net" data-row="subs"></span>

                    <!-- Row 4: Operating breakdown (toggled).
                         The .tl-band spans all columns and paints the
                         zebra tint as one continuous rectangle regardless
                         of per-cell width. Values sit above it via z-index. -->
                    <div class="tl-band" data-row="op" hidden></div>
                    <div class="tl-bd-label has-tooltip" data-row="op" data-tooltip="The operating budget pays for the state&rsquo;s ongoing, day-to-day services like salaries, programs, and utilities each year." hidden><span class="tl-bd-name-full">Operating</span><span class="tl-bd-name-abbr">Op.</span><span class="tl-bd-share" id="tl-bd-share-op"></span></div>
                    <span class="tl-bd-cell" id="tl-bd-op-gov" data-col="gov" data-row="op" hidden></span>
                    <span class="tl-bd-cell" id="tl-bd-op-hd1" data-col="hd1" data-row="op" hidden></span>
                    <span class="tl-bd-cell" id="tl-bd-op-sd1" data-col="sd1" data-row="op" hidden></span>
                    <span class="tl-bd-cell" id="tl-bd-op-cd1" data-col="cd1" data-row="op" hidden></span>
                    <span class="tl-bd-cell" id="tl-bd-op-enacted" data-col="enacted" data-row="op" hidden></span>
                    <span class="tl-bd-cell" id="tl-bd-op-net" data-col="net" data-row="op" hidden></span>

                    <!-- Row 5: Capital breakdown (toggled) -->
                    <div class="tl-band" data-row="cap" hidden></div>
                    <div class="tl-bd-label has-tooltip" data-row="cap" data-tooltip="The capital budget pays for building and fixing long-term physical projects like schools, roads, and other facilities." hidden><span class="tl-bd-name-full">Capital</span><span class="tl-bd-name-abbr">Cap.</span><span class="tl-bd-share" id="tl-bd-share-cap"></span></div>
                    <span class="tl-bd-cell" id="tl-bd-cap-gov" data-col="gov" data-row="cap" hidden></span>
                    <span class="tl-bd-cell" id="tl-bd-cap-hd1" data-col="hd1" data-row="cap" hidden></span>
                    <span class="tl-bd-cell" id="tl-bd-cap-sd1" data-col="sd1" data-row="cap" hidden></span>
                    <span class="tl-bd-cell" id="tl-bd-cap-cd1" data-col="cd1" data-row="cap" hidden></span>
                    <span class="tl-bd-cell" id="tl-bd-cap-enacted" data-col="enacted" data-row="cap" hidden></span>
                    <span class="tl-bd-cell" id="tl-bd-cap-net" data-col="net" data-row="cap" hidden></span>

                    <!-- Hidden checkboxes (state toggles; labels for these are the dots above) -->
                    <input type="checkbox" class="tl-cb" id="tl-gov" checked>
                    <input type="checkbox" class="tl-cb" id="tl-hd1">
                    <input type="checkbox" class="tl-cb" id="tl-sd1">
                    <input type="checkbox" class="tl-cb" id="tl-cd1">
                    <input type="checkbox" class="tl-cb" id="tl-enacted" checked>
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
    initDeptBreakdownCardHandlers();
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
    // Timeline state: defaults to just the endpoints (Gov → Enacted) so the
    // summary bar is uncluttered; HD1/SD1/CD1 are off by default but easy to
    // toggle on via the dots. The Enacted stage (Act 175, signed 6/26/2026)
    // is CD1 signed into law with no line-item vetoes, so it reuses the
    // amount_cd1 figures throughout — there is no separate enacted dataset.
    let govActive = true;
    let hd1Active = false;
    let sd1Active = false;
    let cd1Active = false;
    let enactedActive = true;
    let showBreakdown = false; // whether Op/Cap sub-chips are visible under each node

    // --- URL state persistence ---
    // Key filter state is encoded into the hash query string so views can be shared.
    // Example: #/?fy=27&q=airport&mode=decreases&sort=change&dir=desc
    // Uses history.replaceState (no popstate fired) so router never re-navigates.
    const readUrlState = () => {
        const qs = (typeof window._routeQueryString !== 'undefined')
            ? window._routeQueryString
            : (window.location.hash.split('?')[1] || '');
        const p = new URLSearchParams(qs);
        return {
            fy:    p.get('fy')    || '26',
            q:     p.get('q')    || '',
            mode:  p.get('mode') || 'all',
            sort:  p.get('sort') || 'change',
            dir:   p.get('dir')  || 'asc',
            nodes: p.get('nodes') || 'gov,enacted',
        };
    };
    const syncUrlState = () => {
        const fy = activeData === draftComparisonDataFY27 ? '27' : '26';
        const q    = document.getElementById('draft-search')?.value || '';
        const mode = document.getElementById('draft-filter')?.value || 'all';
        const activeNodes = [govActive && 'gov', hd1Active && 'hd1', sd1Active && 'sd1', cd1Active && 'cd1', enactedActive && 'enacted']
            .filter(Boolean).join(',');
        const p = new URLSearchParams();
        if (fy   !== '26')               p.set('fy',    fy);
        if (q)                           p.set('q',     q);
        if (mode !== 'all')              p.set('mode',  mode);
        if (sortCol !== 'change')        p.set('sort',  sortCol);
        if (sortDir !== 'asc')           p.set('dir',   sortDir);
        if (activeNodes !== 'gov,enacted') p.set('nodes', activeNodes);
        const qs = p.toString();
        history.replaceState(null, '', '#/' + (qs ? '?' + qs : ''));
    };
    // Read URL on init; pending values applied on the first render call
    const _initState = readUrlState();
    let pendingQ    = _initState.q;
    let pendingMode = _initState.mode !== 'all' ? _initState.mode : '';
    // Apply URL sort state immediately
    sortCol = _initState.sort;
    sortDir = _initState.dir;
    // Apply URL FY state
    if (_initState.fy === '27' && draftComparisonDataFY27) {
        activeData    = draftComparisonDataFY27;
        activeProjects = projectsDataFY27;
    }
    // Apply URL timeline nodes
    {
        const ns = new Set(_initState.nodes.split(','));
        govActive = ns.has('gov');
        hd1Active = ns.has('hd1');
        sd1Active = ns.has('sd1');
        cd1Active = ns.has('cd1');
        enactedActive = ns.has('enacted');
    }

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
        const posKey = dataset.metadata.fiscal_year === 2026 ? 'positions_fy2026' : 'positions_fy2027';
        const posTempKey = dataset.metadata.fiscal_year === 2026 ? 'positions_temp_fy2026' : 'positions_temp_fy2027';
        // Governor's Message mid-session amendments count toward the Gov's
        // Request — fold the signed GM delta into the baseline amount.
        const gmKey = dataset.metadata.fiscal_year === 2026 ? 'gm_delta_fy2026' : 'gm_delta_fy2027';
        for (const r of dataset.comparisons) {
            const match = baselineLookup.get(`${r.department_code}_${r.program_id}_${r.fund_type}_${r.section}`);
            r.amount_baseline = match ? ((match[fyKey] || 0) + (match[gmKey] || 0)) : 0;
            r.positions_baseline = match ? (match[posKey] ?? null) : null;
            r.positions_temp_baseline = match ? (match[posTempKey] ?? null) : null;
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
        const posKey = dataset.metadata.fiscal_year === 2026 ? 'positions_fy2026' : 'positions_fy2027';
        const posTempKey = dataset.metadata.fiscal_year === 2026 ? 'positions_temp_fy2026' : 'positions_temp_fy2027';
        const gmKey = dataset.metadata.fiscal_year === 2026 ? 'gm_delta_fy2026' : 'gm_delta_fy2027';
        const hd1Key = 'amount_' + dataset.metadata.draft1.toLowerCase();
        const sd1Key = 'amount_' + dataset.metadata.draft2.toLowerCase();
        const present = new Set();
        for (const r of dataset.comparisons) {
            present.add(`${r.department_code}_${r.program_id}_${r.fund_type}_${r.section}`);
        }
        for (const g of governorRequestData) {
            const key = `${g.department_code}_${g.program_id}_${g.fund_type}_${g.section}`;
            if (present.has(key)) continue;
            const amt = (g[fyKey] || 0) + (g[gmKey] || 0);
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
                amount_sd1: 0,
                positions_hd1: null,
                positions_sd1: null,
                positions_cd1: null,
                positions_temp_hd1: null,
                positions_temp_sd1: null,
                positions_temp_cd1: null,
                change: 0,
                pct_change: 0,
                change_type: 'removed',
                amount_baseline: amt,
                positions_baseline: g[posKey] ?? null,
                positions_temp_baseline: g[posTempKey] ?? null,
                _govOrphan: true,
            });
        }
    };
    if (draftComparisonData) injectOrphans(draftComparisonData);
    if (draftComparisonDataFY27) injectOrphans(draftComparisonDataFY27);

    // Derived getters: leftmost active = d1, rightmost active = d2.
    // The five-stage timeline (Gov → HD1 → SD1 → CD1 → Enacted) means the
    // rightmost active node falls back through Enacted → CD1 → SD1 → HD1 as
    // columns are toggled off. The Enacted stage has no dataset of its own —
    // Act 175 was signed with no line-item vetoes, so it maps to amount_cd1.
    const getD1Key = () => {
        if (govActive) return 'amount_baseline';
        if (hd1Active) return 'amount_hd1';
        if (sd1Active) return 'amount_sd1';
        return 'amount_cd1'; // CD1 or Enacted — same figures
    };
    const getD2Key = () => {
        if (enactedActive) return 'amount_cd1'; // Enacted == CD1
        if (cd1Active) return 'amount_cd1';
        if (sd1Active) return 'amount_sd1';
        if (hd1Active) return 'amount_hd1';
        return 'amount_baseline';
    };
    const getD1Label = () => {
        if (govActive) return "Gov's Request";
        if (hd1Active) return 'HD1';
        if (sd1Active) return 'SD1';
        return cd1Active ? 'CD1' : 'Enacted';
    };
    const getD2Label = () => {
        if (enactedActive) return 'Enacted';
        if (cd1Active) return 'CD1';
        if (sd1Active) return 'SD1';
        if (hd1Active) return 'HD1';
        return "Gov's Request";
    };
    const getChangeLabel = (sortArrowHtml = '') => {
        const from = getD1Label() === "Gov's Request" ? 'Gov.' : getD1Label();
        const to = getD2Label() === "Gov's Request" ? 'Gov.' : getD2Label();
        return `Change${sortArrowHtml}<span class="th-sub">${from} → ${to}</span>`;
    };
    // Position counts (perm+temp) parallel the dollar columns. Each amount key
    // has a matching positions key on the comparison records.
    const POS_KEY = {
        amount_baseline: 'positions_baseline',
        amount_hd1: 'positions_hd1',
        amount_sd1: 'positions_sd1',
        amount_cd1: 'positions_cd1',
    };
    const POS_TEMP_KEY = {
        amount_baseline: 'positions_temp_baseline',
        amount_hd1: 'positions_temp_hd1',
        amount_sd1: 'positions_temp_sd1',
        amount_cd1: 'positions_temp_cd1',
    };
    const posKeyFor = (amountKey) => POS_KEY[amountKey] || null;

    // Governor's Message detail belongs to the Gov's Request column. These
    // helpers only fire when Gov is the d1 column (govActive) and the program
    // has detail. govCellAttrs returns a SINGLE merged class + data-* block
    // (consumed by the .has-gov popover); govFlag renders the in-cell hint and
    // the "not funded" chip.
    const govShows = (p) => !!(p && govActive && getD1Key() === 'amount_baseline' && p.reason_gov);
    const govCellAttrs = (p, baseClass) => {
        if (!govShows(p)) return baseClass ? ` class="${baseClass}"` : '';
        return ` class="${baseClass} has-gov"`
            + ` data-gov-title="${_escAttr(p.reason_gov_title || '')}"`
            + ` data-gov="${_escAttr(p.reason_gov)}"`
            + ` data-gov-concur="${p.gov_not_concur ? '1' : '0'}"`
            + ` data-program-id="${_escAttr(p.program_id || '')}"`
            + ` data-program-name="${_escAttr(p.program_name || '')}"`
            + ` tabindex="0"`;
    };
    const govFlag = (p) => govShows(p)
        ? `<span class="gov-msg-hint" aria-hidden="true">ⓘ</span>` : '';

    // CD1 column: the items the Governor requested that the Legislature crossed
    // out (gov_not_concur). Shows a "✗ cut" hint + a hover listing those items
    // struck through. Only when CD1 is the active d2 column.
    const cd1CutShows = (p) => !!(p && (cd1Active || enactedActive) && getD2Key() === 'amount_cd1'
        && p.gov_not_concur && p.reason_gov);
    const cd1CutCellAttrs = (p, baseClass) => {
        if (!cd1CutShows(p)) return baseClass ? ` class="${baseClass}"` : '';
        return ` class="${baseClass} has-govcut"`
            + ` data-cut="${_escAttr(p.reason_gov)}"`
            + ` data-cut-title="${_escAttr(p.reason_gov_title || '')}"`
            + ` data-program-id="${_escAttr(p.program_id || '')}"`
            + ` data-program-name="${_escAttr(p.program_name || '')}"`
            + ` tabindex="0"`;
    };
    const cd1CutFlag = (p) => cd1CutShows(p)
        ? `<span class="gov-cut-hint" aria-hidden="true">✗ cut</span>` : '';

    // HD1 is a visible middle column only when it is active AND is not itself an endpoint
    const showHD1Col = () => hd1Active && getD1Label() !== 'HD1' && getD2Label() !== 'HD1';
    // SD1 is a visible middle column when it is active AND is not itself an endpoint
    const showSD1Col = () => sd1Active && getD1Label() !== 'SD1' && getD2Label() !== 'SD1';
    // CD1 never renders as a middle column: the only stage after it is Enacted,
    // which carries identical figures (Act 175 = CD1 signed with no vetoes), so
    // a CD1 column beside an Enacted endpoint would duplicate every value.

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

    // Animated count-up for the summary-bar money chips: on value change the
    // number ticks from its previous value to the new one (ease-out cubic,
    // ~550ms) instead of snapping. Keyed per element id so each chip animates
    // independently; an in-flight tick is cancelled when a newer value lands.
    // First paint counts up from $0 as a page-load entrance.
    //
    // `prev` (the last-shown values) persists across page visits on window so
    // the entrance plays once — on the very first load and whenever a value
    // genuinely changes (e.g. the FY toggle) — instead of replaying the
    // $0 → $23B count-up every time the user switches back to this tab, which
    // read as lag. raf/tmo stay per-init so a stale in-flight tick from a prior
    // visit can never blank a freshly rendered chip.
    const _amtAnim = { prev: (window._draftAmtPrev ||= {}), raf: {}, tmo: {} };
    const _reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const setAnimatedAmount = (id, val, toHTML) => {
        const el = document.getElementById(id);
        if (!el) return;
        const from = _amtAnim.prev[id] ?? 0;
        if (from === val) {
            // Same value: leave a running entrance tick alone; otherwise
            // re-render directly (formatting may have changed, e.g. the
            // phone-breakpoint decimal count).
            if (!(id in _amtAnim.raf)) el.innerHTML = toHTML(val);
            return;
        }
        _amtAnim.prev[id] = val;
        if (id in _amtAnim.raf) cancelAnimationFrame(_amtAnim.raf[id]);
        clearTimeout(_amtAnim.tmo[id]);
        const finish = () => {
            delete _amtAnim.raf[id];
            clearTimeout(_amtAnim.tmo[id]);
            delete _amtAnim.tmo[id];
            el.innerHTML = toHTML(val);
        };
        if (_reducedMotion.matches) { finish(); return; }
        const t0 = performance.now(), dur = 550;
        const tick = (t) => {
            const p = Math.min((t - t0) / dur, 1);
            if (p >= 1) { finish(); return; }
            const eased = 1 - Math.pow(1 - p, 3);
            el.innerHTML = toHTML(from + (val - from) * eased);
            _amtAnim.raf[id] = requestAnimationFrame(tick);
        };
        _amtAnim.raf[id] = requestAnimationFrame(tick);
        // rAF never fires while the tab is hidden/backgrounded — without this
        // backstop the chip would sit on its stale value until the next frame.
        _amtAnim.tmo[id] = setTimeout(() => {
            if (id in _amtAnim.raf) { cancelAnimationFrame(_amtAnim.raf[id]); finish(); }
        }, dur + 200);
    };

    const updateSummaryCards = () => {
        const meta = activeData.metadata;
        const d2Key = getD2Key();
        const d2Label = getD2Label();
        const recs = activeData.comparisons;
        const fyKey = meta.fiscal_year === 2026 ? 'amount_fy2026' : 'amount_fy2027';
        const gmKey = meta.fiscal_year === 2026 ? 'gm_delta_fy2026' : 'gm_delta_fy2027';

        const sumBy = (section) => {
            const sr = recs.filter(r => r.section === section);
            const hd1 = sr.reduce((s, r) => s + (r.amount_hd1 || 0), 0);
            const sd1 = sr.reduce((s, r) => s + (r.amount_sd1 || 0), 0);
            const cd1 = sr.reduce((s, r) => s + (r.amount_cd1 || 0), 0);
            const d2 = sr.reduce((s, r) => s + (r[d2Key] || 0), 0);
            // Baseline totals from governorRequestData (full, not joined — avoids missing programs).
            // Includes the Governor's Message mid-session amendments (gm_delta).
            const baseline = (governorRequestData || [])
                .filter(r => r.section === section)
                .reduce((s, r) => s + (r[fyKey] || 0) + (r[gmKey] || 0), 0);
            // d1 is the leftmost active stage's total
            const d1 = govActive ? baseline : (hd1Active ? hd1 : (sd1Active ? sd1 : cd1));
            return { d1, d2, delta: d2 - d1, baseline, hd1, sd1, cd1 };
        };
        const op  = sumBy('Operating');
        const cap = sumBy('Capital Improvement');

        // Totals (always shown in main chips)
        const totGov = op.baseline + cap.baseline;
        const totHD1 = op.hd1 + cap.hd1;
        const totSD1 = op.sd1 + cap.sd1;
        const totCD1 = op.cd1 + cap.cd1;
        const totEnacted = totCD1; // Act 175 == CD1 (signed with no line-item vetoes)
        const totD2  = op.d2 + cap.d2;
        const totD1  = op.d1 + cap.d1;
        const totNet = totD2 - totD1;
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
        if (sd1Active) nodes.push({ val: totSD1, label: 'SD1' });
        if (cd1Active) nodes.push({ val: totCD1, label: 'CD1' });
        if (enactedActive) nodes.push({ val: totEnacted, label: 'Enacted' });

        // Compact format for amounts shown directly under each timeline dot.
        // Phones get one decimal — the second decimal is what pushes the
        // pill row past 375px (a matchMedia listener re-renders on change).
        const dec = window.matchMedia('(max-width: 640px)').matches ? 1 : 2;
        const fmtShort = (n) => {
            if (n == null) return '';
            const abs = Math.abs(n);
            const sign = n < 0 ? '-' : '';
            if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(dec)}B`;
            if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(dec)}M`;
            if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(0)}K`;
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
            { id: 'tl-amt-cd1', val: totCD1 },
            { id: 'tl-amt-enacted', val: totEnacted },
        ].forEach(({ id, val }) => setAnimatedAmount(id, val, fmtShortHTML));

        // Context captions under each pill. Whole millions are enough
        // precision for a caption — the exact figures live in the chips.
        const fmtCaption = (n) => {
            const abs = Math.abs(n), sign = n < 0 ? '−' : '+';
            if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}B`;
            if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(0)}M`;
            if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(0)}K`;
            return `${sign}$${abs.toFixed(0)}`;
        };
        const setSub = (id, text, cls = '') => {
            const el = document.getElementById(id);
            if (el) { el.textContent = text; el.className = 'tl-sub' + (cls ? ' ' + cls : ''); }
        };
        const subCls = (n) => n > 0 ? 'tl-sub-up' : n < 0 ? 'tl-sub-down' : '';

        // ── Connector deltas ──────────────────────────────────────────────
        // Stage-to-stage changes render as dimension lines spanning the gap
        // between consecutive ACTIVE pills (line from pill-center to
        // pill-center, arrowhead into the destination, amount + "Gov. → HD1"
        // kicker breaking the line). The geometry + kicker make the basis of
        // each delta explicit. A muted (toggled-off) stage is skipped — the
        // line passes over its column, spanning the two stages actually being
        // compared. With fewer than 3 active stages the single delta would
        // duplicate the Net Change pill, so no connectors are drawn.
        const stageVals = { gov: totGov, hd1: totHD1, sd1: totSD1, cd1: totCD1, enacted: totEnacted };
        const stageCols = { gov: 3, hd1: 4, sd1: 5, cd1: 6, enacted: 7 };
        const stageLbls = { gov: 'Gov.', hd1: 'HD1', sd1: 'SD1', cd1: 'CD1', enacted: 'Enacted' };
        const tlEl = document.getElementById('compare-timeline');
        tlEl?.querySelectorAll('.tl-delta').forEach(el => el.remove());
        const activeStages = ['gov', 'hd1', 'sd1', 'cd1', 'enacted']
            .filter(n => document.getElementById(`tl-${n}`)?.checked);
        const showDeltas = activeStages.length >= 3;

        // Anchor captions ("baseline" / "final budget") share the subs row with
        // the connector deltas, so they only render when NO deltas are drawn —
        // otherwise the gov/cd1 anchors collide with the first/last delta chips.
        // In the multi-stage view the delta progression IS the caption row.
        setSub('tl-sub-gov', showDeltas ? '' : 'baseline');
        setSub('tl-sub-hd1', '');
        setSub('tl-sub-sd1', '');
        // The "destination" anchor sits under the rightmost active stage:
        // Enacted when it's on, otherwise CD1.
        setSub('tl-sub-cd1', (showDeltas || enactedActive) ? '' : 'final budget', (showDeltas || enactedActive) ? '' : 'tl-sub-final');
        setSub('tl-sub-enacted', (showDeltas || !enactedActive) ? '' : 'became law', (showDeltas || !enactedActive) ? '' : 'tl-sub-final');

        if (tlEl && showDeltas) {
            for (let i = 1; i < activeStages.length; i++) {
                const a = activeStages[i - 1], b = activeStages[i];
                const d = stageVals[b] - stageVals[a];
                const span = document.createElement('span');
                span.className = 'tl-delta';
                span.dataset.row = 'subs';
                const c1 = stageCols[a], c2 = stageCols[b];
                span.style.gridColumn = `${c1} / ${c2 + 1}`;
                // Inset so the hairline runs pill-center to pill-center.
                span.style.setProperty('--tl-ins', `${100 / (2 * (c2 - c1 + 1))}%`);
                const amt = d === 0 ? 'no change' : fmtCaption(d);
                span.innerHTML =
                    `<span class="tl-delta-chip">` +
                    `<span class="tl-delta-amt ${subCls(d)}">${amt}</span>` +
                    `<span class="tl-delta-kicker">${stageLbls[a]} → ${stageLbls[b]}</span>` +
                    `</span>`;
                span.title = `${stageLbls[b]} is ${amt === 'no change' ? 'unchanged' : amt} vs ${stageLbls[a]}`;
                tlEl.appendChild(span);
            }
        }

        // Net caption: percent + scope, stacked in the same chip language as
        // the connector deltas (amount over a "from → to" kicker).
        const fromLbl = getD1Label() === "Gov's Request" ? 'Gov.' : getD1Label();
        const toLbl = getD2Label() === "Gov's Request" ? 'Gov.' : getD2Label();
        const absPct = Math.abs(netPct);
        const pctStr = tabNet === 0 ? '0%'
            : `${tabNet > 0 ? '+' : '−'}${absPct >= 0.01 ? absPct.toFixed(2) : absPct.toFixed(3)}%`;
        const netSubEl = document.getElementById('tl-sub-net');
        if (netSubEl) {
            netSubEl.className = 'tl-sub';
            netSubEl.innerHTML =
                `<span class="tl-delta-chip tl-delta-chip-net">` +
                `<span class="tl-delta-amt">${pctStr}</span>` +
                `<span class="tl-delta-kicker">${fromLbl} → ${toLbl}</span>` +
                `</span>`;
        }

        // Populate per-cell Operating / Capital breakdown values (grid layout).
        // IDs follow the pattern tl-bd-{op|cap}-{gov|hd1|sd1|cd1|net}.
        const signed = (n) => (n > 0 ? '+' : '') + fmtShort(n);
        const cells = [
            { col: 'gov', opV: op.baseline,         capV: cap.baseline,         fmt: fmtShort },
            { col: 'hd1', opV: op.hd1,              capV: cap.hd1,              fmt: fmtShort },
            { col: 'sd1', opV: op.sd1,              capV: cap.sd1,              fmt: fmtShort },
            { col: 'cd1', opV: op.cd1,              capV: cap.cd1,              fmt: fmtShort },
            { col: 'enacted', opV: op.cd1,          capV: cap.cd1,              fmt: fmtShort },
            { col: 'net', opV: op.d2 - op.d1,       capV: cap.d2 - cap.d1,      fmt: signed   },
        ];
        // Two-tone suffix for breakdown values, matching the totals pills.
        // Net cells stay single-tone so the direction color isn't diluted.
        const twoTone = (s) => {
            const m = s.match(/^(-?\$[0-9.]+)([BMK])$/);
            return m ? `${m[1]}<span class="tl-bd-suffix">${m[2]}</span>` : s;
        };
        cells.forEach(({ col, opV, capV, fmt }) => {
            const opEl  = document.getElementById(`tl-bd-op-${col}`);
            const capEl = document.getElementById(`tl-bd-cap-${col}`);
            if (opEl)  opEl.innerHTML  = col === 'net' ? fmt(opV) : twoTone(fmt(opV));
            if (capEl) capEl.innerHTML = col === 'net' ? fmt(capV) : twoTone(fmt(capV));
            // Net cells color by their own sign — Operating can rise while
            // the overall net falls, so the container-level direction class
            // can't drive these.
            if (col === 'net') {
                if (opEl) {
                    opEl.classList.toggle('bd-net-pos', opV > 0);
                    opEl.classList.toggle('bd-net-neg', opV < 0);
                }
                if (capEl) {
                    capEl.classList.toggle('bd-net-pos', capV > 0);
                    capEl.classList.toggle('bd-net-neg', capV < 0);
                }
            }
        });
        // Share-of-total chips on the Operating/Capital row labels, based
        // on the current comparison endpoint (d2).
        const shareTot = op.d2 + cap.d2;
        const opShareEl = document.getElementById('tl-bd-share-op');
        const capShareEl = document.getElementById('tl-bd-share-cap');
        if (opShareEl)  opShareEl.textContent  = shareTot ? `${Math.round(op.d2 / shareTot * 100)}%` : '';
        if (capShareEl) capShareEl.textContent = shareTot ? `${Math.round(cap.d2 / shareTot * 100)}%` : '';
        // Toggle the .show-breakdown class on the timeline; CSS animates the
        // breakdown rows in/out via max-height + opacity transitions on each
        // cell.  We strip the legacy `hidden` attribute that the page HTML
        // ships with so the rows participate in the transition (display:none
        // can't be transitioned).
        const tlCmpForBreakdown = document.getElementById('compare-timeline');
        if (tlCmpForBreakdown) {
            tlCmpForBreakdown.querySelectorAll('[data-row="op"][hidden], [data-row="cap"][hidden]')
                .forEach(el => el.removeAttribute('hidden'));
            tlCmpForBreakdown.classList.toggle('show-breakdown', showBreakdown);
        }

        // Net-direction state — lives on .compare-timeline and cascades
        // to all [data-col="net"] cells (sparkline + chip + breakdown).
        const tlCmp = document.getElementById('compare-timeline');
        if (tlCmp) {
            tlCmp.classList.toggle('net-positive', netCls === 'positive');
            tlCmp.classList.toggle('net-negative', netCls === 'negative');
        }
        // Inline arrow + amount + percentage inside a single chip.
        // The arrow replaces the old circle-in-dot-row marker.
        const netHTML = (n) => {
            const sign = n > 0 ? '+' : '';
            const m = fmtShort(n).match(/^(-?\$[0-9.]+)([BMK]?)$/);
            return m
                ? `<span class="tl-net-val">${sign}${m[1]}</span>` +
                  (m[2] ? `<span class="tl-net-suffix">${m[2]}</span>` : '')
                : `<span class="tl-net-val">${sign}${fmtShort(n)}</span>`;
        };
        setAnimatedAmount('tl-amt-net', tabNet, netHTML);
        // Sparkline: one dot per ACTIVE stage with the last highlighted, so the
        // spark always matches the journey being compared (muted stages don't
        // add phantom kinks). Vertically scales to the range of the plotted
        // totals so visually-tiny deltas still show a slope.
        const spark = document.getElementById('tl-net-spark');
        if (spark) {
            const stageTotals = { gov: totGov, hd1: totHD1, sd1: totSD1, cd1: totCD1, enacted: totEnacted };
            const sparkStages = activeStages.length >= 2 ? activeStages : ['gov', 'enacted'];
            const vs = sparkStages.map(n => stageTotals[n]);
            const mn = Math.min(...vs), mx = Math.max(...vs);
            const range = mx - mn || 1;
            const y = v => (15 - ((v - mn) / range) * 10).toFixed(1);
            const xs = vs.map((_, i) => (6 + 48 * i / (vs.length - 1)).toFixed(1));
            const pts = vs.map((v, i) => `${xs[i]},${y(v)}`).join(' ');
            // pathLength=100 normalizes the polyline for the CSS draw-on
            // animation (stroke-dasharray 100 → dashoffset 100 → 0). Each dot
            // fades in as the line's drawing edge reaches it.
            spark.innerHTML =
                `<polyline class="tl-spark-line" pathLength="100" points="${pts}"/>` +
                vs.map((v, i) => {
                    const end = i === vs.length - 1;
                    const delay = (0.05 + 0.5 * i / (vs.length - 1)).toFixed(2);
                    return `<circle class="tl-spark-dot${end ? ' tl-spark-dot-end' : ''}" cx="${xs[i]}" cy="${y(v)}" r="${end ? 2.7 : 1.7}" style="animation-delay:${delay}s"/>`;
                }).join('');
        }
        // Update expand caret on Gov amount row
        const expandBtn = document.getElementById('tl-expand-btn');
        if (expandBtn) {
            expandBtn.classList.toggle('open', showBreakdown);
            expandBtn.setAttribute('aria-expanded', showBreakdown ? 'true' : 'false');
            expandBtn.setAttribute('aria-label',
                `${showBreakdown ? 'Hide' : 'Show'} operating and capital breakdown`);
        }

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
        // On first render, use URL-persisted values before the DOM elements exist
        const _pq = pendingQ; const _pm = pendingMode;
        pendingQ = ''; pendingMode = '';
        const mode = document.getElementById('draft-filter')?.value || _pm || 'all';
        const q = (document.getElementById('draft-search')?.value || _pq || '').toLowerCase();

        let data = [...activeData.comparisons];

        // Checkbox filters (null = all selected)
        if (checkedSections) data = data.filter(r => checkedSections.has(r.section));
        if (checkedFunds) data = data.filter(r => checkedFunds.has(r.fund_category));

        // Change type filter (applied before search so totalBeforeSearch = post-mode count)
        if (mode === 'modified') data = data.filter(r => r.change_type === 'modified' && r.change !== 0);
        else if (mode === 'increases') data = data.filter(r => (r.change || 0) > 0);
        else if (mode === 'decreases') data = data.filter(r => (r.change || 0) < 0);
        else if (mode === 'added') data = data.filter(r => r.change_type === 'added');
        else if (mode === 'removed') data = data.filter(r => r.change_type === 'removed');

        // Search — applied after mode filter so we can show "X of Y" count
        const totalBeforeSearch = data.length;
        if (q) data = data.filter(r =>
            (r.program_name || '').toLowerCase().includes(q) ||
            (r.program_id || '').toLowerCase().includes(q) ||
            (r.department_name || '').toLowerCase().includes(q));

        // Sort
        const resolveSort = (r) => {
            if (sortCol === 'd1') return r[d1Key] || 0;
            if (sortCol === 'd2') return r[d2Key] || 0;
            if (sortCol === 'hd1') return r[hd1Key] || 0;
            if (sortCol === 'sd1') return r.amount_sd1 || 0;
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
        const filterVal = document.getElementById('draft-filter')?.value || _pm || 'all';
        const searchVal = document.getElementById('draft-search')?.value || _pq || '';
        const searchWasFocused = document.activeElement?.id === 'draft-search';
        const searchSelStart = document.getElementById('draft-search')?.selectionStart;
        const searchSelEnd = document.getElementById('draft-search')?.selectionEnd;
        document.getElementById('draft-summary').innerHTML =
            `<span class="stat-tag stat-tag-neutral items-filter-tag">
                ${q ? `<strong>${data.length}</strong> of ${totalBeforeSearch}` : `<strong>${data.length}</strong>`} programs ▾
                <select id="draft-filter" class="items-filter-select">
                    <option value="all"${filterVal==='all'?' selected':''}>All Changes</option>
                    <option value="modified"${filterVal==='modified'?' selected':''}>Modified Only</option>
                </select>
             </span>`
            + `<input type="text" id="draft-search" class="search-input search-inline" placeholder="Search..." value="${searchVal.replace(/"/g, '&quot;')}">
             <span class="compare-info-icon reading-guide-pill" id="reading-guide-box" tabindex="0">
                 <svg class="rg-info-svg" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.4"/><circle cx="8" cy="4.6" r="0.95" fill="currentColor"/><rect x="7.15" y="6.8" width="1.7" height="5.2" rx="0.6" fill="currentColor"/></svg> How to read this
                 <div class="reading-guide-panel">
                     <p class="reading-guide-summary">Some changes are real cuts/increases; others are <strong>funds reshuffled between depts</strong>.</p>
                     <div class="rg-chips">
                         <p class="rg-chips-title">Chips on a program row</p>
                         <dl class="rg-chips-defs">
                             <dt><span class="pair-chip pair-chip-out" style="pointer-events:none;">→ AGS</span></dt>
                             <dd>moved <em>to</em> that dept</dd>
                             <dt><span class="pair-chip pair-chip-in" style="pointer-events:none;">← BED</span></dt>
                             <dd>moved <em>from</em> that dept</dd>
                             <dt><span class="pair-chip pair-chip-neutral" style="pointer-events:none;">↔ EDN</span></dt>
                             <dd>also under that dept</dd>
                             <dt><span class="data-note" style="pointer-events:none;">⚠</span></dt>
                             <dd>data anomaly (hover)</dd>
                         </dl>
                         <p class="rg-chips-help">Hover a chip to highlight; click to jump.</p>
                     </div>
                     <details class="rg-chips rg-funds">
                         <summary>Fund-chip colors</summary>
                         <dl class="rg-chips-defs rg-funds-defs">
                             <dt><span class="fund-chip" data-fund-cat="General Funds" style="pointer-events:none;">A</span></dt>
                             <dd>State General (tax revenue)</dd>
                             <dt><span class="fund-chip" data-fund-cat="Special Funds" style="pointer-events:none;">B T W</span></dt>
                             <dd>State Dedicated</dd>
                             <dt><span class="fund-chip" data-fund-cat="Federal Funds" style="pointer-events:none;">N P</span></dt>
                             <dd>Federal</dd>
                             <dt><span class="fund-chip" data-fund-cat="General Obligation Bond Fund" style="pointer-events:none;">C E</span></dt>
                             <dd>Borrowed (bond debt)</dd>
                             <dt><span class="fund-chip" data-fund-cat="Interdepartmental Transfers" style="pointer-events:none;">U S R X</span></dt>
                             <dd>Transfers / Other</dd>
                         </dl>
                     </details>
                     <details class="rg-chips rg-funds rg-positions">
                         <summary>Position counts</summary>
                         <dl class="rg-chips-defs rg-positions-defs">
                             <dt><span class="pos-sub" style="margin-top:0;"><span class="pos-perm">26<span class="pos-unit">perm</span></span></span></dt>
                             <dd><strong>Permanent</strong> — ongoing established jobs (FTE)</dd>
                             <dt><span class="pos-sub" style="margin-top:0;"><span class="pos-temp">6<span class="pos-unit">temp</span></span></span></dt>
                             <dd><strong>Temporary</strong> — time-limited, often grant-funded</dd>
                         </dl>
                         <p class="rg-chips-help">Shown under each stage's dollars, so headcount changes track Gov → CD1.</p>
                     </details>
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

        // Build cross-reference map: program_id → Map<deptCode, {d1, d2, delta}>
        // Must be built before depts sort so realDelta (excl. transfers) can
        // power the change-column sort consistently with the displayed value.
        const splitPrograms = new Map();
        for (const r of activeData.comparisons) {
            const pid = r.program_id;
            const dc  = r.department_code;
            if (!pid || !dc) continue;
            if (!splitPrograms.has(pid)) splitPrograms.set(pid, new Map());
            const sm = splitPrograms.get(pid);
            if (!sm.has(dc)) sm.set(dc, { d1: 0, d2: 0 });
            const entry = sm.get(dc);
            entry.d1 += r[d1Key] || 0;
            entry.d2 += r[d2Key] || 0;
        }
        // Only keep programs that appear in 2+ departments; compute delta
        for (const [pid, sm] of splitPrograms) {
            if (sm.size < 2) { splitPrograms.delete(pid); continue; }
            for (const vals of sm.values()) vals.delta = vals.d2 - vals.d1;
        }

        // Pre-compute dept aggregates, then sort by active sortCol/sortDir.
        // Change sort uses the full dept delta so per-dept rankings match the
        // headline-total reconciliation (sum of dept rows = headline total).
        // Department position total for a stage: dedupe each program's count
        // (positions repeat across a program's fund rows) then sum across the
        // department's programs. Returns null when no program has positions.
        const deptStagePositions = (rows, key) => {
            if (!key) return null;
            const byProg = new Map();
            for (const r of rows) {
                const v = r[key];
                if (v == null || v === '' || Number.isNaN(Number(v))) continue;
                const pid = r.program_id || '';
                const nv = Number(v);
                const cur = byProg.get(pid);
                byProg.set(pid, cur == null ? nv : Math.max(cur, nv));
            }
            if (byProg.size === 0) return null;
            let sum = 0;
            for (const v of byProg.values()) sum += v;
            return sum;
        };
        const depts = [...deptMap.values()].map(d => {
            d.d1 = d.rows.reduce((s, r) => s + (r[d1Key] || 0), 0);
            d.d2 = d.rows.reduce((s, r) => s + (r[d2Key] || 0), 0);
            d.hd1 = d.rows.reduce((s, r) => s + (r[hd1Key] || 0), 0);
            d.sd1 = d.rows.reduce((s, r) => s + (r.amount_sd1 || 0), 0);
            d.posD1  = deptStagePositions(d.rows, posKeyFor(d1Key));
            d.posD2  = deptStagePositions(d.rows, posKeyFor(d2Key));
            d.posHD1 = deptStagePositions(d.rows, 'positions_hd1');
            d.posSD1 = deptStagePositions(d.rows, 'positions_sd1');
            d.posTempD1  = deptStagePositions(d.rows, POS_TEMP_KEY[d1Key]);
            d.posTempD2  = deptStagePositions(d.rows, POS_TEMP_KEY[d2Key]);
            d.posTempHD1 = deptStagePositions(d.rows, 'positions_temp_hd1');
            d.posTempSD1 = deptStagePositions(d.rows, 'positions_temp_sd1');
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
            else { va = a.delta; vb = b.delta; } // change sort uses full dept delta
            if (typeof va === 'string') return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
            return sortDir === 'asc' ? va - vb : vb - va;
        });

        // Per-section and per-fund transfer lookups — same shape as splitPrograms
        // but keyed by "pid|section" and "pid|section|fund" so pair chips and the
        // amber "transferred" style can appear on section rows and fund sub-rows.
        const splitBySection = new Map();
        const splitByFund    = new Map();
        for (const r of activeData.comparisons) {
            const pid = r.program_id, dc = r.department_code;
            if (!pid || !dc || !splitPrograms.has(pid)) continue;
            const sKey = `${pid}|${r.section || ''}`;
            if (!splitBySection.has(sKey)) splitBySection.set(sKey, new Map());
            const sm = splitBySection.get(sKey);
            if (!sm.has(dc)) sm.set(dc, { d1: 0, d2: 0 });
            sm.get(dc).d1 += r[d1Key] || 0;
            sm.get(dc).d2 += r[d2Key] || 0;
            const fKey = `${pid}|${r.section || ''}|${r.fund_category || ''}`;
            if (!splitByFund.has(fKey)) splitByFund.set(fKey, new Map());
            const fm = splitByFund.get(fKey);
            if (!fm.has(dc)) fm.set(dc, { d1: 0, d2: 0 });
            fm.get(dc).d1 += r[d1Key] || 0;
            fm.get(dc).d2 += r[d2Key] || 0;
        }
        for (const [k, m] of splitBySection) {
            if (m.size < 2) { splitBySection.delete(k); continue; }
            for (const v of m.values()) v.delta = v.d2 - v.d1;
        }
        for (const [k, m] of splitByFund) {
            if (m.size < 2) { splitByFund.delete(k); continue; }
            for (const v of m.values()) v.delta = v.d2 - v.d1;
        }

        // Reusable pair-chip builder for program, section, and fund levels.
        // splitMap: Map<dept_code, {delta}> with 2+ entries.
        const buildPairChips = (pid, thisDept, splitMap) => {
            if (!splitMap || splitMap.size < 2) return '';
            const thisDelta = splitMap.get(thisDept)?.delta || 0;
            const SIG = 100_000;
            return [...splitMap.keys()]
                .filter(d => d !== thisDept)
                .map(d => {
                    const od = splitMap.get(d)?.delta || 0;
                    const abs = Math.abs(od);
                    let arrow, cls;
                    if (Math.abs(thisDelta) > SIG && abs > SIG && (thisDelta < 0) !== (od < 0)) {
                        arrow = thisDelta < 0 ? '→' : '←';
                        cls   = thisDelta < 0 ? 'pair-chip-out' : 'pair-chip-in';
                    } else {
                        arrow = '↔'; cls = 'pair-chip-neutral';
                    }
                    const odStr = abs >= 1e9 ? `${od<0?'−':'+'}$${(abs/1e9).toFixed(1)}B`
                                : abs >= 1e6 ? `${od<0?'−':'+'}$${(abs/1e6).toFixed(1)}M`
                                : abs >= 1e3 ? `${od<0?'−':'+'}$${Math.round(abs/1e3)}K`
                                : `${od<0?'−':'+'}$${abs}`;
                    const tip = (`Also under ${d} (${odStr}). Hover to highlight; click to jump.`)
                        .replace(/&/g, '&amp;').replace(/"/g, '&quot;');
                    return `<a class="pair-chip ${cls}" href="javascript:void(0)" data-scroll-dept="${d}" data-pair-key="${pid}" title="${tip}">${arrow}&nbsp;${d}</a>`;
                }).join(' ');
        };

        // "→ AGS" annotation rendered below the delta chip for transferred rows.
        const transferAnnotation = (pid, thisDept, splitMap, deptScopedDelta) => {
            if (!splitMap || splitMap.size < 2 || deptScopedDelta === 0) return '';
            const others = [...splitMap.keys()].filter(d => d !== thisDept);
            if (!others.length) return '';
            const arrow = deptScopedDelta < 0 ? '→' : '←';
            return `<span class="change-transfer-dest">${arrow} ${others.join(', ')}</span>`;
        };

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
            // AGS820: HD1-introduced new program ($360K Operating, fund A,
            // both FY26 and FY27). The bill SD1 carries it through unchanged.
            // The Senate Money Committee Report's published Operating SD1
            // FY26 total ($19,772,640,288) is exactly $360K LESS than a
            // line-by-line sum of Section 13 — the report appears to net
            // AGS820's $360K addition against AGS901's $360K reduction
            // rather than counting both. Our totals reflect the bill's
            // actual line items.
            'AGS820': {
                any: 'AGS820 (Hawaii Broadband and Digital Equity Office) is a new HD1-introduced program at $360K/year (fund A). The Senate Money Committee Report\'s published SD1 FY26 Operating total appears to net AGS820\'s addition against AGS901\'s offsetting $360K reduction rather than counting both — so our line-by-line total will run $360K higher than the Senate report\'s aggregate.'
            },
            // EDN407 FY27 Capital: Section 13 program total ($30M EDN dept
            // fund C) exceeds the sum of Section 14 itemized projects ($25M
            // for HAWAII LIBRARY HEALTH/SAFETY) by $5M. The capital projects
            // table will appear $5M short relative to the main table for this
            // program — a bill drafting inconsistency between the two sections.
            'EDN407': {
                fy27: 'Section 13 program total for EDN407 fund C ($30M FY27) exceeds the sum of Section 14 itemized projects ($25M for HAWAII LIBRARY HEALTH/SAFETY) by $5M. Inconsistency in the bill itself — the project list will appear short by that amount.'
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

        // Positions are a program-level figure that repeats on every fund row,
        // so they are deduped with max() — never summed (that would inflate by the
        // number of fund rows). null means "no position line for this program".
        const maxPos = (a, b) => {
            if (b == null || b === '') return a;
            const nb = Number(b);
            if (Number.isNaN(nb)) return a;
            return a == null ? nb : Math.max(a, nb);
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
                        d1: 0, d2: 0, hd1: 0, sd1: 0, funds: new Set(), sections: new Set(),
                        posBaseline: null, posHd1: null, posSd1: null, posCd1: null,
                        posTempBaseline: null, posTempHd1: null, posTempSd1: null, posTempCd1: null,
                        hasAdded: false, hasRemoved: false, rawRows: [],
                        // Worksheet reasons (from extract_worksheet_reasons.py) live on
                        // every raw row of a program; copy onto the aggregated view so
                        // changeReasonTooltipAttrs(p) can read them at render time.
                        reason_sd_change: r.reason_sd_change || '',
                        reason_hd_change: r.reason_hd_change || '',
                        // Governor's Message detail (extract_governor_message.py) —
                        // surfaced as a tooltip on the Gov's Request cell.
                        reason_gov: r.reason_gov || '',
                        reason_gov_title: r.reason_gov_title || '',
                        gov_not_concur: r.gov_not_concur || false,
                    });
                }
                const p = pMap.get(pid);
                p.d1 += r[d1Key] || 0;
                p.d2 += r[d2Key] || 0;
                p.hd1 += r[hd1Key] || 0;
                p.sd1 += r.amount_sd1 || 0;
                p.posBaseline = maxPos(p.posBaseline, r.positions_baseline);
                p.posHd1 = maxPos(p.posHd1, r.positions_hd1);
                p.posSd1 = maxPos(p.posSd1, r.positions_sd1);
                p.posCd1 = maxPos(p.posCd1, r.positions_cd1);
                p.posTempBaseline = maxPos(p.posTempBaseline, r.positions_temp_baseline);
                p.posTempHd1 = maxPos(p.posTempHd1, r.positions_temp_hd1);
                p.posTempSd1 = maxPos(p.posTempSd1, r.positions_temp_sd1);
                p.posTempCd1 = maxPos(p.posTempCd1, r.positions_temp_cd1);
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
                p.d1DeptScope  = p.d1;
                p.d2DeptScope  = p.d2;
                p.hd1DeptScope = p.hd1;
                p.sd1DeptScope = p.sd1;
                const mySections = new Set(p.rawRows.map(r => r.section));
                p.crossDeptAugmented = new Set(); // other depts pulled in
                for (const r of activeData.comparisons) {
                    if (r.program_id !== p.program_id) continue;
                    if (r.department_code === p.department_code) continue;
                    if (!mySections.has(r.section)) continue;
                    p.d1  += r[d1Key]  || 0;
                    p.d2  += r[d2Key]  || 0;
                    p.hd1 += r[hd1Key] || 0;
                    p.sd1 += r.amount_sd1 || 0;
                    p.posBaseline = maxPos(p.posBaseline, r.positions_baseline);
                    p.posHd1 = maxPos(p.posHd1, r.positions_hd1);
                    p.posSd1 = maxPos(p.posSd1, r.positions_sd1);
                    p.posCd1 = maxPos(p.posCd1, r.positions_cd1);
                    p.posTempBaseline = maxPos(p.posTempBaseline, r.positions_temp_baseline);
                    p.posTempHd1 = maxPos(p.posTempHd1, r.positions_temp_hd1);
                    p.posTempSd1 = maxPos(p.posTempSd1, r.positions_temp_sd1);
                    p.posTempCd1 = maxPos(p.posTempCd1, r.positions_temp_cd1);
                    if (r.fund_category) p.funds.add(r.fund_category);
                    p.rawRows.push(r);
                    p.crossDeptAugmented.add(r.department_code);
                }
            }
            return [...pMap.values()].map(p => {
                // For split programs (same program_id across multiple depts), the
                // cross-dept augmentation makes p.d1/p.d2 the combined total — which
                // nets to $0 change even when one dept lost $49.75M to another.
                // Show the dept-scoped slice instead so the actual movement is visible.
                const isSplit = p.d1DeptScope !== undefined;
                p.change = isSplit
                    ? (p.d2DeptScope  - p.d1DeptScope)
                    : (p.d2 - p.d1);
                p.pct_change = (() => {
                    const base = isSplit ? p.d1DeptScope : p.d1;
                    return base !== 0
                        ? (p.change / Math.abs(base)) * 100
                        : (p.change !== 0 ? 100 : 0);
                })();
                // Display columns: show dept-scoped slice for split programs so the
                // Gov/HD1/SD1 cells are arithmetically consistent with the change cell.
                p.displayD1  = isSplit ? p.d1DeptScope  : p.d1;
                p.displayD2  = isSplit ? p.d2DeptScope  : p.d2;
                p.displayHD1 = isSplit ? p.hd1DeptScope : p.hd1;
                p.displaySD1 = isSplit ? p.sd1DeptScope : p.sd1;
                // Position counts are program-level (not dept-scoped); map each
                // active stage to its deduped count.
                const posOf = (amountKey) => {
                    switch (amountKey) {
                        case 'amount_baseline': return p.posBaseline;
                        case 'amount_hd1': return p.posHd1;
                        case 'amount_sd1': return p.posSd1;
                        case 'amount_cd1': return p.posCd1;
                        default: return null;
                    }
                };
                const posTempOf = (amountKey) => {
                    switch (amountKey) {
                        case 'amount_baseline': return p.posTempBaseline;
                        case 'amount_hd1': return p.posTempHd1;
                        case 'amount_sd1': return p.posTempSd1;
                        case 'amount_cd1': return p.posTempCd1;
                        default: return null;
                    }
                };
                p.posD1  = posOf(getD1Key());
                p.posD2  = posOf(getD2Key());
                p.posHD1 = p.posHd1;
                p.posSD1 = p.posSd1;
                p.posTempD1  = posTempOf(getD1Key());
                p.posTempD2  = posTempOf(getD2Key());
                p.posTempHD1 = p.posTempHd1;
                p.posTempSD1 = p.posTempSd1;
                p.isTransfer = isSplit && p.change !== 0;
                // Use dept-scoped values so split programs that are 100%
                // transferred OUT of this dept (d2DeptScope === 0 here even
                // though augmented p.d2 picked up sibling-dept rows) are
                // correctly tagged 'removed' — drives the badge in the
                // change cell. Non-split programs are unaffected
                // (displayD1/D2 === d1/d2).
                p.change_type = p.hasAdded   && p.displayD1 === 0 ? 'added'
                              : p.hasRemoved && p.displayD2 === 0 ? 'removed'
                              : 'modified';
                p.isMixed = p.sections.size > 1;
                p.section = p.isMixed ? 'Mixed' : [...p.sections][0] || '';
                p.fundLabel = p.funds.size === 1 ? [...p.funds][0] : `${p.funds.size} funds`;
                p.fundShort = p.funds.size === 1 ? shortFund([...p.funds][0]) : `${p.funds.size} funds`;
                p.fundTitle = p.funds.size > 1 ? [...p.funds].join(' · ') : '';
                return p;
            });
        };

        // Sub-row badge: section/fund rows don't carry change_type, so derive
        // the "new" / "removed" label from d1/d2 directly. Same visual as the
        // program-row typeBadge, just computed inline.
        const subRowBadge = (d1, d2) => {
            if ((d1 || 0) > 0 && (d2 || 0) === 0) return '<span class="badge badge-remove">removed</span>';
            if ((d1 || 0) === 0 && (d2 || 0) > 0) return '<span class="badge badge-add">new</span>';
            return '';
        };

        let bodyHtml = '';
        for (const dept of depts) {
            bodyHtml += `<tbody class="dept-block" data-dept-block="${dept.code}">`;
            const deptD1 = dept.d1;
            const deptD2 = dept.d2;
            const deptDelta = dept.delta;
            const isOpen = autoExpand || expandedDepts.has(dept.code);
            const arrow = isOpen ? ' open' : '';

            const programs = aggregatePrograms(dept.rows);

            // Show the FULL dept-level delta on the change cell so per-dept rows
            // sum to the headline total — this matches the Senate Money Committee
            // Report's per-dept "definitive decreases". Earlier we used a "real
            // net" (excluding split/transferred programs), but that hid genuine
            // cuts to depts whose appropriations were redirected to AGS bond
            // financing or county codes (e.g. PSD -$49.75M, BUF -$43M). The
            // hover-card breakdown still itemizes Increases / Reductions /
            // Moved between depts so transfer context isn't lost.
            const xferDelta  = programs.reduce((s, p) => s + (p.isTransfer ? (p.change || 0) : 0), 0);
            const xferGross  = programs.reduce((s, p) => s + (p.isTransfer ? Math.abs(p.change || 0) : 0), 0);
            const deptCls    = deptDelta > 0 ? 'positive' : deptDelta < 0 ? 'negative' : '';
            // If there are transfers, show a small amber badge below the chip
            // (gross moved through this dept; not double-counted in the main number).
            const deptXferNote = xferGross !== 0
                ? `<div><span class="dept-xfer-note">⇄ ${_fmtShort(xferGross)} moved</span></div>`
                : '';

            bodyHtml += `<tr class="dept-group-row${isOpen ? ' open' : ''}" data-dept="${dept.code}">
                <td><span class="dept-arrow${arrow}">▶</span> <span class="dept-chip">${highlight(dept.code, q)}</span> ${highlight(dept.name, q)} <span class="dept-count">(${programs.length} programs)</span></td>
                <td></td><td></td>
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(deptD1)}</span>${posChip(dept.posD1, dept.posTempD1)}</td>
                ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(dept.hd1)}</span>${posChip(dept.posHD1, dept.posTempHD1)}</td>` : ''}
                ${showSD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(dept.sd1)}</span>${posChip(dept.posSD1, dept.posTempSD1)}</td>` : ''}
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(deptD2)}</span>${posChip(dept.posD2, dept.posTempD2)}</td>
                <td class="amount-cell ${deptCls}" data-dept-bd="${_escAttr(buildDeptBreakdownHTML(dept.code, dept.name, programs, splitPrograms))}"><span class="figure-chip">${fmtHtml(deptDelta)}</span>${deptXferNote}</td>
            </tr>`;

            for (const p of programs) {
                const cls = p.isTransfer ? 'transferred'
                    : p.change > 0 ? 'positive' : p.change < 0 ? 'negative' : '';
                const progTransferAnnotation = p.isTransfer
                    ? transferAnnotation(p.program_id, dept.code, splitPrograms.get(p.program_id), p.change)
                    : '';
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
                    const progArrow = progOpen ? ' open' : '';
                    bodyHtml += `<tr class="dept-detail-row prog-group-row change-${p.change_type}${isOpen ? '' : ' hidden'}" data-dept="${dept.code}" data-prog="${progKey}"${pairKeyAttr}>
                        <td class="detail-indent"><span class="dept-arrow${progArrow}">▶</span> <strong${purposeTooltipAttrs(p.program_id)}>${highlight(p.program_id, q)}</strong> ${highlight(p.program_name, q)}${sparklineSvg([p.displayD1, p.displayHD1, p.displayD2])}${pairChips}${dataNoteHtml}</td>
                        <td><span class="section-chip">Mixed</span></td>
                        <td>${p.fundShort ? `<span class="fund-chip${p.fundTitle ? ' fund-chip-multi' : ''}"${p.fundTitle ? ` data-funds="${p.fundTitle}"` : ''}${p.funds.size === 1 ? ` data-fund-cat="${[...p.funds][0]}"` : ''}>${p.fundShort}</span>` : ''}</td>
                        <td${govCellAttrs(p, 'amount-cell')}><span class="figure-chip">${fmtHtml(p.displayD1)}</span>${posChip(p.posD1, p.posTempD1)}${govFlag(p)}</td>
                        ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(p.displayHD1)}</span>${posChip(p.posHD1, p.posTempHD1)}</td>` : ''}
                        ${showSD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(p.displaySD1)}</span>${posChip(p.posSD1, p.posTempSD1)}</td>` : ''}
                        <td${cd1CutCellAttrs(p, 'amount-cell')}><span class="figure-chip">${fmtHtml(p.displayD2)}</span>${posChip(p.posD2, p.posTempD2)}${cd1CutFlag(p)}</td>
                        <td${changeReasonCellAttrs(p, `amount-cell ${cls}`)}><span class="figure-chip">${fmtHtml(p.change)}</span>${typeBadge}${divergenceChipHtml(p)}${progTransferAnnotation}</td>
                    </tr>`;
                    for (const sec of [...p.sections].sort()) {
                        // For split programs rawRows includes sibling-dept rows (pulled in
                        // by the augmentation loop). Filter to this dept only so the section
                        // sub-row shows the dept-scoped amounts, matching the program row.
                        const secRows = p.rawRows.filter(r => r.section === sec && r.department_code === p.department_code);
                        const secD1 = secRows.reduce((s, r) => s + (r[d1Key] || 0), 0);
                        const secD2 = secRows.reduce((s, r) => s + (r[d2Key] || 0), 0);
                        const secHD1 = secRows.reduce((s, r) => s + (r[hd1Key] || 0), 0);
                        const secSD1 = secRows.reduce((s, r) => s + (r.amount_sd1 || 0), 0);
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
                        const secFundArrow = secFundOpen ? ' open' : '';
                        // Section-level transfer detection
                        const secSplitMap = splitBySection.get(`${p.program_id}|${sec}`);
                        const secIsTransfer = !!secSplitMap && secDelta !== 0;
                        const secTransferCls = secIsTransfer ? 'transferred'
                            : secDelta > 0 ? 'positive' : secDelta < 0 ? 'negative' : '';
                        const secPairChips = secSplitMap
                            ? buildPairChips(p.program_id, dept.code, secSplitMap) : '';
                        const secTransferNote = secIsTransfer
                            ? transferAnnotation(p.program_id, dept.code, secSplitMap, secDelta) : '';
                        bodyHtml += `<tr class="prog-section-row${isSecFundGroup ? ' prog-fund-group' : ''}${isOpen && progOpen ? '' : ' hidden'}" data-dept="${dept.code}" data-prog="${progKey}"${isSecFundGroup ? ` data-fund-key="${secFundKey}"` : ''}>
                            <td class="section-indent">${isSecFundGroup ? `<span class="dept-arrow${secFundArrow}">▶</span> ` : ''}${secChipHtml}${secPairChips}</td>
                            <td></td>
                            <td>${secFundLabel ? `<span class="fund-chip${secFundTitle ? ' fund-chip-multi' : ''}"${secFundTitle ? ` data-funds="${secFundTitle}"` : ''}>${secFundLabel}</span>` : ''}</td>
                            <td class="amount-cell"><span class="figure-chip">${fmtHtml(secD1)}</span></td>
                            ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(secHD1)}</span></td>` : ''}
                            ${showSD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(secSD1)}</span></td>` : ''}
                            <td class="amount-cell"><span class="figure-chip">${fmtHtml(secD2)}</span></td>
                            <td class="amount-cell ${secTransferCls}"><span class="figure-chip">${fmtHtml(secDelta)}</span>${subRowBadge(secD1, secD2)}${secTransferNote}</td>
                        </tr>`;
                        if (isSecFundGroup) {
                            const byFund = new Map();
                            for (const r of secRows) {
                                const fc = r.fund_category || '(unknown)';
                                if (!byFund.has(fc)) byFund.set(fc, { d1: 0, d2: 0, hd1: 0, sd1: 0 });
                                const f = byFund.get(fc);
                                f.d1  += r[d1Key]  || 0;
                                f.d2  += r[d2Key]  || 0;
                                f.hd1 += r[hd1Key] || 0;
                                f.sd1 += r.amount_sd1 || 0;
                            }
                            for (const [fc, f] of byFund) {
                                const fDelta = f.d2 - f.d1;
                                const fPct = f.d1 !== 0 ? ((f.d2 - f.d1) / Math.abs(f.d1)) * 100 : (f.d2 !== 0 ? 100 : 0);
                                const fSplitMap = splitByFund.get(`${p.program_id}|${sec}|${fc}`);
                                const fIsTransfer = !!fSplitMap && fDelta !== 0;
                                const fCls = fIsTransfer ? 'transferred'
                                    : fDelta > 0 ? 'positive' : fDelta < 0 ? 'negative' : '';
                                const fPairChips = fSplitMap
                                    ? buildPairChips(p.program_id, dept.code, fSplitMap) : '';
                                const fTransferNote = fIsTransfer
                                    ? transferAnnotation(p.program_id, dept.code, fSplitMap, fDelta) : '';
                                bodyHtml += `<tr class="prog-fund-row${isOpen && progOpen && secFundOpen ? '' : ' hidden'}" data-dept="${dept.code}" data-prog="${progKey}" data-fund-key="${secFundKey}">
                                    <td class="fund-indent fund-indent-deep"><span class="fund-chip" data-fund-cat="${fc}">${shortFund(fc)}</span> <span class="fund-name-full">${fc}</span>${fPairChips}</td>
                                    <td></td><td></td>
                                    <td class="amount-cell"><span class="figure-chip">${fmtHtml(f.d1)}</span></td>
                                    ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(f.hd1)}</span></td>` : ''}
                                    ${showSD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(f.sd1)}</span></td>` : ''}
                                    <td class="amount-cell"><span class="figure-chip">${fmtHtml(f.d2)}</span></td>
                                    <td class="amount-cell ${fCls}"><span class="figure-chip">${fmtHtml(fDelta)}</span>${subRowBadge(f.d1, f.d2)}${fTransferNote}</td>
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
                    const fundArrow = fundOpen ? ' open' : '';
                    bodyHtml += `<tr class="dept-detail-row prog-fund-group change-${p.change_type}${isOpen ? '' : ' hidden'}" data-dept="${dept.code}" data-fund-key="${fundKey}"${pairKeyAttr}>
                        <td class="detail-indent"><span class="dept-arrow${fundArrow}">▶</span> <strong${purposeTooltipAttrs(p.program_id)}>${highlight(p.program_id, q)}</strong> ${highlight(p.program_name, q)}${sparklineSvg([p.displayD1, p.displayHD1, p.displayD2])}${pairChips}${dataNoteHtml}</td>
                        <td>${progChipHtml}</td>
                        <td><span class="fund-chip fund-chip-multi" data-funds="${p.fundTitle}">${p.fundShort}</span></td>
                        <td${govCellAttrs(p, 'amount-cell')}><span class="figure-chip">${fmtHtml(p.displayD1)}</span>${posChip(p.posD1, p.posTempD1)}${govFlag(p)}</td>
                        ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(p.displayHD1)}</span>${posChip(p.posHD1, p.posTempHD1)}</td>` : ''}
                        ${showSD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(p.displaySD1)}</span>${posChip(p.posSD1, p.posTempSD1)}</td>` : ''}
                        <td${cd1CutCellAttrs(p, 'amount-cell')}><span class="figure-chip">${fmtHtml(p.displayD2)}</span>${posChip(p.posD2, p.posTempD2)}${cd1CutFlag(p)}</td>
                        <td${changeReasonCellAttrs(p, `amount-cell ${cls}`)}><span class="figure-chip">${fmtHtml(p.change)}</span>${typeBadge}${divergenceChipHtml(p)}${progTransferAnnotation}</td>
                    </tr>`;
                    const byFund = new Map();
                    // Filter to this dept's rows so cross-dept augmentation rows
                    // don't inflate fund sub-row amounts for split programs.
                    for (const r of p.rawRows.filter(r => r.department_code === p.department_code)) {
                        const fc = r.fund_category || '(unknown)';
                        if (!byFund.has(fc)) byFund.set(fc, { d1: 0, d2: 0, hd1: 0, sd1: 0 });
                        const f = byFund.get(fc);
                        f.d1  += r[d1Key]  || 0;
                        f.d2  += r[d2Key]  || 0;
                        f.hd1 += r[hd1Key] || 0;
                        f.sd1 += r.amount_sd1 || 0;
                    }
                    for (const [fc, f] of byFund) {
                        const fDelta = f.d2 - f.d1;
                        const fPct = f.d1 !== 0 ? ((f.d2 - f.d1) / Math.abs(f.d1)) * 100 : (f.d2 !== 0 ? 100 : 0);
                        const fSplitMap = splitByFund.get(`${p.program_id}|${p.section}|${fc}`);
                        const fIsTransfer = !!fSplitMap && fDelta !== 0;
                        const fCls = fIsTransfer ? 'transferred'
                            : fDelta > 0 ? 'positive' : fDelta < 0 ? 'negative' : '';
                        const fPairChips = fSplitMap
                            ? buildPairChips(p.program_id, dept.code, fSplitMap) : '';
                        const fTransferNote = fIsTransfer
                            ? transferAnnotation(p.program_id, dept.code, fSplitMap, fDelta) : '';
                        bodyHtml += `<tr class="prog-fund-row${isOpen && fundOpen ? '' : ' hidden'}" data-dept="${dept.code}" data-fund-key="${fundKey}">
                            <td class="fund-indent"><span class="fund-chip" data-fund-cat="${fc}">${shortFund(fc)}</span> <span class="fund-name-full">${fc}</span>${fPairChips}</td>
                            <td></td><td></td>
                            <td class="amount-cell"><span class="figure-chip">${fmtHtml(f.d1)}</span></td>
                            ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(f.hd1)}</span></td>` : ''}
                            ${showSD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(f.sd1)}</span></td>` : ''}
                            <td class="amount-cell"><span class="figure-chip">${fmtHtml(f.d2)}</span></td>
                            <td class="amount-cell ${fCls}"><span class="figure-chip">${fmtHtml(fDelta)}</span>${subRowBadge(f.d1, f.d2)}${fTransferNote}</td>
                        </tr>`;
                    }
                } else {
                    // Single-fund: plain leaf row
                    const progHasProjects = p.section === 'Capital Improvement'
                        && activeProjects?.projects_by_program?.[p.program_id]?.length > 0;
                    const progChipHtml = progHasProjects
                        ? `<a class="section-chip section-chip-link" href="javascript:void(0)" data-scroll-projects="${dept.code}">${p.section} →</a>`
                        : `<span class="section-chip">${p.section}</span>`;
                    bodyHtml += `<tr class="dept-detail-row change-${p.change_type}${isOpen ? '' : ' hidden'}" data-dept="${dept.code}"${pairKeyAttr}>
                        <td class="detail-indent"><strong${purposeTooltipAttrs(p.program_id)}>${highlight(p.program_id, q)}</strong> ${highlight(p.program_name, q)}${sparklineSvg([p.displayD1, p.displayHD1, p.displayD2])}${pairChips}${dataNoteHtml}</td>
                        <td>${progChipHtml}</td>
                        <td>${p.fundShort ? `<span class="fund-chip${p.fundTitle ? ' fund-chip-multi' : ''}"${p.fundTitle ? ` data-funds="${p.fundTitle}"` : ''}${p.funds.size === 1 ? ` data-fund-cat="${[...p.funds][0]}"` : ''}>${p.fundShort}</span>` : ''}</td>
                        <td${govCellAttrs(p, 'amount-cell')}><span class="figure-chip">${fmtHtml(p.displayD1)}</span>${posChip(p.posD1, p.posTempD1)}${govFlag(p)}</td>
                        ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(p.displayHD1)}</span>${posChip(p.posHD1, p.posTempHD1)}</td>` : ''}
                        ${showSD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(p.displaySD1)}</span>${posChip(p.posSD1, p.posTempSD1)}</td>` : ''}
                        <td${cd1CutCellAttrs(p, 'amount-cell')}><span class="figure-chip">${fmtHtml(p.displayD2)}</span>${posChip(p.posD2, p.posTempD2)}${cd1CutFlag(p)}</td>
                        <td${changeReasonCellAttrs(p, `amount-cell ${cls}`)}><span class="figure-chip">${fmtHtml(p.change)}</span>${typeBadge}${divergenceChipHtml(p)}${progTransferAnnotation}</td>
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
            const gSD1 = depts.reduce((s, d) => s + (d.sd1 || 0), 0);
            const sumPos = (k) => { let s = null; for (const d of depts) { if (d[k] != null) s = (s || 0) + d[k]; } return s; };
            const gPosD1 = sumPos('posD1'), gPosD2 = sumPos('posD2'), gPosHD1 = sumPos('posHD1'), gPosSD1 = sumPos('posSD1');
            const gPosTempD1 = sumPos('posTempD1'), gPosTempD2 = sumPos('posTempD2'), gPosTempHD1 = sumPos('posTempHD1'), gPosTempSD1 = sumPos('posTempSD1');
            const gDelta = gD2 - gD1;
            const gCls = gDelta > 0 ? 'positive' : gDelta < 0 ? 'negative' : '';
            const gArrow = gDelta > 0 ? '▲' : gDelta < 0 ? '▼' : '';
            const gPct = gD1 !== 0 ? ((gDelta / Math.abs(gD1)) * 100) : (gDelta !== 0 ? 100 : 0);
            const gPctStr = fmtPct(gPct).replace(/^\+/, '');
            bodyHtml += `<tbody class="totals-block"><tr class="totals-row">
                <td>Total <span class="totals-meta">${depts.length} depts</span></td>
                <td></td><td></td>
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(gD1)}</span>${posChip(gPosD1, gPosTempD1)}</td>
                ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(gHD1)}</span>${posChip(gPosHD1, gPosTempHD1)}</td>` : ''}
                ${showSD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(gSD1)}</span>${posChip(gPosSD1, gPosTempSD1)}</td>` : ''}
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(gD2)}</span>${posChip(gPosD2, gPosTempD2)}</td>
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
            const fgSD1 = fg.rows.reduce((s, r) => s + (r.amount_sd1 || 0), 0);
            const fgDelta = fgD2 - fgD1;
            const fgCls = fgDelta > 0 ? 'positive' : fgDelta < 0 ? 'negative' : '';
            const isOpen = autoExpandFunds || expandedFundTypes.has(fg.type);
            const arrow = isOpen ? ' open' : '';

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
                <td><span class="dept-arrow${arrow}">▶</span> <span class="fund-chip" data-fund-cat="${fg.category}">${fg.type}</span> ${fg.category}${fundNote} <span class="dept-count">(${fg.rows.length})</span>${fgStackBar ? ` ${fgStackBar}` : ''}</td>
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(fgD1)}</span></td>
                ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(fgHD1)}</span></td>` : ''}
                ${showSD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(fgSD1)}</span></td>` : ''}
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
                    ${showSD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(r.amount_sd1 || 0)}</span></td>` : ''}
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
            const fgSD1 = data.reduce((s, r) => s + (r.amount_sd1 || 0), 0);
            const fgDelta = fgD2 - fgD1;
            const fgCls = fgDelta > 0 ? 'positive' : fgDelta < 0 ? 'negative' : '';
            const fgArrow = fgDelta > 0 ? '▲' : fgDelta < 0 ? '▼' : '';
            const fgPct = fgD1 !== 0 ? ((fgDelta / Math.abs(fgD1)) * 100) : (fgDelta !== 0 ? 100 : 0);
            const fgPctStr = fmtPct(fgPct).replace(/^\+/, '');
            fundHtml += `<tbody class="totals-block"><tr class="totals-row">
                <td>Total <span class="totals-meta">${fundGroups.length} fund types</span></td>
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(fgD1)}</span></td>
                ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(fgHD1)}</span></td>` : ''}
                ${showSD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(fgSD1)}</span></td>` : ''}
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(fgD2)}</span></td>
                <td class="amount-cell change-cell ${fgCls}">
                    <span class="change-main">${fgArrow ? `<span class="change-arrow">${fgArrow}</span>` : ''}<span class="figure-chip">${fmtHtml(fgDelta)}</span></span>
                    ${fgArrow ? `<span class="change-pct">${fgPctStr}</span>` : ''}
                </td>
            </tr></tbody>`;
        }

        document.getElementById('draft-results').innerHTML = `
            <div class="table-scroll">
            <table class="data-table" id="draft-table">
                <thead><tr>
                    <th class="sortable th-program-col" data-sort="program_name"><div class="th-program-inner"><span class="th-program-label">Program${sortArrow('program_name')}</span>${(draftComparisonData && draftComparisonDataFY27) ? `<span class="fy-inline-toggle" id="fy-inline-toggle"><button class="fy-inline-btn${activeYear === 26 ? ' active' : ''}" data-fy-inline="26">2026</button><button class="fy-inline-btn${activeYear === 27 ? ' active' : ''}" data-fy-inline="27">2027</button></span>` : ''}</div></th>
                    <th class="th-dropdown" id="th-section"><span class="th-dropdown-btn${checkedSections ? ' th-filtered' : ''}">${secLabel}</span>
                        <div class="th-dropdown-menu">${secChecks}</div></th>
                    <th class="th-dropdown" id="th-fund"><span class="th-dropdown-btn${checkedFunds ? ' th-filtered' : ''}">${fundLabel}</span>
                        <div class="th-dropdown-menu">${fundChecks}</div></th>
                    <th class="sortable amount-cell" data-sort="d1">${getD1Label()}${sortArrow('d1')}</th>
                    ${showHD1Col() ? `<th class="sortable amount-cell" data-sort="hd1">HD1${sortArrow('hd1')}</th>` : ''}
                    ${showSD1Col() ? `<th class="sortable amount-cell" data-sort="sd1">SD1${sortArrow('sd1')}</th>` : ''}
                    <th class="sortable amount-cell" data-sort="d2">${getD2Label()}${sortArrow('d2')}</th>
                    <th class="sortable amount-cell" data-sort="change">${getChangeLabel(sortArrow('change'))}</th>
                </tr></thead>
                ${bodyHtml}
            </table>
            </div>
            <div class="table-export-row"><button class="action-link export-btn" id="export-drafts">⬇ Export CSV</button></div>`;

        document.getElementById('fund-detail-section').innerHTML = `
            <h3 class="fund-detail-heading"><span class="has-tooltip" data-tooltip="Chip color = where the money comes from:&#10;&#10;● State General — A (general fund tax revenue)&#10;● State Dedicated — B, T, W (state funds set aside for a purpose)&#10;● Federal — N, P (US government money)&#10;● Borrowed — C, E (state takes on bond debt)&#10;● Transfers / Other — U, S, R, X&#10;&#10;Letter codes:&#10;A — General funds for everyday state spending&#10;B — Special funds set aside for specific purposes&#10;C — General obligation bond funds for public projects&#10;E — Revenue bond funds repaid from project earnings&#10;N/P — Federal aid from the U.S. government&#10;S — County funds from county governments&#10;T — Trust funds held for specific long-term purposes&#10;U — Interdepartmental transfers between state agencies&#10;W — Revolving funds replenished by program revenue&#10;R — Private contributions and grants&#10;X — Miscellaneous other funds">Fund Detail</span></h3>
            <table class="data-table" id="fund-detail-table">
                <thead><tr>
                    <th>Fund / Program</th>
                    <th class="amount-cell">${getD1Label()}</th>
                    ${showHD1Col() ? '<th class="amount-cell">HD1</th>' : ''}
                    ${showSD1Col() ? '<th class="amount-cell">SD1</th>' : ''}
                    <th class="amount-cell">${getD2Label()}</th>
                    <th class="amount-cell">${getChangeLabel()}</th>
                </tr></thead>
                ${fundHtml}
            </table>
            <div class="table-export-row"><button class="action-link export-btn" id="export-fund-detail">⬇ Export CSV</button></div>`;

        // Re-attach header dropdown events after render
        attachHeaderDropdowns();

        // Stagger the entrance fade of the first screenful of rows (the CSS
        // row-enter animation reads --ri for its delay). Rows beyond the cap
        // keep the default --ri of 0 and fade in together — staggering a
        // long tail would just make deep tables feel slow.
        {
            let ri = 0;
            for (const tr of document.querySelectorAll('#draft-results tbody tr')) {
                if (tr.classList.contains('hidden')) continue;
                tr.style.setProperty('--ri', ri);
                if (++ri >= 15) break;
            }
        }

        window._lastDraftResults = data;
        window._lastDraftMeta = meta;

        renderProjects();

        // Persist current state to URL so the view is shareable
        syncUrlState();

        // Re-evaluate whether each table needs its own scroll pane (deferred:
        // syncTableScrollMode is defined in the init block below, and the
        // toggle needs post-layout widths anyway).
        setTimeout(() => window.syncTableScrollMode?.(), 0);
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

        // Inject "orphan" governor projects: projects that appear in the gov
        // CIP request with a non-zero amount but have NO matching HD1/SD1 row.
        // Without this, those gov amounts show up in the dept-level delta but
        // are invisible at the project level — every row shows $0 change while
        // the summary shows e.g. −$1.5M (AGR141 Wahiawa Dam dropped in HD1).
        // Parallels injectOrphans() in the main comparison table.
        if (govActive && governorProjectsData && governorProjectsData.projects_by_program) {
            // Track which govMap keys were "consumed" by an existing HD1 project.
            // Use the same direct + fuzzy logic as getGovAmt so we don't inject
            // a duplicate for a project the fuzzy matcher already handled.
            const consumedGovKeys = new Set();
            for (const d of deptMap.values()) {
                for (const pr of d.projects) {
                    const nm = normProjectName(pr.project_name);
                    const directKey = `${pr.program_id}:${nm}:${pr.fund_category}`;
                    if (govMap.has(directKey)) {
                        consumedGovKeys.add(directKey);
                    } else {
                        // Mark fuzzy-matched keys consumed
                        const prefix = `${pr.program_id}:`;
                        const suffix = `:${pr.fund_category}`;
                        for (const gk of govMap.keys()) {
                            if (!gk.startsWith(prefix) || !gk.endsWith(suffix)) continue;
                            const gName = gk.slice(prefix.length, gk.length - suffix.length);
                            if (gName.length >= 25 && nm.startsWith(gName)) { consumedGovKeys.add(gk); break; }
                            if (nm.length >= 25 && gName.startsWith(nm)) { consumedGovKeys.add(gk); break; }
                        }
                    }
                }
            }
            // Scan gov projects; inject any with a positive FY amount not consumed.
            for (const projs of Object.values(governorProjectsData.projects_by_program)) {
                for (const gp of projs) {
                    const amt = gp[govFyKey] || 0;
                    if (amt <= 0) continue;
                    const nm = normProjectName(gp.project_name);
                    const k  = `${gp.program_id}:${nm}:${gp.fund_category}`;
                    if (consumedGovKeys.has(k)) continue;
                    // Also skip if any fuzzy match against deptMap projects would cover it
                    const prefix = `${gp.program_id}:`;
                    const suffix = `:${gp.fund_category}`;
                    let fuzzyCovered = false;
                    for (const ck of consumedGovKeys) {
                        if (!ck.startsWith(prefix) || !ck.endsWith(suffix)) continue;
                        const ckName = ck.slice(prefix.length, ck.length - suffix.length);
                        if (ckName.length >= 25 && nm.startsWith(ckName)) { fuzzyCovered = true; break; }
                        if (nm.length >= 25 && ckName.startsWith(nm)) { fuzzyCovered = true; break; }
                    }
                    if (fuzzyCovered) continue;
                    // Inject a synthetic "removed" project row
                    const dc = gp.department_code || '(unknown)';
                    if (!deptMap.has(dc)) {
                        deptMap.set(dc, {
                            code: dc,
                            name: deptNameMap.get(dc) || gp.department_name || dc,
                            projects: [],
                        });
                    }
                    const progName = activeData.comparisons.find(r => r.program_id === gp.program_id)?.program_name || '';
                    deptMap.get(dc).projects.push({
                        project_id: gp.project_id,
                        project_name: gp.project_name,
                        program_id: gp.program_id,
                        program_name: progName,
                        department_code: dc,
                        department_name: gp.department_name || '',
                        fund_category: gp.fund_category || '',
                        fund_type: gp.fund_type || '',
                        [hd1Key]: 0,
                        [sd1Key]: 0,
                        change_type: 'removed',
                        scope: '',
                        _gov_orphan: true,
                    });
                }
            }
        }

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
            const arrow = isOpen ? ' open' : '';

            // Pre-build breakdown HTML for the dept change cell hover card.
            // Uses the same data-dept-bd attribute + initDeptBreakdownCardHandlers
            // infrastructure as the program-level comparison table.
            const projDeptBdHtml = (() => {
                const fmt = (v) => {
                    const sign = v < 0 ? '−' : v > 0 ? '+' : '';
                    const abs = Math.abs(v);
                    if (abs >= 1e9) return `${sign}$${(abs/1e9).toFixed(2)}B`;
                    if (abs >= 1e6) return `${sign}$${(abs/1e6).toFixed(2)}M`;
                    if (abs >= 1e3) return `${sign}$${Math.round(abs/1e3)}K`;
                    return `${sign}$${abs.toLocaleString()}`;
                };
                const rows = filteredProjects
                    .map(pr => {
                        const d1 = govActive ? (resolveGovAmt(pr) ?? 0) : (pr[hd1Key] || 0);
                        return { pr, change: getD2Amt(pr) - d1 };
                    })
                    .filter(r => r.change !== 0)
                    .sort((a, b) => Math.abs(b.change) - Math.abs(a.change));
                if (!rows.length) return '';
                const increases  = rows.filter(r => r.change > 0);
                const reductions = rows.filter(r => r.change < 0);
                const renderRow = ({ pr, change }) => {
                    const cls = change > 0 ? 'positive' : 'negative';
                    const rawName = pr.project_name || '';
                    const shortName = rawName.length > 46 ? rawName.slice(0, 44) + '…' : rawName;
                    const typeBadge = pr.change_type === 'added'
                        ? `<span style="font-size:0.68rem;background:#c8f5da;color:#1a6b3a;border-radius:3px;padding:0 4px;flex-shrink:0">new</span>`
                        : pr.change_type === 'removed'
                        ? `<span style="font-size:0.68rem;background:#ffdde0;color:#8b1a1a;border-radius:3px;padding:0 4px;flex-shrink:0">gone</span>`
                        : '';
                    return `<div class="dept-bd-row">
                        <span class="dept-bd-pid">#${_escHtml(String(pr.project_id))}</span>
                        <span class="dept-bd-name" title="${_escAttr(rawName)}">${_escHtml(shortName)}</span>
                        ${typeBadge}
                        <span class="dept-bd-chip ${cls}">${fmt(change)}</span>
                    </div>`;
                };
                const renderSection = (label, bucket) =>
                    bucket.length ? `<div class="dept-bd-section-label">${label}</div>` + bucket.map(renderRow).join('') : '';
                let html = `<div class="dept-bd-header">
                    <span class="dept-bd-dept-chip">${_escHtml(dept.code)}</span>
                    <span class="dept-bd-dept-name" title="${_escAttr(dept.name)}">${_escHtml(dept.name)}</span>
                </div>`;
                if (dept.description) html += `<p class="dept-bd-desc">${_escHtml(dept.description)}</p>`;
                html += renderSection('Increases', increases);
                html += renderSection('Reductions', reductions);
                const netCls = delta > 0 ? 'positive' : delta < 0 ? 'negative' : '';
                html += `<div class="dept-bd-net">Net <span class="dept-bd-chip ${netCls}">${fmt(delta)}</span></div>`;
                return html;
            })();

            // Dept group row — individual cells matching first table's dept row pattern
            bodyRows += `<tr class="dept-group-row project-dept-row${isOpen ? ' open' : ''}" data-project-dept="${dept.code}">
                <td colspan="3"><span class="dept-arrow${arrow}">▶</span> <span class="dept-chip">${highlight(dept.code, q)}</span> ${highlight(dept.name, q)} <span class="dept-count">(${filteredProjects.length} project${filteredProjects.length === 1 ? '' : 's'})</span></td>
                <td></td>
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(d1Total)}</span></td>
                ${showProjHD1 ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(hd1Total)}</span></td>` : ''}
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(d2Total)}</span></td>
                <td class="amount-cell ${deltaCls}"${projDeptBdHtml ? ` data-dept-bd="${_escAttr(projDeptBdHtml)}"` : ''}><span class="figure-chip">${fmtHtml(delta)}</span></td>
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
            if (arrow) { arrow.textContent = '▶'; arrow.classList.toggle('open', isOpen); }
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
            if (arrow) { arrow.textContent = '▶'; arrow.classList.toggle('open', isOpen); }
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
            if (arrow) { arrow.textContent = '▶'; arrow.classList.toggle('open', isOpen); }
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
            if (arrow) { arrow.textContent = '▶'; arrow.classList.toggle('open', isOpen); }
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

    // Jump-to-row from the dept change-cell breakdown card. Opens the dept,
    // re-renders, then scrolls the matching program row into view and flashes
    // it briefly so the user's eye can track where they landed. Exposed on
    // window so the card click handler (separate closure) can reach in.
    window._deptBdJumpToRow = (deptCode, programId) => {
        if (!deptCode) return;
        expandedDepts.add(deptCode);
        // Re-run the page-level render that draws the table.
        if (typeof render === 'function') render();
        requestAnimationFrame(() => {
            // Prefer the program row; fall back to the dept group row.
            const sel = programId
                ? `.dept-detail-row[data-prog="${deptCode}:${programId}"]`
                : `.dept-group-row[data-dept="${deptCode}"]`;
            const row = document.querySelector(sel)
                     || document.querySelector(`.dept-group-row[data-dept="${deptCode}"]`);
            if (!row) return;
            row.scrollIntoView({ behavior: 'smooth', block: 'center' });
            row.classList.add('row-flash');
            setTimeout(() => row.classList.remove('row-flash'), 1500);
        });
    };

    // --- Fund detail section: expand/collapse + export ---
    document.getElementById('fund-detail-section')?.addEventListener('click', (e) => {
        const fundRow = e.target.closest('.fund-group-row');
        if (fundRow) {
            const ft = fundRow.dataset.fundType;
            if (expandedFundTypes.has(ft)) expandedFundTypes.delete(ft);
            else expandedFundTypes.add(ft);
            const arrow = fundRow.querySelector('.dept-arrow');
            const isOpen = expandedFundTypes.has(ft);
            if (arrow) { arrow.textContent = '▶'; arrow.classList.toggle('open', isOpen); }
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
    // Reflect URL-persisted FY in the segmented control on page load
    if (_initState.fy === '27') {
        document.getElementById('fy-btn-26')?.classList.remove('active');
        document.getElementById('fy-btn-27')?.classList.add('active');
        document.querySelector('.fy-seg-ctrl')?.setAttribute('data-active', '27');
    }

    // --- Compare timeline: Gov's Request / HD1 / SD1 / CD1 checkboxes ---
    // Assigned by the scroll-hint setup further down; called on every stage
    // toggle so the mobile edge-fades update when columns are added/removed
    // (a ResizeObserver alone misses some of these transitions).
    let refreshScrollHints = () => {};
    const updateTimeline = () => {
        govActive     = document.getElementById('tl-gov')?.checked     ?? true;
        hd1Active     = document.getElementById('tl-hd1')?.checked     ?? true;
        sd1Active     = document.getElementById('tl-sd1')?.checked     ?? true;
        cd1Active     = document.getElementById('tl-cd1')?.checked     ?? true;
        enactedActive = document.getElementById('tl-enacted')?.checked ?? true;

        // Enforce minimum two active nodes: disable a checkbox if unchecking it
        // would leave only one node active.
        const activeCount = [govActive, hd1Active, sd1Active, cd1Active, enactedActive].filter(Boolean).length;
        ['gov', 'hd1', 'sd1', 'cd1', 'enacted'].forEach(node => {
            const cb = document.getElementById(`tl-${node}`);
            if (!cb) return;
            const nodeActive = cb.checked;
            // Disable this checkbox if it's currently checked and is the only one keeping count ≥ 2
            cb.disabled = nodeActive && activeCount <= 2;
        });

        // Reflect inactive state on the timeline container (keyed per-column);
        // CSS drives the visual change by selecting cells that carry the matching
        // data-col attribute.
        const tl = document.getElementById('compare-timeline');
        if (tl) {
            ['gov', 'hd1', 'sd1', 'cd1', 'enacted'].forEach(node => {
                const cb = document.getElementById(`tl-${node}`);
                tl.classList.toggle(`col-${node}-inactive`, !(cb?.checked));
            });
        }

        // Tint the dot-connector between ADJACENT active stages sage so the
        // dot row shows which hand-offs are in the comparison. Gaps touching a
        // muted stage stay gray — the connector-delta dimension line below
        // carries the story of spans that skip over a muted stage. Each gap
        // between dot i and dot i+1 is drawn by two segments: i's seg-after +
        // (i+1)'s seg-before.
        const segOrder = ['gov', 'hd1', 'sd1', 'cd1', 'enacted'];
        const stageOn = n => !!document.getElementById(`tl-${n}`)?.checked;
        const segOf = (n, side) =>
            document.querySelector(`.tl-dot-row[data-col="${n}"] .tl-seg-${side}`);
        segOrder.forEach((n, i) => {
            const next = segOrder[i + 1];
            const pairOn = !!next && stageOn(n) && stageOn(next);
            segOf(n, 'after')?.classList.toggle('tl-seg-on', pairOn);
            if (next) segOf(next, 'before')?.classList.toggle('tl-seg-on', pairOn);
        });

        // Mirror checkbox state onto the mobile stage-picker chips (active fill
        // + disabled when toggling off would drop below the 2-stage minimum).
        document.querySelectorAll('.tl-stage-chip').forEach(chip => {
            const cb = document.getElementById(`tl-${chip.dataset.node}`);
            const on = !!cb?.checked;
            chip.classList.toggle('active', on);
            chip.setAttribute('aria-pressed', on ? 'true' : 'false');
            chip.disabled = !!cb?.disabled;
        });

        updateSummaryCards();
        render();
        // Recompute edge-fades after the columns reflow. setTimeout (not rAF)
        // so it still fires if the tab is backgrounded.
        setTimeout(refreshScrollHints, 0);
    };
    document.querySelectorAll('.tl-cb').forEach(cb => cb.addEventListener('change', updateTimeline));
    // Mobile stage chips proxy the hidden checkboxes — flip + dispatch change
    // so the exact same path the desktop dots use drives everything downstream.
    document.querySelectorAll('.tl-stage-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const cb = document.getElementById(`tl-${chip.dataset.node}`);
            if (!cb || cb.disabled) return; // guard: keeps ≥2 stages active
            cb.checked = !cb.checked;
            cb.dispatchEvent(new Event('change', { bubbles: true }));
        });
    });
    // Reflect URL-persisted node state in checkboxes on page load
    if (_initState.nodes !== 'gov,enacted') {
        const ns = new Set(_initState.nodes.split(','));
        ['gov', 'hd1', 'sd1', 'cd1', 'enacted'].forEach(n => {
            const cb = document.getElementById(`tl-${n}`);
            if (cb) cb.checked = ns.has(n);
        });
    }
    // Always sync the timeline UI to current checkbox state so the
    // col-*-inactive classes are applied even on first load (defaults
    // include HD1/SD1 unchecked).
    updateTimeline();

    // Re-render the summary when the phone breakpoint flips so amounts
    // switch between 1- and 2-decimal precision. The MQL must be retained
    // (an unreferenced one can be GC'd and never fire), and a resize
    // fallback covers environments where the change event doesn't dispatch.
    const phoneMq = window.matchMedia('(max-width: 640px)');
    let phoneMqWas = phoneMq.matches;
    const onPhoneMqMaybeChanged = () => {
        if (phoneMq.matches !== phoneMqWas) {
            phoneMqWas = phoneMq.matches;
            updateSummaryCards();
        }
    };
    // The router has no teardown hook, so this init re-runs on every visit to
    // the tab. Drop the previous visit's window/MQL listeners before adding
    // fresh ones, or they pile up and every resize fires N stale handlers.
    if (window._draftPhoneMqHandler) {
        phoneMq.removeEventListener('change', window._draftPhoneMqHandler);
        window.removeEventListener('resize', window._draftPhoneMqHandler);
    }
    window._draftPhoneMqHandler = onPhoneMqMaybeChanged;
    phoneMq.addEventListener('change', onPhoneMqMaybeChanged);
    window.addEventListener('resize', onPhoneMqMaybeChanged);

    // Scroll-hint classes on the (mobile) horizontally scrolling card —
    // CSS fades the clipped edge so it's obvious there's more content.
    const hintBar = document.querySelector('.compare-controls-bar');
    if (hintBar) {
        const updateScrollHints = () => {
            const maxScroll = hintBar.scrollWidth - hintBar.clientWidth;
            hintBar.classList.toggle('scroll-right', maxScroll > 1 && hintBar.scrollLeft < maxScroll - 1);
            hintBar.classList.toggle('scroll-left', hintBar.scrollLeft > 1);
        };
        hintBar.addEventListener('scroll', updateScrollHints, { passive: true });
        // Watch the inner timeline too — toggling stage columns changes the
        // content width without resizing the bar's own box.
        const hintRo = new ResizeObserver(updateScrollHints);
        hintRo.observe(hintBar);
        const hintTl = hintBar.querySelector('.compare-timeline');
        if (hintTl) hintRo.observe(hintTl);
        refreshScrollHints = updateScrollHints; // let updateTimeline drive it too
        updateScrollHints();
    }

    // Expand caret (left of Gov amount) — toggle Op/Cap breakdown
    const expandBtn = document.getElementById('tl-expand-btn');
    if (expandBtn) {
        expandBtn.addEventListener('click', () => {
            // Suppress CSS scroll anchoring during expand/collapse so the browser
            // doesn't adjust scrollY (which makes the summary row appear to jump).
            document.documentElement.style.overflowAnchor = 'none';
            showBreakdown = !showBreakdown;
            updateSummaryCards();
            requestAnimationFrame(() => { document.documentElement.style.overflowAnchor = ''; });
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
            // Column names reflect the ACTIVE comparison endpoints (Gov's
            // Request / HD1 / SD1 / CD1 / Enacted), not the dataset's
            // draft1/draft2, which stay HD1/CD1 regardless of the toggles.
            const d1Name = getD1Label().replace(/[^\w]+/g, '_');
            const d2Name = getD2Label().replace(/[^\w]+/g, '_');
            const rows = (window._lastDraftResults || activeData.comparisons).map(r => ({
                program_id: r.program_id, program_name: r.program_name,
                department_code: r.department_code, department_name: r.department_name,
                section: r.section, fund_type: r.fund_type, fund_category: r.fund_category,
                [d1Name]: r[d1Key], [d2Name]: r[d2Key],
                [`${d1Name}_positions`]: r[posKeyFor(d1Key)] ?? '',
                [`${d2Name}_positions`]: r[posKeyFor(d2Key)] ?? '',
                change: r.change, pct_change: r.pct_change, change_type: r.change_type,
            }));
            downloadCSV(rows, `${meta.bill_number}_${d1Name}_vs_${d2Name}_FY${meta.fiscal_year}.csv`);
        }
    });

    document.getElementById('fund-detail-section')?.addEventListener('click', (e) => {
        const btn = e.target.closest('button.export-btn');
        if (!btn || btn.id !== 'export-fund-detail') return;
        const meta = window._lastDraftMeta || activeData.metadata;
        const d1Key = getD1Key(), d2Key = getD2Key();
        const d1Name = getD1Label().replace(/[^\w]+/g, '_');
        const d2Name = getD2Label().replace(/[^\w]+/g, '_');
        const rows = activeData.comparisons.map(r => ({
            fund_type: r.fund_type, fund_category: r.fund_category,
            program_id: r.program_id, program_name: r.program_name,
            department_code: r.department_code, department_name: r.department_name,
            section: r.section,
            [d1Name]: r[d1Key], [d2Name]: r[d2Key],
            [`${d1Name}_positions`]: r[posKeyFor(d1Key)] ?? '',
            [`${d2Name}_positions`]: r[posKeyFor(d2Key)] ?? '',
            change: r.change, pct_change: r.pct_change,
        }));
        downloadCSV(rows, `${meta.bill_number}_fund_detail_FY${meta.fiscal_year}.csv`);
    });

    // --- Initial render ---
    updateSummaryCards();
    render();

    // Keep --compare-bar-h and per-table --compare-thead-h in sync with the
    // sticky controls bar + table header heights. Open dept/fund rows stick
    // directly below their thead, so we need both measurements — and there
    // are MULTIPLE tables on this page (main comparison, capital projects,
    // fund detail), each with its own thead height. Setting --compare-thead-h
    // on each table scopes the CSS var to that table's open rows.
    const comparePage = document.querySelector('.compare-page');
    if (comparePage) {
        // Controls bar is no longer sticky; only the search/filter row and
        // table headers stick. Measure the search row to offset thead/open rows.
        const searchRow = comparePage.querySelector(':scope > .search-row');
        const syncBarHeight = () => {
            if (searchRow) {
                comparePage.style.setProperty('--compare-search-h', searchRow.offsetHeight + 'px');
            }
            comparePage.querySelectorAll('.data-table').forEach(table => {
                const thead = table.querySelector('thead');
                if (thead) {
                    table.style.setProperty('--compare-thead-h', thead.offsetHeight + 'px');
                }
            });
        };
        syncBarHeight();
        const ro = new ResizeObserver(syncBarHeight);
        if (searchRow) ro.observe(searchRow);
        comparePage.querySelectorAll('.data-table thead').forEach(t => ro.observe(t));

        // Decide per render whether the main table needs its own scroll pane.
        // Default (table fits the card): the pane has no overflow and the page
        // is the only vertical scroller — no nested-scroll trap, and the thead
        // pins below the sticky search row at page level. Only when the table
        // is genuinely wider than the card (3–4 stages on) does .is-wide
        // restore the contained pane with its own sticky context.
        window.syncTableScrollMode = () => {
            comparePage.querySelectorAll('.table-scroll').forEach(pane => {
                const t = pane.querySelector('table');
                if (t) pane.classList.toggle('is-wide', t.scrollWidth > pane.clientWidth + 4);
            });
            syncBarHeight();
        };
        syncTableScrollMode();
        // Same teardown guard as the phone-MQL listener above — replace the
        // prior visit's resize handler rather than stacking another one.
        if (window._draftScrollModeHandler) {
            window.removeEventListener('resize', window._draftScrollModeHandler);
        }
        window._draftScrollModeHandler = () => syncTableScrollMode();
        window.addEventListener('resize', window._draftScrollModeHandler);

        // Floating back-to-top — the compare page is a single long scroll;
        // give deep scrollers a one-tap way home. Created once, page-global.
        if (!document.querySelector('.back-to-top')) {
            const topBtn = document.createElement('button');
            topBtn.className = 'back-to-top';
            topBtn.setAttribute('aria-label', 'Back to top');
            topBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 12 12" aria-hidden="true"><path d="M2.5 7.75 6 4.25l3.5 3.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
            document.body.appendChild(topBtn);
            topBtn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
            const onTopBtnScroll = () => topBtn.classList.toggle('show', window.scrollY > window.innerHeight * 1.25);
            window.addEventListener('scroll', onTopBtnScroll, { passive: true });
            onTopBtnScroll();
        }

        // Cap the reading-guide panel to the space below its pill so it never
        // extends past the fold; with overflow-y:auto it scrolls internally
        // instead of forcing a page scroll. Delegated on the page wrapper
        // because render() recreates the pill on every pass.
        const capReadingGuide = (e) => {
            const pill = e.target.closest?.('.reading-guide-pill');
            const panel = pill?.querySelector('.reading-guide-panel');
            if (!panel) return;
            const below = window.innerHeight - pill.getBoundingClientRect().bottom - 24;
            panel.style.maxHeight = Math.min(380, Math.max(200, below)) + 'px';
        };
        comparePage.addEventListener('mouseover', capReadingGuide);
        comparePage.addEventListener('focusin', capReadingGuide);
    }
};

// ---------------------------------------------------------------------------
// Init hooks
// ---------------------------------------------------------------------------
window.initHomePage = async function () {
    if (!departmentsData?.length) return;

    // ── Multi-year "By Department" init ──────────────────────────────────────
    // Selected fiscal year. FY2016–2025 show department totals from the
    // historical series; FY2026–27 show full program detail from the enacted
    // supplemental (Act 175). Default = FY2026.
    let selectedFy = 2026;
    let sortDir   = 'desc';
    let histMode  = 'nominal';   // 'nominal' | 'real' — drives top history chart

    const idByCode  = new Map(departmentsData.map(d => [d.code, d.id]));
    const deptTotal = (d) => (d.operating_budget || 0) + (d.capital_budget || 0) + (d.one_time_appropriations || 0);

    // Program-level detail dataset for a year (Act 175 for FY2026–27), or null
    // when the year is totals-only (FY2016–2025).
    const detailFor = (fy) => byDeptDatasets[String(fy)] || null;

    // Human label for the selected year, e.g. "FY2026 · Act 175".
    const yearLabel = () =>
        (selectedFy === 2026 || selectedFy === 2027) ? `FY${selectedFy} · Act 175` : `FY${selectedFy}`;

    // ---- Department grid -------------------------------------------------
    // Full-detail selections show a per-dept operating/capital/positions
    // breakdown from the SAME dataset as the card total (so they always
    // reconcile). Totals-only years collapse to total + 12-yr sparkline.
    const renderDeptCard = (r, sparkSvg) => {
        const detailRows = r.hasDetail ? `
            <div class="budget-row"><span>Operating</span><span>${fmt(r.op)}</span></div>
            ${r.cap > 0 ? `<div class="budget-row"><span>Capital</span><span>${fmt(r.cap)}</span></div>` : ''}
            ${r.ot > 0 ? `<div class="budget-row"><span>One-Time</span><span>${fmt(r.ot)}</span></div>` : ''}
            ${r.pos ? `<div class="budget-row"><span>Positions</span><span>${r.pos.toLocaleString(undefined,{maximumFractionDigits:0})}</span></div>` : ''}
        ` : '';
        const id = r.id || idByCode.get(r.code) || (r.code || '').toLowerCase();
        const totalDisplay = r.total != null ? fmt(r.total) : '—';
        // Only the 24 state departments have drill-in pages. County grant
        // pass-through codes (CCH/COH/COK/COM) appear for total accuracy but
        // render as static (non-clickable) cards.
        const hasPage = idByCode.has(r.code);
        // First-sentence description on hover (empty for county pass-throughs and
        // the few departments without a description — no tooltip in that case).
        const summary = deptSummary((departmentsData.find(d => d.code === r.code) || {}).description);
        const h3 = summary
            ? `<h3 class="has-tooltip" data-tooltip="${_escAttr(summary)}">${r.name}</h3>`
            : `<h3>${r.name}</h3>`;
        const inner = `
                ${h3}
                <div class="card-content">
                    <div class="budget-total">
                        <span>Total Budget · ${yearLabel()}</span>
                        <strong>${totalDisplay}</strong>
                    </div>
                    ${sparkSvg ? `<div class="dept-card-spark-wrap">${sparkSvg}</div>` : ''}
                    ${detailRows ? `<div class="budget-breakdown">${detailRows}</div>` : ''}
                </div>`;
        return hasPage
            ? `<a href="#/department/${id}" class="department-card">${inner}</a>`
            : `<div class="department-card department-card-static" title="State grants to ${r.name} — no separate department page">${inner}</div>`;
    };

    const renderGrid = () => {
        const grid = document.getElementById('dept-grid');
        if (!grid) return;
        const fy = selectedFy;
        const detail = detailFor(fy);
        const histByCode = new Map((historicalTrendsData?.by_department || []).map(d => [d.dept_code, d]));

        let rows;
        if (detail) {
            rows = detail.map(d => ({
                code: d.code, name: d.name, id: d.id,
                total: deptTotal(d),
                op: d.operating_budget || 0, cap: d.capital_budget || 0,
                ot: d.one_time_appropriations || 0, pos: d.positions,
                hasDetail: true,
            }));
        } else {
            const fyTotals = deptTotalsForFy(fy); // Map<code,{nominal,real}>
            rows = (historicalTrendsData?.by_department || []).map(d => {
                const t = fyTotals.get(d.dept_code);
                return t ? { code: d.dept_code, name: d.dept_name, total: t.nominal, hasDetail: false } : null;
            }).filter(Boolean);
        }

        rows.sort((a, b) => {
            const tA = a.total ?? -Infinity, tB = b.total ?? -Infinity;
            return sortDir === 'asc' ? tA - tB : tB - tA;
        });

        grid.innerHTML = rows.map(r => {
            const hist = histByCode.get(r.code);
            const points = hist ? hist.series.map(s => ({ fy: s.fy, value: s.nominal })) : [];
            return renderDeptCard(r, deptHistorySparkline(points));
        }).join('');
    };

    // ---- Summary cards (state-wide totals for selected year) ------------
    const renderSummaryCards = () => {
        const wrap = document.getElementById('hb300-summary-cards');
        if (!wrap) return;
        const fy = selectedFy;
        const detail = detailFor(fy);
        let totalAmt, opAmt, capAmt, posAmt;
        if (detail) {
            // Sum the detail dataset so the summary reconciles with the grid.
            totalAmt = detail.reduce((s, d) => s + deptTotal(d), 0);
            opAmt    = detail.reduce((s, d) => s + (d.operating_budget || 0), 0);
            capAmt   = detail.reduce((s, d) => s + (d.capital_budget || 0), 0);
            const p  = detail.reduce((s, d) => s + (d.positions || 0), 0);
            posAmt   = p || null;
        } else {
            const t  = stateTotalsForFy(fy);
            totalAmt = t ? t.total_nominal : null;
            opAmt    = t ? t.operating_nominal : null;
            capAmt   = t ? t.capital_nominal : null;
            posAmt   = null;
        }
        wrap.innerHTML = `
            <div class="summary-card">
                <div class="amount">${totalAmt != null ? fmtHtmlCard(totalAmt) : '—'}</div>
                <div class="label">Total Budget</div>
                <div class="label-sub">${yearLabel()}</div>
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
                <div class="label-sub">${yearLabel()}</div>
            </div>` : ''}`;

        // Help line below the year selector — explains the current selection.
        const help = document.getElementById('hb300-fy-help');
        if (help) {
            help.textContent = (fy === 2026 || fy === 2027)
                ? `FY${fy} enacted supplemental — Act 175 (HB1800), SLH 2026. Full operating, capital, and program detail.`
                : `Department totals only — FY${fy} is from the corresponding biennial appropriations act.`;
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

        // Stacked area: operating fills from the x-axis, capital stacks on
        // top.  The two filled areas always add up to the combined state
        // budget, so the silhouette of the upper stack reads as the total
        // line — no separate "Total" series needed.
        historyChart = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Operating',
                        data: totals.map(t => t[opK]),
                        borderColor: '#5a7b68',
                        backgroundColor: 'rgba(90, 123, 104, 0.55)',
                        tension: 0.25,
                        fill: 'origin',
                        borderWidth: 1.6,
                        pointRadius: 3, pointHoverRadius: 5,
                        pointBackgroundColor: '#5a7b68',
                    },
                    {
                        label: 'Capital',
                        data: totals.map(t => t[capK]),
                        borderColor: '#a08e58',
                        backgroundColor: 'rgba(160, 142, 88, 0.55)',
                        tension: 0.25,
                        fill: '-1',
                        borderWidth: 1.6,
                        // Highlight the currently-selected year on the top
                        // (stacked-total) curve so it's clear which point
                        // matches the dropdown.
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
                            // Add a "Total" footer so the user sees the
                            // combined sum without a third dataset cluttering
                            // the legend.
                            footer: (items) => {
                                const sum = items.reduce((s, it) => s + (it.parsed.y || 0), 0);
                                return `Total: ${fmtB(sum)}`;
                            },
                        },
                    },
                    datalabels: { display: false },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        stacked: true,
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

    // Obligated (fixed) costs stacked-area chart, FY2018–FY2027. Same four
    // bands and palette as the primer's chart; Certificate of Participation
    // folds into Debt Service. White dots mark each year on every band line.
    let obligatedChart = null;
    const renderObligatedChart = () => {
        const canvas = document.getElementById('obligated-chart');
        if (!canvas || typeof Chart === 'undefined' || !obligatedData) return;
        if (obligatedChart) obligatedChart.destroy();
        const series = obligatedData.series;
        const years  = Object.keys(series).sort();
        const labels = years.map(y => `FY${y.slice(2)}`);
        const bands = [
            { label: 'Retirement (ERS)',        keys: ['Retirement System'],                             color: '#2d6a4f' },
            { label: 'Health Benefits (EUTF)',  keys: ['Health Fund'],                                   color: '#6b9080' },
            { label: 'Medicaid & Entitlements', keys: ['Medicaid & Entitlements'],                       color: '#8ab19d' },
            { label: 'Debt Service',            keys: ['Debt Service', 'Certificate of Participation'],  color: '#cce3de' },
        ];
        const fmtB = (v) => `$${(v / 1e9).toFixed(2)}B`;
        const hexA = (hex, a) => {
            const n = parseInt(hex.slice(1), 16);
            return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
        };
        const datasets = bands.map((b, i) => ({
            label: b.label,
            data: years.map(y => b.keys.reduce((t, k) => t + (series[y][k] || 0), 0)),
            borderColor: b.color,
            backgroundColor: hexA(b.color, 0.78),
            fill: i === 0 ? 'origin' : '-1',
            tension: 0.25,
            borderWidth: 1.4,
            pointRadius: 3, pointHoverRadius: 5,
            pointBackgroundColor: '#fff',
            pointBorderColor: '#1b4332',
            pointBorderWidth: 1,
        }));
        obligatedChart = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: { labels, datasets },
            options: {
                maintainAspectRatio: false,
                responsive: true,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: true, position: 'top', labels: { boxWidth: 14 } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${fmtB(ctx.parsed.y)}`,
                            footer: (items) => `Total: ${fmtB(items.reduce((s, it) => s + (it.parsed.y || 0), 0))}`,
                        },
                    },
                    datalabels: { display: false },
                },
                scales: {
                    y: {
                        beginAtZero: true, stacked: true,
                        ticks: { callback: (v) => `$${(v / 1e9).toFixed(0)}B` },
                        title: { display: true, text: 'General funds (nominal $)' },
                    },
                    x: { grid: { display: false } },
                },
            },
        });
    };

    const renderAll = () => {
        renderSummaryCards();
        renderHistoryChart();
        renderObligatedChart();
        renderGrid();
    };

    // ---- Wire up controls ------------------------------------------------
    const fySelect = document.getElementById('hb300-fy-select');
    const fyPrev   = document.getElementById('hb300-fy-prev');
    const fyNext   = document.getElementById('hb300-fy-next');

    // Update the prev/next buttons' enabled state based on the current
    // option position.  Options are listed newest-first, so "prev" moves
    // to a newer year (smaller index) and "next" moves older (larger
    // index).  The labels reflect that visually.
    const syncStepperButtons = () => {
        if (!fySelect) return;
        const idx = fySelect.selectedIndex;
        const last = fySelect.options.length - 1;
        if (fyPrev) fyPrev.disabled = idx <= 0;
        if (fyNext) fyNext.disabled = idx >= last;
    };

    fySelect?.addEventListener('change', (e) => {
        const fy = parseInt(e.target.value, 10);
        if (!Number.isFinite(fy)) return;
        selectedFy = fy;
        syncStepperButtons();
        renderAll();
    });

    fyPrev?.addEventListener('click', () => {
        if (!fySelect || fySelect.selectedIndex <= 0) return;
        fySelect.selectedIndex -= 1;
        fySelect.dispatchEvent(new Event('change'));
    });
    fyNext?.addEventListener('click', () => {
        if (!fySelect || fySelect.selectedIndex >= fySelect.options.length - 1) return;
        fySelect.selectedIndex += 1;
        fySelect.dispatchEvent(new Event('change'));
    });

    // Initial button state sync
    syncStepperButtons();

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
        const fy = selectedFy;
        const detail = detailFor(fy);
        const src = (fy === 2026 || fy === 2027) ? 'Act 175, SLH 2026' : 'enacted biennial act';
        let rows;
        if (detail) {
            // Full detail: operating/capital/positions per department.
            rows = detail.map(d => ({
                code: d.code, name: d.name, fiscal_year: fy, source: src,
                total: deptTotal(d),
                operating: d.operating_budget,
                capital:   d.capital_budget,
                one_time:  d.one_time_appropriations,
                positions: d.positions ?? '',
            }));
        } else {
            // Totals-only historical year.
            const fyTotals = deptTotalsForFy(fy);
            rows = (historicalTrendsData?.by_department || []).map(d => {
                const t = fyTotals.get(d.dept_code);
                return t ? { code: d.dept_code, name: d.dept_name, fiscal_year: fy, source: src, total: t.nominal } : null;
            }).filter(Boolean);
        }
        downloadCSV(rows, `departments_fy${fy}.csv`);
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

// ---------------------------------------------------------------------------
// County budgets — the counties' own operating + capital budgets (separate
// documents from the state bills; HB300 §13 only carries state grants TO
// counties). Honolulu is live (operating via data.honolulu.gov, CIP parsed
// from the capital budget ordinance); the neighbor-island counties publish
// PDF ordinances and appear as "coming soon" until their parsers land.
// Data: county_budgets.json from scripts/process_county_budgets.py — a
// multi-fiscal-year file, each county/year split into operating + cip.
// ---------------------------------------------------------------------------
let countyBudgetsData = null;
const countyState = { county: null, fy: null };

window.loadCountyBudgets = async function () {
    try {
        const response = await fetch('./js/county_budgets.json?v=' + Date.now());
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        countyBudgetsData = await response.json();
        return countyBudgetsData;
    } catch (e) {
        // Missing county data must never break state mode — the Counties tab
        // just renders its empty state.
        console.error('Error loading county budgets:', e);
        return null;
    }
};

// Keep the State|Counties scope pill and body class in sync with the route.
window.updateScopeToggle = function (path) {
    const isCounty = path.startsWith('/counties');
    document.body.classList.toggle('scope-county', isCounty);
    document.querySelector('.scope-btn-state')?.classList.toggle('active', !isCounty);
    document.querySelector('.scope-btn-county')?.classList.toggle('active', isCounty);
};

const COUNTY_ORDER = ['honolulu', 'maui', 'hawaii', 'kauai'];
const countyShortName = (name) =>
    name.replace('City & County of ', '').replace('County of ', '');

const countyFyList = () => (countyBudgetsData?.fiscal_years || []).map(String);
const countyEntryFor = (fy, slug) =>
    countyBudgetsData?.years?.[String(fy)]?.[slug] || null;
// A county is reachable if it has data in ANY fiscal year.
const countyEverAvailable = (slug) =>
    countyFyList().some(fy => countyEntryFor(fy, slug)?.available);

// Stacked single-row bar of fund categories with a legend underneath.
const fundCategoryBar = (fundBreakdown, opts = {}) => {
    if (!fundBreakdown) return '';
    const palette = {
        'General Fund': '#5a7b68',
        'Special / Enterprise Funds': '#7da48d',
        'Federal Funds': '#c9a87b',
        'Bond / Debt Funds': '#a68c68',
        'Trust & Other Funds': '#cdd3d8',
    };
    const entries = Object.entries(fundBreakdown).filter(([, v]) => v > 0);
    const sum = entries.reduce((s, [, v]) => s + v, 0) || 1;
    if (!entries.length) return '';
    const segments = entries.map(([k, v]) =>
        `<span class="fund-cat-seg" style="width:${(v / sum * 100).toFixed(2)}%;background:${palette[k] || '#cdd3d8'}" title="${escapeHtml(k)} — ${fmt(v)}"></span>`
    ).join('');
    const legend = entries.map(([k, v]) =>
        `<span class="fund-cat-legend-item"><span class="legend-swatch" style="background:${palette[k] || '#cdd3d8'}"></span>${escapeHtml(k)} <span class="fund-cat-legend-amt">${fmt(v)}</span></span>`
    ).join('');
    return `<div class="fund-cat-bar-wrap">
        ${opts.title ? `<div class="fund-cat-bar-title">${escapeHtml(opts.title)}</div>` : ''}
        <div class="fund-cat-bar">${segments}</div>
        <div class="fund-cat-legend">${legend}</div>
    </div>`;
};

// ── County data-viz: shared palette, compact formatter, Chart.js mount/destroy ─
const COUNTY_FUND_PALETTE = {
    'General Fund': '#5a7b68',
    'Special / Enterprise Funds': '#7da48d',
    'Federal Funds': '#c9a87b',
    'Bond / Debt Funds': '#a68c68',
    'Trust & Other Funds': '#cdd3d8',
};
const countyFundColor = (cat) => COUNTY_FUND_PALETTE[cat] || '#cdd3d8';
const _dominantFund = (fb) => Object.entries(fb || {}).sort((a, b) => b[1] - a[1])[0]?.[0];

// Compact plain-text money for chart centers / tile labels ($2.3B · $461M · $12K).
const fmtCompact = (n) => {
    if (n == null) return '$0';
    const a = Math.abs(n), s = n < 0 ? '-' : '';
    if (a >= 1e9) return `${s}$${(a / 1e9).toFixed(a >= 1e10 ? 0 : 1)}B`;
    if (a >= 1e6) return `${s}$${(a / 1e6).toFixed(a >= 1e8 ? 0 : 1)}M`;
    if (a >= 1e3) return `${s}$${Math.round(a / 1e3)}K`;
    return `${s}$${Math.round(a)}`;
};
const _countyReducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Live Chart.js instances for the county view — destroyed before each full
// re-render (FY toggle / county switch) so detached canvases never leak.
let _countyCharts = [];
function destroyCountyCharts() {
    _countyCharts.forEach(ch => { try { ch.destroy(); } catch (e) { /* already gone */ } });
    _countyCharts = [];
}

// Fund-category doughnut: canvas + a centered total + a labelled legend. The
// Chart itself is created in mountCountyCharts once this markup is in the DOM.
function fundDonutBlock(canvasId, fundBreakdown, opts = {}) {
    const entries = Object.entries(fundBreakdown || {}).filter(([, v]) => v > 0)
        .sort((a, b) => b[1] - a[1]);
    if (!entries.length) return '';
    const total = entries.reduce((s, [, v]) => s + v, 0);
    const legend = entries.map(([k, v]) => `
        <li class="cdonut-legend-row">
            <span class="cdonut-swatch" style="background:${countyFundColor(k)}"></span>
            <span class="cdonut-legend-name">${escapeHtml(k)}</span>
            <span class="cdonut-legend-amt">${fmtCompact(v)}<em>${(v / total * 100).toFixed(0)}%</em></span>
        </li>`).join('');
    return `<div class="county-viz">
        <div class="county-viz-title">${escapeHtml(opts.title || 'Where it comes from')}</div>
        <div class="cdonut">
            <div class="cdonut-chart">
                <canvas id="${canvasId}" role="img" aria-label="${escapeHtml(opts.aria || 'Fund breakdown')}"></canvas>
                <div class="cdonut-center"><span class="cdonut-center-amt">${fmtCompact(total)}</span><span class="cdonut-center-lbl">${escapeHtml(opts.centerLabel || '')}</span></div>
            </div>
            <ul class="cdonut-legend">${legend}</ul>
        </div>
    </div>`;
}

// Treemap canvas (departments / funds sized by budget, tinted by dominant fund).
function treemapBlock(canvasId, title, aria) {
    return `<div class="county-viz county-viz-treemap">
        <div class="county-viz-title">${escapeHtml(title)}</div>
        <div class="ctreemap"><canvas id="${canvasId}" role="img" aria-label="${escapeHtml(aria)}"></canvas></div>
    </div>`;
}

function _mountDonut(canvasId, fundBreakdown) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return;
    const entries = Object.entries(fundBreakdown || {}).filter(([, v]) => v > 0)
        .sort((a, b) => b[1] - a[1]);
    if (!entries.length) return;
    const total = entries.reduce((s, [, v]) => s + v, 0);
    _countyCharts.push(new Chart(canvas.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: entries.map(([k]) => k),
            datasets: [{
                data: entries.map(([, v]) => v),
                backgroundColor: entries.map(([k]) => countyFundColor(k)),
                borderColor: '#fff', borderWidth: 2, hoverOffset: 6,
            }],
        },
        options: {
            cutout: '64%', maintainAspectRatio: false, responsive: true,
            animation: _countyReducedMotion() ? false : { duration: 500 },
            plugins: {
                legend: { display: false },
                datalabels: { display: false },
                tooltip: { callbacks: {
                    label: (ctx) => `${ctx.label}: ${fmtCompact(ctx.parsed)} (${(ctx.parsed / total * 100).toFixed(0)}%)`,
                } },
            },
        },
    }));
}

function _mountTreemap(canvasId, rows, rowLabel) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined' || !rows?.length) return;
    // Top tiles + an aggregated "Other" so tiny slivers don't clutter the map.
    const sorted = [...rows].sort((a, b) => b.total_budget - a.total_budget);
    const TOP = 14;
    let tree = sorted.slice(0, TOP).map(d => ({
        name: d.name, value: d.total_budget, color: countyFundColor(_dominantFund(d.fund_breakdown)),
    }));
    const rest = sorted.slice(TOP);
    if (rest.length) tree.push({ name: `Other (${rest.length})`,
        value: rest.reduce((s, d) => s + d.total_budget, 0), color: '#b9c4bd' });
    tree = tree.filter(t => t.value > 0);
    if (!tree.length) return;
    const grand = tree.reduce((s, t) => s + t.value, 0) || 1;
    _countyCharts.push(new Chart(canvas.getContext('2d'), {
        type: 'treemap',
        data: { datasets: [{
            tree, key: 'value', borderWidth: 1, borderColor: '#fff', spacing: 1,
            backgroundColor: (ctx) => ctx?.raw?._data?.color || '#ccc',
            labels: {
                display: true, color: '#fff', font: { size: 11, weight: '600' },
                align: 'center', position: 'middle',
                formatter: (ctx) => { const d = ctx?.raw?._data; return d ? [d.name, fmtCompact(d.value)] : ''; },
            },
        }] },
        options: {
            maintainAspectRatio: false, responsive: true,
            animation: _countyReducedMotion() ? false : { duration: 500 },
            plugins: {
                legend: { display: false }, datalabels: { display: false },
                tooltip: { callbacks: {
                    title: (items) => items[0]?.raw?._data?.name || '',
                    label: (ctx) => { const d = ctx?.raw?._data; return d ? `${fmtCompact(d.value)} (${(d.value / grand * 100).toFixed(1)}%)` : ''; },
                } },
            },
        },
    }));
}

// Create every chart for the current county entry (called after a full render).
function mountCountyCharts(c) {
    destroyCountyCharts();
    if (!c || !c.available) return;
    if (c.operating && c.operating.total > 0) {
        _mountDonut('cdonut-op', c.operating.fund_breakdown);
        _mountTreemap('ctreemap-op', c.operating.departments, c.operating.row_label);
    }
    if (c.cip) _mountDonut('cdonut-cip', c.cip.fund_breakdown);
}

// "Budget at a glance" hero — total + an Operating/Capital proportion bar.
function renderCountyHero(c, fy) {
    const op = c.operating_budget || 0, cap = c.capital_budget || 0, tot = c.total_budget || 0;
    const opPct = tot ? op / tot * 100 : 0, capPct = tot ? cap / tot * 100 : 0;
    const seg = (cls, pct) => pct > 0 ? `<span class="chero-seg ${cls}" style="width:${pct.toFixed(1)}%"></span>` : '';
    const fig = (label, val, pct, cls, note) => `
        <div class="chero-fig ${cls}">
            <span class="chero-fig-dot"></span>
            <div class="chero-fig-body">
                <div class="chero-fig-amt">${val > 0 ? fmtHtmlCard(val) : '<span class="chero-dash">—</span>'}</div>
                <div class="chero-fig-lbl">${escapeHtml(label)}${val > 0 ? ` · ${pct.toFixed(0)}%` : (note ? ` · ${escapeHtml(note)}` : '')}</div>
            </div>
        </div>`;
    return `<div class="county-hero">
        <div class="chero-total">
            <div class="chero-total-amt">${fmtHtmlCard(tot)}</div>
            <div class="chero-total-lbl">Total budget <span class="chero-fy">FY${fy}</span></div>
        </div>
        <div class="chero-split">
            <div class="chero-bar">${seg('chero-seg-op', opPct)}${seg('chero-seg-cap', capPct)}</div>
            <div class="chero-figs">
                ${fig('Operating', op, opPct, 'is-op', 'not yet parsed')}
                ${fig('Capital (CIP)', cap, capPct, 'is-cap', c.capital_note || 'not included')}
            </div>
        </div>
    </div>`;
}

window.countiesPage = async function (params) {
    if (!countyBudgetsData || !countyBudgetsData.years) {
        return `
            <section class="compare-page">
                <h2>County Budgets</h2>
                <div class="empty-state">
                    <p>No county budget data available yet.</p>
                    <p>To generate it, run:</p>
                    <pre>python scripts/fetch_county_budgets.py --county honolulu --pdfs
python scripts/process_county_budgets.py --county all</pre>
                </div>
            </section>`;
    }

    const years = countyFyList();
    // Resolve fiscal year: keep prior choice if valid, else the default.
    let fy = countyState.fy && years.includes(String(countyState.fy))
        ? String(countyState.fy) : String(countyBudgetsData.default_fiscal_year);

    // Resolve county: route param, else first county available in this year.
    let selected = params?.county;
    if (!selected || !countyEverAvailable(selected)) {
        selected = COUNTY_ORDER.find(c => countyEntryFor(fy, c)?.available)
            || COUNTY_ORDER.find(countyEverAvailable) || 'honolulu';
    }
    countyState.county = selected;
    countyState.fy = fy;

    const tabs = COUNTY_ORDER.map(slug => {
        // Use any year's entry for the display name.
        const c = years.map(y => countyEntryFor(y, slug)).find(Boolean);
        if (!c) return '';
        const label = escapeHtml(countyShortName(c.name));
        if (!countyEverAvailable(slug)) {
            return `<span class="county-tab county-tab-disabled" title="${escapeHtml(c.name)} — coming soon">${label}<span class="county-tab-soon">soon</span></span>`;
        }
        return `<a href="#/counties/${slug}" class="county-tab ${slug === selected ? 'active' : ''}" title="${escapeHtml(c.name)}">${label}</a>`;
    }).join('');

    const yearBtns = years.map(y =>
        `<button type="button" class="county-year-btn ${y === fy ? 'active' : ''}" data-fy="${y}">FY${y}</button>`
    ).join('');

    const name = countyEntryFor(fy, selected)?.name
        || years.map(y => countyEntryFor(y, selected)).find(Boolean)?.name || '';

    return `
        <section class="compare-page counties-page">
            <div class="county-toolbar">
                <nav class="county-tabs" aria-label="County">${tabs}</nav>
                <div class="county-year-toggle" role="group" aria-label="Fiscal year">
                    <span class="county-year-label">Fiscal year</span>
                    ${yearBtns}
                </div>
            </div>
            <h2 class="county-title" id="county-title">${escapeHtml(name)}</h2>
            <div id="county-body"></div>
        </section>`;
};

// Render the operating department table (expandable to program → fund detail).
function renderCountyOperating(op, expanded) {
    if (!op || !op.departments?.length) return '';
    const rowLabel = op.row_label || 'Department';
    const lc = rowLabel.toLowerCase();
    return `
        <div class="county-section county-operating-section">
            <div class="county-section-head">
                <h3 class="county-section-title">Operating budget</h3>
                <span class="county-section-total">${fmt(op.total)}</span>
            </div>
            <div class="county-overview">
                ${fundDonutBlock('cdonut-op', op.fund_breakdown,
                    { title: 'Where it comes from · by fund', centerLabel: 'operating',
                      aria: 'Operating budget by fund category' })}
                ${treemapBlock('ctreemap-op', `Where it goes · by ${lc}`,
                    `Operating budget by ${lc}`)}
            </div>
            <div class="county-op-table-wrap">${countyOpTableHTML(op, expanded)}</div>
        </div>`;
}

// The operating department/fund table — re-rendered on its own when a row is
// expanded, so the charts above it aren't torn down and rebuilt each click.
function countyOpTableHTML(op, expanded) {
    const rowLabel = op.row_label || 'Department';
    const rowLabelPlural = rowLabel === 'Fund' ? 'funds' : 'departments';
    const maxBudget = Math.max(...op.departments.map(d => d.total_budget), 1);
    let body = '<tbody>';
    for (const d of op.departments) {
        const pct = op.total ? (d.total_budget / op.total * 100) : 0;
        const barColor = countyFundColor(_dominantFund(d.fund_breakdown));
        // A single synthetic "(department-wide)" program means there's no real
        // program detail to drill into (Maui dept-level, Hawaiʻi fund-level).
        const hasDetail = !(d.num_programs <= 1
            && d.programs?.[0]?.program_name === '(department-wide)');
        const isOpen = hasDetail && expanded.has('op:' + d.code);
        body += `<tr class="county-dept-row ${hasDetail ? '' : 'county-dept-flat'} ${isOpen ? 'open' : ''}" ${hasDetail ? `data-key="op:${escapeHtml(d.code)}"` : ''}>
            <td>${hasDetail ? `<span class="county-row-chevron" aria-hidden="true">${isOpen ? '▾' : '▸'}</span>` : ''}${escapeHtml(d.name)}${hasDetail ? `<span class="county-prog-count">${d.num_programs} program${d.num_programs === 1 ? '' : 's'}</span>` : ''}</td>
            <td class="amount-cell"><span class="figure-chip">${fmtHtml(d.total_budget)}</span></td>
            <td class="county-share-cell">
                <span class="county-share-bar"><span class="county-share-fill" style="width:${(d.total_budget / maxBudget * 100).toFixed(1)}%;background:${barColor}"></span></span>
                <span class="county-share-pct">${pct >= 1 ? pct.toFixed(0) + '%' : '<1%'}</span>
            </td>
        </tr>`;
        if (isOpen) {
            body += d.programs.map(p => {
                const funds = p.funds || [];
                const fundDetail = funds.length === 1
                    ? `<span class="county-prog-fund">${escapeHtml(funds[0].fund_name)}</span>`
                    : `<span class="county-prog-funds">${funds.map(f =>
                        `<span class="county-fund-chip">${escapeHtml(f.fund_name)} ${fmtHtml(f.amount)}</span>`).join('')}</span>`;
                return `<tr class="county-prog-row">
                    <td class="county-prog-name">${escapeHtml(p.program_name)}${fundDetail}</td>
                    <td class="amount-cell"><span class="figure-chip">${fmtHtml(p.total_budget)}</span></td>
                    <td></td>
                </tr>`;
            }).join('');
        }
    }
    body += '</tbody>';
    return `<table class="data-table county-table">
        <thead><tr>
            <th>${escapeHtml(rowLabel)}</th>
            <th class="amount-cell">Budget</th>
            <th>Share</th>
        </tr></thead>
        ${body}
        <tbody class="totals-block"><tr class="totals-row">
            <td>Total <span class="totals-meta">${op.num_departments} ${rowLabelPlural}</span></td>
            <td class="amount-cell"><span class="figure-chip">${fmtHtml(op.total)}</span></td>
            <td></td>
        </tr></tbody>
    </table>`;
}

// Render the CIP block: fund donut + by-function bars, then a searchable,
// sortable project list (the list re-renders on its own — see cipResultsHTML).
function renderCountyCip(cip, ui) {
    if (!cip) return '';
    const maxFn = Math.max(...cip.functions.map(f => f.total_budget), 1);
    const fnBars = cip.functions.slice().sort((a, b) => b.total_budget - a.total_budget).map(f => `
        <li class="cfn-row">
            <span class="cfn-name">${escapeHtml(f.name)}</span>
            <span class="cfn-bar"><span class="cfn-fill" style="width:${(f.total_budget / maxFn * 100).toFixed(1)}%;background:${countyFundColor(_dominantFund(f.fund_breakdown))}"></span></span>
            <span class="cfn-amt">${fmtCompact(f.total_budget)}</span>
        </li>`).join('');
    return `
        <div class="county-section county-cip-section">
            <div class="county-section-head">
                <h3 class="county-section-title">Capital improvement program <span class="county-section-tag">CIP</span></h3>
                <span class="county-section-total">${fmt(cip.total)}</span>
            </div>
            <div class="county-overview">
                ${fundDonutBlock('cdonut-cip', cip.fund_breakdown,
                    { title: 'How it’s financed · by fund', centerLabel: 'capital',
                      aria: 'Capital program by fund category' })}
                <div class="county-viz county-viz-fns">
                    <div class="county-viz-title">Where it goes · by function</div>
                    <ul class="cfn-list">${fnBars}</ul>
                </div>
            </div>
            <div class="cip-results-wrap">${cipResultsHTML(cip, ui)}</div>
        </div>`;
}

// Toolbar + filtered/sorted project table — swapped in place on search/sort so
// the donut and function bars above are never rebuilt.
function cipResultsHTML(cip, ui) {
    const q = (ui.cipQuery || '').trim().toLowerCase();
    let projects = cip.projects.filter(p =>
        !q || p.project_name.toLowerCase().includes(q) || p.function.toLowerCase().includes(q)
        || (p.primary_fund || '').toLowerCase().includes(q));
    projects.sort((a, b) => ui.cipSort === 'name'
        ? a.project_name.localeCompare(b.project_name)
        : b.total_budget - a.total_budget);

    const rows = projects.map(p => {
        const funds = p.funds || [];
        const fundCell = funds.length <= 1
            ? escapeHtml(p.primary_fund || '—')
            : `${escapeHtml(p.primary_fund)} <span class="cip-fund-more">+${funds.length - 1}</span>`;
        return `<tr class="cip-project-row" title="${escapeHtml(funds.map(f => f.fund_name + ' ' + fmt(f.amount)).join(' · '))}">
            <td class="cip-proj-name"><span class="cip-fund-dot" style="background:${countyFundColor(p.fund_category)}"></span>${highlight(p.project_name, q)}<span class="cip-proj-func">${escapeHtml(p.function)}</span></td>
            <td class="cip-proj-fund">${fundCell}</td>
            <td class="amount-cell"><span class="figure-chip">${fmtHtml(p.total_budget)}</span></td>
        </tr>`;
    }).join('') || `<tr><td colspan="3" class="cip-empty">No projects match “${escapeHtml(ui.cipQuery)}”.</td></tr>`;

    return `
        <div class="cip-toolbar">
            <input type="search" id="cip-search" class="cip-search" placeholder="Search ${cip.num_projects} projects…" value="${escapeHtml(ui.cipQuery || '')}" aria-label="Search CIP projects">
            <div class="cip-sort" role="group" aria-label="Sort">
                <button type="button" class="cip-sort-btn ${ui.cipSort !== 'name' ? 'active' : ''}" data-sort="amount">Largest</button>
                <button type="button" class="cip-sort-btn ${ui.cipSort === 'name' ? 'active' : ''}" data-sort="name">A–Z</button>
            </div>
        </div>
        <table class="data-table cip-table">
            <thead><tr>
                <th>Project</th>
                <th>Funding source</th>
                <th class="amount-cell">Amount</th>
            </tr></thead>
            <tbody>${rows}</tbody>
        </table>
        <p class="cip-note">${cip.num_projects} projects across ${cip.num_functions} budget functions${q ? ` · ${projects.length} shown` : ''}. Capital figures are parsed from the budget ordinance PDF and reconcile to the published total within ~0.3%.</p>`;
}

function renderCountyBody() {
    const bodyEl = document.getElementById('county-body');
    const titleEl = document.getElementById('county-title');
    if (!bodyEl) return;
    const { county, fy } = countyState;
    const c = countyEntryFor(fy, county);
    if (titleEl) {
        const name = c?.name || countyFyList().map(y => countyEntryFor(y, county)).find(Boolean)?.name || '';
        titleEl.textContent = name;
    }
    if (!c || !c.available) {
        destroyCountyCharts();
        const ever = countyEverAvailable(county);
        bodyEl.innerHTML = `<div class="empty-state">
            <p>${ever
                ? `No budget published for <strong>FY${fy}</strong> yet.`
                : `${escapeHtml(c?.name || 'This county')} budget data is coming soon.`}</p>
            <p>${ever
                ? 'Pick another fiscal year above.'
                : 'The county publishes its budget as ordinance PDFs; a parser for it is planned.'}</p>
        </div>`;
        return;
    }

    const ui = countyState.ui || (countyState.ui = { expanded: new Set(), cipQuery: '', cipSort: 'amount' });
    bodyEl.innerHTML = `
        ${renderCountyHero(c, fy)}
        ${c.coverage_note ? `<p class="county-caveat">${escapeHtml(c.coverage_note)}</p>` : ''}
        ${renderCountyOperating(c.operating, ui.expanded)}
        ${renderCountyCip(c.cip, ui)}
        <p class="county-source">Source: <a href="${escapeHtml(c.source.url)}" target="_blank" rel="noopener">${escapeHtml(c.source.label)}</a> · FY${fy}</p>`;

    // Charts are created after their canvases land in the DOM; this also
    // destroys the previous render's instances so detached canvases never leak.
    mountCountyCharts(c);
}

window.initCountiesPage = function () {
    if (!countyBudgetsData?.years) return;
    countyState.ui = { expanded: new Set(), cipQuery: '', cipSort: 'amount' };
    renderCountyBody();

    // Year toggle — re-render the body in place (county tabs are real links).
    document.querySelector('.county-year-toggle')?.addEventListener('click', (e) => {
        const btn = e.target.closest('.county-year-btn');
        if (!btn) return;
        countyState.fy = btn.getAttribute('data-fy');
        document.querySelectorAll('.county-year-btn').forEach(b =>
            b.classList.toggle('active', b === btn));
        renderCountyBody();
    });

    // Body interactions. Expand / sort / search re-render only their own table
    // region — never the whole body — so the Chart.js charts above survive.
    const bodyEl = document.getElementById('county-body');
    const curEntry = () => countyEntryFor(countyState.fy, countyState.county);

    bodyEl?.addEventListener('click', (e) => {
        const deptRow = e.target.closest('tr.county-dept-row');
        if (deptRow) {
            const key = deptRow.getAttribute('data-key');
            if (!key) return;                 // flat rows (no program detail)
            const ex = countyState.ui.expanded;
            ex.has(key) ? ex.delete(key) : ex.add(key);
            const c = curEntry();
            const wrap = document.querySelector('.county-op-table-wrap');
            if (wrap && c?.operating) wrap.innerHTML = countyOpTableHTML(c.operating, ex);
            return;
        }
        const sortBtn = e.target.closest('.cip-sort-btn');
        if (sortBtn) {
            countyState.ui.cipSort = sortBtn.getAttribute('data-sort');
            const c = curEntry();
            const wrap = document.querySelector('.cip-results-wrap');
            if (wrap && c?.cip) wrap.innerHTML = cipResultsHTML(c.cip, countyState.ui);
        }
    });
    bodyEl?.addEventListener('input', (e) => {
        const search = e.target.closest('#cip-search');
        if (!search) return;
        countyState.ui.cipQuery = search.value;
        // Re-render only the CIP results so the donut/function bars and the
        // input's focus/caret are preserved.
        const c = curEntry();
        const wrap = document.querySelector('.cip-results-wrap');
        if (wrap && c?.cip) {
            wrap.innerHTML = cipResultsHTML(c.cip, countyState.ui);
            const input = document.getElementById('cip-search');
            if (input) { input.focus(); input.setSelectionRange(input.value.length, input.value.length); }
        }
    });
};
