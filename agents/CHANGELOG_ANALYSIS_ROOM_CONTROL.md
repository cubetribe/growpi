# CHANGELOG-Analyse: Raumsteuerung & Override-Logik

**Agent**: Sonnet 4.5 (Analyse)
**Datum**: 2025-12-07
**Auftrag**: Identifizierung aller Änderungen zur Entfeuchter-Steuerung und Override-Funktion

---

## EXECUTIVE SUMMARY

**Identifiziertes Problem**: Die Automatik-Steuerung funktioniert NICHT, obwohl alle Bedingungen erfüllt sind:
- Luftfeuchtigkeit: 66% (sollte Entfeuchter einschalten)
- Sollwert: 62% + 3% = 65% Obergrenze (66% > 65%)
- Automatik: AKTIVIERT
- Erwartung: Entfeuchter AN
- Realität: Entfeuchter AUS

**Root Cause Verdacht**: Es wurden DREI kritische Bugs in v6.13.0 - v6.14.0 behoben, die GENAU dieses Problem verursacht haben könnten. Die Frage ist: Ist die aktuelle Codeversion korrekt deployed auf dem Pi?

---

## CHRONOLOGISCHE ÄNDERUNGSHISTORIE

### v6.4.0 (2025-12-06) - INITIALE EINFÜHRUNG

**Features**:
- Erstmalige Implementation der Raumsteuerung/Entfeuchter
- Smart dehumidifier automation
- Target humidity configuration (30-90%)
- Auto-toggle based on sensor readings
- **Manual override capability** - ERSTE Erwähnung von Override

**Dateien**: Neu erstellt
- `dehumidifier_controller.py`
- `dehumidifier_bp.py`

---

### v6.7.0 (2025-12-06) - DEPLOYMENT FIXES

**Fixed**:
- Kurven-Tab not loading data
- Missing blueprints deployment (`dehumidifier_bp.py`)
- DehumidifierController initialization in hardware service

---

### v6.8.0 (2025-12-06) - ZEITBASIERTE SCHALTUNG EINGEFÜHRT

**Added**:
- **Zeitbasierte Geräte-Schaltung** (Time Schedules)
- Neue DB-Tabelle: `device_time_schedules`
- **Priority-Logik**: Zeit-Fenster > Feuchtigkeit > Manuell
- Smart Fallback: Prüft Feuchtigkeit wenn Zeitfenster endet
- 4 API Endpoints: `/api/room/schedules` (CRUD)
- Validierung: Verhindert überlappende Zeitfenster
- Mitternachts-Wrap-around Support (23:00-01:00)

**KRITISCH**: Dies ist die erste Version mit komplexer Priority-Logik. Potentielle Fehlerquelle!

---

### v6.9.1 (2025-12-07) - BUG #8: STATUS-DESYNC FIX

**Problem identifiziert**:
- Controller speicherte internen Status (`self._is_on`)
- ABER: Synchronisierte NIE mit echtem Tuya-Gerätestatus
- Wenn Gerät manuell/physisch geschaltet wurde, wusste Controller nichts davon
- **Automation schaltete nicht zuverlässig**

**Root Cause** (alte Version):
```python
# In _ensure_state() Zeile 632:
if target_on == self._is_on:
    return None  # Tut nichts weil es denkt State ist korrekt!
```

**Fix implementiert**:
1. Neue Methode: `_sync_device_status()` in DehumidifierController
   - Fragt echten Tuya-Status vor jedem Schaltvorgang ab
   - Synchronisiert internen State mit echtem Gerätestatus
2. Geändert: `_ensure_state()` ruft ZUERST `_sync_device_status()` auf
3. Geändert: `get_status()` synchronisiert auch vor API-Response

**Datei**: `dehumidifier_controller.py` (Zeilen 708-737)

---

### v6.14.0 (2025-12-07) - BUG #9 + #10 FIX

#### Bug #9: SmartPlugController - Keine Erfolgsverifikation

**Problem**:
- `turn_on()` und `turn_off()` gaben IMMER `True` zurück
- OHNE zu verifizieren ob Befehl erfolgreich war

**Fix**:
```python
def turn_on(self, device_id: str) -> bool:
    device.turn_on()
    time.sleep(0.4)  # Warten auf Befehlsverarbeitung

    # Status verifizieren
    status = device.status()
    if status and status.get('dps', {}).get('1') == True:
        return True
    else:
        return False
```

