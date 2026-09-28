(() => {
  const data = window.PORTFOLIO;
  if (!data) {
    document.getElementById("gallery").textContent = "photos.js not found — run: python build.py";
    return;
  }
  const { site, categories, photos } = data;
  const $ = (id) => document.getElementById(id);

  // Site text
  document.querySelectorAll("[data-site]").forEach((el) => {
    el.textContent = site[el.dataset.site] || "";
  });
  document.title = `${site.name} — Photography`;
  $("year").textContent = new Date().getFullYear();

  const hero = photos.find((p) => p.id === site.hero) || photos[0];
  $("hero-img").src = hero.large;

  const cameras = [...new Set(photos.map((p) => p.exif.camera).filter(Boolean))];
  const cameraNames = { "ILCE-7RM3": "Sony α7R III", "ILCE-7RM4": "Sony α7R IV", "ILCE-7M3": "Sony α7 III", "ILCE-7M4": "Sony α7 IV" };
  if (cameras.length) $("gear").textContent = cameras.map((c) => cameraNames[c] || c).join(" and ");

  const links = $("contact-links");
  if (site.email) links.insertAdjacentHTML("beforeend", `<a href="mailto:${site.email}">${site.email}</a>`);
  if (site.instagram) {
    const handle = site.instagram.replace(/^@/, "");
    links.insertAdjacentHTML("beforeend", `<a href="https://instagram.com/${handle}" target="_blank" rel="noopener">@${handle}</a>`);
  }
  if (!links.children.length) links.innerHTML = `<span class="placeholder">Add email / instagram in photos.meta.json</span>`;

  // Top bar background after scrolling past the top
  const topbar = document.querySelector(".topbar");
  const onScroll = () => topbar.classList.toggle("scrolled", window.scrollY > 40);
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // Filters
  let current = "All";
  const filters = $("filters");
  ["All", ...categories].forEach((cat) => {
    const b = document.createElement("button");
    b.type = "button";
    b.role = "tab";
    b.textContent = cat;
    b.setAttribute("aria-selected", cat === current);
    b.addEventListener("click", () => {
      current = cat;
      filters.querySelectorAll("button").forEach((x) => x.setAttribute("aria-selected", x === b));
      renderGallery();
    });
    filters.appendChild(b);
  });

  // Gallery
  const gallery = $("gallery");
  let visible = [];
  const reveal = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        e.target.classList.add("in");
        reveal.unobserve(e.target);
      }
    });
  }, { rootMargin: "0px 0px -40px 0px" });

  function renderGallery() {
    visible = current === "All" ? photos : photos.filter((p) => p.category === current);
    gallery.innerHTML = "";
    visible.forEach((p, i) => {
      const tile = document.createElement("button");
      tile.className = "tile";
      tile.style.setProperty("--r", p.ratio);
      tile.setAttribute("aria-label", `Open ${p.title}`);
      tile.innerHTML = `
        <img src="${p.thumb}" alt="${p.title}" loading="lazy" decoding="async">
        <span class="tile-cap"><strong>${p.title}</strong><span>${p.category}</span></span>`;
      tile.addEventListener("click", () => openLightbox(i));
      gallery.appendChild(tile);
      reveal.observe(tile);
    });
  }
  renderGallery();

  // Lightbox
  const lb = $("lightbox");
  const lbImg = $("lb-img");
  let index = 0;

  function show(i) {
    index = (i + visible.length) % visible.length;
    const p = visible[index];
    lbImg.classList.add("loading");
    lbImg.onload = () => lbImg.classList.remove("loading");
    lbImg.src = p.large;
    lbImg.alt = p.title;
    $("lb-title").textContent = p.title;
    $("lb-cat").textContent = p.category;
    const e = p.exif;
    $("lb-exif").innerHTML = [cameraNames[e.camera] || e.camera, e.lens, e.focal, e.aperture, e.shutter, e.iso]
      .filter(Boolean).map((s) => `<span>${s}</span>`).join("");
    history.replaceState(null, "", `#photo/${p.id}`);
    // Preload neighbours so arrowing through feels instant
    [index - 1, index + 1].forEach((n) => {
      new Image().src = visible[(n + visible.length) % visible.length].large;
    });
  }

  function openLightbox(i) {
    show(i);
    if (!lb.open) lb.showModal();
  }

  function closeLightbox() {
    lb.close();
  }

  lb.addEventListener("close", () => history.replaceState(null, "", "#work"));
  lb.addEventListener("click", (e) => {
    const action = e.target.closest("[data-action]")?.dataset.action;
    if (action === "close") closeLightbox();
    else if (action === "prev") show(index - 1);
    else if (action === "next") show(index + 1);
    else if (e.target === lb || e.target.classList.contains("lb-figure")) closeLightbox();
  });
  document.addEventListener("keydown", (e) => {
    if (!lb.open) return;
    if (e.key === "ArrowLeft") show(index - 1);
    if (e.key === "ArrowRight") show(index + 1);
  });

  let touchX = null;
  lb.addEventListener("touchstart", (e) => { touchX = e.touches[0].clientX; }, { passive: true });
  lb.addEventListener("touchend", (e) => {
    if (touchX === null) return;
    const dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 50) show(index + (dx < 0 ? 1 : -1));
    touchX = null;
  });

  // Deep link: #photo/<id>
  const match = location.hash.match(/^#photo\/(.+)$/);
  if (match) {
    const i = visible.findIndex((p) => p.id === match[1]);
    if (i >= 0) openLightbox(i);
  }
})();
