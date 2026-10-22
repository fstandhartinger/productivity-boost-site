"""Label placement search/check for the hero waterfall on phones.
Renders the static waterfall (reduced motion) with labels hidden, then for each phone label scores candidate
positions by the share of bright signal pixels under the label box, worst case over phone sizes and EN/DE.
usage: place.py search | place.py check"""
import sys, os, threading, http.server, socketserver, functools, io, json
from playwright.sync_api import sync_playwright
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(Q, directory=os.path.join(ROOT, "site"))); threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"
DESK = os.environ.get("MODE") == "desk"
VIEWS = [(1024, 768), (1280, 720), (1366, 768), (1440, 900), (1536, 864), (1680, 1050), (1920, 1080)] if DESK else [(360, 640), (390, 844), (412, 915)]
data = []
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h in VIEWS:
        for path in ("/", "/de/"):
            ctx = b.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce"); pg = ctx.new_page()
            pg.goto(base + path); pg.wait_for_timeout(700)
            info = pg.evaluate("""()=>{const pl=document.querySelector('.plot');pl.scrollIntoView({block:'center'});const r=pl.getBoundingClientRect();
              const labs=[...pl.querySelectorAll('.ann')].filter(e=>getComputedStyle(e).display!=='none').map(e=>{const b=e.getBoundingClientRect();const k=[...e.classList].find(c=>c.startsWith('k-')).slice(2);
                const pt=pl.querySelector('.pt.k-'+k).getBoundingClientRect();return {k,w:b.width,h:b.height,l:b.left-r.left,t:b.top-r.top,px:pt.left+pt.width/2-r.left,py:pt.top+pt.height/2-r.top}});
              const dec=pl.querySelector('.decoder');let win=null;if(dec&&getComputedStyle(dec).display!=='none'){const b=dec.getBoundingClientRect();win=[b.left-r.left,b.top-r.top,b.right-r.left,b.bottom-r.top]}
              return {W:r.width,H:r.height,labs,win}}""")
            pg.add_style_tag(content=".plot .ann,.plot .pt,.plot .leader,.decoder{visibility:hidden!important}")
            pg.wait_for_timeout(100)
            r = pg.evaluate("()=>{const r=document.querySelector('.plot').getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]}")
            img = Image.open(io.BytesIO(pg.screenshot(clip={"x": r[0], "y": r[1], "width": r[2] - r[0], "height": r[3] - r[1]}))).convert("L")
            data.append({"view": f"{w}x{h}{path}", "img": img, **info})
            ctx.close()
    b.close()
srv.shutdown()

def bright(img, box):
    l, t, r, bt = [int(round(v)) for v in box]
    if l < 0 or t < 0 or r > img.width or bt > img.height:
        return 9.0
    px = img.crop((l, t, r, bt)).getdata()
    return sum(1 for v in px if v > 110) / max(1, len(px))

def overlap(a, b, pad=3):
    return not (a[2] + pad < b[0] or b[2] + pad < a[0] or a[3] + pad < b[1] or b[3] + pad < a[1])

if sys.argv[1:] == ["check"]:
    fails = 0
    for d in data:
        boxes = [(L["k"], (L["l"], L["t"], L["l"] + L["w"], L["t"] + L["h"])) for L in d["labs"]]
        for k, bx in boxes:
            br = bright(d["img"], bx)
            hit = [k2 for k2, b2 in boxes if k2 != k and overlap(bx, b2, 0)]
            bad = br > 0.01 or hit
            fails += bool(bad)
            print(f"{'FAIL' if bad else 'ok  '} {d['view']:12} {k:6} bright={br:.4f} overlaps={hit}")
    sys.exit(1 if fails else 0)

# search: greedy, worst case over all views
order = os.environ.get("ORDER", "reax,jev,ralph,rdvr,games").split(",")
keys = [L["k"] for L in data[0]["labs"]]
placed = {}
def fixed_boxes(d):
    out = [(L["l"], L["t"], L["l"] + L["w"], L["t"] + L["h"]) for L in d["labs"] if L["k"] not in order]
    if d.get("win"): out.append(tuple(d["win"]))
    return out
for k in [o for o in order if o in keys]:
    best = None
    cands = [(a, float(x)) for a, x in (c.split(":") for c in os.environ[f"CANDS_{k}"].split(","))] if os.environ.get(f"CANDS_{k}") else \
        [("start", x) for x in (1.5, 2.5, 4, 6)] + [("end", x) for x in (-1.5, -2.5, -4, -6)]
    for anchor, dx in cands:
        if True:
            for dy in range(-30, 46):
                worst = 0; ok = True
                for d in data:
                    L = next(x for x in d["labs"] if x["k"] == k)
                    xa = L["px"] + dx / 100 * d["W"]; yc = L["py"] + dy / 100 * d["H"]
                    bx = (xa, yc - L["h"] / 2, xa + L["w"], yc + L["h"] / 2) if anchor == "start" else (xa - L["w"], yc - L["h"] / 2, xa, yc + L["h"] / 2)
                    if bx[0] < 2 or bx[2] > d["W"] - 2 or bx[1] < 2 or bx[3] > d["H"] - 2: ok = False; break
                    if any(overlap(bx, fb, 4) for fb in fixed_boxes(d)): ok = False; break
                    for k2, (a2, dx2, dy2) in placed.items():
                        L2 = next(x for x in d["labs"] if x["k"] == k2)
                        xb = L2["px"] + dx2 / 100 * d["W"]; yb = L2["py"] + dy2 / 100 * d["H"]
                        b2 = (xb, yb - L2["h"] / 2, xb + L2["w"], yb + L2["h"] / 2) if a2 == "start" else (xb - L2["w"], yb - L2["h"] / 2, xb, yb + L2["h"] / 2)
                        if overlap(bx, b2, 4): ok = False; break
                    if not ok: break
                    worst = max(worst, bright(d["img"], bx))
                if not ok: continue
                score = worst * 100 + abs(dy) * float(os.environ.get('DYW', '0.02')) + abs(dx) * 0.05
                if os.environ.get('DEBUG') == k: print(anchor, dx, dy, round(worst, 4))
                if best is None or score < best[0]:
                    best = (score, worst, anchor, dx, dy)
    print(k, best)
    if best: placed[k] = (best[2], best[3], best[4])
print(json.dumps({k: (v[1], v[2], v[0]) for k, v in placed.items()}))
