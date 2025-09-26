/**
 * Test Cases Management JavaScript
 * 
 * Handles test case CRUD operations and UI interactions.
 */

const PAGE_SIZE = 20;
const FETCH_LIMIT = PAGE_SIZE + 1;

let currentTestCases = [];
let currentTestCaseId = null;
let selectedAgentId = '';
let currentPage = 1;
let hasNextPage = false;
let currentSearchTerm = '';
let searchDebounceTimer = null;
let hasAgentsAvailable = true;

const agentCache = new Map();
const pendingAgentRequests = new Map();

const agentAutocompleteConfigs = {
    filter: {
        inputId: 'agentFilterInput',
        hiddenId: 'agentFilter',
        resultsId: 'agentFilterResults',
        onSelect(agent) {
            if (selectedAgentId !== agent.id) {
                selectedAgentId = agent.id;
                currentPage = 1;
                loadTestCases(1);
            }
        },
        onClear() {
            if (selectedAgentId) {
                selectedAgentId = '';
                currentPage = 1;
                loadTestCases(1);
            }
        },
    },
    create: {
        inputId: 'createTestCaseAgentInput',
        hiddenId: 'createTestCaseAgent',
        resultsId: 'createTestCaseAgentResults',
        onSelect(agent) {
            updateCreateModalState(agent.id);
        },
        onClear() {
            updateCreateModalState('');
        },
    },
    edit: {
        inputId: 'editTestCaseAgentInput',
        hiddenId: 'editTestCaseAgent',
        resultsId: 'editTestCaseAgentResults',
        onSelect(agent) {
            const hidden = document.getElementById('editTestCaseAgent');
            if (hidden) {
                hidden.value = agent.id;
            }
        },
        onClear() {
            const hidden = document.getElementById('editTestCaseAgent');
            if (hidden) {
                hidden.value = '';
            }
        },
    },
};

// Initialize page
document.addEventListener('DOMContentLoaded', async function () {
    setupEventListeners();
    setupAgentAutocompleteControls();

    const urlParams = new URLSearchParams(window.location.search);
    const initialAgentId = urlParams.get('agentId');
    if (initialAgentId) {
        selectedAgentId = initialAgentId;
    }

    await hydrateAgentFilterInput();
    await checkAgentAvailability();
    loadTestCases(1);

    const testCaseId = urlParams.get('id');
    if (testCaseId) {
        setTimeout(() => viewTestCaseInNewPage(testCaseId), 1000);
    }
});

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

async function hydrateAgentFilterInput() {
    if (selectedAgentId) {
        const hidden = document.getElementById('agentFilter');
        if (hidden) {
            hidden.value = selectedAgentId;
        }
        const agent = await ensureAgentLoaded(selectedAgentId);
        const input = document.getElementById('agentFilterInput');
        if (input) {
            input.value = agent?.name || selectedAgentId;
        }
    } else {
        resetAgentAutocomplete('filter');
    }
}

async function checkAgentAvailability() {
    try {
        const results = await fetchJson('/v1/api/agents/?limit=1');
        hasAgentsAvailable = Array.isArray(results)
            ? results.some((agent) => !agent.is_deleted)
            : false;
    } catch (error) {
        console.error('Error checking agent availability:', error);
        hasAgentsAvailable = false;
    }
    updateAgentAvailabilityIndicators();
}

function updateAgentAvailabilityIndicators() {
    const warning = document.getElementById('agentWarning');
    if (warning) {
        warning.classList.toggle('d-none', hasAgentsAvailable);
    }

    document.querySelectorAll('button[data-bs-target="#createTestCaseModal"]').forEach((button) => {
        button.disabled = !hasAgentsAvailable;
    });

    updateCreateModalState(document.getElementById('createTestCaseAgent')?.value || '');
}

