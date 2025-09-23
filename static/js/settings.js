/**
 * Settings page interactions.
 */

let currentEvaluationSettings = null;

const evaluationModelInput = document.getElementById('evaluationModel');
const evaluationProviderInput = document.getElementById('evaluationProvider');
const saveButton = document.getElementById('saveSettingsBtn');
const resetButton = document.getElementById('resetSettingsBtn');
const refreshButton = document.getElementById('refreshSettingsBtn');
const alertContainer = document.getElementById('alertContainer');

async function loadSettings() {
    toggleSaveState(true);
    hideAlert();
    try {
        const response = await fetch('/v1/api/settings/evaluation');
        if (!response.ok) {
            throw new Error(`Failed to load settings (status ${response.status})`);
        }
        const data = await response.json();
        currentEvaluationSettings = data;
        if (evaluationProviderInput) {
            evaluationProviderInput.value = data.provider || 'unknown';
        }
        if (evaluationModelInput) {
            evaluationModelInput.value = data.model_name || '';
        }
    } catch (error) {
        console.error('Failed to load evaluation settings', error);
        showAlert(`Failed to load evaluation settings: ${error.message}`, 'danger');
    } finally {
        toggleSaveState(false);
    }
}

async function saveSettings() {
    if (!evaluationModelInput) {
        return;
    }
    const modelName = evaluationModelInput.value.trim();
    if (!modelName) {
        showAlert('Model name cannot be empty.', 'warning');
        evaluationModelInput.focus();
        return;
    }

    toggleSaveState(true);
    hideAlert();
    try {
        const response = await fetch('/v1/api/settings/evaluation', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_name: modelName })
        });

        if (!response.ok) {
            const payload = await safeParseJson(response);
            const detail = payload?.detail || `HTTP ${response.status}`;
            throw new Error(detail);
        }

        const data = await response.json();
        currentEvaluationSettings = data;
        evaluationModelInput.value = data.model_name || '';
        showAlert('Evaluation settings saved successfully.', 'success');
    } catch (error) {
        console.error('Failed to save evaluation settings', error);
        showAlert(`Failed to save settings: ${error.message}`, 'danger');
    } finally {
        toggleSaveState(false);
    }
}

function resetSettingsForm() {
    if (!currentEvaluationSettings || !evaluationModelInput) {
        return;
    }
    evaluationModelInput.value = currentEvaluationSettings.model_name || '';
    hideAlert();
}

function toggleSaveState(disabled) {
    if (saveButton) {
        saveButton.disabled = disabled;
        saveButton.innerHTML = disabled
            ? '<i class="fas fa-spinner fa-spin me-2"></i>Saving...'
            : '<i class="fas fa-save me-2"></i>Save Changes';
    }
    if (resetButton) {
        resetButton.disabled = disabled;
    }
    if (refreshButton) {
        refreshButton.disabled = disabled;
    }
    if (evaluationModelInput) {
        evaluationModelInput.disabled = disabled;
    }
}

function showAlert(message, type) {
    if (!alertContainer) {
        return;
    }
    alertContainer.className = '';
    alertContainer.classList.add('alert', `alert-${type}`);
    alertContainer.innerHTML = `
        <div class="d-flex justify-content-between align-items-start">
            <div>
                ${escapeHtml(message)}
            </div>
            <button type="button" class="btn-close" aria-label="Close"></button>
        </div>
    `;
    const closeBtn = alertContainer.querySelector('button');
    if (closeBtn) {
        closeBtn.addEventListener('click', hideAlert);
    }
    alertContainer.classList.remove('d-none');
}

function hideAlert() {
    if (!alertContainer) {
        return;
    }
    alertContainer.classList.add('d-none');
    alertContainer.innerHTML = '';
}

function escapeHtml(text) {
    if (text === null || text === undefined) {
        return '';
    }
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.toString().replace(/[&<>"']/g, (m) => map[m]);
}

async function safeParseJson(response) {
    try {
        return await response.json();
    } catch (error) {
        return null;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    if (saveButton) {
        saveButton.addEventListener('click', saveSettings);
    }
    if (resetButton) {
        resetButton.addEventListener('click', resetSettingsForm);
    }
    if (refreshButton) {
        refreshButton.addEventListener('click', loadSettings);
    }

    loadSettings();
});
