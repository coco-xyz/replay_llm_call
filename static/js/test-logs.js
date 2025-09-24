/**
 * Test Logs JavaScript - v2.0 (Fixed filter API paths)
 *
 * Handles test log viewing and filtering.
 */
const PAGE_SIZE = 20;
const FETCH_LIMIT = PAGE_SIZE + 1;

let currentLogs = [];
let currentPage = 1;
let hasNextPage = false;
let currentFilters = { status: '', testCaseId: '', agentId: '', regressionTestId: '' };
let currentLogId = null;

const entityCaches = {
    testCases: new Map(),
    agents: new Map(),
    regressions: new Map(),
};

const pendingEntityRequests = {
    testCases: new Map(),
    agents: new Map(),
    regressions: new Map(),
};

// Initialize page
document.addEventListener('DOMContentLoaded', () => {
    initializeTestLogsPage().catch((error) => {
        console.error('Failed to initialize test logs page:', error);
        showAlert('Failed to initialize test logs page: ' + error.message, 'danger');
    });
});

async function initializeTestLogsPage() {
    const urlParams = new URLSearchParams(window.location.search);

    // Preload filter state from URL so the first fetch respects it
    currentFilters.status = urlParams.get('status') || '';
    currentFilters.testCaseId = urlParams.get('testCaseId') || '';
    currentFilters.agentId = urlParams.get('agentId') || '';
    currentFilters.regressionTestId = urlParams.get('regressionTestId') || '';
    currentLogId = urlParams.get('logId');
    currentPage = 1;

    setupEventListeners();
    setupAutocompleteFilters();

    await hydrateFilterInputs();

    await loadTestLogs();

    if (currentLogId) {
        viewLogInNewPage(currentLogId);
    }
}

function setupEventListeners() {
    // Refresh button
    const refreshTestLogsBtn = document.getElementById('refreshTestLogsBtn');
    if (refreshTestLogsBtn) {
        refreshTestLogsBtn.addEventListener('click', () => {
            currentPage = 1;
            loadTestLogs();
        });
    }

    // Clear filters button
    const clearFiltersBtn = document.getElementById('clearFiltersBtn');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', () => {
            resetAllFilters();
        });
    }

    // Auto-apply filters on change
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', (event) => {
            currentFilters.status = event.target.value;
            currentPage = 1;
            loadTestLogs();
        });
    }

    const prevBtn = document.getElementById('testLogsPrevPageBtn');
    if (prevBtn) {
        prevBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (currentPage > 1) {
                currentPage -= 1;
                loadTestLogs();
            }
        });
    }

    const nextBtn = document.getElementById('testLogsNextPageBtn');
    if (nextBtn) {
        nextBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (hasNextPage) {
                currentPage += 1;
                loadTestLogs();
            }
        });
    }
}

function resetAllFilters() {
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.value = '';
    }
    resetAutocompleteFilter('testCase');
    resetAutocompleteFilter('agent');
    resetAutocompleteFilter('regression');
    currentFilters = { status: '', testCaseId: '', agentId: '', regressionTestId: '' };
    currentPage = 1;
    loadTestLogs();
}

function setupAutocompleteFilters() {
    Object.entries(AUTOCOMPLETE_FILTERS).forEach(([key, config]) => {
        setupAutocompleteFilter(key, config);
    });
}

async function hydrateFilterInputs() {
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.value = currentFilters.status || '';
    }

    const tasks = [];

    if (currentFilters.testCaseId) {
        document.getElementById('testCaseFilter').value = currentFilters.testCaseId;
        tasks.push(
            ensureTestCaseLoaded(currentFilters.testCaseId).then((data) => {
                const input = document.getElementById('testCaseFilterInput');
                if (input) {
                    input.value = data?.name || currentFilters.testCaseId;
                }
            })
        );
    }

    if (currentFilters.agentId) {
        document.getElementById('agentFilter').value = currentFilters.agentId;
        tasks.push(
            ensureAgentLoaded(currentFilters.agentId).then((data) => {
                const input = document.getElementById('agentFilterInput');
                if (input) {
                    input.value = data?.name || currentFilters.agentId;
                }
            })
        );
    }

    if (currentFilters.regressionTestId) {
        document.getElementById('regressionFilter').value = currentFilters.regressionTestId;
        tasks.push(
            ensureRegressionLoaded(currentFilters.regressionTestId).then((data) => {
                const input = document.getElementById('regressionFilterInput');
                if (input) {
                    const agentName = data?.agent?.name || 'Unknown agent';
                    const timestamp = formatRegressionTimestamp(data?.created_at);
                    input.value = `${agentName} · ${timestamp}`;
                }
            })
        );
    }

    if (tasks.length > 0) {
        await Promise.allSettled(tasks);
    }
}

