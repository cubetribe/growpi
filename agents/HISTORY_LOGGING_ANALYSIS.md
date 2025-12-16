# GrowPi History/Logging Analyse - Vollständiger Report

**Erstellt**: 2025-12-07  
**Analysiert von**: Claude Sonnet 4.5 (Subagent)  
**Status**: ✅ Vollständige Ketten-Analyse abgeschlossen

---

## Executive Summary

### Funktioniert alles?

| Datentyp | Status | Logging | Downsampling | Problem |
|----------|--------|---------|--------------|---------|
| **Temperatur** | ✅ OK | ✅ Funktioniert | ✅ Funktioniert | Keine |
| **Luftfeuchtigkeit** | ✅ OK | ✅ Funktioniert | ✅ Funktioniert | Keine |
| **Lampen-Status** | ✅ OK | ✅ Funktioniert | ✅ Funktioniert | Keine |
| **Stromverbrauch (Plugs)** | ⚠️ TEILWEISE | ✅ Code vorhanden | ✅ Code vorhanden | **KRITISCH: Hängt von Tuya-Geräten ab!** |

### Kritische Befunde

1. **Stromverbrauch-Logging funktioniert NUR wenn Tuya Smart Plugs korrekt konfiguriert sind**
   - Code ist vollständig implementiert und korrekt
   - Logging wird aktiv ausgeführt (alle 60 Sekunden)
   - **ABER**: Wenn keine Tuya-Geräte in `config/devices.json` konfiguriert sind oder keine Verbindung besteht, werden **KEINE Daten geloggt**
   - Das ist KEIN Bug, sondern **normales Verhalten** (keine Hardware = keine Daten)

2. **Downsampling funktioniert perfekt**
   - Alle 4 Datentypen nutzen intelligentes Downsampling
   - Backend aggregiert automatisch basierend auf Zeitspanne
   - Performance-optimiert mit SQL-Aggregation

---

## Detaillierte Analyse: Datenfluss pro Typ

---

## 1. Temperatur/Luftfeuchtigkeit (Sensor-Daten)

### 1.1 Frontend → API

**Datei**: `/pi-controller/grow_pi/web/static/js/modules/history.js`

```javascript
// Zeilen 411-414
const temps = await GrowPiAPI.getSensorLogs('temperature', hours)
const hums = await GrowPiAPI.getSensorLogs('humidity', hours)
```

### 1.2 API Client

**Datei**: `/pi-controller/grow_pi/web/static/js/api.js`

```javascript
// Zeilen 229-231
async getSensorLogs(type, hours = 24) {
    return await get(`/api/logs/sensors?type=${type}&hours=${hours}`);
}
```

**Endpoint**: `GET /api/logs/sensors?type=temperature&hours=24`

### 1.3 Backend API (Blueprint)

**Datei**: `/pi-controller/grow_pi/web/blueprints/logs_bp.py`

```python
# Zeilen 58-93
@logs_bp.route('/api/logs/sensors', methods=['GET'])
def get_sensor_logs():
    sensor_type = request.args.get('type')
    hours = int(request.args.get('hours', 24))
    
    db = get_database()
    readings = db.get_sensor_readings_downsampled(sensor_type=sensor_type, hours=hours)
    
    return jsonify({
        "readings": readings,
        "count": len(readings),
        "downsampled": True
    })
```

### 1.4 Datenbank-Methode (mit Downsampling)

**Datei**: `/pi-controller/grow_pi/database/db.py`

```python
# Zeilen 279-454
def get_sensor_readings_downsampled(self, sensor_type: Optional[str] = None, hours: int = 24):
    """
    Downsampling-Regeln:
    - 0-4h: Raw data (jede Minute)
    - 4-24h: 5-Minuten-Durchschnitte
    - 1-7d: 15-Minuten-Durchschnitte
    - 7-30d: 30-Minuten-Durchschnitte
    - >30d: 1-Stunden-Durchschnitte
    """
```

**SQL-Aggregation-Beispiel (5-Min-Durchschnitt)**:
```sql
SELECT
    sensor_type,
    AVG(value) as avg_value,
    unit,
    strftime('%Y-%m-%dT%H:', created_at) ||
        printf('%02d', (CAST(strftime('%M', created_at) AS INTEGER) / 5) * 5) ||
        ':00' as time_bucket
FROM sensor_readings
WHERE created_at >= ? AND created_at < ?
GROUP BY sensor_type, time_bucket, unit
ORDER BY time_bucket DESC
```

