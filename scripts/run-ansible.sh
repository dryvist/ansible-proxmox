#!/usr/bin/env bash
set -euo pipefail

export RUN_ANSIBLE_IDENTITIES="${RUN_ANSIBLE_IDENTITIES:-semaphore?,ansible}"
export RUN_ANSIBLE_FALLBACK_ON_ERROR="${RUN_ANSIBLE_FALLBACK_ON_ERROR:-1}"
export RUN_ANSIBLE_SSH_AGENT="${RUN_ANSIBLE_SSH_AGENT:-1}"
export RUN_ANSIBLE_LIMIT_LOCALHOST="${RUN_ANSIBLE_LIMIT_LOCALHOST:-1}"

# renovate: datasource=github-releases depName=dryvist/homelab-contracts
HOMELAB_CONTRACTS_REF=v5.31.0
exec nix run "github:dryvist/homelab-contracts/${HOMELAB_CONTRACTS_REF}#run-ansible" -- "$@"
