#!/usr/bin/env python3
"""Verify ROS communication and feedback from a running base in an empty world."""
import argparse
import re
import subprocess
import json
import math
import time
import rclpy
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState, LaserScan
from rosgraph_msgs.msg import Clock

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--ground-truth-world')
parser.add_argument('--robot-name', default='tb3_course')
args = parser.parse_args()
def ground_truth():
    output = subprocess.check_output(['gz', 'topic', '-e', '-t', '/world/'+args.ground_truth_world+'/pose/info', '-n', '1'], text=True, timeout=15)
    match = re.search(r'name: "'+re.escape(args.robot_name)+r'"\s+id: \d+\s+position \{([^}]+)\}', output)
    if match is None:
        raise RuntimeError('Robot pose missing from Gazebo ground truth')
    xyz = {k:float(v) for k,v in re.findall(r'([xyz]): ([-+0-9.eE]+)', match.group(1))}
    return xyz.get('x',0.0), xyz.get('y',0.0)
rclpy.init()
node = rclpy.create_node('base_smoke_test', parameter_overrides=[rclpy.Parameter('use_sim_time', value=True)])
seen = {}
for topic, cls in [('odom', Odometry), ('joint_states', JointState), ('scan', LaserScan), ('clock', Clock)]:
    node.create_subscription(cls, topic, lambda msg, t=topic: seen.update({t: msg}), qos_profile_sensor_data)
pub = node.create_publisher(TwistStamped, 'cmd_vel', 10)
def spin_until(predicate, timeout=45):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.05)
        if predicate():
            return
    raise RuntimeError(f'Timeout; topics received: {list(seen)}')
def command(linear, angular, duration):
    end = node.get_clock().now().nanoseconds + int(duration*1e9)
    wall_deadline = time.monotonic() + max(30, duration*30)
    while node.get_clock().now().nanoseconds < end:
        if time.monotonic() > wall_deadline:
            raise RuntimeError('Simulation clock stalled or too slow')
        msg = TwistStamped()
        msg.header.stamp = node.get_clock().now().to_msg()
        msg.twist.linear.x = linear
        msg.twist.angular.z = angular
        pub.publish(msg)
        rclpy.spin_once(node, timeout_sec=0.05)
def yaw():
    q = seen['odom'].pose.pose.orientation
    return math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
try:
    spin_until(lambda: len(seen) == 4 and pub.get_subscription_count() > 0 and node.get_clock().now().nanoseconds > 0)
    truth_start = ground_truth() if args.ground_truth_world else None
    p = seen['odom'].pose.pose.position
    start = (p.x, p.y)
    command(0.1, 0., 3.)
    command(0., 0., 1.)
    p = seen['odom'].pose.pose.position
    distance = math.hypot(p.x-start[0], p.y-start[1])
    before = yaw()
    command(0., 0.3, 3.)
    command(0., 0., 1.)
    angle = abs(math.atan2(math.sin(yaw()-before), math.cos(yaw()-before)))
    velocity = seen['odom'].twist.twist
    report = dict(distance_m=distance, rotation_rad=angle, stopped_linear=velocity.linear.x,
                  stopped_angular=velocity.angular.z, laser_samples=len(seen['scan'].ranges),
                  joint_names=list(seen['joint_states'].name), clock_sec=seen['clock'].clock.sec)
    if truth_start is not None:
        truth_end = ground_truth()
        report['gazebo_world_distance_m'] = math.dist(truth_start, truth_end)
        assert report['gazebo_world_distance_m'] > 0.1, 'Wheels moved but model did not translate'
    print(json.dumps(report, indent=2))
    assert distance > 0.1 and angle > 0.2, 'No measured base motion'
    assert abs(velocity.linear.x) < 0.02 and abs(velocity.angular.z) < 0.02, 'Base did not stop'
finally:
    command(0., 0., 0.2)
    node.destroy_node()
    rclpy.shutdown()
