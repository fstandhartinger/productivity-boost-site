"""X post images + new portrait -> src/img. Usage: python3 -I tools/xposts_r2.py <media/r2/x dir>"""
import json, os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
X = sys.argv[1]; ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("a", os.path.join(ROOT, "tools", "assets_r2_lib.py")); a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
man = json.load(open(os.path.join(ROOT, "src", "data", "img.json")))
im = Image.open(f"{X}/dm-launch.jpg").convert("RGB")
a.emit(man, "x-dm-launch", im, [480, 800, 1200])
a.emit(man, "portrait2", im.crop((190, 0, 730, 675)), [400, 540])
j = Image.open(f"{X}/jevbench.jpg").convert("RGB")
a.emit(man, "x-jevbench", j.crop((0, 0, 2100, 1181)), [480, 800, 1200])
json.dump(man, open(os.path.join(ROOT, "src", "data", "img.json"), "w"), indent=1)
print("ok")
