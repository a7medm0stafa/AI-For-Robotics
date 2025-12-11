import rclpy
from rclpy.node import Node

from std_msgs.msg import Bool, String
from std_srvs.srv import Trigger  # still used for pick/place/KB


class PlanExecutor(Node):
    def __init__(self):
        super().__init__('plan_executor')

        # Parameters
        self.declare_parameter(
            'plan_file',
            '/home/ahmed/AI-For-Robotics/ros2-workspace-ai/planner/sas_plan'
        )
        self.plan_file = self.get_parameter(
            'plan_file'
        ).get_parameter_value().string_value

        # Interfaces to TurtleBotMove
        self.goal_room_pub = self.create_publisher(String, 'goal_room', 1)
        self.move_cmd_pub = self.create_publisher(Bool, 'move_cmd', 1)
        self.move_status_sub = self.create_subscription(
            Bool, 'move_status', self._move_status_callback, 1
        )

        self._waiting_for_move = False

        # Service clients (pick/place/KB) are unchanged
        self.pick_client = self.create_client(Trigger, '/open_manipulator/pick')
        self.place_client = self.create_client(Trigger, '/open_manipulator/place')
        self.kb_update_client = self.create_client(Trigger, '/planner/kb_update')

        # Load plan
        self.actions = self._load_plan(self.plan_file)
        self.get_logger().info(
            f'Loaded {len(self.actions)} actions from plan.'
        )

        # Delay a bit then start execution (ensures subscriptions/pubs are set up)
        self._start_timer = self.create_timer(1.0, self._execute_plan_once)

    def _wait_for_servers(self):
        for name, client in [
            ('pick', self.pick_client),
            ('place', self.place_client),
            ('kb_update', self.kb_update_client),
        ]:
            self.get_logger().info(f'Waiting for {name} service...')
            client.wait_for_service()
            self.get_logger().info(f'{name} service available.')

    # === Callbacks ===

    def _move_status_callback(self, msg: Bool):
        """Receive completion status from TurtleBotMove node."""
        if self._waiting_for_move and msg.data:
            self.get_logger().info('Received move_status=True from move node.')
            self._waiting_for_move = False

    def _load_plan(self, filepath):
        """
        Parse sas_plan of the form:
          (move cinemaroom livingroom)
          (pick chewy garden)
          (place chewy kitchen)
        into:
          {'name': 'move', 'args': ['cinemaroom', 'livingroom']}
        """
        actions = []
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(';'):
                        continue

                    # e.g. "(move cinemaroom livingroom)"
                    if line.startswith('(') and line.endswith(')'):
                        line = line[1:-1]

                    parts = line.split()
                    if not parts:
                        continue

                    action_name = parts[0].lower()
                    args = [p.lower() for p in parts[1:]]

                    actions.append({'name': action_name, 'args': args})
        except Exception as e:
            self.get_logger().error(f'Failed to load plan file {filepath}: {e}')
        return actions

    def _execute_plan_once(self):
        # This timer is only needed once
        self.get_logger().info('Starting plan execution...')
        self._wait_for_servers()
        self._execute_plan()

    def _execute_plan(self):
        for idx, action in enumerate(self.actions):
            name = action['name']
            args = action['args']
            self.get_logger().info(f'Executing action {idx}: {name} {args}')

            ok = False
            if name == 'move':
                ok = self._exec_move(args)
            elif name == 'pick':
                ok = self._exec_pick(args)
            elif name == 'place':
                ok = self._exec_place(args)
            else:
                self.get_logger().warn(f'Unknown action type: {name}, skipping.')
                continue

            # Update KB after each action
            self._update_kb(name, args, ok)

            if not ok:
                self.get_logger().error(f'Action {name} failed, aborting remaining plan.')
                break

        self.get_logger().info('Plan execution finished.')
        rclpy.shutdown()

    # === Concrete executors for each action type ===

    def _exec_move(self, args):
        """Execute a move action via TurtleBotMove node.

        sas_plan example:
            (move cinemaroom livingroom)
        Parsed as:
            name='move', args=['cinemaroom', 'livingroom']
        We navigate to the destination room (last arg).
        """
        if len(args) < 2:
            self.get_logger().error(
                f'move expects at least 2 args [from_room to_room], got {args}'
            )
            return False

        from_room = args[0]
        to_room = args[-1]
        room_name = to_room.lower()

        self.get_logger().info(
            f'MOVE: from \"{from_room}\" to \"{to_room}\" → navigating to \"{room_name}\"'
        )

        # goal_room
        room_msg = String()
        room_msg.data = room_name
        self.goal_room_pub.publish(room_msg)

        # move_cmd = True
        cmd_msg = Bool()
        cmd_msg.data = True
        self._waiting_for_move = True
        self.move_cmd_pub.publish(cmd_msg)

        # wait for move_status=True
        timeout_sec = 300.0
        start_time = self.get_clock().now()

        while rclpy.ok() and self._waiting_for_move:
            rclpy.spin_once(self, timeout_sec=0.1)
            elapsed = (self.get_clock().now() - start_time).nanoseconds / 1e9
            if elapsed > timeout_sec:
                self.get_logger().error('Timed out waiting for move_status=True')
                self._waiting_for_move = False
                return False

        self.get_logger().info('Move action finished (according to move_status).')
        return True

    def _exec_pick(self, args):
        # TODO: replace Trigger with real pick service/action
        req = Trigger.Request()
        future = self.pick_client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        if not future.result() or not future.result().success:
            self.get_logger().error(f'Pick action failed: {future.result()}')
            return False
        self.get_logger().info('Pick action succeeded.')
        return True

    def _exec_place(self, args):
        # TODO: replace Trigger with real place service/action
        req = Trigger.Request()
        future = self.place_client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        if not future.result() or not future.result().success:
            self.get_logger().error(f'Place action failed: {future.result()}')
            return False
        self.get_logger().info('Place action succeeded.')
        return True

    def _update_kb(self, name, args, success: bool):
        """
        Notify KB that an action has been executed.
        For now using Trigger – replace with real KB update srv.
        """
        self.get_logger().info(f'Updating KB: action={name}, args={args}, success={success}')
        req = Trigger.Request()
        future = self.kb_update_client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        if not future.result() or not future.result().success:
            self.get_logger().warn('KB update service call failed or returned false.')


def main(args=None):
    rclpy.init(args=args)
    node = PlanExecutor()
    rclpy.spin(node)


if __name__ == '__main__':
    main()