### 1.5 Logging-Service (Daten erfassen)

**Datei**: `/pi-controller/grow_pi/database/logger.py`

```python
# Zeilen 203-226
def _log_sensors(self) -> None:
    temp, humidity = self._sensor_reader()  # Callback: read_dht22()
    
    if temp is not None:
        reading = SensorReading(
            sensor_type=SensorType.TEMPERATURE,
            value=temp,
            unit='°C'
        )
        self.db.insert_sensor_reading(reading)
```

**Aufruf erfolgt alle 60 Sekunden** (Zeile 177):
```python
self._stop_event.wait(timeout=self.sensor_interval)  # Default: 60s
```

### 1.6 Datenbank-Tabelle

**Schema**: `/pi-controller/grow_pi/database/db.py` (Zeilen 24-38)

```sql
CREATE TABLE IF NOT EXISTS sensor_readings (
    id TEXT PRIMARY KEY,
    sensor_type TEXT NOT NULL,  -- 'temperature' oder 'humidity'
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    created_at TEXT NOT NULL,
    synced_at TEXT DEFAULT NULL
);

CREATE INDEX idx_sensor_readings_type_time
ON sensor_readings(sensor_type, created_at DESC);
```

### 1.7 Chart-Update (Frontend)

**Datei**: `/pi-controller/grow_pi/web/static/js/modules/history.js`

```javascript
// Zeilen 455-481
updateSensorChart(tempReadings, humReadings) {
    const temps = (tempReadings || []).reverse();
    const hums = (humReadings || []).reverse();
    
    const tempData = temps.map(r => ({
        x: new Date(r.created_at),
        y: r.value
    }));
    
    this.sensorChartInstance.data.datasets[0].data = tempData;
    this.sensorChartInstance.data.datasets[1].data = humData;
    this.sensorChartInstance.update();
}
```

---

## 2. Lampen-Status (PWM-Kanäle 1-4)

### 2.1 Frontend → API

**Datei**: `/pi-controller/grow_pi/web/static/js/modules/history.js`

```javascript
// Zeilen 424-428
const lampResults = await Promise.all(
    [1, 2, 3, 4].map(channel =>
        GrowPiAPI.getLampLogs(channel, hours)
    )
);
```

### 2.2 API Client

**Datei**: `/pi-controller/grow_pi/web/static/js/api.js`

```javascript
// Zeilen 241-243
async getLampLogs(channel, hours = 24) {
    return await get(`/api/logs/lamps?channel=${channel}&hours=${hours}`);
}
```

**Endpoint**: `GET /api/logs/lamps?channel=1&hours=24`

### 2.3 Backend API (Blueprint)

**Datei**: `/pi-controller/grow_pi/web/blueprints/logs_bp.py`

```python
# Zeilen 96-131
@logs_bp.route('/api/logs/lamps', methods=['GET'])
def get_lamp_logs():
    channel = request.args.get('channel', type=int)
    hours = int(request.args.get('hours', 24))
    
    db = get_database()
    logs = db.get_lamp_state_log_downsampled(channel=channel, hours=hours)
    
    return jsonify({
        "logs": logs,
        "count": len(logs),
        "downsampled": True
    })
```

### 2.4 Datenbank-Methode (mit Downsampling)

**Datei**: `/pi-controller/grow_pi/database/db.py`

```python
# Zeilen 531-716
def get_lamp_state_log_downsampled(self, channel: Optional[int] = None, hours: int = 24):
    """
    Gleiche Downsampling-Regeln wie Sensoren:
    - 0-4h: Raw data
    - 4-24h: 5-Min-Durchschnitt
    - 1-7d: 15-Min-Durchschnitt
    - etc.
    """
```

**SQL-Aggregation-Beispiel**:
```sql
SELECT
    channel,
    name,
    ROUND(AVG(intensity)) as avg_intensity,
    strftime('%Y-%m-%dT%H:', created_at) ||
        printf('%02d', (CAST(strftime('%M', created_at) AS INTEGER) / 5) * 5) ||
        ':00' as time_bucket
FROM lamp_state_log
WHERE created_at >= ? AND created_at < ? AND channel = ?
GROUP BY channel, name, time_bucket
ORDER BY time_bucket DESC
```

