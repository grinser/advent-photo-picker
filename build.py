#!/usr/bin/env python3
"""Step 3: bursts, moments, places and people; writes data.js for the page. Local."""
import os, sys, json, base64, math, collections, time
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")   # hides "Targets are not supported" warnings
import numpy as np, cv2

OUT = os.path.dirname(os.path.abspath(__file__))
from common import photos_dir
SRC = photos_dir()   # PHOTOS, or the folder process.py used last
if not os.path.exists(os.path.join(OUT, "work", "results.jsonl")): raise SystemExit("Run  python process.py  first.")
DEBUG = os.environ.get("DEBUG")
HOME_CC = os.environ.get("HOME_COUNTRY", "")   # country code shown without suffix in place names, e.g. AT
os.makedirs(os.path.join(OUT, "faces"), exist_ok=True)
rows = []
for l in open(os.path.join(OUT, "work", "results.jsonl")):
    try: r = json.loads(l)
    except Exception: continue
    if r.get("skip") or r.get("err") or "dh" not in r: continue
    rows.append(r)
rows = list({r["f"]: r for r in rows}.values())
rows.sort(key=lambda r: (r["t"], r["f"]))
N = len(rows)
ham = lambda a, b: bin(int(a, 16) ^ int(b, 16)).count("1")

for r in rows: r["lk"] = [0, 0]; r["ec"] = 0
# Genauere Messung (look2.py, MediaPipe Face Mesh): Augen offen, Iris mittig, Kopf frontal. Ersetzt die Kopfhaltung, wo vorhanden.
l2 = os.path.join(OUT, "work", "look2.jsonl")
if os.path.exists(l2):
    EAR = float(os.environ.get("LOOK_EAR", 0.12)); YAW = float(os.environ.get("LOOK_YAW", 0.20)); IR = float(os.environ.get("LOOK_IRIS", 0.10))
    byf = {r["f"]: r for r in rows}
    for l in open(l2):
        x = json.loads(l); k = w = z = 0
        for f in x["fa"]:
            v = f["v"]
            if v is None:
                if min(f["b"][2], f["b"][3]) >= 80: w += 1      # grosses Gesicht ohne Netz: meist Profil oder verdeckt
                continue                                         # kleines Gesicht: unbekannt, zaehlt nicht
            if v[0] < EAR: z += 1
            elif abs(v[2]) < YAW and abs(v[1] - 0.5) < IR: k += 1
            else: w += 1
        if k + w + z and x["f"] in byf: byf[x["f"]]["lk"] = [k, k + w + z]; byf[x["f"]]["ec"] = z

# --- Qualitaet
for r in rows:
    r["shot"] = r["f"].lower().endswith(".png") and not r["cam"]
    r["q"] = math.log10(r["sh"] + 1) + math.log10(r["shm"] + 1)
cam = sorted(r["q"] for r in rows if not r["shot"]) or [0]
for r in rows:
    rank = np.searchsorted(cam, r["q"]) / len(cam)
    pen = 1.0
    if r["br"] < 45 or r["br"] > 215: pen *= 0.75
    if r["dk"] > 0.6 or r["bl"] > 0.4: pen *= 0.8
    big = [f for f in r.get("fa", []) if f["c"] >= 0.9 and min(f["b"][2], f["b"][3]) >= 56]
    allook = r["lk"][1] > 0 and r["lk"][0] == r["lk"][1]
    r["s"] = int(round(min(100, 100 * rank * pen + (5 if big else 0) + (8 if allook else 0))))
    fl = []
    if r["shot"]: fl.append("screenshot")
    else:
        if r["sh"] < float(os.environ.get("BLUR_SH", 60)) and r["shm"] < float(os.environ.get("BLUR_SHM", 200)): fl.append("unscharf")
        if r["br"] < 22: fl.append("dunkel")
        if not r["cam"]: fl.append("import")
    r["fl"] = fl

# --- Serien (aehnliche Bilder kurz hintereinander) und Momente
g = m = -1; prev = None
for r in rows:
    if prev is None or r["t"] - prev["t"] > 2 * 3600: m += 1
    r["m"] = m
    same = False
    if prev is not None and not r["shot"] and not prev["shot"]:
        dt = r["t"] - prev["t"]; d = ham(r["dh"], prev["dh"])
        same = dt <= 3 or (dt <= 60 and d <= 14) or (dt <= 600 and d <= 6)
        if dt <= 1 and d <= 3 and r["w"] == prev["w"]: r["fl"].append("duplikat")
    if not same: g += 1
    r["g"] = g; prev = r