function updateCreateModalState(agentId) {
    const confirmButton = document.querySelector('#createTestCaseModal .btn-primary');
    if (confirmButton) {
        confirmButton.disabled = !hasAgentsAvailable || !agentId;
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

function setupEventListeners() {
    // Search functionality
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (searchDebounceTimer) {
                    clearTimeout(searchDebounceTimer);
                }
                applySearchFilters();
            }
        });

        searchInput.addEventListener('input', function (event) {
            const value = event.target.value;
            if (searchDebounceTimer) {
                clearTimeout(searchDebounceTimer);
            }
            searchDebounceTimer = setTimeout(() => {
                currentSearchTerm = value.trim();
                applySearchFilters();
            }, 400);
        });
    }

    const clearBtn = document.getElementById('clearFiltersBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            const searchField = document.getElementById('searchInput');
            selectedAgentId = '';
            currentSearchTerm = '';
            currentPage = 1;
            resetAgentAutocomplete('filter');
            if (searchDebounceTimer) {
                clearTimeout(searchDebounceTimer);
            }
            if (searchField) {
                searchField.value = '';
                searchField.focus();
            }
            loadTestCases(1);
        });
    }

    const prevBtn = document.getElementById('testCasesPrevPageBtn');
    if (prevBtn) {
        prevBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (currentPage > 1) {
                loadTestCases(currentPage - 1);
            }
        });
    }

    const nextBtn = document.getElementById('testCasesNextPageBtn');
    if (nextBtn) {
        nextBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (hasNextPage) {
                loadTestCases(currentPage + 1);
            }
        });
    }

    const createModal = document.getElementById('createTestCaseModal');
    if (createModal) {
        createModal.addEventListener('shown.bs.modal', () => {
            const agentInput = document.getElementById('createTestCaseAgentInput');
            if (agentInput) {
                agentInput.focus();
            }
            updateCreateModalState(document.getElementById('createTestCaseAgent')?.value || '');
        });
        createModal.addEventListener('hidden.bs.modal', () => {
            const form = document.getElementById('createTestCaseForm');
            if (form) {
                form.reset();
            }
            resetAgentAutocomplete('create');
            updateCreateModalState('');
        });
    }

    const editModal = document.getElementById('editTestCaseModal');
    if (editModal) {
        editModal.addEventListener('hidden.bs.modal', () => {
            const form = document.getElementById('editTestCaseForm');
            if (form) {
                form.reset();
            }
            resetAgentAutocomplete('edit');
        });
    }
}

function applySearchFilters() {
    const searchInput = document.getElementById('searchInput');
    currentSearchTerm = searchInput ? searchInput.value.trim() : '';
    currentPage = 1;
    loadTestCases(1);
}

