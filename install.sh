#!/bin/sh
set -eu

DRY_RUN=0

usage() {
    cat <<'EOF'
Usage: install.sh [--dry-run] [--help]

Installs SCUMMKit from a tagged GitHub release into user-local paths.

Environment:
  SCUMMKIT_VERSION       Release tag to install. Default: latest
  SCUMMKIT_HOME          Install directory. Default: ~/.local/share/scummkit
  SCUMMKIT_BIN_DIR       Wrapper directory. Default: ~/.local/bin
  SCUMMKIT_ARCHIVE_URL   Override release archive URL, mainly for tests
  SCUMMKIT_REPO_OWNER    GitHub owner. Default: jmnunezizu
  SCUMMKIT_REPO_NAME     GitHub repo. Default: scummkit
  SCUMMKIT_NO_PATH_UPDATE
                          Set to 1 to skip shell profile updates
  PYTHON                 Python executable. Default: python3
  CC                     C compiler. Default: first of clang, cc, gcc

The installer does not install system dependencies such as sox, ffmpeg,
bspatch, vgmstream-cli, Python, or a C compiler. It runs scummkit doctor after
installation so missing runtime tools are reported clearly.
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'error: unknown option: %s\n' "$1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

REPO_OWNER=${SCUMMKIT_REPO_OWNER:-jmnunezizu}
REPO_NAME=${SCUMMKIT_REPO_NAME:-scummkit}
VERSION=${SCUMMKIT_VERSION:-latest}
INSTALL_DIR=${SCUMMKIT_HOME:-"$HOME/.local/share/scummkit"}
BIN_DIR=${SCUMMKIT_BIN_DIR:-"$HOME/.local/bin"}
PYTHON=${PYTHON:-python3}

tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/scummkit-install.XXXXXX")

cleanup() {
    rm -rf "$tmp_dir"
}
trap cleanup EXIT INT TERM

info() {
    printf '%s\n' "$*"
}

fail() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

need_tool() {
    if ! command -v "$1" >/dev/null 2>&1; then
        fail "missing required tool '$1'"
    fi
}

find_compiler() {
    if [ -n "${CC:-}" ]; then
        printf '%s\n' "$CC"
        return
    fi
    for candidate in clang cc gcc; do
        if command -v "$candidate" >/dev/null 2>&1; then
            printf '%s\n' "$candidate"
            return
        fi
    done
    fail "missing C compiler; install clang, cc, or gcc"
}

profile_path() {
    shell_name=$(basename "${SHELL:-}")
    case "$shell_name" in
        zsh) printf '%s\n' "$HOME/.zshrc" ;;
        bash)
            if [ -f "$HOME/.bash_profile" ]; then
                printf '%s\n' "$HOME/.bash_profile"
            else
                printf '%s\n' "$HOME/.bashrc"
            fi
            ;;
        fish) printf '%s\n' "" ;;
        *) printf '%s\n' "$HOME/.profile" ;;
    esac
}

ensure_bin_on_path() {
    case ":$PATH:" in
        *":$BIN_DIR:"*)
            return
            ;;
    esac

    profile=$(profile_path)
    info ""
    info "Add this directory to PATH for the current shell:"
    info "  export PATH=\"$BIN_DIR:\$PATH\""

    if [ "${SCUMMKIT_NO_PATH_UPDATE:-}" = "1" ]; then
        info ""
        info "Skipping shell profile update because SCUMMKIT_NO_PATH_UPDATE=1."
        return
    fi

    if [ -z "$profile" ]; then
        info ""
        info "Automatic PATH setup is not supported for your shell."
        return
    fi

    mkdir -p "$(dirname "$profile")"
    touch "$profile"
    if grep -F "SCUMMKit installer" "$profile" >/dev/null 2>&1; then
        info ""
        info "PATH setup already exists in $profile."
        return
    fi

    {
        printf '\n'
        printf '# SCUMMKit installer\n'
        printf 'export PATH="%s:$PATH"\n' "$BIN_DIR"
    } >>"$profile"

    info ""
    info "Added SCUMMKit to PATH for future shells in:"
    info "  $profile"
    info "Open a new shell, or run the export command above now."
}

