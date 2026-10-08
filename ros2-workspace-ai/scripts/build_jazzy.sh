#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
# Stage 1: build only the simulation dependencies, before course integration.
scripts/jazzy_env.sh colcon --log-base .jazzy/log build \
  --base-paths .jazzy/vendor/src --build-base .jazzy/build --install-base .jazzy/install \
  --packages-select turtlebot3_description turtlebot3_manipulation_description turtlebot3_gazebo turtlebot3_msgs \
  --parallel-workers 2 --cmake-args -DBUILD_TESTING=OFF
# Stage 2/3: project packages. Never discover src/ recursively (it contains legacy vendors).
scripts/jazzy_env.sh colcon --log-base .jazzy/log build \
  --base-paths src/tb3_course_sim src/tb3_planner_execution \
  --build-base .jazzy/build --install-base .jazzy/install --parallel-workers 2
