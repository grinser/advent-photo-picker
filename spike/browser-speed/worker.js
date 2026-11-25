// Browser speed spike: one worker = one process of process.py (Pool(4) there, 4 workers here).
// Per picture: read, EXIF, decode, resize to 1600, save preview + thumbnail to OPFS,
// sharpness/brightness/dHash, YuNet, SFace. Everything stays in this browser tab.
let ort, det, rec, exifr, libheif, opfs;
let nativeHeic = null; // unknown until the first HEIC
const TPL = [[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366], [41.5493, 92.3655], [70.7299, 92.2041]];

self.onmessage = async (e) => {
  const m = e.data;
  try {
    if (m.type === 'init') postMessage({ type: 'ready', ...(await init(m)) });
    else if (m.type === 'job') postMessage({ type: 'done', id: m.id, r: await job(m) });
  } catch (err) {
    postMessage({ type: m.type === 'init' ? 'error' : 'done', id: m.id, error: String((err && err.message) || err), r: { err: String((err && err.message) || err) } });
  }
};

async function bytes(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(url + ': HTTP ' + r.status);
  return new Uint8Array(await r.arrayBuffer());
}

// yunet.onnx declares a fixed 640x640 input; OpenCV ignores that, ONNX Runtime does not.
// Swap the two dim_value 640 entries of the input for dim_params "H" and "W" (same byte length).
function dynamicYunet(b) {
  const old = [0x0a, 0x02, 0x08, 0x01, 0x0a, 0x02, 0x08, 0x03, 0x0a, 0x03, 0x08, 0x80, 0x05, 0x0a, 0x03, 0x08, 0x80, 0x05];
  outer: for (let i = 0; i < b.length - old.length; i++) {
    for (let k = 0; k < old.length; k++) if (b[i + k] !== old[k]) continue outer;
    b.set([0x12, 0x01, 0x48], i + 10);
    b.set([0x12, 0x01, 0x57], i + 15);
    return b;
  }
  throw new Error('yunet.onnx: input shape not found, unexpected model file');
}

async function init({ backend }) {
  const t0 = performance.now();
  ort = await import(backend === 'webgpu' ? './vendor/onnxruntime-web/ort.webgpu.min.mjs' : './vendor/onnxruntime-web/ort.wasm.min.mjs');
  ort.env.logLevel = 'error';
  ort.env.wasm.numThreads = 1;
  ort.env.wasm.wasmPaths = new URL('./vendor/onnxruntime-web/', import.meta.url).href;
  const opts = { executionProviders: backend === 'webgpu' ? ['webgpu', 'wasm'] : ['wasm'], graphOptimizationLevel: 'all' };
  const load = async (file, b) => {
    try { return await ort.InferenceSession.create(b, opts); }
    catch (err) { throw new Error(file + ' (' + backend + '): ' + ((err && err.message) || err)); }
  };
  det = await load('yunet.onnx', dynamicYunet(await bytes('../../models/yunet.onnx')));
  const sb = await bytes('../../models/sface.onnx');
  let recEp = backend;
  try { rec = await load('sface.onnx', sb); }
  catch (err) {
    if (backend !== 'webgpu') throw err;
    rec = await ort.InferenceSession.create(sb, { executionProviders: ['wasm'] }); recEp = 'wasm (WebGPU ging nicht)';
  }
  exifr = (await import('./vendor/exifr/full.esm.mjs')).default;
  try { opfs = await (await navigator.storage.getDirectory()).getDirectoryHandle('spike', { create: true }); } catch { opfs = null; }
  return { initMs: performance.now() - t0, opfs: !!opfs, recEp };
}

async function heifDecode(buf) {
  if (!libheif) {
    const mod = await import('./vendor/libheif-js/libheif-bundle.mjs');
    libheif = mod.default;
    if (typeof libheif === 'function') libheif = await libheif();
  }
  const img = new libheif.HeifDecoder().decode(new Uint8Array(buf))[0];
  const w = img.get_width(), h = img.get_height();
  const data = new ImageData(w, h);
  await new Promise((ok, bad) => img.display(data, (d) => (d ? ok() : bad(new Error('HEIF decode failed')))));
  img.free && img.free();
  return await createImageBitmap(data);
}

async function save(name, blob) {
  if (!opfs) return;
  const fh = await opfs.getFileHandle(name, { create: true });
  const h = await fh.createSyncAccessHandle();
  h.truncate(0);
  h.write(new Uint8Array(await blob.arrayBuffer()), { at: 0 });
  h.flush(); h.close();
}

