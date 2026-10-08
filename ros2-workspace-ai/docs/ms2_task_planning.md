# MS2 — student symbolic planning

This milestone runs without ROS, Gazebo, Nav2 or controllers. Python 3.12, a compiler/CMake and Git suffice. The pinned [Fast Downward documentation](https://www.fast-downward.org/latest/documentation/planner-usage/) explains the driver and `astar(lmcut())` search used here.

```bash
bash scripts/build_planner.sh
python3 planner/planner_cli.py --goal 'robot-at bedroom'
python3 planner/planner_cli.py --goal 'in-room cup bedroom'
python3 planner/planner_cli.py --goal 'holding book'
python3 -m pytest -q tests
```

The build downloads commit `1eef26b2cbf599a1894606aa898d9d49e1034cb9` to `.jazzy/downward` and builds `release` with two jobs. It does not reuse `planner/downward` or its old artifacts. On the validation machine the build used GCC 13 and Python 3.12.3. No LP solver is required by the selected search.

## Student tasks and model

Implement a domain/problem or problem generator, goal parser, planner invocation, and structural plan parser. Explain each action's preconditions and effects. The original `planner/domain.pddl` is the TA reference and remains unchanged.

- `move FROM TO`: robot at FROM and rooms connected; robot becomes located at TO.
- `pick OBJECT ROOM`: robot and object in ROOM, hand empty; object becomes held and leaves the room.
- `place OBJECT ROOM`: robot in ROOM and holding object; object enters ROOM, hand becomes empty.

Rooms: livingroom, diningroom, bedroom, storageroom, studyroom, bathroom. Undirected edges: livingroom–diningroom, livingroom–studyroom, diningroom–storageroom, diningroom–bathroom, studyroom–bedroom. Objects: cup, book, remote, phone, panadol, pillow, chewy. Goals preserve the vocabulary `robot-at ROOM`, `holding OBJECT`, `in-room OBJECT ROOM`.

Default state: robot in livingroom, empty hand/open gripper; cup in diningroom, book in studyroom, remote/phone in livingroom, panadol/pillow in bedroom, chewy in storageroom. An existing KB is loaded without resetting it. With no KB, planning-only mode uses the default in memory.

## Output and acceptance

Every invocation writes `.jazzy/plans/plan-<unique>/problem.pddl`, `planner.log`, and, on success, `sas_plan` plus `request.json`. `--output-dir`, `--planner`, and `--timeout` are explicit configuration options. No stale plan file can be interpreted as the new result. Exit 10/11 is treated as proven no solution; exit 12 is incomplete search; other nonzero exits are errors (the pinned lmcut run reports exit 12 for the disconnected acceptance problem); timeouts terminate the planner process group. Plans are parsed and simulated symbolically to check applicability and final goal satisfaction. An empty plan is valid when the goal already holds.

Acceptance cases: reachable room goal; object transport across rooms; already-satisfied goal; disconnected/unreachable goal; planner error/timeout. Accept any applicable plan achieving the goal, not a specific sequence. Planning changes neither the simulated robot nor the persistent KB.

The TA's ROS-independent modules are `planning.py` and `execution.py`. The tests include actual Fast Downward runs; they skip those cases if the pinned executable has not been built, so check the test summary for skips.

`--execute` adds ROS only for MS3. `--reset` explicitly writes default state to `~/.local/state/tb3_course/kb.json` (or `--kb PATH`); it does not move the robot. Never reset during execution or assume restarting the CLI resets the world.
