#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from std_srvs.srv import Trigger
from control_msgs.action import GripperCommand


class GripperControl(Node):

    def __init__(self):
        super().__init__('gripper_control')

        # Action client for gripper
        self.gripper_client = ActionClient(
            self,
            GripperCommand,
            '/gripper_controller/gripper_cmd'
        )

        self.get_logger().info('Waiting for gripper action server...')
        self.gripper_client.wait_for_server()
        self.get_logger().info('Gripper action server ready.')

        # Services exposed to higher-level nodes
        self.create_service(Trigger, 'open_gripper', self.open_gripper)
        self.create_service(Trigger, 'close_gripper', self.close_gripper)

        self.get_logger().info('Gripper control node ready.')

    # ---------------------------
    # OPEN GRIPPER
    # ---------------------------
    def open_gripper(self, request, response):
        goal = GripperCommand.Goal()
        goal.command.position = 0.15    # OPEN
        goal.command.max_effort = 1.0

        self.gripper_client.send_goal_async(goal)

        response.success = True
        response.message = "Gripper opened"
        return response

    # ---------------------------
    # CLOSE GRIPPER
    # ---------------------------
    def close_gripper(self, request, response):
        goal = GripperCommand.Goal()
        goal.command.position = 0.0      # CLOSED
        goal.command.max_effort = 1.0

        self.gripper_client.send_goal_async(goal)

        response.success = True
        response.message = "Gripper closed"
        return response


def main(args=None):
    rclpy.init(args=args)
    node = GripperControl()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
