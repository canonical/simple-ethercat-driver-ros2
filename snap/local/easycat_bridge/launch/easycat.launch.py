"""Launch the EasyCAT EtherCAT hardware, broadcaster, and topic adapter."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import EmitEvent, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    package_share = get_package_share_directory("easycat_bridge")
    slave_config = os.path.join(package_share, "config", "easycat.yaml")
    controller_config = os.path.join(package_share, "config", "controllers.yaml")

    robot_description = f"""<?xml version=\"1.0\"?>
<robot name=\"easycat_bridge\">
  <link name=\"easycat_base\"/>
  <ros2_control name=\"EasycatEthercatSystem\" type=\"system\">
    <hardware>
      <plugin>ethercat_driver/EthercatDriver</plugin>
      <param name=\"master_id\">0</param>
      <param name=\"control_frequency\">100</param>
    </hardware>
    <gpio name=\"easycat\">
      <state_interface name=\"analog_input_0\"/>
      <state_interface name=\"analog_input_1\"/>
      <ec_module name=\"easycat_slave\">
        <plugin>ethercat_generic_plugins/GenericEcSlave</plugin>
        <param name=\"alias\">0</param>
        <param name=\"position\">0</param>
        <param name=\"slave_config\">{slave_config}</param>
      </ec_module>
    </gpio>
  </ros2_control>
</robot>
"""

    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[controller_config],
        output="screen",
    )

    return LaunchDescription(
        [
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                parameters=[{"robot_description": robot_description}],
                output="screen",
            ),
            control_node,
            RegisterEventHandler(
                OnProcessExit(
                    target_action=control_node,
                    on_exit=[
                        EmitEvent(
                            event=Shutdown(reason="controller manager stopped")
                        )
                    ],
                )
            ),
            Node(
                package="controller_manager",
                executable="spawner",
                arguments=[
                    "easycat_state_broadcaster",
                    "--controller-manager",
                    "/controller_manager",
                    "--controller-manager-timeout",
                    "30",
                    "--param-file",
                    controller_config,
                ],
                output="screen",
            ),
            Node(
                package="easycat_bridge",
                executable="easycat_joint_state_adapter",
                output="screen",
            ),
        ]
    )
