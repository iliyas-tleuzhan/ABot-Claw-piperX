#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

cd "${REPO_ROOT}"

if [ -f /opt/ros/jazzy/setup.bash ]; then
  source /opt/ros/jazzy/setup.bash
elif [ -f /opt/ros/humble/setup.bash ]; then
  source /opt/ros/humble/setup.bash
fi

if [ -f /workspace/agx_arm_ws/install/setup.bash ]; then
  source /workspace/agx_arm_ws/install/setup.bash
elif [ -f /home/dase-hw101/agx_arm_ws/install/setup.bash ]; then
  source /home/dase-hw101/agx_arm_ws/install/setup.bash
fi

if [ -f /workspace/ros2_ws/install/setup.bash ]; then
  source /workspace/ros2_ws/install/setup.bash
elif [ -f /home/dase-hw101/ros2_ws/install/setup.bash ]; then
  source /home/dase-hw101/ros2_ws/install/setup.bash
fi

"${SCRIPT_DIR}/start_manipulation_task_listener.sh"

exec python3 robot_layer/arm_piper_x/agent_server/server.py --host 127.0.0.1 --port 8893
