#!/usr/bin/env bash
# Pre-pull a molecule scenario's platform image, with bounded retries.
#
# Molecule's `create` pulls the image inline and gives up after two tries, so a
# transient registry error fails the whole scenario and reads exactly like a
# broken role. It has already happened: Docker Hub returned `500 Internal Server
# Error` on a manifest HEAD and took a promotion gate down with "Error pulling
# image".
#
# Retrying `molecule test` would be the WRONG fix -- that retries the assertions
# too, and a flaky test would become indistinguishable from a passing one. This
# retries only the network fetch. By the time molecule runs, the image is in the
# local daemon and `create` does no pull at all, so the scenario passes or fails
# on its own merits.
#
# A pull that never succeeds still fails the job: this adds patience, not
# tolerance.
#
# Usage: pull-molecule-image.sh <scenario>
set -euo pipefail

scenario="${1:?usage: pull-molecule-image.sh <scenario>}"
manifest="molecule/${scenario}/molecule.yml"

if [ ! -f "$manifest" ]; then
  echo "::error::no molecule.yml for scenario '${scenario}'"
  exit 1
fi

# Scenario files carry the image as ${MOLECULE_IMAGE:-<default>}. CI sets no
# MOLECULE_IMAGE, so resolve the same way the shell would: honour the variable
# when it is set and non-empty, otherwise take the default after ":-".
images="$(python3 - "$manifest" <<'PY'
import os
import sys

import yaml

with open(sys.argv[1]) as fh:
    cfg = yaml.safe_load(fh) or {}

for platform in cfg.get("platforms") or []:
    raw = platform.get("image")
    if not raw:
        continue
    raw = raw.strip()
    if raw.startswith("${") and ":-" in raw:
        name, default = raw[2:].rstrip("}").split(":-", 1)
        raw = os.environ.get(name) or default
    print(raw)
PY
)"

if [ -z "$images" ]; then
  echo "No pre-built image declared for '${scenario}'; molecule will build one."
  exit 0
fi

status=0
while read -r image; do
  [ -n "$image" ] || continue
  pulled=0
  attempts=5
  for attempt in $(seq 1 "$attempts"); do
    if docker pull "$image"; then
      pulled=1
      break
    fi
    if [ "$attempt" -eq "$attempts" ]; then
      echo "pull of ${image} failed (attempt ${attempt}/${attempts}); giving up"
      break
    fi
    echo "pull of ${image} failed (attempt ${attempt}/${attempts}); retrying"
    sleep $((attempt * 10))
  done
  if [ "$pulled" -ne 1 ]; then
    echo "::error::could not pull ${image} after 5 attempts"
    status=1
  fi
done <<EOF
${images}
EOF

exit "$status"