groups = collections.defaultdict(list)
for r in rows: groups[r["g"]].append(r)
bad = {"unscharf", "dunkel", "screenshot", "duplikat"}
for gr in groups.values():
    ok = [r for r in gr if not bad & set(r["fl"])]
    if len(ok) > 1:
        best = max(ok, key=lambda r: r["s"])
        for r in ok:
            if r is not best: r["fl"].append("serie")

# --- Orte (GPS-Raster ~400 m, Nachbarzellen verbunden), Namen offline
cells = {}
for r in rows:
    if "la" in r: cells.setdefault((round(r["la"] / 0.004), round(r["lo"] / 0.006)), []).append(r)
par = {c: c for c in cells}
def find(c):
    while par[c] != c: par[c] = par[par[c]]; c = par[c]
    return c
for (a, b) in cells:
    for da in (-1, 0, 1):
        for db in (-1, 0, 1):
            o = (a + da, b + db)
            if o in cells: par[find(o)] = find((a, b))
cl = collections.defaultdict(list)
for c, rs in cells.items(): cl[find(c)].extend(rs)
cl = sorted(cl.values(), key=len, reverse=True)
cents = [(float(np.mean([r["la"] for r in rs])), float(np.mean([r["lo"] for r in rs]))) for rs in cl]
names = ["Place %d" % (i + 1) for i in range(len(cl))]
try:
    import reverse_geocoder as rg
    res = rg.search(cents, mode=1) if cents else []
    seen = collections.Counter()
    for i, x in enumerate(res):
        base = x["name"] + ("" if x["cc"] == HOME_CC else ", " + x["cc"]); seen[base] += 1
        names[i] = base if seen[base] == 1 else "%s · %d" % (base, seen[base])
except Exception as e:
    print("Place names not available:", e)
places = []
for i, rs in enumerate(cl):
    for r in rs: r["p"] = i
    places.append({"n": names[i], "c": len(rs)})

# --- Personen: Gesichts-Embeddings lokal gruppieren (ohne Namen)
arc = {}
ap = os.path.join(OUT, "work", "arc.jsonl")
if os.path.exists(ap):
    for l in open(ap):
        try: x = json.loads(l); arc[x["f"]] = x["fa"]
        except Exception: pass
USE_ARC = len(arc) > 0
for r in rows: r["pf"] = arc.get(r["f"], []) if USE_ARC else r.get("fa", [])
# ArcFace trennt aehnliche Gesichter (Geschwister) deutlich besser als SFace; Schwellen passend zum Modell
T = float(os.environ.get("FACE_T", 0.45 if USE_ARC else 0.45))      # Gesicht <-> Gruppen-Mittel
TM = float(os.environ.get("FACE_TM", 0.70 if USE_ARC else 0.80))    # Gruppen-Mittel <-> Gruppen-Mittel (zusammenlegen)
F = []
for i, r in enumerate(rows):
    for k, f in enumerate(r["pf"]):
        if "e" in f and f["c"] >= 0.88:
            e = np.frombuffer(base64.b64decode(f["e"]), np.float16).astype(np.float32)
            F.append((i, k, e / (np.linalg.norm(e) + 1e-9), f["b"][2] * f["b"][3]))
