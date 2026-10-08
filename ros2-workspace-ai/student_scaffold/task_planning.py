"""MS2 student tasks: this module must not import ROS."""


def write_problem(state, goal, destination):
    raise NotImplementedError('Validate symbols; encode initial facts, connectivity and goal')


def run_planner(domain, problem, executable, output_dir, timeout):
    raise NotImplementedError('Use isolated outputs; distinguish no solution, errors and timeout')


def parse_and_validate_plan(plan_text, initial_state, goal):
    raise NotImplementedError('Check action syntax, arguments, preconditions, effects and final goal')
