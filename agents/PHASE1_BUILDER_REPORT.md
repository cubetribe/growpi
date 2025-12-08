# Phase 1 Builder Report - Kritischer Bugfix

**Datum**: 2025-12-08
**Version**: 6.15.1
**Agent**: @builder
**Datei**: `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi/utils/dehumidifier_controller.py`

---

## Root Cause Analysis

**Problem**: Entfeuchtungsanlage schaltet nicht aus bei manueller OFF-Betätigung.

**Ursache**: In der `_ensure_state()` Methode war die Reihenfolge der Checks FALSCH:
1. Zeilen 636-649 (ALT): `min_run_time` Check blockierte ALLE Off-Befehle
2. Zeilen 651-666 (ALT): MANUAL Bypass kam DANACH → wurde nie erreicht bei laufendem Timer!

**Resultat**: User klickt "OFF", aber der Code erreicht nie den MANUAL-Check weil vorher durch `min_run_time` blockiert wird.

---

## Implementierte Fixes

### Fix 1: MANUAL Bypass VOR Timing Constraints

**Zeilen**: 636-694 (NEU)

**Änderung**: MANUAL-Check kommt jetzt als ERSTES, BEVOR alle Timing-Checks.

**Vorher** (FALSCH):
```python
# 1. Timing constraints (BLOCKIERT ALLES)
if trigger != TriggerType.MANUAL and self._last_toggle_time:
    elapsed = (datetime.now() - self._last_toggle_time).total_seconds()
    if not target_on and self._is_on:
        if elapsed < self._config.min_run_time:
            return None  # Blockiert AUCH MANUAL!

# 2. MANUAL bypass (WIRD NIE ERREICHT wenn blockiert)
if trigger == TriggerType.MANUAL:
    logger.info(f"MANUAL override...")
```

**Nachher** (KORREKT):
```python
# 1. MANUAL bypass ZUERST - user override takes priority
if trigger == TriggerType.MANUAL:
    logger.info(f"MANUAL override: bypassing timing constraints")
    # Continue to execute command regardless of timing

# 2. Timing constraints NUR für automation triggers
else:
    if self._last_toggle_time:
        elapsed = (datetime.now() - self._last_toggle_time).total_seconds()
        # Timing checks hier...
```

**Resultat**: MANUAL Befehle werden NIEMALS von Timing Constraints blockiert.

---

### Fix 2: Emergency Override bei kritisch niedriger Luftfeuchtigkeit

**Zeilen**: 648-674 (NEU)

**Logik**:
- Wenn `humidity < (low_threshold * 0.85)` → SOFORT ausschalten
- Beispiel: low_threshold=55%, kritisch wäre < 46.75%
- Bypassed `min_run_time` für SAFETY

**Code**:
```python
if not target_on and self._is_on and trigger == TriggerType.HUMIDITY_AUTO:
    humidity = self.get_humidity()
    if humidity is not None:
        low_threshold = self._config.target - self._config.threshold_low
        critical_threshold = low_threshold * 0.85
        if humidity < critical_threshold:
            logger.warning(
                f"EMERGENCY: Humidity critically low ({humidity:.1f}% < {critical_threshold:.1f}%) "
                f"-> forcing immediate shutdown (bypassing min_run_time)"
            )
            # Skip timing constraints - continue to execute
```

**Resultat**: Schutz vor Austrocknung bei AUTO-Modus, selbst wenn `min_run_time` noch nicht abgelaufen ist.

---

### Fix 3: Default min_run_time reduziert

**Zeile**: 82 (geändert von 300 → 60)

**Vorher**:
```python
min_run_time: int = 300  # seconds
```

**Nachher**:
```python
min_run_time: int = 60  # seconds (reduced from 300 to allow faster shutoff)
```

**Resultat**: Reaktionszeit für AUTO-Shutoff von 5 Minuten auf 1 Minute reduziert.

---

## Code-Änderungen Zusammenfassung

| Zeile(n) | Änderung | Typ |
|----------|----------|-----|
| 17-34 | Version → 6.15.1 + Bugfix Docstring | Dokumentation |
| 82 | `min_run_time: int = 300` → `60` | Config Default |
| 636-694 | Komplette Neustrukturierung `_ensure_state()` | Kritischer Fix |

