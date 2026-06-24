let currentModelId = null;
let charts = { map: null, loss: null };
let models = [];
let classCatalog = null;

const $ = (sel) => document.querySelector(sel);

function toast(msg, isError = false) {
  const el = $("#toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.toggle("error", isError);
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2600);
}

function fmtPct(v) {
  return typeof v === "number" && isFinite(v) ? (v * 100).toFixed(1) + "%" : "—";
}

function fmt3(v) {
  return typeof v === "number" && isFinite(v) ? Number(v).toFixed(3) : "—";
}

function fmtTimeSec(sec) {
  if (typeof sec !== "number" || !isFinite(sec) || sec <= 0) return "—";
  return new Date(sec * 1000).toLocaleString();
}

async function loadModelsCompareTable() {
  const body = $("#modelsCompareBody");
  if (!body) return;
  try {
    const res = await fetch("/api/models-summary");
    const data = await res.json();
    const items = Array.isArray(data.items) ? data.items : [];
    if (!items.length) {
      body.innerHTML = `<tr><td colspan="9" style="color:var(--text2)">暂无模型数据</td></tr>`;
      return;
    }
    body.innerHTML = items
      .map((it) => {
        const isActive = currentModelId && it.id === currentModelId;
        const tdStyle = isActive ? ' style="font-weight:900;color:var(--primary)"' : "";
        return `
          <tr>
            <td${tdStyle}>${it.label || it.id}</td>
            <td>${fmt3(it.box_p)}</td>
            <td>${fmt3(it.box_r)}</td>
            <td>${fmt3(it.box_mAP50)}</td>
            <td>${fmt3(it.box_mAP50_95)}</td>
            <td>${fmt3(it.mask_p)}</td>
            <td>${fmt3(it.mask_r)}</td>
            <td>${fmt3(it.mask_mAP50)}</td>
            <td>${fmt3(it.mask_mAP50_95)}</td>
          </tr>
        `;
      })
      .join("");
  } catch (_) {
    body.innerHTML = `<tr><td colspan="9" style="color:#ef4444">加载失败</td></tr>`;
  }
}

async function loadModelInfo(modelId) {
  const res = await fetch(`/api/model-info?model_id=${encodeURIComponent(modelId)}`);
  const data = await res.json();

  const safePct = (v) => (typeof v === "number" && isFinite(v) ? (v * 100).toFixed(1) + "%" : "—");
  const safeNum = (v) => (v == null ? "—" : String(v));
  $("#mBoxMAP").textContent = safePct(data?.metrics?.box_mAP50);
  $("#mMaskMAP").textContent = safePct(data?.metrics?.mask_mAP50);
  $("#mEpochs").textContent = safeNum(data?.epochs);

  
  const w = data?.weights || {};
  const fmtBytes = (b) => {
    if (typeof b !== "number" || !isFinite(b)) return "—";
    const units = ["B", "KB", "MB", "GB"];
    let n = b;
    let i = 0;
    while (n >= 1024 && i < units.length - 1) {
      n /= 1024;
      i++;
    }
    return `${n.toFixed(i === 0 ? 0 : 2)} ${units[i]}`;
  };
  const fmtTime = (sec) => {
    if (typeof sec !== "number" || !isFinite(sec)) return "—";
    return new Date(sec * 1000).toLocaleString();
  };
  const setText = (sel, val) => {
    const el = document.querySelector(sel);
    if (el) el.textContent = val;
  };
  setText("#mWeightsPath", w.path ? String(w.path) : "—");
  setText("#mWeightsSize", fmtBytes(w.bytes));
  setText("#mWeightsMtime", fmtTime(w.mtime));
  setText("#mTask", data?.task ? String(data.task) : "—");
  setText("#mImgSz", data?.imgsz ? `${data.imgsz} × ${data.imgsz}` : "—");
  setText("#mNumClasses", Array.isArray(data?.classes) ? String(data.classes.length) : "—");
  setText("#mFramework", "Ultralytics YOLO Segment");
  const args = data?.args || {};
  const argsParts = [];
  if (args.model) argsParts.push(`model=${args.model}`);
  if (args.data) argsParts.push(`data=${args.data}`);
  if (args.batch != null) argsParts.push(`batch=${args.batch}`);
  if (args.optimizer) argsParts.push(`opt=${args.optimizer}`);
  if (args.device != null) argsParts.push(`device=${args.device}`);
  setText("#mArgsHint", argsParts.length ? argsParts.join("，") : "—");

  
  const tags = $("#classTags");
  if (tags && data && Array.isArray(data.classes)) {
    tags.innerHTML = data.classes
      .map(
        (c) => `
        <div class="class-tag">
          <span class="dot" style="background:${data.colors[c]}"></span>
          ${data.classes_cn[c]} (${c})
        </div>
      `
      )
      .join("");
  }

  const base = data.assets_base_url || "/model-assets";
  const assets = (data && data.assets) || {};
  const setSrc = (sel, name, { hideOnError } = { hideOnError: false }) => {
    const el = document.querySelector(sel);
    if (!el) return;
    const card = el.closest(".card");
    if (card) card.style.display = ""; 
    const rel = assets && assets[name] ? assets[name] : name;
    
    if (hideOnError) {
      el.onerror = () => {
        if (card) card.style.display = "none";
      };
      el.onload = () => {
        if (card) card.style.display = "";
      };
    } else {
      el.onerror = null;
      el.onload = null;
    }
    el.src = `${base}/${rel}`;
  };
  setSrc('img[alt="train batch 0"]', "train_batch0.jpg");
  setSrc('img[alt="train batch 1"]', "train_batch1.jpg");
  setSrc('img[alt="train batch 2"]', "train_batch2.jpg");
  setSrc('img[alt="val labels"]', "val_batch0_labels.jpg");
  setSrc('img[alt="val preds"]', "val_batch0_pred.jpg");
  setSrc('img[alt="confusion matrix"]', "confusion_matrix.png", { hideOnError: true });
  setSrc('img[alt="confusion matrix normalized"]', "confusion_matrix_normalized.png", { hideOnError: true });
  setSrc('img[alt="Box PR"]', "BoxPR_curve.png");
  setSrc('img[alt="Box F1"]', "BoxF1_curve.png");
  setSrc('img[alt="Mask PR"]', "MaskPR_curve.png");
  setSrc('img[alt="Mask F1"]', "MaskF1_curve.png");

  if (data && data.training_curves && data.training_curves.epochs && data.training_curves.epochs.length) {
    renderCharts(data.training_curves);
  }
}

