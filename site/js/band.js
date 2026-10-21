// Waterfall renderer: frequency (x) = genre, rows = time, newest row on top.
// Pure functions + one draw routine; used in the browser and by the build (Playwright) for static images.

export const BAND_MIN = 87.5;
export const BAND_MAX = 108.0;

// "BOOST" colour map: indigo -> electric blue -> cyan -> phosphor green -> the old productivity-boost green -> warm white.
const STOPS = [
  [0.00, [5, 6, 10]],
  [0.12, [11, 11, 28]],
  [0.24, [22, 24, 80]],
  [0.37, [28, 74, 168]],
  [0.50, [20, 136, 150]],
  [0.62, [30, 184, 108]],
  [0.74, [104, 214, 58]],
  [0.85, [196, 234, 78]],
  [0.94, [246, 242, 160]],
  [1.00, [255, 252, 236]],
];

export function colormap(t) {
  t = t < 0 ? 0 : t > 1 ? 1 : t;
  for (let i = 1; i < STOPS.length; i++) {
    const [p1, c1] = STOPS[i];
    if (t <= p1) {
      const [p0, c0] = STOPS[i - 1];
      const k = (t - p0) / (p1 - p0);
      return [0, 1, 2].map((j) => Math.round(c0[j] + (c1[j] - c0[j]) * k));
    }
  }
  return STOPS[STOPS.length - 1][1];
}

let LUT = null;
function lut() {
  if (LUT) return LUT;
  LUT = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    const [r, g, b] = colormap(i / 255);
    LUT[i] = (255 << 24) | (b << 16) | (g << 8) | r; // little-endian RGBA
  }
  return LUT;
}

// Rows, newest first: 2026-10 ... 2025-01, then 2024 ... 1987.
export function buildRows(band) {
  const rows = [];
  const [m0, m1] = band.rows.monthly;
  let [y, m] = m1.split('-').map(Number);
  const [y0, mm0] = m0.split('-').map(Number);
  while (y > y0 || (y === y0 && m >= mm0)) {
    rows.push({ key: `${y}-${String(m).padStart(2, '0')}`, t0: y + (m - 1) / 12, t1: y + m / 12, monthly: true, year: y, month: m });
    m--; if (m === 0) { m = 12; y--; }
  }
  const [ya, yb] = band.rows.yearly;
  for (let yy = yb; yy >= ya; yy--) rows.push({ key: String(yy), t0: yy, t1: yy + 1, monthly: false, year: yy });
  // one declared logarithmic time axis: the closer to today, the more room
  const T = rows[0].t1, c = band.rows.logC || 0.25;
  rows.forEach((r) => { r.w = Math.log(T - r.t0 + c) - Math.log(T - r.t1 + c); });
  return rows;
}

// Pixel layout of the rows for a plot of height h: returns {tops, heights, total} in device px.
export function rowLayout(rows, h) {
  const sum = rows.reduce((a, r) => a + r.w, 0);
  const tops = [], hs = [];
  let acc = 0;
  rows.forEach((r) => { tops.push((acc / sum) * h); acc += r.w; hs.push((r.w / sum) * h); });
  return { tops, heights: hs, total: h };
}

function toT(v, end) {
  if (typeof v === 'number') return end ? v + 1 : v;
  const [y, m] = v.split('-').map(Number);
  return end ? y + m / 12 : y + (m - 1) / 12;
}

export function freqX(f, w) { return ((f - BAND_MIN) / (BAND_MAX - BAND_MIN)) * w; }

// Small deterministic PRNG so the build image and the live canvas match.
function rng(seed) {
  let s = seed >>> 0 || 1;
  return () => { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; return ((s >>> 0) % 100000) / 100000; };
}

const g = (d, s) => Math.exp(-(d * d) / (2 * s * s));

