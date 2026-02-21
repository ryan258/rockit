#!/bin/bash

# ==============================================================================
# Rockit - Batch Converter
#
# DESCRIPTION:
# Acts as the automated entry point for Phase 2. Scans the 'input/saged'
# directory for Beat Sage beatmaps (.zip) and processes them sequentially
# using the rockit.sh Python conversion engine. The playable custom song
# folders are emitted directly to the 'output/' directory.
# ==============================================================================

SAGED_DIR="input/saged"

mkdir -p "$SAGED_DIR"

shopt -s nullglob
files=("$SAGED_DIR"/*.zip)
if [ ${#files[@]} -eq 0 ]; then
    echo -e "\033[1;33mNo .zip files found in $SAGED_DIR/\033[0m"
    echo -e "Please add your Beat Sage .zip files to $SAGED_DIR/ and run again."
    exit 0
fi

echo -e "\033[1;34mStarting Batch Rockit Conversion...\033[0m"

for file in "$SAGED_DIR"/*.zip; do
    if [ -f "$file" ]; then
        filename=$(basename -- "$file")
        echo -e "\n\033[1;36mConverting: $filename\033[0m"
        if ! ./rockit.sh "$file"; then
            echo -e "\033[1;31mFailed: $filename\033[0m"
        fi
    fi
done

echo -e "\n\033[1;32mBatch conversion complete!\033[0m"
echo -e "Check the \033[1;36moutput/\033[0m directory for your playable Ragnarock folders."
