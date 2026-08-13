#!/usr/bin/env bash
set -eo pipefail

LOG_DIR="${ABOTCLAW_LOG_DIR:-/tmp/abotclaw_logs}"
START_TOPIC="${MANIPULATION_TASK_START_TOPIC:-/manipulation_task/start}"
START_BOOL_TOPIC="${MANIPULATION_TASK_START_BOOL_TOPIC:-/manipulation_task/start_bool}"

mkdir -p "${LOG_DIR}"

if ! command -v ros2 >/dev/null 2>&1; then
  echo "ros2 not found; manipulation task listeners were not started" >&2
  exit 0
fi

start_echo_listener() {
  local topic="$1"
  local type="$2"
  local log_file="$3"

  if pgrep -f "ros2 topic echo ${topic} ${type}" >/dev/null 2>&1; then
    echo "listener already running for ${topic}"
    return
  fi

  {
    echo
    echo "===== $(date -Is) listening on ${topic} (${type}) ====="
  } >> "${log_file}"

  nohup ros2 topic echo "${topic}" "${type}" >> "${log_file}" 2>&1 &
  echo "started listener for ${topic}: pid=$!, log=${log_file}"
}

start_echo_listener \
  "${START_TOPIC}" \
  "std_msgs/msg/String" \
  "${LOG_DIR}/manipulation_task_start.log"

start_echo_listener \
  "${START_BOOL_TOPIC}" \
  "std_msgs/msg/Bool" \
  "${LOG_DIR}/manipulation_task_start_bool.log"
