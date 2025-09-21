/**
 * Regression Tests Management JavaScript
 *
 * Coordinates regression history listing and launching new runs.
 */

let regressionTests = [];
let agentOptions = [];
let currentFilters = { agentId: '', status: '' };
let refreshTimeout = null;

window.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    initializeData();
});

async function initializeData() {
    await loadAgents();
    await loadRegressions();
}

function setupEventListeners() {
    const refreshBtn = document.getElementById('refreshRegressionsBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => loadRegressions());
    }

    const clearFiltersBtn = document.getElementById('clearFiltersBtn');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', () => {
            const agentFilter = document.getElementById('agentFilter');
            const statusFilter = document.getElementById('statusFilter');
            if (agentFilter) agentFilter.value = '';
            if (statusFilter) statusFilter.value = '';
            currentFilters = { agentId: '', status: '' };
            loadRegressions();
        });
    }

    const agentFilter = document.getElementById('agentFilter');
    if (agentFilter) {
        agentFilter.addEventListener('change', (event) => {
            currentFilters.agentId = event.target.value;
            loadRegressions();
        });
        agentFilter.value = currentFilters.agentId;
    }

    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', (event) => {
            currentFilters.status = event.target.value;
            loadRegressions();
        });
        statusFilter.value = currentFilters.status;
    }

    const startRegressionBtn = document.getElementById('confirmStartRegression');
    if (startRegressionBtn) {
        startRegressionBtn.addEventListener('click', startRegression);
    }

    const regressionAgentSelect = document.getElementById('regressionAgentSelect');
    if (regressionAgentSelect) {
        regressionAgentSelect.addEventListener('change', (event) => populateDefaultsForAgent(event.target.value));
    }

    const startModal = document.getElementById('startRegressionModal');
    if (startModal) {
        startModal.addEventListener('shown.bs.modal', () => {
            clearModalAlert('startRegressionAlert');
            const settingsInput = document.getElementById('regressionModelSettings');
            if (settingsInput && !settingsInput.value.trim()) {
                settingsInput.value = '{}';
            }
            if (agentOptions.length === 1) {
                document.getElementById('regressionAgentSelect').value = agentOptions[0].id;
                populateDefaultsForAgent(agentOptions[0].id);
            }
        });

        startModal.addEventListener('hidden.bs.modal', () => {
            document.getElementById('startRegressionForm').reset();
            clearModalAlert('startRegressionAlert');
        });
    }

}

async function loadAgents() {
    try {
        const response = await fetch('/v1/api/agents/');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const agents = await response.json();
        agentOptions = agents.filter((agent) => !agent.is_deleted);
        populateAgentFilter(agentOptions);
        populateRegressionAgentSelect(agentOptions);
    } catch (error) {
        console.error('Error loading agents:', error);
        showAlert('Error loading agents: ' + error.message, 'danger');
    }
}

function createRegressionsUrl() {
    const url = new URL('/v1/api/regression-tests/', window.location.origin);
    if (currentFilters.agentId) {
        url.searchParams.append('agent_id', currentFilters.agentId);
    }
    if (currentFilters.status) {
        url.searchParams.append('status', currentFilters.status);
    }
    url.searchParams.append('limit', '100');
    return url;
}

async function loadRegressions() {
    toggleLoading(true);
    if (refreshTimeout) {
        clearTimeout(refreshTimeout);
        refreshTimeout = null;
    }

    try {
        const url = createRegressionsUrl();

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        regressionTests = await response.json();
        displayRegressionTests(regressionTests);
        scheduleAutoRefresh(regressionTests);
    } catch (error) {
        console.error('Error loading regression tests:', error);
        showAlert('Error loading regression tests: ' + error.message, 'danger');
    } finally {
        toggleLoading(false);
    }
}

function displayRegressionTests(regressions) {
    const container = document.getElementById('regressionTestsList');
    const table = document.getElementById('regressionTestsTable');
    const emptyState = document.getElementById('emptyState');

    if (!container || !table || !emptyState) {
        return;
    }

    if (!regressions || regressions.length === 0) {
        container.innerHTML = '';
        table.style.display = 'none';
        emptyState.classList.remove('d-none');
        return;
    }

    emptyState.classList.add('d-none');
    table.style.display = 'table';

    container.innerHTML = regressions.map(buildRegressionRow).join('');
}

