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
            # html/body clip horizontally, so also look for content that ends past the viewport without its own clipping box
            cut = pg.evaluate("""(w)=>{const out=[];for(const e of document.querySelectorAll('body *')){const r=e.getBoundingClientRect();if(r.width===0||r.right<=w+1||e.closest('.sr,[hidden],dialog:not([open])'))continue;
              let p=e.parentElement,clipped=false;while(p&&p!==document.body){const cs=getComputedStyle(p);if(cs.overflowX!=='visible'||cs.clipPath!=='none'){const pr=p.getBoundingClientRect();if(pr.right<=w+1){clipped=true;break}}p=p.parentElement}
              const cs=getComputedStyle(e);if(!clipped&&cs.visibility!=='hidden'&&!(cs.position==='absolute'&&cs.pointerEvents==='none'))out.push(e.tagName+'.'+String(e.className).slice(0,40)+' '+Math.round(r.right))}return out.slice(0,5)}""", w)
            if cut: print("CUT", w, path, cut)
            if sw > w:
                culprit = pg.evaluate("""(w)=>[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>w+1).slice(0,4).map(e=>e.tagName+'.'+e.className+' '+Math.round(e.getBoundingClientRect().right))""", w)
                print("OVERFLOW", w, path, sw, culprit)
            pg.close()
    b.close()
print("overflow check done")
