"""Build a film's soundtrack: music bed + sound effects + voiceover, ducked and loudness-normalised.

    .venv/bin/python tools/sound.py experiments/<film>

Reads film.json -> "mix":
  vo:    [{src, from, to, at}]   phrases cut from audio/vo-<src>.wav (silences measured, not guessed)
  sfx:   [{type, at, ...}]       synthesized one-shots (see SFX below)
  music: {source: "synth", chords: [{at, notes}], pulse: [{from, to, every}]} or {source: "file", path}
  loudness: target LUFS (default -14)

Writes audio/music.wav, audio/sfx.wav, audio/vo.wav (stems) and audio/mix.wav.
Everything is synthesized from sines and short filtered noise: reproducible and licence-free.
No broadband noise in the bed (it reads as hiss); noise only in short one-shots.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, resample_poly

SR = 48000
# Equal temperament, A4 = 440 Hz, every note from C1 to B7 ("C#4" / "Db4" both work).
_SEMI = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
NOTE = {f"{n}{acc}{o}": 440.0 * 2 ** ((_SEMI[n] + d + (o - 4) * 12) / 12)
        for n in _SEMI for acc, d in (("", 0), ("#", 1), ("b", -1)) for o in range(1, 8)}
rng = np.random.default_rng(7)


def t_axis(d):
    return np.arange(int(d * SR)) / SR


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def place(track, clip, at, gain=1.0, pan=0.0):
    """Add a mono clip into a stereo track at time `at` with equal-power pan."""
    i = int(at * SR)
    if i >= track.shape[0]:
        return
    clip = clip[: track.shape[0] - i] * gain
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    track[i:i + len(clip), 0] += clip * l * 1.414
    track[i:i + len(clip), 1] += clip * r * 1.414


# ── one-shot sound effects ────────────────────────────────────────────────────
def sfx_thump(e):      # soft low impact: pitch-dropping sine
    t = t_axis(e.get("dur", .5))
    f = 45 + 45 * np.exp(-t * 18)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)


def sfx_hit(e):        # cut impact: sub drop + a short transient click
    t = t_axis(e.get("dur", .9))
    f = 36 + 44 * np.exp(-t * 14)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.5)
    click = hp(rng.standard_normal(len(t)), 2500) * np.exp(-t * 180) * .35
    return sub + click


def sfx_pluck(e):      # glassy UI pluck for chips / words
    f = NOTE.get(e.get("note"), e.get("freq", 1568.0))
    t = t_axis(e.get("dur", .35))
    return (np.sin(2 * np.pi * f * t) * np.exp(-t * 16) + .35 * np.sin(2 * np.pi * 2.01 * f * t) * np.exp(-t * 30)
            + .15 * np.sin(2 * np.pi * 3.02 * f * t) * np.exp(-t * 45))


def sfx_whoosh(e):     # band-passed noise swell (short: noise is fine in a one-shot)
    d = e.get("dur", 1.0)
    t = t_axis(d)
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    return bp(rng.standard_normal(len(t)), e.get("lo", 500), e.get("hi", 2500)) * env * .5


def sfx_riser(e):      # sine chirp + airy noise that ends exactly on a cut
    d = e.get("dur", 1.0)
    t = t_axis(d)
    f = e.get("f0", 180) * (e.get("f1", 900) / e.get("f0", 180)) ** (t / d)
    env = (t / d) ** 2.2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * .6 + np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR) * .25
    air = hp(rng.standard_normal(len(t)), 3000) * .18
    return (tone + air) * env


def sfx_chime(e):      # soft bell chord for the logo
    notes = e.get("notes", ["A5", "E6", "A6"])
    t = t_axis(e.get("dur", 2.2))
    out = np.zeros(len(t))
    for i, n in enumerate(notes):
        f = NOTE[n]
        out += (np.sin(2 * np.pi * f * t) + .25 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t * 6)) \
            * np.exp(-t * (2.2 + i * .6)) / len(notes)
    attack = np.clip(t / .006, 0, 1)
    return out * attack


def sfx_keys(e):       # a burst of keyboard clicks at typing speed
    d = e.get("dur", 1.0)
    out = np.zeros(int(d * SR))
    t = 0.0
    while t < d - .03:
        n = int(.018 * SR)
        click = hp(rng.standard_normal(n), 1800) * np.exp(-np.arange(n) / SR * 260)
        click += np.sin(2 * np.pi * rng.uniform(180, 260) * np.arange(n) / SR) * np.exp(-np.arange(n) / SR * 120) * .4
        i = int(t * SR)
        out[i:i + n] += click[: len(out) - i] * rng.uniform(.5, 1)
        t += rng.uniform(.045, .11)
    return out


def sfx_clock(e):      # one soft mechanical tick
    t = t_axis(.06)
    return bp(rng.standard_normal(len(t)), 2500, 6000) * np.exp(-t * 140) * .8


def sfx_rustle(e):     # paper: band-passed noise with a fluttering envelope
    d = e.get("dur", 1.0)
    t = t_axis(d)
    flutter = np.clip(np.sin(2 * np.pi * rng.uniform(9, 13) * t + rng.uniform(0, 6)), 0, 1) ** 2
    env = flutter * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.5
    return bp(rng.standard_normal(len(t)), 1200, 7000) * env * .6


def sfx_snap(e):       # a note landing: paper slap + soft low body
    t = t_axis(.25)
    slap = bp(rng.standard_normal(len(t)), 900, 5000) * np.exp(-t * 90)
    body = np.sin(2 * np.pi * 140 * t) * np.exp(-t * 30) * .5
    return slap + body


def sfx_bird(e):       # a short chirp: fast downward FM sine sweep
    out = []
    for k in range(e.get("n", 2)):
        t = t_axis(.09)
        f = e.get("freq", 4200) * (1 + .35 * np.exp(-t * 40)) * (1 + .03 * np.sin(2 * np.pi * 60 * t))
        out.append(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / .09) ** 2)
        out.append(np.zeros(int(.05 * SR)))
    return np.concatenate(out)


SFX = {"thump": sfx_thump, "hit": sfx_hit, "pluck": sfx_pluck, "whoosh": sfx_whoosh,
       "riser": sfx_riser, "chime": sfx_chime, "keys": sfx_keys, "clock": sfx_clock,
       "rustle": sfx_rustle, "snap": sfx_snap, "bird": sfx_bird}


def piano(f, d):       # soft felt-piano-ish tone: few harmonics, fast attack, long exp decay
    t = t_axis(d)
    x = sum(a * np.sin(2 * np.pi * f * h * t) * np.exp(-t * (1.6 + h * 1.2))
            for h, a in [(1, 1), (2, .45), (3, .18), (4, .08)])
    return x * np.clip(t / .004, 0, 1) * np.clip((d - t) / .3, 0, 1)


# ── music bed ─────────────────────────────────────────────────────────────────
def pad_voice(f, d, detune=.35):
    t = t_axis(d)
    x = (np.sin(2 * np.pi * f * t) + np.sin(2 * np.pi * (f + detune) * t) * .8
         + .18 * np.sin(2 * np.pi * 2 * f * t) + .06 * np.sin(2 * np.pi * 3 * f * t))
    return x * (1 + .12 * np.sin(2 * np.pi * .23 * t))


def music_synth(m, total):
    track = np.zeros((int(total * SR), 2))
    chords = m["chords"]
    for i, c in enumerate(chords):
        start = c["at"]
        end = chords[i + 1]["at"] if i + 1 < len(chords) else total
        d = end - start + .6                                   # overlap -> crossfade
        fade_in = c.get("fade", .25)
        for j, n in enumerate(c["notes"]):
            v = pad_voice(NOTE[n], d) * c.get("gain", 1.0) / len(c["notes"])
            t = t_axis(d)
            env = np.clip(t / fade_in, 0, 1) * np.clip((d - t) / .6, 0, 1)
            v = lp(v * env, c.get("lp", 1400))
            place(track, v, start, .5, pan=(-.35 if j % 2 else .35))
    for n in m.get("seq", []):                                # melodic notes (felt piano)
        v = lp(piano(NOTE[n["note"]], n.get("dur", 2.0)), 3500)
        place(track, v, n["at"], n.get("gain", .35), n.get("pan", 0.0))
    for p in m.get("pulse", []):                              # sub pulse = the heartbeat
        k = 0
        while (at := p["from"] + k * p["every"]) < p["to"] - 1e-6:
            t = t_axis(.22)
            f = 50 + 30 * np.exp(-t * 30)
            beat = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16)
            place(track, beat, at, p.get("gain", .5) * (1 + .5 * (k % 2 == 0)))
            k += 1
    return track


def vo_track(film_dir, segs, total):
    track = np.zeros((int(total * SR), 2))
    key = np.zeros(int(total * SR))
    for s in segs:
        rate, x = wavfile.read(film_dir / "audio" / f"vo-{s['src']}.wav")
        x = x.astype(np.float64) / 32768.0
        x = x[int(s["from"] * rate): int(s["to"] * rate)]
        x = resample_poly(x, SR, rate)
        n = len(x)
        ramp = np.ones(n)
        f = int(.015 * SR)
        ramp[:f] = np.linspace(0, 1, f)
        ramp[-f:] = np.linspace(1, 0, f)
        x = x * ramp / (np.max(np.abs(x)) + 1e-9) * .7            # per-phrase peak match
        place(track, x, s["at"], 1.0)
        i = int(s["at"] * SR)
        key[i:i + n] += np.abs(x[: len(key) - i])
    return track, key


def duck(music, key, depth_db=-9, attack=.02, release=.35):
    env = np.zeros_like(key)
    a, r = np.exp(-1 / (attack * SR)), np.exp(-1 / (release * SR))
    level = 0.0
    for i, v in enumerate(key):                            # peak follower
        level = a * level + (1 - a) * v if v > level else r * level + (1 - r) * v
        env[i] = level
    amount = np.clip(env / .08, 0, 1)
    gain = 10 ** (depth_db * amount / 20)
    return music * gain[:, None]


def write(path, x):
    wavfile.write(path, SR, (np.clip(x, -1, 1) * 32767).astype(np.int16))


def main():
    film_dir = Path(sys.argv[1])
    spec = json.loads((film_dir / "film.json").read_text())
    mix, total = spec["mix"], spec["total"]
    out = film_dir / "audio"

    vo, key = vo_track(film_dir, mix["vo"], total)
    m = mix["music"]
    if m["source"] == "synth":
        music = music_synth(m, total)
    else:
        rate, x = wavfile.read(film_dir / m["path"])
        x = x.astype(np.float64) / 32768.0
        x = resample_poly(x, SR, rate) if rate != SR else x
        x = np.column_stack([x, x]) if x.ndim == 1 else x
        music = np.zeros((int(total * SR), 2))
        music[: min(len(x), len(music))] = x[: len(music)]
    music = duck(music, key, mix.get("duck_db", -9))

    sfx = np.zeros((int(total * SR), 2))
    for e in mix["sfx"]:
        place(sfx, SFX[e["type"]](e), e["at"], e.get("gain", .5), e.get("pan", 0.0))

    # rough balance before loudness normalisation: voice leads, music sits under, sfx punctuates
    stems = {"music": music * mix.get("music_gain", .55), "sfx": sfx * mix.get("sfx_gain", .8), "vo": vo}
    for name, x in stems.items():
        write(out / f"{name}.wav", x)
    total_mix = sum(stems.values())
    f_out = int(.25 * SR)
    total_mix[-f_out:] *= np.linspace(1, 0, f_out)[:, None]
    write(out / "premix.wav", total_mix * .7)

    target = mix.get("loudness", -14)
    measure = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(out / "premix.wav"), "-af",
         f"loudnorm=I={target}:TP=-1.5:LRA=9:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    j = json.loads(measure[measure.rindex("{"): measure.rindex("}") + 1])
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(out / "premix.wav"), "-af",
         f"loudnorm=I={target}:TP=-1.5:LRA=9:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
         f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,"
         f"aresample={SR}", "-ar", str(SR), str(out / "mix.wav")], check=True)
    check = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(out / "mix.wav"), "-af", "ebur128=peak=true",
                            "-f", "null", "-"], capture_output=True, text=True).stderr.split("Summary:")[-1]
    print("mix.wav:", " ".join(check.split()))


if __name__ == "__main__":
    main()
