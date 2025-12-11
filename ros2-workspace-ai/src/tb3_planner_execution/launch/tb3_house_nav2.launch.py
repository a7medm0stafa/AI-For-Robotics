#!/usr/bin/env python3
"""
Launch file for TurtleBot3 with manipulator in Gazebo + Nav2
Uses world and map from tb3_planner_execution package
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # Get package share directory
    pkg_share = get_package_share_directory('tb3_planner_execution')

    # Append this package's models directory to GAZEBO_MODEL_PATH
    # so Gazebo can find both custom models and standard models
    existing_gazebo_models = os.environ.get('GAZEBO_MODEL_PATH', '')
    models_path = os.path.join(pkg_share, 'models')
    if existing_gazebo_models:
        new_gazebo_models = f"{models_path}:{existing_gazebo_models}"
    else:
        new_gazebo_models = models_path
    
    set_gazebo_models = SetEnvironmentVariable(
        name='GAZEBO_MODEL_PATH',
        value=new_gazebo_models
    )

    # Declare launch arguments with defaults from this package
    world_arg = DeclareLaunchArgument(
        'world',
        default_value=PathJoinSubstitution([
            FindPackageShare('tb3_planner_execution'),
            'worlds',
            'my_house.world'
        ]),
        description='Path to Gazebo world file'
    )

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock'
    )

    map_arg = DeclareLaunchArgument(
        'map',
        default_value=os.path.join(pkg_share, 'maps', 'map.yaml'),
        description='Full path to map yaml file for Nav2'
    )

    params_arg = DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(pkg_share, 'config', 'nav2_params.yaml'),
        description='Full path to Nav2 parameters file'
    )

    start_rviz_arg = DeclareLaunchArgument(
        'start_rviz',
        default_value='true',
        description='Whether to start RViz2'
    )

    # Include Gazebo + TurtleBot3 manipulation system
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('turtlebot3_manipulation_gazebo'),
                'launch',
                'gazebo.launch.py'
            ])
        ]),
        launch_arguments={
            'world': LaunchConfiguration('world'),
            'start_rviz': LaunchConfiguration('start_rviz'),
        }.items()
    )

    # Include Nav2 bringup with your map
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('nav2_bringup'),
                'launch',
                'bringup_launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'map': LaunchConfiguration('map'),
            'params_file': LaunchConfiguration('params_file'),
        }.items()
    )

    # Static transform: odom -> base_footprint (simple identity transform)
    static_odom_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_odom_to_base',
        arguments=['0', '0', '0', '0', '0', '0', 'odom', 'base_footprint'],
        output='screen'
    )

    # Build launch description
    ld = LaunchDescription()

    # Add environment variable
    ld.add_action(set_gazebo_models)

    # Add arguments
    ld.add_action(world_arg)
    ld.add_action(use_sim_time_arg)
    ld.add_action(map_arg)
    ld.add_action(params_arg)
    ld.add_action(start_rviz_arg)

    # Add includes
    ld.add_action(gazebo_launch)
    ld.add_action(nav2_launch)

    # Add static transform node
    ld.add_action(static_odom_tf)

    return ld
