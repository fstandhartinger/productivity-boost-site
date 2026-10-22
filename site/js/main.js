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
const nl = navigator.language || '';
if (hint && ((lang === 'en' && /^de\b/i.test(nl)) || (lang === 'de' && nl && !/^de\b/i.test(nl)))) {
  let off = false;
  try { off = localStorage.getItem('hint') === '0'; } catch (e) {}
  if (!off) {
    hint.hidden = false; hint.classList.add('on');
    // a hint, not a banner: it leaves once the visitor starts reading
    const away = () => { if (scrollY > innerHeight * 0.5) { hint.hidden = true; removeEventListener('scroll', away); } };
    addEventListener('scroll', away, { passive: true });
  }
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
const navLinks = $$('.stations-nav a, .sheet a'); // the ruler's own lock reflects tuning only
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
  if (navNeedle && frac != null) { navNeedle.style.transform = `translateX(${frac.toFixed(1)}px)`; navNeedle.classList.add('on'); }
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
    // in the hero (nothing reached yet) or past the last station (manifesto, 108.0, footer): no station is current
    if (best !== null && best === sections.length - 1 && sections[best].getBoundingClientRect().bottom < mid) best = null;
    if (best === null) {
      if (current !== null) { current = null; navLinks.forEach((a) => a.setAttribute('aria-current', 'false')); const cn = $('[data-curname]'); if (cn) cn.textContent = ''; }
      if (navNeedle) navNeedle.classList.remove('on');
      if (bbar && bbar.classList.contains('on')) { bbar.classList.remove('on'); bbar.inert = true; }
      return;
    }
    const sec = sections[best];
    const r = sec.getBoundingClientRect();
    const next = sections[best + 1];
    let t = 0;
    if (next) { const rn = next.getBoundingClientRect(); const span = rn.top - r.top; t = Math.min(1, Math.max(0, (mid - r.top) / span)); t = t < 0.7 ? 0 : (t - 0.7) / 0.3; }
    if (links.length) {
      const a = links.find((l) => l.dataset.st === sec.dataset.st);
      const b = next ? links.find((l) => l.dataset.st === next.dataset.st) : null;
      // needle x in px inside its track, on the centre of the active station's frequency
      const box = navNeedle ? navNeedle.parentElement.getBoundingClientRect() : null;
      const ca = a ? $('b', a).getBoundingClientRect() : null, cb = b ? $('b', b).getBoundingClientRect() : null;
      if (ca && box && box.width) { const xa = ca.left + ca.width / 2 - box.left, xb = cb ? cb.left + cb.width / 2 - box.left : xa; frac = xa + (xb - xa) * t; }
    }
    setCurrent(sec.dataset.st, frac);
    if (bbar) { const on = scrollY > innerHeight * 0.9; if (on !== bbar.classList.contains('on')) { bbar.classList.toggle('on', on); bbar.inert = !on; } }
  };
  addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
  addEventListener('resize', update);
  // the header reflows when it leaves the dark hero (brand subline); re-place the needle then
  if (links.length && 'ResizeObserver' in window) new ResizeObserver(() => { if (!ticking) { ticking = true; requestAnimationFrame(update); } }).observe(links[0].closest('ol'));
  update();
}
// close the sheet after choosing a station

// ---------- the instrument ----------
// the SSTV picture decodes once per visit; layout changes (resize, rotate) must not replay it
$$('.sstv img').forEach((i) => i.addEventListener('animationend', () => { i.style.animation = 'none'; }, { once: true }));
const inst = $('.inst');
if (inst) initInstrument(inst);

