# GrowPi Test Environment

Diese Testumgebung ermöglicht es, den GrowPi Controller **lokal auf macOS/Linux zu testen**, ohne echte Hardware (Raspberry Pi, GPIO, DHT22 Sensor).

## Überblick

Die Test-Umgebung simuliert alle Hardware-Komponenten:
- **MockPWMController**: Simuliert GPIO-PWM-Steuerung ohne pigpio
- **MockDHT22**: Generiert realistische Temperatur/Luftfeuchtigkeits-Daten
- **MockDataLogger**: In-Memory Datenbank statt SQLite
- **Flask API**: Läuft identisch zum echten System

## Voraussetzungen

### Nur Python-Dependencies
```bash
# Keine Hardware-spezifischen Pakete erforderlich!
pip install flask flask-cors pyyaml
```

### NICHT erforderlich
- pigpio (nur auf Raspberry Pi)
- board / adafruit_dht (Sensor-Bibliotheken)
- SQLite (wird gemockt)

## Quick Start

### 1. Installation
```bash
cd pi-controller/test_environment
pip install -r requirements.txt
```

### 2. Server starten
```bash
python run_local.py
```

Der Server startet auf `http://localhost:5000` im **SIMULATION MODE**.

### 3. API testen
```bash
# System-Status abrufen
curl http://localhost:5000/api/status

# Lampe auf 50% setzen
curl -X POST http://localhost:5000/api/lamp/1 \
  -H "Content-Type: application/json" \
  -d '{"intensity": 50}'

# Temperatur abrufen (Mock-Daten)
curl http://localhost:5000/api/temperature
```

## Konfiguration

### Test-Config (`config_test.yaml`)

```yaml
simulation_mode: true  # Aktiviert Mock-Hardware
lamps:
  channels:
    - channel: 1
      name: "Far Red"
      gpio_pin: 16  # Wird ignoriert im Simulation Mode
    # ...
```

**Wichtig**: `simulation_mode: true` aktiviert automatisch alle Mocks.

## Mock-Komponenten

### MockPWMController
Simuliert PWM-Steuerung ohne echte GPIO-Pins.

**Features**:
- Speichert Intensitäten in-memory
- Gibt realistische Logging-Ausgaben
- Keine Hardware-Abhängigkeiten

**Usage**:
```python
from mock_hardware import MockPWMController

controller = MockPWMController()
controller.set_intensity(1, 50)  # Kanal 1 auf 50%
state = controller.get_current_state()  # {1: 50, 2: 0, ...}
```

### MockDHT22
Generiert realistische Sensor-Daten.

**Daten-Charakteristik**:
- Temperatur: 18-26°C mit Sinus-Variation (simuliert Tag/Nacht)
- Luftfeuchtigkeit: 50-70% mit Rauschen
- Zeitabhängig (morgens kühler, nachmittags wärmer)

**Usage**:
```python
from mock_hardware import MockDHT22

sensor = MockDHT22()
temp, humidity = sensor.read()  # (22.3, 58.4)
```

### MockDataLogger
In-Memory Datenbank für Logging.

**Features**:
- Keine SQLite-Datei erforderlich
- Speichert Daten in Python-Listen
- Gleiche API wie echter DataLogger

**Usage**:
```python
from mock_hardware import MockDataLogger

logger = MockDataLogger()
logger.log_sensor_reading('temperature', 22.5)
readings = logger.get_sensor_logs()  # Liste aller Readings
```

## Test-Szenarien

### 1. Basis-Funktionalität
```python
# Start test server
python run_local.py
```

**Prüfen**:
- Server startet ohne Fehler
- `/api/status` gibt valide Daten zurück
- Mock-Sensoren liefern Werte

### 2. Lampen-Steuerung
```bash
# Alle Lampen auf verschiedene Werte setzen
for i in 1 2 3 4; do
  curl -X POST http://localhost:5000/api/lamp/$i \
    -H "Content-Type: application/json" \
    -d "{\"intensity\": $((i * 25))}"
done

# Status prüfen
curl http://localhost:5000/api/status | jq '.lamps'
```

**Erwartetes Ergebnis**:
```json
{
  "lamps": [
    {"channel": 1, "name": "Far Red", "intensity": 25},
    {"channel": 2, "name": "Warm White", "intensity": 50},
    {"channel": 3, "name": "Cool White", "intensity": 75},
    {"channel": 4, "name": "UV", "intensity": 100}
  ]
}
```

