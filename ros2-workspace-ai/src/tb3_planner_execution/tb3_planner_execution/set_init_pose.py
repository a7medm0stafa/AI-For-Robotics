#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped
import time

class InitialPoseSetter(Node):
    
    def __init__(self):
        super().__init__('initial_pose_setter')
        self.publisher = self.create_publisher(
            PoseWithCovarianceStamped,
            '/initialpose',
            10
        )
        
        # Give time for RViz/AMCL to initialize
        self.get_logger().info("Waiting 3 seconds for RViz/AMCL to initialize...")
        time.sleep(3)
        
        self.publish_initial_pose()
        
    def publish_initial_pose(self):
        msg = PoseWithCovarianceStamped()
        
        # Header
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        
        # Position (original values that work with origin [-6.86, -5.35, 0])
        msg.pose.pose.position.x = -2.0
        msg.pose.pose.position.y = -0.5
        msg.pose.pose.position.z = 0.0
        
        # Orientation (robot facing forward)
        msg.pose.pose.orientation.x = 0.0
        msg.pose.pose.orientation.y = 0.0
        msg.pose.pose.orientation.z = 0.0
        msg.pose.pose.orientation.w = 1.0
        
        # Covariance (uncertainty)
        msg.pose.covariance = [0.25, 0.0, 0.0, 0.0, 0.0, 0.0,
                                0.0, 0.25, 0.0, 0.0, 0.0, 0.0,
                                0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                                0.0, 0.0, 0.0, 0.0, 0.0, 0.06853892326654787]
        
        # Publish multiple times to ensure it's received
        for i in range(5):
            self.publisher.publish(msg)
            self.get_logger().info(f"Published initial pose (attempt {i+1}/5): x={msg.pose.pose.position.x}, y={msg.pose.pose.position.y}")
            time.sleep(0.5)
        
        self.get_logger().info("Initial pose set successfully!")

def main(args=None):
    rclpy.init(args=args)
    node = InitialPoseSetter()
    # Keep node alive briefly to ensure messages are sent
    time.sleep(3)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
