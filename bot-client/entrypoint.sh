#!/bin/bash
set -e

# Virtual display
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
sleep 1

# VNC server on the virtual display (no password — localhost only inside the container)
x11vnc -display :99 -forever -nopw -rfbport 5900 -quiet -bg
sleep 0.5

# noVNC websocket proxy — serves web UI at http://HOST:6080/vnc.html
websockify --web /usr/share/novnc/ 6080 localhost:5900 &
sleep 0.5

exec ./slowburnbot "$@"
