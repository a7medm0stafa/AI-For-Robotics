# Student starter structure — intentionally incomplete

These files are specifications/stubs, not the TA solution. Copy them into your own ROS Python package or planning project and implement the TODOs. Keep your implementation separate from `tb3_planner_execution`, which is complete TA reference material.

- MS1: create an `ament_python` package with dependencies `rclpy`, `geometry_msgs`, `nav_msgs`, `sensor_msgs`, `control_msgs`, `trajectory_msgs`; implement `robot_control.py` and console entry points.
- MS2: implement `task_planning.py` and your own PDDL domain/problem generator. It must run with ordinary Python and no ROS imports.
- MS3: implement `plan_execution.py`; bind symbolic actions to your MS1 clients, handle IDs/results, and persist only successful effects.

Interfaces and acceptance demonstrations are in `docs/ms1_robot_control.md`, `docs/ms2_task_planning.md`, and `docs/ms3_integration.md`. No grading weights or deadlines are implied.
