import math
import heapq
import time
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

MAP_BOUNDS = {'x': [0, 20], 'y': [-5, 5]}
OBSTACLE = {'x': [8, 12], 'y': [-1.5, 1.5]}
START_STATE = (2.0, 0.0, 0.0)
GOAL_REGION = {'x_min': 18.0, 'y_range': [-1.0, 1.0]}
V = 1.0
DELTA_T = 0.2
STEERING_INPUTS = {'left': -math.radians(35), 'straight': 0.0, 'right': math.radians(35)}
L = 1
GRID_SPACING = 0.2
NUM_THETA_DISCRETIZATIONS = 16
ANGLE_RESOLUTION = 2 * math.pi / NUM_THETA_DISCRETIZATIONS

class Node:
    def __init__(self, x, y, theta, g=0, h=0, parent=None):
        self.x = x
        self.y = y
        self.theta = theta
        self.g = g
        self.h = h
        self.f = g + h
        self.parent = parent
    def __lt__(self, other):
        return self.f < other.f
    def __repr__(self):
        return f"Node(x={self.x:.2f}, y={self.y:.2f}, theta={self.theta:.2f}, f={self.f:.2f})"

class AStarPlanner:
    def __init__(self):
        self.open_set = []
        self.closed_set = set()
        self.goal_node = None

    def _discretize_state(self, node):
        ix = int(round(node.x / GRID_SPACING))
        iy = int(round(node.y / GRID_SPACING))
        normalized_theta = node.theta % (2 * math.pi)
        itheta = int(round(normalized_theta / ANGLE_RESOLUTION)) % NUM_THETA_DISCRETIZATIONS
        return (ix, iy, itheta)

    def _calculate_heuristic(self, node):
        goal_x = GOAL_REGION['x_min']
        goal_y = 0
        return math.hypot(node.x - goal_x, node.y - goal_y)

    def _is_in_goal_region(self, node):
        return (node.x >= GOAL_REGION['x_min'] and
                GOAL_REGION['y_range'][0] <= node.y <= GOAL_REGION['y_range'][1])

    def _is_collision(self, node):
        if not (MAP_BOUNDS['x'][0] <= node.x <= MAP_BOUNDS['x'][1] and
                MAP_BOUNDS['y'][0] <= node.y <= MAP_BOUNDS['y'][1]):
            return True
        if (OBSTACLE['x'][0] <= node.x <= OBSTACLE['x'][1] and
            OBSTACLE['y'][0] <= node.y <= OBSTACLE['y'][1]):
            return True
        return False

    def _get_next_states(self, current_node):
        next_states = []
        move_cost = V * DELTA_T
        for steer_name, delta in STEERING_INPUTS.items():
            theta_dot = (V / L) * math.tan(delta)
            new_theta = current_node.theta + theta_dot * DELTA_T
            new_x = current_node.x + V * math.cos(current_node.theta) * DELTA_T
            new_y = current_node.y + V * math.sin(current_node.theta) * DELTA_T
            new_g = current_node.g + move_cost
            neighbor_node = Node(new_x, new_y, new_theta, g=new_g, parent=current_node)
            neighbor_node.h = self._calculate_heuristic(neighbor_node)
            neighbor_node.f = neighbor_node.g + neighbor_node.h
            next_states.append(neighbor_node)
        return next_states

    def plan(self, visualize_search=True):
        start_time = time.time()
        start_node = Node(x=START_STATE[0], y=START_STATE[1], theta=START_STATE[2])
        start_node.h = self._calculate_heuristic(start_node)
        start_node.f = start_node.h
        heapq.heappush(self.open_set, start_node)

        if visualize_search:
            plt.ion()
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.set_xlim(MAP_BOUNDS['x'])
            ax.set_ylim(MAP_BOUNDS['y'])
            ax.set_aspect('equal', adjustable='box')
            ax.add_patch(patches.Rectangle(
                (OBSTACLE['x'][0], OBSTACLE['y'][0]),
                OBSTACLE['x'][1] - OBSTACLE['x'][0],
                OBSTACLE['y'][1] - OBSTACLE['y'][0],
                facecolor='gray', edgecolor='black'))
            ax.add_patch(patches.Rectangle(
                (GOAL_REGION['x_min'], GOAL_REGION['y_range'][0]),
                MAP_BOUNDS['x'][1] - GOAL_REGION['x_min'],
                GOAL_REGION['y_range'][1] - GOAL_REGION['y_range'][0],
                facecolor='lightgreen', alpha=0.6))
            ax.plot(START_STATE[0], START_STATE[1], 'ro', label='Start')
            explored_plot, = ax.plot([], [], 'k.', alpha=0.4, label='Explored')
            plt.legend()
            explored_x, explored_y = [], []

        while self.open_set:
            current_node = heapq.heappop(self.open_set)
            if self._is_in_goal_region(current_node):
                self.goal_node = current_node
                execution_time = time.time() - start_time
                if visualize_search:
                    plt.ioff()
                return self._reconstruct_path(), len(self.closed_set), execution_time
            discrete_state = self._discretize_state(current_node)
            if discrete_state in self.closed_set:
                continue
            self.closed_set.add(discrete_state)
            if visualize_search:
                explored_x.append(current_node.x)
                explored_y.append(current_node.y)
                explored_plot.set_data(explored_x, explored_y)
                plt.pause(0.001)
            for neighbor in self._get_next_states(current_node):
                if self._is_collision(neighbor):
                    continue
                neighbor_discrete_state = self._discretize_state(neighbor)
                if neighbor_discrete_state in self.closed_set:
                    continue
                heapq.heappush(self.open_set, neighbor)

        execution_time = time.time() - start_time
        if visualize_search:
            plt.ioff()
        return None, len(self.closed_set), execution_time

    def _reconstruct_path(self):
        path = []
        current = self.goal_node
        while current is not None:
            path.append((current.x, current.y))
            current = current.parent
        return path[::-1]

