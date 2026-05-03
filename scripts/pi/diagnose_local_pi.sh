#!/usr/bin/env bash
set -uo pipefail

# Read-only GrowPi LAN diagnosis.
# Defaults come from repo .env without sourcing it, so secrets are not executed
# and password/token values are not printed.

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env}"
SCAN_SUBNET="${SCAN_SUBNET:-0}"

if [[ "${1:-}" == "--scan" ]]; then
  SCAN_SUBNET=1
fi

env_value() {
  local key="$1"
  [[ -f "${ENV_FILE}" ]] || return 0
  awk -F= -v key="${key}" '
    $1 == key {
      value = substr($0, index($0, "=") + 1)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
      gsub(/^"|"$/, "", value)
      gsub(/^'\''|'\''$/, "", value)
      print value
      exit
    }
  ' "${ENV_FILE}"
}

RASPI_HOST="${RASPI_HOST:-$(env_value RASPI_HOST)}"
RASPI_USERNAME="${RASPI_USERNAME:-$(env_value RASPI_USERNAME)}"
RASPI_HOSTNAME="${RASPI_HOSTNAME:-$(env_value RASPI_HOSTNAME)}"
RASPI_SSH_PORT="${RASPI_SSH_PORT:-$(env_value RASPI_SSH_PORT)}"
CONFIG_API_PORT="$(env_value API_PORT)"
API_PORT="${GROWPI_API_PORT:-${CONFIG_API_PORT:-5000}}"

RASPI_HOST="${RASPI_HOST:-growpi.local}"
RASPI_USERNAME="${RASPI_USERNAME:-admin}"
RASPI_HOSTNAME="${RASPI_HOSTNAME:-growpi}"
RASPI_SSH_PORT="${RASPI_SSH_PORT:-22}"

unique_ports() {
  awk 'NF && !seen[$0]++'
}

SSH_PORTS=()
while IFS= read -r port; do
  SSH_PORTS+=("${port}")
done < <(printf '%s\n22\n2222\n' "${RASPI_SSH_PORT}" | unique_ports)

section() {
  printf '\n== %s ==\n' "$1"
}

have() {
  command -v "$1" >/dev/null 2>&1
}

nc_check() {
  local host="$1"
  local port="$2"
  if ! have nc; then
    printf 'nc missing\n'
    return 2
  fi
  if [[ "$(uname -s)" == "Darwin" ]]; then
    nc -G 2 -w 2 -z "${host}" "${port}" >/dev/null 2>&1
  elif have timeout; then
    timeout 3 nc -w 2 -z "${host}" "${port}" >/dev/null 2>&1
  else
    nc -w 2 -z "${host}" "${port}" >/dev/null 2>&1
  fi
}

ping_check() {
  local host="$1"
  if [[ "$(uname -s)" == "Darwin" ]]; then
    ping -c 2 -W 1000 "${host}" >/dev/null 2>&1
  else
    ping -c 2 -W 1 "${host}" >/dev/null 2>&1
  fi
}

http_check() {
  local url="$1"
  local tmp
  tmp="$(mktemp)"
  if ! have curl; then
    printf 'curl missing\n'
    rm -f "${tmp}"
    return 2
  fi

  local code
  code="$(curl -sS --connect-timeout 3 --max-time 8 -o "${tmp}" -w '%{http_code}' "${url}" 2>"${tmp}.err" || true)"
  printf 'HTTP %s %s\n' "${code:-000}" "${url}"
  if [[ -s "${tmp}.err" ]]; then
    sed 's/^/  curl: /' "${tmp}.err"
  fi
  if [[ -s "${tmp}" ]]; then
    head -c 1600 "${tmp}" | sed 's/^/  /'
    printf '\n'
  fi
  rm -f "${tmp}" "${tmp}.err"
}

resolve_name() {
  local name="$1"
  if have python3; then
    python3 - "${name}" <<'PY' 2>/dev/null
import socket
import sys

socket.setdefaulttimeout(3)
try:
    for result in socket.getaddrinfo(sys.argv[1], None, socket.AF_INET):
        print(result[4][0])
except Exception:
    pass
PY
  elif have getent; then
    getent hosts "${name}" 2>/dev/null | awk '{print $1}'
  fi
}

