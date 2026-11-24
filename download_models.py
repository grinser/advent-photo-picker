#!/usr/bin/env python3
"""Downloads the three face models into models/ (about 330 MB, once). Works on macOS, Windows and Linux."""
import os, sys, ssl, shutil, subprocess, zipfile, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "models")
os.makedirs(DIR, exist_ok=True)

def get(url, path, size=None):
    if os.path.exists(path) and (size is None or os.path.getsize(path) == size):
        print("ok ", os.path.basename(path)); return
    print("get", os.path.basename(path))
    tty = sys.stdout.isatty(); seen = [-1]
    def hook(n, bs, total):
        if total <= 0: return
        pct = min(100, n * bs * 100 // total)
        if tty: print("\r    %d%%" % pct, end="", flush=True)
        elif pct // 25 > seen[0]: seen[0] = pct // 25; print("    %d%%" % pct, flush=True)   # a log gets four lines, not thousands
    try:
        urllib.request.urlretrieve(url, path + ".part", hook); print()
    except urllib.error.URLError as e:
        # A fresh Windows often lacks the root certificate that Python needs; curl uses the system's own check.
        if not isinstance(e.reason, ssl.SSLError) or not shutil.which("curl"): raise
        print("\r    Python could not check the certificate, trying curl")
        subprocess.run(["curl", "-fL", "--progress-bar", "-o", path + ".part", url], check=True)
    if size is not None and os.path.getsize(path + ".part") != size:
        os.remove(path + ".part"); sys.exit("wrong size: " + os.path.basename(path))
    os.replace(path + ".part", path)

# OpenCV Zoo: YuNet (MIT), SFace (Apache 2.0)
get("https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx",
    os.path.join(DIR, "yunet.onnx"), 232589)
get("https://huggingface.co/opencv/face_recognition_sface/resolve/main/face_recognition_sface_2021dec.onnx",
    os.path.join(DIR, "sface.onnx"), 38696353)
# InsightFace ArcFace from buffalo_l: non-commercial research use only
arc = os.path.join(DIR, "w600k_r50.onnx")
if not os.path.exists(arc):
    z = os.path.join(DIR, "buffalo_l.zip")
    get("https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip", z, 288621354)
    with zipfile.ZipFile(z) as f, open(arc, "wb") as o: o.write(f.read(next(n for n in f.namelist() if n.endswith("w600k_r50.onnx"))))
    os.remove(z)
print("models ready")
