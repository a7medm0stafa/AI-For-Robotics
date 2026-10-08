#!/usr/bin/env python3
"""Read-only inventory of the selected migration environment and preserved inputs."""
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[1]
def command(*args):
    return subprocess.check_output(args,cwd=root,text=True).strip()
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
report={'os':platform.freedesktop_os_release()['PRETTY_NAME'],'architecture':platform.machine(),
        'python':platform.python_version(),'compiler':command('g++','--version').splitlines()[0],
        'cmake':command('cmake','--version').splitlines()[0],
        'branch':command('git','branch','--show-current'),
        'remote':command('git','remote','get-url','origin'),
        'base_commit':'44bd8b6', 'active_vendor_packages':['turtlebot3_description','turtlebot3_msgs','turtlebot3_gazebo','turtlebot3_manipulation_description'],
        'snapshots_match':{name:(digest(root/'planner'/name)==digest(root/'.jazzy/snapshots'/name) if (root/'.jazzy/snapshots'/name).exists() else None) for name in ['kb_state.json','problem.pddl','sas_plan']}}
for name in ['map.yaml','map.pgm']:
    path='ros2-workspace-ai/src/tb3_planner_execution/maps/'+name
    before=subprocess.check_output(['git','show','44bd8b6:'+path],cwd=root)
    report.setdefault('map_unchanged',{})[name]=hashlib.sha256(before).hexdigest()==digest(root/'src/tb3_planner_execution/maps'/name)
original=subprocess.check_output(['git','show','44bd8b6:ros2-workspace-ai/src/tb3_planner_execution/models/tb3_house_custom/model.sdf'],cwd=root,text=True)
current=(root/'src/tb3_planner_execution/models/tb3_house_custom/model.sdf').read_text().replace('model://turtlebot3_house/','model://')
def collisions(text):
    tree=ET.fromstring(text)
    return [ET.canonicalize(ET.tostring(c,encoding='unicode'),strip_text=True) for c in tree.findall('.//collision')]
report['house_collision_count']=len(collisions(current))
report['house_collisions_unchanged']=collisions(original)==collisions(current)
print(json.dumps(report,indent=2))
