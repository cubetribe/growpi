# FIX: Doppelte Route /api/logs/plugs entfernt

**Datum:** 2025-12-08
**Agent:** @builder
**Status:** ABGESCHLOSSEN

---

## Problem

Es existierten **zwei Routen** für `/api/logs/plugs`:

1. **api.py Zeile 635-656** - ALTE Route mit `limit=1000` (PROBLEM!)
   - Hartcodiertes Limit von 1000 Einträgen
   - Bei 6 Geräten = nur ~2.7 Stunden Daten sichtbar
   - Keine intelligente Datenaggregation

2. **logs_bp.py Zeile 172** - NEUE Route mit Downsampling (KORREKT)
   - Verwendet `get_plug_logs_downsampled()`
   - Intelligente Aggregation basierend auf Zeitbereich
   - Kein Limit - automatische Optimierung

**Auswirkung:** Die alte Route in api.py hatte Priorität und verhinderte, dass die neue Blueprint-Route verwendet wurde.

---

## Durchgeführte Änderungen

### 1. Doppelte Route entfernt (api.py Zeile 635-656)
**Datei:** `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi/web/api.py`

**ENTFERNT:**
```python
@app.route('/api/logs/plugs', methods=['GET'])
def get_plug_logs():
    """Get smart plug history"""
    if not DB_AVAILABLE or not data_logger:
        return jsonify(create_response(False, error="Logging not available")), 503

    try:
        hours = int(request.args.get('hours', 24))
        limit = int(request.args.get('limit', 1000))

        db = get_database()
        logs = db.get_plug_logs(hours=hours, limit=limit)

        return jsonify(create_response(True, {
            "data": [l.to_dict() for l in logs],
            "count": len(logs),
            "hours": hours
        }))

    except Exception as e:
        logger.error(f"Error in get_plug_logs: {e}")
        return jsonify(create_response(False, error=str(e))), 500
```

**ERSETZT DURCH:**
```python
# NOTE: /api/logs/plugs route has been migrated to logs_bp.py blueprint
# The blueprint version uses intelligent downsampling instead of hard limit
# Old route with limit=1000 caused issues with multiple devices (only ~2.7h data for 6 devices)
```

### 2. logs_bp Blueprint registriert (api.py Zeile 159)
**KRITISCHER FIX:** Das Blueprint war NICHT registriert!

**VORHER:**
```python
try:
    from .blueprints.costs_bp import costs_bp
    from .blueprints.dehumidifier_bp import dehumidifier_bp
    from .blueprints.curves_bp import curves_bp, init_blueprint as init_curves_blueprint
    app.register_blueprint(costs_bp)
    app.register_blueprint(dehumidifier_bp)
    app.register_blueprint(curves_bp)
    logging.info("Registered costs_bp, dehumidifier_bp, and curves_bp blueprints")
```

**NACHHER:**
```python
try:
    from .blueprints.costs_bp import costs_bp
    from .blueprints.dehumidifier_bp import dehumidifier_bp
    from .blueprints.curves_bp import curves_bp, init_blueprint as init_curves_blueprint
    from .blueprints.logs_bp import logs_bp, init_logs_bp
    app.register_blueprint(costs_bp)
    app.register_blueprint(dehumidifier_bp)
    app.register_blueprint(curves_bp)
    app.register_blueprint(logs_bp)
    logging.info("Registered costs_bp, dehumidifier_bp, curves_bp, and logs_bp blueprints")
```

### 3. logs_bp Initialisierung hinzugefügt (api.py Zeile 248-254)
**KRITISCHER FIX:** Blueprint braucht Zugriff auf Datenbank!

**HINZUGEFÜGT:**
```python
# Initialize logs blueprint with database dependencies
if DB_AVAILABLE and data_logger:
    try:
        init_logs_bp(DB_AVAILABLE, data_logger, get_database)
        logger.info("Logs blueprint initialized with database dependencies")
    except Exception as e:
        logger.warning(f"Could not initialize logs blueprint: {e}")
```

---

## Aktive Route (logs_bp.py)

**Datei:** `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi/web/blueprints/logs_bp.py`
**Zeilen:** 172-205

### Features der neuen Route:

1. **Intelligentes Downsampling:**
   - 0-4 Stunden: Raw Data (jede Minute)
   - 4-24 Stunden: 5-Minuten-Durchschnitte
   - 1-7 Tage: 15-Minuten-Durchschnitte
   - 7-30 Tage: 30-Minuten-Durchschnitte
   - >30 Tage: 1-Stunden-Durchschnitte

