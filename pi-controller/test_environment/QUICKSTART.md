# GrowPi Test Environment - Quick Start Guide

Schnellanleitung für die Verwendung der Testumgebung.

## 1. Installation (30 Sekunden)

```bash
cd pi-controller/test_environment
pip install -r requirements.txt
```

**Das war's!** Keine Hardware-Bibliotheken, kein pigpio, kein Raspberry Pi erforderlich.

## 2. Server starten (Methode A: Direkt)

```bash
python run_local.py
```

**Output:**
```
============================================================
GROWPI TEST ENVIRONMENT
============================================================
Simulation Mode: ENABLED
Hardware: ALL MOCKED
Database: IN-MEMORY
============================================================
Starting server on http://0.0.0.0:5000
```

**Server läuft!** Öffne http://localhost:5000/api/status

## 3. Server starten (Methode B: Docker)

```bash
# Aus dem Haupt-Verzeichnis pi-controller/
docker-compose -f test_environment/docker-compose.yml up
```

**Vorteil**: Komplett isoliert, funktioniert identisch überall.

## 4. Erste Tests

### A) Browser-Test
Öffne: http://localhost:5000/api/status

**Erwartete Antwort:**
```json
{
  "success": true,
  "lamps": [
    {"channel": 1, "name": "Far Red", "intensity": 0},
    {"channel": 2, "name": "Warm White", "intensity": 0},
    {"channel": 3, "name": "Cool White", "intensity": 0},
    {"channel": 4, "name": "UV", "intensity": 0}
  ],
  "temperature": 22.3,
  "humidity": 58.7,
  "timestamp": "2025-12-06T12:30:45.123456"
}
```

### B) cURL-Tests
```bash
# System-Status
curl http://localhost:5000/api/status

# Lampe 1 auf 50% setzen
curl -X POST http://localhost:5000/api/lamp/1 \
  -H "Content-Type: application/json" \
  -d '{"intensity": 50}'

# Temperatur abrufen
curl http://localhost:5000/api/temperature

# Logging-Status
curl http://localhost:5000/api/logs/stats
```

### C) Automatische Tests
```bash
# In separatem Terminal (Server muss laufen!)
python test_api.py
```

**Output:**
```
============================================================
GROWPI API TEST SUITE
============================================================
Testing: http://localhost:5000

[TEST] Health Check
  Status: healthy
  Version: 1.2.0
  ✓ PASSED

[TEST] System Status
  Temperature: 22.3°C
  Humidity: 58.7%
  Lamps: 4 channels
  ✓ PASSED

...

RESULTS: 10 passed, 0 failed
```

## 5. Pytest (Erweiterte Tests)

```bash
# Installiere pytest
pip install pytest pytest-cov

# Unit Tests
pytest pytest_example.py -v

# Mit Coverage-Report
pytest pytest_example.py --cov=../grow_pi --cov-report=html

# Öffne Coverage-Report
open htmlcov/index.html
```

## 6. Typische Workflows

### Workflow A: Feature-Entwicklung

```bash
# 1. Server starten
python run_local.py

# 2. In separatem Terminal: Code ändern (VSCode etc.)
# grow_pi/web/api.py editieren...

# 3. Tests ausführen
python test_api.py

# 4. Server neu starten (Ctrl+C, dann wieder python run_local.py)
```

**Tipp**: `--debug` aktiviert Auto-Reload:
```bash
python run_local.py --debug
```

### Workflow B: API-Integration testen

```bash
# 1. Server starten
python run_local.py

# 2. Postman / Insomnia verwenden
# - Import: http://localhost:5000/api/status
# - Teste alle Endpoints interaktiv

# 3. Oder mit Python-Script:
python -c "
import requests
resp = requests.get('http://localhost:5000/api/status')
print(resp.json())
"
```

### Workflow C: Frontend-Entwicklung

```bash
# 1. Test-Server starten (Backend)
python run_local.py

# 2. Frontend starten (separates Terminal)
cd ../../frontend
npm run dev

# 3. Frontend greift auf localhost:5000 zu
# API-Calls funktionieren ohne echte Hardware!
```

## 7. Debugging

### Problem: ModuleNotFoundError
**Fehler**: `ModuleNotFoundError: No module named 'grow_pi'`

**Lösung**:
```bash
# Stelle sicher, dass du im richtigen Verzeichnis bist
cd pi-controller/test_environment
python run_local.py
```

### Problem: Port bereits belegt
**Fehler**: `Address already in use`

**Lösung**:
```bash
# Nutze anderen Port
python run_local.py --port 8000

# Oder finde blockierenden Prozess
lsof -i :5000
kill <PID>
```

### Problem: Logs zu verbose
**Lösung**: In `run_local.py` ändern:
```python
logging.basicConfig(level=logging.INFO)  # statt DEBUG
```

## 8. Was wird simuliert?

| Hardware | Mock-Komponente | Verhalten |
|----------|----------------|-----------|
| GPIO PWM | MockPWMController | Speichert Werte in-memory |
| DHT22 Sensor | MockDHT22 | Synthetische Zeit-basierte Daten |
| SQLite DB | MockDatabase | Python-Listen statt Datei |
| Smart Plugs | MockSmartPlugController | Fake Energiedaten |

**Wichtig**: Alle Mock-Komponenten haben die **identische API** wie die echten Komponenten!

## 9. Migration zu echter Hardware

Wenn du bereit bist, auf dem Raspberry Pi zu deployen:

```bash
# 1. Auf Raspberry Pi
ssh admin@192.168.0.86

# 2. Installation
cd /opt/grow-pi
sudo ./install.sh

# 3. Konfiguration anpassen
sudo nano config/config.yaml
# Setze: simulation_mode: false

# 4. Service starten
sudo systemctl start grow-pi
```

**Unterschied**: Nur die Config-Datei ändert sich, der Code bleibt identisch!

## 10. Nützliche Links

- **API-Dokumentation**: Siehe `../grow_pi/web/api.py` Docstrings
- **Hardware-Spec**: `../../docs/SPEC_RASPBERRY_PI.md`
- **Frontend-Integration**: `../../docs/SPEC_FRONTEND.md`

## 11. Häufig verwendete Befehle

```bash
# Server starten (Standard)
python run_local.py

# Server mit Custom-Port
python run_local.py --port 8000

# Nur Tests ausführen (kein Server)
python run_local.py --test

# API-Tests
python test_api.py

# Unit Tests
pytest pytest_example.py -v

# Docker
docker-compose -f test_environment/docker-compose.yml up

# Docker neu bauen
docker-compose -f test_environment/docker-compose.yml up --build
```

## 12. Beispiel-Session (komplett)

```bash
# Terminal 1: Server starten
cd pi-controller/test_environment
python run_local.py

# Terminal 2: Tests
cd pi-controller/test_environment
python test_api.py

# Terminal 3: Manuelle Tests
curl http://localhost:5000/api/status | jq
curl -X POST http://localhost:5000/api/lamp/1 -H "Content-Type: application/json" -d '{"intensity": 75}'
curl http://localhost:5000/api/status | jq '.lamps[0]'
```

**Ergebnis**: Alle Tests grün, API funktioniert perfekt - ohne Hardware!

---

**Fragen?** Siehe `README.md` für Details oder schreib an d.westermann@ol-mg.de
