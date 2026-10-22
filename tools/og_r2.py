"""OG images 1200x630 per language from the site's own type. Usage: python3 -I tools/og_r2.py"""
import os, sys
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from content import T
F = os.path.join(ROOT, "src", "fonts")
def page(lang):
    t = T[lang]; p = t["presets"][0]
    rows = "".join(f'<div class="r{" w" if i==0 else ""}"><span style="font-stretch:{75+round(v*50)}%">{o}</span><b>{v:.2f}</b><i><em style="width:{v*100}%"></em></i></div>' for i,(o,v) in enumerate(p["opts"]))
    return f"""<html><head><style>
@font-face{{font-family:A;src:url(file://{F}/archivo.woff2);font-weight:380 640;font-stretch:75% 125%}}
@font-face{{font-family:M;src:url(file://{F}/plex-mono.woff2)}}
body{{margin:0;width:1200px;height:630px;background:#f6f5f0;color:#111214;font-family:A;display:grid;grid-template-columns:1.25fr .75fr;gap:56px;padding:72px 80px;box-sizing:border-box;align-items:center}}
.k{{font:15px M;letter-spacing:.06em;text-transform:uppercase;color:#6a6c71;margin-bottom:28px;display:flex;gap:10px;align-items:center}}
.k i{{width:11px;height:11px;border-radius:50%;background:#0f6e50;display:inline-block}}
h1{{font-size:62px;line-height:1.0;font-weight:560;font-stretch:{108 if lang=='en' else 100}%;letter-spacing:-.035em;margin:0}}
.c{{background:#efede6;border:1px solid rgba(17,18,20,.12);border-radius:18px;padding:26px}}
.s{{font-size:17px;color:#45474c;margin-bottom:18px}}
.r{{display:grid;grid-template-columns:1fr auto;gap:8px 12px;margin:14px 0;align-items:baseline}}
.r span{{font-size:28px;font-weight:520;color:#6a6c71}} .r.w span,.r.w b{{color:#111214}}
.r b{{font:16px M;color:#6a6c71}} .r i{{grid-column:1/-1;height:7px;background:#e2e0d8;border-radius:4px;overflow:hidden}}
.r em{{display:block;height:100%;background:#8b8d92}} .r.w em{{background:#0f6e50}}
.f{{position:absolute;left:80px;bottom:44px;font:15px M;color:#6a6c71}}
</style></head><body><div><div class="k"><i></i>productivity-boost.com</div><h1>{t['h1']}</h1></div>
<div class="c"><div class="s">{p['q']}</div>{rows}</div><div class="f">Decision Models · REAX · Florian Standhartinger</div></body></html>"""
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width":1200,"height":630})
    for lang in ("en","de"):
        pg.set_content(page(lang)); pg.wait_for_timeout(400)
        pg.screenshot(path=os.path.join(ROOT,"src","img",f"og-{lang}.png"))
    b.close()
print("og ok")
