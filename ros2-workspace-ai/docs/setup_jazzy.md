# Setup from Ubuntu 24.04

This is the primary simulation path for amd64 Ubuntu 24.04 (Python 3.12). Jazzy also publishes arm64 packages; this project has only been exercised on amd64. Read the [migration status](jazzy_migration_status.md): the clean build and simulations were run on an existing Jazzy machine, **not a fresh OS**, and apt installation plus Nav2 validation remain pending.

## 1. Install ROS and development tools

Use a fresh terminal without a Humble overlay. Check `cat /etc/os-release` and `uname -m`. Follow the [official Jazzy deb installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html); its [official source](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Installation/Ubuntu-Install-Debs.rst) is accessible if the rendered page blocks requests.

```bash
sudo apt update
sudo apt install locales software-properties-common curl python3
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
sudo add-apt-repository universe
```

Check `/etc/apt/sources.list.d/ubuntu.sources`: the main Ubuntu suite should include `noble noble-updates noble-backports`, plus the usual security entry. Apply normal OS updates before ROS installation. Configure the ROS repository and key using the official `ros2-apt-source` package:

```bash
ROS_APT_SOURCE_VERSION="$(curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"])')"
curl -fL -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.noble_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb
sudo apt update
sudo apt install ros-jazzy-desktop ros-dev-tools python3-vcstool python3-pytest build-essential cmake git
source /opt/ros/jazzy/setup.bash
```

The repository package maintains its key/configuration. Do not add a second ROS apt source if one already exists. This setup does not modify `.bashrc`; source explicitly in each ordinary terminal.

Verify ROS communication in two terminals, sourcing Jazzy in both:

```bash
ros2 run demo_nodes_cpp talker
# second terminal:
ros2 run demo_nodes_py listener
```

Expected: publishing messages and matching `I heard` messages. Stop both with Ctrl+C. The migration machine passed this test; evidence is [here](evidence/ros_communication.txt).

## 2. Obtain and initialize this workspace

Obtain the TA's `jazzy` branch of the project and enter its `ros2-workspace-ai` directory. The local migration branch must be shared/published by the TA before students can clone it from a remote; this migration does not publish the branch.

```bash
bash scripts/init_jazzy.sh
bash scripts/install_jazzy_dependencies.sh
```

The first command imports exact commits from `dependencies/jazzy.repos` and rejects an existing checkout with unexpected revisions or edits. The second installs Harmonic integration, controller plugins and Nav2, initializes rosdep only when needed, updates its database, and resolves the selected simulation manifests. It requires sudo. It does not install Gazebo Classic. Read [dependency ownership](../dependencies/README.md) before adding packages.

`rosdep` warnings about deprecated `pkg_resources` were observed but are not dependency-resolution failures. Resolve actual missing dependencies before MS3. On the validation machine these were `ros-jazzy-nav2-msgs`, `ros-jazzy-nav2-bringup`, `ros-jazzy-navigation2`, and the vendor description's `ros-jazzy-joint-state-publisher-gui`. The latter is not used by the headless launch, but is still an upstream manifest dependency.

## 3. Build and source only Jazzy

```bash
bash scripts/build_jazzy.sh
scripts/jazzy_env.sh ros2 pkg prefix turtlebot3_gazebo
scripts/jazzy_env.sh ros2 pkg prefix turtlebot3_manipulation_description
scripts/jazzy_env.sh ros2 pkg prefix tb3_course_sim
scripts/jazzy_env.sh printenv AMENT_PREFIX_PATH
```

Prefixes must resolve beneath this workspace's `.jazzy/install` for those three packages. No `/opt/ros/humble`, legacy `install/`, or unrelated workspace should occur in the active environment. `jazzy_env.sh` starts a clean environment, sources Jazzy and `.jazzy/install/local_setup.bash`, sets `TURTLEBOT3_MODEL=waffle_pi`, and defaults to domain 73. Every course terminal uses this wrapper. To get an interactive clean shell, use `scripts/jazzy_env.sh bash --noprofile --norc`.

Never recursively build the legacy `src/` tree. The script first builds four vendor simulation packages, then the two course packages, in separate Jazzy artifact directories. SDK/hardware and MoveIt are not needed for the joint-space simulation path.

## 4. Standard base, then attached arm

