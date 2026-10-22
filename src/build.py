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
    return html.escape(s, quote=True)

def sha(b):
    return hashlib.sha256(b).hexdigest()[:10]

_VQ = {}
def vq(path):
    """content-hashed URL for an asset under src/ (immutable caching)."""
    if path not in _VQ:
        p = os.path.join(SRC, path.lstrip("/"))
        _VQ[path] = f"{path}?v={sha(open(p, 'rb').read())}"
    return _VQ[path]

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
<link rel="canonical" href="{BASE_URL}{path}">{alts}
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
          f'<span aria-hidden="true">{t["switch_short"]}</span><span class="sr">{esc(t["switch_label"])}</span></a>') if alt_path else ""
    theme = (f'<button class="theme" type="button" data-labels=\'{json.dumps(t["theme_states"], ensure_ascii=False)}\' aria-label="{esc(t["theme_states"]["system"])}">'
             '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><circle cx="10" cy="10" r="6.5"/><path d="M10 3.5a6.5 6.5 0 0 1 0 13z"/></svg></button>')
    return f"""<a class="skip" href="#main">{esc(t["skip"])}</a>
<header class="top" id="top">
 <div class="wrap bar">
  <a class="mark" href="{base}"><span class="dot" aria-hidden="true"></span><span>productivity-boost<span class="tld">.com</span></span></a>
  <nav class="nav" aria-label="{'Main' if lang == 'en' else 'Hauptnavigation'}"><ul>{nav}</ul></nav>
  <div class="tools">{sw}{theme}
   <details class="menu"><summary>{esc(t["menu"])}</summary><nav aria-label="{esc(t['menu'])}"><ul>{nav}</ul></nav></details>
  </div>
 </div>
</header>
<div class="sentinel" aria-hidden="true"></div>"""

def footer(lang, alt_path=None):
    t = T[lang]
    notes = "".join(f"<li>{esc(n.format(asof=ASOF[lang]))}</li>" for n in t["notes"])
    ln = f' <span class="muted">({t["legal_note"]})</span>' if t["legal_note"] else ""
    return f"""<footer class="foot">
 <div class="wrap">
  <div class="notes"><h2 class="label">{esc(t["notes_h"])}</h2><ol>{notes}</ol></div>
  <div class="legal">
   <p>{esc(t["company"])}</p>
   <p><a href="/impressum/" hreflang="de" lang="de">{esc(t["imprint"])}</a> · <a href="/datenschutz/" hreflang="de" lang="de">{esc(t["privacy"])}</a>{ln}</p>
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
        rows += (f'<li class="opt{" win" if i == 0 else ""}"><span class="o w{stretch(p)}">{esc(o)}</span>'
                 f'<span class="track" aria-hidden="true"><span class="fill p{round(p * 100)}"></span></span>'
                 f'<span class="v">{p:.2f}</span></li>')
    def pretty(s):
        return esc(json.dumps(json.loads(s), indent=2, ensure_ascii=False))
    return f"""<div class="dpanel" id="dp-{pr['id']}" role="tabpanel" aria-labelledby="dt-{pr['id']}" data-i="{idx}">
  <p class="dstate"><span class="label">{esc(t['state'])}</span> {esc(pr['state'])}</p>
  <p class="dq"><span class="label">{esc(t['question'])}</span> {esc(pr['q'])} <span class="model">{pr['model']}</span></p>
  <ol class="opts">{rows}</ol>
  <details class="json"><summary>{esc(t['panel_json'])}</summary>
   <p class="label">{esc(t['req'])} · POST /v1/systemone</p><pre tabindex="0"><code>{pretty(pr['req'])}</code></pre>
   <p class="label">{esc(t['res'])}</p><pre tabindex="0"><code>{pretty(pr['res'])}</code></pre>
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
  <p class="eyebrow">{esc(t["eyebrow"])}</p>
  <h1 id="h1">{esc(t["h1"])}</h1>
  <p class="lede">{esc(t["sub"])}</p>
  <p class="ctas"><a class="btn" href="#products">{esc(t["cta1"])}<span aria-hidden="true"> ↓</span></a>{ext(QS_URL, esc(t["cta2"]), lang, "tlink")}</p>
 </div>
 <figure class="decide" aria-label="{esc(t['panel_label'])}">
  <div class="tabs" role="tablist" aria-label="{esc(t['panel_label'])}">{tabs}</div>
  {panels}
  <figcaption>{esc(t["panel_caption"])} {ext(QS_URL, 'decisionmodels.io/docs/quickstart', lang)}</figcaption>
 </figure>
 <ul class="proof" role="list">{proof}</ul>
