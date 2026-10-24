# New Preview film: why it took 9 versions (retrospective, 2026-10-10)

Final approved cut: `new-preview-film-v9.mp4` (3:32, 1080p). Source: `film-kit/film/v7/`.
Raaj's verdict on v9: "this is good".

---

## 1. What happened, version by version

| Ver | What we shipped | Raaj's feedback | Root cause (ours) |
|---|---|---|---|
| v1 | Technical page + first film | MemoryLayer icon in the background; bad frames at 23/24 s; element popped in and out at 32 s; "boot" behind "Main" at 34 s; **same music as MemoryLayer**; missing the core message ("build only what's yours", first user installs); missed facts (cache, npm only for user packages); voice copied MemoryLayer | Reused the previous project's assets (brand bleed). Didn't sweep memory and commits for facts before scripting. No frame-by-frame QA. |
| v2 | Calm explainer ("engineer at a whiteboard") | "I still want ad type video, not page explaining" | **Format never pinned down at intake.** We guessed "explainer" from the doc context. |
| v3 | Short ad cut | "Missing things. Detailed explanation, ad type, long is OK" | Guessed length/depth instead of asking. Two versions lost on format alone. |
| v4 | Detailed ad | "Presentation really good" **but** many wrong values; **2× too fast**; voice changed (I said female, got male Puck); new music worse | Numbers taken loosely from memory without checking the primary source. Pace never measured. Voice swapped without a test listen. Changed music that wasn't broken. |
| v5 | Fact-fixed, 4:32 | "On by default" conveys the wrong message; many shots need full redesign; cursor clicks the wrong icon | Overcorrected pace (2× fast → too slow). A product default was described ambiguously. Cursor aimed with hand-typed coordinates. |
| v6 | Redesign of 8 sequences | Redesigns loved. **Voice faster and different after 1:00**; emoji icons look bad; fact-check again | One long TTS take **accelerates** (+40–50% words/s by the end), and we never measured that. Emoji used as icons. |
| v7 | Per-sentence TTS + atempo | **Tone changed ~10 times**; voice inaudible after 2:00; text overflow; black chips behind icon text | Mixed TTS calls (each call = a different read). The 3.1 TTS quota (10/day) ran out halfway and we patched around it. A global `.st` CSS class collided with shot labels. No overflow scan. |
| v8 | One original take, rubberband-stretched; overflow/chips fixed | **After 2:00 voice too low, music dominates** | Measured voice vs music **broadband** (looked fine at 12 dB) instead of in the **speech band** (1–4 kHz), where bright music sections masked the voice. The source take's last word was cut off and we didn't notice. |
| v9 | New single take (2 takes, best chosen) + speech-band sidechain mix | **"This is good"** | Fixed at the source: one steady take, measured pace, speech-band mix, listening check before delivery. |

**In one line:** about 2 versions went to an unclear brief (format and length), 2 to facts and wording, 1 to pace, and 3 to voice and mix. Picture design was mostly right by v6.

---

## 2. Repeated mistakes (patterns)

1. **Guessing instead of asking at intake.** Format (page / explainer / ad), length and depth were guessed and got wrong twice. The spec-video workflow already says to stop at gates. We skipped the script/shotlist approval and built full films.
2. **Facts from memory summaries, not primary sources.** Wrong values in v4; ambiguous "on by default" in v5. Every number needs a source line (commit, log, measurement), and every default needs its exact condition.
3. **Changing things that weren't broken.** Voice and music were swapped in v1/v4 and then had to be restored. Once Raaj approves an element (voice, music, a shot), freeze it.
4. **Voice handled as a one-shot step.** We never measured pace, never listened end-to-end, mixed takes, and missed a truncated last word. Voice took 4 rounds (v4, v6, v7, v8).
5. **Audio QA by broadband numbers.** "12 dB over the bed" was true but meaningless where the music occupies the speech band.
6. **Delivered without a full pass.** Raaj found overflow, black chips, the wrong cursor target and bad icons. Checking contact sheets of a few frames is not a review.
7. **Pace swung between extremes.** 2× too fast → too slow → asked faster. There was no numeric target.
8. **Brand bleed from the previous film.** MemoryLayer icon and music carried over into a WaveMaker film.
9. **Quota surprises.** The TTS free tier (10 requests/day on 3.1) ran out mid-fix and forced a compromise (v7).

---

## 3. What fixed it (keep doing this)

- **Modular film:** `film-core.js` (FX helpers, palette, Studio UI pieces) + one file per shot + `kept.js` for approved shots, so approved work is frozen and redesigns don't touch it.
- **Audio is authoritative:** `retime.py` warps the whole timeline (shots, chapters, SFX, music sections) from the base timeline to new voice lengths. Music sections in `timeline.json` are in **beats**, not seconds.
- **Voice:**
  - ONE continuous take, same voice JSON.
  - Direction: "same pace start to finish, ~140 wpm, never speed up".
  - Generate 2 takes and let a critic pick.
  - Measure words/s per line.
  - Even out leftover drift with `rubberband --fine --formant`, capped at 1.12×.
  - Transcribe every line, and especially check the **last word**.
- **Mix (`mix2.py`):**
  - Multiband sidechain on music+SFX during speech: mid −18 dB, high −10, low −4.
  - Bed lower in the second half and under the closing line.
  - +3 dB voice presence; −14 LUFS.
  - Measure in the **1–4 kHz** band.
- **Listening review before delivery:** Gemini as a "strict broadcast mix engineer / VO director" scores balance per half, tone consistency and unclear words.
- **Visual QA:**
  - `tools/probe.mjs` scans the whole film for spilled/clipped text.
  - Stills every 3 s across the full film.
  - The cursor targets real elements via `C.rectOf`.
  - Icons only from the **Material Symbols** font in palette colours (never emoji).
  - Shot CSS classes must be unique (the `.st` lesson).
- **Fact table** (`FACTCHECK-v4.md`): every on-screen and narrated claim maps to a commit, log or measurement. Estimates are labelled "expected".

---

## 4. Consistency checklist for the next film

**Intake (before any build)**
- [ ] Format confirmed: ad / explainer / doc page. Length range confirmed. Audience confirmed.
- [ ] Brand assets for *this* product (logo, palette, font). Nothing carried over from the last film.
- [ ] Fact table built from primary sources; product defaults written with exact conditions.
- [ ] Script + shotlist approved (gate) before any rendering.

**Voice lock**
- [ ] Voice name + full JSON frozen after approval. Never change it unless asked; test-listen before claiming gender or tone.
- [ ] Check the TTS quota first (3.1 free tier = 10 requests/day); have the backup key ready.
- [ ] One take for the whole narration; 2 takes, pick the best; per-line words/s within ±10%.
- [ ] Every line transcribed; last word present.

**Mix**
- [ ] Voice ≥ 25 dB over the bed in the 1–4 kHz band during speech, every 15 s window.
- [ ] Listening review: balance ≥ 9/10 in each half, no unclear words.

**Picture**
- [ ] Overflow probe clean; full-film stills every 3 s reviewed.
- [ ] Font icons only, palette colours; no dark chips; unique CSS class names.
- [ ] Approved shots frozen (`kept.js`); changes go only into the shots named in feedback.

**Delivery**
- [ ] Only ship after all of the above pass.
- [ ] Reply with what changed, and what I could not verify.
