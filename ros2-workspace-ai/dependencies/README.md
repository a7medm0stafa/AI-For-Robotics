# Dependency ownership

`jazzy.repos` pins four official ROBOTIS Git commits. `fast_downward.repos` pins Fast Downward release 24.06.1 (commit `1eef26b2cbf599a1894606aa898d9d49e1034cb9`). `installed_versions.tsv` records the tested core apt versions; it is an evidence record, not a frozen apt mirror. Nav2 versions cannot yet be recorded because Nav2 is not installed.

| Source | Selected packages / purpose |
|---|---|
| turtlebot3 | turtlebot3_description; upstream Jazzy Nav2 parameter reference |
| turtlebot3_msgs | turtlebot3_msgs |
| turtlebot3_simulations | turtlebot3_gazebo; standard base smoke test and house furniture meshes |
| turtlebot3_manipulation | turtlebot3_manipulation_description; Waffle Pi and OpenMANIPULATOR-X geometry, inertias, joints, limits, mimic |
| apt Jazzy | ROS desktop, ros_gz, gz_ros2_control, controller plugins, Nav2, tools; resolved from selected manifests |
| project | tb3_course_sim: Harmonic world, bridges, controllers, and combined description; tb3_planner_execution: course assets and TA nodes |

All vendor checkouts are unchanged. The upstream manipulation Jazzy top-level simulation xacro still contains `libgazebo_ros2_control.so`; the separate manipulation simulation repository offers no Jazzy branch. `tb3_course_sim` includes only the geometry macros and supplies current integration. It never launches vendor Classic plugins. One diff-drive controller owns wheel commands, odometry and `odom -> base_footprint`; one joint-state broadcaster owns joint states. Only clock and laser are bridged.

The simulation subset does not build or require OpenCR/Dynamixel hardware drivers, SDK examples, MoveIt, teleop, or Cartographer. These are outside this course path, so their legacy and upstream manifests are not fed into the active dependency resolution/build. Do not build the entire upstream manipulation tree and assume hardware compatibility was validated. No vendor C++ port was made.

The installed `position_controllers/GripperActionController` still exports `control_msgs/action/GripperCommand` at `/gripper_controller/gripper_cmd` and was tested. It emits a deprecation warning; changing to the parallel gripper controller would require changing the action client and tests together. Retaining this supported installed interface avoids an unnecessary API change during the Jazzy conversion.

The custom and legacy upstream house collision structures compared identically before migration (107 collisions). The course copy keeps the geometry and replaces Classic material scripts with SDF colors. Furniture mesh URIs resolve through the pinned `turtlebot3_gazebo/models/turtlebot3_house` resources. The map image, YAML origin/resolution, PDDL domain, original mutable KB, generated problem, and old plan remain unchanged.
