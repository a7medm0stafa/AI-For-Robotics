"""Canonical course house launch; all custom resources use installed package paths."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, AppendEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    course = Path(get_package_share_directory('tb3_planner_execution'))
    sim = Path(get_package_share_directory('tb3_course_sim'))
    vendor = Path(get_package_share_directory('turtlebot3_gazebo'))
    defaults = dict(world=str(course/'worlds/my_house.world'), gui='false', use_sim_time='true', x='-2.65', y='1.0', yaw='0.0', robot_name='tb3_course')
    return LaunchDescription([
        *[DeclareLaunchArgument(k, default_value=v) for k,v in defaults.items()],
        AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH', str(course/'models')),
        AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH', str(vendor/'models')),
        AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH', str(vendor/'models/turtlebot3_house/cafe_table/materials/textures')),
        AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH', str(vendor/'models/turtlebot3_house/table_marble/materials/textures')),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(sim/'launch/sim.launch.py')),
                                 launch_arguments={k:LaunchConfiguration(k) for k in defaults}.items()),
    ])
