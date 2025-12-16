# AI-For-Robotics

## Complete Pick-Place System with PDDL Planning

This project implements an autonomous pick-and-place system using TurtleBot3 with manipulation, featuring:
- PDDL-based task planning with Fast Downward
- Nav2 navigation
- Gripper control with arm movement
- Knowledge base persistence

## How to Run

### Terminal 1: Gazebo Simulation
```bash
cd ~/AI-For-Robotics/ros2-workspace-ai
source install/setup.bash
ros2 launch turtlebot3_manipulation_gazebo gazebo.launch.py
```

### Terminal 2: Nav2 Navigation
```bash
cd ~/AI-For-Robotics/ros2-workspace-ai
source install/setup.bash
# Option 1: Using absolute path
ros2 launch turtlebot3_navigation2 navigation2.launch.py use_sim_time:=True map:=$PWD/src/tb3_planner_execution/maps/map.yaml

# Option 2: Using relative path (must be in ros2-workspace-ai directory)
ros2 launch turtlebot3_navigation2 navigation2.launch.py use_sim_time:=True map:=$(pwd)/src/tb3_planner_execution/maps/map.yaml
```

**Note:** ROS2 launch files resolve paths from where you run the command, not from the package directory. Using `$PWD` or `$(pwd)` expands to the current directory, making it work regardless of your username.

### Terminal 3: Init Pose Node
```bash
cd ~/AI-For-Robotics/ros2-workspace-ai
source install/setup.bash
ros2 run tb3_planner_execution init_pose
```


### Terminal 4: TurtleBot Movement Node
```bash
cd ~/AI-For-Robotics/ros2-workspace-ai
source install/setup.bash
ros2 run tb3_planner_execution turtlebot_move
```


### Terminal 5: Gripper Control Node
```bash
cd ~/AI-For-Robotics/ros2-workspace-ai
source install/setup.bash
ros2 run tb3_planner_execution gripper_control
```
**Features:** 
- Pick sequence: Arm down → Close gripper → Arm up
- Place sequence: Arm down → Open gripper → Arm up

### Terminal 6: Plan Executor Node
```bash
cd ~/AI-For-Robotics/ros2-workspace-ai
source install/setup.bash
ros2 run tb3_planner_execution planner_executor --ros-args -p use_gripper:=true
```

### Terminal 7: Planner CLI
```bash
cd ~/AI-For-Robotics/ros2-workspace-ai
python3 planner/planner_cli.py
```

## Using the Planner CLI

The CLI accepts goal commands to plan and execute tasks:

### Available Commands:
- `robot-at ROOM` - Move robot to specified room
  - Example: `robot-at bedroom`
  
- `in-room OBJ ROOM` - Move object to specified room (pick and place)
  - Example: `in-room cup bedroom`
  
- `holding OBJ` - Pick up specified object
  - Example: `holding cup`

- `reset_kb` - Reset knowledge base to default state
- `help` - Show available commands
- `quit` - Exit the planner

### Example Session:
```
=== Current KB ===
Robot at: livingroom
Holding: None
Objects:
  cup: diningroom
  book: studyroom
  remote: livingroom
==================

Enter goal: in-room cup bedroom

Plan (Fast Downward):
 1. (move livingroom diningroom)
 2. (pick cup diningroom)
 3. (move diningroom bedroom)
 4. (place cup bedroom)

>>> Execution complete! KB has been reloaded.
```

## System Features

### Knowledge Base
- **Auto-reset on startup:** KB resets to default state when CLI starts
- **Persistent state:** KB saved to `planner/kb_state.json`
- **Tracks:** robot location, held object, gripper state, object locations

### Room Coordinates
- **Living Room:** (-2.65, 1.0)
- **Dining Room:** (4.8, 1.3)
- **Bedroom:** (-6.3, -0.45)
- **Study Room:** (-6.0, 3.0)
- **Bathroom:** (0.9, 3.2)
- **Storage Room:** (5.55, -2.8)

### Available Objects
- cup, book, remote, phone, panadol, pillow, chewy

## Technical Details

### Architecture
- **Planner:** Fast Downward (PDDL)
- **Navigation:** Nav2 with dynamic orientation
- **Manipulation:** Joint-space arm control + gripper
- **Execution:** Multi-threaded ROS2 nodes with callback groups

### Key Components
1. **planner_cli.py** - Interactive planning interface
2. **plan_executor_node.py** - Executes PDDL plans
3. **TurtleBotMove.py** - Handles navigation
4. **grip_ctrl.py** - Controls gripper and arm movements

## Troubleshooting

**Robot doesn't navigate:**
- Make sure you set the initial pose in RViz2 (step 3)
- Check that Nav2 shows the costmap properly

**Plan execution hangs:**
- Restart all nodes
- Check that all 7 terminals are running
- Verify gripper_control service is available: `ros2 service list | grep gripper`

**KB doesn't reset:**
- KB auto-resets when CLI starts
- Manually reset with `reset_kb` command

## Notes
- Robot spawns in living room at (-2.65, 1.0)
- Gripper must be in "open" state before picking
- All paths are relative to `ros2-workspace-ai` directory
- Use `$PWD` or `$(pwd)` for portable paths instead of hardcoded `/home/username/`

