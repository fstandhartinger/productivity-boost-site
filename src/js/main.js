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
    const st = (b.closest('dialog') || d).querySelector('[data-copy-status]');
    if (st) st.textContent = b.dataset.copied;
    const sp = $('span', b); const old = sp.textContent; sp.textContent = b.dataset.copied;
    setTimeout(() => { sp.textContent = old; if (st) st.textContent = ''; }, 2000);
  } catch (e) {}
}));

// ---------- write me: small sheet with address, copy, open mail app ----------
const mail = $('#mail');
const sheet = $('#sheet');
const openDialog = (dlg) => { if (!dlg || !dlg.showModal) return false; d.querySelectorAll('dialog[open]').forEach((x) => x.close()); dlg.showModal(); return true; };
$$('dialog').forEach((dlg) => dlg.addEventListener('click', (e) => { if (e.target === dlg) dlg.close(); })); // backdrop
$$('[data-mail]').forEach((a) => a.addEventListener('click', (e) => { if (openDialog(mail)) e.preventDefault(); }));
$$('[data-open-sheet]').forEach((b) => b.addEventListener('click', () => openDialog(sheet)));
$$('#sheet a').forEach((a) => a.addEventListener('click', () => sheet.close()));
// after any jump to a station, move focus to its heading (keyboard + screen readers land there too)
const focusStation = (id) => { const h = d.getElementById(id)?.querySelector('h2'); if (h) { h.tabIndex = -1; h.focus({ preventScroll: true }); } };
d.addEventListener('click', (e) => {
  const a = e.target.closest('a[href*="#"]'); if (!a || e.defaultPrevented) return;
  const id = a.getAttribute('href').split('#')[1]; if (id && d.getElementById(id)?.matches('section.station, section.works-group')) setTimeout(() => focusStation(id), 0);
});

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
    const cn = $('[data-curname]'); if (cn && NAMES[id]) cn.textContent = `${NAMES[id].f} · ${NAMES[id].n}`;
    const top = $('.top'); if (top) top.dataset.st = id;
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
    if (bbar) { const on = scrollY > innerHeight * 0.9; if (on !== bbar.classList.contains('on')) { bbar.classList.toggle('on', on); bbar.inert = !on; } }
  };
  addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
  addEventListener('resize', update);
  update();
}
// close the sheet after choosing a station

// ---------- the instrument ----------
const inst = $('.inst');
if (inst) initInstrument(inst);

