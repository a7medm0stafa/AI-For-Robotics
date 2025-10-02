import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    # Declare launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    map_dir = LaunchConfiguration(
        'map',
        default=os.path.join(
            get_package_share_directory('project_enviroment'),
            'maps',
            'map.yaml'))
    
    # Get the share directories for other packages
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    
    # use turtlebot with manipulator
    turtlebot3_manipulation_gazebo_dir = get_package_share_directory('turtlebot3_manipulation_gazebo')

    # Set the TURTLEBOT3_MODEL environment variable
    # This is crucial for the TurtleBot3 simulation packages
    os.environ['TURTLEBOT3_MODEL'] = 'waffle_pi'

    # The main Gazebo launch file for the house world with the manipulator
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(turtlebot3_manipulation_gazebo_dir, 'launch', 'gazebo.launch.py')
        ),
        # Pass the correct argument name 'world' to specify the world file
        launch_arguments={'world': os.path.join(
            turtlebot3_manipulation_gazebo_dir,
            'worlds',
            'my_house.world'
        )}.items()
    )

    # Launch Nav2 with the provided map
    nav2_bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'map': map_dir,
            'use_sim_time': use_sim_time,
            'params_file': os.path.join(
                get_package_share_directory('project_enviroment'),
                'config',
                'nav2_params.yaml')
        }.items()
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true', description='Use simulation (Gazebo) clock'),
        DeclareLaunchArgument('map', default_value=map_dir, description='Full path to map file to load'),
        
        gazebo_launch,
        nav2_bringup_launch,
    ])