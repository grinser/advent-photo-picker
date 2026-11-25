#!/usr/bin/env python3
"""Copies the chosen photos as JPEG into calendar-photos/ next to this script. The page builds the command.
Usage: python export.py 00_cover_2025-12-28_IMG_1008.jpg=IMG_1008.HEIC 01_...=... (target name = file in PHOTOS)
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
pairs = [a.split("=", 1) for a in sys.argv[1:]]
if not pairs: sys.exit("Nothing to export. Copy the whole command from the page's export dialog.")
missing = [n for _, n in pairs if not os.path.exists(source_path(n, SRC, EXTRA))]
if missing: sys.exit("Not found in " + SRC + ": " + ", ".join(missing[:3]) + ". Nothing was changed.")
for old in os.listdir(OUT):   # an earlier export would leave a second 07_... next to the new one
    if old[:2].isdigit() and old[2:3] == "_" and old.lower().endswith(".jpg"): os.remove(os.path.join(OUT, old))
for target, name in pairs:
    im = Image.open(source_path(name, SRC, EXTRA))
    icc = im.info.get("icc_profile")
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.save(os.path.join(OUT, target), "JPEG", quality=92, icc_profile=icc)
    print("ok", target, flush=True)
print(len(pairs), "photos in", OUT)
try:   # showing the folder is a convenience; the photos are written either way
    if sys.platform == "win32": os.startfile(OUT)
    elif sys.platform == "darwin": subprocess.run(["open", OUT])
    else: subprocess.run(["xdg-open", OUT])
except OSError:
    pass