is_ipv4() {
  [[ "$1" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]
}

local_subnet_prefix() {
  local addr
  if is_ipv4 "${RASPI_HOST}"; then
    printf '%s\n' "${RASPI_HOST%.*}"
    return 0
  fi
  if have ipconfig; then
    for iface in en8 en0 en1; do
      addr="$(ipconfig getifaddr "${iface}" 2>/dev/null || true)"
      if is_ipv4 "${addr}"; then
        printf '%s\n' "${addr%.*}"
        return 0
      fi
    done
  fi
  if have hostname; then
    addr="$(hostname -I 2>/dev/null | awk '{print $1}')"
    if is_ipv4 "${addr}"; then
      printf '%s\n' "${addr%.*}"
      return 0
    fi
  fi
  return 1
}

section "Config"
printf 'workspace=%s\n' "${ROOT_DIR}"
printf 'env_file=%s\n' "${ENV_FILE}"
printf 'raspi_host=%s\n' "${RASPI_HOST}"
printf 'raspi_hostname=%s\n' "${RASPI_HOSTNAME}"
printf 'raspi_user=%s\n' "${RASPI_USERNAME}"
printf 'ssh_ports=%s\n' "${SSH_PORTS[*]}"
printf 'api_port=%s\n' "${API_PORT}"
if [[ "${CONFIG_API_PORT}" != "" && "${CONFIG_API_PORT}" != "5000" ]]; then
  printf 'warning=.env API_PORT is %s, but GrowPi Pi API is documented on port 5000\n' "${CONFIG_API_PORT}"
fi

section "Local host port 5000"
if have lsof; then
  lsof -nP -iTCP:5000 -sTCP:LISTEN || true
fi
http_check "http://127.0.0.1:5000/api/health/"

section "Local network"
if have route; then
  route -n get default 2>/dev/null | awk '/gateway|interface/ {print}' || true
fi
if have ipconfig; then
  for iface in en0 en1 en8; do
    ipconfig getifaddr "${iface}" 2>/dev/null | sed "s/^/${iface}=/" || true
  done
fi
if have hostname; then
  hostname -I 2>/dev/null | sed 's/^/hostname_I=/' || true
fi

section "Name resolution"
names="$(printf '%s\n' "${RASPI_HOSTNAME}" "${RASPI_HOSTNAME}.local" growpi.local raspberrypi.local | awk 'NF && !seen[$0]++')"
while IFS= read -r name; do
  [[ -z "${name}" ]] && continue
  resolved="$(resolve_name "${name}" | tr '\n' ' ')"
  printf '%s -> %s\n' "${name}" "${resolved:-NO_DNS}"
done <<< "${names}"

section "Target reachability"
if ping_check "${RASPI_HOST}"; then
  printf 'ping %s PASS\n' "${RASPI_HOST}"
else
  printf 'ping %s FAIL\n' "${RASPI_HOST}"
fi

for port in "${SSH_PORTS[@]}" "${API_PORT}" 80 443; do
  if nc_check "${RASPI_HOST}" "${port}"; then
    printf 'tcp %s:%s OPEN\n' "${RASPI_HOST}" "${port}"
  else
    printf 'tcp %s:%s CLOSED_OR_TIMEOUT\n' "${RASPI_HOST}" "${port}"
  fi
done

section "GrowPi HTTP"
http_check "http://${RASPI_HOST}:${API_PORT}/api/version"
http_check "http://${RASPI_HOST}:${API_PORT}/api/health"
http_check "http://${RASPI_HOST}:${API_PORT}/api/status"

section "SSH read-only checks"
if have ssh; then
  ssh_ok=0
  for ssh_port in "${SSH_PORTS[@]}"; do
    printf 'trying ssh port %s\n' "${ssh_port}"
    if ssh -o BatchMode=yes \
        -o ConnectTimeout=5 \
        -o StrictHostKeyChecking=accept-new \
        -p "${ssh_port}" \
        "${RASPI_USERNAME}@${RASPI_HOST}" '
          set +e
          echo "SSH_OK"
          hostname
          hostname -I 2>/dev/null || true
          uptime
          systemctl is-active grow-pi growpi-web pigpiod 2>/dev/null || true
          systemctl status grow-pi growpi-web pigpiod --no-pager -n 20 2>/dev/null || true
          curl -fsS http://127.0.0.1:5000/api/health 2>/dev/null || true
          curl -fsS http://127.0.0.1:5000/api/temperature 2>/dev/null || true
          ss -tlnp 2>/dev/null | grep -E "(:22|:2222|:5000)" || true
          vcgencmd get_throttled 2>/dev/null || true
          df -h / /opt/grow-pi 2>/dev/null || true
          free -h 2>/dev/null || true
          journalctl -u grow-pi -u growpi-web -n 80 --no-pager -p warning..alert 2>/dev/null || true
        '; then
      ssh_ok=1
      break
    fi
  done
  if [[ "${ssh_ok}" != "1" ]]; then
    printf 'SSH_BATCHMODE_FAILED\n'
  fi
else
  printf 'ssh missing\n'
fi

if [[ "${SCAN_SUBNET}" == "1" ]]; then
  section "Subnet scan"
  prefix="$(local_subnet_prefix || true)"
  if [[ -z "${prefix}" ]]; then
    printf 'could not determine local subnet prefix\n'
    exit 0
  fi
  printf 'scanning %s.0/24 for SSH ports and API port %s\n' "${prefix}" "${API_PORT}"
  for port in "${SSH_PORTS[@]}" "${API_PORT}"; do
    printf 'PORT %s\n' "${port}"
    seq 1 254 | xargs -P64 -I{} bash -c '
      ip="$1.$2"
      port="$3"
      if [[ "$(uname -s)" == "Darwin" ]]; then
        nc -G 1 -w 1 -z "$ip" "$port" >/dev/null 2>&1
      elif command -v timeout >/dev/null 2>&1; then
        timeout 2 nc -w 1 -z "$ip" "$port" >/dev/null 2>&1
      else
        nc -w 1 -z "$ip" "$port" >/dev/null 2>&1
      fi
      if [[ "$?" -eq 0 ]]; then
        echo "$ip:$port"
      fi
    ' _ "${prefix}" {} "${port}"
  done
fi

section "Interpretation"
cat <<EOF
- If ${RASPI_HOST}:${API_PORT} times out and SSH also fails, this workstation cannot reach the Pi on the configured LAN address.
- If 127.0.0.1:5000 returns AirTunes/AirPlay 403, that is the Mac local AirPlay receiver, not GrowPi.
- If SSH works but HTTP fails, inspect growpi-web.service and its journal output above.
- If HTTP works locally on the Pi but not from LAN, inspect firewall, bind address, and router/client isolation.
EOF
