// Global departments data
let departmentsData = [];

// Load departments data
async function loadDepartments() {
    try {
        const response = await fetch('/js/departments.json');
        departmentsData = await response.json();
        return departmentsData;
    } catch (error) {
        console.error('Error loading departments:', error);
        return [];
    }
}

// Main application logic
document.addEventListener('DOMContentLoaded', async () => {
    // Load departments data first
    await loadDepartments();
    
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
});

// Page Components
async function homePage() {
    // Calculate summary statistics
    const totalDepts = departmentsData.length;
    const validBudgets = departmentsData.filter(d => d.budget !== '$0' && d.budget !== '$0M');
    
    // Find largest department
    let largestDept = { budget: '$0', name: 'N/A' };
    let totalBudgetValue = 0;
    
    validBudgets.forEach(dept => {
        const budgetStr = dept.budget.replace(/[$,]/g, '');
        let value = 0;
        
        if (budgetStr.includes('B')) {
            value = parseFloat(budgetStr) * 1000000000;
        } else if (budgetStr.includes('M')) {
            value = parseFloat(budgetStr) * 1000000;
        }
        
        totalBudgetValue += value;
        
        if (value > parseFloat(largestDept.budget.replace(/[$,BM]/g, '')) * (largestDept.budget.includes('B') ? 1000000000 : largestDept.budget.includes('M') ? 1000000 : 1)) {
            largestDept = dept;
        }
    });
    
    const totalBudgetFormatted = totalBudgetValue > 1000000000 ? 
        `$${(totalBudgetValue / 1000000000).toFixed(1)}B` : 
        `$${(totalBudgetValue / 1000000).toFixed(0)}M`;
    
    // Get top departments for display
    const topDepartments = validBudgets
        .sort((a, b) => {
            const aVal = parseFloat(a.budget.replace(/[$,BM]/g, '')) * (a.budget.includes('B') ? 1000 : 1);
            const bVal = parseFloat(b.budget.replace(/[$,BM]/g, '')) * (b.budget.includes('B') ? 1000 : 1);
            return bVal - aVal;
        })
        .slice(0, 6);
    
    const departmentCards = topDepartments.map(dept => `
        <a href="#/department/${dept.id}" class="department-card">
            <h3>${dept.name}</h3>
            <div class="card-content">
                <p><strong>Budget:</strong> ${dept.budget}</p>
                <span class="view-details">View Details →</span>
            </div>
        </a>
    `).join('');
    
    return `
        <section class="home-page">
            <h2>Welcome to the Hawaii State Budget Explorer</h2>
            <p>Explore the FY 2026 budget allocations across all state departments.</p>
            
            <div class="summary-cards">
                <div class="summary-card">
                    <div class="amount">${totalBudgetFormatted}</div>
                    <div class="label">Total Budget</div>
                </div>
                <div class="summary-card">
                    <div class="amount">${totalDepts}</div>
                    <div class="label">Departments</div>
                </div>
                <div class="summary-card">
                    <div class="amount">${largestDept.budget}</div>
                    <div class="label">Largest Department</div>
                </div>
            </div>
            
            <div class="cta-buttons">
                <a href="#/departments" class="button primary">Browse All Departments</a>
                <a href="#/about" class="button secondary">About This Project</a>
            </div>
            
            <h3>Top Departments by Budget</h3>
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
    
    // Load the department's HTML content
    try {
        const response = await fetch(`/pages/${deptId}.html`);
        if (!response.ok) {
            throw new Error('Department page not found');
        }
        const htmlContent = await response.text();
        
        return `
            <section class="department-detail">
                <a href="#/departments" class="back-button">← Back to Departments</a>
                ${htmlContent}
            </section>
        `;
    } catch (error) {
        console.error('Error loading department page:', error);
        return `
            <section class="department-detail">
                <a href="#/departments" class="back-button">← Back to Departments</a>
                <h2>${dept.name}</h2>
                <p>Budget: ${dept.budget}</p>
                <p>Detailed information for this department is currently unavailable.</p>
            </section>
        `;
    }
            
            <div class="department-header">
                <h2>${deptData.name}</h2>
                <p>${deptData.description}</p>
            </div>
            
            <div class="summary-cards">
                <div class="summary-card">
                    <div class="amount">${deptData.budget.total}</div>
                    <div class="label">Total Budget</div>
                </div>
                <div class="summary-card">
                    <div class="amount">${deptData.budget.operating}</div>
                    <div class="label">Operating</div>
                </div>
                <div class="summary-card">
                    <div class="amount">${deptData.budget.capital}</div>
                    <div class="label">Capital</div>
                </div>
                <div class="summary-card">
                    <div class="amount ${deptData.budget.changeType}">${deptData.budget.change}</div>
                    <div class="label">vs. Last Year</div>
                </div>
            </div>
            
            <div class="chart-container">
                <canvas id="deptBudgetChart"></canvas>
            </div>
            
            <h3>Program Allocations</h3>
            <table class="budget-table">
                <thead>
                    <tr>
                        <th>Program</th>
                        <th class="amount">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    ${programRows}
                </tbody>
            </table>
        </section>
    `;
}

