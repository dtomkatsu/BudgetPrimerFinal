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
// Home Page
// ---------------------------------------------------------------------------

window.homePage = async function () {
    if (!departmentsData?.length || !summaryStats) {
        return `<section class="home-page"><div class="loading"><div class="spinner"></div><p>Loading...</p></div></section>`;
    }

    const grandTotal = summaryStats.total_budget;
    const positions = summaryStats.total_positions;

    const deptCard = (dept) => {
        const op = dept.operating_budget || 0;
        const cap = dept.capital_budget || 0;
        const ot = dept.one_time_appropriations || 0;
        const total = op + cap + ot;
        const pos = dept.positions;
        return `
            <a href="#/department/${dept.id}" class="department-card">
                <h3>${dept.name}</h3>
                <div class="card-content">
                    <div class="budget-total">
                        <span>Total Budget</span>
                        <strong>${fmt(total)}</strong>
                    </div>
                    <div class="budget-breakdown">
                        <div class="budget-row"><span>Operating</span><span>${fmt(op)}</span></div>
                        ${cap > 0 ? `<div class="budget-row"><span>Capital</span><span>${fmt(cap)}</span></div>` : ''}
                        ${ot > 0 ? `<div class="budget-row"><span>One-Time</span><span>${fmt(ot)}</span></div>` : ''}
                        ${pos ? `<div class="budget-row"><span>Positions</span><span>${pos.toLocaleString(undefined,{maximumFractionDigits:0})}</span></div>` : ''}
                    </div>
                </div>
            </a>`;
    };

    const sorted = sortDepartments('desc');

    const html = `
        <section class="home-page">
            <div class="context-banner"><strong>Historical reference:</strong> This is the FY2025–26 enacted budget (HB300), passed by the Legislature last year. For the current FY2026–27 supplemental budget draft comparison, see <a href="#/">HB1800 →</a></div>
            <div class="summary-cards-grid">
                <div class="summary-card"><div class="amount">${fmtHtmlCard(grandTotal)}</div><div class="label">Total Budget</div><div class="label-sub">(FY 2026)</div></div>
                <div class="summary-card"><div class="amount">${fmtHtmlCard(summaryStats.operating_budget)}</div><div class="label">Operating</div></div>
                <div class="summary-card"><div class="amount">${fmtHtmlCard(summaryStats.capital_budget)}</div><div class="label">Capital</div></div>
                ${positions ? `<div class="summary-card"><div class="amount">${positions.toLocaleString(undefined,{maximumFractionDigits:0})}</div><div class="label">Total Positions</div></div>` : ''}
            </div>
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
            <div class="department-grid" id="dept-grid">${sorted.map(deptCard).join('')}</div>
        </section>`;

    setTimeout(() => {
        document.querySelectorAll('.sort-btn').forEach(btn => {
            btn.addEventListener('click', function () {
                const s = sortDepartments(this.dataset.sort);
                document.getElementById('dept-grid').innerHTML = s.map(deptCard).join('');
                document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
            });
        });
        document.getElementById('export-depts')?.addEventListener('click', () => {
            const rows = departmentsData.map(d => ({
                code: d.code, name: d.name, operating: d.operating_budget,
                capital: d.capital_budget, one_time: d.one_time_appropriations,
                total: (d.operating_budget||0)+(d.capital_budget||0)+(d.one_time_appropriations||0),
                positions: d.positions || '',
            }));
            downloadCSV(rows, 'departments_fy2026.csv');
        });
    }, 0);

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

    // Fund breakdown for this department
    const fundBreakdown = dept.fund_breakdown || {};
    const fundRows = Object.entries(fundBreakdown)
        .sort(([, a], [, b]) => b - a)
        .map(([fund, amt]) => `<tr><td>${fund}</td><td class="amount-cell">${fmt(amt)}</td><td class="amount-cell">${(amt / total * 100).toFixed(1)}%</td></tr>`)
        .join('');

    const programRows = progList.map(p => `
        <tr>
            <td><strong>${p.id}</strong></td>
            <td>${p.name}</td>
            <td class="amount-cell">${fmt(p.operating)}</td>
            <td class="amount-cell">${p.capital > 0 ? fmt(p.capital) : '—'}</td>
            <td class="amount-cell">${fmt(p.total)}</td>
            <td class="amount-cell">${p.positions ? p.positions.toLocaleString(undefined,{maximumFractionDigits:0}) : '—'}</td>
        </tr>`).join('');

    return `
        <section class="department-detail">
            <a href="#/enacted" class="back-button">← Back to HB300 Budget</a>
            <div class="department-header">
                <h2>${dept.name} (${dept.code})</h2>
                ${dept.description ? `<p class="dept-desc">${dept.description}</p>` : ''}
            </div>

            <div class="summary-cards-grid">
                <div class="summary-card"><div class="amount">${fmtHtmlCard(total)}</div><div class="label">Total</div></div>
                <div class="summary-card"><div class="amount">${fmtHtmlCard(dept.operating_budget)}</div><div class="label">Operating</div></div>
                <div class="summary-card"><div class="amount">${fmtHtmlCard(dept.capital_budget)}</div><div class="label">Capital</div></div>
                ${dept.positions ? `<div class="summary-card"><div class="amount">${dept.positions.toLocaleString(undefined,{maximumFractionDigits:0})}</div><div class="label">Positions</div></div>` : ''}
            </div>

            <h3>Fund Type Breakdown</h3>
            <table class="data-table">
                <thead><tr><th>Fund Type</th><th>Amount</th><th>% of Dept</th></tr></thead>
                <tbody>${fundRows}</tbody>
            </table>

            <h3>Programs (${progList.length})</h3>
            <button class="action-link export-btn" id="export-programs">⬇ Export Programs CSV</button>
            <table class="data-table programs-table">
                <thead><tr><th>ID</th><th>Program</th><th>Operating</th><th>Capital</th><th>Total</th><th>Positions</th></tr></thead>
                <tbody>${programRows}</tbody>
            </table>
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
        <div class="fy-seg-ctrl">
            <button id="fy-btn-26" data-fy="26" class="active">FY2026</button>
            <button id="fy-btn-27" data-fy="27">FY2027</button>
        </div>` : (draftComparisonDataFY27 ? '<div class="fy-seg-ctrl"><button class="active" data-fy="27">FY2027</button></div>' : '');

    return `
        <section class="compare-page">
            <div class="compare-page-titlerow">
                <h2>HB 1800 · Draft Comparison</h2>
                <span class="compare-info-icon reading-guide-pill" id="reading-guide-box" tabindex="0">
                    ⓘ How to read this
                    <div class="reading-guide-panel">
                        <p class="reading-guide-summary">Not every change is a real cut or increase — some reflect <strong>funds being reshuffled between departments</strong>.</p>
                        <p><strong>In the House draft (HD1), capital projects are sometimes listed under AGS (Accounting &amp; General Services) as a placeholder.</strong> In addition, some programs, like Rental Housing, receive funding from multiple departments (e.g., HMS and BED).</p>
                        <p>Badges on program rows explain what kind of change occurred:<br>
                        <span class="transfer-badge transfer-pure" style="display:inline;pointer-events:none;">→ Moved to dept</span> — funds shifted between departments; total unchanged.<br>
                        <span class="transfer-badge transfer-partial" style="display:inline;pointer-events:none;">→ Partly moved to dept</span> — partial transfer with a net change.<br>
                        <span class="data-note" style="pointer-events:none;">⚠</span> — known data anomaly; hover for details.<br>
                        <span class="fund-note" style="pointer-events:none;">ℹ bond-financed capital projects</span> — in the Fund Detail section below.</p>
                    </div>
                </span>
            </div>
            <p class="compare-page-desc">Compare the Governor's request, House Draft 1, and Senate Draft 1 to see what was added, cut, or moved.</p>
            <div class="compare-controls-bar">
                ${fyToggle}
                <span class="ctrl-divider-v"></span>
                <div class="compare-timeline" id="compare-timeline">
                    <div class="tl-node" id="tl-node-gov">
                        <span class="tl-label">Gov.</span>
                        <div class="tl-dot-row">
                            <span class="tl-seg tl-seg-before"></span>
                            <label class="tl-dot-lbl" for="tl-gov"><span class="tl-dot"></span></label>
                            <span class="tl-seg tl-seg-after"></span>
                        </div>
                        <div class="tl-amt-wrap">
                            <button class="tl-expand-caret" id="tl-expand-btn" aria-label="Show breakdown">▾</button>
                            <span class="tl-amt" id="tl-amt-gov"></span>
                        </div>
                        <div class="tl-breakdown" id="tl-bd-gov" hidden></div>
                        <input type="checkbox" class="tl-cb" id="tl-gov" checked>
                    </div>
                    <div class="tl-node" id="tl-node-hd1">
                        <span class="tl-label">HD1</span>
                        <div class="tl-dot-row">
                            <span class="tl-seg tl-seg-before"></span>
                            <label class="tl-dot-lbl" for="tl-hd1"><span class="tl-dot"></span></label>
                            <span class="tl-seg tl-seg-after"></span>
                        </div>
                        <span class="tl-amt" id="tl-amt-hd1"></span>
                        <div class="tl-breakdown" id="tl-bd-hd1" hidden></div>
                        <input type="checkbox" class="tl-cb" id="tl-hd1" checked>
                    </div>
                    <div class="tl-node" id="tl-node-sd1">
                        <span class="tl-label">SD1</span>
                        <div class="tl-dot-row">
                            <span class="tl-seg tl-seg-before"></span>
                            <label class="tl-dot-lbl" for="tl-sd1"><span class="tl-dot"></span></label>
                            <span class="tl-seg tl-seg-after"></span>
                        </div>
                        <span class="tl-amt" id="tl-amt-sd1"></span>
                        <div class="tl-breakdown" id="tl-bd-sd1" hidden></div>
                        <input type="checkbox" class="tl-cb" id="tl-sd1" checked>
                    </div>
                    <!-- Net change node — 4th timeline node (derived, visually separated) -->
                    <div class="tl-node tl-net-node" id="tl-node-net">
                        <span class="tl-label">Net Change</span>
                        <div class="tl-net-spark-row">
                            <svg class="tl-net-spark" id="tl-net-spark" viewBox="0 0 60 20" aria-hidden="true"></svg>
                        </div>
                        <span class="tl-amt tl-net-chip" id="tl-amt-net"></span>
                        <div class="tl-breakdown" id="tl-bd-net" hidden></div>
                    </div>
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

        // Update main Total amounts directly under each dot
        [
            { id: 'tl-amt-gov', val: totGov },
            { id: 'tl-amt-hd1', val: totHD1 },
            { id: 'tl-amt-sd1', val: totSD1 },
        ].forEach(({ id, val }) => {
            const el = document.getElementById(id);
            if (el) el.textContent = fmtShort(val);
        });

        // Populate Operating / Capital breakdown sub-chips (shown only when expanded)
        const signed = (n) => (n > 0 ? '+' : '') + fmtShort(n);
        const bd = [
            { id: 'tl-bd-gov', opV: op.baseline,        capV: cap.baseline,        isNet: false },
            { id: 'tl-bd-hd1', opV: op.hd1,             capV: cap.hd1,             isNet: false },
            { id: 'tl-bd-sd1', opV: op.d2,              capV: cap.d2,              isNet: false },
            { id: 'tl-bd-net', opV: op.d2 - op.d1,      capV: cap.d2 - cap.d1,     isNet: true  },
        ];
        bd.forEach(({ id, opV, capV, isNet }) => {
            const el = document.getElementById(id);
            if (!el) return;
            const fmt = isNet ? signed : fmtShort;
            el.innerHTML =
                `<span class="tl-bd-row"><span class="tl-bd-lbl">Op</span>${fmt(opV)}</span>` +
                `<span class="tl-bd-row"><span class="tl-bd-lbl">Cap</span>${fmt(capV)}</span>`;
            el.hidden = !showBreakdown;
        });

        // Update the 4th Net Change timeline node
        const netNode  = document.getElementById('tl-node-net');
        if (netNode) netNode.className = `tl-node tl-net-node ${netCls}`;
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
                `<span class="tl-net-arrow" aria-hidden="true">${arrow}</span>` +
                `<span class="tl-net-val">${sign}${fmtShort(tabNet)}</span>` +
                `<span class="tl-net-pct">${pct}</span>`;
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
        if (expandBtn) expandBtn.textContent = showBreakdown ? '▴' : '▾';

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
            + `<input type="text" id="draft-search" class="search-input search-inline" placeholder="Search..." value="${searchVal.replace(/"/g, '&quot;')}">`;
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
            const arrow = sortCol === col ? (sortDir === 'asc' ? ' ▲' : ' ▼') : '';
            return arrow;
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
            const deptD1 = dept.d1;
            const deptD2 = dept.d2;
            const deptDelta = dept.delta;
            const deptCls = deptDelta > 0 ? 'positive' : deptDelta < 0 ? 'negative' : '';
            const isOpen = autoExpand || expandedDepts.has(dept.code);
            const arrow = isOpen ? '▼' : '▶';

            const programs = aggregatePrograms(dept.rows);

            // Reconciliation badge: when cross-dept aggregation makes split programs show
            // a change that differs from the slice of money actually booked to this dept,
            // the numbers won't appear to add up. Explain it in plain language.
            // Mismatch = dept.delta − sum(programs.change). For each split program,
            // its individual contribution to the mismatch is:
            //   contribution = (dept-scoped change) − (augmented program.change)
            // Only programs with non-trivial contribution are listed.
            const MISMATCH_THRESHOLD = 1000000;    // $1M — minimum dept-level mismatch to show badge
            const PROG_CONTRIB_THRESHOLD = 100000; // $100K — minimum per-program contribution to list
            const programChangeSum = programs.reduce((s, p) => s + p.change, 0);
            const mismatch = dept.delta - programChangeSum;

            // Tag each split program with its individual contribution and direction
            const affectedPrograms = programs
                .filter(p => splitPrograms.has(p.program_id) && p.crossDeptAugmented && p.crossDeptAugmented.size > 0)
                .map(p => {
                    const deptScopedChange = (p.d2DeptScope || 0) - (p.d1DeptScope || 0);
                    const contribution = deptScopedChange - p.change;
                    return { ...p, contribution };
                })
                .filter(p => Math.abs(p.contribution) >= PROG_CONTRIB_THRESHOLD);

            let deptTransferNote = '';
            if (Math.abs(mismatch) >= MISMATCH_THRESHOLD && affectedPrograms.length > 0) {
                // Title-case a program name while preserving parenthesized acronyms: (HYCF), (DHS), etc.
                const prettyName = (name) => (name || '').split(' ').map(word => {
                    if (/^\([A-Z]+\)$/.test(word)) return word;
                    return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
                }).join(' ');

                const incoming = affectedPrograms.filter(p => p.contribution > 0);
                const outgoing = affectedPrograms.filter(p => p.contribution < 0);
                const isMixed = incoming.length > 0 && outgoing.length > 0;

                const listProgs = (arr) => arr.map(p => `${p.program_id} ${prettyName(p.program_name)}`).join(', ');

                let badgeLabel, tooltip;
                if (isMixed) {
                    badgeLabel = 'some program funding shifted between departments';
                    tooltip = `Some funding for programs (${listProgs(incoming)}) is routed through ${dept.code} from other departments, while funding for (${listProgs(outgoing)}) is routed from ${dept.code} to other departments. The programs still get the same money — the budget just records which department holds the line item. That's why this row has a change but the program rows show $0 change.`;
                } else if (incoming.length > 0) {
                    badgeLabel = 'some program funding routed through this dept';
                    tooltip = `Part of the funding for (${listProgs(incoming)}) is routed through ${dept.code} even though the programs are run by other departments. The programs still get the same money — the budget just records which department holds the line item. That's why this row's total went up but the program rows show $0 change.`;
                } else {
                    badgeLabel = 'some program funding routed through other depts';
                    tooltip = `Part of the funding for (${listProgs(outgoing)}) is now routed through other departments instead of ${dept.code}. The programs still get the same money — the budget just records which department holds the line item. That's why this row's total went down but the program rows show $0 change.`;
                }
                const tooltipEscaped = tooltip.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
                deptTransferNote = ` <span class="dept-transfer-note" title="${tooltipEscaped}">↔ ${badgeLabel}</span>`;
            }

            bodyHtml += `<tr class="dept-group-row${isOpen ? ' open' : ''}" data-dept="${dept.code}">
                <td><span class="dept-arrow">${arrow}</span> <strong>${dept.code}</strong> ${dept.name} <span class="dept-count">(${programs.length} programs)</span>${deptTransferNote}</td>
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

                // Cross-reference note for programs split across departments
                const splitDeptMap = splitPrograms.get(p.program_id);
                let crossRefNote = '';
                let transferBadge = '';
                if (splitDeptMap) {
                    const otherDepts = [...splitDeptMap.keys()].filter(d => d !== dept.code);
                    const thisDelta = splitDeptMap.get(dept.code)?.delta || 0;
                    const THRESHOLD = 1000000; // $1M minimum to flag

                    const fmtNet = (v) => {
                        const sign = v < 0 ? '−' : '+';
                        const abs = Math.abs(v);
                        if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(1)}B`;
                        if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`;
                        return `${sign}$${(abs / 1e3).toFixed(0)}K`;
                    };
                    const fmtAbs = (v) => fmtNet(Math.abs(v)).slice(1); // strip leading sign

                    // Find depts with a meaningfully offsetting change
                    const offsetDepts = otherDepts.filter(d => {
                        const od = splitDeptMap.get(d)?.delta || 0;
                        return Math.abs(thisDelta) > THRESHOLD && Math.abs(od) > THRESHOLD &&
                               ((thisDelta < 0 && od > 0) || (thisDelta > 0 && od < 0));
                    });

                    if (offsetDepts.length > 0) {
                        const allInvolved = [dept.code, ...offsetDepts];
                        const totalNet = allInvolved.reduce((s, d) => s + (splitDeptMap.get(d)?.delta || 0), 0);
                        const isPure = Math.abs(totalNet) < Math.abs(thisDelta) * 0.15;

                        // Direction is uniform: if this dept decreased, money moved OUT (→); if increased, moved IN (←)
                        const movedOut = thisDelta < 0;
                        const dirIcon = movedOut ? '→' : '←';
                        const verb = movedOut ? 'Moved to' : 'Moved from';
                        const partialVerb = movedOut ? 'Partly moved to' : 'Partly moved from';

                        const offsetParts = offsetDepts.map(d => {
                            const od = splitDeptMap.get(d)?.delta || 0;
                            return `<a class="transfer-link" href="javascript:void(0)" data-scroll-dept="${d}">${d}</a> (${fmtAbs(od)})`;
                        }).join(', ');

                        if (isPure) {
                            transferBadge = `<span class="transfer-badge transfer-pure" title="Funds moved between departments — total program funding is unchanged.">${dirIcon} ${verb} ${offsetParts}</span>`;
                        } else {
                            const netLabel = fmtNet(totalNet);
                            const netDesc = totalNet < 0 ? 'net cut' : 'net add';
                            transferBadge = `<span class="transfer-badge transfer-partial" title="Part of this change reflects an inter-department transfer. Net change across all involved departments: ${netLabel}.">${dirIcon} ${partialVerb} ${offsetParts}; ${netDesc}: ${netLabel}</span>`;
                        }
                    } else {
                        // No offsetting change — just show a quiet cross-link in the name column
                        const otherLinks = otherDepts
                            .map(d => `<a class="split-link" href="javascript:void(0)" data-scroll-dept="${d}">${d}</a>`)
                            .join(', ');
                        crossRefNote = ` <span class="split-note">also in ${otherLinks}</span>`;
                    }
                }
                const dataNoteHtml = buildDataNote(p.program_id, activeYear);

                if (p.isMixed) {
                    const progArrow = progOpen ? '▼' : '▶';
                    bodyHtml += `<tr class="dept-detail-row prog-group-row${isOpen ? '' : ' hidden'}" data-dept="${dept.code}" data-prog="${progKey}">
                        <td class="detail-indent"><span class="dept-arrow">${progArrow}</span> <strong>${p.program_id}</strong> ${p.program_name}${crossRefNote}${dataNoteHtml}</td>
                        <td><span class="section-chip">Mixed</span></td>
                        <td>${p.fundShort ? `<span class="fund-chip${p.fundTitle ? ' fund-chip-multi' : ''}"${p.fundTitle ? ` data-funds="${p.fundTitle}"` : ''}>${p.fundShort}</span>` : ''}</td>
                        <td class="amount-cell"><span class="figure-chip">${fmtHtml(p.d1)}</span></td>
                        ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(p.hd1)}</span></td>` : ''}
                        <td class="amount-cell"><span class="figure-chip">${fmtHtml(p.d2)}</span></td>
                        <td class="amount-cell ${cls}"><span class="figure-chip">${fmtHtml(p.change)}</span>${transferBadge}</td>
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
                                    <td class="fund-indent fund-indent-deep"><span class="fund-chip">${shortFund(fc)}</span> <span class="fund-name-full">${fc}</span></td>
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
                    bodyHtml += `<tr class="dept-detail-row prog-fund-group${isOpen ? '' : ' hidden'}" data-dept="${dept.code}" data-fund-key="${fundKey}">
                        <td class="detail-indent"><span class="dept-arrow">${fundArrow}</span> <strong>${p.program_id}</strong> ${p.program_name}${crossRefNote}${dataNoteHtml}</td>
                        <td>${progChipHtml}</td>
                        <td><span class="fund-chip fund-chip-multi" data-funds="${p.fundTitle}">${p.fundShort}</span></td>
                        <td class="amount-cell"><span class="figure-chip">${fmtHtml(p.d1)}</span></td>
                        ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(p.hd1)}</span></td>` : ''}
                        <td class="amount-cell"><span class="figure-chip">${fmtHtml(p.d2)}</span></td>
                        <td class="amount-cell ${cls}"><span class="figure-chip">${fmtHtml(p.change)}</span>${transferBadge}</td>
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
                            <td class="fund-indent"><span class="fund-chip">${shortFund(fc)}</span> <span class="fund-name-full">${fc}</span></td>
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
                    bodyHtml += `<tr class="dept-detail-row${isOpen ? '' : ' hidden'}" data-dept="${dept.code}">
                        <td class="detail-indent"><strong>${p.program_id}</strong> ${p.program_name}${crossRefNote}${dataNoteHtml}</td>
                        <td>${progChipHtml}</td>
                        <td>${p.fundShort ? `<span class="fund-chip${p.fundTitle ? ' fund-chip-multi' : ''}"${p.fundTitle ? ` data-funds="${p.fundTitle}"` : ''}>${p.fundShort}</span>` : ''}</td>
                        <td class="amount-cell"><span class="figure-chip">${fmtHtml(p.d1)}</span></td>
                        ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(p.hd1)}</span></td>` : ''}
                        <td class="amount-cell"><span class="figure-chip">${fmtHtml(p.d2)}</span></td>
                        <td class="amount-cell ${cls}"><span class="figure-chip">${fmtHtml(p.change)}</span>${transferBadge}</td>
                    </tr>`;
                }
            }
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
            fundHtml += `<tr class="fund-group-row${isOpen ? ' open' : ''}" data-fund-type="${fg.type}">
                <td><span class="dept-arrow">${arrow}</span> <strong>${fg.type}</strong> — ${fg.category}${fundNote} <span class="dept-count">(${fg.rows.length})</span></td>
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(fgD1)}</span></td>
                ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(fgHD1)}</span></td>` : ''}
                <td class="amount-cell"><span class="figure-chip">${fmtHtml(fgD2)}</span></td>
                <td class="amount-cell ${fgCls}"><span class="figure-chip">${fmtHtml(fgDelta)}</span></td>
                <td></td>
            </tr>`;

            for (const r of fg.rows) {
                const delta = r[d2Key] - r[d1Key];
                const cls = delta > 0 ? 'positive' : delta < 0 ? 'negative' : '';
                const dynPct = r[d1Key] !== 0 ? ((delta / Math.abs(r[d1Key])) * 100) : (delta !== 0 ? 100 : 0);
                fundHtml += `<tr class="fund-detail-row${isOpen ? '' : ' hidden'}" data-fund-type="${fg.type}">
                    <td class="detail-indent"><strong>${r.program_id || ''}</strong> ${r.program_name || ''}</td>
                    <td class="amount-cell"><span class="figure-chip">${fmtHtml(r[d1Key])}</span></td>
                    ${showHD1Col() ? `<td class="amount-cell"><span class="figure-chip">${fmtHtml(r[hd1Key] || 0)}</span></td>` : ''}
                    <td class="amount-cell"><span class="figure-chip">${fmtHtml(r[d2Key])}</span></td>
                    <td class="amount-cell ${cls}"><span class="figure-chip">${fmtHtml(delta)}</span></td>
                    <td class="amount-cell ${cls}">${fmtPct(dynPct)}</td>
                </tr>`;
            }
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
                <tbody>${bodyHtml}</tbody>
            </table>
            <div class="table-export-row"><button class="action-link export-btn" id="export-drafts">⬇ Export CSV</button></div>`;

        document.getElementById('fund-detail-section').innerHTML = `
            <h3 class="fund-detail-heading"><span class="has-tooltip" data-tooltip="A — General funds for everyday state spending&#10;B — Special funds set aside for specific purposes&#10;C — General obligation bond funds for public projects&#10;E — Revenue bond funds repaid from project earnings&#10;K/L/M/N — Federal aid funds from the U.S. government&#10;S — County funds from county governments&#10;T — Trust funds held for specific long-term purposes">Fund Detail</span></h3>
            <table class="data-table" id="fund-detail-table">
                <thead><tr>
                    <th>Fund / Program</th>
                    <th class="amount-cell">${getD1Label()}</th>
                    ${showHD1Col() ? '<th class="amount-cell">HD1</th>' : ''}
                    <th class="amount-cell">${getD2Label()}</th>
                    <th class="amount-cell">${getChangeLabel()}</th>
                    <th class="amount-cell">%</th>
                </tr></thead>
                <tbody>${fundHtml}</tbody>
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
            const delta = d2Total - d1Total;
            const deltaCls = delta > 0 ? 'positive' : delta < 0 ? 'negative' : '';
            const isOpen = expandedProjectPrograms.has(dept.code);
            const arrow = isOpen ? '▼' : '▶';

            // Dept group row — individual cells matching first table's dept row pattern
            bodyRows += `<tr class="dept-group-row project-dept-row${isOpen ? ' open' : ''}" data-project-dept="${dept.code}">
                <td colspan="3"><span class="dept-arrow">${arrow}</span> <strong>${dept.code}</strong> ${dept.name} <span class="dept-count">(${filteredProjects.length} project${filteredProjects.length === 1 ? '' : 's'})</span></td>
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
                    <td class="project-program-cell"><strong>${pr.program_id}</strong><div class="project-prog-name">${progName}</div></td>
                    <td class="project-num">${pr.project_id}</td>
                    <td><div class="project-name">${pr.project_name}</div>${scope}</td>
                    <td><span class="fund-chip">${shortFund(pr.fund_category)}</span></td>
                    ${govCell}
                    ${hd1Cell}
                    <td class="amount-cell"><span class="figure-chip">${fmtHtml(d2Amt)}</span></td>
                    <td class="amount-cell ${cls}"><span class="figure-chip">${fmtHtml(change)}</span> ${badge}</td>
                </tr>`;
            }
        }

        let html;
        if (visibleCount === 0) {
            html = `<div class="empty-state"><p>No capital projects match the current filter.</p></div>`;
        } else {
            const projSortArrow = (col) =>
                projSortCol === col ? (projSortDir === 'asc' ? ' ▲' : ' ▼') : '';
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
                <tbody>${bodyRows}</tbody>
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

    document.getElementById('draft-results')?.addEventListener('click', (e) => {
        // Cross-reference split-dept link: scroll to and expand that department
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
        const node = document.getElementById('tl-node-net');
        if (!node) return;
        node.classList.remove('tl-net-refresh');
        void node.offsetWidth; // force reflow so re-adding the class restarts the animation
        node.classList.add('tl-net-refresh');
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

        // Reflect inactive state visually on each node
        ['gov', 'hd1', 'sd1'].forEach(node => {
            const el = document.getElementById(`tl-node-${node}`);
            const cb = document.getElementById(`tl-${node}`);
            if (el) el.classList.toggle('tl-inactive', !(cb?.checked));
        });

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
window.initHomePage = async function () {};

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

