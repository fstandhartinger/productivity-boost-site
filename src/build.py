# -*- coding: utf-8 -*-
"""Static site generator for productivity-boost.com (round 2: calm company site). Usage: python3 -I src/build.py -> ./site"""
import base64, hashlib, html, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
OUT = os.path.join(ROOT, "site")
sys.path.insert(0, SRC)
from content import T, ASOF, EMAIL, GH_URL, QS_URL, DM_URL  # noqa: E402

BASE_URL = os.environ.get("SITE_URL", "https://productivity-boost.app.mintapis.com")
BUILD_ID = os.environ.get("BUILD_ID", "dev")
IMG = json.load(open(os.path.join(SRC, "data", "img.json")))
POSTS_F = os.path.join(SRC, "data", "posts.json")
POSTS = json.load(open(POSTS_F)) if os.path.exists(POSTS_F) else []

def esc(s):
    return html.escape(s.replace("\u2011", "-"), quote=True)

def rich(s):
    """escaped text; words with a non-breaking hyphen (U+2011) never break (the font has no U+2011 glyph)."""
    out = []
    for part in re.split(r"(\S*\u2011\S*)", s):
        out.append(f'<span class="nw">{esc(part)}</span>' if "\u2011" in part else esc(part))
    return "".join(out)

def sha(b):
    return hashlib.sha256(b).hexdigest()[:10]

_VQ = {}
def vq(path):
    """content-hashed URL for an asset under src/ (immutable caching)."""
    if path not in _VQ:
        p = os.path.join(SRC, path.lstrip("/"))
        _VQ[path] = f"{path}?v={sha(open(p, 'rb').read())}"
    return _VQ[path]

def marks(s, lang="en"):
    """escaped text with [n] note markers turned into links to the footer notes."""
    return re.sub(r"\[(\d)\]", lambda m: f'<sup class="fn"><a id="ref-{m.group(1)}" href="#note-{m.group(1)}">{m.group(1)}<span class="sr"> ({T[lang]["note"]})</span></a></sup>', esc(s))

def ext(url, label, lang, cls=""):
    c = f' class="{cls}"' if cls else ""
    return f'<a{c} href="{esc(url)}" rel="noopener" target="_blank">{label}<span class="sr"> ({T[lang]["new_tab"]})</span><span class="ext" aria-hidden="true">↗</span></a>'

def picture(name, alt, sizes, cls="", eager=False, mobile=None, mq="(max-width: 47.99em)"):
    m = IMG[name]
    def sset(n, kind):
        return ", ".join(f"{vq(f'/img/{n}-{w}.{kind}')} {w}w" for w in IMG[n]["widths"])
    srcs = ""
    if mobile:
        mm = IMG[mobile]
        srcs += (f'<source type="image/avif" media="{mq}" srcset="{sset(mobile, "avif")}" sizes="100vw" width="{mm["w"]}" height="{mm["h"]}">'
                 f'<source type="image/webp" media="{mq}" srcset="{sset(mobile, "webp")}" sizes="100vw" width="{mm["w"]}" height="{mm["h"]}">')
    srcs += f'<source type="image/avif" srcset="{sset(name, "avif")}" sizes="{sizes}">'
    load = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy"'
    small = m["widths"][min(1, len(m["widths"]) - 1)]
    c = f' class="{cls}"' if cls else ""
    return (f'<picture{c}>{srcs}<img src="{vq(f"/img/{name}-{small}.webp")}" srcset="{sset(name, "webp")}" sizes="{sizes}" '
            f'width="{m["w"]}" height="{m["h"]}" alt="{esc(alt)}" decoding="async" {load}></picture>')

# ---------------- head / chrome ----------------
THEME_JS = "(function(){try{var t=localStorage.getItem('theme');if(t==='light'||t==='dark')document.documentElement.dataset.theme=t}catch(e){}document.documentElement.classList.add('js')})();"

