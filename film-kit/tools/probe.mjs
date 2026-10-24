// Scan a film for text overflow: text wider than its own box, text spilling out of its card ancestor, or off-screen.
import http from 'node:http'; import { readFile } from 'node:fs/promises'; import { join, extname } from 'node:path';
import { chromium } from 'playwright';
const ROOT = new URL('..', import.meta.url).pathname, dir = process.argv[2], step = +(process.argv[3] || 0.5);
const MT = { '.html': 'text/html', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.json': 'application/json', '.png': 'image/png' };
const server = http.createServer(async (q, r) => { try { const p = join(ROOT, decodeURIComponent(q.url.split('?')[0])); const buf = await readFile(p); r.writeHead(200, { 'content-type': MT[extname(p)] || 'application/octet-stream' }); r.end(buf); } catch { r.writeHead(404); r.end(); } });
await new Promise(r => server.listen(0, r));
const b = await chromium.launch({ channel: 'chrome' }); const pg = await b.newPage({ viewport: { width: 1920, height: 1080 } });
await pg.goto(`http://127.0.0.1:${server.address().port}/${dir}/film/index.html?fmt=16x9`); await pg.evaluate(() => window.READY);
const total = await pg.evaluate(() => window.DURATION); const seen = new Map();
for (let t = 0.25; t < total; t += step) {
  const hits = await pg.evaluate((t) => { window.seek(t); const out = [];
    const vis = (e) => { for (let n = e; n && n !== document.body; n = n.parentElement) { const s = getComputedStyle(n); if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity < 0.05) return false; } return true; };
    for (const e of document.querySelectorAll('body *')) {
      if (!e.childNodes.length || ![...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
      if (!vis(e)) continue; const r = e.getBoundingClientRect(); if (!r.width) continue;
      const txt = e.textContent.trim().slice(0, 40);
      if (e.scrollWidth > e.clientWidth + 3 && getComputedStyle(e).overflow !== 'visible') out.push(['clipped', txt]);
      const rg = document.createRange(); rg.selectNodeContents(e); const tr = rg.getBoundingClientRect();
      if (tr.right > 1920 + 2 || tr.left < -2 || tr.bottom > 1082 || tr.top < -2) out.push(['offscreen', txt]);
      for (let a = e.parentElement; a && a !== document.body; a = a.parentElement) {
        const s = getComputedStyle(a); const boxy = s.backgroundColor !== 'rgba(0, 0, 0, 0)' || s.backgroundImage !== 'none' || s.borderStyle !== 'none';
        if (!boxy || a.getBoundingClientRect().width > 1800) continue; const ar = a.getBoundingClientRect();
        if (tr.right > ar.right + 2 || tr.left < ar.left - 2 || tr.bottom > ar.bottom + 3) out.push(['spills', txt, Math.round(Math.max(tr.right - ar.right, ar.left - tr.left, tr.bottom - ar.bottom))]);
        break;
      }
      if (tr.width > r.width + 4) out.push(['wider', txt, Math.round(tr.width - r.width)]);
    }
    return out; }, t);
  for (const h of hits) { const k = h[0] + '|' + h[1]; if (!seen.has(k)) seen.set(k, [t.toFixed(2), h[2] ?? '']); }
}
for (const [k, [t, d]] of seen) console.log(t.padStart(7), k, d);
await b.close(); server.close();
