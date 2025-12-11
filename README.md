# AI-For-Robotics
how to run:
1- spawn tb3 with manipulator in gazebo: 
ros2 launch turtlebot3_manipulation_gazebo gazebo.launch.py

2- launch Rviz2 node for nav2

ros2 launch turtlebot3_navigation2 navigation2.launch.py use_sim_time:=True map:=/home/ahmed/AI-For-Robotics/ros2-workspace-ai/src/tb3_planner_execution/maps/map.yaml

3-initialize robot pose from rviz2

4-set goal pose from rviz2