def head(lang, title, desc, path, alt_path=None, og=True, robots=None):
    t = T[lang]
    alts = ""
    if alt_path is not None:
        en, de = (path, alt_path) if lang == "en" else (alt_path, path)
        alts = (f'<link rel="alternate" hreflang="en" href="{BASE_URL}{en}"><link rel="alternate" hreflang="de" href="{BASE_URL}{de}">'
                f'<link rel="alternate" hreflang="x-default" href="{BASE_URL}{en}">')
    ogm = ""
    if og:
        ogi = f"{BASE_URL}{vq(f'/img/og-{lang}.png')}"
        ogm = (f'<meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">'
               f'<meta property="og:url" content="{BASE_URL}{path}"><meta property="og:image" content="{ogi}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
               f'<meta property="og:locale" content="{t["locale"]}"><meta property="og:site_name" content="productivity-boost.com"><meta name="twitter:card" content="summary_large_image">')
    rb = f'<meta name="robots" content="{robots}">' if robots else ""
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" media="(prefers-color-scheme: light)" content="#f6f5f0">
<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#0d0e10">
<meta name="build" content="{BUILD_ID}">{rb}
{"" if path == "/404.html" else f'<link rel="canonical" href="{BASE_URL}{path}">'}{alts}
<script>{THEME_JS}</script>
<link rel="preload" href="{vq('/fonts/archivo.woff2')}" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{vq('/css/site.css')}">
<link rel="icon" href="{vq('/static/favicon.svg')}" type="image/svg+xml">
<link rel="apple-touch-icon" href="{vq('/static/apple-touch-icon.png')}">
{ogm}
</head>"""

def header(lang, alt_path, home=True):
    t = T[lang]
    base = "/" if lang == "en" else "/de/"
    pre = "" if home else base
    nav = "".join(f'<li><a href="{pre}#{i}">{esc(l)}</a></li>' for i, l in t["nav"])
    alt_lang = "de" if lang == "en" else "en"
    sw = (f'<a class="lang" href="{alt_path}" hreflang="{alt_lang}" lang="{alt_lang}" title="{esc(t["switch_title"])}">'
          f'{t["switch_short"]}<span class="sr"> – {esc(t["switch_label"])}</span></a>') if alt_path else ""
    theme = (f'<button class="theme" type="button" data-labels=\'{json.dumps(t["theme_states"], ensure_ascii=False)}\' aria-label="{esc(t["theme_states"]["system"])}">'
             '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><circle cx="10" cy="10" r="6.5"/><path d="M10 3.5a6.5 6.5 0 0 1 0 13z"/></svg></button>')
    return f"""<a class="skip" href="#main">{esc(t["skip"])}</a>
<header class="top" id="top">
 <div class="wrap bar">
  <a class="mark" href="{base}"><span class="dot" aria-hidden="true"></span><span>productivity-boost<span class="tld">.com</span></span></a>
  <nav class="nav" aria-label="{'Main' if lang == 'en' else 'Hauptnavigation'}"><ul>{nav}</ul></nav>
  <div class="tools">{sw}{theme}
   <details class="menu"><summary>{esc(t["menu"])}</summary><nav aria-label="{esc(t['menu'])}"><ul role="list">{nav}</ul></nav></details>
  </div>
 </div>
</header>
<div class="sentinel" aria-hidden="true"></div>"""

def footer(lang, alt_path=None, notes_block=True):
    t = T[lang]
    notes = "".join(f'<li id="note-{i + 1}">{esc(n.format(asof=ASOF[lang]))} <a class="back" href="#ref-{i + 1}">{esc(t["back"])}<span class="sr"> ({t["note"]} {i + 1})</span></a></li>' for i, n in enumerate(t["notes"]))
    ln = f' <span class="muted nw">({t["legal_note"]})</span>' if t["legal_note"] else ""
    return f"""<footer class="foot">
 <div class="wrap">
  {f'<div class="notes"><h2 class="label">{esc(t["notes_h"])}</h2><ol>{notes}</ol></div>' if notes_block else '<div></div>'}
  <div class="legal">
   <p>{esc(t["company"])}</p>
   <p><a href="/impressum/" hreflang="de">{esc(t["imprint"])}{f' (<span lang="de">{t["imprint_de"]}</span>)' if t["imprint_de"] else ""}</a> · <a href="/datenschutz/" hreflang="de">{esc(t["privacy"])}{f' (<span lang="de">{t["privacy_de"]}</span>)' if t["privacy_de"] else ""}</a>{ln}</p>
   <p class="muted">© 2014–2026 · <a href="{EMAIL and 'mailto:' + EMAIL}">{EMAIL}</a></p>
  </div>
 </div>
