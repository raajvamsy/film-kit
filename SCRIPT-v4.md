# New Preview — v4 · detailed, ad-style · ~2 min · 16:9

**Style:** a launch ad that also teaches. Each chapter opens on a big title card, hard cuts land on the beat, the type is the subject, and something is moving in every frame. Every shot has one bold phrase on screen and one short spoken line.
**Stage:** a recreated WaveMaker Studio (header ▶ / ▾ Rebuild Preview, Pages list, phone canvas, properties panel) and the real WaveMaker logos. Background: blue wave lines on a dark "before" world, then a light "after" world.
**Voice:** Gemini "Puck": upbeat, confident, energetic. **Music:** a new driving electronic score with a drop at the turn (chapter 2).

## Review of v3: what it was missing
| Gathered fact | v3 | v4 |
|---|---|---|
| ▶ Play = clean build if no generated app, otherwise incremental; ▾ Rebuild Preview = always clean | partial | shot 1.1 + 2.3 |
| Old way: 2.3 GB node_modules per project, one 6.8 MB bundle, npm pins memory at the cap, ~2 min | ✗ | ch 1 |
| A single build got OOM-killed at 2.5 GB (before the guards) | ✗ | 1.4 |
| Built-ins install once per machine; the first build pays (~1.6 GB); every later project links in (hardlinks) | ✓ | 2.2 |
| Built-ins survive Rebuild Preview; a new rn-app version gets a fresh store; old ones auto-pruned | partial | 2.3 |
| npm runs only for packages you add (the "extras" layer); clean preview reinstalls just those | partial | 2.4 |
| Five layers: vendor · extras · user · modified · boot; an edit rebuilds the last two | ✗ | ch 3 |
| Library transforms shared across the machine: 97 s → 12.7 s, peak memory roughly halved | ✗ | 3.3 |
| Boundary mode: the build walks ~159 modules, not ~2,730 | proof only | 3.4 |
| Fast path: a small edit builds in ~2 s; hot patch 312 ms vs 2,079 ms restart, no page reload | partial | ch 4 |
| "Preview ready / failed" message in the app | ✗ | 4.3 |
| Caches keyed by content fingerprints; can't go stale; atomic publish; unchanged chunks → 304 | ✗ | ch 5 |
| Guards: memory-aware admission gate, heap cap, CPU-aware watchdog, per-project lock, other projects build side by side | partial | ch 5 |
| App generation skips prettify: 30 s → 10 s | ✗ | 3.5 |
| Working set: home, login, Common, edited and opened pages; other pages are stubs that build when opened; `pages` pins | partial | ch 6 |
| Big app (PNB, 3,381 files): 21 min → 1–2 min (**estimate**) | ✓ | 6.3 |
| Controls: on by default; `legacy-web-preview` to switch back; `allPages:false` to opt in | ✗ | ch 7 |

