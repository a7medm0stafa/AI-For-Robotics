#!/usr/bin/env python3
"""Inject an inactive controller; restore it even when the assertion fails."""
import json
import subprocess
import rclpy
from std_srvs.srv import Trigger
rclpy.init()
n = rclpy.create_node('gripper_failure_smoke')
client = n.create_client(Trigger, 'close_gripper')
try:
    subprocess.run(['ros2','control','switch_controllers','--deactivate','gripper_controller'], check=True)
    assert client.wait_for_service(timeout_sec=10)
    future = client.call_async(Trigger.Request())
    rclpy.spin_until_future_complete(n, future, timeout_sec=90)
    assert future.done() and not future.result().success
    print(json.dumps(dict(success=future.result().success, message=future.result().message)))
finally:
    subprocess.run(['ros2','control','switch_controllers','--activate','gripper_controller'], check=True)
    n.destroy_node()
    rclpy.shutdown()