</section>"""

def facts(items):
    return '<dl class="facts">' + "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in items) + "</dl>"

def links(items, lang):
    return '<p class="links">' + "".join(ext(u, esc(l), lang) for l, u in items) + "</p>"

def shot(light, dark, mob_light, mob_dark, alt, sizes):
    """theme-aware screenshot: both variants lazy; CSS shows the one matching the theme (hidden lazy images never load)."""
    if dark is None:
        return f'<div class="shot">{picture(light, alt, sizes, mobile=mob_light)}</div>'
    return (f'<div class="shot"><div class="v-light">{picture(light, alt, sizes, mobile=mob_light)}</div>'
            f'<div class="v-dark">{picture(dark, alt, sizes, mobile=mob_dark)}</div></div>')

def products(lang):
    t = T[lang]
    sizes = "(min-width: 75em) 760px, (min-width: 48em) 58vw, 100vw"
    fit = ""
    for i, (verb, name, txt, url, host) in enumerate(t["fit"]):
        fit += (f'<li class="node"><p class="label"><span class="n">{i + 1}</span> {esc(verb)}</p><h4>{esc(name)}</h4><p>{esc(txt)}</p>'
                f'<p class="host">{ext(url, esc(host), lang)}</p></li>')
    return f"""<section class="products" id="products" aria-labelledby="products-h">
 <h2 class="sr" id="products-h">{esc(t["products_h"])}</h2>
 <article class="chapter wrap" aria-labelledby="dm-h">
  <div class="ch-copy">
   <p class="kicker"><span>{esc(t["dm_kicker"])}</span><span class="host">{esc(t["dm_host"])}</span></p>
   <h3 id="dm-h">{esc(t["dm_h"])}</h3>
   <p>{esc(t["dm_p"])}</p>
   {facts(t["dm_facts"])}
   {links(t["dm_links"], lang)}
  </div>
  {shot("dm-desk-light", "dm-desk-dark", "dm-mob-light", "dm-mob-dark", t["dm_alt"], sizes)}
 </article>
 <article class="chapter flip wrap" aria-labelledby="reax-h">
  <div class="ch-copy">
   <p class="kicker"><span>{esc(t["reax_kicker"])}</span><span class="host">{esc(t["reax_host"])}</span></p>
   <h3 id="reax-h">{esc(t["reax_h"])}</h3>
   <p>{esc(t["reax_p"])}</p>
   {facts(t["reax_facts"])}
   {links(t["reax_links"], lang)}
  </div>
  <div class="stack">
   {shot("reax-desk", None, "reax-mob", None, t["reax_alt"], sizes)}
   {shot("mine-desk-light", "mine-desk-dark", "mine-mob-light", "mine-mob-dark", t["mine_alt"], "(min-width: 48em) 34vw, 100vw").replace('class="shot"', 'class="shot small"', 1)}
  </div>
 </article>
 <div class="fit wrap" aria-labelledby="fit-h">
  <h3 class="label" id="fit-h">{esc(t["fit_h"])}</h3>
  <ol class="flow">{fit}</ol>
 </div>
