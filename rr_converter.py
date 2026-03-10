"""
rr_converter.py - Rockit Beatmap Translation Engine

This script converts AI-generated Beat Saber custom maps (from Beat Sage)
into playable Ragnarock VR maps.

It translates the 4x3 Beat Saber coordinate grid into the 1x4 Ragnarock
drum lane format. Crucially, it filters out AI inconsistencies, stripping
duplicates, limiting hammer strikes (to a maximum of 2 concurrent notes),
and capping maximum note speed to prevent physically unplayable sequences.
"""

import os
import json
import tempfile
import zipfile
import shutil
import argparse
import re
import subprocess
import sys
import math

import soundfile as sf

DIFFICULTY_RANKS = {
    "Easy": 1,
    "Normal": 3,
    "Hard": 5,
    "Expert": 7,
    "ExpertPlus": 9,
}


def _default_difficulty_rank(difficulty_name):
    return DIFFICULTY_RANKS.get(difficulty_name or "", 5)


def _difficulty_sort_key(beatmap_info):
    difficulty_name = beatmap_info.get("_difficulty", "")
    difficulty_rank = beatmap_info.get("_difficultyRank")
    try:
        normalized_rank = int(difficulty_rank)
    except (TypeError, ValueError):
        normalized_rank = _default_difficulty_rank(difficulty_name)

    return (normalized_rank, difficulty_name, beatmap_info.get("_beatmapFilename", ""))


def _extract_notes_from_beatmap(beatmap_data):
    notes = beatmap_data.get("_notes", [])
    if not notes and "colorNotes" in beatmap_data:
        for note in beatmap_data["colorNotes"]:
            notes.append({"_time": note.get("b"), "_lineIndex": note.get("x")})
    return notes


def detect_song_duration_seconds(audio_path):
    """
    Measures audio duration in seconds for the packaged song asset.

    Uses libsndfile first for local audio parsing and falls back to ffprobe
    when the container/codec is not directly supported.
    """
    try:
        info = sf.info(audio_path)
        duration = float(info.duration)
        if math.isfinite(duration) and duration > 0:
            return duration
    except RuntimeError:
        pass

    if shutil.which("ffprobe") is None:
        raise RuntimeError(
            f"Could not determine duration for {audio_path}. soundfile failed and ffprobe is unavailable."
        )

    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed to measure duration for {audio_path}.")

    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"ffprobe returned an invalid duration for {audio_path}.") from exc

    if not math.isfinite(duration) or duration <= 0:
        raise RuntimeError(f"Measured invalid audio duration for {audio_path}: {duration}")

    return duration


def compute_average_nps(rr_notes, song_duration_seconds):
    """
    Calculates average notes-per-second over the full song duration.
    """
    if song_duration_seconds <= 0:
        raise ValueError("Song duration must be positive to compute NPS.")

    return len(rr_notes) / float(song_duration_seconds)


def nps_to_difficulty_rank(nps):
    """
    Maps average NPS to a 1-10 in-game difficulty rank.

    The 2x scale keeps low-density Ragnarock charts separated while still
    capping extreme charts at 10.
    """
    return max(1, min(10, int(round(nps * 2.0))))


