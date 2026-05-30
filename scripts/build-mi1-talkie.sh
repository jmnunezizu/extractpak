#!/usr/bin/env sh
set -eu

usage() {
    cat <<'EOF'
Usage:
  scripts/build-mi1-talkie.sh --pak /path/to/Monkey1.pak \
    --builder /path/to/MI1_Ultimate_Talkie_Edition_Builder \
    --out /path/to/output-folder \
    --audio ogg [--skip-sbl] [--skip-music] [--dry-run] [--verbose]

This native helper currently performs the supported MI1 build steps:
  - validate inputs
  - extract classic/en/monkey1.000 and monkey1.001 with extractpak
  - patch them to monkey.000 and monkey.001 with native bspatch
  - extract WAV files from Speech.xwb and SFXNew.xwb, including WMA entries via ffmpeg
  - process voice.bat's SoX trim/mix steps and Ogg conversion
  - build monkey.sog with the native ScummVM speech archive packer
  - inject high quality SBL sound effects with the native sbl.bat port
  - convert CD and Special Edition music with the native cdaudio.bat port
  - copy the builder readme

Still TODO:
  - support FLAC/MP3/raw modes
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

PAK=
BUILDER=
OUT=
AUDIO=
DRY_RUN=0
VERBOSE=0
SKIP_SBL=0
SKIP_MUSIC=0

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
        --skip-sbl)
            SKIP_SBL=1
            shift
            ;;
        --skip-music)
            SKIP_MUSIC=1
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
    ogg) ;;
    *) die "MI1 native build currently supports --audio ogg only" ;;
esac

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
EXTRACTPAK=${EXTRACTPAK:-"$REPO_ROOT/extractpak"}
EXTRACT_XWB=${EXTRACT_XWB:-"$REPO_ROOT/scripts/extract-xwb.py"}
PROCESS_VOICES=${PROCESS_VOICES:-"$REPO_ROOT/scripts/process-mi1-voices.sh"}
PROCESS_SBL=${PROCESS_SBL:-"$REPO_ROOT/scripts/process-mi1-sbl.sh"}
PROCESS_MUSIC=${PROCESS_MUSIC:-"$REPO_ROOT/scripts/process-mi1-music.sh"}
BUILD_MONSTER=${BUILD_MONSTER:-"$REPO_ROOT/scripts/build-monster.py"}
WORK="$OUT/.work"
EXTRACTED="$WORK/extracted"
SPEECH_WAV="$WORK/speech-wav"
SFXNEW_WAV="$WORK/sfxnew-wav"
PROCESSED_VOICE="$WORK/processed-voice"
SBL_WORK="$WORK/sbl"
MUSIC_WORK="$WORK/music"
TOOLS="$BUILDER/tools"
PAK_DIR=$(CDPATH= cd -- "$(dirname -- "$PAK")" && pwd)
AUDIO_DIR="$PAK_DIR/audio"

require_file "$PAK"
require_dir "$BUILDER"
require_dir "$TOOLS"
require_file "$BUILDER/readme.txt"
require_file "$TOOLS/patch10.000"
require_file "$TOOLS/patch10.001"
require_file "$TOOLS/monster.tbl"
require_file "$AUDIO_DIR/Speech.xwb"
require_file "$AUDIO_DIR/SFXNew.xwb"
require_file "$EXTRACTPAK"
require_file "$EXTRACT_XWB"
require_file "$PROCESS_VOICES"
require_file "$PROCESS_SBL"
require_file "$PROCESS_MUSIC"
require_file "$BUILD_MONSTER"
require_tool bspatch "install bsdiff/bspatch; macOS usually provides /usr/bin/bspatch"
require_tool ffmpeg "install ffmpeg; it is required to decode WMA entries from SFXNew.xwb"

log "Monkey Island 1 Ultimate Talkie native helper"
log "pak:     $PAK"
log "builder: $BUILDER"
log "out:     $OUT"
log "audio:   $AUDIO"