function initInstrument(inst) {
  const plot = $('.plot', inst), canvas = $('canvas', plot), ctx = canvas.getContext('2d');
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
    inst.classList.add('locked'); readout.classList.add('tuned');
    $$('.ruler .st', inst).forEach((a) => a.setAttribute('aria-current', a.dataset.st === id ? 'true' : 'false'));
    setNum(n.f);
    if (user) { readout.classList.remove('locked'); void readout.offsetWidth; readout.classList.add('locked'); }
    rname.innerHTML = ''; rname.append(n.n + ' '); const em = d.createElement('em'); em.textContent = n.p || ''; rname.append(em); rsub.textContent = n.r; go.href = '#' + id; go.setAttribute('aria-label', `${go.dataset.aria}: ${n.n}`);
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
  // touch: the first tap previews (read-out shows name + plain sentence); plot columns only ever preview on touch;
  // the ruler label tapped again, or the read-out's ↓, jumps. Mouse clicks and keyboard/screen-reader activation jump at once.
  let lastPointer = '', previewed = null;
  inst.addEventListener('pointerdown', (e) => { lastPointer = e.pointerType; }, true);
  $$('[data-tune]', inst).forEach((a) => a.addEventListener('click', (e) => {
    const id = a.dataset.tune, touch = (lastPointer === 'touch' || lastPointer === 'pen') && e.detail > 0;
    lastPointer = '';
    if (touch && (a.classList.contains('hit') || previewed !== id)) { e.preventDefault(); previewed = id; lock(id, true); return; }
    previewed = null; tuneTo(id, e);
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
    const r = plot.getBoundingClientRect(); const dpr = Math.min(1.25, devicePixelRatio || 1);
    w = Math.max(1, Math.round(r.width * dpr)); h = Math.max(1, Math.round(r.height * dpr));
    canvas.width = w; canvas.height = h;
    sp = spectra(band, w); layout = { w, h };
  }
  function paintAll() { paintRows(ctx, sp, layout, 0, sp.rows.length); }
  function reveal() {
    const n = sp.rows.length, dur = 2200; let i = n - 1; const t0 = performance.now();
    layout.rows = layout.rows || rowLayout(sp.rows, h);
    // start from the noise floor, then receive 1987 → Oct 2026; new rows enter at the top and push history down
    plot.classList.add('live'); // canvas starts transparent over the CSS noise floor
    const step = (now) => {
      if (!motion()) { paintAll(); return done(); }
      const target = Math.min(n, Math.floor(((now - t0) / dur) * n));
      while (n - 1 - i < target && i >= 0) {
        const hh = Math.round(layout.rows.tops[i + 1] ?? h) - Math.round(layout.rows.tops[i]);
        ctx.globalCompositeOperation = 'copy'; ctx.drawImage(canvas, 0, 0, w, h - hh, 0, hh, w, h - hh); ctx.globalCompositeOperation = 'source-over';
        paintRows(ctx, sp, layout, i, i + 1, -Math.round(layout.rows.tops[i]));
        i--;
      }
      if (i >= 0) raf = requestAnimationFrame(step); else done();
    };
    raf = requestAnimationFrame(step);
  }
  function done() { revealed = true; plot.classList.add('live', 'done'); shimmer(); }
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
    $$('video.loop').forEach((v) => { if (paused) v.pause(); else if (v.closest('.in')) v.play().catch(() => {}); });
    if (!paused && revealed) shimmer();
  });
  if (paused) { pauseBtn?.setAttribute('aria-pressed', 'true'); }
  // skip the reveal on any key/tap
  const skip = () => { if (!revealed && sp) { cancelAnimationFrame(raf); paintAll(); done(); } };
  addEventListener('keydown', skip, { once: true });
  plot.addEventListener('pointerdown', skip, { once: true });

  async function boot() {
    try { band = await (await fetch('/js/band.json')).json(); } catch (e) { root.classList.remove('motion'); return; } // static image + labels
    if (!root.classList.contains('motion')) { revealed = true; return; } // the static image is the final frame
    size();
    // start when the panel is in view (it usually is on load)
    const st = new IntersectionObserver(([e]) => { if (e.isIntersecting) { st.disconnect(); paused ? (paintAll(), done()) : reveal(); } });
    st.observe(plot);
  }
  let rs = 0;
  addEventListener('resize', () => { clearTimeout(rs); rs = setTimeout(() => {
    if (!band || !sp) return;
    const r = plot.getBoundingClientRect(), dpr = Math.min(1.25, devicePixelRatio || 1);
    if (Math.round(r.width * dpr) === w && Math.round(r.height * dpr) === h) return; // e.g. the phone URL bar: nothing to redraw
    size(); paintAll();
  }, 200); });
  const idle = window.requestIdleCallback || ((f) => setTimeout(f, 200));
  if (d.readyState === 'complete') idle(boot); else addEventListener('load', () => idle(boot), { once: true });
}

// ---------- VR loop: its own pause control ----------
$$('[data-vid]').forEach((b) => {
  const v = b.parentElement.querySelector('video'); if (!v) return;
  const sync = () => { const p = v.paused; b.setAttribute('aria-pressed', String(p)); b.innerHTML = p ? '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 1.5v9l7.5-4.5z" fill="currentColor"/></svg>' : '<svg viewBox="0 0 12 12" aria-hidden="true"><rect x="2" y="1" width="3" height="10" fill="currentColor"/><rect x="7" y="1" width="3" height="10" fill="currentColor"/></svg>'; };
  v.addEventListener('play', sync); v.addEventListener('pause', sync); sync();
  b.addEventListener('click', () => { if (v.paused) v.play().catch(() => {}); else v.pause(); });
});

// ---------- header: dark while the dark hero is under it ----------
const topbar = $('.top.on-dark'), heroEl = $('.hero');
if (topbar && heroEl) new IntersectionObserver(([e]) => topbar.classList.toggle('on-dark', e.isIntersecting), { rootMargin: `-${56}px 0px 0px 0px`, threshold: 0 }).observe(heroEl);
