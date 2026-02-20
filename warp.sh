#!/bin/bash

# Rockit - Audio Warping Preprocessor
# Usage: ./warp.sh <path_to_raw_audio> <output_name>

if [ -z "$1" ] || [ -z "$2" ]; then
    echo -e "\033[1;31mError: Missing arguments.\033[0m"
    echo -e "Usage: \033[1;36m./warp.sh <path_to_raw_audio> <output_name>\033[0m"
    echo ""
    echo -e "Example: \033[1;36m./warp.sh input/suno_song.mp3 output/suno_warped.mp3\033[0m"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="$2"

if [[ ! "$OUTPUT_FILE" == *.mp3 ]]; then
    OUTPUT_FILE="${OUTPUT_FILE%.*}.mp3"
    echo -e "\033[1;33mNotice: Auto-correcting output extension to .mp3 to guarantee Beat Sage compression limits.\033[0m"
fi

echo -e "\033[1;34mStarting Rockit Audio Warping...\033[0m"
echo -e "\033[1;33mThis process uses Demucs stem-separation and Librosa beat-tracking. It may take a few minutes.\033[0m"

uv run python warper.py "$INPUT_FILE" "$OUTPUT_FILE"

if [ $? -eq 0 ]; then
    echo -e "\033[1;32mWarping completed!\033[0m"
    echo -e "You can now upload the resulting \033[1;36m$OUTPUT_FILE\033[0m to Beat Sage."
else
    echo -e "\033[1;31mWarping failed. Check the error logs above.\033[0m"
    exit 1
fi