async function aboutPage() {
    return `
        <section class="about-page">
            <h2>About the Hawaii State Budget Explorer</h2>
            <p>This interactive tool allows you to explore the Hawaii State Budget for Fiscal Year 2026.</p>
            
            <h3>Data Sources</h3>
            <ul>
                <li>HB300 CD1 - State of Hawaii Operating and Capital Budget</li>
                <li>Department of Budget and Finance</li>
                <li>Governor's Office</li>
            </ul>
            
            <h3>Methodology</h3>
            <p>Budget data is sourced from official state documents and processed to provide an accessible view of state spending.</p>
            
            <h3>Contact</h3>
            <p>For questions about this tool, please contact [Your Contact Information].</p>
        </section>
    `;
}

function notFoundPage() {
    return `
        <div class="not-found">
            <h2>Page Not Found</h2>
            <p>The page you're looking for doesn't exist or has been moved.</p>
            <a href="#/" class="button">Return to Home</a>
        </div>
    `;
}

// Initialization Functions
async function initHomePage() {
    // Initialize home page charts
    const ctx = document.getElementById('budgetOverviewChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Education', 'Health', 'Transportation', 'Public Safety', 'HRD', 'Other'],
            datasets: [{
                label: 'Budget ($ Millions)',
                data: [2300, 1800, 1200, 850, 37, 2500],
                backgroundColor: [
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(255, 99, 132, 0.7)',
                    'rgba(255, 206, 86, 0.7)',
                    'rgba(75, 192, 192, 0.7)',
                    'rgba(153, 102, 255, 0.7)',
                    'rgba(255, 159, 64, 0.7)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `$${context.raw.toLocaleString()}M`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return `$${value.toLocaleString()}M`;
                        }
                    }
                }
            }
        }
    });
}

async function initDepartmentsPage() {
    // Any department list specific initialization
    console.log('Departments page initialized');
}

async function initDepartmentDetailPage() {
    // Initialize department detail charts
    const ctx = document.getElementById('deptBudgetChart')?.getContext('2d');
    if (ctx) {
        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Employee Training', 'Benefits', 'Workforce Dev', 'Technology'],
                datasets: [{
                    data: [12, 15, 8, 2],
                    backgroundColor: [
                        '#4e79a7',
                        '#f28e2b',
                        '#e15759',
                        '#76b7b2'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: $${value}M (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
}

// Utility function to update iframe height
function updateIframeHeight() {
    if (window.self !== window.top) {
        const height = document.documentElement.scrollHeight;
        window.parent.postMessage({ 
            type: 'setHeight', 
            height: height 
        }, '*');
    }
}

// Update iframe height on window resize
window.addEventListener('resize', updateIframeHeight);
