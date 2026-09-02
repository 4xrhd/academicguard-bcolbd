/**
 * insight_engine.js | Automated AI & Similarity Insight Engine
 * Generates plain-English analytical alert cards and parses natural-language query filters.
 */

export const InsightEngine = {
  /**
   * Evaluate batch submissions and similarity results to produce action-oriented insight alerts
   */
  generateInsights(riskRanking = [], similarityPairs = []) {
    const insights = [];

    // 1. High Structural Code Plagiarism Alert
    const highCodePairs = similarityPairs.filter(p => (p.code_ast_score || 0) >= 0.75);
    if (highCodePairs.length > 0) {
      insights.push({
        id: "insight-code-cluster",
        level: "warning",
        icon: "ag-code-slash",
        title: "Structural Code Plagiarism Cluster Flagged",
        message: `Identified ${highCodePairs.length} student pair(s) sharing over 75% AST code structure despite renamed variables or modified comments.`,
        actionLabel: "Inspect Code Matches",
        filterKey: "has_code"
      });
    }

    // 2. High AI Synthetic Content Cluster Alert
    const highAiSubs = riskRanking.filter(r => (r.ai_prob || 0) >= 0.80);
    if (highAiSubs.length > 0) {
      insights.push({
        id: "insight-ai-cluster",
        level: "danger",
        icon: "ag-robot",
        title: "Potential LLM Synthetic Content Flagged",
        message: `${highAiSubs.length} submission(s) display low GPT-2 perplexity and uniform stylometric structure characteristic of generative AI output.`,
        actionLabel: "Filter AI Papers",
        filterKey: "high_ai"
      });
    }

    // 3. High Composite Risk Alert
    const highRiskSubs = riskRanking.filter(r => r.risk_level === "high");
    if (highRiskSubs.length >= 3) {
      insights.push({
        id: "insight-high-risk",
        level: "danger",
        icon: "ag-exclamation-triangle-fill",
        title: "Action Required: High-Risk Submissions Pending Triage",
        message: `${highRiskSubs.length} submission(s) exceeded the multi-factor risk threshold and require instructor review before grade finalization.`,
        actionLabel: "Launch Smart Triage Queue",
        filterKey: "high_risk"
      });
    }

    // 4. Clean Class Integrity Benchmark
    if (highRiskSubs.length === 0 && highAiSubs.length === 0 && riskRanking.length > 0) {
      insights.push({
        id: "insight-clean",
        level: "success",
        icon: "ag-check-circle-fill",
        title: "High Academic Integrity Compliance",
        message: "No major plagiarism clusters or synthetic content anomalies were detected in this analysis batch.",
        actionLabel: "Approve Class Results",
        filterKey: "all"
      });
    }

    return insights;
  },

  /**
   * Parse natural-language search queries into filter parameters
   */
  parseNLQuery(queryStr = "") {
    const q = queryStr.toLowerCase().trim();
    const filters = {
      minAiProb: null,
      minTextSim: null,
      hasCode: null,
      riskLevel: null
    };

    if (!q) return filters;

    // AI probability extraction (e.g. "ai over 80%", "gpt > 70%")
    if (q.includes("ai") || q.includes("gpt") || q.includes("synthetic")) {
      const match = q.match(/(?:over|above|>|at least)\s*(\d+)%/);
      if (match) {
        filters.minAiProb = parseFloat(match[1]) / 100;
      } else {
        filters.minAiProb = 0.70;
      }
    }

    // Text similarity extraction (e.g. "similarity > 50%")
    if (q.includes("similarity") || q.includes("text") || q.includes("plagiarism")) {
      const match = q.match(/(?:over|above|>)\s*(\d+)%/);
      if (match) {
        filters.minTextSim = parseFloat(match[1]) / 100;
      } else {
        filters.minTextSim = 0.40;
      }
    }

    // Code filter
    if (q.includes("code") || q.includes("ast") || q.includes("program")) {
      filters.hasCode = true;
    }

    // Risk level
    if (q.includes("high risk") || q.includes("flagged") || q.includes("urgent")) {
      filters.riskLevel = "high";
    } else if (q.includes("medium risk") || q.includes("moderate")) {
      filters.riskLevel = "medium";
    } else if (q.includes("low risk") || q.includes("clean")) {
      filters.riskLevel = "low";
    }

    return filters;
  }
};

window.InsightEngine = InsightEngine;
