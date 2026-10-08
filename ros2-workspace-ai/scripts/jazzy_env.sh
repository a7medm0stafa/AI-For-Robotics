#!/usr/bin/env bash
# Execute a command in a clean ROS environment. Never source the legacy overlay.
set -eo pipefail
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ${TB3_CLEAN_ENV:-0} != 1 ]]; then
  exec env -i HOME="$HOME" USER="${USER:-student}" PATH=/usr/local/bin:/usr/bin:/bin LANG=C.UTF-8 DISPLAY="${DISPLAY:-}" XAUTHORITY="${XAUTHORITY:-}" XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-}" TERM="${TERM:-xterm}" ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-73}" TB3_CLEAN_ENV=1 bash "$0" "$@"
fi
source /opt/ros/jazzy/setup.bash
if [[ -f "$project_root/.jazzy/install/local_setup.bash" ]]; then
  source "$project_root/.jazzy/install/local_setup.bash"
fi
export TURTLEBOT3_MODEL=waffle_pi
export ROS_LOG_DIR="$project_root/.jazzy/ros_logs"
mkdir -p "$ROS_LOG_DIR"
cd "$project_root"
exec "$@"