### 3. Sensor-Logging
```bash
# 10 Sekunden warten, dann Logs abrufen
sleep 10
curl http://localhost:5000/api/logs/sensors | jq
```

**Erwartetes Ergebnis**:
- Mehrere Temperatur/Humidity-Readings
- Zeitstempel innerhalb der letzten 10 Sekunden
- Realistische Werte (temp: ~22°C, humidity: ~60%)

### 4. Kurven-Steuerung (wenn implementiert)
```bash
# Kurve für Kanal 1 setzen
curl -X PUT http://localhost:5000/api/curves/1 \
  -H "Content-Type: application/json" \
  -d '{
    "curve": [
      {"time": "06:00", "intensity": 0},
      {"time": "12:00", "intensity": 80},
      {"time": "20:00", "intensity": 0}
    ],
    "enabled": true
  }'

# Aktuelle Intensität abrufen (zeitabhängig)
curl http://localhost:5000/api/curves/intensities
```

## Docker-Support (Optional)

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["python", "run_local.py"]
```

### Bauen & Starten
```bash
docker build -t growpi-test .
docker run -p 5000:5000 growpi-test
```

**Vorteil**: Isolierte Test-Umgebung, funktioniert identisch auf allen Systemen.

## Debugging

### Log-Levels anpassen
```python
# In run_local.py
import logging
logging.basicConfig(level=logging.DEBUG)  # Mehr Output
```

### Mock-Daten anpassen
```python
# In mock_hardware.py
class MockDHT22:
    def read(self):
        # Custom test data
        return (25.0, 65.0)  # Feste Werte für Tests
```

### Flask Debug Mode
```python
# In run_local.py
app.run(debug=True)  # Auto-reload bei Code-Änderungen
```

## Unterschiede zur Produktions-Umgebung

| Feature | Test-Umgebung | Raspberry Pi |
|---------|---------------|--------------|
| GPIO-Steuerung | Gemockt (In-Memory) | Echte PWM via pigpio |
| DHT22 Sensor | Synthetische Daten | Echte Hardware-Reads |
| Datenbank | In-Memory Listen | SQLite-Datei |
| Config-Datei | `config_test.yaml` | `config/config.yaml` |
| Performance | Sofort (kein I/O) | Hardware-Latenz |

## Continuous Integration

### GitHub Actions Beispiel
```yaml
name: Test GrowPi Controller

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd pi-controller/test_environment
          pip install -r requirements.txt

      - name: Run tests
        run: |
          cd pi-controller/test_environment
          python run_local.py &
          sleep 5
          curl http://localhost:5000/api/status
```

## Troubleshooting

### Problem: `ModuleNotFoundError: No module named 'pigpio'`
**Lösung**: Stelle sicher, dass `simulation_mode: true` in `config_test.yaml` gesetzt ist.

### Problem: Mock-Daten ändern sich nicht
**Ursache**: MockDHT22 verwendet Zeit-basierte Variation.
**Lösung**: Warte 60 Sekunden oder ändere `time.time()` für Tests.

### Problem: Logging-Daten verschwinden
**Ursache**: In-Memory Storage wird bei Restart gelöscht.
**Lösung**: Normal - für persistente Daten echte SQLite-Datenbank verwenden.

## Nächste Schritte

### Erweiterungen
- **Unit Tests**: pytest-Framework für automatisierte Tests
- **Integration Tests**: Testen Sie API-Endpoints systematisch
- **Frontend-Mock**: Serve static HTML für UI-Testing
- **Snapshot-Tests**: Vergleichen Sie API-Responses gegen Baselines

### Migration zu Real Hardware
1. Ändere `simulation_mode: false` in `config.yaml`
2. Installiere Hardware-Dependencies: `pip install pigpio adafruit-circuitpython-dht`
3. Verbinde echte Sensoren/GPIO
4. Starte mit `sudo python -m grow_pi.web.api`

## Support

**Dokumentation**: Siehe `docs/SPEC_RASPBERRY_PI.md`
**Issues**: GitHub Issues im Repository
**Entwickler**: d.westermann@ol-mg.de

---

**Letzte Aktualisierung**: 2025-12-06
**Version**: 1.0.0
