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
CERT_DIR=""
RUNNER_BAO_TOKEN=""

revoke_runner_token() {
  [[ -z $RUNNER_BAO_TOKEN ]] && return 0
  { set +x; } 2>/dev/null
  if curl -fsSL --max-time 10 -X POST \
    -H @<(printf 'X-Vault-Token: %s\n' "$RUNNER_BAO_TOKEN") \
    "$BAO_ADDR/v1/auth/token/revoke-self" >/dev/null 2>&1; then
    RUNNER_BAO_TOKEN=""
    return 0
  fi
  return 1
}

cleanup() {
  local status=$?
  revoke_runner_token || true
  if [[ $AGENT_STARTED == true ]]; then
    ssh-agent -k >/dev/null 2>&1 || true
  fi
  [[ -n $CERT_DIR ]] && rm -rf "$CERT_DIR"
  return "$status"
}
trap cleanup EXIT

# --- Preferred auth: short-lived SSH certificate from the OpenBao CA --------
# ssh-certificate-authority ADR: mint an ephemeral ed25519 keypair, sign it via
# ssh-client-ca/sign/automation-{semaphore,ansible} (principal `semaphore` or
# the shared `ansible`, cert TTL <=1h), and point the inventory at the key
# (OpenSSH pairs id + id-cert.pub automatically). Requires BAO_ADDR + one of
# the AppRole pairs in the ambient env (Doppler). With that env present, a
# mint failure is fatal.
mint_ssh_cert() {
  local mount=${SSH_CA_MOUNT:-ssh-client-ca} login token signed
  CERT_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ansible-sshcert.XXXXXX") || return 1
  chmod 700 "$CERT_DIR"
  (umask 077 && ssh-keygen -q -t ed25519 -N '' -C "ansible-converge" -f "$CERT_DIR/id") || return 1
  # No secret material on any command line; xtrace stays off around the login.
  { set +x; } 2>/dev/null
  login=$(jq -nc \
    '{role_id: env.CONVERGE_ROLE_ID, secret_id: env.CONVERGE_SECRET_ID}' |
    curl -fsSL --max-time 10 -H 'Content-Type: application/json' --data @- \
      "$BAO_ADDR/v1/auth/approle/login") || return 1
  token=$(printf '%s' "$login" | jq -er '.auth.client_token') || return 1
  RUNNER_BAO_TOKEN=$token
  signed=$(jq -nc --rawfile pub "$CERT_DIR/id.pub" --arg ttl "${SSH_CERT_TTL:-1h}" \
    '{public_key: $pub, ttl: $ttl}' |
    curl -fsSL --max-time 10 \
      -H @<(printf 'X-Vault-Token: %s\n' "$RUNNER_BAO_TOKEN") --data @- \
      "$BAO_ADDR/v1/$mount/sign/$CONVERGE_SIGN_ROLE" |
    jq -er '.data.signed_key') || return 1
  printf '%s\n' "$signed" >"$CERT_DIR/id-cert.pub"
  export PROXMOX_SSH_KEY_PATH="$CERT_DIR/id"

  if [[ -z ${BAO_TOKEN:-} ]]; then
    # The inventory resolver and controller-side OpenBao reads share this
    # short-lived token. Cleanup revokes it after ansible-playbook exits.
    export BAO_TOKEN=$RUNNER_BAO_TOKEN
  else
    # A caller-supplied token may carry broader human policy. Preserve it and
    # revoke the runner-owned signing token as soon as the cert is minted.
    revoke_runner_token || true
  fi
}

