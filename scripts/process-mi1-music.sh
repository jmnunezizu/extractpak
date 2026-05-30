#!/usr/bin/env sh
set -eu

usage() {
    cat <<'EOF'
Usage:
  scripts/process-mi1-music.sh --audio-dir /path/to/MonkeyIsland/audio \
    --out /path/to/output-folder \
    --work /path/to/.work/music \
    --audio ogg [--dry-run] [--verbose]

This ports tools/cdaudio.bat for the Ogg path. It decodes MusicOriginal.xwb,
MusicNew.xwb, and Ambience.xwb with vgmstream-cli, then applies the same SoX
trims/gains/mixes into cd_music_ogg/ and se_music_ogg/.
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

sox_can_write() {
    sox --help-format "$1" 2>/dev/null | grep -q 'Writes:'
}

AUDIO_DIR=
OUT=
WORK=
AUDIO=
DRY_RUN=0
VERBOSE=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --audio-dir)
            [ "$#" -ge 2 ] || die "--audio-dir requires a value"
            AUDIO_DIR=$2
            shift 2
            ;;
        --out)
            [ "$#" -ge 2 ] || die "--out requires a value"
            OUT=$2
            shift 2
            ;;
        --work)
            [ "$#" -ge 2 ] || die "--work requires a value"
            WORK=$2
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

[ -n "$AUDIO_DIR" ] || die "--audio-dir is required"
[ -n "$OUT" ] || die "--out is required"
[ -n "$WORK" ] || die "--work is required"
[ -n "$AUDIO" ] || die "--audio is required"

case "$AUDIO" in
    ogg) ;;
    *) die "MI1 music conversion currently supports --audio ogg only" ;;
esac

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
require_dir "$AUDIO_DIR"
require_file "$AUDIO_DIR/MusicOriginal.xwb"
require_file "$AUDIO_DIR/MusicNew.xwb"
require_file "$AUDIO_DIR/Ambience.xwb"
require_tool sox "install SoX to reproduce cdaudio.bat transforms"
require_tool vgmstream-cli "install vgmstream to decode XACT WMA music banks correctly"

if ! sox_can_write ogg; then
    die "this script currently requires SoX with Ogg/Vorbis write support"
fi

ORIGINAL="$WORK/original-wav"
NEW="$WORK/new-wav"
AMBIENCE="$WORK/ambience-wav"
CD_OUT="$OUT/cd_music_$AUDIO"
SE_OUT="$OUT/se_music_$AUDIO"

if [ "$DRY_RUN" -eq 1 ]; then
    log "Planned MI1 music conversion:"
    log "  extract MusicOriginal.xwb -> $ORIGINAL"
    log "  write classic CD tracks -> $CD_OUT"
    log "  extract MusicNew.xwb -> $NEW"
    log "  extract Ambience.xwb -> $AMBIENCE"
    log "  write Special Edition music/ambience tracks -> $SE_OUT"
    exit 0
fi

case "$WORK" in
    /|.) die "refusing to use unsafe work directory: $WORK" ;;
esac

rm -rf "$WORK"
mkdir -p "$ORIGINAL" "$NEW" "$AMBIENCE" "$CD_OUT" "$SE_OUT"

decode_bank() {
    bank=$1
    dst=$2
    label=$3
    verbose "decode $label $bank -> $dst"
    vgmstream-cli -i -S 0 -o "$dst/?n.wav" "$bank"
}

decode_bank "$AUDIO_DIR/MusicOriginal.xwb" "$ORIGINAL" "classic CD music"

cd_track() {
    src=$1
    dst=$2
    shift 2
    require_file "$ORIGINAL/$src"
    verbose "cd music $dst <- MusicOriginal.xwb/$src"
    sox "$ORIGINAL/$src" -V0 "$CD_OUT/$dst" "$@"
}

