#!/usr/bin/env python3
"""Estimate a planar map offset from house wall surfaces; diagnostic, not localization."""
from pathlib import Path
import json
import math
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image
from scipy.optimize import differential_evolution
from scipy.spatial import cKDTree
import yaml

root = Path(__file__).resolve().parents[1]
share = root/'src/tb3_planner_execution'
meta = yaml.safe_load((share/'maps/map.yaml').read_text())
map_image = np.asarray(Image.open(share/'maps/map.pgm'))
v, u = np.where(map_image < 80)
occupied = np.column_stack([meta['origin'][0]+(u+0.5)*meta['resolution'], meta['origin'][1]+(map_image.shape[0]-v-0.5)*meta['resolution']])
points = []
model = ET.parse(share/'models/tb3_house_custom/model.sdf').getroot().find('model')
for link in model.findall('link'):
    if not link.get('name', '').startswith('Wall'):
        continue
    pose = np.array([float(x) for x in link.findtext('pose', '0 0 0 0 0 0').split()])
    for collision in link.findall('collision'):
        box = collision.findtext('geometry/box/size')
        if box is None:
            continue
        size = np.array([float(x) for x in box.split()])
        cp = np.array([float(x) for x in collision.findtext('pose', '0 0 0 0 0 0').split()])
        corners = np.array([[-1,-1],[1,-1],[1,1],[-1,1]]) * size[:2]/2
        angle = pose[5]+cp[5]
        rotation = np.array([[math.cos(angle),-math.sin(angle)],[math.sin(angle),math.cos(angle)]])
        corners = corners @ rotation.T + pose[:2] + cp[:2]
        for a,b in zip(corners,np.roll(corners,-1,axis=0)):
            points.extend(a+(b-a)*t for t in np.linspace(0,1,max(2,int(np.linalg.norm(b-a)/0.025))))
points=np.asarray(points)
tree=cKDTree(points)
def cost(params):
    dx,dy,yaw=params
    rot=np.array([[math.cos(yaw),-math.sin(yaw)],[math.sin(yaw),math.cos(yaw)]])
    distances=tree.query((occupied-[dx,dy]) @ rot)[0]
    return np.mean(np.minimum(distances,0.3)**2)
fit=differential_evolution(cost,[(-3,3),(-3,3),(-0.15,0.15)],seed=42,tol=1e-8)
report=dict(world_to_map=dict(x=float(fit.x[0]),y=float(fit.x[1]),yaw=float(fit.x[2])),
            clipped_rms_m=float(math.sqrt(fit.fun)), identity_rms_m=float(math.sqrt(cost([0,0,0]))),
            legacy_offset_rms_m=float(math.sqrt(cost([2,0.5,0]))), method='occupied map pixels to wall surfaces; residual clipped at 0.3m; furniture excluded')
print(json.dumps(report,indent=2))