# Prefer the execution plane's own AppRole (principal `semaphore`) so its
# cert is distinguishable from the shared `ansible` identity in sshd logs;
# fall back to the shared ansible pair with a loud warning.
CONVERGE_ROLE_ID="" CONVERGE_SECRET_ID="" CONVERGE_SIGN_ROLE="" CONVERGE_IDENTITY=""
if [[ -n ${OPENBAO_APPROLE_SEMAPHORE_ROLE_ID:-} && -n ${OPENBAO_APPROLE_SEMAPHORE_SECRET_ID:-} ]]; then
  export CONVERGE_ROLE_ID=$OPENBAO_APPROLE_SEMAPHORE_ROLE_ID
  export CONVERGE_SECRET_ID=$OPENBAO_APPROLE_SEMAPHORE_SECRET_ID
  CONVERGE_SIGN_ROLE="automation-semaphore"
  CONVERGE_IDENTITY="semaphore"
elif [[ -n ${OPENBAO_APPROLE_ANSIBLE_ROLE_ID:-} && -n ${OPENBAO_APPROLE_ANSIBLE_SECRET_ID:-} ]]; then
  export CONVERGE_ROLE_ID=$OPENBAO_APPROLE_ANSIBLE_ROLE_ID
  export CONVERGE_SECRET_ID=$OPENBAO_APPROLE_ANSIBLE_SECRET_ID
  CONVERGE_SIGN_ROLE="automation-ansible"
  CONVERGE_IDENTITY="ansible"
  if [[ -n ${BAO_ADDR:-} ]]; then
    echo "WARNING: OPENBAO_APPROLE_SEMAPHORE_ROLE_ID/OPENBAO_APPROLE_SEMAPHORE_SECRET_ID" >&2
    echo "are not set — authenticating as the shared 'ansible' identity rather than" >&2
    echo "the execution plane's own." >&2
  fi
fi

if [[ -n ${BAO_ADDR:-} && -n $CONVERGE_ROLE_ID && -n $CONVERGE_SECRET_ID ]]; then
  # FAIL-LOUD: when the cert env is present, a mint failure is an error — never
  # silently ride the static key (that masked a dead cert path once already).
  # Break-glass = unset BAO_ADDR and both AppRole pairs, and set the static
  # key vars instead.
  if ! mint_ssh_cert; then
    echo "ERROR: OpenBao SSH cert mint FAILED and the cert env is present — refusing" >&2
    echo "the silent static-key fallback. Fix the cert path, or unset BAO_ADDR and the" >&2
    echo "OPENBAO_APPROLE_* env to deliberately use the static break-glass key." >&2
    exit 1
  fi
  unset CONVERGE_ROLE_ID CONVERGE_SECRET_ID
  echo "Using a short-lived SSH certificate from the OpenBao CA ($CONVERGE_SIGN_ROLE)."
  echo "  authenticated as: $CONVERGE_IDENTITY"
# If key file exists at PROXMOX_SSH_KEY_PATH, export expanded path for inventory.
# Otherwise load key content into ssh-agent and unset PROXMOX_SSH_KEY_PATH so
# inventory/hosts.yml omits ansible_ssh_private_key_file (Ansible uses the agent).
elif [[ -n ${PROXMOX_SSH_KEY_PATH:-} ]] && [[ -f ${PROXMOX_SSH_KEY_PATH/#\~/$HOME} ]]; then
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

# Pin host identities: materialize the reviewed known_hosts (Doppler
# SSH_KNOWN_HOSTS, harvested over authenticated channels) and verify strictly.
# A rebuilt guest gets a new host key and fails closed until re-harvested.
if [[ -n ${SSH_KNOWN_HOSTS:-} ]]; then
  if [[ -z $CERT_DIR ]]; then
    CERT_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ansible-sshkh.XXXXXX")
    chmod 700 "$CERT_DIR"
  fi
  printf '%s\n' "$SSH_KNOWN_HOSTS" >"$CERT_DIR/known_hosts"
  chmod 600 "$CERT_DIR/known_hosts"
  export ANSIBLE_SSH_COMMON_ARGS="-o UserKnownHostsFile=$CERT_DIR/known_hosts -o GlobalKnownHostsFile=/dev/null -o StrictHostKeyChecking=yes${ANSIBLE_SSH_COMMON_ARGS:+ $ANSIBLE_SSH_COMMON_ARGS}"
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
