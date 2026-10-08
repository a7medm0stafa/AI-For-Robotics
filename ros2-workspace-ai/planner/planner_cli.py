#!/usr/bin/env python3
"""MS2 planning-only CLI; ROS is imported only with --execute (MS3)."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src/tb3_planner_execution'))
from tb3_planner_execution.planning import (DEFAULT_STATE, atomic_json, default_kb_path,
    load_state, parse_goal, plan, state_lock)


def execute(request, timeout):
    import rclpy
    from std_msgs.msg import String
    rclpy.init()
    node = rclpy.create_node('planner_cli')
    replies = []
    node.create_subscription(String, 'plan_result', lambda m: replies.append(json.loads(m.data)), 10)
    pub = node.create_publisher(String, 'plan_request', 10)
    try:
        deadline = time.monotonic()+10
        while pub.get_subscription_count() == 0 and time.monotonic()<deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
        if not pub.get_subscription_count():
            raise RuntimeError('No plan executor discovered')
        pub.publish(String(data=json.dumps(request)))
        deadline = time.monotonic()+timeout
        while time.monotonic()<deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            for result in replies:
                if result.get('id') == request['id']:
                    print(json.dumps(result, indent=2))
                    return 0 if result['success'] else 1
        raise TimeoutError('Execution response timed out; executor may still be active. Inspect journal before reset/retry.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--goal', help='robot-at ROOM | holding OBJECT | in-room OBJECT ROOM')
    parser.add_argument('--kb', type=Path, default=default_kb_path())
    parser.add_argument('--reset', action='store_true', help='Explicitly reset only after robot/object state is reconciled')
    parser.add_argument('--planner', type=Path, default=Path(os.environ.get('FAST_DOWNWARD', ROOT/'.jazzy/downward/fast-downward.py')))
    parser.add_argument('--output-dir', type=Path, default=ROOT/'.jazzy/plans')
    parser.add_argument('--timeout', type=float, default=30)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--execution-timeout', type=float, default=1800)
    args = parser.parse_args()
    try:
        if args.reset:
            with state_lock(args.kb):
                journal_path = Path(str(args.kb)+'.execution.json')
                journal = json.loads(journal_path.read_text()) if journal_path.exists() else {}
                seen_ids = journal.get('seen_ids', [journal['id']] if journal.get('id') else [])
                atomic_json(args.kb, deepcopy(DEFAULT_STATE))
                atomic_json(journal_path, dict(status='succeeded', id=None, seen_ids=seen_ids, message='Explicit user reset'))
            print(f'Reset {args.kb}; this does not move the robot.')
        if not args.goal:
            if not args.reset:
                parser.error('--goal or --reset is required')
            return 0
        if args.execute and not args.kb.exists():
            raise ValueError('Initialize matching robot/KB state explicitly with --reset first')
        if args.kb.exists():
            with state_lock(args.kb):
                state = load_state(args.kb)
        else:
            state = deepcopy(DEFAULT_STATE)
        request, run = plan(state, parse_goal(args.goal), ROOT/'planner/domain.pddl', args.planner, args.output_dir, args.timeout)
        print(json.dumps(request, indent=2))
        print(f'Artifacts: {run}')
        if args.execute:
            # Executor checks the shared path; never transmit an arbitrary writable path.
            request['kb_path'] = str(args.kb.expanduser().resolve())
            return execute(request, args.execution_timeout)
        return 0
    except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
