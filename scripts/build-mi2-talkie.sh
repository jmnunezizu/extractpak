#!/usr/bin/env sh
set -eu

usage() {
    cat <<'EOF'
Usage:
  scripts/build-mi2-talkie.sh --pak /path/to/monkey2.pak \
    --builder /path/to/MI2_Ultimate_Talkie_Edition_Builder \
    --out /path/to/output-folder \
    --audio flac|ogg|mp3|raw [--dry-run] [--verbose]

This native helper currently performs the supported steps:
  - validate inputs
  - extract classic/en/monkey2.000 and monkey2.001 with extractpak
  - patch monkey2.000 and monkey2.001 with native bspatch
  - extract WAV files from Speech.xwb and Patch.xwb
  - process voice.bat's SoX trim/mix steps and selected audio conversion
  - build a ScummVM compressed speech archive for ogg/flac/mp3
  - copy the builder readme

Raw monster.sou generation is not implemented yet.
EOF
}

die() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

log() {
    printf '%s\n' "$*"
}

verbose() {
    if [ "$VERBOSE" -eq 1 ]; then
        printf '%s\n' "$*"
    fi
}

run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '[dry-run] %s\n' "$*"
    else
        verbose "+ $*"
        "$@"
    fi
}

require_file() {
    [ -f "$1" ] || die "missing file: $1"
}

require_dir() {
    [ -d "$1" ] || die "missing directory: $1"
}

require_tool() {
    command -v "$1" >/dev/null 2>&1 || die "missing required tool '$1': $2"
}

clean_output_dir() {
    [ -n "$OUT" ] || die "--out is required"
    case "$OUT" in
        /|.) die "refusing to use unsafe output directory: $OUT" ;;
    esac

    if [ "$DRY_RUN" -eq 1 ]; then
        printf '[dry-run] rm -rf %s\n' "$OUT"
        printf '[dry-run] mkdir -p %s\n' "$OUT"
    else
        rm -rf "$OUT"
        mkdir -p "$OUT"
    fi
}

check_audio_tools() {
    case "$AUDIO" in
        raw)
            verbose "raw mode maps to the builder's wav/monster.sou path"
            ;;
        flac)
            if ! command -v flac >/dev/null 2>&1 && ! command -v ffmpeg >/dev/null 2>&1; then
                die "FLAC mode needs flac or ffmpeg for sample encoding."
            fi
            ;;
        ogg)
            if ! command -v oggenc >/dev/null 2>&1 && ! command -v sox >/dev/null 2>&1 && ! command -v ffmpeg >/dev/null 2>&1; then
                die "Ogg mode needs oggenc, sox, or ffmpeg for sample encoding."
            fi
            ;;
        mp3)
            if ! command -v lame >/dev/null 2>&1 && ! command -v ffmpeg >/dev/null 2>&1; then
                die "MP3 mode needs lame or ffmpeg for sample encoding."
            fi
            ;;
    esac

    require_tool sox "install SoX; it is required for voice.bat trimming, mixing, and sample conversion"
}

PAK=
BUILDER=
OUT=
AUDIO=
DRY_RUN=0
VERBOSE=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --pak)
            [ "$#" -ge 2 ] || die "--pak requires a value"
            PAK=$2
            shift 2
            ;;
        --builder)
            [ "$#" -ge 2 ] || die "--builder requires a value"
            BUILDER=$2
            shift 2
            ;;
        --out)
            [ "$#" -ge 2 ] || die "--out requires a value"
            OUT=$2
            shift 2
            ;;
        --audio)
            [ "$#" -ge 2 ] || die "--audio requires a value"
            AUDIO=$2
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --verbose)
            VERBOSE=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "unknown argument: $1"
            ;;
    esac
done

[ -n "$PAK" ] || die "--pak is required"
[ -n "$BUILDER" ] || die "--builder is required"
[ -n "$OUT" ] || die "--out is required"
[ -n "$AUDIO" ] || die "--audio is required"

