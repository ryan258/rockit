# Rockit - Beat Saber to Ragnarock Converter

Rockit is a conversion pipeline that takes raw AI-generated audio (like Suno) and turns it into a playable custom level for Ragnarock VR. It handles everything from tempo-locking the audio to packaging a fully-rated, multi-difficulty Ragnarock song folder.

## Pipeline Overview

```
Suno audio  →  [warp]  →  Beat Sage  →  [rockit]  →  Ragnarock Quest
```

1. **Warp** — locks the organic, fluctuating Suno tempo to a mathematically perfect static BPM grid and masters the output to a consistent loudness target.
2. **Beat Sage** — (manual upload) generates one or more Beat Saber difficulty charts from the BPM-locked audio.
3. **Rockit** — converts all Beat Sage difficulty charts into Ragnarock format, applies playability filters, calculates NPS-based difficulty ratings, and packages the final song folder.

## Requirements

- **Python 3.11** managed via [`uv`](https://github.com/astral-sh/uv)
- **ffmpeg** — required for loudness mastering and audio duration detection
- **rubberband-cli** — required by `pyrubberband` for time-stretching
- **adb** — optional, required only for automatic Quest deployment via `./rockit.sh --deploy`
- Python dependencies are declared in `pyproject.toml` and installed automatically by `uv run`

## Quick Start

```bash
# Step 1: Lock tempo and master loudness
./batch_warp.sh          # processes input/to-warp/ → input/warped/

# Step 2: Upload input/warped/*.mp3 to beatsage.com, download zips → input/saged/

# Step 3: Convert to Ragnarock
./batch_rockit.sh        # processes input/saged/ → output/
```

Or run a single file:

```bash
./warp.sh input/to-warp/song.mp3 input/warped/song.mp3
./rockit.sh input/saged/song.zip
./rockit.sh --deploy input/saged/song.zip
```

## Warper (`warper.py`)

Processes raw audio into a BPM-locked, loudness-mastered file suitable for Beat Sage.

**Steps:**
1. **Stem separation (Demucs)** — isolates the drum track to remove melodic interference from beat detection.
2. **Beat tracking (Librosa)** — detects precise beat onset times from the isolated drums.
3. **Time-stretching (Rubberband)** — stretches the original stereo master between each detected beat onset, forcing the entire track onto a rigid BPM grid.
4. **Loudness mastering (ffmpeg loudnorm)** — two-pass EBU R128 normalization to `-14 LUFS / -1.0 dBTP` so all songs play at a consistent volume in VR.

**Options:**
```
./warp.sh <input> <output>

warper.py flags:
  --bpm FLOAT        Force a specific target BPM (default: auto-detected)
  --lufs FLOAT       Integrated loudness target in LUFS (default: -14.0)
  --true-peak FLOAT  True peak ceiling in dBTP (default: -1.0)
```

**Output format:** `.mp3` (enforced by `warp.sh` for Beat Sage compatibility)

## Converter (`rr_converter.py`)

Converts a Beat Sage `.zip` into a playable Ragnarock custom song folder.

**What it does:**
- Parses every difficulty chart in the Beat Sage zip (Normal, Hard, Expert, etc.) and converts all of them simultaneously, outputting `Level1.json`, `Level2.json`, etc.
- Maps Beat Saber's 4-column grid (`_lineIndex`) 1:1 to Ragnarock's 4 drum lanes.
- Applies three playability filters to each difficulty:
  1. **Deduplication** — removes overlapping notes on the same beat and lane.
  2. **Hammer limit** — caps concurrent notes at 2 per beat (one per hand), keeping only the outer-most lanes of any chord.
  3. **Speed cap** — culls notes closer than `0.125` beats (1/32nd note) apart to prevent physically exhausting AI-generated spam.
- Measures the actual audio duration and writes it to `info.dat` (replaces the old hardcoded 5:00 placeholder).
- Calculates average Notes Per Second (NPS) for each difficulty and maps it to a 1–10 `_difficultyRank` in `info.dat` so the in-game difficulty display reflects chart density.
- Copies audio and cover art assets into the output folder.

**Options:**
```
./rockit.sh [--deploy] <beat_sage.zip>

rr_converter.py flags:
  --min-delta FLOAT  Minimum beat delta between note clusters (default: 0.125)
  --hammer-limit INT Max concurrent notes per beat (default: 2)
```

## Transferring to Quest

To convert and immediately push the generated song folder to a connected Quest:

```bash
./rockit.sh --deploy input/saged/song.zip
```

Manual transfer still works too. Copy the output folder to your headset:

```
Android/data/com.wanadev.ragnarockquest/files/CustomSongs/
```

The `--deploy` flag uses `adb` to create `CustomSongs/` when needed and push the generated folder automatically. You can still use Android File Transfer or SideQuest if you prefer the manual flow.

## Concept Workflow

The `concept/` directory holds album-level ideation and per-track Suno prompt files. See `concept/instructions.md` for the workflow and `concept/album-outline.md` for the current album.
