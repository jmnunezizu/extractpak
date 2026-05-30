#!/usr/bin/env sh
set -eu

usage() {
    cat <<'EOF'
Usage:
  scripts/process-mi1-sbl.sh --builder /path/to/MI1_Ultimate_Talkie_Edition_Builder \
    --samples-wav /path/to/.work/processed-voice/samples-wav \
    --monkey000 /path/to/monkey.000 \
    --monkey001 /path/to/monkey.001 \
    --work /path/to/.work/sbl [--dry-run] [--verbose]

Runs the native MI1 sbl.bat replacement:
  - parses tools/sbl.bat
  - runs the same SoX trim/downsample commands
  - converts each temporary WAV with scripts/wav2sbl.py-compatible logic
  - injects SBL chunks into monkey.001 and updates monkey.000 sound offsets
EOF
}

die() {
    printf 'error: %s\n' "$*" >&2
    exit 1
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

BUILDER=
SAMPLES_WAV=
MONKEY000=
MONKEY001=
WORK=
DRY_RUN=0
VERBOSE=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --builder)
            [ "$#" -ge 2 ] || die "--builder requires a value"
            BUILDER=$2
            shift 2
            ;;
        --samples-wav)
            [ "$#" -ge 2 ] || die "--samples-wav requires a value"
            SAMPLES_WAV=$2
            shift 2
            ;;
        --monkey000)
            [ "$#" -ge 2 ] || die "--monkey000 requires a value"
            MONKEY000=$2
            shift 2
            ;;
        --monkey001)
            [ "$#" -ge 2 ] || die "--monkey001 requires a value"
            MONKEY001=$2
            shift 2
            ;;
        --work)
            [ "$#" -ge 2 ] || die "--work requires a value"
            WORK=$2
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
[ -n "$SAMPLES_WAV" ] || die "--samples-wav is required"
[ -n "$MONKEY000" ] || die "--monkey000 is required"
[ -n "$MONKEY001" ] || die "--monkey001 is required"
[ -n "$WORK" ] || die "--work is required"

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
INJECT_SBL=${INJECT_SBL:-"$SCRIPT_DIR/inject-mi1-sbl.py"}

require_dir "$BUILDER"
require_dir "$BUILDER/tools"
require_file "$BUILDER/tools/sbl.bat"
require_dir "$SAMPLES_WAV"
require_file "$INJECT_SBL"
require_tool sox "install SoX; it is required for sbl.bat sound-effect conversion"

if [ "$DRY_RUN" -eq 0 ]; then
    require_file "$MONKEY000"
    require_file "$MONKEY001"
fi

set -- "$INJECT_SBL" \
    --builder "$BUILDER" \
    --samples-wav "$SAMPLES_WAV" \
    --monkey000 "$MONKEY000" \
    --monkey001 "$MONKEY001" \
    --work "$WORK"

if [ "$DRY_RUN" -eq 1 ]; then
    set -- "$@" --dry-run
fi
if [ "$VERBOSE" -eq 1 ]; then
    set -- "$@" --verbose
fi

"$@"