async function setModel(modelId, { silent } = { silent: false }) {
  const sel = $("#modelSelectInfo");
  currentModelId = modelId;
  if (sel && sel.value !== modelId) sel.value = modelId;
  await loadModelInfo(modelId);
  
  loadModelsCompareTable();
  if (!silent) toast("已切换模型版本");
}

function renderCharts(curves) {
  if (charts.map) charts.map.destroy();
  if (charts.loss) charts.loss.destroy();

  const baseOpts = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: "#5b6b83", font: { size: 12 } } },
    },
    scales: {
      x: {
        title: { display: true, text: "Epoch", color: "#5b6b83" },
        ticks: { color: "#5b6b83", maxTicksLimit: 20 },
        grid: { color: "rgba(2,6,23,.06)" },
      },
      y: {
        ticks: { color: "#5b6b83" },
        grid: { color: "rgba(2,6,23,.06)" },
      },
    },
    elements: { point: { radius: 0 }, line: { borderWidth: 2 } },
  };

  charts.map = new Chart($("#chartMAP"), {
    type: "line",
    data: {
      labels: curves.epochs,
      datasets: [
        {
          label: "Box mAP50",
          data: curves.box_mAP50,
          borderColor: "#2563eb",
          backgroundColor: "rgba(37,99,235,.10)",
          fill: true,
          tension: 0.3,
        },
        {
          label: "Mask mAP50",
          data: curves.mask_mAP50,
          borderColor: "#0ea5e9",
          backgroundColor: "rgba(14,165,233,.08)",
          fill: true,
          tension: 0.3,
        },
      ],
    },
    options: {
      ...baseOpts,
      plugins: {
        ...baseOpts.plugins,
        title: {
          display: true,
          text: "mAP50 曲线",
          color: "#0b1220",
          font: { size: 14, weight: 700 },
        },
      },
    },
  });

  charts.loss = new Chart($("#chartLoss"), {
    type: "line",
    data: {
      labels: curves.epochs,
      datasets: [
        { label: "Train Box Loss", data: curves.train_box_loss, borderColor: "#ef4444", tension: 0.3 },
        { label: "Train Seg Loss", data: curves.train_seg_loss, borderColor: "#f97316", tension: 0.3 },
        { label: "Val Box Loss", data: curves.val_box_loss, borderColor: "#22c55e", tension: 0.3 },
        { label: "Val Seg Loss", data: curves.val_seg_loss, borderColor: "#06b6d4", tension: 0.3 },
      ],
    },
    options: {
      ...baseOpts,
      plugins: {
        ...baseOpts.plugins,
        title: {
          display: true,
          text: "损失函数曲线",
          color: "#0b1220",
          font: { size: 14, weight: 700 },
        },
      },
    },
  });
}

async function loadModels() {
  const sel = $("#modelSelectInfo");
  const res = await fetch("/api/models");
  const data = await res.json();
  models = data.models || [];
  classCatalog = data.class_catalog || null;
  sel.innerHTML = models.map((m) => `<option value="${m.id}">${m.id}</option>`).join("");
  currentModelId = data.default || (models[0] && models[0].id);
  if (currentModelId) sel.value = currentModelId;

  sel.addEventListener("change", async () => {
    await setModel(sel.value);
  });

  await loadModelsCompareTable();
  await loadModelInfo(currentModelId);
}

loadModels().catch(() => toast("加载失败", true));

