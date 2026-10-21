# -*- coding: utf-8 -*-
"""Static site generator for productivity-boost.com. Usage: python3 -I src/build.py  (writes ./site)"""
import base64, hashlib, html, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
OUT = os.path.join(ROOT, "site")
sys.path.insert(0, SRC)
from content import T, STATIONS, CARDS, HOPS, LOGBOOK, WORKS, EMAIL, X_URL, GH_URL, HF_URL, ASOF, FLAG, FLAG_DE  # noqa: E402

BASE_URL = os.environ.get("SITE_URL", "https://productivity-boost.app.mintapis.com")
BAND = json.load(open(os.path.join(SRC, "data", "band.json")))
ASSETS = json.load(open(os.path.join(SRC, "data", "assets.json"))) if os.path.exists(os.path.join(SRC, "data", "assets.json")) else {}
ST = {s["id"]: s for s in STATIONS}
BAND_ST = {s["id"]: s for s in BAND["stations"]}
FMIN, FMAX = 87.5, 108.0
ORDER = [s["id"] for s in STATIONS]

def esc(s):
    return html.escape(s, quote=True)

def xpct(freq):
    return (float(freq) - FMIN) / (FMAX - FMIN) * 100

# ---------- band numerals (custom single-stroke SVG glyphs) ----------
GLYPHS = {
 "0": "M30 6C15 6 8 22 8 50s7 44 22 44 22-16 22-44S45 6 30 6z",
 "1": "M17 20 33 6v88",
 "2": "M9 27C9 14 18 6 30 6s21 8 21 20c0 11-6 18-15 27L9 94h43",
 "3": "M10 6h40L28 40c15 0 24 9 24 26 0 17-11 28-25 28-10 0-17-5-21-12",
 "4": "M40 94V6L6 68h48",
 "5": "M50 6H15l-4 38c5-4 11-6 18-6 14 0 23 11 23 27 0 17-10 29-25 29-10 0-17-5-21-12",
 "6": "M46 8C26 14 8 33 8 62c0 20 9 32 22 32s22-11 22-28-10-27-22-27C18 39 9 48 8 60",
 "7": "M7 6h46L24 94",
 "8": "M30 47c-11 0-18-8-18-20S19 6 30 6s18 9 18 21-7 20-18 20zm0 0C16 47 8 57 8 71s9 23 22 23 22-9 22-23-8-24-22-24z",
 "9": "M14 92c20-6 38-26 38-55C52 18 43 6 30 6S8 17 8 33s9 27 22 27c11 0 19-7 22-17",
 ".": "M8 92.5v.1",
 ",": "M9 90l-5 11",
}
ADV = {".": 22, ",": 22}

def sprite():
    syms = "".join(f'<symbol id="g{ord(k)}" viewBox="0 0 {ADV.get(k,60)} 100" overflow="visible"><path d="{d}"/></symbol>' for k, d in GLYPHS.items())
    return f'<svg width="0" height="0" class="sr" aria-hidden="true" focusable="false"><defs>{syms}</defs></svg>'

def numerals(text, lang, cls="num", label=True):
    if lang == "de":
        text = text.replace(".", ",")
    x = 0; uses = []
    for ch in text:
        if ch not in GLYPHS:
            continue
        w = ADV.get(ch, 60)
        uses.append(f'<use href="#g{ord(ch)}" x="{x}" y="0" width="{w}" height="100"/>')
        x += w + (4 if ch in ".," else 10)
    vb = x - 10
    sr = f'<span class="sr">{esc(text)} {T[lang]["mhz"]}</span>' if label else ""
    return f'<svg class="{cls}" viewBox="-6 -6 {vb + 12} 112" aria-hidden="true" focusable="false">{"".join(uses)}</svg>{sr}'

# ---------- row layout (mirror of band.js rowLayout) ----------
def rows_layout():
    import math
    rows = []
    y, m = map(int, BAND["rows"]["monthly"][1].split("-"))
    y0, m0 = map(int, BAND["rows"]["monthly"][0].split("-"))
    while (y > y0) or (y == y0 and m >= m0):
        rows.append({"key": f"{y}-{m:02d}", "t0": y + (m - 1) / 12, "t1": y + m / 12, "year": y, "month": m})
        m -= 1
        if m == 0:
            m = 12; y -= 1
    ya, yb = BAND["rows"]["yearly"]
    for yy in range(yb, ya - 1, -1):
        rows.append({"key": str(yy), "t0": yy, "t1": yy + 1, "year": yy})
    T = rows[0]["t1"]; c = BAND["rows"].get("logC", 0.25)
    for r in rows:
        r["w"] = math.log(T - r["t0"] + c) - math.log(T - r["t1"] + c)
    tot = sum(r["w"] for r in rows); acc = 0
    for r in rows:
        r["top"] = acc / tot * 100; acc += r["w"]; r["bot"] = acc / tot * 100
    return rows

def ypct(t):
    """y position (percent from top) of time t on the log axis."""
    import math
    T = ROWS[0]["t1"]; c = BAND["rows"].get("logC", 0.25)
    tot = math.log(T - ROWS[-1]["t0"] + c) - math.log(c)
    return (math.log(T - t + c) - math.log(c)) / tot * 100

ROWS = rows_layout()

def year_ticks(lang):
    mon = {"en": ("Oct 2026", "Jan 2026"), "de": ("Okt. 2026", "Jan. 2026")}[lang]
    ticks = [(ypct(2026 + 10 / 12), mon[0]), (ypct(2026.0), mon[1]), (ypct(2025.0), "2025"), (ypct(2020.0), "2020"),
             (ypct(2010.0), "2010"), (ypct(2000.0), "2000"), (ypct(1987.0), "1987")]
    out = "".join(f'<span class="yt{i}">{lab}</span>' for i, (p, lab) in enumerate(ticks))
    css = "".join(f".yt{i}{{top:{p:.2f}%}}" for i, (p, _) in enumerate(ticks))
    return out, css

