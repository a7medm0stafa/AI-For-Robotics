"""Wait for active AMCL and a simulation clock before setting the configured pose."""
import math
import time
import rclpy
from rclpy.node import Node
from lifecycle_msgs.srv import GetState
from geometry_msgs.msg import PoseWithCovarianceStamped


def main(args=None):
    rclpy.init(args=args)
    node = Node('initial_pose_setter')
    x = node.declare_parameter('x', -0.65).value
    y = node.declare_parameter('y', 1.5).value
    yaw = node.declare_parameter('yaw', 0.0).value
    publisher = node.create_publisher(PoseWithCovarianceStamped, 'initialpose', 10)
    client = node.create_client(GetState, '/amcl/get_state')
    deadline = time.monotonic()+60
    try:
        while rclpy.ok() and time.monotonic()<deadline:
            if client.wait_for_service(timeout_sec=1):
                future = client.call_async(GetState.Request())
                rclpy.spin_until_future_complete(node, future, timeout_sec=1)
                if future.done() and future.result().current_state.id == 3 and publisher.get_subscription_count() and node.get_clock().now().nanoseconds:
                    msg = PoseWithCovarianceStamped()
                    msg.header.frame_id = 'map'
                    msg.header.stamp = node.get_clock().now().to_msg()
                    msg.pose.pose.position.x, msg.pose.pose.position.y = float(x), float(y)
                    msg.pose.pose.orientation.z, msg.pose.pose.orientation.w = math.sin(yaw/2), math.cos(yaw/2)
                    msg.pose.covariance[0] = msg.pose.covariance[7] = 0.25
                    msg.pose.covariance[35] = 0.0685
                    publisher.publish(msg)
                    rclpy.spin_once(node, timeout_sec=0.5)
                    node.get_logger().info('Initial pose sent to active AMCL; verify localization before navigation')
                    return
            rclpy.spin_once(node, timeout_sec=0.1)
        raise RuntimeError('AMCL/clock not ready after 60 seconds')
    finally:
        node.destroy_node()
        rclpy.shutdown()
