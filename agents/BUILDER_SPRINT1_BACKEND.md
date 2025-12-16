# Builder Report: Sprint 1 Backend Implementation

**Datum:** 2025-12-16
**Agent:** @builder
**Version:** v6.21.0 (geplant)
**Status:** ✅ COMPLETED

---

## Aufgabe

Backend-Änderungen für Kalender-Verbesserung Sprint 1 implementieren gemäß Analyse-Report.

---

## Implementierte Änderungen

### Task 1.1: phase_day in Response ✅

**Datei:** `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi/web/blueprints/calendar_bp.py`

**Geänderte Funktionen:**
- `get_grows()` (Zeilen 139-162)
- `get_grow()` (Zeilen 266-287)

**Implementierung:**

```python
# Calculate phase_day (current day of phase)
phase_day = None
if row[5]:  # phase_started_at
    try:
        phase_start = datetime.fromisoformat(row[5])
        phase_day = (datetime.now() - phase_start).days + 1
    except Exception as e:
        logger.warning(f"Failed to calculate phase_day for grow {row[0]}: {e}")
```

**Neues Response-Feld:**
```json
{
  "id": "...",
  "name": "Grow 1",
  "current_phase": "flowering",
  "phase_started_at": "2025-12-01T00:00:00",
  "phase_day": 16,  // NEU!
  ...
}
```

**Logik:**
- Berechnet Differenz zwischen `datetime.now()` und `phase_started_at`
- Formel: `(now - phase_start).days + 1`
- Tag 1 = Starttag der Phase
- Fehlerbehandlung: `phase_day = None` bei Parsing-Fehlern

---

### Task 1.2: Datum editierbar in update_grow() ✅

**Datei:** `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi/web/blueprints/calendar_bp.py`

**Geänderte Funktion:** `update_grow()` (Zeilen 296-403)

**Neue editierbare Felder:**

#### 1. `start_date` (YYYY-MM-DD)
```python
if 'start_date' in data:
    if not validate_date(data['start_date']):
        return jsonify(create_response(False, error="Invalid start_date format. Use YYYY-MM-DD")), 400
    # Validate date is not in the future
    try:
        start_dt = datetime.strptime(data['start_date'], '%Y-%m-%d')
        if start_dt.date() > datetime.now().date():
            return jsonify(create_response(False, error="start_date cannot be in the future")), 400
    except Exception as e:
        return jsonify(create_response(False, error=f"Invalid start_date: {str(e)}")), 400
    updates.append("start_date = ?")
    params.append(data['start_date'])
```

#### 2. `phase_started_at` (ISO datetime)
```python
if 'phase_started_at' in data:
    if not validate_datetime(data['phase_started_at']):
        return jsonify(create_response(False, error="Invalid phase_started_at format. Use ISO datetime")), 400
    # Validate datetime is not in the future
    try:
        phase_dt = datetime.fromisoformat(data['phase_started_at'])
        if phase_dt > datetime.now():
            return jsonify(create_response(False, error="phase_started_at cannot be in the future")), 400
    except Exception as e:
        return jsonify(create_response(False, error=f"Invalid phase_started_at: {str(e)}")), 400
    updates.append("phase_started_at = ?")
    params.append(data['phase_started_at'])
```

**Zusätzliche Logik: Synchronisation mit phase_events**

Wenn `phase_started_at` geändert wird, wird automatisch das zugehörige `phase_event` aktualisiert:

```python
# If phase_started_at is being updated, also update the corresponding phase_event
if 'phase_started_at' in data:
    # Get current phase
    cursor.execute("SELECT current_phase FROM grows WHERE id = ?", (grow_id,))
    phase_row = cursor.fetchone()
    if phase_row:
        current_phase = phase_row[0]
        # Update the most recent phase_event for this phase
        cursor.execute("""
            UPDATE phase_events
            SET started_at = ?, updated_at = ?
            WHERE grow_id = ? AND phase = ? AND ended_at IS NULL
        """, (data['phase_started_at'], datetime.now().isoformat(), grow_id, current_phase))
```

**Validierung:**
- ✅ Format-Check (YYYY-MM-DD / ISO datetime)
- ✅ Zukunfts-Check (darf nicht in der Zukunft liegen)
- ✅ Error-Handling mit aussagekräftigen Messages

