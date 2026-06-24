
let currentFile = null;
let currentModelId = null;
let currentModelIds = [];
let queue = [];
let queueRunning = false;
let queueStopRequested = false;

let rtSingleDetectBusy = false;
let activeObjectUrls = [];
let meCache = null;
let meCacheAt = 0;

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

async function getMeCached() {
  const now = Date.now();
  if (meCache && now - meCacheAt < 30_000) return meCache;
  try {
    const res = await fetch("/api/me");
    const data = await res.json().catch(() => ({}));
    meCache = data || { logged_in: false };
  } catch (_) {
    meCache = { logged_in: false };
  }
  meCacheAt = now;
  return meCache;
}


function toast(msg, isError = false) {
  const el = $("#toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.toggle("error", isError);
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2600);
}


$$(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    $$(".tab-btn").forEach((b) => b.classList.remove("active"));
    $$(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    $(`#${btn.dataset.tab}`).classList.add("active");
  });
});


$("#confSlider")?.addEventListener("input", (e) => {
  $("#confVal").textContent = parseFloat(e.target.value).toFixed(2);
});
$("#iouSlider")?.addEventListener("input", (e) => {
  $("#iouVal").textContent = parseFloat(e.target.value).toFixed(2);
});

function getConfIouValues() {
  const confSlider = $("#confSlider");
  const iouSlider = $("#iouSlider");
  const confHidden = $("#conf");
  const iouHidden = $("#iou");
  const conf = confSlider ? confSlider.value : confHidden ? confHidden.value : "0.25";
  const iou = iouSlider ? iouSlider.value : iouHidden ? iouHidden.value : "0.45";
  
  let mm_per_pixel = null;
  try {
    const el = document.getElementById("mmPerPixel");
    const raw = el ? String(el.value || "").trim() : "";
    if (raw) {
      const v = Number(raw);
      if (Number.isFinite(v) && v > 0) mm_per_pixel = v;
    }
  } catch (_) {}
  return { conf, iou, mm_per_pixel };
}


function formatQuantLengthWidthMm(q, data) {
  if (!q) return "-";
  const lm = Number(q.length_mm);
  const wm = Number(q.max_width_mm);
  if (Number.isFinite(lm) && Number.isFinite(wm) && lm >= 0 && wm >= 0) {
    return `${lm.toFixed(2)}mm / ${wm.toFixed(2)}mm`;
  }
  const p = data?.params || {};
  const mmpp = Number(data?.mm_per_pixel ?? p.mm_per_pixel ?? p.scale_mm_per_pixel);
  if (!(Number.isFinite(mmpp) && mmpp > 0)) return "-";
  const lp = Number(q.length_px);
  const mx = Number(q.max_width_px);
  if (Number.isFinite(lp) && Number.isFinite(mx)) {
    return `${(lp * mmpp).toFixed(2)}mm / ${(mx * mmpp).toFixed(2)}mm`;
  }
  return "-";
}


const uploadZone = $("#uploadZone");
const fileInput = $("#fileInput");

uploadZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadZone.classList.add("dragover");
});
uploadZone.addEventListener("dragleave", () => {
  uploadZone.classList.remove("dragover");
});
uploadZone.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadZone.classList.remove("dragover");
  if (e.dataTransfer.files.length) handleFiles(Array.from(e.dataTransfer.files));
});

fileInput.addEventListener("change", () => {
  if (fileInput.files.length) handleFiles(Array.from(fileInput.files));
});

function handleFiles(files) {
  const MAX_TASKS = 50;
  let items = (files || []).filter(
    (f) => f && f.type && (f.type.startsWith("image/") || f.type.startsWith("video/"))
  );
  if (!items.length) {
    toast("请上传图片或视频文件", true);
    return;
  }
  if (items.length > MAX_TASKS) {
    toast(`一次最多允许上传 ${MAX_TASKS} 个文件，已自动截取前 ${MAX_TASKS} 个`, true);
    items = items.slice(0, MAX_TASKS);
  }

  
  try {
    activeObjectUrls.forEach((u) => URL.revokeObjectURL(u));
  } catch (_) {}
  activeObjectUrls = [];

  
  queue = items.map((f) => ({ id: `${Date.now()}_${Math.random().toString(16).slice(2)}`, file: f, status: "pending" }));
  currentFile = items[0];
  showPreview(queue, 0);
  if (isRealtimePage()) renderRealtimeSidepanelSkeleton();
  syncResultPanelForActiveQueueTask();
}

