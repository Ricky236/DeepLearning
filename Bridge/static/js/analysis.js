const $ = (sel) => document.querySelector(sel);

let charts = { trend: null, byClass: null, byModel: null };

const DEFECT_BAR_COLORS_CN = {
  裂缝: { fill: "rgba(239,68,68,0.72)", stroke: "rgba(185,28,28,0.9)" },
  钢筋外露: { fill: "rgba(250,204,21,0.78)", stroke: "rgba(202,138,4,0.95)" },
  钢筋裸露: { fill: "rgba(250,204,21,0.78)", stroke: "rgba(202,138,4,0.95)" },
  剥落: { fill: "rgba(234,179,8,0.75)", stroke: "rgba(161,98,7,0.95)" },
  破损: { fill: "rgba(139,90,43,0.72)", stroke: "rgba(92,59,28,0.95)" },
  白华: { fill: "rgba(59,130,246,0.72)", stroke: "rgba(29,78,216,0.95)" },
};

const DEFECT_FALLBACK_PALETTE = [
  { fill: "rgba(0,123,255,0.65)", stroke: "rgba(0,86,179,0.95)" },
  { fill: "rgba(14,165,233,0.65)", stroke: "rgba(3,105,161,0.95)" },
  { fill: "rgba(99,102,241,0.65)", stroke: "rgba(67,56,202,0.95)" },
  { fill: "rgba(249,115,22,0.65)", stroke: "rgba(194,65,12,0.95)" },
  { fill: "rgba(16,185,129,0.65)", stroke: "rgba(5,122,85,0.95)" },
  { fill: "rgba(236,72,153,0.60)", stroke: "rgba(157,23,77,0.95)" },
  { fill: "rgba(168,85,247,0.65)", stroke: "rgba(107,33,168,0.95)" },
  { fill: "rgba(20,184,166,0.65)", stroke: "rgba(13,116,106,0.95)" },
];

function defectBarStyle(label) {
  const key = String(label || "").trim();
  if (DEFECT_BAR_COLORS_CN[key]) return DEFECT_BAR_COLORS_CN[key];
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
  return DEFECT_FALLBACK_PALETTE[h % DEFECT_FALLBACK_PALETTE.length];
}

function setText(id, v) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = v == null || v === "" ? "-" : String(v);
}

function destroyCharts() {
  Object.values(charts).forEach((c) => {
    try {
      c?.destroy();
    } catch (_) {}
  });
  charts = { trend: null, byClass: null, byModel: null };
}