</footer>
<script src="{vq('/js/main.js')}" defer></script>
</body>
</html>"""

# ---------------- sections ----------------
def stretch(p):
    return 75 + round(p * 50)  # confidence -> width axis (75 % .. 125 %)

def decision(pr, lang, idx):
    t = T[lang]
    rows = ""
    for i, (o, p) in enumerate(pr["opts"]):
        rows += (f'<li class="opt{" win" if i == 0 else ""}"><span class="o">{esc(o)}</span>'
                 f'<span class="track" aria-hidden="true"><span class="fill p{round(p * 100)}"></span></span>'
                 f'<span class="v">{(f"{p:.2f}".replace(".", ",") if lang == "de" else f"{p:.2f}")}</span></li>')
    def pretty(s):
        return esc(json.dumps(json.loads(s), indent=2, ensure_ascii=False))
    return f"""<div class="dpanel{' on' if idx == 0 else ''}" id="dp-{pr['id']}" data-i="{idx}">
  <p class="dstate"><span class="label">{esc(t['state'])}</span> {esc(pr['state'])}</p>
  <p class="dq"><span class="label">{esc(t['question'])}</span> {esc(pr['q'])} <span class="model">{pr['model']}</span></p>
  <ol class="opts">{rows}</ol>
  <details class="json"><summary>{esc(t['panel_json'])}</summary>
   <p class="label">{esc(t['req'])} · POST /v1/systemone</p><pre tabindex="0" role="region" aria-label="{esc(t['req'])} JSON"><code>{pretty(pr['req'])}</code></pre>
   {f'<p class="label">{esc(t["noul_note"])}</p>' if pr["id"] == "guard" else ""}<p class="label">{esc(t['res'])}</p><pre tabindex="0" role="region" aria-label="{esc(t['res'])} JSON"><code>{pretty(pr['res'])}</code></pre>
  </details>
 </div>"""

def hero(lang):
    t = T[lang]
    tabs = "".join(f'<button type="button" role="tab" id="dt-{p["id"]}" aria-controls="dp-{p["id"]}" aria-selected="{"true" if i == 0 else "false"}" tabindex="{0 if i == 0 else -1}">{esc(p["tab"])}</button>'
                   for i, p in enumerate(t["presets"]))
    panels = "".join(decision(p, lang, i) for i, p in enumerate(t["presets"]))
    proof = "".join(f"<li>{esc(x)}</li>" for x in t["proof"])
    return f"""<section class="hero wrap" aria-labelledby="h1">
 <div class="hero-copy">
  <p class="eyebrow"><span>{esc(t["eyebrow"][0])}</span><span class="sep" aria-hidden="true"> · </span><span>{esc(t["eyebrow"][1])}</span></p>
  <h1 id="h1">{esc(t["h1"])}</h1>
  <p class="lede">{esc(t["sub"])}</p>
  <p class="ctas">{ext("https://decisionmodels.io/login?next=/dashboard", esc(t["cta1"]), lang, "btn")}{ext(QS_URL, esc(t["cta2"]), lang, "tlink")}</p>
 </div>
 <figure class="decide">
  <div class="tabs" role="tablist" aria-label="{esc(t['panel_label'])}">{tabs}</div>
  {panels}
  <figcaption>{esc(t["panel_caption"])} {ext(QS_URL, 'decisionmodels.io/docs/quickstart', lang)}</figcaption>
 </figure>
 <ul class="proof" role="list">{proof}</ul>
 </section>""" + fit(lang)

def facts(items):
    return '<dl class="facts">' + "".join(f"<div><dt>{esc(k)}</dt><dd>{rich(v)}</dd></div>" for k, v in items) + "</dl>"

def links(items, lang):
    return '<p class="links">' + "".join(ext(u, esc(l), lang) for l, u in items) + "</p>"

def shot(light, dark, mob_light, mob_dark, alt, sizes, href=None, cls="shot", lang="en"):
    """theme-aware screenshot link: both variants lazy; CSS shows the one matching the theme (hidden lazy images never load).
    The link is named by its destination; the alt text describes the screenshot."""
    host = re.sub(r"^https?://", "", href or "").rstrip("/")
    tag, attrs = ("a", f' href="{esc(href)}" rel="noopener" target="_blank" aria-label="{esc(host)} ({T[lang]["new_tab"]})"') if href else ("div", "")
    if dark is None:
        return f'<{tag} class="{cls}"{attrs}>{picture(light, alt, sizes)}</{tag}>'
    return (f'<{tag} class="{cls}"{attrs}><span class="v-light">{picture(light, alt, sizes)}</span>'
            f'<span class="v-dark">{picture(dark, alt, sizes)}</span></{tag}>')

def products(lang):
    t = T[lang]
    sizes = "(min-width: 75em) 640px, (min-width: 62em) 52vw, 100vw"
    cap = t["shot_cap"]
    return f"""<section class="products" id="products" aria-labelledby="products-h">
 <div class="wrap p-head"><p class="kicker"><span>{esc(t["products_k"])}</span></p><h2 id="products-h">{esc(t["products_h"])}</h2></div>
 <article class="chapter wrap" aria-labelledby="dm-h">
  <div class="ch-copy">
   <p class="kicker"><span>{esc(t["dm_kicker"])}</span><span class="host">{esc(t["dm_host"])}</span></p>
   <h3 id="dm-h">{rich(t["dm_h"])}</h3>
   <p>{marks(t["dm_p"], lang)}</p>
   {links(t["dm_links"], lang)}
  </div>
  <figure class="ch-media">
   {shot("dm-desk-light", "dm-desk-dark", None, None, t["dm_alt"], sizes, DM_URL, lang=lang)}
   <figcaption>{esc(cap.format(site="decisionmodels.io"))}</figcaption>
  </figure>
  <div class="ch-foot">{facts(t["dm_facts"])}</div>
 </article>
 <article class="chapter flip wrap" aria-labelledby="reax-h">
  <div class="ch-copy">
   <p class="kicker"><span>{esc(t["reax_kicker"])}</span><span class="host">{esc(t["reax_host"])}</span></p>
   <h3 id="reax-h">{esc(t["reax_h"])}</h3>
   <p>{esc(t["reax_p"])}</p>
   {links(t["reax_links"], lang)}
  </div>
  <figure class="ch-media stack">
   {shot("reax-desk", None, None, None, t["reax_alt"], sizes, "https://reax.co", lang=lang)}
   <figcaption>{esc(cap.format(site="reax.co"))}</figcaption>
  </figure>
  <div class="ch-foot">{facts(t["reax_facts"])}</div>
 </article>
 </section>"""

def fit(lang):
    t = T[lang]
    items = ""
    for i, (verb, name, txt, url, host) in enumerate(t["fit"]):
        items += (f'<li class="node"><p class="label"><span class="n" aria-hidden="true">{i + 1}</span> {esc(verb)}</p><h3>{esc(name)}</h3><p>{marks(txt, lang)}</p>'
                  f'<p class="host">{ext(url, esc(host), lang)}</p></li>')
    return f"""<section class="fit wrap" aria-labelledby="fit-h">
 <h2 class="label" id="fit-h">{esc(t["fit_h"])}</h2>
 <ol class="flow">{items}</ol>
