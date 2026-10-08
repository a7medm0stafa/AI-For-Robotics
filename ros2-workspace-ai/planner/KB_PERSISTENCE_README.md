# Jazzy knowledge-base persistence

The CLI and executor share `~/.local/state/tb3_course/kb.json` by default. Override with CLI `--kb PATH` and executor `-p kb_path:=PATH`. Starting the CLI does not reset state. Planning-only mode never writes symbolic effects to the KB.

The executor is the only action-effect writer. It holds a file lock, validates the initial state/plan, executes one action at a time, and atomically writes effects only after confirmed success. The adjacent `.execution.json` journal latches interrupted/failed execution for reconciliation. `planner_cli.py --reset` is explicit and does not move the robot. See [the complete semantics and recovery procedure](../docs/ms3_integration.md).

`planner/kb_state.json`, `problem.pddl` and `sas_plan` are preserved historical state, not active runtime files. The old `kb_update_service.py` is retired. Inspect current state with `python3 planner/test_kb_state.py --kb PATH`. Run actual persistence/failure tests with `python3 -m pytest -q tests`.
