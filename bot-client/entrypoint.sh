#!/bin/bash
set -e

# Virtual display
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
sleep 1

exec ./slowburnbot "$@"
