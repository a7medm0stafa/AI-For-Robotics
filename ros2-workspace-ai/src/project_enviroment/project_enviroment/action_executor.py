#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
import os
import time
import copy

from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from std_srvs.srv import Trigger

# ✅ IMPORT KB & TRANSITION LOGIC FROM PLANNER
from project_enviroment.planner_cli import (
    robot_location,
    holding,
    objects,
    apply_action_to_kb,
    show_kb
)


# ===============================
# PREDEFINED ARM JOINT POSES
# ===============================
ARM_POSES = {
    "stow":  [0.0, -1.2, 1.8, 0.0],
    "pick":  [0.0, 0.5, 0.0, 0.0],
    "place": [0.0, -0.5, 0.9, 0.0],
}


class ActionExecutor(Node):

    def __init__(self):
        super().__init__('action_executor')

        # ---------------------------
        # Copy KB from planner (IMPORTANT)
        # ---------------------------
        self.robot_location = robot_location
        self.holding = holding
        self.objects = copy.deepcopy(objects)

        self.get_logger().info("Initial KB loaded from planner")
        show_kb(self.robot_location, self.holding, self.objects)

        # ---------------------------
        # Arm controller client
        # ---------------------------
        self.arm_client = ActionClient(
            self,
            FollowJointTrajectory,
            '/arm_controller/follow_joint_trajectory'
        )
        self.get_logger().info('Waiting for arm controller...')
        self.arm_client.wait_for_server()
        self.get_logger().info('Arm controller ready.')

        # ---------------------------
        # Gripper services
        # ---------------------------
        self.open_gripper = self.create_client(
            Trigger, '/open_gripper'
        )
        self.close_gripper = self.create_client(
            Trigger, '/close_gripper'
        )
        self.wait_for_services()

        # ---------------------------
        # SAS plan path (same as planner)
        # ---------------------------
        self.plan_file = os.path.expanduser(
            '/home/zuma/AI-For-Robotics/ros2-workspace-ai/src/project_enviroment/project_enviroment/sas_plan'
        )

        self.get_logger().info('Action Executor started.')
        self.execute_plan()

    # ------------------------------------------------
    def wait_for_services(self):
        while not self.open_gripper.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for /open_gripper...')
        while not self.close_gripper.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for /close_gripper...')

    # ------------------------------------------------
    def send_arm_pose(self, pose_name):
        joints = ARM_POSES[pose_name]

        traj = JointTrajectory()
        traj.joint_names = ['joint1', 'joint2', 'joint3', 'joint4']

        point = JointTrajectoryPoint()
        point.positions = joints
        point.time_from_start.sec = 2

        traj.points.append(point)

        goal = FollowJointTrajectory.Goal()
        goal.trajectory = traj

        self.arm_client.send_goal_async(goal)
        time.sleep(2.5)

    # ------------------------------------------------
    def call_gripper(self, client, name):
        req = Trigger.Request()
        future = client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        self.get_logger().info(f'{name} executed')
        time.sleep(1.0)

    # ------------------------------------------------
    def parse_sas_plan(self):
        if not os.path.exists(self.plan_file):
            self.get_logger().error('sas_plan not found')
            return []

        actions = []
        with open(self.plan_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and line.startswith("(") and not line.startswith(";"):
                    actions.append(line)
        return actions

    # ------------------------------------------------
    def execute_plan(self):
        actions = self.parse_sas_plan()
        self.get_logger().info(f'Executing {len(actions)} actions from sas_plan')

        for action in actions:
            self.execute_action(action)

        self.get_logger().info('All actions executed ✅')
        show_kb(self.robot_location, self.holding, self.objects)

    # ------------------------------------------------
    def execute_action(self, action_str):
        tokens = action_str.strip("()").split()
        act = tokens[0]

        self.get_logger().info(f'Executing action: {action_str}')

        # ---------------- MOVE ----------------
        if act == "move":
            _, frm, to = tokens

            self.get_logger().info(
                f"MOVE action: {frm} -> {to} (Nav2 not implemented yet)"
            )

            # ✅ NO physical navigation yet
            # ✅ KB update only

        # ---------------- PICK ----------------
        elif act == "pick":
            _, obj, room = tokens

            self.send_arm_pose("pick")
            self.call_gripper(self.close_gripper, "close_gripper")

        # ---------------- PLACE ----------------
        elif act == "place":
            _, obj, room = tokens

            self.send_arm_pose("place")
            self.call_gripper(self.open_gripper, "open_gripper")

        else:
            self.get_logger().warn(f'Unknown action: {act}')
            return

        # ---------------- KB UPDATE (SINGLE SOURCE OF TRUTH)
        self.robot_location, self.holding, self.objects = apply_action_to_kb(
            action_str,
            self.robot_location,
            self.holding,
            self.objects
        )

        self.get_logger().info("KB updated after action")
        show_kb(self.robot_location, self.holding, self.objects)


def main(args=None):
    rclpy.init(args=args)
    node = ActionExecutor()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
