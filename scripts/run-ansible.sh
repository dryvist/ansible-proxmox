#!/usr/bin/env bash
set -euo pipefail

export RUN_ANSIBLE_IDENTITIES="${RUN_ANSIBLE_IDENTITIES:-semaphore?,ansible}"
export RUN_ANSIBLE_SSH_AGENT="${RUN_ANSIBLE_SSH_AGENT:-1}"
export RUN_ANSIBLE_LIMIT_LOCALHOST="${RUN_ANSIBLE_LIMIT_LOCALHOST:-1}"

exec nix run github:dryvist/homelab-contracts/v5.30.0#run-ansible -- "$@"
