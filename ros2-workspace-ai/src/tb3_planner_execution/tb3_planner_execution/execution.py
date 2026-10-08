"""Pure execution transaction; injected operations make failures testable without ROS."""
from .planning import atomic_json, load_state, state_lock, transition, validate_plan
from pathlib import Path
import json
import uuid


def execute_request(request, kb_path, perform):
    """Commit only confirmed effects. Persist an uncertainty latch across crashes/failures."""
    response = dict(id=request.get('id'), success=False, completed=0, message='')
    journal_path = Path(str(kb_path)+'.execution.json')
    try:
        uuid.UUID(request['id'])
        with state_lock(kb_path):
            seen_ids = []
            if journal_path.exists():
                journal = json.loads(journal_path.read_text())
                seen_ids = journal.get('seen_ids', [journal['id']] if journal.get('id') else [])
                if request['id'] in seen_ids:
                    raise ValueError('Duplicate execution ID; do not replay commands')
                if journal.get('status') != 'succeeded':
                    raise ValueError('Previous run requires physical reconciliation and explicit KB reset')
            state = load_state(kb_path)
            if state != request['initial_state']:
                raise ValueError('Stale plan: initial KB no longer matches')
            validate_plan(state, request['actions'], request['goal'])
            seen_ids = seen_ids + [request['id']]
            atomic_json(journal_path, dict(id=request['id'], seen_ids=seen_ids, status='running', completed=0))
            try:
                for action in request['actions']:
                    next_state = transition(state, action)
                    if perform(action) is not True:
                        raise RuntimeError(f'Action failed: {action}')
                    atomic_json(kb_path, next_state)
                    state = next_state
                    response['completed'] += 1
                    atomic_json(journal_path, dict(id=request['id'], seen_ids=seen_ids, status='running', completed=response['completed']))
                response.update(success=True, message='All controller actions succeeded')
            except Exception as exc:
                response['message'] = str(exc)
            atomic_json(journal_path, dict(response, seen_ids=seen_ids, status='succeeded' if response['success'] else 'needs_reconciliation'))
    except Exception as exc:
        response['success'] = False
        response['message'] = str(exc)
    return response
