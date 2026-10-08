#!/usr/bin/env bash
# Keep installed ROS Jazzy binaries on one apt release set. Does not upgrade unrelated packages.
set -euo pipefail
sudo apt-get update
python3 - <<'PY'
import subprocess
output=subprocess.check_output(['dpkg-query','-W','-f=${db:Status-Abbrev} ${binary:Package}\n','ros-jazzy-*'],text=True)
packages=[line.split()[1] for line in output.splitlines() if line.startswith('ii ')]
if not packages:
    raise SystemExit('No installed Jazzy packages found')
subprocess.run(['sudo','apt-get','install','--only-upgrade','-y',*packages],check=True)
PY
