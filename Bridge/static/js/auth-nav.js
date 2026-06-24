function navHashHue(seed) {
  let h = 0;
  const s = String(seed || "");
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h) % 360;
}

function navAvatarLetter(name) {
  const s = String(name || "").trim();
  if (!s) return "?";
  const ch = s[0];
  return /[a-z]/i.test(ch) ? ch.toUpperCase() : ch;
}

function applyTopbarAvatar(username, avatarUrl) {
  const el = document.querySelector(".userbox .avatar");
  if (!el) return;
  el.innerHTML = "";
  el.style.background = "";
  const u = avatarUrl && String(avatarUrl).trim();
  const uname = username != null ? String(username).trim() : "";
  if (!u && !uname) {
    return;
  }
  if (u) {
    const img = document.createElement("img");
    img.alt = "";
    img.src = u + (u.includes("?") ? "&" : "?") + "t=" + Date.now();
    el.appendChild(img);
    return;
  }
  const name = uname || "";
  const letter = navAvatarLetter(name);
  const hue = navHashHue(name || "user");
  const hue2 = (hue + 48) % 360;
  el.style.background = `linear-gradient(135deg, hsl(${hue},52%,42%), hsl(${hue2},46%,34%))`;
  const sp = document.createElement("span");
  sp.className = "nav-avatar-letter";
  sp.textContent = letter;
  el.appendChild(sp);
}

async function updateAuthNav() {
  const elLogin = document.querySelector("#navLogin");
  const elRegister = document.querySelector("#navRegister");
  const elUser = document.querySelector("#navUser");
  const elLogout = document.querySelector("#navLogout");
  if (!elLogin || !elRegister || !elUser || !elLogout) return;

  try {
    const res = await fetch("/api/me");
    const data = await res.json();
    if (data.logged_in) {
      elLogin.style.display = "none";
      elRegister.style.display = "none";
      elUser.style.display = "inline-flex";
      elLogout.style.display = "inline-flex";
      elUser.textContent = data.user.username;
      elUser.href = "/history";
      applyTopbarAvatar(data.user.username, data.user.avatar_url || "");

      elLogout.onclick = async () => {
        await fetch("/api/logout", { method: "POST" });
        location.href = "/";
      };
    } else {
      elLogin.style.display = "inline-flex";
      elRegister.style.display = "inline-flex";
      elUser.style.display = "none";
      elLogout.style.display = "none";
      applyTopbarAvatar("", null);
    }
  } catch (_) {
    
    applyTopbarAvatar("", null);
  }
}

window.updateAuthNav = updateAuthNav;
updateAuthNav();
