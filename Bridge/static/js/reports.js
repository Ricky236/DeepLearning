const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

let historyItems = [];

const MAX_FIGURE_RECORDS = 5;
const MAX_DETAIL_ROWS = 80;


let __lastReportState = null;

function reportExportUrls() {
  const primary =
    typeof window !== "undefined" && window.__REPORT_EXPORT_URL__
      ? String(window.__REPORT_EXPORT_URL__)
      : "/api/reports/export";
  const fallback =
    typeof window !== "undefined" && window.__REPORT_EXPORT_FALLBACK_URL__
      ? String(window.__REPORT_EXPORT_FALLBACK_URL__)
      : "/reports/api/export";
  return { primary, fallback };
}

function setText(id, v) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = v == null || v === "" ? "-" : String(v);
}

function setHint(msg, isError = false) {
  const el = $("#historyHint");
  if (!el) return;
  el.textContent = msg || "";
  el.style.color = isError ? "var(--error, #b53333)" : "";
}


function toast(msg, isError = false) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.toggle("error", isError);
  el.classList.add("show");
  window.clearTimeout(toast._t);
  toast._t = window.setTimeout(() => el.classList.remove("show"), isError ? 4200 : 3200);
}

function formatTs(ts) {
  const d = new Date(Number(ts || 0));
  if (!Number.isFinite(d.getTime())) return "-";
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function resultJsonUrlFromResultUrl(resultUrl) {
  if (!resultUrl || typeof resultUrl !== "string") return null;
  const jsonUrl = resultUrl.replace(/\.jpg$/i, ".json").replace(/\.jpeg$/i, ".json").replace(/\.png$/i, ".json");
  try {
    const u = new URL(jsonUrl, location.origin);
    const name = u.pathname.split("/").pop();
    return name ? `/api/result-json/${encodeURIComponent(name)}` : jsonUrl;
  } catch (_) {
    return jsonUrl;
  }
}

function statsFromDetections(dets) {
  const stats = {};
  for (const d of dets || []) {
    const k = d.class_cn || d.class || "未知";
    stats[k] = (stats[k] || 0) + 1;
  }
  return stats;
}

function avgConf(dets) {
  const arr = (dets || []).map((d) => Number(d.confidence)).filter((x) => Number.isFinite(x));
  if (!arr.length) return null;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function fmtInferMs(ms) {
  if (ms == null || ms === "" || !Number.isFinite(Number(ms))) return "-";
  return `${Number(ms).toFixed(0)} ms`;
}

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** 单条记录卡片内「主要类别」列表 HTML */
function topCategoryLinesHtml(stats, max = 5) {
  const lines = Object.entries(stats || {})
    .filter(([, n]) => Number(n) > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, max)
    .map(([k, v]) => `<li>${escapeHtml(k)}：<strong>${v}</strong> 处</li>`);
  return lines.length ? lines.join("") : `<li style="color:var(--rp-text2);list-style:disc">暂无类别统计（可依赖 JSON 明细）</li>`;
}

function buildOneRecordCardHtml(p, index) {
  const it = p.it;
  const ts = formatTs(it.ts);
  const model = it.model_label || it.model_id || "-";
  const total = p.total;
  const nDets = (p.dets || []).length;
  const ac = avgConf(p.dets);
  const confStr = ac == null ? "—" : `${(ac * 100).toFixed(1)}%`;
  const ms = fmtInferMs(it.inference_ms);
  return `<div class="rs-summary-card">
    <div class="rs-summary-card-head">
      <span class="rs-summary-card-idx">记录 ${index}</span>
      <span class="rs-summary-card-time">${escapeHtml(ts)}</span>
    </div>
    <div class="rs-summary-card-model"><span class="k">模型</span>${escapeHtml(model)}</div>
    <ul class="rs-summary-card-metrics">
      <li>病害数量：<strong>${total}</strong>（JSON 检测框 <strong>${nDets}</strong> 条）</li>
      <li>平均置信度：<strong>${confStr}</strong></li>
      <li>推理耗时：<strong>${escapeHtml(ms)}</strong></li>
    </ul>
    <div class="rs-summary-card-sub">本条 · 主要类别</div>
    <ul class="rs-summary-card-cats">${topCategoryLinesHtml(p.stats, 6)}</ul>
  </div>`;
}

/**
 * @param {Array<{it:any,stats:any,dets:any[],total:number}>} perItem
 * @param {null|{timeLabel:string,grandTotal:number,mergedStats:object,detCount:number}} merged 多条时传入合计上下文
 */
function renderSummarySection(perItem, merged) {
  const lead = $("#rSummaryLead");
  const cards = $("#rSummaryCards");
  if (!lead || !cards) return;

  if (!perItem.length) {
    lead.textContent = "请在右侧勾选历史记录并点击「更新报告预览」，或点击「填充示例」查看版式。";
    cards.innerHTML = "";
    return;
  }

  if (perItem.length === 1) {
    lead.textContent =
      "以下为所选单次检测的概要；第二节为该病害分类统计，第三、四节为图像与逐条明细。";
    cards.innerHTML = buildOneRecordCardHtml(perItem[0], 1);
    return;
  }

  const { timeLabel, grandTotal, detCount } = merged || {};

  lead.innerHTML = `本报告汇总 <strong>${perItem.length}</strong> 条独立检测记录（时间范围：<strong>${escapeHtml(
    timeLabel || ""
  )}</strong>）。<strong>合计病害 ${grandTotal ?? "—"} 个</strong>，明细共 <strong>${detCount ?? "—"}</strong> 条。`;

  cards.innerHTML = perItem.map((p, i) => buildOneRecordCardHtml(p, i + 1)).join("");
}

function renderCategoryList(stats) {
  const ul = $("#rCategoryList");
  if (!ul) return;
  const entries = Object.entries(stats || {})
    .filter(([, v]) => Number(v) > 0)
    .sort((a, b) => b[1] - a[1]);
  ul.innerHTML =
    entries.map(([k, v]) => `<li><strong>${k}</strong>：${v} 处</li>`).join("") ||
    `<li style="color:var(--rp-text2)">暂无分类统计数据</li>`;
}

/** rootMmpp：结果 JSON 根上的 mm_per_pixel，用于旧数据从 px 换算。 */
function rowRemark(d, rootMmpp) {
  const q = d.quant;
  if (q) {
    const lm = Number(q.length_mm);
    const wm = Number(q.max_width_mm);
    if (Number.isFinite(lm) && Number.isFinite(wm) && lm >= 0 && wm >= 0) {
      return `长约 ${lm.toFixed(1)} mm，最大宽度约 ${wm.toFixed(1)} mm`;
    }
    const mmpp = Number(rootMmpp);
    const lp = Number(q.length_px);
    const mx = Number(q.max_width_px);
    if (Number.isFinite(mmpp) && mmpp > 0 && Number.isFinite(lp) && Number.isFinite(mx)) {
      return `长约 ${(lp * mmpp).toFixed(1)} mm，最大宽度约 ${(mx * mmpp).toFixed(1)} mm`;
    }
    return "-";
  }
  if (d.bbox && d.bbox.length) return `位置 ${d.bbox.map((n) => Math.round(n)).join(", ")}`;
  return "-";
}

function fillDetailTableMerged(rows) {
  const body = $("#rDetRows");
  if (!body) return;
  if (!rows || !rows.length) {
    body.innerHTML = `<tr><td colspan="5" style="text-align:center">暂无明细（需结果 JSON 中含 detections）</td></tr>`;
    return;
  }
  body.innerHTML = rows
    .slice(0, MAX_DETAIL_ROWS)
    .map((row, i) => {
      const d = row.d;
      const src = row.source || "-";
      const cls = d.class_cn || d.class || "-";
      const conf = d.confidence != null ? `${(Number(d.confidence) * 100).toFixed(1)}%` : "-";
      return `<tr><td>${i + 1}</td><td>${src}</td><td>${cls}</td><td>${conf}</td><td>${rowRemark(d, row.mm_per_pixel)}</td></tr>`;
    })
    .join("");
}

function renderFiguresMulti(perItem) {
  const wrap = $("#rFiguresMulti");
  const note = $("#rFiguresNote");
  if (!wrap) return;
  const slice = perItem.slice(0, MAX_FIGURE_RECORDS);
  wrap.innerHTML = slice
    .map((p, idx) => {
      const orig = p.it.original_url || p.it.result_url || "";
      const res = p.it.result_url || p.it.original_url || "";
      const title = `记录 ${idx + 1} · ${formatTs(p.it.ts)} · ${p.it.model_label || p.it.model_id || "-"}`;
      return `
      <div class="rs-figure-pair-block">
        <div class="rs-figure-pair-title">${title}</div>
        <div class="rs-figures">
          <figure class="rs-fig">
            <div class="rs-fig-inner"><img alt="原始" src="${orig}" loading="lazy"/></div>
            <figcaption>原始图像</figcaption>
          </figure>
          <figure class="rs-fig">
            <div class="rs-fig-inner"><img alt="检测结果" src="${res}" loading="lazy"/></div>
            <figcaption>检测结果</figcaption>
          </figure>
        </div>
      </div>`;
    })
    .join("");

  if (note) {
    if (perItem.length > MAX_FIGURE_RECORDS) {
      note.hidden = false;
      note.textContent = `另有 ${perItem.length - MAX_FIGURE_RECORDS} 条记录未展开配图，可在「检测结果」页逐条查看。`;
    } else {
      note.hidden = true;
      note.textContent = "";
    }
  }
}

function touchFooterGenerated() {
  const el = $("#rFooterGenerated");
  if (!el) return;
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  el.textContent = `报告生成时间：${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function syncHistoryItemCheckedClass() {
  $$("#historyList .history-item").forEach((lab) => {
    const cb = lab.querySelector('input[type="checkbox"]');
    lab.classList.toggle("history-item--checked", !!(cb && cb.checked));
  });
}

function renderHistoryList() {
  const list = $("#historyList");
  if (!list) return;
  const sorted = [...historyItems].sort((a, b) => Number(b.ts || 0) - Number(a.ts || 0));
  if (!sorted.length) {
    list.innerHTML = `<div class="history-empty">暂无历史记录，请先进行检测并保存。</div>`;
    return;
  }
  list.innerHTML = sorted
    .map((it) => {
      const id = String(it.id).replace(/"/g, "&quot;");
      const t = formatTs(it.ts);
      const m = (it.model_label || it.model_id || "-").replace(/</g, "&lt;");
      const tot = it.total != null && it.total !== "" ? it.total : "—";
      return `<label class="history-item" data-id="${id}">
        <input type="checkbox" name="historyPick" value="${id}" />
        <span class="history-item-body">
          <span class="history-item-title">${t}</span>
          <span class="history-item-meta">${m} · 病害约 ${tot} 个</span>
        </span>
      </label>`;
    })
    .join("");
  syncHistoryItemCheckedClass();
}

async function loadLocalHistoryOptions() {
  if (!$("#historyList")) return;
  try {
    const profileRaw = localStorage.getItem("bridge_profile");
    const profile = profileRaw ? JSON.parse(profileRaw) : null;
    const userId = profile && profile.userId ? profile.userId : null;
    if (!userId) {
      setHint("未登录且无本机用户标识：无法读取本机历史。请登录或先在检测流程中产生记录。");
      historyItems = [];
      renderHistoryList();
      return;
    }
    const key = `bridge_history_${userId}`;
    const raw = localStorage.getItem(key);
    const arr = raw ? JSON.parse(raw) : [];
    historyItems = (Array.isArray(arr) ? arr : []).map((it, idx) => ({
      id: `local_${it.ts || 0}_${idx}`,
      ts: it.ts,
      model_id: it.model_id,
      model_label: it.model_label || it.model_id,
      original_url: it.original_url,
      result_url: it.result_url,
      total: it.total,
      inference_ms: it.inference_ms,
      stats_json: JSON.stringify(it.stats || {}),
      __local: true,
    }));
    renderHistoryList();
    setHint(`已加载本机历史 ${historyItems.length} 条。`);
  } catch (_) {
    setHint("读取本机历史失败。");
    historyItems = [];
    renderHistoryList();
  }
}

async function loadServerHistoryOptions() {
  if (!$("#historyList")) return;
  const me = await fetch("/api/me").then((r) => r.json());
  if (!me.logged_in) {
    await loadLocalHistoryOptions();
    return;
  }
  const res = await fetch("/api/history?limit=200");
  if (!res.ok) {
    await loadLocalHistoryOptions();
    setHint("账号历史读取失败，已回退到本机历史（如有）。");
    return;
  }
  const resp = await res.json();
  historyItems = resp.items || [];
  renderHistoryList();
  setHint(`已加载账号历史 ${historyItems.length} 条，可在列表中勾选（支持多选）。`);
}

async function fetchItemPayload(it) {
  let stats = {};
  try {
    stats = JSON.parse(it.stats_json || "{}");
  } catch (_) {
    stats = {};
  }
  const result = it.result_url || "";
  const jsonUrl = resultJsonUrlFromResultUrl(result);
  let dets = [];
  let mm_per_pixel = null;
  if (jsonUrl) {
    try {
      const res = await fetch(jsonUrl);
      if (res.ok) {
        const data = await res.json();
        dets = Array.isArray(data.detections) ? data.detections : [];
        const mm = Number(data.mm_per_pixel);
        if (Number.isFinite(mm) && mm > 0) mm_per_pixel = mm;
        if (!Object.keys(stats).length && dets.length) stats = statsFromDetections(dets);
      }
    } catch (_) {}
  }
  if (!(Number(mm_per_pixel) > 0) && it.params_json) {
    try {
      const pj = JSON.parse(it.params_json);
      const m2 = Number(pj.mm_per_pixel ?? pj.scale_mm_per_pixel);
      if (Number.isFinite(m2) && m2 > 0) mm_per_pixel = m2;
    } catch (_) {}
  }
  const totalFromStats = Object.values(stats).reduce((a, b) => a + Number(b || 0), 0);
  const total =
    Number.isFinite(Number(it.total)) && Number(it.total) > 0
      ? Number(it.total)
      : totalFromStats > 0
        ? totalFromStats
        : (dets || []).length;
  return { it, stats, dets, total: total || 0, mm_per_pixel };
}

async function applySelectedHistoryMerged() {
  const ids = [...$$('#historyList input[name="historyPick"]:checked')].map((cb) => cb.value);
  if (!ids.length) {
    setHint("请至少勾选一条历史记录，再点击「更新报告预览」。");
    return;
  }
  const items = ids
    .map((id) => historyItems.find((x) => String(x.id) === String(id)))
    .filter(Boolean);
  if (!items.length) return;

  items.sort((a, b) => Number(b.ts || 0) - Number(a.ts || 0));

  const perItem = [];
  for (const it of items) {
    perItem.push(await fetchItemPayload(it));
  }

  const mergedStats = {};
  const allDetsWithSource = [];
  let sumMs = 0;
  let msN = 0;
  for (const p of perItem) {
    for (const [k, v] of Object.entries(p.stats || {})) {
      mergedStats[k] = (mergedStats[k] || 0) + Number(v || 0);
    }
    const srcShort = formatTs(p.it.ts).replace(/^\d{4}-/, "");
    const rootMmpp = p.mm_per_pixel;
    for (const d of p.dets) {
      allDetsWithSource.push({ d, source: srcShort, mm_per_pixel: rootMmpp });
    }
    if (p.it.inference_ms != null && Number.isFinite(Number(p.it.inference_ms))) {
      sumMs += Number(p.it.inference_ms);
      msN += 1;
    }
  }

  const grandTotalFromStats = Object.values(mergedStats).reduce((a, b) => a + b, 0);
  const grandTotal = grandTotalFromStats > 0 ? grandTotalFromStats : allDetsWithSource.length;

  const allConfs = allDetsWithSource.map(({ d }) => Number(d.confidence)).filter((x) => Number.isFinite(x));
  const ac = allConfs.length ? allConfs.reduce((a, b) => a + b, 0) / allConfs.length : null;

  const tss = items.map((i) => Number(i.ts || 0)).filter((x) => Number.isFinite(x));
  const minTs = Math.min(...tss);
  const maxTs = Math.max(...tss);
  const timeLabel =
    items.length === 1 ? formatTs(items[0].ts) : `${formatTs(minTs)} ～ ${formatTs(maxTs)}（${items.length} 条）`;

  const modelsArr = [...new Set(items.map((i) => String(i.model_label || i.model_id || "-")))];
  let modelsStr = modelsArr.join("、");
  if (modelsStr.length > 120) modelsStr = `${modelsStr.slice(0, 120)}…`;

  setText("rMetaTime", timeLabel);
  setText("rMetaModel", modelsStr);
  setText("rMetaTotal", String(grandTotal));
  setText("rMetaConf", ac == null ? "-" : `${(ac * 100).toFixed(1)}%`);
  if (items.length === 1) {
    setText("rMetaMs", fmtInferMs(items[0].inference_ms));
  } else {
    setText("rMetaMs", msN ? `均值 ${Math.round(sumMs / msN)} ms` : "-");
  }

  renderSummarySection(perItem, {
    timeLabel,
    grandTotal,
    mergedStats,
    detCount: allDetsWithSource.length,
  });

  renderCategoryList(mergedStats);
  fillDetailTableMerged(allDetsWithSource);
  renderFiguresMulti(perItem);
  touchFooterGenerated();
  __lastReportState = { perItem, mergedStats, allDetsWithSource };
  setHint(`已根据 ${items.length} 条记录更新报告预览，可导出 Word / PDF / Markdown。`);
}

function fillDemo() {
  $$('#historyList input[name="historyPick"]').forEach((cb) => {
    cb.checked = false;
  });
  syncHistoryItemCheckedClass();

  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  const tsLabel = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`;

  setText("rMetaTime", tsLabel);
  setText("rMetaModel", "model1（示例）");
  setText("rMetaTotal", "36");
  setText("rMetaConf", "86.2%");
  setText("rMetaMs", "120 ms");

  const stats = { 裂缝: 18, 剥落: 6, 钢筋外露: 3, 白华: 4, 破损: 5 };
  const dets = [
    { class_cn: "裂缝", class: "Crack-Detection", confidence: 0.92, bbox: [10, 20, 90, 120] },
    { class_cn: "剥落", class: "Spalling", confidence: 0.84, bbox: [120, 60, 190, 150] },
    { class_cn: "钢筋外露", class: "Exposed Rebar", confidence: 0.78, bbox: [220, 80, 290, 160] },
  ];

  const demoIt = {
    ts: now.getTime(),
    model_label: "model1（示例）",
    inference_ms: 120,
    original_url: "/static/img/bridge-cover.svg",
    result_url: "/static/img/bridge-overview.svg",
  };
  renderSummarySection([{ it: demoIt, stats, dets, total: 36 }], null);
  renderCategoryList(stats);
  fillDetailTableMerged(dets.map((d) => ({ d, source: "示例" })));
  renderFiguresMulti([{ it: demoIt, stats, dets, total: 36 }]);
  touchFooterGenerated();
  __lastReportState = {
    perItem: [{ it: demoIt, stats, dets, total: 36 }],
    mergedStats: stats,
    allDetsWithSource: dets.map((d) => ({ d, source: "示例" })),
  };
  setHint("已填入示例，可导出 Word / PDF / Markdown。");
}

function buildExportPayload() {
  const st = __lastReportState;
  if (!st || !st.perItem || !st.perItem.length) return null;

  const meta = {
    time: ($("#rMetaTime") && $("#rMetaTime").textContent.trim()) || "-",
    model: ($("#rMetaModel") && $("#rMetaModel").textContent.trim()) || "-",
    total: ($("#rMetaTotal") && $("#rMetaTotal").textContent.trim()) || "-",
    conf: ($("#rMetaConf") && $("#rMetaConf").textContent.trim()) || "-",
    ms: ($("#rMetaMs") && $("#rMetaMs").textContent.trim()) || "-",
  };
  const lead = ($("#rSummaryLead") && ($("#rSummaryLead").innerText || "").trim()) || "";

  const summary_cards = st.perItem.map((p, i) => {
    const ac = avgConf(p.dets);
    return {
      index: i + 1,
      time: formatTs(p.it.ts),
      model: String(p.it.model_label || p.it.model_id || "-"),
      total: p.total,
      n_dets: (p.dets || []).length,
      avg_conf: ac == null ? "—" : `${(ac * 100).toFixed(1)}%`,
      infer_ms: fmtInferMs(p.it.inference_ms),
      top_cats: Object.entries(p.stats || {})
        .filter(([, n]) => Number(n) > 0)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8)
        .map(([name, count]) => ({ name, count })),
    };
  });

  const figures = st.perItem.slice(0, MAX_FIGURE_RECORDS).map((p, i) => ({
    title: `记录 ${i + 1} · ${formatTs(p.it.ts)} · ${p.it.model_label || p.it.model_id || "-"}`,
    original_url: p.it.original_url || "",
    result_url: p.it.result_url || "",
  }));

  const detail_rows = (st.allDetsWithSource || []).slice(0, MAX_DETAIL_ROWS).map((row, i) => ({
    seq: i + 1,
    source: row.source,
    class: row.d.class_cn || row.d.class || "-",
    conf: row.d.confidence != null ? `${(Number(row.d.confidence) * 100).toFixed(1)}%` : "—",
    remark: rowRemark(row.d, row.mm_per_pixel),
  }));

  return {
    version: 1,
    title: "桥梁表观病害检测报告",
    footer_line: ($("#rFooterLine") && $("#rFooterLine").textContent.trim()) || "",
    footer_generated: ($("#rFooterGenerated") && $("#rFooterGenerated").textContent.trim()) || "",
    meta,
    summary_lead_plain: lead,
    summary_cards,
    merged_stats: st.mergedStats || {},
    figures,
    detail_rows,
  };
}

async function exportReportFile(format) {
  touchFooterGenerated();
  const payload = buildExportPayload();
  if (!payload) {
    const msg = "请先点击「更新报告预览」或「填充示例」生成预览，再导出。";
    setHint(msg, true);
    toast(msg, true);
    return;
  }
  try {
    const { primary, fallback } = reportExportUrls();
    let res = await fetch(primary, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format, payload }),
    });
    if (res.status === 404 && fallback && fallback !== primary) {
      res = await fetch(fallback, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ format, payload }),
      });
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const msg = err.error || `导出失败（HTTP ${res.status}）`;
      setHint(msg, true);
      toast(msg, true);
      return;
    }
    const blob = await res.blob();
    const dis = res.headers.get("Content-Disposition") || "";
    let name = `report.${format}`;
    const m = /filename\*=UTF-8''([^;\n]+)|filename="([^"]+)"/i.exec(dis);
    if (m) name = decodeURIComponent((m[1] || m[2]).trim());
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = name;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
    // 立即 revoke 会导致部分浏览器取消下载，延迟释放
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 120000);
    const okMsg = `已开始下载：${name}`;
    setHint(okMsg);
    toast(okMsg, false);
  } catch (e) {
    const msg = e.message || "导出请求失败";
    setHint(msg, true);
    toast(msg, true);
  }
}

