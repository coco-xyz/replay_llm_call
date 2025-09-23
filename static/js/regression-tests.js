/**
 * Regression Tests Management JavaScript
 *
 * Coordinates regression history listing and launching new runs.
 */
const PAGE_SIZE = 20;
const FETCH_LIMIT = PAGE_SIZE + 1;

let regressionTests = [];
let currentFilters = { agentId: '', status: '' };
let refreshTimeout = null;
let currentPage = 1;
let hasNextPage = false;

const agentCache = new Map();
const pendingAgentRequests = new Map();

const agentAutocompleteConfigs = {
    filter: {
        inputId: 'agentFilterInput',
        hiddenId: 'agentFilter',
        resultsId: 'agentFilterResults',
        onSelect(agent) {
            if (currentFilters.agentId !== agent.id) {
                currentFilters.agentId = agent.id;
                currentPage = 1;
                loadRegressions(1);
            }
        },
        onClear() {
            if (currentFilters.agentId) {
                currentFilters.agentId = '';
                currentPage = 1;
                loadRegressions(1);
            }
        },
    },
    modal: {
        inputId: 'regressionAgentInput',
        hiddenId: 'regressionAgentId',
        resultsId: 'regressionAgentResults',
        onSelect(agent) {
            populateDefaultsForAgent(agent);
        },
        onClear() {
            populateDefaultsForAgent(null);
        },
    },
};

window.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    initializeData();
});

async function initializeData() {
    const urlParams = new URLSearchParams(window.location.search);
    currentFilters.agentId = urlParams.get('agentId') || '';
    currentFilters.status = urlParams.get('status') || '';

    setupAgentAutocompleteControls();
    await hydrateFilterInputs();
    await loadRegressions(1);
}

function setupAgentAutocompleteControls() {
    Object.entries(agentAutocompleteConfigs).forEach(([key, config]) => {
        setupAgentAutocomplete(key, config);
    });
}

function setupAgentAutocomplete(key, config) {
    const input = document.getElementById(config.inputId);
    const hidden = document.getElementById(config.hiddenId);
    const results = document.getElementById(config.resultsId);
    if (!input || !hidden || !results) {
        return;
    }

    let debounceTimer = null;
    let activeController = null;

    const closeResults = () => {
        results.classList.add('d-none');
        results.innerHTML = '';
    };

    const selectResult = (agent) => {
        hidden.value = agent.id;
        input.value = agent.name;
        agentCache.set(agent.id, agent);
        closeResults();
        if (typeof config.onSelect === 'function') {
            config.onSelect(agent);
        }
    };

    const renderResults = (items) => {
        if (!items || items.length === 0) {
            results.innerHTML = '<div class="filter-search-empty">No matches</div>';
            results.classList.remove('d-none');
            return;
        }

        const fragment = document.createDocumentFragment();
        items.forEach((agent) => {
            const button = document.createElement('button');
            button.type = 'button';
            const primary = document.createElement('span');
            primary.textContent = agent.name || agent.id;
            button.appendChild(primary);
            if (agent.description) {
                const secondary = document.createElement('span');
                secondary.className = 'result-secondary';
                secondary.textContent = agent.description;
                button.appendChild(secondary);
            }
            button.addEventListener('mousedown', (event) => {
                event.preventDefault();
                selectResult(agent);
            });
            fragment.appendChild(button);
        });
        results.innerHTML = '';
        results.appendChild(fragment);
        results.classList.remove('d-none');
    };

    const performSearch = (query) => {
        if (!query) {
            closeResults();
            return;
        }

        if (activeController) {
            activeController.abort();
        }

        activeController = new AbortController();
        searchAgents(query, { signal: activeController.signal })
            .then(renderResults)
            .catch((error) => {
                if (isAbortError(error)) {
                    return;
                }
                console.error('Agent search failed:', error);
                results.innerHTML = '<div class="filter-search-empty text-danger">Search failed</div>';
                results.classList.remove('d-none');
            });
    };

    input.addEventListener('input', (event) => {
        const query = event.target.value.trim();
        if (hidden.value) {
            hidden.value = '';
            if (typeof config.onClear === 'function') {
                config.onClear();
            }
        }
        if (debounceTimer) {
            clearTimeout(debounceTimer);
        }
        if (!query) {
            closeResults();
            return;
        }
        debounceTimer = window.setTimeout(() => performSearch(query), 250);
    });

    input.addEventListener('focus', () => {
        const query = input.value.trim();
        if (query) {
            performSearch(query);
        }
    });

    input.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeResults();
            input.blur();
        }
    });

    input.addEventListener('blur', () => {
        window.setTimeout(closeResults, 150);
    });
}

