/**
 * Agents Management JavaScript
 *
 * Handles fetching, creating, updating, and deleting agents for the replay UI.
 */

let agents = [];

// Initialize page
window.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadAgents();
});

function setupEventListeners() {
    const refreshBtn = document.getElementById('refreshAgentsBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => loadAgents());
    }

    const createBtn = document.getElementById('confirmCreateAgent');
    if (createBtn) {
        createBtn.addEventListener('click', createAgent);
    }

    const updateBtn = document.getElementById('confirmUpdateAgent');
    if (updateBtn) {
        updateBtn.addEventListener('click', updateAgent);
    }

    const createModal = document.getElementById('createAgentModal');
    if (createModal) {
        createModal.addEventListener('hidden.bs.modal', () => {
            document.getElementById('createAgentForm').reset();
            clearModalAlert('createAgentAlert');
        });
    }

    const editModal = document.getElementById('editAgentModal');
    if (editModal) {
        editModal.addEventListener('hidden.bs.modal', () => {
            clearModalAlert('editAgentAlert');
        });
    }
}

async function loadAgents() {
    toggleLoading(true);
    try {
        const response = await fetch('/v1/api/agents/');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        agents = await response.json();
        displayAgents(agents);
        updateAgentHints(agents);
    } catch (error) {
        console.error('Error loading agents:', error);
        showAlert('Error loading agents: ' + error.message, 'danger');
    } finally {
        toggleLoading(false);
    }
}

function displayAgents(agentList) {
    const container = document.getElementById('agentsList');
    const table = document.getElementById('agentsTable');
    const emptyState = document.getElementById('emptyState');

    if (!container || !table || !emptyState) {
        return;
    }

    if (!agentList || agentList.length === 0) {
        container.innerHTML = '';
        table.style.display = 'none';
        emptyState.classList.remove('d-none');
        return;
    }

    table.style.display = 'table';
    emptyState.classList.add('d-none');

    const rows = agentList
        .map((agent) => {
            const descriptionHtml = agent.description
                ? `<div class="text-muted small text-break">${escapeHtml(truncateText(agent.description, 160))}</div>`
                : '<span class="text-muted">—</span>';
            const systemPrompt = agent.default_system_prompt
                ? `<div class="text-truncate" style="max-width: 260px;" title="${escapeHtml(agent.default_system_prompt)}">${escapeHtml(truncateText(agent.default_system_prompt, 120))}</div>`
                : '<span class="text-muted">—</span>';
            const modelSettings = agent.default_model_settings
                ? `<code class="text-muted">${escapeHtml(truncateText(JSON.stringify(agent.default_model_settings), 120))}</code>`
                : '<span class="text-muted">Inherited per case</span>';

            const createdAt = formatDate(agent.created_at);

            return `
            <tr>
                <td>
                    <div class="d-flex flex-column">
                        <div class="d-flex align-items-center gap-2">
                            <strong>${escapeHtml(agent.name)}</strong>
                        </div>
                    </div>
                </td>
                <td>${descriptionHtml}</td>
                <td>
                    <div class="d-flex flex-column gap-1">
                        <span class="badge bg-primary">${escapeHtml(agent.default_model_name || 'Not set')}</span>
                        ${systemPrompt}
                        <div class="text-muted small">${modelSettings}</div>
                    </div>
                </td>
                <td>
                    <div class="d-flex flex-column">
                        <span>${createdAt}</span>
                    </div>
                </td>
                <td class="text-end">
                    <div class="btn-group btn-group-sm" role="group">
                        <button type="button" class="btn btn-outline-info" onclick="viewAgentDetails('${agent.id}')" title="View details">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button type="button" class="btn btn-outline-primary" onclick="openEditAgent('${agent.id}')">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button type="button" class="btn btn-outline-secondary" onclick="openAgentTestCases('${agent.id}')" title="View test cases">
                            <i class="fas fa-list"></i>
                        </button>
                        <button type="button" class="btn btn-outline-danger" onclick="deleteAgent('${agent.id}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>`;
        })
        .join('');

    container.innerHTML = rows;
}

function updateAgentHints(agentList) {
    const hint = document.getElementById('agentHelp');
    if (!hint) {
        return;
    }

    if (!agentList || agentList.length === 0) {
        hint.classList.remove('d-none');
    } else {
        hint.classList.add('d-none');
    }
}