# ---------- generated CSS (positions; no inline style attributes because of the CSP) ----------
def gen_css():
    css = []
    for s in BAND["stations"]:
        css.append(f".x-{s['id']}{{left:{xpct(s['freq']):.3f}%}}")
    for p in range(0, 101):
        css.append(f".p{p}{{--p:{p/100:.2f}}}")
    _, ycss = year_ticks("en")
    css.append(ycss)
    _, acss = annotations("en")
    css.append(acss)
    css.append(".plot{--ar:6/5}")
    css.append(f".yours{{left:{xpct(107.4):.2f}%}}")
    for s_ in BAND["stations"]:
        css.append(f".inst[data-st={s_['id']}] .lockmark{{left:{xpct(s_['freq']):.3f}%}}")
    return "".join(css)

def minify_css(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s*([{};:,>])\s*", r"\1", s)
    return s.replace(";}", "}").strip()

HEAD_JS = ("(function(){var d=document.documentElement;d.classList.add('js');try{var t=localStorage.getItem('theme');if(t)d.setAttribute('data-theme',t)}catch(e){}"
           "var c=navigator.connection,m=matchMedia('(prefers-reduced-motion: reduce)').matches||(c&&c.saveData);if(!m)d.classList.add('motion');"
           "setTimeout(function(){if(!window.__fsboot){d.classList.remove('js');d.classList.remove('motion')}},3000)})();")

def sha(s):
    return "'sha256-" + base64.b64encode(hashlib.sha256(s.encode()).digest()).decode() + "'"

# ---------- images ----------
def picture(name, alt, sizes, cls="", eager=False, fetch_high=False, ar=None):
    a = ASSETS.get(name)
    if not a:
        return f'<!-- missing asset {name} -->'
    ws = a["widths"]; base = a["base"]
    srcset_avif = ", ".join(f"/img/{base}-{w}.avif {w}w" for w in ws)
    srcset_webp = ", ".join(f"/img/{base}-{w}.webp {w}w" for w in ws)
    w0 = ws[-1]; h0 = round(w0 * a["h"] / a["w"])
    attrs = f'width="{w0}" height="{h0}" alt="{esc(alt)}" decoding="async"'
    attrs += ' loading="eager"' if eager else ' loading="lazy"'
    if fetch_high:
        attrs += ' fetchpriority="high"'
    if cls:
        attrs += f' class="{cls}"'
    return (f'<picture><source type="image/avif" srcset="{srcset_avif}" sizes="{sizes}">'
            f'<source type="image/webp" srcset="{srcset_webp}" sizes="{sizes}">'
            f'<img src="/img/{base}-{ws[len(ws)//2]}.webp" {attrs}></picture>')

ICON = {
 "mail": '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/></svg>',
 "theme": '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 0 0 0 16z" fill="currentColor"/></svg>',
 "pause": '<svg viewBox="0 0 12 12" aria-hidden="true"><rect x="2" y="1" width="3" height="10" fill="currentColor"/><rect x="7" y="1" width="3" height="10" fill="currentColor"/></svg>',
 "dial": '<svg viewBox="0 0 26 26" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="1.5" y="1.5" width="23" height="23" rx="4"/><path d="M6 17h14M8 17v-3M11 17v-5M14 17v-3M17 17v-7M20 17v-2" stroke-linecap="round"/><path d="M15.5 6v13" stroke-width="2.2"/></svg>',
 "copy": '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/></svg>',
}

def st_name(sid, lang):
    s = ST[sid]
    return s["de"] if lang == "de" else s["en"]

def st_plain(sid, lang):
    s = ST[sid]
    return s["de_plain"] if lang == "de" else s.get("en_plain", s["en"])

def freq_txt(f, lang):
    return f.replace(".", ",") if lang == "de" else f

# ---------- page chrome ----------
def head(lang, title, desc, path, alt_path, og="og", extra=""):
    t = T[lang]
    url = BASE_URL + path
    en_path, de_path = (path, alt_path) if lang == "en" else (alt_path, path)
    ld = {"@context": "https://schema.org", "@type": "Person", "name": "Florian Standhartinger", "url": BASE_URL + "/",
          "jobTitle": "AI builder", "worksFor": {"@type": "Organization", "name": "productivity-boost.com Betriebs UG (haftungsbeschränkt) & Co. KG"},
          "address": {"@type": "PostalAddress", "addressLocality": "Passau", "addressCountry": "DE"},
          "sameAs": [GH_URL, X_URL, HF_URL]}
    return f'''<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="en" href="{BASE_URL + en_path}">
<link rel="alternate" hreflang="de" href="{BASE_URL + de_path}">
<link rel="alternate" hreflang="x-default" href="{BASE_URL + en_path}">
<meta name="theme-color" content="#F2EFE7" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0B0C0F" media="(prefers-color-scheme: dark)">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE_URL}/img/{og}-{lang}.jpg">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:locale" content="{t['locale']}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:creator" content="@airesearch12">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preload" href="/fonts/hubot-display.woff2" as="font" type="font/woff2" crossorigin>
<script>{HEAD_JS}</script>
<style>{CSS}</style>
<script type="module" src="/js/main.js?v={ASSETS.get('_v','1')}"></script>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
{extra}</head>'''

def topbar(lang, alt_path, active=None, home=True):
    t = T[lang]
    links = []
    for s_ in sorted(BAND["stations"], key=lambda q: q["freq"]):
        sid = s_["id"]
        href = f'{t["home"]}#{sid}' if not home else f'#{sid}'
        links.append(f'<li><a href="{href}" data-st="{sid}"><b aria-hidden="true">{freq_txt(str(s_["freq"]), lang)}</b><span class="nm" aria-hidden="true">{esc(st_plain(sid, lang))}</span><span class="sr">{freq_txt(str(s_["freq"]), lang)} {T[lang]["mhz"]}, {esc(st_plain(sid, lang))}</span></a></li>')
    return f"""<a class="skip" href="#main">{t["skip"]}</a>
<div class="langhint" id="langhint" hidden><div class="wrap"><a href="{alt_path}" lang="de" hreflang="de">{t["hint_link"]} →</a><button type="button" data-close-hint aria-label="{t["hint_close"]}">✕</button></div></div>
<header class="top{" on-dark" if home else ""}"><div class="wrap">
<a class="brand" href="{t["home"]}" aria-label="Florian Standhartinger">{ICON["dial"]}<span aria-hidden="true">Florian Standhartinger</span></a>
<nav class="stations-nav" aria-label="{t["nav_top"]}"><span class="curname" aria-hidden="true" data-curname>{freq_txt("105.8", lang)} · {esc(st_plain("decisions", lang))}</span><ol>{"".join(links)}</ol><div class="needle-track" aria-hidden="true"><i class="needle"></i></div></nav>
<div class="tools">
<a class="tbtn" href="{alt_path}" hreflang="{"de" if lang == "en" else "en"}" lang="{"de" if lang == "en" else "en"}"><span aria-hidden="true">{t["other_short"]}</span><span class="sr">{t["other_label"]}</span></a>
<button class="tbtn" type="button" data-theme-toggle aria-label="{t["theme"]}">{ICON["theme"]}</button>
<a class="btn write" href="mailto:{EMAIL}" data-mail>{ICON["mail"]}{t["write"]}</a>
</div></div></header>"""

def footer(lang):
    t = T[lang]
    lb = "".join(f'<li><span>{esc(a)}</span>{esc(b)}</li>' for a, b in LOGBOOK[lang])
    legal_lang = ' lang="de" hreflang="de"' if lang == "en" else ""
    return f'''<footer><div class="wrap">
<details id="logbook"><summary>{t["logbook"]}</summary><ol class="logbook">{lb}</ol></details>
<div><div class="legal"><a href="/impressum/"{legal_lang}>{t["impressum"]}</a><a href="/datenschutz/"{legal_lang}>{t["privacy"]}</a><a href="mailto:{EMAIL}">{EMAIL}</a></div>
<p>{esc(t["rights"])}</p></div>
</div></footer>'''

def mail_sheet(lang):
    t = T[lang]
    return f"""<dialog class="sheet mailsheet" id="mail" aria-labelledby="mail-h"><div class="in">
<h2 id="mail-h">{t["mail_title"]}</h2><p class="addr">{EMAIL}</p>
<div class="row"><button class="btn" type="button" autofocus data-copy="{EMAIL}" data-copied="{t["copied"]}">{ICON["copy"]}<span>{t["copy"]}</span></button><a class="btn ghost" href="mailto:{EMAIL}">{ICON["mail"]}{t["mail_open"]}</a></div>
<p class="dim small">{t["mail_note"]}</p><span class="sr" role="status" data-copy-status></span>
<form method="dialog"><button class="tbtn close" aria-label="{t["sheet_close"]}">✕</button></form></div></dialog>"""

def bottom_bar(lang, home=True):
    t = T[lang]
    items = "".join(
        f'<li><a href="{"" if home else t["home"]}#{s["id"]}" data-st="{s["id"]}"><b>{freq_txt(s["freq"], lang)}</b>{st_name(s["id"], lang)}</a></li>' for s in STATIONS)
    return f"""<div class="bbar" id="bbar" data-st="decisions" inert>
<button class="cur" type="button" data-open-sheet aria-haspopup="dialog"><b data-cur-f>{freq_txt("105.8", lang)}</b><span data-cur-n>{esc(st_plain("decisions", lang))}</span></button>
<a class="btn" href="mailto:{EMAIL}" data-mail>{ICON["mail"]}{t["write"]}</a></div>
<dialog class="sheet" id="sheet" aria-labelledby="sheet-h"><div class="in">
<h2 id="sheet-h">{t["sheet_title"]}</h2><nav aria-label="{t["nav_sheet"]}"><ol>{items}</ol></nav>
<div class="row"><a class="btn ghost" href="{t["works"]}">{t["all"]}</a><a class="btn ghost" href="{t["other_home"]}" hreflang="{"de" if lang == "en" else "en"}">{t["other_label"]}</a><a class="btn" href="mailto:{EMAIL}" data-mail>{t["write"]}</a></div>
<form method="dialog"><button class="tbtn close" aria-label="{t["sheet_close"]}">✕</button></form>
</div></dialog>{mail_sheet(lang)}"""

# ---------- hero ----------
def ruler_svg():
    ticks = []
    f = 87.5
    while f <= 108.001:
        x = xpct(f)
        major = abs(f - round(f)) < 1e-6
        h = 9 if major else 5
        ticks.append(f'<line x1="{x:.3f}%" x2="{x:.3f}%" y1="{46-h}" y2="46"/>')
        f += 0.5
    labels = []
    pass
    return (f'<svg class="scale" aria-hidden="true" focusable="false"><g stroke="currentColor" stroke-width="1" opacity=".55">{"".join(ticks)}</g>'
            f'<g fill="currentColor" font-family="ui-monospace,monospace" font-size="9" opacity=".7">{"".join(labels)}</g></svg>')

ANN = [  # in-plot labels: key, station, time, label offset (dx, dy in % of the plot), shown on phones
 ("reax", "networks", 2026 + 9.5 / 12, (-3, 13), True, "end"),
 ("ralph", "agents", 2026 + 0.5 / 12, (3, 6), True, "start"),
 ("rdvr", "worlds", 2017.5, (1.5, -8), True, "start"),
 ("dax", "systems", 2015.0, (3, 3), False, "start"),
 ("bh", "benchmarks", 2026 + 5.5 / 12, (3, 7), False, "start"),
 ("lgbm", "decisions", 2018.5, (-3, 4), False, "end"),
 ("games", "worlds", 1994.0, (3, 0), True, "start"),
]

def annotations(lang):
    t = T[lang]
    out = []; css = []
    for i, (k, sid, tm, (dx, dy), mob, anchor) in enumerate(ANN):
        x = xpct(BAND_ST[sid]["freq"]); y = ypct(tm)
        lx, ly = x + dx, y + dy
        lab = esc(t["ann"][k]).replace("★", '<span aria-hidden="true">★</span><span class="sr"> GitHub stars</span>')
        cls = "ann" + ("" if mob else " desk") + (" rt" if anchor == "end" else "")
        out.append(f'<i class="pt a{i}{"" if mob else " desk"}" aria-hidden="true"></i><span class="{cls} l{i}" aria-hidden="true">{lab}</span>')
        css.append(f".pt.a{i}{{left:{x:.2f}%;top:{y:.2f}%}}.ann.l{i}{{left:{lx:.2f}%;top:{ly:.2f}%}}")
        out.append(f'<svg class="leader{"" if mob else " desk"}" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><line x1="{x:.2f}" y1="{y:.2f}" x2="{lx:.2f}" y2="{ly:.2f}"/></svg>')
    return "".join(out), "".join(css)

def instrument(lang):
    t = T[lang]
    st_links, hits = [], []
    band_order = sorted(BAND["stations"], key=lambda s: s["freq"])
    for s in band_order:
        sid = s["id"]; nm = st_plain(sid, lang)
        short = nm.split(" ")[0] if sid == "studio" else nm
        st_links.append(f'<a class="st x-{sid}" href="#{sid}" data-st="{sid}" data-tune="{sid}"><span aria-hidden="true">{freq_txt(str(s["freq"]), lang)}</span><i aria-hidden="true">{esc(short)}</i><span class="sr">{freq_txt(str(s["freq"]), lang)} {T[lang]["mhz"]}, {esc(nm)}</span></a>')
        hits.append(f'<a class="hit x-{sid}" href="#{sid}" data-tune="{sid}" tabindex="-1" aria-hidden="true"></a>')
    yt, _ = year_ticks(lang)
    ann, _ = annotations(lang)
    wf = ASSETS.get("wf")
    wf_img = ""
    if wf:
        wf_img = (f'<picture><source type="image/avif" media="(min-width:640px)" srcset="/img/{wf["base"]}-d.avif">'
                  f'<source type="image/webp" media="(min-width:640px)" srcset="/img/{wf["base"]}-d.webp">'
                  f'<source type="image/avif" srcset="/img/{wf["base"]}-m.avif"><img src="/img/{wf["base"]}-m.webp" width="{wf["mw"]}" height="{wf["mh"]}" alt="" decoding="async" loading="eager" fetchpriority="high"></picture>')
    fl = FLAG_DE if lang == "de" else FLAG
    names = json.dumps({s["id"]: {"f": freq_txt(str(s["freq"]), lang), "n": st_plain(s["id"], lang), "p": fl[s["id"]], "r": ST[s["id"]]["read"][lang]} for s in band_order}, ensure_ascii=False)
    first = band_order[-1]
    return f"""<figure class="inst locked" data-st="decisions" aria-label="{t["inst_title"]}" aria-describedby="inst-cap">
<div class="inst-head"><b class="ttl">{t["inst_title"]}</b><span class="kind">{t["inst_kind"]}</span><span class="kind-m">{t["tap"]} ↓</span><button class="pause" type="button" data-pause aria-pressed="false" aria-label="{t["pause"]}" data-l-pause="{t["pause"]}" data-l-play="{t["play"]}">{ICON["pause"]}</button></div>
<div class="ruler">{ruler_svg()}<nav aria-label="{t["nav_inst"]}">{"".join(st_links)}</nav><input class="needle-range" type="range" min="0" max="6" step="1" value="6" aria-label="{t["pick"]}" aria-valuetext="{freq_txt(str(first["freq"]), lang)} {t["mhz"]}, {st_plain(first["id"], lang)}"></div>
<div class="readout locked">{numerals("105.8", lang, cls="rnum num", label=False)}<span class="rtxt" aria-live="polite"><span class="rname">{esc(st_plain("decisions", lang))} <em>{esc(fl["decisions"])}</em></span><span class="rsub">{esc(ST["decisions"]["read"][lang])}</span></span><a href="#decisions" data-go aria-label="{t["readout_go"].rstrip(" ↓")}: {esc(st_plain("decisions", lang))}"><span class="gl">{t["readout_go"]}</span><span class="gs" aria-hidden="true">{t["go_short"]}</span></a></div>
<div class="plotwrap"><div class="years" aria-hidden="true">{yt}</div>
<div class="plot">{wf_img}<i class="floor"></i><canvas aria-hidden="true"></canvas><i class="static"></i><i class="yours" aria-hidden="true"></i>{"".join(hits)}{ann}</div></div>
<div class="plotfoot"><span>{freq_txt("87.5", lang)} · {t["since87"]}</span><a href="#contact">{t["yourproj"]} · {freq_txt("108.0", lang)} →</a></div>
<script type="application/json" id="st-names">{names}</script>
<figcaption id="inst-cap" class="sr">{esc(t["fig_alt"])}</figcaption>
</figure>"""

def hero(lang):
    t = T[lang]
    face = picture("sstv-face", "Florian Standhartinger", "40px", cls="face", eager=True)
    return f"""<section class="hero" aria-labelledby="h1"><div class="wrap hero-in">
<div class="hero-txt">
<div class="idline"><span class="facewrap">{face}</span><div class="who">Florian Standhartinger<span>{t["who_sub"]}</span></div></div>
<h1 id="h1"><span>{esc(t["h1a"])}</span> <span class="l2">{esc(t["h1b"])}</span></h1>
<p class="genres">{esc(t["genres"])}</p><p class="genres-short">{esc(t["genres_short"])}</p>
<div class="ctas"><a class="btn inv" href="mailto:{EMAIL}" data-mail>{ICON["mail"]}{t["write"]}</a><a class="btn ghost" href="{t["works"]}">{t["all"]}</a></div>
<div class="hero-foot"><p class="legend">{t["legend"]}</p><p class="legend">{t["figures"]} <a href="#logbook" data-open-logbook>{t["logbook_link"]}</a></p>
<div class="decoder"><div class="sstv" role="img" aria-label="Florian Standhartinger · {t["sstv_title"]}">{picture("sstv", "", "(min-width:1080px) 220px, 1px", eager=False)}</div><span class="dlab" aria-hidden="true">{t["sstv_title"]} · RX 21.10.2026</span></div></div>
</div>
{instrument(lang)}
<p class="hero-meta">{t["figures"]} <a href="#logbook" data-open-logbook>{t["logbook_link"]}</a></p>
</div></section>"""

# ---------- station signal panels ----------
def sig_decisions(lang):
    t = T[lang]
    q = {"en": ("A business customer asks to update an invoice address.", "Which support queue fits?", [("billing", 87), ("technical", 9), ("account", 4)]),
         "de": ("Ein Geschäftskunde möchte seine Rechnungsadresse ändern.", "Welche Support-Queue passt?", [("billing", 87), ("technical", 9), ("account", 4)])}[lang]
    bars = "".join(f'<div class="bar"><span>{a}</span><i class="p{p}"></i><span>0.{p:02d}</span></div>' for a, p in q[2])
    k = {"en": [("70 ms", "median round trip, s1-fast · 180 requests from Germany, 17 Oct 2026"), ("27B", "parameters in REAX 1, open, Apache-2.0"), ("EU", "tier for personal data")],
         "de": [("70 ms", "Median-Antwortzeit, s1-fast · 180 Anfragen aus Deutschland, 17. Okt. 2026"), ("27 Mrd.", "Parameter in REAX 1, offen, Apache-2.0"), ("EU", "Tarif für personenbezogene Daten")]}[lang]
    kp = "".join(f'<div><b>{a}</b>{esc(b)}</div>' for a, b in k)
    cap_l = {"en": "Request → answer", "de": "Anfrage → Antwort"}[lang]
    note = {"en": "Sample request from the decisionmodels.io quickstart (illustrative); the latency is measured.",
            "de": "Beispielanfrage aus dem Quickstart von decisionmodels.io (illustrativ); die Antwortzeit ist gemessen."}[lang]
    return f'''<div class="panel sig dark"><div><div class="sig-cap"><span>{cap_l}</span><b>{t["sample"]}</b></div>
<p class="sig-note">STATE · {esc(q[0])}</p><div class="bars"><div class="q">{esc(q[1])}</div>{bars}</div></div>
<div><div class="kpi">{kp}</div><p class="sig-note">{note}</p></div></div>'''

def sig_benchmarks(lang):
    t = T[lang]
    dots = ASSETS.get("jevdots", {}).get("svg", "")
    cap = {"en": "Each dot is one AI system on the public JevBench board, placed by its Intelligence score (236 rows, 21 Oct 2026). Names on benchmarkheaven.com.",
           "de": "Jeder Punkt ist ein KI-System auf der öffentlichen JevBench-Tafel, nach seinem Intelligence-Wert platziert (236 Zeilen, 21. Okt. 2026). Namen auf benchmarkheaven.com."}[lang]
    k = {"en": [("194", "open-weights systems ranked"), ("1,500", "decisions per system"), ("4", "scores: accuracy, calibration, latency, cost")],
         "de": [("194", "offene Systeme im Ranking"), ("1.500", "Entscheidungen pro System"), ("4", "Werte: Genauigkeit, Kalibrierung, Latenz, Kosten")]}[lang]
    kp = "".join(f'<div><b>{a}</b>{esc(b)}</div>' for a, b in k)
    return f'''<div class="panel sig dark"><div class="sig-cap"><span>JevBench · Intelligence</span><b>{t["measured"]}</b></div>
<figure role="img" aria-label="{esc(cap)}">{dots}</figure><p class="sig-note">{esc(cap)}</p><div class="kpi">{kp}</div></div>'''

def sig_networks(lang):
    t = T[lang]
    pools = {"en": [("s1-fast", "NVIDIA GPUs from 24 GB"), ("s1-pro", "80–96 GB GPUs"), ("s1-lite", "small GPUs, incl. Jetson Orin"), ("s1-cpu", "plain CPUs")],
             "de": [("s1-fast", "NVIDIA-GPUs ab 24 GB"), ("s1-pro", "GPUs mit 80–96 GB"), ("s1-lite", "kleine GPUs, auch Jetson Orin"), ("s1-cpu", "einfache CPUs")]}[lang]
    pp = "".join(f'<div><b>{a}</b>{esc(b)}</div>' for a, b in pools)
    ring = netring_svg()
    cap = {"en": "Miners serve, validators re-run every answer and time it (illustration).", "de": "Miner liefern, Validatoren rechnen jede Antwort nach und stoppen die Zeit (Illustration)."}[lang]
    return f'''<div class="panel sig dark"><div class="sig-cap"><span>REAX · netuid 92</span><b>Live · 14 Oct 2026</b></div>
<figure role="img" aria-label="{esc(cap)}">{ring}</figure><p class="sig-note">{esc(cap)}</p><div class="pools">{pp}</div></div>'''

def netring_svg():
    import math
    nodes = []
    for i in range(18):
        a = i / 18 * math.tau
        x = 150 + 112 * math.cos(a); y = 110 + 78 * math.sin(a)
        r = 3.2 if i % 3 else 5
        nodes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}"/>')
        if i % 3 == 0:
            nodes.append(f'<line x1="150" y1="110" x2="{x:.1f}" y2="{y:.1f}" opacity=".28"/>')
    return (f'<svg class="netring" viewBox="0 0 300 220" aria-hidden="true"><g fill="currentColor" stroke="currentColor" stroke-width="1">{"".join(nodes)}</g>'
            f'<ellipse cx="150" cy="110" rx="112" ry="78" fill="none" stroke="currentColor" opacity=".25"/>'
            f'<circle cx="150" cy="110" r="26" fill="#08090D" stroke="currentColor"/><text x="150" y="115" fill="currentColor" font-family="ui-monospace,monospace" font-size="14" text-anchor="middle">92</text></svg>')

