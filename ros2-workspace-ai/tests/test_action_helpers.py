from concurrent.futures import Future
from types import SimpleNamespace
import pytest
from tb3_planner_execution.action_helpers import run_action


def done(value):
    future = Future()
    future.set_result(value)
    return future


class Client:
    def __init__(self, accepted=True, status=4, reached=True):
        self.handle = SimpleNamespace(accepted=accepted, get_result_async=lambda: done(SimpleNamespace(status=status, result=SimpleNamespace(reached_goal=reached))))
    def wait_for_server(self, timeout_sec):
        return True
    def send_goal_async(self, goal):
        return done(self.handle)


@pytest.mark.parametrize('status,reached,expected', [(4,True,True),(4,False,False),(6,True,False),(5,True,False)])
def test_done_does_not_mean_success(status,reached,expected):
    assert run_action(Client(status=status,reached=reached), object(), 1, lambda r:r.reached_goal) is expected


def test_rejected_goal():
    with pytest.raises(RuntimeError,match='rejected'):
        run_action(Client(accepted=False), object(), 1, lambda r: True)


def test_missing_controller():
    client=Client()
    client.wait_for_server=lambda timeout_sec:False
    with pytest.raises(RuntimeError,match='unavailable'):
        run_action(client, object(), 1, lambda r:True)


def test_result_timeout_cancels_goal():
    client = Client()
    canceled = []
    client.handle.get_result_async = lambda: Future()
    client.handle.cancel_goal_async = lambda: canceled.append(True) or done(None)
    with pytest.raises(TimeoutError):
        run_action(client, object(), 0.01, lambda r: True)
    assert canceled == [True]
