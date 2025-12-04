# GrowPi - Raspberry Pi Controller

Python-basierter Controller-Service für den Raspberry Pi 3B+.

## Übersicht

Dieser Controller läuft auf dem Raspberry Pi und steuert Grow-Lampen via PWM.

**Aktueller Stand: MVP Level 1** - Lampen werden beim Start auf feste Werte gesetzt.

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
      name: "Red"
      gpio_pin: 12
      default_intensity: 50   # <-- Hier anpassen

    - channel: 3
      name: "Warm White"
      gpio_pin: 18
      default_intensity: 75   # <-- Hier anpassen
    # ...
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

### PWM Kanäle

| Kanal | Farbe       | GPIO | Pin | Status       |
|-------|-------------|------|-----|--------------|
| 1     | Red         | 12   | 32  | ⏳ Pending   |
| 2     | Blue        | 13   | 33  | ⏳ Pending   |
| 3     | Warm White  | 18   | 12  | ✅ Verifiziert |
| 4     | Cool White  | 19   | 35  | ⏳ Pending   |
| 5     | UV          | 21   | 40  | ⏳ Pending   |

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
| 1     | Feste Lampenwerte    | ✅ MVP  |
| 2     | Logging verbessern   | ⏳     |
| 3     | DHT22 Sensor         | ⏳     |
| 4     | Kurven-Interpolation | ⏳     |
| 5     | API-Client (Server)  | ⏳     |
| 6     | Offline-Modus        | ⏳     |
| 7     | RS485 Bodensensoren  | ⏳     |

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

**Python Version**: 3.11+
**Aktuelles Level**: MVP (Level 1)
**Stand**: 2025-12-04
