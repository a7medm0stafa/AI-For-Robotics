# MS1 — student robot control

Goal: command and observe the mobile base, attached arm, and gripper without Fast Downward. Use the verified environment in [setup](setup_jazzy.md). The complete TA solutions are `TurtleBotMove.py`, `grip_ctrl.py`, and the smoke scripts; they are reference material, not student submissions. Begin with [the scaffold](../student_scaffold/README.md).

## Interfaces

| Purpose | Interface | Expected observation |
|---|---|---|
| Base command | `/cmd_vel`, `geometry_msgs/msg/TwistStamped` | Current simulation timestamp, linear x and angular z; zero command stops |
| Base feedback | `/odom`, `nav_msgs/msg/Odometry` | Pose in `odom`, velocity; never relabel as `map` |
| Laser / clock | `/scan`, `sensor_msgs/msg/LaserScan`; `/clock`, `rosgraph_msgs/msg/Clock` | Sensor QoS, 360 scan values; advancing simulation time |
| Joint feedback | `/joint_states`, `sensor_msgs/msg/JointState` | Two wheel, four arm, two finger joints |
| Arm | `/arm_controller/follow_joint_trajectory`, `control_msgs/action/FollowJointTrajectory` | Accepted goal, status SUCCEEDED, error_code 0 |
| Gripper | `/gripper_controller/gripper_cmd`, `control_msgs/action/GripperCommand` | Accepted goal, SUCCEEDED, reached_goal true, stalled false |
| TA pick/place wrappers | `close_gripper`, `open_gripper`, `std_srvs/srv/Trigger` | Full reach/grip/home sequence; truthful success/message |

Arm joints: `joint1`, `joint2`, `joint3`, `joint4` (radians). Tested home `[0,0,0,-0.1]`, reach `[0,0.3,0.5,0.5]`, with a two-second trajectory. Gripper command joint: `gripper_left_joint`, meters; tested open `0.01`, closed `-0.01`. `gripper_right_joint` mimics it in URDF and has state interfaces only. Read the pinned upstream joint limits before designing new poses.

## Student implementation tasks

1. Implement a node publishing stamped base commands and reading odometry. Demonstrate forward, rotation, and stop, recording measured displacement, heading change, and stopped velocity. Publish zero in cleanup and use a bounded duration.
2. Implement arm and gripper action clients. Demonstrate home/reach and open/close; inspect acceptance, status and result fields. Handle unavailable controllers and timeouts, and cancel timed-out goals.
3. Provide a trigger independent of the planner. Serialize conflicting manipulation sequences, reject concurrent requests explicitly, and keep the executor able to process action responses while waiting.
4. Explain frame IDs, simulation time and QoS. Distinguish completion from success and a commanded joint position from verified feedback.

Acceptance: successful observable base motion and stop, controller-confirmed arm/gripper motion with matching feedback, clear failure for an inactive/unavailable controller, and no overlapping arm sequences. Rejected/aborted/timed-out commands must not print success. Do not implement your own ros2_control or Nav2 replacement.

## TA standalone demonstration

Terminal 1 starts `tb3_course_sim sim.launch.py`; terminal 2 runs:

```bash
scripts/jazzy_env.sh ros2 run tb3_planner_execution gripper_control --ros-args -p use_sim_time:=true
```

Terminal 3 runs `scripts/jazzy_env.sh python3 scripts/smoke_gripper_services.py`. This checks complete sequences and overlapping-request rejection. `smoke_gripper_failure.py` temporarily deactivates the simulated gripper controller, checks failure, and restores activation. After that intentional fault, reconcile the arm and restart `gripper_control` to clear its failure latch.

Room navigation is optional preparation here and is described in MS3. Pick/place in this course is a **symbolic grasp abstraction** supported by controller motion. No Gazebo object is attached or transported physically by this implementation.
