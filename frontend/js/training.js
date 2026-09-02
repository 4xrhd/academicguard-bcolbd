/**
 * training.js | Model training dashboard logic.
 * Handles triggering auto-trainer and viewing job history / model metrics.
 */

let pollingInterval = null;

document.addEventListener("DOMContentLoaded", async () => {
  try {
    if (window.guardSession) {
      await guardSession();
    }
  } catch (e) {
    console.warn("Session guard notice:", e);
  }
  await loadDashboard();
});

async function loadDashboard() {
  try {
    await Promise.all([loadDataSummary(), loadHistory(), checkRunningTraining()]);
  } catch (err) {
    console.error("Dashboard load error:", err);
  }
}

async function loadDataSummary() {
  try {
    const stats = await Api.get("/training/data-summary");

    document.getElementById("total-annotations").textContent = stats.total_annotations;
    document.getElementById("human-count").textContent = stats.binary_distribution.human || 0;
    document.getElementById("ai-count").textContent = stats.binary_distribution.ai || 0;
    document.getElementById("min-required").textContent = stats.min_samples_required;

    // Class balance bars
    const total = (stats.binary_distribution.human || 0) + (stats.binary_distribution.ai || 0);
    if (total > 0) {
      const humanPct = (stats.binary_distribution.human / total * 100).toFixed(0);
      const aiPct = (stats.binary_distribution.ai / total * 100).toFixed(0);
      document.getElementById("human-bar").style.width = `${humanPct}%`;
      document.getElementById("ai-bar").style.width = `${aiPct}%`;
      const hpEl = document.getElementById("human-pct-label");
      if (hpEl) hpEl.textContent = `${humanPct}%`;
      const apEl = document.getElementById("ai-pct-label");
      if (apEl) apEl.textContent = `${aiPct}%`;
    }

    // Label detail pills
    const labelDetail = document.getElementById("label-detail");
    const meta = {
      human: { title: 'Human Written', icon: 'person-check', rgb: '16, 185, 129' },
      ai_generated: { title: 'AI Generated', icon: 'robot', rgb: '244, 63, 94' },
      mixed: { title: 'Mixed Synthetic', icon: 'shuffle', rgb: '139, 92, 246' },
      plagiarized: { title: 'Plagiarized Copy', icon: 'files', rgb: '245, 158, 11' }
    };

    labelDetail.innerHTML = Object.entries(stats.label_distribution).map(([label, count]) => {
      const cfg = meta[label] || {
        title: label.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        icon: 'tag',
        rgb: '99, 102, 241'
      };
      return `
        <div class="label-dist-pill" style="--chip-rgb: ${cfg.rgb};">
          <div class="label-pill-icon">
            <i class="ag-icon ag-${cfg.icon}"></i>
          </div>
          <span class="label-pill-name">${cfg.title}</span>
          <span class="label-pill-count">${count}</span>
        </div>
      `;
    }).join('');

    // Readiness
    const trainBtn = document.getElementById("train-btn");
    const hint = document.getElementById("train-hint");
    const badge = document.getElementById("readiness-badge");

    if (stats.ready_to_train) {
      trainBtn.disabled = false;
      hint.textContent = "✓ Sufficient data available. Click to start training.";
      hint.className = "text-success small mb-0 fw-bold";
      badge.textContent = "READY";
      badge.className = "badge bg-success bg-opacity-10 text-success";
    } else {
      trainBtn.disabled = true;
      const needed = stats.min_samples_required - stats.total_annotations;
      hint.textContent = `Need ${Math.max(0, needed)} more annotations (min ${stats.min_per_class_required} per class).`;
      hint.className = "text-muted small mb-0";
      badge.textContent = "NOT READY";
      badge.className = "badge bg-warning bg-opacity-10 text-warning";
    }
  } catch (err) {
    console.warn("Could not load data summary:", err);
  }
}

