#!/usr/bin/env python3
"""Render EtherCAT analog joint states as a live terminal dashboard."""

import argparse
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Dict, Optional

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


JOINT_LABELS = {
    "easycat_analog_0": "A0",
    "easycat_analog_1": "A1",
}
ADC_MIN = 0.0
ADC_MAX = 255.0
BAR_WIDTH = 48


def values_by_joint(message: JointState) -> Dict[str, float]:
    """Return finite position values keyed by joint name."""
    values = {}
    for name, value in zip(message.name, message.position):
        if name in JOINT_LABELS and math.isfinite(value):
            values[name] = value
    return values


def render_bar(value: float) -> str:
    """Render an ADC value as a fixed-width text bar."""
    fraction = min(1.0, max(0.0, (value - ADC_MIN) / (ADC_MAX - ADC_MIN)))
    filled = round(fraction * BAR_WIDTH)
    return "█" * filled + "·" * (BAR_WIDTH - filled)


class EasycatConsoleMonitor(Node):
    """Subscribe to /joint_states and display A0/A1 at a readable rate."""

    def __init__(self, bridge_process: Optional[subprocess.Popen] = None) -> None:
        super().__init__("easycat_console_monitor")
        self._bridge_process = bridge_process
        self._started_at = time.monotonic()
        self._values: Dict[str, float] = {}
        self._last_message_at: Optional[float] = None
        self._interactive = sys.stdout.isatty()
        self._last_plain_output_at = 0.0
        self.create_subscription(JointState, "/joint_states", self._on_joint_state, 10)
        self.create_timer(0.1, self._render)
        if self._interactive:
            print("\033[2J\033[?25l", end="", flush=True)

    def destroy_node(self):
        if self._interactive:
            print("\033[?25h", end="", flush=True)
        return super().destroy_node()

    def _on_joint_state(self, message: JointState) -> None:
        current_values = values_by_joint(message)
        if len(current_values) == len(JOINT_LABELS):
            self._values = current_values
            self._last_message_at = time.monotonic()

    def _status(self) -> str:
        if self._bridge_process is not None and self._bridge_process.poll() is not None:
            return "BRIDGE STOPPED - CHECK LOG"
        if self._last_message_at is None:
            if time.monotonic() - self._started_at > 15.0:
                return "NO DATA - CHECK DEVICE/LOG"
            return "WAITING FOR ETHERCAT DATA"
        if time.monotonic() - self._last_message_at > 1.0:
            return "DATA STALE"
        return "LIVE"

    def _render(self) -> None:
        status = self._status()
        lines = [
            "╔════════════════════════════════════════════════════════════════╗",
            "║                   EtherCAT ROS 2 Bridge                        ║",
            "╠════════════════════════════════════════════════════════════════╣",
            f"║ Status: {status:<55}║",
        ]

        for joint_name, label in JOINT_LABELS.items():
            if joint_name in self._values:
                value = self._values[joint_name]
                lines.append(f"║ {label}: {value:6.1f}  [{render_bar(value)}] ║")
            else:
                lines.append(f"║ {label}: {'--.-':>6}  [{' ' * BAR_WIDTH}] ║")

        lines.extend(
            [
                "╠════════════════════════════════════════════════════════════════╣",
                "║ ROS topic: /joint_states    Range: 0–255    Ctrl-C to stop     ║",
                "╚════════════════════════════════════════════════════════════════╝",
            ]
        )
        output = "\n".join(lines)

        if self._interactive:
            print("\033[H" + output, end="", flush=True)
        elif time.monotonic() - self._last_plain_output_at >= 1.0:
            if self._values:
                print(
                    "EtherCAT ROS 2 Bridge LIVE | "
                    + " | ".join(
                        f"{JOINT_LABELS[name]}={self._values[name]:.1f}"
                        for name in JOINT_LABELS
                    ),
                    flush=True,
                )
            else:
                print(
                    "EtherCAT ROS 2 Bridge | waiting for /joint_states ...",
                    flush=True,
                )
            self._last_plain_output_at = time.monotonic()


def start_bridge() -> tuple[subprocess.Popen, object, Path]:
    """Start the bridge launch with output redirected to a persistent demo log."""
    data_directory = Path(os.environ.get("SNAP_USER_DATA", "/tmp"))
    data_directory.mkdir(parents=True, exist_ok=True)
    log_path = data_directory / "easycat-demo.log"
    log_stream = log_path.open("w", encoding="utf-8", buffering=1)
    process = subprocess.Popen(
        ["ros2", "launch", "easycat_bridge", "easycat.launch.py"],
        stdout=log_stream,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    return process, log_stream, log_path


def stop_bridge(process: subprocess.Popen) -> None:
    """Stop the complete launch process group, escalating only if needed."""
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGINT)
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def main(args=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--launch-bridge",
        action="store_true",
        help="start the packaged EtherCAT ROS 2 bridge and capture its logs",
    )
    parsed_args, ros_args = parser.parse_known_args(args)

    bridge_process = None
    bridge_log = None
    log_path = None
    if parsed_args.launch_bridge:
        bridge_process, bridge_log, log_path = start_bridge()

    rclpy.init(args=ros_args)
    node = EasycatConsoleMonitor(bridge_process)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
        if bridge_process is not None:
            stop_bridge(bridge_process)
        if bridge_log is not None:
            bridge_log.close()
        if log_path is not None:
            print(f"\nBridge log: {log_path}")


if __name__ == "__main__":
    main()
