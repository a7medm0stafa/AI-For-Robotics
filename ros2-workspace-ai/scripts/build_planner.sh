#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p .jazzy
vcs import .jazzy --input dependencies/fast_downward.repos --skip-existing
planner_revision="$(git -C .jazzy/downward rev-parse HEAD)"
if [[ "$planner_revision" != 1eef26b2cbf599a1894606aa898d9d49e1034cb9 ]]; then
  echo 'Fast Downward revision mismatch; preserve your checkout and use the pinned revision.' >&2
  exit 1
fi
python3 .jazzy/downward/build.py release -j2