async function loadHistory() {
  try {
    const runs = await Api.get("/training/history");
    const tbody = document.getElementById("history-body");

    if (!runs || !runs.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8" class="text-center py-5">
            <div class="empty-state m-0 p-0 shadow-none border-0 bg-transparent">
              <div class="empty-state-icon mx-auto"><i class="ag-icon ag-activity"></i></div>
              <p class="mb-0 fw-bold">No training runs yet</p>
              <small class="text-muted">Start a new model training process to see history here.</small>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    // Update active model card from most recent active run
    const activeRun = runs.find(r => r.is_active);
    if (activeRun) {
      document.getElementById("active-model-badge").textContent = `v${new Date(activeRun.started_at).toISOString().slice(0,10)}`;
      document.getElementById("active-roc-auc").textContent = (activeRun.roc_auc != null && !isNaN(Number(activeRun.roc_auc))) ? Number(activeRun.roc_auc).toFixed(3) : "—";
      document.getElementById("active-accuracy").textContent = (activeRun.accuracy != null && !isNaN(Number(activeRun.accuracy))) ? (Number(activeRun.accuracy) * 100).toFixed(1) + '%' : "—";
      document.getElementById("active-f1").textContent = (activeRun.f1_score != null && !isNaN(Number(activeRun.f1_score))) ? Number(activeRun.f1_score).toFixed(3) : "—";
      document.getElementById("active-samples").textContent = activeRun.samples_count || "—";
    }

    tbody.innerHTML = runs.map(run => {
      const statusColors = { completed: 'success', running: 'primary', pending: 'warning', failed: 'danger' };
      const statusIcons = { completed: 'check-circle', running: 'activity', pending: 'clock', failed: 'x-circle' };

      const ra = (run.roc_auc != null && !isNaN(Number(run.roc_auc))) ? Number(run.roc_auc).toFixed(3) : '—';
      const acc = (run.accuracy != null && !isNaN(Number(run.accuracy))) ? (Number(run.accuracy) * 100).toFixed(1) + '%' : '—';
      const f1 = (run.f1_score != null && !isNaN(Number(run.f1_score))) ? Number(run.f1_score).toFixed(3) : '—';

      return `
        <tr class="history-row">
          <td class="small">${new Date(run.started_at).toLocaleString()}</td>
          <td>
            <span class="badge bg-${statusColors[run.status]} bg-opacity-10 text-${statusColors[run.status]}">
              <i class="ag-icon ag-${statusIcons[run.status]} me-1"></i>${run.status}
            </span>
          </td>
          <td class="fw-bold">${run.samples_count}</td>
          <td>${ra}</td>
          <td>${acc}</td>
          <td>${f1}</td>
          <td>${run.is_active
            ? '<span class="badge bg-success active-badge">ACTIVE</span>'
            : (run.status === 'completed' ? `<button class="btn btn-sm btn-outline-primary" onclick="activateModel('${run.id}')">Activate</button>` : '—')
          }</td>
          <td>
            ${run.error_message
              ? `<span class="text-danger small" title="${run.error_message}"><i class="ag-icon ag-info-circle"></i></span>`
              : '—'}
          </td>
        </tr>`;
    }).join('');
  } catch (err) {
    console.warn("Could not load history:", err);
  }
}

async function checkRunningTraining() {
  try {
    const status = await Api.get("/training/status");
    if (status && (status.status === "running" || status.status === "pending")) {
      showTrainingProgress();
      startPolling();
    }
  } catch (err) {
    // No running training
  }
}

async function startTraining() {
  const btn = document.getElementById("train-btn");
  if (!confirm("Start model retraining? This will extract features from all annotated submissions and train a new model.")) {
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Starting...';

  try {
    await Api.post("/training/start", {});
    showTrainingProgress();
    startPolling();
  } catch (err) {
    alert("Failed to start training: " + (err.detail || err.message));
    btn.disabled = false;
    btn.innerHTML = '<i class="ag-icon ag-play-fill me-2"></i>Train Model';
  }
}

function showTrainingProgress() {
  const prog = document.getElementById("training-progress");
  prog.classList.add("active");
  document.getElementById("training-progress-bar").style.width = "30%";
  document.getElementById("train-btn").disabled = true;
  document.getElementById("train-btn").innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Training...';
}

function startPolling() {
  if (pollingInterval) clearInterval(pollingInterval);
  pollingInterval = setInterval(pollTrainingStatus, 3000);
}

async function pollTrainingStatus() {
  try {
    const status = await Api.get("/training/status");
    if (!status) return;

    if (status.status === "running") {
      document.getElementById("training-status-text").textContent = "Extracting features & training model…";
      document.getElementById("training-progress-bar").style.width = "60%";
    } else if (status.status === "completed") {
      clearInterval(pollingInterval);
      document.getElementById("training-progress").classList.remove("active");
      document.getElementById("training-progress-bar").style.width = "100%";

      // Show result
      const result = document.getElementById("training-result");
      result.classList.remove("d-none");
      document.getElementById("training-result-text").textContent =
        `ROC-AUC: ${status.roc_auc?.toFixed(3) || '—'} | ` +
        `Accuracy: ${status.accuracy ? (status.accuracy * 100).toFixed(1) + '%' : '—'} | ` +
        `F1: ${status.f1_score?.toFixed(3) || '—'} | ` +
        `Samples: ${status.samples_count}`;

      // Refresh everything
      await loadDashboard();
    } else if (status.status === "failed") {
      clearInterval(pollingInterval);
      document.getElementById("training-progress").classList.remove("active");

      const result = document.getElementById("training-result");
      result.classList.remove("d-none");
      result.querySelector('.alert').className = 'alert alert-danger d-flex align-items-center gap-3';
      result.querySelector('h6').textContent = 'Training Failed';
      document.getElementById("training-result-text").textContent = status.error_message || "Unknown error";

      document.getElementById("train-btn").disabled = false;
      document.getElementById("train-btn").innerHTML = '<i class="ag-icon ag-play-fill me-2"></i>Train Model';
    }
  } catch (err) {
    console.warn("Polling error:", err);
  }
}

async function activateModel(runId) {
  if (!confirm("Activate this model version? The current active model will be replaced.")) return;

  try {
    await Api.post(`/training/${runId}/activate`, {});
    await loadDashboard();
  } catch (err) {
    alert("Activation failed: " + (err.detail || err.message));
  }
}

// Export functions to global scope
window.startTraining = startTraining;
window.activateModel = activateModel;
