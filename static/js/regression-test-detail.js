/**
 * Regression Test Detail JavaScript
 *
 * Displays regression metadata and associated logs.
 */

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
            loadRegressionLogs();
        });
    }

    const refreshLogsBtn = document.getElementById('refreshLogsBtn');
    if (refreshLogsBtn) {
        refreshLogsBtn.addEventListener('click', () => loadRegressionLogs());
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
    const viewAllLogsBtn = document.getElementById('viewAllLogsBtn');
    const logsLink = `/test-logs?regressionTestId=${encodeURIComponent(regression.id)}`;
    if (openLogsBtn) openLogsBtn.href = logsLink;
    if (viewAllLogsBtn) viewAllLogsBtn.href = logsLink;

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

async function loadRegressionLogs() {
    const logsContainer = document.getElementById('logsList');
    if (logsContainer) {
        logsContainer.innerHTML = '<tr><td colspan="5" class="text-muted">Loading logs...</td></tr>';
    }

    try {
        const response = await fetch(`/v1/api/regression-tests/${regressionId}/logs?limit=50`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const logs = await response.json();
        displayRegressionLogs(logs);
    } catch (error) {
        console.error('Error loading regression logs:', error);
        showDetailError('Failed to load regression logs: ' + error.message);
    }
}

function displayRegressionLogs(logs) {
    const list = document.getElementById('logsList');
    const emptyState = document.getElementById('logsEmptyState');
    if (!list || !emptyState) return;

    if (!logs || logs.length === 0) {
        list.innerHTML = '';
        emptyState.classList.remove('d-none');
        return;
    }

    emptyState.classList.add('d-none');

    const rows = logs
        .map((log) => {
            const statusBadge = buildLogStatusBadge(log.status);
            const executedAt = formatDate(log.created_at);
            const responseTime = log.response_time_ms != null ? `${log.response_time_ms} ms` : '—';
            return `
            <tr>
                <td>
                    <div class="d-flex flex-column">
                        <a href="/test-cases/${log.test_case_id}" target="_blank" class="fw-semibold text-decoration-none">
                            ${escapeHtml(log.test_case_id)}
                        </a>
                        <small class="text-muted">Log ID: ${escapeHtml(log.id)}</small>
                    </div>
                </td>
                <td>${statusBadge}</td>
                <td><span class="badge bg-primary">${escapeHtml(log.model_name)}</span></td>
                <td>${responseTime}</td>
                <td>${executedAt}</td>
            </tr>`;
        })
        .join('');

    list.innerHTML = rows;
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

function buildLogStatusBadge(status) {
    const normalized = (status || '').toLowerCase();
    if (normalized === 'success') {
        return '<span class="badge bg-success"><i class="fas fa-check me-1"></i>Success</span>';
    }
    if (normalized === 'failed') {
        return '<span class="badge bg-danger"><i class="fas fa-times me-1"></i>Failed</span>';
    }
    return `<span class="badge bg-secondary">${escapeHtml(status)}</span>`;
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
