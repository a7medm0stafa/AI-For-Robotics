#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
import time

from std_srvs.srv import Trigger
from control_msgs.action import GripperCommand, FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


class GripperControl(Node):

    def __init__(self):
        super().__init__('gripper_control')

        # Use reentrant callback group to allow parallel execution
        self.callback_group = ReentrantCallbackGroup()

        # Action client for gripper
        self._gripper_action_client = ActionClient(
            self, 
            GripperCommand, 
            '/gripper_controller/gripper_cmd',
            callback_group=self.callback_group
        )

        # Action client for arm joint trajectory
        self._arm_action_client = ActionClient(
            self,
            FollowJointTrajectory,
            '/arm_controller/follow_joint_trajectory',
            callback_group=self.callback_group
        )

        # Services for open/close with arm movement
        self.open_srv = self.create_service(
            Trigger, 
            'open_gripper', 
            self.open_gripper,
            callback_group=self.callback_group
        )
        self.close_srv = self.create_service(
            Trigger, 
            'close_gripper', 
            self.close_gripper,
            callback_group=self.callback_group
        )

        # Arm joint positions (adjust these based on your robot's configuration)
        # Format: [joint1, joint2, joint3, joint4]
        # Current joint values from /joint_states: joint1≈0, joint2≈0.003, joint3≈0.069, joint4≈-0.087
        self.arm_home_position = [0.0, 0.0, 0.0, -0.1]  # Home position (up)
        self.arm_down_position = [0.0, 0.3, 0.5, 0.5]   # Down position (reach forward/down)

        # Joint names from your TurtleBot3 Manipulation
        self.arm_joint_names = [
            'joint1',  # Base rotation
            'joint2',  # Shoulder pitch
            'joint3',  # Elbow pitch
            'joint4'   # Wrist pitch
        ]

        self.get_logger().info('Gripper control with arm movement ready.')
        self.get_logger().info(f'Arm joints: {self.arm_joint_names}')

    # ---------------------------
    # ARM MOVEMENT
    # ---------------------------
    def move_arm(self, target_position, duration=2.0):
        """
        Move arm to target joint position.
        
        Args:
            target_position: List of joint angles [j1, j2, j3, j4]
            duration: Time to reach target (seconds)
        
        Returns:
            bool: Success status
        """
        self.get_logger().info(f'Moving arm to: {target_position}')
        
        if not self._arm_action_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('Arm controller not available')
            return False

        # Create trajectory goal
        goal = FollowJointTrajectory.Goal()
        goal.trajectory = JointTrajectory()
        goal.trajectory.joint_names = self.arm_joint_names

        # Create trajectory point
        point = JointTrajectoryPoint()
        point.positions = target_position
        point.velocities = [0.0] * len(target_position)
        point.time_from_start.sec = int(duration)
        point.time_from_start.nanosec = int((duration - int(duration)) * 1e9)

        goal.trajectory.points = [point]

        # Send goal
        future = self._arm_action_client.send_goal_async(goal)
        
        # Poll future without blocking executor
        timeout = duration + 5.0
        start = time.time()
        while not future.done() and (time.time() - start) < timeout:
            time.sleep(0.1)

        if not future.done():
            self.get_logger().error('Arm movement goal timed out')
            return False

        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Arm movement goal rejected')
            return False

        # Wait for result
        result_future = goal_handle.get_result_async()
        start = time.time()
        while not result_future.done() and (time.time() - start) < timeout:
            time.sleep(0.1)

        if not result_future.done():
            self.get_logger().error('Arm movement result timed out')
            return False

        result = result_future.result()
        if result.status == 4:  # SUCCEEDED
            self.get_logger().info('✅ Arm moved successfully')
            return True
        else:
            self.get_logger().error(f'Arm movement failed with status: {result.status}')
            return False

    def control_gripper(self, position, max_effort):
        """
        Control gripper position.
        
        Args:
            position: Target position (0.01 = open, -0.01 = closed)
            max_effort: Maximum effort (-1.0 = no limit, 50.0 = grip force)
        
        Returns:
            bool: Success status
        """
        if not self._gripper_action_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('Gripper action server not available')
            return False

        goal = GripperCommand.Goal()
        goal.command.position = position
        goal.command.max_effort = max_effort

        future = self._gripper_action_client.send_goal_async(goal)
        
        timeout = 10.0
        start = time.time()
        while not future.done() and (time.time() - start) < timeout:
            time.sleep(0.1)

        if not future.done():
            self.get_logger().error('Gripper control timed out')
            return False

        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Gripper goal rejected')
            return False

        result_future = goal_handle.get_result_async()
        start = time.time()
        while not result_future.done() and (time.time() - start) < timeout:
            time.sleep(0.1)

        return result_future.done()

    # ---------------------------
    # PICK SEQUENCE
    # ---------------------------
    def close_gripper(self, request, response):
        """
        Pick sequence:
        1. Move arm down
        2. Close gripper
        3. Move arm up
        """
        self.get_logger().info('Starting PICK sequence...')
        
        # Step 1: Move arm down to picking position
        self.get_logger().info('Step 1: Moving arm down')
        if not self.move_arm(self.arm_down_position, duration=2.0):
            response.success = False
            response.message = 'Failed to move arm down'
            return response

        time.sleep(0.5)  # Brief pause

        # Step 2: Close gripper
        self.get_logger().info('Step 2: Closing gripper')
        if not self.control_gripper(position=-0.01, max_effort=50.0):
            response.success = False
            response.message = 'Failed to close gripper'
            # Try to return arm to home anyway
            self.move_arm(self.arm_home_position, duration=2.0)
            return response

        time.sleep(0.5)  # Brief pause

        # Step 3: Move arm back up to home position
        self.get_logger().info('Step 3: Moving arm up')
        if not self.move_arm(self.arm_home_position, duration=2.0):
            response.success = False
            response.message = 'Failed to move arm up (object picked)'
            return response

        response.success = True
        response.message = 'Pick sequence completed successfully'
        self.get_logger().info('✅ PICK sequence completed')
        return response

    # ---------------------------
    # PLACE SEQUENCE
    # ---------------------------
    def open_gripper(self, request, response):
        """
        Place sequence:
        1. Move arm down
        2. Open gripper
        3. Move arm up
        """
        self.get_logger().info('Starting PLACE sequence...')
        
        # Step 1: Move arm down to placing position
        self.get_logger().info('Step 1: Moving arm down')
        if not self.move_arm(self.arm_down_position, duration=2.0):
            response.success = False
            response.message = 'Failed to move arm down'
            return response

        time.sleep(0.5)  # Brief pause

        # Step 2: Open gripper
        self.get_logger().info('Step 2: Opening gripper')
        if not self.control_gripper(position=0.01, max_effort=-1.0):
            response.success = False
            response.message = 'Failed to open gripper'
            # Try to return arm to home anyway
            self.move_arm(self.arm_home_position, duration=2.0)
            return response

        time.sleep(0.5)  # Brief pause

        # Step 3: Move arm back up to home position
        self.get_logger().info('Step 3: Moving arm up')
        if not self.move_arm(self.arm_home_position, duration=2.0):
            response.success = False
            response.message = 'Failed to move arm up (object released)'
            return response

        response.success = True
        response.message = 'Place sequence completed successfully'
        self.get_logger().info('✅ PLACE sequence completed')
        return response


def main(args=None):
    rclpy.init(args=args)
    node = GripperControl()
    
    # Use MultiThreadedExecutor to handle concurrent callbacks
    from rclpy.executors import MultiThreadedExecutor
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down gripper control')
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