function main() {
  $("#btnFillDemo")?.addEventListener("click", fillDemo);
  $("#btnExportDocx")?.addEventListener("click", () => exportReportFile("docx"));
  $("#btnExportPdf")?.addEventListener("click", () => exportReportFile("pdf"));
  $("#btnExportMd")?.addEventListener("click", () => exportReportFile("md"));
  $("#btnHistoryRefresh")?.addEventListener("click", () => loadServerHistoryOptions());
  $("#btnApplyHistory")?.addEventListener("click", () => applySelectedHistoryMerged().catch(() => setHint("加载所选记录失败，请重试。")));

  $("#btnHistorySelectAll")?.addEventListener("click", () => {
    $$('#historyList input[name="historyPick"]').forEach((cb) => {
      cb.checked = true;
    });
    syncHistoryItemCheckedClass();
  });
  $("#btnHistoryClearSel")?.addEventListener("click", () => {
    $$('#historyList input[name="historyPick"]').forEach((cb) => {
      cb.checked = false;
    });
    syncHistoryItemCheckedClass();
  });

  $("#historyList")?.addEventListener("change", (e) => {
    const t = e.target;
    if (t && t.matches && t.matches('input[type="checkbox"][name="historyPick"]')) {
      syncHistoryItemCheckedClass();
    }
  });

  touchFooterGenerated();
  loadServerHistoryOptions();

  try {
    const raw = sessionStorage.getItem("report_seed");
    if (raw) {
      sessionStorage.removeItem("report_seed");
      const seed = JSON.parse(raw);
      const hid = seed && seed.history_id != null ? String(seed.history_id) : null;
      if (hid) {
        const t = setInterval(() => {
          const cb = [...$$('#historyList input[name="historyPick"]')].find((c) => c.value === hid);
          if (cb) {
            cb.checked = true;
            syncHistoryItemCheckedClass();
            applySelectedHistoryMerged().catch(() => {});
            clearInterval(t);
          }
        }, 200);
        setTimeout(() => clearInterval(t), 5000);
      }
    }
  } catch (_) {}
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => main());
} else {
  main();
}