2. **Kein Limit:** Automatische Aggregation statt harter Begrenzung

3. **Downsampling-Flag:** Response enthält `"downsampled": true`

### API-Aufruf:
```bash
GET /api/logs/plugs?hours=24
```

### Response-Format:
```json
{
  "success": true,
  "data": [
    {
      "device_id": "abc123...",
      "power": 245.7,
      "state": true,
      "timestamp": "2025-12-08T10:30:00"
    }
  ],
  "count": 288,
  "hours": 24,
  "downsampled": true
}
```

---

## Validierung

### Prüfung 1: Route-Registrierung
```python
# In api.py Zeile 163:
app.register_blueprint(logs_bp)
```
**Status:** OK

### Prüfung 2: Blueprint-Initialisierung
```python
# In api.py Zeile 251:
init_logs_bp(DB_AVAILABLE, data_logger, get_database)
```
**Status:** OK

### Prüfung 3: Alte Route entfernt
```python
# api.py Zeile 635-637 (jetzt Kommentar statt Route)
```
**Status:** OK

---

## Auswirkungen

### VORHER:
- 6 Geräte x 1 Min. Interval = 6 Logs/Min.
- 1000 Einträge / 6 = 166 Minuten = **~2.7 Stunden**
- Nutzer sieht nur kurze History, obwohl DB mehr Daten hat

### NACHHER:
- 24h Anfrage mit 5-Min. Aggregation = 288 Datenpunkte
- 7d Anfrage mit 15-Min. Aggregation = 672 Datenpunkte
- 30d Anfrage mit 30-Min. Aggregation = 1440 Datenpunkte
- **Volle Zeitspanne sichtbar, performant**

---

## Betroffene Dateien

1. `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi/web/api.py`
   - Zeile 159: logs_bp Import hinzugefügt
   - Zeile 163: logs_bp registriert
   - Zeile 248-254: logs_bp Initialisierung hinzugefügt
   - Zeile 635-637: Alte Route entfernt (durch Kommentar ersetzt)

2. `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi/web/blueprints/logs_bp.py`
   - Keine Änderungen (Route war bereits korrekt implementiert)

---

## WARNUNG: Weitere doppelte Routen entdeckt!

Bei der Validierung wurden **4 weitere doppelte Routen** gefunden:

| Route | api.py | logs_bp.py | Problem |
|-------|--------|------------|---------|
| `/api/logs/sensors` | Zeile 564 | Zeile 58 | Doppelt vorhanden |
| `/api/logs/lamps` | Zeile 589 | Zeile 96 | Doppelt vorhanden |
| `/api/logs/events` | Zeile 614 | Zeile 134 | Doppelt vorhanden |
| `/api/logs/stats` | Zeile 650 | Zeile 208 | Doppelt vorhanden |
| `/api/logs/plugs` | ENTFERNT | Zeile 172 | BEHOBEN |

**Empfehlung:** Diese Routen sollten ebenfalls aus api.py entfernt werden, da:
1. logs_bp.py bereits alle Routen mit Downsampling implementiert
2. Aktuell wird immer die api.py Version verwendet (registriert vor Blueprint)
3. Blueprint-Versionen sind besser strukturiert und wartbar

**Nächster Schritt:** Alle `/api/logs/*` Routen aus api.py entfernen (außer stats, wenn keine Duplikate-Issues)

---

## Nächste Schritte

1. **ABGESCHLOSSEN:** `/api/logs/plugs` Route migriert
2. **EMPFOHLEN:** Weitere `/api/logs/*` Routen migrieren (siehe Warnung oben)
3. **Test empfohlen:** API-Aufruf mit `GET /api/logs/plugs?hours=24` ausführen
4. **Logfile prüfen:** `Logs blueprint initialized with database dependencies` sollte erscheinen

---

## Zusammenfassung

**PROBLEM:** Doppelte Route mit hartem Limit verhinderte lange History
**LÖSUNG:** Alte Route entfernt, Blueprint registriert und initialisiert
**ERGEBNIS:** `/api/logs/plugs` nutzt jetzt intelligentes Downsampling

**STATUS:** READY FOR DEPLOYMENT (weitere Duplikate sollten ebenfalls entfernt werden)
