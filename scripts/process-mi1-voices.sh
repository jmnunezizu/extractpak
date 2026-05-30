#!/usr/bin/env sh
set -eu

usage() {
    cat <<'EOF'
Usage:
  scripts/process-mi1-voices.sh --builder /path/to/MI1_Ultimate_Talkie_Edition_Builder \
    --speech-wav /path/to/.work/speech-wav \
    --sfx-wav /path/to/.work/sfxnew-wav \
    --out /path/to/.work/processed-voice \
    --audio ogg|flac|mp3|raw [--dry-run] [--verbose]

This processes extracted MI1 Speech.xwb and SFXNew.xwb WAV files through the
native equivalent of tools/voice.bat and selected audio conversion.
It does not perform sbl.bat resource injection or cdaudio.bat music conversion.
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

monster_refs() {
    awk '{ name = substr($0, 9); sub(/\r$/, "", name); print name }' "$TOOLS/monster.tbl"
}

expected_monster_entries() {
    monster_refs | sort -u | wc -l | tr -d ' '
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

sample_path() {
    printf '%s/%s' "$SAMPLES" "$1"
}

special_trim() {
    src=$1
    dst=$2
    start=$3
    length=$4

    require_file "$(sample_path "$src")"
    verbose "sox trim $src $start $length -> $dst"
    sox "$(sample_path "$src")" -D -c 1 -t wav -V0 "$(sample_path "$dst")" trim "$start" "$length"
}

special_gain() {
    src=$1
    dst=$2
    gain=$3

    require_file "$(sample_path "$src")"
    verbose "sox gain $src $gain -> $dst"
    sox "$(sample_path "$src")" -D -c 1 -t wav -V0 "$(sample_path "$dst")" gain "$gain"
}

special_compand() {
    src=$1
    dst=$2
    attack=$3
    curve=$4
    gain=$5

    require_file "$(sample_path "$src")"
    verbose "sox compand $src -> $dst"
    sox "$(sample_path "$src")" -D -c 1 -t wav -V0 "$(sample_path "$dst")" compand 0.0,0.5 "$curve" "$gain" -99
}

special_mix_compand() {
    src1=$1
    src2=$2
    dst=$3
    curve=$4
    gain=$5

    require_file "$(sample_path "$src1")"
    require_file "$(sample_path "$src2")"
    verbose "sox mix $src1 $src2 -> $dst"
    sox "$(sample_path "$src1")" "$(sample_path "$src2")" -m -D -c 1 -t wav -V0 "$(sample_path "$dst")" compand 0.0,0.5 "$curve" "$gain" -99
}

make_special_cases() {
    verbose "copy _cdt_silence -> _cdt_silence.wav"
    cp "$TOOLS/_cdt_silence" "$(sample_path _cdt_silence.wav)"

    special_trim STN_59_stans_89_1.wav _cdt_you_could.wav 0.000 3.375
    special_trim STN_59_stans_76_1.wav _cdt_10000.wav 3.002 0.962
    special_trim STN_59_stans_96_1.wav _cdt_9000.wav 3.344 1.009
    special_trim STN_59_stans_97_1.wav _cdt_8000.wav 3.396 0.695
    special_trim STN_59_stans_99_1.wav _cdt_7000.wav 3.204 0.812
    special_trim STN_59_stans_101_1.wav _cdt_6000.wav 3.159 0.813
    special_trim STN_59_stans_103_1.wav _cdt_5000.wav 3.402 0.765
    special_trim STN_59_stans_69_2.wav _cdt_4000.wav 0.000 0.919
    special_trim STN_59_stans_67_2.wav _cdt_3000.wav 0.000 1.395
    special_trim STN_59_stans_113_1.wav _cdt_900.wav 4.180 0.430
    special_trim STN_59_stans_103_1.wav _cdt_800.wav 4.180 0.430
    special_trim STN_59_stans_101_1.wav _cdt_700.wav 3.972 0.626
    special_trim STN_59_stans_99_1.wav _cdt_600.wav 4.016 0.578
    special_trim STN_59_stans_89_1.wav _cdt_500.wav 4.318 0.508
    special_trim STN_59_stans_112_1.wav _cdt_400.wav 3.713 0.640
    special_trim STN_59_stans_102_1.wav _cdt_300.wav 3.860 0.692
    special_trim STN_59_stans_100_1.wav _cdt_200.wav 3.830 0.691
    special_trim STN_59_stans_98_1.wav _cdt_100.wav 3.721 0.663
    special_trim STN_59_stans_97_1.wav _cdt_n50.wav 4.593 0.613
    special_trim STN_59_stans_90_1.wav _cdt_pieces.wav 4.531 0.705
    special_trim 130_Monkey_Bride.wav _cdt_bride.wav 5.382 4.246

    special_mix_compand SMK_43_trainers-house_16_22.wav 50_sound_SBL_the-machine.wav _cdt_machine.wav -4.3,-4.3,-0,-4.3 4
    special_gain Sheriff_UnknownFilename_03.wav _cdt_psssst.wav -15
    special_compand TRL_57_bridge_16_2.wav _cdt_eatya.wav 0.0,0.5 -8.3,-8.3,-0,-8.3 8
    special_gain GUY_20_main-beach_71_3.wav _cdt_ht.wav -4
    special_trim 2_sound_SBL_door-open.wav _cdt_dooropen.wav 0.005 0.390
    special_trim 3_sound_SBL_door-close.wav _cdt_doorclose.wav 0.011 0.222
    sox "$(sample_path _cdt_dooropen.wav)" -D -c 1 -t wav -V0 "$(sample_path _cdt_dooropen.tmp.wav)" gain -3
    mv "$(sample_path _cdt_dooropen.tmp.wav)" "$(sample_path _cdt_dooropen.wav)"
    sox "$(sample_path _cdt_doorclose.wav)" -D -c 1 -t wav -V0 "$(sample_path _cdt_doorclose.tmp.wav)" gain -2
    mv "$(sample_path _cdt_doorclose.tmp.wav)" "$(sample_path _cdt_doorclose.wav)"
    special_trim 67_sound_SBL_soup-bubble.wav _cdt_bubble.wav 0.013 0.337
    sox "$(sample_path _cdt_bubble.wav)" -D -c 1 -t wav -V0 "$(sample_path _cdt_bubble.tmp.wav)" gain -6
    mv "$(sample_path _cdt_bubble.tmp.wav)" "$(sample_path _cdt_bubble.wav)"

    special_mix_compand 22_sound_SBL_whack_01.wav 110_Guybrush_Punched.wav _cdt_guykick1.wav -4.3,-4.3,-0,-4.3 4
    special_mix_compand 22_sound_SBL_whack_01.wav StanTheSalesman_Grunt_03.wav _cdt_stankick.wav -4.3,-4.3,-0,-4.3 4
    special_trim 144_Fight_Stage_5_Shredder.wav _cdt_shredder.wav 0.245 5.121

    special_mix_compand FreddyFreak_Grunts_01.wav 109_Head_Hit_01.wav _cdt_hit01.wav -6.3,-6.3,-0,-6.3 6
    special_mix_compand FreddyFreak_Grunts_02.wav 109_Head_Hit_01.wav _cdt_hit02.wav -6.3,-6.3,-0,-6.3 6
    special_mix_compand FreddyFreak_Grunts_03.wav 109_Head_Hit_01.wav _cdt_hit03.wav -6.3,-6.3,-0,-6.3 6
    special_mix_compand FreddyFreak_Grunts_04.wav 109_Head_Hit_01.wav _cdt_hit04.wav -6.3,-6.3,-0,-6.3 6
    special_mix_compand FreddyFreak_Grunts_05.wav 109_Head_Hit_01.wav _cdt_hit05.wav -6.3,-6.3,-0,-6.3 6
    special_mix_compand FreddyFreak_Grunts_06.wav 109_Head_Hit_01.wav _cdt_hit06.wav -6.3,-6.3,-0,-6.3 6
    special_mix_compand FreddyFreak_Grunts_07.wav 109_Head_Hit_01.wav _cdt_hit07.wav -6.3,-6.3,-0,-6.3 6
    special_mix_compand FreddyFreak_Grunts_08.wav 109_Head_Hit_01.wav _cdt_hit08.wav -6.3,-6.3,-0,-6.3 6
    special_mix_compand FreddyFreak_Grunts_09.wav 109_Head_Hit_01.wav _cdt_hit09.wav -6.3,-6.3,-0,-6.3 6
    special_mix_compand FreddyFreak_Grunts_10.wav 109_Head_Hit_01.wav _cdt_hit10.wav -6.3,-6.3,-0,-6.3 6

    special_mix_compand PHN_35_low-street_63_4.wav FRK_35_low-street_63_5.wav _cdt_jamrum.wav -4.3,-4.3,-0,-4.3 4
    require_file "$(sample_path FRK_35_low-street_63_3.wav)"
    require_file "$(sample_path PHN_35_low-street_63_2.wav)"
    verbose "sox delay FRK_35_low-street_63_3.wav -> temp.wav"
    sox "$(sample_path FRK_35_low-street_63_3.wav)" -t wav -V0 "$TEMP/temp.wav" delay 0.25
    sox "$TEMP/temp.wav" "$(sample_path PHN_35_low-street_63_2.wav)" -m -D -c 1 -t wav -V0 "$(sample_path _cdt_rumjam.wav)" compand 0.0,0.5 -4.3,-4.3,-0,-4.3 4 -99

    rm -f "$(sample_path TRL_57_bridge_16_2.wav)"
    mv "$(sample_path _cdt_eatya.wav)" "$(sample_path TRL_57_bridge_16_2.wav)"
    rm -f "$(sample_path GUY_20_main-beach_71_3.wav)"
    mv "$(sample_path _cdt_ht.wav)" "$(sample_path GUY_20_main-beach_71_3.wav)"

    if [ "$VERBOSE" -eq 0 ]; then
        rm -f "$TEMP/temp.wav"
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

write_sample_set() {
    find "$1" -type f -name "*.$2" -exec basename {} ".$2" \; | sort -u
}

check_monster_coverage() {
    refs_file="$OUT/monster-refs.txt"
    samples_file="$OUT/sample-names.txt"
    missing_file="$OUT/missing-monster-samples.txt"
    unreferenced_file="$OUT/unreferenced-samples.txt"

    monster_refs | sort -u > "$refs_file"
    write_sample_set "$FINAL" "$EXT" > "$samples_file"
    comm -23 "$refs_file" "$samples_file" > "$missing_file"
    comm -13 "$refs_file" "$samples_file" > "$unreferenced_file"

    MISSING_COUNT=$(wc -l < "$missing_file" | tr -d ' ')
    UNREFERENCED_COUNT=$(wc -l < "$unreferenced_file" | tr -d ' ')
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
SFX_WAV=
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
        --sfx-wav)
            [ "$#" -ge 2 ] || die "--sfx-wav requires a value"
            SFX_WAV=$2
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
[ -n "$SFX_WAV" ] || die "--sfx-wav is required"
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
require_dir "$SFX_WAV"
require_file "$SPEECH_WAV/STN_59_stans_89_1.wav"
require_file "$SFX_WAV/2_sound_SBL_door-open.wav"
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

log "MI1 voice processing"
log "speech wav: $SPEECH_WAV"
log "sfx wav:    $SFX_WAV"
log "out:        $OUT"
log "audio:      $AUDIO"

if [ "$DRY_RUN" -eq 1 ]; then
    log ""
    log "Planned voice steps:"
    log "1. Normalize Speech.xwb and SFXNew.xwb WAV files into samples-wav/."
    log "2. Copy _cdt_silence and create voice.bat special-case _cdt_*.wav files with SoX."
    log "3. Replace TRL_57_bridge_16_2.wav and GUY_20_main-beach_71_3.wav as voice.bat does."
    log "4. Convert samples to $AUDIO files in final-$AUDIO/."
    log "5. Stop before sbl.bat and cdaudio.bat."
    exit 0
fi

safe_clean_dir
mkdir -p "$SAMPLES" "$TEMP" "$FINAL"

normalize_wavs "$SFX_WAV" sfx
normalize_wavs "$SPEECH_WAV" speech
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
check_monster_coverage

log ""
log "Voice processing complete."
log "Normalized WAV files: $NORMALIZED_COUNT"
log "WAV files after special cases: $SAMPLE_COUNT"
log "Processed $AUDIO files: $PROCESSED_COUNT"
log "Expected unique monster.tbl references: $EXPECTED_COUNT"
log "Missing monster.tbl samples: $MISSING_COUNT"
log "Unreferenced processed samples: $UNREFERENCED_COUNT"
if [ "$MISSING_COUNT" -ne 0 ]; then
    log "warning: missing sample names written to $OUT/missing-monster-samples.txt"
fi
if [ "$UNREFERENCED_COUNT" -ne 0 ]; then
    log "warning: unreferenced sample names written to $OUT/unreferenced-samples.txt"
fi

probe_outputs

log "Processed files are in:"
log "  $FINAL"