function buildRegressionRow(regression) {
    const statusBadge = buildStatusBadge(regression.status);
    const agentName = regression.agent ? regression.agent.name : 'Unknown agent';
    const overrides = `
        <div class="d-flex flex-column gap-1">
            <span class="badge bg-primary">${escapeHtml(regression.model_name_override)}</span>
            <small class="text-muted text-truncate" style="max-width: 260px;" title="${escapeHtml(regression.system_prompt_override)}">
                ${escapeHtml(truncateText(regression.system_prompt_override, 120))}
            </small>
        </div>
    `;
    const settings = `<code class="text-muted">${escapeHtml(truncateText(JSON.stringify(regression.model_settings_override), 120))}</code>`;
    const results = `
        <div class="d-flex flex-wrap gap-2">
            <span class="badge bg-primary">Total ${regression.total_count}</span>
            <span class="badge bg-success">Passed ${regression.success_count}</span>
            <span class="badge bg-danger">Failed ${regression.failed_count}</span>
        </div>
    `;

    const started = formatDate(regression.started_at);
    const completed = formatDate(regression.completed_at);
    const timing = `
        <div class="d-flex flex-column">
            <span><strong>Start:</strong> ${started}</span>
            <span><strong>End:</strong> ${completed}</span>
        </div>
    `;

    return `
        <tr data-regression-id="${escapeHtml(regression.id)}">
            <td>
                <div class="d-flex flex-column">
                    <strong>${escapeHtml(agentName)}</strong>
                    <small class="text-muted">${escapeHtml(regression.id)}</small>
                </div>
            </td>
            <td>${statusBadge}</td>
            <td>
                ${overrides}
                <div class="small mt-2">${settings}</div>
            </td>
            <td>${results}</td>
            <td>${timing}</td>
            <td class="text-end">
                <div class="btn-group btn-group-sm" role="group">
                    <button type="button" class="btn btn-outline-primary" onclick="openRegressionDetail('${regression.id}')">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button type="button" class="btn btn-outline-secondary" onclick="loadRegressions()" title="Refresh list">
                        <i class="fas fa-rotate"></i>
                    </button>
                </div>
            </td>
        </tr>
    `;
}

function buildStatusBadge(status) {
    const normalized = (status || '').toLowerCase();
    switch (normalized) {
        case 'pending':
            return '<span class="badge bg-secondary"><i class="fas fa-clock me-1"></i>Pending</span>';
        case 'running':
            return '<span class="badge bg-warning"><i class="fas fa-spinner fa-spin me-1"></i>Running</span>';
        case 'completed':
            return '<span class="badge bg-success"><i class="fas fa-check me-1"></i>Completed</span>';
        case 'failed':
            return '<span class="badge bg-danger"><i class="fas fa-triangle-exclamation me-1"></i>Failed</span>';
        default:
            return `<span class="badge bg-secondary">${escapeHtml(status)}</span>`;
    }
}

function populateAgentFilter(agents) {
    const filter = document.getElementById('agentFilter');
    if (!filter) return;

    filter.innerHTML = '<option value="">All agents</option>';
    agents.forEach((agent) => {
        const option = document.createElement('option');
        option.value = agent.id;
        option.textContent = agent.name;
        filter.appendChild(option);
    });

    if (currentFilters.agentId) {
        filter.value = currentFilters.agentId;
    }
}

function populateRegressionAgentSelect(agents) {
    const select = document.getElementById('regressionAgentSelect');
    const startButton = document.getElementById('startRegressionBtn');
    if (!select) return;

    select.innerHTML = '<option value="">Select an agent...</option>';
    agents.forEach((agent) => {
        const option = document.createElement('option');
        option.value = agent.id;
        option.textContent = agent.name;
        select.appendChild(option);
    });

    if (startButton) {
        startButton.disabled = agents.length === 0;
    }
}

function populateDefaultsForAgent(agentId) {
    if (!agentId) {
        return;
    }

    const agent = agentOptions.find((item) => item.id === agentId);
    if (!agent) {
        return;
    }

    document.getElementById('regressionModelName').value = agent.default_model_name || '';
    document.getElementById('regressionSystemPrompt').value = agent.default_system_prompt || '';
    const settings = agent.default_model_settings ? JSON.stringify(agent.default_model_settings, null, 2) : '{}';
    document.getElementById('regressionModelSettings').value = settings;
}

