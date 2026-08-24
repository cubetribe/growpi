# GrowPi LAN Incident Diagnosis

Generated: 2026-05-03T08:34:14Z
Last updated: 2026-05-03T13:12:36+02:00

## Scope

- Workspace: `<LOCAL_WORKSPACE>`
- Git status: no Git repository detected at or above workspace root
- Runtime target from local config: `<PI_HOST>`, user `<PI_USER>`, SSH port `22`
- Expected GrowPi Pi API port: `5000`

## Reproduced Failures

1. Raspberry Pi target unreachable from this workstation:
   - `ping <PI_HOST>`: fail
   - ARP entry for `<PI_HOST>`: `incomplete` on the active LAN interface
   - `tcp <PI_HOST>:22`: closed or timeout
   - `tcp <PI_HOST>:5000`: closed or timeout
   - `ssh <PI_USER>@<PI_HOST>`: host down / timeout
   - `http://<PI_HOST>:5000/api/version`: connection failed
   - `http://<PI_HOST>:5000/api/health`: connection failed

2. mDNS/DNS discovery did not locate the Pi:
   - `growpi`: no DNS result
   - `growpi.local`: no DNS result
   - `raspberrypi.local`: no DNS result

3. Browser URL `http://127.0.0.1:5000/api/health/` is not the Pi:
   - Local listener on port `5000`: macOS `ControlCenter`
   - HTTP result: `403 Forbidden`
   - Server header: `AirTunes`
   - Interpretation: this is the Mac AirPlay receiver, not GrowPi.

4. Subnet scan found no GrowPi candidate:
   - No open SSH (`:22`) hosts detected in the scanned LAN subnet.
   - Open `:5000` hosts were local/AirPlay-style candidates, not GrowPi API responses.
   - Explicit source-IP tests from both local interfaces failed:
     - Ethernet interface
     - Wi-Fi interface
   - Known Raspberry Pi MAC prefixes were not present in the ARP table.

5. Local simulation environment failed before dependency installation:
   - Command: `python3 pi-controller/test_environment/run_local.py --host 127.0.0.1 --port 8000`
   - Failure: `ModuleNotFoundError: No module named 'flask'`
   - Cause found in installer: `pi-controller/install.sh` copied `requirements.txt` but only installed `PyYAML pigpio`.

6. GitHub Actions outbound path is also unavailable:
   - Self-hosted runner `growpi-01`: `offline`
   - Last successful runner evidence: 2026-03-02, machine name `growpi`, local API health `healthy`
   - Latest failed deploy run: 2026-03-06

## Root-Cause Boundary

The initial app connectivity incident was outside the GrowPi Python service code path because the configured Pi address was not reachable at network level from this Mac. Since the user reported that hardware control continued, the likely split was:

- `grow-pi.service` may still be running locally on the Raspberry Pi and controlling GPIO/PWM.
- LAN access to the Pi, the Pi IP, Wi-Fi/Ethernet, router client isolation, or `growpi-web.service` exposure is broken.
- The Pi also appears unable to maintain the outbound GitHub runner connection, so the issue is not limited to inbound SSH/API.

The local `127.0.0.1:5000` browser result is a separate local macOS AirPlay conflict and should not be used as a Pi health check.

## Post-Reboot Status

After the user hardware-rebooted the Pi, the configured target became reachable again:

- `ping <PI_HOST>`: pass
- `<PI_HOSTNAME>.local`: resolves to `<PI_HOST>`
- ARP MAC for `<PI_HOST>`: Raspberry Pi vendor prefix on local interfaces
- `tcp <PI_HOST>:22`: open
- `tcp <PI_HOST>:2222`: closed/refused
- `tcp <PI_HOST>:5000`: open
- `http://<PI_HOST>:5000/api/status`: pass, lamps remain controlled
- `http://<PI_HOST>:5000/api/temperature`: HTTP `503`, `Sensor read failed`
- `http://<PI_HOST>:5000/api/health`: reachable but `critical`

Live health still reports hardware-level faults:

- `system.power.raw`: `0x50005`
- `under_voltage_now`: `true`
- `currently_throttled`: `true`
- `under_voltage_occurred`: `true`
- `throttling_occurred`: `true`
- `circuit_breaker.state`: `open`
- `circuit_breaker.fail_count`: `5`
- `temperature`: `null`
- `humidity`: `null`

API-level attempts to reset the sensor circuit breaker and restart the
controller did not recover sensor readings. The remaining faults require power
and DHT22 hardware inspection.

## Fixes Applied In Workspace

- Added `scripts/pi/diagnose_local_pi.sh` for repeatable read-only LAN and optional SSH diagnostics.
- Updated `.env` and `.env.example`: `API_PORT=5000`.
- Fixed `pi-controller/install.sh`:
  - copies `VERSION` into `/opt/grow-pi`
  - installs full `requirements.txt` instead of only `PyYAML pigpio`
- Documented macOS AirPlay port `5000` conflict and the diagnostic script in `README.md`.
- Documented local simulation workaround `--port 8000` in `pi-controller/test_environment/README.md`.
- Added `docs/PI_OPERATIONS_RUNBOOK.md` with the live status, hardware actions,
  and stabilization plan.
- Hardened the planned deploy path so runtime-local files are preserved and
  dependencies are installed before service restart.
- Restricted automatic Pi deployment to `main` and manual dispatch, preventing
  production restarts from feature-branch pushes while hardware health is
  critical.
- Hardened the planned health API contract so `/api/health/*` endpoints return
  API responses and sensor circuit breaker faults influence overall health.

## Recommended Next Physical Checks

Run directly on the Raspberry Pi with keyboard/monitor or through the router device console:

```bash
hostname -I
sudo systemctl status grow-pi growpi-web pigpiod --no-pager
curl -fsS http://127.0.0.1:5000/api/health
vcgencmd get_throttled
sudo journalctl -u grow-pi -u growpi-web -n 120 --no-pager
```

If `hostname -I` is no longer the configured `<PI_HOST>`, update the app and `.env` to the new Pi address or reserve a static DHCP lease for the Pi.

## Current User Check Links

- UI: `http://<PI_HOST>:5000`
- Canonical health: `http://<PI_HOST>:5000/api/health`
- Status: `http://<PI_HOST>:5000/api/status`
