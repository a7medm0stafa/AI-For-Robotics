"""Harmonic mobile manipulator; defaults to an offline, empty smoke-test world."""
from pathlib import Path
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, AppendEnvironmentVariable, RegisterEventHandler, EmitEvent
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro


def start(context):
    share = Path(get_package_share_directory('tb3_course_sim'))
    vendor = Path(get_package_share_directory('turtlebot3_manipulation_description'))
    value = lambda name: LaunchConfiguration(name).perform(context)
    sim_time = value('use_sim_time').lower() == 'true'
    description = xacro.process_file(str(share / 'urdf/mobile_manipulator.urdf.xacro')).toxml()
    args = '-r -v 2 ' + ('-s --headless-rendering ' if value('gui').lower() != 'true' else '')
    # gz_args is shell-split by upstream launch; quote world paths containing spaces.
    import shlex
    args += shlex.quote(value('world'))
    actions = [
        AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH', str(vendor.parent)),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(Path(get_package_share_directory('ros_gz_sim')) / 'launch/gz_sim.launch.py')),
                                 launch_arguments={'gz_args': args, 'on_exit_shutdown': 'true'}.items()),
        Node(package='robot_state_publisher', executable='robot_state_publisher', parameters=[{'robot_description': description, 'use_sim_time': sim_time}]),
        Node(package='ros_gz_sim', executable='create', arguments=['-name', value('robot_name'), '-topic', '/robot_description', '-x', value('x'), '-y', value('y'), '-z', '0.02', '-Y', value('yaw')]),
        Node(package='ros_gz_bridge', executable='parameter_bridge', parameters=[{'config_file': str(share / 'config/bridge.yaml'), 'use_sim_time': sim_time}]),
    ]
    spawner = Node(package='controller_manager', executable='spawner',
                   arguments=['joint_state_broadcaster', 'diff_drive_controller', 'arm_controller', 'gripper_controller',
                              '-c', '/controller_manager', '--controller-manager-timeout', '90',
                              '--switch-timeout', '60', '--service-call-timeout', '90', '--activate-as-group'],
                   parameters=[{'use_sim_time': sim_time}])
    def check_spawner(event, context):
        if event.returncode != 0:
            return [EmitEvent(event=Shutdown(reason='Controller activation failed; inspect simulator log'))]
        return []
    actions += [RegisterEventHandler(OnProcessExit(target_action=spawner, on_exit=check_spawner)), spawner]
    return actions


def generate_launch_description():
    share = Path(get_package_share_directory('tb3_course_sim'))
    defaults = dict(world=str(share / 'worlds/empty.sdf'), gui='false', use_sim_time='true', x='0', y='0', yaw='0', robot_name='tb3_course')
    return LaunchDescription([DeclareLaunchArgument(k, default_value=v) for k, v in defaults.items()] + [OpaqueFunction(function=start)])