async function job({ id, src, name }) {
  const T = {};
  let t = performance.now();
  const lap = (k) => { const n = performance.now(); T[k] = (T[k] || 0) + n - t; t = n; };

  const blob = src instanceof Blob ? src : await (await fetch(src)).blob();
  const buf = await blob.arrayBuffer();
  lap('read');

  let ex = null;
  try { ex = await exifr.parse(buf, { pick: ['DateTimeOriginal', 'Make', 'GPSLatitude'] }); } catch { ex = null; }
  lap('exif');

  const isHeic = /\.(heic|heif)$/i.test(name);
  let bmp, decoder = 'native';
  if (isHeic && nativeHeic === false) { bmp = await heifDecode(buf); decoder = 'libheif'; }
  else {
    try { bmp = await createImageBitmap(blob); if (isHeic) nativeHeic = true; }
    catch (err) {
      if (!isHeic) throw err;
      nativeHeic = false; bmp = await heifDecode(buf); decoder = 'libheif';
    }
  }
  lap('decode');

  const s = Math.min(1, 1600 / Math.max(bmp.width, bmp.height));
  const W = Math.round(bmp.width * s), H = Math.round(bmp.height * s);
  const c = new OffscreenCanvas(W, H);
  const ctx = c.getContext('2d', { willReadFrequently: true });
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(bmp, 0, 0, W, H);
  bmp.close && bmp.close();
  const px = ctx.getImageData(0, 0, W, H).data;
  lap('resize');

  const prev = await c.convertToBlob({ type: 'image/jpeg', quality: 0.8 });
  const ts = Math.min(1, 360 / Math.max(W, H));
  const tc = new OffscreenCanvas(Math.round(W * ts), Math.round(H * ts));
  tc.getContext('2d').drawImage(c, 0, 0, tc.width, tc.height);
  const thumb = await tc.convertToBlob({ type: 'image/jpeg', quality: 0.72 });
  await save('p' + id + '.jpg', prev);
  await save('t' + id + '.jpg', thumb);
  lap('save');

  const m = measure(c, W, H);
  lap('measure');

  const all = await detect(px, W, H);
  lap('detect');

  const fa = [];
  for (const f of all.filter((f) => f[14] >= 0.8).slice(0, 12)) {
    const fd = { b: f.slice(0, 4).map((v) => Math.round(v * 10) / 10), c: Math.round(f[14] * 1000) / 1000 };
    if (Math.min(f[2], f[3]) >= 56) fd.e = await embed(px, W, H, f);
    fa.push(fd);
  }
  lap('embed');

  return {
    ms: T, decoder, w: W, h: H, ...m, nlo: all.length, fa,
    date: ex && ex.DateTimeOriginal ? String(ex.DateTimeOriginal) : null, cam: !!(ex && ex.Make), gps: !!(ex && ex.GPSLatitude),
  };
}

// --- sharpness, brightness, dHash, as in process.py (gray at 640 px, 3x3 Laplacian, 9x8 dHash)
function measure(c, W, H) {
  const s = Math.min(1, 640 / Math.max(W, H));
  const w = Math.round(W * s), h = Math.round(H * s);
  const gc = new OffscreenCanvas(w, h);
  const gx = gc.getContext('2d', { willReadFrequently: true });
  gx.imageSmoothingQuality = 'high';
  gx.drawImage(c, 0, 0, w, h);
  const d = gx.getImageData(0, 0, w, h).data;
  const g = new Float64Array(w * h);
  let sum = 0, dk = 0, bl = 0;
  for (let i = 0, j = 0; j < g.length; i += 4, j++) {
    const v = (d[i] * 4899 + d[i + 1] * 9617 + d[i + 2] * 1868 + 8192) >> 14; // OpenCV RGB->gray
    g[j] = v; sum += v; if (v < 20) dk++; if (v > 245) bl++;
  }
  const at = (x, y) => g[(y < 0 ? -y : y >= h ? 2 * h - y - 2 : y) * w + (x < 0 ? -x : x >= w ? 2 * w - x - 2 : x)];
  let s1 = 0, s2 = 0;
  const tiles = Array.from({ length: 16 }, () => [0, 0, 0]);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const l = at(x - 1, y) + at(x + 1, y) + at(x, y - 1) + at(x, y + 1) - 4 * g[y * w + x];
    s1 += l; s2 += l * l;
    const t = tiles[Math.min(3, (4 * y / h) | 0) * 4 + Math.min(3, (4 * x / w) | 0)];
    t[0] += l; t[1] += l * l; t[2]++;
  }
  const n = w * h, varOf = (a, b, k) => b / k - (a / k) ** 2;
  // dHash: 9x8 area average
  const cell = [];
  for (let r = 0; r < 8; r++) for (let q = 0; q < 9; q++) {
    const x0 = Math.floor(q * w / 9), x1 = Math.floor((q + 1) * w / 9), y0 = Math.floor(r * h / 8), y1 = Math.floor((r + 1) * h / 8);
    let a = 0; for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) a += g[y * w + x];
    cell.push(a / ((x1 - x0) * (y1 - y0)));
  }
  let bits = '';
  for (let r = 0; r < 8; r++) for (let q = 0; q < 8; q++) bits += cell[r * 9 + q + 1] > cell[r * 9 + q] ? '1' : '0';
  return {
    sh: Math.round(varOf(s1, s2, n) * 10) / 10,
    shm: Math.round(Math.max(...tiles.map((t) => varOf(t[0], t[1], t[2]))) * 10) / 10,
    br: Math.round((sum / n) * 10) / 10, dk: Math.round((dk / n) * 1000) / 1000, bl: Math.round((bl / n) * 1000) / 1000,
    dh: BigInt('0b' + bits).toString(16).padStart(16, '0'),
  };
}

