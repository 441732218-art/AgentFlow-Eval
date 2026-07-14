/* Client-side PDF export with Chinese text support via html2canvas */

import { jsPDF } from "jspdf";
import type { TaskReport } from "@/types";

const DIMENSION_LABELS: Record<string, string> = {
  tool_accuracy: "工具准确率",
  answer_correctness: "答案正确性",
  reasoning_coherence: "推理连贯性",
};

function escapeHtml(s: string) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function buildReportHtml(report: TaskReport): string {
  const task = report.task;
  const summary = report.summary;
  const passRate =
    summary && summary.total_traces > 0
      ? Math.round((summary.success_count / summary.total_traces) * 100)
      : null;

  const dimRows = Object.entries(summary?.dimension_scores || {})
    .map(
      ([k, v]) =>
        `<tr><td>${escapeHtml(DIMENSION_LABELS[k] || k)}</td><td>${escapeHtml(String(v))}</td></tr>`
    )
    .join("");

  const detailRows: string[] = [];
  for (const d of report.details || []) {
    for (const t of d.traces || []) {
      const scores = t.scores || {};
      const total = Object.values(scores).reduce((a, b) => a + Number(b || 0), 0);
      detailRows.push(
        `<tr>
          <td>${escapeHtml((d.user_query || "").slice(0, 80))}</td>
          <td>${escapeHtml(t.status || "")}</td>
          <td>${scores.tool_accuracy ?? ""}</td>
          <td>${scores.answer_correctness ?? ""}</td>
          <td>${scores.reasoning_coherence ?? ""}</td>
          <td>${Math.round(total)}</td>
          <td>${t.total_tokens ?? ""}</td>
          <td>${t.response_time_ms ?? ""}</td>
        </tr>`
      );
    }
  }

  return `
  <div id="af-pdf-root" style="
    width: 794px;
    padding: 36px 40px;
    background: #fff;
    color: #111;
    font-family: 'Microsoft YaHei','PingFang SC','Noto Sans SC',system-ui,sans-serif;
    font-size: 12px;
    line-height: 1.5;
    box-sizing: border-box;
  ">
    <div style="font-size: 20px; font-weight: 700; margin-bottom: 4px; color: #0ea5e9;">
      AgentFlow-Eval 评测报告
    </div>
    <div style="font-size: 16px; font-weight: 600; margin-bottom: 12px;">
      ${escapeHtml(task?.name || task?.id || "未命名任务")}
    </div>
    <div style="color: #555; margin-bottom: 18px;">
      <div>任务 ID：${escapeHtml(task?.id || "-")}</div>
      <div>状态：${escapeHtml(task?.status || "-")}</div>
      <div>生成时间：${escapeHtml(new Date().toLocaleString())}</div>
    </div>

    <div style="font-size: 14px; font-weight: 700; margin: 16px 0 8px; border-bottom: 2px solid #0ea5e9; padding-bottom: 4px;">
      汇总
    </div>
    <table style="width:100%; border-collapse: collapse; margin-bottom: 12px;">
      <tr><td style="padding:4px 0;color:#555;">综合得分</td><td>${summary?.overall_score ?? "-"}</td></tr>
      <tr><td style="padding:4px 0;color:#555;">成功 / 总 Trace</td>
        <td>${summary?.success_count ?? "-"} / ${summary?.total_traces ?? "-"}${
          passRate != null ? `（${passRate}%）` : ""
        }</td></tr>
      <tr><td style="padding:4px 0;color:#555;">用例数</td><td>${summary?.total_suites ?? report.details?.length ?? "-"}</td></tr>
      <tr><td style="padding:4px 0;color:#555;">总 Tokens</td><td>${summary?.total_tokens ?? "-"}</td></tr>
      <tr><td style="padding:4px 0;color:#555;">总耗时</td><td>${
        summary?.total_time_ms != null ? `${summary.total_time_ms} ms` : "-"
      }</td></tr>
    </table>

    ${
      dimRows
        ? `<div style="font-size: 14px; font-weight: 700; margin: 16px 0 8px; border-bottom: 2px solid #6366f1; padding-bottom: 4px;">维度得分</div>
    <table style="width:100%; border-collapse: collapse; margin-bottom: 12px;">
      <thead><tr style="background:#eef2ff;">
        <th style="text-align:left;padding:6px;border:1px solid #ddd;">维度</th>
        <th style="text-align:left;padding:6px;border:1px solid #ddd;">得分</th>
      </tr></thead>
      <tbody>${dimRows}</tbody>
    </table>`
        : ""
    }

    ${
      detailRows.length
        ? `<div style="font-size: 14px; font-weight: 700; margin: 16px 0 8px; border-bottom: 2px solid #6366f1; padding-bottom: 4px;">用例明细</div>
    <table style="width:100%; border-collapse: collapse; font-size: 11px;">
      <thead><tr style="background:#eef2ff;">
        <th style="text-align:left;padding:5px;border:1px solid #ddd;">用例</th>
        <th style="text-align:left;padding:5px;border:1px solid #ddd;">状态</th>
        <th style="text-align:left;padding:5px;border:1px solid #ddd;">工具</th>
        <th style="text-align:left;padding:5px;border:1px solid #ddd;">答案</th>
        <th style="text-align:left;padding:5px;border:1px solid #ddd;">推理</th>
        <th style="text-align:left;padding:5px;border:1px solid #ddd;">总分</th>
        <th style="text-align:left;padding:5px;border:1px solid #ddd;">Tokens</th>
        <th style="text-align:left;padding:5px;border:1px solid #ddd;">ms</th>
      </tr></thead>
      <tbody>${detailRows.join("")}</tbody>
    </table>`
        : ""
    }

    <div style="margin-top: 24px; color: #999; font-size: 10px;">
      Generated by AgentFlow-Eval · ${escapeHtml(new Date().toISOString())}
    </div>
  </div>`;
}

