# AI for Robotics: Jazzy migration and course handoff

## Mission

You are the developing agent preparing this project for an AI for Robotics course. The project owner is now the teaching assistant. Deliver a working, reproducible ROS 2 Jazzy reference implementation and beginner-friendly instructions, starting from a fresh OS installation and ending with integrated task planning and robot execution.

The course milestones are fixed:

| Milestone | Student work | Required outcome |
| --- | --- | --- |
| MS1 | Install ROS 2 Jazzy and TurtleBot3/manipulation dependencies; implement nodes controlling the mobile robot, arm, and gripper. | Students can command and observe the robot and manipulator without a task planner. |
| MS2 | Install and use Fast Downward; implement the PDDL task model and planning workflow. | A goal and initial state produce a valid symbolic plan without running the simulator. |
| MS3 | Connect the planner to the TurtleBot3 control nodes. | Symbolic move/pick/place actions execute sequentially, with truthful results and knowledge-base updates. |

The custom package, house/world assets, map, room configuration, and planner are project work to preserve and migrate. Treat the existing implementations as TA reference material. Provide student-facing task specifications separately so that “implement a node” is not reduced to running the supplied solution. Do not invent grading weights or deadlines.

Default scope: simulation on Ubuntu 24.04 with ROS 2 Jazzy and Gazebo Harmonic, using TurtleBot3 with OpenMANIPULATOR-X. Verify the exact robot model against the current descriptions; do not substitute a bare Burger for the final mobile manipulator. Physical hardware deployment, perception, and autonomous grasp planning are outside the default scope.

## Working rules

- Read the current README and repository instructions before editing. Preserve uncommitted changes and generated project state; do not reset the existing workspace.
- The owner reports that vendor packages were installed rather than intentionally developed. Prefer supported upstream Jazzy versions over manually porting old vendor code. Compare before replacement because local assets and launch defaults may still contain project-specific changes.
- Preserve the legacy workspace as a reference. Work in an isolated checkout/workspace, or separate build/install/log directories. Avoid discovering duplicate ROS packages in the same source tree.
- Do not reuse Humble build artifacts, source the old install overlay, or solve compatibility by mixing Humble and Jazzy libraries.
- Use official upstream documentation and actual installed package interfaces. Pin tested revisions. Never assume every repository has a `jazzy` branch or that a Humble launch command still exists.
- Complete and test each stage before treating the next stage as validated. Report commands, observed results, and unresolved issues honestly. A successful build is not proof of working navigation or manipulation.
- Keep course-specific launch/configuration in project packages where possible, with minimal documented vendor patches only when necessary.

## Existing workspace and actual workflow

Paths in this document are relative to the repository root.

| Location | Role |
| --- | --- |
| `src/turtlebot3/` | Vendor robot packages, including navigation and bringup. |
| `src/turtlebot3_manipulation/` | Vendor manipulation descriptions, control, navigation, and MoveIt configuration. |
| `src/turtlebot3_simulations/` | Existing simulation packages, including the locally present `turtlebot3_manipulation_gazebo`. |
| `src/turtlebot3_msgs/`, `src/DynamixelSDK/` | Vendor dependencies. |
| `src/tb3_planner_execution/` | Project launch files, configuration, models, map, and Python execution nodes. |
| `planner/` | Fast Downward integration, PDDL, CLI, and knowledge-base files. |

The README documents separate terminals, not the combined house launch:

```bash
# Historical Humble workflow: reference only, not verified Jazzy commands.
ros2 launch turtlebot3_manipulation_gazebo gazebo.launch.py
ros2 launch turtlebot3_navigation2 navigation2.launch.py use_sim_time:=True map:=$PWD/src/tb3_planner_execution/maps/map.yaml
ros2 run tb3_planner_execution init_pose
ros2 run tb3_planner_execution turtlebot_move
ros2 run tb3_planner_execution gripper_control
ros2 run tb3_planner_execution planner_executor --ros-args -p use_gripper:=true
python3 planner/planner_cli.py
```