def extract_bs_data(zip_path, temp_dir):
    """
    Extracts a Beat Sage zip archive and parses its metadata and beatmaps.

    Args:
        zip_path (str): The path to the downloaded Beat Sage .zip file.
        temp_dir (str): A temporary directory path to extract contents to.

    Returns:
        tuple: (info_dict, difficulty_sets, base_directory_path)
    """
    zip_path = os.path.abspath(zip_path)
    print(f"Input zip: {zip_path}")
    print(f"Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    info_path = None
    base_dir = temp_dir
    for root, _, files in os.walk(temp_dir):
        for f in files:
            if f.lower() == "info.dat":
                info_path = os.path.join(root, f)
                base_dir = root
                break
        if info_path:
            break

    if not info_path:
        raise FileNotFoundError("info.dat or Info.dat not found in the zip archive.")
        
    with open(info_path, 'r', encoding='utf-8') as f:
        info = json.load(f)
        
    diff_sets = info.get("_difficultyBeatmapSets", [])
    if not diff_sets:
        raise ValueError("No beatmap sets found in Info.dat")

    difficulty_sets = []
    selected_beatmaps = []

    for diff_set in diff_sets:
        characteristic_name = diff_set.get("_beatmapCharacteristicName", "Standard")
        diff_infos = diff_set.get("_difficultyBeatmaps", [])
        if not diff_infos:
            continue

        loaded_beatmaps = []
        for diff_info in sorted(diff_infos, key=_difficulty_sort_key):
            beatmap_filename = diff_info.get("_beatmapFilename")
            if not beatmap_filename:
                raise ValueError("Beatmap filename missing from difficulty metadata.")

            dat_path = os.path.join(base_dir, beatmap_filename)
            if not os.path.exists(dat_path):
                raise FileNotFoundError(f"Beatmap data file {beatmap_filename} not found.")

            with open(dat_path, 'r', encoding='utf-8') as f:
                beatmap_data = json.load(f)

            difficulty_name = diff_info.get("_difficulty") or os.path.splitext(beatmap_filename)[0]
            difficulty_rank = diff_info.get("_difficultyRank")
            try:
                normalized_rank = int(difficulty_rank)
            except (TypeError, ValueError):
                normalized_rank = _default_difficulty_rank(difficulty_name)

            loaded_beatmaps.append({
                "difficulty": difficulty_name,
                "difficulty_rank": normalized_rank,
                "source_filename": beatmap_filename,
                "note_jump_movement_speed": diff_info.get("_noteJumpMovementSpeed", 20),
                "note_jump_start_beat_offset": diff_info.get("_noteJumpStartBeatOffset", 0),
                "notes": _extract_notes_from_beatmap(beatmap_data),
            })
            selected_beatmaps.append(f"{characteristic_name}/{difficulty_name} -> {beatmap_filename}")

        if loaded_beatmaps:
            difficulty_sets.append({
                "characteristic_name": characteristic_name,
                "beatmaps": loaded_beatmaps,
            })

    if not difficulty_sets:
        raise ValueError("No difficulty beatmaps found.")

    print("Selected beatmaps:")
    for selected in selected_beatmaps:
        print(f" - {selected}")

    return info, difficulty_sets, base_dir

def convert_notes(bs_notes):
    """
    Translates Beat Saber spatial coordinates into Ragnarock drum lanes.

    Beat Saber uses a 4-column (lineIndex 0-3) by 3-row grid.
    Ragnarock uses 4 drums (lineIndex 0-3) on a single row.

    This maps the columns 1:1 and homogenizes the note types/layers
    to prevent Unity parser crashes in the Ragnarock engine.

    Args:
        bs_notes (list): Array of raw Beat Saber note dictionaries.

    Returns:
        list: Array of converted Ragnarock note dictionaries.
    """
    rr_notes = []
    for note in bs_notes:
        # Extract time and lineIndex (column)
        time = note.get("_time")
        line_index = note.get("_lineIndex")
        
        if time is None or line_index is None:
            continue
            
        # Beat Saber: 0=Left, 1=MiddleLeft, 2=MiddleRight, 3=Right
        # Ragnarock: 0=Left, 1=MiddleLeft, 2=MiddleRight, 3=Right
        # Direct 1:1 mapping!
        if 0 <= line_index <= 3:
            rr_notes.append({
                "_time": round(float(time), 4),
                "_lineIndex": int(line_index),
                "_lineLayer": 1,
                "_type": 0,
                "_cutDirection": 1
            })
            
    return rr_notes

def clean_chart(notes, min_time_delta=0.125, hammer_limit=2):
    """
    Applies strict physical playability filters to the translated notes.

    AI mappers often generate overlapping or impossibly fast note clusters.
    This function enforces human constraints:
    1. Deduplication: Removes identical notes sharing the same time and drum.
    2. Hammer Limit: Drops notes if >2 appear concurrently (you only have 2 hammers).
    3. Speed Cap: Prunes notes closer than `min_time_delta` to prevent exhaustion.

    Args:
        notes (list): The array of Ragnarock-formatted notes.
        min_time_delta (float): Minimum beats allowed between distinct notes.
        hammer_limit (int): Maximum concurrent notes allowed.

    Returns:
        list: The safe, playable array of notes.
    """
    if not notes:
        return []

    # 1. Sort by time, then by lineIndex
    sorted_notes = sorted(notes, key=lambda x: (x["_time"], x["_lineIndex"]))
    
    # 2. Deduplication (same time, same lane)
    deduped = []
    for note in sorted_notes:
        if not deduped:
            deduped.append(note)
        else:
            last = deduped[-1]
            if abs(last["_time"] - note["_time"]) < 0.001 and last["_lineIndex"] == note["_lineIndex"]:
                pass # Skip exact duplicate
            else:
                deduped.append(note)

    # 3. Hammer Limit (Max N notes perfectly concurrent)
    time_groups = {}
    for note in deduped:
        t = note["_time"]
        # Group by very close times floating point approx
        t_key = round(t * 1000) / 1000 
        time_groups.setdefault(t_key, []).append(note)
        
    hammer_limited = []
    for t_key in sorted(time_groups.keys()):
        group = time_groups[t_key]
        if len(group) > hammer_limit:
            # Keep outer notes (min and max lineIndex)
            group.sort(key=lambda x: x["_lineIndex"])
            hammer_limited.append(group[0])
            hammer_limited.append(group[-1])
        else:
            hammer_limited.extend(group)
            
    # Re-sort after hammer limiting
    hammer_limited.sort(key=lambda x: x["_time"])

    # 4. Speed Cap (Min delta between note clusters)
    final_notes = []
    last_allowed_time = -1.0
    
    for note in hammer_limited:
        t = note["_time"]
        
        # If it's part of a chord (same time as last allowed time), let it pass
        if abs(t - last_allowed_time) < 0.001 and final_notes:
            final_notes.append(note)
            continue
            
        # Check delta
        if last_allowed_time == -1.0 or (t - last_allowed_time) >= min_time_delta:
            final_notes.append(note)
            last_allowed_time = t
        else:
            # Prune note (too fast)
            pass
            
    print(f"Chart Cleaned: Started with {len(notes)} notes -> Ended with {len(final_notes)} notes")
    return final_notes

def build_rr_difficulty_sets(
    bs_difficulty_sets,
    min_time_delta=0.125,
    hammer_limit=2,
    song_duration_seconds=None,
):
    """
    Converts and cleans every Beat Saber difficulty chart in extraction order.

    Args:
        bs_difficulty_sets (list): Parsed Beat Sage difficulty metadata and notes.
        min_time_delta (float): Minimum beat delta between note clusters.
        hammer_limit (int): Maximum concurrent notes allowed.

    Returns:
        list: Difficulty-set metadata with Ragnarock notes and LevelN.json filenames.
    """
    rr_difficulty_sets = []
    level_number = 1

    for diff_set in bs_difficulty_sets:
        rr_beatmaps = []
        for beatmap in diff_set["beatmaps"]:
            raw_rr_notes = convert_notes(beatmap["notes"])
            print(
                "Converted notes before cleanup "
                f"[{diff_set['characteristic_name']}/{beatmap['difficulty']}]: {len(raw_rr_notes)}"
            )

            clean_rr_notes = clean_chart(
                raw_rr_notes,
                min_time_delta=min_time_delta,
                hammer_limit=hammer_limit,
            )

            average_nps = None
            difficulty_rank = beatmap["difficulty_rank"]
            if song_duration_seconds is not None:
                average_nps = compute_average_nps(clean_rr_notes, song_duration_seconds)
                difficulty_rank = nps_to_difficulty_rank(average_nps)

            rr_beatmaps.append({
                "difficulty": beatmap["difficulty"],
                "difficulty_rank": difficulty_rank,
                "note_jump_movement_speed": beatmap["note_jump_movement_speed"],
                "note_jump_start_beat_offset": beatmap["note_jump_start_beat_offset"],
                "output_filename": f"Level{level_number}.json",
                "rr_notes": clean_rr_notes,
                "average_nps": None if average_nps is None else round(average_nps, 2),
                "notes_count": len(clean_rr_notes),
            })
            level_number += 1

        if rr_beatmaps:
            rr_difficulty_sets.append({
                "characteristic_name": diff_set["characteristic_name"],
                "beatmaps": rr_beatmaps,
            })

    if not rr_difficulty_sets:
        raise ValueError("No converted difficulty charts were produced.")

    return rr_difficulty_sets


def package_rr_song(temp_dir, output_dir, bs_info, rr_difficulty_sets, song_duration_seconds=None):
    """
    Compiles the final Ragnarock custom song folder.

    Constructs the exact strict JSON schema required by Ragnarock's C#
    Unity parser, copies the cover art and audio, and saves them
    into the designated output directory.

    Args:
        temp_dir (str): The extraction directory containing audio/art assets.
        output_dir (str): The final destination folder for the Ragnarock song.
        bs_info (dict): The original Beat Saber Info.dat metadata.
        rr_difficulty_sets (list): Converted Ragnarock difficulty sets and notes.
        song_duration_seconds (float, optional): Measured audio duration in seconds.
    """
    print(f"Packaging to {output_dir}...")
    os.makedirs(output_dir, exist_ok=True)
    
    # Locate audio and cover
    audio_file = bs_info.get("_songFilename")
    cover_file = bs_info.get("_coverImageFilename")

    if not audio_file:
        raise ValueError("Song audio filename missing from Beat Saber metadata.")

    audio_source = os.path.join(temp_dir, audio_file)
    if not os.path.exists(audio_source):
        raise FileNotFoundError(f"Song audio file not found: {audio_source}")

    shutil.copy2(audio_source, os.path.join(output_dir, audio_file))

    if cover_file:
        cover_source = os.path.join(temp_dir, cover_file)
        if not os.path.exists(cover_source):
            raise FileNotFoundError(f"Cover image file not found: {cover_source}")
        shutil.copy2(cover_source, os.path.join(output_dir, cover_file))
        
    # the info.dat expects audio and cover to exist with same names, we'll keep the names.
    
    clean_song_name = bs_info.get("_songName", "Unknown Song")
    for ext in [".ogg", ".mp3", ".wav"]:
        clean_song_name = clean_song_name.replace(ext, "")
    clean_song_name = clean_song_name.strip()
    
    if song_duration_seconds is None:
        song_duration_seconds = detect_song_duration_seconds(audio_source)
    display_duration_seconds = max(1, int(round(song_duration_seconds)))
    print(f"Measured song duration: {song_duration_seconds:.2f}s")

    # Create Ragnarock info.dat (Lowercase, Version 1.0.0 required)
    rr_info = {
        "_version": "1.0.0",
        "_explicit": "false",
        "_songName": clean_song_name,
        "_songSubName": bs_info.get("_songSubName", ""),
        "_songAuthorName": bs_info.get("_songAuthorName", "Suno AI"),
        "_levelAuthorName": "ryanleej",
        "_beatsPerMinute": int(bs_info.get("_beatsPerMinute", 120)),
        "_shuffle": 0,
        "_shufflePeriod": 0.5,
        "_previewStartTime": int(bs_info.get("_previewStartTime", 12)),
        "_previewDuration": int(bs_info.get("_previewDuration", 10)),
        "_songApproximativeDuration": display_duration_seconds,
        "_songFilename": audio_file,
        "_coverImageFilename": cover_file or "",
        "_environmentName": "Midgard",
        "_songTimeOffset": 0,
        "_difficultyBeatmapSets": []
    }

    total_levels = 0
    for diff_set in rr_difficulty_sets:
        packaged_beatmaps = []
        for beatmap in diff_set["beatmaps"]:
            if beatmap.get("average_nps") is not None:
                print(
                    f"Difficulty rating [{diff_set['characteristic_name']}/{beatmap['difficulty']}]: "
                    f"{beatmap['average_nps']:.2f} NPS -> Rank {beatmap['difficulty_rank']}/10"
                )

            packaged_beatmaps.append({
                "_difficulty": beatmap["difficulty"],
                "_difficultyRank": int(beatmap["difficulty_rank"]),
                "_beatmapFilename": beatmap["output_filename"],
                "_noteJumpMovementSpeed": beatmap["note_jump_movement_speed"],
                "_noteJumpStartBeatOffset": beatmap["note_jump_start_beat_offset"],
            })

            level_data = {
                "_version": "1.0.0",
                "_customData": {
                    "_time": 0,
                    "_BPMChanges": [],
                    "_bookmarks": []
                },
                "_events": [],
                "_notes": beatmap["rr_notes"],
                "_obstacles": [],
                "_waypoints": []
            }

            with open(os.path.join(output_dir, beatmap["output_filename"]), "w", encoding='utf-8') as f:
                json.dump(level_data, f, separators=(',', ':'))

            total_levels += 1

        if packaged_beatmaps:
            rr_info["_difficultyBeatmapSets"].append({
                "_beatmapCharacteristicName": diff_set["characteristic_name"],
                "_difficultyBeatmaps": packaged_beatmaps,
            })

    if not rr_info["_difficultyBeatmapSets"]:
        raise ValueError("No Ragnarock difficulty charts available to package.")

    with open(os.path.join(output_dir, "info.dat"), "w", encoding='utf-8') as f:
        json.dump(rr_info, f, indent=2)

    print(f"Successfully packaged {rr_info.get('_songName')}!")
    print(f"Difficulty files written: {total_levels}")
    print(f"Output folder: {os.path.abspath(output_dir)}")

def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert Beat Saber maps to Ragnarock with playability filters.")
    parser.add_argument("zip_path", help="Path to the Beat Sage output .zip file")
    parser.add_argument("--min-delta", type=float, default=0.125, help="Minimum beat delta between notes (Speed Cap, default 0.125)")
    parser.add_argument("--hammer-limit", type=int, default=2, help="Max notes per beat (default 2)")
    
    args = parser.parse_args(argv)
    
    zip_path = os.path.abspath(args.zip_path)
    if not os.path.exists(zip_path):
        print(f"Error: Could not find file {zip_path}", file=sys.stderr)
        return 1
        
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            bs_info, bs_difficulty_sets, base_dir = extract_bs_data(zip_path, temp_dir)
            
            # Determine output folder name strictly as [song][artist][user] locally
            song_name = bs_info.get("_songName", "Unknown")
            for ext in [".ogg", ".mp3", ".wav"]:
                song_name = song_name.replace(ext, "")
            song_author = bs_info.get("_songAuthorName", "SunoAI")
            level_author = "ryanleej"
            
            raw_folder_name = f"{song_name}{song_author}{level_author}"
            safe_folder_name = re.sub(r'[^a-zA-Z0-9]', '', raw_folder_name).lower()
            
            # Ensure the output directory is inside the 'output' folder in the project root
            project_root = os.path.dirname(os.path.abspath(__file__))
            output_base_dir = os.path.join(project_root, "output")
            os.makedirs(output_base_dir, exist_ok=True)
            
            output_dir = os.path.join(output_base_dir, safe_folder_name)
            
            audio_source = os.path.join(base_dir, bs_info.get("_songFilename", ""))
            song_duration_seconds = detect_song_duration_seconds(audio_source)

            rr_difficulty_sets = build_rr_difficulty_sets(
                bs_difficulty_sets,
                min_time_delta=args.min_delta, 
                hammer_limit=args.hammer_limit,
                song_duration_seconds=song_duration_seconds,
            )

            package_rr_song(
                base_dir,
                output_dir,
                bs_info,
                rr_difficulty_sets,
                song_duration_seconds=song_duration_seconds,
            )
            return 0
            
        except Exception as exc:
            print(f"An error occurred during conversion: {exc}", file=sys.stderr)
            return 1

if __name__ == "__main__":
    raise SystemExit(main())
