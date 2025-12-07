# Plan: api.py Refactoring

**Erstellt:** 2025-12-07
**Status:** GENEHMIGUNG AUSSTEHEND
**Ziel:** api.py von 1119 Zeilen auf ~200 Zeilen reduzieren

---

## Problem

Die aktuelle `api.py` ist ein **Monolith mit 1119 Zeilen**, der:
- Schwer zu debuggen ist
- Doppelte Implementierungen enthält
- Inkonsistente Blueprint-Nutzung hat
- Bei jedem Agenten-Durchlauf Fehler produziert

---

## Ist-Zustand

```
api.py (1119 Zeilen)
├── Imports & Config          (141 Zeilen)
├── Flask App Setup           (26 Zeilen)
├── Hardware-Init             (102 Zeilen)
├── Helper Functions          (115 Zeilen)
├── API Routes (DUPLIZIERT!)  (701 Zeilen)  ← DAS PROBLEM
├── Error Handlers            (11 Zeilen)
└── run_server()              (23 Zeilen)
```

**701 Zeilen sind duplizierter Code!** Diese Routes existieren bereits in Blueprints.

---

## Soll-Zustand

```
api.py (~200 Zeilen)
├── Imports                   (40 Zeilen)
├── Flask App Setup           (20 Zeilen)
├── Hardware-Init             (60 Zeilen)
├── Blueprint-Registrierung   (40 Zeilen)
├── Static File Routes        (15 Zeilen)
├── Error Handlers            (10 Zeilen)
└── run_server()              (15 Zeilen)

blueprints/
├── status_bp.py       → /api/status, /api/health
├── temperature_bp.py  → /api/temperature
├── lamps_bp.py        → /api/lamp/<ch>
├── logs_bp.py         → /api/logs/*
├── curves_bp.py       → /api/curves/*
├── mode_bp.py         → /api/mode
├── costs_bp.py        → /api/costs/* (bereits)
├── dehumidifier_bp.py → /api/room/* (bereits)
└── camera_bp.py       → /api/camera/* (NEU)
```

---

## Refactoring-Schritte

### Phase 1: Vorbereitung (HEUTE)

**Schritt 1.1:** Backup erstellen
```bash
cp api.py api.py.backup.20251207
```

**Schritt 1.2:** Bugfix deployen (ERLEDIGT)
- `dehumidifier_controller.set_humidity_reader()` hinzugefügt

---

### Phase 2: camera_bp.py erstellen

**Neue Datei:** `blueprints/camera_bp.py`

**Code extrahieren aus api.py:**
- Zeilen 905-1065 (Camera Routes)
- `/api/camera/snapshot`
- `/api/camera/stream`

**Geschätzte Größe:** ~160 Zeilen

---

### Phase 3: dependencies.py aktivieren

**Datei:** `dependencies.py` (existiert bereits!)

**Änderung in api.py:**
```python
# Nach Hardware-Init hinzufügen:
from .dependencies import (
    init_pwm_controller, init_dht_sensor, init_data_logger,
    init_curve_controller, init_mode_manager
)

init_pwm_controller(pwm_controller)
init_dht_sensor(dht_sensor, DHT_AVAILABLE)
init_data_logger(data_logger, db if DB_AVAILABLE else None)
init_curve_controller(curve_controller, CURVE_AVAILABLE)
init_mode_manager(mode_manager, MODE_MANAGER_AVAILABLE)
```

---

### Phase 4: Alle Blueprints registrieren

**Aktuell registriert (3):**
- costs_bp ✓
- dehumidifier_bp ✓
- curves_bp ✓

**Fehlen noch (5):**
- status_bp
- temperature_bp
- lamps_bp
- logs_bp
- mode_bp

