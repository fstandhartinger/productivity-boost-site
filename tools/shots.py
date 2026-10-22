"""Screenshots of the built site (served locally). Usage: python3 -I tools/shots.py <outdir> [base_url]"""
import sys, os, threading, http.server, socketserver, functools
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
base = sys.argv[2] if len(sys.argv) > 2 else None
if not base:
    H = functools.partial(Q, directory=os.path.join(ROOT, "site")); H.log_message = lambda *a: None
    srv = socketserver.TCPServer(('127.0.0.1', 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
shots = [("desk-en", "/", 1440, 900, "light", True), ("desk-de", "/de/", 1440, 900, "light", False), ("desk-en-dark", "/", 1440, 900, "dark", False),
         ("mob-en", "/", 390, 844, "light", True), ("mob-de", "/de/", 390, 844, "light", True), ("mob-en-dark", "/", 390, 844, "dark", False),
         ("works-en", "/works/", 1440, 900, "light", False), ("mob-works-de", "/de/projekte/", 390, 844, "light", False),
         ("desk-de-dark", "/de/", 1440, 900, "dark", False), ("mob-de-dark", "/de/", 390, 844, "dark", False),
         ("desk-en-s2", "/#benchmarks", 1440, 900, "light", False), ("desk-de-s3", "/de/#agents", 1440, 900, "dark", False),
         ("mob-en-s2", "/#networks", 390, 844, "light", False), ("mob-de-s3", "/de/#worlds", 390, 844, "dark", False)]
only = os.environ.get("ONLY")
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, path, w, h, scheme, full in shots:
        if only and name not in only.split(","): continue
        ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=(1 if full else 2) if w < 500 else 1, color_scheme=scheme, is_mobile=w < 500, has_touch=w < 500)
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: errs.append(m.text) if m.type in ("error", "warning") else None)
        marker = os.environ.get("MARKER")
        for attempt in range(8):
            resp = pg.goto(base + path, wait_until="load")
            html = pg.content()
            if resp and resp.status in (200, 304) and (not marker or marker in html) and "Bad Gateway" not in html: break
            print(name, "stale or error, retry", attempt, resp.status if resp else None); pg.wait_for_timeout(10000)
        else:
            raise SystemExit(f"{name}: page never showed the expected build")
        pg.wait_for_timeout(5200)
        pg.screenshot(path=f"{out}/{name}-top.png")
        if full:
            # scroll through to trigger in-view states, then full page
            H_ = pg.evaluate("document.body.scrollHeight")
            for y in range(0, H_, 700): pg.evaluate(f"scrollTo(0,{y})"); pg.wait_for_timeout(120)
            pg.evaluate("scrollTo(0,0)"); pg.wait_for_timeout(600)
            pg.screenshot(path=f"{out}/{name}-full.png", full_page=True)
        if errs: print(name, "ERRORS:", errs[:5])
        ctx.close()
    b.close()
print("shots ->", out)