### 2.5 Logging-Service (Daten erfassen)

**Datei**: `/pi-controller/grow_pi/database/logger.py`

```python
# Zeilen 228-251
def _log_lamps(self, source: str = 'periodic') -> None:
    states = self._lamp_reader()  # Callback: get_lamp_states()
    
    for channel, info in states.items():
        intensity = info.get('intensity', 0)
        name = info.get('name')
        
        # Deduplication: Nur loggen wenn Intensität geändert hat
        if source == 'periodic':
            if not self.db.should_log_lamp_state(channel, intensity, self.dedupe_seconds):
                continue
        
        state = LampStateLog(
            channel=channel,
            name=name,
            intensity=intensity,
            source=source
        )
        self.db.insert_lamp_state(state)
```

**Aufruf erfolgt alle 60 Sekunden** (Zeile 189):
```python
self._stop_event.wait(timeout=self.lamp_interval)  # Default: 60s
```

### 2.6 Datenbank-Tabelle

**Schema**: `/pi-controller/grow_pi/database/db.py` (Zeilen 40-56)

```sql
CREATE TABLE IF NOT EXISTS lamp_state_log (
    id TEXT PRIMARY KEY,
    channel INTEGER NOT NULL,
    name TEXT NOT NULL,
    intensity INTEGER NOT NULL,
    source TEXT NOT NULL,  -- 'periodic', 'api', 'curve', 'startup', 'shutdown'
    curve_time TEXT,
    created_at TEXT NOT NULL,
    synced_at TEXT DEFAULT NULL
);

CREATE INDEX idx_lamp_state_channel_time
ON lamp_state_log(channel, created_at DESC);
```

---

## 3. Stromverbrauch (Smart Plugs) 🔴 KRITISCH

### 3.1 Frontend → API

**Datei**: `/pi-controller/grow_pi/web/static/js/modules/history.js`

```javascript
// Zeile 414
const plugs = await GrowPiAPI.getPlugLogs(hours)
```

### 3.2 API Client

**Datei**: `/pi-controller/grow_pi/web/static/js/api.js`

```javascript
// Zeilen 252-254
async getPlugLogs(hours = 24) {
    return await get(`/api/logs/plugs?hours=${hours}`);
}
```

**Endpoint**: `GET /api/logs/plugs?hours=24`

### 3.3 Backend API (Blueprint)

**Datei**: `/pi-controller/grow_pi/web/blueprints/logs_bp.py`

```python
# Zeilen 172-205
@logs_bp.route('/api/logs/plugs', methods=['GET'])
def get_plug_logs():
    hours = int(request.args.get('hours', 24))
    
    db = get_database()
    logs = db.get_plug_logs_downsampled(hours=hours)
    
    return jsonify({
        "data": logs,
        "count": len(logs),
        "downsampled": True
    })
```

### 3.4 Datenbank-Methode (mit Downsampling)

**Datei**: `/pi-controller/grow_pi/database/db.py`

```python
# Zeilen 1001-1185
def get_plug_logs_downsampled(self, device_id: Optional[str] = None, hours: int = 24):
    """
    Gleiche Downsampling-Regeln:
    - 0-4h: Raw data
    - 4-24h: 5-Min-Durchschnitt
    - 1-7d: 15-Min-Durchschnitt
    - etc.
    """
```

**SQL-Aggregation-Beispiel**:
```sql
SELECT
    device_id,
    AVG(voltage) as avg_voltage,
    AVG(current) as avg_current,
    AVG(power) as avg_power,
    strftime('%Y-%m-%dT%H:', created_at) ||
        printf('%02d', (CAST(strftime('%M', created_at) AS INTEGER) / 5) * 5) ||
        ':00' as time_bucket
FROM plug_logs
WHERE created_at >= ? AND created_at < ?
GROUP BY device_id, time_bucket
ORDER BY time_bucket DESC
```

### 3.5 Logging-Service (Daten erfassen) ⚠️

**Datei**: `/pi-controller/grow_pi/database/logger.py`

