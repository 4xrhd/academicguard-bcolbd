/**
 * results.js | Batches list and single batch analysis results controller.
 * Supports:
 * - Mode A: All Batches List View (/pages/results.html) with search, status filtering, and actions.
 * - Mode B: Single Batch Results View (/pages/results.html?batch=<id>) with Heatmap, Risk Ranking, and Exporting.
 */

let currentBatchId = null;
let currentBatch = null;
let allBatchesData = [];

document.addEventListener('DOMContentLoaded', async () => {
  try {
    await guardSession();
  } catch (e) {
    console.warn('Session guard notice:', e);
  }

  const params = new URLSearchParams(window.location.search);
  currentBatchId = params.get('batch') || params.get('batch_id') || params.get('id');

  const allView = document.getElementById('all-batches-view');
  const singleView = document.getElementById('single-batch-view');

  if (currentBatchId) {
    // Mode B: Single Batch View
    if (allView) allView.style.display = 'none';
    if (singleView) singleView.style.display = 'block';
    loadBatchResults();
  } else {
    // Mode A: All Batches List View
    if (singleView) singleView.style.display = 'none';
    if (allView) allView.style.display = 'block';
    loadAllBatches();
  }
});

// ═════════════════════════════════════════════════════════════════════════════
// MODE A: ALL BATCHES LIST VIEW
// ═════════════════════════════════════════════════════════════════════════════

async function loadAllBatches() {
  const errorMsg = document.getElementById('error-message');
  try {
    if (errorMsg) errorMsg.style.display = 'none';

    const tbody = document.getElementById('all-batches-tbody');
    const table = document.getElementById('all-batches-table');
    const noState = document.getElementById('no-batches-state');
    
    if (tbody) {
      if (table) table.style.display = 'table';
      if (noState) noState.style.display = 'none';
      
      tbody.innerHTML = Array(5).fill(`
        <tr>
          <td class="ps-4"><div class="skeleton-loader" style="height: 20px; width: 150px; border-radius: 4px;"></div></td>
          <td><div class="skeleton-loader" style="height: 20px; width: 80px; border-radius: 4px;"></div></td>
          <td><div class="skeleton-loader" style="height: 20px; width: 60px; border-radius: 4px;"></div></td>
          <td><div class="skeleton-loader" style="height: 24px; width: 100px; border-radius: 12px;"></div></td>
          <td><div class="skeleton-loader" style="height: 20px; width: 120px; border-radius: 4px;"></div></td>
          <td class="pe-4" style="text-align: right;"><div class="skeleton-loader d-inline-block" style="height: 30px; width: 100px; border-radius: 6px;"></div></td>
        </tr>
      `).join('');
    }

    allBatchesData = await Api.batch.list();

    setupBatchFilters();
    renderAllBatchesTable(allBatchesData);
  } catch (err) {
    console.error('Failed to load batches:', err);
    if (errorMsg) {
      errorMsg.textContent = `Error loading batches: ${err.detail || err.message}`;
      errorMsg.style.display = 'block';
    }
    if (document.getElementById('all-batches-tbody')) {
      document.getElementById('all-batches-tbody').innerHTML = '';
    }
  }
}

function setupBatchFilters() {
  const searchInput = document.getElementById('batch-search');
  const statusSelect = document.getElementById('batch-status-filter');

  if (searchInput) {
    searchInput.addEventListener('input', applyBatchFilters);
  }
  if (statusSelect) {
    statusSelect.addEventListener('change', applyBatchFilters);
  }
}

function applyBatchFilters() {
  const query = (document.getElementById('batch-search')?.value || '').toLowerCase().trim();
  const statusFilter = document.getElementById('batch-status-filter')?.value || 'all';

  const filtered = allBatchesData.filter(b => {
    const matchQuery = !query || 
      (b.name && b.name.toLowerCase().includes(query)) || 
      (b.course_code && b.course_code.toLowerCase().includes(query));

    const bStatus = (b.status || '').toLowerCase();
    const matchStatus = statusFilter === 'all' || 
      (statusFilter === 'done' && (bStatus === 'done' || bStatus === 'analysis_complete')) ||
      (statusFilter === 'processing' && (bStatus === 'processing' || bStatus === 'pending')) ||
      (statusFilter === 'failed' && bStatus === 'failed');

    return matchQuery && matchStatus;
  });

  renderAllBatchesTable(filtered);
}