function showPreview(items, activeIndex = 0) {
  const strip = $("#previewStrip");
  if (!strip) return;
  strip.style.display = "flex";
  strip.innerHTML = "";

  const arr = Array.isArray(items) ? items : [{ file: items }];
  arr.forEach((it, idx) => {
    const thumb = document.createElement("div");
    thumb.className = `thumb ${idx === activeIndex ? "active" : ""}`;
    thumb.dataset.queueIndex = String(idx);

    const img = document.createElement("img");
    const url = URL.createObjectURL(it.file);
    activeObjectUrls.push(url);
    img.src = url;
    thumb.appendChild(img);

    
    if (it.status) {
      const dot = document.createElement("span");
      dot.style.cssText =
        "position:absolute;right:6px;top:6px;width:10px;height:10px;border-radius:50%;background:#9ca3af;border:2px solid #fff";
      if (it.status === "running") dot.style.background = "#007BFF";
      if (it.status === "done") dot.style.background = "#16a34a";
      if (it.status === "error") dot.style.background = "#ef4444";
      thumb.style.position = "relative";
      thumb.appendChild(dot);
    }

    thumb.addEventListener("click", () => {
      currentFile = it.file;
      showPreview(arr, idx);
      showLivePreview(it.file);
      syncResultPanelForActiveQueueTask();
    });

    strip.appendChild(thumb);
  });

  showLivePreview(arr[activeIndex]?.file);
  updateQueueInfo();
  adjustRealtimeViewportFit();
}

function showLivePreview(file) {
  const live = $("#liveImg");
  if (!live) return; 
  if (!file) return;
  const liveVideo = $("#liveVideo");
  const url = URL.createObjectURL(file);
  activeObjectUrls.push(url);
  if (file.type && file.type.startsWith("video/")) {
    
    live.classList.remove("is-visible");
    live.src = "";
    if (liveVideo) {
      liveVideo.src = url;
      liveVideo.style.display = "block";
      try { liveVideo.currentTime = 0; } catch (_) {}
    }
  } else {
    
    if (liveVideo) {
      try { liveVideo.pause(); } catch (_) {}
      liveVideo.src = "";
      liveVideo.style.display = "none";
    }
    live.src = url;
    live.classList.add("is-visible");
  }
  if (uploadZone) uploadZone.style.display = "none";
  adjustRealtimeViewportFit();
}

function updateQueueInfo() {
  const el = $("#queueInfo");
  if (!el) return;
  const total = queue.length;
  const done = queue.filter((t) => t.status === "done").length;
  const err = queue.filter((t) => t.status === "error").length;
  el.innerHTML = `
    队列：${total}
    （完成 <span class="queue-info__done">${done}</span>
    / 失败 <span class="queue-info__err">${err}</span>）
  `.replace(/\s+/g, " ").trim();
}

function isRealtimePage() {
  return !!$("#queueInfo");
}

function isRealtimeDetectionBusy() {
  return isRealtimePage() && (queueRunning || rtSingleDetectBusy);
}

let rtClassCatalog = null; 
let rtSideStats = null; 

function fallbackRealtimeClassOrder() {
  
  return ["裂缝", "钢筋外露", "剥落", "破损", "白华"];
}

function fallbackRealtimeStatColors() {
  return {
    裂缝: "#ef4444",
    钢筋外露: "#facc15",
    剥落: "#eab308",
    破损: "#8b5a2b",
    白华: "#3b82f6",
  };
}

function applyRtClassCatalogPayload(payload) {
  rtClassCatalog = payload && Array.isArray(payload.items) ? payload : null;
  if (isRealtimePage()) renderClassCatalog();
}

async function ensureRtClassCatalogLoaded() {
  if (rtClassCatalog) return;
  try {
    const res = await fetch("/api/detection-classes");
    if (!res.ok) return;
    const data = await res.json();
    applyRtClassCatalogPayload(data);
  } catch (_) {}
}

function renderClassCatalog() {
  const el = $("#classCatalog");
  if (!el) return;
  const items = (rtClassCatalog && rtClassCatalog.items) || [];
  if (!items.length) {
    el.innerHTML = `<div class="class-catalog-title">全部类别</div><div class="class-line"><div class="class-cn" style="color:var(--text2);font-weight:700">加载中…</div></div>`;
    return;
  }
  const st = rtSideStats || {};
  const dashMode = st && Object.values(st).some((v) => v === "-");
  const hasStats = st && Object.keys(st).length > 0;
  el.innerHTML = `
    <div class="class-catalog-title">全部类别（${items.length}）</div>
    ${items
      .map((it) => {
        const cn = it.class_cn || "-";
        const en = it.class_en || "";
        const dot = it.color || "#888";
        let countText = "-";
        if (hasStats) {
          if (dashMode) countText = "-";
          else countText = `${Object.prototype.hasOwnProperty.call(st, cn) ? st[cn] : 0}`;
        }
        return `
          <div class="class-line" title="${en}">
            <span class="class-dot" style="background:${dot}"></span>
            <div class="class-cn">${cn}</div>
            <div class="class-en">${en}</div>
            <div class="class-count">${countText}</div>
          </div>
        `;
      })
      .join("")}
  `;
}

function realtimeStatColors() {
  const base = fallbackRealtimeStatColors();
  const items = (rtClassCatalog && rtClassCatalog.items) || [];
  if (!items.length) return base;
  const m = { ...base };
  for (const it of items) {
    const cn = it.class_cn;
    if (!cn) continue;
    if (it.color) m[cn] = it.color;
  }
  return m;
}

