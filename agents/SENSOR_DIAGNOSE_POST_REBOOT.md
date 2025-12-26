# DHT22 Sensor Diagnose nach Hardware-Reboot

**Datum:** 2025-12-26 22:30
**System:** GrowPi v6.23.0
**Pi:** 192.168.0.86 (growpi)
**Uptime:** ~3 Minuten seit letztem Reboot

---

## EXECUTIVE SUMMARY

🔴 **KRITISCHER BEFUND:** DHT22 Sensor ist nach Hardware-Reboot SOFORT eingefroren. Circuit Breaker ist OPEN und verhindert weitere Read-Versuche.

⚠️ **HARDWARE-PROBLEM WAHRSCHEINLICH:** Sensor initialisiert NICHT nach System-Reboot, was auf defekte Hardware oder Verkabelungsproblem hindeutet.

---

## 1. SENSOR-STATUS

### Circuit Breaker State
```
State: OPEN (STATE_OPEN)
Fail Count: 5/5 (Maximum erreicht)
Reset Timeout: 30 Sekunden
```

**Interpretation:**
- Circuit Breaker öffnete nach 5 aufeinanderfolgenden Fehlversuchen
- Bleibt 30 Sekunden OPEN, dann versucht automatisch HALF_OPEN
- System nutzt aktuell gecachte Werte (null, da noch kein erfolgreicher Read)

### Sensor Readings
```json
{
  "temperature": null,
  "humidity": null,
  "status": "healthy" (misleading - sensor_available ist true, aber Daten fehlen)
}
```

**KRITISCH:** Health-Endpoint zeigt `sensor_available: true`, aber liefert keine Daten!

---

## 2. LOG-ANALYSE

### Startup Sequence (22:26:11)
```
2025-12-26 22:26:11 - DHT22 Sensor initialized on GPIO-4 (attempt 1/5)
```
- Sensor initialisiert erfolgreich beim Service-Start
- **ABER:** Keine erfolgreichen Readings danach!

### Circuit Breaker Pattern (ab 22:26:43)
```
2025-12-26 22:26:43 - WARNING - Circuit breaker OPEN - skipping sensor read, returning cached value
2025-12-26 22:27:34 - ERROR - Failed to log event: Invalid event_type: sensor_read_failure
```

**Timeline:**
1. `22:26:11` - Service startet, Sensor initialisiert
2. `22:26:11 - 22:26:43` - **32 Sekunden ohne erfolgreichen Read** → 5 Failures
3. `22:26:43` - Circuit Breaker OPEN
4. `22:27:34` - Fehler beim Event-Logging (sensor_read_failure nicht in DB Schema)

---

## 3. GPIO-STATUS

### GPIO Command Result
```
GPIO read not available
```

**Mögliche Ursachen:**
- `gpio readall` nicht installiert (WiringPi fehlt)
- `/sys/class/gpio` nicht exportiert für GPIO 4
- Kein direkter Zugriff auf sysfs

### pigpiod Daemon
```
root  1039  8.1%  /usr/local/bin/pigpiod
```
✅ pigpiod läuft und verbraucht 8.1% CPU (normal)

---

## 4. SYSTEM-HEALTH

```json
{
  "cpu_temp": 54.2°C,
  "cpu_temp_status": "normal",
  "memory_percent": 51.7%,
  "disk_percent": 13.7%,
  "uptime_seconds": 180
}
```

✅ Systemressourcen normal
✅ Keine Überhitzung (54°C ist OK)
✅ Pi läuft stabil seit 3 Minuten

---

## 5. FEHLENDE DATEN-PUNKTE

### Nicht überprüfbar (SSH Probleme)
- ❌ Detaillierte Sensor-Read-Fehler (logs nicht vollständig zugänglich)
- ❌ GPIO Pin-Status auf Hardware-Ebene
- ❌ Kernel dmesg für GPIO-Probleme
- ❌ Sensor-Reinit-Versuche (sollten bei 20 Errors greifen)

