/**
 * settings.js | Management of saved marking configurations.
 */

document.addEventListener("DOMContentLoaded", () => {
    if (document.body.dataset.page !== "settings") return;
    initSettingsPage();
});

let savedConfigs = [];

async function initSettingsPage() {
    loadProfileDetails();
    await loadConfigs();
}

function loadProfileDetails() {
    const user = typeof getUserInfo === 'function' ? getUserInfo() : null;
    if (user) {
        const userName = user.full_name || user.email || 'Instructor';
        const userEmail = user.email || 'instructor@academicguard.ai';
        const userRole = user.role === 'admin' ? 'Administrator' : 'Instructor';
        const userInitials = userName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'AG';

        const avatarEl = document.getElementById('settings-user-avatar');
        const nameEl = document.getElementById('settings-user-name');
        const emailEl = document.getElementById('settings-user-email');
        const roleEl = document.getElementById('settings-user-role');

        if (avatarEl) avatarEl.textContent = userInitials;
        if (nameEl) nameEl.textContent = userName;
        if (emailEl) emailEl.textContent = userEmail;
        if (roleEl) {
            roleEl.textContent = userRole;
            roleEl.className = `user-role-badge ${user.role === 'admin' ? 'admin' : 'instructor'}`;
        }
    }
}

async function loadConfigs() {
    try {
        savedConfigs = await Api.marking.listConfigs();
        renderConfigsTable();
    } catch (err) {
        showAlert(err.detail || "Failed to load configurations.", "danger");
    }
}

