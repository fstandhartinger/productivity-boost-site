"""Build-time asset pipeline: responsive AVIF/WebP, the VR loop, waterfall images, hop slices, dot plot, OG images.
Usage: python3 -I tools/assets.py <job-media-dir>   (writes site/img + src/data/assets.json)"""
import json, os, subprocess, sys, random, math
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA = sys.argv[1]
IMG = os.path.join(ROOT, "site", "img"); os.makedirs(IMG, exist_ok=True)
TMP = "/tmp/pbsite"; os.makedirs(TMP, exist_ok=True)
manifest = {"_v": "1"}

def avif(src_png, dst, crf=34):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src_png, "-c:v", "libaom-av1", "-still-picture", "1",
                    "-crf", str(crf), "-b:v", "0", "-cpu-used", "4", "-pix_fmt", "yuv420p", dst], check=True)

def responsive(name, im, widths, crf=34, q=78):
    base = name
    for w in widths:
        h = round(im.height * w / im.width)
        r = im.resize((w, h), Image.LANCZOS).convert("RGB")
        p = f"{TMP}/{base}-{w}.png"; r.save(p)
        avif(p, f"{IMG}/{base}-{w}.avif", crf)
        r.save(f"{IMG}/{base}-{w}.webp", "WEBP", quality=q, method=6)
    manifest[name] = {"base": base, "widths": widths, "w": im.width, "h": im.height}

