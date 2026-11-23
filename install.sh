#!/usr/bin/env bash
set -euo pipefail

DOCG_REPO="${DOCG_REPO:-https://github.com/DenHafiz69/docg.git}"
DOCG_REF="${DOCG_REF:-main}"

info()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33mwarning:\033[0m %s\n' "$*" >&2; }
error() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

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

detect_local_checkout() {
    if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
        local script_dir
        script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        if [ -f "$script_dir/pyproject.toml" ] && [ -d "$script_dir/src/docg" ]; then
            printf '%s' "$script_dir"
            return 0
        fi
    fi
    return 1
}

main() {
    ensure_uv

    local local_dir
    if local_dir="$(detect_local_checkout)"; then
        info "Installing docg (editable) from $local_dir..."
        uv tool install --force -e "$local_dir"
    else
        info "Installing docg from $DOCG_REPO ($DOCG_REF)..."
        uv tool install --force "git+${DOCG_REPO}@${DOCG_REF}"
    fi

    export PATH="$HOME/.local/bin:$PATH"
    if command -v docg >/dev/null 2>&1; then
        info "docg installed: $(command -v docg)"
        info "Initializing global config and data directories..."
        docg init
    else
        warn "docg was installed, but '$HOME/.local/bin' is not in your PATH."
        warn "Add this to your shell profile: export PATH=\"\$HOME/.local/bin:\$PATH\""
        warn "Then run 'docg init' to create starter configs in ~/.config/docg/."
    fi

    printf '\n'
    info "Run 'docg --help' or 'docg paths' to get started."
}

main "$@"