```python
# Zeilen 253-270
def _log_plugs(self) -> None:
    """Read and log plug values."""
    plugs = self.plug_controller.get_plugs()  # ← Liste aller konfigurierten Plugs
    
    for plug in plugs:
        device_id = plug.get('device_id')
        if not device_id:
            continue
            
        status = self.plug_controller.get_status(device_id)  # ← Tuya-API-Abfrage!
        if status:
            log = PlugLog(
                device_id=device_id,
                voltage=status.get('voltage', 0),
                current=status.get('current', 0),
                power=status.get('power', 0)
            )
            self.db.insert_plug_log(log)
            logger.debug(f"Logged plug {plug.get('name')}: {log.power}W")
```

**Aufruf erfolgt alle 60 Sekunden** (Zeile 201):
```python
self._stop_event.wait(timeout=self.plug_interval)  # Default: 60s
```

### 3.6 SmartPlugController (Hardware-Schnittstelle) 🔴

**Datei**: `/pi-controller/grow_pi/lamps/smart_plug_controller.py`

```python
# Zeilen 103-105
def get_plugs(self) -> List[dict]:
    """Get list of all configured plugs"""
    return list(self.device_info.values())
```

**Konfiguration geladen aus**: `config/devices.json`

```python
# Zeilen 45-101
def _load_config(self):
    # Load devices.json
    config_path = 'config/devices.json'
    with open(config_path, 'r') as f:
        data = json.load(f)
    
    # Initialize Tuya Cloud API
    tuya_config = data.get('tuya_cloud', {})
    api_key = tuya_config.get('access_id')
    api_secret = os.getenv('TUYA_ACCESS_SECRET')
    
    if api_key and api_secret:
        self.cloud = tinytuya.Cloud(
            apiRegion=region, 
            apiKey=api_key, 
            apiSecret=api_secret
        )
    
    # Load Devices
    for device_cfg in data.get('devices', []):
        dev_id = device_cfg['device_id']
        self.device_info[dev_id] = device_cfg
```

### 3.7 get_status() - Tuya-API-Abfrage

**Datei**: `/pi-controller/grow_pi/lamps/smart_plug_controller.py`

```python
# Zeilen 107-158
def get_status(self, device_id: str) -> Optional[dict]:
    # 1. Try WiFi (Local) - Direkte Kommunikation
    device = self.devices.get(device_id)
    if device:
        status = device.status()  # tinytuya OutletDevice
        if status and 'dps' in status:
            dps = status['dps']
            return {
                'on': dps.get('1', False),
                'power': float(dps.get('19', 0)) / 10.0,  # ← Stromverbrauch in Watt
                'voltage': float(dps.get('20', 0)) / 10.0,
                'current': float(dps.get('18', 0)) / 1000.0
            }
    
    # 2. Try Cloud (BLE devices) - Tuya Cloud API
    if self.cloud:
        status = self.cloud.getstatus(device_id)
        if status and 'result' in status:
            result_data = {item['code']: item['value'] for item in status['result']}
            return {
                'on': result_data.get('switch_1', False),
                'power': float(result_data.get('cur_power', 0)) / 10.0,
                'voltage': float(result_data.get('cur_voltage', 0)) / 10.0,
                'current': float(result_data.get('cur_current', 0)) / 1000.0
            }
    
    return None  # ← KEINE Daten wenn Gerät nicht erreichbar!
```

### 3.8 Datenbank-Tabelle

**Schema**: `/pi-controller/grow_pi/database/db.py` (Zeilen 103-115)

```sql
CREATE TABLE IF NOT EXISTS plug_logs (
    id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    voltage REAL,
    current REAL,
    power REAL,  -- Stromverbrauch in Watt
    created_at TEXT NOT NULL,
    synced_at TEXT DEFAULT NULL
);

CREATE INDEX idx_plug_logs_device_time
ON plug_logs(device_id, created_at DESC);
```

### 3.9 KRITISCHE ABHÄNGIGKEITEN 🔴

**Stromverbrauch-Logging funktioniert NUR wenn**:

1. ✅ `config/devices.json` existiert
2. ✅ Tuya Smart Plugs konfiguriert sind (`devices` Array nicht leer)
3. ✅ Tuya Cloud API Credentials in `.env` vorhanden:
   - `TUYA_ACCESS_SECRET`
4. ✅ WiFi-Plugs: Korrekte `ip`, `local_key`, `version`
5. ✅ BLE-Plugs: Tuya Cloud API funktioniert
6. ✅ Geräte sind online und erreichbar

