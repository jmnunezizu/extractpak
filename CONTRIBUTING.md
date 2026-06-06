# Contributing

SCUMMKit builds local ScummVM-compatible Monkey Island Ultimate Talkie Edition
folders from assets users already own. Keep changes focused, reproducible, and
clear about what is generated locally.

## Development Setup

Install runtime tools first:

```bash
brew install python sox ffmpeg vgmstream bsdiff
```

On Debian/Ubuntu:

```bash
sudo apt install python3 python3-venv python3-pytest sox ffmpeg bsdiff clang
```

Install `vgmstream-cli` separately if your package manager does not provide it.

Compile the local PAK extractor from a checkout:

```bash
clang extractpak.c -o extractpak
```

Run the CLI from a checkout with:

```bash
python3 -m scummkit --version
python3 -m scummkit doctor
```

## Validation

Run the lightweight checks before opening a PR:

```bash
sh -n install.sh
sh -n scripts/test-install.sh
sh -n scripts/release.sh
PYTHONPYCACHEPREFIX=/tmp/scummkit-pycache python3 -m py_compile scummkit/*.py scummkit/commands/*.py scummkit/builders/*.py
python3 -m pytest
```

Smoke-test the installer against a temporary local archive:

```bash
scripts/test-install.sh
```

Keep the temporary install for inspection with:

```bash
SCUMMKIT_TEST_INSTALL_KEEP=1 scripts/test-install.sh
```

## Branches and Commits

- Create feature branches from `main`.
- Use focused branch names such as `feature/8-installer-distribution`.
- Keep commits scoped to one behavior or documentation change.
- Use conventional commit messages so release-please can classify changes:
  - `feat: add MI1 install smoke test`
  - `fix: report missing extractpak as actionable error`
  - `docs: clarify installer options`
  - `test: cover release script syntax`
- Use `feat!:` or a `BREAKING CHANGE:` footer only for breaking changes.
- Do not commit local game assets, generated game output, or files extracted
  from personally owned game installations.

## Installer Changes

The installer is intentionally user-local and non-sudo by default:

```text
~/.local/share/scummkit
~/.local/bin/scummkit
```

It installs SCUMMKit itself, creates a private virtual environment, compiles
`extractpak`, and runs `scummkit doctor`. It does not install system
dependencies such as `sox`, `ffmpeg`, `bspatch`, `vgmstream-cli`, Python, or a
C compiler.

If you change installer behavior, update:

- `install.sh`
- `scripts/test-install.sh`
- `tests/test_install_script.py`
- README install/uninstall notes

## Releases

Release PRs are maintained by release-please from conventional commits merged
to `main`. The release-please workflow updates:

- `CHANGELOG.md`
- `pyproject.toml`
- `scummkit/__init__.py`
- `.release-please-manifest.json`

When the release PR is merged, release-please creates the GitHub release. The
workflow then uploads `install.sh` as a release asset so the public install
command works:

```bash
curl -fsSL https://github.com/jmnunezizu/scummkit/releases/latest/download/install.sh | sh
```

The manual release script remains available as a fallback from a clean `main`
checkout:

```bash
scripts/release.sh --dry-run v0.3.0
scripts/release.sh v0.3.0
```

Use the manual script only when release-please is not suitable for a given
release. It validates versions, runs checks, smoke-tests the installer, creates
and pushes the tag, creates the GitHub release, and uploads `install.sh`.

## Legal and Asset Handling

- Do not commit copyrighted game assets.
- Do not commit generated ScummVM output folders.
- Treat files under local `~/Downloads/MonkeyIsland*` paths as inputs only.
- Keep third-party Ultimate Talkie patch/table attribution intact.
- Preserve license and notice updates when changing bundled third-party data.
