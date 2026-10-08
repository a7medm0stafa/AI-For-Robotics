"""TA MS1 reference: serialized arm-down/grip/arm-home sequences."""
import threading
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_srvs.srv import Trigger
from control_msgs.action import FollowJointTrajectory, GripperCommand
from trajectory_msgs.msg import JointTrajectoryPoint
from .action_helpers import run_action


class GripperControl(Node):
    def __init__(self):
        super().__init__('gripper_control')
        group = ReentrantCallbackGroup()
        self.arm = ActionClient(self, FollowJointTrajectory, '/arm_controller/follow_joint_trajectory', callback_group=group)
        self.gripper = ActionClient(self, GripperCommand, '/gripper_controller/gripper_cmd', callback_group=group)
        self.lock = threading.Lock()
        self.faulted = False
        self.home = self.declare_parameter('home', [0., 0., 0., -0.1]).value
        self.reach = self.declare_parameter('reach', [0., 0.3, 0.5, 0.5]).value
        self.create_service(Trigger, 'open_gripper', lambda req, res: self.sequence(False, res), callback_group=group)
        self.create_service(Trigger, 'close_gripper', lambda req, res: self.sequence(True, res), callback_group=group)

    def move_arm(self, positions):
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = ['joint1', 'joint2', 'joint3', 'joint4']
        point = JointTrajectoryPoint(positions=list(positions), velocities=[0.]*4)
        point.time_from_start.sec = 2
        goal.trajectory.points = [point]
        return run_action(self.arm, goal, 12, lambda result: result.error_code == 0)

    def control_gripper(self, closed):
        goal = GripperCommand.Goal()
        goal.command.position = -0.01 if closed else 0.01
        goal.command.max_effort = 1.0
        return run_action(self.gripper, goal, 10, lambda result: result.reached_goal and not result.stalled)

    def sequence(self, closed, response):
        if not self.lock.acquire(blocking=False):
            response.success, response.message = False, 'Manipulator busy'
            return response
        try:
            if self.faulted:
                raise RuntimeError('Previous failure: reconcile arm state and restart this node')
            response.success = self.move_arm(self.reach) and self.control_gripper(closed) and self.move_arm(self.home)
            response.message = 'Controller sequence succeeded (symbolic grasp abstraction)' if response.success else 'Controller sequence failed; reconcile state before retry'
            self.faulted = not response.success
        except Exception as exc:
            self.faulted = True
            response.success, response.message = False, str(exc)
        finally:
            self.lock.release()
        return response


def main(args=None):
    rclpy.init(args=args)
    node = GripperControl()
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
