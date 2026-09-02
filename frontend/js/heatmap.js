/**
 * heatmap.js | D3.js interactive N×N similarity heatmap matrix.
 * FR-DASH-02: Cell colour intensity = pairwise text similarity score.
 *             Cells are interactive and display hover tooltips.
 */

/**
 * Render the similarity heatmap into a container element.
 * Supports both:
 *   renderHeatmap(containerId, { student_ids, matrix }, onCellClick)
 *   renderHeatmap(containerId, studentIds, matrix, onCellClick)
 *
 * @param {string}   containerId - DOM element ID to render into
 * @param {string[]|object} studentIdsOrData  - Array of student IDs or { student_ids, matrix } object
 * @param {number[][]} [maybeMatrix]          - N×N similarity matrix (0.0–1.0)
 * @param {Function} [onCellClick]            - Callback(subAId, subBId) on cell click
 */
function renderHeatmap(containerId, studentIdsOrData, maybeMatrix, onCellClick) {
  const container = document.getElementById(containerId);
  if (!container) return;

  let studentIds = [];
  let matrix = [];
  let callback = onCellClick;

  if (studentIdsOrData && typeof studentIdsOrData === "object" && !Array.isArray(studentIdsOrData)) {
    studentIds = studentIdsOrData.student_ids || [];
    matrix = studentIdsOrData.matrix || [];
    if (typeof maybeMatrix === "function") {
      callback = maybeMatrix;
    }
  } else if (Array.isArray(studentIdsOrData)) {
    studentIds = studentIdsOrData;
    matrix = Array.isArray(maybeMatrix) ? maybeMatrix : [];
  }

  if (!studentIds.length || !matrix.length) {
    container.innerHTML = `
      <div class="text-center text-muted py-5">
        <i class="ag-icon ag-grid-3x3 fs-2 opacity-50 mb-2 d-block"></i>
        <p class="mb-0">No pairwise similarity data available for this batch.</p>
      </div>`;
    return;
  }

  const n = studentIds.length;
  container.innerHTML = ""; // Clear previous render

  if (typeof d3 === "undefined") {
    container.innerHTML = `
      <div class="text-center text-muted py-4">
        <p>Loading interactive matrix…</p>
        <p class="small">${n}×${n} matrix loaded (${n} students).</p>
      </div>`;
    return;
  }

  const isDarkMode = document.documentElement.getAttribute("data-theme") === "dark" ||
                     document.body.classList.contains("dark-theme");

  const cellSize = Math.max(28, Math.min(48, Math.floor(560 / n)));
  const margin = { top: 90, right: 30, bottom: 30, left: 90 };
  const width = n * cellSize + margin.left + margin.right;
  const height = n * cellSize + margin.top + margin.bottom;

  // Setup SVG container with ARIA attributes
  const svg = d3.select(`#${containerId}`)
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMinYMin meet")
    .attr("role", "grid")
    .attr("aria-label", `Pairwise similarity matrix for ${n} submissions`)
    .style("max-width", "100%")
    .style("height", "auto")
    .style("font-family", "'Inter', system-ui, -apple-system, sans-serif");

  const g = svg.append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  // Custom multi-stop color scale: low = soft navy/slate, medium = amber tint, high = vibrant red/crimson
  const colorScale = d3.scaleSequential()
    .domain([0, 1])
    .interpolator(d3.interpolateRgbBasis([
      isDarkMode ? "#1e293b" : "#f1f5f9",
      isDarkMode ? "#1e3a8a" : "#93c5fd",
      isDarkMode ? "#d97706" : "#f59e0b",
      isDarkMode ? "#ef4444" : "#dc2626"
    ]));

  // Flatten matrix into structured dataset for single batch D3 data-join (prevents N² individual DOM append calls)
  const cellData = [];
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      const val = matrix[i] && matrix[i][j] !== undefined ? matrix[i][j] : 0.0;
      cellData.push({
        row: i,
        col: j,
        studentA: studentIds[i],
        studentB: studentIds[j],
        value: val,
        isDiag: i === j
      });
    }
  }

  // Batch append rects with D3 data-join
  const cells = g.selectAll(".heatmap-cell")
    .data(cellData)
    .join("rect")
    .attr("class", "heatmap-cell")
    .attr("x", d => d.col * cellSize)
    .attr("y", d => d.row * cellSize)
    .attr("width", cellSize - 2)
    .attr("height", cellSize - 2)
    .attr("rx", 4)
    .attr("fill", d => d.isDiag ? (isDarkMode ? "#334155" : "#e2e8f0") : colorScale(d.value))
    .attr("tabindex", d => d.isDiag ? "-1" : "0")
    .attr("role", "gridcell")
    .attr("aria-label", d => d.isDiag
      ? `Self-comparison for ${d.studentA}`
      : `Similarity between ${d.studentA} and ${d.studentB}: ${(d.value * 100).toFixed(1)}%`)
    .style("cursor", d => d.isDiag ? "default" : "pointer")
    .style("outline", "none")
    .style("transition", "all 0.15s ease-in-out");

  // Tooltips
  cells.append("title")
    .text(d => d.isDiag
      ? `Self-comparison (${d.studentA}): 100%`
      : `${d.studentA} ↔ ${d.studentB}: ${(d.value * 100).toFixed(1)}% Similarity`);

  // Interactive event listeners with delegated hover & keyboard navigation
  cells.filter(d => !d.isDiag)
    .on("mouseover focus", function() {
      d3.select(this)
        .attr("stroke", isDarkMode ? "#ffffff" : "#0f172a")
        .attr("stroke-width", 2);
    })
    .on("mouseout blur", function() {
      d3.select(this)
        .attr("stroke", "none");
    })
    .on("click", (event, d) => {
      if (typeof callback === "function") {
        callback(d.studentA, d.studentB);
      }
    })
    .on("keydown", (event, d) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        if (typeof callback === "function") {
          callback(d.studentA, d.studentB);
        }
      } else if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(event.key)) {
        event.preventDefault();
        let targetRow = d.row;
        let targetCol = d.col;
        if (event.key === "ArrowUp") targetRow = Math.max(0, d.row - 1);
        if (event.key === "ArrowDown") targetRow = Math.min(n - 1, d.row + 1);
        if (event.key === "ArrowLeft") targetCol = Math.max(0, d.col - 1);
        if (event.key === "ArrowRight") targetCol = Math.min(n - 1, d.col + 1);

        const nextCell = cells.nodes().find(node => {
          const datum = d3.select(node).datum();
          return datum.row === targetRow && datum.col === targetCol;
        });
        if (nextCell) nextCell.focus();
      }
    });

  // Cell percentage labels (for larger cell dimensions)
  if (cellSize >= 38) {
    g.selectAll(".heatmap-text")
      .data(cellData)
      .join("text")
      .attr("class", "heatmap-text")
      .attr("x", d => d.col * cellSize + (cellSize - 2) / 2)
      .attr("y", d => d.row * cellSize + (cellSize - 2) / 2 + 1)
      .attr("text-anchor", "middle")
      .attr("dominant-baseline", "middle")
      .attr("font-size", `${Math.max(9, Math.floor(cellSize * 0.26))}px`)
      .attr("font-weight", "600")
      .attr("fill", d => d.isDiag ? (isDarkMode ? "#94a3b8" : "#64748b") : (d.value > 0.45 ? "#ffffff" : (isDarkMode ? "#cbd5e1" : "#1e293b")))
      .attr("pointer-events", "none")
      .text(d => d.isDiag ? "—" : `${Math.round(d.value * 100)}%`);
  }

  // Row labels (Y axis)
  g.selectAll(".row-label")
    .data(studentIds)
    .join("text")
    .attr("class", "heatmap-label")
    .attr("x", -10)
    .attr("y", (d, i) => i * cellSize + (cellSize - 2) / 2)
    .attr("text-anchor", "end")
    .attr("dominant-baseline", "middle")
    .attr("font-size", `${Math.min(12, Math.max(10, Math.floor(cellSize * 0.35)))}px`)
    .attr("font-weight", "500")
    .attr("fill", isDarkMode ? "#94a3b8" : "#475569")
    .text(d => String(d).length > 10 ? String(d).slice(0, 10) + "…" : String(d));

  // Column labels (X axis)
  g.selectAll(".col-label")
    .data(studentIds)
    .join("text")
    .attr("class", "heatmap-label")
    .attr("x", (d, i) => i * cellSize + (cellSize - 2) / 2)
    .attr("y", -10)
    .attr("text-anchor", "start")
    .attr("dominant-baseline", "auto")
    .attr("transform", (d, i) => `rotate(-45, ${i * cellSize + (cellSize - 2) / 2}, -10)`)
    .attr("font-size", `${Math.min(12, Math.max(10, Math.floor(cellSize * 0.35)))}px`)
    .attr("font-weight", "500")
    .attr("fill", isDarkMode ? "#94a3b8" : "#475569")
    .text(d => String(d).length > 10 ? String(d).slice(0, 10) + "…" : String(d));
}

/**
 * Build colour scale legend SVG.
 * @param {string} containerId
 */
function renderHeatmapLegend(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = `
    <div class="d-flex align-items-center gap-2 small text-muted">
      <span>0%</span>
      <div style="height: 10px; width: 120px; border-radius: 5px; background: linear-gradient(to right, #f1f5f9, #93c5fd, #f59e0b, #dc2626);"></div>
      <span>100%</span>
    </div>
  `;
}

window.renderHeatmap       = renderHeatmap;
window.renderHeatmapLegend = renderHeatmapLegend;