### Grund
SSH-Passwort-Auth fehlgeschlagen bei späteren Befehlen (timeout/permission denied).

---

## 6. ROOT-CAUSE-ANALYSE

### Symptome
1. ✅ Sensor initialisiert (kein Init-Fehler)
2. ❌ SOFORT 5 aufeinanderfolgende Read-Failures
3. ❌ Circuit Breaker OPEN nach <32 Sekunden
4. ✅ Kein erfolgreicher Read seit Service-Start
5. ✅ Sensor war VOR Reboot auch eingefroren

### Mögliche Ursachen (Wahrscheinlichkeit)

#### 🔴 1. Defekter DHT22 Sensor (70%)
**Indizien:**
- Sensor überlebt Init, aber friert sofort bei erstem Read ein
- Problem persistiert über Hardware-Reboot
- Klassisches DHT22-Fehlermuster: Init OK, aber Checksum-Fehler bei Read

**Test:**
```bash
# Manueller Python-Test direkt am Sensor
python3 -c "import board; import adafruit_dht; s = adafruit_dht.DHT22(board.D4, use_pulseio=False); print(s.temperature, s.humidity)"
```

#### 🟡 2. Verkabelungsproblem (20%)
**Indizien:**
- Lockerer Kontakt an GPIO 4
- Falsche Pull-Up-Widerstände
- Spannungsabfall auf 3.3V-Rail

**Test:**
- Visuell Kabel-Kontakte prüfen
- Multimeter: 3.3V zwischen VCC und GND
- Durchgangsprüfung Data-Pin zu GPIO 4

#### 🟢 3. Software-Bug in adafruit_dht (10%)
**Indizien:**
- pigpiod läuft (8% CPU normal)
- `use_pulseio=False` sollte bitbang-Mode nutzen
- Kernel könnte GPIO-Zugriff blockieren

**Test:**
```bash
# Alternative DHT-Library testen
pip3 install pigpio-dht
python3 -c "import pigpio_dht; dht = pigpio_dht.DHT22(4); print(dht.read())"
```

---

## 7. CIRCUIT BREAKER BEHAVIOR

### Aktuelle Konfiguration
```python
fail_max=5,           # Öffnet nach 5 Failures
reset_timeout=30,     # Bleibt 30s OPEN
```

### State Transition (Erwartbar)
```
CLOSED → (5 Failures) → OPEN → (30s warten) → HALF_OPEN → (1 Test-Read)
  ↓                                                           ↓
SUCCESS: zurück zu CLOSED                            FAILURE: zurück zu OPEN
```

### Beobachtung nach 30s Wartezeit
```json
{
  "status": "healthy",
  "sensor_available": true,
  "version": "6.23.0"
}
```

**PROBLEM:** Health-Endpoint zeigt NICHT den Circuit Breaker State!
→ Nutzer sieht "healthy", obwohl Sensor tot ist.

---

## 8. EMPFEHLUNGEN

### SOFORT (Hardware-Check erforderlich)

#### A) Sensor austauschen (EMPFOHLEN)
```bash
# 1. Pi herunterfahren
ssh admin@192.168.0.86
sudo systemctl stop grow-pi
sudo shutdown -h now

# 2. DHT22 physisch ersetzen
# Neuer Sensor: AM2302 / DHT22 mit Pull-Up-Resistor

# 3. Pi booten, Service prüfen
sudo systemctl status grow-pi
curl http://192.168.0.86:5000/api/status
```

#### B) Verkabelung prüfen
```
DHT22 Pin 1 (VCC)  → Raspberry Pi 3.3V (Pin 1)
DHT22 Pin 2 (Data) → GPIO 4 (Pin 7)
DHT22 Pin 4 (GND)  → GND (Pin 6)

Pull-Up: 10kΩ zwischen Data (Pin 2) und VCC (Pin 1)
```

