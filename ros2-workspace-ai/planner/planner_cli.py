#!/usr/bin/env python3
"""
planner_cli.py - Fast Downward with ROS 2 integration

After generating a plan, this script triggers the plan_executor node.
"""

from collections import deque
import json
import os
import subprocess
import shlex
import sys
import time

# ROS 2 imports
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool

# ------------------ Knowledge Base ------------------
rooms = ["livingroom", "diningroom", "bedroom", 
         "storageroom", "studyroom", "bathroom"]

# connectivity as undirected edges (we will add both directions automatically)
connectivity = {
    ("livingroom", "diningroom"),
    ("livingroom", "studyroom"),
    ("diningroom", "storageroom"),
    ("diningroom", "bathroom"),
    ("studyroom", "bedroom"),
    
}

# objects -> initial room (note: remove leading/trailing spaces in room names)
objects = {
    "cup": "diningroom",
    "book": "studyroom",
    "remote": "livingroom",
    "phone": "livingroom",
    "panadol": "bedroom", 
    "pillow": "bedroom",
    "chewy": "storageroom"
}

robot_location = "livingroom"  # Robot spawns at the door
holding = None
gripper_state = "open"  # Track gripper state: "open" or "closed"

# files
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DOMAIN_FILENAME = os.path.join(SCRIPT_DIR, "domain.pddl")
PROBLEM_FILENAME = os.path.join(SCRIPT_DIR, "problem.pddl")
# Ensure Fast Downward writes sas_plan into the planner folder
PLAN_OUTPUT_FILENAME = os.path.join(SCRIPT_DIR, "sas_plan")

# ------------------ KB Persistence Functions ------------------
KB_STATE_FILE = os.path.join(SCRIPT_DIR, "kb_state.json")

def load_kb_from_file():
    """Load KB state from JSON file if it exists."""
    global robot_location, holding, objects, gripper_state
    if os.path.exists(KB_STATE_FILE):
        try:
            with open(KB_STATE_FILE, 'r') as f:
                data = json.load(f)
                robot_location = data.get("robot_location", robot_location)
                holding = data.get("holding", holding)
                objects = data.get("objects", objects)
                gripper_state = data.get("gripper_state", "open")
            print(f"Loaded KB from {KB_STATE_FILE}")
        except Exception as e:
            print(f"Warning: Failed to load KB from file: {e}")
            print("Using default KB values.")
    else:
        print("No KB state file found, using default values.")
        save_kb_to_file()  # Create initial file

