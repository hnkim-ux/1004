(function () {
  var P = window.PROFILE;

  var ICONS = {
    layers: '<path d="M12 3 2 8l10 5 10-5-10-5z"/><path d="m2 13 10 5 10-5"/>',
    signal: '<path d="M2 12h4l3-7 4 14 3-7h6"/>',
    shield: '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3z"/><path d="m9 12 2 2 4-4"/>',
    doc: '<path d="M14 3H6v18h12V7l-4-4z"/><path d="M14 3v4h4M9 13h6M9 17h6"/>',
  };

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function $(id) { return document.getElementById(id); }
  function chips(list) {
    return '<div class="chips">' + list.map(function (t) { return '<span class="chip">' + esc(t) + "</span>"; }).join("") + "</div>";
  }

  // 단순 텍스트 바인딩
  document.querySelectorAll("[data-bind]").forEach(function (el) {
    el.textContent = P[el.dataset.bind];
  });
  $("year").textContent = new Date().getFullYear();

  $("about-text").innerHTML = P.about.map(function (p) { return "<p>" + esc(p) + "</p>"; }).join("");
  $("highlights").innerHTML = P.highlights
    .map(function (h) { return "<li><strong>" + esc(h.value) + "</strong><span>" + esc(h.label) + "</span></li>"; })
    .join("");

  $("expertise-list").innerHTML = P.expertise
    .map(function (e) {
      return (
        '<article class="card"><div class="card-icon"><svg viewBox="0 0 24 24" aria-hidden="true">' +
        (ICONS[e.icon] || ICONS.layers) +
        "</svg></div><h3>" + esc(e.title) + "</h3><ul>" +
        e.items.map(function (i) { return "<li>" + esc(i) + "</li>"; }).join("") +
        "</ul></article>"
      );
    })
    .join("");

  $("skills-list").innerHTML = P.skills
    .map(function (s) { return "<div><h3>" + esc(s.group) + "</h3>" + chips(s.items) + "</div>"; })
    .join("");

  $("projects-list").innerHTML = P.projects
    .map(function (p) {
      return (
        '<article class="card"><div class="project-head"><h3>' + esc(p.title) + "</h3>" +
        '<span class="project-period">' + esc(p.period) + "</span></div>" +
        '<span class="tag">' + esc(p.system) + "</span>" +
        '<p class="project-role">' + esc(p.role) + "</p>" +
        '<div class="metrics">' +
        p.metrics.map(function (m) { return "<div><strong>" + esc(m.value) + "</strong><span>" + esc(m.label) + "</span></div>"; }).join("") +
        "</div>" + chips(p.tools) + "</article>"
      );
    })
    .join("");

  $("experience-list").innerHTML = P.experience
    .map(function (x) {
      return '<li><span class="when">' + esc(x.period) + "</span><h3>" + esc(x.org) + "</h3><p>" + esc(x.role) + "</p></li>";
    })
    .join("");

  // Contact
  var link = $("email-link");
  link.href = "mailto:" + P.email;
  link.textContent = P.email;

  var toast = $("toast"), toastTimer;
  function showToast(msg) {
    toast.textContent = msg;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.classList.remove("show"); }, 2000);
  }
  $("copy-email").addEventListener("click", function () {
    var done = function () { showToast("이메일 주소를 복사했습니다"); };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(P.email).then(done, fallback);
    } else {
      fallback();
    }
    function fallback() {
      var ta = document.createElement("textarea");
      ta.value = P.email;
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); done(); } catch (e) { showToast(P.email); }
      ta.remove();
    }
  });

  // 테마 전환
  var root = document.documentElement;
  document.querySelector(".theme-toggle").addEventListener("click", function () {
    var current = root.dataset.theme ||
      (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    var next = current === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch (e) {}
  });

  // 현재 섹션 메뉴 강조
  var links = document.querySelectorAll(".nav-links a");
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        links.forEach(function (a) { a.classList.toggle("active", a.getAttribute("href") === "#" + en.target.id); });
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    document.querySelectorAll("main section[id]").forEach(function (s) { io.observe(s); });
  }
})();
