// productivity-boost.com — progressive enhancement only: everything is readable without this file.
(function () {
  "use strict";
  var root = document.documentElement;

  // header hairline once the page scrolls (sentinel, no scroll listener)
  var top = document.querySelector(".top"), sentinel = document.querySelector(".sentinel");
  if (top && sentinel && "IntersectionObserver" in window) {
    new IntersectionObserver(function (e) { top.classList.toggle("scrolled", !e[0].isIntersecting); }).observe(sentinel);
  }

  // theme: system -> light -> dark
  var btn = document.querySelector(".theme");
  if (btn) {
    var labels = JSON.parse(btn.getAttribute("data-labels"));
    var cur = function () { return root.dataset.theme || "system"; };
    var paint = function () { btn.setAttribute("aria-label", labels[cur()]); };
    paint();
    btn.addEventListener("click", function () {
      var next = { system: "light", light: "dark", dark: "system" }[cur()];
      if (next === "system") { delete root.dataset.theme; } else { root.dataset.theme = next; }
      try { next === "system" ? localStorage.removeItem("theme") : localStorage.setItem("theme", next); } catch (e) {}
      paint();
    });
  }

  // menu: close on link click and on Escape
  var menu = document.querySelector(".menu");
  if (menu) {
    menu.addEventListener("click", function (e) { if (e.target.closest("a")) menu.open = false; });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && menu.open) { menu.open = false; menu.querySelector("summary").focus(); }
    });
    document.addEventListener("click", function (e) { if (menu.open && !menu.contains(e.target)) menu.open = false; });
    menu.addEventListener("focusout", function (e) { if (menu.open && e.relatedTarget && !menu.contains(e.relatedTarget)) menu.open = false; });
  }

  // earlier-work rail: a focusable, labelled scroll region only when it actually scrolls (phones)
  var rail = document.querySelector(".rail");
  if (rail) {
    var fitRail = function () {
      if (rail.scrollWidth > rail.clientWidth + 2) { rail.tabIndex = 0; rail.setAttribute("aria-label", rail.getAttribute("data-label")); }
      else { rail.removeAttribute("tabindex"); rail.removeAttribute("aria-label"); }
    };
    fitRail();
    window.addEventListener("resize", fitRail);
  }

  // decision panel: tabs (WAI-ARIA tabs pattern) + the bars settle once
  var tabs = Array.prototype.slice.call(document.querySelectorAll(".tabs [role=tab]"));
  var panels = Array.prototype.slice.call(document.querySelectorAll(".dpanel"));
  function show(i, focus) {
    tabs.forEach(function (t, j) {
      var on = i === j;
      t.setAttribute("aria-selected", on ? "true" : "false");
      t.tabIndex = on ? 0 : -1;
      panels[j].hidden = !on;
      panels[j].classList.toggle("on", on);
      panels[j].classList.remove("play");
    });
    void panels[i].offsetWidth;
    panels[i].classList.add("play");
    if (focus) tabs[i].focus();
  }
  if (tabs.length && panels.length === tabs.length) {
    panels.forEach(function (p, j) { p.setAttribute("role", "tabpanel"); p.setAttribute("aria-labelledby", tabs[j].id); });
    tabs.forEach(function (t, i) {
      t.addEventListener("click", function () { show(i, false); });
      t.addEventListener("keydown", function (e) {
        var k = e.key, n = tabs.length, j = null;
        if (k === "ArrowRight") j = (i + 1) % n; else if (k === "ArrowLeft") j = (i - 1 + n) % n;
        else if (k === "Home") j = 0; else if (k === "End") j = n - 1;
        if (j !== null) { e.preventDefault(); show(j, true); }
      });
    });
    show(0, false);
  }
})();