function realtimeClassOrder() {
  const items = (rtClassCatalog && rtClassCatalog.items) || [];
  if (!items.length) return fallbackRealtimeClassOrder();
  return items.map((it) => it.class_cn).filter(Boolean);
}

function setRealtimeInferChips({ sizeText, totalText, msText } = {}) {
  if (!isRealtimePage()) return;
  const szEl = $("#inferSize");
  const totEl = $("#inferTotal");
  const msEl = $("#inferMs");
  if (szEl) szEl.textContent = sizeText ?? "-";
  if (totEl) totEl.textContent = totalText ?? "-";
  if (msEl) {
    const v = msText ?? "-";
    if (v === "检测中…") {
      msEl.innerHTML = `<span class="infer-loading"><span class="mini-spinner" aria-hidden="true"></span>检测中</span>`;
    } else {
      msEl.textContent = v;
    }
  }
}

function renderRealtimeSidepanelStatsHTML({ stats, total }) {
  const totalLabel = total == null ? "0" : `${total}`;
  rtSideStats = stats || null;
  if (isRealtimePage()) renderClassCatalog();

  return `
    <div class="stat-pill stat-pill--full">
      <span style="color:var(--primary-light)">总计</span>
      <span class="count">${totalLabel}</span> 个病害
    </div>
  `;
}


function renderRealtimeSidepanelSkeleton() {
  if (!isRealtimePage()) return;
  const statsRow = $("#statsRow");
  if (!statsRow) return;

  statsRow.innerHTML = renderRealtimeSidepanelStatsHTML({
    stats: Object.fromEntries(realtimeClassOrder().map((k) => [k, 0])),
    total: 0,
  });

  setRealtimeInferChips({ sizeText: "-", totalText: "-", msText: "-" });
}

function renderRealtimeSidepanelLoading() {
  if (!isRealtimePage()) return;
  const statsRow = $("#statsRow");
  if (!statsRow) return;

  statsRow.innerHTML = renderRealtimeSidepanelStatsHTML({
    stats: Object.fromEntries(realtimeClassOrder().map((k) => [k, "-"])),
    total: "-",
  });

  setRealtimeInferChips({ sizeText: "-", totalText: "-", msText: "检测中…" });
}


function syncResultPanelForActiveQueueTask() {
  if (!queue.length || !$("#queueInfo")) return;
  const strip = $("#previewStrip");
  if (!strip) return;
  const active = strip.querySelector(".thumb.active");
  if (!active) return;
  const idx = Number(active.dataset.queueIndex);
  if (Number.isNaN(idx) || idx < 0 || idx >= queue.length) return;
  const task = queue[idx];
  if (task.status === "done" && task.result) {
    if (task.result.__compare) renderCompareResult(task.result.payload, { persist: false, scroll: false });
    else renderResult(task.result.payload, { persist: false, scroll: false });
  } else {
    $("#resultArea").style.display = "none";
    const ca = $("#compareArea");
    if (ca) ca.style.display = "none";
    if (task.status === "running") renderRealtimeSidepanelLoading();
    else renderRealtimeSidepanelSkeleton();
  }
}

function attachDetectionToQueueTask(file, res) {
  const t = queue.find((q) => q.file === file);
  if (t) {
    t.status = "done";
    t.result = res;
  }
}

function adjustRealtimeViewportFit() {
  
  const page = document.querySelector(".page-realtime");
  if (!page) return;
  const viewer = $("#viewer") || document.querySelector(".page-realtime .viewer");
  const side = document.querySelector(".page-realtime .sidepanel");
  if (!viewer || !side) return;
  const strip = $("#previewStrip");
  const footer = document.querySelector(".footer");

  
  requestAnimationFrame(() => {
    const footerH = footer ? footer.getBoundingClientRect().height : 0;
    const bottomLimit = window.innerHeight - footerH - 8;
    const top = viewer.getBoundingClientRect().top;
    const stripH =
      strip && strip.style.display !== "none" ? strip.getBoundingClientRect().height + 10 : 0;
    const available = bottomLimit - top - stripH;
    const h = Math.max(220, Math.min(Math.floor(available), 560));
    viewer.style.height = `${h}px`;
    
    side.style.height = "auto";
    side.style.minHeight = `${h}px`;
  });
}


$("#detectBtn").addEventListener("click", runDetection);

