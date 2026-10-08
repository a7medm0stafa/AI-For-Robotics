"""Course map, Jazzy Nav2 parameters, and simulation time explicitly forwarded."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    course = Path(get_package_share_directory('tb3_planner_execution'))
    nav = Path(get_package_share_directory('nav2_bringup'))
    defaults = dict(map=str(course/'maps/map.yaml'), params_file=str(course/'config/nav2_params.yaml'), use_sim_time='true')
    return LaunchDescription([
        *[DeclareLaunchArgument(k, default_value=v) for k,v in defaults.items()],
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(nav/'launch/bringup_launch.py')),
                                 launch_arguments={**{k:LaunchConfiguration(k) for k in defaults}, 'autostart':'true', 'use_composition':'false'}.items()),
    ])
