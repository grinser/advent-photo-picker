#!/usr/bin/env python3
"""Step 1: read every photo once, write previews, measure sharpness, brightness and faces. Local. Can be resumed."""
import os, sys, json, time, calendar, datetime, base64
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")   # hides "Targets are not supported" warnings
import numpy as np, cv2
from PIL import Image, ImageOps
import pillow_heif
pillow_heif.register_heif_opener()
from multiprocessing import Pool
from common import photos_dir, need_models, progress, outside_photos, interactive, ask

OUT = os.path.dirname(os.path.abspath(__file__))
SRC = photos_dir()
outside_photos(OUT, SRC)
# START: first day to include (YYYY-MM-DD), default one year back
START_FILE = os.path.join(OUT, "work", "start.txt")
START = os.environ.get("START", "").strip().strip('"')
if not START and os.path.exists(START_FILE): START = open(START_FILE).read().strip()   # same as last run
if not START and interactive():
    START = ask("First day to include, as 2025-12-01. Press Enter for the last 365 days:\n> ").strip()
START = START or (datetime.date.today() - datetime.timedelta(days=365)).isoformat()
os.environ["START"] = START   # worker processes inherit it
try:
    START_T = calendar.timegm(time.strptime(START, "%Y-%m-%d"))
except ValueError:
    sys.exit("START must look like 2025-12-01, not " + START)
EXT = {".heic", ".jpg", ".jpeg", ".png"}
RES = os.path.join(OUT, "work", "results.jsonl")
det = rec = None

def init():
    global det, rec
    cv2.setNumThreads(1)
    det = cv2.FaceDetectorYN.create(os.path.join(OUT, "models", "yunet.onnx"), "", (320, 320), 0.5, 0.3, 50)   # weak hits only count for the "no people" filter
    rec = cv2.FaceRecognizerSF.create(os.path.join(OUT, "models", "sface.onnx"), "")

def dms(v, ref):
    try:
        d = float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600
        return -d if ref in ("S", "W") else d
    except Exception:
        return None