def visualize(path, explored_nodes, exec_time):
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_xlim(MAP_BOUNDS['x'])
    ax.set_ylim(MAP_BOUNDS['y'])
    ax.set_aspect('equal', adjustable='box')
    obstacle_patch = patches.Rectangle(
        (OBSTACLE['x'][0], OBSTACLE['y'][0]),
        OBSTACLE['x'][1] - OBSTACLE['x'][0],
        OBSTACLE['y'][1] - OBSTACLE['y'][0],
        facecolor='gray',
        edgecolor='black',
        linewidth=1.5,
        label='Obstacle')
    ax.add_patch(obstacle_patch)
    goal_patch = patches.Rectangle(
        (GOAL_REGION['x_min'], GOAL_REGION['y_range'][0]),
        MAP_BOUNDS['x'][1] - GOAL_REGION['x_min'],
        GOAL_REGION['y_range'][1] - GOAL_REGION['y_range'][0],
        facecolor='lightgreen',
        edgecolor='green',
        linewidth=1,
        alpha=0.6,
        label='Goal Region')
    ax.add_patch(goal_patch)
    ax.plot(START_STATE[0], START_STATE[1], 'ro', markersize=8, label='Start')
    if path:
        path_x, path_y = zip(*path)
        ax.plot(path_x, path_y, 'b-', linewidth=2, label='Planned Path')
    ax.set_xlabel('X (meters)')
    ax.set_ylabel('Y (meters)')
    ax.set_title('A* Path Planning for a Kinematic Car')
    ax.set_xticks(np.arange(MAP_BOUNDS['x'][0], MAP_BOUNDS['x'][1] + 0.5, 0.5))
    ax.set_yticks(np.arange(MAP_BOUNDS['y'][0], MAP_BOUNDS['y'][1] + 0.5, 0.5))
    ax.grid(True, which='both', linestyle='--', color='gray', alpha=0.6)
    ax.legend()
    stats_text = (f"Execution Time: {exec_time:.2f} s\n"
                  f"Explored Nodes: {explored_nodes}")
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
            fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.5', fc='wheat', alpha=0.5))
    plt.show()

if __name__ == "__main__":
    planner = AStarPlanner()
    final_path, num_explored_nodes, execution_time = planner.plan()
    if final_path:
        print(f"\n--- Search Results ---")
        print(f"Path found with {len(final_path)} points.")
        print(f"Number of Explored Nodes: {num_explored_nodes}")
        print(f"Execution Time: {execution_time:.4f} seconds")
        visualize(final_path, num_explored_nodes, execution_time)
    else:
        print("\nCould not find a path to the goal.")
        visualize(None, num_explored_nodes, execution_time)
