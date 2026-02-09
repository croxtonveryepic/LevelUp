#!/usr/bin/env bash
# LevelUp installer — global (uv tool) or dev (venv + editable).
#
# Usage:
#   ./install.sh              # Global install via uv tool
#   ./install.sh --dev        # Dev install (venv + editable + dev deps)
#   ./install.sh --gui        # Global install with GUI (PyQt6)
#   ./install.sh --dev --gui  # Dev install with GUI

set -euo pipefail

# ── Parse flags ──────────────────────────────────────────────────────────────
DEV=false
GUI=false
for arg in "$@"; do
    case "$arg" in
        --dev)  DEV=true ;;
        --gui)  GUI=true ;;
        *)      echo "Unknown option: $arg"; echo "Usage: $0 [--dev] [--gui]"; exit 1 ;;
    esac
done

# ── Helpers ──────────────────────────────────────────────────────────────────
info()  { echo -e "\033[1;34m==>\033[0m $*"; }
ok()    { echo -e "\033[1;32m==>\033[0m $*"; }
err()   { echo -e "\033[1;31mError:\033[0m $*" >&2; }

# ── Check Python 3.11+ ──────────────────────────────────────────────────────
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        ver=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || true)
        major=${ver%%.*}
        minor=${ver#*.}
        if [[ "$major" -ge 3 && "$minor" -ge 11 ]]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    err "Python 3.11+ is required but not found."
    echo "Install Python from https://www.python.org/downloads/"
    exit 1
fi
info "Using Python: $PYTHON ($($PYTHON --version))"

# ── Check uv ─────────────────────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
    err "uv is required but not found."
    echo "Install uv: https://docs.astral.sh/uv/getting-started/installation/"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
info "Using uv: $(uv --version)"

# ── Resolve source directory (where this script lives) ───────────────────────
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LEVELUP_DIR="$HOME/.levelup"
META_FILE="$LEVELUP_DIR/install.json"

mkdir -p "$LEVELUP_DIR"

# ── Detect git remote URL ───────────────────────────────────────────────────
REPO_URL=""
if git -C "$SOURCE_DIR" remote get-url origin &>/dev/null; then
    REPO_URL="$(git -C "$SOURCE_DIR" remote get-url origin)"
fi

# ── Install ──────────────────────────────────────────────────────────────────
if [[ "$DEV" == true ]]; then
    info "Installing in dev mode (venv + editable)..."

    # Create venv if needed
    if [[ ! -d "$SOURCE_DIR/.venv" ]]; then
        info "Creating virtual environment..."
        uv venv "$SOURCE_DIR/.venv"
    fi

    # Determine venv python path
    if [[ -f "$SOURCE_DIR/.venv/bin/python" ]]; then
        VENV_PYTHON="$SOURCE_DIR/.venv/bin/python"
    elif [[ -f "$SOURCE_DIR/.venv/Scripts/python.exe" ]]; then
        VENV_PYTHON="$SOURCE_DIR/.venv/Scripts/python.exe"
    else
        err "Could not find Python in .venv"
        exit 1
    fi

    # Build extras string
    if [[ "$GUI" == true ]]; then
        EXTRAS=".[dev,gui]"
    else
        EXTRAS=".[dev]"
    fi

    info "Installing: uv pip install -e \"$EXTRAS\" ..."
    uv pip install -e "$EXTRAS" --python "$VENV_PYTHON"

    # Write install metadata (build JSON manually to include optional fields)
    _meta="{\"method\":\"editable\",\"source_path\":\"$SOURCE_DIR\""
    if [[ "$GUI" == true ]]; then _meta="$_meta,\"extras\":[\"gui\"]"; fi
    if [[ -n "$REPO_URL" ]]; then _meta="$_meta,\"repo_url\":\"$REPO_URL\""; fi
    _meta="$_meta}"
    echo "$_meta" > "$META_FILE"

    ok "Dev install complete!"
    echo ""
    echo "Activate the virtual environment:"
    if [[ -f "$SOURCE_DIR/.venv/bin/activate" ]]; then
        echo "  source $SOURCE_DIR/.venv/bin/activate"
    else
        echo "  $SOURCE_DIR/.venv/Scripts/activate"
    fi
    echo ""
    echo "Then run:"
    echo "  levelup --version"

else
    info "Installing globally via uv tool..."

    # Build extras string
    if [[ "$GUI" == true ]]; then
        INSTALL_TARGET="$SOURCE_DIR[gui]"
    else
        INSTALL_TARGET="$SOURCE_DIR"
    fi

    uv tool install --force "$INSTALL_TARGET" --python "$PYTHON"

    # Write install metadata (build JSON manually to include optional fields)
    _meta="{\"method\":\"global\",\"source_path\":\"$SOURCE_DIR\""
    if [[ "$GUI" == true ]]; then _meta="$_meta,\"extras\":[\"gui\"]"; fi
    if [[ -n "$REPO_URL" ]]; then _meta="$_meta,\"repo_url\":\"$REPO_URL\""; fi
    _meta="$_meta}"
    echo "$_meta" > "$META_FILE"

    ok "Global install complete!"
    echo ""
    echo "Run from anywhere:"
    echo "  levelup --version"
fi
