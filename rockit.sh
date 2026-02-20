#!/bin/bash

# Rockit - Beat Sage to Ragnarock Converter Entry Point
# Usage: ./rockit.sh <path_to_beatsaber_zip> [output_directory]

if [ -z "$1" ]; then
    echo -e "\033[1;31mError: No input file provided.\033[0m"
    echo -e "Usage: \033[1;36m./rockit.sh <path_to_beatsaber_zip>\033[0m"
    echo ""
    echo -e "Pipeline Instructions:"
    echo "  1. Warp your audio to a fixed BPM and export as .ogg"
    echo "  2. Upload the .ogg to https://beatsage.com/ and download the .zip"
    echo "  3. Run this script with the downloaded .zip to create a Ragnarock level"
    exit 1
fi

ZIP_FILE="$1"

echo -e "\033[1;34mStarting Rockit Conversion Pipeline...\033[0m"

python3 rr_converter.py "$ZIP_FILE"

if [ $? -eq 0 ]; then
    echo -e "\033[1;32mConversion completed successfully!\033[0m"
else
    echo -e "\033[1;31mConversion failed. Check the error logs above.\033[0m"
    exit 1
fi
