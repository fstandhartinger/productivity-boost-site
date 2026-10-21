import sys, os, threading, http.server, socketserver, functools
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = functools.partial(Q, directory=os.path.join(ROOT, "site")); H.log_message = lambda *a: None
srv = socketserver.TCPServer(('127.0.0.1', 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (320, 360, 390, 768, 1024, 1280, 1440, 1920):
        for path in ("/", "/de/", "/works/", "/de/projekte/", "/impressum/", "/datenschutz/"):
            pg = b.new_page(viewport={"width": w, "height": 800}); pg.goto(base + path); pg.wait_for_timeout(300)
            sw = pg.evaluate("document.documentElement.scrollWidth")
            if sw > w:
                culprit = pg.evaluate("""(w)=>[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>w+1).slice(0,4).map(e=>e.tagName+'.'+e.className+' '+Math.round(e.getBoundingClientRect().right))""", w)
                print("OVERFLOW", w, path, sw, culprit)
            pg.close()
    b.close()
print("overflow check done")
