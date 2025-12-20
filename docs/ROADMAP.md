# GrowPi Roadmap

**Version**: v6.21.0 | **Stand**: 2025-12-20 | **Status**: Active Development

---

## Schnellübersicht

### KRITISCH
| # | Feature | Status | Version |
|---|---------|--------|---------|
| 1 | [Pi Health Monitoring](#1-pi-health-monitoring) | 📋 Geplant | v6.22.0 |
| 2 | [CPU-Lüftersteuerung](#2-cpu-lüftersteuerung) | 📋 Geplant | v6.22.0 |

### REFACTORING
| # | Feature | Status | Version |
|---|---------|--------|---------|
| 3 | [TinyTuya Migration](#3-tinytuya-migration) | 📋 Geplant | v6.23.0 |
| 4 | [api.py Modularisierung](#4-apipy-modularisierung) | 📋 Geplant | - |

### FEATURES
| # | Feature | Status | Version |
|---|---------|--------|---------|
| 5 | [Timelapse Kamera](#5-timelapse-kamera) | 📋 Geplant | v6.17.0 |
| 6 | [Bezier Editor Mobile Fix](#6-bezier-editor-mobile-fix) | 🟡 UI-Polish | v6.15.1 |
| 7 | [Device Status Dashboard](#7-device-status-dashboard) | 📋 Geplant | - |

### OFFENE BUGS
| # | Bug | Status |
|---|-----|--------|
| 8 | [Zeitschaltung/Override testen](#8-zeitschaltungoverride-testen) | 🟡 Zu testen |
| 9 | [Datalog/History Problem](#9-dataloghistory-problem) | 🔴 Zu untersuchen |

---

## Details

---

### 1. Pi Health Monitoring

**Status**: 📋 GEPLANT - KRITISCH
**Version**: v6.22.0
**Grund**: Pi-Absturz am 2025-12-20 ohne Vorwarnung

#### Ziel

Dashboard-Widget mit System-Health:

| Metrik | Warnschwelle |
|--------|--------------|
| CPU-Temperatur | > 70°C Warnung, > 80°C Kritisch |
| CPU-Auslastung | > 80% Warnung |
| RAM-Nutzung | > 85% Warnung |
| Disk-Nutzung | > 90% Warnung |
| Uptime | Info |
| Sensor-Status | Rot wenn Fehler |

#### API-Endpoints

- `GET /api/health/system` - CPU, RAM, Disk, Uptime
- `GET /api/health/sensors` - Status aller Sensoren

#### Betroffene Dateien

- `grow_pi/web/blueprints/health_bp.py` (NEU)
- `static/js/modules/health.js` (NEU)
- `static/index.html` (Dashboard Widget)

---

### 2. CPU-Lüftersteuerung

**Status**: 📋 GEPLANT
**Abhängigkeit**: Pi Health Dashboard muss zuerst implementiert sein
**Hardware**: Noctua-Lüfter (wird später angeschlossen)

#### Ziel

Temperaturgesteuerte Lüftersteuerung:
- < 50°C: Lüfter aus
- 50-60°C: Lüfter 50%
- > 60°C: Lüfter 100%

---

### 3. TinyTuya Migration

**Status**: 📋 GEPLANT - KRITISCH
**Version**: v6.23.0
**Aufwand**: 3-4 Stunden

#### Hintergrund

Cloud API hat Quota Limits → Smart Plugs nicht steuerbar. TinyTuya = lokale Kommunikation ohne Cloud.

#### Vorteile

| Vorher (Cloud) | Nachher (Lokal) |
|----------------|-----------------|
| ❌ Quota Limits | ✅ Keine Limits |
| ❌ 500-2000ms | ✅ 50-100ms |
| ❌ Internet nötig | ✅ Offline-fähig |

#### Schritte

1. `pip install tinytuya`
2. `python -m tinytuya wizard` (holt Local Keys)
3. `SmartPlugController.py` migrieren
4. Testen

#### Betroffene Dateien

- `/pi-controller/grow_pi/lamps/smart_plug_controller.py`
- `/pi-controller/devices.json` (NEU)

---

### 4. api.py Modularisierung

**Status**: 📋 GEPLANT
**Detaillierter Plan**: [`PLAN_API_REFACTORING.md`](./PLAN_API_REFACTORING.md)

#### Problem

- `api.py` hat **1119 Zeilen** - zu groß
- ~700 Zeilen sind **duplizierter Code**
- Nur 3 von 9 Blueprints aktiv

#### Ziel

- api.py: 1119 → ~200 Zeilen
- Alle 9 Blueprints aktivieren
- Duplikate entfernen

---

### 5. Timelapse Kamera

**Status**: 📋 GEPLANT
**Version**: v6.17.0
**Detaillierter Plan**: [`/agents/TIMELAPSE_CAMERA_PLAN.md`](/agents/TIMELAPSE_CAMERA_PLAN.md)

#### Funktionalität

- Intervall: 30s bis 10 Minuten (konfigurierbar)
- **Dunkelheits-Filter**: Überspringt schwarze Bilder wenn Lampen aus
- Galerie mit Lightbox
- Speicher-Anzeige

#### API-Endpoints

- `GET /api/camera/timelapse/stats`
- `GET/POST /api/camera/timelapse/config`
- `GET /api/camera/timelapse/images`

---

### 6. Bezier Editor Mobile Fix

**Status**: 🟡 FUNKTIONIERT - UI POLISH NÖTIG
**Version**: v6.15.1

#### Aktueller Stand

- ✅ Grundfunktionalität implementiert
- ✅ Keyframes können gesetzt/verschoben werden

#### TODO

- [ ] Mobile Layout verbessern
- [ ] Touch-Targets größer
- [ ] Fullscreen-Modus optimieren

---

### 7. Device Status Dashboard

**Status**: 📋 GEPLANT
**Aufwand**: 1-2 Tage

#### Ziel

Zentrale Übersicht aller schaltbaren Geräte mit Manual Override:
- Auto/Manual Toggle pro Gerät
- ON/OFF Status
- Letzte Aktion + Trigger-Grund

---

### 8. Zeitschaltung/Override testen

**Status**: 🟡 ZU TESTEN

#### Zu testen

- [ ] Zeitfenster im UI anlegen
- [ ] Prüfen ob Scheduler greift
- [ ] Override-Funktion testen

---

### 9. Datalog/History Problem

**Status**: 🔴 ZU UNTERSUCHEN
**Gemeldet**: 2025-12-07

#### Symptome

Console zeigt `[History] Loading data for 24 hours (downsampled)` - unbekanntes Problem.

#### Zu untersuchen

- [ ] Werden Daten korrekt geladen?
- [ ] Chart-Darstellung prüfen
- [ ] API-Response prüfen

---

## Future Features (Ideen)

- Multi-Geräte-Szenarien (z.B. "Nacht-Modus")
- Heizungs-Steuerung (Temperatur-basiert)
- Lüftungs-Automation
- VPD-Optimierung
- Push-Benachrichtigungen (Telegram/Email)
- Hochauflösende Kurven (96 Steps statt 24)

---

## Archiv

Alle abgeschlossenen Features und Bugs: **[ROADMAP_ARCHIVE.md](./ROADMAP_ARCHIVE.md)**

---

## Change Log

| Datum | Änderung |
|-------|----------|
| 2025-12-20 | Roadmap aufgeräumt, Archiv erstellt |
| 2025-12-20 | TinyTuya Migration dokumentiert |
| 2025-12-20 | Pi Health Monitoring hinzugefügt |

---

**Aktuelle Version**: v6.21.0
