/**
 * auth.js | Login, registration, and session guard logic.
 * FR-AUTH-01: Registration form validation + submit.
 * FR-AUTH-02: Login form submit → JWT cookie set by server.
 * FR-AUTH-03: RBAC redirect | admin → admin panel, instructor → dashboard.
 */

document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  initAuthFlow(page);
});

/**
 * Global session guard that can be awaited by pages
 */
async function guardSession() {
  const page = document.body.dataset.page;
  return await initAuthFlow(page);
}
window.guardSession = guardSession;

const PUBLIC_PAGES = new Set(["login", "register"]);
const ROLE_PAGE_REQUIREMENTS = {
  admin: ["admin"],
};

let _authFlowPromise = null;

// ── Session bootstrapping + guard ─────────────────────────────────────────────
async function initAuthFlow(page) {
  if (_authFlowPromise) return _authFlowPromise;

  _authFlowPromise = (async () => {
    if (page === "login") initLogin();
    if (page === "register") initRegister();

    let user = null;
    try {
      user = await Api.auth.me();
    } catch (_) {
      user = null;
    }

    if (PUBLIC_PAGES.has(page)) {
      if (user) {
        const target = getSafeNextPath() || getDefaultPathForRole(user.role);
        if (!window.location.pathname.endsWith(target)) {
          window.location.href = target;
        }
      }
      return user;
    }

    if (!user) {
      const next = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.href = `/pages/login.html?next=${next}`;
      return null;
    }

    if (!isAuthorizedForPage(page, user.role)) {
      redirectByRole(user.role);
      return user;
    }

    window._currentUser = user;
    try {
      localStorage.setItem('user', JSON.stringify(user));
    } catch (_) {}
    populateNavbar(user);
    if (typeof window.syncSidebarUser === 'function') {
      window.syncSidebarUser();
    }
    return user;
  })().finally(() => {
    _authFlowPromise = null;
  });

  return _authFlowPromise;
}

// ── Login ─────────────────────────────────────────────────────────────────────
function initLogin() {
  const form = document.getElementById("login-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    
    if (!form.checkValidity()) {
      e.stopPropagation();
      form.classList.add('was-validated');
      return;
    }
    
    clearErrors(form);

    const email    = form.querySelector("#email").value.trim();
    const password = form.querySelector("#password").value;

    try {
      showSpinner(form);
      await Api.auth.login({ email, password });
      const user = await Api.auth.me();
      window._currentUser = user;
      try {
        localStorage.setItem('user', JSON.stringify(user));
      } catch (_) {}
      const target = getSafeNextPath() || getDefaultPathForRole(user.role);
      window.location.href = target;
    } catch (err) {
      showError(form, err.detail || "Login failed. Please check your credentials.");
    } finally {
      hideSpinner(form);
    }
  });
}

// ── Registration ──────────────────────────────────────────────────────────────
function initRegister() {
  const form = document.getElementById("register-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (!form.checkValidity()) {
      e.stopPropagation();
      form.classList.add('was-validated');
      return;
    }

    clearErrors(form);

    const full_name = form.querySelector("#full-name").value.trim();
    const email     = form.querySelector("#email").value.trim();
    const password  = form.querySelector("#password").value;
    const confirm   = form.querySelector("#confirm-password").value;

    // Client-side validation
    if (password !== confirm) {
      showError(form, "Passwords do not match.");
      return;
    }

    try {
      showSpinner(form);
      await Api.auth.register({ full_name, email, password });
      // Auto-login after registration
      await Api.auth.login({ email, password });
      const user = await Api.auth.me();
      window._currentUser = user;
      try {
        localStorage.setItem('user', JSON.stringify(user));
      } catch (_) {}
      window.location.href = getDefaultPathForRole(user.role);
    } catch (err) {
      showError(form, err.detail || "Registration failed.");
    } finally {
      hideSpinner(form);
    }
  });
}

// ── Logout ────────────────────────────────────────────────────────────────────
async function logout() {
  try {
    try {
      localStorage.removeItem('user');
    } catch (_) {}
    await Api.auth.logout();
  } finally {
    window.location.href = "/pages/login.html";
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function showError(container, message) {
  let alert = container.querySelector(".alert-danger");
  if (!alert) {
    alert = document.createElement("div");
    alert.className = "alert alert-danger mt-3";
    container.prepend(alert);
  }
  alert.textContent = message;
}

function clearErrors(container) {
  container.querySelectorAll(".alert-danger").forEach(el => el.remove());
}

function showSpinner(container) {
  const btn = container.querySelector("[type=submit]");
  if (btn) { btn.disabled = true; btn.dataset.original = btn.innerHTML; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Please wait…'; }
}

function hideSpinner(container) {
  const btn = container.querySelector("[type=submit]");
  if (btn && btn.dataset.original) { btn.disabled = false; btn.innerHTML = btn.dataset.original; }
}

window.logout = logout;

function populateNavbar(user) {
  if (!user) return;
  const name = user.full_name || user.email || "User";
  const role = user.role === 'admin' ? 'Administrator' : 'Instructor';
  const initials = name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'AG';

  const nameEl = document.getElementById("nav-username");
  if (nameEl) nameEl.textContent = name;

  const roleEl = document.getElementById("nav-userrole");
  if (roleEl) {
    roleEl.textContent = role;
    if (user.role === 'admin') {
      roleEl.className = 'badge bg-warning bg-opacity-25 text-warning';
    }
  }

  const avatarEl = document.getElementById("user-avatar-initials");
  if (avatarEl) avatarEl.textContent = initials;

  const dropNameEl = document.getElementById("dropdown-user-name");
  if (dropNameEl) dropNameEl.textContent = name;

  const dropRoleEl = document.getElementById("dropdown-user-role");
  if (dropRoleEl) dropRoleEl.textContent = role;

  const dropAdminItem = document.getElementById("dropdown-admin-item");
  if (dropAdminItem) {
    dropAdminItem.style.display = user.role === 'admin' ? 'block' : 'none';
  }
}

function isAuthorizedForPage(page, role) {
  const allowedRoles = ROLE_PAGE_REQUIREMENTS[page];
  if (!allowedRoles) return true;
  return allowedRoles.includes(role);
}

function redirectByRole(role) {
  window.location.href = getDefaultPathForRole(role);
}

function getDefaultPathForRole(role) {
  return role === "admin" ? "/pages/admin.html" : "/pages/dashboard.html";
}

function getSafeNextPath() {
  const next = new URLSearchParams(window.location.search).get("next");
  if (!next) return null;
  // Prevent open redirects: only allow in-app absolute paths.
  if (!next.startsWith("/") || next.startsWith("//")) return null;
  // Prevent circular redirects back to authentication endpoints
  if (next.includes("login.html") || next.includes("register.html")) return null;
  return next;
}
