from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'tb3_planner_execution'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Install launch files
        ('share/' + package_name + '/launch', [
            'launch/tb3_house_nav2.launch.py',
        ]),
        ('share/' + package_name + '/launch', [
            'launch/gazebo.launch.py',
        ]),
        ('share/' + package_name + '/launch', [
        'launch/base.launch.py',
        ]),
        # Install config files
        ('share/' + package_name + '/config', [
            'config/nav2_params.yaml',
        ]),
        # Install maps
        ('share/' + package_name + '/maps', glob('maps/*')),
        # Install worlds
        ('share/' + package_name + '/worlds', glob('worlds/*.world')),
        # Install models
        ('share/' + package_name + '/models/tb3_house_custom', 
            glob('models/tb3_house_custom/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ahmed',
    maintainer_email='ahm.mostafa03@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'planner_executor = tb3_planner_execution.plan_executor_node:main',
            'move_executor = tb3_planner_execution.move_executor_node:main',
            'manip_executor = tb3_planner_execution.manip_executor_node:main',
            'TurtleBotMove = tb3_planner_execution.TurtleBotMove:main',
        ],
    },
)
