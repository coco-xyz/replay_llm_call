/**
 * Regression Test Detail JavaScript
 *
 * Displays regression metadata and associated logs.
 */

window.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadRegressionDetail();
});

function setupEventListeners() {
    const refreshBtn = document.getElementById('refreshDetailBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadRegressionDetail();
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
