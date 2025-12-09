#!/usr/bin/env python3
"""
Manipulator Executor Node
Subscribes to /planner/command for pick/place actions
Controls the gripper and arm to manipulate objects
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from std_msgs.msg import String
from control_msgs.action import GripperCommand
import time


class ManipulatorExecutorNode(Node):
    def __init__(self):
        super().__init__('manip_executor')
        
        # Subscribe to planner commands
        self.command_sub = self.create_subscription(
            String,
            '/planner/command',
            self.command_callback,
            10
        )
        
        # Publish status updates
        self.status_pub = self.create_publisher(String, '/planner/status', 10)
        
        # Gripper action client
        self.gripper_client = ActionClient(
            self,
            GripperCommand,
            '/gripper_controller/gripper_cmd'
        )
        
        self.get_logger().info('Manipulator Executor Node started')
        self.get_logger().info('Waiting for gripper action server...')
        
        # Wait for action server (with timeout)
        if self.gripper_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().info('✓ Gripper action server connected')
        else:
            self.get_logger().warn('Gripper action server not available, will retry on first use')
    
    def command_callback(self, msg):
        """Handle incoming commands"""
        command = msg.data.split()
        
        # Only handle 'pick' and 'place' commands
        if len(command) < 2:
            return
        
        action_type = command[0]
        
        if action_type == 'pick':
            # Format: pick object_name room_name
            if len(command) < 3:
                return
            object_name = command[1]
            room_name = command[2]
            
            self.get_logger().info(f'🤖 Picking up {object_name} from {room_name}')
            success = self.pick_object(object_name, room_name)
            
            status_msg = String()
            if success:
                status_msg.data = f'done pick {object_name} {room_name}'
                self.get_logger().info(f'✓ Successfully picked {object_name}')
            else:
                status_msg.data = f'failed pick {object_name} {room_name}'
                self.get_logger().error(f'✗ Failed to pick {object_name}')
            
            self.status_pub.publish(status_msg)
        
        elif action_type == 'place':
            # Format: place object_name room_name
            if len(command) < 3:
                return
            object_name = command[1]
            room_name = command[2]
            
            self.get_logger().info(f'🤖 Placing {object_name} in {room_name}')
            success = self.place_object(object_name, room_name)
            
            status_msg = String()
            if success:
                status_msg.data = f'done place {object_name} {room_name}'
                self.get_logger().info(f'✓ Successfully placed {object_name}')
            else:
                status_msg.data = f'failed place {object_name} {room_name}'
                self.get_logger().error(f'✗ Failed to place {object_name}')
            
            self.status_pub.publish(status_msg)
    
    def pick_object(self, object_name, room_name):
        """
        Execute pick action
        TODO: Add proper arm movement and visual servoing
        For now, just opens/closes gripper
        """
        # Step 1: Open gripper
        if not self.control_gripper(open=True):
            return False
        
        time.sleep(1.0)
        
        # TODO: Step 2: Move arm to object position
        # This would use arm_controller with JointTrajectory
        self.get_logger().info(f'[TODO] Moving arm to {object_name} position...')
        time.sleep(2.0)  # Simulate arm movement
        
        # Step 3: Close gripper
        if not self.control_gripper(open=False):
            return False
        
        time.sleep(1.0)
        
        # TODO: Step 4: Lift arm
        self.get_logger().info('[TODO] Lifting arm...')
        time.sleep(1.0)
        
        return True
    
    def place_object(self, object_name, room_name):
        """
        Execute place action
        TODO: Add proper arm movement
        For now, just opens gripper
        """
        # TODO: Step 1: Move arm to place position
        self.get_logger().info(f'[TODO] Moving arm to place position in {room_name}...')
        time.sleep(2.0)  # Simulate arm movement
        
        # Step 2: Open gripper
        if not self.control_gripper(open=True):
            return False
        
        time.sleep(1.0)
        
        # TODO: Step 3: Retract arm
        self.get_logger().info('[TODO] Retracting arm...')
        time.sleep(1.0)
        
        return True
    
    def control_gripper(self, open=True):
        """Control the gripper (open or close)"""
        # Wait for server if not ready
        if not self.gripper_client.server_is_ready():
            self.get_logger().warn('Waiting for gripper server...')
            if not self.gripper_client.wait_for_server(timeout_sec=5.0):
                self.get_logger().error('Gripper server timeout')
                return False
        
        goal = GripperCommand.Goal()
        
        if open:
            goal.command.position = 0.01  # Open position (max opening)
            self.get_logger().info('Opening gripper...')
        else:
            goal.command.position = -0.01  # Close position (fully closed)
            self.get_logger().info('Closing gripper...')
        
        goal.command.max_effort = -1.0  # Use default effort
        
        # Send goal
        send_goal_future = self.gripper_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_goal_future, timeout_sec=3.0)
        
        if not send_goal_future.done():
            self.get_logger().error('Gripper goal send timeout')
            return False
        
        goal_handle = send_goal_future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Gripper goal rejected')
            return False
        
        # Wait for result
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future, timeout_sec=5.0)
        
        if not result_future.done():
            self.get_logger().error('Gripper result timeout')
            return False
        
        result = result_future.result()
        
        if result.status == 4:  # SUCCEEDED
            action = 'opened' if open else 'closed'
            self.get_logger().info(f'✓ Gripper {action}')
            return True
        else:
            self.get_logger().error(f'Gripper control failed with status: {result.status}')
            return False


def main(args=None):
    rclpy.init(args=args)
    node = ManipulatorExecutorNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