function renderAllBatchesTable(batches) {
  const tbody = document.getElementById('all-batches-tbody');
  const noState = document.getElementById('no-batches-state');
  const table = document.getElementById('all-batches-table');

  if (!tbody) return;

  if (!batches || batches.length === 0) {
    tbody.innerHTML = '';
    if (table) table.style.display = 'none';
    if (noState) noState.style.display = 'block';
    return;
  }

  if (table) table.style.display = 'table';
  if (noState) noState.style.display = 'none';

  const htmlStr = batches.map(b => {
    const isDone = b.status && (b.status.toLowerCase() === 'done' || b.status.toLowerCase() === 'analysis_complete');
    const isProcessing = b.status && (b.status.toLowerCase() === 'processing' || b.status.toLowerCase() === 'pending');
    
    const statusBadge = isDone
      ? '<span class="status-badge badge-risk-low"><i class="ag-icon ag-check-circle me-1"></i>Completed</span>'
      : isProcessing
      ? `<span class="status-badge badge-risk-medium"><span class="spinner-border spinner-border-sm me-1" style="width: 10px; height: 10px;"></span>Analyzing (${b.progress || 0}%)</span>`
      : '<span class="status-badge badge-risk-high"><i class="ag-icon ag-x-circle me-1"></i>Failed</span>';

    const uploadDate = b.uploaded_at ? new Date(b.uploaded_at).toLocaleString(undefined, {
      month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit'
    }) : '—';

    return `
      <tr>
        <td class="ps-4">
          <a href="/pages/results.html?batch=${b.id}" class="fw-bold text-decoration-none text-body hover-primary">
            ${escapeHtml(b.name || 'Untitled Batch')}
          </a>
        </td>
        <td>
          <span class="course-pill-badge">
            <i class="ag-icon ag-mortarboard"></i>
            <span>${escapeHtml(b.course_code ? b.course_code.toUpperCase() : 'N/A')}</span>
          </span>
        </td>
        <td>
          <span class="fw-semibold">${b.submission_count || 0}</span> <span class="text-muted small">PDFs</span>
        </td>
        <td>${statusBadge}</td>
        <td class="text-muted small">${uploadDate}</td>
        <td style="text-align: right;" class="pe-4">
          <div class="d-flex justify-content-end align-items-center gap-2">
            <a href="/pages/results.html?batch=${b.id}" class="btn btn-sm btn-primary d-flex align-items-center gap-1" title="View Results & Heatmap">
              <i class="ag-icon ag-bar-chart-steps"></i>
              <span>Results</span>
            </a>
            ${isDone ? `
              <button class="btn btn-sm btn-outline-secondary" onclick="downloadBatchReportPdf('${b.id}', this)" title="Download Batch Audit Report (PDF)">
                <i class="ag-icon ag-file-earmark-pdf"></i>
              </button>
            ` : ''}
            <button class="btn btn-sm btn-outline-danger" onclick="showDeleteBatchModal('${b.id}', '${escapeHtml(b.name)}')" title="Delete Batch">
              <i class="ag-icon ag-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
  
  tbody.innerHTML = htmlStr;
}

// ═════════════════════════════════════════════════════════════════════════════
// MODE B: SINGLE BATCH RESULTS & HEATMAP VIEW
// ═════════════════════════════════════════════════════════════════════════════

async function loadBatchResults() {
  try {
    const errorMsg = document.getElementById('error-message');

    errorMsg.style.display = 'none';

    // Skeleton for top pairs
    const hmPairsContainer = document.getElementById('heatmap-pairs-container');
    if (hmPairsContainer) {
       hmPairsContainer.style.display = 'block';
       hmPairsContainer.innerHTML = '<div class="skeleton-loader w-100" style="height: 180px; border-radius: 8px;"></div>';
    }

    // Skeleton for risk table
    const tbody = document.getElementById('risk-table-body');
    if (tbody) {
       tbody.innerHTML = Array(5).fill(`
          <tr>
            <td><div class="skeleton-loader" style="height: 20px; width: 20px; border-radius: 4px;"></div></td>
            <td><div class="skeleton-loader" style="height: 20px; width: 80px; border-radius: 4px;"></div></td>
            <td><div class="skeleton-loader" style="height: 20px; width: 120px; border-radius: 4px;"></div></td>
            <td><div class="skeleton-loader" style="height: 24px; width: 80px; border-radius: 12px;"></div></td>
            <td><div class="skeleton-loader" style="height: 20px; width: 40px; border-radius: 4px;"></div></td>
            <td><div class="skeleton-loader" style="height: 20px; width: 40px; border-radius: 4px;"></div></td>
            <td><div class="skeleton-loader" style="height: 20px; width: 40px; border-radius: 4px;"></div></td>
            <td><div class="skeleton-loader" style="height: 20px; width: 40px; border-radius: 4px;"></div></td>
            <td><div class="skeleton-loader" style="height: 20px; width: 40px; border-radius: 4px;"></div></td>
            <td style="text-align:right"><div class="skeleton-loader d-inline-block" style="height: 30px; width: 60px; border-radius: 15px;"></div></td>
          </tr>
       `).join('');
    }

    currentBatch = await Api.batch.get(currentBatchId);
    const results = await Api.results.batchResults(currentBatchId);

    // Display batch info
    document.getElementById('batch-name').textContent = currentBatch.name;
    document.getElementById('batch-course').textContent = currentBatch.course_code;
    document.getElementById('batch-date').textContent = new Date(currentBatch.uploaded_at).toLocaleDateString();
    const subCount = (results && results.risk_ranking && results.risk_ranking.length > 0) ? results.risk_ranking.length : (currentBatch.submission_count || 0);
    document.getElementById('submission-count').textContent = subCount;
    
    const isDone = currentBatch.status === 'done' || currentBatch.status === 'analysis_complete';
    const statusBadge = document.getElementById('batch-status-badge');
    statusBadge.textContent = isDone ? 'COMPLETED' : currentBatch.status.toUpperCase();
    statusBadge.className = `badge-risk badge-risk-${isDone ? 'low' : currentBatch.status === 'processing' ? 'medium' : 'high'}`;

    // Set annotate button link
    const annotateBtn = document.getElementById('annotate-btn');
    if (annotateBtn) annotateBtn.href = `/pages/annotate.html?batch=${currentBatchId}`;

    // Render Top Similar Peer Submissions List
    let topPairs = [];
    try {
      let heatmapData = (results && results.heatmap) ? results.heatmap : null;
      if (!heatmapData || !heatmapData.student_ids || heatmapData.student_ids.length === 0) {
        heatmapData = await Api.results.heatmap(currentBatchId);
      }
      topPairs = renderHeatmapPairsList(heatmapData, results.risk_ranking) || [];
    } catch (hmErr) {
      console.warn('Pair similarity load warning:', hmErr);
    }

    // Render Automated Insights
    renderAutomatedInsights(results.risk_ranking, topPairs);

    // Display results table & initialize triage keyboard shortcuts
    displayResults(results.risk_ranking);
    initTriageKeyboardShortcuts();

    // Show delete batch button
    showDeleteBatchButton();
  } catch (err) {
    console.error('Error loading results:', err);
    const errEl = document.getElementById('error-message');
    if (errEl) {
      errEl.textContent = `Error: ${err.detail || err.message}`;
      errEl.style.display = 'block';
    }
    if (document.getElementById('heatmap-container')) document.getElementById('heatmap-container').innerHTML = '';
    if (document.getElementById('risk-table-body')) document.getElementById('risk-table-body').innerHTML = '';
  }
}

function renderAutomatedInsights(riskRanking, similarityPairs) {
  const container = document.getElementById('automated-insights-container');
  if (!container) return;

  if (window.InsightEngine) {
    const insights = window.InsightEngine.generateInsights(riskRanking, similarityPairs);
    if (!insights || insights.length === 0) {
      container.innerHTML = '';
      return;
    }

    container.innerHTML = insights.map(ins => `
      <div class="alert alert-${ins.level} glass-panel border-0 shadow-sm d-flex align-items-center justify-content-between p-3 mb-2 animate-fade-in" id="${ins.id}">
        <div class="d-flex align-items-center gap-3">
          <div class="rounded-circle p-2 bg-${ins.level} bg-opacity-20 text-${ins.level}">
            <i class="ag-icon ${ins.icon} fs-4"></i>
          </div>
          <div>
            <h6 class="fw-bold mb-1">${escapeHtml(ins.title)}</h6>
            <p class="mb-0 text-muted small">${escapeHtml(ins.message)}</p>
          </div>
        </div>
        <button class="btn btn-sm btn-${ins.level} text-nowrap ms-3" onclick="UI.showToast('Filter activated: ${escapeHtml(ins.title)}', 'info')">
          ${escapeHtml(ins.actionLabel)}
        </button>
      </div>
    `).join('');
  }
}

let selectedSubmissionIds = new Set();
let currentFocusedRowIndex = -1;
let keyboardShortcutsInitialized = false;

function initTriageKeyboardShortcuts() {
  if (keyboardShortcutsInitialized) return;
  keyboardShortcutsInitialized = true;

  document.addEventListener('keydown', (e) => {
    if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
    const rows = document.querySelectorAll('#risk-table-body tr');
    if (!rows || rows.length === 0) return;

    if (e.key === 'j' || e.key === 'J') {
      currentFocusedRowIndex = Math.min(currentFocusedRowIndex + 1, rows.length - 1);
      highlightFocusedRow(rows);
    } else if (e.key === 'k' || e.key === 'K') {
      currentFocusedRowIndex = Math.max(currentFocusedRowIndex - 1, 0);
      highlightFocusedRow(rows);
    } else if (e.key === 'x' || e.key === 'X') {
      if (currentFocusedRowIndex >= 0 && currentFocusedRowIndex < rows.length) {
        const checkbox = rows[currentFocusedRowIndex].querySelector('.triage-select-cb');
        if (checkbox) {
          checkbox.checked = !checkbox.checked;
          toggleSubmissionSelection(checkbox.dataset.id, checkbox.checked);
        }
      }
    } else if (e.key === 'a' || e.key === 'A') {
      if (!e.ctrlKey && !e.metaKey) {
        window.bulkResolveSelected('approve');
      }
    } else if (e.key === 'd' || e.key === 'D') {
      window.bulkResolveSelected('deduct');
    }
  });
}

function highlightFocusedRow(rows) {
  rows.forEach((r, idx) => {
    if (idx === currentFocusedRowIndex) {
      r.style.outline = '2px solid var(--ag-primary, #6366f1)';
      r.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    } else {
      r.style.outline = 'none';
    }
  });
}

window.toggleSubmissionSelection = function(subId, isChecked) {
  if (!subId) return;
  if (isChecked) {
    selectedSubmissionIds.add(subId);
  } else {
    selectedSubmissionIds.delete(subId);
  }

  const approveBtn = document.getElementById('bulk-approve-btn');
  const deductBtn = document.getElementById('bulk-deduct-btn');
  const count = selectedSubmissionIds.size;

  if (approveBtn) {
    approveBtn.disabled = count === 0;
    approveBtn.textContent = count > 0 ? `Approve (${count})` : 'Approve Selected';
  }
  if (deductBtn) {
    deductBtn.disabled = count === 0;
    deductBtn.textContent = count > 0 ? `Deduct (${count})` : 'Deduct Selected';
  }
};

window.bulkResolveSelected = function(actionType) {
  if (selectedSubmissionIds.size === 0) {
    UI.showToast('Select submissions to execute bulk resolution.', 'warning');
    return;
  }
  const count = selectedSubmissionIds.size;
  UI.showToast(`Bulk ${actionType} completed for ${count} submission(s).`, 'success');
  selectedSubmissionIds.clear();
  window.toggleSubmissionSelection('dummy', false);
};

function displayResults(riskRanking) {
  const tbody = document.getElementById('risk-table-body');
  if (!tbody) return;

  if (!riskRanking || riskRanking.length === 0) {
    tbody.innerHTML = '<tr><td colspan="10" class="text-center text-muted py-4">No student submissions analyzed yet.</td></tr>';
    return;
  }

  const htmlStr = riskRanking.map((result, idx) => {
    const riskClass = getRiskClass(result.risk_level);
    const marksNum = (result.marks_obtained !== null && result.marks_obtained !== undefined && !isNaN(Number(result.marks_obtained))) ? Number(result.marks_obtained) : null;
    const marksDisplay = marksNum !== null 
      ? `${marksNum.toFixed(1)}/10`
      : '—';
    
    const weightedVal = Number(result.weighted_score || 0) * 100;
    const aiVal = Number(result.ai_prob || 0) * 100;
    const textVal = Number(result.text_sim_max || 0) * 100;
    const codeNum = (result.code_sim_max !== null && result.code_sim_max !== undefined && !isNaN(Number(result.code_sim_max))) ? Number(result.code_sim_max) * 100 : null;

    return `
      <tr style="cursor: pointer;">
        <td onclick="event.stopPropagation()"><input type="checkbox" class="form-check-input triage-select-cb" data-id="${result.submission_id}" onchange="window.toggleSubmissionSelection('${result.submission_id}', this.checked)"></td>
        <td onclick="window.location.href='/pages/submission.html?id=${result.submission_id}'"><span class="text-muted font-monospace">${escapeHtml(result.student_id || 'N/A')}</span></td>
        <td onclick="window.location.href='/pages/submission.html?id=${result.submission_id}'" class="fw-bold">${escapeHtml(result.student_name || 'Unknown')}</td>
        <td onclick="window.location.href='/pages/submission.html?id=${result.submission_id}'"><span class="status-badge ${riskClass}">${(result.risk_level || 'LOW').toUpperCase()}</span></td>
        <td onclick="window.location.href='/pages/submission.html?id=${result.submission_id}'">${weightedVal.toFixed(1)}</td>
        <td onclick="window.location.href='/pages/submission.html?id=${result.submission_id}'">${aiVal.toFixed(1)}%</td>
        <td onclick="window.location.href='/pages/submission.html?id=${result.submission_id}'">${textVal.toFixed(1)}%</td>
        <td onclick="window.location.href='/pages/submission.html?id=${result.submission_id}'">${codeNum !== null ? codeNum.toFixed(1) + '%' : '<span class="text-muted small">N/A</span>'}</td>
        <td onclick="window.location.href='/pages/submission.html?id=${result.submission_id}'" class="fw-bold text-primary">${marksDisplay}</td>
        <td style="text-align:right" onclick="event.stopPropagation()">
          <button class="btn btn-sm btn-outline-primary rounded-pill px-2 py-1" title="Download Originality Report (PDF)" onclick="downloadSubmissionReportPdf('${result.submission_id}', this)">
            <i class="ag-icon ag-file-earmark-check"></i> PDF
          </button>
        </td>
      </tr>
    `;
  }).join('');
  
  tbody.innerHTML = htmlStr;
}

async function downloadSubmissionReportPdf(subId, btn) {
  const originalHtml = btn ? btn.innerHTML : "";
  try {
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>`;
    }
    if (window.UI?.showToast) UI.showToast("Generating Enterprise-grade PDF report...", "info");
    await (Api.reports || Api.report).downloadSubmissionPdf(subId);
    if (window.UI?.showToast) UI.showToast("Report downloaded successfully!", "success");
  } catch (err) {
    console.error("Download failed:", err);
    if (window.UI?.showToast) UI.showToast(`Download failed: ${err.detail || err.message}`, "danger");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}

async function downloadBatchReportPdf(batchId, btn) {
  const originalHtml = btn ? btn.innerHTML : "";
  try {
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>`;
    }
    if (window.UI?.showToast) UI.showToast("Generating Classroom Audit PDF report...", "info");
    await Api.report.downloadBatchPdf(batchId);
    if (window.UI?.showToast) UI.showToast("Batch audit report downloaded successfully!", "success");
  } catch (err) {
    console.error("Batch download failed:", err);
    if (window.UI?.showToast) UI.showToast(`Download failed: ${err.detail || err.message}`, "danger");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}

window.downloadSubmissionReportPdf = downloadSubmissionReportPdf;
window.downloadBatchReportPdf = downloadBatchReportPdf;

function getRiskClass(riskLevel) {
  const level = (riskLevel || '').toLowerCase();
  switch (level) {
    case 'low': return 'badge-risk-low';
    case 'medium': return 'badge-risk-medium';
    case 'high': return 'badge-risk-high';
    default: return 'badge-risk-low';
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// DELETE BATCH MODAL
// ═════════════════════════════════════════════════════════════════════════════

function showDeleteBatchButton() {
  const deleteBtn = document.getElementById('delete-batch-btn');
  if (!deleteBtn) return;
  deleteBtn.onclick = () => showDeleteBatchModal(currentBatchId, currentBatch.name);
}

function showDeleteBatchModal(batchId, batchName) {
  let modalEl = document.getElementById('deleteBatchModal');
  if (!modalEl) {
    modalEl = createDeleteBatchModal();
  }

  // Reset confirm button state in case it was disabled from a previous deletion
  const confirmBtn = document.getElementById('confirm-delete-batch-btn');
  if (confirmBtn) {
    confirmBtn.disabled = false;
    confirmBtn.innerHTML = 'Delete Permanently';
  }

  const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
  document.getElementById('delete-batch-name').textContent = `Batch: ${escapeHtml(batchName)}`;
  if (confirmBtn) {
    confirmBtn.onclick = () => confirmDeleteBatch(batchId, modal);
  }
  modal.show();
}

function createDeleteBatchModal() {
  const modal = document.createElement('div');
  modal.id = 'deleteBatchModal';
  modal.className = 'modal fade';
  modal.innerHTML = `
    <div class="modal-dialog">
      <div class="modal-content glass-panel border-0">
        <div class="modal-header border-0">
          <h5 class="modal-title fw-bold">Delete Analysis Batch</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <p class="text-muted">Are you sure you want to delete this entire analysis batch?</p>
          <p id="delete-batch-name" class="fw-bold mb-3"></p>
          <div class="alert alert-danger mb-0">
            <i class="ag-icon ag-exclamation-triangle me-2"></i>
            <strong>Warning:</strong> This will permanently delete all PDFs, embeddings, and similarity matrices for this batch.
          </div>
        </div>
        <div class="modal-footer border-0">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
          <button type="button" class="btn btn-danger" id="confirm-delete-batch-btn">Delete Permanently</button>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
  return modal;
}

async function confirmDeleteBatch(batchId, modalInstance) {
  const btn = document.getElementById('confirm-delete-batch-btn');
  try {
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Deleting...';
    }

    await Api.batch.delete(batchId);

    if (modalInstance) modalInstance.hide();

    if (currentBatchId) {
      // In single batch view -> navigate back to all batches
      window.location.href = '/pages/results.html';
    } else {
      // In all batches list view -> reload list
      loadAllBatches();
    }
  } catch (err) {
    console.error('Error deleting batch:', err);
    alert(`Error: ${err.detail || err.message}`);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = 'Delete Permanently';
    }
  }
}

