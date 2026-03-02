# GrowPi - Raspberry Pi Controller

Python-basierter Controller-Service für den Raspberry Pi 3B+.

## Übersicht

Dieser Controller läuft auf dem Raspberry Pi und steuert Grow-Lampen via PWM.

**Aktueller Stand: v6.25.2 (2026-03-02) - Split-Process Consistency Hardening**
- Web-Interface auf Port 5000
- **Tank-Mode Hardening**: Production-Ready Robustness
  - Circuit Breaker für DHT22 Sensor (Auto-Recovery nach Freeze)
  - systemd Watchdog Integration (Auto-Restart bei Hang)
  - Thread-Safe Operations mit Lock Ordering Convention
  - Database Retry-on-Busy mit exponential backoff
- **Observability Layer**: Health Check API & Incident Snapshots
  - `/api/health/` - Comprehensive Health Check
  - `/api/health/ready` - Kubernetes Readiness Probe
  - `/api/health/live` - Liveness Probe
  - `/api/health/metrics` - Prometheus-Style Metriken
- **Pi Health Monitoring**: Live System-Metriken im Dashboard
- Live-Kamera Livestream (USB-Webcam, 720p, Auto-Detection)
- **TinyTuya Lokale Steuerung**: Smart Plugs ohne Cloud-API
- Sonnenkurven-Modus mit automatischer Tageszeit-Interpolation
- 4 PWM-Kanäle für LED-Steuerung
- Raumklima-Steuerung mit Entfeuchtung
- **Grow Calendar** mit Phase Tracking & Milestones
- **CPU-optimiert**: ~28% statt 75% Auslastung

## Quick Start (MVP)

### 1. Auf den Pi kopieren

```bash
# Vom Entwicklungs-PC:
scp -r pi-controller admin@192.168.0.86:/home/admin/
```

### 2. Installation

```bash
# Auf dem Pi:
cd /home/admin/pi-controller
chmod +x install.sh
./install.sh
```

Wichtig nach der Installation:

```bash
sudo reboot
```

### 3. Konfiguration anpassen

```bash
nano /opt/grow-pi/config/config.yaml
```

Setze die gewünschten Lampen-Intensitäten (0-100%):

```yaml
lamps:
  channels:
    - channel: 1
      name: "Far Red"
      gpio_pin: 16          # Pin 36
      default_intensity: 10

    - channel: 2
      name: "Warm White"
      gpio_pin: 13          # Pin 33
      default_intensity: 10

    - channel: 3
      name: "Cool White"
      gpio_pin: 12          # Pin 32
      default_intensity: 10

    - channel: 4
      name: "UV"
      gpio_pin: 18          # Pin 12
      default_intensity: 0
```

### 4. Service starten

```bash
sudo systemctl start grow-pi
sudo systemctl start growpi-web
sudo systemctl status grow-pi
sudo systemctl status growpi-web
```

### 5. Logs prüfen

```bash
sudo journalctl -u grow-pi -f
sudo journalctl -u growpi-web -f
```

---

## Hardware

- **Platform**: Raspberry Pi 3B+
- **Hostname**: growpi
- **IP**: 192.168.0.86

### PWM Kanäle (FINAL - 2025-12-05)

| Kanal | Farbe       | GPIO | Pin | Status |
|-------|-------------|------|-----|--------|
| 1     | Far Red     | 16   | 36  | ✅ Aktiv |
| 2     | Warm White  | 13   | 33  | ✅ Aktiv |
| 3     | Cool White  | 18   | 12  | ✅ Aktiv |
| 4     | UV          | 12   | 32  | ✅ Aktiv |

Detaillierte Pin-Belegung: [`../docs/HARDWARE_PINOUT.md`](../docs/HARDWARE_PINOUT.md)

---

## Entwicklung

### Test-Modus (ohne Service)

```bash
cd /opt/grow-pi
source venv/bin/activate

# Test: Initialisieren und Status zeigen, dann beenden
python -m grow_pi.main --test

# Normal starten (Ctrl+C zum Stoppen)
python -m grow_pi.main
```

### Debug-Logging

In `config/config.yaml`:

```yaml
logging:
  level: "DEBUG"
```

---

## Architektur (MVP)

```
pi-controller/
├── grow_pi/
│   ├── __init__.py
│   ├── __main__.py      # Module entry point
│   ├── main.py          # Hauptcontroller
│   ├── config.py        # YAML Konfiguration laden
│   └── lamps/
│       ├── __init__.py
│       └── pwm_controller.py  # PWM Steuerung
├── config/
│   └── config.yaml      # Konfiguration mit Intensitäten
├── systemd/
│   └── grow-pi.service  # Auto-Start Service
├── install.sh           # Installations-Script
└── requirements.txt
```

---

## Erweiterungs-Roadmap

