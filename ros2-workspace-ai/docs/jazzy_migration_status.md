# Jazzy migration status — 2026-10-08

Branch: `jazzy`, created from `44bd8b6`. **This is a working simulation/MS2 migration with MS3 still blocked, not a fully accepted course release.** The owner could not install additional system packages during this session. No apt installation was performed and no hardware checks were attempted.

## Stage gates and evidence

| Stage | Observed result | Gate |
|---|---|---|
| 0: inventory/isolation | Ubuntu 24.04.4 amd64, Python 3.12.3, GCC 13.3, CMake 4.2.1; source pins recorded; separate `.jazzy` artifacts; clean ROS environment; original local state preserved | Passed for this machine |
| 1: vendor installation | Four selected upstream simulation packages built and resolve to `.jazzy/install`; C++ talker/Python listener communicate. rosdep still reports Nav2 and optional vendor GUI dependency missing | Partial; clean-OS/apt trial pending |
| 2: standard robot/manipulator | Official Waffle Pi base smoke passed. Course-owned attached OpenMANIPULATOR-X model passes base, arm and both-finger tests in an empty Harmonic world | Passed headless simulation |
| 3: custom assets/MS1 reference | House model/resources installed; preserved 107 collisions; house base and arm/gripper tests pass; standalone Trigger sequences succeed and reject overlap; inactive controller returns failure | Control passed; map localization pending |
| 4: MS2 | Pinned Fast Downward built; planning-only CLI runs without ROS sourcing; reachable transport/movement, already-satisfied, disconnected and error/timeout cases tested | Passed |
| 5: MS3 | Direct Nav2 client, immutable plan requests, atomic KB effects, failure/overlap/stale-plan tests implemented. Actual Nav2/localization/transport not run | Blocked on system dependencies; not accepted |

## What actually ran

- `bash scripts/init_jazzy.sh`: all four pinned source revisions matched; vendor checkouts have no patches. [Record](evidence/pinned_sources.txt).
- `bash scripts/build_jazzy.sh`: four vendor packages then two project packages built. Final project rebuild: [log](evidence/course_build.txt); initial vendor build: [summary](evidence/vendor_build.txt). CMake emitted compatibility/deprecation notices for upstream minimum versions, not build errors.
- `demo_nodes_cpp talker` with `demo_nodes_py listener`: [matching messages](evidence/ros_communication.txt).
- `ros2 launch turtlebot3_gazebo empty_world.launch.py`, then `scripts/smoke_base.py`: 0.241 m odometry travel, 0.695 rad rotation, stopped velocity zero, 360 laser values, wheel joint states and clock. [Evidence](evidence/upstream_base.json).
- `ros2 launch tb3_course_sim sim.launch.py`: attached-model base test measured 0.285 m, 0.831 rad, and stopped; arm reach/home returned error_code 0; both fingers reached -0.01 and +0.01 m. [Base](evidence/combined_base.json), [manipulator](evidence/combined_manipulator.json), [actions](evidence/actions.txt).
- Migrated `gripper_control` with `smoke_gripper_services.py`: one overlapping request rejected as busy; successful complete sequences. [Service evidence](evidence/gripper_services.json).
- `smoke_gripper_failure.py`: deactivated gripper controller, received `success:false`, and restored controller activation. [Actual failure](evidence/gripper_failure.txt). Node requires restart/reconciliation after this intentional fault.
- `ros2 launch tb3_planner_execution gazebo.launch.py`: all four controllers active after the readiness fix. `smoke_base.py --ground-truth-world course` measured 0.292 m odometry versus 0.279 m actual Gazebo model displacement, 0.900 rad rotation, and stopped. [House base](evidence/house_base.json), [controllers](evidence/house_controllers.txt), [house arm/gripper](evidence/house_manipulator.json), [runtime excerpt](evidence/house_runtime_excerpt.txt).
- ROS graph audit: one publisher each for odometry, joints, clock and scan; diff-drive subscribes to `geometry_msgs/msg/TwistStamped`. [Graph](evidence/velocity_interface.txt).
- Fast Downward 24.06.1 built with `python3 .jazzy/downward/build.py release -j2`. Planning-only CLI also ran under `env -i` with no sourced ROS environment. [CLI output](evidence/planning_only_cli.txt).
- `python3 -m pytest -q tests`: **29 passed**, no skipped real-planner cases. Includes injected move/pick/place failures, no effects for failed actions, no continuation, duplicate/stale/overlapping plan rejection, journal write failure, controller rejection/status checks and timeout cancellation. [Summary](evidence/planner_executor_tests.txt).
- Python compile checks, shell syntax checks and `git diff --check` were run. These are static checks; they do not validate the unavailable Nav2 runtime.

Detailed machine and asset preservation evidence is in [inventory.json](evidence/inventory.json). Apt versions are in [installed_versions.tsv](../dependencies/installed_versions.tsv); upstream source and Fast Downward revisions are in the `.repos` manifests. Full local launch/build logs remain under `.jazzy/`.

