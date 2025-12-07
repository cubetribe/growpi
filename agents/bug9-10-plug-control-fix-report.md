# Bug #9 + Bug #10: Smart Plug Control Fix Report

**Datum**: 2025-12-07
**Version**: 6.9.2
**Status**: BEHOBEN

---

## Zusammenfassung

Zwei kritische Bugs in der Lueftersteuerung wurden behoben:

1. **Bug #9**: `SmartPlugController.turn_on()` und `turn_off()` gaben immer `True` zurueck ohne zu verifizieren, ob der Befehl erfolgreich war
2. **Bug #10**: Bei manueller Steuerung (MANUAL Trigger) wurde der Befehl uebersprungen, wenn der interne Status "korrekt" erschien

---

## Bug #9: SmartPlugController - Keine Erfolgsverifikation

### Problem

Die Methoden `turn_on()` und `turn_off()` sendeten den Befehl an das Tuya-Geraet und gaben sofort `True` zurueck, ohne zu pruefen ob das Geraet tatsaechlich geschaltet wurde.

**Vorher (Zeilen 160-181)**:
```python
def turn_on(self, device_id: str) -> bool:
    """Turn plug on"""
    device = self.devices.get(device_id)
    if device:
        try:
            device.turn_on()
            if device_id in self.last_update: del self.last_update[device_id]
            return True  # <- Immer True, keine Verifikation!
        except Exception as e:
            logger.error(f"Error turning on {device_id} (Local): {e}")
    # ... Cloud Teil hatte das gleiche Problem
```

### Loesung

Nach dem Senden des Befehls:
1. **Kurz warten** (0.4s lokal, 0.5s Cloud) damit das Geraet den Befehl verarbeiten kann
2. **Status abfragen** via `device.status()` (lokal) oder `cloud.getstatus()` (Cloud)
3. **Verifizieren** dass der erwartete Zustand erreicht wurde (`dps['1']` fuer lokal, `switch_1` fuer Cloud)
4. **Bei Fehlschlag**: Ausfuehrlich loggen und `False` zurueckgeben

**Nachher (Zeilen 160-227 fuer turn_on, 229-296 fuer turn_off)**:
```python
def turn_on(self, device_id: str) -> bool:
    """Turn plug on with verification."""
    device = self.devices.get(device_id)
    if device:
        try:
            device.turn_on()
            time.sleep(0.4)  # Wait for device to process

            # Verify the state change
            status = device.status()
            if status and status.get('dps', {}).get('1') == True:
                # Invalidate cache
                if device_id in self.last_update: del self.last_update[device_id]
                if device_id in self.cache: del self.cache[device_id]
                logger.info(f"Successfully turned ON {device_id} (Local, verified)")
                return True
            else:
                logger.error(f"turn_on verification FAILED for {device_id}")
                return False
        except Exception as e:
            logger.error(f"Error turning on {device_id} (Local): {e}")

    # Cloud mit gleicher Logik...
```

### Geaenderte Datei

**Datei**: `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi/lamps/smart_plug_controller.py`

| Methode | Zeilen (vorher) | Zeilen (nachher) | Aenderung |
|---------|-----------------|------------------|-----------|
| `turn_on()` | 160-181 | 160-227 | +67 Zeilen (Verifikation + Logging) |
| `turn_off()` | 183-204 | 229-296 | +67 Zeilen (Verifikation + Logging) |

---

## Bug #10: DehumidifierController - Manuelle Steuerung Skip-Bug

### Problem

In `_ensure_state()` wurde bei `target_on == self._is_on` sofort `return None` ausgefuehrt - auch bei manueller Steuerung. Das bedeutete:
- User klickt "Einschalten"
- System denkt: "Ist schon an (laut internem Status)"
- Befehl wird NICHT gesendet
- Geraet bleibt in seinem tatsaechlichen Zustand (der eventuell "aus" ist)

**Vorher (Zeilen 640-642)**:
```python
# State is already correct
if target_on == self._is_on:
    return None  # <- Auch bei MANUAL!
```

### Loesung

