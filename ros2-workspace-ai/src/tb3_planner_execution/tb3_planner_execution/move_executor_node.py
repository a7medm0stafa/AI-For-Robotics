#!/usr/bin/env python3
"""
Move Executor Node
Subscribes to /planner/command for move actions
Uses Nav2 NavigateToPose action to move the robot between rooms
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from std_msgs.msg import String
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
import time


# Room locations (x, y, yaw in radians)
# TODO: Update these with actual coordinates from your map!
ROOM_POSES = {
    'kitchen': {'x': -2.0, 'y': -0.5, 'yaw': 0.0},
    'bedroom': {'x': 1.5, 'y': 2.0, 'yaw': 1.57},
    'livingroom': {'x': 0.0, 'y': 0.0, 'yaw': 0.0},
    'bathroom': {'x': -1.0, 'y': 2.5, 'yaw': 3.14},
}


class MoveExecutorNode(Node):
    def __init__(self):
        super().__init__('move_executor')
        
        # Subscribe to planner commands
        self.command_sub = self.create_subscription(
            String,
            '/planner/command',
            self.command_callback,
            10
        )
        
        # Publish status updates
        self.status_pub = self.create_publisher(String, '/planner/status', 10)
        
        # Nav2 action client
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        
        self.get_logger().info('Move Executor Node started')
        self.get_logger().info('Waiting for Nav2 action server...')
        
        # Wait for action server
        self.nav_client.wait_for_server()
        self.get_logger().info('✓ Nav2 action server connected')
    
    def command_callback(self, msg):
        """Handle incoming commands"""
        command = msg.data.split()
        
        # Only handle 'move' commands
        if len(command) < 3 or command[0] != 'move':
            return
        
        from_room = command[1]
        to_room = command[2]
        
        self.get_logger().info(f'🚗 Moving from {from_room} to {to_room}')
        
        # Get target pose
        if to_room not in ROOM_POSES:
            self.get_logger().error(f'Unknown room: {to_room}')
            status_msg = String()
            status_msg.data = f'failed move unknown_room {to_room}'
            self.status_pub.publish(status_msg)
            return
        
        # Execute navigation
        success = self.navigate_to_room(to_room)
        
        # Publish status
        status_msg = String()
        if success:
            status_msg.data = f'done move {from_room} {to_room}'
            self.get_logger().info(f'✓ Successfully moved to {to_room}')
        else:
            status_msg.data = f'failed move {from_room} {to_room}'
            self.get_logger().error(f'✗ Failed to move to {to_room}')
        
        self.status_pub.publish(status_msg)
    
    def navigate_to_room(self, room_name):
        """Navigate to a room using Nav2"""
        pose_data = ROOM_POSES[room_name]
        
        # Create goal
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = PoseStamped()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        
        # Set position
        goal_msg.pose.pose.position.x = pose_data['x']
        goal_msg.pose.pose.position.y = pose_data['y']
        goal_msg.pose.pose.position.z = 0.0
        
        # Set orientation (yaw to quaternion)
        import math
        yaw = pose_data['yaw']
        goal_msg.pose.pose.orientation.x = 0.0
        goal_msg.pose.pose.orientation.y = 0.0
        goal_msg.pose.pose.orientation.z = math.sin(yaw / 2.0)
        goal_msg.pose.pose.orientation.w = math.cos(yaw / 2.0)
        
        self.get_logger().info(f'Sending goal: ({pose_data["x"]}, {pose_data["y"]}, yaw={pose_data["yaw"]})')
        
        # Send goal
        send_goal_future = self.nav_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)
        
        goal_handle = send_goal_future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Goal rejected by Nav2')
            return False
        
        self.get_logger().info('Goal accepted, waiting for result...')
        
        # Wait for result
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        
        result = result_future.result()
        
        # Check result
        if result.status == 4:  # SUCCEEDED
            return True
        else:
            self.get_logger().error(f'Navigation failed with status: {result.status}')
            return False


def main(args=None):
    rclpy.init(args=args)
    node = MoveExecutorNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
