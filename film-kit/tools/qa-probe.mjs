// QA probe: scan a whole HTML film for the layout defects that kept reaching review.
//   node tools/qa-probe.mjs film/<name> [--step 0.25] [--fmt 16x9] [--min-font 20] [--dwell 2] [--safe 0.03]
// Reports, per defect, the first time it is seen and how long it persists:
//   clipped   text cut by its own box (scrollWidth > clientWidth with overflow not visible)
//   spills    text ink outside its nearest card (an ancestor with a background, border or shadow)
//   offscreen text ink outside the title-safe area (5% margin)
//   occluded  another element is painted on top of the text (content behind content)
//   overlap   two separate text blocks intersect (labels touching / stacked)
//   emoji     emoji or pictographic glyphs used as icons (use the icon font instead)
//   tiny      font smaller than --min-font px
//   empty     a visible pill/chip with no content (a status label whose text is not set yet) — hide with :empty
// Elements mid-transition (scene root translated) or faded below 0.9 opacity are skipped, and a defect must
// persist for --dwell consecutive samples, so only held frames are reported. Exit code 1 when anything is found.
// INTENTIONAL overlays (a stamp over a list, a toast over an app bar, a chip flying over a panel) must be declared
// with data-qa="overlay" on the overlaying element; undeclared overlap/occlusion is a defect.
import http from 'node:http'; import { readFile } from 'node:fs/promises'; import { join, extname } from 'node:path';
import { chromium } from 'playwright';
const ROOT = new URL('..', import.meta.url).pathname;
const argv = process.argv.slice(2), dir = argv[0];
const opt = (k, d) => { const i = argv.indexOf(k); return i > 0 ? argv[i + 1] : d; };
const step = +opt('--step', 0.25), fmt = opt('--fmt', '16x9'), minFont = +opt('--min-font', 20), dwell = +opt('--dwell', 2), safe = +opt('--safe', 0.03);
const MT = { '.html': 'text/html', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.css': 'text/css' };
const server = http.createServer(async (q, r) => {
  try { const p = join(ROOT, decodeURIComponent(q.url.split('?')[0])); const buf = await readFile(p); r.writeHead(200, { 'content-type': MT[extname(p)] || 'application/octet-stream' }); r.end(buf); }
  catch { r.writeHead(404); r.end(); }
});
await new Promise(r => server.listen(0, r));
const [W, H] = fmt === '9x16' ? [1080, 1920] : [1920, 1080];
const b = await chromium.launch({ channel: 'chrome' }); const pg = await b.newPage({ viewport: { width: W, height: H } });
const errs = []; pg.on('pageerror', e => errs.push(String(e)));
pg.on('response', r => { if (r.status() >= 400 && !/favicon/.test(r.url())) errs.push(`HTTP ${r.status()} ${r.url()}`); });
await pg.goto(`http://127.0.0.1:${server.address().port}/${dir}/film/index.html?fmt=${fmt}`);
await pg.evaluate(() => window.READY);
// hit-testing: full-frame SVG/canvas layers must not count as "on top" unless a drawn shape is actually there
await pg.addStyleTag({ content: 'svg{pointer-events:none!important} svg *{pointer-events:visiblePainted!important} canvas,.vignette{pointer-events:none!important}' });
const total = await pg.evaluate(() => window.DURATION);
if (!total || errs.length) { console.error('qa-probe: film failed to load:\n  ' + (errs.join('\n  ') || 'window.DURATION missing')); await b.close(); server.close(); process.exit(2); }

const runs = new Map();   // key -> {kind, text, first, cur, best, detail}
for (let t = 0.1, idx = 0; t < total; t += step, idx++) {
  const hits = await pg.evaluate(({ t, W, H, minFont, safe }) => {
    window.seek(t); const out = []; const cs = (e) => getComputedStyle(e);
    const settled = (e) => {
      let op = 1;
      for (let n = e; n && n !== document.body; n = n.parentElement) {
        const s = cs(n); if (s.display === 'none' || s.visibility === 'hidden') return false;
        op *= +s.opacity; if (op < 0.9) return false;
        if (s.transform !== 'none') { const m = new DOMMatrix(s.transform); const r = n.getBoundingClientRect(); if (r.width >= W * 0.95 && Math.abs(m.e) > 2) return false; }
      }
      return true;
    };
    const boxy = (s) => s.backgroundColor !== 'rgba(0, 0, 0, 0)' || s.backgroundImage !== 'none' || (s.borderStyle !== 'none' && parseFloat(s.borderWidth) > 0) || s.boxShadow !== 'none';
    const texts = [];
    for (const e of document.querySelectorAll('body *')) {
      if (['SCRIPT', 'STYLE'].includes(e.tagName)) continue;
      const own = [...e.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim());
      if (!own.length || !settled(e)) continue;
      const rg = document.createRange(); rg.selectNodeContents(e); const tr = rg.getBoundingClientRect();
      if (tr.width < 2 || tr.height < 2) continue;
      const ink = { left: tr.left, right: tr.right, top: tr.top + tr.height * 0.2, bottom: tr.bottom - tr.height * 0.22 }; ink.width = ink.right - ink.left; ink.height = ink.bottom - ink.top;
      const txt = e.textContent.trim().replace(/\s+/g, ' ').slice(0, 48), s = cs(e), icon = e.classList.contains('ic');
      texts.push({ e, tr: ink, txt, icon, declared: !!e.closest('[data-qa=overlay]') });
      if (!icon && /\p{Extended_Pictographic}/u.test(own.map(n => n.textContent).join(''))) out.push(['emoji', txt, '']);
      if (!icon && parseFloat(s.fontSize) < minFont) out.push(['tiny', txt, s.fontSize]);
      if (e.scrollWidth > e.clientWidth + 3 && s.overflow !== 'visible') out.push(['clipped', txt, `${e.scrollWidth - e.clientWidth}px`]);
      const mx = W * safe, my = H * safe;
      const inFrame = ink.right > 0 && ink.left < W && ink.bottom > 0 && ink.top < H;   // parked fully outside = invisible, not a defect
      if (inFrame && (ink.left < mx - 2 || ink.right > W - mx + 2 || ink.top < my - 2 || ink.bottom > H - my + 2)) out.push(['offscreen', txt, '']);
      for (let a = e.parentElement; a && a !== document.body; a = a.parentElement) {
        const as = cs(a); if (!boxy(as)) continue; const ar = a.getBoundingClientRect(); if (ar.width >= W * 0.95) break;
        const over = Math.max(ink.right - ar.right, ar.left - ink.left, ink.bottom - ar.bottom, ar.top - ink.top);
        if (over > 2) out.push(['spills', txt, `${Math.round(over)}px`]);
        break;
      }
      // occlusion: sample points across the glyph line; the top-most PAINTING element must be the text, its own box,
      // a descendant, or a declared overlay. Transparent containers (caption lines, wrappers) are looked through.
      let px = 0, py = 0;
      const paints = (n) => {
        if (n instanceof SVGElement || ['IMG', 'VIDEO', 'CANVAS'].includes(n.tagName)) return true;
        let op = 1; for (let a = n; a && a !== document.body; a = a.parentElement) op *= +cs(a).opacity; if (op < 0.05) return false;
        const ns = cs(n); if (boxy(ns)) return true;
        if (![...n.childNodes].some(c => c.nodeType === 3 && c.textContent.trim())) return false;
        const r = document.createRange(); r.selectNodeContents(n); const q = r.getBoundingClientRect();   // text-only: paints only where its glyphs are
        return px >= q.left && px <= q.right && py >= q.top + q.height * 0.2 && py <= q.bottom - q.height * 0.22;
      };
      const ys = ink.top + ink.height / 2; let occ = null;
      for (const fx of [0.12, 0.5, 0.88]) {
        const x = ink.left + ink.width * fx; if (x < 0 || x > W || ys < 0 || ys > H) continue;
        px = x; py = ys; const peeled = []; let top = document.elementFromPoint(x, ys);
        while (top && top !== e && !e.contains(top) && !top.contains(e) && !paints(top) && peeled.length < 12) { peeled.push([top, top.style.pointerEvents]); top.style.pointerEvents = 'none'; top = document.elementFromPoint(x, ys); }
        peeled.forEach(([n, v]) => { n.style.pointerEvents = v; });
        if (top && top !== e && !e.contains(top) && !top.contains(e) && !top.closest('[data-qa=overlay]') && !e.closest('[data-qa=overlay]')) { occ = top; break; }
      }
      if (occ) out.push(['occluded', txt, `by <${occ.tagName.toLowerCase()}${occ.className && typeof occ.className === 'string' ? '.' + occ.className.split(' ')[0] : ''}> "${(occ.textContent || '').trim().slice(0, 24)}"`]);
    }
    for (const e of document.querySelectorAll('body *')) {   // empty pills/chips
      if (e.children.length || e.textContent.trim() || e instanceof SVGElement || e.closest('[data-qa]')) continue;
      const s = cs(e); if (!boxy(s)) continue; const r = e.getBoundingClientRect();
      if (r.width < 12 || r.height < 6 || r.width > 400 || r.width < r.height * 1.4) continue;
      if (parseFloat(s.borderTopLeftRadius) < r.height / 3 || !settled(e)) continue;
      const sib = e.parentElement ? [...e.parentElement.children].filter(c => !c.children.length && !c.textContent.trim()).length : 0;
      if (sib >= 3) continue;   // a grid of tiles is drawing, not a missing label
      if (r.right > 0 && r.left < W && r.bottom > 0 && r.top < H) out.push(['empty', (e.className || e.tagName).toString().slice(0, 30), `${Math.round(r.width)}x${Math.round(r.height)}px at ${Math.round(r.left)},${Math.round(r.top)}`]);
    }
    for (let i = 0; i < texts.length; i++) for (let j = i + 1; j < texts.length; j++) {
      const A = texts[i], B = texts[j]; if (A.e.contains(B.e) || B.e.contains(A.e) || A.declared || B.declared) continue;
      const w = Math.min(A.tr.right, B.tr.right) - Math.max(A.tr.left, B.tr.left), h = Math.min(A.tr.bottom, B.tr.bottom) - Math.max(A.tr.top, B.tr.top);
      if (w <= 0 || h <= 0) continue; const small = Math.min(A.tr.width * A.tr.height, B.tr.width * B.tr.height);
      if (w * h > 100 && w * h > 0.2 * small) out.push(['overlap', `${A.txt} × ${B.txt}`, `${Math.round(w)}x${Math.round(h)}px`]);
    }
    return out;
  }, { t, W, H, minFont, safe });
  const seen = new Set();
  for (const [kind, text, detail] of hits) {
    const k = kind + '|' + text; if (seen.has(k)) continue; seen.add(k);
    const r = runs.get(k) || { kind, text, first: null, cur: 0, best: 0, last: -9, detail };
    r.cur = r.last === idx - 1 ? r.cur + 1 : 1; r.last = idx; if (r.cur >= dwell && r.first === null) r.first = t - step * (dwell - 1);
    r.best = Math.max(r.best, r.cur); r.detail = r.detail || detail; runs.set(k, r);
  }
}
const found = [...runs.values()].filter(r => r.best >= dwell).sort((a, b) => a.first - b.first);
const order = ['occluded', 'overlap', 'spills', 'clipped', 'empty', 'emoji', 'tiny', 'offscreen'];
for (const kind of order) {
  const rows = found.filter(r => r.kind === kind); if (!rows.length) continue;
  console.log(`\n${kind.toUpperCase()} (${rows.length})`);
  for (const r of rows) console.log(`  ${r.first.toFixed(2).padStart(7)}s  ${(r.best * step).toFixed(2)}s held  ${r.text}  ${r.detail}`);
}
console.log(`\nqa-probe: ${found.length} held defect(s) over ${total.toFixed(1)}s at ${step}s steps (${fmt})`);
await b.close(); server.close(); process.exit(found.length ? 1 : 0);