async function startRegression() {
    const agentSelect = document.getElementById('regressionAgentSelect');
    const modelNameInput = document.getElementById('regressionModelName');
    const systemPromptInput = document.getElementById('regressionSystemPrompt');
    const modelSettingsInput = document.getElementById('regressionModelSettings');

    const agentId = agentSelect.value;
    const modelName = modelNameInput.value.trim();
    const systemPrompt = systemPromptInput.value.trim();
    const modelSettingsText = modelSettingsInput.value.trim();

    if (!agentId || !modelName || !systemPrompt || !modelSettingsText) {
        showModalAlert('startRegressionAlert', 'All override fields are required.', 'warning');
        return;
    }

    let modelSettings;
    try {
        modelSettings = JSON.parse(modelSettingsText);
    } catch (error) {
        showModalAlert('startRegressionAlert', 'Model settings must be valid JSON. ' + error.message, 'danger');
        return;
    }

    const payload = {
        agent_id: agentId,
        model_name_override: modelName,
        system_prompt_override: systemPrompt,
        model_settings_override: modelSettings,
    };

    const confirmButton = document.getElementById('confirmStartRegression');
    if (confirmButton) {
        confirmButton.disabled = true;
        confirmButton.dataset.originalText = confirmButton.innerHTML;
        confirmButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Launching…';
    }

    try {
        const response = await fetch('/v1/api/regression-tests/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const errorData = await safeJson(response);
            const message = errorData?.detail || `HTTP error! status: ${response.status}`;
            throw new Error(message);
        }

        bootstrap.Modal.getInstance(document.getElementById('startRegressionModal')).hide();
        showAlert('Regression run started successfully.', 'success');
        loadRegressions();
    } catch (error) {
        console.error('Error starting regression:', error);
        showModalAlert('startRegressionAlert', 'Error starting regression: ' + error.message, 'danger');
    } finally {
        if (confirmButton) {
            confirmButton.disabled = false;
            confirmButton.innerHTML = confirmButton.dataset.originalText || confirmButton.innerHTML;
            delete confirmButton.dataset.originalText;
        }
    }
}

function scheduleAutoRefresh(regressions) {
    if (refreshTimeout) {
        clearTimeout(refreshTimeout);
        refreshTimeout = null;
    }

    const hasRunning = regressions.some((item) => ['pending', 'running'].includes((item.status || '').toLowerCase()));
    if (hasRunning) {
        refreshTimeout = setTimeout(() => {
            refreshRunningRegressions();
        }, 1000);
    }
}

async function refreshRunningRegressions() {
    try {
        const url = createRegressionsUrl();
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const updatedRegressions = await response.json();
        regressionTests = updatedRegressions;
        updateRegressionRows(updatedRegressions);
    } catch (error) {
        console.error('Error refreshing regression tests:', error);
    } finally {
        scheduleAutoRefresh(regressionTests);
    }
}

function updateRegressionRows(regressions) {
    const container = document.getElementById('regressionTestsList');
    const table = document.getElementById('regressionTestsTable');
    const emptyState = document.getElementById('emptyState');
    if (!container || !table || !emptyState) {
        return;
    }

    if (!regressions || regressions.length === 0) {
        displayRegressionTests(regressions);
        return;
    }

    emptyState.classList.add('d-none');
    table.style.display = 'table';

    const activeIds = new Set();
    const existingRowsMap = new Map();
    Array.from(container.querySelectorAll('tr[data-regression-id]')).forEach((row) => {
        const id = row.getAttribute('data-regression-id');
        if (id) {
            existingRowsMap.set(id, row);
        }
    });

    regressions.forEach((regression, index) => {
        const wrapper = document.createElement('tbody');
        wrapper.innerHTML = buildRegressionRow(regression).trim();
        const newRow = wrapper.firstElementChild;
        if (!newRow) {
            return;
        }

        const existingRow = existingRowsMap.get(regression.id);

        if (existingRow) {
            existingRow.replaceWith(newRow);
            existingRowsMap.set(regression.id, newRow);
        } else if (container.children[index]) {
            container.insertBefore(newRow, container.children[index]);
        } else {
            container.appendChild(newRow);
        }

        activeIds.add(regression.id);
    });

    existingRowsMap.forEach((row, regressionId) => {
        if (!activeIds.has(regressionId) && row.isConnected) {
            row.remove();
        }
    });
}

}

function openRegressionDetail(regressionId) {
    window.open(`/regression-tests/${regressionId}`, '_blank');
}

function toggleLoading(show) {
    const spinner = document.getElementById('loadingSpinner');
    const table = document.getElementById('regressionTestsTable');
    if (!spinner || !table) return;

    if (show) {
        spinner.classList.remove('d-none');
        table.classList.add('d-none');
    } else {
        spinner.classList.add('d-none');
        table.classList.remove('d-none');
    }
}

async function safeJson(response) {
    try {
        return await response.json();
    } catch (error) {
        return null;
    }
}

function showAlert(message, type) {
    const container = document.querySelector('.container');
    if (!container) return;

    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    container.insertBefore(alert, container.firstChild);

    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 6000);
}

function showModalAlert(containerId, message, type) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = `
        <div class="alert alert-${type}" role="alert">
            ${message}
        </div>
    `;
}

function clearModalAlert(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = '';
    }
}

function escapeHtml(text) {
    if (text === null || text === undefined) {
        return '';
    }
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function truncateText(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '…';
}

function formatDate(dateString) {
    if (!dateString) {
        return '<span class="text-muted">—</span>';
    }
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) {
        return escapeHtml(dateString);
    }
    return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
}

window.openRegressionDetail = openRegressionDetail;
