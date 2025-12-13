#!/usr/bin/env python3
"""
KB Update Service Node

This service receives action execution updates from the plan executor
and updates the knowledge base accordingly by modifying the kb_state.json file.
"""

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
import sys
import os
import json

# Import the planner KB utilities
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from planner_cli import KB_STATE_FILE, apply_action_to_kb


class KBUpdateService(Node):
    def __init__(self):
        super().__init__('kb_update_service')
        
        # Load initial KB state from file
        self.load_kb_state()
        
        # Create service
        self.srv = self.create_service(
            Trigger,
            '/planner/kb_update',
            self.kb_update_callback
        )
        
        # Store last action for update (will be passed via custom message in future)
        self.last_action = None
        self.last_args = None
        
        self.get_logger().info('KB Update Service started')
        self.get_logger().info(f'Initial KB state:')
        self.get_logger().info(f'  Robot at: {self.robot_location}')
        self.get_logger().info(f'  Holding: {self.holding}')
        self.get_logger().info(f'  Objects: {self.objects}')
    
    def load_kb_state(self):
        """Load KB state from JSON file."""
        try:
            if os.path.exists(KB_STATE_FILE):
                with open(KB_STATE_FILE, 'r') as f:
                    data = json.load(f)
                    self.robot_location = data.get("robot_location", "livingroom")
                    self.holding = data.get("holding", None)
                    self.objects = data.get("objects", {})
                self.get_logger().info(f'Loaded KB from {KB_STATE_FILE}')
            else:
                # Initialize with defaults
                self.robot_location = "livingroom"
                self.holding = None
                self.objects = {}
                self.get_logger().warn(f'KB file not found, using defaults')
        except Exception as e:
            self.get_logger().error(f'Failed to load KB: {e}')
            self.robot_location = "livingroom"
            self.holding = None
            self.objects = {}
    
    def save_kb_state(self):
        """Save KB state to JSON file."""
        try:
            data = {
                "robot_location": self.robot_location,
                "holding": self.holding,
                "objects": self.objects
            }
            with open(KB_STATE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            self.get_logger().info(f'Saved KB to {KB_STATE_FILE}')
            return True
        except Exception as e:
            self.get_logger().error(f'Failed to save KB: {e}')
            return False
    
    def kb_update_callback(self, request, response):
        """
        Update KB based on last executed action.
        For now using Trigger service - ideally should use custom message.
        
        The plan executor should publish the action details separately,
        or we need a custom service definition.
        """
        self.get_logger().info('KB update request received')
        
        # TODO: When you define UpdateKB.srv with action details, parse here
        # For now, we assume the plan_executor sets action info via a topic
        # or we just reload from file (since planner_cli saves after execution)
        
        # Reload KB from file (in case planner_cli updated it)
        self.load_kb_state()
        
        self.get_logger().info(f'KB reloaded - Robot at: {self.robot_location}, Holding: {self.holding}')
        
        response.success = True
        response.message = f'KB updated: robot at {self.robot_location}'
        return response
    
    def update_kb_with_action(self, action_name, args):
        """
        Apply an action to the KB and save to file.
        This will be called when we have custom service messages.
        """
        action_str = f"({action_name} {' '.join(args)})"
        self.get_logger().info(f'Applying action to KB: {action_str}')
        
        try:
            self.robot_location, self.holding, self.objects = apply_action_to_kb(
                action_str, self.robot_location, self.holding, self.objects
            )
            self.get_logger().info(f'KB updated - Robot: {self.robot_location}, Holding: {self.holding}')
            return self.save_kb_state()
        except Exception as e:
            self.get_logger().error(f'Failed to apply action to KB: {e}')
            return False


def main(args=None):
    rclpy.init(args=args)
    node = KBUpdateService()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down KB update service')
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
