#!/usr/bin/env bash
# OpenSprite uninstaller for installs created by scripts/install.sh.
#
# Safe default: remove the command and code checkout, but keep ~/.opensprite.
# Use --full to also delete runtime config, data, sessions, and logs.

set -euo pipefail

INSTALL_DIR="${OPENSPRITE_INSTALL_DIR:-$HOME/.local/share/opensprite/opensprite}"
APP_HOME="${OPENSPRITE_HOME:-$HOME/.opensprite}"
LINK_PATH="$HOME/.local/bin/opensprite"
FULL_UNINSTALL=0
ASSUME_YES=0

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { printf "%b==>%b %s\n" "$CYAN" "$NC" "$1"; }
log_success() { printf "%bOK%b %s\n" "$GREEN" "$NC" "$1"; }
log_warn() { printf "%b!%b %s\n" "$YELLOW" "$NC" "$1"; }
log_error() { printf "%bError:%b %s\n" "$RED" "$NC" "$1" >&2; }

usage() {
  cat <<'EOF'
OpenSprite uninstaller

Usage: uninstall.sh [options]

Options:
  --dir PATH       Installed repository checkout. Default: ~/.local/share/opensprite/opensprite
  --home PATH      Runtime data directory. Default: ~/.opensprite
  --full           Also remove runtime config, sessions, logs, and data.
  -y, --yes        Skip confirmation prompts.
  -h, --help       Show this help.

Environment overrides:
  OPENSPRITE_INSTALL_DIR
  OPENSPRITE_HOME
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir)
      INSTALL_DIR="$2"
      shift 2
      ;;
    --home)
      APP_HOME="$2"
      shift 2
      ;;
    --full)
      FULL_UNINSTALL=1
      shift
      ;;
    -y|--yes)
      ASSUME_YES=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      log_error "Unknown option: $1"
      usage >&2
      exit 2
      ;;
  esac
done

confirm_uninstall() {
  if [[ "$ASSUME_YES" -eq 1 ]]; then
    return 0
  fi

  echo "OpenSprite uninstall will remove:"
  echo "  Command: $LINK_PATH"
  echo "  Code:    $INSTALL_DIR"
  if [[ "$FULL_UNINSTALL" -eq 1 ]]; then
    echo "  Data:    $APP_HOME"
    echo
    log_warn "Full uninstall deletes configs, sessions, memories, logs, and local databases."
  else
    echo "  Data:    kept at $APP_HOME"
  fi
  echo

  local answer
  read -r -p "Type 'yes' to continue: " answer || answer=""
  if [[ "$answer" != "yes" ]]; then
    echo "Uninstall cancelled."
    exit 0
  fi
}

validate_paths() {
  case "$INSTALL_DIR" in
    ""|"/"|"."|"$HOME"|"$HOME/" )
      log_error "Refusing to remove unsafe install directory: $INSTALL_DIR"
      exit 1
      ;;
  esac
  case "$APP_HOME" in
    ""|"/"|"."|"$HOME"|"$HOME/" )
      log_error "Refusing to remove unsafe runtime data directory: $APP_HOME"
      exit 1
      ;;
  esac
}

opensprite_cmd() {
  if [[ -x "$INSTALL_DIR/.venv/bin/opensprite" ]]; then
    printf '%s' "$INSTALL_DIR/.venv/bin/opensprite"
    return 0
  fi
  if command -v opensprite >/dev/null 2>&1; then
    command -v opensprite
    return 0
  fi
  return 1
}

stop_gateway() {
  local cmd
  if cmd="$(opensprite_cmd)"; then
    log_info "Stopping OpenSprite gateway"
    "$cmd" service stop >/dev/null 2>&1 || true
    "$cmd" service uninstall >/dev/null 2>&1 || true
    return 0
  fi

  if command -v systemctl >/dev/null 2>&1; then
    systemctl --user stop opensprite-gateway.service >/dev/null 2>&1 || true
    systemctl --user disable opensprite-gateway.service >/dev/null 2>&1 || true
    rm -f "$HOME/.config/systemd/user/opensprite-gateway.service"
    systemctl --user daemon-reload >/dev/null 2>&1 || true
  fi

  if [[ -f "$APP_HOME/gateway.pid" ]]; then
    local pid
    pid="$(cat "$APP_HOME/gateway.pid" 2>/dev/null || true)"
    if [[ "$pid" =~ ^[0-9]+$ ]]; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
    rm -f "$APP_HOME/gateway.pid"
  fi
}

remove_command_link() {
  if [[ -L "$LINK_PATH" ]]; then
    local target
    target="$(readlink "$LINK_PATH")"
    if [[ "$target" == "$INSTALL_DIR/.venv/bin/opensprite" ]]; then
      rm -f "$LINK_PATH"
      log_success "Removed $LINK_PATH"
    else
      log_warn "Not removing $LINK_PATH because it points to $target"
    fi
  elif [[ -e "$LINK_PATH" ]]; then
    log_warn "Not removing $LINK_PATH because it is not a symlink"
  fi
}

remove_install_dir() {
  if [[ -d "$INSTALL_DIR" ]]; then
    rm -rf "$INSTALL_DIR"
    log_success "Removed $INSTALL_DIR"
  else
    log_info "Code directory not found: $INSTALL_DIR"
  fi
}

remove_app_home() {
  if [[ "$FULL_UNINSTALL" -ne 1 ]]; then
    log_info "Keeping runtime data in $APP_HOME"
    return 0
  fi
  if [[ -d "$APP_HOME" ]]; then
    rm -rf "$APP_HOME"
    log_success "Removed $APP_HOME"
  else
    log_info "Runtime data directory not found: $APP_HOME"
  fi
}

main() {
  validate_paths
  confirm_uninstall
  stop_gateway
  remove_command_link
  remove_install_dir
  remove_app_home
  log_success "OpenSprite uninstall complete"
}

main