| Level | Feature                  | Status |
|-------|--------------------------|--------|
| 1     | Feste Lampenwerte        | ✅ Done |
| 2     | Logging verbessern       | ✅ Done |
| 3     | DHT22 Sensor             | ✅ Done (2025-12-05) |
| 4     | Kurven-Interpolation     | ✅ Done |
| 4b    | Web-Interface            | ✅ Done |
| 5     | SQLite Daten-Logging     | ✅ Done (2025-12-05) |
| 6     | Kosten-Tracking          | ✅ Done (2025-12-06) |
| 7     | Room Environment         | ✅ Done (2025-12-06) |
| 8     | **Live-Kamera**          | ✅ Done (2025-12-06) |
| 9     | Timelapse                | ✅ Done (2025-12-09) |
| 10    | **Grow Calendar**        | ✅ Done (2025-12-17) |
| 11    | **Pi Health Monitoring** | ✅ Done (2025-12-20) |
| 12    | **TinyTuya Lokal**       | ✅ Done (2025-12-20) |
| 13    | **Tank-Mode Hardening**  | ✅ Done (2025-12-26) |
| 14    | RS485 Bodensensoren      | ⏳ Geplant |

### Health Monitoring API (v6.23.0 - Enhanced)

```bash
# Comprehensive Health Check (mit CPU-Temp, RAM, Disk, Sensor Status)
curl "http://192.168.0.86:5000/api/health/"
# → {
#     "status": "healthy",
#     "version": "6.23.0",
#     "timestamp": "2025-12-26T10:30:00Z",
#     "system": {
#       "cpu_temp": 52.3,
#       "cpu_temp_status": "normal",
#       "cpu_load": 28.5,
#       "memory_percent": 62.1,
#       "memory_status": "normal",
#       "disk_percent": 45.3,
#       "disk_status": "normal",
#       "uptime_seconds": 345678
#     },
#     "sensor": {
#       "available": true,
#       "error_count": 0,
#       "circuit_breaker_state": "closed"
#     },
#     "database": {
#       "available": true,
#       "active_connections": 3
#     }
#   }

# Kubernetes Readiness Probe (Ready to serve traffic?)
curl "http://192.168.0.86:5000/api/health/ready"
# → 200 OK or 503 Service Unavailable

# Kubernetes Liveness Probe (Application alive?)
curl "http://192.168.0.86:5000/api/health/live"
# → 200 OK or 503 Service Unavailable

# Prometheus-Style Metrics
curl "http://192.168.0.86:5000/api/health/metrics"
# → {
#     "sensor_error_count": 0,
#     "database_active_connections": 3,
#     "circuit_breaker_state": "closed",
#     "system_cpu_load": 28.5,
#     "system_memory_percent": 62.1
#   }
```

### Camera API Endpoints

```bash
# Live-Snapshot (JPEG)
curl "http://192.168.0.86:5000/api/camera/snapshot" -o snapshot.jpg

# Kamera-Status
curl "http://192.168.0.86:5000/api/camera/status"
# → {"available": true, "resolution": "1280x720", ...}
```

### Logging API Endpoints

```bash
# Sensor-Historie (letzte 24h)
curl "http://192.168.0.86:5000/api/logs/sensors?type=temperature&hours=24"

# Lampen-Historie für Kanal 1
curl "http://192.168.0.86:5000/api/logs/lamps?channel=1&hours=24"

# System-Events
curl "http://192.168.0.86:5000/api/logs/events"

# Logging-Statistiken
curl "http://192.168.0.86:5000/api/logs/stats"
```

---

## Service-Befehle

```bash
# Status
sudo systemctl status grow-pi
sudo systemctl status growpi-web

# Start / Stop / Restart
sudo systemctl start grow-pi
sudo systemctl start growpi-web
sudo systemctl stop grow-pi
sudo systemctl stop growpi-web
sudo systemctl restart grow-pi
sudo systemctl restart growpi-web

# Auto-Start aktivieren/deaktivieren
sudo systemctl enable grow-pi
sudo systemctl enable growpi-web
sudo systemctl disable grow-pi
sudo systemctl disable growpi-web

# Logs (live)
sudo journalctl -u grow-pi -f
sudo journalctl -u growpi-web -f

# Logs (letzte 100 Zeilen)
sudo journalctl -u grow-pi -n 100
sudo journalctl -u growpi-web -n 100
```

### GitHub Actions Auto-Deploy (Self-Hosted Runner)

Der Pi kann Deployments nach `git push` automatisch selbst ausführen.

- Workflow: `../.github/workflows/pi-autodeploy.yml`
- Deploy-Skript: `../scripts/pi/github_runner_deploy.sh`
- Setup/Architektur: `../docs/GITHUB_ACTIONS_PI_AUTODEPLOY.md`

Wichtig:
- Keine eingehenden Ports im Router erforderlich
- Runner verbindet sich nur ausgehend per HTTPS zu GitHub
- Deployment-Feedback (PASS/FAIL + Logs) erscheint direkt im GitHub Actions Run

### Watchdog-Checks

