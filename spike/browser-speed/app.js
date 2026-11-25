// Browser speed spike: start N workers, feed them pictures, report times and compare with reference.json.
const $ = (id) => document.getElementById(id);
const EXT = /\.(heic|heif|jpe?g|png)$/i;
let manifest = null, reference = null;

async function loadJSON(url) {
  try { const r = await fetch(url); return r.ok ? await r.json() : null; } catch { return null; }
}

async function startPool(n, backend) {
  const t0 = performance.now();
  const ws = await Promise.all(Array.from({ length: n }, () => new Promise((ok, bad) => {
    const w = new Worker(new URL('./worker.js', import.meta.url), { type: 'module' });
    w.onmessage = (e) => (e.data.type === 'ready' ? ok({ w, info: e.data }) : bad(new Error(e.data.error)));
    w.onerror = (e) => bad(new Error(e.message || 'Worker konnte nicht starten'));
    w.postMessage({ type: 'init', backend });
  })));
  return { ws, initMs: performance.now() - t0 };
}

async function runJobs(ws, jobs, onProgress) {
  const results = new Array(jobs.length);
  let next = 0, done = 0;
  await Promise.all(ws.map(({ w }) => new Promise((ok) => {
    const feed = () => {
      if (next >= jobs.length) return ok();
      const id = next++;
      w.onmessage = (e) => { results[id] = e.data.r; onProgress(++done, jobs.length); feed(); };
      w.postMessage({ type: 'job', id, ...jobs[id] });
    };
    feed();
  })));
  return results;
}

async function clearOpfs() {
  try { await (await navigator.storage.getDirectory()).removeEntry('spike', { recursive: true }); } catch { /* nothing to clear */ }
}

const median = (a) => { const s = [...a].sort((x, y) => x - y); return s.length ? s[(s.length - 1) >> 1] : NaN; };
const cos = (a, b) => a.reduce((s, v, i) => s + v * b[i], 0);
function iou(a, b) {
  const ix = Math.max(0, Math.min(a[0] + a[2], b[0] + b[2]) - Math.max(a[0], b[0]));
  const iy = Math.max(0, Math.min(a[1] + a[3], b[1] + b[3]) - Math.max(a[1], b[1]));
  return (ix * iy) / (a[2] * a[3] + b[2] * b[3] - ix * iy);
}
const ham = (a, b) => [...(BigInt('0x' + a) ^ BigInt('0x' + b)).toString(2)].filter((c) => c === '1').length;

function compare(jobs, rows) {
  if (!reference) return null;
  let refFaces = 0, found = 0, extra = 0, sims = [], shr = [], dh = [], meta = 0, n = 0;
  rows.forEach((r, i) => {
    const ref = reference.files[jobs[i].name];
    if (!ref || r.err) return;
    n++;
    refFaces += ref.fa.length;
    const used = new Set();
    for (const f of ref.fa) {
      let best = -1, bi = -1;
      r.fa.forEach((g, j) => { const v = iou(f.b, g.b); if (!used.has(j) && v > best) { best = v; bi = j; } });
      if (best >= 0.5) { found++; used.add(bi); if (f.e && r.fa[bi].e) sims.push(cos(f.e, r.fa[bi].e)); }
    }
    extra += r.fa.length - used.size;
    shr.push(r.sh / (ref.sh || 1));
    dh.push(ham(r.dh, ref.dh));
    if ((r.date || '').length > 0 === (ref.date !== 'None') && r.cam === ref.cam && r.gps === ref.gps) meta++;
  });
  return { n, refFaces, found, extra, simMedian: median(sims), simMin: Math.min(...sims), nSims: sims.length, shRatio: median(shr), dhMedian: median(dh), meta };
}

function report(kind, cfg, pool, jobs, rows, wallMs) {
  const ok = rows.filter((r) => r && !r.err);
  const errs = rows.length - ok.length;
  const per = wallMs / rows.length;
  const stages = {};
  for (const r of ok) for (const [k, v] of Object.entries(r.ms)) (stages[k] ||= []).push(v);
  const decoders = ok.reduce((a, r) => ((a[r.decoder] = (a[r.decoder] || 0) + 1), a), {});
  const cmp = kind === 'own' ? null : compare(jobs, rows);
  const py = reference && reference.python && reference.python[kind];
  const lines = [
    `Browser: ${navigator.userAgent}`,
    `Kerne laut Browser: ${navigator.hardwareConcurrency}, Rechenweg: ${cfg.backend} (SFace: ${pool.ws[0].info.recEp}), Worker: ${cfg.workers}, OPFS: ${pool.ws[0].info.opfs ? 'ja' : 'nein'}`,
    `Bilder: ${kind === 'own' ? 'eigener Ordner' : 'Testbilder ' + kind.toUpperCase()}, ${rows.length} Stück, ${errs} Fehler${errs ? ' (' + [...new Set(rows.filter((r) => r && r.err).map((r) => r.err))].slice(0, 2).join('; ') + ')' : ''}`,
    `Start der Worker inkl. Modelle laden: ${(pool.initMs / 1000).toFixed(1)} s`,
    `Gesamt: ${(wallMs / 1000).toFixed(1)} s = ${per.toFixed(0)} ms pro Bild, hochgerechnet ${(per * 6000 / 60000).toFixed(0)} min für 6.000 Bilder`,
    `Median pro Schritt (ein Worker, ms): ` + Object.entries(stages).map(([k, v]) => `${k} ${median(v).toFixed(0)}`).join(', '),
    `Dekodiert mit: ` + Object.entries(decoders).map(([k, v]) => `${k} ${v}`).join(', '),
  ];
  if (py) lines.push(`Python (reference.py, ${reference.python.cpu} Kerne, 4 Prozesse): ${py.ms_per_picture} ms pro Bild, hochgerechnet ${(py.ms_per_picture * 6000 / 60000).toFixed(0)} min; Browser/Python = ${(per / py.ms_per_picture).toFixed(2)}`);
  if (cmp) lines.push(
    `Abgleich mit Python: Gesichter ${cmp.found} von ${cmp.refFaces} gefunden, ${cmp.extra} zusätzlich; ` +
    (cmp.nSims ? `SFace-Ähnlichkeit Median ${cmp.simMedian.toFixed(3)}, Minimum ${cmp.simMin.toFixed(3)} (${cmp.nSims} Gesichter); ` : '') +
    `Schärfe Browser/Python ${cmp.shRatio.toFixed(2)}; dHash-Abstand Median ${cmp.dhMedian} von 64 Bit; EXIF gleich in ${cmp.meta} von ${cmp.n}`);
  else if (kind !== 'own') lines.push('Kein Abgleich: testset/reference.json fehlt (reference.py laufen lassen).');
  $('out').innerHTML = '<table>' + lines.map((l) => { const i = l.indexOf(': '); return `<tr><th>${l.slice(0, i)}</th><td>${l.slice(i + 2)}</td></tr>`; }).join('') + '</table>';
  $('text').textContent = lines.join('\n');
  $('text').hidden = false; $('copy').hidden = false;
  window.spikeResult = { kind, cfg, wallMs, per, stages: Object.fromEntries(Object.entries(stages).map(([k, v]) => [k, median(v)])), decoders, cmp, errs, text: lines.join('\n') };
}

