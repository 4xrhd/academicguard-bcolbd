/**
 * annotate.js | Annotation page logic.
 * Loads submissions, displays annotation controls, saves to backend.
 */

const batchId = new URLSearchParams(window.location.search).get("batch");
let submissions = [];
let annotations = {};  // submissionId -> {label, confidence, notes}
let existingAnnotations = {};  // from server

document.addEventListener("DOMContentLoaded", async () => {
  if (!batchId) {
    showError("No batch ID provided. Go back to dashboard.");
    return;
  }
  await loadData();
});

async function loadData() {
  try {
    // Load batch results
    const data = await Api.get(`/batches/${batchId}/results`);
    document.getElementById("batch-name-display").textContent = data.batch.name;

    submissions = data.risk_ranking || [];

    // Load existing annotations
    try {
      const annList = await Api.get(`/batches/${batchId}/annotations`);
      annList.forEach(a => {
        existingAnnotations[a.submission_id] = a;
        annotations[a.submission_id] = {
          label: a.label,
          confidence: a.confidence,
          notes: a.notes || "",
          saved: true,
        };
      });
    } catch (e) {
      console.warn("Could not load annotations:", e);
    }

    renderSubmissions();
    updateProgress();
  } catch (err) {
    showError(err.detail || err.message || "Failed to load data.");
  }
}

function renderSubmissions() {
  const container = document.getElementById("submissions-container");
  document.getElementById("bulk-action-bar").classList.remove("d-none");

  if (!submissions.length) {
    container.innerHTML = `
      <div class="empty-state my-5">
        <div class="empty-state-icon"><i class="ag-icon ag-folder-x"></i></div>
        <h4>No Submissions Found</h4>
        <p>This batch does not contain any submissions to annotate.</p>
        <a href="/pages/dashboard.html" class="btn btn-outline-primary mt-3">Back to Dashboard</a>
      </div>
    `;
    return;
  }

  container.innerHTML = submissions.map((sub, idx) => {
    const ann = annotations[sub.submission_id];
    const isAnnotated = ann && ann.label;
    const riskColor = sub.risk_level === "high" ? "danger" : sub.risk_level === "medium" ? "warning" : "success";
    const aiPct = (Number(sub.ai_prob || 0) * 100).toFixed(0);
    const textSimPct = (Number(sub.text_sim_max || 0) * 100).toFixed(0);
    const codeSimPct = sub.code_sim_max != null ? (Number(sub.code_sim_max) * 100).toFixed(0) : '0';
    const weightedPct = (Number(sub.weighted_score || 0) * 100).toFixed(0);

    return `
    <div class="annotation-card p-4 mb-3 ${isAnnotated ? 'annotated' : ''}" id="card-${sub.submission_id}" data-idx="${idx}">
      <div class="row align-items-start">
        <!-- Left: Submission info -->
        <div class="col-lg-5">
          <div class="d-flex align-items-center gap-3 mb-3">
            <span class="badge bg-${riskColor} bg-opacity-10 text-${riskColor} px-3 py-2 fw-bold">
              ${(sub.risk_level || 'LOW').toUpperCase()}
            </span>
            <div>
              <h6 class="mb-0 fw-bold">${sub.student_name || sub.student_id || 'Unknown'}</h6>
              <small class="text-muted">ID: ${sub.student_id || '—'}</small>
            </div>
            ${isAnnotated ? '<i class="ag-icon ag-check-circle-fill text-success ms-auto fs-5"></i>' : ''}
          </div>

          <!-- System scores -->
          <div class="d-flex gap-2 mb-3 flex-wrap">
            <span class="system-prediction bg-${aiPct > 60 ? 'danger' : aiPct > 30 ? 'warning' : 'success'} bg-opacity-10 text-${aiPct > 60 ? 'danger' : aiPct > 30 ? 'warning' : 'success'}">
              <i class="ag-icon ag-robot me-1"></i>AI: ${aiPct}%
            </span>
            <span class="system-prediction bg-primary bg-opacity-10 text-primary">
              <i class="ag-icon ag-files me-1"></i>Text Sim: ${textSimPct}%
            </span>
            <span class="system-prediction bg-info bg-opacity-10 text-info">
              <i class="ag-icon ag-code-slash me-1"></i>Code: ${codeSimPct}%
            </span>
            <span class="system-prediction bg-secondary bg-opacity-10" style="color: var(--ag-text);">
              Score: ${weightedPct}%
            </span>
          </div>

          <a href="/pages/submission.html?id=${sub.submission_id}" target="_blank" class="btn btn-sm btn-outline-primary mb-2">
            <i class="ag-icon ag-eye me-1"></i>View Full Detail
          </a>
        </div>

        <!-- Right: Annotation controls -->
        <div class="col-lg-7">
          <label class="form-label fw-bold small text-muted mb-2">YOUR ANNOTATION</label>
          <div class="d-flex gap-2 mb-3 flex-wrap" id="labels-${sub.submission_id}">
            ${['human', 'ai_generated', 'plagiarized', 'mixed'].map(label => `
              <button class="label-btn ${label} ${ann?.label === label ? 'selected' : ''}"
                      onclick="selectLabel('${sub.submission_id}', '${label}', this)">
                <i class="ag-icon ag-${labelIcon(label)} me-1"></i>${labelDisplay(label)}
              </button>
            `).join('')}
          </div>

          <div class="row g-3 align-items-end">
            <div class="col-md-5">
              <label class="form-label small text-muted mb-1">Confidence</label>
              <div class="d-flex align-items-center gap-2">
                <input type="range" class="confidence-slider" min="0" max="100" value="${(ann?.confidence || 1) * 100}"
                       oninput="updateConfidence('${sub.submission_id}', this.value)" id="conf-${sub.submission_id}">
                <span class="fw-bold small" id="conf-val-${sub.submission_id}">${((ann?.confidence || 1) * 100).toFixed(0)}%</span>
              </div>
            </div>
            <div class="col-md-7">
              <label class="form-label small text-muted mb-1">Notes (optional)</label>
              <input type="text" class="form-control form-control-sm" placeholder="Reason for this label..."
                     value="${ann?.notes || ''}" onchange="updateNotes('${sub.submission_id}', this.value)"
                     id="notes-${sub.submission_id}">
            </div>
          </div>
        </div>
      </div>
    </div>`;
  }).join('');
}

