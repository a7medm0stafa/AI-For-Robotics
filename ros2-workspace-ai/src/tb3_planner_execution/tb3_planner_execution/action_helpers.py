"""Bounded action waits for worker callbacks; the executor must keep spinning."""
import threading


def wait_future(future, timeout):
    done = threading.Event()
    future.add_done_callback(lambda _: done.set())
    if not done.wait(timeout):
        raise TimeoutError('ROS response timed out')
    return future.result()


def run_action(client, goal, timeout, successful):
    if not client.wait_for_server(timeout_sec=5):
        raise RuntimeError('Action server unavailable')
    accepted = client.send_goal_async(goal)
    try:
        handle = wait_future(accepted, 5)
    except TimeoutError:
        # Late acceptance must not leave an unobserved command running.
        def cancel_late(future):
            try:
                late = future.result()
                if late.accepted:
                    late.cancel_goal_async()
            except Exception:
                pass
        accepted.add_done_callback(cancel_late)
        raise
    if not handle.accepted:
        raise RuntimeError('Action goal rejected')
    try:
        result = wait_future(handle.get_result_async(), timeout)
    except TimeoutError:
        try:
            wait_future(handle.cancel_goal_async(), 3)
        except Exception:
            pass
        raise
    return result.status == 4 and successful(result.result)
