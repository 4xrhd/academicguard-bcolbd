/**
 * upload.js | Drag-and-drop multi-file upload with progress bar and file preview.
 * FR-UPLOAD-01: Upload 1–60 PDF files via multipart POST.
 * FR-UPLOAD-04: Poll /batches/{id}/status every 3 seconds until done/error.
 */

document.addEventListener("DOMContentLoaded", () => {
  if (document.body.dataset.page !== "upload") return;
  initUploadPage();
});

function initUploadPage() {
  const dropzone   = document.getElementById("dropzone");
  const fileInput  = document.getElementById("file-input");
  const fileList   = document.getElementById("file-list");
  const uploadForm = document.getElementById("upload-form");
  const configSelect = document.getElementById("marking-config-select");

  let savedConfigs = [];
  let selectedFiles = [];

  // Fetch saved configs
  loadSavedConfigs();

  // ── Drag and drop ──────────────────────────────────────────────────────────
  dropzone.addEventListener("click",      () => fileInput.click());
  dropzone.addEventListener("dragover",   (e) => { e.preventDefault(); dropzone.classList.add("dragover"); });
  dropzone.addEventListener("dragleave",  ()  => dropzone.classList.remove("dragover"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    addFiles([...e.dataTransfer.files]);
  });

  fileInput.addEventListener("change", () => addFiles([...fileInput.files]));

  configSelect.addEventListener("change", (e) => {
    if (e.target.value === "custom") {
      showMarkingConfigModal();
    } else {
      updateConfigPreview(e.target.value);
    }
  });

  async function loadSavedConfigs() {
    try {
      savedConfigs = await Api.marking.listConfigs();
      savedConfigs.forEach(cfg => {
        const opt = document.createElement("option");
        opt.value = cfg.id;
        opt.textContent = `${cfg.name}${cfg.is_default ? " (Default)" : ""}`;
        configSelect.appendChild(opt);
      });
      
      // Select default if exists
      const defaultCfg = savedConfigs.find(c => c.is_default);
      if (defaultCfg) {
        configSelect.value = defaultCfg.id;
        updateConfigPreview(defaultCfg.id);
      }
    } catch (err) {
      console.warn("Failed to load marking configs:", err);
    }
  }

  function updateConfigPreview(configId) {
    const preview = document.getElementById("config-preview");
    const total = document.getElementById("preview-total");
    if (!configId || configId === "custom") {
      preview.classList.add("d-none");
      return;
    }
    const cfg = savedConfigs.find(c => c.id === configId);
    if (cfg) {
      total.textContent = `${cfg.total_marks} Marks`;
      preview.classList.remove("d-none");
    }
  }

  function addFiles(files) {
    const pdfs = files.filter(f => f.type === "application/pdf");
    const combined = [...selectedFiles, ...pdfs];

    if (combined.length > 60) {
      showAlert("Maximum 60 files per batch.", "warning");
      return;
    }

    selectedFiles = combined;
    renderFileList();
  }

  function renderFileList() {
    fileList.innerHTML = "";

    if (selectedFiles.length === 0) {
      fileList.innerHTML = `
        <div class="empty-state text-center p-4">
            <i class="ag-icon ag-folder2-open text-muted fs-1 mb-2"></i>
            <p class="mb-0 fw-bold">No files selected</p>
            <p class="small text-muted mb-0">Drag and drop PDFs above to add them to this analysis.</p>
        </div>
      `;
      document.getElementById("file-count").textContent = `0 files`;
      return;
    }

    selectedFiles.forEach((file, idx) => {
      const sizeMB = (file.size / 1024 / 1024).toFixed(2);
      const tooLarge = file.size > 10 * 1024 * 1024;
      const pill = document.createElement("div");
      pill.className = `file-pill ${tooLarge ? "border-danger text-danger bg-danger bg-opacity-10" : ""}`;
      pill.innerHTML = `
        <div class="d-flex align-items-center gap-3">
          <div class="file-pill-icon-bubble ${tooLarge ? 'border-danger text-danger' : ''}">
            <i class="ag-icon ag-file-earmark-pdf"></i>
          </div>
          <div>
            <div class="fw-bold small text-truncate" style="max-width: 280px; color: var(--ag-text);">${escapeHtml(file.name)}</div>
            <div class="x-small text-muted font-monospace">${sizeMB} MB ${tooLarge ? "— <span class='text-danger fw-bold'>EXCEEDS 10MB</span>" : ""}</div>
          </div>
        </div>
        <button type="button" class="remove-file-btn remove-file" data-idx="${idx}" title="Remove file" aria-label="Remove file">
            <i class="ag-icon ag-x"></i>
        </button>`;
      fileList.appendChild(pill);
    });

    // Remove individual file
    fileList.querySelectorAll(".remove-file").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        selectedFiles.splice(parseInt(btn.getAttribute("data-idx")), 1);
        renderFileList();
      });
    });

    document.getElementById("file-count").textContent = `${selectedFiles.length} files selected`;
  }

  // ── Form submit ────────────────────────────────────────────────────────────
  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    uploadForm.classList.add("was-validated");

    const batchName  = document.getElementById("batch-name").value.trim();
    const courseCode = document.getElementById("course-code").value.trim();

    if (!batchName || !courseCode) {
      showAlert("Please enter batch name and course code.", "warning");
      return;
    }
    if (selectedFiles.length === 0) {
      showAlert("Please select at least one PDF file.", "warning");
      return;
    }
    const oversized = selectedFiles.filter(f => f.size > 10 * 1024 * 1024);
    if (oversized.length > 0) {
      showAlert(`${oversized.length} file(s) exceed 10 MB and will be rejected.`, "warning");
      return;
    }

    const configId = configSelect.value;
    
    if (configId === "custom") {
      // Custom config modal was already shown or needs to be shown
      showMarkingConfigModal();
      window.pendingUploadData = { batchName, courseCode, files: selectedFiles };
      return;
    }

    // Direct upload with saved config or default
    try {
      const formData = new FormData();
      formData.append("batch_name", batchName);
      formData.append("course_code", courseCode);
      selectedFiles.forEach(f => formData.append("files", f));
      if (configId) formData.append("config_id", configId);

      setUploadState(true);
      const result = await Api.batch.upload(formData);
      const batchId = result.id || result.batch_id;
      
      showAlert("Batch uploaded. Starting analysis...", "success");
      document.getElementById("upload-btn").innerHTML = '<i class="ag-icon ag-activity me-2"></i> Analyzing...';
      showUploadProgress(batchId);
    } catch (err) {
      showAlert(err.detail || "Upload failed.", "danger");
      setUploadState(false);
    }
  });
}

