const $ = (sel) => document.querySelector(sel);

function toast(msg, isError = false) {
  const el = $("#toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.toggle("error", isError);
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2600);
}

async function login() {
  const username = ($("#username").value || "").trim();
  const password = $("#password").value || "";
  if (!username || !password) {
    toast("请输入用户名和密码", true);
    return;
  }
  const btn = $("#loginBtn");
  btn.disabled = true;
  try {
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "登录失败");
    toast("登录成功");
    const url = new URL(location.href);
    const next = url.searchParams.get("next");
    const target = next && next.startsWith("/") ? next : "/profile";
    setTimeout(() => (location.href = target), 300);
  } catch (e) {
    toast(e.message || "登录失败", true);
  } finally {
    btn.disabled = false;
  }
}

$("#loginBtn").addEventListener("click", login);
$("#password").addEventListener("keydown", (e) => {
  if (e.key === "Enter") login();
});

