#!/usr/bin/env python3
"""
Planner Executor Node
Reads the sas_plan file from Fast Downward and publishes commands sequentially
to the move and manipulator executor nodes.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import os
import time


class PlannerExecutorNode(Node):
    def __init__(self):
        super().__init__('planner_executor')
        
        # Publishers and Subscribers
        self.command_pub = self.create_publisher(String, '/planner/command', 10)
        self.status_sub = self.create_subscription(
            String,
            '/planner/status',
            self.status_callback,
            10
        )
        
        # State variables
        self.plan = []
        self.current_step = 0
        self.waiting_for_completion = False
        
        # Parameters
        self.declare_parameter('plan_file', '/home/ahmed/AI-For-Robotics/ros2-workspace-ai/planner/sas_plan')
        
        self.get_logger().info('Planner Executor Node started')
        
        # Wait a bit for other nodes to start, then load and execute plan
        self.create_timer(2.0, self.load_and_execute_plan_once)
    
    def load_and_execute_plan_once(self):
        """Load plan once and start execution"""
        self.destroy_timer(self.create_timer(2.0, lambda: None))  # Stop the timer
        
        plan_file = self.get_parameter('plan_file').value
        
        if self.load_plan(plan_file):
            self.get_logger().info(f'Loaded plan with {len(self.plan)} steps')
            self.execute_next_step()
        else:
            self.get_logger().error('Failed to load plan. Node will wait for manual intervention.')
    
    def load_plan(self, plan_file):
        """Load the sas_plan file"""
        try:
            if not os.path.exists(plan_file):
                self.get_logger().error(f'Plan file not found: {plan_file}')
                return False
            
            with open(plan_file, 'r') as f:
                lines = f.readlines()
            
            # Parse plan file (format: "(action arg1 arg2 ...)")
            self.plan = []
            for line in lines:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith(';'):
                    continue
                # Parse action from format: "(move room1 room2)"
                if line.startswith('(') and line.endswith(')'):
                    # Remove parentheses and split
                    action_parts = line[1:-1].split()
                    if action_parts:
                        self.plan.append(action_parts)
            
            return len(self.plan) > 0
        
        except Exception as e:
            self.get_logger().error(f'Error loading plan: {str(e)}')
            return False
    
    def execute_next_step(self):
        """Execute the next step in the plan"""
        if self.current_step >= len(self.plan):
            self.get_logger().info('🎉 Plan execution completed!')
            return
        
        action = self.plan[self.current_step]
        self.get_logger().info(f'Step {self.current_step + 1}/{len(self.plan)}: {action}')
        
        # Format: action_type arg1 arg2 ...
        # Examples: ['move', 'kitchen', 'bedroom'], ['pick', 'cup', 'kitchen']
        command_msg = String()
        command_msg.data = ' '.join(action)
        
        self.command_pub.publish(command_msg)
        self.waiting_for_completion = True
        self.get_logger().info(f'→ Published command: {command_msg.data}')
    
    def status_callback(self, msg):
        """Handle status updates from executor nodes"""
        if not self.waiting_for_completion:
            return
        
        status = msg.data
        self.get_logger().info(f'← Received status: {status}')
        
        # Check if current action completed
        current_action = self.plan[self.current_step]
        action_type = current_action[0]
        
        # Status format: "done move kitchen bedroom" or "done pick cup kitchen"
        if status.startswith(f'done {action_type}'):
            self.waiting_for_completion = False
            self.current_step += 1
            
            # Wait a bit before next action
            time.sleep(0.5)
            self.execute_next_step()
        
        elif status.startswith('failed'):
            self.get_logger().error(f'Action failed: {status}')
            self.get_logger().error('Stopping plan execution')
            self.waiting_for_completion = False


def main(args=None):
    rclpy.init(args=args)
    node = PlannerExecutorNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
