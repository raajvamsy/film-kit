# v4 fact-check (against memory + commits) → fixes for v5

| # | v4 said | Truth (source) | v5 |
|---|---|---|---|
| 1 | "rebuilds 2,723 modules" (old way) | 2,723 = modules in a **small app's Metro graph**, 26 project source (measured 2026-09-02). Not an old-builder rebuild count. | "A small app bundles ~2,700 modules. Only 26 are your code." |
| 2 | "build killed · out of memory" in the OLD-way chapter | OOM kill happened to the **first version of the new pipeline** (Metro child, 2026-09-02) and the one-time shared install. Old esbuild path pinned memory at the cap but **no kill** (oom_kill unchanged, 2026-09-16). | Old way: "memory pinned at the cap". Kill removed. |
| 3 | Implied old edit = full ~2 min rebuild | Old esbuild **incremental** ≈ 23 s (no reinstall), clean ≈ 2 min (measured). | Show "old: ~23 s per edit". |
| 4 | "installs once per **machine**" | Shared store is per **container**, per rn-app version (`/root/.wm/.../shared-nm-web-<hash>` + volume vendor store). | "once per container" |
| 5 | "first build only · **~1.6 GB**" | 1.6 GB was **peak RAM** of that install, not size. | size removed |
| 6 | "v12.0 → v12.1" | invented version numbers | "new WaveMaker version" |
| 7 | "+ react-konva" as a user package | react-konva is a **WaveMaker wmx** dependency (commit 1d8f5016), not user-added | generic "+ your-package" |
| 8 | "npm only runs for packages you add" | npm is **skipped when the shared install satisfies every dependency** (`computeVendorDelta`), otherwise a normal install runs. | "Skipped when everything's already there; runs only when your app needs more." |
| 9 | "walks 159 modules, not 2,730" for every build | Boundary mode applies to **edit builds when caches exist** (measured 159 vs 2,730, 2026-09-20). | "An edit walks ~160 modules" |
| 10 | "patched in a third of a second" as the whole edit | 312 ms is the **client apply** only (vs 2,079 ms restart). Small-edit build ≈ 1.7–2.2 s. | "Build ~2 s, patch lands in 0.3 s" |
| 11 | "~10 s edits" (end card) | 9.6–12.7 s was a **pre-fast-path** measurement (2026-09-03). | replaced with "~2 s edit builds" |
| 12 | Fingerprint inputs incl. "transform options" | Key = lockfile hash + reachable module set + builder-file fingerprint (+ platform). | inputs corrected |
| 13 | "they never serve stale code" | Over-claim (in-place node_modules edits are not hashed). | "input changes → key changes → rebuilt" |
| 14 | "For big apps, preview builds only the pages you're working on" | Page mode is **opt-in** (`allPages:false`); default builds all pages. | "switch on page mode" |
| 15 | "Open another page, it's built on the spot" | Needs the Studio-side change (**uncommitted**). | kept, worded "built when you get there"; flagged |
| 16 | 97 s → 12.7 s, 7×, ~half memory | ✓ cold vs warm shared transform cache, same project; peak 2,244 → 1,258 MiB | kept |
| 17 | 30 s → 10 s codegen, 304s, guards, 2.5 GB / 10 devs, 2.3 GB node_modules, 6.8 MB bundle, Rebuild Preview keeps store, old store pruned, 21 min PNB | ✓ | kept (21 → 1–2 min stays **estimate**) |