async function runDetection() {
  if (!currentFile) {
    toast("请先上传图片", true);
    return;
  }
  const modelIds = getSelectedModelIds();
  if (!modelIds.length) {
    toast("请选择模型版本", true);
    return;
  }
  if (currentFile.type && currentFile.type.startsWith("video/") && modelIds.length > 1) {
    toast("视频检测暂仅支持单模型，请只选择一个模型", true);
    return;
  }
  
  const isRealtime = !!$("#queueInfo");
  const batch = isRealtime && queue.length > 1;
  const btn = $("#detectBtn");

  if (!batch) {
    btn.disabled = true;
    $("#spinner").classList.add("show");
    $("#resultArea").style.display = "none";
    const compareArea = $("#compareArea");
    if (compareArea) compareArea.style.display = "none";
    if (isRealtime) renderRealtimeSidepanelLoading();
    rtSingleDetectBusy = true;
    try {
      const data = await detectOne(currentFile, modelIds);
      attachDetectionToQueueTask(currentFile, data);
      if (queue.length) showPreview(queue, queue.findIndex((q) => q.file === currentFile));
      if (data.__compare) renderCompareResult(data.payload);
      else renderResult(data.payload);
    } catch (e) {
      toast(e.message || "请求失败", true);
      if (isRealtime) renderRealtimeSidepanelSkeleton();
    } finally {
      rtSingleDetectBusy = false;
      btn.disabled = false;
      $("#spinner").classList.remove("show");
    }
    return;
  }

  
  if (queueRunning) return;
  queueRunning = true;
  queueStopRequested = false;
  btn.disabled = true;
  $("#resultArea").style.display = "none";
  const compareArea = $("#compareArea");
  if (compareArea) compareArea.style.display = "none";

  try {
    for (let i = 0; i < queue.length; i++) {
      if (queueStopRequested) break;
      const task = queue[i];
      if (!task || task.status === "done") continue;
      task.status = "running";
      showPreview(queue, i);
      $("#spinner").classList.add("show");
      updateQueueInfo();
      renderRealtimeSidepanelLoading();

      try {
        const res = await detectOne(task.file, modelIds);
        task.status = "done";
        task.result = res;
        showPreview(queue, i);
        if (res.__compare) renderCompareResult(res.payload, { scroll: false });
        else renderResult(res.payload, { scroll: false });
      } catch (e) {
        task.status = "error";
        task.error = e?.message || "failed";
        toast(`第 ${i + 1} 张失败：${task.error}`, true);
        renderRealtimeSidepanelSkeleton();
      } finally {
        $("#spinner").classList.remove("show");
        updateQueueInfo();
        showPreview(queue, i);
      }
    }
  } finally {
    queueRunning = false;
    btn.disabled = false;
    updateQueueInfo();
    syncResultPanelForActiveQueueTask();
    $("#spinner").classList.remove("show");
    if (queue.length > 1) {
      const ra = $("#resultArea");
      const ca = $("#compareArea");
      if (ra && ra.style.display !== "none") ra.scrollIntoView({ behavior: "smooth", block: "start" });
      else if (ca && ca.style.display !== "none") ca.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }
}

async function detectOne(file, modelIds) {
  const fd = new FormData();
  const isVideo = file && file.type && file.type.startsWith("video/");
  if (isVideo) fd.append("video", file);
  else fd.append("image", file);
  const { conf, iou, mm_per_pixel } = getConfIouValues();
  fd.append("conf", conf);
  fd.append("iou", iou);
  if (mm_per_pixel != null) fd.append("mm_per_pixel", String(mm_per_pixel));

  if (modelIds.length === 1) {
    fd.append("model_id", modelIds[0]);
    const res = await fetch(isVideo ? "/api/detect-video" : "/api/detect", { method: "POST", body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || "Detection failed");
    }
    return { __compare: false, payload: await res.json() };
  }

  fd.append("model_ids", modelIds.join(","));
  const res = await fetch("/api/detect-compare", { method: "POST", body: fd });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || "Compare failed");
  }
  return { __compare: true, payload: await res.json() };
}

function getSelectedModelIds() {
  const items = $("#modelSelectItems");
  if (!items) return currentModelId ? [currentModelId] : ["model1"];
  const values = Array.from(items.querySelectorAll("input[type=checkbox][data-model-id]"))
    .filter((cb) => cb.checked)
    .map((cb) => cb.getAttribute("data-model-id"))
    .filter(Boolean);
  return values.length ? values : (currentModelId ? [currentModelId] : ["model1"]);
}

