# Kritischer Bug-Fix Plan: Entfeuchtungsanlage schaltet nicht aus

**Datum:** 2025-12-08
**Version:** v6.16.0 (geplant)
**Priorität:** KRITISCH
**Status:** PLAN - Wartet auf Genehmigung

---

## Executive Summary

### Zwei Probleme identifiziert:

| Problem | Schwere | Ursache |
|---------|---------|---------|
| **Bug A:** Entfeuchtung schaltet nicht aus | KRITISCH | `min_run_time` (300s) blockiert Off-Befehl |
| **Problem B:** API Chaos | HOCH | 20+ duplizierte Endpoints, Flask-Routing-Konflikte |

### Empfehlung: **BUG FIX FIRST**

**Begründung:**
- Refactoring ist zu risikoreich für Hardware-kritische Steuerung
- Der Bug ist ein **Konfigurationsproblem**, kein Code-Fehler
- Fix ist trivial (Zahlenwert ändern), Refactoring ist komplex
- Produktionssystem muss JETZT stabil laufen

---

## Analyse-Ergebnisse

### Bug A: Root Cause Analysis

**Flow wenn Aus-Befehl ausgelöst wird:**

```
1. Luftfeuchtigkeit sinkt unter low_threshold (z.B. 52% < 55%)
2. _check_humidity_automation() erkennt: "Muss ausschalten"
3. Ruft _ensure_state(False) auf
4. _ensure_state() prüft: elapsed < min_run_time (5s < 300s)
5. → BLOCKIERT! "min_run_time not reached"
6. Plug bleibt AN für volle 5 Minuten
```

**Problematische Zeilen in `dehumidifier_controller.py`:**
- Zeilen 645-649: `min_run_time` Constraint blockiert Off-Befehl
- Default: `min_run_time = 300` (5 Minuten!)
- Vergleich: `min_off_time = 60` (1 Minute)

**Warum Ein funktioniert aber Aus nicht:**
- Ein-Schalten: `min_off_time = 60s` → kurzes Fenster
- Aus-Schalten: `min_run_time = 300s` → 5 Minuten Blockade!

### Problem B: API Chaos Analysis

**api.py Statistiken:**
- **1504 Zeilen** (viel zu groß!)
- **30 Endpoints** direkt in api.py
- **32 Endpoints** in Blueprints
- **20+ Duplikate** zwischen api.py und Blueprints

**Kritischer Konflikt bei Dehumidifier:**

| Endpoint | api.py (Legacy) | Blueprint (Modern) |
|----------|-----------------|-------------------|
| POST /api/room/config | `schedule_enabled` ❌ | `time_schedule_enabled` ✅ |
| POST /api/room/dehumidifier | Alte Logik | Neue Logik mit Verifikation |

**Flask-Routing-Problem:**
- api.py Routen werden ZUERST registriert
- Blueprint Routen werden SPÄTER registriert
- Bei Duplikaten gewinnt api.py → **FALSCHE Route wird verwendet!**

---

## Aktionsplan

### Phase 1: Hotfix (v6.16.0) - HEUTE

**Ziel:** Entfeuchtung schaltet zuverlässig aus

#### Schritt 1.1: min_run_time reduzieren
```python
# dehumidifier_controller.py, Zeile ~95
# ALT:
min_run_time: int = 300  # 5 Minuten

# NEU:
min_run_time: int = 60   # 1 Minute (wie min_off_time)
```

**Risiko:** Gering - nur Timing-Constraint
**Vorteil:** Sofortige Wirkung, keine Code-Änderung

#### Schritt 1.2: Legacy-Routen deaktivieren
```python
# api.py, Zeilen 1100-1250
# Kommentiere die Legacy Dehumidifier-Routen aus:
# - /api/room (GET)
# - /api/room/config (GET, POST)
# - /api/room/dehumidifier (POST)
```

**Risiko:** Mittel - könnte Frontend-Calls brechen
**Vorteil:** Blueprint-Routen übernehmen (korrekte Logik)

#### Schritt 1.3: Validierung
- Teste manuelles Ein/Aus über Frontend
- Teste Automation bei Grenzwerten
- Prüfe Logs auf "Blocked" Meldungen

### Phase 2: Stabilisierung (v6.17.0) - Diese Woche

**Ziel:** Robustere Automation

#### Schritt 2.1: Separate Constraints für AUTO/MANUAL
```python
def _ensure_state(self, target_on: bool, trigger: TriggerType, reason: str):
    # MANUAL Triggers ignorieren min_run_time
    if trigger == TriggerType.MANUAL:
        # Direkt ausführen ohne Timing-Constraints
        return self._set_plug_state(target_on)

    # AUTO Triggers respektieren Constraints
    if not target_on and self._is_on:
        if elapsed < self._config.min_run_time:
            logger.debug(f"Blocked: min_run_time not reached")
            return None
```

#### Schritt 2.2: Intelligente Fallback-Logik
```python
# Override bei kritischen Bedingungen
if humidity < (low_threshold * 0.85):  # 15% unter Schwelle
    logger.warning(f"Critical low humidity {humidity}%, forcing OFF")
    return self._ensure_state(False, TriggerType.EMERGENCY, "critical low")
```

### Phase 3: Refactoring (v6.20.0+) - Später

**Ziel:** Clean Code, keine Duplikate

#### Schritt 3.1: Blueprint-Migration
- Alle Legacy-Routen aus api.py entfernen
- Nur Blueprint-Registrierung behalten
- api.py auf <200 Zeilen reduzieren

#### Schritt 3.2: Endpoint-Konsolidierung
- Duplikate eliminieren
- Konsistente Naming-Convention
- OpenAPI/Swagger Dokumentation

#### Schritt 3.3: Tests
- Unit Tests für alle Endpoints
- Integration Tests für Automation
- Load Tests für Stabilität

---

## Risiko-Assessment

| Aktion | Risiko | Mitigation |
|--------|--------|------------|
| min_run_time ändern | Gering | Kann schnell zurückgesetzt werden |
| Legacy-Routen deaktivieren | Mittel | Teste alle Frontend-Funktionen |
| Refactoring | HOCH | Erst nach Stabilisierung, schrittweise |

---

## Empfohlene Reihenfolge

```
HEUTE:
├── 1. min_run_time = 60 setzen (5 Min → 1 Min)
├── 2. Legacy-Routen in api.py auskommentieren
├── 3. Testen (Manual + Auto)
└── 4. Deploy als v6.16.0

DIESE WOCHE:
├── 5. MANUAL Override für Constraints
├── 6. Emergency Fallback-Logik
└── 7. Deploy als v6.17.0

SPÄTER:
├── 8. Vollständiges API Refactoring
├── 9. Test-Suite aufbauen
└── 10. Dokumentation aktualisieren
```

---

## Fragen an User

1. **min_run_time:** Soll es auf 60s oder noch kürzer (30s) gesetzt werden?
2. **Legacy-Routen:** Soll ich sie auskommentieren oder komplett löschen?
3. **Priorität:** Ist Phase 2 (Stabilisierung) wichtiger als Phase 3 (Refactoring)?

---

## Nächste Schritte

Nach Genehmigung:
1. `@builder` für Phase 1 Implementierung
2. `@validator` für Cross-File-Konsistenz
3. Deployment auf Pi (mit deiner Erlaubnis)
4. `@scribe` für CHANGELOG Update

---

**Erstellt von:** Orchestrator
**Agenten verwendet:** @architect, @explore
**Wartet auf:** User-Genehmigung