function labelIcon(label) {
  const icons = { human: 'user-check', ai_generated: 'bot', plagiarized: 'copy', mixed: 'shuffle' };
  return icons[label] || 'tag';
}

function labelDisplay(label) {
  const names = { human: 'Human', ai_generated: 'AI Generated', plagiarized: 'Plagiarized', mixed: 'Mixed' };
  return names[label] || label;
}

function selectLabel(subId, label, btn) {
  // Deselect all in this group
  const group = document.getElementById(`labels-${subId}`);
  group.querySelectorAll('.label-btn').forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');

  if (!annotations[subId]) annotations[subId] = { confidence: 1.0, notes: "", saved: false };
  annotations[subId].label = label;
  annotations[subId].saved = false;

  const card = document.getElementById(`card-${subId}`);
  card.classList.add('annotated');

  updateProgress();
}

function updateConfidence(subId, value) {
  if (!annotations[subId]) annotations[subId] = { confidence: 1.0, notes: "", saved: false };
  annotations[subId].confidence = value / 100;
  annotations[subId].saved = false;
  document.getElementById(`conf-val-${subId}`).textContent = `${value}%`;
  updateProgress();
}

function updateNotes(subId, value) {
  if (!annotations[subId]) annotations[subId] = { confidence: 1.0, notes: "", saved: false };
  annotations[subId].notes = value;
  annotations[subId].saved = false;
  updateProgress();
}

function updateProgress() {
  const total = submissions.length;
  const annotated = Object.values(annotations).filter(a => a.label).length;
  const unsaved = Object.values(annotations).filter(a => a.label && !a.saved).length;

  const pct = total ? Math.round(annotated / total * 100) : 0;
  document.getElementById("batch-progress-text").textContent = `${pct}%`;
  document.getElementById("batch-progress-bar").style.width = `${pct}%`;
  document.getElementById("unsaved-count").textContent = unsaved;
}

async function saveAllAnnotations() {
  const toSave = Object.entries(annotations)
    .filter(([_, a]) => a.label && !a.saved)
    .map(([subId, a]) => ({
      submission_id: subId,
      label: a.label,
      confidence: a.confidence,
      notes: a.notes || null,
    }));

  if (!toSave.length) {
    alert("Nothing to save!");
    return;
  }

  try {
    const btn = document.querySelector('#bulk-action-bar .btn-primary');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Saving...';

    await Api.post(`/batches/${batchId}/annotate-bulk`, { annotations: toSave });

    // Mark all as saved
    toSave.forEach(item => {
      if (annotations[item.submission_id]) {
        annotations[item.submission_id].saved = true;
      }
    });

    updateProgress();
    btn.innerHTML = '<i class="ag-icon ag-check-circle me-1"></i>Saved!';
    setTimeout(() => {
      btn.disabled = false;
      btn.innerHTML = `<i class="ag-icon ag-cloud-upload me-1"></i>Save All (<span id="unsaved-count">0</span>)`;
    }, 2000);
  } catch (err) {
    alert("Save failed: " + (err.detail || err.message));
    const btn = document.querySelector('#bulk-action-bar .btn-primary');
    btn.disabled = false;
    btn.innerHTML = `<i class="ag-icon ag-cloud-upload me-1"></i>Save All (<span id="unsaved-count">${toSave.length}</span>)`;
  }
}

function bulkAnnotate(label) {
  const threshold = label === 'human' ? 0.40 : 0.70;

  submissions.forEach(sub => {
    const score = sub.weighted_score;
    const shouldApply = label === 'human' ? score < threshold : score >= threshold;

    if (shouldApply && !annotations[sub.submission_id]?.saved) {
      // Select the button
      const btn = document.querySelector(`#labels-${sub.submission_id} .${label}`);
      if (btn) selectLabel(sub.submission_id, label, btn);
    }
  });
}

function showError(msg) {
  const el = document.getElementById("error-message");
  el.textContent = msg;
  el.style.display = "block";
}

// Export functions to global scope for HTML event handlers
window.selectLabel = selectLabel;
window.updateConfidence = updateConfidence;
window.updateNotes = updateNotes;
window.saveAllAnnotations = saveAllAnnotations;
window.bulkAnnotate = bulkAnnotate;
