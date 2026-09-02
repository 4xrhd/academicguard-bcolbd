/**
 * role_dashboard_adapter.js | Role-Based Dynamic Dashboard Scaffolding
 * Adapts UI layout, widget density, and action items for 4 user personas:
 * 1. Instructor (Prof Clark) | Simple, high-level narrative summary & risk badges
 * 2. TA (Emma) | High-efficiency triage queue & bulk actions
 * 3. Admin (Patel) | Dense ML accuracy metrics, system health, audit logs
 * 4. Department Head | Executive KPI summaries & cross-course comparison
 */

const ROLE_CONFIGS = {
  instructor: {
    roleName: "Instructor View (Professor Clark)",
    subtitle: "High-level course integrity overview and plain-English analysis summaries.",
    density: "comfortable",
    primaryAction: { label: "Upload Assignment Batch", href: "/pages/upload.html", icon: "ag-cloud-upload" },
    widgets: [
      { id: "kpi-summary", title: "Class Integrity Overview", col: 12 },
      { id: "flagged-highlights", title: "Submissions Requiring Review", col: 8 },
      { id: "recent-activity", title: "Recent Batches", col: 4 }
    ]
  },
  ta: {
    roleName: "TA Grading & Triage Station (Emma)",
    subtitle: "Fast-paced triage queue, bulk mark deduction tools, and AST side-by-side viewer.",
    density: "compact",
    primaryAction: { label: "Start Triage Session", action: "startTriage", icon: "ag-play-fill" },
    widgets: [
      { id: "quick-triage-queue", title: "Smart Triage Queue (Action Required)", col: 12 },
      { id: "pending-annotations", title: "Pending Ground-Truth Labels", col: 6 },
      { id: "recent-activity", title: "Recent Batch Results", col: 6 }
    ]
  },
  admin: {
    roleName: "System Administration & ML Metrics (Admin Patel)",
    subtitle: "Model calibration, incremental training metrics, system logs, and RBAC control.",
    density: "compact",
    primaryAction: { label: "Model Training Panel", href: "/pages/training.html", icon: "ag-cpu" },
    widgets: [
      { id: "system-health", title: "Platform & Model Performance Metrics", col: 12 },
      { id: "kpi-summary", title: "System-Wide Volume Overview", col: 6 },
      { id: "recent-activity", title: "Audit Trail & Recent Batches", col: 6 }
    ]
  },
  dept_head: {
    roleName: "Department Integrity Executive Brief",
    subtitle: "Aggregated accreditation metrics, course-by-course comparisons, and executive exports.",
    density: "spacious",
    primaryAction: { label: "Export Monthly Brief (PDF)", action: "exportBrief", icon: "ag-download" },
    widgets: [
      { id: "dept-kpi-brief", title: "Departmental Risk & Compliance KPIs", col: 12 },
      { id: "course-comparison", title: "Course Integrity Distribution", col: 8 },
      { id: "recent-activity", title: "Department Batches", col: 4 }
    ]
  }
};

export const RoleDashboardAdapter = {
  getProfile(role) {
    return ROLE_CONFIGS[role] || ROLE_CONFIGS.instructor;
  },

  applyRoleView(role, user) {
    const profile = this.getProfile(role);
    
    // Update Subtitle & Role Tag
    const roleTagEl = document.getElementById("dashboard-role-tag");
    if (roleTagEl) {
      roleTagEl.textContent = profile.roleName;
    }

    const subtitleEl = document.getElementById("dashboard-subtitle");
    if (subtitleEl) {
      subtitleEl.textContent = profile.subtitle;
    }

    // Configure Role Action Button
    const actionBtn = document.getElementById("dashboard-primary-action");
    if (actionBtn) {
      actionBtn.innerHTML = `<i class="ag-icon ${profile.primaryAction.icon} me-2"></i>${profile.primaryAction.label}`;
      if (profile.primaryAction.href) {
        actionBtn.onclick = () => window.location.href = profile.primaryAction.href;
      } else if (profile.primaryAction.action === "startTriage") {
        actionBtn.onclick = () => window.location.href = "/pages/results.html?triage=1";
      } else if (profile.primaryAction.action === "exportBrief") {
        actionBtn.onclick = () => UI.showToast("Exporting Departmental Integrity Executive Brief (PDF)...", "info");
      }
    }
  }
};

window.RoleDashboardAdapter = RoleDashboardAdapter;