# --- portrait (Florian's own photo from his old site) ---
pt = Image.open(os.path.join(MEDIA, "orig", "150daa_335ae049b7564c96ab065fd64489ea45~mv2.jpg"))
responsive("portrait", pt.crop((1200, 100, 2300, 1475)), [320, 480, 640], crf=36)
responsive("portrait-sq", pt.crop((1080, 160, 2340, 1420)), [104, 156], crf=36)
# --- the portrait as a received SSTV picture (Robot-36-like): slant, line jitter, chroma smear, noise, header bar ---
def sstv_image(src, w, h, seed=36):
    import random as _r
    from PIL import ImageFilter, ImageDraw, ImageFont
    rnd = _r.Random(seed)
    im = src.resize((w, h), Image.LANCZOS).convert("YCbCr")
    Y, Cb, Cr = im.split()
    # chroma at quarter resolution, smeared horizontally (SSTV sends colour at lower resolution)
    from PIL import ImageChops
    Cb = ImageChops.offset(Cb.resize((w // 5, h // 2), Image.BILINEAR).resize((w, h), Image.BILINEAR).filter(ImageFilter.BoxBlur(1)), 3, 0)
    Cr = ImageChops.offset(Cr.resize((w // 5, h // 2), Image.BILINEAR).resize((w, h), Image.BILINEAR).filter(ImageFilter.BoxBlur(1)), -2, 0)
    rgb = Image.merge("YCbCr", (Y, Cb, Cr)).convert("RGB")
    out = Image.new("RGB", (w, h), (8, 9, 13))
    px = rgb.load(); po = out.load()
    for y in range(h):
        shift = y * 0.05 + (rnd.random() - 0.5) * (5 if rnd.random() < 0.06 else 1.2)  # visible slant + line jitter
        bright = (0.8 if y % 2 else 1.0) * (0.92 + 0.08 * rnd.random())  # scan lines
        for x in range(w):
            sx = int(x - shift)
            if 0 <= sx < w:
                r, g, b = px[sx, y]
                n = (rnd.random() - 0.5) * 30
                po[x, y] = (max(0, min(255, int(r * bright + n))), max(0, min(255, int(g * bright + n))), max(0, min(255, int(b * bright + n))))
    # the last lines arrive noisy (signal fading out), like a real reception
    for y in range(int(h * 0.955), h):
        for x in range(w):
            v = int(rnd.random() * 70)
            po[x, y] = (v // 2, v, v // 2 + 10)
    d = ImageDraw.Draw(out)
    d.rectangle([0, 0, w, int(h * 0.085)], fill=(8, 9, 13))
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", max(11, w // 24))
    except Exception:
        f = None
    d.text((6, 3), "RX ROBOT36 21.10.26 JN68", fill=(255, 214, 130), font=f)
    return out

pt_crop = pt.crop((900, 200, 2352, 1289))  # 4:3 landscape, face right of centre like the original framing
frame = sstv_image(pt_crop, 320, 240)      # Robot 36 is 320x240
frame.save(f"{TMP}/sstv-320.png"); avif(f"{TMP}/sstv-320.png", f"{IMG}/sstv-320.avif", 24)
face = sstv_image(pt.crop((1080, 160, 2340, 1420)), 120, 120, seed=7)  # phone avatar, same reception
face.save(f"{IMG}/sstv-face-120.webp", "WEBP", quality=85, method=6); face.save(f"{TMP}/sf.png"); avif(f"{TMP}/sf.png", f"{IMG}/sstv-face-120.avif", 28)
manifest["sstv-face"] = {"base": "sstv-face", "widths": [120], "w": 120, "h": 120}
frame.save(f"{IMG}/sstv-320.webp", "WEBP", quality=90, method=6)
big = frame.resize((640, 480), Image.NEAREST)  # the receiver's pixels, doubled
big.save(f"{TMP}/sstv-640.png"); avif(f"{TMP}/sstv-640.png", f"{IMG}/sstv-640.avif", 26)
big.save(f"{IMG}/sstv-640.webp", "WEBP", quality=88, method=6)
manifest["sstv"] = {"base": "sstv", "widths": [320, 640], "w": 640, "h": 480}

# --- Rewind Recorder (own product mock-up) ---
rw = Image.open(os.path.join(MEDIA, "orig", "150daa_b4a13be7a747483b87229adc4be48315~mv2.png"))
responsive("rwrec", rw, [480, 800], crf=34)
# --- Room Designer VR: poster + 6 s silent loop from its own Steam trailer ---
steam = "/home/flori/jobs/productivity-boost-website-20261021/workers/research/media/steam"
ss2 = Image.open(os.path.join(steam, "ss2.jpg"))
responsive("rdvr", ss2, [480, 800, 1200], crf=34)
tr = os.path.join(steam, "trailer_720p.mp4")
if os.path.exists(tr):
    # two shots from Florian's own trailer: draw the floor plan (26 s), then stand in the furnished room (155 s)
    crop = "crop=iw:ih*0.76:0:ih*0.12,scale=640:-2"
    fc = (f"[0:v]trim=start=155:end=158.5,setpts=PTS-STARTPTS,{crop},fps=24[a];"
          f"[0:v]trim=start=27.6:end=31.1,setpts=PTS-STARTPTS,{crop},fps=24[b];[a][b]concat=n=2:v=1:a=0[v]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", tr, "-filter_complex", fc, "-map", "[v]", "-an",
                    "-c:v", "libx264", "-profile:v", "main", "-crf", "30", "-preset", "slow", "-movflags", "+faststart", "-pix_fmt", "yuv420p", f"{IMG}/rdvr-loop.mp4"], check=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", tr, "-filter_complex", fc, "-map", "[v]", "-an",
                    "-c:v", "libvpx-vp9", "-crf", "40", "-b:v", "0", "-row-mt", "1", f"{IMG}/rdvr-loop.webm"], check=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "155.2", "-i", tr, "-frames:v", "1", "-vf", crop, f"{TMP}/poster.png"], check=True)
    pim = Image.open(f"{TMP}/poster.png"); pim.convert("RGB").save(f"{IMG}/rdvr-poster.webp", "WEBP", quality=72, method=6)
    manifest["rdvr_loop"] = {"mp4": "rdvr-loop.mp4", "webm": "rdvr-loop.webm", "poster": "rdvr-poster.webp", "w": pim.width, "h": pim.height}

# --- noise tile ---
rnd = random.Random(7); n = Image.new("L", (96, 96))
n.putdata([int(10 + 46 * rnd.random() ** 2) for _ in range(96 * 96)])
Image.merge("RGB", (n.point(lambda v: 5 + v // 4), n.point(lambda v: 5 + v // 5), n.point(lambda v: 9 + v // 4))).save(f"{IMG}/noise.webp", "WEBP", quality=60, method=6)

# --- waterfall: final frame (desktop + phone), hop slices ---
STF = {"worlds": 88.7, "systems": 91.4, "agents": 93.9, "studio": 96.6, "networks": 99.2, "benchmarks": 102.5, "decisions": 105.8}
HOPS = [("decisions", "benchmarks", "2026-10", "2026-01"), ("benchmarks", "networks", "2026-10", "2025-09"), ("networks", "studio", "2026-10", "2025-09"),
        ("studio", "agents", "2026-10", "2025-12"), ("agents", "systems", "2026-10", "2024"), ("systems", "worlds", "2019", "2014")]
jobs = [(f"{TMP}/wf-d.png", "mode=full&w=1600&h=520"), (f"{TMP}/wf-m.png", "mode=full&w=480&h=480"), (f"{TMP}/og-wf.png", "mode=full&w=560&h=630")]
for a, b, r0, r1 in HOPS:
    f0, f1 = sorted([STF[a], STF[b]]); f0 -= 0.9; f1 += 0.9
    jobs.append((f"{TMP}/hop-{a}-{b}.png", f"mode=crop&w=520&h=150&f0={f0}&f1={f1}&r0={r0}&r1={r1}&st={a},{b}"))
subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tools", "render.py"), ROOT, json.dumps(jobs)], check=True)
for k in ("d", "m"):
    im = Image.open(f"{TMP}/wf-{k}.png").convert("RGB"); im.save(f"{TMP}/wf-{k}-rgb.png")
    avif(f"{TMP}/wf-{k}-rgb.png", f"{IMG}/wf-{k}.avif", 38)
    im.save(f"{IMG}/wf-{k}.webp", "WEBP", quality=70, method=6)
manifest["wf"] = {"base": "wf", "mw": 480, "mh": 480, "dw": 1600, "dh": 520}
for a, b, _, _ in HOPS:
    im = Image.open(f"{TMP}/hop-{a}-{b}.png").convert("RGB")
    im.save(f"{IMG}/hop-{a}-{b}.webp", "WEBP", quality=72, method=6)
    manifest[f"hop-{a}-{b}"] = {"file": f"hop-{a}-{b}.webp", "w": im.width, "h": im.height}

# --- receiver monitors: screenshots of his own live products (Playwright, 1280x800 @1.5x, 22 Oct 2026), top 936 px ---
for k in ("decisions", "benchmarks", "networks", "agents"):
    src = os.path.join(MEDIA, "rx", f"{k}.png")
    if os.path.exists(src):
        responsive(f"rx-{k}", Image.open(src).convert("RGB").crop((0, 0, 1920, 936)), [480, 800, 1200], crf=32, q=80)

# --- JevBench dot plot (public board, 21 Oct 2026), inline SVG ---
rows = json.load(open(os.path.join(ROOT, "src", "data", "jevbench_intel.json")))
import re as _re
pairs = sorted((float(_re.match(r"[0-9.]+", r[1]).group(0)), "below" in r[1]) for r in rows if _re.match(r"[0-9.]+", r[1]))
vals = [v for v, _ in pairs]
lo, hi = 0, 100
bins = {}
dots = []
for v, below in pairs:
    b = int((v - lo) / (hi - lo) * 68)
    k = bins.get(b, 0); bins[b] = k + 1
    x = 14 + (v - lo) / (hi - lo) * 272
    y = 112 - k * 4.6
    dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.9"' + (' fill="none" stroke="currentColor" stroke-width=".7" opacity=".6"/>' if below else '/>'))
axis = "".join(f'<text x="{14 + t / 100 * 272:.1f}" y="128" text-anchor="middle">{t}</text>' for t in (0, 25, 50, 75, 100))
top = int(112 - max(bins.values()) * 4.6 - 10)  # crop the empty sky above the tallest stack
svg = (f'<svg class="dots" viewBox="0 {top} 300 {134 - top}" aria-hidden="true"><line x1="14" y1="116" x2="286" y2="116" stroke="#8E97A8" stroke-width=".6"/>'
       f'<g fill="currentColor" fill-opacity=".9">{"".join(dots)}</g><g font-family="ui-monospace,monospace" font-size="7" fill="#8E97A8">{axis}</g></svg>')
manifest["jevdots"] = {"svg": svg, "n": len(vals), "max": max(vals), "min": min(vals)}
print("jevbench n", len(vals), "range", min(vals), max(vals), "tallest bin", max(bins.values()))

# --- OG images (EN/DE) ---
import shutil, threading, http.server, socketserver, functools, urllib.parse
from playwright.sync_api import sync_playwright
shutil.copy(f"{TMP}/og-wf.png", os.path.join(ROOT, "tmp-og-wf.png"))
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Q, directory=ROOT)); threading.Thread(target=srv.serve_forever, daemon=True).start()
og = {"en": ("Florian Standhartinger · Passau · coding since 1987", "I build AI.", "I just can’t stay on one station.", "Self-portrait, 1987–2026"),
      "de": ("Florian Standhartinger · Passau · programmiert seit 1987", "Ich baue KI.", "Und wechsle ständig den Sender.", "Selbstporträt, 1987–2026")}
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 630})
    for lg, (k, a, bb, t) in og.items():
        pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/tools/og.html?" + urllib.parse.urlencode({"k": k, "a": a, "b": bb, "t": t})); pg.wait_for_timeout(500)
        pg.screenshot(path=f"{TMP}/og-{lg}.png"); Image.open(f"{TMP}/og-{lg}.png").convert("RGB").save(f"{IMG}/og-{lg}.jpg", "JPEG", quality=86, optimize=True, progressive=True)
    b.close()
srv.shutdown(); os.remove(os.path.join(ROOT, "tmp-og-wf.png"))
json.dump(manifest, open(os.path.join(ROOT, "src", "data", "assets.json"), "w"), indent=1)
print("assets ok")