## Fixes and decisions

- Kept all legacy vendor source directories and old build/install/log artifacts. The active build explicitly discovers only selected pinned Jazzy sources and course packages. `.vscode/settings.json` and original mutable planner KB/problem/plan edits were not changed by the migration; their bytes match the initial snapshots.
- Reused upstream Waffle Pi/OpenMANIPULATOR-X geometry. The manipulation Jazzy top-level simulation still references Classic, so project-owned `tb3_course_sim` supplies Harmonic systems and gz_ros2_control. No vendor source patches were needed.
- Preserved the installed GripperCommand controller interface. Its deprecation warning is documented; it was not incorrectly treated as removed.
- Installed custom models recursively, changed Classic visual scripts to SDF colors, resolved nested furniture meshes/textures through pinned package resources, and embedded ground/light for the course world.
- House loading exposed a five-second controller activation timeout. Startup now activates all four controllers as a group with a 60-second switch deadline and shuts down on spawner failure. No fixed sleep is used for controller readiness.
- Slow rendering exposed a wall-time motion-test assumption. Motion durations now use simulation time with a separate wall-time timeout.
- Corrected map-frame position handling, centralized room coordinates, removed hidden coordinate additions, and explicitly forward map/params/time in navigation launch. Map offset remains provisional until AMCL validation.
- Separated ROS-free planning from ROS execution. Each plan has isolated output, a UUID and a validated initial state. The legacy KB update service is retired; the executor alone writes confirmed effects.
- Gripper/arm clients check acceptance, status and result, cancel timed-out goals, serialize sequences and latch failures. Execution preserves already-confirmed effects, rejects uncertain-state resumes, and never treats disabled manipulation as success.

## Remaining work before student release

1. When system installation is available, run `bash scripts/install_jazzy_dependencies.sh`. Current [rosdep result](evidence/rosdep_check.txt) lists `ros-jazzy-nav2-msgs`, `ros-jazzy-nav2-bringup`, `ros-jazzy-navigation2`, and `ros-jazzy-joint-state-publisher-gui`. [Navigation launch failure](evidence/navigation_blocker.txt) confirms `nav2_bringup` is absent. Record the installed Nav2 versions and rerun rosdep check.
2. Follow the entire [MS3 sequence](ms3_integration.md): verify AMCL laser/map alignment, `map -> odom -> base_footprint`, stamped velocity chain, footprint and one room goal. Only then validate full transport and real navigation/manipulation failure injection with final KB evidence.
3. Resolve map alignment: supplied map/image are unchanged. The explicit legacy offset `[2.0,0.5]` is supported approximately by wall fitting, but is **not verified by localization**. [Fit](evidence/map_alignment.json). Adjust configuration or regenerate a map only after observing actual alignment; keep room semantics consistent.
4. Run [setup](setup_jazzy.md) on a fresh Ubuntu 24.04 machine. Existing apt packages on this TA machine are not evidence of a fresh install. ARM64, GUI appearance, physical hardware and passive mechanical mimic behavior remain unverified.
5. Share the local `jazzy` branch with students only after the remaining acceptance gates pass. No remote push or publication was performed.

Gazebo emitted EGL fallback warnings while producing scan data, and DART reported unsupported native mimic constraints. `gz_ros2_control` applies the mimic relation and both simulated finger positions passed. There were no unresolved furniture texture lookup errors in the final house startup. Physical object grasp/attachment was never claimed: pick/place remains the documented symbolic/controller abstraction.

Student challenges and concrete troubleshooting are maintained in [setup](setup_jazzy.md#student-troubleshooting-record); student work is separately scoped in [MS1](ms1_robot_control.md), [MS2](ms2_task_planning.md), [MS3](ms3_integration.md), and [the scaffold](../student_scaffold/README.md).

## Upstream references inspected

- [Official Jazzy installation source](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Installation/Ubuntu-Install-Debs.rst) and its apt repository setup include.
- [ROBOTIS manipulation Jazzy](https://github.com/ROBOTIS-GIT/turtlebot3_manipulation/tree/jazzy) and all pinned vendor manifests/xacros; separate simulation repository branch list was checked with `git ls-remote`.
- [Jazzy gz_ros2_control](https://control.ros.org/jazzy/doc/gz_ros2_control/doc/index.html) and actual installed controller exports/interfaces.
- [Iron-to-Jazzy Nav2 migration](https://docs.nav2.org/jazzy/configuration_and_development/migration_guides/iron/Iron/), Jazzy navigation launch source and NavigateToPose action definition. The older Humble-to-Iron rendered documentation URL was unavailable during inspection; use the Jazzy baseline and complete runtime verification rather than claiming every intermediate configuration was tested.
- [Fast Downward planner usage](https://www.fast-downward.org/latest/documentation/planner-usage/) and pinned driver exit-code definitions. Exit 12 means incomplete search, not certified unsolvability; the disconnected acceptance problem returned that code with this search/version.
