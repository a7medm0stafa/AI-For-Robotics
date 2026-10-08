"""TA MS3 reference. Immutable requests, direct Nav2 actions, truthful results."""
import json
from pathlib import Path
import threading
import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import String
from std_srvs.srv import Trigger
from .action_helpers import wait_future
from .execution import execute_request
from .navigation import RoomNavigation
from .planning import default_kb_path


class PlanExecutor(Node):
    def __init__(self):
        super().__init__('plan_executor')
        group = ReentrantCallbackGroup()
        self.kb = Path(self.declare_parameter('kb_path', str(default_kb_path())).value).expanduser().resolve()
        self.use_gripper = self.declare_parameter('use_gripper', True).value
        self.navigation = RoomNavigation(self, group)
        self.lock = threading.Lock()
        self.services = {name: self.create_client(Trigger, endpoint, callback_group=group)
                         for name, endpoint in [('pick', 'close_gripper'), ('place', 'open_gripper')]}
        self.results = self.create_publisher(String, 'plan_result', 10)
        self.create_subscription(String, 'plan_request', self.request, 10, callback_group=group)

    def perform(self, action):
        self.get_logger().info(f'Executing {action}')
        if action[0] == 'move':
            return self.navigation.move(action[2])
        if not self.use_gripper:
            raise RuntimeError('Manipulation disabled; cannot claim pick/place success')
        client = self.services[action[0]]
        if not client.wait_for_service(timeout_sec=5):
            raise RuntimeError('Manipulator service unavailable')
        # Three bounded controller calls can take up to 64 seconds including discovery/acknowledgement.
        result = wait_future(client.call_async(Trigger.Request()), 90)
        if not result.success:
            self.get_logger().error(result.message)
        return result.success

    def request(self, msg):
        acquired = False
        reply = dict(id=None, success=False, completed=0)
        try:
            request = json.loads(msg.data)
            reply['id'] = request['id']
            acquired = self.lock.acquire(False)
            if not acquired:
                raise RuntimeError('Executor busy: overlapping plan rejected')
            if Path(request['kb_path']).expanduser().resolve() != self.kb:
                raise ValueError('CLI and executor KB paths differ')
            reply = execute_request(request, self.kb, self.perform)
        except Exception as exc:
            reply['message'] = str(exc)
        finally:
            if acquired:
                self.lock.release()
        self.results.publish(String(data=json.dumps(reply)))
        self.get_logger().info(json.dumps(reply))


def main(args=None):
    rclpy.init(args=args)
    node = PlanExecutor()
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