function renderConfigsTable() {
    const tbody = document.getElementById("configs-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!savedConfigs || savedConfigs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center py-5">
                    <div class="empty-state">
                        <i class="ag-icon ag-file-earmark-x display-4 text-muted mb-3 opacity-50"></i>
                        <h6 class="fw-bold text-body">No Rubric Templates Found</h6>
                        <p class="text-muted small mb-3">You haven't created any marking deduction templates yet.</p>
                        <div class="d-flex justify-content-center gap-2 flex-wrap">
                          <button class="btn btn-primary btn-sm px-3 py-2" onclick="showConfigModal()">
                              <i class="ag-icon ag-plus-lg me-1"></i>Create Custom Template
                          </button>
                          <button class="btn btn-outline-info btn-sm px-3 py-2" onclick="applyPreset('theory_only'); showConfigModal();">
                              <i class="ag-icon ag-book me-1"></i>Add Theory-Only Rubric
                          </button>
                        </div>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    savedConfigs.forEach(cfg => {
        const row = document.createElement("tr");
        row.style.borderBottom = "1px solid var(--ag-border)";
        const date = cfg.created_at ? new Date(cfg.created_at).toLocaleDateString() : "|";
        const isTheory = cfg.config_data?.weight_profile === 'theory_only' || (cfg.name && cfg.name.toLowerCase().includes('theory'));
        const profileBadge = isTheory
            ? '<span class="badge bg-info bg-opacity-15 text-info px-2.5 py-1.5 fw-semibold" style="border: 1px solid rgba(14, 165, 233, 0.3);"><i class="ag-icon ag-book me-1"></i>Theory-Only Profile</span>'
            : '<span class="badge bg-purple bg-opacity-15 text-purple px-2.5 py-1.5 fw-semibold" style="border: 1px solid rgba(147, 51, 234, 0.3);"><i class="ag-icon ag-code-slash me-1"></i>Code-Present Profile</span>';
        
        row.innerHTML = `
            <td style="padding: 1rem;">
                <div class="fw-bold text-body fs-6 d-flex align-items-center gap-2">
                    <i class="ag-icon ag-bookmark-fill text-primary"></i>
                    <span>${escapeHtml(cfg.name)}</span>
                </div>
                <div class="mt-1">
                    ${profileBadge}
                </div>
            </td>
            <td style="padding: 1rem;">
                <span class="badge bg-primary bg-opacity-15 text-primary px-3 py-2 font-monospace fw-bold" style="font-size: 0.85rem; border: 1px solid hsla(var(--ag-primary-hsl), 0.25);">
                    ${cfg.total_marks} Marks
                </span>
            </td>
            <td style="padding: 1rem;">
                ${cfg.is_default 
                    ? '<span class="badge bg-success bg-opacity-15 text-success px-3 py-2 fw-semibold" style="border: 1px solid rgba(34, 197, 94, 0.3);"><i class="ag-icon ag-check-circle me-1"></i>DEFAULT TEMPLATE</span>' 
                    : '<span class="badge bg-secondary bg-opacity-10 text-muted px-3 py-2">STANDARD</span>'}
            </td>
            <td style="padding: 1rem;">
                <div class="text-body small d-flex align-items-center gap-1">
                    <i class="ag-icon ag-calendar3 text-muted"></i>
                    <span>${date}</span>
                </div>
            </td>
            <td class="text-end" style="padding: 1rem;">
                <div class="d-inline-flex gap-2">
                    <button class="btn btn-sm btn-outline-primary d-flex align-items-center gap-1 px-3 py-1.5 shadow-sm" onclick="editConfig('${cfg.id}')" title="Edit Template">
                        <i class="ag-icon ag-pencil"></i>
                        <span class="small">Edit</span>
                    </button>
                    ${!cfg.is_default ? `
                        <button class="btn btn-sm btn-outline-success d-flex align-items-center gap-1 px-3 py-1.5 shadow-sm" onclick="setDefaultConfig('${cfg.id}')" title="Set as Default">
                            <i class="ag-icon ag-star"></i>
                            <span class="small">Default</span>
                        </button>
                    ` : ''}
                    <button class="btn btn-sm btn-outline-danger d-flex align-items-center gap-1 px-3 py-1.5 shadow-sm" onclick="deleteConfig('${cfg.id}')" title="Delete Template">
                        <i class="ag-icon ag-trash"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

window.setDefaultConfig = async function(id) {
    const cfg = savedConfigs.find(c => c.id === id);
    if (!cfg) return;
    try {
        const payload = { name: cfg.name, total_marks: cfg.total_marks, config_data: cfg.config_data, is_default: true };
        await Api.marking.updateConfig(id, payload);
        showAlert(`Set "${cfg.name}" as your default configuration template.`, "success");
        loadConfigs();
    } catch (err) {
        showAlert(err.detail || "Failed to set default.", "danger");
    }
};

function showConfigModal() {
    document.getElementById("marking-config-form").reset();
    document.getElementById("config-id").value = "";
    document.getElementById("modal-title").textContent = "Create Marking Template";
    
    // Default to theory_only or code_present
    const profileSelect = document.getElementById("config-profile");
    if (profileSelect) {
        profileSelect.value = "theory_only";
        toggleProfileFields("theory_only");
    }

    // Clear containers
    ["ai", "text", "code", "risk"].forEach(t => {
        const el = document.getElementById(`${t}-thresholds-container`);
        if (el) el.innerHTML = "";
    });
    
    // Add default preset thresholds for Theory-Only
    applyPreset("theory_only");

    const modal = new bootstrap.Modal(document.getElementById("markingConfigModal"));
    modal.show();
}

window.editConfig = function(id) {
    const cfg = savedConfigs.find(c => c.id === id);
    if (!cfg) return;

    document.getElementById("config-id").value = cfg.id;
    document.getElementById("config-name").value = cfg.name;
    document.getElementById("total-marks").value = cfg.total_marks;
    document.getElementById("is-default").checked = cfg.is_default;
    document.getElementById("modal-title").textContent = "Edit Marking Template";

    const data = cfg.config_data || {};
    const profileType = data.weight_profile || (cfg.name && cfg.name.toLowerCase().includes('theory') ? 'theory_only' : 'code_present');
    const profileSelect = document.getElementById("config-profile");
    if (profileSelect) {
        profileSelect.value = profileType;
        toggleProfileFields(profileType);
    }

    const mapping = {
        ai: "ai_thresholds",
        text: "text_copy_thresholds",
        code: "code_ast_thresholds",
        risk: "risk_score_thresholds"
    };

    Object.entries(mapping).forEach(([type, key]) => {
        const container = document.getElementById(`${type}-thresholds-container`);
        if (!container) return;
        container.innerHTML = "";
        const thresholds = data[key] || [];
        thresholds.forEach((t, idx) => {
            addThresholdRow(type, idx, t.min_value, t.max_value, t.marks_deduct);
        });
        if (thresholds.length === 0 && (type !== 'code' || profileType !== 'theory_only')) {
            addThreshold(type);
        }
    });

    const modal = new bootstrap.Modal(document.getElementById("markingConfigModal"));
    modal.show();
};

window.deleteConfig = async function(id) {
    if (!confirm("Are you sure you want to delete this configuration?")) return;
    try {
        await Api.marking.deleteConfig(id);
        showAlert("Configuration deleted successfully.", "success");
        loadConfigs();
    } catch (err) {
        showAlert(err.detail || "Deletion failed.", "danger");
    }
};

window.saveTemplate = async function() {
    const id = document.getElementById("config-id").value;
    const name = document.getElementById("config-name").value.trim();
    const totalMarks = parseFloat(document.getElementById("total-marks").value);
    const isDefault = document.getElementById("is-default").checked;
    const profileType = document.getElementById("config-profile")?.value || "theory_only";

    const form = document.getElementById("marking-config-form");
    if (!form.checkValidity()) {
        form.classList.add("was-validated");
        return;
    }
    form.classList.remove("was-validated");

    const configData = {
        total_marks: totalMarks,
        weight_profile: profileType,
        ai_thresholds: getThresholdsFromUI("ai"),
        text_copy_thresholds: getThresholdsFromUI("text"),
        code_ast_thresholds: profileType === "theory_only" ? [] : getThresholdsFromUI("code"),
        risk_score_thresholds: getThresholdsFromUI("risk"),
    };

    try {
        const payload = { name, total_marks: totalMarks, config_data: configData, is_default: isDefault };
        if (id) {
            await Api.marking.updateConfig(id, payload);
        } else {
            await Api.marking.createConfig(payload);
        }
        
        bootstrap.Modal.getInstance(document.getElementById("markingConfigModal")).hide();
        showAlert(`Configuration ${id ? "updated" : "created"} successfully.`, "success");
        loadConfigs();
    } catch (err) {
        showAlert(err.detail || "Save failed.", "danger");
    }
};

function toggleProfileFields(profileType) {
    const codeWrapper = document.getElementById("code-thresholds-wrapper");
    const descText = document.getElementById("profile-desc-text");
    if (profileType === "theory_only") {
        if (codeWrapper) codeWrapper.style.display = "none";
        if (descText) descText.textContent = "Theory-Only profile evaluates written theory text (55% AI + 45% Text Sim) without Code AST requirements.";
    } else {
        if (codeWrapper) codeWrapper.style.display = "block";
        if (descText) descText.textContent = "Code-Present profile evaluates theory text, AST code structures, and AI likelihood (40% AI + 35% Text Sim + 25% Code AST).";
    }
}

function applyPreset(type) {
    const profileSelect = document.getElementById("config-profile");
    const nameInput = document.getElementById("config-name");
    const marksInput = document.getElementById("total-marks");

    ["ai", "text", "code", "risk"].forEach(t => {
        const el = document.getElementById(`${t}-thresholds-container`);
        if (el) el.innerHTML = "";
    });

    if (type === "theory_only") {
        if (profileSelect) profileSelect.value = "theory_only";
        if (nameInput) nameInput.value = "Standard Theory Essay Rubric";
        if (marksInput) marksInput.value = 10;
        toggleProfileFields("theory_only");

        addThresholdRow("ai", 0, 50, 75, 2.5);
        addThresholdRow("ai", 1, 75, 100, 5.0);
        addThresholdRow("text", 0, 40, 70, 2.0);
        addThresholdRow("text", 1, 70, 100, 4.0);
        addThresholdRow("risk", 0, 60, 100, 1.0);
    } else {
        if (profileSelect) profileSelect.value = "code_present";
        if (nameInput) nameInput.value = "CS Programming & Theory Rubric";
        if (marksInput) marksInput.value = 10;
        toggleProfileFields("code_present");

        addThresholdRow("ai", 0, 50, 100, 3.0);
        addThresholdRow("text", 0, 40, 100, 3.0);
        addThresholdRow("code", 0, 50, 100, 3.0);
        addThresholdRow("risk", 0, 70, 100, 1.0);
    }
}

window.toggleProfileFields = toggleProfileFields;
window.applyPreset = applyPreset;

// Re-use threshold logic from upload.js (consider refactoring into a shared marking-ui.js later)
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

function getThresholdsFromUI(type) {
    const container = document.getElementById(`${type}-thresholds-container`);
    const thresholds = [];
    container.querySelectorAll(".threshold-row").forEach(row => {
        const min = parseFloat(row.querySelector('[data-field="min"]').value);
        const max = parseFloat(row.querySelector('[data-field="max"]').value);
        const deduct = parseFloat(row.querySelector('[data-field="deduct"]').value);
        if (!isNaN(min) && !isNaN(max) && !isNaN(deduct)) {
            thresholds.push({ min_value: min, max_value: max, marks_deduct: deduct });
        }
    });
    return thresholds;
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

window.addThreshold = addThreshold;
window.removeThresholdRow = removeThresholdRow;
window.showConfigModal = showConfigModal;
