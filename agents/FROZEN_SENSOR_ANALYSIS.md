# KRITISCHE SENSOR-DIAGNOSE: ROOT CAUSE ANALYSE

**Datum:** 2025-12-22
**Agent:** Explorer (Sonnet)
**Status:** KRITISCHER BUG GEFUNDEN

---

## PROBLEM IDENTIFIZIERT

Die DHT22 Sensor-Werte sind seit gestern 14:00 Uhr **EINGEFROREN** auf 22.9°C und 63.8%. Die Werte ändern sich nicht mehr, obwohl der Sensor online sein sollte.

---

## ROOT CAUSE: DOPPELTE DHT22 CACHE-IMPLEMENTIERUNGEN

Es existieren **ZWEI SEPARATE UND UNABHÄNGIGE DHT22-CACHE-SYSTEME**, die NICHT miteinander kommunizieren:

### 1. TEMPERATURE_BP.PY - Alte Cache-Implementierung
- **Datei**: `pi-controller/grow_pi/web/blueprints/temperature_bp.py`
- **Zeilen**: 57-98
- **Cache Variable**: `_dht_cache` (modul-lokal)
- **Cache TTL**: 30 Sekunden
- **Status**: NOCH REGISTRIERT und WIRD VOM DEHUMIDIFIER VERWENDET!

### 2. SENSOR_CACHE.PY - Neue Shared Cache-Implementierung
- **Datei**: `pi-controller/grow_pi/utils/sensor_cache.py`
- **Zeilen**: 26-31
- **Cache Variable**: `_sensor_cache` (modul-lokal)
- **Cache TTL**: 30 Sekunden
- **Status**: NEU hinzugefügt, SOLL die zentrale Quelle sein

---

## DAS KERNPROBLEM: INCOMPLETE MIGRATION

In der v6.22.2-Änderung wurde versucht, von `temperature_bp.py`-Cache auf `sensor_cache.py` zu migrieren. **ABER DIE MIGRATION IST UNVOLLSTÄNDIG**:

### Was WURDE geändert:
- ✅ `dehumidifier_bp.py` Zeile 81-87: Importiert jetzt `sensor_cache`
- ✅ `status_bp.py`: Importiert jetzt `sensor_cache`

### Was NICHT geändert wurde - DAS IST DER BUG:
- ❌ `app.py` Zeile 444-452: Dehumidifier nutzt immer noch `temperature_bp.read_dht22()`!
- ❌ `app.py` Zeile 509-518: DataLogger nutzt auch die alte Funktion!
- ❌ `temperature_bp.py`: HAT NOCH SEINE EIGENE `read_dht22()` FUNKTION

```python
# app.py Zeile 444-452 - PROBLEM!
def humidity_reader():
    from .blueprints.temperature_bp import read_dht22 as bp_read_dht22  # <-- FALSCH!
    _, humidity = bp_read_dht22()
    return humidity
```

---

## WARUM SIND DIE WERTE EINGEFROREN?

### Ablauf:

1. **14:00 Uhr**: DHT22 Sensor funktioniert, Cache wird aktualisiert
2. **14:30 Uhr**: DHT22 Sensor **FÄLLT AUS** (GPIO-Fehler, Timeout, etc.)
3. **14:31 Uhr**:
   - `temperature_bp.read_dht22()` versucht 3x zu lesen, schlägt fehl
   - **ALS FALLBACK**: Gibt den letzten Cached-Wert zurück (22.9°C, 63.8%)
   - **Timestamp wird NICHT aktualisiert!**
4. **14:32 Uhr+**: Jede neue Anfrage:
   - Prüft: `now - timestamp < 30` → Der alte Timestamp ist < 30 Sekunden!
   - Gibt SOFORT den alten Wert zurück, OHNE SENSOR-VERSUCH
   - **CACHE IST JETZT EINGEFROREN!**

### Kritischer Code (temperature_bp.py Zeile 71-76):

```python
# Return cached value if recent enough
now = time.time()
if now - _dht_cache["timestamp"] < DHT_CACHE_SECONDS:  # <-- Timestamp ist ALT!
    if _dht_cache["temp"] is not None:
        return (_dht_cache["temp"], _dht_cache["humidity"])  # <-- GEFRORENE WERTE!
```

**Das Problem**: Bei Sensor-Ausfall wird der Timestamp nicht aktualisiert, aber der Cache-Check sagt trotzdem "frisch genug" und gibt die alten Werte ewig zurück.

---

## BETROFFENE CODE-STELLEN

### PRIMARY: `temperature_bp.py`

| Zeile | Problem |
|-------|---------|
| 57-59 | Duplicate Cache `_dht_cache` |
| 71-75 | Cache-Check gibt alte Werte ohne Timeout-Update zurück |
| 92-95 | Fallback bei Sensor-Fehler, Timestamp wird nicht aktualisiert |

### SECONDARY: `app.py`

| Zeile | Problem |
|-------|---------|
| 444-452 | Dehumidifier-Reader nutzt `temperature_bp.read_dht22()` statt sensor_cache |
| 509-518 | DataLogger nutzt auch die falsche Funktion |

---

## EMPFOHLENER FIX

### Phase 1: Vollständige Migration zu sensor_cache

1. **In `app.py`**: Alle Referenzen zu `temperature_bp.read_dht22()` ersetzen durch `sensor_cache.read_dht22()`

2. **Dehumidifier humidity_reader (app.py Zeile 444-452)**:
```python
def humidity_reader():
    from grow_pi.utils.sensor_cache import read_dht22
    _, humidity = read_dht22()
    return humidity
```

3. **DataLogger sensor_reader (app.py Zeile 509-518)**:
```python
def sensor_reader():
    from grow_pi.utils.sensor_cache import read_dht22
    return read_dht22()
```

### Phase 2: Cache-Timeout-Bug beheben

In `sensor_cache.py`: Bei Sensor-Fehler Timestamp aktualisieren, damit nach 30s ein neuer Versuch gestartet wird.

### Phase 3: Dead Code entfernen

`temperature_bp.py` Zeile 57-98: Die alte `read_dht22()` Funktion als deprecated markieren oder entfernen.

---

## RISK ASSESSMENT

| Faktor | Bewertung |
|--------|-----------|
| Severity | 🔴 CRITICAL |
| Impact | Falsche Sensor-Werte für beliebig lange Zeit |
| Scope | Alle DHT22-abhängigen Endpoints |
| Fix Complexity | MEDIUM (3 Dateien ändern) |
| Rollback Risk | LOW (kann einfach rückgängig gemacht werden) |

---

## VALIDIERUNGSPUNKTE NACH FIX

1. ✅ Sensor-Werte aktualisieren sich kontinuierlich
2. ✅ Bei Sensor-Ausfall: Timeout nach ~30s, dann neuer Versuch
3. ✅ Alle Endpoints zeigen identische Werte
4. ✅ Dehumidifier funktioniert mit korrekten Werten
5. ✅ DataLogger schreibt korrekte Werte
6. ✅ Keine Endlos-Cache-Loops mehr

---

**NÄCHSTER SCHRITT:** Builder-Agent zur Implementierung des Fixes