def sig_studio(lang):
    t = T[lang]
    img = picture("rwrec", {"en": "Rewind Recorder in Vuzix AR glasses: a red dot and the words “Tap to save last 10 seconds as video” over a football match.",
                            "de": "Rewind Recorder in der Vuzix-AR-Brille: ein roter Punkt und „Tap to save last 10 seconds as video“ über einem Fußballspiel."}[lang],
                  "(min-width:900px) 40vw, 92vw", cls="archive")
    cap = {"en": "Rewind Recorder, Vuzix AR glasses: the moment you just saw becomes a video. Archive, around 2020.",
           "de": "Rewind Recorder, Vuzix-AR-Brille: der Moment, den du gerade gesehen hast, wird zum Video. Archiv, um 2020."}[lang]
    return f'''<div class="panel sig dark"><div class="sig-cap"><span>Studio · AR · video</span><b>Archive</b></div>
<div class="media">{img}<div class="cap">{esc(cap)}</div></div></div>'''

def sig_agents(lang):
    t = T[lang]
    lines = {"en": [("c", "$ ./ralph.sh   # loop until the spec is done"), ("", "▸ orient      read specs/ + IMPLEMENTATION_PLAN.md"), ("", "▸ pick        one task, fresh context"),
                    ("", "▸ implement   code + tests"), ("", "▸ verify      acceptance criteria"), ("", "▸ commit      git commit && git push"), ("ok", "✓ <promise>DONE</promise>  → next iteration")],
             "de": [("c", "$ ./ralph.sh   # Schleife bis die Spezifikation erfüllt ist"), ("", "▸ orient      specs/ + IMPLEMENTATION_PLAN.md lesen"), ("", "▸ pick        eine Aufgabe, frischer Kontext"),
                    ("", "▸ implement   Code + Tests"), ("", "▸ verify      Abnahmekriterien"), ("", "▸ commit      git commit && git push"), ("ok", "✓ <promise>DONE</promise>  → nächste Runde")]}[lang]
    lg = "\n".join(f'<span class="ln {c}">{esc(s)}</span>' for c, s in lines)
    cap = {"en": "The loop as documented in the README.", "de": "Die Schleife, wie sie im README beschrieben ist."}[lang]
    return f'''<div class="panel sig dark"><div class="sig-cap"><span>ralph-wiggum · loop</span><b>README</b></div><pre class="log">{lg}</pre><p class="sig-note">{esc(cap)}</p></div>'''

