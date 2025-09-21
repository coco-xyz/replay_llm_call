/**
 * Test Execution JavaScript
 * 
 * Handles test execution and result display.
 */

let currentTestCase = null;
let isExecuting = false;
let currentTools = [];
let editingToolIndex = -1;
let availableAgents = [];
let selectedAgentId = '';
let availableTestCases = [];

// Prevent blur-hide race when clicking dropdown
let pointerDownInDropdown = false;

// Model name history management
const MODEL_HISTORY_KEY = 'llm_replay_model_history';
const MAX_HISTORY_ITEMS = 10;

// Initialize page
document.addEventListener('DOMContentLoaded', async function () {
    setupEventListeners();

    const urlParams = new URLSearchParams(window.location.search);
    const logId = urlParams.get('logId');
    let logData = null;

    if (logId) {
        try {
            logData = await fetchTestLogDetails(logId);
            selectedAgentId = logData.agent_id || '';
        } catch (error) {
            console.error('Unable to load log for re-execution:', error);
            showAlert('Unable to load log for re-execution: ' + error.message, 'warning');
        }
    } else {
        const initialAgentId = urlParams.get('agentId');
        if (initialAgentId) {
            selectedAgentId = initialAgentId;
        }
    }

    await loadAgents();
    await loadTestCases();

    if (logData) {
        await prefillExecutionFromLog(logData);
    } else {
        // Check if test case ID is provided in URL
        const testCaseId = urlParams.get('testCaseId');
        if (testCaseId) {
            setTimeout(() => selectTestCase(testCaseId), 1000);
        }
    }
});

function setupEventListeners() {
    const agentSelect = document.getElementById('agentSelect');
    if (agentSelect) {
        agentSelect.addEventListener('change', async function () {
            selectedAgentId = this.value;
            clearSelection();
            await loadTestCases();
        });
    }

    // Test case selection
    document.getElementById('testCaseSelect').addEventListener('change', function () {
        const testCaseId = this.value;
        if (testCaseId) {
            selectTestCase(testCaseId);
        } else {
            clearSelection();
        }
    });

    // Model name input with history
    setupModelNameInput();
}

async function loadAgents() {
    try {
        const response = await fetch('/v1/api/agents/');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        availableAgents = data.filter((agent) => !agent.is_deleted);
        populateAgentSelect();
        updateAgentWarning();
    } catch (error) {
        console.error('Error loading agents:', error);
        showAlert('Error loading agents: ' + error.message, 'danger');
    }
}

function populateAgentSelect() {
    const select = document.getElementById('agentSelect');
    if (!select) {
        return;
    }

    const previousValue = select.value;
    select.innerHTML = '<option value="">All agents</option>';
    availableAgents.forEach((agent) => {
        const option = document.createElement('option');
        option.value = agent.id;
        option.textContent = agent.name;
        select.appendChild(option);
    });

    const desiredValue = selectedAgentId || previousValue || '';
    select.value = desiredValue;
    if (select.value !== desiredValue) {
        select.value = '';
    }
    selectedAgentId = select.value;
}

function updateAgentWarning() {
    const warning = document.getElementById('executionAgentWarning');
    const agentSelect = document.getElementById('agentSelect');
    if (!warning) return;

    if (availableAgents.length === 0) {
        warning.classList.remove('d-none');
        if (agentSelect) {
            agentSelect.disabled = true;
        }
    } else {
        warning.classList.add('d-none');
        if (agentSelect) {
            agentSelect.disabled = false;
        }
    }
}

async function loadTestCases() {
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
        availableTestCases = testCases;
        populateTestCaseSelect(testCases);

    } catch (error) {
        console.error('Error loading test cases:', error);
        showAlert('Error loading test cases: ' + error.message, 'danger');
    }
}

