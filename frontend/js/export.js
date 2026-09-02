/**
 * export.js | Export Centre logic.
 * Handles downloading Enterprise-grade PDF audit reports, Excel sheets, CSV, and JSON.
 */

document.addEventListener("DOMContentLoaded", () => {
  if (document.body.dataset.page !== "results") return;
  initExportHandlers();
});

function initExportHandlers() {
  const pdfPreviewBtn = document.getElementById("pdf-preview-btn");
  if (pdfPreviewBtn) {
    pdfPreviewBtn.addEventListener("click", async () => {
      const batchId = new URLSearchParams(window.location.search).get("batch");
      if (!batchId) return;
      try {
        if (window.UI?.showToast) UI.showToast("Generating Batch Audit PDF report...", "info");
        await Api.report.downloadBatchPdf(batchId);
        if (window.UI?.showToast) UI.showToast("Batch audit report downloaded successfully!", "success");
      } catch (err) {
        console.error("Batch PDF export failed:", err);
        if (window.UI?.showToast) UI.showToast(`Export failed: ${err.detail || err.message}`, "danger");
      }
    });
  }
}

/**
 * Handle JSON, CSV, Excel, and PDF exports with full authentication and error feedback
 */
async function exportBatch(format) {
  try {
    const batchId = new URLSearchParams(window.location.search).get("batch");
    if (!batchId) {
      if (window.UI?.showToast) UI.showToast("No active batch selected.", "warning");
      else alert("No active batch selected.");
      return;
    }

    if (window.UI?.showToast) UI.showToast(`Preparing ${format.toUpperCase()} export...`, "info");

    if (format === 'pdf') {
      await (Api.reports || Api.report).downloadBatchPdf(batchId);
    } else if (format === 'excel') {
      await (Api.reports || Api.report).downloadBatchExcel(batchId);
    } else if (format === 'csv') {
      await (Api.reports || Api.report).downloadBatchCsv(batchId);
    } else if (format === 'json') {
      await (Api.reports || Api.report).downloadBatchJson(batchId);
    }
    if (window.UI?.showToast) UI.showToast(`${format.toUpperCase()} export completed!`, "success");
  } catch (err) {
    console.error(`Export failed for ${format}:`, err);
    if (window.UI?.showToast) UI.showToast(`Export failed: ${err.detail || err.message}`, "danger");
    else alert("Export failed: " + (err.detail || err.message));
  }
}

/**
 * Trigger a file download by creating a hidden anchor.
 */
function downloadFile(dataUrl, filename) {
  const a = document.createElement("a");
  a.href = dataUrl;
  a.download = filename;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

window.downloadFile = downloadFile;
window.exportBatch  = exportBatch;