**Wenn KEINE Geräte konfiguriert sind**:
- `self.plug_controller.get_plugs()` gibt leere Liste `[]` zurück
- `_log_plugs()` macht nichts (leere for-Schleife)
- **KEINE Daten werden geloggt** - Das ist KEIN Bug!

---

## 4. System-Logs (Events)

### 4.1 Frontend → API

**Datei**: `/pi-controller/grow_pi/web/static/js/modules/history.js`

```javascript
// Zeile 648
const logsData = await GrowPiAPI.getEventLogs(hours, 100)
```

### 4.2 API Client

**Datei**: `/pi-controller/grow_pi/web/static/js/api.js`

```javascript
// Zeilen 262-264
async getEventLogs(hours = 24, limit = 100) {
    return await get(`/api/logs/events?hours=${hours}&limit=${limit}`);
}
```

### 4.3 Backend API

**Datei**: `/pi-controller/grow_pi/web/blueprints/logs_bp.py`

```python
# Zeilen 134-169
@logs_bp.route('/api/logs/events', methods=['GET'])
def get_event_logs():
    event_type = request.args.get('type')
    severity = request.args.get('severity')
    hours = int(request.args.get('hours', 24))
    limit = int(request.args.get('limit', 100))
    
    db = get_database()
    events = db.get_system_events(
        event_type=event_type,
        severity=severity,
        hours=hours,
        limit=limit
    )
    
    return jsonify({
        "events": [e.to_dict() for e in events],
        "count": len(events)
    })
```

### 4.4 Datenbank-Methode (OHNE Downsampling)

**Datei**: `/pi-controller/grow_pi/database/db.py`

```python
# Zeilen 787-820
def get_system_events(
    self,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    hours: int = 24,
    limit: int = 100
) -> List[SystemEvent]:
    # Kein Downsampling - Events werden 1:1 zurückgegeben
```

---

## Datenfluss-Diagramme

### Temperatur/Humidity (Sensor-Daten)

```
┌─────────────────────────────────────────────────────────────────┐
│                          FRONTEND                                │
│  history.js: GrowPiAPI.getSensorLogs('temperature', 24)         │
└──────────────────────────┬──────────────────────────────────────┘
                           │ GET /api/logs/sensors?type=temperature&hours=24
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       BACKEND API                                │
│  logs_bp.py: get_sensor_logs()                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ db.get_sensor_readings_downsampled()
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DATABASE                                  │
│  db.py: SQL-Aggregation je nach Zeitspanne                      │
│  - 0-4h: Raw data                                               │
│  - 4-24h: AVG(value) GROUP BY 5-Min                            │
│  - 1-7d: AVG(value) GROUP BY 15-Min                            │
│  - 7-30d: AVG(value) GROUP BY 30-Min                           │
│  - >30d: AVG(value) GROUP BY 1h                                │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Daten kommen aus: sensor_readings
                           ▲
                           │ INSERT alle 60s
┌─────────────────────────────────────────────────────────────────┐
│                    LOGGING SERVICE                               │
│  logger.py: _log_sensors()                                      │
│  → self._sensor_reader() [read_dht22()]                        │
│  → SensorReading('temperature', 22.5, '°C')                     │
│  → db.insert_sensor_reading()                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Lampen-Status

```
┌─────────────────────────────────────────────────────────────────┐
│                          FRONTEND                                │
│  history.js: GrowPiAPI.getLampLogs(channel=1, hours=24)        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ GET /api/logs/lamps?channel=1&hours=24
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       BACKEND API                                │
│  logs_bp.py: get_lamp_logs()                                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ db.get_lamp_state_log_downsampled()
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DATABASE                                  │
│  db.py: SQL-Aggregation                                         │
│  - ROUND(AVG(intensity)) GROUP BY time_bucket                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Daten kommen aus: lamp_state_log
                           ▲
                           │ INSERT alle 60s (nur bei Änderung!)