def sig_systems(lang):
    t = T[lang]
    cap = {"en": "Illustration — the real system is confidential: exposure from millions of contracts, aggregated live and put on a map.",
           "de": "Illustration – das echte System ist vertraulich: Risiken aus Millionen Verträgen, live aggregiert und auf die Karte gebracht."}[lang]
    return f'''<div class="panel sig dark"><div class="sig-cap"><span>Risk · geo · real time</span><b>{t["illus"]}</b></div>
<figure role="img" aria-label="{esc(cap)}">{systems_svg()}</figure><p class="sig-note">{esc(cap)}</p></div>'''

def systems_svg():
    import random
    rnd = random.Random(2014)
    dots = []
    # a dotted world-ish grid with hot spots (illustrative)
    for gy in range(0, 13):
        for gx in range(0, 30):
            x = 12 + gx * 9.6; y = 14 + gy * 9.6
            land = (0.25 < gx / 30 < 0.36 and 2 < gy < 11) or (0.42 < gx / 30 < 0.56 and 1 < gy < 7) or (0.45 < gx / 30 < 0.6 and 6 < gy < 12) or (0.6 < gx / 30 < 0.88 and 1 < gy < 8) or (0.78 < gx / 30 < 0.9 and 8 < gy < 11) or (0.05 < gx / 30 < 0.22 and 1 < gy < 7)
            if land and rnd.random() < 0.82:
                dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.5"/>')
    hot = [(118, 45, 22), (210, 38, 15), (250, 70, 11), (60, 52, 13), (150, 100, 9)]
    rings = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="currentColor" fill-opacity=".14" stroke="currentColor"/>' for x, y, r in hot)
    return (f'<svg class="dots" viewBox="0 0 300 140" aria-hidden="true"><g fill="#8E97A8" opacity=".55">{"".join(dots)}</g>{rings}'
            f'<g font-family="ui-monospace,monospace" font-size="7" fill="#8E97A8"><text x="6" y="137">contracts ▸ exposure ▸ map</text></g></svg>')

