#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[pi-deploy] %s\n' "$*"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log "Missing required command: $1"
    exit 1
  fi
}

require_cmd rsync
require_cmd curl
require_cmd python3
require_cmd sudo
require_cmd systemctl

WORKSPACE="${GITHUB_WORKSPACE:-$(pwd)}"
SOURCE_DIR="${SOURCE_DIR:-${WORKSPACE}/pi-controller}"
TARGET_DIR="${TARGET_DIR:-/opt/grow-pi}"
SERVICE_CONTROLLER="${SERVICE_CONTROLLER:-grow-pi}"
SERVICE_WEB="${SERVICE_WEB:-growpi-web}"
VERSION_ENDPOINT="${VERSION_ENDPOINT:-http://127.0.0.1:5000/api/version}"
HEALTH_ENDPOINT="${HEALTH_ENDPOINT:-http://127.0.0.1:5000/api/health}"

if [[ ! -d "${SOURCE_DIR}" ]]; then
  log "Source directory not found: ${SOURCE_DIR}"
  exit 1
fi

log "Sync ${SOURCE_DIR} -> ${TARGET_DIR}"
sudo mkdir -p "${TARGET_DIR}"
sudo rsync -a --delete \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude 'data/' \
  --exclude 'logs/' \
  --exclude 'venv/' \
  --exclude 'config/config.yaml' \
  --exclude 'config/devices.json' \
  --exclude 'config/room_config.json' \
  --exclude '*.backup' \
  --exclude '*.backup_*' \
  --exclude 'grow_pi.backup*/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude '*.pyc' \
  --exclude '.coverage' \
  "${SOURCE_DIR}/" "${TARGET_DIR}/"

log "Install Python dependencies"
if [[ ! -x "${TARGET_DIR}/venv/bin/python" ]]; then
  sudo python3 -m venv "${TARGET_DIR}/venv"
fi
sudo "${TARGET_DIR}/venv/bin/python" -m pip install --upgrade pip
sudo "${TARGET_DIR}/venv/bin/python" -m pip install -r "${TARGET_DIR}/requirements.txt"

log "Restart systemd services: ${SERVICE_CONTROLLER}, ${SERVICE_WEB}"
sudo systemctl restart "${SERVICE_CONTROLLER}" "${SERVICE_WEB}"

log "Wait for services to become active"
sudo systemctl is-active --quiet "${SERVICE_CONTROLLER}"
sudo systemctl is-active --quiet "${SERVICE_WEB}"

log "Wait for API endpoint"
for _ in $(seq 1 30); do
  if curl -fsS "${VERSION_ENDPOINT}" >/tmp/growpi-version.json 2>/dev/null; then
    break
  fi
  sleep 2
done

if [[ ! -s /tmp/growpi-version.json ]]; then
  log "Version endpoint did not respond in time"
  exit 1
fi

API_VERSION="$(python3 - <<'PY'
import json
with open('/tmp/growpi-version.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(data.get('version', ''))
PY
)"
FILE_VERSION="$(tr -d '\n' < "${TARGET_DIR}/VERSION")"

if [[ -z "${API_VERSION}" || -z "${FILE_VERSION}" ]]; then
  log "Could not determine versions (api='${API_VERSION}', file='${FILE_VERSION}')"
  exit 1
fi

if [[ "${API_VERSION}" != "${FILE_VERSION}" ]]; then
  log "Version mismatch: api=${API_VERSION}, file=${FILE_VERSION}"
  exit 1
fi

HEALTH_JSON="$(curl -fsS "${HEALTH_ENDPOINT}")"
export HEALTH_JSON
HEALTH_STATUS="$(python3 - <<'PY'
import json
import os

raw = os.environ.get("HEALTH_JSON", "")
try:
    payload = json.loads(raw)
except json.JSONDecodeError:
    print("invalid-json")
    raise SystemExit(0)

print(payload.get("status", payload.get("data", {}).get("status", "unknown")))
PY
)"

if [[ "${HEALTH_STATUS}" == "critical" || "${HEALTH_STATUS}" == "invalid-json" ]]; then
  log "Health check failed: ${HEALTH_STATUS}"
  exit 1
fi

log "Deployment successful"
log "Version: ${API_VERSION}"
log "Health: ${HEALTH_STATUS}"
