#!/usr/bin/env bash
# Render one v6 shot in isolation and tile the stills.  bash tools/shot.sh <ID> <round> <t1,t2,...> [film=v6]
set -euo pipefail
ID="$1"; ROUND="$2"; TIMES="$3"; FILM="${4:-v6}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/film/$FILM/review/$ID/$ROUND"
QUERY="shots=$ID"; [ "$ID" = "kept" ] && QUERY="shots="
cd "$ROOT"
node tools/record.mjs "film/$FILM" --at "$TIMES" --query "$QUERY" --out "$OUT" 2>&1 | grep -v -E '^(Current directory|Loading default|Identity added)' || true
cd "$OUT"
ls t*.png | sort -t t -k2 -g | sed "s|^|file '$OUT/|;s|$|'|" | awk '{print; print "duration 1"}' > list.txt
N=$(ls t*.png | wc -l | tr -d ' '); COLS=3; [ "$N" -le 4 ] && COLS=2
ffmpeg -y -hide_banner -loglevel error -f concat -safe 0 -i list.txt -vf "scale=640:-1,tile=${COLS}x$(( (N + COLS - 1) / COLS )):padding=6:color=white" -frames:v 1 sheet.jpg
echo "stills: $(ls t*.png | sort -t t -k2 -g | tr '\n' ' ')"
echo "sheet:  $OUT/sheet.jpg"
