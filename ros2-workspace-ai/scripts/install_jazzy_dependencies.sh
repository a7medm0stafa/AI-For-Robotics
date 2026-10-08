#!/usr/bin/env bash
set -eo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
# Run after ROS Jazzy repository setup; deliberately does not edit .bashrc.
source /opt/ros/jazzy/setup.bash
sudo apt-get update
sudo apt-get install -y ros-jazzy-desktop ros-dev-tools python3-vcstool python3-pytest build-essential cmake git ros-jazzy-ros-gz ros-jazzy-gz-ros2-control ros-jazzy-ros2-controllers ros-jazzy-navigation2 ros-jazzy-nav2-bringup
if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  sudo rosdep init
fi
rosdep update --rosdistro jazzy
rosdep install --from-paths \
  .jazzy/vendor/src/turtlebot3/turtlebot3_description \
  .jazzy/vendor/src/turtlebot3_msgs \
  .jazzy/vendor/src/turtlebot3_simulations/turtlebot3_gazebo \
  .jazzy/vendor/src/turtlebot3_manipulation/turtlebot3_manipulation_description \
  src/tb3_course_sim src/tb3_planner_execution \
  --ignore-src --rosdistro jazzy -y
