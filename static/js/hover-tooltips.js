/**
 * Hover Tooltip Manager
 *
 * Provides shared interactive tooltip behavior for table previews.
 */
(function tooltipManager(window, document) {
    const HIDE_DELAY = 200;
    const OFFSET = 12;
    const MIN_MARGIN = 12;
    const DEFAULT_SELECTOR = '.log-preview[data-hover-html]';

    const state = {
        trigger: null,
        panel: null,
        isPinned: false,
        hideTimer: null,
        docClickBound: false
    };

    function attach(root, options) {
        if (!root) {
            return;
        }
        const config = options || {};
        const selector = config.selector || DEFAULT_SELECTOR;
        const getContent = config.getContent || defaultGetContent;
        const triggers = root.querySelectorAll(selector);

        triggers.forEach((trigger) => {
            if (trigger.dataset.hoverTooltipBound === '1') {
                return;
            }
            trigger.dataset.hoverTooltipBound = '1';
            trigger.addEventListener('mouseenter', (event) => {
                const html = getContent(event.currentTarget);
                showTooltip(event.currentTarget, html);
            });
            trigger.addEventListener('mouseleave', onTriggerLeave);
            trigger.addEventListener('mousemove', onTriggerMove);
        });
    }

    function defaultGetContent(trigger) {
        if (!trigger) {
            return '';
        }
        return trigger.getAttribute('data-hover-html') || '';
    }

    function onTriggerLeave(event) {
        const related = event.relatedTarget;
        if (state.isPinned && related === state.panel) {
            return;
        }
        scheduleHide();
    }

    function onTriggerMove(event) {
        if (!state.trigger || state.isPinned) {
            return;
        }
        positionPanel(event.currentTarget);
    }

    function ensurePanel() {
        if (state.panel && document.body.contains(state.panel)) {
            return state.panel;
        }

        const panel = document.createElement('div');
        panel.className = 'log-tooltip-panel';
        panel.style.display = 'none';
        panel.addEventListener('mouseenter', () => {
            state.isPinned = true;
            clearHideTimer();
            panel.classList.add('pinned');
        });
        panel.addEventListener('mouseleave', (event) => {
            if (state.isPinned) {
                return;
            }
            const toElement = event.relatedTarget;
            if (!toElement || toElement !== state.trigger) {
                scheduleHide();
            }
        });

        document.body.appendChild(panel);
        state.panel = panel;

        if (!state.docClickBound) {
            document.addEventListener('click', handleDocumentClick, true);
            state.docClickBound = true;
        }

        return panel;
    }

    function showTooltip(trigger, html) {
        const panel = ensurePanel();
        const sameTrigger = state.trigger === trigger;
        const reuseContent = state.isPinned && sameTrigger;
        if (!reuseContent) {
            panel.innerHTML = html || '';
            panel.scrollTop = 0;
        }
        panel.classList.toggle('pinned', reuseContent);
        panel.style.display = 'block';
        state.trigger = trigger;
        state.isPinned = reuseContent;
        positionPanel(trigger);
        clearHideTimer();
    }

    function positionPanel(trigger) {
        const panel = ensurePanel();
        const rect = trigger.getBoundingClientRect();
        const panelRect = panel.getBoundingClientRect();
        const viewportHeight = window.innerHeight;

        const idealTop = rect.top + window.scrollY;
        const panelHeight = panelRect.height;
        const maxTop = window.scrollY + viewportHeight - panelHeight - MIN_MARGIN;
        const top = Math.max(window.scrollY + MIN_MARGIN, Math.min(idealTop, maxTop));

        const left = rect.right + OFFSET + window.scrollX;
        panel.style.top = `${top}px`;
        panel.style.left = `${left}px`;

        const triggerMiddle = rect.top + rect.height / 2 + window.scrollY;
        const arrowOffset = Math.min(
            Math.max(triggerMiddle - top - 8, MIN_MARGIN),
            Math.max(panelHeight - 20, MIN_MARGIN)
        );
        panel.style.setProperty('--log-tooltip-arrow-top', `${arrowOffset}px`);
    }

    function scheduleHide() {
        clearHideTimer();
        state.hideTimer = window.setTimeout(() => {
            if (!state.isPinned) {
                hideTooltip();
            }
        }, HIDE_DELAY);
    }

    function clearHideTimer() {
        if (state.hideTimer) {
            clearTimeout(state.hideTimer);
            state.hideTimer = null;
        }
    }

    function hideTooltip() {
        clearHideTimer();
        if (state.panel) {
            state.panel.style.display = 'none';
            state.panel.classList.remove('pinned');
        }
        state.trigger = null;
        state.isPinned = false;
    }

    function handleDocumentClick(event) {
        if (!state.panel || state.panel.style.display === 'none' || !state.isPinned) {
            return;
        }
        if (state.panel.contains(event.target)) {
            return;
        }
        if (state.trigger && state.trigger.contains(event.target)) {
            return;
        }
        hideTooltip();
    }

    window.HoverTooltip = {
        attach,
        hide: hideTooltip
    };
})(window, document);
