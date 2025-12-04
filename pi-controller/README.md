# GrowPi - Raspberry Pi Controller

Python-basierter Controller-Service für den Raspberry Pi 3B+.

## Übersicht

Dieser Controller läuft auf dem Raspberry Pi und:
- Liest Sensor-Daten (DHT22, RS485 Bodensensoren)
- Steuert 5-Kanal PWM LED-Lampen
- Kommuniziert mit dem VPS-Server via HTTPS API
- Arbeitet autonom bei Netzwerkausfall (Offline-Modus)

## Hardware

- **Platform**: Raspberry Pi 3B+
- **Hostname**: growpi
- **IP**: 192.168.0.86

Detaillierte Pin-Belegung: [`../docs/HARDWARE_PINOUT.md`](../docs/HARDWARE_PINOUT.md)

## Installation

### Voraussetzungen

```bash
# System-Pakete
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv pigpio

# pigpio Daemon starten
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
```

### Setup

```bash
# Virtual Environment erstellen
cd pi-controller
python3 -m venv venv
source venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt

# Konfiguration anpassen
cp config/config.example.yaml config/config.yaml
# Bearbeite config/config.yaml mit deinem API-Key
```

## Entwicklung

### Lokale Tests

```bash
# Virtual Environment aktivieren
source venv/bin/activate

# Controller starten
python -m grow_pi.main

# Tests ausführen
pytest tests/
```

### Sensor-Tests

```bash
# DHT22 Sensor testen
python -m grow_pi.tests.test_dht22

# PWM Test
python -m grow_pi.tests.test_pwm
```

## Deployment

### Systemd Service

```bash
# Service installieren
sudo cp systemd/grow-pi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable grow-pi
sudo systemctl start grow-pi

# Status prüfen
sudo systemctl status grow-pi

# Logs anzeigen
sudo journalctl -u grow-pi -f
```

## Konfiguration

Siehe [`config/config.example.yaml`](config/config.example.yaml) für alle Optionen.

**Wichtige Einstellungen:**
- `server.url`: VPS API URL
- `server.api_key`: Zone API Key (von Web-Dashboard)
- `sensors.read_interval`: Sensor-Polling-Intervall (Sekunden)
- `lamps.channels`: GPIO-Pin-Zuordnung

## Architektur

```
grow_pi/
├── main.py              # Entry Point
├── config.py            # Config Loader
├── sensors/
│   ├── base.py          # Abstract Sensor Class
│   ├── dht22.py         # DHT22 Implementation
│   └── rs485_soil.py    # RS485 Soil Sensors
├── lamps/
│   ├── pwm_controller.py
│   └── lamp_manager.py
├── api/
│   ├── client.py        # HTTP Client für VPS
│   └── models.py
├── scheduler/
│   ├── sensor_scheduler.py
│   └── lamp_scheduler.py
└── utils/
    └── interpolation.py  # Curve Interpolation
```

## Hardware-Status

### ✅ Verifiziert

- DHT22 Sensor (GPIO-4 / Pin 7)
- PWM GPIO-18 (Pin 12 / Kanal 3)

### ⏳ Ausstehend

- PWM GPIO-12, 13, 19, 21 (Kanäle 1, 2, 4, 5)
- RS485 Bodensensoren

## Referenzen

- **Hardware Pinout**: [`../docs/HARDWARE_PINOUT.md`](../docs/HARDWARE_PINOUT.md)
- **Raspberry Pi Spec**: [`../docs/SPEC_RASPBERRY_PI.md`](../docs/SPEC_RASPBERRY_PI.md)
- **Architektur**: [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)

---

**Python Version**: 3.13.5
**Basierend auf**: SPEC_RASPBERRY_PI.md
