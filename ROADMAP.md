# **ROADMAP: Suno AI \-\> Beat Saber AI \-\> Ragnarock VR Converter**

**BLUF:** This project bridges raw, fluctuating AI audio (Suno) into a strict, playable VR rhythm game grid (Ragnarock). It translates Beat Saber grid coordinates (4x3) into Ragnarock drum lanes (1x4) while aggressively filtering out AI-generated note spam to conserve physical energy.

## **Phase 1: Polish and Tooling Adjustments**

Moving forward, the pipeline can be enhanced with the following automation and polish features:

- **[ ] Automated Quest Deployment (ADB):** Add a `--deploy` flag to `rockit.sh` that utilizes the Android Debug Bridge (`adb`) to automatically push the generated `_Ragnarock` folder directly to the connected Quest headset's `CustomSongs` directory, eliminating the manual drag-and-drop step.
- **[ ] Multi-Difficulty Support:** Update `rr_converter.py` to parse and process multiple difficulty charts (e.g., Normal, Hard, Expert) from the Beat Sage `.zip` simultaneously. The script should output `Level1.json`, `Level2.json`, etc., within the same Ragnarock folder, allowing players to choose their difficulty in-game.
- **[ ] Audio Loudness Normalization (LUFS):** Integrate a loudness normalization step into `warper.py`. The script will measure the LUFS (Loudness Units relative to Full Scale) of the isolated audio and automatically adjust the gain to match a standard target (e.g., -14 LUFS), ensuring all custom songs play at a consistent volume in VR.
- **[ ] Automatic Song Duration:** Dynamically calculate the accurate song playback length in seconds during the conversion script instead of defaulting to an inaccurate placeholder (e.g., 5:00) so the in-game UI shows the true track time.
- **[ ] Dynamic Difficulty Rating (NPS):** Calculate the overall Notes Per Second (NPS) for the generated chart and automatically assign it a relative difficulty level (1-10) within the `Info.dat`, providing a clear metric for players before they select the song in Ragnarock.

## **Phase 2: Advanced Charting & Generation**

- **[ ] Dynamic Environment Mapping:** Inject custom environment settings in `Info.dat` to match song themes based on user tags or metadata (instead of always defaulting to "Midgard").
- **[ ] Smart Obstacle/Note Density Controls:** Introduce configurable flags in the conversion script to allow users to scale down the overall note density or automatically generate specific obstacle patterns for high-intensity sections of a track.

## **Phase 3: GUI & Usability**

- **[ ] Desktop Companion App:** Wrap the shell scripts and Python pipeline in a simple graphical user interface (GUI) using Tkinter, PyQt, or Electron for non-technical users to drag-and-drop tracks.
- **[ ] Enhanced Logging & Progress Tracking:** Improve terminal output to show clear progress bars per step, especially useful for tracking the status of long batch-processing runs.
