#!/usr/bin/env python3
"""Demo-Daten fuer Screenshots: gezeichnete Skizzen statt echter Fotos. Schreibt nach demo/. Keine echten Bilder noetig."""
import os, json, math, random, calendar, shutil
from PIL import Image, ImageDraw, ImageFilter
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo")
for d in ("thumbs", "prev", "faces"): os.makedirs(os.path.join(OUT, d), exist_ok=True)
R = random.Random(24)
INK = (52, 46, 40)
PEOPLE = [dict(hair=(122, 78, 44), shirt=(232, 132, 62), kid=True, style="short"),
          dict(hair=(226, 190, 96), shirt=(70, 160, 160), kid=True, style="tails"),
          dict(hair=(60, 52, 48), shirt=(120, 110, 170), kid=False, style="glasses")]

def jit(pts, a=3): return [(x + R.uniform(-a, a), y + R.uniform(-a, a)) for x, y in pts]
def line(d, pts, w=6, fill=INK):
    for _ in range(2): d.line(jit(pts), fill=fill, width=w, joint="curve")
def blob(d, pts, fill, w=6):
    d.polygon(pts, fill=fill); line(d, pts + [pts[0]], w)
def circ(cx, cy, rx, ry=None, n=28):
    ry = ry or rx; return [(cx + rx * math.cos(i * 2 * math.pi / n), cy + ry * math.sin(i * 2 * math.pi / n)) for i in range(n)]
def ground(d, W, H, y, fill, amp=18):
    pts = [(x, y + amp * math.sin(x / 170 + R.random())) for x in range(0, W + 80, 80)]
    blob(d, pts + [(W, H), (0, H)], fill)
def sun(d, x, y, r=70, fill=(250, 208, 90)):
    blob(d, circ(x, y, r), fill)
    for i in range(10):
        a = i * math.pi / 5; line(d, [(x + (r + 18) * math.cos(a), y + (r + 18) * math.sin(a)), (x + (r + 55) * math.cos(a), y + (r + 55) * math.sin(a))], 5)
def cloud(d, x, y, s=1.0):
    for dx, dy, r in ((0, 0, 55), (60, -22, 68), (125, 0, 55), (62, 22, 60)): d.polygon(circ(x + dx * s, y + dy * s, r * s), fill=(250, 250, 250))
    line(d, circ(x + 62 * s, y, 118 * s, 62 * s), 4)
def mountain(d, x, y, w, h, snow=True, fill=(150, 158, 172)):
    blob(d, [(x, y), (x + w / 2, y - h), (x + w, y)], fill)
    if snow: blob(d, [(x + w * .36, y - h * .72), (x + w / 2, y - h), (x + w * .64, y - h * .72), (x + w * .55, y - h * .62), (x + w * .5, y - h * .7), (x + w * .44, y - h * .6)], (252, 252, 255), 4)
def pine(d, x, y, s=1.0, fill=(70, 130, 90), deco=False):
    blob(d, [(x - 14 * s, y), (x + 14 * s, y), (x + 14 * s, y - 50 * s), (x - 14 * s, y - 50 * s)], (130, 92, 60), 4)
    for k in range(3): blob(d, [(x - (110 - 22 * k) * s, y - (45 + 85 * k) * s), (x, y - (190 + 85 * k) * s), (x + (110 - 22 * k) * s, y - (45 + 85 * k) * s)], fill)
    if deco:
        for _ in range(12):
            k = R.uniform(.15, .85); px = x + R.uniform(-80, 80) * (1 - k) * s; py = y - (60 + 300 * k) * s
            d.ellipse([px - 11, py - 11, px + 11, py + 11], fill=R.choice([(214, 60, 52), (240, 196, 70), (80, 150, 210)]), outline=INK, width=3)
        blob(d, circ(x, y - 365 * s, 20 * s, n=10), (240, 196, 70), 4)
def tree(d, x, y, s=1.0, fill=(110, 170, 90)):
    blob(d, [(x - 16 * s, y), (x + 16 * s, y), (x + 12 * s, y - 150 * s), (x - 12 * s, y - 150 * s)], (130, 92, 60), 4)
    blob(d, circ(x, y - 230 * s, 120 * s, 105 * s), fill)