function renderResult(data, opts = {}) {
  const persist = opts.persist !== false;
  const scroll = opts.scroll !== false;

  $("#resultArea").style.display = "block";
  const compareArea = $("#compareArea");
  if (compareArea) compareArea.style.display = "none";
  $("#origImg").src = data.original_url;
  $("#resImg").src = data.image_url;

  
  try {
    const a = document.getElementById("openResultsBtn");
    if (a) {
      const u = new URL("/results", location.origin);
      
      const raw = localStorage.getItem("last_detection_payload");
      const p = raw ? JSON.parse(raw) : null;
      if (p && p.history_id != null) {
        u.searchParams.set("history_id", String(p.history_id));
      } else {
        u.searchParams.set("original_url", data.original_url || "");
        u.searchParams.set("result_url", data.image_url || "");
        if (data.model_label) u.searchParams.set("model_label", data.model_label);
        const ms = data.forward_ms ?? data.inference_ms;
        if (ms != null) u.searchParams.set("inference_ms", String(ms));
      }
      a.setAttribute("href", u.pathname + "?" + u.searchParams.toString());
    }
  } catch (_) {}

  
  try {
    localStorage.setItem(
      "last_detection_payload",
      JSON.stringify({
        original_url: data.original_url,
        result_url: data.image_url,
        model_id: data.model_id,
        model_label: data.model_label || null,
        inference_ms: data.inference_ms,
        forward_ms: data.forward_ms,
        stats: data.stats,
        detections: data.detections,
      })
    );
  } catch (_) {}

  if (persist) {
    
    (async () => {
      try {
        const me = await getMeCached();
        if (!me.logged_in) return;
        
        let modelLabel = data.model_label || null;
        if (!modelLabel) {
          try {
            const ms = await fetch("/api/models").then((r) => r.json());
            const found = (ms.models || []).find((m) => m.id === (data.model_id || currentModelId));
            modelLabel = found ? found.label : null;
          } catch (_) {}
        }

        const tsNow = Date.now();
        const mmpp = (() => { try { return Number(getConfIouValues().mm_per_pixel); } catch (_) { return null; } })();
        const res = await fetch("/api/history", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ts: tsNow,
            model_id: data.model_id || currentModelId || null,
            model_label: modelLabel,
            total: data.total,
            inference_ms: data.inference_ms,
            stats_json: JSON.stringify(data.stats || {}),
            original_url: data.original_url,
            result_url: data.image_url,
            conf: (() => { try { return Number(getConfIouValues().conf); } catch (_) { return null; } })(),
            iou: (() => { try { return Number(getConfIouValues().iou); } catch (_) { return null; } })(),
            params_json: (() => { try { const p = getConfIouValues(); return JSON.stringify({ conf: Number(p.conf), iou: Number(p.iou), mm_per_pixel: p.mm_per_pixel }); } catch (_) { return null; } })(),
            ...(mmpp != null && Number.isFinite(mmpp) ? { scale_mm_per_pixel: mmpp } : {}),
          }),
        });
        const saved = await res.json().catch(() => ({}));
        const hid = saved && saved.id != null ? saved.id : null;

        
        try {
          const profileRaw = localStorage.getItem("bridge_profile");
          const profile = profileRaw ? JSON.parse(profileRaw) : null;
          const userId = profile && profile.userId ? profile.userId : null;
          if (userId) {
            const key = `bridge_history_${userId}`;
            const raw = localStorage.getItem(key);
            const arr = raw ? JSON.parse(raw) : [];
            const item = {
              ts: tsNow,
              model_id: data.model_id || currentModelId || null,
              stats: data.stats || {},
              total: data.total,
              inference_ms: data.inference_ms,
              original_url: data.original_url,
              result_url: data.image_url,
            };
            const next = Array.isArray(arr) ? [item, ...arr].slice(0, 200) : [item];
            localStorage.setItem(key, JSON.stringify(next));
          }
        } catch (_) {}

        
        if (hid != null) {
          try {
            const raw = localStorage.getItem("last_detection_payload");
            const p = raw ? JSON.parse(raw) : null;
            if (p && !p.history_id) {
              p.history_id = hid;
              if (!p.model_label && modelLabel) p.model_label = modelLabel;
              localStorage.setItem("last_detection_payload", JSON.stringify(p));
            }
          } catch (_) {}
        }
      } catch (_) {}
    })();
  }

  
  const statsRow = $("#statsRow");
  const colors = realtimeStatColors();
  const classOrder = realtimeClassOrder();
  const stats = data.stats || {};
  if (isRealtimePage() && statsRow) {
    statsRow.innerHTML = renderRealtimeSidepanelStatsHTML({
      stats,
      total: data.total,
    });
  } else if (statsRow) {
    statsRow.innerHTML = `
    <div class="stat-pill">
      <span style="color:var(--primary-light)">总计</span>
      <span class="count">${data.total}</span> 个病害
    </div>
    ${Object.entries(stats)
      .map(
        ([k, v]) => `
      <div class="stat-pill">
        <span style="width:10px;height:10px;border-radius:50%;background:${colors[k] || "#888"}"></span>
        <span>${k}</span>
        <span class="count">${v}</span>
      </div>
    `
      )
      .join("")}
    <div class="stat-pill">
      <span style="color:var(--text-sec)">耗时</span>
      <span class="count">${data.forward_ms ?? data.inference_ms}</span> ms
    </div>
  `;
  }

  
  const tbody = $("#detBody");
  tbody.innerHTML = data.detections
    .map(
      (d, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><span style="display:inline-flex;align-items:center;gap:6px">
        <span style="width:8px;height:8px;border-radius:50%;background:${colors[d.class_cn] || "#888"}"></span>
        ${d.class_cn}
      </span></td>
      <td style="color:var(--text-sec)">${d.class}</td>
      <td>
        <span class="conf-bar" style="width:${d.confidence * 100}px"></span>
        ${(d.confidence * 100).toFixed(1)}%
      </td>
      <td style="font-family:monospace;font-size:.8rem;color:var(--text-sec)">${
        formatQuantLengthWidthMm(d.quant, data)
      }</td>
      <td style="font-family:monospace;font-size:.8rem;color:var(--text-sec)">${(d.bbox || []).map((v) => Math.round(v)).join(", ")}</td>
    </tr>
  `
    )
    .join("");

  const sz = data.image_size;
  if (isRealtimePage()) {
    setRealtimeInferChips({
      sizeText: `${sz.width}×${sz.height}`,
      totalText: `${data.total}`,
      msText: `${data.forward_ms ?? data.inference_ms} ms`,
    });
  } else {
    const info = $("#inferenceInfo");
    if (info)
      info.textContent = `图像尺寸: ${sz.width}×${sz.height} | 检测到 ${data.total} 个病害目标 | 耗时 ${data.forward_ms ?? data.inference_ms} ms`;
  }

  const hint = $("#resultTaskHint");
  if (hint) {
    if (queue.length > 1) {
      const t = queue.find(
        (q) => q.result && !q.result.__compare && q.result.payload && q.result.payload.original_url === data.original_url
      );
      hint.textContent = t ? `当前：第 ${queue.indexOf(t) + 1} 张 · ${t.file.name}` : "";
    } else hint.textContent = "";
  }

  if (scroll) $("#resultArea").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderCompareResult(payload, opts = {}) {
  const persist = opts.persist !== false;
  const scroll = opts.scroll !== false;

  const compareArea = $("#compareArea");
  const grid = $("#compareGrid");
  const info = $("#compareInfo");
  const head = $("#compareHead");
  const body = $("#compareBody");
  if (!compareArea || !grid) return;

  $("#resultArea").style.display = "none";
  compareArea.style.display = "block";
  let infoLine = `对比模型数: ${payload.count} | 原图相同，结果图为各模型推理输出`;
  if (queue.length > 1 && payload.original_url) {
    const t = queue.find(
      (q) => q.result && q.result.__compare && q.result.payload && q.result.payload.original_url === payload.original_url
    );
    if (t) infoLine += ` | 当前：第 ${queue.indexOf(t) + 1} 张 · ${t.file.name}`;
  }
  if (info) info.textContent = infoLine;

  const singleHint = $("#resultTaskHint");
  if (singleHint) singleHint.textContent = "";

  
  if (isRealtimePage()) {
    const statsRow = $("#statsRow");
    const colors2 = realtimeStatColors();
    const classOrder2 = realtimeClassOrder();
    const results = payload.results || [];
    const totals = results.map((r) => Number(r.total ?? 0));
    const sumTotal = totals.reduce((a, b) => a + b, 0);
    const agg = {};
    for (const r of results) {
      const st = r.stats || {};
      for (const k of classOrder2) agg[k] = (agg[k] || 0) + (Number(st[k]) || 0);
    }
    const times = results.map((r) => r.forward_ms ?? r.inference_ms).filter((v) => v != null);
    const timeNums = times.map((x) => Number(x)).filter((n) => Number.isFinite(n));
    const maxMs = timeNums.length ? Math.max(...timeNums) : null;
    const sz0 = results[0] && results[0].image_size ? results[0].image_size : null;
    const sizeText0 =
      sz0 && sz0.width && sz0.height ? `${sz0.width}×${sz0.height}` : "-";

    if (statsRow) {
      statsRow.innerHTML = renderRealtimeSidepanelStatsHTML({
        stats: agg,
        total: sumTotal,
      });
    }
    setRealtimeInferChips({
      sizeText: sizeText0,
      totalText: `${sumTotal}`,
      msText: maxMs == null ? "-" : `${maxMs} ms`,
    });
  }

  const colors = realtimeStatColors();
  const classOrder = realtimeClassOrder();
  if (head && body) {
    head.innerHTML = `
      <tr>
        <th>模型</th>
        <th>总数</th>
        <th>平均置信度</th>
        ${classOrder.map((c) => `<th>${c}</th>`).join("")}
        <th>耗时</th>
      </tr>
    `;
    body.innerHTML = (payload.results || [])
      .map((r) => {
        const stats = r.stats || {};
        const dets = r.detections || [];
        const avgConf =
          dets.length > 0
            ? dets.reduce((s, d) => s + (Number(d.confidence) || 0), 0) / dets.length
            : null;
        return `
          <tr>
            <td style="font-weight:800">${r.model_label || r.model_id}</td>
            <td>${r.total ?? 0}</td>
            <td>${avgConf == null ? "-" : (avgConf * 100).toFixed(1) + "%"}</td>
            ${classOrder
              .map(
                (c) =>
                  `<td><span style="display:inline-flex;align-items:center;gap:6px"><span style="width:8px;height:8px;border-radius:50%;background:${colors[c] || "#888"}"></span>${stats[c] || 0}</span></td>`
              )
              .join("")}
            <td>${(r.forward_ms ?? r.inference_ms) ?? "-"} ms</td>
          </tr>
        `;
      })
      .join("");
  }

  grid.innerHTML = (payload.results || [])
    .map((r) => {
      const statsText = Object.entries(r.stats || {})
        .sort((a, b) => b[1] - a[1])
        .map(([k, v]) => `<span class="badge"><span style="width:8px;height:8px;border-radius:50%;background:${colors[k] || "#888"}"></span>${k}${v}</span>`)
        .join(" ");

      return `
        <div class="card compare-card">
          <div class="compare-head">
            <div style="font-weight:900">${r.model_label || r.model_id}</div>
            <div style="color:var(--text-sec);font-size:.85rem">${(r.forward_ms ?? r.inference_ms)} ms | ${r.total} 个</div>
          </div>
          <div class="compare-body">
            <div class="result-images" style="grid-template-columns:1fr 1fr;margin-bottom:12px">
              <div class="img-box">
                <span class="img-label">原始图像</span>
                <img src="${payload.original_url}" alt="original"/>
              </div>
              <div class="img-box">
                <span class="img-label">检测结果</span>
                <img src="${r.image_url}" alt="result"/>
              </div>
            </div>
            <div class="mini-row">${statsText || "<span style='color:var(--text-sec)'>无检测结果</span>"}</div>
          </div>
        </div>
      `;
    })
    .join("");

  if (scroll) compareArea.scrollIntoView({ behavior: "smooth", block: "start" });

  if (persist) {
    
    (async () => {
      try {
        const me = await getMeCached();
        if (!me.logged_in) return;
        const now = Date.now();
        for (const r of payload.results || []) {
          await fetch("/api/history", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              ts: now,
              model_id: r.model_id,
              model_label: r.model_label,
              total: r.total,
              inference_ms: r.inference_ms,
              stats_json: JSON.stringify(r.stats || {}),
              original_url: payload.original_url,
              result_url: r.image_url,
            }),
          });
        }
      } catch (_) {}
    })();
  }
}


