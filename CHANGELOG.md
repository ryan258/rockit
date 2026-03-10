# CHANGELOG

## Unreleased

### Added
- **Multi-difficulty support** — `rr_converter.py` now parses and converts every difficulty chart in a Beat Sage zip simultaneously (Normal, Hard, Expert, etc.), outputting `Level1.json`, `Level2.json`, etc. in the same Ragnarock folder.
- **Dynamic difficulty rating (NPS)** — converter calculates average Notes Per Second for each chart and maps it to a 1–10 `_difficultyRank` in `info.dat`, so the in-game difficulty display reflects actual chart density.
- **Automatic song duration** — converter measures the packaged audio file and writes the real playback length into `info.dat`, replacing the previous hardcoded 5:00 placeholder.
- **Loudness mastering** — `warper.py` now runs a two-pass EBU R128 loudnorm (measure then apply linear correction) via ffmpeg, targeting `-14 LUFS / -1.0 dBTP` by default. Configurable via `--lufs` and `--true-peak` flags.
- **OGG output support** — `warper.py` now correctly encodes `.ogg` files using `libvorbis` (previously fell back to `libmp3lame`).
- **Test suite** — added `tests/test_rr_converter.py` and `tests/test_warper.py`.
- **Concept workflow** — added `concept/album-outline.md` and `concept/instructions.md` as a structured AI-driven album ideation workspace. Song files in `concept/songs/` are gitignored.
- **Batch summary reporting** — `batch_rockit.sh` and `batch_warp.sh` now print a success/failure count at completion and exit with code 1 if any job failed.

### Changed
- `rr_converter.py` — `extract_bs_data` now returns all difficulty sets instead of a single hard-coded Expert chart.
- `rr_converter.py` — audio file presence is now validated before copy; missing audio raises `FileNotFoundError` instead of silently skipping.
- `warper.py` — Demucs temp directory is now managed with `tempfile.TemporaryDirectory` (no more hardcoded `temp_demucs/` left behind on failure).
- `warper.py` — all fatal conditions now raise typed exceptions (`RuntimeError`, `FileNotFoundError`, `ValueError`) instead of printing and returning `None`.
- Both `main()` functions now accept an `argv` parameter for testability and use `raise SystemExit(main())` as the entry point.
- Error output now goes to `sys.stderr`; exit codes are returned from `main()`.

---

## v0.2.0 — Batch Processing Pipeline

- Introduced `batch_warp.sh` and `batch_rockit.sh` for processing entire folders of audio and Beat Sage zips in one command.
- Added `input/to-warp/` and `input/saged/` as dedicated staging directories.

## v0.1.0 — Initial Pipeline

- `warper.py` — Demucs stem separation, Librosa beat tracking, Rubberband time-stretching to a fixed BPM grid.
- `rr_converter.py` — Beat Saber v2/v3 note parsing, 4-column to 4-drum lane mapping, deduplication, hammer limit, and speed cap filters.
- `rockit.sh` / `warp.sh` — shell entry points using `uv run`.
- Beat Saber to Ragnarock `info.dat` schema mapping with `Midgard` environment injection.