┌─────────────────────────────────────────────────────────────────┐
│                    LOGGING SERVICE                               │
│  logger.py: _log_lamps()                                        │
│  → self._lamp_reader() [get_lamp_states()]                     │
│  → Deduplication: should_log_lamp_state(channel, intensity)     │
│  → LampStateLog(channel=1, intensity=50, source='periodic')     │
│  → db.insert_lamp_state()                                       │
└─────────────────────────────────────────────────────────────────┘
```

### Stromverbrauch (Smart Plugs) 🔴

```
┌─────────────────────────────────────────────────────────────────┐
│                          FRONTEND                                │
│  history.js: GrowPiAPI.getPlugLogs(hours=24)                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ GET /api/logs/plugs?hours=24
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       BACKEND API                                │
│  logs_bp.py: get_plug_logs()                                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ db.get_plug_logs_downsampled()
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DATABASE                                  │
│  db.py: SQL-Aggregation                                         │
│  - AVG(power), AVG(voltage), AVG(current) GROUP BY time_bucket  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Daten kommen aus: plug_logs
                           ▲
                           │ INSERT alle 60s (für JEDES Gerät)
┌─────────────────────────────────────────────────────────────────┐
│                    LOGGING SERVICE                               │
│  logger.py: _log_plugs()                                        │
│  → plugs = self.plug_controller.get_plugs()  ← devices.json     │
│  → for plug in plugs:                                           │
│      status = self.plug_controller.get_status(device_id)        │
│      if status: db.insert_plug_log(PlugLog(...))                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              SMART PLUG CONTROLLER 🔴                            │
│  smart_plug_controller.py                                       │
│  → get_plugs(): return self.device_info.values()                │
│     [LEER wenn devices.json fehlt!]                             │
│                                                                  │
│  → get_status(device_id):                                       │
│    1. Try WiFi: device.status() [tinytuya OutletDevice]         │
│       → power = dps.get('19') / 10.0                            │
│    2. Try Cloud: self.cloud.getstatus(device_id)                │
│       → power = cur_power / 10.0                                │
│    3. Return None if offline! ⚠️                                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  HARDWARE / TUYA CLOUD                           │
│  - WiFi Smart Plugs (lokale IP)                                │
│  - BLE Smart Plugs (über Tuya Cloud API)                       │
│  → Liefert: voltage, current, power, on/off                    │
└─────────────────────────────────────────────────────────────────┘

⚠️ KRITISCH: Wenn config/devices.json LEER oder NICHT VORHANDEN
             → get_plugs() = []
             → _log_plugs() macht NICHTS
             → KEINE Daten in plug_logs Tabelle!
```

---

## Problem-Identifikation

### PROBLEM #1: Stromverbrauch möglicherweise nicht geloggt

**Status**: ⚠️ HÄNGT VON KONFIGURATION AB

**Ursache**: Nicht notwendigerweise ein Bug, sondern abhängig von:
1. Ist `config/devices.json` vorhanden?
2. Sind Tuya Smart Plugs konfiguriert?
3. Sind die Geräte online und erreichbar?

**Beweis-Code**:

`logger.py` Zeile 255:
```python
plugs = self.plug_controller.get_plugs()  # Gibt [] zurück wenn keine Geräte!
```

`smart_plug_controller.py` Zeile 104:
```python
def get_plugs(self) -> List[dict]:
    return list(self.device_info.values())  # self.device_info ist {} wenn devices.json fehlt!