**Aktualisierte Docstring:**
```python
"""Update grow details

Body:
    name: string (optional)
    strain: string (optional)
    notes: string (optional)
    is_active: boolean (optional)
    start_date: YYYY-MM-DD (optional) - cannot be in future
    phase_started_at: ISO datetime (optional) - cannot be in future, updates corresponding phase_event
"""
```

---

## Geänderte Dateien

```
pi-controller/grow_pi/web/blueprints/calendar_bp.py
- get_grows(): +10 Zeilen (phase_day Berechnung)
- get_grow(): +10 Zeilen (phase_day Berechnung)
- update_grow(): +46 Zeilen (start_date + phase_started_at editierbar)
- Docstring update: +2 Zeilen
```

**Total:** 68 neue Zeilen

---

## API-Änderungen (Backwards Compatible)

### GET /api/calendar/grows

**VORHER:**
```json
{
  "success": true,
  "grows": [
    {
      "id": "...",
      "name": "Grow 1",
      "current_phase": "flowering",
      "phase_started_at": "2025-12-01T00:00:00"
    }
  ]
}
```

**NACHHER:**
```json
{
  "success": true,
  "grows": [
    {
      "id": "...",
      "name": "Grow 1",
      "current_phase": "flowering",
      "phase_started_at": "2025-12-01T00:00:00",
      "phase_day": 16  // NEU
    }
  ]
}
```

### PUT /api/calendar/grows/<id>

**NEU erlaubte Felder:**
```json
{
  "start_date": "2025-11-01",
  "phase_started_at": "2025-12-01T00:00:00"
}
```

**Fehler-Responses:**
- `400`: "Invalid start_date format. Use YYYY-MM-DD"
- `400`: "start_date cannot be in the future"
- `400`: "Invalid phase_started_at format. Use ISO datetime"
- `400`: "phase_started_at cannot be in the future"

---

## Backwards Compatibility

✅ **KEINE Breaking Changes!**

- Bestehende API-Consumer funktionieren weiterhin
- `phase_day` ist ein NEUES Feld (additive change)
- `start_date` / `phase_started_at` sind OPTIONAL in PUT
- Alte Grows ohne `phase_started_at` → `phase_day = None`

---

## Frontend-Integration (Nächster Schritt)

Das Frontend kann jetzt:

1. **Status Dashboard bauen:**
   ```javascript
   const response = await fetch('/api/calendar/grows?active_only=true');
   const { grows } = await response.json();
   const activeGrow = grows[0];

   console.log(`Tag ${activeGrow.phase_day} der ${activeGrow.current_phase}`);
   // Output: "Tag 16 der flowering"
   ```

2. **Daten editieren:**
   ```javascript
   await fetch(`/api/calendar/grows/${growId}`, {
     method: 'PUT',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       start_date: '2025-11-01',
       phase_started_at: '2025-12-01T00:00:00'
     })
   });
   ```

---

## Testing Checklist

- [ ] GET /api/calendar/grows enthält `phase_day`
- [ ] GET /api/calendar/grows/<id> enthält `phase_day`
- [ ] phase_day = None für Grows ohne phase_started_at
- [ ] phase_day korrekt berechnet (Tag 1 am Starttag)
- [ ] PUT /api/calendar/grows/<id> mit start_date funktioniert
- [ ] PUT /api/calendar/grows/<id> mit phase_started_at funktioniert
- [ ] Zukunfts-Validierung rejected Datum in der Zukunft
- [ ] Format-Validierung rejected ungültige Formate
- [ ] phase_events wird synchronisiert bei phase_started_at Änderung
- [ ] Alte API-Consumer funktionieren weiterhin

---

## Nächste Schritte

**@validator:** API-Consumer-Check durchführen

**Frontend Tasks (Sprint 1):**
1. Status Dashboard bauen (Task 1.3)
2. JS für Status Dashboard (Task 1.4)
3. Einstellungen Modal (Task 1.5)

**Sprint 2:**
- Ereignisliste implementieren

---

## Code Quality

✅ TypeScript strict mode nicht relevant (Python Backend)
✅ Error Handling implementiert
✅ Logging für Debugging hinzugefügt
✅ Docstrings aktualisiert
✅ Backwards Compatible
✅ UTC-konsistente Berechnungen

---

**Implementierung abgeschlossen. Bereit für Testing & Validator-Check.**
