const $ = (sel) => document.querySelector(sel);

function toast(msg, isError = false) {
  const el = $("#toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.toggle("error", isError);
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2600);
}

function fmtTime(ts) {
  const d = new Date(Number(ts || 0));
  if (!Number.isFinite(d.getTime())) return "-";
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

let cameras = [];
let activeCameraId = null;
let editingCameraId = null;


let localMediaStream = null;

function setLocalCamUi(active) {
  const video = $("#localPreview");
  const ph = $("#localCamPlaceholder");
  const openBtn = $("#btnOpenLocalCam");
  const closeBtn = $("#btnCloseLocalCam");
  const status = $("#localCamStatus");
  if (video) {
    video.style.display = active ? "block" : "none";
  }
  if (ph) ph.style.display = active ? "none" : "block";
  if (openBtn) openBtn.disabled = !!active;
  if (closeBtn) closeBtn.disabled = !active;
  if (status) status.textContent = active ? "预览中" : "未启动";
}

function closeLocalCamera() {
  if (localMediaStream) {
    for (const t of localMediaStream.getTracks()) {
      try {
        t.stop();
      } catch (_) {
        
      }
    }
    localMediaStream = null;
  }
  const video = $("#localPreview");
  if (video) {
    video.srcObject = null;
  }
  setLocalCamUi(false);
}

async function openLocalCamera() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    toast("摄像头打开失败", true);
    return;
  }
  if (localMediaStream) closeLocalCamera();
  const video = $("#localPreview");
  if (!video) {
    toast("摄像头打开失败", true);
    return;
  }
  try {
    
    video.muted = true;
    video.setAttribute("playsinline", "");
    video.setAttribute("webkit-playsinline", "");
    setLocalCamUi(true);

    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    localMediaStream = stream;
    video.srcObject = stream;
    try {
      await video.play();
    } catch (playErr) {
      const n = playErr && playErr.name;
      if (n !== "AbortError") {
        console.warn("[local cam] video.play()", playErr);
      }
    }
    stream.getVideoTracks()[0]?.addEventListener("ended", () => {
      closeLocalCamera();
      toast("摄像头已断开", false);
    });
  } catch {
    toast("摄像头打开失败", true);
    setLocalCamUi(false);
  }
}

async function apiJson(url, opts = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data && (data.error || data.message) ? (data.error || data.message) : `请求失败：${res.status}`;
    const err = new Error(msg);
    err.status = res.status;
    err.payload = data;
    throw err;
  }
  return data;
}

function renderCameraList() {
  const body = $("#camBody");
  if (!body) return;
  if (!cameras.length) {
    body.innerHTML = `<tr><td colspan="3" style="color:var(--text2)">-</td></tr>`;
    return;
  }
  body.innerHTML = cameras
    .map((c) => {
      const active = String(c.id) === String(activeCameraId);
      const status = c.enabled ? "启用" : "禁用";
      return `<tr data-cam-id="${c.id}" style="cursor:pointer;${active ? "background:rgba(0,123,255,0.08)" : ""}">
        <td title="${c.stream_url}" style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${c.name}</td>
        <td style="white-space:nowrap">${c.protocol || "-"}</td>
        <td style="white-space:nowrap">${status}</td>
      </tr>`;
    })
    .join("");
}

function updateActiveMeta() {
  const el = $("#activeCamMeta");
  if (!el) return;
  const c = cameras.find((x) => String(x.id) === String(activeCameraId));
  if (!c) {
    el.textContent = "未选择摄像头";
    return;
  }
  el.textContent = `${c.name} · ${c.protocol || "-"} · ${c.enabled ? "启用" : "禁用"}`;
}

async function loadCameras() {
  try {
    const data = await apiJson("/api/cameras");
    cameras = data.items || [];
  } catch (e) {
    cameras = [];
    if (e.status === 401) {
      toast("请先登录后管理摄像头与监测记录", true);
    } else {
      toast(e.message || "摄像头加载失败", true);
    }
  }
  if (activeCameraId != null && !cameras.some((c) => String(c.id) === String(activeCameraId))) {
    activeCameraId = null;
  }
  renderCameraList();
  updateActiveMeta();
}

function showCamForm(mode) {
  const card = $("#camFormCard");
  if (!card) return;
  card.style.display = "block";
  const title = $("#camFormTitle");
  if (title) title.textContent = mode === "edit" ? "编辑摄像头" : "添加摄像头";
}

function hideCamForm() {
  const card = $("#camFormCard");
  if (!card) return;
  card.style.display = "none";
  editingCameraId = null;
  $("#camName").value = "";
  $("#camUrl").value = "";
  $("#camProtocol").value = "RTSP";
}