function resetAgentAutocomplete(key) {
    const config = agentAutocompleteConfigs[key];
    if (!config) {
        return;
    }
    const input = document.getElementById(config.inputId);
    const hidden = document.getElementById(config.hiddenId);
    const results = document.getElementById(config.resultsId);
    if (input) {
        input.value = '';
    }
    if (hidden && hidden.value) {
        hidden.value = '';
        if (typeof config.onClear === 'function') {
            config.onClear();
        }
    } else if (hidden) {
        hidden.value = '';
    }
    if (results) {
        results.classList.add('d-none');
        results.innerHTML = '';
    }
}

async function hydrateFilterInputs() {
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.value = currentFilters.status || '';
    }

    if (currentFilters.agentId) {
        const hidden = document.getElementById('agentFilter');
        if (hidden) {
            hidden.value = currentFilters.agentId;
        }
        const agent = await ensureAgentLoaded(currentFilters.agentId);
        const input = document.getElementById('agentFilterInput');
        if (input) {
            input.value = agent?.name || currentFilters.agentId;
        }
    }
}

function setupEventListeners() {
    const refreshBtn = document.getElementById('refreshRegressionsBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => loadRegressions(currentPage));
    }

    const clearFiltersBtn = document.getElementById('clearFiltersBtn');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', () => {
            resetAgentAutocomplete('filter');
            const statusFilter = document.getElementById('statusFilter');
            if (statusFilter) {
                statusFilter.value = '';
            }
            currentFilters = { agentId: '', status: '' };
            currentPage = 1;
            loadRegressions(1);
        });
    }

    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.value = currentFilters.status || '';
        statusFilter.addEventListener('change', (event) => {
            currentFilters.status = event.target.value;
            currentPage = 1;
            loadRegressions(1);
        });
    }

    const startRegressionBtn = document.getElementById('confirmStartRegression');
    if (startRegressionBtn) {
        startRegressionBtn.addEventListener('click', startRegression);
    }

    const startModal = document.getElementById('startRegressionModal');
    if (startModal) {
        startModal.addEventListener('shown.bs.modal', () => {
            clearModalAlert('startRegressionAlert');
            const settingsInput = document.getElementById('regressionModelSettings');
            if (settingsInput && !settingsInput.value.trim()) {
                settingsInput.value = '{}';
            }
            const agentInput = document.getElementById('regressionAgentInput');
            if (agentInput) {
                agentInput.focus();
            }
        });

        startModal.addEventListener('hidden.bs.modal', () => {
            document.getElementById('startRegressionForm').reset();
            clearModalAlert('startRegressionAlert');
            resetAgentAutocomplete('modal');
            populateDefaultsForAgent(null);
        });
    }

    if (window.ModelHistoryManager) {
        window.ModelHistoryManager.initInput({
            inputId: 'regressionModelName',
            dropdownId: 'regressionModelNameDropdown',
        });
    }

    const prevBtn = document.getElementById('regressionsPrevPageBtn');
    if (prevBtn) {
        prevBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (currentPage > 1) {
                loadRegressions(currentPage - 1);
            }
        });
    }

    const nextBtn = document.getElementById('regressionsNextPageBtn');
    if (nextBtn) {
        nextBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (hasNextPage) {
                loadRegressions(currentPage + 1);
            }
        });
    }
}

