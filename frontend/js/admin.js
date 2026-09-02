/**
 * admin.js | Admin panel functionality
 */

let allUsers = [];
let selectedUserId = null;
let currentUserId = null;
let deactivateModal = null;
let reactivateModal = null;
let deleteModal = null;

function getModal(id) {
  const el = document.getElementById(id);
  return el ? bootstrap.Modal.getOrCreateInstance(el) : null;
}

document.addEventListener('DOMContentLoaded', async () => {
  deactivateModal = getModal('deactivateModal');
  reactivateModal = getModal('reactivateModal');
  deleteModal = getModal('deleteModal');

  // Verify admin role
  try {
    const user = await Api.auth.me();
    if (user.role !== 'admin') {
      window.location.href = '/pages/dashboard.html';
      return;
    }
    document.getElementById('nav-username').textContent = user.full_name || 'Admin';
  } catch (err) {
    console.error('Auth check failed:', err);
  }

  // Load initial data
  loadUsers();
  loadAuditLogs();

  // Event listeners
  document.getElementById('user-search').addEventListener('input', filterUsers);
  document.getElementById('confirm-deactivate-btn').addEventListener('click', confirmDeactivate);
  document.getElementById('confirm-reactivate-btn').addEventListener('click', confirmReactivate);
  document.getElementById('confirm-delete-btn').addEventListener('click', confirmDelete);
});

/**
 * Load and display all users
 */
