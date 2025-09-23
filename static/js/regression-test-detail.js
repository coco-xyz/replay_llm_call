/**
 * Regression Test Detail JavaScript
 *
 * Displays regression metadata and associated logs.
 */

const LOGS_PAGE_SIZE = 10;
let logsPage = 1;
let currentLogs = [];
const testCaseCache = new Map();
const pendingTestCaseRequests = new Map();

window.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadRegressionDetail();
    loadRegressionLogs();
});

function setupEventListeners() {
    const refreshBtn = document.getElementById('refreshDetailBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadRegressionDetail();
            logsPage = 1;
            loadRegressionLogs();
        });
    }

    const refreshLogsBtn = document.getElementById('refreshLogsBtn');
    if (refreshLogsBtn) {
        refreshLogsBtn.addEventListener('click', () => {
            logsPage = 1;
            loadRegressionLogs();
        });
    }

    const prevPageBtn = document.getElementById('logsPrevPageBtn');
    if (prevPageBtn) {
        prevPageBtn.addEventListener('click', (event) => {
            event.preventDefault();
            loadPreviousLogsPage();
        });
    }

    const nextPageBtn = document.getElementById('logsNextPageBtn');
    if (nextPageBtn) {
        nextPageBtn.addEventListener('click', (event) => {
            event.preventDefault();
            loadNextLogsPage();
        });
    }
}