function isAbortError(error) {
    return error && (error.name === 'AbortError' || error.code === 20);
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
}

async function searchAgents(query, options = {}) {
    if (!query) {
        return [];
    }
    const params = new URLSearchParams({ search: query, limit: '5' });
    try {
        const results = await fetchJson(`/v1/api/agents/?${params}`, options);
        results.forEach((agent) => {
            agentCache.set(agent.id, agent);
        });
        return results;
    } catch (error) {
        if (isAbortError(error)) {
            return [];
        }
        console.error('Error searching agents:', error);
        return [];
    }
}

async function ensureAgentLoaded(agentId) {
    if (!agentId) {
        return null;
    }
    if (agentCache.has(agentId)) {
        return agentCache.get(agentId);
    }
    if (pendingAgentRequests.has(agentId)) {
        return pendingAgentRequests.get(agentId);
    }

    const promise = (async () => {
        try {
            const agent = await fetchJson(`/v1/api/agents/${agentId}`);
            agentCache.set(agentId, agent);
            return agent;
        } catch (error) {
            console.error(`Failed to fetch agent ${agentId}:`, error);
            agentCache.set(agentId, null);
            return null;
        } finally {
            pendingAgentRequests.delete(agentId);
        }
    })();

    pendingAgentRequests.set(agentId, promise);
    return promise;
}

async function populateDefaultsForAgent(agentOrData) {
    const modelNameInput = document.getElementById('regressionModelName');
    const systemPromptInput = document.getElementById('regressionSystemPrompt');
    const modelSettingsInput = document.getElementById('regressionModelSettings');
    const hiddenAgentInput = document.getElementById('regressionAgentId');

    if (!modelNameInput || !systemPromptInput || !modelSettingsInput || !hiddenAgentInput) {
        return;
    }

    if (!agentOrData) {
        hiddenAgentInput.value = '';
        modelNameInput.value = '';
        systemPromptInput.value = '';
        if (!modelSettingsInput.value.trim()) {
            modelSettingsInput.value = '{}';
        }
        return;
    }

    let agentData = agentOrData;
    if (typeof agentData === 'string') {
        agentData = await ensureAgentLoaded(agentData);
    }

    if (!agentData) {
        hiddenAgentInput.value = '';
        return;
    }

    hiddenAgentInput.value = agentData.id;
    modelNameInput.value = agentData.default_model_name || '';
    systemPromptInput.value = agentData.default_system_prompt || '';
    const settingsValue = agentData.default_model_settings
        ? JSON.stringify(agentData.default_model_settings, null, 2)
        : '{}';
    modelSettingsInput.value = settingsValue;
}

function createRegressionsUrl(page) {
    const url = new URL('/v1/api/regression-tests/', window.location.origin);
    if (currentFilters.agentId) {
        url.searchParams.append('agent_id', currentFilters.agentId);
    }
    if (currentFilters.status) {
        url.searchParams.append('status', currentFilters.status);
    }
    url.searchParams.append('limit', FETCH_LIMIT.toString());
    url.searchParams.append('offset', ((page - 1) * PAGE_SIZE).toString());
    return url;
}

