"""Optional combined course simulator and navigation launch."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    share = Path(get_package_share_directory('tb3_planner_execution'))
    defaults = dict(world=str(share/'worlds/my_house.world'), map=str(share/'maps/map.yaml'), params_file=str(share/'config/nav2_params.yaml'), use_sim_time='true', gui='false', x='-2.65', y='1.0', yaw='0.0')
    actions = [DeclareLaunchArgument(k, default_value=v) for k,v in defaults.items()]
    for file, keys in [('gazebo.launch.py',['world','use_sim_time','gui','x','y','yaw']),('navigation.launch.py',['map','params_file','use_sim_time'])]:
        actions.append(IncludeLaunchDescription(PythonLaunchDescriptionSource(str(share/'launch'/file)), launch_arguments={k:LaunchConfiguration(k) for k in keys}.items()))
    return LaunchDescription(actions)
