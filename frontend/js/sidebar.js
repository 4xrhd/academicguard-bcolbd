/**
 * sidebar.js | Ultra-responsive, collapsible unified navigation component.
 * Features:
 * - Full Expanded mode (240px) vs Compact Icon-Rail mode (72px) with animated tooltips.
 * - Persistent collapse state stored in localStorage.
 * - Role-Based Access Control (RBAC): Admin link dynamically shown for administrator accounts.
 * - Asynchronous auth session synchronization (never stuck on "Guest").
 * - Mobile offcanvas slide-out drawer with backdrop blur and tap-to-dismiss.
 * - Dark/Light theme toggle integration.
 */

(function() {
    'use strict';

    // Get current active page identifier from URL
    function getCurrentPage() {
        const path = window.location.pathname;
        if (path.includes('dashboard.html')) return 'dashboard';
        if (path.includes('upload.html')) return 'upload';
        if (path.includes('results.html')) return 'results';
        if (path.includes('submission.html')) return 'results'; // Highlight All Batches / Results for submission view
        if (path.includes('admin.html')) return 'admin';
        if (path.includes('training.html')) return 'training';
        if (path.includes('annotate.html')) return 'training'; // Highlight Training for annotate view
        if (path.includes('settings.html')) return 'settings';
        return 'dashboard';
    }

    // Get user info synchronously (from window._currentUser or localStorage)
    function getUserInfo() {
        if (window._currentUser && typeof window._currentUser === 'object') {
            return window._currentUser;
        }
        try {
            const userStr = localStorage.getItem('user');
            return userStr ? JSON.parse(userStr) : null;
        } catch {
            return null;
        }
    }

    // Generate unified sidebar HTML
    function generateSidebar() {
        const currentPage = getCurrentPage();
        const user = getUserInfo();
        const isAdmin = user && user.role === 'admin';

        const menuItems = [
            { id: 'dashboard', icon: 'ag-grid-1x2', label: 'Dashboard', href: '/pages/dashboard.html', tooltip: 'Dashboard' },
            { id: 'upload', icon: 'ag-plus-circle', label: 'New Analysis', href: '/pages/upload.html', tooltip: 'New Analysis' },
            { id: 'results', icon: 'ag-bar-chart-steps', label: 'All Batches', href: '/pages/results.html', tooltip: 'All Batches' },
            { id: 'training', icon: 'ag-cpu', label: 'Model Retraining', href: '/pages/training.html', tooltip: 'Model Retraining' },
            { id: 'settings', icon: 'ag-gear', label: 'Settings', href: '/pages/settings.html', tooltip: 'Settings' },
            { type: 'divider' },
            { id: 'admin', icon: 'ag-people-fill', label: 'User Management', href: '/pages/admin.html', adminOnly: true, badge: 'Admin', tooltip: 'User Management (RBAC)' },
        ];

        const navItems = menuItems.map(item => {
            if (item.type === 'divider') {
                return '<div class="sidebar-divider"></div>';
            }
            if (item.adminOnly && !isAdmin) {
                return `
                    <a class="nav-link ${currentPage === item.id ? 'active' : ''}" href="${item.href}" id="sidebar-admin-link" data-tooltip="${item.tooltip}" style="display: none;">
                        <i class="ag-icon ${item.icon}"></i>
                        <span>${item.label}</span>
                        ${item.badge ? `<span class="nav-badge">${item.badge}</span>` : ''}
                    </a>
                `;
            }
            const isActive = currentPage === item.id ? 'active' : '';
            return `
                <a class="nav-link ${isActive}" href="${item.href}" ${item.id === 'admin' ? 'id="sidebar-admin-link"' : ''} data-tooltip="${item.tooltip}">
                    <i class="ag-icon ${item.icon}"></i>
                    <span>${item.label}</span>
                    ${item.badge ? `<span class="nav-badge">${item.badge}</span>` : ''}
                </a>
            `;
        }).join('');

        const userName = user ? (user.full_name || user.email || 'User') : 'Instructor';
        const userRole = user && user.role === 'admin' ? 'Administrator' : 'Instructor';
        const roleClass = user && user.role === 'admin' ? 'admin' : 'instructor';
        const userInitials = userName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'AG';
        const isCollapsed = localStorage.getItem('ag_sidebar_collapsed') === 'true';

        return `
            <!-- Sidebar Container -->
            <aside class="sidebar ${isCollapsed ? 'collapsed' : ''}" id="sidebar">
                <!-- Desktop Collapse Button -->
                <button class="sidebar-collapse-btn d-none d-md-flex" id="sidebar-collapse-btn" title="Toggle Sidebar" aria-label="Toggle sidebar width">
                    <i class="ag-icon ag-chevron-left"></i>
                </button>

                <!-- Brand Header -->
                <div class="sidebar-brand">
                    <a href="/pages/dashboard.html" class="brand-link">
                        <div class="brand-logo">
                            <i class="ag-icon ag-shield-check"></i>
                        </div>
                        <div class="brand-text">
                            <span class="brand-name">AcademicGuard</span>
                            <span class="brand-tag">INTEGRITY PLATFORM</span>
                        </div>
                    </a>
                </div>

                <!-- User Profile Section -->
                <div class="sidebar-user">
                    <div class="user-avatar-wrap">
                        <div class="user-avatar" id="sidebar-avatar">${userInitials}</div>
                        <span class="user-status-dot" title="Active"></span>
                    </div>
                    <div class="user-info">
                        <div class="user-name" id="sidebar-username">${userName}</div>
                        <span class="user-role-badge ${roleClass}" id="sidebar-role-badge">${userRole}</span>
                    </div>
                </div>

                <!-- Navigation Links -->
                <div class="sidebar-nav">
                    <p class="nav-section-title">MAIN MENU</p>
                    <nav class="nav flex-column">
                        ${navItems}
                    </nav>
                </div>

                <!-- Quick Actions (New Analysis) -->
                <div class="sidebar-actions">
                    <a href="/pages/upload.html" class="btn btn-primary w-100 d-flex align-items-center justify-content-center gap-2 shadow-sm">
                        <i class="ag-icon ag-plus-lg"></i>
                        <span>New Analysis</span>
                    </a>
                </div>

                <!-- Help & Engine Info Card -->
                <div class="sidebar-help">
                    <div class="help-card">
                        <i class="ag-icon ag-cpu text-primary fs-5"></i>
                        <div class="help-content">
                            <p class="help-title">NLP & AST Engine</p>
                            <p class="help-link">v2.5 Active Model</p>
                        </div>
                    </div>
                </div>

                <!-- Logout Button -->
                <div class="sidebar-footer">
                    <button class="btn btn-outline-danger w-100 d-flex align-items-center justify-content-center gap-2" onclick="logout()" title="Sign Out">
                        <i class="ag-icon ag-box-arrow-right"></i>
                        <span class="btn-logout-text">Sign Out</span>
                    </button>
                </div>
            </aside>
        `;
    }

    // Insert or refresh sidebar
    function initSidebar() {
        // Ensure mobile toggle and overlay exist outside dashboard-layout
        if (!document.getElementById('sidebar-toggle')) {
            document.body.insertAdjacentHTML('afterbegin', `
                <button class="sidebar-toggle d-md-none" id="sidebar-toggle" aria-label="Toggle navigation menu">
                    <i class="ag-icon ag-list"></i>
                </button>
            `);
        }
        if (!document.getElementById('sidebar-overlay')) {
            document.body.insertAdjacentHTML('afterbegin', `
                <div class="sidebar-overlay" id="sidebar-overlay"></div>
            `);
        }

        const existingSidebar = document.getElementById('sidebar') || document.querySelector('.sidebar');
        const dashboardLayout = document.querySelector('.dashboard-layout');

        if (existingSidebar && dashboardLayout) {
            existingSidebar.remove();
            dashboardLayout.insertAdjacentHTML('afterbegin', generateSidebar());
        } else if (!dashboardLayout) {
            const mainContent = document.querySelector('main') || document.querySelector('.dashboard-main');
            if (mainContent) {
                const wrapper = document.createElement('div');
                wrapper.className = 'dashboard-layout';
                mainContent.parentNode.insertBefore(wrapper, mainContent);
                wrapper.appendChild(mainContent);
                wrapper.insertAdjacentHTML('afterbegin', generateSidebar());
            }
        }

        // Setup event handlers
        setupCollapseToggle();
        setupMobileToggle();
        setupThemeToggle();
        syncUserData();
    }

    // Collapse toggle (Desktop/Tablet)
    function setupCollapseToggle() {
        const collapseBtn = document.getElementById('sidebar-collapse-btn');
        const sidebar = document.getElementById('sidebar');

        if (collapseBtn && sidebar) {
            collapseBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const isCollapsed = sidebar.classList.toggle('collapsed');
                localStorage.setItem('ag_sidebar_collapsed', isCollapsed ? 'true' : 'false');
            });
        }
    }

    // Mobile sidebar toggle with tap-to-dismiss
    function setupMobileToggle() {
        const toggle = document.getElementById('sidebar-toggle');
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');

        if (toggle && sidebar) {
            toggle.addEventListener('click', (e) => {
                e.stopPropagation();
                sidebar.classList.toggle('show');
                if (overlay) overlay.classList.toggle('show');
            });

            if (overlay) {
                overlay.addEventListener('click', () => {
                    sidebar.classList.remove('show');
                    overlay.classList.remove('show');
                });
            }

            // Close mobile drawer when clicking any link inside sidebar
            sidebar.querySelectorAll('.nav-link, .sidebar-actions a').forEach(link => {
                link.addEventListener('click', () => {
                    if (window.innerWidth < 768) {
                        sidebar.classList.remove('show');
                        if (overlay) overlay.classList.remove('show');
                    }
                });
            });
        }
    }

    // Theme toggle functionality
    function setupThemeToggle() {
        const toggle = document.getElementById('theme-toggle');
        if (toggle) {
            toggle.onclick = (e) => {
                e.preventDefault();
                if (window.UI && typeof window.UI.toggleTheme === 'function') {
                    window.UI.toggleTheme();
                } else {
                    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
                    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
                    document.documentElement.setAttribute('data-theme', newTheme);
                    document.documentElement.setAttribute('data-bs-theme', newTheme);
                    localStorage.setItem('ag-theme', newTheme);
                    localStorage.setItem('theme', newTheme);
                    updateThemeIcon(newTheme);
                }
            };
        }
        const savedTheme = localStorage.getItem('ag-theme') || localStorage.getItem('theme') || 'dark';
        updateThemeIcon(savedTheme);
    }

    function updateThemeIcon(theme) {
        const icon = document.getElementById('theme-icon');
        if (icon) {
            icon.className = theme === 'dark' ? 'ag-icon ag-sun-fill' : 'ag-icon ag-moon-fill';
        }
    }

    // Asynchronously synchronize user profile data & RBAC visibility
    async function syncUserData() {
        let user = getUserInfo();

        if (!user && window.Api && window.Api.auth) {
            try {
                user = await window.Api.auth.me();
                if (user) {
                    window._currentUser = user;
                    try {
                        localStorage.setItem('user', JSON.stringify(user));
                    } catch (_) {}
                }
            } catch (_) {
                user = null;
            }
        }

        if (user) {
            const userName = user.full_name || user.email || 'User';
            const userRole = user.role === 'admin' ? 'Administrator' : 'Instructor';
            const roleClass = user.role === 'admin' ? 'admin' : 'instructor';
            const userInitials = userName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'AG';

            const sidebarUsername = document.getElementById('sidebar-username');
            const sidebarRoleBadge = document.getElementById('sidebar-role-badge');
            const sidebarAvatar = document.getElementById('sidebar-avatar');
            const navUsername = document.getElementById('nav-username');
            const adminLink = document.getElementById('sidebar-admin-link');

            if (sidebarUsername) sidebarUsername.textContent = userName;
            if (sidebarRoleBadge) {
                sidebarRoleBadge.textContent = userRole;
                sidebarRoleBadge.className = `user-role-badge ${roleClass}`;
            }
            if (sidebarAvatar) sidebarAvatar.textContent = userInitials;
            if (navUsername) navUsername.textContent = userName;

            // Show admin link if user is administrator
            if (adminLink) {
                adminLink.style.display = user.role === 'admin' ? 'flex' : 'none';
            }
        }
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSidebar);
    } else {
        initSidebar();
    }

    // Expose globally
    window.initSidebar = initSidebar;
    window.syncSidebarUser = syncUserData;
})();
