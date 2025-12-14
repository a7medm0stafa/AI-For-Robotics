import rclpy
from rclpy.node import Node
import threading
import json
import os

from std_msgs.msg import Bool, String
from std_srvs.srv import Trigger

# Path to KB state file
KB_STATE_FILE = os.path.join(
    os.path.expanduser("~"),
    "AI-For-Robotics",
    "ros2-workspace-ai",
    "planner",
    "kb_state.json"
)


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
        self.goal_room_pub = self.create_publisher(String, 'goal_room', 10)
        self.move_cmd_pub = self.create_publisher(Bool, 'move_cmd', 10)
        self.move_status_sub = self.create_subscription(
            Bool, 'move_status', self._move_status_callback, 10
        )

        # Subscribe to plan ready trigger from planner
        self.plan_ready_sub = self.create_subscription(
            Bool, 'plan_ready', self._plan_ready_callback, 10
        )

        # Use threading.Event instead of a boolean flag
        self._move_complete_event = threading.Event()

        # Service clients (pick/place/KB) - optional for now
        self.pick_client = self.create_client(Trigger, '/open_manipulator/pick')
        self.place_client = self.create_client(Trigger, '/open_manipulator/place')
        self.kb_update_client = self.create_client(Trigger, '/planner/kb_update')

        # Flag to enable/disable service waiting
        self.declare_parameter('wait_for_services', False)
        self.wait_for_services = self.get_parameter('wait_for_services').get_parameter_value().bool_value

        # Publish when plan execution finishes
        self.plan_complete_pub = self.create_publisher(Bool, 'plan_complete', 10)

        # Don't auto-start execution - wait for trigger
        self.actions = []
        self._execution_thread = None
        
        self.get_logger().info('Plan executor node initialized. Waiting for plan_ready trigger...')

    def _plan_ready_callback(self, msg: Bool):
        """Triggered when planner publishes a new plan."""
        if not msg.data:
            return
        
        self.get_logger().info('Received plan_ready trigger! Loading and executing plan...')
        
        # Reload plan from file
        self.actions = self._load_plan(self.plan_file)
        self.get_logger().info(f'Loaded {len(self.actions)} actions from plan.')
        
        # Start execution in a separate thread
        if self._execution_thread is not None and self._execution_thread.is_alive():
            self.get_logger().warn('Execution already in progress, ignoring trigger.')
            return
        
        self._execution_thread = threading.Thread(target=self._execute_plan)
        self._execution_thread.start()

    def _load_kb_state(self):
        """Load current KB state from file."""
        try:
            if os.path.exists(KB_STATE_FILE):
                with open(KB_STATE_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get("robot_location"), data.get("holding"), data.get("objects", {})
            else:
                self.get_logger().warn(f'KB state file not found: {KB_STATE_FILE}')
                return "livingroom", None, {}
        except Exception as e:
            self.get_logger().error(f'Failed to load KB state: {e}')
            return "livingroom", None, {}
    
    def _save_kb_state(self, robot_loc, holding, objects):
        """Save KB state to file after action execution."""
        try:
            data = {
                "robot_location": robot_loc,
                "holding": holding,
                "objects": objects
            }
            with open(KB_STATE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            self.get_logger().info(f'Saved KB: robot={robot_loc}, holding={holding}')
            return True
        except Exception as e:
            self.get_logger().error(f'Failed to save KB state: {e}')
            return False
    
    def _apply_action_to_kb(self, action_name, args):
        """
        Apply an action to the KB and save the updated state.
        This mimics apply_action_to_kb from planner_cli.py
        """
        robot_loc, holding, objects = self._load_kb_state()
        
        if action_name == "move":
            # args: [from_room, to_room]
            if len(args) >= 2:
                robot_loc = args[-1]  # destination room
        elif action_name == "pick":
            # args: [object, room]
            if len(args) >= 1:
                obj = args[0]
                holding = obj
                if obj in objects:
                    objects[obj] = None
        elif action_name == "place":
            # args: [object, room]
            if len(args) >= 2:
                obj = args[0]
                room = args[1]
                objects[obj] = room
                holding = None
        
        # Save updated KB
        self._save_kb_state(robot_loc, holding, objects)
        return True

    def _wait_for_servers(self):
        if not self.wait_for_services:
            self.get_logger().info('Skipping service wait (wait_for_services=False)')
            return
            
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
        self.get_logger().info(f'Received move_status: {msg.data}')
        if msg.data:
            self.get_logger().info('Move completed! Setting event.')
            self._move_complete_event.set()

    def _plan_ready_callback(self, msg: Bool):
        """Triggered when planner publishes a new plan."""
        if not msg.data:
            return
        
        self.get_logger().info('Received plan_ready trigger! Loading and executing plan...')
        
        # Reload plan from file
        self.actions = self._load_plan(self.plan_file)
        self.get_logger().info(f'Loaded {len(self.actions)} actions from plan.')
        
        # Start execution in a separate thread
        if self._execution_thread is not None and self._execution_thread.is_alive():
            self.get_logger().warn('Execution already in progress, ignoring trigger.')
            return
        
        self._execution_thread = threading.Thread(target=self._execute_plan)
        self._execution_thread.start()

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

    def _execute_plan(self):
        self.get_logger().info(f'Starting execution of {len(self.actions)} actions...')
        self._wait_for_servers()
        
        for idx, action in enumerate(self.actions):
            name = action['name']
            args = action['args']
            self.get_logger().info(f'='*60)
            self.get_logger().info(f'Executing action {idx+1}/{len(self.actions)}: {name} {args}')
            self.get_logger().info(f'='*60)

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
            
            self.get_logger().info(f'Action {idx+1}/{len(self.actions)} completed successfully')

        self.get_logger().info('='*60)
        self.get_logger().info('Plan execution finished. Ready for next plan.')
        self.get_logger().info('='*60)
        # DON'T call rclpy.shutdown() here
        
        # Notify planner that execution is complete
        msg = Bool()
        msg.data = True
        self.plan_complete_pub.publish(msg)
        self.get_logger().info('Published plan_complete=True')

    # === Concrete executors for each action type ===

    def _exec_move(self, args):
        """Execute a move action via TurtleBotMove node."""
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

        # Clear the event before starting
        self._move_complete_event.clear()

        # Publish goal room
        room_msg = String()
        room_msg.data = room_name
        self.goal_room_pub.publish(room_msg)

        # Publish move command
        cmd_msg = Bool()
        cmd_msg.data = True
        self.move_cmd_pub.publish(cmd_msg)
        
        self.get_logger().info(f'Published goal_room={room_name} and move_cmd=True, waiting for move_status...')

        # Wait for the event to be set (with timeout)
        timeout_sec = 300.0
        success = self._move_complete_event.wait(timeout=timeout_sec)

        if not success:
            self.get_logger().error(f'Timed out waiting for move_status after {timeout_sec}s')
            return False

        self.get_logger().info('Move action finished (according to move_status).')
        return True

    def _exec_pick(self, args):
        """Execute pick action - calls service if available, otherwise logs and continues."""
        if not self.wait_for_services:
            self.get_logger().info(f'PICK action (skipped - services disabled): {args}')
            return True
            
        req = Trigger.Request()
        future = self.pick_client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        if not future.result() or not future.result().success:
            self.get_logger().error(f'Pick action failed: {future.result()}')
            return False
        self.get_logger().info('Pick action succeeded.')
        return True

    def _exec_place(self, args):
        """Execute place action - calls service if available, otherwise logs and continues."""
        if not self.wait_for_services:
            self.get_logger().info(f'PLACE action (skipped - services disabled): {args}')
            return True
            
        req = Trigger.Request()
        future = self.place_client.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        if not future.result() or not future.result().success:
            self.get_logger().error(f'Place action failed: {future.result()}')
            return False
        self.get_logger().info('Place action succeeded.')
        return True

    def _update_kb(self, name, args, success: bool):
        """Update KB after action execution - saves to kb_state.json file."""
        if not success:
            self.get_logger().warn(f'Action {name} failed, skipping KB update')
            return
            
        self.get_logger().info(f'Updating KB: action={name}, args={args}')
        
        # Apply action to KB file
        self._apply_action_to_kb(name, args)
        
        # Optionally also call KB update service if enabled
        if self.wait_for_services:
            req = Trigger.Request()
            future = self.kb_update_client.call_async(req)
            rclpy.spin_until_future_complete(self, future)
            if not future.result() or not future.result().success:
                self.get_logger().warn('KB update service call failed or returned false.')


def main(args=None):
    rclpy.init(args=args)
    node = PlanExecutor()
    
    # Use MultiThreadedExecutor to handle callbacks while blocking in _exec_move
    from rclpy.executors import MultiThreadedExecutor
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    
    try:
        executor.spin()
    finally:
        executor.shutdown()
        node.destroy_node()


if __name__ == '__main__':
    main()