#!/usr/bin/env python3
"""Read-only KB inspection utility (not a persistence acceptance test)."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src/tb3_planner_execution'))
from tb3_planner_execution.planning import default_kb_path, load_state

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kb', type=Path, default=default_kb_path())
    args = parser.parse_args()
    print(json.dumps(load_state(args.kb), indent=2))
