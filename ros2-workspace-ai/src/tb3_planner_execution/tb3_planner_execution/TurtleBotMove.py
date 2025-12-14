import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String
from geometry_msgs.msg import PoseStamped
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
import math

class MoveNode(Node):
    def __init__(self):
        super().__init__('move_node')

        self.move_done = False
        self._action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        
        # Room coordinates - Position only (x, y)
        # Orientation will be set dynamically based on approach direction
        self.room_coordinates = {
            "diningroom": (4.8, 1.3),
            "storageroom": (5.55, -2.8),
            "livingroom": (-2.65, 1.0),
            "bathroom": (0.9, 3.2),
            "studyroom": (-6.0, 3.0),
            "bedroom": (-6.3, -0.45)
        }

        # Publishers
        self.move_status_pub = self.create_publisher(Bool, 'move_status', 10)
        self.position_pub = self.create_publisher(PoseStamped, 'robot_position', 10)
        self.position_timer = self.create_timer(5.0, self.publish_position)

        # Subscribers
        self.move_cmd_sub = self.create_subscription(
            Bool, 'move_cmd', self.move_command_callback, 10
        )
        self.goal_room_sub = self.create_subscription(
            String, 'goal_room', self.goal_room_callback, 10
        )
        self.subscription = self.create_subscription(
            Odometry, '/odom', self.odom_callback, 10
        )

        # State
        self.x = 0.0
        self.y = 0.0
        self.q = None
        
        self.get_logger().info("Move Node initialized.")
        self.get_logger().info("Available rooms: " + str(list(self.room_coordinates.keys())))

    def odom_callback(self, msg):
        """Get TurtleBot position from odometry."""
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y
        self.q = msg.pose.pose.orientation

    def publish_position(self):
        """Publish current robot position."""
        if self.q is not None:
            pose_msg = PoseStamped()
            pose_msg.header.stamp = self.get_clock().now().to_msg()
            pose_msg.header.frame_id = 'map'
            pose_msg.pose.position.x = self.x 
            pose_msg.pose.position.y = self.y 
            pose_msg.pose.position.z = 0.0
            pose_msg.pose.orientation = self.q
            self.position_pub.publish(pose_msg)
            
            self.get_logger().info(f"Robot at: ({self.x:.2f}, {self.y:.2f})")

    def move_command_callback(self, msg):
        """Receive move command trigger."""
        if msg.data:
            self.get_logger().info("Received move command")
            self.move_done = False

    def goal_room_callback(self, msg):
        """Receive room goal and initiate navigation."""
        room_name = msg.data.strip().lower()
        coords = self.get_room_coordinates(room_name)
        if coords is None:
            self.get_logger().error(f"❌ UNKNOWN ROOM: '{room_name}'")
            self.get_logger().info(f"Available: {list(self.room_coordinates.keys())}")
            msg = Bool()
            msg.data = False
            self.move_status_pub.publish(msg)
            return

        # Calculate orientation based on current position → goal
        x, y = coords
        yaw = self.calculate_approach_angle(x, y)
        
        # Check if already at goal
        distance = math.sqrt((x - self.x)**2 + (y - self.y)**2)
        
        if distance < 0.5:  # Within 50cm
            self.get_logger().info(f'✅ Already at {room_name} ({self.x:.2f}, {self.y:.2f})')
            self.get_logger().info('No movement needed - returning success')
            msg = Bool()
            msg.data = True
            self.move_status_pub.publish(msg)
            return
        
        self.get_logger().info(f"🎯 Goal: {room_name} at ({x:.2f}, {y:.2f})")
        self.get_logger().info(f"📍 Current: ({self.x:.2f}, {self.y:.2f})")
        self.get_logger().info(f"📏 Distance: {distance:.2f}m, Approach angle: {math.degrees(yaw):.1f}°")
        self.send_goal(x, y, yaw)

    def calculate_approach_angle(self, goal_x, goal_y):
        """
        Calculate orientation to face the goal from current position.
        This allows Nav2 to choose the best approach path.
        """
        dx = goal_x - self.x
        dy = goal_y - self.y
        yaw = math.atan2(dy, dx)
        return yaw

    def get_room_coordinates(self, room_name):
        """Get coordinates for a room name."""
        return self.room_coordinates.get(room_name.lower(), None)

    def send_goal(self, x, y, yaw):
        """Send navigation goal to Nav2."""
        self.get_logger().info('Waiting for Nav2 action server...')
        server_available = self._action_client.wait_for_server(timeout_sec=10.0)
        
        if not server_available:
            self.get_logger().error('❌ Nav2 NOT RUNNING!')
            msg = Bool()
            msg.data = False
            self.move_status_pub.publish(msg)
            return
        
        self.get_logger().info('✅ Nav2 available')

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = x + 2.0
        goal_msg.pose.pose.position.y = y + 0.5
        goal_msg.pose.pose.position.z = 0.0

        # Convert yaw to quaternion
        # Use approach angle so robot faces the direction it's traveling
        goal_msg.pose.pose.orientation.w = math.cos(yaw / 2.0)
        goal_msg.pose.pose.orientation.x = 0.0
        goal_msg.pose.pose.orientation.y = 0.0
        goal_msg.pose.pose.orientation.z = math.sin(yaw / 2.0)

        self.get_logger().info(f'📤 Sending goal: ({x:.2f}, {y:.2f}, yaw={math.degrees(yaw):.1f}°)')
        
        self._send_goal_future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )
        self._send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        """Handle goal acceptance/rejection."""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('❌ Nav2 REJECTED goal!')
            self.get_logger().error('Set initial pose in RViz2: "2D Pose Estimate"')
            msg = Bool()
            msg.data = False
            self.move_status_pub.publish(msg)
            return

        self.get_logger().info('✅ Nav2 ACCEPTED, navigating...')
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def feedback_callback(self, feedback_msg):
        pass

    def get_result_callback(self, future):
        """Handle navigation result."""
        status = future.result().status
        
        if status == 4:  # SUCCEEDED
            self.get_logger().info(f'✅ SUCCESS! At ({self.x:.2f}, {self.y:.2f})')
            msg = Bool()
            msg.data = True
            self.move_status_pub.publish(msg)
        elif status == 6:  # ABORTED
            self.get_logger().error(f'❌ ABORTED! Nav2 could not find path')
            msg = Bool()
            msg.data = False
            self.move_status_pub.publish(msg)
        else:
            self.get_logger().error(f'❌ FAILED! Status: {status}')
            msg = Bool()
            msg.data = False
            self.move_status_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = MoveNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down')
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