</section>"""

def fmt_views(v, lang):
    if lang == "de":
        return f"{v // 1_000_000} Mio." if v >= 1_000_000 else f"{v // 1000} Tsd."
    return (f"{v // 100_000 / 10:.1f}".rstrip("0").rstrip(".") + "M") if v >= 1_000_000 else f"{v // 1000}k"

def public(lang):
    t = T[lang]
    cards = ""
    for k, p in enumerate(POSTS):
        img = (picture(p["img"], p["alt_" + lang], "(min-width: 62em) 400px, (min-width: 48em) 46vw, 100vw", cls="chart" if p.get("chart") else "") if p.get("img")
               else f'<span class="word" aria-hidden="true">{esc(p.get("word", ""))}</span>')
        badge = f'<span class="vbadge" aria-hidden="true">{esc(t["video"])}</span>' if p.get("video") else ""
        cards += (f'<li class="post"><a href="{esc(p["url"])}" rel="noopener" target="_blank">'
                  f'<div class="pimg">{img}{badge}</div>'
                  f'<p class="views" id="pv{k}"><strong>{fmt_views(p["views"], lang)}</strong> {esc(t["views"])}</p>'
                  f'<h3 id="pt{k}">{esc(p["title_" + lang])}</h3><p>{esc(p["what_" + lang])}</p>'
                  f'<p class="meta">{esc(p["date_" + lang])} · {esc(t["open_post"])}<span class="sr"> ({t["new_tab"]})</span><span aria-hidden="true"> ↗</span></p></a></li>')
    posts = f'<ul class="posts" role="list">{cards}</ul>' if cards else ""
    lab = "".join(f'<li><p class="label">{esc(g)}</p><h4>{ext(u, esc(n), lang)}</h4><p>{esc(d)}</p><p class="meta">{esc(m)}</p></li>'
                  for n, g, d, m, u in t["lab"])
    return f"""<section class="public wrap" id="public" aria-labelledby="public-h">
 <p class="kicker"><span>{esc(t["pub_kicker"])}</span>{ext("https://x.com/airesearch12", "@airesearch12", lang, "host")}</p>
 <h2 id="public-h">{esc(t["pub_h"])}</h2>
 <p class="intro">{marks(t["pub_p"], lang)}</p>
 {posts}
 <h3 class="label lab-h">{esc(t["lab_h"])}</h3>
 <ul class="lab" role="list">{lab}</ul>
 <p class="more">{ext(GH_URL + "?tab=repositories", esc(t["all_gh"]), lang)}</p>