def house(d, x, y, s=1.0):
    blob(d, [(x, y), (x + 300 * s, y), (x + 300 * s, y - 200 * s), (x, y - 200 * s)], (244, 226, 190))
    blob(d, [(x - 30 * s, y - 200 * s), (x + 150 * s, y - 330 * s), (x + 330 * s, y - 200 * s)], (196, 92, 70))
    blob(d, [(x + 120 * s, y), (x + 180 * s, y), (x + 180 * s, y - 110 * s), (x + 120 * s, y - 110 * s)], (130, 92, 60), 4)
    blob(d, [(x + 210 * s, y - 90 * s), (x + 265 * s, y - 90 * s), (x + 265 * s, y - 145 * s), (x + 210 * s, y - 145 * s)], (190, 222, 240), 4)
def snowman(d, x, y, s=1.0):
    for r, dy in ((90, 90), (65, 235), (45, 340)): blob(d, circ(x, y - dy * s, r * s), (252, 252, 255))
    d.ellipse([x - 20 * s, y - 352 * s, x - 8 * s, y - 340 * s], fill=INK); d.ellipse([x + 8 * s, y - 352 * s, x + 20 * s, y - 340 * s], fill=INK)
    blob(d, [(x, y - 335 * s), (x + 50 * s, y - 325 * s), (x, y - 318 * s)], (240, 140, 50), 3)
    line(d, [(x - 60 * s, y - 250 * s), (x - 150 * s, y - 310 * s)], 6); line(d, [(x + 60 * s, y - 250 * s), (x + 150 * s, y - 310 * s)], 6)
def face(d, x, y, r, p, look=True, smile=True):
    hair, st = p["hair"], p["style"]
    if st == "tails":
        blob(d, circ(x - r * 1.15, y + r * .2, r * .38, r * .55), hair, 4); blob(d, circ(x + r * 1.15, y + r * .2, r * .38, r * .55), hair, 4)
    blob(d, circ(x, y, r), (250, 220, 190))
    d.pieslice([x - r * 1.05, y - r * 1.12, x + r * 1.05, y + r * .9], 180, 360, fill=hair); line(d, [(x - r, y - r * .1), (x - r * .6, y - r * .95), (x, y - r * 1.12), (x + r * .6, y - r * .95), (x + r, y - r * .1)], 4)
    ex = 0 if look else r * .28
    for sx in (-1, 1): d.ellipse([x + sx * r * .36 + ex - r * .09, y - r * .05 - r * .09, x + sx * r * .36 + ex + r * .09, y - r * .05 + r * .09], fill=INK)
    if st == "glasses":
        for sx in (-1, 1): d.ellipse([x + sx * r * .36 - r * .26, y - r * .3, x + sx * r * .36 + r * .26, y + r * .2], outline=INK, width=max(3, int(r * .07)))
        d.line([(x - r * .1, y - r * .05), (x + r * .1, y - r * .05)], fill=INK, width=max(3, int(r * .07)))
    if smile: d.arc([x - r * .42 + ex, y + r * .12, x + r * .42 + ex, y + r * .62], 15, 165, fill=INK, width=max(3, int(r * .08)))
def person(d, x, y, pid, s=1.0, look=True, arms="down"):
    p = PEOPLE[pid]; k = (0.72 if p["kid"] else 1.0) * s; r = 46 * k
    blob(d, [(x - 28 * k, y), (x - 6 * k, y), (x - 6 * k, y - 130 * k), (x - 28 * k, y - 130 * k)], (70, 84, 120), 4)
    blob(d, [(x + 6 * k, y), (x + 28 * k, y), (x + 28 * k, y - 130 * k), (x + 6 * k, y - 130 * k)], (70, 84, 120), 4)
    blob(d, [(x - 48 * k, y - 120 * k), (x + 48 * k, y - 120 * k), (x + 40 * k, y - 270 * k), (x - 40 * k, y - 270 * k)], p["shirt"])
    ay = -330 if arms == "up" else -150
    line(d, [(x - 42 * k, y - 250 * k), (x - 95 * k, y + ay * k)], 9); line(d, [(x + 42 * k, y - 250 * k), (x + 95 * k, y + ay * k)], 9)
    face(d, x, y - 318 * k, r, p, look)
    return (x, y - 318 * k, r)