1. **MANUAL Trigger**: Befehl wird IMMER gesendet, unabhaengig vom internen Status
2. **min_run_time/min_off_time**: Werden bei MANUAL uebersprungen (User-Override)
3. **Logging**: Klare Meldung wenn ein MANUAL Override trotz "korrektem" Status ausgefuehrt wird

**Nachher (Zeilen 631-661)**:
```python
# Check minimum time constraints (skip for MANUAL triggers - user override)
if trigger != TriggerType.MANUAL and self._last_toggle_time:
    # ... min_time checks nur fuer Automation

# BUGFIX 6.9.2: For MANUAL triggers, ALWAYS send the command
if trigger == TriggerType.MANUAL:
    if target_on == self._is_on:
        logger.info(
            f"MANUAL override: forcing {'ON' if target_on else 'OFF'} command "
            f"even though internal state is already {self._is_on}"
        )
    # Continue to execute command regardless of current state
else:
    # For automation triggers: Skip if state is already correct
    if target_on == self._is_on:
        logger.debug(f"State already correct, skipping")
        return None

# Execute state change
success = self._set_plug_state(target_on)
```

### Geaenderte Datei

**Datei**: `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi/utils/dehumidifier_controller.py`

| Bereich | Zeilen (vorher) | Zeilen (nachher) | Aenderung |
|---------|-----------------|------------------|-----------|
| Docstring Version | 17-24 | 17-29 | Version auf 6.9.2, Bugfix dokumentiert |
| `_ensure_state()` | 609-663 | 609-681 | +18 Zeilen (MANUAL Override Logik) |

---

## Zusammenspiel der Fixes

Die beiden Bugs haengen zusammen und verstaerken sich gegenseitig:

**Vorher (fehlerhaft)**:
1. User klickt "Einschalten"
2. `_ensure_state()` prueft: `target_on == self._is_on` -> "schon an" -> **return None** (Bug #10)
3. Selbst wenn der Befehl durchkaeme: `turn_on()` wuerde blind `True` zurueckgeben (Bug #9)

**Nachher (korrekt)**:
1. User klickt "Einschalten"
2. `_ensure_state()` erkennt MANUAL Trigger -> sendet IMMER den Befehl
3. `turn_on()` sendet Befehl, wartet, verifiziert Status
4. Nur wenn `dps['1'] == True`: `return True` und Update interner Status
5. Bei Fehlschlag: `return False` mit detailliertem Error-Log

---

## Log-Beispiele

### Erfolgreiche manuelle Schaltung:
```
INFO - MANUAL override: forcing ON command even though internal state is already False
INFO - Successfully turned ON bf123456789abcdef (Local, verified)
INFO - Dehumidifier ON (trigger: manual, manual on)
```

### Fehlgeschlagene Schaltung:
```
INFO - MANUAL override: forcing ON command even though internal state is already True
ERROR - turn_on verification FAILED for bf123456789abcdef (Local): expected dps['1']=True, got status={'dps': {'1': False, '18': 0, '19': 0, '20': 2300}}
ERROR - Failed to set dehumidifier state to ON
```

---

## Testempfehlung

Nach dem Neustart des Pi-Controllers:

1. **API-Test manuelles Einschalten**:
   ```bash
   curl -X POST http://192.168.0.86:5000/api/dehumidifier/on
   ```
   - Erwartung: `{"success": true}` nur wenn Geraet wirklich an ist

2. **API-Test Status-Refresh**:
   ```bash
   curl http://192.168.0.86:5000/api/dehumidifier/status
   ```
   - Erwartung: `is_on` stimmt mit physischem Geraetezustand ueberein

3. **Log-Ueberpruefung**:
   ```bash
   journalctl -u growpi -f | grep -E "(MANUAL override|verification|Successfully turned)"
   ```

---

## Betroffene Dateien

| Datei | Pfad |
|-------|------|
| SmartPlugController | `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi/lamps/smart_plug_controller.py` |
| DehumidifierController | `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi/utils/dehumidifier_controller.py` |

---

## Naechste Schritte

1. Code-Review durch Entwickler
2. Nach Genehmigung: Pi-Controller neu starten
3. Manuelle Tests durchfuehren
4. Log-Ausgaben verifizieren

**WICHTIG**: Neustart des Pi-Controllers erst nach expliziter Genehmigung!
