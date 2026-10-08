#!/usr/bin/env python3
"""Standalone MS1 service validation including rejection of overlapping sequences."""
import json
import rclpy
from std_srvs.srv import Trigger
rclpy.init()
node = rclpy.create_node('gripper_service_smoke')
results = []
try:
    clients = [node.create_client(Trigger, name) for name in ['close_gripper', 'open_gripper']]
    assert all(c.wait_for_service(timeout_sec=10) for c in clients)
    first = clients[0].call_async(Trigger.Request())
    overlap = clients[1].call_async(Trigger.Request())
    rclpy.spin_until_future_complete(node, overlap, timeout_sec=90)
    rclpy.spin_until_future_complete(node, first, timeout_sec=90)
    assert first.done() and overlap.done()
    answers = [first.result(), overlap.result()]
    assert sum(answer.success for answer in answers) == 1, answers
    assert any('busy' in answer.message for answer in answers), answers
    results.extend(dict(success=a.success, message=a.message) for a in answers)
    future = clients[1].call_async(Trigger.Request())
    rclpy.spin_until_future_complete(node, future, timeout_sec=90)
    assert future.done() and future.result().success
    results.append(dict(success=future.result().success, message=future.result().message))
    print(json.dumps(results, indent=2))
finally:
    node.destroy_node()
    rclpy.shutdown()