/**
 * Export report as multi-page A4 PDF with full Chinese rendering
 * (DOM + system CJK fonts → canvas → jsPDF images).
 */
export async function exportReportPdf(report: TaskReport, filename?: string) {
  const html2canvas = (await import("html2canvas")).default;

  const host = document.createElement("div");
  host.style.cssText =
    "position:fixed;left:-10000px;top:0;z-index:-1;pointer-events:none;background:#fff;";
  host.innerHTML = buildReportHtml(report);
  document.body.appendChild(host);

  try {
    const root = host.querySelector("#af-pdf-root") as HTMLElement;
    const canvas = await html2canvas(root, {
      scale: 2,
      useCORS: true,
      backgroundColor: "#ffffff",
      logging: false,
    });

    const pdf = new jsPDF({ unit: "pt", format: "a4", orientation: "portrait" });
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const margin = 24;
    const imgWidth = pageWidth - margin * 2;

    // Slice canvas into pages
    const pageCanvas = document.createElement("canvas");
    const pageCtx = pageCanvas.getContext("2d")!;
    const sliceHeightPx = Math.floor((pageHeight - margin * 2) * (canvas.width / imgWidth));
    pageCanvas.width = canvas.width;

    let offsetY = 0;
    let pageIndex = 0;
    while (offsetY < canvas.height) {
      const h = Math.min(sliceHeightPx, canvas.height - offsetY);
      pageCanvas.height = h;
      pageCtx.clearRect(0, 0, pageCanvas.width, h);
      pageCtx.drawImage(canvas, 0, offsetY, canvas.width, h, 0, 0, canvas.width, h);
      const imgData = pageCanvas.toDataURL("image/jpeg", 0.92);
      const sliceDisplayHeight = (h * imgWidth) / canvas.width;
      if (pageIndex > 0) pdf.addPage();
      pdf.addImage(imgData, "JPEG", margin, margin, imgWidth, sliceDisplayHeight);
      offsetY += h;
      pageIndex += 1;
    }

    const name = filename || `report-${report.task?.id || "export"}.pdf`;
    pdf.save(name);
  } finally {
    document.body.removeChild(host);
  }
}