</section>"""

def earlier(lang):
    t = T[lang]
    cards = ""
    for name, title, tag, txt in t["early"]:
        key = "old-" + name
        alt = IMG[key].get("alt_" + lang) or title
        wide = name == "bms-area"
        logo = name in ("lightgbm-dotnet", "subtitles")
        cards += (f'<li class="ew{" wide" if wide else ""}{" logo" if logo else ""}">{picture(key, alt, "(min-width: 75em) 600px, (min-width: 48em) 60vw, 78vw" if wide else "(min-width: 75em) 290px, (min-width: 48em) 30vw, 78vw")}'
                  f'<p class="label">{esc(tag)}</p><h3>{esc(title)}</h3><p>{esc(txt)}</p></li>')
    return f"""<section class="earlier" id="earlier" aria-labelledby="earlier-h">
 <div class="wrap">
  <p class="kicker"><span>{esc(t["early_kicker"])}</span></p>
  <h2 id="earlier-h">{esc(t["early_h"])}</h2>
  <p class="intro">{esc(t["early_p"])}</p>
 </div>
 <div class="rail-wrap"><ul class="rail" role="list" data-label="{esc(t['early_region'])}">{cards}</ul></div>
</section>"""

def about(lang):
    t = T[lang]
    ps = "".join(f"<p>{esc(p)}</p>" for p in t["about_p"])
    els = "".join(f'<li><span class="label">{esc(k)}</span> {ext(u, esc(v), lang)}</li>' for k, v, u in t["elsewhere"])
    return f"""<section class="about wrap" id="about" aria-labelledby="about-h">
 <p class="kicker a-k"><span>{esc(t["about_kicker"])}</span></p>
 <div class="portrait">{picture("portrait2", t["portrait_alt"], "(min-width: 48em) 320px, 60vw")}</div>
 <div class="about-copy">
  <h2 id="about-h">{esc(t["about_h"])}</h2>
  {ps}
  <ul class="elsewhere" role="list">{els}</ul>
 </div>
</section>"""

def contact(lang):
    t = T[lang]
    st = "".join(f'<li><span class="label">{esc(k)}</span>{ext(u, esc(v), lang)}</li>' for k, v, u in t["start"])
    return f"""<section class="contact wrap" id="contact" aria-labelledby="contact-h">
 <p class="kicker"><span>{esc(t["contact_kicker"])}</span></p>
 <div class="c-grid">
  <div><h2 id="contact-h">{esc(t["contact_h"])}</h2>
  <p class="c-p">{esc(t["contact_p"])}</p>
  <p class="mail"><a href="mailto:{EMAIL}">{EMAIL}</a></p></div>
  <div class="start"><h3 class="label">{esc(t["start_h"])}</h3><ul role="list">{st}</ul></div>
 </div>