Start the official base example:

```bash
scripts/jazzy_env.sh ros2 launch turtlebot3_gazebo empty_world.launch.py
# another terminal:
scripts/jazzy_env.sh python3 scripts/smoke_base.py
```

This upstream example opens Gazebo and may fetch ground/sun resources from Fuel. It was exercised successfully here. Stop it before the combined example:

```bash
scripts/jazzy_env.sh ros2 launch tb3_course_sim sim.launch.py
# another terminal:
scripts/jazzy_env.sh python3 scripts/smoke_base.py
scripts/jazzy_env.sh python3 scripts/smoke_manipulator.py
```

The course empty world embeds ground/light and uses installed meshes. It starts headless by default. `gui:=true` opens a GUI; visual inspection must be recorded separately. Tests command motion, assert odometry displacement/rotation/stopping, observe clock/scan/joints, check action acceptance/status/error codes and check both finger positions. Do not run motion smoke tests during autonomous navigation. Restart the simulator after tests to return to the defined initial pose.

Diagnostic commands:

```bash
scripts/jazzy_env.sh ros2 control list_controllers
scripts/jazzy_env.sh ros2 action list -t
scripts/jazzy_env.sh ros2 topic info /cmd_vel -v
scripts/jazzy_env.sh ros2 topic echo /scan --once --qos-reliability best_effort
scripts/jazzy_env.sh ros2 run tf2_ros tf2_echo odom base_footprint
```

Expected: four active controllers; FollowJointTrajectory and GripperCommand actions; `TwistStamped` commands; 360 laser samples; changing odometry TF during movement. Clock and scan use `ros_gz_bridge`. ROS controllers already supply odometry/joints/TF: do not bridge second copies.

## 5. Course world and remaining acceptance

```bash
scripts/jazzy_env.sh ros2 launch tb3_planner_execution gazebo.launch.py
```

The canonical spawn is world `(-2.65, 1.0, yaw=0)`. Follow [MS1](ms1_robot_control.md) and [MS2](ms2_task_planning.md) independently, then [MS3](ms3_integration.md) after Nav2 installation and map verification.

## Student troubleshooting record

| Symptom | Cause / response |
|---|---|
| Wrong package or Python ABI errors | A shell sourced Humble or another overlay. Use the clean wrapper; never reuse legacy build/install. |
| Duplicate package names during build | Recursive discovery found the legacy vendors. Use `build_jazzy.sh` and its explicit base paths. |
| Manipulation Jazzy example asks for Classic libraries | The upstream branch still contains Classic launch/xacro integration. Use `tb3_course_sim`; this is TA infrastructure. |
| Robot visible but wheel controller inactive | Large scene startup exceeded the default controller switch timeout. Course startup uses a 60-second group activation wait and fails clearly on spawner failure. Inspect logs instead of adding fixed sleeps. |
| Motion topic exists but robot does not move | Check all publishers/subscribers use `TwistStamped`; publish current simulation timestamps and check controller activation. |
| Motion test is too short in a heavy house | Measure the commanded duration in simulation time, with a separate wall-clock deadline; do not assume real-time rendering. |
| Scan never arrives | Check headless rendering/GPU support, `/clock`, bridge topic and sensor QoS. This machine emitted EGL fallback warnings but produced scans. |
| Arm/gripper hangs | Callback starvation, paused simulation, unavailable controller, or rejected action. TA nodes have bounded waits, a multithreaded executor and sequence lock. |
| “Manipulator busy” | A sequence is running; overlapping requests are deliberately rejected. |
| Gripper deprecation warning | Installed legacy GripperCommand controller still works; changing controller requires changing its action client. |
| Planner seems to reuse an old result | Every run must use its own output directory; inspect its planner log and exit code. |
| Room goal displaced from the house | World and map frames differ. The explicit provisional transform is in `rooms.yaml`; verify with localization. |
| KB says robot moved after a failed request | Only successful actions may commit effects. Run the regression tests; reconcile physical state after any timeout. |

Gazebo DART reports that native mimic constraints are unsupported. The installed `gz_ros2_control` plugin applies the URDF mimic relationship, and both finger positions were measured successfully; a passive physical mimic mechanism is not validated.

No physical robot, perception system, autonomous grasp planner, or object-attachment plugin is part of this setup.