def flakes(d, W, H, n=90):
    for _ in range(n):
        x, y, r = R.uniform(0, W), R.uniform(0, H), R.uniform(4, 9); d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255))
def rain(d, W, H):
    for _ in range(70):
        x, y = R.uniform(0, W), R.uniform(0, H * .8); d.line([(x, y), (x - 14, y + 44)], fill=(120, 150, 190), width=4)
def waves(d, W, y0, y1):
    for y in range(int(y0), int(y1), 46):
        line(d, [(x, y + 10 * math.sin(x / 60)) for x in range(R.randint(0, 200), W, 30)][:R.randint(8, 22)], 4, (240, 250, 255))
def tent(d, x, y, s=1.0):
    blob(d, [(x - 170 * s, y), (x, y - 210 * s), (x + 170 * s, y)], (232, 150, 70)); blob(d, [(x - 40 * s, y), (x, y - 120 * s), (x + 40 * s, y)], (90, 70, 60), 4)
def pumpkin(d, x, y, s=1.0):
    blob(d, circ(x, y - 50 * s, 70 * s, 52 * s), (236, 140, 50)); line(d, [(x, y - 100 * s), (x + 12 * s, y - 130 * s)], 8, (90, 120, 60))
    for dx in (-30, 0, 30): d.arc([x + (dx - 26) * s, y - 100 * s, x + (dx + 26) * s, y], 90, 270, fill=INK, width=3)
def kite(d, x, y, s=1.0):
    blob(d, [(x, y - 90 * s), (x + 60 * s, y), (x, y + 110 * s), (x - 60 * s, y)], (214, 70, 80)); line(d, [(x, y + 110 * s), (x - 40 * s, y + 220 * s), (x + 20 * s, y + 330 * s), (x - 160 * s, y + 520 * s)], 4)
def umbrella(d, x, y, s=1.0):
    d.pieslice([x - 130 * s, y - 120 * s, x + 130 * s, y + 120 * s], 180, 360, fill=(214, 70, 80), outline=INK, width=6); line(d, [(x, y), (x, y + 190 * s)], 7)
def ball(d, x, y, r=44):
    blob(d, circ(x, y, r), (250, 250, 250), 5); d.pieslice([x - r, y - r, x + r, y + r], 200, 300, fill=(214, 70, 80)); d.pieslice([x - r, y - r, x + r, y + r], 20, 120, fill=(70, 130, 200))
def cake(d, x, y, s=1.0):
    blob(d, [(x - 130 * s, y), (x + 130 * s, y), (x + 130 * s, y - 120 * s), (x - 130 * s, y - 120 * s)], (250, 226, 200)); blob(d, [(x - 130 * s, y - 120 * s), (x + 130 * s, y - 120 * s), (x + 130 * s, y - 160 * s), (x - 130 * s, y - 160 * s)], (236, 150, 170), 4)
    for dx in (-80, -27, 27, 80):
        line(d, [(x + dx * s, y - 160 * s), (x + dx * s, y - 215 * s)], 7, (80, 150, 210)); d.ellipse([x + dx * s - 9, y - 240 * s, x + dx * s + 9, y - 214 * s], fill=(250, 196, 70))
def lantern(d, x, y, s=1.0):
    line(d, [(x, y - 260 * s), (x + 70 * s, y - 330 * s)], 6); blob(d, circ(x, y - 180 * s, 55 * s, 75 * s), (250, 206, 90))

SCENES = {  # je Monat: Hintergrund + Dinge; Ort-Index: 0 Zuhause, 1 See, 2 Berge, 3 Stadtpark, 4 Strand
 12: ("xmas", 0), 1: ("sled", 2), 2: ("ski", 2), 3: ("rain", 3), 4: ("garden", 0), 5: ("park", 3),
 6: ("lake", 1), 7: ("beach", 4), 8: ("camp", 2), 9: ("forest", 3), 10: ("kite", 3), 11: ("lantern", 0)}
PLACES = ["Gingerbread House", "Eggnog Lake", "Mount Snowball", "Candy Cane Park", "Tinsel Beach"]