**Neue Registrierung:**
```python
from .blueprints import (
    status_bp,
    temperature_bp,
    lamps_bp, init_lamps_blueprint,
    logs_bp, init_logs_bp,
    mode_bp, init_mode_blueprint,
    curves_bp, init_blueprint as init_curves_blueprint,
    costs_bp,
    dehumidifier_bp,
    camera_bp  # NEU
)

# Initialize blueprints with dependencies
init_lamps_blueprint(pwm_controller, LAMP_CHANNELS, data_logger)
init_logs_bp(DB_AVAILABLE, data_logger, get_database)
init_mode_blueprint(mode_manager, curve_controller, pwm_controller, data_logger)
init_curves_blueprint(curve_controller, DB_AVAILABLE, data_logger)

# Register ALL blueprints
app.register_blueprint(status_bp)
app.register_blueprint(temperature_bp)
app.register_blueprint(lamps_bp)
app.register_blueprint(logs_bp)
app.register_blueprint(mode_bp)
app.register_blueprint(curves_bp)
app.register_blueprint(costs_bp)
app.register_blueprint(dehumidifier_bp)
app.register_blueprint(camera_bp)
```

---

### Phase 5: Doppelte Routes entfernen

**ZU LÖSCHEN aus api.py:**

| Zeilen | Route | Ersetzt durch |
|--------|-------|---------------|
| 414-447 | /api/status | status_bp |
| 450-502 | /api/lamp/<ch> | lamps_bp |
| 505-523 | /api/temperature | temperature_bp |
| 530-648 | /api/logs/* | logs_bp |
| 654-814 | /api/curves/* | curves_bp |
| 840-902 | /api/mode | mode_bp |
| 930-1065 | /api/camera/* | camera_bp |
| 1071-1082 | /api/health | status_bp |

**Geschätzte Ersparnis:** ~700 Zeilen

---

### Phase 6: Helper Functions konsolidieren

**Problem:** `read_dht22()` existiert zweimal:
- api.py (Zeile 297-333)
- temperature_bp.py (Zeile 62-97)

**Lösung:**
1. Funktion in `dependencies.py` oder eigene `sensors.py` verschieben
2. Von beiden Stellen importieren

---

## Reihenfolge der Umsetzung

```
1. [x] Bugfix deployen (dehumidifier_controller.set_humidity_reader)
2. [ ] camera_bp.py erstellen
3. [ ] dependencies.py aktivieren
4. [ ] Alle Blueprints registrieren
5. [ ] Camera-Routes aus api.py entfernen (Test!)
6. [ ] Curves-Routes aus api.py entfernen (Test!)
7. [ ] Mode-Routes aus api.py entfernen (Test!)
8. [ ] Status/Health-Routes aus api.py entfernen (Test!)
9. [ ] Temperature-Route aus api.py entfernen (Test!)
10. [ ] Lamp-Routes aus api.py entfernen (Test!)
11. [ ] Logs-Routes aus api.py entfernen (Test!)
12. [ ] read_dht22() konsolidieren
13. [ ] Finale Tests aller Endpoints
```

---

## Risiko-Minimierung

### Nach JEDEM Schritt:
1. Service neu starten
2. Health-Check: `curl http://192.168.0.86:5000/api/health`
3. Betroffene Endpoints testen
4. Bei Fehler: Rollback auf vorherigen Stand

### Rollback-Plan:
```bash
# Bei Problemen:
cp api.py.backup.20251207 api.py
sudo systemctl restart grow-pi
```

---

## Erwartetes Ergebnis

| Metrik | Vorher | Nachher |
|--------|--------|---------|
| api.py Zeilen | 1119 | ~200 |
| Duplizierter Code | ~700 Zeilen | 0 |
| Registrierte Blueprints | 3 | 9 |
| Wartbarkeit | Schlecht | Gut |

---

## Zeitschätzung

| Phase | Dauer |
|-------|-------|
| Phase 2: camera_bp.py | 15 min |
| Phase 3: dependencies.py | 10 min |
| Phase 4: Blueprint-Registrierung | 10 min |
| Phase 5: Routes entfernen | 30 min |
| Phase 6: Helper konsolidieren | 15 min |
| Testen | 30 min |
| **GESAMT** | **~2 Stunden** |

---

## Genehmigung erforderlich

**Bitte bestätige:**
- [ ] Plan verstanden
- [ ] Zeitfenster für Refactoring (System ggf. kurz offline)
- [ ] Bereit zum Starten

---

*Dieser Plan wurde erstellt basierend auf der Opus-Agent Analyse.*
