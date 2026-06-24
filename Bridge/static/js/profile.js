const $ = (sel) => document.querySelector(sel);

function toast(msg, isError = false) {
  const el = $("#toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.toggle("error", isError);
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2600);
}

function getOrCreateUser() {
  const key = "bridge_profile";
  const raw = localStorage.getItem(key);
  if (raw) {
    try {
      const obj = JSON.parse(raw);
      if (obj && obj.userId) {
        if (!obj.createdAt) {
          obj.createdAt = Date.now();
          localStorage.setItem(key, JSON.stringify(obj));
        }
        return obj;
      }
    } catch (_) {}
  }
  const userId =
    (crypto && crypto.randomUUID && crypto.randomUUID()) ||
    `u_${Math.random().toString(16).slice(2)}${Date.now().toString(16)}`;
  const profile = { userId, nickname: "未命名用户", createdAt: Date.now() };
  localStorage.setItem(key, JSON.stringify(profile));
  return profile;
}

function saveUser(profile) {
  localStorage.setItem("bridge_profile", JSON.stringify(profile));
}

function historyKey(userId) {
  return `bridge_history_${userId}`;
}

function loadHistory(userId) {
  const raw = localStorage.getItem(historyKey(userId));
  if (!raw) return [];
  try {
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr : [];
  } catch (_) {
    return [];
  }
}

function saveHistory(userId, items) {
  localStorage.setItem(historyKey(userId), JSON.stringify(items));
}

function formatTime(ts) {
  const d = new Date(ts);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function statsText(stats) {
  if (!stats) return "-";
  const entries = Object.entries(stats);
  if (!entries.length) return "-";
  return entries
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `${k}${v}`)
    .join(" / ");
}

function withinDays(ts, days) {
  if (days === "all") return true;
  const d = parseInt(days, 10);
  if (!d) return true;
  const cutoff = Date.now() - d * 24 * 60 * 60 * 1000;
  return ts >= cutoff;
}

function hashHue(seed) {
  let h = 0;
  const s = String(seed || "");
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h) % 360;
}

function avatarLetter(name) {
  const s = String(name || "").trim();
  if (!s) return "?";
  const ch = s[0];
  return /[a-z]/i.test(ch) ? ch.toUpperCase() : ch;
}


function renderUserPanel(me, profile) {
  const wrap = $("#profileAvatarWrap");
  const letterEl = $("#profileAvatarLetter");
  const img = $("#profileAvatarImg");
  const actions = $("#profileAvatarActions");
  const btnClear = $("#btnClearAvatar");
  const nick = $("#profileNickname");
  const created = $("#profileCreatedAt");
  const uid = $("#profileUserId");
  const guestRow = $("#profileGuestNickRow");

  const logged = me && me.logged_in && me.user;
  const displayName = logged ? String(me.user.username || "—") : String(profile.nickname || "未命名用户");
  const seed = logged ? displayName : String(profile.userId || displayName);
  const hue = hashHue(seed);
  const hue2 = (hue + 48) % 360;
  const avatarUrl = logged && me.user.avatar_url ? String(me.user.avatar_url).trim() : "";

  if (actions) actions.style.display = logged ? "block" : "none";
  if (btnClear) btnClear.style.display = logged && avatarUrl ? "inline-flex" : "none";

  if (wrap && letterEl && img) {
    if (avatarUrl) {
      img.src = avatarUrl + (avatarUrl.includes("?") ? "&" : "?") + "t=" + Date.now();
      img.style.display = "block";
      letterEl.style.display = "none";
      wrap.style.background = "transparent";
    } else {
      img.removeAttribute("src");
      img.style.display = "none";
      letterEl.style.display = "";
      letterEl.textContent = avatarLetter(displayName);
      wrap.style.background = `linear-gradient(135deg, hsl(${hue},52%,42%), hsl(${hue2},46%,34%))`;
    }
  }

  if (nick) nick.textContent = displayName;

  if (created) {
    if (logged && me.user.created_at != null) {
      const ts = Number(me.user.created_at) * 1000;
      created.textContent = Number.isFinite(ts) && ts > 0 ? formatTime(ts) : "—";
    } else if (profile.createdAt) {
      created.textContent = formatTime(Number(profile.createdAt));
    } else {
      created.textContent = "—";
    }
  }

  if (uid) uid.textContent = logged ? String(me.user.id) : String(profile.userId || "—");

  if (guestRow) guestRow.style.display = logged ? "none" : "block";
}