const AUTOCOMPLETE_FILTERS = {
    testCase: {
        inputId: 'testCaseFilterInput',
        hiddenId: 'testCaseFilter',
        resultsId: 'testCaseFilterResults',
        filterKey: 'testCaseId',
        searchFn: searchTestCases,
        mapResult: (item) => ({
            value: item.id,
            display: item.name,
            secondary: item.id,
        }),
    },
    agent: {
        inputId: 'agentFilterInput',
        hiddenId: 'agentFilter',
        resultsId: 'agentFilterResults',
        filterKey: 'agentId',
        searchFn: searchAgents,
        mapResult: (item) => ({
            value: item.id,
            display: item.name,
            secondary: item.description ? truncateText(item.description, 60) : item.id,
        }),
    },
    regression: {
        inputId: 'regressionFilterInput',
        hiddenId: 'regressionFilter',
        resultsId: 'regressionFilterResults',
        filterKey: 'regressionTestId',
        searchFn: searchRegressions,
        mapResult: (item) => {
            const agentName = item.agent?.name || 'Unknown agent';
            const timestamp = formatRegressionTimestamp(item.created_at);
            return {
                value: item.id,
                display: `${agentName} · ${timestamp}`,
                secondary: item.id,
            };
        },
    },
};

function setupAutocompleteFilter(key, config) {
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

    const performSearch = (query) => {
        if (!query) {
            closeResults();
            return;
        }
        if (activeController) {
            activeController.abort();
        }
        activeController = new AbortController();
        config
            .searchFn(query, { signal: activeController.signal })
            .then((items) => {
                if (!items || items.length === 0) {
                    results.innerHTML = '<div class="filter-search-empty">No matches</div>';
                    results.classList.remove('d-none');
                    return;
                }
                results.innerHTML = '';
                const fragment = document.createDocumentFragment();
                items.forEach((item) => {
                    const mapped = config.mapResult(item);
                    const button = document.createElement('button');
                    button.type = 'button';
                    const primary = document.createElement('span');
                    primary.textContent = mapped.display || mapped.value;
                    button.appendChild(primary);
                    if (mapped.secondary) {
                        const secondary = document.createElement('span');
                        secondary.className = 'result-secondary';
                        secondary.textContent = mapped.secondary;
                        button.appendChild(secondary);
                    }
                    button.addEventListener('mousedown', (event) => {
                        event.preventDefault();
                        selectResult(mapped);
                    });
                    fragment.appendChild(button);
                });
                results.appendChild(fragment);
                results.classList.remove('d-none');
            })
            .catch((error) => {
                if (error.name === 'AbortError') {
                    return;
                }
                console.error('Search failed:', error);
                results.innerHTML = '<div class="filter-search-empty text-danger">Search failed</div>';
                results.classList.remove('d-none');
            });
    };

    const selectResult = (mapped) => {
        hidden.value = mapped.value;
        input.value = mapped.display || mapped.value;
        currentFilters[config.filterKey] = mapped.value;
        currentPage = 1;
        closeResults();
        loadTestLogs();
    };

    const handleInputChange = (event) => {
        const query = event.target.value.trim();
        if (hidden.value) {
            hidden.value = '';
        }
        if (currentFilters[config.filterKey]) {
            currentFilters[config.filterKey] = '';
            currentPage = 1;
            loadTestLogs();
        }
        if (debounceTimer) {
            clearTimeout(debounceTimer);
        }
        if (!query) {
            closeResults();
            return;
        }
        debounceTimer = window.setTimeout(() => performSearch(query), 250);
    };

    input.addEventListener('input', handleInputChange);
    input.addEventListener('focus', (event) => {
        const query = event.target.value.trim();
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

function resetAutocompleteFilter(key) {
    const config = AUTOCOMPLETE_FILTERS[key];
    if (!config) {
        return;
    }
    const input = document.getElementById(config.inputId);
    const hidden = document.getElementById(config.hiddenId);
    const results = document.getElementById(config.resultsId);
    if (input) {
        input.value = '';
    }
    if (hidden) {
        hidden.value = '';
    }
    if (results) {
        results.classList.add('d-none');
        results.innerHTML = '';
    }
}

async function loadTestLogs() {
    showLoading(true);
    try {
        const params = new URLSearchParams({
            limit: FETCH_LIMIT,
            offset: (currentPage - 1) * PAGE_SIZE
        });

        if (currentFilters.status) {
            params.append('status', currentFilters.status);
        }
        if (currentFilters.testCaseId) {
            params.append('test_case_id', currentFilters.testCaseId);
        }
        if (currentFilters.agentId) {
            params.append('agent_id', currentFilters.agentId);
        }
        if (currentFilters.regressionTestId) {
            params.append('regression_test_id', currentFilters.regressionTestId);
        }

        const response = await fetch(`/v1/api/test-logs/filter/combined?${params}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const logs = await response.json();
        hasNextPage = logs.length > PAGE_SIZE;
        currentLogs = hasNextPage ? logs.slice(0, PAGE_SIZE) : logs;

        await displayTestLogs(currentLogs);

    } catch (error) {
        console.error('Error loading test logs:', error);
        showAlert('Error loading test logs: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

function formatRegressionTimestamp(createdAt) {
    if (!createdAt) {
        return 'Unknown';
    }
    const date = new Date(createdAt);
    if (Number.isNaN(date.getTime())) {
        return 'Unknown';
    }

    const pad = (value) => String(value).padStart(2, '0');
    const yyyy = date.getFullYear();
    const MM = pad(date.getMonth() + 1);
    const dd = pad(date.getDate());
    const hh = pad(date.getHours());
    const mm = pad(date.getMinutes());
    const ss = pad(date.getSeconds());

    return `${yyyy}${MM}${dd}${hh}${mm}${ss}`;
}

function getCachedTestCase(testCaseId) {
    if (!testCaseId) {
        return null;
    }
    return entityCaches.testCases.get(testCaseId) || null;
}

function getCachedAgent(agentId) {
    if (!agentId) {
        return null;
    }
    return entityCaches.agents.get(agentId) || null;
}

function getCachedRegression(regressionId) {
    if (!regressionId) {
        return null;
    }
    return entityCaches.regressions.get(regressionId) || null;
}

async function ensureTestCaseLoaded(testCaseId) {
    if (!testCaseId) {
        return null;
    }
    return ensureEntityLoaded('testCases', testCaseId, () =>
        fetchJson(`/v1/api/test-cases/${testCaseId}`)
    );
}

async function ensureAgentLoaded(agentId) {
    if (!agentId) {
        return null;
    }
    return ensureEntityLoaded('agents', agentId, () =>
        fetchJson(`/v1/api/agents/${agentId}`)
    );
}

async function ensureRegressionLoaded(regressionId) {
    if (!regressionId) {
        return null;
    }
    return ensureEntityLoaded('regressions', regressionId, () =>
        fetchJson(`/v1/api/regression-tests/${regressionId}`)
    );
}

function ensureEntityLoaded(cacheKey, id, fetcher) {
    const cache = entityCaches[cacheKey];
    const pendingMap = pendingEntityRequests[cacheKey];
    if (cache.has(id)) {
        return Promise.resolve(cache.get(id));
    }
    if (pendingMap.has(id)) {
        return pendingMap.get(id);
    }
    const promise = (async () => {
        try {
            const data = await fetcher();
            cache.set(id, data);
            return data;
        } catch (error) {
            console.error(`Failed to load ${cacheKey.slice(0, -1)} ${id}:`, error);
            cache.set(id, null);
            return null;
        } finally {
            pendingMap.delete(id);
        }
    })();
    pendingMap.set(id, promise);
    return promise;
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
}

function isAbortError(error) {
    return error && (error.name === 'AbortError' || error.code === 20);
}

async function searchTestCases(query, options = {}) {
    if (!query) {
        return [];
    }
    const params = new URLSearchParams({ q: query, limit: '5' });
    try {
        const results = await fetchJson(`/v1/api/test-cases/search?${params}`, options);
        results.forEach((item) => {
            entityCaches.testCases.set(item.id, item);
        });
        return results;
    } catch (error) {
        if (isAbortError(error)) {
            return [];
        }
        console.error('Error searching test cases:', error);
        return [];
    }
}

async function searchAgents(query, options = {}) {
    if (!query) {
        return [];
    }
    const params = new URLSearchParams({ limit: '5', search: query });
    try {
        const results = await fetchJson(`/v1/api/agents/?${params}`, options);
        results.forEach((item) => {
            entityCaches.agents.set(item.id, item);
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

async function searchRegressions(query, options = {}) {
    if (!query) {
        return [];
    }
    const params = new URLSearchParams({ limit: '5', search: query });
    try {
        const results = await fetchJson(`/v1/api/regression-tests/?${params}`, options);
        results.forEach((item) => {
            entityCaches.regressions.set(item.id, item);
        });
        return results;
    } catch (error) {
        if (isAbortError(error)) {
            return [];
        }
        console.error('Error searching regressions:', error);
        return [];
    }
}

function formatResponseTime(value) {
    if (value === null || value === undefined) {
        return '—';
    }
    return `${value}ms`;
}

function resolveEvaluationDisplay(target) {
    const status = target && typeof target.is_passed !== 'undefined' ? target.is_passed : null;
    if (status === true) {
        return { label: 'Passed', badgeClass: 'bg-success', icon: 'check' };
    }
    if (status === false) {
        return { label: 'Declined', badgeClass: 'bg-danger', icon: 'times' };
    }
    return { label: 'Unknown', badgeClass: 'bg-secondary', icon: 'question' };
}

function buildEvaluationTooltip(log) {
    if (!log) {
        return 'Evaluation details unavailable.';
    }

    const lines = [];
    const feedback = (log.evaluation_feedback || '').trim();
    if (feedback) {
        lines.push(feedback);
    }

    if (log.response_expectation_snapshot) {
        lines.push(`Expectation snapshot:\n${log.response_expectation_snapshot.trim()}`);
    }

    if (log.evaluation_model_name) {
        lines.push(`Model: ${log.evaluation_model_name}`);
    }

    const metadata = log.evaluation_metadata || {};
    if (Array.isArray(metadata.missing_criteria) && metadata.missing_criteria.length > 0) {
        lines.push(`Missing criteria:\n- ${metadata.missing_criteria.join('\n- ')}`);
    }
    if (Array.isArray(metadata.satisfied_criteria) && metadata.satisfied_criteria.length > 0) {
        lines.push(`Satisfied criteria:\n- ${metadata.satisfied_criteria.join('\n- ')}`);
    }

    if (lines.length === 0) {
        const display = resolveEvaluationDisplay(log);
        if (display.label === 'Passed') {
            lines.push('Marked as passed.');
        } else if (display.label === 'Declined') {
            lines.push('Marked as declined.');
        } else {
            lines.push('Evaluation skipped or not applicable.');
        }
    }

    return lines.join('\n\n');
}

function formatPassBadge(log) {
    const display = resolveEvaluationDisplay(log);
    const tooltipContent = encodeTooltipPayload(buildEvaluationTooltip(log));
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

    return `<div class="text-break" style="white-space: pre-wrap;">${escapeHtml(trimmed)}</div>`;
}

function formatExpectationSnapshot(snapshot) {
    if (!snapshot) {
        return '<span class="text-muted">—</span>';
    }

    const trimmed = snapshot.trim();
    if (!trimmed) {
        return '<span class="text-muted">—</span>';
    }

    return `<div class="text-break" style="white-space: pre-wrap;">${escapeHtml(trimmed)}</div>`;
}

function formatRegressionLabel(regressionId) {
    if (!regressionId) {
        return '<span class="text-muted">—</span>';
    }

    const regression = getCachedRegression(regressionId);
    const encodedId = encodeURIComponent(regressionId);

    if (!regression) {
        return `<a href="/regression-tests/${encodedId}" target="_blank">${escapeHtml(regressionId)}</a>`;
    }

    const timestamp = formatRegressionTimestamp(regression.created_at);
    const display = timestamp || regressionId;
    return `<a href="/regression-tests/${encodedId}" target="_blank">${escapeHtml(display)}</a>`;
}

function formatAgentLabel(agentId) {
    if (!agentId) {
        return '<span class="text-muted">—</span>';
    }
    const agent = getCachedAgent(agentId);
    if (agent) {
        return `<span class="badge bg-primary">${escapeHtml(agent.name)}</span> <small class="text-muted ms-2">${escapeHtml(agent.id)}</small>`;
    }
    return escapeHtml(agentId);
}

async function displayTestLogs(logs) {
    const container = document.getElementById('testLogsList');
    const emptyState = document.getElementById('emptyState');
    const table = document.getElementById('testLogsTable');

    if (logs.length === 0) {
        container.innerHTML = '';
        table.style.display = 'none';
        emptyState.classList.remove('d-none');
        updatePagination();
        return;
    }

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

    const uniqueTestCaseIds = [...new Set(logs.map((log) => log.test_case_id).filter(Boolean))];
    const uniqueAgentIds = [...new Set(logs.map((log) => log.agent_id).filter(Boolean))];
    const uniqueRegressionIds = [
        ...new Set(logs.map((log) => log.regression_test_id).filter(Boolean)),
    ];

    await Promise.all([
        Promise.all(uniqueTestCaseIds.map((id) => ensureTestCaseLoaded(id))),
        Promise.all(uniqueAgentIds.map((id) => ensureAgentLoaded(id))),
        Promise.all(uniqueRegressionIds.map((id) => ensureRegressionLoaded(id))),
    ]);

    const html = logs.map((log) => {
        const testCase = getCachedTestCase(log.test_case_id);
        const testCaseName = testCase ? testCase.name : 'Unknown Test Case';
        const agent = getCachedAgent(log.agent_id);
        const agentName = agent ? agent.name : 'Unknown agent';
        const regressionLabel = formatRegressionLabel(log.regression_test_id);
        const responseTime = formatResponseTime(log.response_time_ms);
        const rawUserMessage = log.user_message || '';
        const hasUserMessage = rawUserMessage.trim().length > 0;
        const userMessageClass = hasUserMessage ? 'log-preview' : 'log-preview placeholder';
        const userMessageContent = hasUserMessage ? truncateText(rawUserMessage, 160) : '—';
        const userMessageEncoded = encodeTooltipPayload(rawUserMessage);
        const userMessageFallback = encodeTooltipPayload('No user message recorded');
        const rawLlmResponse = log.llm_response || '';
        const hasLlmResponse = rawLlmResponse.trim().length > 0;
        const llmResponseClass = hasLlmResponse ? 'log-preview' : 'log-preview placeholder';
        const llmResponseContent = hasLlmResponse ? truncateText(rawLlmResponse, 160) : '—';
        const llmResponseEncoded = encodeTooltipPayload(rawLlmResponse);
        const llmResponseFallback = encodeTooltipPayload('No LLM response captured');
        const passBadge = formatPassBadge(log);

        return `
        <tr>
            <td>
                <div class="log-summary">
                    <div>
                        ${testCase ? `<a href="/test-cases/${escapeHtml(log.test_case_id)}" class="text-decoration-none" target="_blank"><strong>${escapeHtml(testCaseName)}</strong></a>` : `<span class="text-muted">${escapeHtml(testCaseName)}</span>`}
                    </div>
                    <div class="meta-line">
                        ${agent ? `<a href="/agents/${escapeHtml(log.agent_id)}" class="badge bg-primary text-decoration-none" target="_blank">${escapeHtml(agentName)}</a>` : `<span class="text-muted">${escapeHtml(agentName)}</span>`}
                    </div>
                    <div class="meta-line">
                        ${regressionLabel}
                    </div>
                </div>
            </td>
            <td>
                <span class="badge bg-secondary">${escapeHtml(log.model_name)}</span>
            </td>
            <td>
                <div class="status-meta">
                    <span class="badge ${log.status === 'success' ? 'bg-success' : 'bg-danger'}">
                        <i class="fas fa-${log.status === 'success' ? 'check-circle' : 'times-circle'} me-1"></i>
                        ${log.status.toUpperCase()}
                    </span>
                    <span class="response-time">
                        <i class="fas fa-stopwatch me-1"></i>${responseTime}
                    </span>
                </div>
                ${log.error_message ? `<div class="text-danger small mt-1">${truncateText(log.error_message, 80)}</div>` : ''}
            </td>
            <td>
                <span class="${userMessageClass}" data-bs-toggle="tooltip" data-bs-placement="top" data-bs-custom-class="log-tooltip" data-bs-html="true"
                      data-tooltip-content="${userMessageEncoded}" data-tooltip-fallback="${userMessageFallback}">
                    ${userMessageContent}
                </span>
            </td>
            <td>
                <span class="${llmResponseClass}" data-bs-toggle="tooltip" data-bs-placement="top" data-bs-custom-class="log-tooltip" data-bs-html="true"
                      data-tooltip-content="${llmResponseEncoded}" data-tooltip-fallback="${llmResponseFallback}">
                    ${llmResponseContent}
                </span>
            </td>
            <td>
                <div class=\"d-flex flex-column align-items-start gap-1\">${passBadge}</div>
            </td>
            <td>
                <small class="text-muted">${formatDate(log.created_at)}</small>
            </td>
            <td>
                <div class="btn-group" role="group">
                    <button type="button" class="btn btn-sm btn-outline-primary" onclick="viewLogInNewPage('${log.id}')" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-secondary" onclick="reExecuteLog('${log.id}')" title="Re-execute">
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
    applyTooltipContent(container);
    if (window.HoverTooltip) {
        window.HoverTooltip.attach(container);
    }
    initializeTooltips();
    updatePagination();
}

// Function to open log in new page
function viewLogInNewPage(logId) {
    window.open(`/test-logs/${logId}`, '_blank');
}

// Keep the original viewLog function for backward compatibility (if needed)
async function viewLog(logId) {
    try {
        const response = await fetch(`/v1/api/test-logs/${logId}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status} `);

        const log = await response.json();
        currentLogId = logId;

        await Promise.all([
            ensureTestCaseLoaded(log.test_case_id),
            ensureAgentLoaded(log.agent_id),
            ensureRegressionLoaded(log.regression_test_id),
        ]);

        const relatedTestCase = getCachedTestCase(log.test_case_id);

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
                        <tr><td><strong>Agent:</strong></td><td>${formatAgentLabel(log.agent_id)}</td></tr>
                        <tr><td><strong>Regression:</strong></td><td>${formatRegressionLabel(log.regression_test_id)}</td></tr>
                        <tr><td><strong>Response Time:</strong></td><td>${formatResponseTime(log.response_time_ms)}</td></tr>
                        <tr><td><strong>Evaluation Result:</strong></td><td>${formatPassBadge(log)}</td></tr>
                        <tr><td><strong>Evaluation Feedback:</strong></td><td>${formatEvaluationFeedback(log.evaluation_feedback)}</td></tr>
                        <tr><td><strong>Evaluation Model:</strong></td><td>${escapeHtml(log.evaluation_model_name || '—')}</td></tr>
                        <tr><td><strong>Expectation Snapshot:</strong></td><td>${formatExpectationSnapshot(log.response_expectation_snapshot)}</td></tr>
                        <tr><td><strong>Test Case:</strong></td><td>
                            <div>
                                <a href="/test-cases/${log.test_case_id}" class="text-decoration-none" target="_blank">
                                    ${escapeHtml(relatedTestCase?.name || log.test_case_id)}
                                    <i class="fas fa-external-link-alt ms-1" style="font-size: 0.8em;"></i>
                                </a>
                            </div>
                            ${relatedTestCase?.description ? `
                                <div class="text-muted mt-1" style="font-size: 0.9em;">
                                    <span title="${escapeHtml(relatedTestCase.description)}" style="cursor: help;">
                                        ${truncateText(relatedTestCase.description, 100)}
                                    </span>
                                </div>
                            ` : ''}
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

        const logDetailsContainer = document.getElementById('logDetails');
        logDetailsContainer.innerHTML = detailsHtml;
        applyTooltipContent(logDetailsContainer);
        if (window.HoverTooltip) {
            window.HoverTooltip.attach(logDetailsContainer);
        }
        initializeTooltips();

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('viewLogModal'));
        modal.show();

    } catch (error) {
        console.error('Error loading log details:', error);
        showAlert('Error loading log details: ' + error.message, 'danger');
    }
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
    window.location.href = `/test-execution?testCaseId=${testCaseId}`;
}

function reExecuteLog(logId) {
    const url = `/test-execution?logId=${encodeURIComponent(logId)}`;
    const newWindow = window.open(url, '_blank', 'noopener,noreferrer');
    if (newWindow) {
        newWindow.opener = null;
    }
}

function reExecuteFromLog() {
    if (currentLogId) {
        reExecuteLog(currentLogId);
    }
}

function updatePagination() {
    const pagination = document.getElementById('testLogsPagination');
    const status = document.getElementById('testLogsPaginationStatus');
    const pageLabel = document.getElementById('testLogsPaginationCurrentPage');
    const prevBtn = document.getElementById('testLogsPrevPage');
    const nextBtn = document.getElementById('testLogsNextPage');

    if (!pagination || !status || !pageLabel || !prevBtn || !nextBtn) {
        return;
    }

    if (currentLogs.length === 0) {
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
    const end = start + currentLogs.length - 1;
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

function truncateText(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return escapeHtml(text);
    return escapeHtml(text.substring(0, maxLength)) + '...';
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

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
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