def sig_worlds(lang):
    t = T[lang]
    v = ASSETS.get("rdvr_loop")
    cap = {"en": "Room Designer VR, from its own Steam trailer (2017). Silent loop.", "de": "Room Designer VR, aus dem eigenen Steam-Trailer (2017). Stumme Schleife."}[lang]
    alt = {"en": "Room Designer VR: drawing a floor plan with a VR controller on a blueprint grid.", "de": "Room Designer VR: ein Grundriss wird mit dem VR-Controller auf ein Raster gezeichnet."}[lang]
    if v:
        media = (f'<video class="loop" muted loop playsinline preload="none" width="{v["w"]}" height="{v["h"]}" poster="/img/{v["poster"]}" aria-label="{esc(alt)}">'
                 f'<source src="/img/{v["webm"]}" type="video/webm"><source src="/img/{v["mp4"]}" type="video/mp4"></video>'
                 f'<button class="vbtn" type="button" data-vid aria-pressed="false" aria-label="{t["vid_pause"]}" data-l-pause="{t["vid_pause"]}" data-l-play="{t["vid_play"]}">{ICON["pause"]}</button>')
    else:
        media = picture("rdvr", alt, "(min-width:900px) 40vw, 92vw")
    return f'''<div class="panel sig dark"><div class="sig-cap"><span>Room Designer VR · HTC Vive</span><b>Steam · 2017</b></div>
<div class="media">{media}<div class="cap">{esc(cap)}</div></div></div>'''

