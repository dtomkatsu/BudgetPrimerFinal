// Global departments data
let departmentsData = [];

// Load departments data
async function loadDepartments() {
    try {
        const response = await fetch('./js/departments.json');
        departmentsData = await response.json();
        return departmentsData;
    } catch (error) {
        console.error('Error loading departments:', error);
        return [];
    }
}

// Main application logic
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Load departments data first
        departmentsData = await loadDepartments();
        console.log('Loaded departments:', departmentsData);
        
        // Define routes
        const routes = [
        {
            path: '/',
            component: homePage,
            init: initHomePage
        },
        {
            path: '/departments',
            component: departmentsPage,
            init: initDepartmentsPage
        },
        {
            path: '/department/:id',
            component: departmentDetailPage,
            init: initDepartmentDetailPage
        },
        {
            path: '/about',
            component: aboutPage
        },
        {
            path: '*',
            component: notFoundPage
        }
    ];

        // Initialize router
        const router = new Router(routes);
        
        // Handle initial route
        router.handleRoute();
    } catch (error) {
        console.error('Error initializing app:', error);
        document.getElementById('app').innerHTML = `
            <div class="error-message">
                <h2>Error Loading Application</h2>
                <p>There was an error loading the application. Please refresh the page to try again.</p>
                <p>Error details: ${error.message}</p>
            </div>`;
    }
});

// Page Components
async function homePage() {
    // Format currency function
    const formatAmount = (amount) => {
        if (!amount) return '$0';
        if (amount >= 1000000000) {
            return `$${(amount / 1000000000).toFixed(1)}B`;
        }
        if (amount >= 1000000) {
            return `$${(amount / 1000000).toFixed(1)}M`;
        }
        return `$${amount.toLocaleString()}`;
    };

    // Generate department cards with budget breakdown
    const departmentCards = departmentsData.map(dept => {
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
                        <div class="budget-row">
                            <span>Capital</span>
                            <span>${formatAmount(capital)}</span>
                        </div>
                        ${oneTime > 0 ? `
                        <div class="budget-row">
                            <span>One-Time</span>
                            <span>${formatAmount(oneTime)}</span>
                        </div>
                        ` : ''}
                    </div>
                </div>
            </a>
        `;
    }).join('');
    
    return `
        <section class="home-page">
            <h2>Hawaii State Budget FY 2026</h2>
            <p>Browse all ${departmentsData.length} departments in the Hawaii State Budget.</p>
            <div class="department-grid">
                ${departmentCards}
            </div>
        </section>
    `;
}

async function departmentsPage() {
    // Use the real departments data
    const departmentCards = departmentsData.map(dept => `
        <a href="#/department/${dept.id}" class="department-card">
            <h3>${dept.name}</h3>
            <div class="card-content">
                <p><strong>Budget:</strong> ${dept.budget}</p>
                <span class="view-details">View Details →</span>
            </div>
        </a>
    `).join('');
    
    return `
        <section class="departments-page">
            <h2>All Departments</h2>
            <p>Browse all ${departmentsData.length} departments in the Hawaii State Budget.</p>
            <div class="department-grid">
                ${departmentCards}
            </div>
        </section>
    `;
}

async function departmentDetailPage() {
    const deptId = window.location.hash.split('/').pop();
    
    // Find the department in our data
    const dept = departmentsData.find(d => d.id === deptId);
    if (!dept) {
        return `
            <section class="department-detail">
                <a href="#/departments" class="back-button">← Back to Departments</a>
                <h2>Department Not Found</h2>
                <p>The requested department could not be found.</p>
            </section>
        `;
    }
    
    // Load the department's full budget report HTML content
    try {
        const response = await fetch(`./pages/${deptId}_budget_report.html`);
        if (!response.ok) {
            throw new Error('Department budget report not found');
        }
        const htmlContent = await response.text();
        
        return `
            <section class="department-detail">
                <a href="#/departments" class="back-button">← Back to Departments</a>
                <div class="department-content">
                    ${htmlContent}
                </div>
            </section>
        `;
    } catch (error) {
        console.error('Error loading department budget report:', error);
        
        // Fallback to try the simple HTML file
        try {
            const fallbackResponse = await fetch(`./pages/${deptId}.html`);
            if (!fallbackResponse.ok) {
                throw new Error('Department page not found');
            }
            const fallbackContent = await fallbackResponse.text();
            
            return `
                <section class="department-detail">
                    <a href="#/departments" class="back-button">← Back to Departments</a>
                    <div class="department-content">
                        ${fallbackContent}
                    </div>
                </section>
            `;
        } catch (fallbackError) {
            console.error('Error loading fallback department page:', fallbackError);
            return `
                <section class="department-detail">
                    <a href="#/departments" class="back-button">← Back to Departments</a>
                    <h2>${dept.name}</h2>
                    <p>Budget: ${dept.budget}</p>
                    <p>Detailed information for this department is currently unavailable.</p>
                </section>
            `;
        }
    }
}

async function aboutPage() {
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

async function notFoundPage() {
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
async function initHomePage() {
    // Any initialization code for home page
}

async function initDepartmentsPage() {
    // Any initialization code for departments page
}

async function initDepartmentDetailPage() {
    // Any initialization code for department detail page
}