case "$AUDIO" in
    flac|ogg|mp3|raw) ;;
    *) die "--audio must be one of: flac, ogg, mp3, raw" ;;
esac

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
EXTRACTPAK=${EXTRACTPAK:-"$REPO_ROOT/extractpak"}
EXTRACT_XWB=${EXTRACT_XWB:-"$REPO_ROOT/scripts/extract-xwb.py"}
PROCESS_VOICES=${PROCESS_VOICES:-"$REPO_ROOT/scripts/process-mi2-voices.sh"}
BUILD_MONSTER=${BUILD_MONSTER:-"$REPO_ROOT/scripts/build-monster.py"}
WORK="$OUT/.work"
EXTRACTED="$WORK/extracted"
SPEECH_WAV="$WORK/speech-wav"
PATCH_WAV="$WORK/patch-wav"
PROCESSED_VOICE="$WORK/processed-voice"
TOOLS="$BUILDER/tools"
PAK_DIR=$(CDPATH= cd -- "$(dirname -- "$PAK")" && pwd)
AUDIO_DIR="$PAK_DIR/audio"

require_file "$PAK"
require_dir "$BUILDER"
require_dir "$TOOLS"
require_file "$BUILDER/readme.txt"
require_file "$TOOLS/patch02.000"
require_file "$TOOLS/patch02.001"
require_file "$AUDIO_DIR/Speech.xwb"
require_file "$AUDIO_DIR/Patch.xwb"
require_file "$EXTRACTPAK"
require_file "$EXTRACT_XWB"
require_file "$PROCESS_VOICES"
require_file "$BUILD_MONSTER"
require_tool bspatch "install bsdiff/bspatch; macOS usually provides /usr/bin/bspatch"

check_audio_tools

log "Monkey Island 2 Ultimate Talkie native helper"
log "pak:     $PAK"
log "builder: $BUILDER"
log "out:     $OUT"
log "audio:   $AUDIO"

if [ "$DRY_RUN" -eq 1 ]; then
    log ""
    log "Planned steps:"
    log "1. Clean and recreate output directory."
    log "2. Extract classic/en from monkey2.pak using extractpak."
    log "3. Patch monkey2.000 and monkey2.001 using bspatch and builder patches."
    log "4. Extract WAV files from Speech.xwb and Patch.xwb."
    log "5. Process voice.bat sample trims/mixes and convert samples for $AUDIO mode."
    log "6. Build the ScummVM speech archive."
    log "7. Copy builder readme."
fi

clean_output_dir
run mkdir -p "$EXTRACTED"
run "$EXTRACTPAK" --only classic/en "$PAK" "$EXTRACTED"

SRC000="$EXTRACTED/classic/en/monkey2.000"
SRC001="$EXTRACTED/classic/en/monkey2.001"

if [ "$DRY_RUN" -eq 0 ]; then
    require_file "$SRC000"
    require_file "$SRC001"
fi

run bspatch "$SRC000" "$OUT/monkey2.000" "$TOOLS/patch02.000"
run bspatch "$SRC001" "$OUT/monkey2.001" "$TOOLS/patch02.001"
run mkdir -p "$SPEECH_WAV" "$PATCH_WAV"
if [ "$DRY_RUN" -eq 1 ]; then
    run "$EXTRACT_XWB" "$AUDIO_DIR/Speech.xwb" "$SPEECH_WAV"
    run "$EXTRACT_XWB" "$AUDIO_DIR/Patch.xwb" "$PATCH_WAV"
else
    if [ "$VERBOSE" -eq 1 ]; then
        "$EXTRACT_XWB" "$AUDIO_DIR/Speech.xwb" "$SPEECH_WAV" --verbose
        "$EXTRACT_XWB" "$AUDIO_DIR/Patch.xwb" "$PATCH_WAV" --verbose
    else
        "$EXTRACT_XWB" "$AUDIO_DIR/Speech.xwb" "$SPEECH_WAV"
        "$EXTRACT_XWB" "$AUDIO_DIR/Patch.xwb" "$PATCH_WAV"
    fi
