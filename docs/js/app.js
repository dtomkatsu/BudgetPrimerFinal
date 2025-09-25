// Global departments data
let departmentsData = [];

// Load departments data
window.loadDepartments = async function() {
    try {
        console.log('Loading departments data...');
        // Use relative path that works for both local and GitHub Pages
        const response = await fetch('./js/departments.json');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        departmentsData = await response.json();
        console.log('Successfully loaded departments data:', departmentsData.length, 'departments');
        
        return departmentsData;
    } catch (error) {
        console.error('Error loading departments:', error);
        // Show error state in the UI
        const app = document.getElementById('app');
        if (app) {
            app.innerHTML = `
                <div class="error-message">
                    <h2>Error Loading Data</h2>
                    <p>There was an error loading the budget data. Please refresh the page to try again.</p>
                    <p>${error.message}</p>
                </div>`;
        }
        return [];
    }
};

// Sort departments by total budget (descending by default)
function sortDepartments(direction = 'desc') {
    if (!departmentsData || departmentsData.length === 0) {
        console.error('No departments data available for sorting');
        return [];
    }
    return [...departmentsData].sort((a, b) => {
        const totalA = (a.operating_budget || 0) + (a.capital_budget || 0) + (a.one_time_appropriations || 0);
        const totalB = (b.operating_budget || 0) + (b.capital_budget || 0) + (b.one_time_appropriations || 0);
        return direction === 'asc' ? totalA - totalB : totalB - totalA;
    });
}

// Page Components
window.homePage = async function() {
    console.log('homePage called, departmentsData:', departmentsData ? departmentsData.length : 'null/undefined');
    
    // Show loading state if data isn't loaded yet
    if (!departmentsData || departmentsData.length === 0) {
        console.log('No departments data available, showing loading state');
        return `
            <section class="home-page">
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Loading budget data...</p>
                </div>
            </section>`;
    }

    // Format currency function
    const formatAmount = (amount) => {
        if (amount === undefined || amount === null) return '$0';
        if (amount >= 1000000000) {
            return `$${(amount / 1000000000).toFixed(1)}B`;
        }
        if (amount >= 1000000) {
            return `$${(amount / 1000000).toFixed(1)}M`;
        }
        return `$${amount.toLocaleString()}`;
    };

    // Generate department cards with budget breakdown
    const generateDepartmentCards = (departments) => {
        return departments.map(dept => {
            const operating = dept.operating_budget || 0;
            const capital = dept.capital_budget || 0;
            const oneTime = dept.one_time_appropriations || 0;
            const total = operating + capital + oneTime;

            return `
                <a href="#/department/${dept.id}" class="department-card">
                    <h3>${dept.name}</h3>
                    <div class="card-content">
                        <div class="budget-total">
                            <span>Total Budget</span>
                            <strong>${formatAmount(total)}</strong>
                        </div>
                        <div class="budget-breakdown">
                            <div class="budget-row">
                                <span>Operating</span>
                                <span>${formatAmount(operating)}</span>
                            </div>
                            ${capital > 0 ? `
                            <div class="budget-row">
                                <span>Capital</span>
                                <span>${formatAmount(capital)}</span>
                            </div>` : ''}
                            ${oneTime > 0 ? `
                            <div class="budget-row">
                                <span>One-Time</span>
                                <span>${formatAmount(oneTime)}</span>
                            </div>` : ''}
                        </div>
                    </div>
                </a>
            `;
        }).join('');
    };

    // Initial render with default sorting (descending)
    const sortedDepartments = sortDepartments('desc');
    const departmentCards = generateDepartmentCards(sortedDepartments);

    // Return the HTML template with the sorted cards
    const html = `
        <section class="home-page">
            <h2>Hawaii State Budget FY 2026</h2>
            <p>Browse all ${departmentsData.length} departments in the Hawaii State Budget.</p>
            <div class="sort-controls">
                <span>Sort by Total Budget: </span>
                <button id="sort-desc" class="sort-btn active" data-sort="desc">High to Low ↓</button>
                <button id="sort-asc" class="sort-btn" data-sort="asc">Low to High ↑</button>
            </div>
            <div class="department-grid">
                ${departmentCards}
            </div>
        </section>
    `;

    // Add event listeners after the DOM is updated
    setTimeout(() => {
        const sortButtons = document.querySelectorAll('.sort-btn');
        sortButtons.forEach(button => {
            button.addEventListener('click', function() {
                const sortDirection = this.dataset.sort;
                const sortedDepartments = sortDepartments(sortDirection);
                const departmentGrid = document.querySelector('.department-grid');
                departmentGrid.innerHTML = generateDepartmentCards(sortedDepartments);
                
                // Update active state of buttons
                sortButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
            });
        });
    }, 0);

    return html;
}

