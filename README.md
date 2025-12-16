# AI-For-Robotics
how to run:
1- spawn tb3 with manipulator in gazebo: 
ros2 launch turtlebot3_manipulation_gazebo gazebo.launch.py

2- launch Rviz2 node for nav2

ros2 launch turtlebot3_navigation2 navigation2.launch.py use_sim_time:=True map:=/home/ahmed/AI-For-Robotics/ros2-workspace-ai/src/tb3_planner_execution/maps/map.yaml

3-initialize robot pose from rviz2 place in origin of map 
ros2 run tb3_planner_execution set_init_pose

4- run turtlebotmove.py node 
ros2 run tb3_planner_execution turtlebot_move

5-run planner executor node 
ros2 run tb3_planner_execution planner_executor

6- run planner CLI 
python3 planner/planner_cli.py
    in the CLI give the robot desired tasks, 

