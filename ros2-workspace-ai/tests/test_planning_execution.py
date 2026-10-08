from copy import deepcopy
import json
from pathlib import Path
import sys
import uuid
import pytest
from tb3_planner_execution.planning import (DEFAULT_STATE, NoSolution, IncompleteSearch, atomic_json, load_state,
    parse_goal, parse_plan, plan, state_lock, transition, validate_plan)
from tb3_planner_execution.execution import execute_request

ROOT = Path(__file__).resolve().parents[1]
FD = ROOT/'planner/downward/fast-downward.py'


@pytest.mark.parametrize('goal', ['robot-at bedroom', 'in-room cup bedroom', 'holding book', 'robot-at livingroom'])
def test_real_planner(tmp_path, goal):
    if not (FD.parent/'builds/release/bin/downward').exists():
        pytest.skip('Build pinned Fast Downward first')
    state = deepcopy(DEFAULT_STATE)
    request, run = plan(state, parse_goal(goal), ROOT/'planner/domain.pddl', FD, tmp_path)
    validate_plan(state, request['actions'], request['goal'])
    assert state == DEFAULT_STATE
    assert (run/'request.json').exists()
    if goal == 'robot-at livingroom':
        assert request['actions'] == []


def test_unreachable(tmp_path):
    if not (FD.parent/'builds/release/bin/downward').exists():
        pytest.skip('Build pinned Fast Downward first')
    with pytest.raises((NoSolution, IncompleteSearch)):
        plan(DEFAULT_STATE, parse_goal('robot-at bedroom'), ROOT/'planner/domain.pddl', FD, tmp_path, edges=set())


@pytest.mark.parametrize('program,error', [('import sys; sys.exit(33)', RuntimeError), ('import time; time.sleep(60)', TimeoutError)])
def test_planner_failure_and_stale_plan(tmp_path, program, error):
    executable = tmp_path/'fake.py'
    executable.write_text(program)
    (tmp_path/'sas_plan').write_text('(move livingroom diningroom)')
    with pytest.raises(error):
        plan(DEFAULT_STATE, parse_goal('robot-at diningroom'), ROOT/'planner/domain.pddl', executable, tmp_path, timeout=0.2)
    assert not list(tmp_path.glob('plan-*/request.json'))


@pytest.mark.parametrize('text', ['(fly livingroom bedroom)', '(move livingroom)', 'move livingroom diningroom', '(pick cup unknown extra)'])
def test_strict_parser(text):
    with pytest.raises(ValueError):
        parse_plan(text)


def request():
    return dict(id=str(uuid.uuid4()), initial_state=deepcopy(DEFAULT_STATE), goal=['in-room','cup','bedroom'], actions=[
        ['move','livingroom','diningroom'], ['pick','cup','diningroom'], ['move','diningroom','livingroom'],
        ['move','livingroom','studyroom'], ['move','studyroom','bedroom'], ['place','cup','bedroom']])


@pytest.mark.parametrize('failed_index', [0, 1, 3, 5])
def test_failed_actions_never_commit_or_continue(tmp_path, failed_index):
    kb = tmp_path/'kb.json'
    atomic_json(kb, DEFAULT_STATE)
    req = request()
    calls = []
    def perform(action):
        calls.append(action)
        return len(calls)-1 != failed_index
    result = execute_request(req, kb, perform)
    assert not result['success'] and result['completed'] == failed_index
    expected = deepcopy(DEFAULT_STATE)
    for action in req['actions'][:failed_index]:
        expected = transition(expected, action)
    assert load_state(kb) == expected
    assert len(calls) == failed_index+1
    retry = request()
    retry['initial_state'] = expected
    assert not execute_request(retry, kb, lambda _: pytest.fail('Uncertain state must block execution'))['success']


def test_success_and_duplicate(tmp_path):
    kb = tmp_path/'kb.json'
    atomic_json(kb, DEFAULT_STATE)
    req = request()
    calls = []
    result = execute_request(req, kb, lambda action: calls.append(action) is None)
    assert result['success'] and calls == req['actions']
    assert load_state(kb)['objects']['cup'] == 'bedroom'
    assert not execute_request(req, kb, lambda _: pytest.fail('Duplicate execution'))['success']


def test_stale_and_invalid_plan(tmp_path):
    kb = tmp_path/'kb.json'
    atomic_json(kb, DEFAULT_STATE)
    req = request()
    req['initial_state']['robot_location'] = 'bathroom'
    assert not execute_request(req, kb, lambda _: pytest.fail('Stale plan'))['success']
    req = request()
    req['actions'] = [['pick', 'cup', 'diningroom']]
    assert not execute_request(req, kb, lambda _: pytest.fail('Invalid precondition'))['success']
    assert load_state(kb) == DEFAULT_STATE


def test_overlapping_execution_lock(tmp_path):
    kb = tmp_path/'kb.json'
    atomic_json(kb, DEFAULT_STATE)
    with state_lock(kb):
        result = execute_request(request(), kb, lambda _: pytest.fail('Overlapping plan'))
    assert not result['success'] and 'busy' in result['message']


def test_empty_plan(tmp_path):
    kb = tmp_path/'kb.json'
    atomic_json(kb, DEFAULT_STATE)
    req = request()
    req.update(actions=[], goal=['robot-at','livingroom'])
    assert execute_request(req, kb, lambda _: pytest.fail('Empty plan should issue no actions'))['success']


def test_action_exception(tmp_path):
    kb = tmp_path/'kb.json'
    atomic_json(kb, DEFAULT_STATE)
    def perform(_):
        raise TimeoutError('injected navigation timeout')
    result = execute_request(request(), kb, perform)
    assert not result['success'] and result['completed'] == 0
    assert load_state(kb) == DEFAULT_STATE


def test_journal_write_failure_never_reports_success(tmp_path, monkeypatch):
    import tb3_planner_execution.execution as execution
    kb = tmp_path/'kb.json'
    atomic_json(kb, DEFAULT_STATE)
    real_write = execution.atomic_json
    def fail_final(path, data):
        if data.get('status') == 'succeeded':
            raise OSError('injected disk failure')
        real_write(path, data)
    monkeypatch.setattr(execution, 'atomic_json', fail_final)
    result = execute_request(request(), kb, lambda _: True)
    assert not result['success'] and 'disk failure' in result['message']


def test_duplicate_id_after_intervening_success(tmp_path):
    kb = tmp_path/'kb.json'
    atomic_json(kb, DEFAULT_STATE)
    first = request()
    first.update(actions=[], goal=['robot-at', 'livingroom'])
    second = deepcopy(first)
    second['id'] = str(uuid.uuid4())
    assert execute_request(first, kb, lambda _: True)['success']
    assert execute_request(second, kb, lambda _: True)['success']
    result = execute_request(first, kb, lambda _: pytest.fail('Old UUID must not execute'))
    assert not result['success'] and 'Duplicate' in result['message']


def test_interactive_cli_without_ros(tmp_path):
    import os
    import subprocess
    process = subprocess.run([sys.executable, str(ROOT/'planner/planner_cli.py'),
                              '--kb', str(tmp_path/'kb.json'), '--output-dir', str(tmp_path/'plans')],
                             input='robot-at livingroom\nquit\n', text=True, capture_output=True,
                             env={'PATH': '/usr/bin:/bin', 'HOME': str(tmp_path)}, timeout=30)
    assert process.returncode == 0, process.stderr
    assert 'planning only' in process.stdout and '"actions": []' in process.stdout
    assert not (tmp_path/'kb.json').exists()