**Datei**: `smart_plug_controller.py` (Zeilen 160-296)

---

#### Bug #10: DehumidifierController - Manual Override Skip-Bug

**Problem**:
- Bei `target_on == self._is_on` wurde sofort `return None` ausgeführt
- **AUCH BEI MANUELLER STEUERUNG**!

**Fix**:
```python
# BUGFIX 6.9.2: For MANUAL triggers, ALWAYS send command
if trigger == TriggerType.MANUAL:
    if target_on == self._is_on:
        logger.info("MANUAL override: forcing command")
    # Continue to execute command regardless
else:
    # For automation: Skip if state already correct
    if target_on == self._is_on:
        return None
```

**ABER**: Dieser Fix betrifft nur MANUAL Trigger, NICHT HUMIDITY_AUTO!

---

## POTENTIELLE PROBLEMSTELLEN

### HAUPTVERDACHT #1: Early Return bei Automatik

**Zeile 664-666** in aktueller Version:
```python
else:
    # For automation triggers: Skip if state is already correct
    if target_on == self._is_on:
        return None
```

Wenn `self._is_on` falsch synchronisiert ist, wird der Schaltbefehl übersprungen.

---

### HAUPTVERDACHT #2: Sync schlägt fehl

```python
def _sync_device_status(self) -> None:
    if self._plug_controller is None or not self._tuya_device_id:
        return  # WIRD ÜBERSPRUNGEN wenn kein Controller!
```

Mögliche Fehlerquellen:
1. `self._plug_controller is None` - Sync wird ÜBERSPRUNGEN
2. `self._tuya_device_id` ist leer - Sync wird ÜBERSPRUNGEN
3. Exception beim Sync - Wird nur gewarnt, Status bleibt falsch

---

### HAUPTVERDACHT #3: Automatik ist deaktiviert

```python
if not self._config.enabled:
    # Manual mode - don't change anything
    return None
```

---

## WAHRSCHEINLICHSTE FEHLERURSACHEN

### Szenario A: Status-Desync (Bug #8 nicht vollständig gefixt)
- `_sync_device_status()` wird übersprungen oder schlägt fehl
- Interner Status `self._is_on` ist falsch
- Automatik denkt Gerät ist schon im Zielzustand → skip

### Szenario B: Controller nicht initialisiert
- `self._plug_controller is None`
- Sync wird IMMER übersprungen
- Schaltbefehle werden simuliert

### Szenario C: Automatik-Config ist deaktiviert
- `self._config.enabled = False`
- `check_and_control()` tut nichts

---

## EMPFOHLENE DIAGNOSTIK

### 1. Log-Analyse auf dem Pi

```bash
ssh admin@192.168.0.86
sudo journalctl -u grow-pi -n 200 --no-pager | grep -E "(Humidity|Dehumidifier|Status sync|ensure_state)"
```

**Wonach suchen**:
- "Humidity: 66.0% (target: 62%, high: 65%, low: 56%)" - Zeigt Automatik läuft
- "Status sync: internal=X, actual=Y" - Zeigt Sync funktioniert
- "Could not sync device status" - Sync schlägt fehl
- "State already OFF, skipping (trigger: humidity_auto)" - **SMOKING GUN!**

### 2. Prüfe Konfiguration

```bash
sqlite3 /opt/grow-pi/data/growpi.db "SELECT * FROM device_automation_config WHERE device_id=1;"
```

### 3. Prüfe Tuya Device ID

```bash
sqlite3 /opt/grow-pi/data/growpi.db "SELECT id, name, tuya_device_id FROM switchable_devices WHERE id=1;"
```

### 4. Test: Manueller API-Call

```bash
curl http://192.168.0.86:5000/api/room
curl -X POST http://192.168.0.86:5000/api/room/on
curl http://192.168.0.86:5000/api/room
```

---

## NÄCHSTE SCHRITTE

1. **Log-Analyse durchführen** - Siehe Diagnostik oben
2. **Wenn "State already OFF, skipping"** - Sync-Problem (Bug #8)
3. **Wenn "Plug controller not available"** - Initialisierungsproblem
4. **Wenn keine Humidity-Logs** - Config ist deaktiviert oder Control Loop tot

---

**Report erstellt**: 2025-12-07 21:45 CET
