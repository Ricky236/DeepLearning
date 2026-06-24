(() => {
  const nav = document.querySelector(".navbar .nav-main");
  if (!nav) return;

  const links = Array.from(nav.querySelectorAll("a"));
  if (!links.length) return;

  const indicator = document.createElement("div");
  indicator.className = "nav-indicator";
  nav.appendChild(indicator);

  const getActive = () => nav.querySelector("a.active") || links[0];

  const placeTo = (el, { show } = { show: true }) => {
    if (!el) return;
    const navRect = nav.getBoundingClientRect();
    const r = el.getBoundingClientRect();
    const left = r.left - navRect.left;
    const width = r.width;
    indicator.style.width = `${Math.max(0, width)}px`;
    indicator.style.transform = `translateX(${Math.max(0, left)}px)`;
    indicator.style.opacity = show ? "1" : indicator.style.opacity;
  };

  const snapToActive = () => placeTo(getActive(), { show: false });

  
  requestAnimationFrame(() => {
    snapToActive();
  });

  
  links.forEach((a) => {
    a.addEventListener("mouseenter", () => placeTo(a));
    a.addEventListener("focus", () => placeTo(a));
    a.addEventListener("click", () => {
      
      links.forEach((x) => x.classList.remove("active"));
      a.classList.add("active");
      placeTo(a);
    });
  });

  nav.addEventListener("mouseleave", () => snapToActive());

  
  window.addEventListener("resize", () => snapToActive());
})();