The simulator command resolves to `src/turtlebot3_simulations/turtlebot3_manipulation_gazebo/launch/gazebo.launch.py`, not the identically named file in the custom package. Its current default is `turtlebot3_gazebo/worlds/turtlebot3_house.world`, with spawn x=-2.65, y=1.0. The custom simulator launch instead refers to `tb3_planner_execution/worlds/my_house.world` and has different spawn defaults. Establish which world geometry matches the supplied map, room coordinates, and intended course environment before choosing the canonical launch.

`tb3_house_nav2.launch.py` is an alternative entry point. Its custom Nav2 parameter declaration/forwarding is commented out. The README navigation command also does not select the custom parameter file. Parent launch configurations may inherit map/time values, so do not claim they are necessarily lost; make argument forwarding explicit in the final implementation.

## Stage 0 — Inventory and reproducibility

1. Record OS, architecture, Python, ROS distributions, installed packages, repository remotes/revisions, and local modifications.
2. Inventory custom worlds, meshes/models, maps, room coordinates, PDDL, controller names, and current ROS interfaces. Preserve copies of mutable KB/problem/plan files for comparison.
3. Select a clean reference environment matching students' target OS. The TA machine already having Jazzy is not a substitute for validating installation instructions from scratch.
4. Establish a pinned dependency manifest (`dependencies/jazzy.repos`, or an equally reproducible package/version record). Record source versus binary choices and avoid accidental overlays of duplicate vendor packages.
5. Create a migration status document with stage results, exact versions, launch commands, and known limitations.

Gate: dependency ownership and a clean build strategy are documented; no Humble paths occur in the active Jazzy environment.

## Stage 1 — Fresh ROS and vendor installation

Write and execute a beginner-readable setup guide covering these steps:

1. Ubuntu 24.04 prerequisites, supported architecture, locale, required apt repositories, and official ROS repository/key setup, following the current Jazzy installation guide.
2. Install the Jazzy desktop environment and development tools: compiler/CMake, Git, colcon, rosdep, and vcstool as needed. Explain terminal sourcing and verify ROS with a publisher/subscriber example.
3. Install the supported Jazzy/Harmonic integration and control dependencies. Verify availability before prescribing apt names. Resolve dependencies from manifests with rosdep rather than relying on packages installed incidentally on the TA machine.
4. Obtain official Jazzy-compatible TurtleBot3, messages, simulation, manipulation, and required SDK/driver dependencies. Follow their dependency manifests and pin tested commits or releases.
5. Identify the actual supported mobile-manipulator simulation package and launch command. Inspect its manifests, robot description, simulator backend, and examples. Do not assume a similarly named repository is ROS 2/Harmonic compatible.
6. If no suitable upstream combined simulation exists, document that finding and build the smallest course-owned integration using supported robot descriptions, Harmonic, and `gz_ros2_control`. This is TA infrastructure work, not a prerequisite porting exercise for students.
7. Build and source only the new overlay in every required terminal. Document the chosen robot-model environment variables and how to verify package resolution.

Official `jazzy` branches were verified for `turtlebot3`, `turtlebot3_manipulation`, and `turtlebot3_simulations`. This does not establish identical launch layouts or support for every package in the current workspace. The separate `turtlebot3_manipulation_simulations` repository advertised `noetic` and `main` at handoff time; a `jazzy` URL returned 404. Recheck upstream, and do not prescribe cloning its nonexistent Jazzy branch.

Provide one tested primary installation path. Add alternatives only when tested and useful. Make setup scripts repeatable, detect existing rosdep initialization, and avoid unnecessary shell-startup modifications. Package installation must respect the execution environment's approval requirements.

Gate: fresh build succeeds; ROS communication works; package prefixes resolve to the intended Jazzy installation. No simulator or controller depends on Gazebo Classic.

## Stage 2 — Verify the standard robot and manipulator

First validate upstream examples in a simple world, before adding the course house, Nav2 tuning, or planner.

- Spawn the mobile base; observe joint states, laser data, odometry, and simulation clock.
- Command forward motion, rotation, and stopping. Verify actual simulated motion and feedback, not merely successful publication.
- Spawn/test the arm and gripper through their real controller interfaces. Demonstrate home/reach positions and opening/closing with successful action results.
- Confirm the arm is attached to the mobile base in the final combined model. A standalone arm demo alone is insufficient.
- Record topic names and types, action names and types, joint names/limits, controller names, and coordinate frames.
- Assign one owner to wheel control and `odom -> base` TF. Avoid duplicate odometry, joint-state, or TF publishers. Identify which signals need `ros_gz_bridge`; do not blindly bridge signals already published by ROS controllers.
- Verify `/clock` bridging and consistent simulation time. Match sensor QoS and command types throughout the graph.

