# Rockit - Beat Saber to Ragnarock Converter

Rockit is a conversion tool designed to bridge the gap between AI-generated audio (like Suno) and VR rhythm games. It takes a raw audio file that has been warped to a fixed BPM, relies on Beat Sage to generate a 4-lane Beat Saber map, and converts that map into a perfectly playable Ragnarock VR level.

During the conversion, Rockit heavily filters and cleans the AI-generated Beat Saber chart to ensure it respects human playability constraints in Ragnarock (e.g., removing impossible drum rolls, >2 hammer strikes, and overlapping notes).

## Project Requirements

- **Python 3** (Standard library only; no external pypi dependencies needed for the core converter)
- A DAW (like Ableton) or stems AI (like Fadr/Moises) to warp raw audio to a static BPM.

## Execution Flow

To convert a new song, follow these 3 steps:

1. **(Automated)** Run the audio warper on your raw Suno `.wav` or `.mp3` to mathematically lock the fluctuating tempo to a fixed BPM grid:
   ```bash
   ./warp.sh input/suno_song.wav output/locked_audio.mp3
   ```
2. **(Manual)** Upload the `output/locked_audio.mp3` file to [Beat Sage](https://beatsage.com/) to automatically generate the Beat Saber AI beatmap. Download the resulting `.zip` file.
3. **(Automated)** Place the `.zip` file in the `input/` folder, and run the wrapper script:

```bash
./rockit.sh input/BeatSage_Map.zip
```

The script will instantly unzip the file, convert the notes, apply Ragnarock playability limits, and emit a playable custom folder in the `output/` directory (e.g., `output/SongName_Ragnarock/`).

### Transferring to Quest

Move the generated folder to your Quest headset's custom song directory:
`Android > data > com.wanadev.ragnarockquest > files > UE4Game > Ragnarock > Ragnarock > Saved > CustomSongs`

## How The Converter Works (`rr_converter.py`)

The core engine performs a 1:1 mapping from Beat Saber's 4 columns (`_lineIndex`) to Ragnarock's 4 drums. During this process, it applies three major filters:

1. **Deduplication:** Strips strictly duplicate overlapping notes on the same beat and lane.
2. **Hammer Limit:** Prevents >2 notes from occurring at the exact same beat by preserving only the outer bounds of a chord (since players only have 2 hammers).
3. **Speed Cap:** Computes the time delta between note groups, culling notes clustered closer than `0.125` beats (1/32nd notes) to prevent physical exhaustion from AI-generated spam. This is adjustable via the `--min-delta` flag.

The script then automatically injects Ragnarock's needed configuration overrides (such as the `Midgard` environment setting) into the `Info.dat`.