SIG = {"decisions": sig_decisions, "benchmarks": sig_benchmarks, "networks": sig_networks, "studio": sig_studio,
       "agents": sig_agents, "systems": sig_systems, "worlds": sig_worlds}

def card(sid, lang):
    t = T[lang]; c = CARDS[sid]
    links = " · ".join(f'<a href="{u}">{esc(l)}</a>' for l, u in c["links"])
    return f'''<article class="card"><span class="qsl" aria-hidden="true">{t["qsl"]} {freq_txt(ST[sid]["freq"], lang)}</span>
<div><div class="yr">{c["year"]}</div><h3>{esc(c["title"][lang])}</h3></div>
<dl><div><dt>{t["built"]}</dt><dd>{esc(c["built"][lang])}</dd></div><div><dt>{t["proofl"]}</dt><dd>{esc(c["proof"][lang]).replace("★", '<span aria-hidden="true">★</span><span class="sr"> GitHub stars</span>')}</dd></div></dl>
<p class="note">{esc(c["note"][lang])}</p>{f'<p class="go">{links}</p>' if links else ''}</article>'''

def station(sid, lang, idx):
    t = T[lang]; s = ST[sid]
    wide = " wide" if sid == "decisions" else (" flip" if idx % 2 == 0 else "")
    return f'''<section class="station{wide}" id="{sid}" data-st="{sid}" aria-labelledby="h-{sid}">
<div class="wrap"><header class="st-head"><div class="st-num">{numerals(s["freq"], lang)}<span class="mhz" aria-hidden="true">MHz</span></div>
<div><h2 class="st-name" id="h-{sid}" lang="{lang}">{s["de"] if lang == "de" else s["en"]}</h2><p class="st-sub">{esc(s["sub"][lang])}</p></div></header>
<div class="st-body">{SIG[sid](lang)}{card(sid, lang)}</div>
<a class="more" href="{t["works"]}#{sid}">{t["more"].format(name=esc(st_plain(sid, lang)))}</a></div></section>'''

