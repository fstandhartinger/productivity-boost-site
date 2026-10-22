import os, subprocess
from PIL import Image
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "img")
def emit(man, name, im, widths, crf=33, q=80):
    ws = [w for w in widths if w <= im.width] or [im.width]
    for w in ws:
        r = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
        r.save(f"{OUT}/{name}-{w}.webp", quality=q, method=6)
        tmp = f"/tmp/_x_{name}-{w}.png"; r.save(tmp)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", tmp, "-c:v", "libaom-av1", "-still-picture", "1", "-crf", str(crf), "-b:v", "0", "-pix_fmt", "yuv420p", f"{OUT}/{name}-{w}.avif"], check=True)
        os.remove(tmp)
    man[name] = {"widths": ws, "w": ws[-1], "h": round(im.height * ws[-1] / im.width)}
