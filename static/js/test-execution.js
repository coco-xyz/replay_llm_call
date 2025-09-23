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
let initialTestCaseId = '';

// Initialize page
document.addEventListener('DOMContentLoaded', () => {
    initializeTestExecutionPage().catch((error) => {
        console.error('Failed to initialize test execution page:', error);
        showAlert('Failed to initialize test execution page: ' + error.message, 'danger');
    });
});

async function initializeTestExecutionPage() {
    setupEventListeners();

    const urlParams = new URLSearchParams(window.location.search);
    const logId = urlParams.get('logId');
    const initialAgentId = urlParams.get('agentId');
    initialTestCaseId = urlParams.get('testCaseId') || '';

    let logData = null;

    if (logId) {
        try {
            logData = await fetchTestLogDetails(logId);
            selectedAgentId = logData.agent_id || '';
        } catch (error) {
            console.error('Unable to load log for re-execution:', error);
            showAlert('Unable to load log for re-execution: ' + error.message, 'warning');
        }
    } else if (initialAgentId) {
        selectedAgentId = initialAgentId;
    }

    await loadAgents();
    await loadTestCases();

    if (logData) {
        await prefillExecutionFromLog(logData);
        return;
    }

    if (initialTestCaseId) {
        const select = document.getElementById('testCaseSelect');
        if (select) {
            select.value = initialTestCaseId;
        }
        await selectTestCase(initialTestCaseId);
    }
}

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

    // Add validation listeners for required fields
    const modelNameInput = document.getElementById('modelName');
    const systemPromptInput = document.getElementById('systemPrompt');
    const userMessageInput = document.getElementById('userMessage');

    if (modelNameInput) {
        modelNameInput.addEventListener('input', validateExecutionForm);
    }
    if (systemPromptInput) {
        systemPromptInput.addEventListener('input', validateExecutionForm);
    }
    if (userMessageInput) {
        userMessageInput.addEventListener('input', validateExecutionForm);
    }
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
        updateSelectedTestCaseInfo(null);
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

    updateSelectedTestCaseInfo(null);
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
        validateExecutionForm();

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

        validateExecutionForm();
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

    updateSelectedTestCaseInfo(testCase);

    // Validate form after populating
    validateExecutionForm();
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
    updateSelectedTestCaseInfo(null);
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

function validateExecutionForm() {
    const modelNameInput = document.getElementById('modelName');
    const systemPromptInput = document.getElementById('systemPrompt');
    const userMessageInput = document.getElementById('userMessage');

    const modelName = modelNameInput.value.trim();
    const systemPrompt = systemPromptInput.value.trim();
    const userMessage = userMessageInput.value.trim();

    // Remove previous validation classes
    modelNameInput.classList.remove('is-invalid');
    systemPromptInput.classList.remove('is-invalid');
    userMessageInput.classList.remove('is-invalid');

    // Check each field and add validation classes
    let isValid = true;

    if (!modelName) {
        modelNameInput.classList.add('is-invalid');
        isValid = false;
    }

    if (!systemPrompt) {
        systemPromptInput.classList.add('is-invalid');
        isValid = false;
    }

    if (!userMessage) {
        userMessageInput.classList.add('is-invalid');
        isValid = false;
    }

    if (!currentTestCase) {
        isValid = false;
    }

    if (isValid) {
        enableExecuteButton();
    } else {
        disableExecuteButton();
    }

    return isValid;
}

