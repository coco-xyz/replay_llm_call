/**
 * Model History Manager
 *
 * Provides reusable helpers for managing the model name history dropdown
 * that is shared across multiple pages and modal dialogs.
 */
(function () {
    const MODEL_HISTORY_KEY = 'llm_replay_model_history';
    const MAX_HISTORY_ITEMS = 10;

    class ModelHistoryInput {
        constructor(input, dropdown) {
            this.input = input;
            this.dropdown = dropdown;
            this.pointerDownInDropdown = false;

            this.handleDocumentClick = this.handleDocumentClick.bind(this);
            this.onFocus = this.onFocus.bind(this);
            this.onBlur = this.onBlur.bind(this);
            this.onInput = this.onInput.bind(this);
            this.onKeyDown = this.onKeyDown.bind(this);

            this.initialize();
        }

        initialize() {
            this.input.setAttribute('autocomplete', 'off');

            this.input.addEventListener('focus', this.onFocus);
            this.input.addEventListener('blur', this.onBlur);
            this.input.addEventListener('input', this.onInput);
            this.input.addEventListener('keydown', this.onKeyDown);
            document.addEventListener('click', this.handleDocumentClick);
        }

        onFocus() {
            this.showHistory();
        }

        onBlur() {
            const value = this.input.value.trim();
            if (value) {
                saveModelToHistory(value);
            }

            setTimeout(() => {
                if (!this.pointerDownInDropdown) {
                    this.hideHistory();
                }
                this.pointerDownInDropdown = false;
            }, 0);
        }

        onInput(event) {
            const value = event.target.value.trim();
            if (value) {
                this.filterHistory(value);
            } else {
                this.showHistory();
            }
        }

        onKeyDown(event) {
            if (event.key === 'Enter') {
                const value = this.input.value.trim();
                if (value) {
                    saveModelToHistory(value);
                }
                this.hideHistory();
            } else if (event.key === 'Escape') {
                this.hideHistory();
            }
        }

        handleDocumentClick(event) {
            if (this.input.contains(event.target) || this.dropdown.contains(event.target)) {
                return;
            }
            this.hideHistory();
        }

        showHistory() {
            const history = getModelHistory();
            this.renderDropdown(history);
        }

        filterHistory(searchTerm) {
            const term = searchTerm.toLowerCase();
            const filtered = getModelHistory().filter((modelName) =>
                modelName.toLowerCase().includes(term)
            );
            this.renderDropdown(filtered);
        }

        renderDropdown(items) {
            if (!items || items.length === 0) {
                this.dropdown.innerHTML = '';
                this.dropdown.classList.remove('show');
                return;
            }

            this.dropdown.innerHTML = '';

            items.forEach((modelName) => {
                const item = document.createElement('div');
                item.className = 'dropdown-item d-flex justify-content-between align-items-center';
                item.style.cursor = 'pointer';

                const modelText = document.createElement('span');
                modelText.textContent = modelName;
                modelText.style.flex = '1';

                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'btn btn-sm btn-outline-danger ms-2';
                deleteBtn.innerHTML = '<i class="fas fa-times"></i>';
                deleteBtn.title = 'Remove from history';
                deleteBtn.style.fontSize = '0.75rem';
                deleteBtn.style.padding = '0.125rem 0.25rem';

                item.addEventListener('mousedown', (event) => {
                    if (event.target === deleteBtn || deleteBtn.contains(event.target)) {
                        removeFromModelHistory(modelName);
                        this.showHistory();
                        return;
                    }

                    this.pointerDownInDropdown = true;
                    this.input.value = modelName;
                    saveModelToHistory(modelName);
                });

                item.addEventListener('mouseup', () => {
                    this.hideHistory();
                    this.pointerDownInDropdown = false;
                });

                item.appendChild(modelText);
                item.appendChild(deleteBtn);
                this.dropdown.appendChild(item);
            });

            this.dropdown.classList.add('show');
        }

        hideHistory() {
            this.dropdown.classList.remove('show');
        }
    }

    function getModelHistory() {
        try {
            const history = localStorage.getItem(MODEL_HISTORY_KEY);
            return history ? JSON.parse(history) : [];
        } catch (error) {
            console.error('Error loading model history:', error);
            return [];
        }
    }

    function saveModelToHistory(modelName) {
        if (!modelName || modelName.trim() === '') {
            return;
        }

        try {
            let history = getModelHistory();
            history = history.filter((item) => item !== modelName);
            history.unshift(modelName);
            if (history.length > MAX_HISTORY_ITEMS) {
                history = history.slice(0, MAX_HISTORY_ITEMS);
            }
            localStorage.setItem(MODEL_HISTORY_KEY, JSON.stringify(history));
        } catch (error) {
            console.error('Error saving model history:', error);
        }
    }

    function removeFromModelHistory(modelName) {
        try {
            let history = getModelHistory();
            history = history.filter((item) => item !== modelName);
            localStorage.setItem(MODEL_HISTORY_KEY, JSON.stringify(history));
        } catch (error) {
            console.error('Error removing from model history:', error);
        }
    }

    window.ModelHistoryManager = {
        initInput(options) {
            if (!options) {
                return null;
            }

            const input = options.inputElement || document.getElementById(options.inputId);
            const dropdown = options.dropdownElement || document.getElementById(options.dropdownId);

            if (!input || !dropdown) {
                return null;
            }

            return new ModelHistoryInput(input, dropdown);
        },
        saveModelToHistory,
        getModelHistory,
        removeFromModelHistory,
    };
})();