if [ "$DRY_RUN" -eq 1 ]; then
    log ""
    log "Planned steps:"
    log "1. Clean and recreate output directory."
    log "2. Extract classic/en from Monkey1.pak using extractpak."
    log "3. Patch monkey1.000 and monkey1.001 to monkey.000 and monkey.001."
    log "4. Extract WAV files from Speech.xwb and SFXNew.xwb, decoding WMA entries with ffmpeg."
    log "5. Process voice.bat sample trims/mixes and convert samples to Ogg."
    log "6. Build monkey.sog with build-monster.py."
    if [ "$SKIP_SBL" -eq 1 ]; then
        log "7. Skip SBL resource injection."
    else
        log "7. Inject SBL sound effects into monkey.000/monkey.001."
    fi
    if [ "$SKIP_MUSIC" -eq 1 ]; then
        log "8. Skip music conversion."
    else
        log "8. Convert CD and Special Edition music to Ogg."
    fi
    log "9. Copy builder readme."
fi

clean_output_dir
run mkdir -p "$EXTRACTED"
run "$EXTRACTPAK" --only classic/en "$PAK" "$EXTRACTED"

SRC000="$EXTRACTED/classic/en/monkey1.000"
SRC001="$EXTRACTED/classic/en/monkey1.001"

if [ "$DRY_RUN" -eq 0 ]; then
    require_file "$SRC000"
    require_file "$SRC001"
fi

run bspatch "$SRC000" "$OUT/monkey.000" "$TOOLS/patch10.000"
run bspatch "$SRC001" "$OUT/monkey.001" "$TOOLS/patch10.001"

run mkdir -p "$SPEECH_WAV" "$SFXNEW_WAV"
if [ "$DRY_RUN" -eq 1 ]; then
    run "$EXTRACT_XWB" "$AUDIO_DIR/Speech.xwb" "$SPEECH_WAV"
    run "$EXTRACT_XWB" "$AUDIO_DIR/SFXNew.xwb" "$SFXNEW_WAV" --decode-wma
else
    if [ "$VERBOSE" -eq 1 ]; then
        "$EXTRACT_XWB" "$AUDIO_DIR/Speech.xwb" "$SPEECH_WAV" --verbose
        "$EXTRACT_XWB" "$AUDIO_DIR/SFXNew.xwb" "$SFXNEW_WAV" --decode-wma --verbose
    else
        "$EXTRACT_XWB" "$AUDIO_DIR/Speech.xwb" "$SPEECH_WAV"
        "$EXTRACT_XWB" "$AUDIO_DIR/SFXNew.xwb" "$SFXNEW_WAV" --decode-wma
    fi
fi

if [ "$DRY_RUN" -eq 1 ]; then
    run "$PROCESS_VOICES" --builder "$BUILDER" --speech-wav "$SPEECH_WAV" --sfx-wav "$SFXNEW_WAV" --out "$PROCESSED_VOICE" --audio "$AUDIO" --dry-run
    run "$BUILD_MONSTER" --table "$TOOLS/monster.tbl" --samples "$PROCESSED_VOICE/final-$AUDIO" --out "$OUT/monkey.sog" --format "$AUDIO" --dry-run
else
    if [ "$VERBOSE" -eq 1 ]; then
        "$PROCESS_VOICES" --builder "$BUILDER" --speech-wav "$SPEECH_WAV" --sfx-wav "$SFXNEW_WAV" --out "$PROCESSED_VOICE" --audio "$AUDIO" --verbose
        "$BUILD_MONSTER" --table "$TOOLS/monster.tbl" --samples "$PROCESSED_VOICE/final-$AUDIO" --out "$OUT/monkey.sog" --format "$AUDIO" --verbose
    else
        "$PROCESS_VOICES" --builder "$BUILDER" --speech-wav "$SPEECH_WAV" --sfx-wav "$SFXNEW_WAV" --out "$PROCESSED_VOICE" --audio "$AUDIO"
        "$BUILD_MONSTER" --table "$TOOLS/monster.tbl" --samples "$PROCESSED_VOICE/final-$AUDIO" --out "$OUT/monkey.sog" --format "$AUDIO"
    fi
fi