async function createAgent() {
    const nameInput = document.getElementById('createAgentName');
    const descriptionInput = document.getElementById('createAgentDescription');
    const modelNameInput = document.getElementById('createAgentModelName');
    const systemPromptInput = document.getElementById('createAgentSystemPrompt');
    const modelSettingsInput = document.getElementById('createAgentModelSettings');

    const name = nameInput.value.trim();
    const modelName = modelNameInput.value.trim();
    const systemPrompt = systemPromptInput.value.trim();

    if (!name || !modelName || !systemPrompt) {
        showModalAlert('createAgentAlert', 'Name, default model, and system prompt are required.', 'warning');
        return;
    }

    let modelSettings = {};
    try {
        modelSettings = parseJsonOrThrow(modelSettingsInput.value.trim(), {});
    } catch (error) {
        showModalAlert('createAgentAlert', error.message, 'danger');
        return;
    }

    const payload = {
        name: name,
        description: descriptionInput.value.trim() || null,
        default_model_name: modelName,
        default_system_prompt: systemPrompt,
        default_model_settings: modelSettings,
    };

    try {
        const response = await fetch('/v1/api/agents/', {
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

        bootstrap.Modal.getInstance(document.getElementById('createAgentModal')).hide();
        showAlert('Agent created successfully.', 'success');
        loadAgents();
    } catch (error) {
        console.error('Error creating agent:', error);
        showModalAlert('createAgentAlert', 'Error creating agent: ' + error.message, 'danger');
    }
}

function openEditAgent(agentId) {
    const agent = agents.find((item) => item.id === agentId);
    if (!agent) {
        showAlert('Unable to locate agent for editing.', 'danger');
        return;
    }

    document.getElementById('editAgentId').value = agent.id;
    document.getElementById('editAgentName').value = agent.name;
    document.getElementById('editAgentDescription').value = agent.description || '';
    document.getElementById('editAgentModelName').value = agent.default_model_name || '';
    document.getElementById('editAgentSystemPrompt').value = agent.default_system_prompt || '';
    document.getElementById('editAgentModelSettings').value = agent.default_model_settings
        ? JSON.stringify(agent.default_model_settings, null, 2)
        : '';

    clearModalAlert('editAgentAlert');
    const modal = new bootstrap.Modal(document.getElementById('editAgentModal'));
    modal.show();
}

async function updateAgent() {
    const agentId = document.getElementById('editAgentId').value;
    const name = document.getElementById('editAgentName').value.trim();
    const modelName = document.getElementById('editAgentModelName').value.trim();
    const systemPrompt = document.getElementById('editAgentSystemPrompt').value.trim();
    const modelSettingsText = document.getElementById('editAgentModelSettings').value.trim();

    if (!name || !modelName || !systemPrompt) {
        showModalAlert('editAgentAlert', 'Name, default model, and system prompt are required.', 'warning');
        return;
    }

    let modelSettings = {};
    try {
        modelSettings = parseJsonOrThrow(modelSettingsText, {});
    } catch (error) {
        showModalAlert('editAgentAlert', error.message, 'danger');
        return;
    }

    const payload = {
        name: name,
        description: document.getElementById('editAgentDescription').value.trim() || null,
        default_model_name: modelName,
        default_system_prompt: systemPrompt,
        default_model_settings: modelSettings,
    };

    try {
        const response = await fetch(`/v1/api/agents/${agentId}`, {
            method: 'PUT',
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

        bootstrap.Modal.getInstance(document.getElementById('editAgentModal')).hide();
        showAlert('Agent updated successfully.', 'success');
        loadAgents();
    } catch (error) {
        console.error('Error updating agent:', error);
        showModalAlert('editAgentAlert', 'Error updating agent: ' + error.message, 'danger');
    }
}

async function deleteAgent(agentId) {
    if (!confirm('Delete this agent? Associated test cases and regression tests will also be deleted.')) {
        return;
    }

    try {
        const response = await fetch(`/v1/api/agents/${agentId}`, {
            method: 'DELETE',
        });

        if (!response.ok) {
            const errorData = await safeJson(response);
            const message = errorData?.detail || `HTTP error! status: ${response.status}`;
            throw new Error(message);
        }

        showAlert('Agent deleted successfully.', 'success');
        loadAgents();
    } catch (error) {
        console.error('Error deleting agent:', error);
        showAlert('Error deleting agent: ' + error.message, 'danger');
    }
}

function openAgentTestCases(agentId) {
    window.open(`/test-cases?agentId=${encodeURIComponent(agentId)}`, '_blank');
}

// Helpers
function toggleLoading(show) {
    const spinner = document.getElementById('loadingSpinner');
    const table = document.getElementById('agentsTable');
    if (!spinner || !table) {
        return;
    }

    if (show) {
        spinner.classList.remove('d-none');
        table.classList.add('d-none');
    } else {
        spinner.classList.add('d-none');
        table.classList.remove('d-none');
    }
}

function parseJsonOrThrow(text, fallback) {
    if (!text) {
        return fallback;
    }

    try {
        return JSON.parse(text);
    } catch (error) {
        throw new Error('Model settings must be valid JSON. ' + error.message);
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

function viewAgentDetails(agentId) {
    window.open(`/agents/${agentId}`, '_blank');
}

// expose functions used by inline handlers
window.openEditAgent = openEditAgent;
window.viewAgentDetails = viewAgentDetails;
window.deleteAgent = deleteAgent;
window.openAgentTestCases = openAgentTestCases;
