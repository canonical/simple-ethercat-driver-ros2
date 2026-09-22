cmake_minimum_required(VERSION 3.16)
project(easycat_bridge)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(
  PROGRAMS easycat_bridge/joint_state_adapter.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME easycat_joint_state_adapter
)

install(
  PROGRAMS easycat_bridge/console_monitor.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME easycat_console_monitor
)

install(
  DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)

ament_package()