#!/bin/sh
set -eu

DRY_RUN=0
if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=1
    shift
fi

VERSION=${1:-}
if [ -z "$VERSION" ]; then
    printf 'usage: %s [--dry-run] vX.Y.Z\n' "$0" >&2
    exit 2
fi

case "$VERSION" in
    v[0-9]*.[0-9]*.[0-9]*) ;;
    *)
        printf 'error: version must look like vX.Y.Z, got %s\n' "$VERSION" >&2
        exit 2
        ;;
esac

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PACKAGE_VERSION=${VERSION#v}

info() {
    printf '%s\n' "$*"
}

fail() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

run() {
    if [ "$DRY_RUN" = "1" ]; then
        printf '+ %s\n' "$*"
    else
        "$@"
    fi
}

require_tool() {
    command -v "$1" >/dev/null 2>&1 || fail "missing required tool '$1'"
}

require_tool git
require_tool gh
require_tool python3
require_tool sh

cd "$ROOT"

branch=$(git branch --show-current)
if [ "$branch" != "main" ] && [ "$DRY_RUN" != "1" ]; then
    fail "releases must be created from main; current branch is $branch"
fi

if [ -n "$(git status --short)" ] && [ "$DRY_RUN" != "1" ]; then
    fail "working tree is dirty; commit or stash changes before releasing"
fi

if git rev-parse "$VERSION" >/dev/null 2>&1 && [ "$DRY_RUN" != "1" ]; then
    fail "tag already exists locally: $VERSION"
fi

if git ls-remote --exit-code --tags origin "refs/tags/$VERSION" >/dev/null 2>&1 && [ "$DRY_RUN" != "1" ]; then
    fail "tag already exists on origin: $VERSION"
fi

pyproject_version=$(python3 - <<'PY'
from pathlib import Path

for line in Path("pyproject.toml").read_text().splitlines():
    line = line.strip()
    if line.startswith("version = "):
        print(line.split("=", 1)[1].strip().strip('"'))
        break
else:
    raise SystemExit("missing project version")
PY
)

module_version=$(python3 - <<'PY'
from scummkit import __version__

print(__version__)
PY
)

if [ "$pyproject_version" != "$PACKAGE_VERSION" ]; then
    fail "pyproject.toml version is $pyproject_version, expected $PACKAGE_VERSION"
fi

if [ "$module_version" != "$PACKAGE_VERSION" ]; then
    fail "scummkit.__version__ is $module_version, expected $PACKAGE_VERSION"
fi

info "Running release validation"
run sh -n install.sh
run sh -n scripts/test-install.sh
run env PYTHONPYCACHEPREFIX=/tmp/scummkit-release-pycache python3 -m py_compile scummkit/*.py scummkit/commands/*.py scummkit/builders/*.py
run python3 -m pytest
run scripts/test-install.sh

notes_file=$(mktemp "${TMPDIR:-/tmp}/scummkit-release-notes.XXXXXX.md")
trap 'rm -f "$notes_file"' EXIT INT TERM

cat >"$notes_file" <<EOF
## Highlights

- Adds a user-local installer script and installer smoke test.
- Installs SCUMMKit into ~/.local/share/scummkit with a ~/.local/bin/scummkit wrapper.
- Compiles extractpak during install and verifies the install with scummkit doctor.
- Adds scummkit --version.

## Install

\`\`\`bash
curl -fsSL https://github.com/jmnunezizu/scummkit/releases/latest/download/install.sh | sh
\`\`\`

## Validation

- sh -n install.sh
- sh -n scripts/test-install.sh
- Python compile check
- pytest
- scripts/test-install.sh

## Notes

- The installer does not install system dependencies such as sox, ffmpeg, bspatch, vgmstream-cli, Python, or a C compiler.
- Generated game outputs still depend on locally owned game assets and are not redistributable.
EOF

info "Creating $VERSION release"
run git tag "$VERSION"
run git push origin "$VERSION"
run gh release create "$VERSION" --title "SCUMMKit $VERSION" --notes-file "$notes_file" install.sh

info "Release $VERSION complete"