function buildCharts(data) {
  destroyCharts();
  const trend = data.trend || {};
  const labels = (trend.labels || []).map((d) => {
    const parts = String(d).split("-");
    return parts.length === 3 ? `${parts[1]}-${parts[2]}` : String(d);
  });

  const ctxTrend = $("#anaTrend");
  if (ctxTrend) {
    
    charts.trend = new Chart(ctxTrend, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "检测次数",
            data: trend.runs || [],
            borderColor: "#007BFF",
            backgroundColor: "rgba(0,123,255,0.10)",
            tension: 0.3,
            fill: true,
            pointRadius: 0,
          },
          {
            label: "病害总数",
            data: trend.defects || [],
            borderColor: "#f97316",
            backgroundColor: "rgba(249,115,22,0.08)",
            tension: 0.3,
            fill: false,
            pointRadius: 0,
            yAxisID: "y1",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { boxWidth: 10, boxHeight: 10 } }, tooltip: { mode: "index", intersect: false } },
        interaction: { mode: "index", intersect: false },
        scales: {
          x: { grid: { display: false } },
          y: { beginAtZero: true, ticks: { precision: 0 } },
          y1: { beginAtZero: true, position: "right", grid: { drawOnChartArea: false }, ticks: { precision: 0 } },
        },
      },
    });
  }

  const ctxClass = $("#anaByClass");
  if (ctxClass) {
    const c = data.by_class || {};
    const cLabels = c.labels || [];
    const cValues = c.values || [];
    const styles = cLabels.map((lb) => defectBarStyle(lb));
    
    charts.byClass = new Chart(ctxClass, {
      type: "bar",
      data: {
        labels: cLabels,
        datasets: [{ data: cValues, backgroundColor: styles.map((s) => s.fill), borderColor: styles.map((s) => s.stroke), borderWidth: 1 }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { grid: { display: false } }, y: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    });
  }

  const ctxModel = $("#anaByModel");
  if (ctxModel) {
    const m = data.by_model || {};
    const mLabels = m.labels || [];
    const mValues = m.values || [];
    
    charts.byModel = new Chart(ctxModel, {
      type: "doughnut",
      data: {
        labels: mLabels,
        datasets: [
          {
            data: mValues,
            backgroundColor: [
              "rgba(0,123,255,0.70)",
              "rgba(14,165,233,0.70)",
              "rgba(99,102,241,0.70)",
              "rgba(249,115,22,0.70)",
              "rgba(250,204,21,0.70)",
              "rgba(16,185,129,0.70)",
              "rgba(239,68,68,0.70)",
              "rgba(139,92,246,0.70)",
              "rgba(20,184,166,0.70)",
              "rgba(168,85,247,0.70)",
            ],
            borderColor: "#ffffff",
            borderWidth: 2,
          },
        ],
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom", labels: { boxWidth: 10, boxHeight: 10 } } } },
    });
  }
}

async function loadAnalysis() {
  const days = $("#anaDays")?.value || "30";
  const model = $("#anaModel")?.value || "";
  const cls = $("#anaClass")?.value || "";
  const res = await fetch(
    `/api/analysis?days=${encodeURIComponent(days)}&model=${encodeURIComponent(model)}&class=${encodeURIComponent(cls)}`
  );
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "加载失败");
  return data;
}

function syncFilterOptions(data) {
  const mSel = $("#anaModel");
  const cSel = $("#anaClass");
  const opts = data?.filters?.options || {};
  const sel = data?.filters?.selected || {};
  if (mSel) {
    const cur = mSel.value;
    const list = Array.isArray(opts.models) ? opts.models : [];
    mSel.innerHTML = `<option value="">全部模型</option>` + list.map((m) => `<option value="${String(m)}">${String(m)}</option>`).join("");
    const target = cur || sel.model || "";
    if ([...mSel.options].some((o) => o.value === target)) mSel.value = target;
  }
  if (cSel) {
    const cur = cSel.value;
    const list = Array.isArray(opts.classes) ? opts.classes : [];
    cSel.innerHTML = `<option value="">全部类型</option>` + list.map((c) => `<option value="${String(c)}">${String(c)}</option>`).join("");
    const target = cur || sel.class || "";
    if ([...cSel.options].some((o) => o.value === target)) cSel.value = target;
  }
}

async function refresh() {
  try {
    const data = await loadAnalysis();
    syncFilterOptions(data);
    setText("anaRuns", data.kpis?.runs ?? "-");
    setText("anaDefects", data.kpis?.defects ?? "-");
    setText("anaAvgMs", data.kpis?.avg_inference_ms == null ? "-" : `${Number(data.kpis.avg_inference_ms).toFixed(0)} ms`);
    setText("anaModels", data.kpis?.models_used ?? "-");
    buildCharts(data);
  } catch (e) {
    setText("anaRuns", "-");
    setText("anaDefects", "-");
    setText("anaAvgMs", "-");
    setText("anaModels", "-");
  }
}

$("#anaRefresh")?.addEventListener("click", refresh);
$("#anaDays")?.addEventListener("change", refresh);
$("#anaModel")?.addEventListener("change", refresh);
$("#anaClass")?.addEventListener("change", refresh);

$("#anaExport")?.addEventListener("click", async () => {
  try {
    const days = $("#anaDays")?.value || "30";
    const model = $("#anaModel")?.value || "";
    const cls = $("#anaClass")?.value || "";
    const res = await fetch(
      `/api/analysis/export?days=${encodeURIComponent(days)}&model=${encodeURIComponent(model)}&class=${encodeURIComponent(cls)}&limit=5000`
    );
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "导出失败");
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    const stamp = Date.now();
    a.download = `analysis_export_${days}d_${stamp}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  } catch (_) {}
});

refresh();

