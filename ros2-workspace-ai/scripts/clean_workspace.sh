#!/usr/bin/env bash
# Remove disposable logs/caches; keep compiled software and runtime KB/plan data.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python3 - <<'PY'
from pathlib import Path
import shutil
root=Path.cwd()
for name in ['log','.pytest_cache']:
    path=root/name
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
for source in [root/'scripts',root/'tests',root/'src/tb3_planner_execution',root/'planner']:
    for path in source.rglob('__pycache__'):
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
print('Removed logs and Python/test caches; kept build, install and planner state.')
PY
