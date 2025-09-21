/**
 * Test Cases Management JavaScript
 * 
 * Handles test case CRUD operations and UI interactions.
 */

let currentTestCases = [];
let currentTestCaseId = null;
let agents = [];
let selectedAgentId = '';

// Initialize page
document.addEventListener('DOMContentLoaded', async function () {
    setupEventListeners();

    const urlParams = new URLSearchParams(window.location.search);
    const initialAgentId = urlParams.get('agentId');
    if (initialAgentId) {
        selectedAgentId = initialAgentId;
    }

    await loadAgents();
    loadTestCases();

    if (initialAgentId) {
        const agentFilter = document.getElementById('agentFilter');
        if (agentFilter) {
            agentFilter.value = initialAgentId;
        }
    }

    const testCaseId = urlParams.get('id');
    if (testCaseId) {
        setTimeout(() => viewTestCaseInNewPage(testCaseId), 1000);
    }
});

function setupEventListeners() {
    // Search functionality
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                searchTestCases();
            }
        });

        // Also trigger search on input change with debounce
        let searchTimeout;
        searchInput.addEventListener('input', function () {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                searchTestCases();
            }, 500); // 500ms debounce
        });
    }

    const agentFilter = document.getElementById('agentFilter');
    if (agentFilter) {
        agentFilter.addEventListener('change', function () {
            selectedAgentId = this.value;
            loadTestCases();
        });
    }

    const clearBtn = document.getElementById('clearFiltersBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            const agentSelect = document.getElementById('agentFilter');
            const searchField = document.getElementById('searchInput');
            selectedAgentId = '';
            if (agentSelect) {
                agentSelect.value = '';
            }
            if (searchField) {
                searchField.value = '';
            }
            loadTestCases();
        });
    }
}