// One spectrum per data row (length w). Intensity roughly 0..1.2.
export function spectra(band, w, opts = {}) {
  const rows = buildRows(band);
  const st = Object.fromEntries(band.stations.map((s) => [s.id, s]));
  const S = (w * 2.6) / (BAND_MAX - BAND_MIN); // typical station spacing in px
  const only = opts.station || null;
  const out = rows.map(() => new Float32Array(w));
  const r = rng(92);
  band.entries.forEach((e, ei) => {
    if (only && e.st !== only && e.side !== only) return;
    const a = toT(e.from, false), b = toT(e.to, true);
    const cx = freqX(st[e.st].freq, w);
    const nx = e.side ? freqX(st[e.side].freq, w) : null;
    let firstRow = -1;
    rows.forEach((row, ri) => { if (Math.min(b, row.t1) - Math.max(a, row.t0) > 0) firstRow = ri; }); // newest-first: last match = oldest row
    rows.forEach((row, ri) => {
      const overlap = Math.min(b, row.t1) - Math.max(a, row.t0);
      if (overlap <= 0) return;
      const cover = Math.min(1, overlap / (row.t1 - row.t0));
      const life = 0.86 + 0.14 * r();
      const L = e.level * cover * life;
      const spec = out[ri];
      for (let x = 0; x < w; x++) {
        const d = x - cx;
        let v = 0;
        if (e.kind === 'carrier') {
          v = L * (0.85 * g(d, Math.max(0.9, S * 0.012)) + 0.22 * g(d, S * 0.06));
        } else if (e.scope === 1) {
          v = L * (0.95 * g(d, S * 0.05) + 0.16 * g(d, S * 0.14));
        } else if (e.scope === 2) {
          v = L * (0.72 * g(d - S * 0.06, S * 0.04) + 0.72 * g(d + S * 0.06, S * 0.04) + 0.12 * g(d, S * 0.16));
        } else {
          const hw = S * 0.1;
          const ad = Math.abs(d);
          const top = ad < hw ? 1 : g(ad - hw, S * 0.035);
          v = L * (0.62 * top * (0.8 + 0.2 * Math.sin(x * 1.3 + ei)) + 0.08 * g(d, S * 0.14));
        }
        if (nx !== null && opts.sidebands && ri === firstRow) {
          // sideband toward the neighbour station: a faint ridge + a small pilot at the neighbour
          const lo = Math.min(cx, nx), hi = Math.max(cx, nx);
          if (x > lo && x < hi) v += L * 0.22 * Math.sin(Math.PI * (x - lo) / (hi - lo)) ** 0.6;
          v += L * 0.42 * g(x - nx, S * 0.03);
        }
        spec[x] += v;
      }
    });
  });
  return { rows, out };
}

// Draw rows [from, to) of the plot into an ImageData-backed canvas region.
// layout: {w, h, rowH} in device pixels. Noise is deterministic per (x, y) unless `t` (time) is given for the live strip.
const NOISE = (() => { const n = new Float32Array(8192); const r = rng(1987); for (let i = 0; i < n.length; i++) n[i] = r(); return n; })();

// Tone map: soft roll-off toward white so wide signals glow instead of clipping into blocks.
const TONE = (() => { const t = new Uint8Array(1200); for (let i = 0; i < t.length; i++) { const v = i / 400; t[i] = Math.min(255, Math.round((1 - Math.exp(-v * 1.75)) * 262)); } return t; })();

export function paintRows(ctx, sp, layout, rowFrom, rowTo, yOffset = 0, t = 0) {
  const { w, h } = layout;
  const L = lut();
  const lay = layout.rows || (layout.rows = rowLayout(sp.rows, h));
  const y0 = Math.round(lay.tops[rowFrom]);
  const y1 = rowTo >= sp.rows.length ? Math.round(h) : Math.round(lay.tops[rowTo]);
  const hh = y1 - y0;
  if (hh <= 0) return;
  const img = ctx.createImageData(w, hh);
  const px = new Uint32Array(img.data.buffer);
  const tt = t ? Math.floor(t) * 131 : 0;
  let ri = rowFrom;
  for (let y = 0; y < hh; y++) {
    const gy = y0 + y;
    while (ri < sp.rows.length - 1 && gy >= lay.tops[ri + 1]) ri++;
    const spec = sp.out[ri];
    // soft attack/decay: blend toward the neighbouring rows near the row edges
    const fy = (gy - lay.tops[ri]) / Math.max(1, lay.heights[ri]);
    const prev = sp.out[ri - 1] || spec, next = sp.out[ri + 1] || spec;
    const kp = fy < 0.3 ? (0.3 - fy) / 0.6 : 0;
    const kn = fy > 0.7 ? (fy - 0.7) / 0.6 : 0;
    const flick = 0.88 + 0.24 * NOISE[(gy * 37 + tt) & 8191];
    const base = gy * 113 + tt;
    for (let x = 0; x < w; x++) {
      const n = NOISE[(base + x * 7) & 8191];
      const n2 = NOISE[(x * 3 + (gy >> 2) * 59) & 8191];
      const fade = 0.78 + 0.44 * NOISE[(gy * 41 + (x >> 3) * 11 + tt) & 8191];
      const sv = spec[x] * (1 - kp - kn) + prev[x] * kp + next[x] * kn;
      const v = 0.012 + 0.05 * n * n * n + 0.012 * n2 + sv * flick * fade;
      const i = (TONE[(v * 400) | 0] ?? 255);
      px[y * w + x] = L[i];
    }
  }
  ctx.putImageData(img, 0, yOffset + y0);
}