function populateTestCaseSelect(testCases) {
    const select = document.getElementById('testCaseSelect');

    // Clear existing options except the first one
    select.innerHTML = '<option value="">Select a test case...</option>';

    if (!testCases || testCases.length === 0) {
        select.disabled = true;
        disableExecuteButton();
        updateSelectedAgentSummary(null);
        return;
    }

    select.disabled = false;
    testCases.forEach((testCase) => {
        const option = document.createElement('option');
        const agentName = testCase.agent ? testCase.agent.name : 'Unknown agent';
        option.value = testCase.id;
        option.textContent = `${testCase.name} (${agentName})`;
        select.appendChild(option);
    });

    updateSelectedAgentSummary(null);
}

async function selectTestCase(testCaseId) {
    try {
        const response = await fetch(`/v1/api/test-cases/${testCaseId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const testCase = await response.json();
        currentTestCase = testCase;

        // Update UI
        document.getElementById('testCaseSelect').value = testCaseId;
        populateExecutionParameters(testCase);
        enableExecuteButton();

    } catch (error) {
        console.error('Error loading test case:', error);
        showAlert('Error loading test case: ' + error.message, 'danger');
    }
}



async function fetchTestLogDetails(logId) {
    const response = await fetch(`/v1/api/test-logs/${logId}`);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
}

async function prefillExecutionFromLog(log) {
    try {
        if (!log.test_case_id) {
            throw new Error('Log is missing an associated test case');
        }

        await selectTestCase(log.test_case_id);

        const modelNameInput = document.getElementById('modelName');
        const systemPromptInput = document.getElementById('systemPrompt');
        const userMessageInput = document.getElementById('userMessage');
        const modelSettingsInput = document.getElementById('modelSettings');
        const modelSettingsCollapse = document.getElementById('modelSettingsCollapse');

        if (modelNameInput) {
            modelNameInput.value = log.model_name || '';
        }
        if (systemPromptInput) {
            systemPromptInput.value = log.system_prompt || '';
        }
        if (userMessageInput) {
            userMessageInput.value = log.user_message || '';
        }

        if (modelSettingsInput) {
            if (log.model_settings && Object.keys(log.model_settings).length > 0) {
                modelSettingsInput.value = JSON.stringify(log.model_settings, null, 2);
                if (modelSettingsCollapse && !modelSettingsCollapse.classList.contains('show')) {
                    new bootstrap.Collapse(modelSettingsCollapse, { show: true });
                }
            } else {
                modelSettingsInput.value = '';
            }
        }

        currentTools = Array.isArray(log.tools)
            ? JSON.parse(JSON.stringify(log.tools))
            : [];
        displayTools();

        enableExecuteButton();
        showAlert('Loaded execution parameters from the selected test log.', 'info');
    } catch (error) {
        console.error('Failed to prefill execution from log:', error);
        showAlert('Failed to prefill execution parameters from log: ' + error.message, 'warning');
    }
}

function populateExecutionParameters(testCase) {
    document.getElementById('modelName').value = testCase.model_name;
    document.getElementById('systemPrompt').value = testCase.system_prompt;
    document.getElementById('userMessage').value = testCase.last_user_message;

    // Populate model settings
    const modelSettingsInput = document.getElementById('modelSettings');
    const modelSettingsCollapse = document.getElementById('modelSettingsCollapse');

    if (testCase.model_settings !== null && testCase.model_settings !== undefined) {
        modelSettingsInput.value = JSON.stringify(testCase.model_settings, null, 2);
        // Auto-expand if there are model settings
        if (!modelSettingsCollapse.classList.contains('show')) {
            const bsCollapse = new bootstrap.Collapse(modelSettingsCollapse, { show: true });
        }
    } else {
        modelSettingsInput.value = '';
        // Keep collapsed if no model settings
    }

    // Populate tools
    currentTools = testCase.tools ? JSON.parse(JSON.stringify(testCase.tools)) : [];
    displayTools();

    updateSelectedAgentSummary(testCase);
}

function clearSelection() {
    currentTestCase = null;
    document.getElementById('testCaseSelect').value = '';
    document.getElementById('modelName').value = '';
    document.getElementById('modelSettings').value = '';
    document.getElementById('systemPrompt').value = '';
    document.getElementById('userMessage').value = '';

    // Clear tools
    currentTools = [];
    displayTools();

    disableExecuteButton();
    clearResults();
    updateSelectedAgentSummary(null);
}

function enableExecuteButton() {
    const btn = document.getElementById('executeBtn');
    btn.disabled = false;
    btn.classList.remove('btn-secondary');
    btn.classList.add('btn-success');
}

function disableExecuteButton() {
    const btn = document.getElementById('executeBtn');
    btn.disabled = true;
    btn.classList.remove('btn-success');
    btn.classList.add('btn-secondary');
}

async function executeTest() {
    if (!currentTestCase || isExecuting) {
        return;
    }

    const modelName = document.getElementById('modelName').value.trim();
    const systemPrompt = document.getElementById('systemPrompt').value.trim();
    const userMessage = document.getElementById('userMessage').value.trim();
    const modelSettingsText = document.getElementById('modelSettings').value.trim();

    if (!modelName) {
        showAlert('Please specify a model name', 'warning');
        return;
    }

    setExecutionState(true);

    try {
        // Parse model settings JSON
        let modelSettings = null;
        if (modelSettingsText) {
            try {
                modelSettings = JSON.parse(modelSettingsText);
            } catch (e) {
                showAlert('Invalid JSON in model settings: ' + e.message, 'danger');
                return;
            }
        }

        const requestBody = {
            test_case_id: currentTestCase.id,
            modified_model_name: modelName || null,
            modified_system_prompt: systemPrompt || null,
            modified_last_user_message: userMessage || null,
            modified_model_settings: modelSettings,
            modified_tools: currentTools.length > 0 ? currentTools : null
        };

        const response = await fetch('/v1/api/test-execution/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        displayExecutionResult(result);

    } catch (error) {
        console.error('Error executing test:', error);
        showAlert('Error executing test: ' + error.message, 'danger');
        displayExecutionError(error.message);
    } finally {
        setExecutionState(false);
    }
}

function setExecutionState(executing) {
    isExecuting = executing;
    const executeBtn = document.getElementById('executeBtn');
    const resultStatus = document.getElementById('resultStatus');

    if (executing) {
        executeBtn.disabled = true;
        executeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Executing...';

        // Show running status
        resultStatus.classList.remove('d-none');
        const statusBadge = document.getElementById('statusBadge');
        statusBadge.className = 'badge bg-primary';
        statusBadge.textContent = 'Running';

    } else {
        executeBtn.disabled = false;
        executeBtn.innerHTML = '<i class="fas fa-play me-2"></i>Execute Test';
    }
}

function displayExecutionResult(result) {
    const resultsContainer = document.getElementById('executionResults');
    const resultStatus = document.getElementById('resultStatus');
    const statusBadge = document.getElementById('statusBadge');

    // Update status badge
    resultStatus.classList.remove('d-none');
    if (result.status === 'success') {
        statusBadge.className = 'badge bg-success';
        statusBadge.textContent = 'Success';
    } else {
        statusBadge.className = 'badge bg-danger';
        statusBadge.textContent = 'Failed';
    }

    // Display results
    const responseTime = result.response_time_ms != null ? `${result.response_time_ms}ms` : '—';

    const html = `
        <div class="row mb-3">
            <div class="col-md-8">
                <table class="table table-sm mb-0">
                    <tr><td><strong>Status:</strong></td><td>
                        <span class="status-${result.status}">
                            <i class="fas fa-${result.status === 'success' ? 'check-circle' : 'times-circle'} me-1"></i>
                            ${result.status.toUpperCase()}
                        </span>
                    </td></tr>
                    <tr><td><strong>Response Time:</strong></td><td>${responseTime}</td></tr>
                    <tr><td><strong>Agent:</strong></td><td>${formatAgentContext(result)}</td></tr>
                    <tr><td><strong>Regression:</strong></td><td>${formatRegressionContext(result)}</td></tr>
                    <tr><td><strong>Log ID:</strong></td><td>${result.log_id || '—'}</td></tr>
                </table>
            </div>
            <div class="col-md-4">
                <div class="d-grid gap-1">
                    <button class="btn btn-outline-primary btn-sm" onclick="viewTestLog('${result.log_id}')">
                        <i class="fas fa-eye me-1"></i>View Log
                    </button>
                    <button class="btn btn-outline-secondary btn-sm" onclick="executeTest()">
                        <i class="fas fa-redo me-1"></i>Execute Again
                    </button>
                </div>
            </div>
        </div>

        ${result.error_message ? `
            <div class="alert alert-danger mb-3">
                <strong>Error:</strong> ${escapeHtml(result.error_message)}
            </div>
        ` : ''}

        ${result.llm_response ? `
            <div class="llm-response-container">
                <h6 class="mb-2">LLM Response</h6>
                <div class="llm-response-content">${escapeHtml(result.llm_response)}</div>
            </div>
        ` : ''}
    `;

    resultsContainer.innerHTML = html;
}

function displayExecutionError(errorMessage) {
    const resultsContainer = document.getElementById('executionResults');
    const resultStatus = document.getElementById('resultStatus');
    const statusBadge = document.getElementById('statusBadge');

    // Update status badge
    resultStatus.classList.remove('d-none');
    statusBadge.className = 'badge bg-danger';
    statusBadge.textContent = 'Error';

    const html = `
        <div class="alert alert-danger">
            <h6><i class="fas fa-exclamation-triangle me-2"></i>Execution Failed</h6>
            <p class="mb-0">${escapeHtml(errorMessage)}</p>
        </div>
        <div class="text-center">
            <button class="btn btn-primary" onclick="executeTest()">
                <i class="fas fa-redo me-2"></i>Try Again
            </button>
        </div>
    `;

    resultsContainer.innerHTML = html;
}

function clearResults() {
    const resultsContainer = document.getElementById('executionResults');
    const resultStatus = document.getElementById('resultStatus');

    resultStatus.classList.add('d-none');

    resultsContainer.innerHTML = `
        <div class="text-center text-muted">
            <i class="fas fa-info-circle fa-2x mb-3"></i>
            <p>Select a test case and click "Execute Test" to see results here</p>
        </div>
    `;
}

function updateSelectedAgentSummary(testCase) {
    const summary = document.getElementById('selectedTestCaseAgent');
    if (!summary) return;

    if (!testCase) {
        if (availableAgents.length === 0) {
            summary.innerHTML = '<span class="text-muted">Create an agent to load execution parameters.</span>';
        } else if (availableTestCases.length === 0) {
            summary.innerHTML = '<span class="text-muted">No test cases available for this agent.</span>';
        } else {
            summary.innerHTML = '<span class="text-muted">Select a test case to preview its details.</span>';
        }
        return;
    }

    const resolvedAgent = testCase.agent
        || availableAgents.find((agent) => agent.id === testCase.agent_id)
        || null;
    const agentName = resolvedAgent ? resolvedAgent.name : 'Unknown agent';
    const agentId = testCase.agent_id ? escapeHtml(testCase.agent_id) : '';
    const encodedAgentId = testCase.agent_id ? encodeURIComponent(testCase.agent_id) : '';

    summary.innerHTML = `
        <div class="d-flex flex-column">
            <div>
                <span class="badge bg-primary">${escapeHtml(agentName)}</span>
                ${agentId ? `<small class="text-muted ms-2">${agentId}</small>` : ''}
            </div>
            ${encodedAgentId ? `
                <div class="mt-1 small">
                    <a href="/test-cases?agentId=${encodedAgentId}" class="text-decoration-none" target="_blank">
                        View all test cases for this agent
                        <i class="fas fa-external-link-alt ms-1" style="font-size: 0.75em;"></i>
                    </a>
                </div>
            ` : ''}
        </div>
    `;
}

function formatAgentContext(result) {
    const agentId = result.agent_id || (currentTestCase ? currentTestCase.agent_id : null);
    const agentName = currentTestCase && currentTestCase.agent ? currentTestCase.agent.name : null;

    if (!agentId && !agentName) {
        return '<span class="text-muted">N/A</span>';
    }

    const parts = [];
    if (agentName) {
        parts.push(`<span class="badge bg-primary">${escapeHtml(agentName)}</span>`);
    }
    if (agentId) {
        parts.push(`<small class="text-muted ms-2">${escapeHtml(agentId)}</small>`);
    }
    return parts.join(' ');
}

function formatRegressionContext(result) {
    if (result.regression_test_id) {
        const link = `/regression-tests/${result.regression_test_id}`;
        return `<a href="${link}" target="_blank">${escapeHtml(result.regression_test_id)}</a>`;
    }
    return '<span class="text-muted">Ad-hoc execution</span>';
}

function resetToOriginal() {
    if (currentTestCase) {
        populateExecutionParameters(currentTestCase);
        showAlert('Parameters reset to original values', 'info');
    }
}

function viewTestLogs() {
    if (currentTestCase) {
        window.open(`/test-logs?testCaseId=${currentTestCase.id}`, '_blank');
    } else {
        window.open('/test-logs', '_blank');
    }
}

function viewTestLog(logId) {
    window.open(`/test-logs/${logId}`, '_blank');
}

// Utility functions
function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    const toastRoot = document.getElementById('toast-root');
    if (toastRoot) {
        toastRoot.appendChild(alertDiv);
    } else {
        const container = document.querySelector('.container');
        if (container) {
            if (container.firstChild) {
                container.insertBefore(alertDiv, container.firstChild);
            } else {
                container.appendChild(alertDiv);
            }
        }
    }

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

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// Tools Management Functions
function displayTools() {
    const container = document.getElementById('toolsList');

    if (currentTools.length === 0) {
        container.innerHTML = '<p class="text-muted mb-0">No tools configured</p>';
        return;
    }

    const html = currentTools.map((tool, index) => `
        <div class="tool-item border rounded p-3 mb-2 bg-white">
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    <h6 class="mb-1">
                        <i class="fas fa-wrench me-2 text-primary"></i>
                        ${escapeHtml(tool.function?.name || 'Unknown Tool')}
                    </h6>
                    <p class="text-muted small mb-1">Type: ${escapeHtml(tool.type || 'function')}</p>
                    ${tool.function?.description ? `<p class="text-muted small mb-0">${escapeHtml(tool.function.description)}</p>` : ''}
                </div>
                <div class="btn-group">
                    <button type="button" class="btn btn-sm btn-outline-primary" onclick="editTool(${index})" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-danger" onclick="deleteTool(${index})" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');

    container.innerHTML = html;
}

function addTool() {
    editingToolIndex = -1;
    document.getElementById('toolEditorForm').reset();
    document.getElementById('toolIndex').value = '';
    document.querySelector('#toolEditorModal .modal-title').textContent = 'Add Tool Configuration';

    // Set default parameters schema
    document.getElementById('toolParameters').value = JSON.stringify({
        "type": "object",
        "properties": {},
        "required": []
    }, null, 2);

    const modal = new bootstrap.Modal(document.getElementById('toolEditorModal'));
    modal.show();
}

function editTool(index) {
    editingToolIndex = index;
    const tool = currentTools[index];

    document.getElementById('toolIndex').value = index;
    document.getElementById('toolType').value = tool.type || 'function';
    document.getElementById('toolName').value = tool.function?.name || '';
    document.getElementById('toolDescription').value = tool.function?.description || '';
    document.getElementById('toolParameters').value = JSON.stringify(tool.function?.parameters || {}, null, 2);
    document.getElementById('toolStrict').checked = tool.function?.strict === true;

    document.querySelector('#toolEditorModal .modal-title').textContent = 'Edit Tool Configuration';

    const modal = new bootstrap.Modal(document.getElementById('toolEditorModal'));
    modal.show();
}

function deleteTool(index) {
    if (confirm('Are you sure you want to delete this tool?')) {
        currentTools.splice(index, 1);
        displayTools();
        showAlert('Tool deleted successfully', 'success');
    }
}

function saveTool() {
    const type = document.getElementById('toolType').value;
    const name = document.getElementById('toolName').value.trim();
    const description = document.getElementById('toolDescription').value.trim();
    const parametersText = document.getElementById('toolParameters').value.trim();
    const strict = document.getElementById('toolStrict').checked;

    if (!name) {
        showAlert('Please enter a function name', 'warning');
        return;
    }

    if (!parametersText) {
        showAlert('Please enter parameters schema', 'warning');
        return;
    }

    let parameters;
    try {
        parameters = JSON.parse(parametersText);
    } catch (e) {
        showAlert('Invalid JSON in parameters schema', 'danger');
        return;
    }

    const tool = {
        type: type,
        function: {
            name: name,
            description: description || undefined,
            parameters: parameters
        }
    };

    if (strict) {
        tool.function.strict = true;
    }

    if (editingToolIndex >= 0) {
        currentTools[editingToolIndex] = tool;
        showAlert('Tool updated successfully', 'success');
    } else {
        currentTools.push(tool);
        showAlert('Tool added successfully', 'success');
    }

    displayTools();

    const modal = bootstrap.Modal.getInstance(document.getElementById('toolEditorModal'));
    modal.hide();
}

function resetTools() {
    if (currentTestCase && currentTestCase.tools) {
        currentTools = JSON.parse(JSON.stringify(currentTestCase.tools));
        displayTools();
        showAlert('Tools reset to original configuration', 'info');
    } else {
        currentTools = [];
        displayTools();
        showAlert('Tools cleared', 'info');
    }
}

// Model Name History Management Functions
function setupModelNameInput() {
    const modelNameInput = document.getElementById('modelName');
    const dropdown = document.getElementById('modelNameDropdown');

    // Load and display history on focus
    modelNameInput.addEventListener('focus', function () {
        showModelHistory();
    });

    // Hide dropdown when clicking outside
    document.addEventListener('click', function (event) {
        if (!modelNameInput.contains(event.target) && !dropdown.contains(event.target)) {
            hideModelHistory();
        }
    });

    // Filter history as user types
    modelNameInput.addEventListener('input', function () {
        const value = this.value.trim();
        if (value.length > 0) {
            filterModelHistory(value);
        } else {
            showModelHistory();
        }
    });

    // Save to history when user finishes typing (on blur or enter)
    modelNameInput.addEventListener('blur', function () {
        const value = this.value.trim();
        if (value) {
            saveModelToHistory(value);
        }

        // Only hide if not clicking in dropdown
        setTimeout(() => {
            if (!pointerDownInDropdown) {
                hideModelHistory();
            }
            pointerDownInDropdown = false;
        }, 0);
    });

    modelNameInput.addEventListener('keydown', function (event) {
        if (event.key === 'Enter') {
            const value = this.value.trim();
            if (value) {
                saveModelToHistory(value);
            }
            hideModelHistory();
        } else if (event.key === 'Escape') {
            hideModelHistory();
        }
    });
}

function getModelHistory() {
    try {
        const history = localStorage.getItem(MODEL_HISTORY_KEY);
        return history ? JSON.parse(history) : [];
    } catch (error) {
        console.error('Error loading model history:', error);
        return [];
    }
}

function saveModelToHistory(modelName) {
    if (!modelName || modelName.trim() === '') return;

    try {
        let history = getModelHistory();

        // Remove if already exists (to move to top)
        history = history.filter(item => item !== modelName);

        // Add to beginning
        history.unshift(modelName);

        // Limit to MAX_HISTORY_ITEMS
        if (history.length > MAX_HISTORY_ITEMS) {
            history = history.slice(0, MAX_HISTORY_ITEMS);
        }

        localStorage.setItem(MODEL_HISTORY_KEY, JSON.stringify(history));
    } catch (error) {
        console.error('Error saving model history:', error);
    }
}

function removeFromModelHistory(modelName) {
    try {
        let history = getModelHistory();
        history = history.filter(item => item !== modelName);
        localStorage.setItem(MODEL_HISTORY_KEY, JSON.stringify(history));
        showModelHistory(); // Refresh the dropdown
    } catch (error) {
        console.error('Error removing from model history:', error);
    }
}

function showModelHistory() {
    const dropdown = document.getElementById('modelNameDropdown');
    const history = getModelHistory();

    if (history.length === 0) {
        dropdown.classList.remove('show');
        return;
    }

    dropdown.innerHTML = '';

    history.forEach(modelName => {
        const item = document.createElement('div');
        item.className = 'dropdown-item d-flex justify-content-between align-items-center';
        item.style.cursor = 'pointer';

        const modelText = document.createElement('span');
        modelText.textContent = modelName;
        modelText.style.flex = '1';

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-sm btn-outline-danger ms-2';
        deleteBtn.innerHTML = '<i class="fas fa-times"></i>';
        deleteBtn.title = 'Remove from history';
        deleteBtn.style.fontSize = '0.75rem';
        deleteBtn.style.padding = '0.125rem 0.25rem';

        // Use mousedown to set value before input loses focus
        item.addEventListener('mousedown', function (e) {
            if (e.target === deleteBtn || deleteBtn.contains(e.target)) {
                removeFromModelHistory(modelName);
                return;
            }

            pointerDownInDropdown = true;
            document.getElementById('modelName').value = modelName;
            saveModelToHistory(modelName);
        });

        item.addEventListener('mouseup', function () {
            hideModelHistory();
            pointerDownInDropdown = false;
        });

        item.appendChild(modelText);
        item.appendChild(deleteBtn);
        dropdown.appendChild(item);
    });

    dropdown.classList.add('show');
}

function filterModelHistory(searchTerm) {
    const dropdown = document.getElementById('modelNameDropdown');
    const history = getModelHistory();

    const filtered = history.filter(modelName =>
        modelName.toLowerCase().includes(searchTerm.toLowerCase())
    );

    if (filtered.length === 0) {
        dropdown.classList.remove('show');
        return;
    }

    dropdown.innerHTML = '';

    filtered.forEach(modelName => {
        const item = document.createElement('div');
        item.className = 'dropdown-item d-flex justify-content-between align-items-center';
        item.style.cursor = 'pointer';

        const modelText = document.createElement('span');
        modelText.textContent = modelName;
        modelText.style.flex = '1';

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-sm btn-outline-danger ms-2';
        deleteBtn.innerHTML = '<i class="fas fa-times"></i>';
        deleteBtn.title = 'Remove from history';
        deleteBtn.style.fontSize = '0.75rem';
        deleteBtn.style.padding = '0.125rem 0.25rem';

        // Use mousedown to set value before input loses focus
        item.addEventListener('mousedown', function (e) {
            if (e.target === deleteBtn || deleteBtn.contains(e.target)) {
                removeFromModelHistory(modelName);
                return;
            }

            pointerDownInDropdown = true;
            document.getElementById('modelName').value = modelName;
            saveModelToHistory(modelName);
        });

        item.addEventListener('mouseup', function () {
            hideModelHistory();
            pointerDownInDropdown = false;
        });

        item.appendChild(modelText);
        item.appendChild(deleteBtn);
        dropdown.appendChild(item);
    });

    dropdown.classList.add('show');
}

function hideModelHistory() {
    const dropdown = document.getElementById('modelNameDropdown');
    dropdown.classList.remove('show');
}
