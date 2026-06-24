const $ = (sel) => document.querySelector(sel);

function fmtTime(ts) {
  const d = new Date(Number(ts || 0));
  if (!Number.isFinite(d.getTime())) return "-";
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}


function formatQuantLengthWidthMm(q, payload) {
  if (!q) return "-";
  const lm = Number(q.length_mm);
  const wm = Number(q.max_width_mm);
  if (Number.isFinite(lm) && Number.isFinite(wm) && lm >= 0 && wm >= 0) {
    return `${lm.toFixed(2)}mm / ${wm.toFixed(2)}mm`;
  }
  const p = payload?.params || {};
  const mmpp = Number(payload?.mm_per_pixel ?? p.mm_per_pixel ?? p.scale_mm_per_pixel);
  if (!(Number.isFinite(mmpp) && mmpp > 0)) return "-";
  const lp = Number(q.length_px);
  const mx = Number(q.max_width_px);
  if (Number.isFinite(lp) && Number.isFinite(mx)) {
    return `${(lp * mmpp).toFixed(2)}mm / ${(mx * mmpp).toFixed(2)}mm`;
  }
  return "-";
}

function getLastPayload() {
  
  const url = new URL(location.href);
  const history_id = url.searchParams.get("history_id");
  const original_url = url.searchParams.get("original_url");
  const result_url = url.searchParams.get("result_url");
  const model_label = url.searchParams.get("model_label");
  const inference_ms = url.searchParams.get("inference_ms");
  if (history_id) {
    return { history_id: Number(history_id) };
  }
  if (original_url && result_url) {
    return {
      original_url,
      result_url,
      model_label,
      inference_ms: inference_ms ? Number(inference_ms) : null,
      stats: null,
      detections: [],
    };
  }

  
  try {
    const rawS = sessionStorage.getItem("results_payload");
    if (rawS) {
      sessionStorage.removeItem("results_payload");
      return JSON.parse(rawS);
    }
  } catch (_) {}

  
  try {
    const raw = localStorage.getItem("last_detection_payload");
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (_) {
    return null;
  }
}

function renderList(payload) {
  const statsBody = $("#statsBody");
  const detList = $("#detList");
  const meta = $("#resultMeta");
  const paramsEl = $("#resultParams");
  if (!payload) return;

  const stats = payload.stats || {};
  const dets = payload.detections || [];

  if (meta) {
    const parts = [];
    if (payload.ts) parts.push(fmtTime(payload.ts));
    if (payload.model_label) parts.push(payload.model_label);
    const ms = payload.forward_ms ?? payload.inference_ms;
    if (ms != null) parts.push(`${ms}ms`);
    meta.textContent = parts.join(" | ");
  }

  if (paramsEl) {
    const p = payload.params || {};
    const confV = p.conf != null ? p.conf : payload.conf;
    const iouV = p.iou != null ? p.iou : payload.iou;
    const bits = [];
    if (confV != null && Number.isFinite(Number(confV))) bits.push(`conf=${Number(confV).toFixed(2)}`);
    if (iouV != null && Number.isFinite(Number(iouV))) bits.push(`iou=${Number(iouV).toFixed(2)}`);
    paramsEl.textContent = bits.length ? `检测参数：${bits.join("，")}` : "";
  }

  if (statsBody) {
    const rows = Object.entries(stats)
      .sort((a, b) => b[1] - a[1])
      .map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`)
      .join("");
    statsBody.innerHTML = rows || `<tr><td colspan="2" style="color:var(--text2)">-</td></tr>`;
  }

  if (detList) {
    detList.innerHTML =
      dets
        .slice(0, 200)
        .map(
          (d, i) => {
            const qText = formatQuantLengthWidthMm(d.quant, payload);
            return `<tr><td>${i + 1}</td><td>${d.class_cn || d.class}</td><td>${((d.confidence || 0) * 100).toFixed(1)}%</td><td style="font-family:monospace;font-size:.8rem;color:var(--text2)">${qText}</td></tr>`;
          }
        )
        .join("") || `<tr><td colspan="4" style="color:var(--text2)">-</td></tr>`;
  }
}

function renderHistoryList(items, activeId) {
  const body = $("#historyBody");
  const hint = $("#historyHint");
  if (!body) return;
  const arr = Array.isArray(items) ? items : [];
  if (hint) {
    hint.textContent = arr.length ? `共 ${arr.length} 条记录，点击可查看` : "暂无历史记录";
  }
  if (!arr.length) {
    body.innerHTML = `<tr><td colspan="4" style="color:var(--text2)">-</td></tr>`;
    return;
  }
  body.innerHTML = arr
    .map((it) => {
      const id = it.id;
      const t = fmtTime(it.ts);
      const model = it.model_label || it.model_id || "-";
      const total = it.total ?? 0;
      const isActive = activeId != null && String(activeId) === String(id);
      const checked = selectedIds.has(String(id)) ? "checked" : "";
      return `<tr data-history-id="${id}" style="cursor:pointer;${isActive ? "background:rgba(0,123,255,0.08)" : ""}">
        <td><input type="checkbox" class="hist-sel" data-hid="${id}" ${checked}/></td>
        <td style="white-space:nowrap">${t}</td>
        <td title="${model}" style="max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${model}</td>
        <td style="white-space:nowrap">${total}</td>
      </tr>`;
    })
    .join("");
}

function createViewer(elWrap, elImg, elOverlay) {
  let scale = 1;
  let x = 0;
  let y = 0;
  let dragging = false;
  let last = { x: 0, y: 0 };

  const apply = () => {
    elImg.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
    if (elOverlay) elOverlay.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
  };

  const clamp = () => {
    
    const rect = elWrap.getBoundingClientRect();
    const iw = elImg.naturalWidth * scale;
    const ih = elImg.naturalHeight * scale;
    const minX = Math.min(0, rect.width - iw);
    const minY = Math.min(0, rect.height - ih);
    x = Math.max(minX - 100, Math.min(x, 100));
    y = Math.max(minY - 100, Math.min(y, 100));
  };

  const fit = () => {
    const rect = elWrap.getBoundingClientRect();
    const sw = rect.width / elImg.naturalWidth;
    const sh = rect.height / elImg.naturalHeight;
    scale = Math.min(sw, sh);
    x = (rect.width - elImg.naturalWidth * scale) / 2;
    y = (rect.height - elImg.naturalHeight * scale) / 2;
    apply();
  };

  const reset = () => {
    scale = 1;
    x = 0;
    y = 0;
    apply();
  };

  elWrap.addEventListener("wheel", (e) => {
    e.preventDefault();
    const rect = elWrap.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    const delta = -e.deltaY;
    const factor = delta > 0 ? 1.08 : 0.92;
    const next = Math.max(0.2, Math.min(scale * factor, 10));

    
    const rx = (mx - x) / scale;
    const ry = (my - y) / scale;
    scale = next;
    x = mx - rx * scale;
    y = my - ry * scale;
    clamp();
    apply();
  }, { passive: false });

  elWrap.addEventListener("mousedown", (e) => {
    dragging = true;
    elImg.style.cursor = "grabbing";
    last = { x: e.clientX, y: e.clientY };
  });
  window.addEventListener("mouseup", () => {
    dragging = false;
    elImg.style.cursor = "grab";
  });
  window.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    x += e.clientX - last.x;
    y += e.clientY - last.y;
    last = { x: e.clientX, y: e.clientY };
    clamp();
    apply();
  });

  window.addEventListener("resize", () => {
    if (elImg.complete && elImg.naturalWidth) fit();
  });

  return { fit, reset, setTransform: (nx, ny, ns) => { x = nx; y = ny; scale = ns; apply(); } };
}

function maskStrokeColor(det) {
  const key = det?.class || det?.class_cn || "";
  const map = {
    "Crack-Detection": "#ef4444",
    "裂缝": "#ef4444",
    "Spalling": "#f97316",
    "剥落": "#f97316",
    "Exposed Rebar": "#facc15",
    "钢筋外露": "#facc15",
    "Break": "#8b5a2b",
    "断裂": "#8b5a2b",
    "Efflorescence": "#3b82f6",
    "泛碱": "#3b82f6",
  };
  return map[key] || "#007BFF";
}

function drawMasks(canvas, payload) {
  if (!canvas) return;
  const dets = payload?.detections || [];
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  for (const d of dets) {
    const pts = d.mask;
    if (!Array.isArray(pts) || pts.length < 3) continue;
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    ctx.closePath();
    ctx.strokeStyle = maskStrokeColor(d);
    ctx.lineWidth = 2;
    ctx.globalAlpha = 0.95;
    ctx.stroke();
  }
  ctx.globalAlpha = 1;
}

async function tryLoadDetectionsFromResultJson(resultUrl) {
  if (!resultUrl || typeof resultUrl !== "string") return null;
  const jsonUrl = resultUrl.replace(/\.jpg$/i, ".json").replace(/\.jpeg$/i, ".json").replace(/\.png$/i, ".json");
  try {
    const u = new URL(jsonUrl, location.origin);
    const name = u.pathname.split("/").pop();
    const apiUrl = name ? `/api/result-json/${encodeURIComponent(name)}` : jsonUrl;
    
    let res = await fetch(apiUrl);
    if (!res.ok) {
      
      res = await fetch(jsonUrl);
    }
    if (!res.ok) return null;
    const data = await res.json();
    if (!data || !Array.isArray(data.detections)) return null;
    const mm = data.mm_per_pixel;
    const mmNum = Number(mm);
    return {
      detections: data.detections,
      mm_per_pixel: Number.isFinite(mmNum) && mmNum > 0 ? mmNum : null,
      mm_per_pixel_source: data.mm_per_pixel_source,
    };
  } catch (_) {
    return null;
  }
}

let viewerApi = null;
let viewerShowing = "result";
let currentPayload = null;
let historyItemsCache = [];
let isLoggedInCache = null;
let selectedIds = new Set();
let lastQuery = { q: "", cls: "", sort: "ts_desc" };

async function isLoggedIn() {
  if (isLoggedInCache != null) return isLoggedInCache;
  try {
    const res = await fetch("/api/me");
    const data = await res.json().catch(() => ({}));
    isLoggedInCache = !!data.logged_in;
    return isLoggedInCache;
  } catch (_) {
    isLoggedInCache = false;
    return false;
  }
}

async function hydrateFromHistoryId(historyId) {
  const res = await fetch(`/api/history/${encodeURIComponent(historyId)}`);
  if (!res.ok) throw new Error("历史记录加载失败");
  const data = await res.json();
  const it = data.item;
  const stats = (() => {
    try {
      return JSON.parse(it.stats_json || "{}");
    } catch (_) {
      return {};
    }
  })();
  const base = {
    history_id: it.id,
    ts: it.ts,
    original_url: it.original_url,
    result_url: it.result_url,
    model_label: it.model_label || it.model_id,
    inference_ms: it.inference_ms,
    stats,
    params: it.params || {},
    conf: it.conf,
    iou: it.iou,
  };
  const meta = await tryLoadDetectionsFromResultJson(base.result_url);
  const dets = meta?.detections;
  return {
    ...base,
    detections: dets || [],
    ...(meta?.mm_per_pixel != null ? { mm_per_pixel: meta.mm_per_pixel } : {}),
    ...(meta?.mm_per_pixel_source != null ? { mm_per_pixel_source: meta.mm_per_pixel_source } : {}),
  };
}

async function hydrateFromLocalItem(it) {
  const stats = (() => {
    try {
      return JSON.parse(it.stats_json || "{}");
    } catch (_) {
      return {};
    }
  })();
  const base = {
    history_id: it.id,
    ts: it.ts,
    original_url: it.original_url,
    result_url: it.result_url,
    model_label: it.model_label || it.model_id,
    inference_ms: it.inference_ms,
    stats,
  };
  const meta = await tryLoadDetectionsFromResultJson(base.result_url);
  const dets = meta?.detections;
  return {
    ...base,
    detections: dets || [],
    ...(meta?.mm_per_pixel != null ? { mm_per_pixel: meta.mm_per_pixel } : {}),
    ...(meta?.mm_per_pixel_source != null ? { mm_per_pixel_source: meta.mm_per_pixel_source } : {}),
  };
}

function setUrlHistoryId(historyId) {
  const url = new URL(location.href);
  if (historyId == null) url.searchParams.delete("history_id");
  else url.searchParams.set("history_id", String(historyId));
  history.pushState({}, "", url.toString());
}

function ensureViewerBound() {
  const wrap = $("#viewer");
  const img = $("#viewerImg");
  const canvas = $("#viewerCanvas");
  if (!wrap || !img) return null;

  if (!viewerApi) {
    viewerApi = createViewer(wrap, img, canvas);
    $("#btnReset")?.addEventListener("click", () => viewerApi?.reset());
    $("#btnFit")?.addEventListener("click", () => viewerApi?.fit());
    $("#btnToggle")?.addEventListener("click", () => {
      if (!currentPayload) return;
      const original = currentPayload.original_url;
      const result = currentPayload.result_url || currentPayload.image_url;
      viewerShowing = viewerShowing === "result" ? "original" : "result";
      
      loadViewerImage(viewerShowing === "result" ? result : original, {
        showCanvas: viewerShowing === "result",
        redrawMasks: viewerShowing === "result",
      });
    });
    $("#btnDownloadResult")?.addEventListener("click", async () => {
      try {
        if (!currentPayload) return;
        const url = currentPayload.__viewer_result_url || currentPayload.result_url || currentPayload.image_url;
        if (!url) return;
        const nameBase = currentPayload.history_id != null ? `result_${currentPayload.history_id}` : "result";
        const filename = `${nameBase}.jpg`;
        const res = await fetch(url, { cache: "no-cache" });
        if (!res.ok) throw new Error("download failed");
        const blob = await res.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
          URL.revokeObjectURL(a.href);
          a.remove();
        }, 300);
      } catch (_) {
        
        const url = currentPayload?.__viewer_result_url || currentPayload?.result_url || currentPayload?.image_url;
        if (url) window.open(url, "_blank");
      }
    });
  }

  return { wrap, img, canvas };
}

function loadViewerImage(src, opts = {}) {
  const v = ensureViewerBound();
  if (!v) return;
  const { img, canvas } = v;
  const showCanvas = opts.showCanvas !== false;
  const redrawMasks = opts.redrawMasks !== false;

  if (canvas) canvas.style.display = showCanvas ? "block" : "none";
  img.src = src;

  const afterLoad = () => {
    if (canvas) {
      canvas.width = img.naturalWidth || 1;
      canvas.height = img.naturalHeight || 1;
      if (redrawMasks && currentPayload) drawMasks(canvas, currentPayload);
    }
    viewerApi?.fit();
  };

  
  img.onload = afterLoad;
  
  if (img.complete && img.naturalWidth) afterLoad();
}

function renderViewer(payload) {
  const v = ensureViewerBound();
  if (!v) return;

  currentPayload = payload;
  viewerShowing = "result";
  const original = payload.original_url;
  const result = payload.result_url || payload.image_url;
  
  loadViewerImage(result, { showCanvas: true, redrawMasks: true });

  
  payload.__viewer_original_url = original;
  payload.__viewer_result_url = result;
}

async function loadAndShow(payloadOrHistoryId) {
  let payload = null;
  if (payloadOrHistoryId && typeof payloadOrHistoryId === "object" && !payloadOrHistoryId.history_id) {
    
    payload = payloadOrHistoryId;
  } else if (payloadOrHistoryId && typeof payloadOrHistoryId === "object" && payloadOrHistoryId.__local) {
    payload = await hydrateFromLocalItem(payloadOrHistoryId);
  } else if (payloadOrHistoryId != null && String(payloadOrHistoryId).startsWith("local_")) {
    const it = historyItemsCache.find((x) => String(x.id) === String(payloadOrHistoryId));
    if (it) payload = await hydrateFromLocalItem(it);
  } else if (payloadOrHistoryId != null) {
    payload = await hydrateFromHistoryId(payloadOrHistoryId);
  }
  if (!payload) return;
  renderList(payload);
  renderViewer(payload);
  const activeId = payload.history_id ?? null;
  renderHistoryList(historyItemsCache, activeId);
}

async function loadServerHistoryAll() {
  const hint = $("#historyHint");
  if (hint) hint.textContent = "加载历史记录中…";
  const q = encodeURIComponent(lastQuery.q || "");
  const cls = encodeURIComponent(lastQuery.cls || "");
  const sort = encodeURIComponent(lastQuery.sort || "ts_desc");
  const res = await fetch(`/api/history?limit=500&q=${q}&class=${cls}&sort=${sort}`);
  if (!res.ok) throw new Error("history not available");
  const data = await res.json();
  return data.items || [];
}

function loadLocalHistoryFallback() {
  try {
    const profileRaw = localStorage.getItem("bridge_profile");
    const profile = profileRaw ? JSON.parse(profileRaw) : null;
    const userId = profile && profile.userId ? profile.userId : null;
    if (!userId) return [];
    const key = `bridge_history_${userId}`;
    const raw = localStorage.getItem(key);
    const arr = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(arr)) return [];
    return arr.map((it, idx) => ({
      id: `local_${idx}`,
      ts: it.ts,
      model_label: it.model_id || "-",
      model_id: it.model_id,
      total: it.total,
      inference_ms: it.inference_ms,
      stats_json: JSON.stringify(it.stats || {}),
      original_url: it.original_url,
      result_url: it.result_url,
      __local: true,
    }));
  } catch (_) {
    return [];
  }
}

function bindHistoryClick() {
  const body = $("#historyBody");
  if (!body) return;
  body.addEventListener("click", async (e) => {
    const cb = e.target.closest("input.hist-sel");
    if (cb) {
      const hid = cb.getAttribute("data-hid");
      if (hid) {
        if (cb.checked) selectedIds.add(String(hid));
        else selectedIds.delete(String(hid));
      }
      e.stopPropagation();
      return;
    }
    const tr = e.target.closest("tr[data-history-id]");
    if (!tr) return;
    const hid = tr.getAttribute("data-history-id");
    try {
      setUrlHistoryId(hid);
      await loadAndShow(hid);
    } catch (_) {}
  });
}

function toast(msg, isError = false) {
  const el = $("#toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.toggle("error", isError);
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2600);
}

function bindFiltersAndActions(loggedIn) {
  const qEl = $("#histQ");
  const clsEl = $("#histClass");
  const sortEl = $("#histSort");
  const selAll = $("#histSelAll");

  const refresh = async () => {
    if (!loggedIn) return;
    selectedIds = new Set();
    lastQuery = { q: (qEl?.value || "").trim(), cls: clsEl?.value || "", sort: sortEl?.value || "ts_desc" };
    historyItemsCache = await loadServerHistoryAll();
    renderHistoryList(historyItemsCache, currentPayload?.history_id ?? null);
  };

  let timer = null;
  const debounce = () => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => refresh().catch(() => {}), 260);
  };

  qEl?.addEventListener("input", debounce);
  clsEl?.addEventListener("change", () => refresh().catch(() => {}));
  sortEl?.addEventListener("change", () => refresh().catch(() => {}));

  selAll?.addEventListener("change", () => {
    const checked = !!selAll.checked;
    selectedIds = new Set(checked ? historyItemsCache.map((x) => String(x.id)) : []);
    renderHistoryList(historyItemsCache, currentPayload?.history_id ?? null);
  });
  
  selAll?.addEventListener("click", (e) => e.stopPropagation());

  $("#btnExport")?.addEventListener("click", async () => {
    if (!loggedIn) return toast("请先登录后导出", true);
    try {
      const params = new URLSearchParams();
      params.set("limit", "500");
      params.set("q", (qEl?.value || "").trim());
      params.set("class", clsEl?.value || "");
      params.set("sort", sortEl?.value || "ts_desc");
      const res = await fetch(`/api/history/export?${params.toString()}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || "导出失败");
      const blob = new Blob([JSON.stringify(data.items || [], null, 2)], { type: "application/json;charset=utf-8" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `history_export_${Date.now()}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (e) {
      toast(e.message || "导出失败", true);
    }
  });

  $("#btnDelete")?.addEventListener("click", async () => {
    if (!loggedIn) return toast("请先登录后删除", true);
    const ids = Array.from(selectedIds);
    if (!ids.length) return toast("请先勾选要删除的记录", true);
    if (!confirm(`确认删除选中的 ${ids.length} 条记录？`)) return;
    for (const id of ids) {
      try {
        await fetch(`/api/history/${encodeURIComponent(id)}`, { method: "DELETE" });
      } catch (_) {}
    }
    await refresh();
    toast("已删除");
  });

  $("#btnReanalyze")?.addEventListener("click", () => {
    const hid = currentPayload?.history_id;
    if (!hid) return toast("请先打开一条历史详情", true);
    if (!loggedIn) return toast("请先登录后使用再次分析", true);
    try {
      sessionStorage.setItem("detect_from_history_id", String(hid));
    } catch (_) {}
    location.assign(`/detect?history_id=${encodeURIComponent(String(hid))}`);
  });

  $("#btnReport")?.addEventListener("click", () => {
    const hid = currentPayload?.history_id;
    if (!hid) return;
    try {
      sessionStorage.setItem("report_seed", JSON.stringify({ history_id: hid }));
    } catch (_) {}
  });
}

async function main() {
  const loggedIn = await isLoggedIn();
  const hint = $("#historyHint");
  if (!loggedIn) {
    historyItemsCache = [];
    renderHistoryList([], null);
    if (hint) hint.textContent = "访客仅可查看本次检测结果；登录后可查看并管理历史记录。";
  } else {
    try {
      historyItemsCache = await loadServerHistoryAll();
    } catch (_) {
      historyItemsCache = loadLocalHistoryFallback();
    }
    renderHistoryList(historyItemsCache, null);
    bindHistoryClick();
    bindFiltersAndActions(true);
  }

  const payload0 = getLastPayload();
  if (!loggedIn && payload0 && payload0.history_id != null) {
    
    setUrlHistoryId(null);
  }
  if (loggedIn && payload0 && payload0.history_id != null) {
    try {
      await loadAndShow(payload0.history_id);
      return;
    } catch (_) {}
  }
  if (payload0 && !payload0.history_id) {
    try {
      await loadAndShow(payload0);
      return;
    } catch (_) {}
  }
  if (loggedIn && historyItemsCache.length) {
    await loadAndShow(historyItemsCache[0].id);
  }
}

main();

