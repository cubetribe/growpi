# GrowPi - Raspberry Pi Controller

Python-basierter Controller-Service für den Raspberry Pi 3B+.

## Übersicht

Dieser Controller läuft auf dem Raspberry Pi und steuert Grow-Lampen via PWM.

**Aktueller Stand: v6.7 (2025-12-06)**
- Web-Interface auf Port 5000
- Live-Kamera Livestream (USB-Webcam, 720p)
- Sonnenkurven-Modus mit automatischer Tageszeit-Interpolation
- 4 PWM-Kanäle für LED-Steuerung
- Raumklima-Steuerung mit Entfeuchtung
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
sudo systemctl status grow-pi
```

### 5. Logs prüfen

```bash
sudo journalctl -u grow-pi -f
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
| 3     | Cool White  | 12   | 32  | ✅ Aktiv |
| 4     | UV          | 18   | 12  | ✅ Aktiv |

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

| Level | Feature              | Status |
|-------|----------------------|--------|
| 1     | Feste Lampenwerte    | ✅ Done |
| 2     | Logging verbessern   | ✅ Done |
| 3     | DHT22 Sensor         | ✅ Done (2025-12-05) |
| 4     | Kurven-Interpolation | ✅ Done |
| 4b    | Web-Interface        | ✅ Done |
| 5     | SQLite Daten-Logging | ✅ Done (2025-12-05) |
| 6     | Kosten-Tracking      | ✅ Done (2025-12-06) |
| 7     | Room Environment     | ✅ Done (2025-12-06) |
| 8     | **Live-Kamera**      | ✅ Done (2025-12-06) |
| 9     | Timelapse            | ⏳ Vorbereitet |
| 10    | RS485 Bodensensoren  | ⏳     |

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

# Start / Stop / Restart
sudo systemctl start grow-pi
sudo systemctl stop grow-pi
sudo systemctl restart grow-pi

# Auto-Start aktivieren/deaktivieren
sudo systemctl enable grow-pi
sudo systemctl disable grow-pi

# Logs (live)
sudo journalctl -u grow-pi -f

# Logs (letzte 100 Zeilen)
sudo journalctl -u grow-pi -n 100
```

---

## Troubleshooting

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

---

## Referenzen

- **Hardware Pinout**: [`../docs/HARDWARE_PINOUT.md`](../docs/HARDWARE_PINOUT.md)
- **Raspberry Pi Spec**: [`../docs/SPEC_RASPBERRY_PI.md`](../docs/SPEC_RASPBERRY_PI.md)

---

**Python Version**: 3.13
**Aktuelles Level**: v6.7 (CPU-Optimierung)
**Stand**: 2025-12-06
**Web-Interface**: http://192.168.0.86:5000
**Changelog**: [CHANGELOG.md](CHANGELOG.md)

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
