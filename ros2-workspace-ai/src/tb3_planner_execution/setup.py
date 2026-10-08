from setuptools import find_packages, setup
from glob import glob
from pathlib import Path

package_name = 'tb3_planner_execution'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.py')),
        ('share/' + package_name + '/worlds', glob('worlds/*.world')),
        ('share/' + package_name + '/maps', glob('maps/*')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
    ] + [(str(Path('share') / package_name / folder), [str(f) for f in Path(folder).iterdir() if f.is_file()])
         for folder in ['models'] + [str(d) for d in Path('models').rglob('*') if d.is_dir()]],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ahmed',
    maintainer_email='ahmed@todo.todo',
    description='TurtleBot3 Planner Execution Package',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'planner_executor = tb3_planner_execution.plan_executor_node:main',
            'turtlebot_move = tb3_planner_execution.TurtleBotMove:main',
            'gripper_control = tb3_planner_execution.grip_ctrl:main',
            'init_pose = tb3_planner_execution.init_pose:main',
        ],
    },
)