async function loadModels() {
  const items = $("#modelSelectItems");
  const btn = $("#modelSelectBtn");
  const panel = $("#modelSelectPanel");
  const okBtn = $("#modelSelectOkBtn");
  const allBtn = $("#modelSelectAllBtn");
  const clearBtn = $("#modelSelectClearBtn");
  try {
    const res = await fetch("/api/models");
    const data = await res.json();
    const list = data.models || [];
    currentModelId = data.default || (data.models[0] && data.models[0].id);
    currentModelIds = currentModelId ? [currentModelId] : [];

    if (data.class_catalog) applyRtClassCatalogPayload(data.class_catalog);
    else if (isRealtimePage()) await ensureRtClassCatalogLoaded();
    if (isRealtimePage() && !isRealtimeDetectionBusy()) {
      
      renderRealtimeSidepanelSkeleton();
    }

    if (items) {
      items.innerHTML = list
        .map((m) => {
          const checked = m.id === currentModelId ? "checked" : "";
          return `
            <label class="multi-select-item">
              <input type="checkbox" ${checked} data-model-id="${m.id}"/>
              <div>
                <div class="label">${m.label}</div>
                <div class="sub">${m.id}</div>
              </div>
            </label>
          `;
        })
        .join("");
    }

    function updateBtnText() {
      const ids = getSelectedModelIds();
      if (!btn) return;
      if (!ids.length) btn.textContent = "请选择";
      else if (ids.length === 1) {
        const found = list.find((m) => m.id === ids[0]);
        btn.textContent = found ? found.label : ids[0];
      } else {
        btn.textContent = `已选择 ${ids.length} 个模型`;
      }
    }

    function openPanel() {
      if (!panel) return;
      panel.style.display = "block";
      updateBtnText();
    }
    function closePanel() {
      if (!panel) return;
      panel.style.display = "none";
    }

    if (btn) {
      btn.addEventListener("click", () => {
        if (!panel) return;
        panel.style.display = panel.style.display === "none" ? "block" : "none";
        updateBtnText();
      });
    }
    document.addEventListener("click", (e) => {
      if (!panel || !btn) return;
      const wrap = $("#modelSelectWrap");
      if (wrap && !wrap.contains(e.target)) closePanel();
    });

    if (okBtn) {
      okBtn.addEventListener("click", () => {
        const ids = getSelectedModelIds();
        currentModelIds = ids;
        currentModelId = ids[0] || currentModelId || "model1";
        updateBtnText();
        closePanel();
      });
    }
    if (allBtn) {
      allBtn.addEventListener("click", () => {
        if (!items) return;
        items.querySelectorAll("input[type=checkbox][data-model-id]").forEach((cb) => (cb.checked = true));
        updateBtnText();
      });
    }
    if (clearBtn) {
      clearBtn.addEventListener("click", () => {
        if (!items) return;
        items.querySelectorAll("input[type=checkbox][data-model-id]").forEach((cb) => (cb.checked = false));
        updateBtnText();
      });
    }

    updateBtnText();

  } catch (e) {
    console.error("Failed to load models:", e);
    if (items) items.innerHTML = `<div class="multi-select-empty">加载失败</div>`;
    if (btn) btn.textContent = "加载失败";
    if (isRealtimePage() && !isRealtimeDetectionBusy()) renderRealtimeSidepanelSkeleton();
  }
}