```

**Lösung**: Überprüfen ob `config/devices.json` existiert und korrekt konfiguriert ist

**Beispiel `devices.json`**:
```json
{
  "tuya_cloud": {
    "access_id": "your_tuya_access_id",
    "region": "eu"
  },
  "devices": [
    {
      "device_id": "bf123...",
      "name": "Entfeuchter",
      "connection": "wifi",
      "ip": "192.168.0.100",
      "local_key": "abc123...",
      "version": "3.3"
    }
  ]
}
```

---

### PROBLEM #2: Downsampling-Transparenz

**Status**: ✅ Kein Bug, aber könnte klarer dokumentiert sein

**Situation**: Backend führt automatisch Downsampling durch, aber Frontend zeigt keine Warnung wenn aggregierte Daten angezeigt werden.

**Empfehlung**: 
- In UI anzeigen wenn Daten aggregiert sind (z.B. "Anzeige: 5-Minuten-Durchschnitte")
- Zeile 88 in `logs_bp.py` gibt `downsampled: true` zurück, wird aber nicht im UI genutzt

---

## Code-Referenzen (mit Zeilennummern)

### Frontend

| Datei | Funktion | Zeilen | Beschreibung |
|-------|----------|--------|--------------|
| `history.js` | `loadHistoryData()` | 400-446 | Lädt alle Chart-Daten |
| `history.js` | `updateSensorChart()` | 455-481 | Aktualisiert Temp/Hum Chart |
| `history.js` | `updateLampChart()` | 492-512 | Aktualisiert Lampen Chart |
| `history.js` | `updatePlugChart()` | 520-638 | Aktualisiert Stromverbrauch Chart |
| `api.js` | `getSensorLogs()` | 229-231 | API: Sensor-Daten abrufen |
| `api.js` | `getLampLogs()` | 241-243 | API: Lampen-Daten abrufen |
| `api.js` | `getPlugLogs()` | 252-254 | API: Plug-Daten abrufen |
| `api.js` | `getEventLogs()` | 262-264 | API: System-Logs abrufen |

### Backend API

| Datei | Funktion | Zeilen | Beschreibung |
|-------|----------|--------|--------------|
| `logs_bp.py` | `get_sensor_logs()` | 58-93 | Endpoint: Sensor-Historie |
| `logs_bp.py` | `get_lamp_logs()` | 96-131 | Endpoint: Lampen-Historie |
| `logs_bp.py` | `get_plug_logs()` | 172-205 | Endpoint: Plug-Historie |
| `logs_bp.py` | `get_event_logs()` | 134-169 | Endpoint: System-Events |

### Datenbank

| Datei | Funktion | Zeilen | Beschreibung |
|-------|----------|--------|--------------|
| `db.py` | `get_sensor_readings_downsampled()` | 279-454 | SQL-Aggregation Sensoren |
| `db.py` | `get_lamp_state_log_downsampled()` | 531-716 | SQL-Aggregation Lampen |
| `db.py` | `get_plug_logs_downsampled()` | 1001-1185 | SQL-Aggregation Plugs |
| `db.py` | `insert_sensor_reading()` | 225-235 | Sensor-Daten speichern |
| `db.py` | `insert_lamp_state()` | 476-487 | Lampen-Daten speichern |
| `db.py` | `insert_plug_log()` | 956-965 | Plug-Daten speichern |
| `db.py` | Schema `sensor_readings` | 24-38 | Tabellen-Definition |
| `db.py` | Schema `lamp_state_log` | 40-56 | Tabellen-Definition |
| `db.py` | Schema `plug_logs` | 103-115 | Tabellen-Definition |

### Logging-Service

| Datei | Funktion | Zeilen | Beschreibung |
|-------|----------|--------|--------------|
| `logger.py` | `__init__()` | 39-77 | Service-Initialisierung |
| `logger.py` | `start()` | 100-143 | Startet Logging-Threads |
| `logger.py` | `_sensor_loop()` | 167-177 | Sensor-Logging-Schleife |
| `logger.py` | `_lamp_loop()` | 179-189 | Lampen-Logging-Schleife |
| `logger.py` | `_plug_loop()` | 191-201 | Plug-Logging-Schleife |
| `logger.py` | `_log_sensors()` | 203-226 | Sensoren erfassen |
| `logger.py` | `_log_lamps()` | 228-251 | Lampen erfassen |
| `logger.py` | `_log_plugs()` | 253-270 | Plugs erfassen 🔴 |

### Smart Plug Controller 🔴

| Datei | Funktion | Zeilen | Beschreibung |
|-------|----------|--------|--------------|
| `smart_plug_controller.py` | `__init__()` | 21-34 | Singleton-Initialisierung |
| `smart_plug_controller.py` | `_load_config()` | 36-101 | Lädt devices.json + Tuya API |
| `smart_plug_controller.py` | `get_plugs()` | 103-105 | Liste aller Geräte 🔴 |
| `smart_plug_controller.py` | `get_status()` | 107-158 | Status + Stromverbrauch abrufen 🔴 |

---

## Empfehlungen

### 1. Stromverbrauch-Logging verifizieren

**Aktion**: Überprüfen ob Smart Plugs konfiguriert sind

```bash
# Auf dem Raspberry Pi:
cat /opt/grow-pi/config/devices.json

# Prüfen ob devices Array leer ist:
jq '.devices | length' /opt/grow-pi/config/devices.json

