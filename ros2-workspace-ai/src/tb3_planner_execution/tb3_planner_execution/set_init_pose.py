#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped
import time

class InitialPoseSetter(Node):
    def __init__(self):
        super().__init__('initial_pose_setter')
        
        # Publisher for initial pose
        self.pose_pub = self.create_publisher(
            PoseWithCovarianceStamped,
            '/initialpose',
            10
        )
        
        # Wait for subscriber to connect
        time.sleep(2)
        
        # Set initial pose at robot spawn location (-2.0, -0.5)
        self.publish_initial_pose()
        
        self.get_logger().info('Initial pose set successfully!')
        
    def publish_initial_pose(self):
        pose_msg = PoseWithCovarianceStamped()
        
        # Header
        pose_msg.header.stamp = self.get_clock().now().to_msg()
        pose_msg.header.frame_id = 'map'
        
        # Position (where robot spawns in gazebo.launch.py)
        pose_msg.pose.pose.position.x = -2.0
        pose_msg.pose.pose.position.y = -0.5
        pose_msg.pose.pose.position.z = 0.0
        
        # Orientation (facing forward, quaternion for yaw=0)
        pose_msg.pose.pose.orientation.x = 0.0
        pose_msg.pose.pose.orientation.y = 0.0
        pose_msg.pose.pose.orientation.z = 0.0
        pose_msg.pose.pose.orientation.w = 1.0
        
        # Covariance (uncertainty in pose estimate)
        pose_msg.pose.covariance = [
            0.25, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.25, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.06853891909122467
        ]
        
        # Publish the pose
        self.pose_pub.publish(pose_msg)
        self.get_logger().info(f'Published initial pose: x={pose_msg.pose.pose.position.x}, y={pose_msg.pose.pose.position.y}')

def main(args=None):
    rclpy.init(args=args)
    node = InitialPoseSetter()
    
    # Keep node alive briefly then shutdown
    time.sleep(1)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()