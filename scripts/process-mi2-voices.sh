#!/usr/bin/env sh
set -eu

usage() {
    cat <<'EOF'
Usage:
  scripts/process-mi2-voices.sh --builder /path/to/MI2_Ultimate_Talkie_Edition_Builder \
    --speech-wav /path/to/.work/speech-wav \
    --patch-wav /path/to/.work/patch-wav \
    --out /path/to/.work/processed-voice \
    --audio ogg|flac|mp3|raw [--dry-run] [--verbose]

This processes extracted Speech.xwb and Patch.xwb WAV files through the native
equivalent of tools/voice.bat and the selected audio conversion batch file.
It does not build monkey2.sog/so3/sof or monster.sou.
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

require_file() {
    [ -f "$1" ] || die "missing file: $1"
}

require_dir() {
    [ -d "$1" ] || die "missing directory: $1"
}

require_tool() {
    command -v "$1" >/dev/null 2>&1 || die "missing required tool '$1': $2"
}

sox_can_write() {
    sox --help-format "$1" 2>/dev/null | grep -q 'Writes:'
}

safe_clean_dir() {
    [ -n "$OUT" ] || die "--out is required"
    case "$OUT" in
        /|.) die "refusing to use unsafe output directory: $OUT" ;;
    esac

    if [ "$DRY_RUN" -eq 1 ]; then
        log "[dry-run] rm -rf $OUT"
        log "[dry-run] mkdir -p $OUT"
    else
        rm -rf "$OUT"
        mkdir -p "$OUT"
    fi
}

count_wavs() {
    find "$1" -type f -name '*.wav' | wc -l | tr -d ' '
}

expected_monster_entries() {
    strings -n 4 "$TOOLS/monster.tbl" | awk '{ print substr($0, 9) }' | sort -u | wc -l | tr -d ' '
}

