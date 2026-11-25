#!/usr/bin/env python3
"""Browser speed spike, step 2: run the Python steps of process.py on the test set.

Same work as process.py per picture (EXIF, preview and thumbnail, sharpness, brightness, dHash, YuNet,
SFace), with the same Pool(4). It prints the time per picture and writes testset/reference.json, which
the browser page uses to check that it finds the same faces. Reads only the synthetic test set.
Run it from the repo root:  python spike/browser-speed/reference.py
"""
import os, sys, json, time, base64, tempfile
from multiprocessing import Pool
import numpy as np, cv2
from PIL import Image, ImageOps
import pillow_heif
pillow_heif.register_heif_opener()

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SET = os.path.join(HERE, "testset")
TMP = tempfile.mkdtemp(prefix="spike-prev-")
det = rec = None


def init():
    global det, rec
    cv2.setNumThreads(1)
    det = cv2.FaceDetectorYN.create(os.path.join(ROOT, "models", "yunet.onnx"), "", (320, 320), 0.5, 0.3, 50)
    rec = cv2.FaceRecognizerSF.create(os.path.join(ROOT, "models", "sface.onnx"), "")


def work(rel):
    """A copy of process.work() without the date filter, timed per stage."""
    T = {}; t = time.perf_counter()
    def lap(k):
        nonlocal t
        now = time.perf_counter(); T[k] = T.get(k, 0) + (now - t) * 1000; t = now
    im = Image.open(os.path.join(SET, rel)); ex = im.getexif()
    dto = ex.get_ifd(0x8769).get(36867); cam = ex.get(271); gps = ex.get_ifd(0x8825).get(2)
    lap("exif")
    if im.format == "JPEG": im.draft("RGB", (2400, 2400))
    im = ImageOps.exif_transpose(im).convert("RGB")
    lap("decode")
    im.thumbnail((1600, 1600), Image.LANCZOS)
    lap("resize")
    name = rel.replace("/", "_")
    im.save(os.path.join(TMP, name + ".jpg"), quality=80)
    th = im.copy(); th.thumbnail((360, 360)); th.save(os.path.join(TMP, name + "_t.jpg"), quality=72)
    lap("save")
    a = np.asarray(im); bgr = cv2.cvtColor(a, cv2.COLOR_RGB2BGR); gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    s = 640 / max(gray.shape)
    g = cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else gray
    lp = cv2.Laplacian(g, cv2.CV_64F)
    sh = float(lp.var()); br = float(g.mean())
    d = cv2.resize(g, (9, 8), interpolation=cv2.INTER_AREA)
    dh = "%016x" % int("".join("1" if b else "0" for b in (d[:, 1:] > d[:, :-1]).flatten()), 2)
    lap("measure")
    det.setInputSize((bgr.shape[1], bgr.shape[0]))
    _, fs = det.detect(bgr)
    lap("detect")
    faces = []
    for f in ([] if fs is None else [f for f in fs if f[14] >= 0.8][:12]):
        x, y, w, h = [float(v) for v in f[:4]]
        fd = {"b": [round(x, 1), round(y, 1), round(w, 1), round(h, 1)], "c": round(float(f[14]), 3)}
        if min(w, h) >= 56:
            e = rec.feature(rec.alignCrop(bgr, f)).flatten()
            fd["e"] = [round(float(v), 5) for v in e / (np.linalg.norm(e) + 1e-9)]
        faces.append(fd)
    lap("embed")
    return {"f": rel, "ms": T, "w": im.size[0], "h": im.size[1], "sh": round(sh, 1), "br": round(br, 1), "dh": dh,
            "date": str(dto), "cam": bool(cam), "gps": gps is not None, "nlo": 0 if fs is None else len(fs), "fa": faces}


def run(kind, files):
    t0 = time.perf_counter()
    with Pool(4, init) as pool:
        rows = list(pool.imap_unordered(work, files, chunksize=1))
    wall = time.perf_counter() - t0
    stages = {}
    for r in rows:
        for k, v in r["ms"].items(): stages.setdefault(k, []).append(v)
    per = wall / len(rows)
    print("%s: %d pictures in %.1f s with 4 processes = %.0f ms per picture, about %.0f min per 6,000" % (
        kind.upper(), len(rows), wall, per * 1000, per * 6000 / 60))
    print("   median ms per stage (one process): " + ", ".join(
        "%s %.0f" % (k, float(np.median(v))) for k, v in stages.items()))
    return rows, {"wall_s": round(wall, 2), "n": len(rows), "ms_per_picture": round(per * 1000),
                  "stages_median_ms": {k: round(float(np.median(v))) for k, v in stages.items()}}


def main():
    if not os.path.exists(os.path.join(ROOT, "models", "sface.onnx")):
        sys.exit("Models missing. Run  python download_models.py  first.")
    man = json.load(open(os.path.join(SET, "manifest.json")))
    out = {"python": {"cpu": os.cpu_count(), "opencv": cv2.__version__}, "files": {}}
    for kind in ("jpeg", "heic", "iphone"):
        files = man.get("iphone", []) * 12 if kind == "iphone" else [f[kind] for f in man["files"]]
        rows, summary = run(kind, files)
        out["python"][kind] = summary
        for r in rows: out["files"][r["f"]] = {k: r[k] for k in ("w", "h", "sh", "br", "dh", "date", "cam", "gps", "nlo", "fa")}
    json.dump(out, open(os.path.join(SET, "reference.json"), "w"))
    print("Wrote testset/reference.json. Next: serve the repo folder and open the page, see README.md.")


if __name__ == "__main__":
    main()
