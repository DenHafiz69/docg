#!/usr/bin/env bash
set -euo pipefail

DOCG_REPO="${DOCG_REPO:-https://github.com/DenHafiz69/docg.git}"
DOCG_REF="${DOCG_REF:-main}"
DEFAULT_INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/docg"

info()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33mwarning:\033[0m %s\n' "$*" >&2; }
error() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || error "Required command '$1' is not installed."
}

ensure_uv() {
    if command -v uv >/dev/null 2>&1; then
        return 0
    fi

    info "Installing uv..."
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        error "Neither 'curl' nor 'wget' is available to install uv."
    fi

    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    command -v uv >/dev/null 2>&1 || error "uv installation succeeded, but 'uv' was not found on PATH."
}

resolve_install_dir() {
    if [ -n "${DOCG_DIR:-}" ]; then
        printf '%s' "$DOCG_DIR"
        return 0
    fi

    # If executed directly from a local checkout (e.g. ./install.sh), use it in-place.
    if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
        local script_dir
        script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        if [ -f "$script_dir/pyproject.toml" ] && [ -d "$script_dir/src/docg" ]; then
            printf '%s' "$script_dir"
            return 0
        fi
    fi

    printf '%s' "$DEFAULT_INSTALL_DIR"
}

main() {
    ensure_uv

    local install_dir
    install_dir="$(resolve_install_dir)"

    if [ -f "$install_dir/pyproject.toml" ] && [ -d "$install_dir/src/docg" ]; then
        if [ -d "$install_dir/.git" ] && { [ -z "${BASH_SOURCE[0]:-}" ] || [ ! -f "${BASH_SOURCE[0]:-}" ]; }; then
            need_cmd git
            info "Updating existing docg checkout in $install_dir..."
            git -C "$install_dir" pull --ff-only
        else
            info "Using existing local checkout at $install_dir"
        fi
    else
        need_cmd git
        info "Cloning docg ($DOCG_REF) into $install_dir..."
        mkdir -p "$(dirname "$install_dir")"
        git clone --branch "$DOCG_REF" "$DOCG_REPO" "$install_dir"
    fi

    info "Installing docg CLI via uv tool..."
    uv tool install --force -e "$install_dir"

    export PATH="$HOME/.local/bin:$PATH"
    if command -v docg >/dev/null 2>&1; then
        info "docg installed successfully: $(command -v docg)"
    else
        warn "docg was installed, but '$HOME/.local/bin' is not in your PATH."
        warn "Add this to your shell profile: export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi

    printf '\n'
    info "Workspace directory: $install_dir"
    info "Run 'docg --help' to get started, or set DOCG_HOME to use a custom config/data folder."
}

main "$@"