async function loadTestCases() {
    showLoading(true);
    try {
        const url = new URL('/v1/api/test-cases/', window.location.origin);
        if (selectedAgentId) {
            url.searchParams.append('agent_id', selectedAgentId);
        }

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const testCases = await response.json();
        currentTestCases = testCases;
        displayTestCases(testCases);

    } catch (error) {
        console.error('Error loading test cases:', error);
        showAlert('Error loading test cases: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

async function loadAgents() {
    try {
        const response = await fetch('/v1/api/agents/');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        agents = data.filter((agent) => !agent.is_deleted);
        populateAgentFilter();
        populateAgentSelects();
        updateAgentWarning();
    } catch (error) {
        console.error('Error loading agents:', error);
        showAlert('Error loading agents: ' + error.message, 'danger');
    }
}

function populateAgentFilter() {
    const filter = document.getElementById('agentFilter');
    if (!filter) {
        return;
    }

    const previousValue = filter.value;
    filter.innerHTML = '<option value="">All agents</option>';
    agents.forEach((agent) => {
        const option = document.createElement('option');
        option.value = agent.id;
        option.textContent = agent.name;
        filter.appendChild(option);
    });

    if (selectedAgentId && !agents.some((agent) => agent.id === selectedAgentId)) {
        selectedAgentId = '';
    }

    const desiredValue = selectedAgentId || previousValue || '';
    filter.value = desiredValue;
    if (filter.value !== desiredValue) {
        filter.value = '';
    }
    selectedAgentId = filter.value;
}

function populateAgentSelects() {
    const createSelect = document.getElementById('createTestCaseAgent');
    const editSelect = document.getElementById('editTestCaseAgent');

    [createSelect, editSelect].forEach((select) => {
        if (!select) return;
        const selectedValue = select.value;
        select.innerHTML = '<option value="">Select an agent...</option>';
        agents.forEach((agent) => {
            const option = document.createElement('option');
            option.value = agent.id;
            option.textContent = agent.name;
            select.appendChild(option);
        });

        if (selectedValue) {
            select.value = selectedValue;
        } else if (select.id === 'createTestCaseAgent' && agents.length === 1) {
            select.value = agents[0].id;
        }
    });

    const hasAgents = agents.length > 0;
    const modalConfirmButton = document.querySelector('#createTestCaseModal .btn-primary');
    if (modalConfirmButton) {
        modalConfirmButton.disabled = !hasAgents;
    }

    document.querySelectorAll('button[data-bs-target="#createTestCaseModal"]').forEach((button) => {
        button.disabled = !hasAgents;
    });
}

function updateAgentWarning() {
    const warning = document.getElementById('agentWarning');
    if (!warning) {
        return;
    }

    if (agents.length === 0) {
        warning.classList.remove('d-none');
    } else {
        warning.classList.add('d-none');
    }
}

function displayTestCases(testCases) {
    const container = document.getElementById('testCasesList');
    const emptyState = document.getElementById('emptyState');
    const table = document.getElementById('testCasesTable');

    if (testCases.length === 0) {
        container.innerHTML = '';
        table.style.display = 'none';
        emptyState.classList.remove('d-none');
        return;
    }

    emptyState.classList.add('d-none');
    table.style.display = 'table';

    const html = testCases.map(testCase => {
        const agentName = testCase.agent ? testCase.agent.name : 'Unknown agent';
        const agentDisplay = escapeHtml(agentName);

        return `
        <tr>
            <td>
                <div class="d-flex flex-column">
                    <strong>${escapeHtml(testCase.name)}</strong>
                    ${testCase.description ? `<small class="text-muted">${escapeHtml(truncateText(testCase.description, 60))}</small>` : ''}
                </div>
            </td>
            <td>
                <div class="d-flex flex-column">
                    <span>${agentDisplay}</span>
                    <small class="text-muted">${escapeHtml(testCase.agent_id)}</small>
                </div>
            </td>
            <td>
                <div class="d-flex flex-column">
                    <span class="badge bg-primary model-badge">${escapeHtml(testCase.model_name)}</span>
                    ${testCase.tools ? '<span class="badge bg-info model-badge mt-1">Tools</span>' : ''}
                </div>
            </td>
            <td>
                <div class="text-truncate" style="max-width: 300px;" title="${escapeHtml(testCase.system_prompt)}">
                    ${escapeHtml(truncateText(testCase.system_prompt, 80))}
                </div>
            </td>
            <td>
                <small class="text-muted">${formatDate(testCase.created_at)}</small>
            </td>
            <td>
                <div class="btn-group" role="group">
                    <button type="button" class="btn btn-sm btn-outline-primary" onclick="viewTestCaseInNewPage('${testCase.id}')" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-secondary" onclick="editTestCase('${testCase.id}')" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-info" onclick="reimportTestCase('${testCase.id}')" title="Re-import Raw Data">
                        <i class="fas fa-upload"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-success" onclick="executeTestCase('${testCase.id}')" title="Execute">
                        <i class="fas fa-play"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-danger" onclick="deleteTestCase('${testCase.id}')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `;
    }).join('');

    container.innerHTML = html;
}

async function createTestCase() {
    const name = document.getElementById('testCaseName').value.trim();
    const description = document.getElementById('testCaseDescription').value.trim();
    const rawDataText = document.getElementById('rawData').value.trim();
    const agentSelect = document.getElementById('createTestCaseAgent');
    const agentId = agentSelect ? agentSelect.value : '';

    if (!name || !rawDataText || !agentId) {
        showAlert('Please fill in all required fields including the owning agent', 'warning');
        return;
    }

    let rawData;
    try {
        rawData = JSON.parse(rawDataText);
    } catch (error) {
        showAlert('Invalid JSON format in raw data', 'danger');
        return;
    }

    try {
        const response = await fetch('/v1/api/test-cases/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                description: description || null,
                raw_data: rawData,
                agent_id: agentId
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        const newTestCase = await response.json();
        showAlert('Test case created successfully!', 'success');

        // Close modal and reset form
        const modal = bootstrap.Modal.getInstance(document.getElementById('createTestCaseModal'));
        modal.hide();
        document.getElementById('createTestCaseForm').reset();
        populateAgentSelects();

        // Reload test cases
        loadTestCases();

    } catch (error) {
        console.error('Error creating test case:', error);
        showAlert('Error creating test case: ' + error.message, 'danger');
    }
}

async function editTestCase(testCaseId) {
    try {
        const response = await fetch(`/v1/api/test-cases/${testCaseId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const testCase = await response.json();

        // Populate edit form (only name and description)
        document.getElementById('editTestCaseId').value = testCase.id;
        document.getElementById('editTestCaseName').value = testCase.name;
        document.getElementById('editTestCaseDescription').value = testCase.description || '';
        const editAgentSelect = document.getElementById('editTestCaseAgent');
        if (editAgentSelect) {
            editAgentSelect.value = testCase.agent_id || '';
        }

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('editTestCaseModal'));
        modal.show();

    } catch (error) {
        console.error('Error loading test case for edit:', error);
        showAlert('Error loading test case: ' + error.message, 'danger');
    }
}

async function updateTestCase() {
    const testCaseId = document.getElementById('editTestCaseId').value;
    const name = document.getElementById('editTestCaseName').value.trim();
    const description = document.getElementById('editTestCaseDescription').value.trim();
    const agentId = document.getElementById('editTestCaseAgent').value;

    if (!name || !agentId) {
        showAlert('Please provide a name and agent for the test case', 'warning');
        return;
    }

    try {
        const response = await fetch(`/v1/api/test-cases/${testCaseId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                description: description || null,
                agent_id: agentId || null
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        showAlert('Test case updated successfully!', 'success');

        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('editTestCaseModal'));
        modal.hide();

        // Reload test cases
        loadTestCases();

    } catch (error) {
        console.error('Error updating test case:', error);
        showAlert('Error updating test case: ' + error.message, 'danger');
    }
}

async function reimportTestCase(testCaseId) {
    try {
        // Set the test case ID in the modal
        document.getElementById('reimportTestCaseId').value = testCaseId;

        // Clear the textarea
        document.getElementById('reimportRawData').value = '';
        clearModalAlert('reimportAlertContainer');

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('reimportTestCaseModal'));
        modal.show();

    } catch (error) {
        console.error('Error opening reimport modal:', error);
        showAlert('Error opening reimport modal: ' + error.message, 'danger');
    }
}

async function confirmReimportTestCase() {
    const testCaseId = document.getElementById('reimportTestCaseId').value;
    const rawDataText = document.getElementById('reimportRawData').value.trim();

    if (!rawDataText) {
        showModalAlert('reimportAlertContainer', 'Please enter the raw data', 'warning');
        return;
    }

    let rawData;
    try {
        rawData = JSON.parse(rawDataText);
    } catch (error) {
        showModalAlert('reimportAlertContainer', 'Invalid JSON format in raw data', 'danger');
        return;
    }

    try {
        const response = await fetch(`/v1/api/test-cases/${testCaseId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                raw_data: rawData
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('reimportTestCaseModal'));
        modal.hide();

        // Reset form
        document.getElementById('reimportTestCaseForm').reset();
        clearModalAlert('reimportAlertContainer');

        // Reload test cases
        loadTestCases();

        showAlert('Test case raw data re-imported successfully!', 'success');

    } catch (error) {
        console.error('Error re-importing test case:', error);
        showModalAlert('reimportAlertContainer', 'Error re-importing test case: ' + error.message, 'danger');
    }
}

async function deleteTestCase(testCaseId) {
    if (!confirm('Are you sure you want to delete this test case? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/v1/api/test-cases/${testCaseId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        showAlert('Test case deleted successfully!', 'success');
        loadTestCases();

    } catch (error) {
        console.error('Error deleting test case:', error);
        showAlert('Error deleting test case: ' + error.message, 'danger');
    }
}

async function viewTestCase(testCaseId) {
    try {
        const response = await fetch(`/v1/api/test-cases/${testCaseId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const testCase = await response.json();
        currentTestCaseId = testCaseId;

        // Helper function to format middle messages
        const formatMiddleMessages = (messages) => {
            if (!messages || messages.length === 0) {
                return '<div class="text-muted">No middle messages</div>';
            }

            return messages.map((message, index) => {
                const role = message.role || 'unknown';
                const content = message.content || '';
                const toolCalls = message.tool_calls || [];
                const roleColor = {
                    'user': 'text-primary',
                    'assistant': 'text-success',
                    'tool': 'text-warning',
                    'system': 'text-info'
                }[role] || 'text-secondary';

                // Format tool calls if present
                const formatToolCalls = (calls) => {
                    if (!calls || calls.length === 0) return '';

                    return calls.map((call, callIndex) => {
                        const toolId = call.id || 'unknown';
                        const toolName = call.function?.name || 'unknown';
                        const toolArgs = call.function?.arguments || '';

                        // Try to format arguments as JSON for better readability
                        let formattedArgs = toolArgs;
                        try {
                            if (typeof toolArgs === 'string') {
                                const parsed = JSON.parse(toolArgs);
                                formattedArgs = JSON.stringify(parsed, null, 2);
                            } else if (typeof toolArgs === 'object') {
                                formattedArgs = JSON.stringify(toolArgs, null, 2);
                            }
                        } catch (e) {
                            // Keep original format if JSON parsing fails
                            formattedArgs = String(toolArgs);
                        }

                        return `
                            <div class="mt-2 p-2 bg-warning bg-opacity-10 border border-warning border-opacity-25 rounded">
                                <div class="d-flex align-items-center mb-1">
                                    <i class="fas fa-tools text-warning me-2"></i>
                                    <strong class="text-warning">Tool Call #${callIndex + 1}</strong>
                                </div>
                                <div class="small">
                                    <div><strong>Name:</strong> <code>${escapeHtml(toolName)}</code></div>
                                    <div><strong>ID:</strong> <code>${escapeHtml(toolId)}</code></div>
                                    <div><strong>Arguments:</strong></div>
                                    <pre class="bg-light p-2 rounded mt-1 mb-0" style="font-size: 0.8em; max-height: 100px; overflow-y: auto;">${escapeHtml(formattedArgs)}</pre>
                                </div>
                            </div>
                        `;
                    }).join('');
                };

                return `
                    <div class="mb-2 border-start border-3 ps-2" style="border-color: var(--bs-${role === 'user' ? 'primary' : role === 'assistant' ? 'success' : role === 'tool' ? 'warning' : 'secondary'}) !important;">
                        <div class="d-flex align-items-center mb-1">
                            <span class="badge bg-secondary me-2">#${index + 1}</span>
                            <strong class="${roleColor}">${escapeHtml(role.toUpperCase())}</strong>
                            ${toolCalls.length > 0 ? `<span class="badge bg-warning ms-2">${toolCalls.length} tool call${toolCalls.length > 1 ? 's' : ''}</span>` : ''}
                        </div>
                        ${content ? `<pre class="bg-light p-2 rounded mb-0" style="font-size: 0.85em; max-height: 150px; overflow-y: auto;">${escapeHtml(content)}</pre>` : ''}
                        ${formatToolCalls(toolCalls)}
                    </div>
                `;
            }).join('');
        };

        // Display test case details
        const detailsHtml = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Basic Information</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Name:</strong></td><td>${escapeHtml(testCase.name)}</td></tr>
                        <tr><td><strong>Description:</strong></td><td>${escapeHtml(testCase.description || 'N/A')}</td></tr>
                        <tr><td><strong>Agent:</strong></td><td>${testCase.agent ? `<span class="badge bg-primary">${escapeHtml(testCase.agent.name)}</span>` : 'Unknown'}<br><small class="text-muted">${escapeHtml(testCase.agent_id)}</small></td></tr>
                        <tr><td><strong>Model:</strong></td><td>${escapeHtml(testCase.model_name)}</td></tr>
                        <tr><td><strong>Has Tools:</strong></td><td>${testCase.tools ? 'Yes' : 'No'}</td></tr>
                        <tr><td><strong>Created:</strong></td><td>${formatDate(testCase.created_at)}</td></tr>
                        <tr><td><strong>Updated:</strong></td><td>${formatDate(testCase.updated_at)}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>System Prompt</h6>
                    <pre class="bg-light p-3 rounded" style="max-height: 200px; overflow-y: auto;">${escapeHtml(testCase.system_prompt)}</pre>
                </div>
            </div>
            <div class="row mt-3">
                <div class="col-md-6">
                    <h6>Middle Messages</h6>
                    <div style="max-height: 300px; overflow-y: auto;">
                        ${formatMiddleMessages(testCase.middle_messages)}
                    </div>
                </div>
                <div class="col-md-6">
                    <h6>Last User Message</h6>
                    <pre class="bg-light p-3 rounded" style="max-height: 300px; overflow-y: auto;">${escapeHtml(testCase.last_user_message)}</pre>
                </div>
            </div>
            ${testCase.tools && testCase.tools.length > 0 ? `
            <div class="row mt-3">
                <div class="col-12">
                    <h6>Tools Configuration</h6>
                    <div class="accordion" id="toolsAccordion">
                        ${testCase.tools.map((tool, index) => `
                            <div class="accordion-item">
                                <h2 class="accordion-header" id="heading${index}">
                                    <button class="accordion-button collapsed" type="button"
                                            data-bs-toggle="collapse" data-bs-target="#collapse${index}"
                                            aria-expanded="false" aria-controls="collapse${index}">
                                        <i class="fas fa-wrench me-2"></i>
                                        <strong>${escapeHtml(tool.function?.name || 'Unknown Tool')}</strong>
                                        ${tool.function?.description ? `<span class="text-muted ms-2">- ${escapeHtml(truncateText(tool.function.description, 60))}</span>` : ''}
                                    </button>
                                </h2>
                                <div id="collapse${index}" class="accordion-collapse collapse"
                                     aria-labelledby="heading${index}" data-bs-parent="#toolsAccordion">
                                    <div class="accordion-body">
                                        <div class="row">
                                            <div class="col-md-6">
                                                <h6 class="text-primary">Function Details</h6>
                                                <table class="table table-sm">
                                                    <tr><td><strong>Name:</strong></td><td>${escapeHtml(tool.function?.name || 'N/A')}</td></tr>
                                                    <tr><td><strong>Type:</strong></td><td>${escapeHtml(tool.type || 'N/A')}</td></tr>
                                                    ${tool.function?.description ? `<tr><td><strong>Description:</strong></td><td>${escapeHtml(tool.function.description)}</td></tr>` : ''}
                                                </table>
                                            </div>
                                            <div class="col-md-6">
                                                <h6 class="text-success">Parameters Schema</h6>
                                                <pre class="bg-light p-2 rounded" style="max-height: 300px; overflow-y: auto; font-size: 0.85em;">${escapeHtml(JSON.stringify(tool.function?.parameters || {}, null, 2))}</pre>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
            ` : ''}
        `;

        document.getElementById('testCaseDetails').innerHTML = detailsHtml;

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('viewTestCaseModal'));
        modal.show();

    } catch (error) {
        console.error('Error loading test case details:', error);
        showAlert('Error loading test case details: ' + error.message, 'danger');
    }
}

function executeTestCase(testCaseId) {
    // Open test execution page in a new tab with the selected test case ID
    const executionUrl = `/test-execution?testCaseId=${testCaseId}`;
    const newWindow = window.open(executionUrl, '_blank');
    if (!newWindow) {
        // Fallback if the browser blocks popups
        window.location.href = executionUrl;
        return;
    }

    // Ensure the newly opened tab cannot control the original window
    newWindow.opener = null;
}

function executeFromView() {
    if (currentTestCaseId) {
        executeTestCase(currentTestCaseId);
    }
}

async function searchTestCases() {
    const query = document.getElementById('searchInput').value.trim();

    if (!query) {
        loadTestCases();
        return;
    }

    showLoading(true);
    try {
        const url = new URL('/v1/api/test-cases/search', window.location.origin);
        url.searchParams.append('q', query);
        if (selectedAgentId) {
            url.searchParams.append('agent_id', selectedAgentId);
        }

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const testCases = await response.json();
        displayTestCases(testCases);

    } catch (error) {
        console.error('Error searching test cases:', error);
        showAlert('Error searching test cases: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

// Utility functions
function showLoading(show) {
    const spinner = document.getElementById('loadingSpinner');
    const list = document.getElementById('testCasesList');

    if (show) {
        spinner.classList.remove('d-none');
        list.classList.add('d-none');
    } else {
        spinner.classList.add('d-none');
        list.classList.remove('d-none');
    }
}

function clearModalAlert(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = '';
    }
}

function showModalAlert(containerId, message, type) {
    const container = document.getElementById(containerId);
    if (!container) {
        showAlert(message, type);
        return;
    }

    container.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
}

function showAlert(message, type) {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
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

// New function to open test case details in a new page
function viewTestCaseInNewPage(testCaseId) {
    window.open(`/test-cases/${testCaseId}`, '_blank');
}
