/**
 * ui.js | Global UI logic for AcademicGuard
 * Handles:
 * - Theme switching (Dark/Light)
 * - Page transition animations
 * - Shared component initializations
 */

const UI = {
    init() {
        this.initTheme();
        this.setupToggles();
        this.initPageTransitions();
        this.initSidebar();
        this.syncSidebarUser();
    },

    initSidebar() {
        const toggleBtn = document.getElementById('sidebar-toggle');
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');

        if (toggleBtn && sidebar) {
            toggleBtn.onclick = (e) => {
                e.stopPropagation();
                sidebar.classList.toggle('show');
                if (overlay) overlay.classList.toggle('show');
            };
        }

        if (overlay && sidebar) {
            overlay.onclick = () => {
                sidebar.classList.remove('show');
                overlay.classList.remove('show');
            };
        }

        // Highlight active nav link based on current page
        const currentPage = document.body.dataset.page || '';
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.sidebar .nav-link');
        navLinks.forEach(link => {
            const href = link.getAttribute('href') || '';
            if ((currentPage && href.includes(currentPage)) || (currentPath && href.endsWith(currentPath))) {
                link.classList.add('active');
            }
        });
    },

    syncSidebarUser() {
        let user = window._currentUser;
        if (!user) {
            try {
                user = JSON.parse(localStorage.getItem('user'));
            } catch (_) {}
        }
        if (!user) return;

        const name = user.full_name || user.email || "User";
        const role = user.role === 'admin' ? 'Administrator' : 'Instructor';
        const initials = name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'AG';

        const sidebarUsername = document.getElementById('sidebar-username');
        if (sidebarUsername) sidebarUsername.textContent = name;

        const sidebarAvatar = document.getElementById('sidebar-avatar') || document.getElementById('user-avatar');
        if (sidebarAvatar) sidebarAvatar.textContent = initials;

        const sidebarRoleBadge = document.getElementById('sidebar-role-badge') || document.getElementById('sidebar-role');
        if (sidebarRoleBadge) {
            sidebarRoleBadge.textContent = role;
            if (user.role === 'admin') {
                sidebarRoleBadge.className = 'user-role-badge admin';
            } else {
                sidebarRoleBadge.className = 'user-role-badge instructor';
            }
        }

        const adminLink = document.getElementById('sidebar-admin-link') || document.getElementById('admin-link');
        if (adminLink) {
            adminLink.style.display = user.role === 'admin' ? 'flex' : 'none';
        }
    },

    initTheme() {
        const savedTheme = localStorage.getItem('ag-theme') || localStorage.getItem('theme') || 'dark';
        this.setTheme(savedTheme);
    },

    setTheme(theme) {
        const activeTheme = theme === 'light' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', activeTheme);
        document.documentElement.setAttribute('data-bs-theme', activeTheme);
        if (document.body) {
            document.body.setAttribute('data-theme', activeTheme);
        }
        localStorage.setItem('ag-theme', activeTheme);
        localStorage.setItem('theme', activeTheme);
        this.updateThemeIcons(activeTheme);
        this.applyChartDefaults(activeTheme);
        this.refreshCharts();
        window.dispatchEvent(new CustomEvent('ag-theme-change', { detail: { theme: activeTheme } }));
    },

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
    },

    updateThemeIcons(theme) {
        const isDark = theme === 'dark';
        const toggles = document.querySelectorAll('.theme-toggle, #theme-toggle');
        toggles.forEach(toggle => {
            toggle.setAttribute('title', isDark ? 'Switch to light mode' : 'Switch to dark mode');
            toggle.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
            const icon = toggle.querySelector('i') || toggle;
            if (icon && icon.tagName === 'I') {
                icon.className = isDark ? 'ag-icon ag-sun-fill' : 'ag-icon ag-moon-fill';
            }
        });
        const themeIcon = document.getElementById('theme-icon');
        if (themeIcon) {
            themeIcon.className = isDark ? 'ag-icon ag-sun-fill' : 'ag-icon ag-moon-fill';
        }
    },

    setupToggles() {
        // 1. Handle existing toggles in HTML
        const existingToggles = document.querySelectorAll('.theme-toggle, #theme-toggle');
        existingToggles.forEach(toggle => {
            toggle.onclick = (e) => {
                e.preventDefault();
                this.toggleTheme();
            };
        });

        // 2. Add toggle to navbar if missing but navbar exists
        const navRight = document.querySelector('.navbar-ag .navbar-actions, .navbar-ag .d-flex.align-items-center:last-child');
        if (navRight && !document.querySelector('.navbar-ag .theme-toggle, .navbar-ag #theme-toggle')) {
            const toggle = this.createToggleElement('me-3');
            navRight.prepend(toggle);
        }

        // 3. Add floating toggle for pages without navbar (Login/Register)
        if (!document.querySelector('.navbar-ag') && !document.querySelector('.theme-toggle')) {
            const floatingToggle = this.createToggleElement('position-fixed');
            Object.assign(floatingToggle.style, {
                top: '20px',
                right: '20px',
                zIndex: '9999',
                boxShadow: 'var(--ag-shadow-lg)'
            });
            document.body.appendChild(floatingToggle);
        }

        const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
        this.updateThemeIcons(currentTheme);
    },

    createToggleElement(extraClass = '') {
        const toggle = document.createElement('button');
        toggle.className = `theme-toggle btn ${extraClass}`;
        toggle.type = 'button';
        toggle.title = 'Toggle Theme';
        toggle.innerHTML = '<i class="ag-icon ag-sun-fill"></i>';
        toggle.onclick = (e) => {
            e.preventDefault();
            this.toggleTheme();
        };
        return toggle;
    },

    initPageTransitions() {
        document.body.classList.add('animate-fade-in');
    },

    // Chart.js Theme Management
    applyChartDefaults(theme) {
        if (typeof Chart === 'undefined') return;
        const isDark = theme === 'dark';
        const textColor = isDark ? '#cbd5e1' : '#334155';
        const gridColor = isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.07)';

        Object.assign(Chart.defaults, {
            color: textColor,
            font: {
                family: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                size: 12,
            }
        });

        if (Chart.defaults.scales?.linear?.grid) {
            Chart.defaults.scales.linear.grid.color = gridColor;
        }
        if (Chart.defaults.scales?.linear?.ticks) {
            Chart.defaults.scales.linear.ticks.color = textColor;
        }
        if (Chart.defaults.scales?.category?.grid) {
            Chart.defaults.scales.category.grid.color = gridColor;
        }
        if (Chart.defaults.scales?.category?.ticks) {
            Chart.defaults.scales.category.ticks.color = textColor;
        }
        
        if (Chart.defaults.plugins?.legend?.labels) {
            Chart.defaults.plugins.legend.labels.color = textColor;
            Chart.defaults.plugins.legend.labels.font = {
                family: "'Outfit', sans-serif",
                weight: '600',
                size: 12
            };
        }

        if (Chart.defaults.plugins?.tooltip) {
            Chart.defaults.plugins.tooltip.backgroundColor = isDark ? 'rgba(17, 23, 40, 0.96)' : 'rgba(255, 255, 255, 0.98)';
            Chart.defaults.plugins.tooltip.titleColor = isDark ? '#f8fafc' : '#0f172a';
            Chart.defaults.plugins.tooltip.titleFont = {
                family: "'Outfit', sans-serif",
                weight: '700',
                size: 13
            };
            Chart.defaults.plugins.tooltip.bodyColor = isDark ? '#cbd5e1' : '#334155';
            Chart.defaults.plugins.tooltip.bodyFont = {
                family: "'Inter', sans-serif",
                size: 12
            };
            Chart.defaults.plugins.tooltip.borderColor = isDark ? 'rgba(255, 255, 255, 0.15)' : 'rgba(0, 0, 0, 0.12)';
            Chart.defaults.plugins.tooltip.borderWidth = 1;
            Chart.defaults.plugins.tooltip.padding = 10;
            Chart.defaults.plugins.tooltip.cornerRadius = 8;
            Chart.defaults.plugins.tooltip.boxPadding = 4;
        }
    },

    refreshCharts() {
        if (typeof Chart === 'undefined') return;

        // Find all chart instances and update them
        Object.values(Chart.instances).forEach(chart => {
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            const textColor = isDark ? '#cbd5e1' : '#334155';
            const gridColor = isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.07)';

            chart.options.color = textColor;

            if (chart.options.scales) {
                Object.values(chart.options.scales).forEach(scale => {
                    if (scale.grid) scale.grid.color = gridColor;
                    if (scale.ticks) scale.ticks.color = textColor;
                });
            }

            if (chart.options.plugins?.legend?.labels) {
                chart.options.plugins.legend.labels.color = textColor;
            }

            chart.update();
        });
    },

    // Utilities & Feedback
    showToast(message, type = 'info') {
        let container = document.getElementById('ag-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'ag-toast-container';
            container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            container.style.zIndex = '99999';
            document.body.appendChild(container);
        }
        const toastEl = document.createElement('div');
        const bgClass = type === 'danger' ? 'bg-danger text-white' :
                        type === 'success' ? 'bg-success text-white' :
                        type === 'warning' ? 'bg-warning text-dark' : 'bg-primary text-white';
        toastEl.className = `toast align-items-center ${bgClass} border-0 shadow-lg animate-fade-in`;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body fw-medium">
                    ${message}
                </div>
                <button type="button" class="btn-close ${type !== 'warning' ? 'btn-close-white' : ''} me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        container.appendChild(toastEl);
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
            const bsToast = new bootstrap.Toast(toastEl, { delay: 4500 });
            bsToast.show();
            toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
        } else {
            setTimeout(() => toastEl.remove(), 4500);
        }
    },

    // Skeleton Loaders
    renderSkeletonTable(tbody, rows = 5, cols = 6) {
        if (!tbody) return;
        let html = '';
        for (let r = 0; r < rows; r++) {
            html += '<tr>';
            for (let c = 0; c < cols; c++) {
                const width = Math.floor(Math.random() * 40) + 50; // 50-90% width
                html += `<td><div class="skeleton-loader" style="height: 1.1rem; width: ${width}%; border-radius: var(--ag-radius-xs);"></div></td>`;
            }
            html += '</tr>';
        }
        tbody.innerHTML = html;
    },

    renderSkeletonCards(container, count = 4) {
        if (!container) return;
        let html = '';
        for (let i = 0; i < count; i++) {
            html += `
                <div class="custom-metric-card">
                    <div class="skeleton-loader mb-2" style="height: 0.8rem; width: 40%; border-radius: var(--ag-radius-xs);"></div>
                    <div class="skeleton-loader mb-3" style="height: 2.2rem; width: 65%; border-radius: var(--ag-radius-sm);"></div>
                    <div class="skeleton-loader" style="height: 0.75rem; width: 80%; border-radius: var(--ag-radius-xs);"></div>
                </div>
            `;
        }
        container.innerHTML = html;
    },

    // Empty States
    renderEmptyState(container, { icon = 'bi-inbox', title = 'No Data Available', description = 'There are currently no records to display.', actionText = '', actionHref = '', actionOnClick = '' } = {}) {
        if (!container) return;
        const btnHtml = actionText ? `
            <a href="${actionHref || 'javascript:void(0)'}" ${actionOnClick ? `onclick="${actionOnClick}"` : ''} class="btn btn-primary btn-sm mt-2">
                ${actionText}
            </a>
        ` : '';

        container.innerHTML = `
            <div class="ag-empty-state animate-fade-in">
                <div class="ag-empty-icon">
                    <i class="bi ${icon}"></i>
                </div>
                <h6 class="ag-empty-title">${title}</h6>
                <p class="ag-empty-text">${description}</p>
                ${btnHtml}
            </div>
        `;
    },

    // ── Accessibility Suite (WCAG 2.2 AA) ─────────────────────────────────
    initAccessibility() {
        this.ensureSkipLink();
        this.initAriaLive();
        this.loadA11yPreferences();
        this.bindKeyboardShortcuts();
    },

    ensureSkipLink() {
        if (!document.querySelector('.skip-link') && document.body) {
            const skipLink = document.createElement('a');
            skipLink.href = '#main-content';
            skipLink.className = 'skip-link';
            skipLink.textContent = 'Skip to main content';
            document.body.prepend(skipLink);

            // Ensure main content element has id and tabindex
            const main = document.querySelector('main');
            if (main && !main.id) {
                main.id = 'main-content';
                main.setAttribute('tabindex', '-1');
            }
        }
    },

    initAriaLive() {
        if (!document.getElementById('ag-a11y-live-polite')) {
            const polite = document.createElement('div');
            polite.id = 'ag-a11y-live-polite';
            polite.className = 'sr-only';
            polite.setAttribute('aria-live', 'polite');
            polite.setAttribute('aria-atomic', 'true');
            document.body.appendChild(polite);
        }
        if (!document.getElementById('ag-a11y-live-assertive')) {
            const assertive = document.createElement('div');
            assertive.id = 'ag-a11y-live-assertive';
            assertive.className = 'sr-only';
            assertive.setAttribute('aria-live', 'assertive');
            assertive.setAttribute('aria-atomic', 'true');
            document.body.appendChild(assertive);
        }
    },

    announce(message, priority = 'polite') {
        const regionId = priority === 'assertive' ? 'ag-a11y-live-assertive' : 'ag-a11y-live-polite';
        const region = document.getElementById(regionId);
        if (region) {
            region.textContent = '';
            setTimeout(() => {
                region.textContent = message;
            }, 50);
        }
    },

    loadA11yPreferences() {
        const savedScale = localStorage.getItem('ag-font-scale');
        if (savedScale) this.setFontScale(savedScale);

        const savedContrast = localStorage.getItem('ag-high-contrast');
        if (savedContrast === 'true') this.setHighContrast(true);

        const savedMotion = localStorage.getItem('ag-reduced-motion');
        if (savedMotion === 'true') this.setReducedMotion(true);
    },

    setFontScale(percentage) {
        document.documentElement.setAttribute('data-font-scale', percentage);
        localStorage.setItem('ag-font-scale', percentage);
        this.announce(`Font size scaled to ${percentage} percent`);
    },

    setHighContrast(enable) {
        if (enable) {
            document.documentElement.setAttribute('data-theme', 'high-contrast');
            localStorage.setItem('ag-high-contrast', 'true');
            this.announce('High contrast mode enabled', 'assertive');
        } else {
            const savedTheme = localStorage.getItem('ag-theme') || 'dark';
            document.documentElement.setAttribute('data-theme', savedTheme);
            localStorage.setItem('ag-high-contrast', 'false');
            this.announce('High contrast mode disabled');
        }
    },

    setReducedMotion(enable) {
        document.documentElement.setAttribute('data-reduced-motion', enable ? 'true' : 'false');
        localStorage.setItem('ag-reduced-motion', enable ? 'true' : 'false');
        this.announce(enable ? 'Reduced motion enabled' : 'Reduced motion disabled');
    },

    bindKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Shift + ? to toggle Accessibility & Keyboard Shortcuts modal
            if (e.key === '?' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
                e.preventDefault();
                this.showKeyboardShortcuts();
            }
        });
    },

    showKeyboardShortcuts() {
        let modal = document.getElementById('ag-a11y-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'ag-a11y-modal';
            modal.className = 'modal fade';
            modal.setAttribute('tabindex', '-1');
            modal.setAttribute('role', 'dialog');
            modal.setAttribute('aria-labelledby', 'ag-a11y-modal-title');
            modal.setAttribute('aria-modal', 'true');
            modal.innerHTML = `
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content shadow-lg border-0" style="background: var(--ag-card-bg); color: var(--ag-text);">
                        <div class="modal-header border-bottom border-secondary border-opacity-20">
                            <h5 class="modal-title fw-bold d-flex align-items-center gap-2" id="ag-a11y-modal-title">
                                <i class="ag-icon ag-universal-access text-primary"></i>
                                <span>Accessibility & Keyboard Shortcuts</span>
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-4">
                                <h6 class="fw-bold small text-muted text-uppercase tracking-wider mb-2">Display & Contrast Controls</h6>
                                <div class="d-flex flex-wrap gap-2 mb-2">
                                    <button class="btn btn-sm btn-outline-primary" onclick="UI.setFontScale('100')">Font 100%</button>
                                    <button class="btn btn-sm btn-outline-primary" onclick="UI.setFontScale('125')">Font 125%</button>
                                    <button class="btn btn-sm btn-outline-primary" onclick="UI.setFontScale('150')">Font 150%</button>
                                    <button class="btn btn-sm btn-outline-primary" onclick="UI.setFontScale('200')">Font 200%</button>
                                </div>
                                <div class="d-flex gap-2">
                                    <button class="btn btn-sm btn-outline-warning" onclick="UI.setHighContrast(document.documentElement.getAttribute('data-theme') !== 'high-contrast')">Toggle High Contrast</button>
                                    <button class="btn btn-sm btn-outline-info" onclick="UI.setReducedMotion(document.documentElement.getAttribute('data-reduced-motion') !== 'true')">Toggle Reduced Motion</button>
                                </div>
                            </div>
                            <div>
                                <h6 class="fw-bold small text-muted text-uppercase tracking-wider mb-2">Navigation Shortcuts</h6>
                                <ul class="list-unstyled small mb-0">
                                    <li class="d-flex justify-content-between py-1 border-bottom border-secondary border-opacity-10"><span>Open Shortcuts Guide</span> <kbd>?</kbd></li>
                                    <li class="d-flex justify-content-between py-1 border-bottom border-secondary border-opacity-10"><span>Skip to Main Content</span> <kbd>Tab</kbd></li>
                                    <li class="d-flex justify-content-between py-1 border-bottom border-secondary border-opacity-10"><span>Heatmap Matrix Traversal</span> <kbd>Arrow Keys</kbd></li>
                                    <li class="d-flex justify-content-between py-1"><span>Select Matrix Cell / Button</span> <kbd>Enter / Space</kbd></li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
            this.announce('Accessibility and keyboard shortcuts dialog opened', 'assertive');
        }
    },

    renderSkeletonTable(rows = 5, cols = 4) {
        let html = `<table class="table align-middle"><thead><tr>`;
        for (let c = 0; c < cols; c++) {
            html += `<th><div class="skeleton skeleton-text" style="width: 60%;"></div></th>`;
        }
        html += `</tr></thead><tbody>`;
        for (let r = 0; r < rows; r++) {
            html += `<tr>`;
            for (let c = 0; c < cols; c++) {
                html += `<td><div class="skeleton skeleton-text"></div></td>`;
            }
            html += `</tr>`;
        }
        html += `</tbody></table>`;
        return html;
    },

    renderSkeletonCards(count = 3) {
        let html = `<div class="row g-4">`;
        for (let i = 0; i < count; i++) {
            html += `
            <div class="col-12 col-md-4">
                <div class="card glass-panel border-0 p-4">
                    <div class="skeleton skeleton-title"></div>
                    <div class="skeleton skeleton-text"></div>
                    <div class="skeleton skeleton-text" style="width: 80%;"></div>
                </div>
            </div>`;
        }
        html += `</div>`;
        return html;
    }
};

window.escapeHtml = function(str) {
    if (!str && str !== 0) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
};

window.UI = UI;

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    UI.init();
    UI.initAccessibility();
});