async function loadUsers() {
  try {
    const tbody = document.getElementById('users-table-body');
    let skeletonHtml = '';
    for (let i = 0; i < 5; i++) {
        skeletonHtml += `
        <tr>
            <td><div class="skeleton-loader" style="height: 20px; width: 120px;"></div></td>
            <td><div class="skeleton-loader" style="height: 20px; width: 150px;"></div></td>
            <td><div class="skeleton-loader" style="height: 20px; width: 80px;"></div></td>
            <td><div class="skeleton-loader" style="height: 20px; width: 80px;"></div></td>
            <td><div class="skeleton-loader" style="height: 20px; width: 100px;"></div></td>
            <td><div class="skeleton-loader" style="height: 20px; width: 100px; float: right;"></div></td>
        </tr>`;
    }
    tbody.innerHTML = skeletonHtml;

    allUsers = await Api.admin.listUsers();

    if (!allUsers || allUsers.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" class="text-center py-5">
            <div class="ag-empty-state p-3">
              <div class="ag-empty-icon mb-2" style="width: 48px; height: 48px; font-size: 1.25rem;">
                <i class="ag-icon ag-people"></i>
              </div>
              <h6 class="ag-empty-title mb-1">No Users Found</h6>
              <p class="ag-empty-text mb-0 small">No instructor accounts match your criteria.</p>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    const htmlStr = allUsers.map(user => {
      const joinDate = new Date(user.created_at).toLocaleDateString();
      const statusClass = user.is_active ? 'user-status-active' : 'user-status-inactive';
      const statusText = user.is_active ? 'Active' : 'Inactive';
      const statusIcon = user.is_active ? 'check-circle' : 'x-circle';
      
      const roleClass = user.role === 'admin' ? 'bg-danger' : 'bg-primary';
      const roleText = user.role === 'admin' ? 'Admin' : 'Instructor';

      return `
        <tr>
          <td>
            <div class="d-flex align-items-center gap-2">
              <div class="p-2 rounded-circle" style="background: var(--ag-border)">
                <i class="ag-icon ag-person text-muted"></i>
              </div>
              <div>
                <div class="fw-bold">${escapeHtml(user.full_name)}</div>
              </div>
            </div>
          </td>
          <td>${escapeHtml(user.email)}</td>
          <td>
            <span class="badge ${roleClass}">${roleText}</span>
          </td>
          <td>
            <span class="user-status-badge ${statusClass}">
              <i class="ag-icon ag-${statusIcon}"></i>
              ${statusText}
            </span>
          </td>
          <td class="text-muted small">${joinDate}</td>
          <td class="text-end">
            <button class="btn btn-sm btn-outline-primary me-1" onclick="showChangeRoleModal('${user.id}', '${escapeHtml(user.full_name)}', '${user.role}')" title="Change Role">
              <i class="ag-icon ag-arrow-left-right"></i>
            </button>
            ${user.is_active && user.role !== 'admin' ? `
              <button class="btn btn-sm btn-outline-warning me-1" onclick="showDeactivateModal('${user.id}', '${escapeHtml(user.full_name)}')">
                <i class="ag-icon ag-pause-circle"></i>
              </button>
            ` : user.role === 'admin' ? `
              <span class="text-muted small">—</span>
            ` : `
              <button class="btn btn-sm btn-outline-success me-1" onclick="showReactivateModal('${user.id}', '${escapeHtml(user.full_name)}')">
                <i class="ag-icon ag-play-circle"></i>
              </button>
            `}
            ${user.role !== 'admin' ? `
              <button class="btn btn-sm btn-outline-danger" onclick="showDeleteModal('${user.id}', '${escapeHtml(user.full_name)}')">
                <i class="ag-icon ag-trash"></i>
              </button>
            ` : ''}
          </td>
        </tr>
      `;
    }).join('');
    tbody.innerHTML = htmlStr;
  } catch (err) {
    console.error('Error loading users:', err);
    document.getElementById('users-table-body').innerHTML = `
      <tr><td colspan="6" class="text-center py-4 text-danger">
        Error loading users: ${err.detail || err.message}
      </td></tr>
    `;
  }
}

/**
 * Filter users by search term
 */
function filterUsers() {
  const searchTerm = document.getElementById('user-search').value.toLowerCase();
  const tbody = document.getElementById('users-table-body');
  const rows = tbody.querySelectorAll('tr');

  rows.forEach(row => {
    const text = row.textContent.toLowerCase();
    row.style.display = text.includes(searchTerm) ? '' : 'none';
  });
}

/**
 * Show deactivate confirmation modal
 */
function showDeactivateModal(userId, userName) {
  selectedUserId = userId;
  document.getElementById('deactivate-user-name').textContent = userName;
  deactivateModal = deactivateModal || getModal('deactivateModal');
  if (deactivateModal) deactivateModal.show();
}

/**
 * Confirm and execute user deactivation
 */
async function confirmDeactivate() {
  if (!selectedUserId) return;

  try {
    const btn = document.getElementById('confirm-deactivate-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Deactivating...';

    await Api.admin.deactivateUser(selectedUserId);

    deactivateModal = deactivateModal || getModal('deactivateModal');
    if (deactivateModal) deactivateModal.hide();
    selectedUserId = null;

    // Show success message
    showAlert('User suspended successfully', 'warning');

    // Reload users
    loadUsers();
  } catch (err) {
    console.error('Error deactivating user:', err);
    showAlert(`Error: ${err.detail || err.message}`, 'danger');
  } finally {
    const btn = document.getElementById('confirm-deactivate-btn');
    btn.disabled = false;
    btn.innerHTML = 'Deactivate';
  }
}

/**
 * Show reactivate confirmation modal
 */
function showReactivateModal(userId, userName) {
  selectedUserId = userId;
  document.getElementById('reactivate-user-name').textContent = userName;
  reactivateModal = reactivateModal || getModal('reactivateModal');
  if (reactivateModal) reactivateModal.show();
}

/**
 * Confirm and execute user reactivation
 */
async function confirmReactivate() {
  if (!selectedUserId) return;

  try {
    const btn = document.getElementById('confirm-reactivate-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Reactivating...';

    await Api.admin.reactivateUser(selectedUserId);

    reactivateModal = reactivateModal || getModal('reactivateModal');
    if (reactivateModal) reactivateModal.hide();
    selectedUserId = null;

    // Show success message
    showAlert('User access restored successfully', 'success');

    // Reload users
    loadUsers();
  } catch (err) {
    console.error('Error reactivating user:', err);
    showAlert(`Error: ${err.detail || err.message}`, 'danger');
  } finally {
    const btn = document.getElementById('confirm-reactivate-btn');
    btn.disabled = false;
    btn.innerHTML = 'Reactivate';
  }
}

/**
 * Show delete confirmation modal
 */
function showDeleteModal(userId, userName) {
  selectedUserId = userId;
  document.getElementById('delete-user-name').textContent = userName;
  deleteModal = deleteModal || getModal('deleteModal');
  if (deleteModal) deleteModal.show();
}

/**
 * Confirm and execute permanent deletion
 */
async function confirmDelete() {
  if (!selectedUserId) return;

  try {
    const btn = document.getElementById('confirm-delete-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Deleting...';

    await Api.admin.deleteUser(selectedUserId);

    deleteModal = deleteModal || getModal('deleteModal');
    if (deleteModal) deleteModal.hide();
    selectedUserId = null;

    showAlert('User account totally ripped out of existence', 'danger');

    loadUsers();
  } catch (err) {
    console.error('Error deleting user:', err);
    showAlert(`Error: ${err.detail || err.message}`, 'danger');
  } finally {
    const btn = document.getElementById('confirm-delete-btn');
    btn.disabled = false;
    btn.innerHTML = 'Permanently Delete';
  }
}

/**
 * Load and display audit logs
 */
async function loadAuditLogs() {
  try {
    const container = document.getElementById('audit-logs-container');
    container.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div></div>';

    const params = {
      limit: 100,
      offset: 0
    };

    const actionFilter = document.getElementById('audit-action-filter')?.value;
    if (actionFilter) params.action = actionFilter;

    const logs = await Api.admin.auditLogs(params);

    if (!logs || logs.length === 0) {
      container.innerHTML = `
        <div class="ag-empty-state p-5">
          <div class="ag-empty-icon mb-2">
            <i class="ag-icon ag-file-text"></i>
          </div>
          <h6 class="ag-empty-title">No Audit Logs Found</h6>
          <p class="ag-empty-text mb-0">There are no security or activity logs matching your current filter.</p>
        </div>
      `;
      return;
    }

    const htmlStr = logs.map(log => {
      const timestamp = new Date(log.timestamp).toLocaleString();
      const actionBadgeClass = getActionBadgeClass(log.action);

      return `
        <div class="audit-log-row">
          <div class="d-flex justify-content-between align-items-start">
            <div class="flex-grow-1">
              <div class="d-flex align-items-center gap-2 mb-2">
                <span class="action-badge ${actionBadgeClass}">${escapeHtml(log.action)}</span>
                <span class="text-muted small">${timestamp}</span>
              </div>
              <div class="small">
                <strong>User:</strong> ${log.user_id ? log.user_id.substring(0, 8) + '...' : 'System'}<br>
                <strong>Entity:</strong> ${log.entity_type || 'N/A'} (${log.entity_id ? log.entity_id.substring(0, 8) + '...' : 'N/A'})<br>
                ${log.ip_address ? `<strong>IP:</strong> ${escapeHtml(log.ip_address)}<br>` : ''}
              </div>
            </div>
          </div>
        </div>
      `;
    }).join('');
    container.innerHTML = htmlStr;
  } catch (err) {
    console.error('Error loading audit logs:', err);
    document.getElementById('audit-logs-container').innerHTML = `
      <div class="p-4 text-center text-danger">
        Error loading audit logs: ${err.detail || err.message}
      </div>
    `;
  }
}

/**
 * Get badge class for action type
 */
function getActionBadgeClass(action) {
  if (action.includes('login')) return 'action-login';
  if (action.includes('upload')) return 'action-upload';
  if (action.includes('delete')) return 'action-delete';
  return 'action-other';
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
  const alertDiv = document.createElement('div');
  alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
  alertDiv.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  `;

  const container = document.querySelector('.dashboard-main');
  container.insertBefore(alertDiv, container.firstChild);

  setTimeout(() => alertDiv.remove(), 5000);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

/**
 * Logout function
 */
async function logout() {
  try {
    await Api.auth.logout();
    window.location.href = '/pages/login.html';
  } catch (err) {
    console.error('Logout error:', err);
    window.location.href = '/pages/login.html';
  }
}


// ── Change Role ───────────────────────────────────────────────────────────────

let changeRoleModal;

function showChangeRoleModal(userId, userName, currentRole) {
  currentUserId = userId;
  
  if (!changeRoleModal) {
    changeRoleModal = createChangeRoleModal();
  }
  
  document.getElementById('change-role-user-name').textContent = userName;
  document.getElementById('change-role-current').textContent = currentRole === 'admin' ? 'Admin' : 'Instructor';
  
  // Set the select to the opposite role
  const select = document.getElementById('new-role-select');
  select.value = currentRole === 'admin' ? 'instructor' : 'admin';
  
  changeRoleModal.show();
}

function createChangeRoleModal() {
  const modalHtml = `
    <div class="modal fade" id="changeRoleModal" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content glass-panel border-0">
          <div class="modal-header border-0 pb-0">
            <h5 class="modal-title fw-bold">Change User Role</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body px-4 py-4">
            <p class="text-muted">Change the account type for:</p>
            <p class="fw-bold mb-3" id="change-role-user-name"></p>
            <div class="mb-3">
              <label class="form-label">Current Role</label>
              <p class="fw-bold text-primary" id="change-role-current"></p>
            </div>
            <div class="mb-3">
              <label for="new-role-select" class="form-label">New Role</label>
              <select class="form-select" aria-label="Select an option" id="new-role-select">
                <option value="instructor">Instructor</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div class="alert alert-info mb-0">
              <i class="ag-icon ag-info-circle me-2"></i>
              <strong>Note:</strong> Changing to Admin will grant full system access. Changing to Instructor will restrict access.
            </div>
          </div>
          <div class="modal-footer border-0">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-primary" id="confirm-change-role-btn" onclick="confirmChangeRole()">
              Change Role
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
  
  document.body.insertAdjacentHTML('beforeend', modalHtml);
  return new bootstrap.Modal(document.getElementById('changeRoleModal'));
}

async function confirmChangeRole() {
  try {
    const btn = document.getElementById('confirm-change-role-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Changing...';

    const newRole = document.getElementById('new-role-select').value;
    const result = await Api.admin.changeUserRole(currentUserId, newRole);
    
    changeRoleModal.hide();
    showAlert(result.message || 'User role changed successfully', 'success');
    await loadUsers();
  } catch (err) {
    showAlert(err.detail || 'Failed to change user role', 'danger');
  } finally {
    const btn = document.getElementById('confirm-change-role-btn');
    btn.disabled = false;
    btn.innerHTML = 'Change Role';
  }
}

// Export to global scope
window.showChangeRoleModal = showChangeRoleModal;
window.confirmChangeRole = confirmChangeRole;
