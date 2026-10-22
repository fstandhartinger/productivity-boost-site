"""Round-2 asset pipeline: product screenshot crops, graded old-site images, duotone portrait -> src/img (AVIF + WebP).
Usage: python3 -I tools/assets_r2.py <job-media-r2-dir>   (dir contains live/ and img/)"""
import json, os, subprocess, sys
from PIL import Image, ImageEnhance, ImageOps

MEDIA = sys.argv[1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "src", "img")
os.makedirs(OUT, exist_ok=True)
manifest = {}

def avif(png, dst, crf=33):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", png, "-c:v", "libaom-av1", "-still-picture", "1",
                    "-crf", str(crf), "-b:v", "0", "-pix_fmt", "yuv420p", dst], check=True)

def emit(name, im, widths, crf=33, q=80):
    im = im.convert("RGB")
    ws = [w for w in widths if w <= im.width] or [im.width]
    for w in ws:
        h = round(im.height * w / im.width)
        r = im.resize((w, h), Image.LANCZOS)
        r.save(f"{OUT}/{name}-{w}.webp", quality=q, method=6)
        tmp = f"/tmp/_a_{name}-{w}.png"
        r.save(tmp)
        avif(tmp, f"{OUT}/{name}-{w}.avif", crf)
        os.remove(tmp)
    manifest[name] = {"widths": ws, "w": ws[-1], "h": round(im.height * ws[-1] / im.width)}

def live(fn):
    return Image.open(os.path.join(MEDIA, "live", fn))

# ---- product screens (desktop sources are 2x of 1440x900; mobile 3x of 390x844) ----
S = 2
crops = {
    "dm-desk-light": ("decisionmodels-desktop-light.png", (0, 0, 1440, 640)),
    "dm-desk-dark": ("decisionmodels-desktop-dark.png", (0, 0, 1440, 640)),
    "reax-desk": ("reax-desktop-dark.png", (0, 0, 1440, 820)),
    "mine-desk-light": ("mine-desktop-light.png", (0, 0, 1440, 800)),
    "mine-desk-dark": ("mine-desktop-dark.png", (0, 0, 1440, 800)),
    "jev-desk-light": ("jevbench-desktop-light.png", (0, 0, 1440, 900)),
    "jev-desk-dark": ("jevbench-desktop-dark.png", (0, 0, 1440, 900)),
}
for name, (fn, box) in crops.items():
    im = live(fn).crop(tuple(v * S for v in box))
    emit(name, im, [640, 960, 1440, 2000])
mcrops = {
    "dm-mob-light": "decisionmodels-mobile-light.png", "dm-mob-dark": "decisionmodels-mobile-dark.png",
    "reax-mob": "reax-mobile-dark.png", "mine-mob-light": "mine-mobile-light.png", "mine-mob-dark": "mine-mobile-dark.png",
}
for name, fn in mcrops.items():
    im = live(fn)
    im = im.crop((0, 0, im.width, round(im.width * 1.6)))  # 390 x 624 css
    emit(name, im, [390, 600, 780])

# ---- old-site images: one shared grade (matte, slightly desaturated) ----
man = json.load(open(os.path.join(MEDIA, "img", "manifest.json")))
for m in man:
    n = m["name"]
    src = os.path.join(MEDIA, "img", f"{n}-{m['widths'][-1]}.webp")
    im = Image.open(src).convert("RGB")
    if n == "portrait":
        g = ImageOps.grayscale(im)
        g = ImageOps.autocontrast(g, cutoff=1)
        duo = ImageOps.colorize(g, black="#15171a", white="#efeee8", mid="#7d8a84")
        emit("portrait", duo, [400, 800], crf=30)
        continue
    im = ImageEnhance.Color(im).enhance(0.85)
    im = ImageEnhance.Contrast(im).enhance(0.94)
    im = Image.blend(im, Image.new("RGB", im.size, (236, 234, 226)), 0.04)
    emit("old-" + n, im, [480, 800, 1200])
    manifest["old-" + n]["alt_en"] = m.get("alt_en", "")
    manifest["old-" + n]["alt_de"] = m.get("alt_de", "")

json.dump(manifest, open(os.path.join(ROOT, "src", "data", "img.json"), "w"), indent=1)
print(len(manifest), "images")
