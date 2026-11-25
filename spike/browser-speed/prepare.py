#!/usr/bin/env python3
"""Browser speed spike, step 1: make a test set and fetch the browser libraries.

The test set is synthetic: phone-sized pictures (12 MP) built from the public-domain NASA portrait
astronaut.jpg (from scikit-image), as JPEG and HEIC with EXIF. It never reads your photos.
The libraries come from the npm registry and are checked against fixed SHA-256 sums.
Run it from the repo root with the picker's environment:  python spike/browser-speed/prepare.py
"""
import os, io, json, random, hashlib, tarfile, urllib.request, datetime
import numpy as np
from PIL import Image, ImageFilter
import pillow_heif

HERE = os.path.dirname(os.path.abspath(__file__))
SET = os.path.join(HERE, "testset")
VENDOR = os.path.join(HERE, "vendor")
N = int(os.environ.get("SPIKE_N", 24))

# npm package -> (sha256 of the tarball, files to keep)
PACKAGES = {
    "onnxruntime-web/-/onnxruntime-web-1.22.0.tgz": ("e293551f9d36d003e293d0f2937fee7b3dfdcef76d71d1449b55e2d4157c7aea", [
        "dist/ort.wasm.min.mjs", "dist/ort-wasm-simd-threaded.mjs", "dist/ort-wasm-simd-threaded.wasm",
        "dist/ort.webgpu.min.mjs", "dist/ort-wasm-simd-threaded.jsep.mjs", "dist/ort-wasm-simd-threaded.jsep.wasm"]),
    "libheif-js/-/libheif-js-1.23.5.tgz": ("d0bfe7198bd624c524cef8ccf78e15ceb42683c87598c64c2e13ced0d8680932", ["libheif-wasm/libheif-bundle.mjs"]),
    "exifr/-/exifr-7.1.3.tgz": ("cf2515f5eed3a60ed33d5d4ad709af6acbe5d69a36e0d36924d80cb8b66a0dc2", ["dist/full.esm.mjs"]),
}


def fetch_vendor():
    for path, (sha, keep) in PACKAGES.items():
        name = path.split("/")[0]
        dest = os.path.join(VENDOR, name)
        if all(os.path.exists(os.path.join(dest, os.path.basename(k))) for k in keep):
            continue
        url = "https://registry.npmjs.org/" + path
        print("Downloading", url)
        data = urllib.request.urlopen(url, timeout=120).read()
        got = hashlib.sha256(data).hexdigest()
        if got != sha:
            raise SystemExit("Checksum mismatch for %s: %s" % (path, got))
        os.makedirs(dest, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as t:
            for k in keep:
                with open(os.path.join(dest, os.path.basename(k)), "wb") as o:
                    o.write(t.extractfile("package/" + k).read())


def background(rng, w, h):
    """Smooth colour fields plus fine grain, so JPEG and HEIC sizes look like phone photos."""
    small = rng.integers(0, 255, (6, 8, 3), dtype=np.uint8)
    im = Image.fromarray(small).resize((w, h), Image.BICUBIC)
    a = np.asarray(im).astype(np.int16)
    a += rng.integers(-18, 18, (h, w, 1), dtype=np.int16)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def exif_for(i, rng):
    ex = Image.Exif()
    t = datetime.datetime(2025, 12, 1) + datetime.timedelta(days=i * 14, hours=int(rng.integers(8, 20)))
    ex[0x010F] = "Spike"          # Make
    ex[0x0110] = "Synthetic 12MP"  # Model
    ifd = ex.get_ifd(0x8769)
    ifd[0x9003] = t.strftime("%Y:%m:%d %H:%M:%S")   # DateTimeOriginal
    if i % 2 == 0:
        gps = ex.get_ifd(0x8825)
        gps[1], gps[2] = "N", (48.0, 18.0, 0.0)
        gps[3], gps[4] = "E", (14.0, 17.0, 0.0)
    return ex


def make_set():
    if os.path.exists(os.path.join(SET, "manifest.json")):
        print("Test set exists:", SET)
        return
    rng = np.random.default_rng(7)
    random.seed(7)
    face = Image.open(os.path.join(HERE, "astronaut.jpg")).convert("RGB").crop((120, 10, 330, 240))
    os.makedirs(os.path.join(SET, "jpeg"), exist_ok=True)
    os.makedirs(os.path.join(SET, "heic"), exist_ok=True)
    files = []
    for i in range(N):
        w, h = (4032, 3024) if i % 3 else (3024, 4032)
        im = background(rng, w, h)
        faces = [0, 1, 2, 3, 5][i % 5]
        for _ in range(faces):
            s = float(rng.uniform(1.2, 5.5))
            f = face.resize((int(face.width * s), int(face.height * s)), Image.LANCZOS)
            x = int(rng.integers(0, w - f.width)); y = int(rng.integers(0, h - f.height))
            im.paste(f, (x, y))
        if i % 6 == 5:
            im = im.filter(ImageFilter.GaussianBlur(6))   # a blurry one
        ex = exif_for(i, rng)
        jp = "jpeg/%02d.jpg" % i
        im.save(os.path.join(SET, jp), quality=90, exif=ex.tobytes())
        hp = "heic/%02d.heic" % i
        pillow_heif.from_pillow(im).save(os.path.join(SET, hp), quality=80, exif=ex.tobytes())
        files.append({"jpeg": jp, "heic": hp, "faces_pasted": faces})
        print("\r%d of %d test pictures" % (i + 1, N), end="", flush=True)
    print()
    json.dump({"files": files}, open(os.path.join(SET, "manifest.json"), "w"), indent=1)


# Two real iPhone HEIC files from exifr's test fixtures (MIT), for decoding speed and EXIF of real files
IPHONE = {
    "heic-iphone7.heic": "599f04081cac8d3682a0f06a46f892744beb86356fb2b74f0afc79414272fdba",
    "heic-iphone.heic": "4a77750547ae1d54bd009ac037b48307b20322cff5ed1fde55ac289469350a0b",
}


def fetch_iphone():
    man_path = os.path.join(SET, "manifest.json")
    man = json.load(open(man_path))
    if man.get("iphone"):
        return
    os.makedirs(os.path.join(SET, "iphone"), exist_ok=True)
    for name, sha in IPHONE.items():
        url = "https://raw.githubusercontent.com/MikeKovarik/exifr/master/test/fixtures/" + name
        print("Downloading", url)
        data = urllib.request.urlopen(url, timeout=120).read()
        if hashlib.sha256(data).hexdigest() != sha:
            raise SystemExit("Checksum mismatch for " + name)
        open(os.path.join(SET, "iphone", name), "wb").write(data)
    man["iphone"] = ["iphone/" + n for n in IPHONE]
    json.dump(man, open(man_path, "w"), indent=1)


if __name__ == "__main__":
    fetch_vendor()
    make_set()
    fetch_iphone()
    print("Next:  python spike/browser-speed/reference.py")