async function run(kind, jobs) {
  const cfg = { backend: $('backend').value, workers: +$('workers').value };
  document.querySelectorAll('button').forEach((b) => (b.disabled = true));
  $('out').innerHTML = ''; $('text').hidden = true; $('copy').hidden = true; window.spikeResult = null;
  try {
    await clearOpfs();
    $('status').textContent = `Starte ${cfg.workers} Worker und lade die Modelle …`;
    const pool = await startPool(cfg.workers, cfg.backend);
    const t0 = performance.now();
    const rows = await runJobs(pool.ws, jobs, (d, n) => ($('status').textContent = `${d} von ${n} Bildern …`));
    const wallMs = performance.now() - t0;
    pool.ws.forEach(({ w }) => w.terminate());
    $('status').textContent = 'Fertig.';
    report(kind, cfg, pool, jobs, rows, wallMs);
  } catch (err) {
    $('status').textContent = 'Fehler: ' + ((err && err.message) || err);
    window.spikeResult = { error: String((err && err.message) || err) };
  } finally {
    await clearOpfs();
    document.querySelectorAll('button').forEach((b) => (b.disabled = false));
  }
}

const testJobs = (kind) => (kind === 'iphone' ? Array(12).fill(manifest.iphone || []).flat() : manifest.files.map((f) => f[kind]))
  .map((name) => ({ name, src: new URL('testset/' + name, location.href).href }));
$('jpeg').onclick = () => manifest ? run('jpeg', testJobs('jpeg')) : ($('status').textContent = 'testset/manifest.json fehlt: erst prepare.py laufen lassen.');
$('heic').onclick = () => manifest ? run('heic', testJobs('heic')) : ($('status').textContent = 'testset/manifest.json fehlt: erst prepare.py laufen lassen.');
$('iphone').onclick = () => manifest ? run('iphone', testJobs('iphone')) : ($('status').textContent = 'testset/manifest.json fehlt: erst prepare.py laufen lassen.');
$('own').onclick = () => $('dir').click();
$('dir').onchange = () => {
  const files = [...$('dir').files].filter((f) => EXT.test(f.name) && !f.name.startsWith('._'));
  $('dir').value = '';
  if (files.length) run('own', files.map((f, i) => ({ name: 'own' + i + f.name.slice(f.name.lastIndexOf('.')), src: f })));
};
$('copy').onclick = () => navigator.clipboard.writeText($('text').textContent).then(() => ($('status').textContent = 'Kopiert.'));

manifest = await loadJSON('testset/manifest.json');
reference = await loadJSON('testset/reference.json');
const q = new URLSearchParams(location.search);
if (q.get('backend')) $('backend').value = q.get('backend');
if (q.get('workers')) $('workers').value = q.get('workers');
if (q.get('auto') === 'all' && manifest) {
  // every test set with both backends, one compact summary for copying
  const sum = [];
  for (const backend of ['wasm', 'webgpu']) for (const kind of ['jpeg', 'heic', 'iphone']) {
    $('backend').value = backend;
    await run(kind, testJobs(kind));
    const r = window.spikeResult;
    sum.push(r && r.text ? `${backend} ${kind}: ` + r.text.split('\n').filter((l) => /^(Gesamt|Median|Dekodiert|Python|Abgleich|Kerne)/.test(l)).join(' | ') : `${backend} ${kind}: Fehler ${r && r.error}`);
  }
  sum.unshift('Browser: ' + navigator.userAgent);
  $('text').textContent = sum.join('\n\n'); $('text').hidden = false; $('copy').hidden = false;
  $('out').innerHTML = ''; $('status').textContent = 'Alle Läufe fertig.';
  window.spikeAll = sum.join('\n\n');
} else if (q.get('auto') && manifest) run(q.get('auto'), testJobs(q.get('auto')));