## Shot list (~2 min)
| # | Picture | On-screen phrase | VO |
|---|---|---|---|
| **0** | Logo sting: three blue waves draw on, "wavemaker", then "NEW PREVIEW" punches in | NEW PREVIEW | — |
| **CH 1 · THE WAIT** | title card slams | 01 · THE WAIT | |
| 1.1 | Studio header; cursor clicks ▶; toast "Building preview…" | One click. | You hit preview… |
| 1.2 | Counter races 0 → 2,723 modules; 2,697 grey, **26** green | Only 26 are yours. | …and it rebuilds twenty-seven hundred modules. Only twenty-six are yours. |
| 1.3 | Three projects each pull in a **2.3 GB** library copy → one **6.8 MB** bundle | Copy. Copy. Copy. | Every project copied gigabytes of the same libraries, into one giant bundle. |
| 1.4 | 2.5 GB container, ten developer seats; memory slams the cap; a build crashes | 2.5 GB. Ten people. | One small box, ten developers, and memory at the limit. |
| **CH 2 · THE FLIP** | music drops; wave wipe to light | 02 · BUILD ONLY WHAT'S YOURS | So we flipped it. Build only what's yours. |
| 2.1 | Split screen: "WaveMaker" stack vs "Yours" slice | Theirs vs yours | Everything WaveMaker ships is the same for every app. |
| 2.2 | Built-ins block installs once ("first build only · ~1.6 GB"), then links shoot to 4 projects | Install once. Link everywhere. | So it installs once per machine, and every project just links in. |
| 2.3 | Cursor ▾ → **Rebuild Preview**; the project folder wipes, the built-ins block stays lit; a version tag flips, a new store appears and the old one sweeps away | Even a full rebuild. | Even a full Rebuild Preview keeps them. New WaveMaker version? A fresh store, and the old one cleans itself up. |
| 2.4 | One project adds `react-konva`; a tiny "your packages" brick installs; stamp **npm install · skipped** on the others | npm only for your packages. | NPM only runs for packages you add. |
| **CH 3 · LAYERS** | title card | 03 · CUT INTO LAYERS | |
| 3.1 | Bundle splits into five layers, sorted by change speed | vendor · extras · user · modified · boot | The app is cut into layers by how often they change. |
| 3.2 | Edit pulse: only modified + boot light up | Edit = 2 layers | An edit only touches the last two. |
| 3.3 | Transform cache: a library file is done once per machine; bar 97 s → 12.7 s | Transformed once. | Library code is transformed once for the whole machine. Warm builds run seven times faster. |
| 3.4 | Graph walk: a full tree of 2,730 nodes trims to 159 | 159, not 2,730 | And each build walks a hundred and fifty-nine modules, not twenty-seven hundred. |
| 3.5 | App generation bar 30 s → 10 s | Generate in 10 s | Even code generation got three times faster. |
| **CH 4 · LIVE** | title card | 04 · SEE IT LIVE | |
| 4.1 | Studio canvas: change a button's colour in the properties panel | Change it. | Change a page… |
| 4.2 | "modified" chip flies into the phone preview; button swaps in place; timer **0.3 s** vs **2.1 s** restart | 0.3 s | …and it's patched into the open preview in a third of a second. No reload. |
| 4.3 | In-app toast "Preview ready" | Ready. | And the preview tells you when it's ready. |
| **CH 5 · ROCK SOLID** | title card | 05 · BUILT FOR A SHARED BOX | |
| 5.1 | Fingerprints: inputs → hash → cache drawer; change an input → new key, old drawer emptied | Never stale. | Caches are keyed by fingerprints of their inputs, so they never serve stale code. |
| 5.2 | Browser fetch row: vendor/extras/user → "304 not modified", only "modified" downloads | Download only changes. | Your browser only downloads what changed. |
| 5.3 | Memory lane with gate, heap cap and watchdog; a stuck build is pulled out; two projects build side by side | Every build in budget. | Guards keep every build in its memory budget, clear out stuck builds, and let other projects keep building. |
| **CH 6 · BIG APPS** | title card | 06 · BIG APPS | |
| 6.1 | 800-page grid lights fully, then most go dim; home, login, edited and opened pages stay lit | Only pages you use. | For big apps, preview builds only the pages you're working on. |
| 6.2 | Navigate to a dim page in the phone → it builds and appears | Built when opened. | Open another page, and it's built on the spot. |
| 6.3 | Counter 21 min → 1–2 min, tag "estimate" | 21 min → 1–2 min | Twenty-minute previews should drop to one or two. |
| **CH 7 · YOURS** | | | |
| 7.1 | `wm_rn_config.json` card: `"profile": "legacy-web-preview"` · `"allPages": false` | You're in control. | It's on by default. Switch back, or go per-page, in one line. |
| 7.2 | Proof wall: ~10 s edits (measured), 0.3 s patch, 7× warm builds, 159 modules, 21→1–2 min (est.) | — | — |
| 7.3 | WaveMaker logo · NEW PREVIEW · "In WaveMaker Studio" | NEW PREVIEW | New Preview. Build only what's yours. |

**Numbers check:** everything is measured except "21 min → 1–2 min", which is labelled as an estimate. "~1.6 GB" is the measured size of the first-ever shared install. "Seven times" comes from 97 s → 12.7 s (7.6×). "Three times" comes from 30 s → 10 s (commit 4ae8171f).