// ── Polling ────────────────────────────────────────────────────────────────────
let _pollInterval = null;

function showUploadProgress(batchId) {
  const progressSection = document.getElementById("progress-section");
  if (progressSection) progressSection.style.display = "block";

  _pollInterval = setInterval(async () => {
    try {
      const { status, progress } = await Api.batch.status(batchId);
      updateProgressBar(progress, status);

      if (status === "done") {
        clearInterval(_pollInterval);
        setTimeout(() => window.location.href = `/pages/results.html?batch=${batchId}`, 1000);
      } else if (status === "error") {
        clearInterval(_pollInterval);
        showAlert("Analysis failed. Please check your files and try again.", "danger");
        setUploadState(false);
      }
    } catch (_) {
      // Don't stop on single error, might be transient
    }
  }, 3000);
}

function updateProgressBar(progress, status) {
  const bar = document.getElementById("progress-bar");
  const percentText = document.getElementById("progress-percent");
  
  if (bar) bar.style.width = `${progress}%`;
  if (percentText) percentText.textContent = `${Math.round(progress)}% | ${status.toUpperCase()}`;
}

function setUploadState(uploading) {
  const btn = document.getElementById("upload-btn");
  if (!btn) return;
  btn.disabled = uploading;
  btn.innerHTML = uploading
    ? '<span class="spinner-border spinner-border-sm me-2"></span> Transferring Files...'
    : '<i class="ag-icon ag-play-circle-fill me-2"></i> Launch Analysis';
}