async function prefillDetectFromHistoryQuery() {
  if (!isRealtimePage()) return;
  const u = new URL(location.href);
  let hid = u.searchParams.get("history_id");
  if (!hid) {
    try {
      hid = sessionStorage.getItem("detect_from_history_id");
    } catch (_) {
      hid = null;
    }
  }
  if (!hid) return;
  try {
    sessionStorage.removeItem("detect_from_history_id");
  } catch (_) {}
  try {
    const clean = new URL(location.href);
    if (clean.searchParams.has("history_id")) {
      clean.searchParams.delete("history_id");
      const q = clean.searchParams.toString();
      history.replaceState({}, "", clean.pathname + (q ? `?${q}` : "") + clean.hash);
    }
  } catch (_) {}
  try {
    const res = await fetch(`/api/history/${encodeURIComponent(String(hid))}`);
    if (!res.ok) return;
    const data = await res.json();
    const it = data.item;
    const url = it?.original_url;
    if (!url || typeof url !== "string") return;
    const imgRes = await fetch(url, { credentials: "same-origin" });
    if (!imgRes.ok) return;
    const blob = await imgRes.blob();
    const nameFromUrl = (url.split("?")[0].split("/").pop() || "history.jpg").trim();
    const name = nameFromUrl || "history.jpg";
    const file = new File([blob], name, { type: blob.type || "image/jpeg" });
    handleFiles([file]);
    toast("已载入该条历史的原图，正在自动开始检测…");
    await new Promise((r) => requestAnimationFrame(() => r()));
    await runDetection();
  } catch (_) {
    
  }
}


