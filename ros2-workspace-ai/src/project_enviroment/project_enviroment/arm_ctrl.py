#!/usr/bin/env python3

import math

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from geometry_msgs.msg import Pose
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


class ArmControl(Node):

    def __init__(self):
        super().__init__('arm_control')

        # Action client for the arm trajectory controller
        self.arm_client = ActionClient(
            self,
            FollowJointTrajectory,
            '/arm_controller/follow_joint_trajectory'
        )

        self.get_logger().info('Waiting for arm controller...')
        self.arm_client.wait_for_server()
        self.get_logger().info('Arm controller ready.')

        # Joint order must match the controller
        self.joint_names = ['joint1', 'joint2', 'joint3', 'joint4']

        # Link lengths (meters) for OpenManipulator-X (approx)
        # L1: base to shoulder height
        # L2: shoulder to elbow
        # L3: elbow to wrist
        # L4: wrist to end-effector
        self.L1 = 0.0595
        self.L2 = 0.130
        self.L3 = 0.124
        self.L4 = 0.126

        self.a1 = self.L2
        self.a2 = self.L3 + self.L4


        # Subscribe to target pose in base_link frame
        self.create_subscription(
            Pose,
            '/arm_target_pose',
            self.pose_callback,
            10
        )

        self.get_logger().info('Pose-based Arm Control with IK ready.')

    # -------------------------------------------------
    # Analytical IK: XYZ (base_link) → [j1, j2, j3, j4]
    # -------------------------------------------------
    def ik_xyz_to_joints(self, x, y, z):
        """
        Simple geometric IK for a 4-DOF OpenManipulator-like arm.

        Assumptions:
        - joint1 rotates about z (base yaw)
        - joint2 & joint3 form a planar 2-link arm in (r,z) plane
        - joint4 kept at 0 (no wrist orientation control)
        - target in base_link frame
        """

        # 1) Base rotation (joint1)
        j1 = math.atan2(y, x)

        # 2) Planar distance from base axis
        r = math.sqrt(x * x + y * y)

        # 3) Height relative to joint2 (subtract L1)
        z_rel = z - self.L1

        # Distance from shoulder joint to target point (in plane)
        d = math.sqrt(r * r + z_rel * z_rel)

        # Clamp to reachable workspace
        # Effective link lengths a1 and a2
        a1 = self.a1
        a2 = self.a2

        # Avoid numerical issues
        if d > (a1 + a2):
            self.get_logger().warn(
                f"Target ({x:.3f}, {y:.3f}, {z:.3f}) outside reach "
                f"(d={d:.3f} > a1+a2={a1 + a2:.3f}). Clamping."
            )
            d = a1 + a2 - 1e-6

        if d < abs(a1 - a2):
            self.get_logger().warn(
                f"Target ({x:.3f}, {y:.3f}, {z:.3f}) inside minimum reach "
                f"(d={d:.3f} < |a1-a2|={abs(a1 - a2):.3f}). Clamping."
            )
            d = abs(a1 - a2) + 1e-6

        # 4) Elbow joint (joint3) using law of cosines
        cos_j3 = (d * d - a1 * a1 - a2 * a2) / (2.0 * a1 * a2)
        cos_j3 = max(-1.0, min(1.0, cos_j3))  # clamp
        # Choose elbow "down" configuration
        j3 = math.acos(cos_j3)  # 0 to pi

        # 5) Shoulder joint (joint2)
        # Angle from shoulder to target
        phi = math.atan2(z_rel, r)

        # Angle between a1 and line to target
        k1 = a1 + a2 * cos_j3
        k2 = a2 * math.sin(j3)
        theta = math.atan2(k2, k1)

        j2 = phi - theta

        # 6) Wrist joint (joint4) - keep simple for now
        j4 = 0.0

        return [j1, j2, j3, j4]

    # -------------------------------------------------
    def pose_callback(self, msg: Pose):
        x = msg.position.x
        y = msg.position.y
        z = msg.position.z

        joints = self.ik_xyz_to_joints(x, y, z)

        self.get_logger().info(
            f"IK target XYZ=({x:.3f}, {y:.3f}, {z:.3f}) "
            f"→ joints={['%.2f' % j for j in joints]}"
        )

        traj = JointTrajectory()
        traj.joint_names = self.joint_names

        point = JointTrajectoryPoint()
        point.positions = joints
        point.time_from_start.sec = 2  # 2 seconds to reach target

        traj.points.append(point)

        goal = FollowJointTrajectory.Goal()
        goal.trajectory = traj

        self.arm_client.send_goal_async(goal)

    # -------------------------------------------------


def main(args=None):
    rclpy.init(args=args)
    node = ArmControl()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