async function loadRegressions(page = currentPage) {
    currentPage = page;
    toggleLoading(true);
    if (refreshTimeout) {
        clearTimeout(refreshTimeout);
        refreshTimeout = null;
    }

    try {
        const url = createRegressionsUrl(page);

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const results = await response.json();
        hasNextPage = results.length > PAGE_SIZE;
        regressionTests = hasNextPage ? results.slice(0, PAGE_SIZE) : results;
        displayRegressionTests(regressionTests);
        updateRegressionsPagination();
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
        updateRegressionsPagination();
        return;
    }

    emptyState.classList.add('d-none');
    table.style.display = 'table';

    const sorted = [...regressions].sort((a, b) => {
        const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
        return timeB - timeA;
    });

    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        container.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((el) => {
            const instance = bootstrap.Tooltip.getInstance(el);
            if (instance) {
                instance.dispose();
            }
        });
    }

    container.innerHTML = sorted.map(buildRegressionRow).join('');
    applyTooltipContent(container);
    if (window.HoverTooltip) {
        window.HoverTooltip.attach(container);
    }
    initializeTooltips();
    updateRegressionsPagination();
}

function updateRegressionsPagination() {
    const pagination = document.getElementById('regressionsPagination');
    const status = document.getElementById('regressionsPaginationStatus');
    const pageLabel = document.getElementById('regressionsPaginationCurrentPage');
    const prevBtn = document.getElementById('regressionsPrevPage');
    const nextBtn = document.getElementById('regressionsNextPage');

    if (!pagination || !status || !pageLabel || !prevBtn || !nextBtn) {
        return;
    }

    if (regressionTests.length === 0) {
        pagination.classList.add('d-none');
        status.textContent = '';
        pageLabel.textContent = '';
        if (currentPage <= 1) {
            prevBtn.classList.add('disabled');
        } else {
            prevBtn.classList.remove('disabled');
        }
        if (!hasNextPage) {
            nextBtn.classList.add('disabled');
        } else {
            nextBtn.classList.remove('disabled');
        }
        return;
    }

    pagination.classList.remove('d-none');
    const start = (currentPage - 1) * PAGE_SIZE + 1;
    const end = start + regressionTests.length - 1;
    status.textContent = `Showing ${start}-${end}`;
    pageLabel.textContent = `Page ${currentPage}`;
    if (currentPage <= 1) {
        prevBtn.classList.add('disabled');
    } else {
        prevBtn.classList.remove('disabled');
    }
    if (!hasNextPage) {
        nextBtn.classList.add('disabled');
    } else {
        nextBtn.classList.remove('disabled');
    }
}

