"""Tablet ruler check: no staggered genre label may touch a scale tick (768/820/900 px, DE). usage: ruler.py site"""
import sys, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Q, directory=sys.argv[1])); threading.Thread(target=srv.serve_forever, daemon=True).start()
u = f"http://127.0.0.1:{srv.server_address[1]}"
with sync_playwright() as p:
    b = p.chromium.launch()
    for w in (768, 820, 900):
        pg = b.new_page(viewport={'width': w, 'height': 1024}); pg.goto(u + '/de/'); pg.wait_for_timeout(800)
        r = pg.evaluate("(()=>{const r=document.querySelector('.ruler').getBoundingClientRect();return [r.left,r.top+scrollY,r.width,r.height]})()")
        # overlap test: any label box intersecting a tick line of the scale svg
        bad = pg.evaluate("""()=>{const ls=[...document.querySelectorAll('.ruler .st i')].map(e=>e.getBoundingClientRect()).filter(r=>r.width);const ts=[...document.querySelectorAll('.ruler svg.scale line')].map(e=>e.getBoundingClientRect());
          let n=[];for(const l of ls)for(const t of ts){if(t.left>=l.left&&t.left<=l.right&&t.bottom>l.top+1&&t.top<l.bottom-1)n.push([Math.round(l.top),Math.round(l.bottom),Math.round(t.top),Math.round(t.bottom)])}return n.slice(0,3)}""")
        print(w, 'ruler', [round(x) for x in r], 'label/tick overlaps', bad)
        if w == 768:
            pg.evaluate(f"scrollTo(0,{r[1]-40})"); pg.wait_for_timeout(300); pg.screenshot(path='/tmp/pb24/ipad-ruler.png', clip={'x': 0, 'y': 0, 'width': 768, 'height': 160})
    b.close()
srv.shutdown()
