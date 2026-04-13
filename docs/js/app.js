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
            <div class="context-banner">Viewing HB300 enacted budget. <a href="#/">→ HB1800 Draft Comparison</a></div>
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
            <a href="#/enacted" class="back-button">← Back to HB300 Budget</a>
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
        <div class="fy-toggle">
            <button class="sort-btn active" id="fy-btn-26" data-fy="26">FY2026</button>
            <button class="sort-btn" id="fy-btn-27" data-fy="27">FY2027</button>
        </div>` : (draftComparisonDataFY27 ? '<div class="fy-toggle"><button class="sort-btn active" data-fy="27">FY2027</button></div>' : '');

    return `
        <section class="compare-page">
            <h2>HD1 → SD1 Draft Comparison</h2>
            <p class="muted" style="margin-bottom:0.75rem;">Comparing <a href="https://capitol.hawaii.gov/sessions/session2026/bills/HB1800_HD1.htm" target="_blank" rel="noopener">HD1</a> to <a href="https://capitol.hawaii.gov/sessions/session2026/bills/HB1800_SD1.htm" target="_blank" rel="noopener">SD1</a> of HB1800.</p>
            <p class="muted">See also: <a href="https://hiappleseed.org/publications/hawaii-budget-primer-fy202526" target="_blank" rel="noopener">Hawaiʻi Budget Primer FY2025–26</a></p>
            <br>
            ${fyToggle}

            <div class="summary-cards-grid compact" id="draft-cards"></div>
            <div class="draft-stats" id="draft-stats-bar"></div>

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
    let checkedSections = null; // null = all
    let checkedFunds = null;    // null = all
    let expandedDepts = new Set();
    let expandedFundTypes = new Set();
    let expandedPrograms = new Set();

    const getD1Key = () => 'amount_' + activeData.metadata.draft1.toLowerCase();
    const getD2Key = () => 'amount_' + activeData.metadata.draft2.toLowerCase();

    // --- Summary cards ---

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
                <div class="card-section-label card-section-total">Total</div>
                <div class="summary-card"><div class="amount">${fmt(totalD1)}</div><div class="label">${meta.draft1}</div></div>
                <div class="card-arrow">→</div>
                <div class="summary-card"><div class="amount">${fmt(totalD2)}</div><div class="label">${meta.draft2}</div></div>
                <div class="card-arrow"></div>
                ${changeCard(totalNet, 'Net Change')}
                <div class="card-section-label card-section-toggle" data-target="cards-operating"><span class="toggle-arrow">▶</span> <span class="has-tooltip" data-tooltip="Recurring expenditures for day-to-day government operations, including personnel, services, and supplies.">Operating</span></div>
                <div class="card-row-collapsible" id="cards-operating" style="display:none;">
                    <div class="summary-cards-grid compact">
                        <div class="summary-card"><div class="amount">${fmt(op.d1)}</div><div class="label">${meta.draft1}</div></div>
                        <div class="card-arrow">→</div>
                        <div class="summary-card"><div class="amount">${fmt(op.d2)}</div><div class="label">${meta.draft2}</div></div>
                        <div class="card-arrow"></div>
                        ${changeCard(op.delta, 'Change')}
                    </div>
                </div>
                <div class="card-section-label card-section-toggle" data-target="cards-capital"><span class="toggle-arrow">▶</span> <span class="has-tooltip" data-tooltip="One-time spending on construction, land acquisition, and major infrastructure projects funded through bond proceeds or capital appropriations.">Capital Improvement</span></div>
                <div class="card-row-collapsible" id="cards-capital" style="display:none;">
                    <div class="summary-cards-grid compact">
                        <div class="summary-card"><div class="amount">${fmt(cap.d1)}</div><div class="label">${meta.draft1}</div></div>
                        <div class="card-arrow">→</div>
                        <div class="summary-card"><div class="amount">${fmt(cap.d2)}</div><div class="label">${meta.draft2}</div></div>
                        <div class="card-arrow"></div>
                        ${changeCard(cap.delta, 'Change')}
                    </div>
                </div>`;

            cardsEl.querySelectorAll('.card-section-toggle').forEach(label => {
                label.addEventListener('click', () => {
                    const target = document.getElementById(label.dataset.target);
                    const arrow = label.querySelector('.toggle-arrow');
                    if (target.style.display === 'none') {
                        target.style.display = 'block';
                        arrow.textContent = '▼';
                    } else {
                        target.style.display = 'none';
                        arrow.textContent = '▶';
                    }
                });
            });
        }

        const summary = activeData.summary;
        const statsEl = document.getElementById('draft-stats-bar');
        if (statsEl) {
            statsEl.innerHTML = `
                <span class="stat-tag stat-tag-positive">▲ <strong>${summary.items_increased}</strong> increases</span>
                <span class="stat-tag stat-tag-negative">▼ <strong>${summary.items_decreased}</strong> decreases</span>`;
        }
    };

    // --- Build checkbox options from data ---

    const getAllSections = () => [...new Set(activeData.comparisons.map(r => r.section))].filter(Boolean).sort();
    const getAllFunds = () => [...new Set(activeData.comparisons.map(r => r.fund_category))].filter(Boolean).sort();

    // --- Main render: flat table with header dropdowns ---

    const render = () => {
        const meta = activeData.metadata;
        const d1Key = getD1Key(), d2Key = getD2Key();
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
                    <option value="increases"${filterVal==='increases'?' selected':''}>Increases Only</option>
                    <option value="decreases"${filterVal==='decreases'?' selected':''}>Decreases Only</option>
                    <option value="added"${filterVal==='added'?' selected':''}>Newly Added</option>
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
            d.delta = d.d2 - d.d1;
            return d;
        }).sort((a, b) => {
            let va, vb;
            if (sortCol === 'program_name') { va = a.code.toLowerCase(); vb = b.code.toLowerCase(); }
            else if (sortCol === 'd1') { va = a.d1; vb = b.d1; }
            else if (sortCol === 'd2') { va = a.d2; vb = b.d2; }
            else { va = a.delta; vb = b.delta; } // change, pct_change, default
            if (typeof va === 'string') return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
            return sortDir === 'asc' ? va - vb : vb - va;
        });

        // Build cross-reference map: program_id → set of dept codes it appears under
        const splitPrograms = new Map();
        for (const r of activeData.comparisons) {
            const pid = r.program_id;
            const dept = r.department_code;
            if (!pid || !dept) continue;
            if (!splitPrograms.has(pid)) splitPrograms.set(pid, new Set());
            splitPrograms.get(pid).add(dept);
        }
        // Only keep programs that appear in 2+ departments
        for (const [pid, depts] of splitPrograms) {
            if (depts.size < 2) splitPrograms.delete(pid);
        }

        // Auto-expand departments when searching
        const autoExpand = q.length > 0;

        // Aggregate records by program_id within each department
        const aggregatePrograms = (rows) => {
            const pMap = new Map();
            for (const r of rows) {
                const pid = r.program_id || '';
                if (!pMap.has(pid)) {
                    pMap.set(pid, {
                        program_id: pid, program_name: r.program_name || '',
                        department_code: r.department_code, department_name: r.department_name,
                        d1: 0, d2: 0, funds: new Set(), sections: new Set(),
                        hasAdded: false, hasRemoved: false, rawRows: [],
                    });
                }
                const p = pMap.get(pid);
                p.d1 += r[d1Key] || 0;
                p.d2 += r[d2Key] || 0;
                if (r.fund_category) p.funds.add(r.fund_category);
                if (r.section) p.sections.add(r.section);
                if (r.change_type === 'added') p.hasAdded = true;
                if (r.change_type === 'removed') p.hasRemoved = true;
                p.rawRows.push(r);
            }
            return [...pMap.values()].map(p => {
                p.change = p.d2 - p.d1;
                p.pct_change = p.d1 !== 0 ? ((p.d2 - p.d1) / Math.abs(p.d1)) * 100 : (p.d2 !== 0 ? 100 : 0);
                p.change_type = p.hasAdded && p.d1 === 0 ? 'added' : p.hasRemoved && p.d2 === 0 ? 'removed' : 'modified';
                p.isMixed = p.sections.size > 1;
                p.section = p.isMixed ? 'Mixed' : [...p.sections][0] || '';
                p.fundLabel = p.funds.size === 1 ? [...p.funds][0] : `${p.funds.size} funds`;
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
            bodyHtml += `<tr class="dept-group-row" data-dept="${dept.code}">
                <td><span class="dept-arrow">${arrow}</span> <strong>${dept.code}</strong> ${dept.name} <span class="dept-count">(${programs.length} programs)</span></td>
                <td></td><td></td>
                <td class="amount-cell">${fmt(deptD1)}</td>
                <td class="amount-cell">${fmt(deptD2)}</td>
                <td class="amount-cell ${deptCls}">${fmt(deptDelta)}</td>
                <td></td>
            </tr>`;

            for (const p of programs) {
                const cls = p.change > 0 ? 'positive' : p.change < 0 ? 'negative' : '';
                const typeBadge = p.change_type === 'added' ? '<span class="badge badge-add">new</span>'
                    : p.change_type === 'removed' ? '<span class="badge badge-remove">removed</span>' : '';
                const progKey = `${dept.code}:${p.program_id}`;
                const progOpen = autoExpand || expandedPrograms.has(progKey);

                // Cross-reference note for programs split across departments
                const splitDepts = splitPrograms.get(p.program_id);
                const crossRefNote = splitDepts
                    ? ' <span class="split-note">also in ' +
                      [...splitDepts].filter(d => d !== dept.code)
                        .map(d => `<a class="split-link" href="#/hb1800" data-scroll-dept="${d}">${d}</a>`)
                        .join(', ') + '</span>'
                    : '';

                if (p.isMixed) {
                    const progArrow = progOpen ? '▼' : '▶';
                    bodyHtml += `<tr class="dept-detail-row prog-group-row${isOpen ? '' : ' hidden'}" data-dept="${dept.code}" data-prog="${progKey}">
                        <td class="detail-indent"><span class="dept-arrow">${progArrow}</span> <strong>${p.program_id}</strong> ${p.program_name}${crossRefNote}</td>
                        <td>Mixed</td>
                        <td></td>
                        <td class="amount-cell">${fmt(p.d1)}</td>
                        <td class="amount-cell">${fmt(p.d2)}</td>
                        <td class="amount-cell ${cls}">${fmt(p.change)}</td>
                        <td class="amount-cell ${cls}">${p.pct_change != null ? fmtPct(p.pct_change) : '—'}</td>
                    </tr>`;
                    for (const sec of [...p.sections].sort()) {
                        const secRows = p.rawRows.filter(r => r.section === sec);
                        const secD1 = secRows.reduce((s, r) => s + (r[d1Key] || 0), 0);
                        const secD2 = secRows.reduce((s, r) => s + (r[d2Key] || 0), 0);
                        const secDelta = secD2 - secD1;
                        const secCls = secDelta > 0 ? 'positive' : secDelta < 0 ? 'negative' : '';
                        const secPct = secD1 !== 0 ? ((secD2 - secD1) / Math.abs(secD1)) * 100 : (secD2 !== 0 ? 100 : 0);
                        bodyHtml += `<tr class="prog-section-row${isOpen && progOpen ? '' : ' hidden'}" data-dept="${dept.code}" data-prog="${progKey}">
                            <td class="section-indent">${sec}</td>
                            <td></td><td></td>
                            <td class="amount-cell">${fmt(secD1)}</td>
                            <td class="amount-cell">${fmt(secD2)}</td>
                            <td class="amount-cell ${secCls}">${fmt(secDelta)}</td>
                            <td class="amount-cell ${secCls}">${fmtPct(secPct)}</td>
                        </tr>`;
                    }
                } else {
                    bodyHtml += `<tr class="dept-detail-row${isOpen ? '' : ' hidden'}" data-dept="${dept.code}">
                        <td class="detail-indent"><strong>${p.program_id}</strong> ${p.program_name}${crossRefNote}</td>
                        <td>${p.section}</td>
                        <td></td>
                        <td class="amount-cell">${fmt(p.d1)}</td>
                        <td class="amount-cell">${fmt(p.d2)}</td>
                        <td class="amount-cell ${cls}">${fmt(p.change)}</td>
                        <td class="amount-cell ${cls}">${p.pct_change != null ? fmtPct(p.pct_change) : '—'}</td>
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
            const aTotal = a.rows.reduce((s, r) => s + Math.abs(r.change || 0), 0);
            const bTotal = b.rows.reduce((s, r) => s + Math.abs(r.change || 0), 0);
            return bTotal - aTotal;
        });

        const autoExpandFunds = q.length > 0;
        let fundHtml = '';
        for (const fg of fundGroups) {
            const fgD1 = fg.rows.reduce((s, r) => s + (r[d1Key] || 0), 0);
            const fgD2 = fg.rows.reduce((s, r) => s + (r[d2Key] || 0), 0);
            const fgDelta = fgD2 - fgD1;
            const fgCls = fgDelta > 0 ? 'positive' : fgDelta < 0 ? 'negative' : '';
            const isOpen = autoExpandFunds || expandedFundTypes.has(fg.type);
            const arrow = isOpen ? '▼' : '▶';

            fundHtml += `<tr class="fund-group-row" data-fund-type="${fg.type}">
                <td><span class="dept-arrow">${arrow}</span> <strong>${fg.type}</strong> — ${fg.category} <span class="dept-count">(${fg.rows.length})</span></td>
                <td class="amount-cell">${fmt(fgD1)}</td>
                <td class="amount-cell">${fmt(fgD2)}</td>
                <td class="amount-cell ${fgCls}">${fmt(fgDelta)}</td>
                <td></td>
            </tr>`;

            for (const r of fg.rows) {
                const delta = r.change || 0;
                const cls = delta > 0 ? 'positive' : delta < 0 ? 'negative' : '';
                fundHtml += `<tr class="fund-detail-row${isOpen ? '' : ' hidden'}" data-fund-type="${fg.type}">
                    <td class="detail-indent"><strong>${r.program_id || ''}</strong> ${r.program_name || ''}</td>
                    <td class="amount-cell">${fmt(r[d1Key])}</td>
                    <td class="amount-cell">${fmt(r[d2Key])}</td>
                    <td class="amount-cell ${cls}">${fmt(delta)}</td>
                    <td class="amount-cell ${cls}">${r.pct_change != null ? fmtPct(r.pct_change) : '—'}</td>
                </tr>`;
            }
        }

        document.getElementById('draft-results').innerHTML = `
            <table class="data-table" id="draft-table">
                <thead><tr>
                    <th class="sortable" data-sort="program_name">Program${sortArrow('program_name')}</th>
                    <th class="th-dropdown" id="th-section"><span class="th-dropdown-btn">${secLabel}</span>
                        <div class="th-dropdown-menu">${secChecks}</div></th>
                    <th class="th-dropdown" id="th-fund"><span class="th-dropdown-btn">${fundLabel}</span>
                        <div class="th-dropdown-menu">${fundChecks}</div></th>
                    <th class="sortable amount-cell" data-sort="d1">${meta.draft1}${sortArrow('d1')}</th>
                    <th class="sortable amount-cell" data-sort="d2">${meta.draft2}${sortArrow('d2')}</th>
                    <th class="sortable amount-cell" data-sort="change">Change${sortArrow('change')}</th>
                    <th class="sortable amount-cell" data-sort="pct_change">%${sortArrow('pct_change')}</th>
                </tr></thead>
                <tbody>${bodyHtml}</tbody>
            </table>
            <div class="table-export-row"><button class="action-link export-btn" id="export-drafts">⬇ Export CSV</button></div>
            <h3 class="fund-detail-heading"><span class="has-tooltip" data-tooltip="A — General funds for everyday state spending&#10;B — Special funds set aside for specific purposes&#10;C — General obligation bond funds for public projects&#10;E — Revenue bond funds repaid from project earnings&#10;K/L/M/N — Federal aid funds from the U.S. government&#10;S — County funds from county governments&#10;T — Trust funds held for specific long-term purposes">Fund Detail</span></h3>
            <table class="data-table" id="fund-detail-table">
                <thead><tr>
                    <th>Fund / Program</th>
                    <th class="amount-cell">${meta.draft1}</th>
                    <th class="amount-cell">${meta.draft2}</th>
                    <th class="amount-cell">Change</th>
                    <th class="amount-cell">%</th>
                </tr></thead>
                <tbody>${fundHtml}</tbody>
            </table>
            <div class="table-export-row"><button class="action-link export-btn" id="export-fund-detail">⬇ Export CSV</button></div>`;

        // Re-attach header dropdown events after render
        attachHeaderDropdowns();

        window._lastDraftResults = data;
        window._lastDraftMeta = meta;
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
        // Sortable headers
        const th = e.target.closest('th.sortable');
        if (th) {
            const col = th.dataset.sort;
            if (sortCol === col) { sortDir = sortDir === 'asc' ? 'desc' : 'asc'; }
            else { sortCol = col; sortDir = col === 'program_name' ? 'asc' : 'desc'; }
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
            document.querySelectorAll(`.dept-detail-row[data-dept="${dept}"]`).forEach(row => {
                row.classList.toggle('hidden', !isOpen);
            });
            if (!isOpen) {
                document.querySelectorAll(`.prog-section-row[data-dept="${dept}"]`).forEach(row => row.classList.add('hidden'));
            } else {
                document.querySelectorAll(`.prog-section-row[data-dept="${dept}"]`).forEach(row => {
                    row.classList.toggle('hidden', !expandedPrograms.has(row.dataset.prog));
                });
            }
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
            return;
        }
        // Fund group row expand/collapse
        const fundRow = e.target.closest('.fund-group-row');
        if (fundRow) {
            const ft = fundRow.dataset.fundType;
            if (expandedFundTypes.has(ft)) expandedFundTypes.delete(ft);
            else expandedFundTypes.add(ft);
            const arrow = fundRow.querySelector('.dept-arrow');
            const isOpen = expandedFundTypes.has(ft);
            if (arrow) arrow.textContent = isOpen ? '▼' : '▶';
            document.querySelectorAll(`.fund-detail-row[data-fund-type="${ft}"]`).forEach(row => {
                row.classList.toggle('hidden', !isOpen);
            });
        }
    });

    // --- FY toggle ---

    document.getElementById('fy-btn-26')?.addEventListener('click', () => {
        if (!draftComparisonData) return;
        activeData = draftComparisonData;
        checkedSections = null; checkedFunds = null; expandedDepts = new Set(); expandedFundTypes = new Set(); expandedPrograms = new Set();
        document.getElementById('fy-btn-26').classList.add('active');
        document.getElementById('fy-btn-27')?.classList.remove('active');
        updateSummaryCards();
        render();
    });
    document.getElementById('fy-btn-27')?.addEventListener('click', () => {
        if (!draftComparisonDataFY27) return;
        activeData = draftComparisonDataFY27;
        checkedSections = null; checkedFunds = null; expandedDepts = new Set(); expandedFundTypes = new Set(); expandedPrograms = new Set();
        document.getElementById('fy-btn-27').classList.add('active');
        document.getElementById('fy-btn-26')?.classList.remove('active');
        updateSummaryCards();
        render();
    });

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
        } else if (btn.id === 'export-fund-detail') {
            const rows = activeData.comparisons.map(r => ({
                fund_type: r.fund_type, fund_category: r.fund_category,
                program_id: r.program_id, program_name: r.program_name,
                department_code: r.department_code, department_name: r.department_name,
                section: r.section,
                [meta.draft1]: r[d1Key], [meta.draft2]: r[d2Key],
                change: r.change, pct_change: r.pct_change,
            }));
            downloadCSV(rows, `${meta.bill_number}_fund_detail_FY${meta.fiscal_year}.csv`);
        }
    });

    // --- Initial render ---
    updateSummaryCards();
    render();
};

// ---------------------------------------------------------------------------
// Init hooks
// ---------------------------------------------------------------------------
window.initHomePage = async function () {};
