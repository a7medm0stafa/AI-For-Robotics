#!/usr/bin/env python3
"""
Test script to verify KB persistence.
Shows KB state before and after loading from file.
"""

import os
import json

KB_STATE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "kb_state.json"
)

print("=" * 60)
print("KB Persistence Test")
print("=" * 60)

if os.path.exists(KB_STATE_FILE):
    with open(KB_STATE_FILE, 'r') as f:
        data = json.load(f)
    
    print(f"\nCurrent KB State (from {KB_STATE_FILE}):")
    print(f"  Robot Location: {data.get('robot_location')}")
    print(f"  Holding: {data.get('holding')}")
    print(f"  Objects:")
    for obj, loc in data.get('objects', {}).items():
        print(f"    {obj}: {loc}")
else:
    print(f"\nKB state file not found: {KB_STATE_FILE}")
    print("Run the planner or plan executor first to create it.")

print("=" * 60)
