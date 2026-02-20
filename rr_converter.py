import os
import json
import zipfile
import tempfile
import shutil
import argparse
from pathlib import Path

def extract_bs_data(zip_path, temp_dir):
    """Extracts Beat Saber zip and returns info and the notes from highest difficulty."""
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
    """Translates Beat Saber coordinates to Ragnarock drums."""
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
                "_time": float(time),
                "_lineIndex": int(line_index)
            })
            
    return rr_notes

def clean_chart(notes, min_time_delta=0.125, hammer_limit=2):
    """Applies playability filters to the translated notes."""
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
    """Packages the Ragnarock song directory."""
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
    
    # Create Ragnarock Info.dat
    rr_info = {
        "_version": "2.0.0",
        "_songName": bs_info.get("_songName", "Unknown Song"),
        "_songSubName": bs_info.get("_songSubName", ""),
        "_songAuthorName": bs_info.get("_songAuthorName", "Suno AI"),
        "_levelAuthorName": bs_info.get("_levelAuthorName", "rr_converter"),
        "_beatsPerMinute": bs_info.get("_beatsPerMinute", 120),
        "_previewStartTime": bs_info.get("_previewStartTime", 12.0),
        "_previewDuration": bs_info.get("_previewDuration", 10.0),
        "_songFilename": audio_file,
        "_coverImageFilename": cover_file,
        "_environmentName": "Midgard",
        "_songTimeOffset": bs_info.get("_songTimeOffset", 0),
        "_customData": {
            "_contributors": [],
            "_customEnvironment": "",
            "_customEnvironmentHash": ""
        },
        "_difficultyBeatmapSets": [
            {
                "_beatmapCharacteristicName": "Standard",
                "_difficultyBeatmaps": [
                    {
                        "_difficulty": "Normal",
                        "_difficultyRank": 3,
                        "_beatmapFilename": "Level1.json",
                        "_noteJumpMovementSpeed": 10,
                        "_noteJumpStartBeatOffset": 0,
                        "_customData": {
                            "_difficultyLabel": "Converted",
                            "_editorOffset": 0,
                            "_editorOldOffset": 0,
                            "_warnings": [],
                            "_information": [],
                            "_suggestions": [],
                            "_requirements": []
                        }
                    }
                ]
            }
        ]
    }
    
    with open(os.path.join(output_dir, "Info.dat"), "w", encoding='utf-8') as f:
        json.dump(rr_info, f, indent=2)
        
    # Create Level1.json
    level_data = {
        "_version": "2.0.0",
        "_notes": rr_notes,
        "_obstacles": [],
        "_events": [],
        "_customData": {
            "_time": 0.0,
            "_bpmChanges": [],
            "_bookmarks": []
        }
    }
    
    with open(os.path.join(output_dir, "Level1.json"), "w", encoding='utf-8') as f:
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
        
    # Determine output folder name
    base_name = os.path.splitext(os.path.basename(zip_path))[0]
    
    # Ensure the output directory is inside the 'output' folder in the project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    output_base_dir = os.path.join(project_root, "output")
    os.makedirs(output_base_dir, exist_ok=True)
    
    output_dir = os.path.join(output_base_dir, f"{base_name}_Ragnarock")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            bs_info, bs_notes, base_dir = extract_bs_data(zip_path, temp_dir)
            
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