Useful diagnostic commands include `ros2 topic list -t`, `ros2 topic info -v`, `ros2 action list -t`, `ros2 control list_controllers`, and `ros2 run tf2_ros tf2_echo`. Record concrete arguments and expected output in the finished guide.

Gate: base movement and arm/gripper commands work independently and together, with feedback and no task planner running.

## Stage 3 — Migrate course assets and MS1 reference nodes

### Project assets and launch

- Preserve `tb3_planner_execution/worlds/`, `models/`, `maps/`, and room semantics. Port custom world systems, resource paths, and materials to Harmonic. Install model assets through the package's build configuration; current `setup.py` omits `models/`.
- Validate the supplied map against the selected world geometry. Regenerate the map only if necessary, explaining changes to coordinates, origin, resolution, or room goals.
- Choose and document one spawn pose, map pose, and initial localization procedure. Resolve the different hardcoded poses in the existing files. Do not assume simulation-world coordinates equal map coordinates without checking alignment.
- Create a canonical course simulator launch, with explicit world, pose, model, and simulation-time arguments. Keep separate simulation/navigation launches usable for teaching; an optional combined convenience launch may call them.
- Replace machine-specific asset paths with package-share resolution. Use configurable writable locations for KB, generated problem, and plan outputs; do not write into installed package resources.
- Declare all imported and launched dependencies, including `nav_msgs`, `std_srvs`, `control_msgs`, `trajectory_msgs`, launch utilities, simulator integration, and navigation as appropriate.

### MS1 student contract

Students install the verified environment and implement their own control nodes. Provide interface specifications, starter structure, and expected observable behavior separately from complete TA implementations.

Required demonstrations:

1. A node commands base motion and stopping and reads relevant state feedback.
2. A node commands an arm trajectory and gripper opening/closing, handles rejected/failed requests, and reports completion from controller results.
3. Commands can be triggered without Fast Downward. Timeouts and unavailable controllers produce clear failures.

Preserve or adapt `TurtleBotMove.py` and `grip_ctrl.py` as TA references. Room navigation using Nav2 can be prepared here, but full autonomous room-to-room task execution is an MS3 integration requirement. Students are not required to implement a replacement for Nav2 or ros2_control.

Current endpoints to verify against the chosen Jazzy controllers:

| Purpose | Legacy endpoint/interface |
| --- | --- |
| Room navigation | `navigate_to_pose`, `nav2_msgs/action/NavigateToPose` |
| Arm | `/arm_controller/follow_joint_trajectory`, `control_msgs/action/FollowJointTrajectory` |
| Gripper | `/gripper_controller/gripper_cmd`, `control_msgs/action/GripperCommand` |
| Pick/place wrapper | `close_gripper` / `open_gripper`, `std_srvs/srv/Trigger` |

Do not assume a newer gripper controller has the same action type or joint configuration. Update clients and documentation together if changing controllers.

Gate: the project robot works with migrated assets, and the MS1 reference nodes satisfy the standalone demonstrations.

## Stage 4 — MS2: Fast Downward and symbolic planning

1. Install/build a pinned Fast Downward revision using its official instructions for the chosen OS. Record compiler, Python, build command, and executable path. Do not depend on the old bundled build.
2. Preserve and validate `planner/domain.pddl`, problem generation, room connectivity, object names, and goal vocabulary. The existing domain has `move`, `pick`, and `place` actions and models robot location, object location, holding, and an empty hand.
3. Separate the planning core from ROS execution. The existing `planner_cli.py` imports `rclpy` and coordinates execution; introduce a planning-only mode or separate module/CLI so MS2 runs with no simulator, controllers, or ROS nodes.
4. Make planner discovery explicit through configuration or a documented executable path. The legacy search uses `astar(lmcut())`; retain it initially if compatible with the selected model/version.
5. Use a defined output directory and plan filename. Check planner exit status, distinguish no-solution from errors/timeouts, and prevent stale plans from being mistaken for new results. Handle empty plans for already-satisfied goals.
6. Parse plan actions structurally and validate arguments. Test PDDL state transitions without claiming that planning alone has moved the physical/simulated robot.

