#!/usr/bin/env python3
"""Copies the chosen photos as JPEG into calendar-photos/ next to this script. The page builds the command.
Usage: python export.py 00_cover_2025-12-28_IMG_1008.jpg=IMG_1008.HEIC 01_...=... (target name = file in PHOTOS)
Optional --crop=TARGET=X,Y: where the crop sits in that photo (0 = left/top, 0.5 = middle, 1 = right/bottom), as set
by dragging the crop frame in the large view. The photos are not cropped; all crops go to calendar-photos/crops.json
(left, top, width, height as fractions of the photo) for a script that fills the photo service's project file.
Reads the photo folder from data.js, never writes to it. Works on macOS, Windows and Linux."""
import os, sys, json, subprocess
from PIL import Image, ImageOps
import pillow_heif
pillow_heif.register_heif_opener()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import outside_photos, source_path   # also switches the network off

HERE = os.path.dirname(os.path.abspath(__file__))
data = open(os.path.join(HERE, "data.js"), encoding="utf-8").read()
DATA = json.loads(data[data.index("=") + 1:data.rindex(";")])
SRC, EXTRA = DATA["src"], DATA.get("extra", {})
OUT = os.path.join(HERE, "calendar-photos")
for d in [SRC] + list(EXTRA.values()): outside_photos(OUT, d)
os.makedirs(OUT, exist_ok=True)
DOOR, COVER = 1.0, 30.5 / 21   # aspect ratios of a door and the landscape cover, as in the page's crop preview
crops = {}
for a in sys.argv[1:]:
    if a.startswith("--crop="):
        try:
            t, xy = a[len("--crop="):].rsplit("=", 1)
            x, y = (min(1.0, max(0.0, float(v))) for v in xy.split(","))
        except ValueError:
            sys.exit("Can't read " + a + ". Copy the whole command from the page's export dialog. Nothing was changed.")
        crops[t] = [x, y]
pairs = [a.split("=", 1) for a in sys.argv[1:] if not a.startswith("--crop=")]
if not pairs: sys.exit("Nothing to export. Copy the whole command from the page's export dialog.")
missing = [n for _, n in pairs if not os.path.exists(source_path(n, SRC, EXTRA))]
if missing: sys.exit("Not found in " + SRC + ": " + ", ".join(missing[:3]) + ". Nothing was changed.")
for old in os.listdir(OUT):   # an earlier export would leave a second 07_... next to the new one
    if old == "crops.json" or old[:2].isdigit() and old[2:3] == "_" and old.lower().endswith(".jpg"): os.remove(os.path.join(OUT, old))
boxes = {}
for target, name in pairs:
    im = Image.open(source_path(name, SRC, EXTRA))
    icc = im.info.get("icc_profile")
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.save(os.path.join(OUT, target), "JPEG", quality=92, icc_profile=icc)
    W, H = im.size
    a = (COVER if W > H else 1 / COVER) if target.startswith("00_cover") else DOOR
    x, y = crops.get(target, [0.5, 0.5])
    w, h = (a * H / W, 1.0) if W / H > a else (1.0, W / a / H)
    boxes[target] = {"left": round((1 - w) * x, 4), "top": round((1 - h) * y, 4), "width": round(w, 4), "height": round(h, 4)}
    print("ok", target, flush=True)
with open(os.path.join(OUT, "crops.json"), "w", encoding="utf-8") as f:
    json.dump(boxes, f, indent=1)
print(len(pairs), "photos in", OUT)
try:   # showing the folder is a convenience; the photos are written either way
    if sys.platform == "win32": os.startfile(OUT)
    elif sys.platform == "darwin": subprocess.run(["open", OUT])
    else: subprocess.run(["xdg-open", OUT])
except OSError:
    pass
