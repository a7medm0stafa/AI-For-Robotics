"""Map-frame room navigation shared by MS1 standalone and MS3 TA nodes."""
import math
from pathlib import Path
import yaml
from ament_index_python.packages import get_package_share_directory
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped
from tf2_ros import Buffer, TransformListener, TransformException
from rclpy.time import Time
from .action_helpers import run_action


class RoomNavigation:
    def __init__(self, node, group):
        self.node = node
        config = node.declare_parameter('rooms_file', str(Path(get_package_share_directory('tb3_planner_execution'))/'config/rooms.yaml')).value
        self.rooms = yaml.safe_load(Path(config).read_text())['rooms']
        self.timeout = node.declare_parameter('navigation_timeout', 300.0).value
        self.client = ActionClient(node, NavigateToPose, 'navigate_to_pose', callback_group=group)
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, node)
        self.pub = node.create_publisher(PoseStamped, 'robot_position', 10)
        self.timer = node.create_timer(1.0, self.publish_position)

    def pose(self):
        transform = self.buffer.lookup_transform('map', 'base_footprint', Time())
        if self.node.get_clock().now().nanoseconds - Time.from_msg(transform.header.stamp).nanoseconds > 2_000_000_000:
            raise RuntimeError('Map pose is stale')
        pose = PoseStamped()
        pose.header = transform.header
        pose.pose.position.x = transform.transform.translation.x
        pose.pose.position.y = transform.transform.translation.y
        pose.pose.orientation = transform.transform.rotation
        return pose

    def publish_position(self):
        try:
            self.pub.publish(self.pose())
        except (TransformException, RuntimeError):
            pass

    def move(self, room):
        if room not in self.rooms:
            raise ValueError(f'Unknown room: {room}')
        pose = self.pose()  # Require localization; never label odometry as map coordinates.
        x, y = self.rooms[room]
        yaw = math.atan2(y-pose.pose.position.y, x-pose.pose.position.x)
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.node.get_clock().now().to_msg()
        goal.pose.pose.position.x, goal.pose.pose.position.y = float(x), float(y)
        goal.pose.pose.orientation.z = math.sin(yaw/2)
        goal.pose.pose.orientation.w = math.cos(yaw/2)
        return run_action(self.client, goal, self.timeout, lambda result: result.error_code == 0)
