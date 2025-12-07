# CHANGELOG-Analyse v6.0 - v6.9.0 - GrowPi Project

**Erstellt**: 2025-12-07
**Agent**: Explore Subagent

---

## Übersicht der Versionen

| Version | Datum | Status | Hauptfeature |
|---------|-------|--------|--------------|
| v6.9.0 | 06.12.25 | ✅ Deployed | PWM Zero-Downtime Restarts |
| v6.8.1 | 06.12.25 | ⚠️ Probleme | Repository Cleanup, 503 Error |
| v6.8.0 | 06.12.25 | ⚠️ Probleme | 4 Features parallel |
| v6.7.0 | 06.12.25 | ✅ Deployed | Bug Fixes |
| v6.6.0 | 06.12.25 | ✅ Deployed | CPU Optimierung (-67%) |
| v6.5.0 | 06.12.25 | ✅ Deployed | Major Refactoring |
| v6.0 | 06.12.25 | ✅ Branch | Complete Modularization |

---

## ⚠️ KRITISCHE PROBLEME

### 1. `/api/curves/*` 503 Error (v6.8.0/v6.8.1)
- **Status**: NICHT GELÖST
- **Symptom**: CurveController initialisiert nicht
- **Impact**: Kurven-Editor + Presets funktionieren nicht

### 2. Smart Plug Controller nicht integriert (v6.5.0)
- **Status**: BEKANNT
- **Problem**: `smart_plug_controller.py` existiert aber nicht in `app.py`
- **Impact**: Tuya Smart Plug / Entfeuchter-Steuerung nicht aktiv

### 3. Frontend HTML nicht migriert (v6.5.0)
- **Status**: BEKANNT
- **Problem**: JS-Module erstellt, aber index.html nutzt noch inline Code

---

## Neue API-Endpoints (v6.0 - v6.9)

### Core (v6.0)
| Endpoint | Methode | Status |
|----------|---------|--------|
| `/api/status` | GET | ✅ |
| `/api/health` | GET | ✅ |
| `/api/temperature` | GET | ✅ |
| `/api/lamp/<channel>` | POST | ✅ |
| `/api/mode` | GET/POST | ✅ |
| `/api/curves` | GET | ❌ 503 |
| `/api/curves/<channel>` | GET/PUT | ❌ 503 |
| `/api/curves/preview` | GET | ❌ 503 |
| `/api/logs/sensors` | GET | ✅ |
| `/api/logs/lamps` | GET | ✅ |
| `/api/logs/events` | GET | ✅ |

### Costs (v6.5)
| Endpoint | Methode | Status |
|----------|---------|--------|
| `/api/costs` | GET/POST | ⚠️ Zu prüfen |
| `/api/costs/config` | GET/POST | ⚠️ Zu prüfen |

### Room/Dehumidifier (v6.5)
| Endpoint | Methode | Status |
|----------|---------|--------|
| `/api/room` | GET | ⚠️ Zu prüfen |
| `/api/room/config` | GET/POST | ⚠️ Zu prüfen |
| `/api/room/dehumidifier` | POST | ⚠️ Zu prüfen |

### Schedules (v6.8)
| Endpoint | Methode | Status |
|----------|---------|--------|
| `/api/room/schedules` | GET/POST | ⚠️ Zu prüfen |
| `/api/room/schedules/<id>` | PUT/DELETE | ⚠️ Zu prüfen |

### Presets (v6.8)
| Endpoint | Methode | Status |
|----------|---------|--------|
| `/api/curves/presets` | GET/POST | ❌ 503 (abhängig von curves) |
| `/api/curves/presets/<id>` | PUT/DELETE | ❌ 503 |
| `/api/curves/presets/<id>/apply` | POST | ❌ 503 |

---

## Neue DB-Tabellen

| Version | Tabelle | Status |
|---------|---------|--------|
| v6.0 | `sensor_readings` | ✅ |
| v6.0 | `lamp_state_log` | ✅ |
| v6.0 | `system_events` | ✅ |
| v6.0 | `lamp_curves` | ✅ |
| v6.5 | `costs_log` | ⚠️ Zu prüfen |
| v6.5 | `room_config` | ⚠️ Zu prüfen |
| v6.8 | `device_time_schedules` | ⚠️ Zu prüfen |
| v6.8 | `curve_presets` | ⚠️ Zu prüfen |

---

## Neue JavaScript-Module

| Version | Modul | LOC | Status |
|---------|-------|-----|--------|
| v6.0 | `api.js` | 218 | ✅ |
| v6.0 | `state.js` | 336 | ✅ |
| v6.0 | `control.js` | 228 | ✅ |
| v6.0 | `curves.js` | 661 | ✅ |
| v6.0 | `history.js` | 623 | ✅ |
| v6.5 | `costs.js` | 198 | ⚠️ Zu prüfen |
| v6.5 | `environment.js` | 174 | ⚠️ Zu prüfen |
| v6.8 | `accordion.js` | 150 | ✅ |

---

## Feature-Details

### v6.9.0 - PWM Zero-Downtime
- **Neue Datei**: `grow_pi/utils/pwm_state.py`
- **Funktion**: PWM-Werte bleiben bei Service-Restart erhalten
- **Test**: Kein LED-Flackern bei `systemctl restart grow-pi`

### v6.8.0 - Feature Pack (4 Features)

**Feature 1: Version Display** ✅
- Badge im Header zeigt v6.8.0

**Feature 2: Zeitbasierte Schaltung** ⚠️
- DB-Tabelle: `device_time_schedules`
- API: `/api/room/schedules`
- Priority: Zeit > Feuchtigkeit > Manuell

**Feature 3: Accordion** ✅
- Klappbare Sektionen
- localStorage Persistence

**Feature 4: Kurven-Presets** ❌
- DB-Tabelle: `curve_presets`
- API: `/api/curves/presets`
- 3 Built-in: Keimung, Wachstum, Blüte
- **BROKEN**: 503 Error

### v6.6.0 - CPU Optimierung
- CPU: 75% → 15-25% (-67%)
- DHT22 Cache: 3s → 30s
- Logging Interval: 60s → 120s

### v6.5.0 - Modular Architecture
- Frontend LOC: -86%
- 8 Flask Blueprints
- 8 JS Module
- 140 Unit Tests

---

## Debugging Prioritäten

### Priorität 1: Zero-Downtime verifizieren
- [ ] PWM-State-File prüfen
- [ ] Service-Restart testen

### Priorität 2: Curves 503 Error
- [ ] CurveController Initialisierung debuggen
- [ ] Import-Pfade prüfen
- [ ] DB-Schema validieren

### Priorität 3: Entfeuchter/Room
- [ ] DehumidifierController prüfen
- [ ] Tuya-Integration validieren
- [ ] Smart Plug Blueprint fehlt?

### Priorität 4: Kosten-Tracking
- [ ] API-Endpoints testen
- [ ] DB-Tabellen prüfen

---

## Hardware Status

| Komponente | GPIO | Status |
|------------|------|--------|
| Far Red | 16 | ✅ |
| Warm White | 13 | ✅ |
| Cool White | 12 | ✅ |
| UV | 18 | ✅ |
| DHT22 | 4 | ✅ |
| PWM Persistence | - | ✅ (v6.9) |