async function initApp() {
  await loadModels();
  
  try {
    const el = document.getElementById("mmPerPixel");
    if (el) {
      const raw = localStorage.getItem("bridge_mm_per_pixel");
      if (raw) el.value = raw;
      el.addEventListener("change", () => {
        const v = String(el.value || "").trim();
        if (v) localStorage.setItem("bridge_mm_per_pixel", v);
        else localStorage.removeItem("bridge_mm_per_pixel");
      });
    }
  } catch (_) {}
  adjustRealtimeViewportFit();
  window.addEventListener("resize", adjustRealtimeViewportFit);

  if (isRealtimePage()) {
    await prefillDetectFromHistoryQuery();
    window.addEventListener("beforeunload", (e) => {
      if (!isRealtimeDetectionBusy()) return;
      e.preventDefault();
      e.returnValue = "";
    });
    document.addEventListener(
      "click",
      (e) => {
        const a = e.target.closest("a[href]");
        if (!a) return;
        if (a.getAttribute("target") === "_blank") return;
        let url;
        try {
          url = new URL(a.href, location.href);
        } catch {
          return;
        }
        if (url.pathname !== "/detect") return;
        if (location.pathname !== "/detect") return;
        if (!isRealtimeDetectionBusy()) return;
        e.preventDefault();
        toast("检测进行中，请勿刷新本页；请等待完成或停止队列后再操作。", true);
      },
      true
    );
  }
}

initApp();


$("#queueStopBtn")?.addEventListener("click", () => {
  if (!queueRunning) return;
  queueStopRequested = true;
  toast("已请求停止队列");
  updateQueueInfo();
});
$("#queueClearBtn")?.addEventListener("click", () => {
  if (queueRunning) return toast("队列运行中，无法清空", true);
  queue = [];
  currentFile = null;
  try {
    if (fileInput) fileInput.value = "";
  } catch (_) {}
  const strip = $("#previewStrip");
  if (strip) {
    strip.innerHTML = "";
    strip.style.display = "none";
  }
  const live = $("#liveImg");
  if (live) {
    live.src = "";
    live.classList.remove("is-visible");
    if (uploadZone) uploadZone.style.display = "flex";
  }
  $("#resultArea").style.display = "none";
  const ca = $("#compareArea");
  if (ca) ca.style.display = "none";
  updateQueueInfo();
  renderRealtimeSidepanelSkeleton();
  toast("已清空队列");
});


$("#newUploadBtn")?.addEventListener("click", () => {
  if (queueRunning) {
    queueStopRequested = true;
    toast("队列运行中，已请求停止，请稍后再上传新图片", true);
    return;
  }
  
  $("#queueClearBtn")?.click();
  
  try {
    fileInput?.click();
  } catch (_) {}
});