---

## Test-Empfehlungen

### Test 1: Manueller OFF-Befehl während min_run_time
**Setup**:
1. Entfeuchter starten (AUTO oder MANUAL ON)
2. Sofort nach Start (<60s) MANUAL OFF klicken

**Erwartetes Verhalten**:
- Entfeuchter schaltet SOFORT aus
- Log-Meldung: `"MANUAL override: bypassing timing constraints for OFF"`
- Keine Blockierung durch `min_run_time`

**Vorher (Bug)**: Blockiert durch `min_run_time`, nichts passiert
**Nachher (Fix)**: Schaltet sofort aus

---

### Test 2: Emergency Override bei kritischer Luftfeuchtigkeit
**Setup**:
1. Config: `target=60%`, `threshold_low=5%` → low_threshold=55%
2. Entfeuchter läuft (AUTO ON)
3. Luftfeuchtigkeit fällt plötzlich auf 45% (< 46.75%)

**Erwartetes Verhalten**:
- Entfeuchter schaltet SOFORT aus (auch wenn `min_run_time` noch läuft)
- Log-Meldung: `"EMERGENCY: Humidity critically low (45.0% < 46.75%) -> forcing immediate shutdown"`

**Risiko wenn nicht gefixt**: Pflanzen austrocknen weil Entfeuchter nicht rechtzeitig ausschaltet

---

### Test 3: Normal AUTO OFF mit neuem min_run_time
**Setup**:
1. Entfeuchter startet (AUTO ON bei hoher Luftfeuchtigkeit)
2. Luftfeuchtigkeit sinkt unter `low_threshold`

**Erwartetes Verhalten**:
- Nach 60 Sekunden (vorher 300s) schaltet Entfeuchter aus
- Schnellere Reaktion auf Luftfeuchtigkeit-Änderungen

---

### Test 4: MANUAL ON während min_off_time
**Setup**:
1. Entfeuchter ausschalten (AUTO oder MANUAL OFF)
2. Sofort (<60s) MANUAL ON klicken

**Erwartetes Verhalten**:
- Entfeuchter schaltet SOFORT ein
- Keine Blockierung durch `min_off_time`

---

## Regression-Risiken

### Niedrig
- **Auto-Modus Timing**: Normal AUTO ON/OFF sollte weiterhin `min_run_time` / `min_off_time` respektieren
- **Time Schedule**: Time-based schedules sollten unverändert funktionieren

### Zu überwachen
- **Emergency Override zu sensitiv**: Falls 85% Threshold zu hoch, zu häufige Abschaltungen
  - Lösung: Threshold anpassen auf z.B. 80% wenn nötig
- **min_run_time=60s zu kurz**: Falls Entfeuchter zu oft an/aus schaltet (Wear & Tear)
  - Lösung: Config per DB anpassen auf z.B. 120s

---

## Deployment-Hinweise

### Kein DB-Migration nötig
- Alle Änderungen sind Code-Only
- Keine Schema-Änderungen

### Rollback-Plan
Wenn Bug weiterhin auftritt:
```bash
cd /opt/grow-pi
git revert <commit-hash>
sudo systemctl restart grow-pi
```

### Monitoring nach Deployment
```bash
# Live-Logs beobachten
sudo journalctl -u grow-pi -f | grep -E "MANUAL|EMERGENCY|min_run_time"

# Status prüfen
curl http://192.168.0.86:5000/api/dehumidifier/status
```

---

## Betroffene Dateien

- `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi/utils/dehumidifier_controller.py`

---

## Nächste Schritte

1. **Code-Review** durch Architect
2. **Unit Tests** schreiben für `_ensure_state()` Edge Cases
3. **Lokale Tests** durchführen (siehe Test-Plan oben)
4. **Deploy zu Pi** nach User-Genehmigung
5. **Monitor** für 24h nach Deployment

---

**Status**: ✅ Code-Änderungen abgeschlossen
**Bereit für**: Architect Review + User Approval für Deployment