def hop(h, lang):
    t = T[lang]
    a, b = h["a"], h["b"]
    viz = ASSETS.get(f"hop-{a}-{b}")
    vimg = ""
    if viz:
        vimg = f'<img class="slice" src="/img/{viz["file"]}" width="{viz["w"]}" height="{viz["h"]}" alt="" loading="lazy" decoding="async">'
    pl, pu = h["proof"]
    return f'''<aside class="hop" data-hop="{a}:{b}" aria-label="{t["hop_word"]}: {esc(h["title"][lang])}"><div class="wrap">
<div class="from">{numerals(ST[a]["freq"], lang, label=False)}<span aria-hidden="true">→</span>{numerals(ST[b]["freq"], lang, label=False)}<span class="sr">{freq_txt(ST[a]["freq"], lang)} → {freq_txt(ST[b]["freq"], lang)} {t["mhz"]}</span></div>
<div class="resolve viz">{vimg}</div>
<div><span class="mono dim">{t["hop_word"]} · {esc(st_plain(a, lang))} ↔ {esc(st_plain(b, lang))}</span><h3>{esc(h["title"][lang])}</h3><p>{esc(h["text"][lang])}</p><p class="proofl"><a href="{pu}">{esc(pl)}</a></p></div>
</div></aside>'''

def how(lang):
    t = T[lang]
    lis = "".join(f"<li>{esc(x)}</li>" for x in t["how"])
    return f'''<section class="how" aria-labelledby="h-how"><div class="wrap"><h2 class="mono dim" id="h-how">{t["how_title"]}</h2><ol>{lis}</ol><p class="day">{esc(t["day"])}</p></div></section>'''

def end(lang):
    t = T[lang]
    return f'''<section class="end" id="contact" aria-labelledby="h-end"><div class="wrap">
<p class="wrapline">{t["end_wrap"]}</p>
<div class="bignum">{numerals("108.0", lang)}<span class="mono dim" aria-hidden="true">MHz</span></div>
<h2 id="h-end">{esc(t["end_h"])}</h2>
<p class="lead">{esc(t["end_p"])}</p>
<div class="mailrow"><a class="btn" href="mailto:{EMAIL}">{ICON["mail"]}{t["write"]}</a><span class="addr">{EMAIL}</span>
<button class="tbtn" type="button" data-copy="{EMAIL}" data-copied="{t["copied"]}">{ICON["copy"]}<span>{t["copy"]}</span></button><span class="sr" role="status" data-copy-status></span></div>
<div class="links"><a href="{GH_URL}">GitHub · fstandhartinger</a><a href="{X_URL}">X · @airesearch12</a><a href="{HF_URL}">Hugging Face · decisionmodels</a></div>
<p class="sign">{t["sign"]}<small>{esc(t["sign_note"])}</small></p>
</div></section>'''

def page_home(lang):
    t = T[lang]
    path = t["home"]; alt = t["other_home"]
    body = [head(lang, t["title"], t["desc"], path, alt), "<body>", sprite(), topbar(lang, alt),
            '<main id="main">', hero(lang), '<div class="band-start"></div>']
    for i, sid in enumerate(ORDER):
        body.append(station(sid, lang, i))
        if i < len(HOPS):
            body.append(hop(HOPS[i], lang))
    body += [how(lang), end(lang), "</main>", footer(lang), bottom_bar(lang), "</body></html>"]
    return "\n".join(body)

DE_META = [("on GitHub", "auf GitHub"), ("Live since 14 Oct 2026", "Live seit 14. Okt. 2026"), ("Steam, 28 Feb 2017", "Steam, 28. Feb. 2017"),
           ("Unity Asset Store, 8 May 2017", "Unity Asset Store, 8. Mai 2017"), ("194 systems ranked", "194 Systeme im Ranking"),
           ("Closed source", "Nicht öffentlich"), ("Earlier work", "Früheres Projekt"), ("Live demo", "Live-Demo"), ("Live API", "Live-API"),
           ("(own eval, n=1,134)", "(eigene Messung, n=1.134)"), ("88.5 % category accuracy", "88,5 % Kategorie-Genauigkeit"),
           ("Vuzix app store", "Vuzix App Store"), ("Hugging Face, 21 Oct 2026", "Hugging Face, 21. Okt. 2026")]