function buildRegressionRow(regression) {
    const statusBadge = buildStatusBadge(regression.status);
    const agentName = regression.agent ? regression.agent.name : 'Unknown agent';
    const agentId = regression.agent ? regression.agent.id : null;
    const agentPrimaryLine = agentId
        ? `<a href="/agents/${encodeURIComponent(agentId)}" class="text-decoration-none fw-semibold" target="_blank" rel="noopener noreferrer">${escapeHtml(agentName)}</a>`
        : `<span class="fw-semibold">${escapeHtml(agentName)}</span>`;
    
    // Model column with model_settings below
    const modelName = regression.model_name_override
        ? `<span class="badge bg-primary">${escapeHtml(regression.model_name_override)}</span>`
        : '<span class="text-muted">—</span>';
    const modelSettings = regression.model_settings_override
        ? `<div class="text-muted small mt-1">${escapeHtml(JSON.stringify(regression.model_settings_override))}</div>`
        : '<div class="text-muted small mt-1">No settings</div>';
    const modelColumn = `
        <div class="d-flex flex-column">
            ${modelName}
            ${modelSettings}
        </div>
    `;

    // Status column with results below
    const results = `
        <div class="d-flex flex-wrap gap-1 mt-1">
            <span class="badge bg-primary small">Total ${regression.total_count}</span>
            <span class="badge bg-success small">Passed ${regression.passed_count}</span>
            <span class="badge bg-danger small">Declined ${regression.declined_count}</span>
        </div>
    `;
    const statusColumn = `
        <div class="d-flex flex-column">
            ${statusBadge}
            ${results}
        </div>
    `;

    // System prompt column with hover tooltip
    const systemPrompt = regression.system_prompt_override || '';
    const hasSystemPrompt = systemPrompt.trim().length > 0;
    const systemPromptDisplay = hasSystemPrompt ? truncateText(systemPrompt, 90) : '—';
    const systemPromptClass = hasSystemPrompt ? 'log-preview' : 'log-preview placeholder';
    const systemPromptEncoded = encodeTooltipPayload(systemPrompt);
    const systemPromptFallback = encodeTooltipPayload('No system prompt override');
    const systemPromptColumn = `
        <span class="${systemPromptClass}" data-bs-toggle="tooltip" data-bs-placement="top" data-bs-custom-class="log-tooltip" data-bs-html="true"
              data-tooltip-content="${systemPromptEncoded}" data-tooltip-fallback="${systemPromptFallback}">
            ${escapeHtml(systemPromptDisplay)}
        </span>
    `;

    const created = formatDate(regression.created_at);

    return `
        <tr data-regression-id="${escapeHtml(regression.id)}">
            <td>
                <div class="d-flex flex-column">
                    ${agentPrimaryLine}
                </div>
            </td>
            <td>${statusColumn}</td>
            <td>${modelColumn}</td>
            <td>${systemPromptColumn}</td>
            <td>${created}</td>
            <td class="text-end">
                <div class="btn-group btn-group-sm" role="group">
                    <button type="button" class="btn btn-outline-primary" onclick="openRegressionDetail('${regression.id}')" title="View regression details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button type="button" class="btn btn-outline-secondary" onclick="openRegressionLogs('${regression.id}')" title="View related test logs">
                        <i class="fas fa-clipboard-list"></i>
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

async function startRegression() {
    const agentHidden = document.getElementById('regressionAgentId');
    const modelNameInput = document.getElementById('regressionModelName');
    const systemPromptInput = document.getElementById('regressionSystemPrompt');
    const modelSettingsInput = document.getElementById('regressionModelSettings');

    const agentId = agentHidden ? agentHidden.value : '';
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
        loadRegressions(1);
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
        const url = createRegressionsUrl(currentPage);
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const updatedResults = await response.json();
        hasNextPage = updatedResults.length > PAGE_SIZE;
        regressionTests = hasNextPage
            ? updatedResults.slice(0, PAGE_SIZE)
            : updatedResults;
        updateRegressionRows(regressionTests);
        updateRegressionsPagination();
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

    const sorted = [...regressions].sort((a, b) => {
        const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
        const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
        return timeB - timeA;
    });

    emptyState.classList.add('d-none');
    table.style.display = 'table';

    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        container.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((el) => {
            const instance = bootstrap.Tooltip.getInstance(el);
            if (instance) {
                instance.dispose();
            }
        });
    }

    const activeIds = new Set();
    const existingRowsMap = new Map();
    Array.from(container.querySelectorAll('tr[data-regression-id]')).forEach((row) => {
        const id = row.getAttribute('data-regression-id');
        if (id) {
            existingRowsMap.set(id, row);
        }
    });

    sorted.forEach((regression, index) => {
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

    applyTooltipContent(container);
    if (window.HoverTooltip) {
        window.HoverTooltip.attach(container);
    }
    initializeTooltips();
}

function openRegressionDetail(regressionId) {
    window.open(`/regression-tests/${regressionId}`, '_blank');
}

function openRegressionLogs(regressionId) {
    if (!regressionId) return;
    const url = `/test-logs?regressionTestId=${encodeURIComponent(regressionId)}`;
    const newWindow = window.open(url, '_blank');
    if (newWindow) {
        newWindow.opener = null;
    }
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

function initializeTooltips() {
    if (typeof bootstrap === 'undefined' || !bootstrap.Tooltip) {
        return;
    }
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]:not(.log-preview)')
    );
    tooltipTriggerList.forEach((tooltipTriggerEl) => {
        bootstrap.Tooltip.getOrCreateInstance(tooltipTriggerEl);
    });
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

window.openRegressionDetail = openRegressionDetail;
window.openRegressionLogs = openRegressionLogs;