async function loadTestCases(page = currentPage) {
    currentPage = page;
    showLoading(true);
    try {
        const isSearching = currentSearchTerm.length > 0;
        const basePath = isSearching
            ? '/v1/api/test-cases/search'
            : '/v1/api/test-cases/';
        const url = new URL(basePath, window.location.origin);
        url.searchParams.set('limit', FETCH_LIMIT.toString());
        url.searchParams.set('offset', ((page - 1) * PAGE_SIZE).toString());
        if (isSearching) {
            url.searchParams.set('q', currentSearchTerm);
        }
        if (selectedAgentId) {
            url.searchParams.append('agent_id', selectedAgentId);
        }

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const testCases = await response.json();
        hasNextPage = testCases.length > PAGE_SIZE;
        currentTestCases = hasNextPage
            ? testCases.slice(0, PAGE_SIZE)
            : testCases;
        displayTestCases(currentTestCases);
        updateTestCasesPagination();

    } catch (error) {
        console.error('Error loading test cases:', error);
        showAlert('Error loading test cases: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

function displayTestCases(testCases) {
    const container = document.getElementById('testCasesList');
    const emptyState = document.getElementById('emptyState');
    const table = document.getElementById('testCasesTable');

    if (testCases.length === 0) {
        container.innerHTML = '';
        table.style.display = 'none';
        emptyState.classList.remove('d-none');
        updateTestCasesPagination();
        return;
    }

    emptyState.classList.add('d-none');
    table.style.display = 'table';

    const html = testCases.map((testCase) => {
        const agentName = testCase.agent ? testCase.agent.name : 'Unknown agent';
        const agentDisplay = escapeHtml(agentName);
        const agentHref = testCase.agent_id ? `/agents/${encodeURIComponent(testCase.agent_id)}` : '#';
        const agentTag = testCase.agent
            ? `<a href="${agentHref}" class="text-decoration-none text-muted" target="_blank">${agentDisplay}</a>`
            : `<span class="text-muted">${agentDisplay}</span>`;
        const userMessage = testCase.last_user_message || '';
        const hasUserMessage = userMessage.trim().length > 0;
        const userMessageClass = hasUserMessage ? 'log-preview' : 'log-preview placeholder';
        const userMessageDisplay = hasUserMessage ? truncateText(userMessage, 120) : '—';
        const userMessageEncoded = encodeTooltipPayload(userMessage);
        const userMessageFallback = encodeTooltipPayload('No user message provided');
        const responseExample = testCase.response_example || '';
        const hasResponseExample = responseExample.trim().length > 0;
        const responseExampleClass = hasResponseExample ? 'log-preview' : 'log-preview placeholder';
        const responseExampleDisplay = hasResponseExample ? truncateText(responseExample, 120) : '—';
        const responseExampleEncoded = encodeTooltipPayload(responseExample);
        const responseExampleFallback = encodeTooltipPayload('No response example provided');
        const responseExpectation = testCase.response_expectation || '';
        const hasResponseExpectation = responseExpectation.trim().length > 0;
        const responseExpectationClass = hasResponseExpectation ? 'log-preview' : 'log-preview placeholder';
        const responseExpectationDisplay = hasResponseExpectation ? truncateText(responseExpectation, 120) : '—';
        const responseExpectationEncoded = encodeTooltipPayload(responseExpectation);
        const responseExpectationFallback = encodeTooltipPayload('No response expectation provided');
        const userMessageCell = `
            <span class="${userMessageClass}" data-bs-toggle="tooltip" data-bs-placement="top" data-bs-custom-class="log-tooltip" data-bs-html="true"
                  data-tooltip-content="${userMessageEncoded}" data-tooltip-fallback="${userMessageFallback}">
                ${escapeHtml(userMessageDisplay)}
            </span>
        `;
        const responseExampleCell = `
            <span class="${responseExampleClass}" data-bs-toggle="tooltip" data-bs-placement="top" data-bs-custom-class="log-tooltip" data-bs-html="true"
                  data-tooltip-content="${responseExampleEncoded}" data-tooltip-fallback="${responseExampleFallback}">
                ${escapeHtml(responseExampleDisplay)}
            </span>
        `;
        const responseExpectationCell = `
            <span class="${responseExpectationClass}" data-bs-toggle="tooltip" data-bs-placement="top" data-bs-custom-class="log-tooltip" data-bs-html="true"
                  data-tooltip-content="${responseExpectationEncoded}" data-tooltip-fallback="${responseExpectationFallback}">
                ${escapeHtml(responseExpectationDisplay)}
            </span>
        `;

        return `
        <tr>
            <td>
                <div class="d-flex flex-column">
                    <small class="text-muted">${agentTag}</small>
                    <div class="d-flex align-items-center flex-wrap">
                        <strong class="mt-1 d-inline-block">${escapeHtml(testCase.name)}</strong>
                    </div>
                    ${testCase.description ? `<small class="text-muted mt-1">${escapeHtml(truncateText(testCase.description, 60))}</small>` : ''}
                </div>
            </td>
            <td>
                ${userMessageCell}
            </td>
            <td>
                ${responseExampleCell}
            </td>
            <td>
                ${responseExpectationCell}
            </td>
            <td>
                <small class="text-muted">${formatDate(testCase.created_at)}</small>
            </td>
            <td>
                <div class="btn-group" role="group">
                    <button type="button" class="btn btn-sm btn-outline-primary" onclick="viewTestCaseInNewPage('${testCase.id}')" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-secondary" onclick="editTestCase('${testCase.id}')" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-info" onclick="reimportTestCase('${testCase.id}')" title="Re-import Raw Data">
                        <i class="fas fa-upload"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-success" onclick="executeTestCase('${testCase.id}')" title="Execute">
                        <i class="fas fa-play"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-danger" onclick="deleteTestCase('${testCase.id}')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `;
    }).join('');

    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        container.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((el) => {
            const instance = bootstrap.Tooltip.getInstance(el);
            if (instance) {
                instance.dispose();
            }
        });
    }

    container.innerHTML = html;
    applyTooltipContent(container);
    if (window.HoverTooltip) {
        window.HoverTooltip.attach(container);
    }
    initializeTooltips();
}

function updateTestCasesPagination() {
    const pagination = document.getElementById('testCasesPagination');
    const status = document.getElementById('testCasesPaginationStatus');
    const pageLabel = document.getElementById('testCasesPaginationCurrentPage');
    const prevBtn = document.getElementById('testCasesPrevPage');
    const nextBtn = document.getElementById('testCasesNextPage');

    if (!pagination || !status || !pageLabel || !prevBtn || !nextBtn) {
        return;
    }

    if (currentTestCases.length === 0) {
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
    const end = start + currentTestCases.length - 1;
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

async function createTestCase() {
    const name = document.getElementById('testCaseName').value.trim();
    const description = document.getElementById('testCaseDescription').value.trim();
    const responseExampleElement = document.getElementById('responseExample');
    const responseExample = responseExampleElement ? responseExampleElement.value.trim() : '';
    const responseExpectationElement = document.getElementById('responseExpectation');
    const responseExpectation = responseExpectationElement ? responseExpectationElement.value.trim() : '';
    const rawDataText = document.getElementById('rawData').value.trim();
    const agentSelect = document.getElementById('createTestCaseAgent');
    const agentId = agentSelect ? agentSelect.value : '';

    if (!name || !rawDataText || !agentId) {
        showAlert('Please fill in all required fields including the owning agent', 'warning');
        return;
    }

    let rawData;
    try {
        rawData = JSON.parse(rawDataText);
    } catch (error) {
        showAlert('Invalid JSON format in raw data', 'danger');
        return;
    }

    try {
        const response = await fetch('/v1/api/test-cases/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                description: description || null,
                raw_data: rawData,
                agent_id: agentId,
                response_example: responseExample || null,
                response_expectation: responseExpectation || null
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        const newTestCase = await response.json();
        showAlert('Test case created successfully!', 'success');

        // Close modal and reset form
        const modal = bootstrap.Modal.getInstance(document.getElementById('createTestCaseModal'));
        modal.hide();
        document.getElementById('createTestCaseForm').reset();

        // Reload test cases
        loadTestCases(1);

    } catch (error) {
        console.error('Error creating test case:', error);
        showAlert('Error creating test case: ' + error.message, 'danger');
    }
}

async function editTestCase(testCaseId) {
    try {
        const response = await fetch(`/v1/api/test-cases/${testCaseId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const testCase = await response.json();

        // Populate edit form (only name and description)
        document.getElementById('editTestCaseId').value = testCase.id;
        document.getElementById('editTestCaseName').value = testCase.name;
        document.getElementById('editTestCaseDescription').value = testCase.description || '';
        const editResponseExample = document.getElementById('editResponseExample');
        if (editResponseExample) {
            editResponseExample.value = testCase.response_example || '';
        }
        const editResponseExpectation = document.getElementById('editResponseExpectation');
        if (editResponseExpectation) {
            editResponseExpectation.value = testCase.response_expectation || '';
        }
        // Set agent field - both hidden and visible inputs
        const editAgentHidden = document.getElementById('editTestCaseAgent');
        const editAgentInput = document.getElementById('editTestCaseAgentInput');

        if (testCase.agent_id && editAgentHidden && editAgentInput) {
            // Set the hidden field value
            editAgentHidden.value = testCase.agent_id;

            // Load agent info and set the visible input
            try {
                const agent = await ensureAgentLoaded(testCase.agent_id);
                if (agent) {
                    editAgentInput.value = agent.name;
                } else {
                    editAgentInput.value = testCase.agent_id; // fallback to ID if agent not found
                }
            } catch (error) {
                console.error('Error loading agent for edit form:', error);
                editAgentInput.value = testCase.agent_id; // fallback to ID
            }
        } else if (editAgentHidden && editAgentInput) {
            // Clear both fields if no agent
            editAgentHidden.value = '';
            editAgentInput.value = '';
        }

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('editTestCaseModal'));
        modal.show();

    } catch (error) {
        console.error('Error loading test case for edit:', error);
        showAlert('Error loading test case: ' + error.message, 'danger');
    }
}

async function updateTestCase() {
    const testCaseId = document.getElementById('editTestCaseId').value;
    const name = document.getElementById('editTestCaseName').value.trim();
    const description = document.getElementById('editTestCaseDescription').value.trim();
    const agentId = document.getElementById('editTestCaseAgent').value;
    const responseExampleField = document.getElementById('editResponseExample');
    const responseExample = responseExampleField ? responseExampleField.value.trim() : '';
    const responseExpectationField = document.getElementById('editResponseExpectation');
    const responseExpectation = responseExpectationField ? responseExpectationField.value.trim() : '';

    if (!name || !agentId) {
        showAlert('Please provide a name and agent for the test case', 'warning');
        return;
    }

    try {
        const response = await fetch(`/v1/api/test-cases/${testCaseId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                description: description || null,
                agent_id: agentId || null,
                response_example: responseExample || null,
                response_expectation: responseExpectation || null
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        showAlert('Test case updated successfully!', 'success');

        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('editTestCaseModal'));
        modal.hide();

        // Reload test cases
        loadTestCases(currentPage);

    } catch (error) {
        console.error('Error updating test case:', error);
        showAlert('Error updating test case: ' + error.message, 'danger');
    }
}

async function reimportTestCase(testCaseId) {
    try {
        // Set the test case ID in the modal
        document.getElementById('reimportTestCaseId').value = testCaseId;

        // Clear the textarea
        document.getElementById('reimportRawData').value = '';
        clearModalAlert('reimportAlertContainer');

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('reimportTestCaseModal'));
        modal.show();

    } catch (error) {
        console.error('Error opening reimport modal:', error);
        showAlert('Error opening reimport modal: ' + error.message, 'danger');
    }
}

async function confirmReimportTestCase() {
    const testCaseId = document.getElementById('reimportTestCaseId').value;
    const rawDataText = document.getElementById('reimportRawData').value.trim();

    if (!rawDataText) {
        showModalAlert('reimportAlertContainer', 'Please enter the raw data', 'warning');
        return;
    }

    let rawData;
    try {
        rawData = JSON.parse(rawDataText);
    } catch (error) {
        showModalAlert('reimportAlertContainer', 'Invalid JSON format in raw data', 'danger');
        return;
    }

    try {
        const response = await fetch(`/v1/api/test-cases/${testCaseId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                raw_data: rawData
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('reimportTestCaseModal'));
        modal.hide();

        // Reset form
        document.getElementById('reimportTestCaseForm').reset();
        clearModalAlert('reimportAlertContainer');

        // Reload test cases
        loadTestCases(currentPage);

        showAlert('Test case raw data re-imported successfully!', 'success');

    } catch (error) {
        console.error('Error re-importing test case:', error);
        showModalAlert('reimportAlertContainer', 'Error re-importing test case: ' + error.message, 'danger');
    }
}

async function deleteTestCase(testCaseId) {
    if (!confirm('Are you sure you want to delete this test case? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/v1/api/test-cases/${testCaseId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        showAlert('Test case deleted successfully!', 'success');
        loadTestCases(currentPage);

    } catch (error) {
        console.error('Error deleting test case:', error);
        showAlert('Error deleting test case: ' + error.message, 'danger');
    }
}

async function viewTestCase(testCaseId) {
    try {
        const response = await fetch(`/v1/api/test-cases/${testCaseId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const testCase = await response.json();
        currentTestCaseId = testCaseId;

        // Helper function to format middle messages
        const formatMiddleMessages = (messages) => {
            if (!messages || messages.length === 0) {
                return '<div class="text-muted">No middle messages</div>';
            }

            return messages.map((message, index) => {
                const role = message.role || 'unknown';
                const content = message.content || '';
                const toolCalls = message.tool_calls || [];
                const roleColor = {
                    'user': 'text-primary',
                    'assistant': 'text-success',
                    'tool': 'text-warning',
                    'system': 'text-info'
                }[role] || 'text-secondary';

                // Format tool calls if present
                const formatToolCalls = (calls) => {
                    if (!calls || calls.length === 0) return '';

                    return calls.map((call, callIndex) => {
                        const toolId = call.id || 'unknown';
                        const toolName = call.function?.name || 'unknown';
                        const toolArgs = call.function?.arguments || '';

                        // Try to format arguments as JSON for better readability
                        let formattedArgs = toolArgs;
                        try {
                            if (typeof toolArgs === 'string') {
                                const parsed = JSON.parse(toolArgs);
                                formattedArgs = JSON.stringify(parsed, null, 2);
                            } else if (typeof toolArgs === 'object') {
                                formattedArgs = JSON.stringify(toolArgs, null, 2);
                            }
                        } catch (e) {
                            // Keep original format if JSON parsing fails
                            formattedArgs = String(toolArgs);
                        }

                        return `
                            <div class="mt-2 p-2 bg-warning bg-opacity-10 border border-warning border-opacity-25 rounded">
                                <div class="d-flex align-items-center mb-1">
                                    <i class="fas fa-tools text-warning me-2"></i>
                                    <strong class="text-warning">Tool Call #${callIndex + 1}</strong>
                                </div>
                                <div class="small">
                                    <div><strong>Name:</strong> <code>${escapeHtml(toolName)}</code></div>
                                    <div><strong>ID:</strong> <code>${escapeHtml(toolId)}</code></div>
                                    <div><strong>Arguments:</strong></div>
                                    <pre class="bg-light p-2 rounded mt-1 mb-0" style="font-size: 0.8em; max-height: 100px; overflow-y: auto;">${escapeHtml(formattedArgs)}</pre>
                                </div>
                            </div>
                        `;
                    }).join('');
                };

                return `
                    <div class="mb-2 border-start border-3 ps-2" style="border-color: var(--bs-${role === 'user' ? 'primary' : role === 'assistant' ? 'success' : role === 'tool' ? 'warning' : 'secondary'}) !important;">
                        <div class="d-flex align-items-center mb-1">
                            <span class="badge bg-secondary me-2">#${index + 1}</span>
                            <strong class="${roleColor}">${escapeHtml(role.toUpperCase())}</strong>
                            ${toolCalls.length > 0 ? `<span class="badge bg-warning ms-2">${toolCalls.length} tool call${toolCalls.length > 1 ? 's' : ''}</span>` : ''}
                        </div>
                        ${content ? `<pre class="bg-light p-2 rounded mb-0" style="font-size: 0.85em; max-height: 150px; overflow-y: auto;">${escapeHtml(content)}</pre>` : ''}
                        ${formatToolCalls(toolCalls)}
                    </div>
                `;
            }).join('');
        };

        // Display test case details
        const detailsHtml = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Basic Information</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Name:</strong></td><td>${escapeHtml(testCase.name)}</td></tr>
                        <tr><td><strong>Description:</strong></td><td>${escapeHtml(testCase.description || 'N/A')}</td></tr>
                        <tr><td><strong>Agent:</strong></td><td>${testCase.agent ? `<a href="/agents/${escapeHtml(testCase.agent_id)}" class="badge bg-primary text-decoration-none" target="_blank">${escapeHtml(testCase.agent.name)}</a>` : '<span class="text-muted">Unknown</span>'}</td></tr>
                        <tr><td><strong>Model:</strong></td><td>${escapeHtml(testCase.model_name)}</td></tr>
                        <tr><td><strong>Has Tools:</strong></td><td>${testCase.tools ? 'Yes' : 'No'}</td></tr>
                        <tr><td><strong>Created:</strong></td><td>${formatDate(testCase.created_at)}</td></tr>
                        <tr><td><strong>Updated:</strong></td><td>${formatDate(testCase.updated_at)}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>System Prompt</h6>
                    <pre class="bg-light p-3 rounded" style="max-height: 200px; overflow-y: auto;">${escapeHtml(testCase.system_prompt)}</pre>
                </div>
            </div>
            <div class="row mt-3">
                <div class="col-md-6">
                    <h6>Middle Messages</h6>
                    <div style="max-height: 300px; overflow-y: auto;">
                        ${formatMiddleMessages(testCase.middle_messages)}
                    </div>
            </div>
            <div class="col-md-6">
                <h6>Last User Message</h6>
                <pre class="bg-light p-3 rounded" style="max-height: 300px; overflow-y: auto;">${escapeHtml(testCase.last_user_message)}</pre>
            </div>
        </div>
        <div class="row mt-3">
            <div class="col-12">
                <h6>Response Example</h6>
                ${testCase.response_example ? `
                    <pre class="bg-light p-3 rounded" style="max-height: 300px; overflow-y: auto;">${escapeHtml(testCase.response_example)}</pre>
                ` : `
                    <p class="text-muted fst-italic mb-0">No response example recorded.</p>
                `}
            </div>
        </div>
        <div class="row mt-3">
            <div class="col-12">
                <h6>Response Expectation</h6>
                ${testCase.response_expectation ? `
                    <pre class="bg-light p-3 rounded" style="max-height: 300px; overflow-y: auto;">${escapeHtml(testCase.response_expectation)}</pre>
                ` : `
                    <p class="text-muted fst-italic mb-0">No response expectation recorded.</p>
                `}
            </div>
        </div>
        ${testCase.tools && testCase.tools.length > 0 ? `
        <div class="row mt-3">
            <div class="col-12">
                    <h6>Tools Configuration</h6>
                    <div class="accordion" id="toolsAccordion">
                        ${testCase.tools.map((tool, index) => `
                            <div class="accordion-item">
                                <h2 class="accordion-header" id="heading${index}">
                                    <button class="accordion-button collapsed" type="button"
                                            data-bs-toggle="collapse" data-bs-target="#collapse${index}"
                                            aria-expanded="false" aria-controls="collapse${index}">
                                        <i class="fas fa-wrench me-2"></i>
                                        <strong>${escapeHtml(tool.function?.name || 'Unknown Tool')}</strong>
                                        ${tool.function?.description ? `<span class="text-muted ms-2">- ${escapeHtml(truncateText(tool.function.description, 60))}</span>` : ''}
                                    </button>
                                </h2>
                                <div id="collapse${index}" class="accordion-collapse collapse"
                                     aria-labelledby="heading${index}" data-bs-parent="#toolsAccordion">
                                    <div class="accordion-body">
                                        <div class="row">
                                            <div class="col-md-6">
                                                <h6 class="text-primary">Function Details</h6>
                                                <table class="table table-sm">
                                                    <tr><td><strong>Name:</strong></td><td>${escapeHtml(tool.function?.name || 'N/A')}</td></tr>
                                                    <tr><td><strong>Type:</strong></td><td>${escapeHtml(tool.type || 'N/A')}</td></tr>
                                                    ${tool.function?.description ? `<tr><td><strong>Description:</strong></td><td>${escapeHtml(tool.function.description)}</td></tr>` : ''}
                                                </table>
                                            </div>
                                            <div class="col-md-6">
                                                <h6 class="text-success">Parameters Schema</h6>
                                                <pre class="bg-light p-2 rounded" style="max-height: 300px; overflow-y: auto; font-size: 0.85em;">${escapeHtml(JSON.stringify(tool.function?.parameters || {}, null, 2))}</pre>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
            ` : ''}
        `;

        document.getElementById('testCaseDetails').innerHTML = detailsHtml;

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('viewTestCaseModal'));
        modal.show();

    } catch (error) {
        console.error('Error loading test case details:', error);
        showAlert('Error loading test case details: ' + error.message, 'danger');
    }
}

function executeTestCase(testCaseId) {
    // Open test execution page in a new tab with the selected test case ID
    const executionUrl = `/test-execution?testCaseId=${testCaseId}`;
    const newWindow = window.open(executionUrl, '_blank');
    if (!newWindow) {
        // Fallback if the browser blocks popups
        window.location.href = executionUrl;
        return;
    }

    // Ensure the newly opened tab cannot control the original window
    newWindow.opener = null;
}

function executeFromView() {
    if (currentTestCaseId) {
        executeTestCase(currentTestCaseId);
    }
}

// Utility functions
function showLoading(show) {
    const spinner = document.getElementById('loadingSpinner');
    const list = document.getElementById('testCasesList');

    if (show) {
        spinner.classList.remove('d-none');
        list.classList.add('d-none');
    } else {
        spinner.classList.add('d-none');
        list.classList.remove('d-none');
    }
}

function clearModalAlert(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = '';
    }
}

function showModalAlert(containerId, message, type) {
    const container = document.getElementById(containerId);
    if (!container) {
        showAlert(message, type);
        return;
    }

    container.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
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
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
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

// New function to open test case details in a new page
function viewTestCaseInNewPage(testCaseId) {
    window.open(`/test-cases/${testCaseId}`, '_blank');
}