```bash
# Service-Watchdog aus Unit prüfen (WatchdogSec)
systemctl show grow-pi -p WatchdogUSec

# systemd-Manager-Hardware-Watchdog prüfen
systemctl show -p RuntimeWatchdogUSec -p RebootWatchdogUSec

# Runtime-Watchdog Ereignisse ansehen
sudo journalctl -u grow-pi --since "15 min ago" | grep -Ei "watchdog|unhealthy|recovered"
```

---

## Troubleshooting

### Version im Frontend aktualisieren

Nach Code-Updates oder Änderungen an der VERSION-Datei:

```bash
# Service neu starten
sudo systemctl restart grow-pi

# Im Browser: Hard-Refresh für aktuelle Version-Anzeige
# - macOS: Cmd + Shift + R
# - Windows/Linux: Strg + Shift + R
```

Die Version wird im Web-Interface oben rechts angezeigt und sollte mit der VERSION-Datei übereinstimmen.

### pigpiod nicht gestartet

```bash
sudo systemctl start pigpiod
sudo systemctl status pigpiod
```

### Keine Berechtigung für GPIO

```bash
# User zur gpio Gruppe hinzufügen
sudo usermod -a -G gpio admin
# Neu einloggen erforderlich
```

### Service startet nicht

```bash
# Manuell testen
cd /opt/grow-pi
source venv/bin/activate
python -m grow_pi.main --test

# Fehler in Logs prüfen
sudo journalctl -u grow-pi -n 50 --no-pager
```

### Service-Reboot-Loop (StartLimit erreicht)

```bash
# Letzte Fehler ansehen
sudo journalctl -u grow-pi -n 200 --no-pager

# Unit-Parameter prüfen
systemctl cat grow-pi

# Nach Fix Startlimit zurücksetzen und neu starten
sudo systemctl reset-failed grow-pi
sudo systemctl restart grow-pi
```

---

## Referenzen

- **Hardware Pinout**: [`../docs/HARDWARE_PINOUT.md`](../docs/HARDWARE_PINOUT.md)
- **Raspberry Pi Spec**: [`../docs/SPEC_RASPBERRY_PI.md`](../docs/SPEC_RASPBERRY_PI.md)

---

**Python Version**: 3.13
**Aktuelles Level**: v6.25.2 (Split-Process Consistency Hardening)
**Stand**: 2026-03-02
**Web-Interface**: http://192.168.0.86:5000
**Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

## Tank-Mode Features (v6.25.2)

### Production-Ready Robustness

**Circuit Breaker Pattern:**
- Automatische Abschaltung nach 5 Sensor-Fehlern
- 30s Erholungszeit, dann Auto-Recovery
- Verhindert kompletten System-Freeze bei DHT22-Problemen

**systemd Watchdog:**
- Automatischer Service-Restart bei Hang (60s Timeout)
- Watchdog-Ping dynamisch aus `WATCHDOG_USEC` (50% Intervall)
- sd_notify Integration (READY, WATCHDOG, STOPPING)
- Interner Runtime-Watchdog prüft Main-Loop + kritische Worker-Threads
- Bei Teil-Ausfällen wird `WATCHDOG=trigger` ausgelöst (sofortige Recovery)
- Crash-Loop-Schutz mit `StartLimit*` + Reboot-Eskalation

**Hardware Watchdog (Host-Ebene):**
- Kernel-Watchdog via `dtparam=watchdog=on`
- systemd Manager Watchdog (`RuntimeWatchdogSec=15s`)
- Schutz auch bei Host-Freeze außerhalb des Python-Prozesses

**Process Splitting (neu):**
- `grow-pi.service` steuert nur den Controller (`--no-web`)
- `growpi-web.service` betreibt die API separat
- Modus-Synchronisierung läuft prozessübergreifend über `/run/growpi/mode.txt`
- Teilausfälle bleiben isoliert und werden je Service separat neu gestartet

**Thread-Safety:**
- RLock für Sensor Cache (erlaubt nested calls)
- Lock für Mode Manager Operations
- Lock + fcntl für PWM State File
- Dokumentierte Lock Ordering Convention (verhindert Deadlocks)

**Database Hardening:**
- 30s Connect Timeout (statt 5s)
- Retry-on-Busy mit exponential backoff (3 Retries)
- Per-Thread Connections (threading.local())
- atexit Handler für Connection Cleanup

**Observability:**
- Health Check Endpoints (/api/health/*)
- Incident Snapshots bei kritischen Fehlern
- Structured Logging mit Thread-Info
- Prometheus-Style Metriken

---

## Performance-Optimierung (v6.7)

Die CPU-Last wurde von ~75% auf ~28% reduziert:

| Optimierung | Vorher | Nachher |
|-------------|--------|---------|
| Kamera-Polling | 500ms | 10s |
| Main-Loop Sleep | 1s | 5s |
| DataLogger Sleep | for-loop | Event.wait() |
| Logging-Intervall | 60s | 120s |
| DHT22 Cache | 3s | 30s |
