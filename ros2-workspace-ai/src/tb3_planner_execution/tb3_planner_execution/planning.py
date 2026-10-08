"""ROS-independent TA planning/state reference. Planning never changes the KB."""
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import uuid

ROOMS = ('livingroom', 'diningroom', 'bedroom', 'storageroom', 'studyroom', 'bathroom')
EDGES = {('livingroom', 'diningroom'), ('livingroom', 'studyroom'),
         ('diningroom', 'storageroom'), ('diningroom', 'bathroom'), ('studyroom', 'bedroom')}
DEFAULT_STATE = dict(robot_location='livingroom', holding=None, gripper_state='open', objects={
    'cup': 'diningroom', 'book': 'studyroom', 'remote': 'livingroom', 'phone': 'livingroom',
    'panadol': 'bedroom', 'pillow': 'bedroom', 'chewy': 'storageroom'})


def default_kb_path():
    return Path(os.environ.get('TB3_KB_PATH', str(Path.home() / '.local/state/tb3_course/kb.json'))).expanduser()


def validate_state(state):
    if state['robot_location'] not in ROOMS or set(state['objects']) != set(DEFAULT_STATE['objects']):
        raise ValueError('Invalid robot location or object vocabulary')
    held = state['holding']
    if held is not None and held not in state['objects']:
        raise ValueError('Unknown held object')
    for obj, room in state['objects'].items():
        if (obj == held and room is not None) or (obj != held and room not in ROOMS):
            raise ValueError('Each object must be in one room or held')
    if state['gripper_state'] != ('closed' if held else 'open'):
        raise ValueError('Gripper state contradicts holding')
    return state


def load_state(path):
    return validate_state(json.loads(Path(path).read_text()))


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name+'.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def state_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with Path(str(path)+'.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('KB is busy; another execution/reset is active') from exc
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def parse_goal(text):
    parts = text.lower().split()
    if len(parts) == 2 and parts[0] == 'robot-at' and parts[1] in ROOMS:
        return parts
    if len(parts) == 2 and parts[0] == 'holding' and parts[1] in DEFAULT_STATE['objects']:
        return parts
    if len(parts) == 3 and parts[0] == 'in-room' and parts[1] in DEFAULT_STATE['objects'] and parts[2] in ROOMS:
        return parts
    raise ValueError('Expected robot-at ROOM, holding OBJECT, or in-room OBJECT ROOM')


def goal_satisfied(state, goal):
    goal = parse_goal(' '.join(goal))
    if goal[0] == 'robot-at':
        return state['robot_location'] == goal[1]
    if goal[0] == 'holding':
        return state['holding'] == goal[1]
    return state['objects'][goal[1]] == goal[2]


def parse_plan(text):
    actions = []
    for line in text.splitlines():
        line = line.split(';', 1)[0].strip()
        if not line:
            continue
        if not re.fullmatch(r'\((move|pick|place) [a-z][a-z0-9_-]* [a-z][a-z0-9_-]*\)', line):
            raise ValueError(f'Malformed/unknown plan action: {line}')
        actions.append(line[1:-1].split())
    return actions


def transition(state, action, edges=EDGES):
    validate_state(state)
    if not isinstance(action, (list, tuple)) or len(action) != 3:
        raise ValueError('An action must have a name and exactly two arguments')
    name, a, b = action
    new = deepcopy(state)
    if name == 'move' and a in ROOMS and b in ROOMS:
        valid = state['robot_location'] == a and ((a, b) in edges or (b, a) in edges)
        new['robot_location'] = b
    elif name == 'pick' and a in state['objects'] and b in ROOMS:
        valid = state['robot_location'] == b and state['objects'][a] == b and state['holding'] is None
        new.update(holding=a, gripper_state='closed')
        new['objects'][a] = None
    elif name == 'place' and a in state['objects'] and b in ROOMS:
        valid = state['robot_location'] == b and state['holding'] == a
        new.update(holding=None, gripper_state='open')
        new['objects'][a] = b
    else:
        raise ValueError(f'Unknown action/arguments: {action}')
    if not valid:
        raise ValueError(f'Action precondition failed: {action}')
    return validate_state(new)


def validate_plan(state, actions, goal, edges=EDGES):
    for action in actions:
        state = transition(state, action, edges)
    if not goal_satisfied(state, goal):
        raise ValueError('Plan does not achieve the requested goal')
    return state


def problem_text(state, goal, edges=EDGES):
    validate_state(state)
    goal = parse_goal(' '.join(goal))
    facts = [f'(room {r})' for r in ROOMS] + [f'(object {o})' for o in state['objects']]
    facts += [f"(robot-at {state['robot_location']})"]
    facts += [f"(holding {state['holding']})" if state['holding'] else '(empty-hand)']
    facts += [f'(in-room {o} {r})' for o, r in state['objects'].items() if r is not None]
    for a, b in sorted(edges):
        if a not in ROOMS or b not in ROOMS:
            raise ValueError('Unknown room in connectivity')
        facts += [f'(connected {a} {b})', f'(connected {b} {a})']
    return '(define (problem course) (:domain apartment)\n(:objects '+ ' '.join(ROOMS + tuple(state['objects'])) + ')\n(:init '+ ' '.join(facts)+')\n(:goal ('+' '.join(goal)+')))\n'


class NoSolution(RuntimeError):
    """Planner proved that no solution exists."""


class IncompleteSearch(RuntimeError):
    """No plan was found, but the planner did not certify unsolvability."""


def plan(state, goal, domain, executable, output_dir, timeout=30, edges=EDGES):
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='plan-', dir=output_dir))
    (run/'problem.pddl').write_text(problem_text(state, goal, edges))
    command = [sys.executable, str(Path(executable).resolve()), '--plan-file', str(run/'sas_plan'),
               str(Path(domain).resolve()), str(run/'problem.pddl'), '--search', 'astar(lmcut())']
    with (run/'planner.log').open('w') as log:
        process = subprocess.Popen(command, cwd=run, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise TimeoutError(f'Planner timed out; see {run}') from exc
    if code in (10, 11):
        raise NoSolution(f'No solution (exit {code}); see {run}')
    if code == 12:
        raise IncompleteSearch(f'Incomplete search; no plan found, unsolvability not proved; see {run}')
    if code != 0:
        raise RuntimeError(f'Planner failed (exit {code}); see {run}')
    actions = parse_plan((run/'sas_plan').read_text())
    validate_plan(state, actions, goal, edges)
    request = dict(id=str(uuid.uuid4()), initial_state=state, goal=goal, actions=actions)
    atomic_json(run/'request.json', request)
    return request, run
