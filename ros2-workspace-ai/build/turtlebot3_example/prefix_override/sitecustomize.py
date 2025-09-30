import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/ahmed/AI-For-Robotics/ros2-workspace-ai/install/turtlebot3_example'
