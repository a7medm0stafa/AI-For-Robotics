#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python3 - <<'PY'
from pathlib import Path
import subprocess
path=Path('planner/downward')
revision='1eef26b2cbf599a1894606aa898d9d49e1034cb9'
if not (path/'.git').exists():
    if path.exists() and any(path.iterdir()):
        raise SystemExit('planner/downward contains unknown files; refusing to replace them')
    subprocess.run(['git','clone','https://github.com/aibasel/downward.git',str(path)],check=True)
    subprocess.run(['git','-C',str(path),'checkout',revision],check=True)
actual=subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
if actual != revision:
    raise SystemExit('Fast Downward revision mismatch; expected '+revision)
PY
python3 planner/downward/build.py release -j2
