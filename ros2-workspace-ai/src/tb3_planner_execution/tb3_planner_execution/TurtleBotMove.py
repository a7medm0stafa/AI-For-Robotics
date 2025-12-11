import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool , String
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
from transforms3d.euler import euler2quat  

class MoveNode(Node):
    def __init__(self):
        super().__init__('move_node')

        self.move_done=False

        self._action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.room_coordinates = {
            "diningroom": (5.5, 5.0, 1.5708),
            "storageroom": (7.3 , -1.8, 0.0),
            "livingroom": (-2.0, 5.0, 1.5708),
            "door": (2.0, 0.15 , 1.5708),
            "studyroom": (-5.65, 5.75, 1.5708),
            "bedroom": (-4.8, -1.45, 0.0)
        }

        # self.room_coordinates = {
        #     "diningroom": (4.44, 4.65, 1.5708),
        #     "storageroom": (-3.41, 4.50, 1.5708),
        #     "livingroom": (-3.26, 4.65, 1.5708),
        #     "door": (1.0, -0.15 , 1.5708),
        #     "studyroom": (-6.83, 4.66, 1.5708),
        #     "bedroom": (-5.88, -1.45, 0.0)
        # }

        # Publisher
        self.move_status_pub = self.create_publisher(Bool, 'move_status', 1)

        # Subscriber
        self.move_cmd_sub = self.create_subscription(Bool,'move_cmd',self.move_command_callback,1)
        self.goal_room_sub = self.create_subscription(String, 'goal_room', self.goal_room_callback, 1)
        self.subscription = self.create_subscription(Odometry,'/odom',self.odom_callback,1)

        self.get_logger().info("Move Node initialized and ready.")

    def odom_callback(self, msg): #get turtlebot stat.
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y
        self.q = msg.pose.pose.orientation


    def move_command_callback(self, msg):
        if msg.data:
            self.get_logger().info("Received move command: True. Executing move...")
            self.move_done=False
        else:
            self.get_logger().info("Received move command: False. Ignoring.")

    def goal_room_callback(self, msg):
        room_name = msg.data.strip().lower()
        coords = self.get_room_coordinates(room_name)
        if coords is None:
            self.get_logger().warn(f"Unknown room: {room_name}")
            return

        x, y, yaw = coords
        self.get_logger().info(f"Received room goal: {room_name} at ({x}, {y})")
        self.get_logger().info(f"Current Coordinates:({self.x}, {self.y})")
        self.send_goal(x, y, yaw)

    
    def get_room_coordinates(self, room_name):
        return self.room_coordinates.get(room_name.lower(), None)

    def send_goal(self, x, y, yaw):
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y

        # Convert yaw (in radians) to quaternion
        # euler2quat returns (w, x, y, z)
        q = euler2quat(0, 0, yaw)
        goal_msg.pose.pose.orientation.w = q[0]
        goal_msg.pose.pose.orientation.x = q[1]
        goal_msg.pose.pose.orientation.y = q[2]
        goal_msg.pose.pose.orientation.z = q[3]

        self._action_client.wait_for_server()
        self.get_logger().info(f'Sending goal: x={x}, y={y}, yaw={yaw} → quaternion={q}')
        self._send_goal_future = self._action_client.send_goal_async(goal_msg, feedback_callback=self.feedback_callback)
        self._send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('Goal rejected ')
            return

        self.get_logger().info('Goal accepted ')
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        #self.get_logger().info(f'Current progress: {feedback.current_pose.pose.position}')

    def get_result_callback(self, future):
        result = future.result().result
        status = future.result().status

        if status == 4:  # SUCCEEDED
            self.get_logger().info(f'Navigation successful {self.x} , {self.y}')
            result_msg = Bool()
            result_msg.data = True
            self.move_done=True
            msg=Bool()
            msg.data=self.move_done
            self.move_status_pub.publish(msg)

            self.get_logger().info("Move complete. Published move_status: True")
        else:
            self.get_logger().warn(f'Navigation failed with status code: {status}')

def main(args=None):
    rclpy.init(args=args)
    node = MoveNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down node from Ctrl+C')
    finally:
        if rclpy.ok():
            rclpy.shutdown()
        node.destroy_node()



if __name__ == '__main__':
    main()
