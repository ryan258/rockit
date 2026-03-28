# The Happy Path: Suno to Ragnarock on Quest 2

This guide walks through the complete end-to-end process to take an AI-generated song and play it in Ragnarock VR on your Meta Quest 2.

---

### Step 1: Generate the Audio (Suno AI)

1. Go to [Suno.com](https://suno.com/) and generate a song.
2. For the best rhythm game experience, use style prompts that encourage a heavy beat with clear transients (e.g., industrial, metal, EDM, 130 bpm). Avoid ambient or pad-heavy styles that make beat detection harder.
3. Download the audio file (`.mp3` or `.wav`).

### Step 2: Lock the Audio to a Static Grid (Rockit Warper)

Suno's audio has an organic, fluctuating tempo. Rhythm games require a mathematically perfect static BPM grid — otherwise notes drift out of sync with the music.

1. Move your downloaded Suno audio into `rockit/input/to-warp/`.
2. Open a terminal in the `rockit` project directory.
3. Run the batch warper:
   ```bash
   ./batch_warp.sh
   ```
   This uses Demucs to isolate the drum stem, Librosa to detect beat onsets, and Rubberband to stretch the full stereo master onto a locked BPM grid. It then masters the output to `-14 LUFS / -1.0 dBTP` using ffmpeg loudnorm.

   > _This can take a few minutes per song depending on your hardware. Demucs is the slow step._

   Processed files are saved to `input/warped/` as `.mp3`.

### Step 3: Generate the Beatmap (Beat Sage)

1. Go to [Beat Sage](https://beatsage.com/).
2. Upload the `.mp3` files from `input/warped/`.
3. In the configuration options, **select multiple difficulties** (e.g., Normal, Hard, Expert). Rockit will convert all of them — the more you request, the more in-game difficulty options players will have.
4. Click **Create Custom Level** and wait for the AI to finish mapping.
5. Download the resulting `.zip` files and move them into `rockit/input/saged/`.

### Step 4: Convert to Ragnarock Levels (Rockit Converter)

1. In your terminal, run:
   ```bash
   ./batch_rockit.sh
   ```
   Or, for a single map with automatic Quest deployment:
   ```bash
   ./rockit.sh --deploy input/saged/song.zip
   ```
2. For each zip, Rockit will:
   - Convert every Beat Sage difficulty chart into a separate Ragnarock level file (`Level1.json`, `Level2.json`, etc.)
   - Apply playability filters (deduplication, hammer limit, speed cap) to each difficulty
   - Measure the actual audio duration and write it to `info.dat`
   - Calculate the Notes Per Second (NPS) for each difficulty and assign a 1–10 difficulty rank for the in-game song selector
   - Copy audio and cover art into the output folder

   Playable song folders are emitted to `output/`.

### Step 5: Transfer to Quest 2

If you used `./rockit.sh --deploy`, Rockit already pushed the generated folder to the headset over `adb` and you can skip to Step 6.

1. Connect your Meta Quest 2 via USB-C.
2. Put the headset on, unlock it, and select **Allow** when prompted for data access.
3. Use [Android File Transfer](https://www.android.com/filetransfer/) or SideQuest to browse your Quest's storage.
4. Navigate to:
   ```
   Android / data / com.wanadev.ragnarockquest / files / CustomSongs
   ```
   _(Create `CustomSongs` if it doesn't exist.)_
5. Drag the generated song folder from `output/` into `CustomSongs`.

### Step 6: Play!

1. Disconnect the headset and launch **Ragnarock**.
2. Go to **Solo Play**.
3. Navigate to the **Custom Songs** tab in the song selector.
4. Select your song, choose a difficulty level, and start drumming.