normalize_wavs() {
    src_dir=$1
    label=$2

    for wav in "$src_dir"/*.wav; do
        [ -f "$wav" ] || continue
        base=$(basename "$wav")
        dst="$SAMPLES/$base"
        verbose "normalise $label/$base -> samples-wav/$base"
        sox "$wav" -D "$dst"
    done
}

special_trim() {
    src=$1
    dst=$2
    start=$3
    length=$4

    require_file "$SAMPLES/$src"
    verbose "sox trim $src $start $length -> $dst"
    sox "$SAMPLES/$src" -D -c 1 -t wav -V0 "$SAMPLES/$dst" trim "$start" "$length"
}

make_special_cases() {
    require_file "$SAMPLES/000003d5.wav"
    require_file "$SAMPLES/vx112_DemBones_SE_nl_1.wav"
    require_file "$SAMPLES/vx112_DemBones_SE_nl_2.wav"

    verbose "build _cdt_parlay.wav from 000003d5.wav"
    sox -r 42777 "$SAMPLES/000003d5.wav" -D -c 1 -t wav -V0 "$TEMP/temp1.wav" trim 2.866 1.230
    sox "$TEMP/temp1.wav" -r 48016 -D -c 1 -t wav -V0 "$TEMP/temp2.wav"
    sox "$SAMPLES/000003d5.wav" -D -c 1 -t wav -V0 "$TEMP/temp1.wav" trim 0.000 2.553
    sox "$TEMP/temp1.wav" "$TEMP/temp2.wav" "$SAMPLES/_cdt_parlay.wav"

    special_trim vx112_DemBones_SE_nl_1.wav _cdt_arm_con1.wav 71.881 2.073
    special_trim vx112_DemBones_SE_nl_1.wav _cdt_hea_con1.wav 10.943 2.059
    special_trim vx112_DemBones_SE_nl_1.wav _cdt_hip_con1.wav 31.281 2.020
    special_trim vx112_DemBones_SE_nl_2.wav _cdt_leg_con1.wav 31.257 2.075
    special_trim vx112_DemBones_SE_nl_1.wav _cdt_rip_con1.wav 79.304 2.056
    special_trim vx112_DemBones_SE_nl_1.wav _cdt_arm_bone.wav 33.536 1.098
    special_trim vx112_DemBones_SE_nl_1.wav _cdt_hea_bone.wav 74.208 1.178
    special_trim vx112_DemBones_SE_nl_1.wav _cdt_hip_bone.wav 20.673 1.184
    special_trim vx112_DemBones_SE_nl_1.wav _cdt_leg_bone.wav 53.883 1.245
    special_trim vx112_DemBones_SE_nl_1.wav _cdt_rip_bone.wav 40.999 1.161
    special_trim vx112_DemBones_SE_nl_1.wav _cdt_arm_con2.wav 34.994 2.068
    special_trim vx112_DemBones_SE_nl_1.wav _cdt_hea_con2.wav 75.610 2.099
    special_trim vx112_DemBones_SE_nl_2.wav _cdt_hip_con2.wav 35.005 2.051
    special_trim vx112_DemBones_SE_nl_1.wav _cdt_leg_con2.wav 55.252 2.110
    special_trim vx112_DemBones_SE_nl_1.wav _cdt_rip_con2.wav 14.655 2.009

    verbose "copy _cdt_silence -> _cdt_silence.wav"
    cp "$TOOLS/_cdt_silence" "$SAMPLES/_cdt_silence.wav"

    if [ "$VERBOSE" -eq 0 ]; then
        rm -f "$TEMP/temp1.wav" "$TEMP/temp2.wav"
    fi
}

encode_one() {
    wav=$1
    base=$(basename "$wav" .wav)

    case "$AUDIO" in
        raw)
            dst="$FINAL/$base.wav"
            verbose "encode raw wav $base"
            sox "$wav" -D -b 8 -c 1 -r 22050 -t wav -V0 "$dst"
            ;;
        flac)
            dst="$FINAL/$base.flac"
            verbose "encode flac $base"
            if command -v flac >/dev/null 2>&1; then
                flac -f -s -8 -o "$dst" "$wav"
            else
                ffmpeg -hide_banner -loglevel error -y -i "$wav" -c:a flac "$dst"
            fi
            ;;
        ogg)
            dst="$FINAL/$base.ogg"
            verbose "encode ogg $base"
            if sox_can_write ogg; then
                sox "$wav" --comment "" "$dst"
            elif command -v oggenc >/dev/null 2>&1; then
                oggenc -Q -o "$dst" "$wav"
            else
                ffmpeg -hide_banner -loglevel error -y -i "$wav" -c:a vorbis -q:a 5 -strict -2 "$dst"
            fi
            ;;
        mp3)
            dst="$FINAL/$base.mp3"
            verbose "encode mp3 $base"
            if command -v lame >/dev/null 2>&1; then
                lame --quiet "$wav" "$dst"
            else
                ffmpeg -hide_banner -loglevel error -y -i "$wav" -c:a libmp3lame "$dst"
            fi
            ;;
    esac
}

encode_samples() {
    for wav in "$SAMPLES"/*.wav; do
        [ -f "$wav" ] || continue
        encode_one "$wav"
    done
}

probe_outputs() {
    checked=0
    for file in "$FINAL"/*; do
        [ -f "$file" ] || continue
        if command -v sox >/dev/null 2>&1; then
            sox "$file" -n stat >/dev/null 2>&1 || die "failed to probe processed audio: $file"
        elif command -v ffmpeg >/dev/null 2>&1; then
            ffmpeg -hide_banner -loglevel error -i "$file" -f null - >/dev/null 2>&1 || die "failed to probe processed audio: $file"
        fi
        checked=$((checked + 1))
        [ "$checked" -ge 3 ] && break
    done
    log "Probed $checked processed audio file(s)."
}

BUILDER=
SPEECH_WAV=
PATCH_WAV=
OUT=
AUDIO=
DRY_RUN=0
VERBOSE=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --builder)
            [ "$#" -ge 2 ] || die "--builder requires a value"
            BUILDER=$2
            shift 2
            ;;
        --speech-wav)
            [ "$#" -ge 2 ] || die "--speech-wav requires a value"
            SPEECH_WAV=$2
            shift 2
            ;;
        --patch-wav)
            [ "$#" -ge 2 ] || die "--patch-wav requires a value"
            PATCH_WAV=$2
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

[ -n "$BUILDER" ] || die "--builder is required"
[ -n "$SPEECH_WAV" ] || die "--speech-wav is required"
[ -n "$PATCH_WAV" ] || die "--patch-wav is required"
[ -n "$OUT" ] || die "--out is required"
[ -n "$AUDIO" ] || die "--audio is required"

case "$AUDIO" in
    flac|ogg|mp3|raw) ;;
    *) die "--audio must be one of: flac, ogg, mp3, raw" ;;
esac

TOOLS="$BUILDER/tools"
SAMPLES="$OUT/samples-wav"
TEMP="$OUT/tmp"
FINAL="$OUT/final-$AUDIO"

require_dir "$BUILDER"
require_dir "$TOOLS"
require_file "$TOOLS/_cdt_silence"
require_file "$TOOLS/monster.tbl"
require_dir "$SPEECH_WAV"
require_dir "$PATCH_WAV"
require_file "$SPEECH_WAV/00000000.wav"
require_file "$SPEECH_WAV/000003d5.wav"
require_file "$PATCH_WAV/vx112_DemBones_SE_nl_1.wav"
require_file "$PATCH_WAV/vx112_DemBones_SE_nl_2.wav"
require_tool sox "install SoX; it is required for voice.bat trim/mix/conversion steps"

case "$AUDIO" in
    flac)
        if ! command -v flac >/dev/null 2>&1 && ! command -v ffmpeg >/dev/null 2>&1; then
            die "FLAC output requires flac or ffmpeg"
        fi
        ;;
    ogg)
        if ! sox_can_write ogg && ! command -v oggenc >/dev/null 2>&1 && ! command -v ffmpeg >/dev/null 2>&1; then
            die "Ogg output requires SoX with Ogg support, oggenc, or ffmpeg"
        fi
        ;;
    mp3)
        if ! command -v lame >/dev/null 2>&1 && ! command -v ffmpeg >/dev/null 2>&1; then
            die "MP3 output requires lame or ffmpeg"
        fi
        ;;
esac

log "MI2 voice processing"
log "speech wav: $SPEECH_WAV"
log "patch wav:  $PATCH_WAV"
log "out:        $OUT"
log "audio:      $AUDIO"

if [ "$DRY_RUN" -eq 1 ]; then
    log ""
    log "Planned voice steps:"
    log "1. Normalize Speech.xwb and Patch.xwb WAV files into samples-wav/."
    log "2. Create voice.bat special-case _cdt_*.wav files with SoX."
    log "3. Convert samples to $AUDIO files in final-$AUDIO/."
    log "4. Stop before build_monster archive generation."
    exit 0
fi

safe_clean_dir
mkdir -p "$SAMPLES" "$TEMP" "$FINAL"

normalize_wavs "$SPEECH_WAV" speech
normalize_wavs "$PATCH_WAV" patch
NORMALIZED_COUNT=$(count_wavs "$SAMPLES")

make_special_cases
SAMPLE_COUNT=$(count_wavs "$SAMPLES")

encode_samples
case "$AUDIO" in
    raw) EXT=wav ;;
    *) EXT=$AUDIO ;;
esac
PROCESSED_COUNT=$(find "$FINAL" -type f -name "*.$EXT" | wc -l | tr -d ' ')
EXPECTED_COUNT=$(expected_monster_entries)

log ""
log "Voice processing complete."
log "Normalized WAV files: $NORMALIZED_COUNT"
log "WAV files after special cases: $SAMPLE_COUNT"
log "Processed $AUDIO files: $PROCESSED_COUNT"
log "Expected unique monster.tbl references: $EXPECTED_COUNT"
if [ "$PROCESSED_COUNT" -ne "$EXPECTED_COUNT" ]; then
    log "warning: processed file count differs from monster.tbl references; build_monster may intentionally ignore unused samples."
fi

probe_outputs

log "Processed files are in:"
log "  $FINAL"