if [ "$SKIP_SBL" -eq 0 ]; then
    if [ "$DRY_RUN" -eq 1 ]; then
        run "$PROCESS_SBL" --builder "$BUILDER" --samples-wav "$PROCESSED_VOICE/samples-wav" --monkey000 "$OUT/monkey.000" --monkey001 "$OUT/monkey.001" --work "$SBL_WORK" --dry-run
    elif [ "$VERBOSE" -eq 1 ]; then
        "$PROCESS_SBL" --builder "$BUILDER" --samples-wav "$PROCESSED_VOICE/samples-wav" --monkey000 "$OUT/monkey.000" --monkey001 "$OUT/monkey.001" --work "$SBL_WORK" --verbose
    else
        "$PROCESS_SBL" --builder "$BUILDER" --samples-wav "$PROCESSED_VOICE/samples-wav" --monkey000 "$OUT/monkey.000" --monkey001 "$OUT/monkey.001" --work "$SBL_WORK"
    fi
else
    log "Skipping SBL resource injection."
fi

if [ "$SKIP_MUSIC" -eq 0 ]; then
    if [ "$DRY_RUN" -eq 1 ]; then
        run "$PROCESS_MUSIC" --audio-dir "$AUDIO_DIR" --out "$OUT" --work "$MUSIC_WORK" --audio "$AUDIO" --dry-run
    elif [ "$VERBOSE" -eq 1 ]; then
        "$PROCESS_MUSIC" --audio-dir "$AUDIO_DIR" --out "$OUT" --work "$MUSIC_WORK" --audio "$AUDIO" --verbose
    else
        "$PROCESS_MUSIC" --audio-dir "$AUDIO_DIR" --out "$OUT" --work "$MUSIC_WORK" --audio "$AUDIO"
    fi
else
    log "Skipping music conversion."
fi

run cp "$BUILDER/readme.txt" "$OUT/readme.txt"

if [ "$DRY_RUN" -eq 0 ]; then
    SPEECH_COUNT=$(find "$SPEECH_WAV" -type f -name '*.wav' | wc -l | tr -d ' ')
    SFXNEW_COUNT=$(find "$SFXNEW_WAV" -type f -name '*.wav' | wc -l | tr -d ' ')
    PROCESSED_COUNT=$(find "$PROCESSED_VOICE/final-$AUDIO" -type f -name "*.$AUDIO" | wc -l | tr -d ' ')
    if [ -d "$OUT/cd_music_$AUDIO" ]; then
        CD_MUSIC_COUNT=$(find "$OUT/cd_music_$AUDIO" -type f -name "*.$AUDIO" | wc -l | tr -d ' ')
    else
        CD_MUSIC_COUNT=0
    fi
    if [ -d "$OUT/se_music_$AUDIO" ]; then
        SE_MUSIC_COUNT=$(find "$OUT/se_music_$AUDIO" -type f -name "*.$AUDIO" | wc -l | tr -d ' ')
    else
        SE_MUSIC_COUNT=0
    fi
else
    SPEECH_COUNT=planned
    SFXNEW_COUNT=planned
    PROCESSED_COUNT=planned
    CD_MUSIC_COUNT=planned
    SE_MUSIC_COUNT=planned
fi

log ""
log "Native MI1 experimental Ogg build complete."
log "Generated or planned:"
log "  $OUT/monkey.000"
log "  $OUT/monkey.001"
log "  $OUT/monkey.sog"
log "  $OUT/readme.txt"
log "  $OUT/cd_music_$AUDIO/* ($CD_MUSIC_COUNT)"
log "  $OUT/se_music_$AUDIO/* ($SE_MUSIC_COUNT)"
log "  $SPEECH_WAV/*.wav ($SPEECH_COUNT)"
log "  $SFXNEW_WAV/*.wav ($SFXNEW_COUNT)"
log "  $PROCESSED_VOICE/final-$AUDIO/* ($PROCESSED_COUNT)"

if [ "$SKIP_SBL" -eq 0 ]; then
    log "  $SBL_WORK/pre-sbl/monkey.000"
    log "  $SBL_WORK/pre-sbl/monkey.001"
fi

if [ "$DRY_RUN" -eq 0 ]; then
    log ""
    log "Output folder contents:"
    find "$OUT" -maxdepth 2 -type f | sort
fi