MS2 student deliverables: PDDL domain/problem or problem generator, documented goal input, planner invocation, plan parser/output, and explanations of preconditions/effects.

Gate: tests cover a reachable movement goal, object transport across rooms, an already-satisfied goal, an unreachable goal, and a planner failure/timeout. Validate action applicability and final goal satisfaction rather than demanding one exact action sequence.

## Stage 5 — MS3: navigation and planner execution

### Navigation baseline

- Start from the selected Jazzy Nav2 configuration, then apply the robot's footprint, frames, speed limits, sensor topics, map, and course tuning.
- Explicitly pass `map`, `params_file`, and `use_sim_time` in project launch files. Remove paths into `/opt/ros/humble`.
- Use appropriate Jazzy default behavior trees for single-pose and through-poses navigation. Review both Humble-to-Iron and Iron-to-Jazzy migration changes.
- Ensure the velocity chain agrees on `Twist` versus `TwistStamped`, including controller, smoother, collision monitor, teleop, bridge, and final drive system where present.
- Verify `map -> odom -> base_footprint/base_link` and sensor transforms. Do not substitute a static transform for moving odometry.
- Read map-frame robot position through localization/TF. Existing `TurtleBotMove.py` republishes odometry position labeled as `map`; correct that frame assumption.
- Set initial pose after localization is ready, with consistent simulation time. Avoid relying only on fixed sleeps.
- Complete a single navigation goal before connecting the planner.

### Action execution and knowledge base

Map `(move from to)` to room navigation, `(pick object room)` to the arm/gripper pick sequence, and `(place object room)` to the place sequence. Preserve the course's goal vocabulary: `robot-at ROOM`, `holding OBJECT`, and `in-room OBJECT ROOM`.

Execute one plan action at a time. Advance only after its actual success result. Keep command identity, completion, and success distinct; reject overlapping plans or queue them explicitly. Avoid the existing race between separate goal-room and move-trigger topics by using a single request/action or an acknowledged protocol.

Fix these existing correctness issues as part of integration:

- `plan_executor_node.py` sets its completion event even when `move_status` is false, then treats the event as success. Store/check the result separately.
- It publishes `plan_complete=True` after aborting a failed action. Report failure truthfully.
- `grip_ctrl.py` treats a finished gripper result future as success without fully checking status/result. Check acceptance, action status, and controller outcome.
- Align timeouts with the complete arm-down/grip/arm-up sequence. Ensure executor/callback configuration allows results to arrive; avoid deadlocks and concurrent conflicting arm sequences.
- Share one configurable knowledge-base path across CLI and executor. Update robot/object/holding state only after confirmed execution success, write updates atomically, and define reset/resume behavior explicitly.
- A generated plan, timeout, aborted action, or `use_gripper=false` shortcut must not count as an end-to-end manipulation success.

The existing pick/place behavior commands arm/gripper motion and changes symbolic state. That does not prove a physical object was grasped or attached in Gazebo. Preserve this course abstraction unless physical grasping is explicitly required, and label it accurately in demos and student instructions. Do not silently add a perception/grasp-planning project.

Gate: from a defined initial KB and matching robot pose, complete a valid object-transport plan across rooms. Verify observed navigation, manipulation action results, action order, and final KB. Inject a navigation failure and manipulation failure: execution must stop, success must not be reported, and failed effects must not enter the KB.

## Compatibility checklist for retained legacy files

Use this only for code retained after upgrading dependencies; do not blindly edit all vendor files.

