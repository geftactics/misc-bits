#!/usr/bin/env python3

import logging
import random
import sys
import time
from obswebsocket import obsws, requests

# REQUIREMENTS:
# obs-websocket     ->  Install release from https://github.com/Palakis/obs-websocket/releases
# obs-websocket-py  ->  Run 'pip3 install obs-websocket-py'

duration_max    = 10            # Maximum duration we show a scene for before switching
duration_min    = 5             # Minimum duration we show a scene for before switching
scene_prefix    = '_'           # Only auto switch scenes with this prefix
obs_pass        = 'letmein'     # Password/secret for OBS-WebSocket
obs_host        = 'localhost'   # Hostname of OBS-websocket server, usually localhost
obs_port        = 4444          # TCP port that OBS-Webocket server is listening on


logging.basicConfig(level=logging.INFO)
ws = obsws(obs_host, obs_port, obs_pass)
ws.connect()

scenes_all = ws.call(requests.GetSceneList())
scenes_auto = []
last_scene = ''
scene = ''

for s in scenes_all.getScenes():
    if s['name'][0] == scene_prefix:
        print('Added:', s['name'])
        scenes_auto.append(s['name'])

while True:
    while scene == last_scene:
        scene = random.choice(scenes_auto)
    last_scene = scene
    duration = random.randint(duration_min, duration_max)
    print('Switching to [%s] for %ssec...' % (scene, duration))
    ws.call(requests.SetCurrentScene(scene))
    time.sleep(duration)
    
ws.disconnect()
