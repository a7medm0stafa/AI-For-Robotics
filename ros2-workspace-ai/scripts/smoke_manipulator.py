#!/usr/bin/env python3
"""Exercise the attached arm and both fingers; require controller and joint feedback."""
import json
import time
import rclpy
from rclpy.action import ActionClient
from rclpy.qos import qos_profile_sensor_data
from control_msgs.action import FollowJointTrajectory, GripperCommand
from trajectory_msgs.msg import JointTrajectoryPoint
from sensor_msgs.msg import JointState

rclpy.init()
n = rclpy.create_node('manipulator_smoke_test', parameter_overrides=[rclpy.Parameter('use_sim_time', value=True)])
joints = {}
n.create_subscription(JointState, '/joint_states', lambda m: joints.update(zip(m.name, m.position)), qos_profile_sensor_data)
report = []
def result(client, goal):
    assert client.wait_for_server(timeout_sec=30), 'Controller unavailable'
    future = client.send_goal_async(goal)
    rclpy.spin_until_future_complete(n, future, timeout_sec=10)
    assert future.done(), 'Goal acknowledgement timed out'
    handle = future.result()
    assert handle.accepted, 'Goal rejected'
    future = handle.get_result_async()
    rclpy.spin_until_future_complete(n, future, timeout_sec=20)
    if not future.done():
        handle.cancel_goal_async()
        raise RuntimeError('Controller timed out')
    response = future.result()
    assert response.status == 4, response
    return response.result
try:
    arm = ActionClient(n, FollowJointTrajectory, '/arm_controller/follow_joint_trajectory')
    grip = ActionClient(n, GripperCommand, '/gripper_controller/gripper_cmd')
    for target in [[0., 0.3, 0.5, 0.5], [0., 0., 0., -0.1]]:
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = ['joint1', 'joint2', 'joint3', 'joint4']
        point = JointTrajectoryPoint(positions=target, velocities=[0.]*4)
        point.time_from_start.sec = 2
        goal.trajectory.points = [point]
        answer = result(arm, goal)
        assert answer.error_code == 0, answer
        report.append(dict(arm_target=target, error_code=answer.error_code))
    for target in [-0.01, 0.01]:
        goal = GripperCommand.Goal()
        goal.command.position = target
        goal.command.max_effort = 1.0
        answer = result(grip, goal)
        assert answer.reached_goal and not answer.stalled, answer
        end = time.monotonic()+1
        while time.monotonic()<end:
            rclpy.spin_once(n, timeout_sec=0.05)
        measured = [joints[name] for name in ['gripper_left_joint', 'gripper_right_joint']]
        assert all(abs(p-target)<0.002 for p in measured), measured
        report.append(dict(gripper_target=target, measured=measured, reached_goal=answer.reached_goal))
    print(json.dumps(report, indent=2))
finally:
    n.destroy_node()
    rclpy.shutdown()
