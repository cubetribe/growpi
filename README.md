# GrowPi - Raspberry Pi Gewächshaus-Steuerung

Professionelles Gewächshaus-Management-System mit Echtzeit-Überwachung, automatischer Entfeuchtung und Stromkosten-Tracking.

## Projektübersicht

GrowPi ist ein vollständiges Gewächshaus-Kontrollsystem bestehend aus:
- **Pi-Controller**: Python-basierter Daemon auf Raspberry Pi
- **Web-Interface**: Mobile-optimiertes Dashboard unter http://192.168.0.86:5000
- **Smart Home Integration**: Tuya Cloud API für 6 Smart Plugs

## Features

### ✅ Produktiv (Live auf Pi)

| Feature | Beschreibung | Status |
|---------|--------------|--------|
| 💡 **4-Kanal PWM Beleuchtung** | Far Red, Warm White, Cool White, UV mit Sonnenkurven | ✅ |
| 🌡️ **DHT22 Sensor** | Echtzeit Temperatur & Luftfeuchtigkeit | ✅ |
| 💨 **Entfeuchter-Automatik** | Hysterese-Steuerung (10s Check-Intervall) via Tuya Smart Plug | ✅ |
| 🔌 **6 Smart Plugs** | Tuya Cloud Integration mit Power Monitoring | ✅ |
| 💰 **Stromkosten-Tracking** | kWh-Berechnung pro Gerät mit konfigurierbarem Preis | ✅ |
| 📊 **Datenbank-Logging** | SQLite mit Sensor-, Lampen- und Plug-Logs | ✅ |
| 📱 **Web-Interface** | Mobile-optimiertes Dark-Theme Dashboard | ✅ |

### 📋 Geplant
- 📈 VPD-Optimierung (Vapor Pressure Deficit)
- 💧 Bewässerungssteuerung (Pumpe nach Zeitplan)
- 🔔 Push-Benachrichtigungen
- 📸 Kamera-Integration

## Hardware

### Raspberry Pi 3B+
- **Hostname**: growpi
- **IP**: 192.168.0.86
- **OS**: Raspberry Pi OS (Debian)
- **Python**: 3.13

### GPIO-Belegung

| Kanal | Name | GPIO | Pin | Funktion |
|-------|------|------|-----|----------|
| 1 | Far Red | 16 | 36 | PWM Lampe |
| 2 | Warm White | 13 | 33 | PWM Lampe |
| 3 | Cool White | 12 | 32 | PWM Lampe |
| 4 | UV | 18 | 12 | PWM Lampe |
| - | DHT22 | 4 | 7 | Temp/Humidity |

### Smart Plugs (Tuya Cloud)

| Name | Device ID | Funktion |
|------|-----------|----------|
| Main Light | bf36487f... | Haupt-Grow-Light |
| Entfeuchter | bfc70501... | Automatische Entfeuchtung |
| Wohnzimmer | bfcf3ba9... | Zusatzlicht |
| Mittags Sonne | bfbbc4e0... | Zusatzlicht |
| FR main | bfc332c0... | Far Red Zusatz |
| Pumpe | bfad1a50... | Bewässerung |

## Installation

### 1. Repository klonen
```bash
git clone <repository-url>
cd GrowPi
```

### 2. Pi-Controller deployen
```bash
# Auf dem Raspberry Pi
ssh admin@192.168.0.86
cd /opt/grow-pi
source venv/bin/activate
python -m grow_pi.main
```

### 3. Systemd Service
```bash
sudo systemctl enable grow-pi
sudo systemctl start grow-pi
```

## Projekt-Struktur

```
GrowPi/
├── pi-controller/          # Raspberry Pi Controller (Python)
│   └── grow_pi/
│       ├── main.py         # Hauptcontroller
│       ├── config/         # Konfigurationsdateien
│       │   ├── config.yaml # Lampen-Kurven
│       │   └── room_config.json # Entfeuchter + Kosten
│       ├── database/       # SQLite Logging
│       ├── lamps/          # PWM Controller
│       ├── utils/          # Tuya, Entfeuchter, Kurven
│       └── web/            # Flask API + Frontend
│           ├── api.py      # REST Endpoints
│           └── static/     # Web-Interface (HTML/CSS/JS)
├── frontend/               # Next.js Dashboard (optional)
├── docs/                   # Dokumentation
│   └── ROADMAP.md         # Feature-Planung
└── CHANGELOG.md            # Versionshistorie
```

## API Endpoints

### Status & Kontrolle
| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/status` | GET | Lampen-Status + Temperatur |
| `/api/lamp/<ch>` | POST | Lampe setzen (1-4) |
| `/api/mode` | GET/POST | Modus (auto/manual) |
| `/api/temperature` | GET | DHT22 Werte |

### Kurven
| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/curves` | GET | Alle Lichtkurven |
| `/api/curves/<ch>` | PUT | Kurve aktualisieren |
| `/api/curves/intensities` | GET | Aktuelle Werte |

### Room (Entfeuchter)
| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/room` | GET | Temp, Humidity, Dehumidifier Status |
| `/api/room/config` | POST | Schwellwerte setzen |
| `/api/room/dehumidifier` | POST | Manuell AN/AUS |

### Kosten
| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/costs` | GET | Verbrauch + Kosten (period=today/week/month) |
| `/api/costs/config` | GET/POST | kWh-Preis lesen/setzen |

### Logs
| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/logs/sensors` | GET | Sensor-Historie |
| `/api/logs/lamps` | GET | Lampen-Historie |
| `/api/logs/plugs` | GET | Smart Plug Power-Logs |

## Konfiguration

### room_config.json
```json
{
  "dehumidifier": {
    "enabled": true,              // Automatik AN/AUS
    "target": 60.0,               // Ziel-Luftfeuchtigkeit (%)
    "threshold_high": 65.0,       // AN wenn > 65%
    "threshold_low": 55.0,        // AUS wenn < 55%
    "device_id": "bfc705014c6241667avzn8",
    "min_run_time": 60,          // Min. 60s Laufzeit
    "min_off_time": 60           // Min. 60s Auszeit
  },
  "costs": {
    "kwh_price": 0.30,
    "currency": "EUR"
  },
  "devices": {
    "bf36487f67d7bb8fc18buj": "Main Light",
    "bfc705014c6241667avzn8": "Entfeuchter",
    ...
  }
}
```

## Web-Interface

**URL**: http://192.168.0.86:5000

### Tabs
1. **Steuerung** - Lampen-Slider, Modus-Wechsel
2. **Kurven** - 24h Lichtkurven-Editor
3. **Verlauf** - Sensor- und Lampen-Charts
4. **Room** - Entfeuchter-Steuerung
5. **Kosten** - Stromverbrauch pro Gerät

## Entwicklung

### Lokaler Test (ohne Pi)
```bash
cd pi-controller
python -m pytest tests/
```

### Deployment
```bash
# Dateien zum Pi kopieren
scp -r pi-controller/grow_pi admin@192.168.0.86:/opt/grow-pi/

# Service neustarten
ssh admin@192.168.0.86 "sudo systemctl restart grow-pi"
```

## Dokumentation

- [ROADMAP.md](docs/ROADMAP.md) - Feature-Planung
- [CHANGELOG.md](CHANGELOG.md) - Versionshistorie
- [HARDWARE_PINOUT.md](docs/HARDWARE_PINOUT.md) - GPIO-Belegung

## Entwickler

Dennis Westermann (d.westermann@ol-mg.de)

---

**Status**: 🟢 Phase 2 Complete | 🟡 Phase 1 In Progress (Kosten-Monitoring)

*Letzte Aktualisierung: 2025-12-06*