// --- YuNet: input BGR 0..255, padded to a multiple of 32; decoding as in OpenCV's FaceDetectorYN
async function detect(px, W, H) {
  const pw = Math.ceil(W / 32) * 32, ph = Math.ceil(H / 32) * 32, plane = pw * ph;
  const x = new Float32Array(3 * plane);
  for (let y = 0; y < H; y++) for (let q = 0; q < W; q++) {
    const i = (y * W + q) * 4, o = y * pw + q;
    x[o] = px[i + 2]; x[plane + o] = px[i + 1]; x[2 * plane + o] = px[i];
  }
  const out = await det.run({ input: new ort.Tensor('float32', x, [1, 3, ph, pw]) });
  const faces = [];
  for (const st of [8, 16, 32]) {
    const cols = pw / st, rows = ph / st;
    const cls = out['cls_' + st].data, obj = out['obj_' + st].data, bb = out['bbox_' + st].data, kp = out['kps_' + st].data;
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      const i = r * cols + c;
      const score = Math.sqrt(Math.min(1, Math.max(0, cls[i])) * Math.min(1, Math.max(0, obj[i])));
      if (score <= 0.5) continue;
      const cx = (c + bb[i * 4]) * st, cy = (r + bb[i * 4 + 1]) * st;
      const w = Math.exp(bb[i * 4 + 2]) * st, h = Math.exp(bb[i * 4 + 3]) * st;
      const f = [cx - w / 2, cy - h / 2, w, h];
      for (let k = 0; k < 5; k++) f.push((kp[i * 10 + 2 * k] + c) * st, (kp[i * 10 + 2 * k + 1] + r) * st);
      f.push(score);
      faces.push(f);
    }
  }
  faces.sort((a, b) => b[14] - a[14]);
  const keep = [], box = (f) => f.slice(0, 4).map((v) => Math.trunc(v));
  for (const f of faces) {
    const a = box(f);
    if (keep.every((k) => iou(a, box(k)) <= 0.3)) keep.push(f);
    if (keep.length >= 50) break;
  }
  return keep;
}
function iou(a, b) {
  const ix = Math.max(0, Math.min(a[0] + a[2], b[0] + b[2]) - Math.max(a[0], b[0]));
  const iy = Math.max(0, Math.min(a[1] + a[3], b[1] + b[3]) - Math.max(a[1], b[1]));
  const i = ix * iy;
  return i / (a[2] * a[3] + b[2] * b[3] - i);
}

// --- SFace: similarity transform to the 112x112 template, bilinear warp, RGB 0..255
async function embed(px, W, H, f) {
  const S = [0, 1, 2, 3, 4].map((k) => [f[4 + 2 * k], f[5 + 2 * k]]);
  const ms = S.reduce((a, p) => [a[0] + p[0] / 5, a[1] + p[1] / 5], [0, 0]);
  const md = TPL.reduce((a, p) => [a[0] + p[0] / 5, a[1] + p[1] / 5], [0, 0]);
  let nr = 0, ni = 0, den = 0;
  for (let k = 0; k < 5; k++) {
    const sx = S[k][0] - ms[0], sy = S[k][1] - ms[1], dx = TPL[k][0] - md[0], dy = TPL[k][1] - md[1];
    nr += dx * sx + dy * sy; ni += dy * sx - dx * sy; den += sx * sx + sy * sy;
  }
  const ar = nr / den, ai = ni / den;            // dst = (ar + i*ai) * src + t
  const tx = md[0] - (ar * ms[0] - ai * ms[1]), ty = md[1] - (ai * ms[0] + ar * ms[1]);
  const n2 = ar * ar + ai * ai;                  // inverse: src = conj(a)/|a|^2 * (dst - t)
  const x = new Float32Array(3 * 112 * 112), P = 112 * 112;
  for (let v = 0; v < 112; v++) for (let u = 0; u < 112; u++) {
    const du = u - tx, dv = v - ty;
    const sx = (ar * du + ai * dv) / n2, sy = (-ai * du + ar * dv) / n2;
    const x0 = Math.floor(sx), y0 = Math.floor(sy), fx = sx - x0, fy = sy - y0;
    for (let ch = 0; ch < 3; ch++) {
      const p = (xx, yy) => (xx < 0 || yy < 0 || xx >= W || yy >= H ? 0 : px[(yy * W + xx) * 4 + ch]);
      x[ch * P + v * 112 + u] = (1 - fy) * ((1 - fx) * p(x0, y0) + fx * p(x0 + 1, y0)) + fy * ((1 - fx) * p(x0, y0 + 1) + fx * p(x0 + 1, y0 + 1));
    }
  }
  const out = await rec.run({ data: new ort.Tensor('float32', x, [1, 3, 112, 112]) });
  const e = Array.from(out.fc1.data), n = Math.hypot(...e) + 1e-9;
  return e.map((v) => Math.round((v / n) * 1e5) / 1e5);
}
