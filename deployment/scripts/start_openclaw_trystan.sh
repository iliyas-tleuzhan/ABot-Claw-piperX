#!/usr/bin/env bash
set -euo pipefail

# The source tree is mounted into the Trystan container. Keep OpenClaw's
# credentials outside Git and restore them only when the container is new.
STATE_DIR="${OPENCLAW_STATE_DIR:-/ros2_ws/src/.openclaw-state}"
OPENCLAW_DIR="${HOME}/.openclaw"

if [[ -d "${STATE_DIR}" && ! -f "${OPENCLAW_DIR}/openclaw.json" ]]; then
  mkdir -p "${OPENCLAW_DIR}"
  cp -a "${STATE_DIR}/." "${OPENCLAW_DIR}/"
  chmod -R go-rwx "${OPENCLAW_DIR}"
fi

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-173}"
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}"
export ROS_LOCALHOST_ONLY="${ROS_LOCALHOST_ONLY:-1}"

# Always bind clients and the gateway to the token in the active config. Keeping
# an old exported token causes gateway reconnects to fail with token_mismatch.
export OPENCLAW_GATEWAY_TOKEN="$(openclaw config get gateway.auth.token)"

case "${1:-gateway}" in
  gateway)
    exec openclaw gateway run --bind loopback --port "${OPENCLAW_GATEWAY_PORT:-18789}" --force
    ;;
  tui)
    exec openclaw tui
    ;;
  status)
    openclaw config validate
    openclaw models status
    ;;
  *)
    printf 'Usage: %s {gateway|tui|status}\n' "$0" >&2
    exit 2
    ;;
esac
