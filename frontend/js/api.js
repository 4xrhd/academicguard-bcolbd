/**
 * api.js | Fetch wrapper with JWT cookie auth and unified error handling.
 * All client→server communication uses HTTPS; tokens transmitted via HttpOnly cookies.
 * Section 4.4: REST API uses JSON for all request/response bodies except file uploads.
 */

// Detect environment and set API base
const IS_LOCALHOST = [
  "localhost",
  "127.0.0.1",
  "0.0.0.0",
  ""
].includes(window.location.hostname);

const API_BASE = IS_LOCALHOST && window.location.port !== "8000" && window.location.port !== "" 
  ? `http://${window.location.hostname === "0.0.0.0" || !window.location.hostname ? "127.0.0.1" : window.location.hostname}:8000/api/v1` 
  : "/api/v1";

/**
 * Core fetch wrapper.
 * @param {string} path   - API path (e.g. "/auth/login")
 * @param {RequestInit} options
 * @returns {Promise<any>} Parsed JSON response
 */
async function apiFetch(path, options = {}, hasRetried = false) {
  const url = `${path.startsWith('http') ? '' : API_BASE}${path}`;

  const defaults = {
    credentials: "include",   // Send HttpOnly cookies automatically
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  };

  // Don't set Content-Type for FormData (let browser set multipart boundary)
  if (options.body instanceof FormData) {
    delete defaults.headers["Content-Type"];
  }

  try {
    const response = await fetch(url, { ...defaults, ...options });

    if (response.status === 401) {
      const isAuthCheck = path.includes("/auth/me") || path.includes("/auth/refresh") || path.includes("/auth/login");
      // Try token refresh once before redirecting to login
      const refreshed = !hasRetried && !isAuthCheck && await _tryRefresh();
      if (refreshed) {
        return apiFetch(path, options, true);
      }
      // Stay on public auth pages when unauthenticated (login + register)
      const p = window.location.pathname;
      if (!isAuthCheck && !p.endsWith("login.html") && !p.endsWith("register.html")) {
        const next = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.href = `/pages/login.html?next=${next}`;
      }
      throw new ApiError(401, "Session expired. Please sign in again.");
    }

    if (response.status === 403) {
      throw new ApiError(403, "Access denied.");
    }

    if (response.status >= 502 && response.status <= 504 && !hasRetried) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      return apiFetch(path, options, true);
    }

    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const text = await response.text();
        try {
          const body = JSON.parse(text);
          if (Array.isArray(body.detail)) {
            // FastAPI validation errors (422)
            detail = body.detail.map(e => e.msg).join(", ");
          } else if (body.detail) {
            detail = body.detail;
          } else if (body.message) {
            detail = body.message;
          }
        } catch (_) {
          if (text && text.length < 200) {
            detail = text;
          }
        }
      } catch (_) {}
      throw new ApiError(response.status, detail);
    }

    // 204 No Content
    if (response.status === 204) return null;

    return response.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (!hasRetried && (options.method === 'GET' || !options.method)) {
      await new Promise(resolve => setTimeout(resolve, 1200));
      return apiFetch(path, options, true);
    }
    console.error("Fetch error:", err);
    console.error("Attempted URL:", url);
    console.error("API_BASE:", API_BASE);
    throw new ApiError(0, "Network error or server unreachable.");
  }
}

async function _tryRefresh() {
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    return res.ok;
  } catch (_) {
    return false;
  }
}