def save_kb_to_file():
    """Save current KB state to JSON file."""
    global robot_location, holding, objects, gripper_state
    try:
        data = {
            "robot_location": robot_location,
            "holding": holding,
            "objects": objects,
            "gripper_state": gripper_state
        }
        with open(KB_STATE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved KB to {KB_STATE_FILE}")
    except Exception as e:
        print(f"Warning: Failed to save KB to file: {e}")

def reset_kb_to_default():
    """Reset KB to default initial state."""
    global robot_location, holding, objects, gripper_state
    robot_location = "livingroom"  # Robot spawns in living room
    holding = None
    gripper_state = "open"
    objects = {
        "cup": "diningroom",
        "book": "studyroom",
        "remote": "livingroom",
        "phone": "livingroom",
        "panadol": "bedroom",
        "pillow": "bedroom",
        "chewy": "storageroom"
    }
    save_kb_to_file()
    print("✅ KB reset to default state (robot at 'livingroom', holding nothing, gripper open).")

# Candidate fast-downward paths (keep FAST_DOWNWARD env var first)
COMMON_FD_PATHS = [
    os.environ.get("FAST_DOWNWARD"),  # user-provided env var (highest priority)
    os.path.join(os.path.expanduser("~"), "ros2-workspace-ai", "planner", "downward", "fast-downward.py"),
    "/usr/local/bin/fast-downward.py",
    "/usr/bin/fast-downward.py",
    "/mnt/data/downward/fast-downward.py"
]


# ------------------ Domain text (optional fallback writing) ------------------
# If you want the script to write a domain file for convenience, keep this string.
domain_text = """(define (domain apartment)
  (:requirements :strips)
  (:predicates
    (room ?r)
    (object ?o)
    (robot-at ?r)
    (in-room ?o ?r)
    (connected ?r1 ?r2)
    (holding ?o)
    (empty-hand)
  )

  ;; MOVE
  (:action move
    :parameters (?from ?to)
    :precondition (and (robot-at ?from) (connected ?from ?to))
    :effect (and (not (robot-at ?from)) (robot-at ?to))
  )

  ;; PICK
  (:action pick
    :parameters (?o ?r)
    :precondition (and (robot-at ?r) (in-room ?o ?r) (empty-hand))
    :effect (and (holding ?o) (not (in-room ?o ?r)) (not (empty-hand)))
  )

  ;; PLACE
  (:action place
    :parameters (?o ?r)
    :precondition (and (robot-at ?r) (holding ?o))
    :effect (and (in-room ?o ?r) (empty-hand) (not (holding ?o)))
  )
)
"""

def ensure_domain_file():
    if not os.path.exists(DOMAIN_FILENAME):
        with open(DOMAIN_FILENAME, "w") as f:
            f.write(domain_text)
        print(f"Wrote default domain to '{DOMAIN_FILENAME}' (you can replace it with your own domain.pddl).")

# ------------------ Problem writer ------------------
def write_problem(goal_pddl, robot_loc, holding_obj, objects_map, rooms_list, connectivity_set, filename=PROBLEM_FILENAME):
    # sanitize objects and room names (strip spaces)
    rooms_clean = [r.strip() for r in rooms_list]
    objs_clean = {o.strip(): (v.strip() if isinstance(v, str) else v) if v is not None else None
                  for o,v in objects_map.items()}
    objs_decl = " ".join(rooms_clean + list(objs_clean.keys()))
    inits = []
    for r in rooms_clean:
        inits.append(f"(room {r})")
    for o in objs_clean.keys():
        inits.append(f"(object {o})")
    inits.append(f"(robot-at {robot_loc})")
    if holding_obj is None:
        inits.append("(empty-hand)")
    else:
        inits.append(f"(holding {holding_obj})")
    for o, r in objs_clean.items():
        if r is not None:
            inits.append(f"(in-room {o} {r})")
    # add both directions for connectivity; also normalize names
    for a,b in connectivity_set:
        a_s, b_s = str(a).strip(), str(b).strip()
        inits.append(f"(connected {a_s} {b_s})")
        inits.append(f"(connected {b_s} {a_s})")
    problem = f"""(define (problem apartment-example)
  (:domain apartment)

  (:objects
    {objs_decl}
  )

  (:init
    {' '.join(inits)}
  )

  (:goal
    {goal_pddl}
  )
)
"""
    with open(filename, "w") as f:
        f.write(problem)
    print(f"Wrote problem file to: {filename}")

# ------------------ Fast Downward invocation & plan parsing ------------------
def find_fast_downward():
    # return first valid path
    for p in COMMON_FD_PATHS:
        if not p:
            continue
        if os.path.exists(p) and os.access(p, os.R_OK):
            return p
    return None

def call_fast_downward(domain_file, problem_file, fd_path, timeout=30):
    """
    Call fast-downward.py with domain and problem files and return stdout text.
    Uses lmcut astar. Runs the planner with cwd=SCRIPT_DIR so sas_plan is written
    inside the planner folder.
    """
    # remove previous plan file in script folder
    if os.path.exists(PLAN_OUTPUT_FILENAME):
        try:
            os.remove(PLAN_OUTPUT_FILENAME)
        except Exception:
            pass

    # use absolute paths for translator arguments
    domain_abs = os.path.abspath(domain_file)
    problem_abs = os.path.abspath(problem_file)

    cmd = [
        sys.executable, fd_path,
        domain_abs,
        problem_abs,
        "--search",
        "astar(lmcut())"
    ]
    print("Calling Fast Downward:", " ".join(shlex_quote(x) for x in cmd))
    try:
        # IMPORTANT: set cwd so FD writes sas_plan to the planner directory
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=SCRIPT_DIR)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Fast Downward timed out.")

    if proc.returncode != 0:
        raise RuntimeError(f"Fast Downward failed (rc={proc.returncode}). stderr:\n{proc.stderr}\nstdout:\n{proc.stdout}")

    return proc.stdout

