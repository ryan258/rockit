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
from pathlib import Path

def extract_bs_data(zip_path, temp_dir):
    """
    Extracts a Beat Sage zip archive and parses its metadata and beatmap.

    Args:
        zip_path (str): The path to the downloaded Beat Sage .zip file.
        temp_dir (str): A temporary directory path to extract contents to.

    Returns:
        tuple: (info_dict, notes_list, base_directory_path)
    """
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
        
    # Find the data file for the highest difficulty
    # Beat Sage usually generates one difficulty, but let's grab the first available if multiple
    diff_sets = info.get("_difficultyBeatmapSets", [])
    if not diff_sets:
        raise ValueError("No beatmap sets found in Info.dat")
        
    # Just grab the first set and its first difficulty for now
    diff_info = diff_sets[0].get("_difficultyBeatmaps", [])
    if not diff_info:
        raise ValueError("No difficulty beatmaps found.")
        
    beatmap_filename = diff_info[0].get("_beatmapFilename")
    dat_path = os.path.join(base_dir, beatmap_filename)
    
    if not os.path.exists(dat_path):
        raise FileNotFoundError(f"Beatmap data file {beatmap_filename} not found.")
        
    with open(dat_path, 'r', encoding='utf-8') as f:
        beatmap_data = json.load(f)
        
    # Check if _notes or something else (v2 vs v3)
    # v2 uses "_notes", v3 might use "colorNotes" or similar, Beat Sage generally outputs v2
    notes = beatmap_data.get("_notes", []) 
    if not notes and "colorNotes" in beatmap_data:
        # v3 format
        for n in beatmap_data["colorNotes"]:
             notes.append({"_time": n.get("b"), "_lineIndex": n.get("x")})
             
    return info, notes, base_dir

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
    
    cleaned = []
    
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

def package_rr_song(temp_dir, output_dir, bs_info, rr_notes):
    """
    Compiles the final Ragnarock custom song folder.

    Constructs the exact strict JSON schema required by Ragnarock's C#
    Unity parser, copies the cover art and audio, and saves them
    into the designated output directory.

    Args:
        temp_dir (str): The extraction directory containing audio/art assets.
        output_dir (str): The final destination folder for the Ragnarock song.
        bs_info (dict): The original Beat Saber Info.dat metadata.
        rr_notes (list): The final, filtered array of Ragnarock notes.
    """
    print(f"Packaging to {output_dir}...")
    os.makedirs(output_dir, exist_ok=True)
    
    # Locate audio and cover
    audio_file = bs_info.get("_songFilename")
    cover_file = bs_info.get("_coverImageFilename")
    
    # Copy Assets
    if audio_file and os.path.exists(os.path.join(temp_dir, audio_file)):
        shutil.copy2(os.path.join(temp_dir, audio_file), os.path.join(output_dir, audio_file))
    if cover_file and os.path.exists(os.path.join(temp_dir, cover_file)):
        shutil.copy2(os.path.join(temp_dir, cover_file), os.path.join(output_dir, cover_file))
        
    # the info.dat expects audio and cover to exist with same names, we'll keep the names.
    
    clean_song_name = bs_info.get("_songName", "Unknown Song")
    for ext in [".ogg", ".mp3", ".wav"]:
        clean_song_name = clean_song_name.replace(ext, "")
    clean_song_name = clean_song_name.strip()
    
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
        "_songApproximativeDuration": 300, # Approx fallback if not known
        "_songFilename": audio_file,
        "_coverImageFilename": cover_file,
        "_environmentName": "Midgard",
        "_songTimeOffset": 0,
        "_difficultyBeatmapSets": [
            {
                "_beatmapCharacteristicName": "Standard",
                "_difficultyBeatmaps": [
                    {
                        "_difficulty": "ExpertPlus",
                        "_difficultyRank": 7,
                        "_beatmapFilename": "ExpertPlusStandard.dat",
                        "_noteJumpMovementSpeed": 20,
                        "_noteJumpStartBeatOffset": 0
                    }
                ]
            }
        ]
    }
    
    with open(os.path.join(output_dir, "info.dat"), "w", encoding='utf-8') as f:
        json.dump(rr_info, f, indent=2)
        
    # Create ExpertPlusStandard.dat
    level_data = {
        "_version": "1.0.0",
        "_customData": {
            "_time": 0,
            "_BPMChanges": [],
            "_bookmarks": []
        },
        "_events": [],
        "_notes": rr_notes,
        "_obstacles": [],
        "_waypoints": []
    }
    
    with open(os.path.join(output_dir, "ExpertPlusStandard.dat"), "w", encoding='utf-8') as f:
        json.dump(level_data, f, separators=(',', ':')) # tighter json for notes
        
    print(f"Successfully packaged {rr_info.get('_songName')}!")

def main():
    parser = argparse.ArgumentParser(description="Convert Beat Saber maps to Ragnarock with playability filters.")
    parser.add_argument("zip_path", help="Path to the Beat Sage output .zip file")
    parser.add_argument("--min-delta", type=float, default=0.125, help="Minimum beat delta between notes (Speed Cap, default 0.125)")
    parser.add_argument("--hammer-limit", type=int, default=2, help="Max notes per beat (default 2)")
    
    args = parser.parse_args()
    
    zip_path = args.zip_path
    if not os.path.exists(zip_path):
        print(f"Error: Could not find file {zip_path}")
        return
        
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            bs_info, bs_notes, base_dir = extract_bs_data(zip_path, temp_dir)
            
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
            
            raw_rr_notes = convert_notes(bs_notes)
            
            clean_rr_notes = clean_chart(
                raw_rr_notes, 
                min_time_delta=args.min_delta, 
                hammer_limit=args.hammer_limit
            )
            
            package_rr_song(base_dir, output_dir, bs_info, clean_rr_notes)
            
        except Exception as e:
            print(f"An error occurred during conversion: {e}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        import sys
        sys.exit(1)
