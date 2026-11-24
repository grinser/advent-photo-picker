#!/usr/bin/env python3
"""Step 2: better face features (ArcFace R50, local with onnxruntime) for the person groups. Can be resumed."""
import os, json, time, base64
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")   # hides "Targets are not supported" warnings
import numpy as np, cv2
from multiprocessing import Pool
from common import need_models, progress
OUT = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(OUT, "work", "arc.jsonl")
TPL = np.array([[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366], [41.5493, 92.3655], [70.7299, 92.2041]], np.float32)
det = ses = None
def init():
    global det, ses
    import onnxruntime as ort
    cv2.setNumThreads(1)
    det = cv2.FaceDetectorYN.create(os.path.join(OUT, "models", "yunet.onnx"), "", (320, 320), 0.8, 0.3, 50)
    so = ort.SessionOptions(); so.intra_op_num_threads = 1; so.inter_op_num_threads = 1; so.log_severity_level = 3
    ses = ort.InferenceSession(os.path.join(OUT, "models", "w600k_r50.onnx"), so, providers=["CPUExecutionProvider"])
def work(name):
    r = {"f": name, "fa": []}
    try:
        im = cv2.imread(os.path.join(OUT, "prev", name + ".jpg"))
        det.setInputSize((im.shape[1], im.shape[0])); _, fs = det.detect(im)
        crops = []
        for f in (fs if fs is not None else [])[:12]:
            if f[14] < 0.88 or min(f[2], f[3]) < 56: continue
            M, _ = cv2.estimateAffinePartial2D(f[4:14].reshape(5, 2).astype(np.float32), TPL, method=cv2.LMEDS)
            if M is None: continue
            a = cv2.warpAffine(im, M, (112, 112), borderValue=0)
            crops.append(((cv2.cvtColor(a, cv2.COLOR_BGR2RGB).astype(np.float32) - 127.5) / 127.5).transpose(2, 0, 1))
            r["fa"].append({"b": [int(v) for v in f[:4]], "c": round(float(f[14]), 2)})
        for k, c in enumerate(crops):
            e = ses.run(None, {ses.get_inputs()[0].name: c[None]})[0][0]
            e = e / (np.linalg.norm(e) + 1e-9)
            r["fa"][k]["e"] = base64.b64encode(e.astype(np.float16).tobytes()).decode()
    except Exception as e:
        r["err"] = str(e)[:80]
    return r
if __name__ == "__main__":
    need_models("yunet.onnx", "w600k_r50.onnx")
    if not os.path.exists(os.path.join(OUT, "work", "results.jsonl")): raise SystemExit("Run  python process.py  first.")
    budget = float(os.environ.get("BUDGET", "1e9")); t0 = time.time(); done = set()
    if os.path.exists(RES):
        for l in open(RES):
            try: done.add(json.loads(l)["f"])
            except Exception: pass
    names = []
    for l in open(os.path.join(OUT, "work", "results.jsonl")):
        r = json.loads(l)
        if not r.get("skip") and not r.get("err") and r["f"] not in done and r.get("fa"): names.append(r["f"])
    n = 0
    print("%d photos with faces to look at again." % len(names))
    with open(RES, "a") as out, Pool(3, init) as pool:
        for r in pool.imap_unordered(work, names, chunksize=4):
            out.write(json.dumps(r) + "\n"); out.flush(); n += 1
            if n % 20 == 0: progress(n, len(names), t0, time.time())
            if time.time() - t0 > budget: pool.terminate(); break
    print()
    if n < len(names): print("Stopped, %d left. Run  python arc.py  again to continue." % (len(names) - n))
    else: print("Done. Next:  python build.py")
