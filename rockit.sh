#!/bin/bash

# ==============================================================================
# Rockit - Beat Sage to Ragnarock Converter Entry Point
#
# DESCRIPTION:
# Acts as Phase 2 in the Rockit pipeline. It takes a compressed beatmap generated
# by Beat Sage (.zip), unzips the payload, mathematically converts the spatial
# Beat Saber notes to 4-lane Ragnarock drums, applies physical playability
# filters (culling impossible AI spam), and generates a playable Unity standard
# custom mapping folder.
#
# USAGE:
#   ./rockit.sh [--deploy] <path_to_beatsaber_zip>
#
# DEPENDENCIES:
#   - uv (Python package manager)
#   - adb (Android Debug Bridge, only required with --deploy)
#   - rr_converter.py
# ==============================================================================

set -o pipefail

QUEST_CUSTOMSONGS_PATH="/sdcard/Android/data/com.wanadev.ragnarockquest/files/CustomSongs"

print_usage() {
    echo -e "Usage: \033[1;36m./rockit.sh [--deploy] <path_to_beatsaber_zip>\033[0m"
    echo ""
    echo -e "Pipeline Instructions:"
    echo "  1. Warp your audio to a fixed BPM and export as .ogg"
    echo "  2. Upload the .ogg to https://beatsage.com/ and download the .zip"
    echo "  3. Run this script with the downloaded .zip to create a Ragnarock level"
    echo "  4. Add --deploy to copy the generated folder straight to a connected Quest"
}

deploy_to_quest() {
    local output_dir="$1"
    local remote_song_dir="$QUEST_CUSTOMSONGS_PATH/$(basename "$output_dir")"

    if ! command -v adb >/dev/null 2>&1; then
        echo -e "\033[1;31mError: adb is required for --deploy.\033[0m"
        echo "Install Android Platform Tools and make sure your Quest is connected with USB debugging enabled."
        return 1
    fi

    local adb_state
    if ! adb_state=$(adb get-state 2>&1); then
        echo -e "\033[1;31mError: Unable to communicate with a Quest over adb.\033[0m"
        echo "$adb_state"
        echo "Connect the headset, unlock it, and allow USB debugging/data access before retrying."
        return 1
    fi

    echo -e "\033[1;34mPreparing Quest CustomSongs directory...\033[0m"
    if ! adb shell "mkdir -p '$QUEST_CUSTOMSONGS_PATH'" >/dev/null; then
        echo -e "\033[1;31mError: Failed to create the Quest CustomSongs directory.\033[0m"
        return 1
    fi

    echo -e "\033[1;34mRefreshing any existing Quest song folder...\033[0m"
    if ! adb shell "rm -rf '$remote_song_dir'" >/dev/null; then
        echo -e "\033[1;31mError: Failed to clear the existing Quest song folder.\033[0m"
        return 1
    fi

    echo -e "\033[1;34mDeploying $(basename "$output_dir") to Quest...\033[0m"
    if ! adb push "$output_dir" "$QUEST_CUSTOMSONGS_PATH/"; then
        echo -e "\033[1;31mError: adb push failed.\033[0m"
        return 1
    fi

    echo -e "\033[1;32mQuest deployment completed successfully!\033[0m"
    echo "Quest destination: $remote_song_dir"
    return 0
}

DEPLOY_AFTER_CONVERSION=0
ZIP_FILE=""

while [ $# -gt 0 ]; do
    case "$1" in
        --deploy)
            DEPLOY_AFTER_CONVERSION=1
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        -*)
            echo -e "\033[1;31mError: Unknown option $1\033[0m"
            print_usage
            exit 1
            ;;
        *)
            if [ -n "$ZIP_FILE" ]; then
                echo -e "\033[1;31mError: Unexpected extra argument $1\033[0m"
                print_usage
                exit 1
            fi
            ZIP_FILE="$1"
            ;;
    esac
    shift
done

if [ -z "$ZIP_FILE" ]; then
    echo -e "\033[1;31mError: No input file provided.\033[0m"
    print_usage
    exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
    echo -e "\033[1;31mError: uv is required to run the converter with project dependencies.\033[0m"
    exit 1
fi

if [ "$DEPLOY_AFTER_CONVERSION" -eq 1 ] && ! command -v adb >/dev/null 2>&1; then
    echo -e "\033[1;31mError: adb is required for --deploy.\033[0m"
    echo "Install Android Platform Tools and make sure your Quest is connected with USB debugging enabled."
    exit 1
fi

echo -e "\033[1;34mStarting Rockit Conversion Pipeline...\033[0m"

conversion_log="$(mktemp)"
cleanup() {
    rm -f "$conversion_log"
}
trap cleanup EXIT

if uv run python rr_converter.py "$ZIP_FILE" 2>&1 | tee "$conversion_log"; then
    echo -e "\033[1;32mConversion completed successfully!\033[0m"
else
    echo -e "\033[1;31mConversion failed. Check the error logs above.\033[0m"
    exit 1
fi

if [ "$DEPLOY_AFTER_CONVERSION" -eq 1 ]; then
    output_dir="$(sed -n 's/^Output folder: //p' "$conversion_log" | tail -n 1)"
    if [ -z "$output_dir" ]; then
        echo -e "\033[1;31mError: Conversion succeeded but the output folder could not be determined.\033[0m"
        exit 1
    fi

    deploy_to_quest "$output_dir"
fi
