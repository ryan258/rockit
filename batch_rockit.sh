#!/bin/bash

# ==============================================================================
# Rockit - Batch Converter
#
# DESCRIPTION:
# Acts as the automated entry point for Phase 2. Scans the 'input/saged'
# directory for Beat Sage beatmaps (.zip) and processes them sequentially
# using the rockit.sh Python conversion engine. The playable custom song
# folders are emitted directly to the 'output/' directory.
#
# USAGE:
#   ./batch_rockit.sh [--deploy] [--deploy-only]
#
# OPTIONS:
#   --deploy       Forward to rockit.sh to auto-deploy each song to Quest via adb
#   --deploy-only  Skip conversion; deploy all existing output/ folders to Quest
# ==============================================================================

QUEST_CUSTOMSONGS_PATH="/sdcard/Android/data/com.wanadev.ragnarockquest/files/UE4Game/Ragnarock/Ragnarock/Saved/CustomSongs"

deploy_to_quest() {
    local output_dir="$1"
    local remote_song_dir="$QUEST_CUSTOMSONGS_PATH/$(basename "$output_dir")"

    echo -e "\033[1;34mRefreshing any existing Quest song folder...\033[0m"
    adb shell "rm -rf '$remote_song_dir'" >/dev/null

    echo -e "\033[1;34mDeploying $(basename "$output_dir") to Quest...\033[0m"
    if ! adb push "$output_dir" "$QUEST_CUSTOMSONGS_PATH/"; then
        echo -e "\033[1;31mError: adb push failed for $(basename "$output_dir").\033[0m"
        return 1
    fi
    return 0
}

check_adb() {
    if ! command -v adb >/dev/null 2>&1; then
        echo -e "\033[1;31mError: adb is required for deployment.\033[0m"
        echo "Install Android Platform Tools and make sure your Quest is connected with USB debugging enabled."
        exit 1
    fi

    if ! adb get-state >/dev/null 2>&1; then
        echo -e "\033[1;31mError: Unable to communicate with a Quest over adb.\033[0m"
        echo "Connect the headset, unlock it, and allow USB debugging/data access before retrying."
        exit 1
    fi

    adb shell "mkdir -p '$QUEST_CUSTOMSONGS_PATH'" >/dev/null
}

DEPLOY_FLAG=""
DEPLOY_ONLY=0
for arg in "$@"; do
    case "$arg" in
        --deploy) DEPLOY_FLAG="--deploy" ;;
        --deploy-only) DEPLOY_ONLY=1 ;;
    esac
done

# --deploy-only: push everything in output/ to Quest and exit
if [ "$DEPLOY_ONLY" -eq 1 ]; then
    OUTPUT_DIR="output"
    shopt -s nullglob
    dirs=("$OUTPUT_DIR"/*/)
    if [ ${#dirs[@]} -eq 0 ]; then
        echo -e "\033[1;33mNo folders found in $OUTPUT_DIR/\033[0m"
        echo "Run a conversion first, or add Ragnarock song folders to $OUTPUT_DIR/."
        exit 0
    fi

    check_adb

    echo -e "\033[1;34mDeploying ${#dirs[@]} song(s) to Quest...\033[0m"
    successes=0
    failures=0
    for dir in "${dirs[@]}"; do
        if deploy_to_quest "$dir"; then
            successes=$((successes + 1))
        else
            failures=$((failures + 1))
        fi
    done

    echo -e "\n\033[1;34mDeploy summary:\033[0m $successes succeeded, $failures failed."
    [ "$failures" -gt 0 ] && exit 1
    echo -e "\033[1;32mAll songs deployed to Quest!\033[0m"
    exit 0
fi

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

successes=0
failures=0

for file in "$SAGED_DIR"/*.zip; do
    if [ -f "$file" ]; then
        filename=$(basename -- "$file")
        echo -e "\n\033[1;36mConverting: $filename\033[0m"
        if ./rockit.sh $DEPLOY_FLAG "$file"; then
            successes=$((successes + 1))
        else
            failures=$((failures + 1))
            echo -e "\033[1;31mFailed: $filename\033[0m"
        fi
    fi
done

echo -e "\n\033[1;34mBatch conversion summary:\033[0m $successes succeeded, $failures failed."

if [ "$failures" -gt 0 ]; then
    echo -e "\033[1;31mBatch conversion finished with failures.\033[0m"
    exit 1
fi

echo -e "\033[1;32mBatch conversion complete!\033[0m"
echo -e "Check the \033[1;36moutput/\033[0m directory for your playable Ragnarock folders."
