# Jazzy dependencies

The four ROBOTIS source trees are included directly under `src/`, as in the original workspace. Their upstream commits are pinned in `jazzy.repos`. There is no separate migration workspace or vendor overlay to source.

The default `colcon build` discovers eight packages: `turtlebot3_description`, `turtlebot3_msgs`, `turtlebot3_gazebo`, `turtlebot3_navigation2`, `turtlebot3_teleop`, `turtlebot3_manipulation_description`, `tb3_course_sim`, and `tb3_planner_execution`. `COLCON_IGNORE` marks vendor packages outside the simulation course (hardware, MoveIt and mapping). `planner/COLCON_IGNORE` keeps the separately built planner out of colcon.

`tb3_course_sim` includes the upstream Waffle Pi and OpenMANIPULATOR-X geometry and adds Harmonic/gz_ros2_control integration. The upstream manipulation simulation still contains Classic references, so do not launch that unused integration. Course launch and controller configuration live in project packages; vendor geometry is unchanged.

Fast Downward is under `planner/downward`, pinned by `fast_downward.repos`. Run `scripts/build_planner.sh` to fetch the exact revision when absent and build it. No old binary cache is reused after moving the workspace.

System dependencies are Jazzy apt packages resolved by rosdep. `installed_versions.tsv` records tested versions, not a frozen apt mirror. Update `ros-jazzy-diagnostic-updater` alongside Nav2 on older Jazzy installations: a new lifecycle manager with the January 2026 updater library can fail with an undefined symbol.

The GripperCommand controller is deprecated but still exported and tested in Jazzy. Its endpoint is `/gripper_controller/gripper_cmd`; replacing it with the parallel controller also requires updating the action clients.
