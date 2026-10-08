#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
scripts/jazzy_env.sh --underlay colcon build --symlink-install --parallel-workers 2 --cmake-args -DBUILD_TESTING=OFF