persons = []
if F:
    nrm = lambda M: M / (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
    order = sorted(range(len(F)), key=lambda j: -F[j][3])
    E = np.stack([F[j][2] for j in range(len(F))])
    cent = np.zeros((0, E.shape[1]), np.float32); lab = -np.ones(len(F), int)
    for j in order:
        if len(cent):
            sim = nrm(cent) @ E[j]; b = int(sim.argmax())
            if sim[b] > T: cent[b] += E[j]; lab[j] = b; continue
        cent = np.vstack([cent, E[j][None]]); lab[j] = len(cent) - 1
    for _ in range(4):  # Gruppen mit sehr aehnlichem Mittel verbinden, dann alle Gesichter neu zuordnen
        C = nrm(cent); cnt = np.bincount(lab[lab >= 0], minlength=len(C))
        S = C @ C.T; np.fill_diagonal(S, 0); mp = list(range(len(C)))
        def rt(x):
            while mp[x] != x: x = mp[x]
            return x
        for a_, b_ in sorted(zip(*np.where(np.triu(S) > TM)), key=lambda ab: -S[ab[0], ab[1]]):
            ra, rb = rt(a_), rt(b_)
            if ra != rb: mp[rb if cnt[ra] >= cnt[rb] else ra] = ra if cnt[ra] >= cnt[rb] else rb
        lab = np.array([rt(x) if x >= 0 else -1 for x in lab])
        ids = [x for x in np.unique(lab) if x >= 0]
        cent = np.stack([E[lab == x].sum(0) for x in ids])
        sim = E @ nrm(cent).T
        lab = sim.argmax(1); lab[sim.max(1) < T] = -1
        ids = [x for x in np.unique(lab) if x >= 0]
        cent = np.stack([E[lab == x].sum(0) for x in ids]); lab = np.array([ids.index(x) if x >= 0 else -1 for x in lab])
    cnt = np.bincount(lab[lab >= 0])
    top = np.argsort(-cnt)[:6]; Ct = nrm(cent)[top]
    if not USE_ARC: print("Using the simpler face model. Run  python arc.py  first for better person groups.")
    if DEBUG:
        print("groups:", len(cnt), "| no group:", int((lab < 0).sum()), "| largest:", cnt[top].tolist())
        print("similarity of the largest groups:"); print((Ct @ Ct.T).round(2))
    C = cent / np.linalg.norm(cent, axis=1, keepdims=True)
    ph = collections.defaultdict(set)
    for j, l in enumerate(lab):
        if l >= 0: ph[int(l)].add(F[j][0])
    keep = sorted([l for l in ph if len(ph[l]) >= 4], key=lambda l: -len(ph[l]))[:80]
    for pid, l in enumerate(keep):
        for i in ph[l]: rows[i].setdefault("pe", []).append(pid)
        js = [j for j in range(len(F)) if lab[j] == l]
        js.sort(key=lambda j: -(float(E[j] @ C[l]) + min(F[j][3], 40000) / 200000))
        top = sorted(js[:max(8, len(js) // 3)], key=lambda j: rows[F[j][0]]["t"])   # gute Treffer, ueber die Zeit verteilt
        pick = [js[0]] + [top[int(k * (len(top) - 1) / 6)] for k in range(7)]
        seen = set(); n = 0
        for j in pick:
            if j in seen or n >= 8: continue
            seen.add(j); i, k = F[j][0], F[j][1]
            im = cv2.imread(os.path.join(OUT, "prev", rows[i]["f"] + ".jpg"))
            if im is None: continue
            x, y, w, h = rows[i]["pf"][k]["b"]; sz = int(max(w, h) * 0.8); cx, cy = x + w // 2, y + h // 2
            crop = im[max(0, cy - sz):cy + sz, max(0, cx - sz):cx + sz]
            if crop.size:
                cv2.imwrite(os.path.join(OUT, "faces", "p%d_%d.jpg" % (pid, n)), cv2.resize(crop, (200, 200))); n += 1
        persons.append({"id": pid, "c": len(ph[l]), "n": n})

photos = [{"f": r["f"], "t": r["t"], "g": r["g"], "m": r["m"], "p": r.get("p", -1), "s": r["s"], "fl": r["fl"],
           "pe": sorted(r.get("pe", [])), "nf": len([f for f in r.get("fa", []) if f["c"] >= 0.88]), "na": max(r.get("nlo", 0), len(r.get("fa", []))), "w": r["w"], "h": r["h"], "lk": r["lk"], "ec": r["ec"]} for r in rows]
import hashlib
pver = hashlib.md5(json.dumps([[p["f"], p["pe"]] for p in photos if p["pe"]]).encode()).hexdigest()[:10]
merge0 = {}
mp_ = os.path.join(OUT, "person_merge.json")
if os.path.exists(mp_):
    mj = json.load(open(mp_))
    if mj.get("pver") == pver: merge0 = mj.get("merge", {})
    else: print("person_merge.json no longer matches the groups and is ignored")
data = {"merge0": merge0, "pver": pver, "src": SRC, "out": OUT, "py": sys.executable, "sep": os.sep, "gen": time.strftime("%Y-%m-%d %H:%M"), "photos": photos, "places": places, "persons": persons}
open(os.path.join(OUT, "data.js"), "w", encoding="utf-8").write("window.DATA=" + json.dumps(data, separators=(",", ":")) + ";")
c = collections.Counter(x for r in rows for x in r["fl"])
n_cand = sum(1 for r in rows if not (bad | {"serie"}) & set(r["fl"]))
plural = lambda n, one, many: "%d %s" % (n, one if n == 1 else many)
print("%s, %s, %s, %s. Now open index.html in your browser." % (
    plural(N, "photo", "photos"), plural(n_cand, "candidate", "candidates"), plural(len(places), "place", "places"),
    plural(len(persons), "person", "people")))
if DEBUG: print("flags:", dict(c), "| bursts:", len(groups), "| moments:", m + 1, "| faces:", len(F))
