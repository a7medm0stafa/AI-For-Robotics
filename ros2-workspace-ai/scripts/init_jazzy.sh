#!/usr/bin/env bash
# Download only into .jazzy; preserve all legacy sources and build artifacts.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p .jazzy/vendor/src
vcs import .jazzy/vendor/src --input dependencies/jazzy.repos --skip-existing
python3 - <<'PY'
from pathlib import Path
import subprocess, yaml
manifest = yaml.safe_load(Path('dependencies/jazzy.repos').read_text())['repositories']
for name, source in manifest.items():
    path = Path('.jazzy/vendor/src')/name
    revision = subprocess.check_output(['git','-C',str(path),'rev-parse','HEAD'],text=True).strip()
    changes = subprocess.check_output(['git','-C',str(path),'status','--porcelain'],text=True)
    if revision != source['version'] or changes:
        raise SystemExit(f'{path}: revision mismatch or local changes; preserve these and use a clean clone')
print('All four vendor revisions match the manifest; no patches')
PY
