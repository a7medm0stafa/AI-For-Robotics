"""TA standalone room request: JSON {id, room}; one request carries all information."""
import json
import threading
import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import String
from .navigation import RoomNavigation


class MoveNode(Node):
    def __init__(self):
        super().__init__('move_node')
        group = ReentrantCallbackGroup()
        self.navigation = RoomNavigation(self, group)
        self.lock = threading.Lock()
        self.faulted = False
        self.results = self.create_publisher(String, 'room_result', 10)
        self.create_subscription(String, 'room_request', self.request, 10, callback_group=group)

    def request(self, msg):
        reply = dict(id=None, success=False)
        acquired = False
        try:
            request = json.loads(msg.data)
            reply['id'] = request['id']
            acquired = self.lock.acquire(False)
            if not acquired:
                raise RuntimeError('Navigation busy')
            if self.faulted:
                raise RuntimeError('Previous failure; reconcile robot pose and restart this node')
            reply['success'] = self.navigation.move(request['room'])
            self.faulted = not reply['success']
        except Exception as exc:
            reply['message'] = str(exc)
            if acquired:
                self.faulted = True
        finally:
            if acquired:
                self.lock.release()
        self.results.publish(String(data=json.dumps(reply)))


def main(args=None):
    rclpy.init(args=args)
    node = MoveNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
