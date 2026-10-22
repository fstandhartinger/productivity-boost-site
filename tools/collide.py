"""CI check (desktop): the received-picture window must never sit on a signal or a label, and no in-plot label may sit on a
signal or another label. Renders the static waterfall (reduced motion), hides windows + labels, measures bright pixels.
Phones: tools/place.py check."""
import sys, os, threading, http.server, socketserver, functools, io
from playwright.sync_api import sync_playwright
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Q, directory=os.path.join(ROOT, "site"))); threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"
fails = 0
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h in ((1280, 720), (1366, 768), (1440, 900), (1536, 864), (1680, 1050), (1920, 1080)):
        for path in ("/", "/de/"):
            ctx = b.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce"); pg = ctx.new_page()
            pg.goto(base + path); pg.wait_for_timeout(800)
            boxes = pg.evaluate("""()=>[...document.querySelectorAll('.decoder')].filter(e=>getComputedStyle(e).display!=='none').map(e=>{const r=e.getBoundingClientRect();return [e.className,r.left,r.top,r.right,r.bottom]})""")
            labels = pg.evaluate("""()=>[...document.querySelectorAll('.plot .ann')].filter(e=>getComputedStyle(e).display!=='none').map(e=>{const r=e.getBoundingClientRect();return [e.textContent,r.left,r.top,r.right,r.bottom]})""")
            pg.add_style_tag(content=".decoder,.plot .ann,.plot .pt,.plot .leader{visibility:hidden!important}")
            pg.wait_for_timeout(100)
            img = Image.open(io.BytesIO(pg.screenshot())).convert("L")
            for name, l, t, r, bt in boxes:
                crop = img.crop((int(l), int(t), int(r), int(bt)))
                px = list(crop.getdata()); bright = sum(1 for v in px if v > 110) / max(1, len(px))
                hit = [lab for lab, a, b2, c, d in labels if not (c < l or a > r or d < t or b2 > bt)]
                bad = bright > 0.002 or hit
                fails += bool(bad)
                print(f"{'FAIL' if bad else 'ok  '} {w}x{h} {path:4} {name.split()[0]:9} bright={bright:.4f} labels={hit}")
            for lab, l, t, r, bt in labels:
                crop = img.crop((int(l), int(t), int(r), int(bt)))
                px = list(crop.getdata()); br = sum(1 for v in px if v > 110) / max(1, len(px))
                hit = [o[0] for o in labels if o[0] != lab and not (o[3] < l or o[1] > r or o[4] < t or o[2] > bt)]
                bad = br > 0.01 or hit
                fails += bool(bad)
                if bad: print(f"FAIL {w}x{h} {path:4} label {lab!r} bright={br:.4f} overlaps={hit}")
            print(f"     {w}x{h} {path:4} {len(labels)} labels checked")
            ctx.close()
    b.close()
srv.shutdown()
sys.exit(1 if fails else 0)
