const $ = (sel) => document.querySelector(sel);

function fmtDay(ts) {
  const d = new Date(ts);
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function fmtTime(ts) {
  const d = new Date(ts);
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fmtInferMs(ms) {
  if (ms == null || ms === "" || Number.isNaN(Number(ms))) return "-";
  return `${Number(ms).toFixed(0)} ms`;
}

function setText(id, v) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = v == null || v === "" ? "-" : String(v);
}


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

function renderRecent(items) {
  const body = $("#recentBody");
  if (!body) return;
  if (!items || !items.length) {
    body.innerHTML = `<tr><td colspan="4" style="color:var(--text2)">-</td></tr>`;
    return;
  }
  body.innerHTML = items
    .slice(0, 12)
    .map((it) => {
      const t = fmtTime(Number(it.ts || 0));
      const model = it.model_label || it.model_id || "-";
      const total = it.total ?? "-";
      const ms = fmtInferMs(it.inference_ms);
      return `<tr><td>${t}</td><td title="${model}" style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${model}</td><td>${total}</td><td style="white-space:nowrap">${ms}</td></tr>`;
    })
    .join("");
}

function buildCharts(data) {
  
  const labels = (data.trend_30d?.labels || []).map((d) => {
    
    const [y, m, day] = String(d).split("-");
    return `${m}-${day}`;
  });
  const runs = data.trend_30d?.runs || [];
  const defects = data.trend_30d?.defects || [];

  const ctxTrend = $("#chartTrend");
  if (ctxTrend) {
    
    new Chart(ctxTrend, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "检测次数",
            data: runs,
            borderColor: "#007BFF",
            backgroundColor: "rgba(0,123,255,0.10)",
            tension: 0.3,
            fill: true,
            pointRadius: 0,
          },
          {
            label: "病害总数",
            data: defects,
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
        plugins: {
          legend: { labels: { boxWidth: 10, boxHeight: 10 } },
          tooltip: { mode: "index", intersect: false },
        },
        interaction: { mode: "index", intersect: false },
        scales: {
          x: { grid: { display: false } },
          y: { beginAtZero: true, ticks: { precision: 0 } },
          y1: {
            beginAtZero: true,
            position: "right",
            grid: { drawOnChartArea: false },
            ticks: { precision: 0 },
          },
        },
      },
    });
  }

  
  const ctxClass = $("#chartByClass");
  if (ctxClass) {
    const cLabels = data.by_class_30d?.labels || [];
    const cValues = data.by_class_30d?.values || [];
    const barStyles = cLabels.map((lb) => defectBarStyle(lb));
    
    new Chart(ctxClass, {
      type: "bar",
      data: {
        labels: cLabels,
        datasets: [
          {
            label: "数量",
            data: cValues,
            backgroundColor: barStyles.map((s) => s.fill),
            borderColor: barStyles.map((s) => s.stroke),
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false } },
          y: { beginAtZero: true, ticks: { precision: 0 } },
        },
      },
    });
  }

  
  const ctxModel = $("#chartByModel");
  if (ctxModel) {
    const mLabels = data.by_model_30d?.labels || [];
    const mValues = data.by_model_30d?.values || [];
    
    new Chart(ctxModel, {
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
            ],
            borderColor: "#ffffff",
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom", labels: { boxWidth: 10, boxHeight: 10 } },
        },
      },
    });
  }
}

async function main() {
  try {
    const res = await fetch("/api/dashboard");
    const data = await res.json();

    setText("kpiRuns", data.kpis?.runs_30d ?? "-");
    setText("kpiDefects", data.kpis?.defects_30d ?? "-");
    setText(
      "kpiAvgMs",
      data.kpis?.avg_inference_ms_30d == null
        ? "-"
        : `${Number(data.kpis.avg_inference_ms_30d).toFixed(0)} ms`
    );
    setText("kpiModels", data.kpis?.models_used_30d ?? "-");

    renderRecent(data.recent || []);
    buildCharts(data);
  } catch (_) {
    renderRecent([]);
  }
}

main();

