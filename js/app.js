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
            <div class="context-banner"><strong>Historical reference:</strong> This is the FY2025–26 enacted budget (HB300), passed by the Legislature last year. For the current FY2026–27 supplemental budget draft comparison, see <a href="#/">HB1800 →</a></div>
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
        const [r26, r27] = await Promise.all([
            fetch('./js/projects_fy26.json?v=' + Date.now()).catch(() => null),
            fetch('./js/projects_fy27.json?v=' + Date.now()).catch(() => null),
        ]);
        if (r26 && r26.ok) projectsDataFY26 = await r26.json();
        if (r27 && r27.ok) projectsDataFY27 = await r27.json();
        return { fy26: projectsDataFY26, fy27: projectsDataFY27 };
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
        <div class="fy-toggle">
            <button class="sort-btn active" id="fy-btn-26" data-fy="26">FY2026</button>
            <button class="sort-btn" id="fy-btn-27" data-fy="27">FY2027</button>
        </div>` : (draftComparisonDataFY27 ? '<div class="fy-toggle"><button class="sort-btn active" data-fy="27">FY2027</button></div>' : '');

    return `
        <section class="compare-page">
            <h2>HB1800: <a class="draft-title-link" href="https://capitol.hawaii.gov/sessions/session2026/bills/HB1800_HD1.htm" target="_blank" rel="noopener">HD1</a> → <a class="draft-title-link" href="https://capitol.hawaii.gov/sessions/session2026/bills/HB1800_SD1.htm" target="_blank" rel="noopener">SD1</a> Draft Comparison</h2>
            <div class="draft-meta-bar">
                <span>See also: <a href="https://hiappleseed.org/publications/hawaii-budget-primer-fy202526" target="_blank" rel="noopener">Hawaiʻi Budget Primer FY2025–26</a></span>
            </div>
            <div class="compare-toggles-bar">
                ${fyToggle}
                <div class="fy-toggle compare-mode-toggle">
                    <button class="sort-btn active" id="mode-btn-hd1sd1" data-mode="hd1-sd1">HD1 vs SD1</button>
                    <button class="sort-btn" id="mode-btn-hb300" data-mode="vs-hb300">vs HB300 (enacted)</button>
                </div>
            </div>

            <div id="hb300-ref"></div>
            <div class="summary-cards-grid compact" id="draft-cards"></div>
            <div class="draft-stats" id="draft-stats-bar"></div>

            <div class="reading-guide" id="reading-guide-box">
                <div class="reading-guide-header">
                    <span class="reading-guide-icon">ℹ</span>
                    <strong>How to read these numbers</strong>
                    <button class="reading-guide-toggle" id="reading-guide-toggle" aria-expanded="false">More</button>
                </div>
                <p class="reading-guide-summary">Not every change is a real cut or increase — some reflect <strong>funds being reshuffled between departments</strong>.</p>
                <div class="reading-guide-content" id="reading-guide-content" style="display: none;">
                    <p><strong>In the House draft (HD1), capital projects are sometimes listed under AGS (Accounting &amp; General Services) as a placeholder.</strong> In addition, some programs, like Rental Housing, receive funding from multiple departments (e.g., HMS and BED).</p>
                    <p>Look for <span class="realloc-note" style="pointer-events:none;">⚠ reallocation</span> badges on individual programs and <span class="fund-note" style="pointer-events:none;">ℹ bond-financed capital projects</span> in the Fund Detail section below for flagged examples.</p>
                </div>
            </div>

            <div class="search-summary" id="draft-summary"></div>
            <div id="draft-results"></div>

            <div id="projects-section" class="projects-section">
                <h3>Capital Projects (Section 14)</h3>
                <p class="section-desc">Specific projects funded by the capital appropriations above. Click a <span class="section-chip section-chip-link" style="pointer-events:none;">Capital Improvement →</span> chip on any program row to jump to that program's projects.</p>
                <div id="projects-list"></div>
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
    let checkedSections = null; // null = all
    let checkedFunds = null;    // null = all
    let expandedDepts = new Set();
    let expandedFundTypes = new Set();
    let expandedPrograms = new Set();
    let compareMode = 'hd1-sd1'; // 'hd1-sd1' | 'vs-hb300'

    // Build HB300 lookup from fyComparisonData: key = program_id + '_' + fund_type
    const hb300Lookup = new Map();
    for (const r of (fyComparisonData || [])) {
        hb300Lookup.set(`${r.program_id}_${r.fund_type}`, r);
    }

    // Inject amount_hb300 into each comparison record (once at init)
    const injectHB300 = (dataset) => {
        const fyKey = dataset.metadata.fiscal_year === 2026 ? 'amount_fy2026' : 'amount_fy2027';
        for (const r of dataset.comparisons) {
            const match = hb300Lookup.get(`${r.program_id}_${r.fund_type}`);
            r.amount_hb300 = match ? (match[fyKey] || 0) : 0;
        }
    };
    if (draftComparisonData) injectHB300(draftComparisonData);
    if (draftComparisonDataFY27) injectHB300(draftComparisonDataFY27);

    const getD1Key = () => compareMode === 'vs-hb300' ? 'amount_hb300' : 'amount_' + activeData.metadata.draft1.toLowerCase();
    const getD2Key = () => 'amount_' + activeData.metadata.draft2.toLowerCase();
    const getD1Label = () => compareMode === 'vs-hb300' ? 'HB300' : activeData.metadata.draft1;
    const getD2Label = () => activeData.metadata.draft2;

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
        const d1Key = getD1Key(), d2Key = getD2Key();
        const d1Label = getD1Label(), d2Label = getD2Label();
        const recs = activeData.comparisons;
        const fyKey = meta.fiscal_year === 2026 ? 'amount_fy2026' : 'amount_fy2027';

        const sumBy = (section) => {
            const sr = recs.filter(r => r.section === section);
            const d1 = sr.reduce((s, r) => s + (r[d1Key] || 0), 0);
            const d2 = sr.reduce((s, r) => s + (r[d2Key] || 0), 0);
            // HB300 totals from fyComparisonData
            const hb300 = (fyComparisonData || [])
                .filter(r => r.section === section)
                .reduce((s, r) => s + (r[fyKey] || 0), 0);
            return { d1, d2, delta: d2 - d1, hb300 };
        };
        const op = sumBy('Operating');
        const cap = sumBy('Capital Improvement');
        const totalD1 = op.d1 + cap.d1;
        const totalD2 = op.d2 + cap.d2;
        const totalNet = totalD2 - totalD1;
        const hb300Total = op.hb300 + cap.hb300;

        const changeCard = (delta, label) => {
            const cls = delta > 0 ? 'positive' : delta < 0 ? 'negative' : '';
            const negCls = delta < 0 ? ' change-negative' : '';
            return `<div class="summary-card change-card${negCls}"><div class="amount ${cls}">${fmt(delta)}</div><div class="label">${label}</div></div>`;
        };

        // HB300 reference bar (always shown, outside compact grid)
        const hb300RefEl = document.getElementById('hb300-ref');
        if (hb300RefEl) {
            hb300RefEl.innerHTML = `
                <div class="hb300-ref-bar">
                    <span class="hb300-ref-label">HB300 (enacted FY${meta.fiscal_year}):</span>
                    <span class="hb300-ref-chip">${fmt(hb300Total)} total</span>
                    <span class="hb300-ref-chip">${fmt(op.hb300)} operating</span>
                    <span class="hb300-ref-chip">${fmt(cap.hb300)} capital</span>
                </div>`;
        }

        const cardsEl = document.getElementById('draft-cards');
        if (cardsEl) {
            cardsEl.innerHTML = `
                <div class="card-section-label card-section-total">Total</div>
                <div class="summary-card"><div class="amount">${fmt(totalD1)}</div><div class="label">${d1Label}</div></div>
                <div class="card-arrow">→</div>
                <div class="summary-card"><div class="amount">${fmt(totalD2)}</div><div class="label">${d2Label}</div></div>
                <div class="card-arrow"></div>
                ${changeCard(totalNet, 'Net Change')}
                <div class="card-section-label card-section-toggle" data-target="cards-operating"><span class="toggle-arrow">▶</span> <span class="has-tooltip" data-tooltip="Recurring expenditures for day-to-day government operations, including personnel, services, and supplies.">Operating</span></div>
                <div class="card-row-collapsible" id="cards-operating" style="display:none;">
                    <div class="summary-cards-grid compact">
                        <div class="summary-card"><div class="amount">${fmt(op.d1)}</div><div class="label">${d1Label}</div></div>
                        <div class="card-arrow">→</div>
                        <div class="summary-card"><div class="amount">${fmt(op.d2)}</div><div class="label">${d2Label}</div></div>
                        <div class="card-arrow"></div>
                        ${changeCard(op.delta, 'Change')}
                    </div>
                </div>
                <div class="card-section-label card-section-toggle" data-target="cards-capital"><span class="toggle-arrow">▶</span> <span class="has-tooltip" data-tooltip="One-time spending on construction, land acquisition, and major infrastructure projects funded through bond proceeds or capital appropriations.">Capital Improvement</span></div>
                <div class="card-row-collapsible" id="cards-capital" style="display:none;">
                    <div class="summary-cards-grid compact">
                        <div class="summary-card"><div class="amount">${fmt(cap.d1)}</div><div class="label">${d1Label}</div></div>
                        <div class="card-arrow">→</div>
                        <div class="summary-card"><div class="amount">${fmt(cap.d2)}</div><div class="label">${d2Label}</div></div>
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

        // Build cross-reference map: program_id → Map<deptCode, {d1, d2, delta}>
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
            bodyHtml += `<tr class="dept-group-row" data-dept="${dept.code}">
                <td><span class="dept-arrow">${arrow}</span> <strong>${dept.code}</strong> ${dept.name} <span class="dept-count">(${programs.length} programs)</span></td>
                <td></td><td></td>
                <td class="amount-cell"><span class="figure-chip">${fmt(deptD1)}</span></td>
                <td class="amount-cell"><span class="figure-chip">${fmt(deptD2)}</span></td>
                <td class="amount-cell ${deptCls}"><span class="figure-chip">${fmt(deptDelta)}</span></td>
                <td></td>
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
                if (splitDeptMap) {
                    const otherDepts = [...splitDeptMap.keys()].filter(d => d !== dept.code);
                    const otherLinks = otherDepts
                        .map(d => `<a class="split-link" href="javascript:void(0)" data-scroll-dept="${d}">${d}</a>`)
                        .join(', ');
                    crossRefNote = ` <span class="split-note">also in ${otherLinks}</span>`;

                    // Detect reallocation: significant negative here, offsetting positive elsewhere
                    const thisDelta = splitDeptMap.get(dept.code)?.delta || 0;
                    const THRESHOLD = 1000000; // $1M minimum to flag
                    const offsetDepts = otherDepts.filter(d => {
                        const od = splitDeptMap.get(d)?.delta || 0;
                        return thisDelta < -THRESHOLD && od > THRESHOLD;
                    });
                    const sourceDepts = otherDepts.filter(d => {
                        const od = splitDeptMap.get(d)?.delta || 0;
                        return thisDelta > THRESHOLD && od < -THRESHOLD;
                    });

                    const fmtNet = (v) => {
                        const sign = v < 0 ? '−' : '+';
                        const abs = Math.abs(v);
                        if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(1)}B`;
                        if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`;
                        return `${sign}$${(abs / 1e3).toFixed(0)}K`;
                    };

                    if (offsetDepts.length > 0) {
                        const offsetLinks = offsetDepts
                            .map(d => `<a class="split-link" href="javascript:void(0)" data-scroll-dept="${d}">${d}</a>`)
                            .join(', ');
                        // Net change across all involved depts for this program
                        const allInvolved = [dept.code, ...offsetDepts];
                        const totalNet = allInvolved.reduce((s, d) => s + (splitDeptMap.get(d)?.delta || 0), 0);
                        const isPure = Math.abs(totalNet) < Math.abs(thisDelta) * 0.15;
                        if (isPure) {
                            crossRefNote += ` <span class="realloc-note realloc-pure" title="The apparent cut here reflects funds moved to another department — the total program funding is unchanged.">↔ funding shifted to ${offsetLinks} — same total, different department</span>`;
                        } else {
                            const netLabel = fmtNet(totalNet);
                            const netDesc = totalNet < 0 ? 'net cut' : 'net increase';
                            crossRefNote += ` <span class="realloc-note" title="Part of this change reflects funds moved to another department, but there is also a real net change in total program funding.">⚠ partly shifted to ${offsetLinks} (${netLabel} ${netDesc})</span>`;
                        }
                    } else if (sourceDepts.length > 0) {
                        const sourceLinks = sourceDepts
                            .map(d => `<a class="split-link" href="javascript:void(0)" data-scroll-dept="${d}">${d}</a>`)
                            .join(', ');
                        // Net change across all involved depts for this program
                        const allInvolved = [dept.code, ...sourceDepts];
                        const totalNet = allInvolved.reduce((s, d) => s + (splitDeptMap.get(d)?.delta || 0), 0);
                        const isPure = Math.abs(totalNet) < Math.abs(thisDelta) * 0.15;
                        if (isPure) {
                            crossRefNote += ` <span class="realloc-note realloc-pure" title="Part of the apparent increase here reflects funds moved from another department — the total program funding is unchanged.">↔ includes funds shifted from ${sourceLinks} — same total, different department</span>`;
                        } else {
                            const netLabel = fmtNet(totalNet);
                            const netDesc = totalNet > 0 ? 'net increase' : 'net cut';
                            crossRefNote += ` <span class="realloc-note" title="Part of this change reflects funds moved from another department, but there is also a real net change in total program funding.">⚠ partly shifted from ${sourceLinks} (${netLabel} ${netDesc})</span>`;
                        }
                    }
                }

                if (p.isMixed) {
                    const progArrow = progOpen ? '▼' : '▶';
                    bodyHtml += `<tr class="dept-detail-row prog-group-row${isOpen ? '' : ' hidden'}" data-dept="${dept.code}" data-prog="${progKey}">
                        <td class="detail-indent"><span class="dept-arrow">${progArrow}</span> <strong>${p.program_id}</strong> ${p.program_name}${crossRefNote}</td>
                        <td><span class="section-chip">Mixed</span></td>
                        <td>${p.fundShort ? `<span class="fund-chip${p.fundTitle ? ' fund-chip-multi' : ''}"${p.fundTitle ? ` data-funds="${p.fundTitle}"` : ''}>${p.fundShort}</span>` : ''}</td>
                        <td class="amount-cell"><span class="figure-chip">${fmt(p.d1)}</span></td>
                        <td class="amount-cell"><span class="figure-chip">${fmt(p.d2)}</span></td>
                        <td class="amount-cell ${cls}"><span class="figure-chip">${fmt(p.change)}</span></td>
                        <td class="amount-cell ${cls}">${p.pct_change != null ? fmtPct(p.pct_change) : '—'}</td>
                    </tr>`;
                    for (const sec of [...p.sections].sort()) {
                        const secRows = p.rawRows.filter(r => r.section === sec);
                        const secD1 = secRows.reduce((s, r) => s + (r[d1Key] || 0), 0);
                        const secD2 = secRows.reduce((s, r) => s + (r[d2Key] || 0), 0);
                        const secDelta = secD2 - secD1;
                        const secCls = secDelta > 0 ? 'positive' : secDelta < 0 ? 'negative' : '';
                        const secPct = secD1 !== 0 ? ((secD2 - secD1) / Math.abs(secD1)) * 100 : (secD2 !== 0 ? 100 : 0);
                        const secFunds = new Set(secRows.map(r => r.fund_category).filter(Boolean));
                        const secFundLabel = secFunds.size === 1 ? shortFund([...secFunds][0]) : (secFunds.size > 1 ? `${secFunds.size} funds` : '');
                        const secFundTitle = secFunds.size > 1 ? [...secFunds].join(' · ') : '';
                        const secHasProjects = sec === 'Capital Improvement'
                            && activeProjects?.projects_by_program?.[p.program_id]?.length > 0;
                        const secChipHtml = secHasProjects
                            ? `<a class="section-chip section-chip-link" href="javascript:void(0)" data-scroll-projects="${p.program_id}">${sec} →</a>`
                            : `<span class="section-chip">${sec}</span>`;
                        bodyHtml += `<tr class="prog-section-row${isOpen && progOpen ? '' : ' hidden'}" data-dept="${dept.code}" data-prog="${progKey}">
                            <td class="section-indent">${secChipHtml}</td>
                            <td></td>
                            <td>${secFundLabel ? `<span class="fund-chip${secFundTitle ? ' fund-chip-multi' : ''}"${secFundTitle ? ` data-funds="${secFundTitle}"` : ''}>${secFundLabel}</span>` : ''}</td>
                            <td class="amount-cell"><span class="figure-chip">${fmt(secD1)}</span></td>
                            <td class="amount-cell"><span class="figure-chip">${fmt(secD2)}</span></td>
                            <td class="amount-cell ${secCls}"><span class="figure-chip">${fmt(secDelta)}</span></td>
                            <td class="amount-cell ${secCls}">${fmtPct(secPct)}</td>
                        </tr>`;
                    }
                } else {
                    const progHasProjects = p.section === 'Capital Improvement'
                        && activeProjects?.projects_by_program?.[p.program_id]?.length > 0;
                    const progChipHtml = progHasProjects
                        ? `<a class="section-chip section-chip-link" href="javascript:void(0)" data-scroll-projects="${p.program_id}">${p.section} →</a>`
                        : `<span class="section-chip">${p.section}</span>`;
                    bodyHtml += `<tr class="dept-detail-row${isOpen ? '' : ' hidden'}" data-dept="${dept.code}">
                        <td class="detail-indent"><strong>${p.program_id}</strong> ${p.program_name}${crossRefNote}</td>
                        <td>${progChipHtml}</td>
                        <td>${p.fundShort ? `<span class="fund-chip${p.fundTitle ? ' fund-chip-multi' : ''}"${p.fundTitle ? ` data-funds="${p.fundTitle}"` : ''}>${p.fundShort}</span>` : ''}</td>
                        <td class="amount-cell"><span class="figure-chip">${fmt(p.d1)}</span></td>
                        <td class="amount-cell"><span class="figure-chip">${fmt(p.d2)}</span></td>
                        <td class="amount-cell ${cls}"><span class="figure-chip">${fmt(p.change)}</span></td>
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

            const fundNote = fg.type === 'C'
                ? ` <span class="fund-note" title="General obligation bonds are loans the state repays over time. Changes here reflect shifts in which capital projects get bond financing — not cuts to the underlying programs.">ℹ bond-financed capital projects</span>`
                : '';
            fundHtml += `<tr class="fund-group-row" data-fund-type="${fg.type}">
                <td><span class="dept-arrow">${arrow}</span> <strong>${fg.type}</strong> — ${fg.category}${fundNote} <span class="dept-count">(${fg.rows.length})</span></td>
                <td class="amount-cell"><span class="figure-chip">${fmt(fgD1)}</span></td>
                <td class="amount-cell"><span class="figure-chip">${fmt(fgD2)}</span></td>
                <td class="amount-cell ${fgCls}"><span class="figure-chip">${fmt(fgDelta)}</span></td>
                <td></td>
            </tr>`;

            for (const r of fg.rows) {
                const delta = r[d2Key] - r[d1Key];
                const cls = delta > 0 ? 'positive' : delta < 0 ? 'negative' : '';
                const dynPct = r[d1Key] !== 0 ? ((delta / Math.abs(r[d1Key])) * 100) : (delta !== 0 ? 100 : 0);
                fundHtml += `<tr class="fund-detail-row${isOpen ? '' : ' hidden'}" data-fund-type="${fg.type}">
                    <td class="detail-indent"><strong>${r.program_id || ''}</strong> ${r.program_name || ''}</td>
                    <td class="amount-cell"><span class="figure-chip">${fmt(r[d1Key])}</span></td>
                    <td class="amount-cell"><span class="figure-chip">${fmt(r[d2Key])}</span></td>
                    <td class="amount-cell ${cls}"><span class="figure-chip">${fmt(delta)}</span></td>
                    <td class="amount-cell ${cls}">${fmtPct(dynPct)}</td>
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
                    <th class="sortable amount-cell" data-sort="d1">${getD1Label()}${sortArrow('d1')}</th>
                    <th class="sortable amount-cell" data-sort="d2">${getD2Label()}${sortArrow('d2')}</th>
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
                    <th class="amount-cell">${getD1Label()}</th>
                    <th class="amount-cell">${getD2Label()}</th>
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

        renderProjects();
    };

    // --- Render Section 14 capital projects section ---

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
        const d1Label = meta.draft1;
        const d2Label = meta.draft2;
        const d1Key = `amount_${d1Label.toLowerCase()}`;
        const d2Key = `amount_${d2Label.toLowerCase()}`;

        // Build a lookup of program_id → program_name from comparison data
        const progNameMap = new Map();
        for (const r of activeData.comparisons) {
            if (r.program_id && !progNameMap.has(r.program_id)) {
                progNameMap.set(r.program_id, r.program_name || '');
            }
        }

        // Filter by current search query
        const q = (document.getElementById('draft-search')?.value || '').toLowerCase();
        const entries = Object.entries(activeProjects.projects_by_program);

        // Sort by program_id
        entries.sort((a, b) => a[0].localeCompare(b[0]));

        let html = '';
        let visibleCount = 0;
        for (const [pid, projects] of entries) {
            if (!projects || projects.length === 0) continue;
            const progName = progNameMap.get(pid) || (projects[0].program_name || '');
            if (q && !pid.toLowerCase().includes(q) && !progName.toLowerCase().includes(q)) {
                // Also try matching any project name
                const anyMatch = projects.some(pr =>
                    (pr.project_name || '').toLowerCase().includes(q));
                if (!anyMatch) continue;
            }
            visibleCount++;

            const d1Total = projects.reduce((s, pr) => s + (pr[d1Key] || 0), 0);
            const d2Total = projects.reduce((s, pr) => s + (pr[d2Key] || 0), 0);
            const delta = d2Total - d1Total;
            const deltaCls = delta > 0 ? 'positive' : delta < 0 ? 'negative' : '';
            const isOpen = expandedProjectPrograms.has(pid);
            const arrow = isOpen ? '▼' : '▶';

            const rowsHtml = projects.map(pr => {
                const change = pr.change || 0;
                const cls = change > 0 ? 'positive' : change < 0 ? 'negative' : '';
                const badge = pr.change_type === 'added' ? '<span class="badge badge-add">new</span>'
                    : pr.change_type === 'removed' ? '<span class="badge badge-remove">removed</span>' : '';
                const scope = pr.scope ? `<div class="project-scope">${pr.scope}</div>` : '';
                return `<tr class="project-row change-${pr.change_type}">
                    <td class="project-num">${pr.project_id}</td>
                    <td><div class="project-name">${pr.project_name}</div>${scope}</td>
                    <td><span class="fund-chip">${shortFund(pr.fund_category)}</span></td>
                    <td class="amount-cell"><span class="figure-chip">${fmt(pr[d1Key])}</span></td>
                    <td class="amount-cell"><span class="figure-chip">${fmt(pr[d2Key])}</span></td>
                    <td class="amount-cell ${cls}"><span class="figure-chip">${fmt(change)}</span> ${badge}</td>
                </tr>`;
            }).join('');

            html += `<div class="project-program-panel" id="projects-${pid}">
                <div class="project-program-header" data-project-pid="${pid}">
                    <span class="toggle-arrow">${arrow}</span>
                    <strong>${pid}</strong> ${progName}
                    <span class="project-count">(${projects.length} project${projects.length === 1 ? '' : 's'})</span>
                    <span class="project-totals">
                        ${fmt(d1Total)} → ${fmt(d2Total)}
                        <span class="${deltaCls}">(${delta >= 0 ? '+' : ''}${fmt(delta)})</span>
                    </span>
                </div>
                <table class="data-table project-table" id="projects-${pid}-body" style="display:${isOpen ? '' : 'none'};">
                    <thead><tr>
                        <th>#</th><th>Project</th><th>Fund</th>
                        <th class="amount-cell">${d1Label}</th>
                        <th class="amount-cell">${d2Label}</th>
                        <th class="amount-cell">Change</th>
                    </tr></thead>
                    <tbody>${rowsHtml}</tbody>
                </table>
            </div>`;
        }

        if (visibleCount === 0) {
            html = `<div class="empty-state"><p>No capital projects match the current filter.</p></div>`;
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
        const chip = e.target.closest('[data-scroll-projects]');
        if (chip) {
            e.preventDefault();
            e.stopPropagation();
            const pid = chip.dataset.scrollProjects;
            expandedProjectPrograms.add(pid);
            renderProjects();
            requestAnimationFrame(() => {
                const panel = document.getElementById(`projects-${pid}`);
                if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
            return;
        }
        const header = e.target.closest('.project-program-header');
        if (header) {
            const pid = header.dataset.projectPid;
            if (expandedProjectPrograms.has(pid)) expandedProjectPrograms.delete(pid);
            else expandedProjectPrograms.add(pid);
            const body = document.getElementById(`projects-${pid}-body`);
            const arrow = header.querySelector('.toggle-arrow');
            const isOpen = expandedProjectPrograms.has(pid);
            if (body) body.style.display = isOpen ? '' : 'none';
            if (arrow) arrow.textContent = isOpen ? '▼' : '▶';
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
        activeProjects = projectsDataFY26;
        checkedSections = null; checkedFunds = null; expandedDepts = new Set(); expandedFundTypes = new Set(); expandedPrograms = new Set(); expandedProjectPrograms = new Set();
        document.getElementById('fy-btn-26').classList.add('active');
        document.getElementById('fy-btn-27')?.classList.remove('active');
        updateSummaryCards();
        render();
    });
    document.getElementById('fy-btn-27')?.addEventListener('click', () => {
        if (!draftComparisonDataFY27) return;
        activeData = draftComparisonDataFY27;
        activeProjects = projectsDataFY27;
        checkedSections = null; checkedFunds = null; expandedDepts = new Set(); expandedFundTypes = new Set(); expandedPrograms = new Set(); expandedProjectPrograms = new Set();
        document.getElementById('fy-btn-27').classList.add('active');
        document.getElementById('fy-btn-26')?.classList.remove('active');
        updateSummaryCards();
        render();
    });

    // --- Compare mode toggle (HD1 vs SD1 | vs HB300) ---
    document.getElementById('mode-btn-hd1sd1')?.addEventListener('click', () => {
        compareMode = 'hd1-sd1';
        document.getElementById('mode-btn-hd1sd1').classList.add('active');
        document.getElementById('mode-btn-hb300')?.classList.remove('active');
        updateSummaryCards();
        render();
    });
    document.getElementById('mode-btn-hb300')?.addEventListener('click', () => {
        compareMode = 'vs-hb300';
        document.getElementById('mode-btn-hb300').classList.add('active');
        document.getElementById('mode-btn-hd1sd1')?.classList.remove('active');
        updateSummaryCards();
        render();
    });

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
            <p class="page-desc">Enter what you paid in Hawaiʻi state taxes to see a proportional breakdown of where those dollars went across state government.</p>

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

            <p class="calc-note">Note: Hawaiʻi personal income tax primarily funds the general fund portion of the budget (about $10B of $23B). This calculator distributes your payment proportionally across the entire state budget for illustration.</p>

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
                        <span class="dept-pct-label">of state budget</span>
                    </div>
                </div>`;
            }
        }).join('');
        const taxPaidCard = taxAmount > 0
            ? `<div class="summary-card"><div class="amount">${fmtYour(taxAmount)}</div><div class="label">Your tax paid</div></div>`
            : `<div class="summary-card empty-state"><div class="amount">—</div><div class="label">Your tax paid</div><div class="card-sub">Enter above ↑</div></div>`;
        el.innerHTML = `
            ${taxPaidCard}
            <div class="summary-card"><div class="amount">${fmt(grandTotal)}</div><div class="label">FY${activeFY} state budget</div></div>
            ${top3Html}
        `;
    };

    const renderTreemap = (depts, grandTotal, ratio) => {
        const canvas = document.getElementById('tax-treemap');
        if (!canvas || !window.Chart) return;

        // Determine dataset: top-level depts or one dept's programs
        let tree, keyName, labelFn, isDrill = false;
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
        } else {
            tree = depts.map((d, i) => ({
                code: d.code,
                name: d.name,
                value: d.total,
                yourShare: d.total * ratio,
                color: colorForIndex(i),
            }));
        }

        // Update breadcrumb
        const crumb = document.getElementById('treemap-breadcrumb');
        if (crumb) {
            if (isDrill) {
                const dept = depts.find(d => d.code === drillDept);
                crumb.innerHTML = `<span class="crumb-root" data-crumb="root">All departments</span> <span class="crumb-sep">▶</span> <span class="crumb-current">${drillDept} — ${dept?.name || ''}</span>`;
            } else {
                crumb.innerHTML = `<span class="crumb-root-active">All departments</span>`;
            }
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
        expandedDetailDept = null;
        document.querySelectorAll('#calc-fy-toggle button').forEach(b =>
            b.classList.toggle('active', parseInt(b.dataset.fy, 10) === activeFY));
        recompute();
    });

    // Breadcrumb: click root to go back
    document.getElementById('treemap-breadcrumb')?.addEventListener('click', (e) => {
        if (e.target.closest('[data-crumb="root"]')) {
            drillDept = null;
            recompute();
        }
    });

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