cd_track track2.wav track1.ogg trim 0.045 118.503
cd_track track3.wav track2.ogg trim 0.032 122.138
cd_track track4.wav track3.ogg trim 0.031 121.770
cd_track track5.wav track4.ogg trim 0.036 113.585
cd_track track6.wav track5.ogg trim 0.034 125.445
cd_track track7.wav track6.ogg trim 0.034 10.413
cd_track track8.wav track7.ogg trim 0.000 67.936
cd_track track9.wav track8.ogg trim 0.035 137.022
cd_track track10.wav track9.ogg trim 0.038 121.996
cd_track track12.wav track11.ogg trim 0.032 136.786
cd_track track13.wav track12.ogg trim 0.039 120.944
cd_track track14.wav track13.ogg trim 0.037 16.374
cd_track track15.wav track14.ogg trim 0.039 156.310
cd_track track16.wav track15.ogg trim 0.031 146.849
cd_track track17.wav track16.ogg trim 0.039 219.942
cd_track track18.wav track17.ogg trim 1.000 156.971 pad 3.000@95.270
cd_track track19.wav track18.ogg trim 0.035 155.867
cd_track track20.wav track19.ogg trim 0.035 16.295
cd_track track22.wav track21.ogg trim 0.032 132.555
cd_track track23.wav track22.ogg
cd_track track24.wav track23.ogg
cd_track track25.wav track24.ogg

decode_bank "$AUDIO_DIR/MusicNew.xwb" "$NEW" "Special Edition music"
decode_bank "$AUDIO_DIR/Ambience.xwb" "$AMBIENCE" "Special Edition ambience"

se_track() {
    src=$1
    dst=$2
    shift 2
    require_file "$NEW/$src"
    verbose "se music $dst <- MusicNew.xwb/$src"
    sox "$NEW/$src" -V0 "$SE_OUT/$dst" "$@"
}

se_ambience() {
    src=$1
    dst=$2
    shift 2
    require_file "$AMBIENCE/$src"
    verbose "se ambience $dst <- Ambience.xwb/$src"
    sox "$AMBIENCE/$src" -V0 "$SE_OUT/$dst" "$@"
}

se_track track2.wav track1.ogg gain -6
se_track track3.wav track2.ogg gain -6
se_track track4.wav track3.ogg gain -6
se_track track5.wav track4.ogg gain -6
se_track track6.wav track5.ogg gain -6
se_track track7.wav track6.ogg gain -6 trim 0.034 12.027
se_track track8.wav track7.ogg gain -6 trim 0.000 69.445
se_track track9.wav track8_no_sfx.ogg gain -6
sox "$AMBIENCE/AMB_ScummBar_01.wav" -V0 "$WORK/temp-scummbar.wav" trim 0.000 89.687
sox "$WORK/temp-scummbar.wav" "$NEW/track9.wav" -m -V0 "$WORK/track9o.wav"
sox "$WORK/track9o.wav" -V0 "$SE_OUT/track8.ogg"
se_track track10.wav track9.ogg gain -6
se_track track18c.wav track10.ogg gain -6
se_track track12.wav track11.ogg gain -6
se_track track13.wav track12.ogg gain -6
se_track track14.wav track13.ogg gain -6
se_track track15.wav track14.ogg gain -6
se_track track16.wav track15.ogg gain -6 trim 0.000 137.674
se_track track17.wav track16.ogg gain -6
se_track track18b.wav track17.ogg gain -4
se_track track19.wav track18.ogg gain -8
se_track track20.wav track19.ogg gain -6 trim 0.035 14.952
se_track track10a.wav track20.ogg gain -8
se_track track22.wav track21.ogg gain -6
require_file "$ORIGINAL/track23.wav"
require_file "$ORIGINAL/track24.wav"
require_file "$ORIGINAL/track25.wav"
sox "$ORIGINAL/track23.wav" -V0 "$SE_OUT/track22.ogg" compand 0.0,0.5 -5.3,-5.3,-0,-5.3 5 -99
sox "$ORIGINAL/track24.wav" -V0 "$SE_OUT/track23.ogg" compand 0.0,0.5 -5.3,-5.3,-0,-5.3 5 -99
sox "$ORIGINAL/track25.wav" -V0 "$SE_OUT/track24.ogg" compand 0.0,0.5 -5.3,-5.3,-0,-5.3 5 -99
se_ambience AMB_RiverJungle_01.wav track25.ogg gain -10
se_ambience AMB_TownNightClock_01.wav track26.ogg gain -10
se_ambience AMB_TownNight_01.wav track27.ogg gain -10
se_ambience AMB_Underwater_01.wav track28.ogg gain -10
se_ambience AMB_ShipDeck_01.wav track29.ogg gain -7

CD_COUNT=$(find "$CD_OUT" -type f -name '*.ogg' | wc -l | tr -d ' ')
SE_COUNT=$(find "$SE_OUT" -type f -name '*.ogg' | wc -l | tr -d ' ')

log "MI1 music conversion complete."
log "  classic CD music: $CD_COUNT files in $CD_OUT"
log "  Special Edition music: $SE_COUNT files in $SE_OUT"
