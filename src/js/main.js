// productivity-boost.com — progressive enhancement only. Everything works without this file.
import { spectra, paintRows, rowLayout, freqX, BAND_MIN, BAND_MAX } from './band.js';

window.__fsboot = true;
const d = document, root = d.documentElement;
const $ = (s, el = d) => el.querySelector(s);
const $$ = (s, el = d) => [...el.querySelectorAll(s)];
const motion = () => root.classList.contains('motion') && !paused;
const lang = root.lang;
let paused = false;
try { paused = localStorage.getItem('pause') === '1'; } catch (e) {}

// ---------- theme ----------
$$('[data-theme-toggle]').forEach((b) => b.addEventListener('click', () => {
  const cur = root.getAttribute('data-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  const next = cur === 'dark' ? 'light' : 'dark';
  root.setAttribute('data-theme', next);
  try { localStorage.setItem('theme', next); } catch (e) {}
}));

// ---------- language hint (EN pages, German browsers) ----------
const hint = $('#langhint');
if (hint && lang === 'en' && /^de\b/i.test(navigator.language || '')) {
  let off = false;
  try { off = localStorage.getItem('hint') === '0'; } catch (e) {}
  if (!off) { hint.hidden = false; hint.classList.add('on'); }
  $('[data-close-hint]', hint)?.addEventListener('click', () => { hint.hidden = true; try { localStorage.setItem('hint', '0'); } catch (e) {} });
}

// ---------- copy address ----------
$$('[data-copy]').forEach((b) => b.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(b.dataset.copy);
    const st = $('[data-copy-status]');
    if (st) st.textContent = b.dataset.copied;
    const sp = $('span', b); const old = sp.textContent; sp.textContent = b.dataset.copied;
    setTimeout(() => { sp.textContent = old; if (st) st.textContent = ''; }, 2000);
  } catch (e) {}
}));

// ---------- logbook link ----------
function openLog() { const l = $('#logbook'); if (l) l.open = true; }
$$('[data-open-logbook]').forEach((a) => a.addEventListener('click', openLog));
if (location.hash === '#logbook') openLog();
addEventListener('hashchange', () => { if (location.hash === '#logbook') openLog(); });

// ---------- station names ----------
let NAMES = {};
try { NAMES = JSON.parse($('#st-names')?.textContent || '{}'); } catch (e) {}
const ORDER_BAND = ['worlds', 'systems', 'agents', 'studio', 'networks', 'benchmarks', 'decisions'];
const FREQ = { worlds: 88.7, systems: 91.4, agents: 93.9, studio: 96.6, networks: 99.2, benchmarks: 102.5, decisions: 105.8 };
const pct = (f) => ((f - BAND_MIN) / (BAND_MAX - BAND_MIN)) * 100;

// ---------- in-view effects (bars, logs, hops, loop video) ----------
const io = new IntersectionObserver((es) => es.forEach((e) => {
  if (e.isIntersecting) { e.target.classList.add('in'); }
  const v = e.target.querySelector?.('video.loop');
  if (v) { if (e.isIntersecting && motion()) v.play().catch(() => {}); else v.pause(); }
}), { rootMargin: '0px 0px -15% 0px' });
$$('.sig, .hop').forEach((el) => io.observe(el));

// ---------- current station: nav needle + bottom bar ----------
const navNeedle = $('.stations-nav .needle');
const navLinks = $$('.stations-nav a, .ruler .st, .sheet a');
const bbar = $('#bbar');
const sections = $$('section.station, section.works-group');
let current = null;
function setCurrent(id, frac) {
  if (id && id !== current) {
    current = id;
    navLinks.forEach((a) => a.setAttribute('aria-current', a.dataset.st === id ? 'true' : 'false'));
    if (bbar) {
      bbar.dataset.st = id;
      const n = NAMES[id];
      const f = $('[data-cur-f]', bbar), nn = $('[data-cur-n]', bbar);
      if (n && f) { f.textContent = n.f; nn.textContent = n.n; }
      else if (f) { const a = $(`.sheet a[data-st="${id}"]`); if (a) { f.textContent = $('b', a).textContent; nn.textContent = a.textContent.replace(f.textContent, ''); } }
    }
  }
  if (navNeedle && frac != null) {
    const track = navNeedle.parentElement.getBoundingClientRect().width;
    navNeedle.style.transform = `translateX(${(frac * track).toFixed(1)}px)`;
  }
}
if (sections.length) {
  // map scroll position to a continuous position along the nav (page order), so the needle glides through hops
  const links = $$('.stations-nav a');
  let ticking = false;
  const update = () => {
    ticking = false;
    const mid = innerHeight * 0.35;
    let best = null, frac = null;
    for (let i = 0; i < sections.length; i++) {
      const r = sections[i].getBoundingClientRect();
      if (r.top <= mid) best = i;
    }
    if (best === null) { setCurrent(sections[0].dataset.st, null); best = 0; }
    const sec = sections[best];
    const r = sec.getBoundingClientRect();
    const next = sections[best + 1];
    let t = 0;
    if (next) { const rn = next.getBoundingClientRect(); const span = rn.top - r.top; t = Math.min(1, Math.max(0, (mid - r.top) / span)); t = t < 0.7 ? 0 : (t - 0.7) / 0.3; }
    if (links.length) {
      const a = links.find((l) => l.dataset.st === sec.dataset.st);
      const b = next ? links.find((l) => l.dataset.st === next.dataset.st) : null;
      const box = links[0].closest('ol').getBoundingClientRect();
      const ca = a ? a.getBoundingClientRect() : null, cb = b ? b.getBoundingClientRect() : null;
      if (ca) { const xa = ca.left + 6 - box.left, xb = cb ? cb.left + 6 - box.left : xa; frac = (xa + (xb - xa) * t) / box.width; }
    }
    setCurrent(sec.dataset.st, frac);
    if (bbar) bbar.classList.toggle('on', scrollY > innerHeight * 0.9);
  };
  addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
  addEventListener('resize', update);
  update();
}
// close the sheet after choosing a station
$$('.sheet a').forEach((a) => a.addEventListener('click', () => { try { $('#sheet').hidePopover(); } catch (e) {} }));

