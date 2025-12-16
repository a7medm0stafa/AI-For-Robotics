import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup, MutuallyExclusiveCallbackGroup
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

        # Callback groups for concurrent execution
        self.callback_group = ReentrantCallbackGroup()

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
            Bool, 'move_status', self._move_status_callback, 10,
            callback_group=self.callback_group
        )

        # Subscribe to plan ready trigger
        self.plan_ready_sub = self.create_subscription(
            Bool, 'plan_ready', self._plan_ready_callback, 10,
            callback_group=self.callback_group
        )

        # Threading event for move completion
        self._move_complete_event = threading.Event()

        # Service clients for gripper control
        self.open_gripper_client = self.create_client(
            Trigger, 'open_gripper', callback_group=self.callback_group
        )
        self.close_gripper_client = self.create_client(
            Trigger, 'close_gripper', callback_group=self.callback_group
        )

        # Flag to enable/disable gripper services
        self.declare_parameter('use_gripper', True)
        self.use_gripper = self.get_parameter('use_gripper').get_parameter_value().bool_value

        # Publish when plan execution finishes
        self.plan_complete_pub = self.create_publisher(Bool, 'plan_complete', 10)

        self.actions = []
        self._execution_thread = None
        
        self.get_logger().info('Plan executor initialized. Waiting for plan_ready...')

    def _plan_ready_callback(self, msg: Bool):
        """Triggered when planner publishes a new plan."""
        if not msg.data:
            return
        
        self.get_logger().info('Received plan_ready! Loading plan...')
        
        self.actions = self._load_plan(self.plan_file)
        self.get_logger().info(f'Loaded {len(self.actions)} actions.')
        
        if self._execution_thread is not None and self._execution_thread.is_alive():
            self.get_logger().warn('Execution in progress, ignoring.')
            return
        
        self._execution_thread = threading.Thread(target=self._execute_plan)
        self._execution_thread.start()

    def _load_kb_state(self):
        """Load KB state from file."""
        try:
            if os.path.exists(KB_STATE_FILE):
                with open(KB_STATE_FILE, 'r') as f:
                    data = json.load(f)
                    return (
                        data.get("robot_location"), 
                        data.get("holding"), 
                        data.get("objects", {}),
                        data.get("gripper_state", "open")
                    )
            else:
                self.get_logger().warn(f'KB file not found: {KB_STATE_FILE}')
                return "outside", None, {}, "open"
        except Exception as e:
            self.get_logger().error(f'Failed to load KB: {e}')
            return "outside", None, {}, "open"
    
    def _save_kb_state(self, robot_loc, holding, objects, gripper_state):
        """Save KB state to file."""
        try:
            data = {
                "robot_location": robot_loc,
                "holding": holding,
                "objects": objects,
                "gripper_state": gripper_state
            }
            with open(KB_STATE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            self.get_logger().info(
                f'KB saved: robot={robot_loc}, holding={holding}, gripper={gripper_state}'
            )
            return True
        except Exception as e:
            self.get_logger().error(f'Failed to save KB: {e}')
            return False
    
    def _apply_action_to_kb(self, action_name, args):
        """Apply action to KB and save."""
        robot_loc, holding, objects, gripper_state = self._load_kb_state()
        
        if action_name == "move":
            if len(args) >= 2:
                robot_loc = args[-1]
        elif action_name == "pick":
            if len(args) >= 1:
                obj = args[0]
                holding = obj
                if obj in objects:
                    objects[obj] = None
                gripper_state = "closed"
        elif action_name == "place":
            if len(args) >= 2:
                obj = args[0]
                room = args[1]
                objects[obj] = room
                holding = None
                gripper_state = "open"
        
        self._save_kb_state(robot_loc, holding, objects, gripper_state)
        return True

    def _wait_for_gripper_services(self):
        """Wait for gripper services to be available."""
        if not self.use_gripper:
            self.get_logger().info('Gripper disabled (use_gripper=False)')
            return
            
        for name, client in [
            ('open_gripper', self.open_gripper_client),
            ('close_gripper', self.close_gripper_client),
        ]:
            self.get_logger().info(f'Waiting for {name} service...')
            if not client.wait_for_service(timeout_sec=10.0):
                self.get_logger().warn(f'{name} not available after 10s')
            else:
                self.get_logger().info(f'✅ {name} ready')

    # === Callbacks ===

    def _move_status_callback(self, msg: Bool):
        """Receive move completion status."""
        self.get_logger().info(f'📬 Received move_status callback: {msg.data}')
        if msg.data:
            self.get_logger().info('🔔 Setting move_complete_event')
            self._move_complete_event.set()
        else:
            self.get_logger().warn('⚠️ Move failed, but setting event anyway')
            self._move_complete_event.set()  # Set even on failure so we don't hang

    def _load_plan(self, filepath):
        """Parse sas_plan file."""
        actions = []
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(';'):
                        continue

                    if line.startswith('(') and line.endswith(')'):
                        line = line[1:-1]

                    parts = line.split()
                    if not parts:
                        continue

                    action_name = parts[0].lower()
                    args = [p.lower() for p in parts[1:]]
                    actions.append({'name': action_name, 'args': args})
        except Exception as e:
            self.get_logger().error(f'Failed to load plan: {e}')
        return actions

    def _execute_plan(self):
        """Execute loaded plan."""
        self.get_logger().info(f'Executing {len(self.actions)} actions...')
        self._wait_for_gripper_services()
        
        for idx, action in enumerate(self.actions):
            name = action['name']
            args = action['args']
            self.get_logger().info('='*60)
            self.get_logger().info(f'Action {idx+1}/{len(self.actions)}: {name} {args}')
            self.get_logger().info('='*60)

            ok = False
            if name == 'move':
                ok = self._exec_move(args)
            elif name == 'pick':
                ok = self._exec_pick(args)
            elif name == 'place':
                ok = self._exec_place(args)
            else:
                self.get_logger().warn(f'Unknown action: {name}')
                continue

            self._update_kb(name, args, ok)

            if not ok:
                self.get_logger().error(f'Action {name} failed! Aborting.')
                break
            
            self.get_logger().info(f'✅ Action {idx+1} completed')

        self.get_logger().info('='*60)
        self.get_logger().info('Plan execution finished.')
        self.get_logger().info('='*60)
        
        msg = Bool()
        msg.data = True
        self.plan_complete_pub.publish(msg)

    # === Concrete executors for each action type ===

    def _exec_move(self, args):
        """Execute move action."""
        if len(args) < 2:
            self.get_logger().error(f'move needs [from to], got {args}')
            return False

        from_room = args[0]
        to_room = args[-1]

        self.get_logger().info(f'MOVE: {from_room} → {to_room}')

        self._move_complete_event.clear()

        room_msg = String()
        room_msg.data = to_room
        self.goal_room_pub.publish(room_msg)

        cmd_msg = Bool()
        cmd_msg.data = True
        self.move_cmd_pub.publish(cmd_msg)
        
        self.get_logger().info(f'Published goal_room={to_room}, waiting...')

        success = self._move_complete_event.wait(timeout=300.0)

        if not success:
            self.get_logger().error('Move timed out after 300s')
            return False

        self.get_logger().info('✅ Move completed')
        return True

    def _exec_pick(self, args):
        """Execute pick action - close gripper."""
        if len(args) < 2:
            self.get_logger().error(f'pick needs [object room], got {args}')
            return False
            
        obj = args[0]
        room = args[1]
        
        self.get_logger().info(f'PICK: {obj} from {room}')
        
        if not self.use_gripper:
            self.get_logger().info('Gripper disabled, simulating pick')
            return True
            
        req = Trigger.Request()
        future = self.close_gripper_client.call_async(req)
        
        # Wait for future without spinning (executor is already spinning in main thread)
        import time
        timeout = 10.0
        start = time.time()
        while not future.done() and (time.time() - start) < timeout:
            time.sleep(0.1)
        
        if not future.done():
            self.get_logger().error('Close gripper timeout')
            return False
            
        result = future.result()
        if not result or not result.success:
            self.get_logger().error(f'Close gripper failed: {result.message if result else "no response"}')
            return False
            
        self.get_logger().info(f'✅ Picked {obj}')
        return True

    def _exec_place(self, args):
        """Execute place action - open gripper."""
        if len(args) < 2:
            self.get_logger().error(f'place needs [object room], got {args}')
            return False
            
        obj = args[0]
        room = args[1]
        
        self.get_logger().info(f'PLACE: {obj} in {room}')
        
        if not self.use_gripper:
            self.get_logger().info('Gripper disabled, simulating place')
            return True
            
        req = Trigger.Request()
        future = self.open_gripper_client.call_async(req)
        
        # Wait for future without spinning (executor is already spinning in main thread)
        import time
        timeout = 10.0
        start = time.time()
        while not future.done() and (time.time() - start) < timeout:
            time.sleep(0.1)
        
        if not future.done():
            self.get_logger().error('Open gripper timeout')
            return False
            
        result = future.result()
        if not result or not result.success:
            self.get_logger().error(f'Open gripper failed: {result.message if result else "no response"}')
            return False
            
        self.get_logger().info(f'✅ Placed {obj} in {room}')
        return True

    def _update_kb(self, name, args, success: bool):
        """Update KB after action."""
        if not success:
            self.get_logger().warn(f'Skipping KB update (action failed)')
            return
            
        self.get_logger().info(f'Updating KB: {name} {args}')
        self._apply_action_to_kb(name, args)


def main(args=None):
    rclpy.init(args=args)
    node = PlanExecutor()
    
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