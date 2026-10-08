"""MS1 student tasks: implement these contracts in a ROS node."""


def drive_and_measure(linear_speed, angular_speed, duration):
    """Publish stamped commands; measure odometry; always stop on completion/error."""
    raise NotImplementedError('Implement command timing, feedback, simulation time and cleanup')


def command_arm_and_gripper(positions, opening):
    """Return true only for accepted, successful actions with valid controller results."""
    raise NotImplementedError('Implement asynchronous clients, timeout/cancel and sequence exclusion')