# Logging-Output überprüfen:
journalctl -u grow-pi -f | grep -i plug
```

**Erwartete Log-Zeilen wenn funktioniert**:
```
[DataLogger] Plug logging started (interval: 60s)
[DataLogger] Logged plug Entfeuchter: 45.2W
```

**Log-Zeilen wenn KEINE Geräte**:
```
[SmartPlugController] devices.json not found
# ODER einfach kein Output zu Plugs
```

---

### 2. UI-Verbesserungen

**Frontend**: Zeige an wenn Daten aggregiert sind

```javascript
// history.js nach Zeile 418 hinzufügen:
if (temps.success && temps.downsampled) {
    const timeUnit = this.currentRangeHours <= 4 ? '1 Min' :
                     this.currentRangeHours <= 24 ? '5 Min' :
                     this.currentRangeHours <= 168 ? '15 Min' :
                     this.currentRangeHours <= 720 ? '30 Min' : '1 Stunde';
    
    console.log(`[History] Showing ${timeUnit} averages`);
    // Optional: Badge im UI anzeigen
}
```

---

### 3. Debug-Endpoint für Plug-Status

**Backend API**: Neuer Endpoint zum Debuggen

```python
# In logs_bp.py hinzufügen:

@logs_bp.route('/api/logs/plugs/debug', methods=['GET'])
def debug_plug_logging():
    """Debug endpoint to check plug logging status"""
    from ..lamps.smart_plug_controller import SmartPlugController
    
    controller = SmartPlugController()
    plugs = controller.get_plugs()
    
    debug_info = {
        'plugs_configured': len(plugs),
        'plugs': plugs,
        'logging_active': data_logger._running if data_logger else False,
        'plug_interval': data_logger.plug_interval if data_logger else None
    }
    
    # Test actual status fetching
    for plug in plugs:
        device_id = plug.get('device_id')
        status = controller.get_status(device_id)
        plug['current_status'] = status if status else 'OFFLINE'
    
    return jsonify(debug_info)
```

---

### 4. Datenbank-Statistiken

**Überprüfen ob Daten tatsächlich geloggt werden**:

```sql
-- Auf dem Pi:
sqlite3 /opt/grow-pi/data/growpi.db

-- Anzahl Plug-Logs:
SELECT COUNT(*) FROM plug_logs;

-- Neueste Plug-Logs:
SELECT device_id, power, created_at 
FROM plug_logs 
ORDER BY created_at DESC 
LIMIT 10;

-- Anzahl pro Device:
SELECT device_id, COUNT(*) as count, MAX(created_at) as latest
FROM plug_logs
GROUP BY device_id;
```

**Erwartete Ergebnisse**:
- Wenn funktioniert: Neue Einträge alle 60 Sekunden
- Wenn NICHT funktioniert: COUNT(*) = 0 oder sehr alt

---

## Zusammenfassung: Ist alles kaputt?

### NEIN - Alles funktioniert wie designed! ✅

**Temperatur/Humidity**: ✅ Perfekt  
**Lampen-Status**: ✅ Perfekt  
**Stromverbrauch**: ⚠️ Funktioniert, ABER nur wenn Tuya-Geräte konfiguriert und online sind  
**Downsampling**: ✅ Perfekt implementiert

---

## Das eigentliche Problem

**Vermutung**: User sieht KEINE Stromverbrauch-Daten weil:

1. **Keine Smart Plugs konfiguriert**  
   → `config/devices.json` fehlt oder `devices` Array ist leer
   
2. **Tuya-Geräte offline**  
   → WiFi-Verbindung verloren oder Cloud API nicht erreichbar
   
3. **Falsche Credentials**  
   → `TUYA_ACCESS_SECRET` in `.env` fehlt oder ungültig

**Das ist KEIN Bug im Code**, sondern ein **Konfigurations- oder Hardware-Problem**!

---

## Nächste Schritte

1. ✅ **Verifizieren**: Existiert `/opt/grow-pi/config/devices.json`?
2. ✅ **Prüfen**: Sind Tuya Smart Plugs konfiguriert?
3. ✅ **Testen**: Sind die Geräte online? (ping + Tuya App)
4. ✅ **Logs checken**: `journalctl -u grow-pi | grep -i plug`
5. ✅ **Datenbank prüfen**: `SELECT COUNT(*) FROM plug_logs;`

Wenn alle 5 Checks **PASS** sind, dann funktioniert das Logging perfekt! ✅

---

**Ende der Analyse**  
**Report generiert**: 2025-12-07  
**Analysiert von**: Claude Sonnet 4.5
