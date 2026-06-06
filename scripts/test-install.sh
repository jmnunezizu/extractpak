#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION=${SCUMMKIT_VERSION:-v0.3.0}
KEEP=${SCUMMKIT_TEST_INSTALL_KEEP:-0}
TMP_DIR=${SCUMMKIT_TEST_INSTALL_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/scummkit-install-test.XXXXXX")}

cleanup() {
    if [ "$KEEP" != "1" ] && [ -z "${SCUMMKIT_TEST_INSTALL_DIR:-}" ]; then
        rm -rf "$TMP_DIR"
    fi
}
trap cleanup EXIT INT TERM

info() {
    printf '%s\n' "$*"
}

archive="$TMP_DIR/scummkit.tar.gz"
home_dir="$TMP_DIR/home"
bin_dir="$TMP_DIR/bin"

mkdir -p "$TMP_DIR"

info "Creating local install archive"
tar -czf "$archive" -C "$ROOT" \
    README.md \
    pyproject.toml \
    install.sh \
    extractpak.c \
    scummkit \
    third_party \
    licenses \
    LICENSE \
    NOTICE \
    images

info "Running installer into $TMP_DIR"
SCUMMKIT_ARCHIVE_URL="file://$archive" \
SCUMMKIT_HOME="$home_dir" \
SCUMMKIT_BIN_DIR="$bin_dir" \
SCUMMKIT_VERSION="$VERSION" \
"$ROOT/install.sh"

info ""
info "Verifying installed command from /tmp"
(
    cd /tmp
    "$bin_dir/scummkit" --version
    "$bin_dir/scummkit" doctor
)

info ""
info "Install smoke test passed."
if [ "$KEEP" = "1" ] || [ -n "${SCUMMKIT_TEST_INSTALL_DIR:-}" ]; then
    info "Test install kept at: $TMP_DIR"
fi
