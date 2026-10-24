"""Split a one-take narration into its scripted lines and verify each cut.

    .venv/bin/python tools/align.py experiments/<film> [--src all] [--verify]

Reads <film>/lines.json and <film>/audio/vo-<src>.wav. Finds pauses (ffmpeg silencedetect), then picks one
pause per line boundary with a DP that matches each segment's speech time to its word count, preferring long
pauses (sentence breaks) over short ones (commas). Each segment ends just before the next line starts, so a
soft final word is never clipped. --verify transcribes every cut with Gemini (GEMINI_API_KEY) and prints it
next to the scripted line. Writes <film>/segs.json: [{from, to, inner:[[start,end],...]}] in source seconds;
`inner` = pauses inside the line (relative to `from`), useful for syncing visual beats to sentences.
"""
import functools, json, os, re, subprocess, sys
from pathlib import Path

film = Path(sys.argv[1]); src = sys.argv[sys.argv.index('--src') + 1] if '--src' in sys.argv else 'all'
wav = film / 'audio' / f'vo-{src}.wav'
L = json.loads((film / 'lines.json').read_text())
dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(wav)],
                           capture_output=True, text=True).stdout)
out = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(wav), '-af', 'silencedetect=noise=-38dB:d=0.35', '-f', 'null', '-'],
                     capture_output=True, text=True).stderr
ss = [float(x) for x in re.findall(r'silence_start: ([0-9.]+)', out)]
se = [float(x) for x in re.findall(r'silence_end: ([0-9.]+)', out)]
G = [(a, b) for a, b in zip(ss, se) if a > 0.3 and b < dur - 0.05]
END = ss[-1] if ss and ss[-1] > dur - 2.5 and len(ss) > len(se) else dur
w = [len(re.findall(r"[A-Za-z0-9']+", l)) for l in L]
n = len(L)
gap_total = sum(b - a for a, b in G)
rate = (END - gap_total) / sum(w)
exp = [x * rate for x in w]

def speech(i0, i1):
    s = 0.0 if i0 < 0 else G[i0][1]
    e = END if i1 >= len(G) else G[i1][0]
    return e - s - sum(b - a for a, b in G[i0 + 1:i1])

@functools.lru_cache(None)
def f(li, gi):
    if li == n - 1:
        d = speech(gi, len(G)); return ((d - exp[li]) / exp[li]) ** 2, ()
    best = (1e18, ())
    for k in range(gi + 1, len(G) - (n - 2 - li)):
        c = ((speech(gi, k) - exp[li]) / exp[li]) ** 2 - 0.6 * (G[k][1] - G[k][0])
        r, p = f(li + 1, k)
        if c + r < best[0]: best = (c + r, (k,) + p)
    return best

_, pick = f(0, -1)
starts = [0.0] + [G[k][1] for k in pick]
segs = []
for i, a in enumerate(starts):
    to = starts[i + 1] - 0.15 if i + 1 < n else min(dur, END + 0.3)
    fr = max(0.0, a - 0.05)
    inner = [[round(x - fr, 2), round(y - fr, 2)] for x, y in G if fr + 0.2 < x and y < to - 0.2]
    segs.append({'from': round(fr, 2), 'to': round(to, 2), 'inner': inner})
(film / f'segs-{src}.json').write_text(json.dumps(segs, indent=1))
for i, s in enumerate(segs):
    print(f"{i:2d} {s['from']:7.2f} {s['to']:7.2f} {s['to'] - s['from']:5.1f}s exp {exp[i]:4.1f}  {L[i][:50]}")

if '--verify' in sys.argv:
    from google import genai
    from google.genai import types
    c = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
    parts = []
    tmp = film / 'audio' / 'segs'; tmp.mkdir(exist_ok=True)
    for i, s in enumerate(segs):
        p = tmp / f'{src}-{i:02d}.wav'
        subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-ss', str(s['from']), '-to', str(s['to']), '-i', str(wav), str(p)], check=True)
        parts += [types.Part.from_text(text=f'CLIP {i}:'), types.Part.from_bytes(data=p.read_bytes(), mime_type='audio/wav')]
    parts.append(types.Part.from_text(text='Transcribe each numbered clip verbatim. Return a JSON object mapping clip number (string) to transcript.'))
    r = c.models.generate_content(model='gemini-2.5-flash', contents=parts, config=types.GenerateContentConfig(response_mime_type='application/json'))
    d = json.loads(r.text)
    bad = 0
    for i in range(n):
        got = d.get(str(i), '')
        norm = lambda x: re.sub(r'[^a-z0-9]', '', x.lower().replace('npm', 'n p m'.replace(' ', '')))
        ok_end = norm(L[i].split()[-1])[:5] in norm(got)[-25:]
        ok_start = norm(L[i].split()[0])[:4] in norm(got)[:12]
        flag = '' if ok_end and ok_start else '  <-- CHECK'
        bad += bool(flag)
        print(f'{i:2d} {got[:100]}{flag}')
    print('flagged:', bad)