resolve_latest_version() {
    latest_url=$(curl -fsSLI -o /dev/null -w '%{url_effective}' "https://github.com/$REPO_OWNER/$REPO_NAME/releases/latest")
    case "$latest_url" in
        */releases/tag/*) printf '%s\n' "${latest_url##*/releases/tag/}" ;;
        *) fail "could not resolve latest release from $latest_url" ;;
    esac
}

need_tool curl
need_tool tar
need_tool "$PYTHON"

if [ "$VERSION" = "latest" ] && [ -z "${SCUMMKIT_ARCHIVE_URL:-}" ]; then
    VERSION=$(resolve_latest_version)
fi

compiler=$(find_compiler)
archive_url=${SCUMMKIT_ARCHIVE_URL:-"https://github.com/$REPO_OWNER/$REPO_NAME/archive/refs/tags/$VERSION.tar.gz"}
archive="$tmp_dir/scummkit.tar.gz"
source_dir="$tmp_dir/source"
staging_dir="$tmp_dir/staging"

if [ "$DRY_RUN" = "1" ]; then
    info "SCUMMKit install plan:"
    info "  version:      $VERSION"
    info "  source:       $archive_url"
    info "  install dir:  $INSTALL_DIR"
    info "  command:      $BIN_DIR/scummkit"
    info "  python:       $PYTHON"
    info "  compiler:     $compiler"
    info ""
    info "No files were changed."
    exit 0
fi

info "Installing SCUMMKit $VERSION"
info "  source: $archive_url"
info "  target: $INSTALL_DIR"

curl -fsSL "$archive_url" -o "$archive"
mkdir -p "$source_dir" "$staging_dir" "$BIN_DIR"
tar -xzf "$archive" -C "$source_dir"

if [ -f "$source_dir/extractpak.c" ]; then
    archive_root="$source_dir"
else
    archive_root=$(find "$source_dir" -mindepth 1 -maxdepth 1 -type d | head -n 1)
    if [ -z "$archive_root" ] || [ ! -f "$archive_root/extractpak.c" ]; then
        fail "archive does not look like a SCUMMKit release: missing extractpak.c"
    fi
fi

cp -R "$archive_root"/. "$staging_dir"/

info "Creating Python virtual environment"
"$PYTHON" -m venv "$staging_dir/.venv"

info "Compiling extractpak with $compiler"
"$compiler" "$staging_dir/extractpak.c" -o "$staging_dir/extractpak"
chmod +x "$staging_dir/extractpak"

wrapper="$tmp_dir/scummkit"
cat >"$wrapper" <<EOF
#!/bin/sh
cd "$INSTALL_DIR" || exit 1
export PYTHONPATH="$INSTALL_DIR\${PYTHONPATH:+:\$PYTHONPATH}"
exec "$INSTALL_DIR/.venv/bin/python" -m scummkit "\$@"
EOF
chmod +x "$wrapper"

backup_dir="$INSTALL_DIR.previous"
rm -rf "$backup_dir"
if [ -d "$INSTALL_DIR" ]; then
    mv "$INSTALL_DIR" "$backup_dir"
fi
mkdir -p "$(dirname "$INSTALL_DIR")"
mv "$staging_dir" "$INSTALL_DIR"
mv "$wrapper" "$BIN_DIR/scummkit"

info "Installed scummkit command at $BIN_DIR/scummkit"
ensure_bin_on_path

info ""
info "Running scummkit doctor"
if "$BIN_DIR/scummkit" doctor; then
    info ""
    info "SCUMMKit $VERSION installed successfully."
else
    info ""
    info "SCUMMKit was installed, but doctor reported missing runtime tools."
    info "Install the reported tools, then run:"
    info "  scummkit doctor"
fi
