# Spike: the picker's first step in a browser

A throwaway test, not part of the tool. It checks whether `process.py` could run inside a browser tab instead of
Python, and how fast. The page does the same work per picture: read the file, EXIF, decode (JPEG or HEIC), shrink to
1600 px, save a preview and a thumbnail in the browser's private storage (OPFS), sharpness, brightness, dHash, faces
with YuNet and face features with SFace. The models are the same files as in `models/`, run with
[ONNX Runtime Web](https://onnxruntime.ai/docs/tutorials/web/).

It never reads your photos. The test set is synthetic: 24 pictures at 12 MP, built from the public-domain NASA
portrait `astronaut.jpg` (from scikit-image), saved as JPEG and HEIC. Two real iPhone HEIC files come from the test
fixtures of [exifr](https://github.com/MikeKovarik/exifr) (MIT).

## Run it

From the repo folder, with the picker's environment and models in place:

```sh
.venv/bin/python spike/browser-speed/prepare.py     # test set + browser libraries, about 2 minutes
.venv/bin/python spike/browser-speed/reference.py   # the same steps in Python, for comparison
python3 -m http.server 8765 --bind 127.0.0.1
```

Then open <http://localhost:8765/spike/browser-speed/> in each browser and click the three test buttons, first with
"WebAssembly (CPU)", then with "WebGPU". "Copy result" puts the numbers on the clipboard. The page also compares its
faces, face features, sharpness and EXIF with `reference.py`.

`prepare.py` downloads three npm packages (onnxruntime-web, libheif-js, exifr) and two test files and checks each
against a fixed SHA-256 sum. The server only listens on this computer.

## First numbers (cloud container, 4 cores, headless Chromium, 4 workers)

| Test set | Python, 4 processes | Browser, WebAssembly | Browser / Python |
| --- | --- | --- | --- |
| 24 synthetic JPEG | 143 ms per picture | 189 ms | 1.3 |
| 24 synthetic HEIC | 383 ms | 553 ms | 1.4 |
| 2 real iPhone HEIC, 12 times each | 253 ms | 399 ms | 1.6 |

The browser found all 48 faces that Python found and no others. Face features match with a median cosine similarity
of 0.998 (lowest 0.973). Chromium has no HEIC decoder, so libheif in WebAssembly does it there; Safari decodes HEIC
itself. Face detection is the slowest step in WebAssembly, about 2.4 times slower than OpenCV.

Known gaps: exifr cannot read the EXIF that pillow-heif writes into the synthetic HEIC files (it reads the real iPhone
files fine). SFace does not load with the WebGPU backend in ONNX Runtime Web 1.22, so it falls back to WebAssembly.
