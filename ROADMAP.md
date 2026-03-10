# **ROADMAP: Suno AI \-\> Beat Saber AI \-\> Ragnarock VR Converter**

**BLUF:** This project bridges raw, fluctuating AI audio (Suno) into a strict, playable VR rhythm game grid (Ragnarock). It translates Beat Saber grid coordinates (4x3) into Ragnarock drum lanes (1x4) while aggressively filtering out AI-generated note spam to conserve physical energy.

## **Phase 1: Polish and Tooling Adjustments**

Moving forward, the pipeline can be enhanced with the following automation and polish features:

- **[ ] Automated Quest Deployment (ADB):** Add a `--deploy` flag to `rockit.sh` that utilizes the Android Debug Bridge (`adb`) to automatically push the generated `_Ragnarock` folder directly to the connected Quest headset's `CustomSongs` directory, eliminating the manual drag-and-drop step.
- **[x] Multi-Difficulty Support:** `rr_converter.py` now parses and processes multiple difficulty charts (e.g., Normal, Hard, Expert) from the Beat Sage `.zip` simultaneously. The script outputs `Level1.json`, `Level2.json`, etc., within the same Ragnarock folder, allowing players to choose their difficulty in-game.
- **[x] Audio Loudness Normalization (LUFS):** `warper.py` now measures and normalizes output loudness to a streaming-safe target (default `-14 LUFS / -1.0 dBTP`) so custom songs play at a more consistent volume in VR.
- **[x] Automatic Song Duration:** `rr_converter.py` now measures the packaged audio file and writes the actual playback length in seconds into `info.dat` instead of using a placeholder duration.
- **[x] Dynamic Difficulty Rating (NPS):** `rr_converter.py` now calculates average notes-per-second for each generated difficulty and maps that to a 1-10 `_difficultyRank` in `Info.dat` so the in-game difficulty display reflects chart density.

## **Phase 2: Advanced Charting & Generation**

- **[ ] Dynamic Environment Mapping:** Inject custom environment settings in `Info.dat` to match song themes based on user tags or metadata (instead of always defaulting to "Midgard").
- **[ ] Smart Obstacle/Note Density Controls:** Introduce configurable flags in the conversion script to allow users to scale down the overall note density or automatically generate specific obstacle patterns for high-intensity sections of a track.

## **Phase 3: GUI & Usability**

- **[ ] Desktop Companion App:** Wrap the shell scripts and Python pipeline in a simple graphical user interface (GUI) using Tkinter, PyQt, or Electron for non-technical users to drag-and-drop tracks.
- **[ ] Enhanced Logging & Progress Tracking:** Improve terminal output to show clear progress bars per step, especially useful for tracking the status of long batch-processing runs.