function renderTable(profile, items) {
  const body = $("#historyBody");
  if (!body) return;
  if (!items.length) {
    body.innerHTML = `<tr><td colspan="6" style="color:var(--text2);padding:18px 14px">-</td></tr>`;
    return;
  }

  body.innerHTML = items
    .map((it, idx) => {
      const view =
        it.id != null
          ? `<a class="link" href="/results?history_id=${it.id}">查看</a>`
          : `<a class="link open-result" href="javascript:void(0)" data-idx="${idx}">查看</a>`;
      return `
      <tr>
        <td>${formatTime(it.ts)}</td>
        <td style="color:var(--text-sec)">${it.model_label || it.model_id || "-"}</td>
        <td>${statsText(it.stats)}</td>
        <td>${it.total ?? "-"}</td>
        <td>${it.inference_ms ?? "-"} ms</td>
        <td>${view}</td>
      </tr>
    `;
    })
    .join("");

  
  body.querySelectorAll(".open-result").forEach((a) => {
    a.addEventListener("click", () => {
      const i = Number(a.getAttribute("data-idx"));
      const it = items[i];
      if (!it) return;
      try {
        sessionStorage.setItem(
          "results_payload",
          JSON.stringify({
            original_url: it.original_url,
            result_url: it.result_url,
            model_label: it.model_label || it.model_id,
            inference_ms: it.inference_ms,
            stats: it.stats || {},
            detections: it.detections || [],
          })
        );
      } catch (_) {}
      location.href = "/results";
    });
  });
}

function download(filename, content, mime = "application/octet-stream") {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function toCsv(rows) {
  const header = ["ts", "nickname", "model_id", "model_label", "total", "inference_ms", "stats", "original_url", "result_url"];
  const esc = (v) => `"${String(v ?? "").replaceAll('"', '""')}"`;
  const lines = [header.join(",")];
  for (const r of rows) {
    lines.push(
      [
        r.ts,
        r.nickname,
        r.model_id,
        r.model_label,
        r.total,
        r.inference_ms,
        JSON.stringify(r.stats || {}),
        r.original_url,
        r.result_url,
      ].map(esc).join(",")
    );
  }
  return lines.join("\n");
}

async function getModelLabelMap() {
  try {
    const res = await fetch("/api/models");
    const data = await res.json();
    const map = {};
    (data.models || []).forEach((m) => (map[m.id] = m.label));
    return map;
  } catch (_) {
    return {};
  }
}

async function refresh() {
  const profile = getOrCreateUser();
  const nickInput = $("#nickname");
  if (nickInput) nickInput.value = profile.nickname || "";

  let me = { logged_in: false };
  try {
    me = await fetch("/api/me").then((r) => r.json());
  } catch (_) {}

  const kw = ($("#keyword").value || "").trim().toLowerCase();
  const range = $("#range").value;
  const labelMap = await getModelLabelMap();

  
  let items = [];
  try {
    if (me.logged_in) {
      const resp = await fetch("/api/history?limit=200").then((r) => r.json());
      const serverItems = resp.items || [];

      
      
      if (serverItems.length === 0) {
        const localItems = loadHistory(profile.userId);
        if (localItems.length) {
          const syncKey = "bridge_history_synced_to_account";
          if (!localStorage.getItem(syncKey)) {
            for (const it of localItems.slice(0, 200).reverse()) {
              await fetch("/api/history", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  ts: it.ts || Date.now(),
                  model_id: it.model_id,
                  model_label: it.model_label || labelMap[it.model_id] || it.model_id,
                  total: it.total,
                  inference_ms: it.inference_ms,
                  stats_json: JSON.stringify(it.stats || {}),
                  original_url: it.original_url,
                  result_url: it.result_url,
                }),
              });
            }
            localStorage.setItem(syncKey, "1");
            toast("已同步本机历史到账号历史");
            
            const resp2 = await fetch("/api/history?limit=200").then((r) => r.json());
            items = (resp2.items || []).map((it) => it);
          }
        }
      }

      const finalResp = items.length ? { items } : { items: serverItems };
      items = (finalResp.items || []).map((it) => ({
        id: it.id,
        ts: Number(it.ts),
        model_id: it.model_id,
        model_label: it.model_label,
        total: it.total,
        inference_ms: it.inference_ms,
        stats: (() => {
          try { return JSON.parse(it.stats_json || "{}"); } catch (_) { return {}; }
        })(),
        original_url: it.original_url,
        result_url: it.result_url,
      }));
    } else {
      items = loadHistory(profile.userId);
    }
  } catch (_) {
    items = loadHistory(profile.userId);
  }

  items = items.map((it) => ({
    ...it,
    model_label: it.model_label || labelMap[it.model_id] || it.model_id,
    nickname: profile.nickname || "",
  }));
  const loadedCount = items.length;
  items = items
    .filter((it) => withinDays(it.ts, range))
    .filter((it) => {
      if (!kw) return true;
      const s = [
        it.model_id,
        it.model_label,
        JSON.stringify(it.stats || {}),
      ]
        .join(" ")
        .toLowerCase();
      return s.includes(kw);
    })
    .sort((a, b) => b.ts - a.ts);

  if (me.logged_in) {
    try {
      const me2 = await fetch("/api/me").then((r) => r.json());
      if (me2.logged_in) me = me2;
    } catch (_) {}
  }

  renderTable(profile, items);
  renderUserPanel(me, profile);
  if (typeof window.updateAuthNav === "function") window.updateAuthNav();
}