def work(name):
    r = {"f": name}
    try:
        p = os.path.join(SRC, name)
        st = os.stat(p)
        im = Image.open(p)
        ex = im.getexif()
        dto = None
        try:
            dto = ex.get_ifd(0x8769).get(36867)
        except Exception:
            pass
        t = None
        if dto:
            try:
                t = calendar.timegm(time.strptime(str(dto)[:19], "%Y:%m:%d %H:%M:%S"))
            except Exception:
                t = None
        if t is None:
            loc = datetime.datetime.fromtimestamp(st.st_mtime)
            t = calendar.timegm(loc.timetuple()); r["nodate"] = 1
        r["t"] = t
        if t < START_T:
            r["skip"] = 1; return r
        r["cam"] = 1 if ex.get(271) else 0
        try:
            g = ex.get_ifd(0x8825)
            la, lo = dms(g.get(2), g.get(1)), dms(g.get(4), g.get(3))
            if la is not None and lo is not None and (abs(la) > 0.01 or abs(lo) > 0.01):
                r["la"], r["lo"] = round(la, 5), round(lo, 5)
        except Exception:
            pass
        if im.format == "JPEG":
            im.draft("RGB", (2400, 2400))
        im = ImageOps.exif_transpose(im).convert("RGB")
        r["w"], r["h"] = im.size
        im.thumbnail((1600, 1600), Image.LANCZOS)
        if "/" in name:   # photo from a subfolder: previews mirror the folders
            for d in ("prev", "thumbs"): os.makedirs(os.path.join(OUT, d, os.path.dirname(name)), exist_ok=True)
        im.save(os.path.join(OUT, "prev", name + ".jpg"), quality=80)
        a = np.asarray(im)
        th = im.copy(); th.thumbnail((360, 360)); th.save(os.path.join(OUT, "thumbs", name + ".jpg"), quality=72)
        bgr = cv2.cvtColor(a, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        s = 640 / max(gray.shape)
        g = cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else gray
        lap = cv2.Laplacian(g, cv2.CV_64F)
        H, W = lap.shape
        tiles = [lap[y * H // 4:(y + 1) * H // 4, x * W // 4:(x + 1) * W // 4].var() for y in range(4) for x in range(4)]
        r["sh"] = round(float(lap.var()), 1); r["shm"] = round(float(max(tiles)), 1)
        r["br"] = round(float(g.mean()), 1)
        r["dk"] = round(float((g < 20).mean()), 3); r["bl"] = round(float((g > 245).mean()), 3)
        d = cv2.resize(g, (9, 8), interpolation=cv2.INTER_AREA)
        bits = (d[:, 1:] > d[:, :-1]).flatten()
        r["dh"] = "%016x" % int("".join("1" if b else "0" for b in bits), 2)
        faces = []
        if not name.lower().endswith(".png"):
            det.setInputSize((bgr.shape[1], bgr.shape[0]))
            _, fs = det.detect(bgr)
            if fs is not None:
                r["nlo"] = len(fs)   # every hit from 0.5 on; faces below 0.8 are not kept
                for f in [f for f in fs if f[14] >= 0.8][:12]:
                    x, y, w, h = [float(v) for v in f[:4]]
                    fd = {"b": [int(x), int(y), int(w), int(h)], "c": round(float(f[14]), 2)}
                    if min(w, h) >= 56:
                        e = rec.feature(rec.alignCrop(bgr, f)).flatten()
                        e = e / (np.linalg.norm(e) + 1e-9)
                        fd["e"] = base64.b64encode(e.astype(np.float16).tobytes()).decode()
                    faces.append(fd)
        r["fa"] = faces
    except Exception as e:
        r["err"] = str(e)[:120]
    return r

def photo_files():
    """Photos in SRC and its subfolders, as paths relative to SRC with / as separator."""
    for d, dirs, files in os.walk(SRC):
        # skip hidden folders and photo libraries, whose inner copies would show up twice
        dirs[:] = sorted(x for x in dirs if not x.startswith(".") and not x.endswith((".photoslibrary", ".photolibrary")))
        rel = os.path.relpath(d, SRC).replace(os.sep, "/")
        for f in files:
            if os.path.splitext(f)[1].lower() in EXT and not f.startswith("._"):
                yield f if rel == "." else rel + "/" + f

def main():
    need_models("yunet.onnx", "sface.onnx")
    for d in ("prev", "thumbs", "work"): os.makedirs(os.path.join(OUT, d), exist_ok=True)
    saved = os.path.join(OUT, "work", "photos.txt")
    if os.path.exists(RES) and os.path.exists(saved) and open(saved, encoding="utf-8").read().strip() != SRC:
        sys.exit("The work folder belongs to " + open(saved, encoding="utf-8").read().strip() +
                 ". To start over with " + SRC + ", delete the folders work, prev and thumbs first.")
    budget = float(os.environ.get("BUDGET", "1e9")); t0 = time.time()
    done = set()
    if os.path.exists(RES):
        for l in open(RES):
            try: done.add(json.loads(l)["f"])
            except Exception: pass
    pre = START_T - 20 * 86400
    found = list(photo_files())
    names = sorted(f for f in found if f not in done and os.path.getmtime(os.path.join(SRC, f)) >= pre)
    total = len(names) + len(done)
    if not total:
        sys.exit("No photos from " + START + " on in " + SRC + "." + (
            " The folder has %d older photos. Check START." % len(found) if found else " Check the folder."))
    open(saved, "w", encoding="utf-8").write(SRC)
    open(START_FILE, "w").write(START)
    print("%d photos in %s from %s on, %d done earlier." % (total, SRC, START, len(done)))
    n = len(done)
    with open(RES, "a") as out, Pool(4, init) as pool:
        for r in pool.imap_unordered(work, names, chunksize=4):
            out.write(json.dumps(r) + "\n"); out.flush(); n += 1
            if n % 20 == 0: progress(n - len(done), total - len(done), t0, time.time())
            if time.time() - t0 > budget:
                pool.terminate(); break
    print()
    bad = []
    for l in open(RES):
        try: r = json.loads(l)
        except Exception: continue
        if r.get("err"): bad.append(r["f"])
    if n < total:
        print("Stopped at %d of %d. Run  python process.py  again to continue." % (n, total))
    else:
        print("Done: %d photos read%s. Next:  python arc.py" % (n, ", %d could not be read (%s%s)" % (
            len(bad), ", ".join(bad[:3]), ", ..." if len(bad) > 3 else "") if bad else ""))

if __name__ == "__main__":
    main()