async function executeTest() {
    if (!currentTestCase || isExecuting) {
        return;
    }

    const modelName = document.getElementById('modelName').value.trim();
    const systemPrompt = document.getElementById('systemPrompt').value.trim();
    const userMessage = document.getElementById('userMessage').value.trim();
    const modelSettingsText = document.getElementById('modelSettings').value.trim();

    // Validate required fields
    if (!modelName) {
        showAlert('Please specify a model name', 'warning');
        document.getElementById('modelName').focus();
        return;
    }

    if (!systemPrompt) {
        showAlert('Please specify a system prompt', 'warning');
        document.getElementById('systemPrompt').focus();
        return;
    }

    if (!userMessage) {
        showAlert('Please specify a user message', 'warning');
        document.getElementById('userMessage').focus();
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
    const evaluationBadge = formatEvaluationBadge(result);
    const evaluationModel = escapeHtml(result.evaluation_model_name || '—');

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
                    <tr><td><strong>Evaluation Result:</strong></td><td>${evaluationBadge}</td></tr>
                    <tr><td><strong>Evaluation Model:</strong></td><td>${evaluationModel}</td></tr>
                    <tr><td><strong>Log ID:</strong></td><td>${escapeHtml(result.log_id || '—')}</td></tr>
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
    applyTooltipContent(resultsContainer);
    if (window.HoverTooltip) {
        window.HoverTooltip.attach(resultsContainer);
    }
    initializeTooltips(resultsContainer);
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

function updateSelectedTestCaseInfo(testCase) {
    const summary = document.getElementById('selectedTestCaseInfo');
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

    const testCaseName = testCase.name ? escapeHtml(testCase.name) : 'Unknown test case';
    const testCaseId = testCase.id ? escapeHtml(testCase.id) : '';
    const encodedTestCaseId = testCase.id ? encodeURIComponent(testCase.id) : '';

    summary.innerHTML = `
        <div class="d-flex flex-column">
            <div>
                <span class="badge bg-success">${testCaseName}</span>
                ${testCaseId ? `<small class="text-muted ms-2">${testCaseId}</small>` : ''}
            </div>
            ${encodedTestCaseId ? `
                <div class="mt-1 small">
                    <a href="/test-cases/${encodedTestCaseId}" class="text-decoration-none" target="_blank">
                        View test case details
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

function resolveEvaluationDisplay(target) {
    const status = target && typeof target.is_passed !== 'undefined' ? target.is_passed : null;
    if (status === true) {
        return { label: 'Passed', badgeClass: 'bg-success', icon: 'check' };
    }
    if (status === false) {
        return { label: 'Failed', badgeClass: 'bg-danger', icon: 'times' };
    }
    return { label: 'Unknown', badgeClass: 'bg-secondary', icon: 'question' };
}

function buildEvaluationTooltip(result) {
    if (!result) {
        return 'Evaluation details unavailable.';
    }

    const lines = [];
    const feedback = (result.evaluation_feedback || '').trim();
    if (feedback) {
        lines.push(feedback);
    }



    if (result.evaluation_model_name) {
        lines.push(`Model: ${result.evaluation_model_name}`);
    }

    const metadata = result.evaluation_metadata || {};
    if (Array.isArray(metadata.missing_criteria) && metadata.missing_criteria.length > 0) {
        lines.push(`Missing criteria:\n- ${metadata.missing_criteria.join('\n- ')}`);
    }
    if (Array.isArray(metadata.satisfied_criteria) && metadata.satisfied_criteria.length > 0) {
        lines.push(`Satisfied criteria:\n- ${metadata.satisfied_criteria.join('\n- ')}`);
    }

    if (lines.length === 0) {
        const display = resolveEvaluationDisplay(result);
        if (display.label === 'Passed') {
            lines.push('Marked as passed.');
        } else if (display.label === 'Failed') {
            lines.push('Marked as failed.');
        } else {
            lines.push('Evaluation skipped or not applicable.');
        }
    }

    return lines.join('\n\n');
}

function formatEvaluationBadge(result) {
    const display = resolveEvaluationDisplay(result);
    const tooltipContent = encodeTooltipPayload(buildEvaluationTooltip(result));
    const fallback = encodeTooltipPayload(display.label);

    return `
        <span class="badge ${display.badgeClass} log-preview"
              data-bs-toggle="tooltip" data-bs-placement="top"
              data-bs-custom-class="log-tooltip" data-bs-html="true"
              data-tooltip-content="${tooltipContent}" data-tooltip-fallback="${fallback}">
            <i class="fas fa-${display.icon} me-1"></i>${display.label}
        </span>
    `;
}

function formatEvaluationFeedback(feedback) {
    if (!feedback) {
        return '<span class="text-muted">—</span>';
    }
    const trimmed = feedback.trim();
    if (!trimmed) {
        return '<span class="text-muted">—</span>';
    }

    // If feedback is short enough, display it directly
    const maxLength = 150;
    if (trimmed.length <= maxLength) {
        return `<div class="text-break" style="white-space: pre-wrap;">${escapeHtml(trimmed)}</div>`;
    }

    // For long feedback, create a truncated version with hover tooltip
    const truncated = trimmed.substring(0, maxLength) + '...';

    return `<div class="log-preview" data-hover-html="${formatTooltipContent(trimmed)}" style="white-space: pre-wrap;">${escapeHtml(truncated)}</div>`;
}



function formatTooltipContent(text, fallback = '—') {
    if (!text) {
        return `<div class='tooltip-log-content'>${escapeHtml(fallback)}</div>`;
    }
    const normalized = text.trim();
    if (!normalized) {
        return `<div class='tooltip-log-content'>${escapeHtml(fallback)}</div>`;
    }
    const htmlContent = escapeHtml(text).replace(/\n/g, '<br>');
    return `<div class='tooltip-log-content'>${htmlContent}</div>`;
}

function encodeTooltipPayload(text) {
    if (!text) {
        return '';
    }
    return encodeURIComponent(text);
}

function decodeTooltipPayload(value) {
    if (!value) {
        return '';
    }
    try {
        return decodeURIComponent(value);
    } catch (error) {
        console.error('Failed to decode tooltip payload', error);
        return value;
    }
}

function applyTooltipContent(container) {
    if (!container) {
        return;
    }
    const tooltipTargets = container.querySelectorAll('[data-tooltip-content]');
    tooltipTargets.forEach((element) => {
        const encodedContent = element.getAttribute('data-tooltip-content') || '';
        const encodedFallback = element.getAttribute('data-tooltip-fallback') || '';
        const content = decodeTooltipPayload(encodedContent);
        const fallback = decodeTooltipPayload(encodedFallback);
        const tooltipHtml = formatTooltipContent(content, fallback || undefined);
        element.setAttribute('data-bs-title', tooltipHtml);
        element.setAttribute('data-hover-html', tooltipHtml);
    });
}

function initializeTooltips(container) {
    if (typeof bootstrap === 'undefined' || !bootstrap.Tooltip) {
        return;
    }
    const scope = container || document;
    const elements = scope.querySelectorAll
        ? scope.querySelectorAll('[data-bs-toggle="tooltip"]:not(.log-preview)')
        : document.querySelectorAll('[data-bs-toggle="tooltip"]:not(.log-preview)');
    elements.forEach((element) => {
        bootstrap.Tooltip.getOrCreateInstance(element);
    });
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
    if (!window.ModelHistoryManager) {
        console.warn('ModelHistoryManager is not available.');
        return;
    }

    window.ModelHistoryManager.initInput({
        inputId: 'modelName',
        dropdownId: 'modelNameDropdown',
    });
}

// Tooltip utility functions
function formatTooltipContent(text, fallback = '—') {
    if (!text) {
        return `<div class='tooltip-log-content'>${escapeHtml(fallback)}</div>`;
    }
    const trimmed = text.trim();
    if (!trimmed) {
        return `<div class='tooltip-log-content'>${escapeHtml(fallback)}</div>`;
    }
    const htmlContent = escapeHtml(text).replace(/\n/g, '<br>');
    return `<div class='tooltip-log-content'>${htmlContent}</div>`;
}

function encodeTooltipPayload(text) {
    if (!text) {
        return '';
    }
    return encodeURIComponent(text);
}

function decodeTooltipPayload(value) {
    if (!value) {
        return '';
    }
    try {
        return decodeURIComponent(value);
    } catch (error) {
        console.error('Failed to decode tooltip payload', error);
        return value;
    }
}

function applyTooltipContent(container) {
    if (!container) {
        return;
    }
    const tooltipTargets = container.querySelectorAll('[data-tooltip-content]');
    tooltipTargets.forEach((element) => {
        const encodedContent = element.getAttribute('data-tooltip-content') || '';
        const encodedFallback = element.getAttribute('data-tooltip-fallback') || '';
        const content = decodeTooltipPayload(encodedContent);
        const fallback = decodeTooltipPayload(encodedFallback);
        const tooltipHtml = formatTooltipContent(content, fallback || undefined);
        element.setAttribute('data-bs-title', tooltipHtml);
        element.setAttribute('data-hover-html', tooltipHtml);
    });
}

function initializeTooltips(container) {
    if (typeof bootstrap === 'undefined' || !bootstrap.Tooltip) {
        return;
    }
    const selector = container ? '[data-bs-toggle="tooltip"]:not(.log-preview)' : '[data-bs-toggle="tooltip"]:not(.log-preview)';
    const tooltipTriggerList = [].slice.call(
        container ? container.querySelectorAll(selector) : document.querySelectorAll(selector)
    );
    tooltipTriggerList.forEach((tooltipTriggerEl) => {
        bootstrap.Tooltip.getOrCreateInstance(tooltipTriggerEl);
    });
}
