# MS3 — student planner execution

**Runtime gate pending:** Nav2 is not installed on the migration machine. The following sequence is implemented but not an accepted end-to-end demonstration. Install dependencies, verify localization and one navigation goal, then perform object-transport and real failure tests. The pure transaction/failure tests and actual manipulation services have been tested separately.

## Frames and house configuration

The house geometry is the preserved custom copy, equivalent in collisions to the legacy upstream house. Map resolution `0.05` and origin `[-5.9,-5.13,0]` are unchanged. World spawn is `(-2.65,1.0,0)`. `config/rooms.yaml` exposes the **provisional legacy transform** `map = world + [2.0,0.5]`, so initial map pose is `(-0.65,1.5,0)`.

A wall-surface fit estimated translation `(1.978,0.389)` and yaw `-0.0061` rad, with clipped residual RMS 0.141 m; identity was 0.262 m. This supports an offset but does not establish localization accuracy. Preserve the explicit legacy offset until AMCL/laser overlay verifies it; if it needs adjustment, update the transform, room goals and initial pose together. The fit is reproducible with `scripts/check_map_alignment.py` (optional analysis dependencies: numpy, scipy, Pillow, PyYAML).

`odom -> base_footprint` comes from the diff-drive controller; robot_state_publisher supplies the robot tree; AMCL must supply `map -> odom`. No static odometry TF is installed. `RoomNavigation` reads map-frame TF and rejects missing/stale localization. The legacy hidden `+2,+0.5` addition and mislabeled odometry pose are removed.

`navigation.launch.py` explicitly forwards `map`, `params_file`, and `use_sim_time`. Parameters start from the pinned upstream Jazzy Waffle Pi configuration, use a conservative home-arm footprint, and explicitly use `TwistStamped` in controller, behavior, smoother and collision monitor. Both behavior tree overrides are omitted so the installed Jazzy Nav2 chooses the appropriate default tree for each navigator. Validate the velocity chain with `ros2 topic info -v`; navigation tuning remains unverified.

## Terminal order (after prerequisites)

All commands run from `ros2-workspace-ai`; every terminal uses the clean wrapper.

1. Simulator:
   ```bash
   scripts/jazzy_env.sh ros2 launch tb3_planner_execution gazebo.launch.py
   ```
2. Nav2:
   ```bash
   scripts/jazzy_env.sh ros2 launch tb3_planner_execution navigation.launch.py
   ```
3. Initial localization, after checking the provisional alignment:
   ```bash
   scripts/jazzy_env.sh ros2 run tb3_planner_execution init_pose --ros-args -p use_sim_time:=true -p x:=-0.65 -p y:=1.5 -p yaw:=0.0
   scripts/jazzy_env.sh ros2 run tf2_ros tf2_echo map base_footprint
   ```
   The node waits for active AMCL and a clock, with a 60-second deadline. Publication is not proof of localization; inspect the laser/map overlay and pose. An optional `ros2 run rviz2 rviz2` in the wrapper can display `/map`, `/scan`, TF and robot model.
4. Before the planner, verify one room goal using the standalone TA node:
   ```bash
   scripts/jazzy_env.sh ros2 run tb3_planner_execution turtlebot_move --ros-args -p use_sim_time:=true
   # another terminal: subscribe before publishing
   scripts/jazzy_env.sh ros2 topic echo /room_result
   # another terminal:
   scripts/jazzy_env.sh ros2 topic pub --once /room_request std_msgs/msg/String '{data: "{\"id\":\"ms1-check\",\"room\":\"diningroom\"}"}'
   ```
   Require success and verify observed map-frame motion. Stop this standalone node before MS3; the plan executor owns navigation directly. Return the robot to the defined initial pose by restarting the simulator/Nav2 and localizing before resetting the KB.
5. Manipulation wrapper:
   ```bash
   scripts/jazzy_env.sh ros2 run tb3_planner_execution gripper_control --ros-args -p use_sim_time:=true
   ```
6. Executor:
   ```bash
   scripts/jazzy_env.sh ros2 run tb3_planner_execution planner_executor --ros-args -p use_sim_time:=true
   ```
7. With matching robot/KB state and no active execution:
   ```bash
   python3 planner/planner_cli.py --reset
   scripts/jazzy_env.sh python3 planner/planner_cli.py --goal 'in-room cup bedroom' --execute
   ```

Default KB is `~/.local/state/tb3_course/kb.json`. For another writable path, set both CLI `--kb PATH` and executor ROS parameter `-p kb_path:=PATH`. The executor rejects mismatches. Generated files never go into installed package resources.

## Student execution contract

Implement one action at a time. Map move to Nav2, pick to arm-down/close/home, place to arm-down/open/home. An immutable request on `/plan_request` (`std_msgs/String` JSON) includes `id` (UUID), `kb_path`, `initial_state`, `goal`, and parsed `actions`. `/plan_result` returns the same ID, `success`, `completed` action count and explanatory `message`. A single request carries command identity and its arguments; separate room/trigger topics are no longer used by MS3.

Reject overlapping plans, stale initial state, malformed actions and duplicate execution IDs. Check action acceptance, result status and controller error fields. Completion alone is not success. `use_gripper:=false` causes pick/place failure, not simulated success.

Only after actual action success may effects be atomically committed. Completed effects remain if a later action fails; failed effects are absent. A shared file lock prevents reset/execution overlap. The execution journal `<kb>.execution.json` records progress and latches uncertainty after failure or a crash. Reconcile robot/arm/object state and use an explicit reset before retry; do not replay a timed-out plan automatically. A CLI response timeout does not cancel the executor and must not prompt a blind reset.

Manipulation wrappers reject overlap and latch failures until restart/reconciliation. They allow up to 90 seconds for the complete service sequence. Timed-out action goals are canceled, including late acknowledgements. A Trigger service itself has no cancellation API; after its timeout, motion may still be finishing, so execution stops and requires reconciliation.

## Acceptance still to run

- Validate map/laser alignment and all room goals, then a single navigation goal with measured map-frame pose.
- From the stated initial KB and robot pose, execute a cup transport plan through connected rooms. Record action order, Nav2 results, controller results and final KB; cup ends in bedroom, hand empty, robot at bedroom.
- Inject navigation failure (unreachable goal or inactive Nav2 controller) and manipulation failure (inactive gripper). Execution must stop, return false, and preserve only already-confirmed effects.
- Verify duplicate/overlapping plans and response timeouts cannot command a second conflicting run.

Unit tests exercise the transaction under injected failures, and an actual inactive-gripper test has returned failure. They do not substitute for these integrated Nav2 tests. Physical grasping, perception, object attachment and hardware deployment remain outside scope.
