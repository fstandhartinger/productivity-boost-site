"""Screenshot matrix. Usage: python3 -I tools/shots_r2.py <base-url> <outdir> [full|top]"""
import os, sys
from playwright.sync_api import sync_playwright
base, out = sys.argv[1].rstrip("/"), sys.argv[2]; mode = sys.argv[3] if len(sys.argv) > 3 else "full"
os.makedirs(out, exist_ok=True)
VP = {"d1440": (1440, 900, 1), "m390": (390, 844, 2)}
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for lang, path in (("en", "/"), ("de", "/de/")):
        for vk, (w, h, s) in VP.items():
            for scheme in ("light", "dark"):
                ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=s, color_scheme=scheme, reduced_motion="reduce")
                pg = ctx.new_page(); pg.goto(base + path, wait_until="networkidle")
                # load lazy images
                pg.evaluate("async()=>{for(let y=0;y<document.body.scrollHeight;y+=500){window.scrollTo(0,y);await new Promise(r=>setTimeout(r,60))}window.scrollTo(0,0)}")
                pg.wait_for_timeout(500)
                n = f"{out}/{lang}-{vk}-{scheme}"
                pg.screenshot(path=n + "-top.png")
                if mode == "full": pg.screenshot(path=n + "-full.png", full_page=True)
                sw = pg.evaluate("document.documentElement.scrollWidth")
                if sw > w: print("OVERFLOW", lang, vk, scheme, sw)
                ctx.close()
    b.close()
print("shots ok", out)
