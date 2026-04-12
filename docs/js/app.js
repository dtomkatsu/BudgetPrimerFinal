// ---------------------------------------------------------------------------
// Global data
// ---------------------------------------------------------------------------
let departmentsData = [];
let summaryStats = null;
let programsData = [];
let fyComparisonData = [];
let draftComparisonData = null;     // FY2026 comparison
let draftComparisonDataFY27 = null; // FY2027 comparison

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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const fmt = (amount) => {
    if (amount == null) return '$0';
    if (Math.abs(amount) >= 1e9) return `$${(amount / 1e9).toFixed(1)}B`;
    if (Math.abs(amount) >= 1e6) return `$${(amount / 1e6).toFixed(1)}M`;
    if (Math.abs(amount) >= 1e3) return `$${(amount / 1e3).toFixed(0)}K`;
    return `$${amount.toLocaleString()}`;
};

const fmtPct = (v) => v != null ? `${v > 0 ? '+' : ''}${v.toFixed(1)}%` : '—';

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
            <div class="summary-cards-grid">
                <div class="summary-card"><div class="amount">${fmt(grandTotal)}</div><div class="label">Total Budget</div></div>
                <div class="summary-card"><div class="amount">${fmt(summaryStats.operating_budget)}</div><div class="label">Operating</div></div>
                <div class="summary-card"><div class="amount">${fmt(summaryStats.capital_budget)}</div><div class="label">Capital</div></div>
                <div class="summary-card"><div class="amount">${fmt(summaryStats.one_time_appropriations)}</div><div class="label">One-Time</div></div>
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
            <a href="#/" class="back-button">← Back to Home</a>
            <div class="department-header">
                <h2>${dept.name} (${dept.code})</h2>
                ${dept.description ? `<p class="dept-desc">${dept.description}</p>` : ''}
            </div>

            <div class="summary-cards-grid">
                <div class="summary-card"><div class="amount">${fmt(total)}</div><div class="label">Total</div></div>
                <div class="summary-card"><div class="amount">${fmt(dept.operating_budget)}</div><div class="label">Operating</div></div>
                <div class="summary-card"><div class="amount">${fmt(dept.capital_budget)}</div><div class="label">Capital</div></div>
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
            <a href="#/" class="back-button">← Home</a>
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
            <h2>About the Hawaii State Budget Explorer</h2>
            <p>This dashboard presents Hawaii's FY 2026–2027 state budget data parsed from HB 300.
               It does not include budgets for the Judiciary, Legislature, or OHA.</p>
            <h3>Features</h3>
            <ul>
                <li>Browse budget allocations by department with program-level drill-down</li>
                <li>Search and filter across all programs by fund type, section, or keyword</li>
                <li>Compare FY2026 vs FY2027 allocations with delta analysis</li>
                <li>Export filtered data as CSV for offline analysis</li>
                <li>View fund-type composition and position counts</li>
            </ul>
            <h3>Data Source</h3>
            <p>Data is sourced from <a href="https://hiappleseed.org/publications/hawaii-budget-primer-2025-26" target="_blank" rel="noopener">Hawaii Appleseed's Budget Primer 2025-26</a>.</p>
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
                <a href="#/" class="back-button">← Home</a>
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

    // Build section checkbox options
    const allSections = [...new Set(initData.comparisons.map(r => r.section))].filter(Boolean).sort();
    const secChecks = allSections.map(s =>
        `<label><input type="checkbox" value="${s}" checked> ${s}</label>`).join('');

    // Build fund checkbox options
    const allFunds = [...new Set(initData.comparisons.map(r => r.fund_category))].filter(Boolean).sort();
    const fundChecks = allFunds.map(f =>
        `<label><input type="checkbox" value="${f}" checked> ${f}</label>`).join('');

    const fyToggle = (draftComparisonData && draftComparisonDataFY27) ? `
        <div class="fy-toggle">
            <button class="sort-btn active" id="fy-btn-26" data-fy="26">FY2026</button>
            <button class="sort-btn" id="fy-btn-27" data-fy="27">FY2027</button>
        </div>` : (draftComparisonDataFY27 ? '<div class="fy-toggle"><button class="sort-btn active" data-fy="27">FY2027</button></div>' : '');

    return `
        <section class="compare-page">
            <a href="#/" class="back-button">← Home</a>
            <h2>${meta.bill_number}: ${meta.draft1} → ${meta.draft2}</h2>
            <p class="muted" style="margin-bottom:1rem;">Comparing the House Draft (HD1) to the Senate Draft (SD1) of HB1800. The "Introduced" version is a supplemental amendment bill without tabular budget data, so HD1 is used as the baseline.</p>

            ${fyToggle}

            <div class="summary-cards-grid" id="draft-cards"></div>
            <div class="totals-bar" id="draft-totals-bar"></div>
            <div class="draft-stats" id="draft-stats-bar"></div>

            <div class="filter-bar">
                <select id="draft-filter" class="filter-select">
                    <option value="all">All Changes</option>
                    <option value="modified">Modified Only</option>
                    <option value="increases">Increases Only</option>
                    <option value="decreases">Decreases Only</option>
                    <option value="added">Newly Added</option>
                    <option value="removed">Removed</option>
                </select>
                <div class="checkbox-dropdown" id="section-dropdown">
                    <button class="checkbox-dropdown-btn" type="button">Section ▾</button>
                    <div class="checkbox-dropdown-menu">${secChecks}</div>
                </div>
                <div class="checkbox-dropdown" id="fund-dropdown">
                    <button class="checkbox-dropdown-btn" type="button">Fund ▾</button>
                    <div class="checkbox-dropdown-menu">${fundChecks}</div>
                </div>
                <input type="text" id="draft-search" placeholder="Search programs..." class="search-input">
                <button class="action-link export-btn" id="export-drafts">⬇ Export CSV</button>
            </div>
            <div class="search-summary" id="draft-summary"></div>
            <div id="draft-results"></div>
        </section>`;
};