def draw(scene, W, H, who, var, look):
    im = Image.new("RGB", (W, H), (236, 244, 250)); d = ImageDraw.Draw(im); gy = H * .68; faces = []
    sky = {"xmas": (246, 236, 220), "sled": (226, 236, 246), "ski": (206, 228, 248), "rain": (200, 208, 220), "garden": (214, 236, 250), "park": (210, 236, 250),
           "lake": (206, 232, 250), "beach": (200, 232, 252), "camp": (250, 220, 190), "forest": (240, 226, 200), "kite": (214, 232, 244), "lantern": (60, 64, 96)}[scene]
    d.rectangle([0, 0, W, H], fill=sky)
    px = [W * (.3 + .2 * i) + var * 12 for i in range(len(who))]
    if scene == "xmas":
        d.rectangle([0, gy, W, H], fill=(186, 150, 110)); line(d, [(0, gy), (W, gy)]); pine(d, W * .78, gy + 60, 1.25, deco=True)
        blob(d, [(W * .08, gy - 300), (W * .3, gy - 300), (W * .3, gy - 100), (W * .08, gy - 100)], (150, 190, 226)); line(d, [(W * .19, gy - 300), (W * .19, gy - 100)], 4)
        for k in range(3): blob(d, [(W * .6 + k * 70, gy + 90), (W * .6 + k * 70 + 60, gy + 90), (W * .6 + k * 70 + 60, gy + 30), (W * .6 + k * 70, gy + 30)], [(214, 70, 80), (80, 150, 210), (240, 196, 70)][k], 4)
    elif scene in ("sled", "ski"):
        mountain(d, W * .05, gy, W * .5, H * .42); mountain(d, W * .45, gy, W * .55, H * .5); ground(d, W, H, gy, (250, 252, 255)); sun(d, W * .86, H * .16, 55)
        if scene == "sled": snowman(d, W * .82, gy + 90, .9)
        else: pine(d, W * .9, gy + 40, .8, (60, 120, 90)); pine(d, W * .08, gy + 60, .7, (60, 120, 90))
        flakes(d, W, H, 60)
    elif scene == "rain":
        cloud(d, W * .2, H * .16, 1.3); cloud(d, W * .6, H * .12, 1.5); ground(d, W, H, gy, (150, 180, 140)); tree(d, W * .88, gy + 30, 1.0, (100, 150, 100)); rain(d, W, H); umbrella(d, px[0] if px else W * .5, gy - 330, 1.1)
    elif scene == "garden":
        sun(d, W * .12, H * .16); cloud(d, W * .55, H * .14); ground(d, W, H, gy, (150, 200, 120)); house(d, W * .62, gy + 20, 1.1)
        for _ in range(14):
            x, y = R.uniform(0, W * .6), R.uniform(gy + 60, H - 30); line(d, [(x, y), (x, y - 50)], 4, (70, 130, 70)); blob(d, circ(x, y - 60, 16, n=8), R.choice([(236, 110, 130), (250, 206, 90), (250, 250, 250)]), 3)
    elif scene == "park":
        sun(d, W * .85, H * .15); cloud(d, W * .2, H * .15); ground(d, W, H, gy, (150, 200, 120)); tree(d, W * .1, gy + 30, 1.2); tree(d, W * .9, gy + 50, .9); ball(d, W * .7, gy + 120)
    elif scene == "lake":
        mountain(d, W * .0, gy - 40, W * .45, H * .3, False, (120, 160, 130)); mountain(d, W * .5, gy - 40, W * .5, H * .26, False, (120, 160, 130)); sun(d, W * .5, H * .16, 60)
        d.rectangle([0, gy - 40, W, gy + 120], fill=(110, 170, 220)); waves(d, W, gy - 20, gy + 110); ground(d, W, H, gy + 120, (232, 214, 170), 8)
        blob(d, [(W * .7, gy + 40), (W * .95, gy + 40), (W * .9, gy + 85), (W * .75, gy + 85)], (196, 92, 70)); line(d, [(W * .82, gy + 40), (W * .82, gy - 110)], 6); blob(d, [(W * .82, gy - 110), (W * .93, gy + 20), (W * .82, gy + 20)], (250, 250, 250), 4)
    elif scene == "beach":
        sun(d, W * .15, H * .16, 80); cloud(d, W * .6, H * .12); d.rectangle([0, H * .42, W, gy], fill=(80, 160, 220)); waves(d, W, H * .46, gy - 10); ground(d, W, H, gy, (240, 220, 170), 8)
        umbrella(d, W * .84, gy - 150, 1.2); ball(d, W * .62, gy + 150, 50); blob(d, [(W * .1, gy + 200), (W * .2, gy + 200), (W * .18, gy + 120), (W * .12, gy + 120)], (214, 70, 80), 4)
    elif scene == "camp":
        sun(d, W * .5, H * .3, 90, (250, 170, 90)); mountain(d, W * .1, gy, W * .5, H * .4, True, (140, 130, 150)); mountain(d, W * .5, gy, W * .5, H * .34, True, (140, 130, 150)); ground(d, W, H, gy, (120, 160, 100)); tent(d, W * .8, gy + 110, 1.1); pine(d, W * .06, gy + 60, .8)
    elif scene == "forest":
        ground(d, W, H, gy, (196, 150, 90))
        for k in range(6): tree(d, W * (.06 + .18 * k), gy + R.uniform(-10, 60), R.uniform(.8, 1.2), R.choice([(226, 150, 60), (206, 96, 60), (236, 190, 80)]))
        pumpkin(d, W * .86, gy + 190, 1.0)
    elif scene == "kite":
        cloud(d, W * .15, H * .2); cloud(d, W * .7, H * .1, 1.2); ground(d, W, H, gy, (170, 190, 110)); kite(d, W * .72, H * .2, 1.0); tree(d, W * .08, gy + 40, 1.0, (226, 160, 70)); pumpkin(d, W * .9, gy + 160, .8)
    elif scene == "lantern":
        blob(d, circ(W * .85, H * .15, 55), (250, 244, 210), 4)
        for _ in range(40): x, y = R.uniform(0, W), R.uniform(0, gy - 100); d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(250, 244, 210))
        ground(d, W, H, gy, (70, 84, 80)); house(d, W * .05, gy + 20, .9)
        for x in px: lantern(d, x + 110, gy + 60, 1.0)
    extra = {"sled": "up", "beach": "up", "kite": "up", "park": "up"}.get(scene, "down")
    for i, pid in enumerate(who):
        faces.append((pid,) + person(d, px[i], gy + 150 + (i % 2) * 30, pid, 1.25, look[i], extra if i == 0 else "down"))
    if scene == "xmas" and var == 0: cake(d, W * .47, gy + 150, .7)
    im = im.filter(ImageFilter.SMOOTH)
    return im, faces

