import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'project_enviroment'

# This function is needed to recursively find all files in the asset directories
def package_files(data_files, directory_list):
    paths_dict = {}
    for directory in directory_list:
        for (path, directories, filenames) in os.walk(directory):
            for filename in filenames:
                file_path = os.path.join(path, filename)
                install_path = os.path.join('share', package_name, path)
                if install_path in paths_dict.keys():
                    paths_dict[install_path].append(file_path)
                else:
                    paths_dict[install_path] = [file_path]

    for key in paths_dict.keys():
        data_files.append((key, paths_dict[key]))

    return data_files

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    # This is the updated data_files section
    data_files=package_files(
        [
            ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
            ('share/' + package_name, ['package.xml']),
            # Add launch files
            (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
            # Add config directory
            (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        ],
        ['maps/', 'models/', 'worlds/'] # List of directories to install recursively
    ),
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ahmed',
    maintainer_email='ahm.mostafa03@gmail.com',
    description='A package for the project environment and simulation.',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [],
    },
)