function showAlert(msg, type = "info") {
  const container = document.getElementById("alert-container");
  if (!container) return;
  const div = document.createElement("div");
  div.className = `alert alert-${type} alert-dismissible fade show shadow-sm border-0 animate-fade-in`;
  div.innerHTML = `<strong>Note:</strong> ${escapeHtml(msg)}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
  container.prepend(div);
}

function escapeHtml(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}


// ── Marking Configuration ──────────────────────────────────────────────────────
let currentBatchId = null;
let markingConfig = null;

function showMarkingConfigModal() {
  const modal = new bootstrap.Modal(document.getElementById("markingConfigModal"));
  // Initialize with default thresholds
  initializeThresholds();
  modal.show();
}

function initializeThresholds() {
  // Add default thresholds for each category
  const defaults = {
    ai: [
      { min: 10, max: 20, deduct: 2 },
      { min: 21, max: 30, deduct: 6 },
    ],
    text: [
      { min: 20, max: 40, deduct: 2 },
      { min: 41, max: 60, deduct: 5 },
    ],
    code: [
      { min: 20, max: 40, deduct: 2 },
      { min: 41, max: 60, deduct: 5 },
    ],
    risk: [
      { min: 50, max: 70, deduct: 3 },
      { min: 71, max: 100, deduct: 8 },
    ],
  };

  Object.entries(defaults).forEach(([type, thresholds]) => {
    const container = document.getElementById(`${type}-thresholds-container`);
    container.innerHTML = "";
    thresholds.forEach((t, idx) => {
      addThresholdRow(type, idx, t.min, t.max, t.deduct);
    });
  });
}

function addThreshold(type) {
  const container = document.getElementById(`${type}-thresholds-container`);
  const idx = container.children.length;
  addThresholdRow(type, idx, 0, 0, 0);
}

function addThresholdRow(type, idx, minVal = 0, maxVal = 0, deductVal = 0) {
  const container = document.getElementById(`${type}-thresholds-container`);
  const row = document.createElement("div");
  row.className = "row g-2 mb-2 threshold-row";
  row.innerHTML = `
    <div class="col-md-4">
      <input type="number" class="form-control form-control-sm" placeholder="Min %" min="0" max="100" value="${minVal}" data-field="min"/>
    </div>
    <div class="col-md-4">
      <input type="number" class="form-control form-control-sm" placeholder="Max %" min="0" max="100" value="${maxVal}" data-field="max"/>
    </div>
    <div class="col-md-3">
      <input type="number" class="form-control form-control-sm" placeholder="Deduct" min="0" step="0.5" value="${deductVal}" data-field="deduct"/>
    </div>
    <div class="col-md-1">
      <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeThresholdRow(this)">
        <i class="ag-icon ag-trash"></i>
      </button>
    </div>
  `;
  container.appendChild(row);
}

function removeThresholdRow(btn) {
  btn.closest(".threshold-row").remove();
}

async function saveMarkingConfig() {
  const form = document.getElementById("marking-config-form");
  form.classList.add("was-validated");
  
  const totalMarks = parseFloat(document.getElementById("total-marks").value);
  
  if (!totalMarks || totalMarks <= 0) {
    showAlert("Please enter valid total marks.", "warning");
    return;
  }

  const config = {
    total_marks: totalMarks,
    ai_thresholds: getThresholdsFromUI("ai"),
    text_copy_thresholds: getThresholdsFromUI("text"),
    code_ast_thresholds: getThresholdsFromUI("code"),
    risk_score_thresholds: getThresholdsFromUI("risk"),
  };

  // Validate thresholds
  for (const key in config) {
    if (key !== "total_marks" && config[key].length === 0) {
      showAlert(`Please add at least one threshold for ${key.replace(/_/g, " ")}.`, "warning");
      return;
    }
  }

  try {
    // First upload the batch
    const uploadData = window.pendingUploadData || {
      batchName: document.getElementById("batch-name")?.value.trim(),
      courseCode: document.getElementById("course-code")?.value.trim(),
      files: selectedFiles
    };
    if (!uploadData.batchName || !uploadData.courseCode || !uploadData.files || uploadData.files.length === 0) {
      showAlert("Please enter a batch name, course code, and select at least one PDF file.", "warning");
      return;
    }
    const formData = new FormData();
    formData.append("batch_name", uploadData.batchName);
    formData.append("course_code", uploadData.courseCode);
    uploadData.files.forEach(f => formData.append("files", f));

    setUploadState(true);
    const result = await Api.batch.upload(formData);
    currentBatchId = result.id || result.batch_id;
    
    // Then save marking config for THIS batch
    await Api.batch.setMarkingConfig(currentBatchId, config);
    
    // Check if user wants to save this as a permanent template
    const saveAsTemplate = document.getElementById("save-as-template")?.checked;
    if (saveAsTemplate) {
        const templateName = prompt("Enter a name for this marking template:", "Standard Marking");
        if (templateName) {
            await Api.marking.createConfig({
                name: templateName,
                total_marks: totalMarks,
                config_data: config
            });
        }
    }

    bootstrap.Modal.getInstance(document.getElementById("markingConfigModal")).hide();
    showAlert("Marking configuration saved. Starting analysis...", "success");
    
    // Change state to show polling progress
    document.getElementById("upload-btn").innerHTML = '<i class="ag-icon ag-activity me-2"></i> Analyzing...';
    showUploadProgress(currentBatchId);
  } catch (err) {
    showAlert(err.detail || "Failed to save marking configuration or upload.", "danger");
    setUploadState(false);
  }
}

function getThresholdsFromUI(type) {
  const container = document.getElementById(`${type}-thresholds-container`);
  const thresholds = [];
  
  container.querySelectorAll(".threshold-row").forEach(row => {
    const min = parseFloat(row.querySelector('[data-field="min"]').value);
    const max = parseFloat(row.querySelector('[data-field="max"]').value);
    const deduct = parseFloat(row.querySelector('[data-field="deduct"]').value);
    
    if (!isNaN(min) && !isNaN(max) && !isNaN(deduct)) {
      thresholds.push({
        min_value: min,
        max_value: max,
        marks_deduct: deduct,
      });
    }
  });
  
  return thresholds;
}


// Export functions to global scope for HTML onclick handlers
window.addThreshold = addThreshold;
window.removeThresholdRow = removeThresholdRow;
window.saveMarkingConfig = saveMarkingConfig;
