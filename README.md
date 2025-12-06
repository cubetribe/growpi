# GrowPi - Raspberry Pi Web-Konfiguration

Web-basiertes Dashboard zur Überwachung und Steuerung eines Raspberry Pi Systems.

## Projektübersicht

GrowPi ist eine moderne Web-Anwendung, die Daten von einem Raspberry Pi sammelt und in einer übersichtlichen Landing-Page darstellt. Das System besteht aus einem Backend (läuft auf dem Raspberry Pi) und einem Frontend zur Visualisierung der Daten.

## Features

### ✅ Implementiert
- 🌐 **Web-Dashboard**: Vollständiges Next.js Dashboard mit Dark Theme (http://growpi.nm-forum.de)
- 💡 **Beleuchtungssteuerung**: 5-Kanal PWM Lampen mit Kurven-Editor
- 📊 **Sensor-Visualisierung**: Echtzeit-Charts für Temperatur, Luftfeuchtigkeit, Bodenwerte
- 💰 **Stromkosten-Monitoring**: Verbrauchsüberwacht (Heute/Woche/Monat/Jahr, Custom Range)
- 🌡️ **Automatische Raum-Klimakontrolle**: Temperatur, Luftfeuchtigkeit, Entfeuchter Auto-Steuerung
- 🔐 **Authentifizierung**: JWT-basierte Anmeldung mit Row-Level Security
- 🌍 **Mehrsprachig**: Deutsch / Englisch
- 📱 **Responsive**: Mobile-optimiert mit Slide-out Sidebar
- 🌡️ **DHT22 Sensor**: Hardware-verifiziert auf GPIO-4 (21.0°C, 64% RH)

### 🚧 In Entwicklung
- 🔌 **RS485 Bodensensoren**: pH, EC, NPK, Bodenfeuchte
- 🎛️ **PWM Lampen-Hardware**: 5 LED-Kanäle über GPIO
- 🤖 **Pi Controller Service**: Python-basierter Daemon für Sensorabfrage
- 📡 **API-Integration**: Pi ↔ VPS Kommunikation

### 📋 Geplant
- 📈 **Historische Daten**: Langzeit-Datenarchivierung
- 🔔 **Alert-System**: E-Mail/Push bei Schwellwertüberschreitung
- 📸 **Kamera-Integration**: Zeitraffer-Aufnahmen
- 💧 **Bewässerungssteuerung**: Automatische Ventilsteuerung

## Tech Stack

### Frontend (Production)
- **Framework**: Next.js 13.5.1 (App Router)
- **Language**: TypeScript (strict mode)
- **Database**: Supabase (PostgreSQL)
- **UI**: shadcn/ui (Radix) + TailwindCSS
- **Charts**: Recharts
- **Auth**: JWT in HTTP-only cookies
- **Deployed**: http://growpi.nm-forum.de

### Backend / Hardware (Raspberry Pi)
- **Python**: 3.13.5
- **Hardware**: Raspberry Pi 4 Model B
- **OS**: Raspberry Pi OS (Debian, Linux 6.12.47 aarch64)
- **GPIO Control**: pigpio for hardware PWM
- **Sensors**: adafruit-circuitpython-dht 4.0.10
- **Communication**: HTTPS REST API polling

### Raspberry Pi Hardware
- **Model**: Raspberry Pi 3B+
- **Hostname**: growpi
- **IP**: 192.168.0.86
- **SSH**: Port 22 (admin user)
- **Hardware Status**:
  - ✅ DHT22 Sensor (GPIO-4, Pin 7) - Verified
  - ✅ PWM GPIO-18 (Pin 12) - Verified
  - ⏳ PWM GPIO-12,13,19,21 - Pending
  - ⏳ RS485 Sensors - Pending

**📌 [Vollständige Pin-Belegung](docs/HARDWARE_PINOUT.md)** ← Detaillierte Hardware-Dokumentation

## Projekt-Struktur

```
GrowPi/
├── frontend/          # React Frontend
├── backend/           # Backend API (auf Raspberry Pi)
├── docs/              # Dokumentation
├── .env               # Umgebungsvariablen (NICHT committen!)
└── README.md          # Diese Datei
```

## Setup

### Voraussetzungen

- Node.js 20+
- SSH-Zugriff auf Raspberry Pi
- npm oder yarn

### Installation

1. Repository klonen
```bash
git clone <repository-url>
cd GrowPi
```

2. Umgebungsvariablen konfigurieren
```bash
cp .env.example .env
# .env mit deinen Zugangsdaten befüllen
```

3. Frontend installieren
```bash
cd frontend
npm install
```

4. Backend auf Raspberry Pi deployen
```bash
# Details folgen
```

## Entwicklung

### Frontend starten
```bash
cd frontend
npm run dev
```

### Backend auf Raspberry Pi
```bash
ssh admin@192.168.0.86
# Weitere Befehle folgen
```

### Quick Start Guide
Für detaillierte Deployment-Anweisungen siehe [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)

### Testing

**Unit Tests:**
```bash
cd pi-controller
source venv/bin/activate
pytest tests/ -v --cov=grow_pi
# Expected: 140/140 tests PASSED (93% coverage)
```

**Smoke Tests:**
```bash
cd pi-controller
./smoke_test.sh
# Tests API endpoints with curl
```

**Test Environment:**
```bash
cd pi-controller/test_environment
python run_local.py
# Runs local Flask server with mock hardware
```

## Hardware Testing & Development

### SSH-Verbindung zum Raspberry Pi

```bash
# Standard SSH
ssh admin@192.168.0.86

# Mit sshpass (für Scripts)
sshpass -p 'PASSWORD' ssh admin@192.168.0.86

# Hostname: growpi
```

### DHT22 Sensor testen

Der DHT22 Temperatur- und Luftfeuchtigkeitssensor ist auf **GPIO-4** angeschlossen.

**Quick Test:**
```bash
ssh admin@192.168.0.86
sudo python3 /tmp/test_dht22.py
```

**Expected Output:**
```
=== DHT22 Sensor Test auf GPIO-4 ===
Lese Sensor aus...

Messung 1:
  Temperatur: 21.0°C
  Luftfeuchtigkeit: 64.0%
```

**Python Code Pattern:**
```python
import board
import adafruit_dht

# GPIO-4 = board.D4
dhtDevice = adafruit_dht.DHT22(board.D4)

temperature = dhtDevice.temperature  # °C
humidity = dhtDevice.humidity        # %

dhtDevice.exit()  # Cleanup
```

### GPIO Pin Assignment

Gemäß **docs/SPEC_RASPBERRY_PI.md**:

**PWM Lampen (Output)**:
- GPIO 12 → Kanal 1 (Red)
- GPIO 13 → Kanal 2 (Blue)
- GPIO 18 → Kanal 3 (Warm White)
- GPIO 19 → Kanal 4 (Cool White)
- GPIO 21 → Kanal 5 (UV) [Software PWM]

**Sensoren (Input)**:
- GPIO 4 → DHT22 (Temp + Humidity) ✅ Verified
- GPIO 17 → Reserved

**RS485**:
- USB-to-RS485 Adapter → `/dev/ttyUSB0`
- Soil sensors via Modbus protocol

## Deployment

Details zum Deployment folgen nach Fertigstellung der ersten Version.

## Sicherheit

⚠️ **WICHTIG**: Die `.env` Datei enthält sensible Zugangsdaten und darf NIEMALS committed werden!

- Zugangsdaten werden über Umgebungsvariablen verwaltet
- `.gitignore` ist entsprechend konfiguriert
- Bei Problemen: Passwörter sofort ändern!

## Roadmap

### Phase 1: Frontend & Database ✅
- [x] Next.js Dashboard mit App Router
- [x] Supabase PostgreSQL Database
- [x] JWT Authentifizierung
- [x] Lighting Curve Editor (5 Kanäle)
- [x] Sensor Charts (Recharts)
- [x] Responsive Design (Mobile)
- [x] i18n (Deutsch/Englisch)
- [x] Production Deployment (http://growpi.nm-forum.de)

### Phase 2: Hardware Integration 🚧
- [x] SSH-Zugriff zum Raspberry Pi
- [x] DHT22 Sensor-Test (GPIO-4)
- [ ] DHT22 Sensor-Klasse implementieren
- [ ] RS485 Bodensensoren testen
- [ ] PWM Lampen-Steuerung (GPIO 12,13,18,19,21)
- [ ] Python Controller Service (systemd)
- [ ] API-Kommunikation Pi ↔ VPS

### Phase 3: Production Features 📋
- [ ] Historische Daten (Langzeitarchiv)
- [ ] Alert-System (E-Mail/Push)
- [ ] Offline-Modus (Pi arbeitet autonom)
- [ ] Datenexport (CSV/Excel)
- [ ] Kamera-Integration
- [ ] Bewässerungssteuerung

## Entwickler

Dennis Westermann (d.westermann@ol-mg.de)

## Lizenz

TBD

---

**Status**: 🟢 Phase 1 Complete | 🟡 Phase 2 In Progress (Hardware Testing)

*Letzte Aktualisierung: 2025-12-04*

---

## Aktueller Entwicklungsstand

**Frontend**: ✅ Production-ready (http://growpi.nm-forum.de)
**Hardware**: 🔧 DHT22 verified, RS485 + PWM pending
**Integration**: ⏳ Controller service in development

**Nächster Milestone**: Vollständige Python Controller Implementation
