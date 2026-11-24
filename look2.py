#!/usr/bin/env python3
"""Stufe 1d: Augen offen? Blick zur Kamera? Mit MediaPipe Face Mesh (478 Punkte inkl. Iris), lokal.
Braucht mediapipe==0.10.14 (bringt das Modell im Paket mit), siehe README.
Pro Gesicht aus work/arc.jsonl: Ausschnitt aus dem Vorschaubild, dann
  ear  = Lidoeffnung / Augenbreite (Mittel beider Augen); unter 0.15 = Augen zu
  iris = Lage der Iris zwischen den Augenwinkeln (0.5 = mittig)
  yaw  = Nase gegen Augenmitte (0 = Kopf frontal)
  Blick zur Kamera = Augen offen UND Kopf nicht stark gedreht UND Iris gleicht die Kopfdrehung aus (oder beides mittig)."""
import os, json, time, sys
import numpy as np, cv2, mediapipe as mp
import common   # switches the network off
OUT = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(OUT, "work", "look2.jsonl")
MIN = 80   # Gesichter unter 80 px (in der 1600-px-Vorschau) sind zu klein fuer Augen -> "unbekannt"
fm = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.3)
def measure(im, b):
    x, y, w, h = b; s = max(w, h); cx, cy = x + w / 2, y + h / 2; m = int(s * 0.9)
    x0, y0, x1, y1 = int(max(0, cx - m)), int(max(0, cy - m)), int(min(im.shape[1], cx + m)), int(min(im.shape[0], cy + m))
    crop = im[y0:y1, x0:x1]
    if crop.size == 0: return None
    k = 384 / max(crop.shape[:2]); crop = cv2.resize(crop, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC if k > 1 else cv2.INTER_AREA)
    r = fm.process(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
    if not r.multi_face_landmarks: return None
    H, W = crop.shape[:2]; L = np.array([(p.x * W, p.y * H) for p in r.multi_face_landmarks[0].landmark]); d = lambda a, c: float(np.linalg.norm(L[a] - L[c]))
    ear = ((d(159, 145) + d(158, 153) + d(160, 144)) / (3 * d(33, 133)) + (d(386, 374) + d(385, 380) + d(387, 373)) / (3 * d(362, 263))) / 2
    ax = L[263] - L[33]; n = float(np.linalg.norm(ax)) + 1e-6; ax = ax / n
    pos = lambda i, a, c: float((L[i] - L[a]) @ ax) / (float((L[c] - L[a]) @ ax) + 1e-6)      # 0 = bildlinker Augenwinkel, 1 = bildrechter
    iris = (pos(468, 33, 133) + pos(473, 362, 263)) / 2
    yaw = float((L[1] - (L[33] + L[263]) / 2) @ ax) / n                                        # >0: Nase zeigt nach bildrechts
    return round(ear, 3), round(iris, 3), round(yaw, 3)
def judge(v):
    if v is None: return "u"
    ear, iris, yaw = v
    if ear < 0.15: return "z"                       # Augen zu
    g = yaw * 1.0 + (iris - 0.5) * 1.6              # Kopfdrehung und Augenstellung zusammen: ~0 heisst Blick zur Kamera
    return "k" if abs(yaw) < 0.30 and abs(g) < 0.20 else "w"   # k = Kamera, w = weg
if __name__ == "__main__":
    budget = float(os.environ.get("BUDGET", "1e9")); t0 = time.time(); done = set()
    if os.path.exists(RES):
        for l in open(RES):
            try: done.add(json.loads(l)["f"])
            except Exception: pass
    if not os.path.exists(os.path.join(OUT, "work", "arc.jsonl")): raise SystemExit("Run  python arc.py  first.")
    n = todo = 0
    with open(RES, "a") as out:
        for l in open(os.path.join(OUT, "work", "arc.jsonl")):
            r = json.loads(l)
            if r["f"] in done or not r.get("fa"): continue
            if time.time() - t0 > budget: todo += 1; continue
            im = cv2.imread(os.path.join(OUT, "prev", r["f"] + ".jpg")); res = []
            for f in r["fa"]:
                small = min(f["b"][2], f["b"][3]) < MIN
                v = None if (small or im is None) else measure(im, f["b"])
                res.append({"b": f["b"], "v": v, "j": "u" if small else judge(v)})
            out.write(json.dumps({"f": r["f"], "fa": res}) + "\n"); n += 1
    print("Stopped, %d left. Run it again to continue." % todo if todo else "Done. Next:  python build.py")
