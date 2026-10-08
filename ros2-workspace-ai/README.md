# AI for Robotics — Jazzy reference migration

Target: Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic, TurtleBot3 **Waffle Pi with OpenMANIPULATOR-X**. Work is on branch `jazzy`.

**Status:** the vendor base, combined robot, and migrated manipulation services run in simulation; MS2 and execution-state regression tests pass. **Nav2 and end-to-end MS3 are not validated:** the required Nav2 packages are absent on the validation machine and system installation was unavailable. Fresh-OS installation instructions also need a clean-machine trial. See [actual evidence and remaining gates](docs/jazzy_migration_status.md).

The implementations under `src/tb3_planner_execution/` and `planner/planner_cli.py` are **TA references**. Students implement the separately specified tasks in [MS1](docs/ms1_robot_control.md), [MS2](docs/ms2_task_planning.md), and [MS3](docs/ms3_integration.md), starting from [student scaffolds](student_scaffold/README.md).

## Initialize and build

Run from this `ros2-workspace-ai` directory. Start with [fresh Ubuntu setup](docs/setup_jazzy.md) if Jazzy is not installed.

```bash
bash scripts/init_jazzy.sh
bash scripts/install_jazzy_dependencies.sh  # needs sudo; completes rosdep dependencies
bash scripts/build_jazzy.sh
bash scripts/build_planner.sh
python3 -m pytest -q tests
```

`init_jazzy.sh` downloads pinned upstream sources into `.jazzy/vendor/src`. The build uses `.jazzy/build`, `.jazzy/install`, and `.jazzy/log`. Existing `src/` vendor copies and the old `build/`, `install/`, and `log/` remain legacy references. **Do not run an unqualified `colcon build` or source the old `install/setup.bash`.**

Every command below uses `scripts/jazzy_env.sh`, which clears inherited ROS overlays, sources `/opt/ros/jazzy/setup.bash` and the new local overlay, and selects `waffle_pi`. Use the same `ROS_DOMAIN_ID` in all terminals (default 73). The wrapper does not edit `.bashrc`.

## Tested standalone robot workflow

Terminal 1 — empty world, final combined model:

```bash
scripts/jazzy_env.sh ros2 launch tb3_course_sim sim.launch.py
```

Terminal 2 — verify feedback and controller results:

```bash
scripts/jazzy_env.sh python3 scripts/smoke_base.py
scripts/jazzy_env.sh python3 scripts/smoke_manipulator.py
scripts/jazzy_env.sh ros2 run tb3_planner_execution gripper_control --ros-args -p use_sim_time:=true
```

Terminal 3 — trigger complete arm/gripper sequences without a planner:

```bash
scripts/jazzy_env.sh ros2 service call close_gripper std_srvs/srv/Trigger '{}'
scripts/jazzy_env.sh ros2 service call open_gripper std_srvs/srv/Trigger '{}'
```

Stop the empty-world launch before starting the house. The canonical house command is:

```bash
scripts/jazzy_env.sh ros2 launch tb3_planner_execution gazebo.launch.py
```

Both launches default to headless rendering. `gui:=true` enables the GUI; visual inspection is a separate acceptance check. Pick/place means successful joint motions and symbolic object state, **not physical object attachment**.

## Planning without ROS or Gazebo

```bash
python3 planner/planner_cli.py --goal 'in-room cup bedroom'
python3 planner/planner_cli.py --goal 'robot-at livingroom'
```

No ROS imports occur in this mode. Each run gets a new `.jazzy/plans/plan-*/` directory. Planning never updates the KB. `--planner`, `--output-dir`, `--timeout`, and `--kb` are configurable.

## MS3 launch order — pending Nav2 validation

The complete terminal sequence and failure tests are in [MS3 integration](docs/ms3_integration.md). It requires installation of the missing dependencies and confirmation of map alignment before acceptance. Do not interpret the supplied launch files as evidence of a successful transport run.

Preserved historical instructions are in [the Humble README](docs/legacy/README_humble.md); their launch commands are not the Jazzy workflow. Local pre-migration KB/problem/plan copies and the initial diff are preserved in `.jazzy/snapshots/`.