def shlex_quote(s):
    return shlex.quote(s)

def parse_fd_plan_from_stdout(stdout_text):
    """
    Fast Downward prints plan steps in the stdout and/or writes sas_plan (file).
    We'll try to:
     - look for lines that start with '(' and treat them as actions
     - if not found, try to read 'sas_plan' file
    Return: list of action strings like "(move livingroom kitchen)"
    """
    actions = []
    for line in stdout_text.splitlines():
        line = line.strip()
        if line.startswith("(") and line.endswith(")"):
            actions.append(line)
        # some FD versions include 'step' prefixes; collect '(' lines anyway
    if not actions:
        # try to read sas_plan file if it exists
        if os.path.exists(PLAN_OUTPUT_FILENAME):
            with open(PLAN_OUTPUT_FILENAME, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and line.startswith(";"):
                        continue
                    if line.startswith("(") and line.endswith(")"):
                        actions.append(line)
    return actions

# ------------------ Apply action to KB ------------------
def apply_action_to_kb(action_str, robot_loc, holding_obj, objects_map):
    tokens = action_str.strip("()").split()
    act = tokens[0]
    if act == "move":
        _, frm, to = tokens
        robot_loc = to
    elif act == "pick":
        _, obj, room = tokens
        holding_obj = obj
        objects_map[obj] = None
    elif act == "place":
        _, obj, room = tokens
        objects_map[obj] = room
        holding_obj = None
    else:
        raise ValueError("Unknown/unsupported action: " + action_str)
    return robot_loc, holding_obj, objects_map

def show_kb(robot_loc, holding_obj, objects_map):
    print("\n=== Current KB ===")
    print("Robot at:", robot_loc)
    print("Holding:", holding_obj)
    print("Objects:")
    for o,r in objects_map.items():
        print(f"  {o}: {r}")
    print("==================\n")

# ------------------ Goal parser ------------------
def parse_goal_input(goal_input):
    t = goal_input.strip().split()
    if len(t) == 2 and t[0] in ("robot-at", "holding"):
        return (t[0], [t[1]])
    if len(t) == 3 and t[0] == "in-room":
        return ("in-room", [t[1], t[2]])
    raise ValueError("Goal must be 'robot-at ROOM' or 'in-room OBJ ROOM' or 'holding OBJ'")

# ------------------ ROS 2 Integration ------------------
class PlannerNode(Node):
    """Minimal ROS 2 node to trigger plan execution."""
    
    def __init__(self):
        super().__init__('planner_cli_node')
        # Publisher to signal plan executor
        self.plan_ready_pub = self.create_publisher(Bool, 'plan_ready', 10)
        
        # Subscribe to execution completion
        self.execution_complete = False
        self.plan_complete_sub = self.create_subscription(
            Bool, 'plan_complete', self._plan_complete_callback, 10
        )
        
        self.get_logger().info('Planner node initialized.')
    
    def _plan_complete_callback(self, msg):
        if msg.data:
            self.execution_complete = True
            self.get_logger().info('Plan execution completed!')
    
    def trigger_execution(self):
        self.execution_complete = False
        msg = Bool()
        msg.data = True
        self.plan_ready_pub.publish(msg)
        self.get_logger().info('Published plan_ready=True to trigger executor.')
    
    def wait_for_completion(self, timeout=300.0):
        """Wait for plan execution to complete."""
        start = time.time()
        
        while not self.execution_complete:
            rclpy.spin_once(self, timeout_sec=0.1)
            if time.time() - start > timeout:
                self.get_logger().warn('Timeout waiting for plan completion!')
                return False
        
        return True

# ------------------ CLI loop with ROS integration ------------------
def cli_loop():
    global robot_location, holding, objects, rooms, connectivity
    
    rclpy.init()
    planner_node = PlannerNode()
    
    # Auto-reset KB to default state on startup
    print("\n🔄 Auto-resetting KB to default state...")
    reset_kb_to_default()
    
    # Load KB from file at startup (will load the just-reset values)
    load_kb_from_file()
    
    ensure_domain_file()
    fd_path = find_fast_downward()
    if not fd_path:
        print("\nERROR: Fast Downward not found.\n")
        print("Please install Fast Downward and set environment variable FAST_DOWNWARD to the path of fast-downward.py,")
        print("or place fast-downward.py in one of the common locations. Example:")
        print("  export FAST_DOWNWARD=/downward/fast-downward.py")
        print("Then re-run this script.")
        sys.exit(1)

    print(f"Using Fast Downward at: {fd_path}")
    print("Simple Fast-Downward-only planner CLI. Type 'help' for commands.")
    last_goal_pddl = "(robot-at livingroom)"
    
    try:
        while True:
            show_kb(robot_location, holding, objects)
            user = input("Enter goal (e.g. 'in-room cup bedroom'), or command: ").strip()
            if user == "quit":
                print("Bye.")
                break
            if user == "help":
                print("Commands: help, write_problem, reset_kb, quit")
                print("Goals: robot-at ROOM   |   in-room OBJ ROOM   |   holding OBJ")
                continue
            if user == "write_problem":
                # write problem using last_goal_pddl
                write_problem(last_goal_pddl, robot_location, holding, objects, rooms, connectivity)
                continue
            if user == "reset_kb":
                reset_kb_to_default()
                load_kb_from_file()
                continue
            try:
                goal_parsed = parse_goal_input(user)
            except Exception as e:
                print("Bad goal:", e)
                continue

            # convert parsed goal to PDDL string
            if goal_parsed[0] == "robot-at":
                last_goal_pddl = f"(robot-at {goal_parsed[1][0]})"
            elif goal_parsed[0] == "in-room":
                last_goal_pddl = f"(in-room {goal_parsed[1][0]} {goal_parsed[1][1]})"
            else:
                last_goal_pddl = f"(holding {goal_parsed[1][0]})"

            # write problem.pddl for Fast Downward
            write_problem(last_goal_pddl, robot_location, holding, objects, rooms, connectivity, filename=PROBLEM_FILENAME)

            # call Fast Downward (will raise if failure)
            try:
                stdout = call_fast_downward(DOMAIN_FILENAME, PROBLEM_FILENAME, fd_path, timeout=60)
            except Exception as e:
                print("Fast Downward error:", e)
                continue

            # parse plan
            actions = parse_fd_plan_from_stdout(stdout)
            if not actions:
                print("No plan found by Fast Downward (or plan file empty). Check planner stdout for details.")
                print("Fast Downward stdout:")
                print(stdout)
                continue

            print("\nPlan (Fast Downward):")
            for i, a in enumerate(actions):
                print(f" {i+1}. {a}")

            # Trigger plan executor
            print("\n>>> Triggering plan executor node...")
            planner_node.trigger_execution()
            
            print(">>> Waiting for execution to complete...")
            success = planner_node.wait_for_completion(timeout=300.0)
            
            if success:
                # Reload KB from file (executor updated it)
                load_kb_from_file()
                print(">>> Execution complete! KB has been reloaded.\n")
            else:
                print(">>> Execution timeout or failed.\n")
    
    finally:
        planner_node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    cli_loop()