async function loadRegressionDetail() {
    toggleDetailLoading(true);
    try {
        const response = await fetch(`/v1/api/regression-tests/${regressionId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const regression = await response.json();
        displayRegressionDetail(regression);
    } catch (error) {
        console.error('Error loading regression test:', error);
        showDetailError('Failed to load regression test details: ' + error.message);
    } finally {
        toggleDetailLoading(false);
    }
}

function displayRegressionDetail(regression) {
    const content = document.getElementById('regressionContent');
    const errorMessage = document.getElementById('errorMessage');
    if (!content) return;

    errorMessage.classList.add('d-none');
    content.classList.remove('d-none');

    setText('regressionId', regression.id);
    setText('agentName', regression.agent ? regression.agent.name : 'Unknown agent');
    setHtml('statusBadge', buildStatusBadge(regression.status));
    setHtml('startedAt', formatDate(regression.started_at));
    setHtml('completedAt', formatDate(regression.completed_at));
    setHtml('totalCount', regression.total_count);
    setHtml('successCount', regression.success_count);
    setHtml('failedCount', regression.failed_count);

    setText('overrideModel', regression.model_name_override);
    setPre('overridePrompt', regression.system_prompt_override || '');
    const settingsPretty = JSON.stringify(regression.model_settings_override || {}, null, 2);
    setPre('overrideSettings', settingsPretty);

    const openLogsBtn = document.getElementById('openLogsBtn');
    if (openLogsBtn) {
        openLogsBtn.href = `/test-logs?regressionTestId=${encodeURIComponent(regression.id)}`;
    }

    const errorSection = document.getElementById('errorSection');
    const errorMessageText = document.getElementById('errorMessageText');
    if (regression.error_message) {
        errorSection.classList.remove('d-none');
        if (errorMessageText) {
            errorMessageText.textContent = regression.error_message;
        }
    } else {
        errorSection.classList.add('d-none');
    }
}

function toggleDetailLoading(show) {
    const spinner = document.getElementById('loadingSpinner');
    const content = document.getElementById('regressionContent');
    if (!spinner || !content) return;

    if (show) {
        spinner.classList.remove('d-none');
        content.classList.add('d-none');
    } else {
        spinner.classList.add('d-none');
    }
}

function showDetailError(message) {
    const errorBox = document.getElementById('errorMessage');
    const errorText = document.getElementById('errorText');
    if (!errorBox || !errorText) return;

    errorText.textContent = message;
    errorBox.classList.remove('d-none');
}

function setText(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value || '';
    }
}

function setHtml(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = value;
    }
}

function setPre(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    }
}
function buildStatusBadge(status) {
    const normalized = (status || '').toLowerCase();
    const label = formatStatus(status);
    let icon = 'fa-circle';
    let pillClass = 'status-secondary';

    switch (normalized) {
        case 'pending':
            pillClass = 'status-warning';
            icon = 'fa-clock';
            break;
        case 'running':
            pillClass = 'status-warning';
            icon = 'fa-spinner fa-spin';
            break;
        case 'completed':
            pillClass = 'status-success';
            icon = 'fa-check';
            break;
        case 'failed':
            pillClass = 'status-danger';
            icon = 'fa-triangle-exclamation';
            break;
        default:
            pillClass = 'status-secondary';
            icon = 'fa-circle';
            break;
    }

    return `
        <span class="status-pill ${pillClass}">
            <i class="fas ${icon}"></i>
            <span>${label}</span>
        </span>
    `;
}

function formatStatus(status) {
    if (!status) {
        return 'Unknown';
    }
    const normalized = status.toString().toLowerCase();
    return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function escapeHtml(text) {
    if (text === null || text === undefined) {
        return '';
    }
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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

async function loadRegressionLogs() {
    toggleLogsLoading(true);
    try {
        const params = new URLSearchParams({
            limit: LOGS_PAGE_SIZE,
            offset: (logsPage - 1) * LOGS_PAGE_SIZE,
            regression_test_id: regressionId,
        });

        const response = await fetch(`/v1/api/test-logs/filter/combined?${params}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const logs = await response.json();
        if (logsPage > 1 && logs.length === 0) {
            logsPage = Math.max(1, logsPage - 1);
            await loadRegressionLogs();
            return;
        }

        currentLogs = logs;
        await renderRegressionLogs(currentLogs);
        updateLogsPagination();
    } catch (error) {
        console.error('Error loading regression test logs:', error);
        showAlert('Failed to load associated test logs: ' + error.message, 'danger');
    } finally {
        toggleLogsLoading(false);
    }
}

async function renderRegressionLogs(logs) {
    const tableWrapper = document.getElementById('logsTableWrapper');
    const tableBody = document.getElementById('regressionLogsTable');
    const emptyState = document.getElementById('logsEmptyState');
    if (!tableWrapper || !tableBody || !emptyState) {
        return;
    }

    if (!logs || logs.length === 0) {
        tableBody.innerHTML = '';
        tableWrapper.classList.add('d-none');
        emptyState.classList.remove('d-none');
        return;
    }

    emptyState.classList.add('d-none');
    tableWrapper.classList.remove('d-none');

    const uniqueTestCaseIds = Array.from(
        new Set(logs.map((log) => log.test_case_id).filter((id) => Boolean(id))),
    );
    if (uniqueTestCaseIds.length > 0) {
        await Promise.all(uniqueTestCaseIds.map((id) => loadTestCaseDetails(id)));
    }

    const rows = logs
        .map((log) => {
            const statusMeta = formatLogStatusMeta(log.status);
            const responseTime = formatResponseTime(log.response_time_ms);
            const errorMessage = log.error_message
                ? `<div class="text-danger small mt-1">${truncateText(log.error_message, 100)}</div>`
                : '';

            const testCase = log.test_case_id ? testCaseCache.get(log.test_case_id) : null;
            const testCaseName = testCase?.name || log.test_case_id || 'Unknown Test Case';
            const testCaseDescription = testCase?.description;
            const testCaseLink = log.test_case_id
                ? `/test-cases/${encodeURIComponent(log.test_case_id)}`
                : null;
            const testCaseNameMarkup = testCaseLink
                ? `<a href="${testCaseLink}" class="text-decoration-none" target="_blank"><strong>${escapeHtml(testCaseName)}</strong></a>`
                : `<strong>${escapeHtml(testCaseName)}</strong>`;
            const descriptionMarkup = testCaseDescription
                ? `<div class="text-muted small mt-1" title="${escapeHtml(testCaseDescription)}">${truncateText(testCaseDescription, 160)}</div>`
                : '<div class="text-muted small mt-1">—</div>';

            const rawUserMessage = log.user_message || '';
            const hasUserMessage = rawUserMessage.trim().length > 0;
            const userMessageClass = hasUserMessage
                ? 'log-preview'
                : 'log-preview placeholder';
            const userMessageContent = hasUserMessage
                ? truncateText(rawUserMessage, 140)
                : '—';
            const userMessageEncoded = encodeTooltipPayload(rawUserMessage);
            const userMessageFallback = encodeTooltipPayload('No user message recorded');

            const rawLlmResponse = log.llm_response || '';
            const hasLlmResponse = rawLlmResponse.trim().length > 0;
            const llmResponseClass = hasLlmResponse
                ? 'log-preview'
                : 'log-preview placeholder';
            const llmResponseContent = hasLlmResponse
                ? truncateText(rawLlmResponse, 140)
                : '—';
            const llmResponseEncoded = encodeTooltipPayload(rawLlmResponse);
            const llmResponseFallback = encodeTooltipPayload('No LLM response captured');

            const passBadge = formatPassBadge(log);

            const executedAt = formatDate(log.created_at);

            return `
                <tr>
                    <td>
                        ${testCaseNameMarkup}
                        ${descriptionMarkup}
                    </td>
                    <td>
                        <span class="${userMessageClass}" data-bs-toggle="tooltip" data-bs-placement="top" data-bs-custom-class="log-tooltip" data-bs-html="true" data-tooltip-content="${userMessageEncoded}" data-tooltip-fallback="${userMessageFallback}">
                            ${userMessageContent}
                        </span>
                    </td>
                    <td>
                        <span class="${llmResponseClass}" data-bs-toggle="tooltip" data-bs-placement="top" data-bs-custom-class="log-tooltip" data-bs-html="true" data-tooltip-content="${llmResponseEncoded}" data-tooltip-fallback="${llmResponseFallback}">
                            ${llmResponseContent}
                        </span>
                    </td>
                    <td>
                        <div class="d-flex flex-column align-items-start gap-1">
                            ${passBadge}
                        </div>
                    </td>
                    <td>
                        <div class="status-meta mb-1">
                            <span class="badge ${statusMeta.badgeClass}">
                                <i class="fas ${statusMeta.icon} me-1"></i>${statusMeta.label}
                            </span>
                        </div>
                        <div class="text-muted small">${executedAt}</div>
                        <div class="text-muted small">
                            <i class="fas fa-stopwatch me-1"></i>${responseTime}
                        </div>
                        ${errorMessage}
                    </td>
                    <td class="text-end">
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
        })
        .join('');

    tableBody.innerHTML = rows;
    applyTooltipContent(tableBody);
    if (window.HoverTooltip) {
        window.HoverTooltip.attach(tableBody);
    }
    initializeTooltips(tableBody);
}

function formatLogStatusMeta(status) {
    const normalized = (status || '').toLowerCase();
    switch (normalized) {
        case 'success':
            return {
                label: 'SUCCESS',
                badgeClass: 'bg-success',
                icon: 'fa-check-circle',
            };
        case 'failed':
        case 'failure':
            return {
                label: 'FAILED',
                badgeClass: 'bg-danger',
                icon: 'fa-times-circle',
            };
        case 'error':
            return {
                label: 'ERROR',
                badgeClass: 'bg-danger',
                icon: 'fa-triangle-exclamation',
            };
        case 'pending':
            return {
                label: 'PENDING',
                badgeClass: 'bg-warning text-dark',
                icon: 'fa-clock',
            };
        case 'running':
            return {
                label: 'RUNNING',
                badgeClass: 'bg-warning text-dark',
                icon: 'fa-spinner',
            };
        default:
            return {
                label: (status || 'UNKNOWN').toString().toUpperCase(),
                badgeClass: 'bg-secondary',
                icon: 'fa-circle',
            };
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
        return { label: 'Failed', badgeClass: 'bg-danger', icon: 'times' };
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
        } else if (display.label === 'Failed') {
            lines.push('Marked as failed.');
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

async function loadTestCaseDetails(testCaseId) {
    if (!testCaseId) {
        return null;
    }

    if (testCaseCache.has(testCaseId)) {
        return testCaseCache.get(testCaseId);
    }

    if (pendingTestCaseRequests.has(testCaseId)) {
        return pendingTestCaseRequests.get(testCaseId);
    }

    const fetchPromise = (async () => {
        try {
            const response = await fetch(`/v1/api/test-cases/${encodeURIComponent(testCaseId)}`);
            if (!response.ok) {
                if (response.status === 404) {
                    testCaseCache.set(testCaseId, null);
                    return null;
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            testCaseCache.set(testCaseId, data);
            return data;
        } catch (error) {
            console.error(`Failed to load test case ${testCaseId}:`, error);
            testCaseCache.set(testCaseId, null);
            return null;
        } finally {
            pendingTestCaseRequests.delete(testCaseId);
        }
    })();

    pendingTestCaseRequests.set(testCaseId, fetchPromise);
    return fetchPromise;
}

function truncateText(text, maxLength) {
    if (!text) {
        return '';
    }
    const trimmed = text.trim();
    if (trimmed.length <= maxLength) {
        return escapeHtml(trimmed);
    }
    return `${escapeHtml(trimmed.substring(0, maxLength))}...`;
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

function toggleLogsLoading(show) {
    const spinner = document.getElementById('logsLoadingSpinner');
    const tableWrapper = document.getElementById('logsTableWrapper');
    const emptyState = document.getElementById('logsEmptyState');
    if (!spinner || !tableWrapper || !emptyState) {
        return;
    }

    if (show) {
        spinner.classList.remove('d-none');
        tableWrapper.classList.add('d-none');
        emptyState.classList.add('d-none');
    } else {
        spinner.classList.add('d-none');
    }
}

function updateLogsPagination() {
    const pagination = document.getElementById('logsPagination');
    const prevPage = document.getElementById('logsPrevPage');
    const nextPage = document.getElementById('logsNextPage');
    const currentPageSpan = document.getElementById('logsCurrentPage');
    const pageStatus = document.getElementById('logsPageStatus');

    if (!pagination || !prevPage || !nextPage || !currentPageSpan) {
        return;
    }

    if (currentLogs.length === 0 && logsPage === 1) {
        pagination.classList.add('d-none');
        if (pageStatus) {
            pageStatus.textContent = '';
        }
        return;
    }

    pagination.classList.remove('d-none');
    currentPageSpan.textContent = logsPage.toString();

    if (logsPage <= 1) {
        prevPage.classList.add('disabled');
    } else {
        prevPage.classList.remove('disabled');
    }

    if (currentLogs.length < LOGS_PAGE_SIZE) {
        nextPage.classList.add('disabled');
    } else {
        nextPage.classList.remove('disabled');
    }

    if (pageStatus) {
        const start = (logsPage - 1) * LOGS_PAGE_SIZE + 1;
        const end = start + currentLogs.length - 1;
        pageStatus.textContent = `Showing ${start}-${end}`;
    }
}

function loadPreviousLogsPage() {
    if (logsPage > 1) {
        logsPage -= 1;
        loadRegressionLogs();
    }
}

function loadNextLogsPage() {
    if (currentLogs.length < LOGS_PAGE_SIZE) {
        return;
    }
    logsPage += 1;
    loadRegressionLogs();
}

function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${escapeHtml(message)}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    const toastRoot = document.getElementById('toast-root');
    const container = document.querySelector('.container');

    if (toastRoot) {
        toastRoot.appendChild(alertDiv);
    } else if (container) {
        container.insertBefore(alertDiv, container.firstChild);
    }

    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

function viewLogInNewPage(logId) {
    window.open(`/test-logs/${logId}`, '_blank');
}

function reExecuteLog(logId) {
    window.location.href = `/test-execution?logId=${logId}`;
}

async function deleteLog(logId) {
    if (!confirm('Are you sure you want to delete this test log? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/v1/api/test-logs/${logId}`, {
            method: 'DELETE',
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        showAlert('Test log deleted successfully!', 'success');
        loadRegressionLogs();
    } catch (error) {
        console.error('Error deleting test log:', error);
        showAlert('Failed to delete test log: ' + error.message, 'danger');
    }
}
