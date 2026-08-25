#!/usr/bin/env bash
set -e

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/jazzy/setup.bash
source /home/dexy/ws_cobot_pjt/ws_dsr/install/setup.bash
cd "$WORKSPACE_DIR"
colcon build --packages-select icecream_interfaces ice_cream_pj --symlink-install
