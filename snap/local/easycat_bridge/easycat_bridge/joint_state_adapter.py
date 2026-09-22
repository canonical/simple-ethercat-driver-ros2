#!/usr/bin/env python3
"""Convert the EasyCAT GPIO state interfaces into two joint positions."""

from typing import Dict, Optional, Sequence

import rclpy
from control_msgs.msg import DynamicJointState
from rclpy.node import Node
from sensor_msgs.msg import JointState


EASYCAT_RESOURCE = "easycat"
INTERFACE_TO_JOINT = {
    "analog_input_0": "easycat_analog_0",
    "analog_input_1": "easycat_analog_1",
}


def extract_interface_values(
    message: DynamicJointState,
    resource_name: str,
    interface_names: Sequence[str],
) -> Optional[Dict[str, float]]:
    """Return selected values for one resource, or None if data is incomplete."""
    try:
        resource_index = message.joint_names.index(resource_name)
        resource_values = message.interface_values[resource_index]
    except (ValueError, IndexError):
        return None

    values_by_name = dict(zip(resource_values.interface_names, resource_values.values))
    if any(name not in values_by_name for name in interface_names):
        return None
    return {name: values_by_name[name] for name in interface_names}


class EasycatJointStateAdapter(Node):
    """Publish EasyCAT A0/A1 as separate entries on the public /joint_states topic."""

    def __init__(self) -> None:
        super().__init__("easycat_joint_state_adapter")
        self.declare_parameter(
            "input_topic", "/easycat_state_broadcaster/dynamic_joint_states"
        )
        input_topic = self.get_parameter("input_topic").value

        self._publisher = self.create_publisher(JointState, "/joint_states", 10)
        self._subscription = self.create_subscription(
            DynamicJointState, input_topic, self._on_dynamic_joint_state, 10
        )
        self._reported_missing_data = False
        self.get_logger().info(
            f"Converting {input_topic} EasyCAT analog interfaces to /joint_states"
        )

    def _on_dynamic_joint_state(self, message: DynamicJointState) -> None:
        interface_names = tuple(INTERFACE_TO_JOINT)
        values = extract_interface_values(message, EASYCAT_RESOURCE, interface_names)
        if values is None:
            if not self._reported_missing_data:
                self.get_logger().warning(
                    "Waiting for EasyCAT resource with analog_input_0 and analog_input_1"
                )
                self._reported_missing_data = True
            return

        self._reported_missing_data = False
        output = JointState()
        output.header = message.header
        output.name = [INTERFACE_TO_JOINT[name] for name in interface_names]
        output.position = [values[name] for name in interface_names]
        self._publisher.publish(output)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = EasycatJointStateAdapter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