</section>"""

# ---------------- pages ----------------
def page_home(lang):
    t = T[lang]
    path, alt = ("/", "/de/") if lang == "en" else ("/de/", "/")
    return (head(lang, t["title"], t["desc"], path, alt) + "\n<body>\n" + header(lang, alt) +
            '\n<main id="main">\n' + hero(lang) + products(lang) + public(lang) + earlier(lang) + about(lang) + contact(lang) +
            "\n</main>\n" + footer(lang, alt))

def page_legal(kind):
    body = open(os.path.join(SRC, "legal", f"{kind}.html"), encoding="utf-8").read()
    title = {"impressum": "Impressum", "datenschutz": "Datenschutzerklärung"}[kind]
    return (head("de", f"{title} — productivity-boost.com", f"{title} von productivity-boost.com", f"/{kind}/", None, og=False) +
            "\n<body>\n" + header("de", None, home=False) + f'\n<main id="main" class="legalpage wrap">{body}</main>\n' + footer("de", notes_block=False))

def page_404():
    t = T["en"]; d = T["de"]
    return (head("en", t["nf_title"], t["nf_p"], "/404.html", None, og=False, robots="noindex") + "\n<body>\n" + header("en", None, home=False) +
            f'\n<main id="main" class="nf wrap"><p class="kicker"><span>404</span></p><h1>{esc(t["nf_title"])}</h1><p>{esc(t["nf_p"])} <a href="/">{esc(t["nf_home"])}</a></p>'
            f'<p lang="de">{esc(d["nf_p"])} <a href="/de/">{esc(d["nf_home"])}</a></p></main>\n' + footer("en", notes_block=False))

def write(rel, s):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(s)

def gen_css():
    """generated utility classes (no inline styles: strict CSP)."""
    css = [f".p{p} {{--p:{p / 100:.2f}}}" for p in range(0, 101)]
    css += [f".w{w} {{font-stretch:{w}%}}" for w in range(75, 126)]
    return "\n".join(css)

def minify_css(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s*([{};,>])\s*", r"\1", s)
    s = re.sub(r":\s+", ":", s)  # never strip the space *before* a colon: ".a :is(.b)" is a descendant selector
    return s.replace(";}", "}").strip()

def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    for d in ("img", "fonts", "static", "js"):
        shutil.copytree(os.path.join(SRC, d), os.path.join(OUT, d))
    os.makedirs(os.path.join(OUT, "css"))
    css = open(os.path.join(SRC, "css", "site.css"), encoding="utf-8").read() + "\n" + gen_css()
    for f in ("archivo", "plex-mono"):
        css = css.replace(f"url(/fonts/{f}.woff2)", f"url({vq(f'/fonts/{f}.woff2')})")
    open(os.path.join(OUT, "css", "site.css"), "w").write(minify_css(css))
    # css lives in src/css only as source; hash the built file for cache busting
    _VQ["/css/site.css"] = f"/css/site.css?v={sha(open(os.path.join(OUT, 'css', 'site.css'), 'rb').read())}"
    write("index.html", page_home("en"))
    write("de/index.html", page_home("de"))
    write("impressum/index.html", page_legal("impressum"))
    write("datenschutz/index.html", page_legal("datenschutz"))
    write("404.html", page_404())
    shutil.copy(os.path.join(SRC, "static", "favicon.svg"), os.path.join(OUT, "favicon.svg"))
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n")
    urls = [("/", "/de/"), ("/de/", "/")]
    sm = "".join(f'<url><loc>{BASE_URL}{u}</loc><xhtml:link rel="alternate" hreflang="en" href="{BASE_URL}/"/><xhtml:link rel="alternate" hreflang="de" href="{BASE_URL}/de/"/></url>' for u, _ in urls)
    sm += f"<url><loc>{BASE_URL}/impressum/</loc></url><url><loc>{BASE_URL}/datenschutz/</loc></url>"
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">{sm}</urlset>')
    h = base64.b64encode(hashlib.sha256(THEME_JS.encode()).digest()).decode()
    csp = (f"default-src 'none'; script-src 'self' 'sha256-{h}'; style-src 'self'; img-src 'self' data:; font-src 'self'; "
           "connect-src 'self'; manifest-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; upgrade-insecure-requests")
    conf = open(os.path.join(SRC, "nginx.conf.tpl")).read().replace("__CSP__", csp)
    open(os.path.join(ROOT, "nginx.conf"), "w").write(conf)
    print("built", BUILD_ID, "pages: /, /de/, legal, 404; posts:", len(POSTS))

if __name__ == "__main__":
    main()