class ApiError extends Error {
  constructor(status, detail) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

// ── Auth ──────────────────────────────────────────────────────────────────────
let _mePromise = null;
let _cachedUser = null;
let _cachedUserTime = 0;

const authApi = {
  register: (data) => apiFetch("/auth/register", { method: "POST", body: JSON.stringify(data) }),
  login: (data) => {
    _cachedUser = null;
    _mePromise = null;
    return apiFetch("/auth/login", { method: "POST", body: JSON.stringify(data) });
  },
  logout: () => {
    _cachedUser = null;
    _mePromise = null;
    return apiFetch("/auth/logout", { method: "POST" });
  },
  me: (force = false) => {
    const now = Date.now();
    if (!force && _cachedUser && (now - _cachedUserTime < 30000)) {
      return Promise.resolve(_cachedUser);
    }
    if (_mePromise && !force) return _mePromise;
    _mePromise = apiFetch("/auth/me")
      .then(user => {
        _cachedUser = user;
        _cachedUserTime = Date.now();
        _mePromise = null;
        return user;
      })
      .catch(err => {
        _mePromise = null;
        _cachedUser = null;
        throw err;
      });
    return _mePromise;
  },
};

// ── Batches ───────────────────────────────────────────────────────────────────
const batchApi = {
  list:   ()              => apiFetch("/batches"),
  get:    (id)            => apiFetch(`/batches/${id}`),
  status: (id)            => apiFetch(`/batches/${id}/status`),
  delete: (id)            => apiFetch(`/batches/${id}`, { method: "DELETE" }),
  upload: (formData)      => apiFetch("/batches/upload", { method: "POST", body: formData }),
  setMarkingConfig: (batchId, config) => apiFetch(`/batches/${batchId}/marking-config`, { method: "POST", body: JSON.stringify(config) }),
  getMarkingConfig: (batchId) => apiFetch(`/batches/${batchId}/marking-config`),
};

// ── Results ───────────────────────────────────────────────────────────────────
const resultsApi = {
  batchResults:      (batchId) => apiFetch(`/batches/${batchId}/results`),
  heatmap:           (batchId) => apiFetch(`/batches/${batchId}/heatmap`),
  submissionDetail:  (subId)   => apiFetch(`/submissions/${subId}`),
  submissionPairs:   (subId)   => apiFetch(`/submissions/${subId}/pairs`),
};

/**
 * Authenticated binary blob downloader.
 * Guarantees HttpOnly JWT cookie transmission, handles auto-refresh,
 * extracts server-suggested filename from Content-Disposition, and triggers native download/preview.
 */
async function downloadBlob(path, defaultFilename = "report.pdf", openInNewTab = false) {
  const url = `${path.startsWith('http') ? '' : API_BASE}${path}`;
  const response = await fetch(url, {
    method: "GET",
    credentials: "include",
  });

  if (response.status === 401) {
    const refreshed = await _tryRefresh();
    if (refreshed) {
      return downloadBlob(path, defaultFilename, openInNewTab);
    }
    throw new ApiError(401, "Session expired. Please sign in again.");
  }

  if (!response.ok) {
    let errorDetail = "Failed to download file.";
    try {
      const json = await response.json();
      errorDetail = json.detail || errorDetail;
    } catch (e) {
      errorDetail = `Server error (HTTP ${response.status})`;
    }
    throw new ApiError(response.status, errorDetail);
  }

  const blob = await response.blob();
  const blobUrl = window.URL.createObjectURL(blob);

  if (openInNewTab) {
    window.open(blobUrl, "_blank");
    setTimeout(() => window.URL.revokeObjectURL(blobUrl), 60000);
    return blobUrl;
  }

  let filename = defaultFilename;
  const disposition = response.headers.get("Content-Disposition");
  if (disposition && disposition.includes("filename=")) {
    const match = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
    if (match && match[1]) {
      filename = match[1].replace(/['"]/g, '').trim();
    }
  }

  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => window.URL.revokeObjectURL(blobUrl), 10000);
  return filename;
}

// ── Reports ───────────────────────────────────────────────────────────────────
const reportApi = {
  pdf:           (batchId) => `${API_BASE}/batches/${batchId}/reports/pdf`,
  batchPdf:      (batchId) => `${API_BASE}/batches/${batchId}/reports/pdf`,
  submissionPdf: (subId)   => `${API_BASE}/submissions/${subId}/reports/pdf`,
  excel:         (batchId) => `${API_BASE}/batches/${batchId}/reports/excel`,
  csv:           (batchId) => `${API_BASE}/batches/${batchId}/reports/csv`,
  json:          (batchId) => `${API_BASE}/batches/${batchId}/reports/json`,

  // High-reliability authenticated download methods (Blob + HttpOnly Cookies + Auto-refresh)
  downloadSubmissionPdf: (subId, openInNewTab = false) => downloadBlob(`/submissions/${subId}/reports/pdf`, `originality_report_${subId}.pdf`, openInNewTab),
  downloadBatchPdf:      (batchId) => downloadBlob(`/batches/${batchId}/reports/pdf`, `batch_audit_report_${batchId}.pdf`),
  downloadBatchExcel:    (batchId) => downloadBlob(`/batches/${batchId}/reports/excel`, `integrity_report_${batchId}.xlsx`),
  downloadBatchCsv:      (batchId) => downloadBlob(`/batches/${batchId}/reports/csv`, `integrity_report_${batchId}.csv`),
  downloadBatchJson:     (batchId) => downloadBlob(`/batches/${batchId}/reports/json`, `integrity_report_${batchId}.json`),
  viewOriginalPdf:       (subId)   => downloadBlob(`/submissions/${subId}/pdf`, `submission_${subId}.pdf`, true),
};

// ── Admin ─────────────────────────────────────────────────────────────────────
const adminApi = {
  listUsers:      ()       => apiFetch("/admin/users"),
  deactivateUser: (userId) => apiFetch(`/admin/users/${userId}/deactivate`, { method: "POST" }),
  reactivateUser: (userId) => apiFetch(`/admin/users/${userId}/reactivate`, { method: "POST" }),
  deleteUser:     (userId) => apiFetch(`/admin/users/${userId}`, { method: "DELETE" }),
  changeUserRole: (userId, newRole) => apiFetch(`/admin/users/${userId}/change-role?new_role=${newRole}`, { method: "POST" }),
  auditLogs:      (params) => apiFetch("/admin/audit-logs?" + new URLSearchParams(params)),
};

// ── Marking Configurations ────────────────────────────────────────────────────
const markingApi = {
  listConfigs:   ()              => apiFetch("/marking/configs"),
  getConfig:    (id)            => apiFetch(`/marking/configs/${id}`),
  createConfig: (data)          => apiFetch("/marking/configs", { method: "POST", body: JSON.stringify(data) }),
  updateConfig: (id, data)      => apiFetch(`/marking/configs/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteConfig: (id)            => apiFetch(`/marking/configs/${id}`, { method: "DELETE" }),
};

// Export for use in other JS modules
window.Api = {
  auth: authApi,
  batch: batchApi,
  results: resultsApi,
  report: reportApi,
  reports: reportApi,
  admin: adminApi,
  marking: markingApi,
  // Generic helpers for annotation/training pages
  get:  (path)       => apiFetch(path),
  post: (path, data) => apiFetch(path, { method: "POST", body: JSON.stringify(data) }),
  put:  (path, data) => apiFetch(path, { method: "PUT",  body: JSON.stringify(data) }),
};
window.ApiError = ApiError;
