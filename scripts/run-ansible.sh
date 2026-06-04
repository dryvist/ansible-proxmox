#!/usr/bin/env bash
# Ansible runner - loads SSH key into ssh-agent (in-memory only), runs playbook.
# The key NEVER touches disk. Prefers PROXMOX_SSH_KEY_PATH (file path) when
# available; falls back to loading PROXMOX_SSH_PRIVATE_KEY into ssh-agent.
set -euo pipefail

usage() {
  echo "Usage: $0 <playbook> [ansible-playbook args...]"
  echo "Example: $0 playbooks/monitoring.yml --check"
  exit 1
}

[[ $# -lt 1 ]] && usage

PLAYBOOK="$1"
shift

AGENT_STARTED=false

cleanup() {
  if [[ $AGENT_STARTED == true ]]; then
    ssh-agent -k >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

# If key file exists at PROXMOX_SSH_KEY_PATH, export expanded path for inventory.
# Otherwise load key content into ssh-agent and unset PROXMOX_SSH_KEY_PATH so
# inventory/hosts.yml omits ansible_ssh_private_key_file (Ansible uses the agent).
if [[ -n ${PROXMOX_SSH_KEY_PATH:-} ]] && [[ -f ${PROXMOX_SSH_KEY_PATH/#\~/$HOME} ]]; then
  export PROXMOX_SSH_KEY_PATH="${PROXMOX_SSH_KEY_PATH/#\~/$HOME}"
elif [[ -n ${PROXMOX_SSH_PRIVATE_KEY:-} ]]; then
  eval "$(ssh-agent -s)" >/dev/null
  AGENT_STARTED=true
  if ! printf '%s\n' "$PROXMOX_SSH_PRIVATE_KEY" | ssh-add - >/dev/null; then
    echo "ERROR: Failed to load PROXMOX_SSH_PRIVATE_KEY into ssh-agent." >&2
    echo "Ensure the key is valid and not passphrase-protected." >&2
    exit 1
  fi
  unset PROXMOX_SSH_PRIVATE_KEY
  unset PROXMOX_SSH_KEY_PATH
else
  echo "ERROR: No SSH key available."
  echo "Set PROXMOX_SSH_KEY_PATH (file path) or PROXMOX_SSH_PRIVATE_KEY (key content) via Doppler."
  exit 1
fi

# Run ansible-playbook - prefer NIX_SHELL if set, otherwise use PATH
if [[ -n ${NIX_SHELL:-} ]]; then
  nix develop "$NIX_SHELL" --command ansible-playbook "$PLAYBOOK" "$@"
elif command -v ansible-playbook &>/dev/null; then
  ansible-playbook "$PLAYBOOK" "$@"
else
  echo "ERROR: ansible-playbook not found on PATH and NIX_SHELL not set"
  echo "Either activate direnv or set NIX_SHELL to your nix flake path"
  exit 1
fi