function initInstrument(inst) {
  const plot = $('.plot', inst), canvas = $('canvas', plot), ctx = canvas.getContext('2d', { alpha: false });
  const range = $('.needle-range', inst), readout = $('.readout', inst), rname = $('.rname', readout), rsub = $('.rsub', readout);
  const rnum = $('.rnum', readout), go = $('a', readout), stat = $('.static', plot);
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
    inst.classList.add('locked');
    $$('.ruler .st', inst).forEach((a) => a.setAttribute('aria-current', a.dataset.st === id ? 'true' : 'false'));
    setNum(n.f);
    readout.classList.remove('locked'); void readout.offsetWidth; readout.classList.add('locked');
    rname.textContent = n.n; rsub.textContent = n.r; go.href = '#' + id;
    const i = ORDER_BAND.indexOf(id);
    range.value = String(i);
    range.setAttribute('aria-valuetext', `${n.f} ${lang === 'de' ? 'Megahertz' : 'megahertz'}, ${n.n}`);
    if (user && motion()) {
      const now = performance.now();
      if (now - lastBurst > 500) { lastBurst = now; stat.classList.remove('burst'); void stat.offsetWidth; stat.classList.add('burst'); }
    }
  }
  range.addEventListener('input', () => lock(ORDER_BAND[+range.value], true));
  function tuneTo(id, e) {
    const target = d.getElementById(id); if (!target) return;
    if (!d.startViewTransition || !motion()) return; // plain anchor jump
    e.preventDefault();
    lock(id, false);
    rnum.style.viewTransitionName = 'freq';
    const vt = d.startViewTransition(() => {
      rnum.style.viewTransitionName = '';
      const num = $('.st-num svg', target); if (num) num.style.viewTransitionName = 'freq';
      target.scrollIntoView({ block: 'start' });
      history.pushState(null, '', '#' + id);
    });
    vt.finished.finally(() => { const num = $('.st-num svg', target); if (num) num.style.viewTransitionName = ''; const h = $('h2', target); if (h) { h.tabIndex = -1; h.focus({ preventScroll: true }); } });
  }
  const coarse = matchMedia('(pointer: coarse)').matches;
  $$('[data-tune]', inst).forEach((a) => a.addEventListener('click', (e) => {
    const id = a.dataset.tune;
    if (coarse && current_lock !== id) { e.preventDefault(); lock(id, true); rsub.textContent = NAMES[id].r; return; } // preview first
    tuneTo(id, e);
  }));
  go.addEventListener('click', (e) => tuneTo(go.getAttribute('href').slice(1), e));
  $$('.ruler .st, .plot .hit', inst).forEach((a) => {
    a.addEventListener('pointerenter', (e) => { if (e.pointerType === 'mouse') lock(a.dataset.tune, true); });
    a.addEventListener('focus', () => lock(a.dataset.tune, false));
  });
  // pointer drag across the plot on desktop = tuning preview (no scroll hijack)
  plot.addEventListener('pointermove', (e) => {
    if (e.pointerType !== 'mouse') return;
    const r = plot.getBoundingClientRect(); const f = BAND_MIN + ((e.clientX - r.left) / r.width) * (BAND_MAX - BAND_MIN);
    let best = ORDER_BAND[0]; for (const id of ORDER_BAND) if (Math.abs(FREQ[id] - f) < Math.abs(FREQ[best] - f)) best = id;
    if (inst.dataset.st !== best || !inst.classList.contains('locked')) lock(best, true);
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
  function done() { revealed = true; plot.classList.add('live'); if (!inst.classList.contains('locked')) lock('decisions', false); shimmer(); }
  let tShim = 0, lastShim = 0;
  let shimT = 0;
  function shimmer() {
    cancelAnimationFrame(raf); clearTimeout(shimT);
    const strip = 6;
    const tick = () => {
      if (!motion() || !visible) return;
      tShim++; paintRows(ctx, sp, layout, 0, strip, 0, tShim);
      shimT = setTimeout(() => requestAnimationFrame(tick), 85);
    };
    tick();
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
    $$('video.loop').forEach((v) => { if (paused) v.pause(); else if (v.closest('.in')) v.play().catch(() => {}); });
    if (!paused && revealed) shimmer();
  });
  if (paused) { pauseBtn?.setAttribute('aria-pressed', 'true'); pauseBtn?.setAttribute('aria-label', pauseBtn.dataset.lPlay); }
  // skip the reveal on any key/tap
  const skip = () => { if (!revealed && sp) { cancelAnimationFrame(raf); paintAll(); done(); } };
  addEventListener('keydown', skip, { once: true });
  plot.addEventListener('pointerdown', skip, { once: true });

  async function boot() {
    try { band = await (await fetch('/js/band.json')).json(); } catch (e) { return; }
    if (!root.classList.contains('motion')) { revealed = true; lock('decisions', false); return; } // the static image is the final frame
    size();
    // start when the panel is in view (it usually is on load)
    const st = new IntersectionObserver(([e]) => { if (e.isIntersecting) { st.disconnect(); paused ? (paintAll(), done()) : reveal(); } });
    st.observe(plot);
  }
  let rs = 0;
  addEventListener('resize', () => { clearTimeout(rs); rs = setTimeout(() => {
    if (!band || !sp) return;
    const r = plot.getBoundingClientRect(), dpr = Math.min(1.5, devicePixelRatio || 1);
    if (Math.round(r.width * dpr) === w && Math.round(r.height * dpr) === h) return; // e.g. the phone URL bar: nothing to redraw
    size(); paintAll(); if (current_lock) lock(current_lock, false);
  }, 200); });
  const idle = window.requestIdleCallback || ((f) => setTimeout(f, 200));
  if (d.readyState === 'complete') idle(boot); else addEventListener('load', () => idle(boot), { once: true });
}

// ---------- VR loop: its own pause control ----------
$$('[data-vid]').forEach((b) => {
  const v = b.parentElement.querySelector('video'); if (!v) return;
  const sync = () => { const p = v.paused; b.setAttribute('aria-pressed', String(p)); b.setAttribute('aria-label', p ? b.dataset.lPlay : b.dataset.lPause); b.innerHTML = p ? '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 1.5v9l7.5-4.5z" fill="currentColor"/></svg>' : '<svg viewBox="0 0 12 12" aria-hidden="true"><rect x="2" y="1" width="3" height="10" fill="currentColor"/><rect x="7" y="1" width="3" height="10" fill="currentColor"/></svg>'; };
  v.addEventListener('play', sync); v.addEventListener('pause', sync); sync();
  b.addEventListener('click', () => { if (v.paused) v.play().catch(() => {}); else v.pause(); });
});
