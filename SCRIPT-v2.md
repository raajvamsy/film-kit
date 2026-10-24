# New Preview film — v2 script (awaiting OK)

Explainer, ~95 s, 16:9 first. Built as a story about one idea: **most of your app isn't yours — so stop rebuilding it.**

## What changed from v1 (your notes)
1. **Background** — the drifting rounded slabs (read as the MemoryLayer mark) are gone. New world: blueprint dot-grid + slow flowing *wave lines* (WaveMaker), soft blue light. No pills anywhere.
2. **23–24 s / 32 s glitches** — scene transitions rebuilt; nothing appears and vanishes inside half a second; every element enters, holds ≥1.5 s, exits by motion.
3. **Spacing** — every element gets its own zone on a 12-column grid; no overlaps (the "boot behind the window" bug).
4. **Music** — new score: warm piano + soft pulse, different key/tempo, written for this film (not the motion-reel-kit groove used for MemoryLayer).
5. **First user pays once** — new dedicated shot: WaveMaker's built-in packages install once per machine; every later project/user just links them.
6. **Missed facts now in** — npm skipped unless you add your own packages · caches keyed by content so they can't go stale · unchanged chunks served as 304 · build walks ~159 modules instead of ~2,730 · shared transform cache 97 s → 12.7 s.
7. **New voice** — `Erinome` (clear, crisp female), "senior engineer walking you through a whiteboard" tone — brisker and more explanatory than MemoryLayer's calm `Orus`.

## Facts used (all from memory/commits; estimates labelled on screen)
| Claim | Source |
|---|---|
| 2,723 modules bundled, only 26 are project source | measured 2026-09-02 |
| Container 2.5 GB cap, 5–10 users | measured / constraint |
| Old: 2.3 GB node_modules per project, one 6.8 MB bundle, npm pins memory at cap | measured 2026-09-16 |
| WaveMaker packages install once per machine (~1.6 GB, first build only), hardlinked into projects | commits 2284c4e1, shared-node-modules.ts |
| npm install skipped when the shared tree satisfies every dependency; runs only for packages you add | `computeVendorDelta` in shared-node-modules.ts |
| Cache keys = lockfile hash + builder-version fingerprint; new rn-app version → new folder, old pruned | vendor-cache.js, 6dde0c80, 2faafad3 |
| Unchanged chunks keep their timestamp → browser gets 304 | 5f0ac417 |
| Boundary mode: ~159 modules walked vs ~2,730 | measured 2026-09-20 |
| Shared transform cache: cold 97 s → warm 12.7 s, peak memory ~halved | measured 2026-09-02 |
| Edit → visible ~10 s (9.6–12.7 s); hot patch 312 ms vs 2,079 ms restart, page state kept | measured 2026-09-03 / 2026-09-20 |
| Admission gate, heap cap, CPU-aware watchdog | 6ae41fe9, 67254f89 |
| Big app 21 min → 1–2 min with working set | 21 min measured; 1–2 min **estimate** |

## Shot list
| # | Act | Picture (motion) | Voice | ~s |
|---|---|---|---|---|
| 1 | Problem | Studio-like canvas; a label's text changes; a giant "Rebuilding…" counter races 0 → 2,723 modules | You change one word on one page… and preview rebuilds the entire app. | 6 |
| 2 | | Counter freezes; 2,697 modules fade to grey, **26** stay lit green — "only 26 were yours" | We counted. Of twenty-seven hundred modules, only twenty-six were actually yours. | 7 |
| 3 | | Zoom out: one 2.5 GB container, ten developer seats light up | And every rebuild happens in one small shared box, serving up to ten developers. | 7 |
| 4 | | Three projects each copy a 2.3 GB library block in; memory column slams into the cap, red pulse | Each project copied gigabytes of the same libraries, and memory hit the ceiling. | 8 |
| 5 | Idea | Wave wipe to light world. Big line: **"Build what's yours."** grey modules lift away as one block | So the new preview flips it around: build only what's yours. | 6 |
| 6 | | "WaveMaker built-ins" block installs once (progress, "first build only"), then 4 projects/users connect with link lines; a "npm install — skipped" stamp | Everything WaveMaker ships is installed once per machine. The first build pays for it, and every project after that simply links to it. | 10 |
| 7 | | One project adds a package → only a small "your packages" brick gets installed | npm only runs when you add packages of your own. | 5 |
| 8 | | Five layers stack by change speed: built-ins · your packages · your pages · this edit · wiring | The app is cut into layers, by how often they change. | 7 |
| 9 | | Studio edit → "this edit" chip flies into the open preview, page content swaps in place, timer 0.3 s, no page reload (app shell and page stay open; the widget area re-renders) | Change a page, and only that slice rebuilds, patched into the preview you already have open. | 9 |
| 10 | | Fingerprint/keys visual: inputs → hash → cache drawer; change an input → new key, old drawer emptied; browser gets "304 · not modified" for unchanged layers | Caches are keyed by fingerprints of their inputs, so they never serve stale code, and your browser only downloads what actually changed. | 9 |
| 11 | | Guards around a memory lane: gate queues a build, heap cap, watchdog removes a stuck build | Guards keep every build inside its budget, and clear out anything that gets stuck. | 7 |
| 12 | Proof | Three measured stat cards: edit ~10 s vs ~2 min · warm cache 97 s → 12.7 s · walks 159 modules, not 2,730 | The result: edits in about ten seconds, warm builds seven times faster, and a fraction of the work. | 8 |
| 13 | | Page grid for a big app; most dim, a few lit; 21 min → 1–2 min (**estimate**) | For very large apps, building only the pages you open should take twenty minutes down to one or two. | 8 |
| 14 | Sign | WaveMaker-blue wave line resolves into the layer mark; "New Preview · on by default" + switch-back line | The new preview. On by default, and one setting away if you ever need the classic one. | 7 |

Formats: 16:9 now; 9:16 re-blocked after you approve the 16:9 cut.