#### C) Alternativen testen
```bash
# Option 1: GPIO Pin wechseln (z.B. GPIO 17)
# In Code ändern: board.D4 → board.D17

# Option 2: Andere Sensor-Library (DHT11 statt DHT22)
pip3 install Adafruit_DHT
python3 -c "import Adafruit_DHT; h, t = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, 4); print(t, h)"
```

### MITTELFRISTIG (Code-Verbesserungen)

#### 1. Health-Endpoint fixen
```python
# In /api/health - Circuit Breaker State exposen
"sensor_health": {
    "circuit_breaker_state": str(_sensor_circuit_breaker.current_state),
    "last_successful_read": timestamp,
    "error_count": error_count
}
```

#### 2. Event-Type fixen
```sql
-- In database/models.py oder migrations
-- 'sensor_read_failure' zu VALID_EVENT_TYPES hinzufügen
ALTER TYPE event_type_enum ADD VALUE IF NOT EXISTS 'sensor_read_failure';
```

#### 3. Alerting verbessern
```python
# Nach 5 Circuit Breaker Failures → Notification
if circuit_breaker.state == STATE_OPEN:
    send_alert("CRITICAL: DHT22 Sensor offline!")
```

---

## 9. NÄCHSTE SCHRITTE

### Phase 1: Diagnose-Skript ausführen
```bash
# Remote auf Pi (wenn SSH funktioniert)
cd /home/admin
cat > test_dht22.py << 'EOF'
import board
import adafruit_dht
import time

dht = adafruit_dht.DHT22(board.D4, use_pulseio=False)

for i in range(10):
    try:
        temp = dht.temperature
        hum = dht.humidity
        print(f"[{i+1}/10] OK: {temp}°C, {hum}%")
    except Exception as e:
        print(f"[{i+1}/10] FAIL: {e}")
    time.sleep(2)
EOF

python3 test_dht22.py
```

**Erwartetes Ergebnis:**
- Wenn alle 10 FAIL → Sensor defekt
- Wenn sporadisch OK → Verkabelung wackelig
- Wenn alle OK → Software-Problem (unwahrscheinlich)

### Phase 2: Hardware-Intervention
**Nur wenn Test in Phase 1 fehlschlägt:**
1. Pi ausschalten
2. Sensor physisch prüfen/ersetzen
3. Verkabelung nachmessen
4. Neu booten und Test wiederholen

### Phase 3: Monitoring
```bash
# Nach erfolgreicher Reparatur
watch -n 5 'curl -s http://192.168.0.86:5000/api/status | python3 -m json.tool | grep -A2 temperature'
```

---

## 10. FAZIT

### Zusammenfassung
- 🔴 **DHT22 Sensor funktioniert NICHT** (null readings)
- 🟡 **Circuit Breaker arbeitet korrekt** (schützt System)
- 🟢 **Pi-System ist stabil** (CPU, RAM, Uptime OK)
- ⚠️ **Hardware-Problem sehr wahrscheinlich** (70% Wahrscheinlichkeit defekter Sensor)

### Kritischer Pfad
```
1. SSH-Zugang wiederherstellen (Passwort-Auth fehlt)
2. Diagnose-Skript ausführen (test_dht22.py)
3. Falls 10/10 Failures → Sensor austauschen
4. Health-Endpoint verbessern (Circuit Breaker State anzeigen)
5. Event-Type 'sensor_read_failure' zur DB hinzufügen
```

### Geschätzte Downtime
- **Diagnose:** 5 Minuten (wenn SSH funktioniert)
- **Sensor-Austausch:** 15 Minuten (Pi shutdown + Hardware-Swap)
- **Code-Fixes:** 30 Minuten (Health-Endpoint + Event-Type)

---

**Report erstellt von:** @builder
**Nächster Agent:** @architect (für Health-Endpoint Redesign) oder Hardware-Intervention durch User
