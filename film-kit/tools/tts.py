"""Per-shot voiceover via Gemini TTS.

    .venv/bin/python tools/tts.py experiments/<film>/film.json            # generate missing clips
    .venv/bin/python tools/tts.py experiments/<film>/film.json --force    # regenerate all
    .venv/bin/python tools/tts.py experiments/<film>/film.json --dry-run  # timing table only

Reads the "voice" and "vo" sections of film.json. Writes one WAV per line to
<film>/audio/vo-<id>.wav and prints each clip's REAL duration, because a single
long TTS pass drifts run to run; per-line clips placed at fixed timecodes keep
audio as deterministic as the frame-stepped picture.

GEMINI_API_KEY comes from the environment (or ./.env), never from code.
"""
import argparse
import json
import os
import re
import struct
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WPM = 150


def load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def spoken_words(text):
    return len(re.findall(r"[A-Za-z0-9']+", re.sub(r"\[[^\]]*\]", " ", text)))


def estimate(text):
    pauses = sum(float(p) for p in re.findall(r"\[PAUSE=([\d.]+)s\]", text))
    return spoken_words(text) / WPM * 60 + pauses


def prompt(voice, line):
    note = f"\n\n## Direction for this line:\n{line['note']}" if line.get("note") else ""
    return (
        "Read the following transcript based on the audio profile and director's note.\n\n"
        f"# Audio Profile\n{voice['profile']}\n\n"
        f"# Director's note\n{voice['direction']}\n\n"
        f"## Sample Context:\n{voice['context']}{note}\n\n"
        f"## Transcript:\n{line['text']}"
    )


def pcm_to_wav(pcm, mime):
    rate = int(m.group(1)) if (m := re.search(r"rate=(\d+)", mime)) else 24000
    bits = int(m.group(1)) if (m := re.search(r"audio/L(\d+)", mime)) else 16
    block = bits // 8
    return struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(pcm), b"WAVE", b"fmt ", 16, 1,
                       1, rate, rate * block, block, bits, b"data", len(pcm)) + pcm


def duration(path):
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def generate(film_dir, spec, force):
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    voice = spec["voice"]
    models = voice.get("models", ["gemini-2.5-flash-preview-tts"])
    config = types.GenerateContentConfig(
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice["name"]))),
    )
    out_dir = film_dir / "audio"
    out_dir.mkdir(exist_ok=True)
    last = 0.0
    for line in spec["vo"]:
        out = out_dir / f"vo-{line['id']}.wav"
        if out.exists() and not force:
            print(f"  {line['id']}: on disk ({duration(out):.2f}s), skip")
            continue
        # Free tier is ~3 req/min per model: keep calls >=21s apart.
        if last and (wait := 21 - (time.monotonic() - last)) > 0:
            print(f"  throttle {wait:.0f}s")
            time.sleep(wait)
        audio = None
        for model in models:
            for attempt in range(4):
                try:
                    last = time.monotonic()
                    resp = client.models.generate_content(
                        model=model, contents=prompt(voice, line), config=config)
                    part = resp.candidates[0].content.parts[0]
                    audio = pcm_to_wav(part.inline_data.data, part.inline_data.mime_type)
                    break
                except Exception as e:  # 429 -> honour server delay; other model errors -> next model
                    msg = str(e)
                    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                        if "PerDay" in msg:
                            print(f"  {model}: daily quota exhausted")
                            break
                        m = re.search(r"retry in ([\d.]+)s", msg) or re.search(r"'retryDelay': '(\d+)s'", msg)
                        delay = float(m.group(1)) + 2 if m else 25
                        print(f"  {model}: rate limited, waiting {delay:.0f}s")
                        time.sleep(delay)
                        continue
                    print(f"  {model}: {msg[:160]}")
                    break
            if audio:
                print(f"  {line['id']}: {model}")
                break
        if not audio:
            sys.exit(f"{line['id']}: no TTS model succeeded")
        out.write_bytes(audio)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("film")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    load_env()
    spec_path = Path(a.film)
    spec = json.loads(spec_path.read_text())
    film_dir = spec_path.parent

    print(f"{'id':<6}{'at':>6}{'est':>7}  text")
    for line in spec["vo"]:
        print(f"{line['id']:<6}{line['at']:>6.2f}{estimate(line['text']):>6.1f}s  {line['text']}")
    if a.dry_run:
        return
    generate(film_dir, spec, a.force)

    print("\nreal durations:")
    for line in spec["vo"]:
        p = film_dir / "audio" / f"vo-{line['id']}.wav"
        print(f"  {line['id']:<6} at {line['at']:>5.2f}s  len {duration(p):.2f}s  ends {line['at'] + duration(p):.2f}s")


if __name__ == "__main__":
    main()