window.initDraftComparePage = async function () {
    const hasData = (draftComparisonData && draftComparisonData.comparisons) ||
                    (draftComparisonDataFY27 && draftComparisonDataFY27.comparisons);
    if (!hasData) return;

    let activeData = draftComparisonData || draftComparisonDataFY27;
    let sortCol = 'change';
    let sortDir = 'asc';

    // --- Helpers ---

    const getD1Key = () => 'amount_' + activeData.metadata.draft1.toLowerCase();
    const getD2Key = () => 'amount_' + activeData.metadata.draft2.toLowerCase();

    const getCheckedValues = (dropdownId) => {
        const boxes = document.querySelectorAll(`#${dropdownId} input[type="checkbox"]`);
        return [...boxes].filter(cb => cb.checked).map(cb => cb.value);
    };

    const updateDropdownLabel = (dropdownId, label) => {
        const el = document.querySelector(`#${dropdownId} .checkbox-dropdown-btn`);
        if (!el) return;
        const boxes = document.querySelectorAll(`#${dropdownId} input[type="checkbox"]`);
        const total = boxes.length;
        const checked = [...boxes].filter(cb => cb.checked).length;
        el.textContent = checked === total ? `${label} ▾` : `${label} (${checked}/${total}) ▾`;
    };

    // --- Summary cards: Operating / Capital breakdown ---

    const updateSummaryCards = () => {
        const meta = activeData.metadata;
        const d1Key = getD1Key(), d2Key = getD2Key();
        const recs = activeData.comparisons;

        const sumBy = (section) => {
            const sr = recs.filter(r => r.section === section);
            const d1 = sr.reduce((s, r) => s + (r[d1Key] || 0), 0);
            const d2 = sr.reduce((s, r) => s + (r[d2Key] || 0), 0);
            return { d1, d2, delta: d2 - d1 };
        };
        const op = sumBy('Operating');
        const cap = sumBy('Capital Improvement');
        const totalD1 = op.d1 + cap.d1;
        const totalD2 = op.d2 + cap.d2;
        const totalNet = totalD2 - totalD1;

        const changeCard = (delta, label) => {
            const cls = delta > 0 ? 'positive' : delta < 0 ? 'negative' : '';
            const negCls = delta < 0 ? ' change-negative' : '';
            return `<div class="summary-card change-card${negCls}"><div class="amount ${cls}">${fmt(delta)}</div><div class="label">${label}</div></div>`;
        };

        const cardsEl = document.getElementById('draft-cards');
        if (cardsEl) {
            cardsEl.innerHTML = `
                <div class="card-section-label">Operating</div>
                <div class="summary-card"><div class="amount">${fmt(op.d1)}</div><div class="label">${meta.draft1}</div></div>
                <div class="summary-card"><div class="amount">${fmt(op.d2)}</div><div class="label">${meta.draft2}</div></div>
                ${changeCard(op.delta, 'Change')}
                <div class="card-section-label">Capital Improvement</div>
                <div class="summary-card"><div class="amount">${fmt(cap.d1)}</div><div class="label">${meta.draft1}</div></div>
                <div class="summary-card"><div class="amount">${fmt(cap.d2)}</div><div class="label">${meta.draft2}</div></div>
                ${changeCard(cap.delta, 'Change')}`;
        }

        const totalsEl = document.getElementById('draft-totals-bar');
        if (totalsEl) {
            const netCls = totalNet > 0 ? 'positive' : totalNet < 0 ? 'negative' : '';
            totalsEl.innerHTML = `<strong>${meta.draft1} Total:</strong> ${fmt(totalD1)}<span class="sep">|</span><strong>${meta.draft2} Total:</strong> ${fmt(totalD2)}<span class="sep">|</span><strong>Net Change:</strong> <span class="${netCls}">${fmt(totalNet)}</span>`;
        }

        const summary = activeData.summary;
        const statsEl = document.getElementById('draft-stats-bar');
        if (statsEl) {
            statsEl.innerHTML = `
                <strong>${summary.items_modified}</strong> changed ·
                <span class="positive">▲ ${summary.items_increased} increases</span> ·
                <span class="negative">▼ ${summary.items_decreased} decreases</span> ·
                <span>+ ${summary.items_added} added</span> ·
                <span>− ${summary.items_removed} removed</span>`;
        }
    };

    // --- Main render: filter, sort, group by department ---

    const render = () => {
        const meta = activeData.metadata;
        const d1Key = getD1Key(), d2Key = getD2Key();
        const mode = document.getElementById('draft-filter')?.value || 'all';
        const q = (document.getElementById('draft-search')?.value || '').toLowerCase();
        const checkedSections = getCheckedValues('section-dropdown');
        const checkedFunds = getCheckedValues('fund-dropdown');
        const allSections = document.querySelectorAll('#section-dropdown input[type="checkbox"]').length;
        const allFunds = document.querySelectorAll('#fund-dropdown input[type="checkbox"]').length;

        let data = [...activeData.comparisons];

        // Checkbox filters
        if (checkedSections.length < allSections)
            data = data.filter(r => checkedSections.includes(r.section));
        if (checkedFunds.length < allFunds)
            data = data.filter(r => checkedFunds.includes(r.fund_category));

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
            if (sortCol === 'program_name') return (r.program_name || '').toLowerCase();
            return r[sortCol] ?? 0;
        };
        data.sort((a, b) => {
            const va = resolveSort(a), vb = resolveSort(b);
            if (typeof va === 'string') return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
            return sortDir === 'asc' ? va - vb : vb - va;
        });

        // Summary line
        const totalDelta = data.reduce((s, r) => s + (r.change || 0), 0);
        document.getElementById('draft-summary').innerHTML =
            `<strong>${data.length}</strong> items — Net: <strong class="${totalDelta > 0 ? 'positive' : 'negative'}">${fmt(totalDelta)}</strong>`;

        // Group by department
        const deptMap = new Map();
        for (const r of data) {
            const key = r.department_code || 'OTHER';
            if (!deptMap.has(key)) deptMap.set(key, { code: key, name: r.department_name || key, items: [] });
            deptMap.get(key).items.push(r);
        }
        const depts = [...deptMap.values()];
        // Sort departments: alphabetical when sorting by name, else by |change|
        if (sortCol === 'program_name') {
            depts.sort((a, b) => sortDir === 'asc' ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name));
        } else {
            depts.sort((a, b) => {
                const absA = Math.abs(a.items.reduce((s, r) => s + (r.change || 0), 0));
                const absB = Math.abs(b.items.reduce((s, r) => s + (r.change || 0), 0));
                return absB - absA;
            });
        }

        const sortArrow = (col) => {
            const active = sortCol === col ? ' sort-active' : '';
            const arrow = sortCol === col ? (sortDir === 'asc' ? '▲' : '▼') : '▸';
            return `<span class="sort-arrow">${arrow}</span>`;
        };

        // Auto-expand when searching
        const autoExpand = q.length > 0;

        let bodyHtml = '';
        for (const dept of depts) {
            const dD1 = dept.items.reduce((s, r) => s + (r[d1Key] || 0), 0);
            const dD2 = dept.items.reduce((s, r) => s + (r[d2Key] || 0), 0);
            const dDelta = dept.items.reduce((s, r) => s + (r.change || 0), 0);
            const dCls = dDelta > 0 ? 'positive' : dDelta < 0 ? 'negative' : '';
            const expandedCls = autoExpand ? ' expanded' : '';

            bodyHtml += `<tr class="dept-group-row${expandedCls}" data-dept="${dept.code}">
                <td><span class="toggle-arrow">▶</span> <strong>${dept.name}</strong><span class="dept-item-count">(${dept.items.length})</span></td>
                <td></td><td></td>
                <td class="amount-cell">${fmt(dD1)}</td>
                <td class="amount-cell">${fmt(dD2)}</td>
                <td class="amount-cell ${dCls}">${fmt(dDelta)}</td>
                <td></td><td></td>
            </tr>`;

            const hiddenCls = autoExpand ? '' : ' hidden';
            for (const r of dept.items) {
                const delta = r.change || 0;
                const cls = delta > 0 ? 'positive' : delta < 0 ? 'negative' : '';
                const typeBadge = r.change_type === 'added' ? '<span class="badge badge-add">new</span>'
                    : r.change_type === 'removed' ? '<span class="badge badge-remove">removed</span>' : '';
                bodyHtml += `<tr class="dept-detail-row${hiddenCls}" data-dept="${dept.code}">
                    <td><strong>${r.program_id || ''}</strong> ${r.program_name || ''}</td>
                    <td>${r.section || ''}</td>
                    <td>${r.fund_category || ''}</td>
                    <td class="amount-cell">${fmt(r[d1Key])}</td>
                    <td class="amount-cell">${fmt(r[d2Key])}</td>
                    <td class="amount-cell ${cls}">${fmt(delta)}</td>
                    <td class="amount-cell ${cls}">${r.pct_change != null ? fmtPct(r.pct_change) : '—'}</td>
                    <td>${typeBadge}</td>
                </tr>`;
            }
        }

        document.getElementById('draft-results').innerHTML = `
            <table class="data-table" id="draft-table">
                <thead><tr>
                    <th class="sortable" data-sort="program_name">Program ${sortArrow('program_name')}</th>
                    <th>Section</th><th>Fund</th>
                    <th class="sortable amount-cell" data-sort="d1">${meta.draft1} ${sortArrow('d1')}</th>
                    <th class="sortable amount-cell" data-sort="d2">${meta.draft2} ${sortArrow('d2')}</th>
                    <th class="sortable amount-cell" data-sort="change">Change ${sortArrow('change')}</th>
                    <th class="sortable amount-cell" data-sort="pct_change">% ${sortArrow('pct_change')}</th>
                    <th>Type</th>
                </tr></thead>
                <tbody>${bodyHtml}</tbody>
            </table>`;

        window._lastDraftResults = data;
        window._lastDraftMeta = meta;
    };

    // --- Checkbox dropdown open/close ---

    document.querySelectorAll('.checkbox-dropdown-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const dd = btn.closest('.checkbox-dropdown');
            // Close other dropdowns
            document.querySelectorAll('.checkbox-dropdown.open').forEach(el => {
                if (el !== dd) el.classList.remove('open');
            });
            dd.classList.toggle('open');
        });
    });
    document.addEventListener('click', () => {
        document.querySelectorAll('.checkbox-dropdown.open').forEach(el => el.classList.remove('open'));
    });
    document.querySelectorAll('.checkbox-dropdown-menu').forEach(menu => {
        menu.addEventListener('click', (e) => e.stopPropagation());
    });

    // Checkbox change → update label + re-render
    document.querySelectorAll('#section-dropdown input[type="checkbox"]').forEach(cb => {
        cb.addEventListener('change', () => { updateDropdownLabel('section-dropdown', 'Section'); render(); });
    });
    document.querySelectorAll('#fund-dropdown input[type="checkbox"]').forEach(cb => {
        cb.addEventListener('change', () => { updateDropdownLabel('fund-dropdown', 'Fund'); render(); });
    });

    // --- Sortable column headers ---

    document.getElementById('draft-results')?.addEventListener('click', (e) => {
        const th = e.target.closest('th.sortable');
        if (!th) return;
        const col = th.dataset.sort;
        if (sortCol === col) { sortDir = sortDir === 'asc' ? 'desc' : 'asc'; }
        else { sortCol = col; sortDir = col === 'program_name' ? 'asc' : 'desc'; }
        render();
    });

    // --- Department row expand/collapse ---

    document.getElementById('draft-results')?.addEventListener('click', (e) => {
        const groupRow = e.target.closest('.dept-group-row');
        if (!groupRow) return;
        const dept = groupRow.dataset.dept;
        const isExpanded = groupRow.classList.toggle('expanded');
        document.querySelectorAll(`.dept-detail-row[data-dept="${dept}"]`).forEach(tr => {
            tr.classList.toggle('hidden', !isExpanded);
        });
    });

    // --- FY toggle ---

    document.getElementById('fy-btn-26')?.addEventListener('click', () => {
        if (!draftComparisonData) return;
        activeData = draftComparisonData;
        document.getElementById('fy-btn-26').classList.add('active');
        document.getElementById('fy-btn-27')?.classList.remove('active');
        updateSummaryCards();
        render();
    });
    document.getElementById('fy-btn-27')?.addEventListener('click', () => {
        if (!draftComparisonDataFY27) return;
        activeData = draftComparisonDataFY27;
        document.getElementById('fy-btn-27').classList.add('active');
        document.getElementById('fy-btn-26')?.classList.remove('active');
        updateSummaryCards();
        render();
    });

    // --- Other controls ---

    document.getElementById('draft-filter')?.addEventListener('change', render);
    document.getElementById('draft-search')?.addEventListener('input', render);

    document.getElementById('export-drafts')?.addEventListener('click', () => {
        const meta = window._lastDraftMeta || activeData.metadata;
        const d1Key = getD1Key(), d2Key = getD2Key();
        const rows = (window._lastDraftResults || activeData.comparisons).map(r => ({
            program_id: r.program_id, program_name: r.program_name,
            department_code: r.department_code, department_name: r.department_name,
            section: r.section, fund_type: r.fund_type, fund_category: r.fund_category,
            [meta.draft1]: r[d1Key], [meta.draft2]: r[d2Key],
            change: r.change, pct_change: r.pct_change, change_type: r.change_type,
        }));
        downloadCSV(rows, `${meta.bill_number}_${meta.draft1}_vs_${meta.draft2}_FY${meta.fiscal_year}.csv`);
    });

    // --- Initial render ---
    updateSummaryCards();
    render();
};

// ---------------------------------------------------------------------------
// Init hooks
// ---------------------------------------------------------------------------
window.initHomePage = async function () {};