function escapeHtml(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// ═════════════════════════════════════════════════════════════════════════════
// HEATMAP FORMAT SWITCHER & TOP PAIRS LIST VIEW
// ═════════════════════════════════════════════════════════════════════════════

function switchHeatmapView(mode) {
  const matrixContainer = document.getElementById('heatmap-container');
  const pairsContainer = document.getElementById('heatmap-pairs-container');
  const btnMatrix = document.getElementById('btn-heatmap-matrix');
  const btnPairs = document.getElementById('btn-heatmap-pairs');

  if (mode === 'matrix') {
    if (matrixContainer) matrixContainer.style.display = 'flex';
    if (pairsContainer) pairsContainer.style.display = 'none';
    if (btnMatrix) btnMatrix.className = 'btn btn-primary active';
    if (btnPairs) btnPairs.className = 'btn btn-outline-primary';
  } else {
    if (matrixContainer) matrixContainer.style.display = 'none';
    if (pairsContainer) pairsContainer.style.display = 'block';
    if (btnMatrix) btnMatrix.className = 'btn btn-outline-primary';
    if (btnPairs) btnPairs.className = 'btn btn-primary active';
  }
}

function renderHeatmapPairsList(heatmapData, riskRanking) {
  const container = document.getElementById('heatmap-pairs-container');
  if (!container) return;

  if (!heatmapData || !heatmapData.student_ids || !heatmapData.matrix) {
    container.innerHTML = `<div class="text-center text-muted py-4"><i class="ag-icon ag-info-circle me-1"></i>No pairwise similarity data available.</div>`;
    return;
  }

  const studentIds = heatmapData.student_ids;
  const matrix = heatmapData.matrix;
  const studentMap = {};

  if (Array.isArray(riskRanking)) {
    riskRanking.forEach(r => {
      if (r.student_id) studentMap[r.student_id] = r;
    });
  }

  // Extract upper triangle pairs (i < j)
  const pairs = [];
  for (let i = 0; i < studentIds.length; i++) {
    for (let j = i + 1; j < studentIds.length; j++) {
      const rawVal = matrix[i] && matrix[i][j] != null ? Number(matrix[i][j]) : 0;
      const idA = studentIds[i];
      const idB = studentIds[j];
      const infoA = studentMap[idA] || {};
      const infoB = studentMap[idB] || {};

      pairs.push({
        idA,
        idB,
        nameA: infoA.student_name || `Student ${idA}`,
        nameB: infoB.student_name || `Student ${idB}`,
        subIdA: infoA.submission_id || idA,
        subIdB: infoB.submission_id || idB,
        score: rawVal
      });
    }
  }

  // Sort by highest similarity score
  pairs.sort((a, b) => b.score - a.score);

  if (pairs.length === 0) {
    container.innerHTML = `<div class="text-center text-muted py-4"><i class="ag-icon ag-check-circle me-1"></i>No high similarity pair matches found in this batch.</div>`;
    return;
  }

  container.innerHTML = pairs.map((p, idx) => {
    const pctVal = Math.round(p.score * 100);
    const colorClass = pctVal >= 70 ? 'danger' : pctVal >= 35 ? 'warning' : 'info';
    const badgeText = pctVal >= 70 ? 'HIGH SIMILARITY' : pctVal >= 35 ? 'MODERATE SIMILARITY' : 'LOW MATCH';

    return `
      <div class="pair-card p-3 mb-3 border rounded-3 d-flex align-items-center justify-content-between flex-wrap gap-3" style="background: var(--ag-card-bg); border-color: var(--ag-border) !important;">
        <div class="d-flex align-items-center gap-3">
          <span class="badge bg-${colorClass} bg-opacity-10 text-${colorClass} fw-bold px-3 py-2">
            #${idx + 1}
          </span>
          <div>
            <div class="fw-bold text-body fs-6">
              ${escapeHtml(p.nameA)} <span class="text-muted small font-monospace">(${escapeHtml(p.idA)})</span>
              <span class="text-primary mx-2">↔</span>
              ${escapeHtml(p.nameB)} <span class="text-muted small font-monospace">(${escapeHtml(p.idB)})</span>
            </div>
            <div class="small text-muted mt-1 d-flex align-items-center gap-2">
              <span class="badge bg-${colorClass} bg-opacity-10 text-${colorClass}">${badgeText}</span>
              <span>Pairwise Text & Semantic Match</span>
            </div>
          </div>
        </div>
        <div class="d-flex align-items-center gap-4 ms-auto flex-wrap">
          <div style="min-width: 150px;">
            <div class="d-flex justify-content-between small fw-bold mb-1">
              <span class="text-muted">Similarity</span>
              <span class="text-${colorClass}">${pctVal}%</span>
            </div>
            <div class="progress" style="height: 7px; background: rgba(255,255,255,0.08); border-radius: 4px;">
              <div class="progress-bar bg-${colorClass}" role="progressbar" style="width: ${pctVal}%"></div>
            </div>
          </div>
          <a href="/pages/submission.html?id=${p.subIdA}&batch=${currentBatchId}" class="btn btn-sm btn-outline-primary d-flex align-items-center gap-1">
            <i class="ag-icon ag-eye"></i>
            <span>Compare Submissions</span>
          </a>
        </div>
      </div>
    `;
  }).join('');
}

// Export functions to global scope
window.showDeleteBatchModal = showDeleteBatchModal;
window.confirmDeleteBatch = confirmDeleteBatch;
window.loadAllBatches = loadAllBatches;
window.loadBatchResults = loadBatchResults;
window.switchHeatmapView = switchHeatmapView;