def page_works(lang):
    t = T[lang]
    path = t["works"]; alt = t["other_works"]
    groups = []
    for s in STATIONS:
        sid = s["id"]
        cards = []
        for st, title, year, en, de, url, meta in WORKS:
            if st != sid:
                continue
            m = meta
            if lang == "de":
                for a, b in DE_META:
                    m = m.replace(a, b)
            m = esc(m).replace("★", '<span aria-hidden="true">★</span><span class="sr"> GitHub stars</span>')
            link = f'<a href="{url}">{esc(url.split("//")[1].rstrip("/"))} →</a>' if url else ""
            cards.append(f'<article class="wcard"><span class="meta">{esc(year)} · {m}</span><h3>{esc(title)}</h3><p>{esc(de if lang == "de" else en)}</p>{link}</article>')
        groups.append(f'<section class="works-group" id="{sid}" data-st="{sid}" aria-labelledby="w-{sid}"><h2 id="w-{sid}">{s["de"] if lang == "de" else s["en"]} <small>{freq_txt(s["freq"], lang)} MHz</small></h2><div class="grid-cards">{"".join(cards)}</div></section>')
    body = [head(lang, t["works_meta_title"], t["works_desc"], path, alt), "<body>", sprite(), topbar(lang, alt, home=False),
            f'<main id="main" class="wrap"><div class="works-head"><p class="mono dim"><a href="{t["home"]}">{t["back"]}</a></p><h1>{t["works_title"]}</h1><p class="st-sub">{esc(t["works_lead"])}</p></div>',
            "".join(groups), "</main>", footer(lang), bottom_bar(lang, home=False), "</body></html>"]
    return "\n".join(body)

def page_legal(kind):
    # German, binding. Content kept verbatim from the reviewed draft.
    src = open(os.path.join(SRC, "legal", f"{kind}.html")).read()
    title = "Impressum" if kind == "impressum" else "Datenschutzerklärung"
    t = T["de"]
    body = [head("de", f"{title} | productivity-boost.com", f"{title} von productivity-boost.com Betriebs UG (haftungsbeschränkt) & Co. KG.", f"/{kind}/", f"/{kind}/"),
            "<body>", sprite(), topbar("de", "/", home=False), f'<main id="main" class="wrap legalpage">{src}</main>', footer("de"), "</body></html>"]
    return "\n".join(body)

def page_404():
    t = T["en"]
    body = [head("en", "Off the band — Florian Standhartinger", "This page does not exist.", "/404.html", "/404.html"), "<body>", sprite(), topbar("en", "/de/", home=False),
            f'<main id="main" class="wrap end"><p class="wrapline">404 · no carrier</p><div class="bignum">{numerals("404", "en", label=False)}</div>'
            f'<h1>Nothing on this frequency.</h1><p class="lead">The page you tuned to doesn’t exist (any more). <a href="/">Back to the band</a> · <a href="/de/" lang="de" hreflang="de">Zurück zum Band</a></p></main>',
            footer("en"), "</body></html>"]
    return "\n".join(body)

def write(path, s):
    p = os.path.join(OUT, path.lstrip("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(s)

CSS = minify_css(open(os.path.join(SRC, "css", "site.css")).read() + gen_css())

def main():
    os.makedirs(OUT, exist_ok=True)
    write("/index.html", page_home("en"))
    write("/de/index.html", page_home("de"))
    write("/works/index.html", page_works("en"))
    write("/de/projekte/index.html", page_works("de"))
    write("/impressum/index.html", page_legal("impressum"))
    write("/datenschutz/index.html", page_legal("datenschutz"))
    write("/404.html", page_404())
    # sitemap with hreflang pairs (for the real domain)
    pairs = [("/", "/de/"), ("/works/", "/de/projekte/")]
    urls = []
    for en, de in pairs:
        for loc in (en, de):
            urls.append(f"<url><loc>{BASE_URL}{loc}</loc><xhtml:link rel=\"alternate\" hreflang=\"en\" href=\"{BASE_URL}{en}\"/><xhtml:link rel=\"alternate\" hreflang=\"de\" href=\"{BASE_URL}{de}\"/><xhtml:link rel=\"alternate\" hreflang=\"x-default\" href=\"{BASE_URL}{en}\"/></url>")
    for loc in ("/impressum/", "/datenschutz/"):
        urls.append(f"<url><loc>{BASE_URL}{loc}</loc></url>")
    write("/sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">' + "".join(urls) + "</urlset>\n")
    write("/robots.txt", f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n")
    # static files
    for d in ("fonts", "js"):
        shutil.copytree(os.path.join(SRC, d), os.path.join(OUT, d), dirs_exist_ok=True)
    shutil.copy(os.path.join(SRC, "data", "band.json"), os.path.join(OUT, "js", "band.json"))
    for f in ("favicon.svg", "robots.txt", "apple-touch-icon.png"):
        if os.path.exists(os.path.join(SRC, "static", f)):
            shutil.copy(os.path.join(SRC, "static", f), os.path.join(OUT, f))
    # nginx config with CSP hashes for the one inline script and the one inline style
    csp = (f"default-src 'self'; script-src 'self' {sha(HEAD_JS)}; style-src 'self' {sha(CSS)}; img-src 'self' data:; media-src 'self'; "
           "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'none'; object-src 'none'")
    tpl = open(os.path.join(SRC, "nginx.conf.tpl")).read().replace("__CSP__", csp)
    open(os.path.join(ROOT, "nginx.conf"), "w").write(tpl)
    print("built", OUT, "css", len(CSS), "bytes")

if __name__ == "__main__":
    main()