</section>"""

def fmt_views(v, lang):
    if v >= 1_000_000:
        s = f"{v / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M"
    else:
        s = f"{v // 1000}k"
    return s.replace(".", ",") if lang == "de" else s

def public(lang):
    t = T[lang]
    cards = ""
    for p in POSTS:
        img = (picture(p["img"], p["alt_" + lang], "(min-width: 62em) 400px, (min-width: 48em) 46vw, 100vw") if p.get("img")
               else f'<span class="word" aria-hidden="true">{esc(p.get("word", ""))}</span>')
        cards += (f'<li class="post"><a href="{esc(p["url"])}" rel="noopener" target="_blank">'
                  f'<div class="pimg">{img}</div>'
                  f'<p class="views"><strong>{fmt_views(p["views"], lang)}</strong> {esc(t["views"])}{"+" if p.get("plus") else ""}</p>'
                  f'<h3>{esc(p["title_" + lang])}</h3><p>{esc(p["what_" + lang])}</p>'
                  f'<p class="meta">{esc(p["date_" + lang])} · {esc(t["open_post"])}<span class="sr"> ({t["new_tab"]})</span><span aria-hidden="true"> ↗</span></p></a></li>')
    posts = f'<ul class="posts" role="list">{cards}</ul>' if cards else ""
    lab = "".join(f'<li><p class="label">{esc(g)}</p><h4>{ext(u, esc(n), lang)}</h4><p>{esc(d)}</p><p class="meta">{esc(m)}</p></li>'
                  for n, g, d, m, u in t["lab"])
    return f"""<section class="public wrap" id="public" aria-labelledby="public-h">
 <p class="kicker"><span>{esc(t["pub_kicker"])}</span>{ext("https://x.com/airesearch12", "@airesearch12", lang, "host")}</p>
 <h2 id="public-h">{esc(t["pub_h"])}</h2>
 <p class="intro">{esc(t["pub_p"])}</p>
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
        cards += (f'<li class="ew{" wide" if name == "bms-area" else ""}">{picture(key, alt, "(min-width: 75em) 380px, (min-width: 48em) 30vw, 78vw")}'
                  f'<p class="label">{esc(tag)}</p><h3>{esc(title)}</h3><p>{esc(txt)}</p></li>')
    return f"""<section class="earlier" id="earlier" aria-labelledby="earlier-h">
 <div class="wrap">
  <p class="kicker"><span>{esc(t["early_kicker"])}</span></p>
  <h2 id="earlier-h">{esc(t["early_h"])}</h2>
  <p class="intro">{esc(t["early_p"])}</p>
 </div>
 <div class="rail-wrap"><ul class="rail" role="list" tabindex="0" aria-label="{esc(t['early_region'])}">{cards}</ul></div>
</section>"""

def about(lang):
    t = T[lang]
    ps = "".join(f"<p>{esc(p)}</p>" for p in t["about_p"])
    els = "".join(f'<li><span class="label">{esc(k)}</span> {ext(u, esc(v), lang)}</li>' for k, v, u in t["elsewhere"])
    return f"""<section class="about wrap" id="about" aria-labelledby="about-h">
 <div class="portrait">{picture("portrait2", t["portrait_alt"], "(min-width: 48em) 320px, 60vw")}</div>
 <div class="about-copy">
  <p class="kicker"><span>{esc(t["about_kicker"])}</span></p>
  <h2 id="about-h">{esc(t["about_h"])}</h2>
  {ps}
  <ul class="elsewhere" role="list">{els}</ul>
 </div>
</section>"""

def contact(lang):
    t = T[lang]
    return f"""<section class="contact wrap" id="contact" aria-labelledby="contact-h">
 <p class="kicker"><span>{esc(t["contact_kicker"])}</span></p>
 <h2 id="contact-h">{esc(t["contact_h"])}</h2>
 <p>{esc(t["contact_p"])}</p>
 <p class="mail"><a href="mailto:{EMAIL}">{EMAIL}</a></p>
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
            "\n<body>\n" + header("de", None, home=False) + f'\n<main id="main" class="legalpage wrap">{body}</main>\n' + footer("de"))

def page_404():
    t = T["en"]; d = T["de"]
    return (head("en", t["nf_title"], t["nf_p"], "/404.html", None, og=False, robots="noindex") + "\n<body>\n" + header("en", None, home=False) +
            f'\n<main id="main" class="nf wrap"><p class="kicker"><span>404</span></p><h1>{esc(t["nf_title"])}</h1><p>{esc(t["nf_p"])} <a href="/">{esc(t["nf_home"])}</a></p>'
            f'<p lang="de">{esc(d["nf_p"])} <a href="/de/">{esc(d["nf_home"])}</a></p></main>\n' + footer("en"))

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
    s = re.sub(r"\s*([{};:,>])\s*", r"\1", s)
    return s.replace(";}", "}").strip()

def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    for d in ("img", "fonts", "static", "js"):
        shutil.copytree(os.path.join(SRC, d), os.path.join(OUT, d))
    os.makedirs(os.path.join(OUT, "css"))
    css = open(os.path.join(SRC, "css", "site.css"), encoding="utf-8").read() + "\n" + gen_css()
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