fi
if [ "$DRY_RUN" -eq 1 ]; then
    run "$PROCESS_VOICES" --builder "$BUILDER" --speech-wav "$SPEECH_WAV" --patch-wav "$PATCH_WAV" --out "$PROCESSED_VOICE" --audio "$AUDIO" --dry-run
else
    if [ "$VERBOSE" -eq 1 ]; then
        "$PROCESS_VOICES" --builder "$BUILDER" --speech-wav "$SPEECH_WAV" --patch-wav "$PATCH_WAV" --out "$PROCESSED_VOICE" --audio "$AUDIO" --verbose
    else
        "$PROCESS_VOICES" --builder "$BUILDER" --speech-wav "$SPEECH_WAV" --patch-wav "$PATCH_WAV" --out "$PROCESSED_VOICE" --audio "$AUDIO"
    fi
fi
case "$AUDIO" in
    ogg)
        ARCHIVE_NAME=monkey2.sog
        ;;
    flac)
        ARCHIVE_NAME=monkey2.sof
        ;;
    mp3)
        ARCHIVE_NAME=monkey2.so3
        ;;
    raw)
        ARCHIVE_NAME=monster.sou
        ;;
esac
if [ "$DRY_RUN" -eq 1 ]; then
    run "$BUILD_MONSTER" --table "$TOOLS/monster.tbl" --samples "$PROCESSED_VOICE/final-$AUDIO" --out "$OUT/$ARCHIVE_NAME" --format "$AUDIO" --dry-run
else
    if [ "$VERBOSE" -eq 1 ]; then
        "$BUILD_MONSTER" --table "$TOOLS/monster.tbl" --samples "$PROCESSED_VOICE/final-$AUDIO" --out "$OUT/$ARCHIVE_NAME" --format "$AUDIO" --verbose
    else
        "$BUILD_MONSTER" --table "$TOOLS/monster.tbl" --samples "$PROCESSED_VOICE/final-$AUDIO" --out "$OUT/$ARCHIVE_NAME" --format "$AUDIO"
    fi
fi
run cp "$BUILDER/readme.txt" "$OUT/readme.txt"

if [ "$DRY_RUN" -eq 0 ]; then
    SPEECH_COUNT=$(find "$SPEECH_WAV" -type f -name '*.wav' | wc -l | tr -d ' ')
    PATCH_COUNT=$(find "$PATCH_WAV" -type f -name '*.wav' | wc -l | tr -d ' ')
    case "$AUDIO" in
        raw) PROCESSED_EXT=wav ;;
        *) PROCESSED_EXT=$AUDIO ;;
    esac
    PROCESSED_COUNT=$(find "$PROCESSED_VOICE/final-$AUDIO" -type f -name "*.$PROCESSED_EXT" | wc -l | tr -d ' ')
else
    SPEECH_COUNT=planned
    PATCH_COUNT=planned
    PROCESSED_COUNT=planned
fi

log ""
if [ "$AUDIO" = raw ]; then
    log "Native partial build complete."
else
    log "Native experimental build complete."
fi
log "Generated or planned:"
log "  $OUT/monkey2.000"
log "  $OUT/monkey2.001"
log "  $OUT/readme.txt"
log "  $SPEECH_WAV/*.wav ($SPEECH_COUNT)"
log "  $PATCH_WAV/*.wav ($PATCH_COUNT)"
log "  $PROCESSED_VOICE/final-$AUDIO/* ($PROCESSED_COUNT)"
log "  $OUT/$ARCHIVE_NAME"

log ""
if [ "$AUDIO" = raw ]; then
    log "TODO: raw monster.sou generation is not yet native."
else
    log "Experimental ScummVM compressed speech archive generated."
fi

if [ "$DRY_RUN" -eq 0 ]; then
    log ""
    log "Output folder contents:"
    find "$OUT" -maxdepth 2 -type f | sort
    log ""
    log "ScummVM: add this folder as the game directory:"
    log "  $OUT"
fi