async function saveCamera() {
  const name = ($("#camName").value || "").trim();
  const stream_url = ($("#camUrl").value || "").trim();
  const protocol = ($("#camProtocol").value || "").trim();
  if (!name) return toast("请输入名称", true);
  if (!stream_url) return toast("请输入流地址", true);
  try {
    if (editingCameraId != null) {
      await apiJson(`/api/cameras/${encodeURIComponent(editingCameraId)}`, {
        method: "PUT",
        body: JSON.stringify({ name, stream_url, protocol }),
      });
    } else {
      await apiJson("/api/cameras", { method: "POST", body: JSON.stringify({ name, stream_url, protocol }) });
    }
    toast("已保存");
    hideCamForm();
    await loadCameras();
  } catch (e) {
    toast(e.message || "保存失败", true);
  }
}

async function deleteCamera() {
  if (activeCameraId == null) return toast("请先选择摄像头", true);
  if (!confirm("确认删除该摄像头？")) return;
  try {
    await apiJson(`/api/cameras/${encodeURIComponent(activeCameraId)}`, { method: "DELETE" });
    toast("已删除");
    activeCameraId = null;
    await loadCameras();
    await loadRecords();
  } catch (e) {
    toast(e.message || "删除失败", true);
  }
}

async function startStop(mode, action) {
  if (activeCameraId == null) return toast("请先选择摄像头", true);
  try {
    const url = action === "start" ? "/api/monitor/start" : "/api/monitor/stop";
    await apiJson(url, { method: "POST", body: JSON.stringify({ camera_id: activeCameraId, mode }) });
    toast(action === "start" ? "已开始" : "已停止");
    await loadRecords();
  } catch (e) {
    toast(e.message || "操作失败", true);
  }
}

function renderRecords(items) {
  const body = $("#recBody");
  if (!body) return;
  const arr = Array.isArray(items) ? items : [];
  if (!arr.length) {
    body.innerHTML = `<tr><td colspan="4" style="color:var(--text2)">-</td></tr>`;
    return;
  }
  const camName = (id) => (cameras.find((c) => String(c.id) === String(id)) || {}).name || `#${id}`;
  body.innerHTML = arr
    .map((r) => {
      const detail = r.detail || {};
      const mode = detail.mode ? `mode=${detail.mode}` : "";
      return `<tr>
        <td style="white-space:nowrap">${fmtTime(r.ts)}</td>
        <td style="white-space:nowrap">${camName(r.camera_id)}</td>
        <td style="white-space:nowrap">${r.event}</td>
        <td style="color:var(--text2);font-family:var(--font-mono);font-size:12px">${mode || "-"}</td>
      </tr>`;
    })
    .join("");
}

async function loadRecords() {
  try {
    const q = activeCameraId != null ? `?camera_id=${encodeURIComponent(activeCameraId)}&limit=200` : "?limit=200";
    const data = await apiJson(`/api/monitor-records${q}`);
    renderRecords(data.items || []);
  } catch (e) {
    renderRecords([]);
    if (e.status === 401) {
      toast("请先登录后查看监测记录", true);
    } else {
      toast(e.message || "记录加载失败", true);
    }
  }
}

function bind() {
  $("#camBody")?.addEventListener("click", (e) => {
    const tr = e.target.closest("tr[data-cam-id]");
    if (!tr) return;
    activeCameraId = tr.getAttribute("data-cam-id");
    renderCameraList();
    updateActiveMeta();
    loadRecords();
  });

  $("#btnAddCamera")?.addEventListener("click", () => {
    editingCameraId = null;
    $("#camName").value = "";
    $("#camUrl").value = "";
    $("#camProtocol").value = "RTSP";
    showCamForm("add");
  });

  $("#btnEditCamera")?.addEventListener("click", () => {
    if (activeCameraId == null) return toast("请先选择摄像头", true);
    const c = cameras.find((x) => String(x.id) === String(activeCameraId));
    if (!c) return toast("摄像头不存在", true);
    editingCameraId = c.id;
    $("#camName").value = c.name || "";
    $("#camUrl").value = c.stream_url || "";
    $("#camProtocol").value = c.protocol || "RTSP";
    showCamForm("edit");
  });

  $("#btnDeleteCamera")?.addEventListener("click", deleteCamera);
  $("#btnCloseCamForm")?.addEventListener("click", hideCamForm);
  $("#btnSaveCam")?.addEventListener("click", saveCamera);

  $("#btnStartMonitor")?.addEventListener("click", () => startStop("monitor", "start"));
  $("#btnStopMonitor")?.addEventListener("click", () => startStop("monitor", "stop"));
  $("#btnStartDetect")?.addEventListener("click", () => startStop("detect", "start"));
  $("#btnStopDetect")?.addEventListener("click", () => startStop("detect", "stop"));
  $("#btnRefreshRecords")?.addEventListener("click", loadRecords);

  $("#btnOpenLocalCam")?.addEventListener("click", () => {
    openLocalCamera();
  });
  $("#btnCloseLocalCam")?.addEventListener("click", () => {
    closeLocalCamera();
    toast("已关闭摄像头");
  });
}

async function main() {
  bind();
  await loadCameras();
  await loadRecords();
  window.addEventListener("beforeunload", () => closeLocalCamera());
}

main();

