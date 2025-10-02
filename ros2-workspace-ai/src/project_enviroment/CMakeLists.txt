cmake_minimum_required(VERSION 3.5)
project(project_enviroment)

# Find dependencies
find_package(ament_cmake REQUIRED)

# Install the config directory
install(
    DIRECTORY config
    DESTINATION share/${PROJECT_NAME}
)

# Install the launch directory
install(
    DIRECTORY launch
    DESTINATION share/${PROJECT_NAME}
)

install(
    DIRECTORY worlds
    DESTINATION share/${PROJECT_NAME}
)

ament_package()