function init() {
  const profile = getOrCreateUser();
  const nickInput = $("#nickname");
  if (nickInput) nickInput.value = profile.nickname || "";

  $("#saveProfileBtn")?.addEventListener("click", () => {
    const p = getOrCreateUser();
    const nickname = ($("#nickname").value || "").trim();
    p.nickname = nickname || "未命名用户";
    saveUser(p);
    toast("已保存");
    refresh();
  });

  $("#resetProfileBtn")?.addEventListener("click", () => {
    const p = getOrCreateUser();
    p.nickname = "未命名用户";
    saveUser(p);
    if ($("#nickname")) $("#nickname").value = p.nickname;
    toast("已重置");
    refresh();
  });

  $("#refreshBtn").addEventListener("click", refresh);
  $("#keyword").addEventListener("keydown", (e) => {
    if (e.key === "Enter") refresh();
  });

  $("#exportJsonBtn").addEventListener("click", () => {
    const p = getOrCreateUser();
    const items = loadHistory(p.userId);
    download(
      `bridge-history-${p.userId}.json`,
      JSON.stringify({ profile: p, history: items }, null, 2),
      "application/json"
    );
  });

  $("#exportCsvBtn").addEventListener("click", () => {
    const p = getOrCreateUser();
    const items = loadHistory(p.userId).map((it) => ({ ...it, nickname: p.nickname || "" }));
    download(`bridge-history-${p.userId}.csv`, toCsv(items), "text/csv;charset=utf-8");
  });

  $("#clearHistoryBtn").addEventListener("click", () => {
    const p = getOrCreateUser();
    if (!confirm("确定要清空本机历史记录吗？")) return;
    saveHistory(p.userId, []);
    toast("已清空");
    refresh();
  });

  $("#btnPickAvatar")?.addEventListener("click", () => {
    $("#profileAvatarFile")?.click();
  });
  $("#profileAvatarFile")?.addEventListener("change", async (e) => {
    const t = e.target;
    const file = t && t.files && t.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch("/api/me/avatar", { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        toast(data.error || "上传失败", true);
        return;
      }
      toast("头像已更新");
      t.value = "";
      await refresh();
    } catch (err) {
      toast(err.message || "上传失败", true);
    }
  });
  $("#btnClearAvatar")?.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/me/avatar", { method: "DELETE" });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        toast(data.error || "恢复失败", true);
        return;
      }
      toast("已恢复默认头像");
      await refresh();
    } catch (err) {
      toast(err.message || "恢复失败", true);
    }
  });

  refresh();
}

init();

