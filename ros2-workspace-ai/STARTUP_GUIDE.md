# Complete System Startup Guide

## All Fixes Applied:

1. ✅ **KB updates correctly** in planner CLI after execution
2. ✅ **Robot spawns at livingroom** coordinates  
3. ✅ **Automatic initial pose** estimation (no manual RViz clicking)
4. ✅ **KB resets to initial state** with `reset_kb` command
5. ✅ **Robot localization** updates KB based on actual position

---

## Complete Startup Procedure (Correct Order)

### Terminal 1: Start Gazebo with Robot at Livingroom
```bash
cd ~/AI-For-Robotics/ros2-workspace-ai
source install/setup.bash
export TURTLEBOT3_MODEL=waffle_pi

# Option A: Use standard launch (robot spawns at origin)
ros2 launch turtlebot3_manipulation_gazebo gazebo.launch.py

# Option B: Use custom launch (robot spawns at livingroom) - RECOMMENDED
ros2 launch tb3_planner_execution gazebo_spawn_livingroom.launch.py
```

### Terminal 2: Start Nav2 Navigation Stack
```bash
cd ~/AI-For-Robotics/ros2-workspace-ai
source install/setup.bash
export TURTLEBOT3_MODEL=waffle_pi

ros2 launch turtlebot3_navigation2 navigation2.launch.py \
    use_sim_time:=True \
    map:=$HOME/AI-For-Robotics/ros2-workspace-ai/src/tb3_planner_execution/maps/map.yaml
```

Wait for Nav2 to show **"Creating bond timer..."** messages (means it's ready).

### Terminal 3: Auto Initialize Robot Pose (NEW!)
```bash
cd ~/AI-For-Robotics/ros2-workspace-ai
source install/setup.bash

# This automatically sets initial pose - no more manual clicking!
ros2 run tb3_planner_execution auto_initial_pose
```

You should see:
```
[INFO] [auto_initial_pose_node]: Published initial pose: x=-2.60, y=2.30, yaw=0.00
[INFO] [auto_initial_pose_node]: Localization should now be initialized!
```

**Check in RViz**: You should see the robot's particle cloud appear at the correct location.

### Terminal 4: Initialize KB with Robot's Actual Location (OPTIONAL)
```bash
cd ~/AI-For-Robotics/ros2-workspace-ai
source install/setup.bash

# This reads robot's odometry and updates KB to match
ros2 run tb3_planner_execution robot_localization
```

You should see:
```
[INFO] [robot_localization_node]: Robot detected at position: x=-2.60, y=2.30
[INFO] [robot_localization_node]: Closest room: livingroom
[INFO] [robot_localization_node]: Updated KB: robot_location changed from "bedroom" to "livingroom"
```

**Alternative**: In planner CLI, just type `reset_kb` to set KB to default state.

### Terminal 5: Start TurtleBotMove Node
```bash
cd ~/AI-For-Robotics/ros2-workspace-ai
source install/setup.bash

ros2 run tb3_planner_execution turtlebot_move
```

### Terminal 6: Start Plan Executor
```bash
cd ~/AI-For-Robotics/ros2-workspace-ai
source install/setup.bash

ros2 run tb3_planner_execution planner_executor
```

### Terminal 7: Start Planner CLI
```bash
cd ~/AI-For-Robotics/ros2-workspace-ai
source install/setup.bash

python3 planner/planner_cli.py
```

---

## Using the System

### First Time / After Restart:

1. **Reset KB to match robot spawn**:
   ```
   reset_kb
   ```
   This sets robot_location to "livingroom" and resets all objects.

2. **Give a goal**:
   ```
   robot-at diningroom
   ```

3. **Wait for execution**:
   - Planner CLI will show ">>> Waiting for execution to complete..."
   - Robot will navigate in Gazebo
   - When complete, you'll see ">>> Execution complete! KB has been reloaded."
   - KB will automatically update to show robot at "diningroom"

4. **Give another goal**:
   ```
   robot-at bedroom
   ```
   - Plan will start from "diningroom" (the updated location!)
   - KB updates again after execution

### Available Commands in Planner CLI:

- `robot-at ROOM` - Move robot to room
- `in-room OBJ ROOM` - Move object to room (pick and place)
- `holding OBJ` - Pick up object
- `reset_kb` - Reset KB to initial state
- `help` - Show commands
- `quit` - Exit

---

## Troubleshooting

### Robot Spawns Outside the House
**Solution**: Use the custom launch file:
```bash
ros2 launch tb3_planner_execution gazebo_spawn_livingroom.launch.py
```

### "Goal was REJECTED by Nav2!"
**Causes**:
1. Nav2 not fully started - wait for "Creating bond timer..." messages
2. Initial pose not set - run `auto_initial_pose` node
3. Robot not localized - check particle cloud in RViz

**Fix**:
```bash
# Terminal: Auto set initial pose
ros2 run tb3_planner_execution auto_initial_pose
```

### KB Doesn't Update in Planner CLI
**Old behavior** (FIXED): KB stayed at old location
**New behavior**: Planner CLI now **waits** for execution to complete and **automatically reloads** KB

You should see:
```
>>> Waiting for execution to complete...
>>> Execution complete! KB has been reloaded.

=== Current KB ===
Robot at: diningroom  ← UPDATED!
```

### Robot Starts at Wrong Location in KB
**Solution 1** - Reset manually:
```
reset_kb
```

**Solution 2** - Auto-detect from odometry:
```bash
ros2 run tb3_planner_execution robot_localization
```

---

## Room Coordinates Reference

For reference, the room coordinates are:
- **livingroom**: (-2.6, 2.3)
- **diningroom**: (5.5, 5.0)
- **studyroom**: (-6.0, 2.9)
- **bedroom**: (-6.3, -1.5)
- **storageroom**: (1.2, 3.2)
- **bathroom**: (6.2, -1.6)

---

## Quick Start (All-in-One)

```bash
# Terminal 1
ros2 launch tb3_planner_execution gazebo_spawn_livingroom.launch.py

# Terminal 2  
ros2 launch turtlebot3_navigation2 navigation2.launch.py use_sim_time:=True map:=~/AI-For-Robotics/ros2-workspace-ai/src/tb3_planner_execution/maps/map.yaml

# Terminal 3 (wait for Nav2 "bond timer" message)
ros2 run tb3_planner_execution auto_initial_pose

# Terminal 4
ros2 run tb3_planner_execution turtlebot_move

# Terminal 5
ros2 run tb3_planner_execution planner_executor

# Terminal 6
python3 planner/planner_cli.py
# Then type: reset_kb
# Then: robot-at diningroom
```

---

## What Changed (Summary)

1. **Planner CLI** now calls `wait_for_completion()` and reloads KB after execution
2. **KB reset command** added: `reset_kb`
3. **Auto initial pose** node eliminates manual RViz clicking
4. **Custom Gazebo launch** spawns robot at livingroom
5. **Robot localization** node auto-detects room from odometry

Everything should work smoothly now! 🎉