| Legacy pattern/location | Required review |
| --- | --- |
| `gazebo_ros`, `spawn_entity.py`, `gzserver`, Classic `.so` plugins | Replace with Harmonic launch/spawn/systems and the required bridges. |
| `gazebo_ros2_control/GazeboSystem`, `libgazebo_ros2_control.so` | Use the verified Jazzy `gz_ros2_control` equivalents. |
| `fake_components/GenericSystem` | Installed Jazzy exports `mock_components/GenericSystem`; review mock parameters too. |
| Gripper mimic parameters inside `<ros2_control>` | Use supported URDF mimic semantics and compatible command/state interfaces. |
| `base.launch.py` copies and controller YAML | Review robot-description topic, spawner parameter files, controller readiness, remappings, and simulation time. |
| `cmd_vel_unstamped`, `use_stamped_vel: false` | Jazzy diff-drive control expects stamped velocity commands; verify the chosen architecture. |
| `spawner.py` executable | Use the installed `spawner` executable. |
| Controller `open_loop_control` | Review the Jazzy replacement and intended behavior. |
| Older Nav2 planner/behavior plugin IDs using `/` | Use IDs exported by the chosen Jazzy plugins; do not globally replace slashes. |
| Existing gripper controller and hardware API | Check installed exports/headers before calling deprecated APIs removed. Some legacy interfaces remain available. |
| Custom Nav2 YAML and absolute paths | Remove Humble behavior-tree paths and machine-specific asset paths. |
| `build/`, `install/`, `log/`, old Dockerfile | Replace the active build/container configuration with a clean Jazzy environment; preserve legacy artifacts outside the active build. |

## Required final deliverables

Produce a reviewable implementation and these documents/artifacts (equivalent organization is acceptable):

- `dependencies/jazzy.repos` or a complete pinned dependency record, with any vendor patch rationale.
- `docs/setup_jazzy.md`: instructions from fresh Ubuntu through ROS/vendor installation, dependency resolution, build, sourcing, standard robot and arm smoke tests, and troubleshooting.
- `docs/ms1_robot_control.md`: student tasks, interfaces, demonstrations, expected feedback, and acceptance criteria.
- `docs/ms2_task_planning.md`: Fast Downward installation, PDDL tasks, planning-only workflow, and acceptance cases.
- `docs/ms3_integration.md`: action mapping, Nav2/map setup, KB semantics, end-to-end launch sequence, and failure cases.
- A clearly identified TA reference implementation and separately labeled student scaffold/specifications. Existing complete solutions must not masquerade as student exercises.
- Updated root README with tested commands in terminal order, explicit environment sourcing, robot model, initial state, and paths that work under another username.
- Installed project assets, project-owned launch/configuration, meaningful automated planner/executor tests, and reproducible simulator validation instructions.
- A migration report containing actual test evidence and remaining limitations. Hardware checks not performed and GUI/simulation checks blocked by the environment must be labeled unverified.

Final acceptance: another developer can start from the documented fresh environment, reproduce each milestone independently, then run MS3 without relying on the TA machine's old workspace, cached builds, hidden packages, or absolute home-directory paths.

## Official references

Recheck current content during implementation and record the tested versions. These are reference entry points, not a claim that all upstream examples were tested for this project.

- [ROS 2 Jazzy installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
- [TurtleBot3 Jazzy source](https://github.com/ROBOTIS-GIT/turtlebot3/tree/jazzy)
- [TurtleBot3 manipulation Jazzy source](https://github.com/ROBOTIS-GIT/turtlebot3_manipulation/tree/jazzy)
- [TurtleBot3 simulations Jazzy source](https://github.com/ROBOTIS-GIT/turtlebot3_simulations/tree/jazzy)
- [Separate manipulation simulation repository: verify compatibility](https://github.com/ROBOTIS-GIT/turtlebot3_manipulation_simulations)
- [ROBOTIS manipulation manual: check distribution applicability](https://emanual.robotis.com/docs/en/platform/turtlebot3/manipulation/)
- [Gazebo/ROS version pairing](https://gazebosim.org/docs/latest/ros_installation/)
- [Gazebo Classic migration](https://gazebosim.org/docs/latest/gazebo_classic_migration/)
- [Jazzy gz_ros2_control](https://control.ros.org/jazzy/doc/gz_ros2_control/doc/index.html)
- [ros2_control Humble-to-Jazzy migration](https://control.ros.org/jazzy/doc/ros2_control/doc/migration.html)
- [Controller migration](https://control.ros.org/jazzy/doc/ros2_controllers/doc/migration.html)
- [Nav2 migration guides](https://docs.nav2.org/jazzy/configuration_and_development/migration_guides/)
- [Fast Downward documentation](https://www.fast-downward.org/latest/documentation/)
