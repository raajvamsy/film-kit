// Deterministic frame capture. Two film kinds:
//   SVG  : <film>/film.svg exposing window.__seek(t), __TOTAL, __ready          (tools/build.mjs output)
//   HTML : <film>/film/index.html on the motion engine (tools/engine/core.js): window.seek(t), DURATION, READY
//          served over a local http server (fonts and scripts load as in a browser), format via ?fmt=
//
//   node tools/record.mjs experiments/<film>                         # all frames  -> frames[-<fmt>]/
//   node tools/record.mjs experiments/<film> --at 1.2,4.6            # stills only -> stills[-<fmt>]/
//   node tools/record.mjs experiments/<film> --fmt 9x16              # HTML films: any format in film.json "formats"
//   --workers N (default 6 for frames)   parallel pages · frames RESUME by default (missing only) · --fresh to redo all
//
// fps and size come from film.json. Never use Playwright's recordVideo: it is ~1 Mbit/s VP8 and bands everything.
import { chromium } from 'playwright';
import { readFileSync, rmSync, mkdirSync, existsSync, statSync, createReadStream, renameSync } from 'node:fs';
import { join, resolve, dirname, extname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import http from 'node:http';

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const dir = resolve(process.argv[2]);
const arg = k => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : null; };
const stills = arg('--at')?.split(',').map(Number) ?? null;
const extraQuery = arg('--query');   // e.g. shots=L12  (dev isolation: load only some shot files)
const outOverride = arg('--out');
const DSF = Number(arg('--dsf') ?? 1);   // deviceScaleFactor: 2 = 4K capture of a 1080p film (crisp, not upscaled)
const RANGE = arg('--range')?.split(':').map(Number) ?? null;   // frame index range a:b (chunked renders)     // write stills/frames here instead of <film>/stills-<fmt>
const spec = JSON.parse(readFileSync(join(dir, 'film.json'), 'utf8'));
const html = existsSync(join(dir, 'film/index.html'));
const fmt = arg('--fmt') ?? (spec.formats ? Object.keys(spec.formats)[0] : null);
const [W, H] = spec.formats?.[fmt] ?? spec.size, FPS = spec.fps;

let server, url;
if (html) {
  const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.png': 'image/png',
                 '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.wav': 'audio/wav' };
  server = http.createServer((req, res) => {
    const f = join(ROOT, decodeURIComponent(req.url.split('?')[0]));
    if (!f.startsWith(ROOT) || !existsSync(f) || statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'Content-Type': MIME[extname(f)] || 'application/octet-stream' });
    createReadStream(f).pipe(res);
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  url = `http://127.0.0.1:${server.address().port}/${relative(ROOT, join(dir, 'film/index.html'))}?fmt=${fmt}${extraQuery ? '&' + extraQuery : ''}`;
} else url = 'file://' + join(dir, 'film.svg');

// One Chrome PROCESS per worker: pages inside one browser share a single GPU/compositor process, so 6 pages
// rendered no faster than 1 (measured 2.2 fps either way on the grain-heavy 09-reel).
const launch = () => chromium.launch({ channel: 'chrome', headless: true,
  args: ['--force-color-profile=srgb', '--disable-lcd-text', '--font-render-hinting=none'] });
const browsers = [];
const errors = [];
const api = html ? { ready: 'READY', seek: 'seek', total: 'DURATION' } : { ready: '__ready', seek: '__seek', total: '__TOTAL' };
async function openPage() {
  const browser = await launch(); browsers.push(browser);
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: DSF });
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if ((m.type() === 'error' && !/Failed to load resource/.test(m.text())) || /font/.test(m.text())) errors.push(m.text()); });
  page.on('response', r => { if (r.status() >= 400 && !r.url().endsWith('/favicon.ico')) errors.push(`${r.status()} ${r.url()}`); });
  await page.emulateMedia({ reducedMotion: 'reduce' });   // stop any live-preview loop
  await page.goto(url);
  await page.waitForFunction(k => window[k], api.ready, { timeout: 15000 });
  await page.evaluate(k => window[k], api.ready);
  if (errors.length) throw new Error('page errors:\n' + errors.join('\n'));
  return page;
}
const first = await openPage();
const total = await first.evaluate(k => window[k], api.total);

const suffix = html && spec.formats ? `-${fmt}` : '';
const outDir = outOverride ? resolve(outOverride) : join(dir, (stills ? 'stills' : 'frames') + suffix);
// Frames RESUME by default: every frame is a pure function of t, so frames already on disk from an interrupted
// run are kept and only the missing ones are captured. --fresh wipes them. Stills are always redone.
if (stills || process.argv.includes('--fresh')) rmSync(outDir, { recursive: true, force: true });
mkdirSync(outDir, { recursive: true });

const times = stills ?? Array.from({ length: Math.round(total * FPS) }, (_, i) => i / FPS);
const name = i => (stills ? `t${times[i].toFixed(2)}.png` : `f${String(i).padStart(5, '0')}.png`);
const todo = times.map((_, i) => i).filter(i => !RANGE || (i >= RANGE[0] && i < RANGE[1])).filter(i => stills || !existsSync(join(outDir, name(i))) || statSync(join(outDir, name(i))).size === 0);
// Parallel capture: N pages, each seeks independently (deterministic seek(t) makes this safe).
const N = Math.max(1, Math.min(Number(arg('--workers') ?? (stills ? 1 : 6)), todo.length || 1));
const pages = [first, ...await Promise.all(Array.from({ length: N - 1 }, openPage))];
const t0 = Date.now();
let done = 0;
if (todo.length < times.length) console.log(`  resuming: ${times.length - todo.length} frames already on disk, ${todo.length} to capture`);
await Promise.all(pages.map(async (page, w) => {
  for (let j = w; j < todo.length; j += N) {
    const i = todo[j];
    await page.evaluate(([k, t]) => window[k](t), [api.seek, times[i]]);
    const tmp = join(outDir, name(i) + '.part.png');
    await page.screenshot({ path: tmp });
    renameSync(tmp, join(outDir, name(i)));     // atomic: a killed run never leaves a half-written frame
    if (!stills && ++done % 240 === 0) console.log(`  ${done}/${todo.length}  ${((Date.now() - t0) / 1000).toFixed(0)}s  (${N} workers)`);
  }
}));
if (errors.length) throw new Error('page errors during capture:\n' + errors.join('\n'));
console.log(`${todo.length} ${stills ? 'stills' : 'frames'} @ ${W}x${H} -> ${outDir} (dsf ${DSF}) in ${((Date.now() - t0) / 1000).toFixed(0)}s with ${N} workers`);
await Promise.all(browsers.map(b => b.close()));
server?.close();
