# New Preview — Visual Plan (Stage 1, awaiting approval)

Deliverables: (1) an animated technical web page, then (2) a ~90s narrated 16:9 film cut from it.
Audience: management, devs, architects. The page carries the depth; the film carries the story.
Reference engine (read-only): ~/personal/video/experiments/09-reel. Nothing is written there.

Number rule: every figure shows its source label — **measured** (date, project) or **estimate**.

---

## Facts we will use

### Constraints (why the design looks the way it does)
- One preview container = **2.5 GB memory cap**, shared by **5–10 users** (~200–400 MB each). CPU uncapped.
- So: **no long-running server per project** (no Metro/Expo dev server). Short-lived builds + disk caches only.
- Nothing derived from one user's project code may be shared with another project.

### Old preview (esbuild)
- Every preview: full npm install into the project (**2.3 GB node_modules per project**), then esbuild → **one 6.8 MB bundle**.
- Every edit rebuilds the whole app.
- Measured 2026-09-16, small project "rn": ~**2m06s** clean; npm install pins the container at the **2.5 GB cap**.

### New preview (Metro split bundle)
- Bundle split into 5 chunks: **vendor · extras · user · modified · boot**. An edit rebuilds only *modified* + *boot*.
- **Vendor store shared across projects** on the device (hardlinks) — installed once, reused.
- **Disk Metro cache**, split: library transforms shared, project-file transforms kept per project.
- **Fast path + live reload**: small edits hot-patch the open preview (~0.3s patch).
- Safety: memory-aware **admission gate**, Metro **heap cap** (1 GB on this container), **stall watchdog** that kills hung builds.
- **Pages working set (opt-in)**: build home, login, edited and opened pages; others are stubs built on first open.

### Problems we hit → fixes (architect section)
| Problem | Fix |
|---|---|
| Single build OOM-killed at 2.5 GB | Heap cap on Metro + admission gate |
| npm wrote 2.6 GB per project, page cache filled memory | Vendor installed once, hardlinked into projects |
| Gate deadlocked by counting file cache as "used" | Count working set (current − inactive file cache) |
| Hung build held memory forever | Stall watchdog + kill whole process tree |
| Vendor patches failed on a locked store | Patch at vendor install time, before lock |
| Big projects (PNB) ~21 min clean | Per-page working set |

### Numbers
| | Old | New | Source |
|---|---|---|---|
| Small project, clean build | ~2m06s | 47–142s | measured 2026-09-02/16 |
| Small project, edit → visible | full rebuild (~2 min) | 9.6–12.7s; hot patch ~0.3s | measured 2026-09-03 |
| First build on empty container | — | 287s, pins 2.5 GB | measured 2026-09-03 |
| Peak memory, warm rebuild | 2.5 GB (cap) | 2.2 GB, no OOM | measured 2026-09-02 |
| Disk per project | 2.3 GB node_modules | vendor shared | measured |
| Big project (PNB, 3381 files) clean | not measured | ~21 min all pages → **1–2 min working set** | 21 min measured 2026-10-07; 1–2 min **estimate** |
| Big project edit | not measured | **2–5s** | **estimate** |

Gaps flagged on screen: no page counts for the small project; no old-path run on PNB.

---

## Part 1 — Web page outline
1. **Hero**: "Preview, rebuilt for shared containers" + 3 stat tiles (clean time, edit time, memory).
2. **The constraint**: animated container bar filling to 2.5 GB with 5–10 user slots.
3. **Old pipeline**: animated flow npm install → esbuild → one bundle; every edit restarts it.
4. **New pipeline**: flow with shared vendor store, split chunks; an edit lights up only *modified* + *boot*.
5. **Problems → fixes**: six cards, each flips from symptom to fix.
6. **Numbers**: bar charts small vs big project, measured vs estimate styled differently.
7. **Big projects**: working set — 800 pages, only 5 lit; others build when opened.
8. **Controls**: the two wm_rn_config.json switches (fallback profile, pages).

## Part 2 — Film script (~90s, 16:9, Gemini VO, one TTS call)
| # | Beat | Picture | Voice (one explaining sentence) | s |
|---|---|---|---|---|
| 1 | Hook | Progress bar crawling, clock spinning | Every preview used to rebuild your whole app, every time. | 6 |
| 2 | Constraint | One container, 2.5 GB, ten user slots filling | And it all runs in one small shared container, serving up to ten people at once. | 9 |
| 3 | Old way | npm install floods memory → one 6.8 MB bundle | The old builder installed everything per project and produced one big bundle — so memory hit the ceiling. | 11 |
| 4 | Turn | Bundle splits into five chunks | The new preview splits the app into layers that change at different speeds. | 8 |
| 5 | Shared vendor | Library block installed once, linked into many projects | Libraries install once and are shared, so projects stop copying gigabytes. | 9 |
| 6 | Edit loop | Edit → only "modified" chunk lights → hot patch | When you edit a page, only that small piece rebuilds and drops into the open preview. | 10 |
| 7 | Safety | Gate, heap cap, watchdog as guards around memory bar | Guards keep each build inside its memory budget and stop a stuck build from blocking others. | 10 |
| 8 | Proof | Bars: clean 2m06s → ~1 min; edit 2 min → ~10s | On a typical app, a clean preview takes about half the time, and edits show up in seconds. | 10 |
| 9 | Big apps | 800 page grid, a handful lit (labelled estimate) | For very large apps, building only the pages you use is expected to cut twenty minutes to one or two. | 10 |
| 10 | Sign | "New preview — on by default" + fallback line | It's on by default, and you can switch back to the classic builder anytime. | 7 |

## Next stages (each stops for your OK)
2 beat grid · 3 build (page first, then film on the 09-reel HTML engine) · 4 audio (Gemini TTS, key via env only) · 5 critique ≥3 rounds · 6 render.