// ---------- the instrument ----------
const inst = $('.inst');
if (inst) initInstrument(inst);

function initInstrument(inst) {
  const plot = $('.plot', inst), canvas = $('canvas', plot), ctx = canvas.getContext('2d', { alpha: false });
  const range = $('.needle-range', inst), readout = $('.readout', inst), rname = $('.rname', readout), rsub = $('.rsub', readout);
  const rnum = $('.rnum', readout), go = $('a', readout), needle = $('.needle-line', inst), stat = $('.static', plot);
  const pauseBtn = $('[data-pause]', inst);
  let band = null, sp = null, layout = null, w = 0, h = 0, revealed = false, raf = 0, lastBurst = 0;

  // numerals in the read-out use the same sprite as the page
  function setNum(txt) {
    let x = 0, uses = '';
    for (const ch of txt) { const code = ch.charCodeAt(0); const adv = (ch === '.' || ch === ',') ? 22 : 60; uses += `<use href="#g${code}" x="${x}" width="${adv}" height="100"/>`; x += adv + ((ch === '.' || ch === ',') ? 4 : 10); }
    rnum.setAttribute('viewBox', `-6 -6 ${x + 2} 112`); rnum.innerHTML = uses;
  }
  let current_lock = null;
  function lock(id, user) {
    const n = NAMES[id]; if (!n) return;
    current_lock = id;
    inst.dataset.st = id;
    $$('.col', plot).forEach((c) => c.classList.toggle('on', c.dataset.col === id));
    $$('.ruler .st', inst).forEach((a) => a.setAttribute('aria-current', a.dataset.st === id ? 'true' : 'false'));
    setNum(n.f);
    readout.classList.remove('locked'); void readout.offsetWidth; readout.classList.add('locked');
    rname.textContent = n.n; rsub.textContent = n.r; go.href = '#' + id; go.tabIndex = 0; readout.removeAttribute('aria-hidden');
    const pw = plot.parentElement; needle.style.left = `${(pw.offsetLeft + plot.offsetLeft + plot.offsetWidth * pct(FREQ[id]) / 100).toFixed(1)}px`;
    needle.style.top = `${pw.offsetTop}px`; needle.style.height = `${plot.offsetHeight}px`;
    needle.classList.add('on');
    const i = ORDER_BAND.indexOf(id);
    range.value = String(i);
    range.setAttribute('aria-valuetext', `${n.f} ${lang === 'de' ? 'Megahertz' : 'megahertz'}, ${n.n}`);
    if (user && motion()) {
      const now = performance.now();
      if (now - lastBurst > 500) { lastBurst = now; stat.classList.remove('burst'); void stat.offsetWidth; stat.classList.add('burst'); }
    }
  }
  range.addEventListener('input', () => lock(ORDER_BAND[+range.value], true));
  $$('.ruler .st, .plot .hit', inst).forEach((a) => {
    a.addEventListener('pointerenter', (e) => { if (e.pointerType === 'mouse') lock(a.dataset.tune, true); });
    a.addEventListener('focus', () => lock(a.dataset.tune, false));
    a.addEventListener('click', () => lock(a.dataset.tune, true));
  });
  // pointer drag across the plot on desktop = tuning preview (no scroll hijack)
  plot.addEventListener('pointermove', (e) => {
    if (e.pointerType !== 'mouse') return;
    const r = plot.getBoundingClientRect(); const f = BAND_MIN + ((e.clientX - r.left) / r.width) * (BAND_MAX - BAND_MIN);
    let best = ORDER_BAND[0]; for (const id of ORDER_BAND) if (Math.abs(FREQ[id] - f) < Math.abs(FREQ[best] - f)) best = id;
    if (inst.dataset.st !== best || !needle.classList.contains('on')) lock(best, true);
  });

  // ---- waterfall canvas ----
  function size() {
    const r = plot.getBoundingClientRect(); const dpr = Math.min(1.5, devicePixelRatio || 1);
    w = Math.max(1, Math.round(r.width * dpr)); h = Math.max(1, Math.round(r.height * dpr));
    canvas.width = w; canvas.height = h;
    sp = spectra(band, w); layout = { w, h };
  }
  function paintAll() { paintRows(ctx, sp, layout, 0, sp.rows.length); }
  function reveal() {
    const n = sp.rows.length, dur = 2200; let i = n - 1; const t0 = performance.now();
    layout.rows = layout.rows || rowLayout(sp.rows, h);
    // start from the noise floor, then receive 1987 → Oct 2026; new rows enter at the top and push history down
    const empty = { rows: sp.rows, out: sp.rows.map(() => new Float32Array(w)) };
    paintRows(ctx, empty, layout, 0, n);
    plot.classList.add('live');
    const step = (now) => {
      if (!motion()) { paintAll(); return done(); }
      const target = Math.min(n, Math.floor(((now - t0) / dur) * n));
      while (n - 1 - i < target && i >= 0) {
        const hh = Math.round(layout.rows.heights[i]);
        ctx.drawImage(canvas, 0, 0, w, h - hh, 0, hh, w, h - hh);
        paintRows(ctx, sp, layout, i, i + 1, -Math.round(layout.rows.tops[i]));
        i--;
      }
      if (i >= 0) raf = requestAnimationFrame(step); else { paintAll(); done(); }
    };
    raf = requestAnimationFrame(step);
  }
  function done() { revealed = true; plot.classList.add('live'); if (!$('.needle-line.on', inst)) lock('decisions', false); shimmer(); }
  let tShim = 0, lastShim = 0;
  function shimmer() {
    cancelAnimationFrame(raf);
    const strip = 6;
    const tick = (now) => {
      if (!motion() || !visible) return;
      if (now - lastShim > 85) { lastShim = now; tShim++; paintRows(ctx, sp, layout, 0, strip, 0, tShim); }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
  }
  let visible = true;
  const vio = new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible && revealed && motion()) shimmer(); });
  vio.observe(plot);
  d.addEventListener('visibilitychange', () => { visible = !d.hidden; if (visible && revealed && motion()) shimmer(); });

  pauseBtn?.addEventListener('click', () => {
    paused = !paused;
    try { localStorage.setItem('pause', paused ? '1' : '0'); } catch (e) {}
    pauseBtn.setAttribute('aria-pressed', String(paused));
    pauseBtn.setAttribute('aria-label', paused ? pauseBtn.dataset.lPlay : pauseBtn.dataset.lPause);
    $$('video.loop').forEach((v) => paused ? v.pause() : null);
    if (!paused && revealed) shimmer();
  });
  if (paused) { pauseBtn?.setAttribute('aria-pressed', 'true'); pauseBtn?.setAttribute('aria-label', pauseBtn.dataset.lPlay); }
  // skip the reveal on any key/tap
  const skip = () => { if (!revealed && sp) { cancelAnimationFrame(raf); paintAll(); done(); } };
  addEventListener('keydown', skip, { once: true });
  plot.addEventListener('pointerdown', skip, { once: true });

  async function boot() {
    try { band = await (await fetch('/js/band.json')).json(); } catch (e) { return; }
    size();
    if (!root.classList.contains('motion')) { paintAll(); plot.classList.add('live'); revealed = true; lock('decisions', false); return; }
    // start when the panel is in view (it usually is on load)
    const st = new IntersectionObserver(([e]) => { if (e.isIntersecting) { st.disconnect(); paused ? (paintAll(), done()) : reveal(); } });
    st.observe(plot);
  }
  let rs = 0;
  addEventListener('resize', () => { clearTimeout(rs); rs = setTimeout(() => {
    if (!band) return;
    const r = plot.getBoundingClientRect(), dpr = Math.min(1.5, devicePixelRatio || 1);
    if (Math.round(r.width * dpr) === w && Math.round(r.height * dpr) === h) return; // e.g. the phone URL bar: nothing to redraw
    size(); paintAll(); if (current_lock) lock(current_lock, false);
  }, 200); });
  const idle = window.requestIdleCallback || ((f) => setTimeout(f, 200));
  if (d.readyState === 'complete') idle(boot); else addEventListener('load', () => idle(boot), { once: true });
}