def shot(W, H):  # Screenshot-Attrappe
    im = Image.new("RGB", (W, H), (248, 248, 250)); d = ImageDraw.Draw(im); d.rectangle([0, 0, W, 110], fill=(60, 110, 200))
    for k in range(9):
        y = 190 + k * 150; d.rounded_rectangle([60, y, W - 60, y + 110], 20, fill=(232, 236, 242)); d.rectangle([90, y + 30, 90 + R.randint(300, W - 300), y + 50], fill=(170, 178, 190))
    return im

photos = []; idx = 0; g = -1; m = -1
months = [(2025, 12)] + [(2026, k) for k in range(1, 12)]
plan = [("burst3", [0, 1]), ("one", [0]), ("one", [1, 2]), ("blur", [0, 1, 2]), ("one", [2]), ("one", [0, 1, 2]), ("shot", [])]
for (yy, mm) in months:
    scene, place = SCENES[mm]; day = 21 if mm == 12 else R.randint(3, 9)
    for kind, who in plan:
        m += 1; day = min(day + R.randint(1, 4), 28); hour = R.randint(9, 17)
        n = 3 if kind == "burst3" else 1; g += 1
        scores = sorted([R.randint(55, 97) for _ in range(n)], reverse=True)
        for v in range(n):
            idx += 1; f = "IMG_%04d.JPG" % (1000 + idx)
            port = (idx % 5 == 0) and kind != "shot"; W, H = (1200, 1600) if port else (1600, 1200)
            look = [not (kind == "one" and len(who) == 3 and i == 1) and not (v == 2 and i == 0) for i in range(len(who))]
            if kind == "shot": im, faces = shot(1200, 1600), []; W, H = 1200, 1600
            else: im, faces = draw(scene, W, H, who, v, look)
            fl = []
            if kind == "blur": im = im.filter(ImageFilter.GaussianBlur(9)); fl = ["unscharf"]
            if kind == "shot": fl = ["screenshot"]
            if kind == "burst3" and v > 0: fl = ["serie"]
            im.save(os.path.join(OUT, "prev", f + ".jpg"), quality=84); th = im.copy(); th.thumbnail((360, 360)); th.save(os.path.join(OUT, "thumbs", f + ".jpg"), quality=78)
            t = calendar.timegm((yy, mm, day, hour, 10 + v, 5 * v))
            photos.append({"f": f, "t": t, "g": g, "m": m, "p": -1 if kind == "shot" else (place if len(who) != 1 else [place, 0][idx % 2]), "s": 0 if kind == "shot" else (22 if kind == "blur" else scores[v]),
                           "fl": fl, "pe": sorted(who), "nf": len(who), "na": len(who), "w": W * 2.52 // 1, "h": H * 2.52 // 1, "lk": [sum(look), len(who)]})
            photos[-1]["w"], photos[-1]["h"] = (3024, 4032) if H > W else (4032, 3024)
photos.sort(key=lambda p: p["t"])
for pid, p in enumerate(PEOPLE):
    for k in range(3):
        im = Image.new("RGB", (200, 200), [(226, 236, 246), (240, 226, 200), (214, 236, 250)][k]); d = ImageDraw.Draw(im); face(d, 100, 108, 66, p, look=(k != 2)); im.save(os.path.join(OUT, "faces", "p%d_%d.jpg" % (pid, k)), quality=88)
cnt = lambda pid: sum(1 for p in photos if pid in p["pe"])
places = [{"n": n, "c": sum(1 for p in photos if p["p"] == i)} for i, n in enumerate(PLACES)]
data = {"key": "advent24-demo", "pver": "demo", "merge0": {}, "src": "/path/to/your/photos", "out": "/path/to/advent-photo-picker", "gen": "demo data (sketches)", "photos": photos, "places": places,
        "persons": [{"id": i, "c": cnt(i), "n": 3} for i in range(3)]}
cand = [p for p in photos if not p["fl"]]
sel = [p["f"] for p in cand if p["s"] >= 62][:30]; fin = sel[:12:1][:12]; cover = next(p["f"] for p in cand if p["w"] > p["h"] and len(p["pe"]) == 3)
state = {"sel": sorted(set(sel + [cover])), "rej": [next(p["f"] for p in cand if p["f"] not in sel and p["f"] != cover)], "fin": fin, "cover": cover, "names": {"0": "Rudi Red-Nose", "1": "Holly Jolly", "2": "Mr. Tinsel"}, "merge": {}, "hide": [], "pver": "demo", "m0": "{}", "plain": False, "crop": "a", "seen": [p["f"] for p in cand[:9]], "last": cand[8]["f"]}
js = "window.DATA=" + json.dumps(data, separators=(",", ":")) + ";\ntry{if(!localStorage.getItem('advent24-demo'))localStorage.setItem('advent24-demo'," + json.dumps(json.dumps(state)) + ");}catch(e){}\n"
open(os.path.join(OUT, "data.js"), "w").write(js)
print(len(photos), "sketches,", len(cand), "candidates,", len(sel), "shortlisted,", len(fin), "doors. Open demo/index.html")
# Kontaktbogen zur Kontrolle
sheet = Image.new("RGB", (6 * 366, 4 * 366), (30, 30, 30))
for k, p in enumerate([q for q in photos if q["fl"] != ["serie"]][::3][:24]):
    th = Image.open(os.path.join(OUT, "thumbs", p["f"] + ".jpg")); sheet.paste(th, ((k % 6) * 366 + (360 - th.width) // 2, (k // 6) * 366 + (360 - th.height) // 2))
sheet.save(os.path.join(OUT, "_kontaktbogen.jpg"), quality=80)
shutil.copyfile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html"), os.path.join(OUT, "index.html"))
