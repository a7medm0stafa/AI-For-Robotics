#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
import json

class PoseSaver(Node):
    def __init__(self):
        super().__init__('pose_saver')
        
        # Subscribe to robot pose
        self.pose_sub = self.create_subscription(
            Odometry,
            '/odom',
            self.pose_callback,
            10
        )
        
        self.current_pose = None
        self.saved_poses = {}
        
        self.get_logger().info('Pose Saver Node Started!')
        self.get_logger().info('Current pose will be displayed. Press Ctrl+C to save.')
        
    def pose_callback(self, msg):
        self.current_pose = msg.pose.pose
        # Print current position
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        z = msg.pose.pose.position.z
        
        # Get orientation (quaternion)
        qx = msg.pose.pose.orientation.x
        qy = msg.pose.pose.orientation.y
        qz = msg.pose.pose.orientation.z
        qw = msg.pose.pose.orientation.w
        
        print(f"\rCurrent Pose -> X: {x:.3f}, Y: {y:.3f}, Z: {z:.3f} | "
              f"Orientation (quat): [{qx:.3f}, {qy:.3f}, {qz:.3f}, {qw:.3f}]", end='')
    
    def save_pose(self, room_name):
        if self.current_pose:
            pose_data = {
                'position': {
                    'x': self.current_pose.position.x,
                    'y': self.current_pose.position.y,
                    'z': self.current_pose.position.z
                },
                'orientation': {
                    'x': self.current_pose.orientation.x,
                    'y': self.current_pose.orientation.y,
                    'z': self.current_pose.orientation.z,
                    'w': self.current_pose.orientation.w
                }
            }
            self.saved_poses[room_name] = pose_data
            self.get_logger().info(f'\n✓ Saved pose for: {room_name}')
            return True
        return False
    
    def save_to_file(self, filename='room_coordinates.json'):
        with open(filename, 'w') as f:
            json.dump(self.saved_poses, f, indent=4)
        self.get_logger().info(f'All poses saved to {filename}')

def main():
    rclpy.init()
    node = PoseSaver()
    
    print("\n=== POSE SAVER ===")
    print("1. Move robot to a room using teleop")
    print("2. Type room name and press Enter to save")
    print("3. Type 'done' when finished\n")
    
    try:
        # Run node in background
        import threading
        spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
        spin_thread.start()
        
        while True:
            room_name = input("\nEnter room name (or 'done' to finish): ").strip()
            
            if room_name.lower() == 'done':
                break
            
            if room_name:
                node.save_pose(room_name)
        
        # Save all poses to file
        node.save_to_file()
        
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()