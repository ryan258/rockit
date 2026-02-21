#!/bin/bash

# ==============================================================================
# Rockit - Batch Audio Warping
#
# DESCRIPTION:
# Acts as the automated entry point for Phase 0. Scans the 'input/to-warp'
# directory for raw audio files (.wav, .mp3, .ogg) and processes them
# sequentially using the warp.sh algorithm. The locked audio is saved to
# 'input/warped', ready for Beat Sage upload.
# ==============================================================================

TO_WARP_DIR="input/to-warp"
WARPED_DIR="input/warped"

mkdir -p "$WARPED_DIR"

shopt -s nullglob
files=("$TO_WARP_DIR"/*.{wav,mp3,ogg})
if [ ${#files[@]} -eq 0 ]; then
    echo -e "\033[1;33mNo valid audio files found in $TO_WARP_DIR/\033[0m"
    echo -e "Please add your .wav, .mp3, or .ogg files to $TO_WARP_DIR/ and run again."
    exit 0
fi

echo -e "\033[1;34mStarting Batch Audio Warping...\033[0m"

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        filename=$(basename -- "$file")
        basename="${filename%.*}"
        
        output_file="$WARPED_DIR/${basename}.mp3"
        
        echo -e "\n\033[1;36mProcessing: $filename\033[0m"
        if ! ./warp.sh "$file" "$output_file"; then
            echo -e "\033[1;31mFailed: $filename\033[0m"
        fi
    fi
done

echo -e "\n\033[1;32mBatch warping complete!\033[0m"
echo -e "You can now upload the files in \033[1;36m$WARPED_DIR/\033[0m to Beat Sage."
