const $ = (sel) => document.querySelector(sel);

function toast(msg, isError = false) {
  const el = $("#toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.toggle("error", isError);
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2600);
}

async function register() {
  const username = ($("#username").value || "").trim();
  const password = $("#password").value || "";
  if (!username || !password) {
    toast("请输入用户名和密码", true);
    return;
  }
  const btn = $("#registerBtn");
  btn.disabled = true;
  try {
    const res = await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "注册失败");
    toast("注册成功");
    setTimeout(() => (location.href = "/profile"), 300);
  } catch (e) {
    toast(e.message || "注册失败", true);
  } finally {
    btn.disabled = false;
  }
}

$("#registerBtn").addEventListener("click", register);
$("#password").addEventListener("keydown", (e) => {
  if (e.key === "Enter") register();
});

