/**
 * Test Logs JavaScript - v2.0 (Fixed filter API paths)
 *
 * Handles test log viewing and filtering.
 */

let currentLogs = [];
let currentPage = 1;
let currentLimit = 100;
let currentFilters = {};
let currentLogId = null;
let testCasesData = []; // Store test cases data for lookup

// Initialize page
document.addEventListener('DOMContentLoaded', async function () {
    setupEventListeners();

    // Load test cases first, then test logs
    await loadTestCases();
    await loadTestLogs();

    // Check if specific log or test case is requested
    const urlParams = new URLSearchParams(window.location.search);
    const logId = urlParams.get('logId');
    const testCaseId = urlParams.get('testCaseId');

    if (logId) {
        setTimeout(() => viewLogInNewPage(logId), 1000);
    } else if (testCaseId) {
        setTimeout(() => {
            document.getElementById('testCaseFilter').value = testCaseId;
            applyFilters();
        }, 1000);
    }
});

function setupEventListeners() {
    // Limit selection
    document.getElementById('limitSelect').addEventListener('change', function () {
        currentLimit = parseInt(this.value);
        currentPage = 1;
        applyFilters();
    });
}

async function loadTestLogs() {
    showLoading(true);
    try {
        const params = new URLSearchParams({
            limit: currentLimit,
            offset: (currentPage - 1) * currentLimit
        });

        // Add filters
        if (currentFilters.status || currentFilters.testCaseId) {
            // Use combined filter endpoint for better flexibility
            if (currentFilters.status) {
                params.append('status', currentFilters.status);
            }
            if (currentFilters.testCaseId) {
                params.append('test_case_id', currentFilters.testCaseId);
            }

            const response = await fetch(`/v1/api/test-logs/filter/combined?${params}`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const logs = await response.json();
            currentLogs = logs;
        } else {
            const response = await fetch(`/v1/api/test-logs/?${params}`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const logs = await response.json();
            currentLogs = logs;
        }

        displayTestLogs(currentLogs);
        updatePagination();

    } catch (error) {
        console.error('Error loading test logs:', error);
        showAlert('Error loading test logs: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

async function loadTestCases() {
    try {
        const response = await fetch('/v1/api/test-cases/');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const testCases = await response.json();
        testCasesData = testCases; // Store for lookup
        populateTestCaseFilter(testCases);

    } catch (error) {
        console.error('Error loading test cases:', error);
    }
}

function populateTestCaseFilter(testCases) {
    const select = document.getElementById('testCaseFilter');

    // Clear existing options except the first one
    select.innerHTML = '<option value="">All Test Cases</option>';

    testCases.forEach(testCase => {
        const option = document.createElement('option');
        option.value = testCase.id;
        option.textContent = testCase.name;
        select.appendChild(option);
    });
}

// Helper function to find test case by ID
function findTestCaseById(testCaseId) {
    return testCasesData.find(tc => tc.id === testCaseId);
}

function displayTestLogs(logs) {
    const container = document.getElementById('testLogsList');
    const emptyState = document.getElementById('emptyState');
    const table = document.getElementById('testLogsTable');

    if (logs.length === 0) {
        container.innerHTML = '';
        table.style.display = 'none';
        emptyState.classList.remove('d-none');
        return;
    }

    emptyState.classList.add('d-none');
    table.style.display = 'table';

    const html = logs.map(log => {
        const testCase = findTestCaseById(log.test_case_id);
        const testCaseName = testCase ? testCase.name : `Unknown Test Case`;

        return `
        <tr>
            <td>
                <div class="d-flex flex-column">
                    <strong>${escapeHtml(testCaseName)}</strong>
                    <small class="text-muted">Log ID: ${log.id}</small>
                </div>
            </td>
            <td>
                <span class="badge bg-primary">${escapeHtml(log.model_name)}</span>
            </td>
            <td>
                <span class="badge ${log.status === 'success' ? 'bg-success' : 'bg-danger'}">
                    <i class="fas fa-${log.status === 'success' ? 'check-circle' : 'times-circle'} me-1"></i>
                    ${log.status.toUpperCase()}
                </span>
                ${log.error_message ? `<br><small class="text-danger">${escapeHtml(truncateText(log.error_message, 50))}</small>` : ''}
            </td>
            <td>
                <strong>${log.response_time_ms}ms</strong>
            </td>
            <td>
                <small class="text-muted">${formatDate(log.created_at)}</small>
            </td>
            <td>
                <div class="btn-group" role="group">
                    <button type="button" class="btn btn-sm btn-outline-primary" onclick="viewLogInNewPage('${log.id}')" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-secondary" onclick="reExecuteTest('${log.test_case_id}')" title="Re-execute">
                        <i class="fas fa-redo"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-danger" onclick="deleteLog('${log.id}')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
        `;
    }).join('');

    container.innerHTML = html;
}

// Function to open log in new page
function viewLogInNewPage(logId) {
    window.open(`/test-logs/${logId}`, '_blank');
}

// Keep the original viewLog function for backward compatibility (if needed)
async function viewLog(logId) {
    try {
        // Ensure test cases data is loaded
        if (!testCasesData || testCasesData.length === 0) {
            await loadTestCases();
        }

        const response = await fetch(`/v1/api/test-logs/${logId}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status} `);

        const log = await response.json();
        currentLogId = logId;

        // Display log details
        const detailsHtml = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Execution Information</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Status:</strong></td><td>
                            <span class="status-${log.status}">
                                <i class="fas fa-${log.status === 'success' ? 'check-circle' : 'times-circle'} me-1"></i>
                                ${log.status.toUpperCase()}
                            </span>
                        </td></tr>
                        <tr><td><strong>Model:</strong></td><td>${escapeHtml(log.model_name)}</td></tr>
                        <tr><td><strong>Response Time:</strong></td><td>${log.response_time_ms}ms</td></tr>
                        <tr><td><strong>Test Case:</strong></td><td>
                            <a href="/test-cases?id=${log.test_case_id}" class="text-decoration-none" target="_blank">
                                ${escapeHtml(findTestCaseById(log.test_case_id)?.name || log.test_case_id)}
                                <i class="fas fa-external-link-alt ms-1" style="font-size: 0.8em;"></i>
                            </a>
                        </td></tr>
                        <tr><td><strong>Executed At:</strong></td><td>${formatDate(log.created_at)}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>System Prompt</h6>
                    <pre class="bg-light p-3 rounded" style="max-height: 200px; overflow-y: auto;">${escapeHtml(log.system_prompt)}</pre>
                </div>
            </div>

        <div class="row mt-3">
            <div class="col-md-6">
                <h6>User Message</h6>
                <pre class="bg-light p-3 rounded" style="max-height: 200px; overflow-y: auto;">${escapeHtml(log.user_message)}</pre>
            </div>
            <div class="col-md-6">
                ${log.tools && log.tools.length > 0 ? `
                        <h6>Tools Configuration</h6>
                        <div class="accordion" id="logToolsAccordion">
                            ${log.tools.map((tool, index) => `
                                <div class="accordion-item">
                                    <h2 class="accordion-header" id="logHeading${index}">
                                        <button class="accordion-button collapsed" type="button"
                                                data-bs-toggle="collapse" data-bs-target="#logCollapse${index}"
                                                aria-expanded="false" aria-controls="logCollapse${index}">
                                            <i class="fas fa-wrench me-2"></i>
                                            <strong>${escapeHtml(tool.function?.name || 'Unknown Tool')}</strong>
                                        </button>
                                    </h2>
                                    <div id="logCollapse${index}" class="accordion-collapse collapse"
                                         aria-labelledby="logHeading${index}" data-bs-parent="#logToolsAccordion">
                                        <div class="accordion-body">
                                            <pre class="bg-light p-2 rounded" style="max-height: 200px; overflow-y: auto; font-size: 0.85em;">${escapeHtml(JSON.stringify(tool, null, 2))}</pre>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    ` : '<h6>Tools</h6><p class="text-muted">No tools used</p>'}
            </div>
        </div>

            ${log.error_message ? `
                <div class="row mt-3">
                    <div class="col-12">
                        <h6>Error Message</h6>
                        <div class="alert alert-danger">
                            ${escapeHtml(log.error_message)}
                        </div>
                    </div>
                </div>
            ` : ''
            }

            ${log.llm_response ? `
                <div class="row mt-3">
                    <div class="col-12">
                        <h6>LLM Response</h6>
                        <pre class="bg-light p-3 rounded" style="max-height: 400px; overflow-y: auto;">${escapeHtml(log.llm_response)}</pre>
                    </div>
                </div>
            ` : ''
            }
    `;

        document.getElementById('logDetails').innerHTML = detailsHtml;

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('viewLogModal'));
        modal.show();

    } catch (error) {
        console.error('Error loading log details:', error);
        showAlert('Error loading log details: ' + error.message, 'danger');
    }
}

async function applyFilters() {
    const status = document.getElementById('statusFilter').value;
    const testCaseId = document.getElementById('testCaseFilter').value;

    currentFilters = {
        status: status || null,
        testCaseId: testCaseId || null
    };

    currentPage = 1;

    // Ensure test cases are loaded before loading logs
    if (testCasesData.length === 0) {
        await loadTestCases();
    }

    await loadTestLogs();
}

async function deleteLog(logId) {
    if (!confirm('Are you sure you want to delete this test log? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/v1/api/test-logs/${logId}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status} `);

        showAlert('Test log deleted successfully!', 'success');
        loadTestLogs();

    } catch (error) {
        console.error('Error deleting test log:', error);
        showAlert('Error deleting test log: ' + error.message, 'danger');
    }
}

function reExecuteTest(testCaseId) {
    window.location.href = `/ test - execution ? testCaseId = ${testCaseId} `;
}

function reExecuteFromLog() {
    // Get the current log and redirect to execution page
    if (currentLogId) {
        // We need to get the test case ID from the current log
        const log = currentLogs.find(l => l.id === currentLogId);
        if (log) {
            reExecuteTest(log.test_case_id);
        }
    }
}

function loadPreviousPage() {
    if (currentPage > 1) {
        currentPage--;
        loadTestLogs();
    }
}

function loadNextPage() {
    currentPage++;
    loadTestLogs();
}

function updatePagination() {
    const pagination = document.getElementById('pagination');
    const prevPage = document.getElementById('prevPage');
    const nextPage = document.getElementById('nextPage');
    const currentPageSpan = document.getElementById('currentPage');

    if (currentLogs.length > 0) {
        pagination.classList.remove('d-none');
        currentPageSpan.textContent = currentPage;

        // Update previous button
        if (currentPage <= 1) {
            prevPage.classList.add('disabled');
        } else {
            prevPage.classList.remove('disabled');
        }

        // Update next button (disable if we got less than the limit)
        if (currentLogs.length < currentLimit) {
            nextPage.classList.add('disabled');
        } else {
            nextPage.classList.remove('disabled');
        }
    } else {
        pagination.classList.add('d-none');
    }
}

// Utility functions
function showLoading(show) {
    const spinner = document.getElementById('loadingSpinner');
    const list = document.getElementById('testLogsList');

    if (show) {
        spinner.classList.remove('d-none');
        list.classList.add('d-none');
    } else {
        spinner.classList.add('d-none');
        list.classList.remove('d-none');
    }
}

function showAlert(message, type) {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert - ${type} alert - dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    // Insert at top of container
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function truncateText(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}
