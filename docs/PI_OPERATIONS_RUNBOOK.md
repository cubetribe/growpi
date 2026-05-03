# GrowPi Raspberry Pi Operations Runbook

## Current Production Target

- Pi API/UI: `http://<PI_HOST>:5000`
- mDNS target: `<PI_HOSTNAME>.local -> <PI_HOST>`
- SSH: `<PI_USER>@<PI_HOST>`, port `22`
- Alternate SSH port `2222`: closed/refused during 2026-05-03 diagnosis
- GitHub runner: expected runner name `growpi-01`

Use the configured API link for user checks:

```text
http://<PI_HOST>:5000
http://<PI_HOST>:5000/api/health
```

## 2026-05-03 Incident Findings

The app connectivity failure was reproduced as a LAN reachability incident. The
configured Pi host was not reachable before a hardware reboot, while local
macOS port `127.0.0.1:5000` was a separate AirPlay Receiver listener and not
GrowPi.

After the hardware reboot:

- `<PI_HOST>` responds to ping.
- ARP shows a Raspberry Pi vendor MAC prefix for `<PI_HOST>`.
- TCP `<PI_HOST>:22` is open.
- TCP `<PI_HOST>:2222` is closed/refused.
- TCP `<PI_HOST>:5000` is open.
- `GET /api/status` returns lamp state and `logging_enabled: true`.
- `GET /api/temperature` returns HTTP `503` with `Sensor read failed`.
- `GET /api/health` returns `critical`.

The remaining live faults from API health are:

- `system.power.raw: 0x50005`
- `under_voltage_now: true`
- `currently_throttled: true`
- `under_voltage_occurred: true`
- `throttling_occurred: true`
- DHT22 `circuit_breaker.state: open`, `fail_count: 5`
- temperature and humidity are `null`

## Immediate Physical Actions

Handle these before treating software as the root cause:

1. Replace the Pi power supply with a known-good supply rated for the installed
   Pi and attached USB load.
2. Replace or shorten the USB power cable; avoid thin or damaged cables.
3. Remove non-essential USB load temporarily, especially camera or hub devices.
4. Check whether the Pi reports clean power after the change:

```bash
vcgencmd get_throttled
curl -fsS http://127.0.0.1:5000/api/health
```

5. Inspect the DHT22 wiring and pull-up:
   - data pin on the configured GPIO
   - stable 3.3V supply and ground
   - correct pull-up resistor
   - no loose breadboard jumper
6. Replace the DHT22 if wiring and power are clean but `/api/temperature`
   still returns `503`.

## Remote Diagnosis Workflow

Run from this workspace:

```bash
./scripts/pi/diagnose_local_pi.sh --scan
```

Run when SSH is available:

```bash
ssh -p 22 <PI_USER>@<PI_HOST>
sudo systemctl status grow-pi growpi-web pigpiod --no-pager
sudo journalctl -u grow-pi -u growpi-web -b --no-pager -p warning..alert
curl -fsS http://127.0.0.1:5000/api/health
curl -fsS http://127.0.0.1:5000/api/status
curl -fsS http://127.0.0.1:5000/api/temperature
vcgencmd get_throttled
df -h /
free -h
```

Do not use `http://127.0.0.1:5000` on the Mac as a Pi check. On macOS that
address can be AirPlay Receiver.

## Stabilization Plan

### Phase 1: Network Identity

- Reserve the configured `<PI_HOST>` for the Pi in the router DHCP table.
- Keep `<PI_HOSTNAME>.local` working through mDNS, but do not rely on it as the only
  app configuration.
- Record the active SSH port. Current diagnosis shows port `22`, not `2222`.
- Add a dedicated SSH key for maintenance so future diagnosis does not depend
  on interactive password entry.

### Phase 2: Power And Sensor Reliability

- Fix undervoltage until health power flags clear.
- Re-test with camera/USB load disconnected, then reconnect devices one by one.
- Inspect and, if needed, replace the DHT22.
- Keep the circuit breaker behavior strict: failed sensor hardware must degrade
  readings without hanging lamp control.

### Phase 3: API Observability

- Keep `/api/health` as the canonical deploy gate.
- Ensure `/api/health/`, `/api/health/ready`, `/api/health/live`, and
  `/api/health/metrics` return API responses instead of the SPA fallback.
- Include explicit health `issues` so power and sensor faults are visible
  without parsing every nested field.
- Treat an open sensor circuit breaker as a critical health condition.

### Phase 4: Deployment Safety

- Preserve runtime-only files during GitHub runner deployment:
  `.env`, local config, databases, logs, backups, and venv.
- Install Python dependencies from `requirements.txt` before service restart.
- Keep the post-deploy health gate strict: critical health should fail the
  deploy job rather than hiding hardware faults.
- Restrict automatic production deploys to `main`; use manual workflow dispatch
  only after the live health state has been reviewed.

### Phase 5: Data And Runner Maintenance

- Review SQLite growth and unsynced log counts after SSH access is available.
- Define retention/export behavior for sensor, lamp, event, plug, and cost logs.
- Recover the self-hosted GitHub runner if it remains offline after power is
  stable.
- Add periodic manual or automated smoke checks for:
  - API reachability
  - `/api/health`
  - `/api/temperature`
  - current lamp state

## Validation Commands

Local validation for code and scripts:

```bash
bash -n scripts/pi/diagnose_local_pi.sh
bash -n scripts/pi/github_runner_deploy.sh
bash -n pi-controller/install.sh
cd pi-controller
python -m pytest -q tests/unit/test_power_monitor.py tests/unit/test_systemd_watchdog.py tests/unit/test_status_health.py
./smoke_test.sh http://<PI_HOST>:5000
```

Expected current live smoke result before hardware repair: all reachable API
paths pass except `/api/temperature`, which fails with HTTP `503` while the
DHT22 fault is present.