// Department detail page
window.departmentDetailPage = async function(params) {
    console.log('departmentDetailPage called with params:', params);
    const deptId = params?.id;
    console.log('Looking for department ID:', deptId);
    
    if (!deptId) {
        console.error('No department ID provided in params');
        return window.notFoundPage();
    }
    
    const dept = departmentsData.find(d => d.id === deptId);
    console.log('Found department:', dept);
    
    if (!dept) {
        console.error('Department not found for ID:', deptId);
        return window.notFoundPage();
    }
    
    // Load the department's full budget report HTML content
    try {
        const budgetReportPath = `./pages/${deptId}_budget_report.html`;
        console.log('Trying to fetch budget report from:', budgetReportPath);
        const response = await fetch(budgetReportPath);
        console.log('Budget report response status:', response.status);
        if (!response.ok) {
            throw new Error(`Department budget report not found (${response.status})`);
        }
        const htmlContent = await response.text();
        
        return `
            <section class="department-detail">
                <a href="#/" class="back-button">← Back to Home</a>
                <div class="department-content">
                    ${htmlContent}
                </div>
            </section>
        `;
    } catch (error) {
        console.error('Error loading department budget report:', error);
        
        // Fallback to try the simple HTML file
        try {
            const fallbackPath = `./pages/${deptId}.html`;
            console.log('Trying fallback path:', fallbackPath);
            const fallbackResponse = await fetch(fallbackPath);
            console.log('Fallback response status:', fallbackResponse.status);
            if (!fallbackResponse.ok) {
                throw new Error(`Department page not found (${fallbackResponse.status})`);
            }
            const fallbackContent = await fallbackResponse.text();
            
            return `
                <section class="department-detail">
                    <a href="#/" class="back-button">← Back to Home</a>
                    <div class="department-content">
                        ${fallbackContent}
                    </div>
                </section>
            `;
        } catch (fallbackError) {
            console.error('Error loading fallback department page:', fallbackError);
            
            // Final fallback - show basic department info
            return `
                <section class="department-detail">
                    <a href="#/" class="back-button">← Back to Home</a>
                    <h2>${dept.name}</h2>
                    <p>Budget: ${dept.budget}</p>
                    <p>Detailed information for this department is currently unavailable.</p>
                    <p>Error: ${fallbackError.message}</p>
                </section>
            `;
        }
    }
}

window.aboutPage = async function() {
    return `
        <section class="about-page">
            <h2>About the Hawaii State Budget Explorer</h2>
            <p>This interactive tool provides detailed insights into Hawaii's FY 2026 state budget allocations across all departments.</p>
            
            <h3>Features</h3>
            <ul>
                <li>Browse budget allocations by department</li>
                <li>View detailed breakdowns of operating, capital, and one-time appropriations</li>
                <li>Interactive charts and visualizations</li>
                <li>Mobile-responsive design</li>
            </ul>
            
            <h3>Data Source</h3>
            <p>All budget data is sourced from the official Hawaii State Budget documents for Fiscal Year 2026.</p>
            
            <div class="cta-buttons">
                <a href="#/" class="button primary">← Back to Home</a>
                <a href="#/departments" class="button secondary">Browse Departments</a>
            </div>
        </section>
    `;
}

window.notFoundPage = async function() {
    return `
        <section class="not-found-page">
            <h2>Page Not Found</h2>
            <p>The page you're looking for doesn't exist.</p>
            <div class="cta-buttons">
                <a href="#/" class="button primary">← Back to Home</a>
                <a href="#/departments" class="button secondary">Browse Departments</a>
            </div>
        </section>
    `;
}

// Initialize functions (called after page loads)
window.initHomePage = async function() {
    // Any initialization code for home page
}

window.initDepartmentDetailPage = async function() {
    // Any initialization code for department detail page
}
