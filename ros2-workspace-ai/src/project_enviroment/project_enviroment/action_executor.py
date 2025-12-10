#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
import os
import time

from geometry_msgs.msg import Pose
from std_srvs.srv import Trigger

from project_enviroment.world_model import (
    OBJECT_PICK_POSES,
    ROOM_PLACE_POSES
)


class ActionExecutor(Node):

    def __init__(self):
        super().__init__('action_executor')

        # ---- Publishers & Services ----
        self.pose_pub = self.create_publisher(
            Pose, '/arm_target_pose', 10
        )

        self.open_gripper = self.create_client(
            Trigger, '/open_gripper'
        )
        self.close_gripper = self.create_client(
            Trigger, '/close_gripper'
        )

        self.wait_for_services()

        # ---- Path to sas_plan ----
        self.plan_file = os.path.expanduser(
            '~/AI-For-Robotics/ros2-workspace-ai/planner/sas_plan'
        )

        self.get_logger().info('Action Executor started.')
        self.execute_plan()

    # --------------------------------------------------
    def wait_for_services(self):
        while not self.open_gripper.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for /open_gripper...')
        while not self.close_gripper.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Waiting for /close_gripper...')

    # --------------------------------------------------
    def call_gripper(self, client, name):
        req = Trigger.Request()
        future = client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        self.get_logger().info(f'{name} executed')
        time.sleep(1.0)

    # --------------------------------------------------
    def publish_pose(self, x, y, z):
        pose = Pose()
        pose.position.x = x
        pose.position.y = y
        pose.position.z = z
        pose.orientation.w = 1.0

        self.pose_pub.publish(pose)
        self.get_logger().info(
            f'Arm target pose: x={x:.2f}, y={y:.2f}, z={z:.2f}'
        )
        time.sleep(2.0)

    # --------------------------------------------------
    def parse_sas_plan(self):
        if not os.path.exists(self.plan_file):
            self.get_logger().error('sas_plan not found')
            return []

        actions = []
        with open(self.plan_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('(') and not line.startswith(';'):
                    actions.append(line)
        return actions

    # --------------------------------------------------
    def execute_plan(self):
        actions = self.parse_sas_plan()

        self.get_logger().info(
            f'Executing {len(actions)} actions from sas_plan'
        )

        for action in actions:
            self.execute_action(action)

        self.get_logger().info('All actions executed ✅')

    # --------------------------------------------------
    def execute_action(self, action_str):
        """
        Example action_str:
        (pick cup garden)
        (place cup bedroom)
        """

        tokens = action_str.strip('()').split()
        action = tokens[0]

        # ---------------- MOVE (IGNORED) ----------------
        if action == 'move':
            self.get_logger().info('Move action ignored')
            return

        # ---------------- PICK -------------------------
        if action == 'pick':
            self.call_gripper(self.open_gripper, 'open_gripper')
            _, obj, location = tokens

            if obj not in OBJECT_PICK_POSES:
                self.get_logger().error(
                    f'No pick coordinates for object: {obj}'
                )
                return

            x, y, z = OBJECT_PICK_POSES[obj]

            self.get_logger().info(
                f'PICK: object={obj} from {location}'
            )

            self.publish_pose(x, y, z)
            self.call_gripper(self.close_gripper, 'close_gripper')

        # ---------------- PLACE ------------------------
        elif action == 'place':
            _, obj, location = tokens

            if location not in ROOM_PLACE_POSES:
                self.get_logger().error(
                    f'No place coordinates for room: {location}'
                )
                return

            x, y, z = ROOM_PLACE_POSES[location]

            self.get_logger().info(
                f'PLACE: object={obj} to {location}'
            )

            self.publish_pose(x, y, z)
            self.call_gripper(self.open_gripper, 'open_gripper')

        else:
            self.get_logger().warn(
                f'Unknown action type: {action}'
            )


def main(args=None):
    rclpy.init(args=args)
    node = ActionExecutor()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
