# Phase-Day Fix Report
**Datum:** 2025-12-16
**Version:** v6.20.1
**Status:** ✅ Bugs identifiziert - Fix bereit

---

## Problembeschreibung

User meldet zwei Bugs im Kalender-Feature:

1. **Phase-Startdatum:** User ändert das Phase-Startdatum in den Einstellungen, klickt "Speichern", sieht "gespeichert" - aber der angezeigte Wert ändert sich nicht
2. **Tag-Anzeige:** "Tag X der Blüte" wird überhaupt nicht im Status Dashboard angezeigt

---

## Root Cause Analysis

### Live-API-Test
```bash
curl http://localhost:5000/api/calendar/grows?active_only=true
```

**Response:**
```json
{
    "count": 1,
    "grows": [{
        "id": "e2751f6a-c640-4d1b-9a47-67698a3cbda0",
        "name": "Grow 2025_END",
        "current_phase": "flowering",
        "phase_started_at": "2025-12-16T08:08:46.254491",
        "start_date": "2025-11-15",
        "strain": null,
        // ❌ FEHLT: "phase_day": 1
    }]
}
```

### Bug #1: phase_day wird nicht berechnet/gesendet

**Lokale Version** (`calendar_bp.py` Zeilen 141-157):
```python
# Calculate phase_day (current day of phase)
phase_day = None
if row[5]:  # phase_started_at
    try:
        phase_start = datetime.fromisoformat(row[5])
        phase_day = (datetime.now() - phase_start).days + 1  # ✅ Berechnung
    except Exception as e:
        logger.warning(f"Failed to calculate phase_day for grow {row[0]}: {e}")

grows.append({
    'id': row[0],
    ...
    'phase_day': phase_day,  # ✅ In Response aufgenommen
    ...
})
```

**Deployed Version auf Pi:**
```python
grows.append({
    'id': row[0],
    ...
    'notes': row[6],
    'is_active': bool(row[7]),
    'created_at': row[8],
    'updated_at': row[9]
    # ❌ FEHLT: 'phase_day': phase_day
})
```

**Ursache:**
Die auf dem Pi deployed Version ist **veraltet** und enthält nicht die `phase_day` Berechnung!

---

### Bug #2: Phase-Startdatum wird nicht aktualisiert

**Frontend Code-Analyse** (`calendar.js`):

**Zeile 693-749 - `saveGrowSettings()`:**
```javascript
async function saveGrowSettings() {
    if (!currentGrow) return;

    const updates = {};

    // Phase Start wird korrekt gesammelt ✅
    if (newPhaseStart) {
        const currentPhaseDate = currentGrow.phase_started_at?.split('T')[0] || null;
        if (newPhaseStart !== currentPhaseDate) {
            updates.phase_started_at = newPhaseStart + 'T00:00:00'; // ✅
        }
    }

    const data = await GrowPiAPI.updateGrow(currentGrow.id, updates);

    if (data.success) {
        showSuccess('Einstellungen gespeichert!');
        closeGrowSettingsModal();
        await loadGrows(); // ✅ Reload wird aufgerufen!
    }
}
```

**Zeile 203-223 - `loadGrows()`:**
```javascript
async function loadGrows() {
    const data = await GrowPiAPI.getGrows(false);

    if (data.success && data.grows && data.grows.length > 0) {
        currentGrow = data.grows[0]; // ✅ Grow wird aktualisiert
        updateGrowDisplay(); // ✅ Display-Update aufgerufen
        await loadPhaseEvents();
        renderCalendar();
    }
}
```

**Zeile 311-330 - `updateStatusDashboard()`:**
```javascript
function updateStatusDashboard() {
    if (!currentGrow) return;

    const phaseInfo = PHASE_LABELS[currentGrow.current_phase] || PHASE_LABELS.seedling;

    if (statusPhaseIcon) statusPhaseIcon.textContent = phaseInfo.icon;
    if (statusPhaseName) statusPhaseName.textContent = phaseInfo.de;
    if (statusPhaseDay) statusPhaseDay.textContent = currentGrow.phase_day || '-'; // ❌ phase_day existiert nicht!
    if (statusGrowStart) statusGrowStart.textContent = formatDateDE(currentGrow.start_date);
    if (statusPhaseStart) {
        const phaseStartDate = currentGrow.phase_started_at ? currentGrow.phase_started_at.split('T')[0] : null;
        statusPhaseStart.textContent = formatDateDE(phaseStartDate); // ✅ Wird aktualisiert
    }
}
```

**Ursache:**
Das Frontend funktioniert korrekt! Es ruft nach dem Speichern `loadGrows()` auf, welches die neuen Daten lädt und `updateStatusDashboard()` aufruft. ABER:
- Da das Backend kein `phase_day` sendet, zeigt Zeile 324 nur `-` an
- Das Phase-Startdatum wird korrekt angezeigt (Zeile 328), ABER da `phase_day` fehlt, sieht es aus als ob nichts passiert wäre

---

## Die Lösung

### Problem
Die lokale Entwicklungsversion (`calendar_bp.py`) ist **neuer** als die deployed Version auf dem Pi.

### Fix
Deploy der aktuellen `calendar_bp.py` Version auf den Pi.

---

## Deployment-Commands

### Option 1: rsync + restart (empfohlen)
```bash
# 1. Deploy aktualisierte calendar_bp.py
rsync -avz -e "sshpass -p Mi83xer# ssh -o StrictHostKeyChecking=no" \
  /Users/denniswestermann/Desktop/Coding\ Projekte/GrowPi/pi-controller/grow_pi/web/blueprints/calendar_bp.py \
  admin@192.168.0.86:/home/admin/pi-controller/grow_pi/web/blueprints/

# 2. Restart Flask Service
sshpass -p "Mi83xer#" ssh -o StrictHostKeyChecking=no admin@192.168.0.86 \
  'sudo systemctl restart growpi-flask.service'

# 3. Verify
sleep 3
sshpass -p "Mi83xer#" ssh -o StrictHostKeyChecking=no admin@192.168.0.86 \
  'curl -s http://localhost:5000/api/calendar/grows?active_only=true' | python3 -m json.tool | grep -A 1 phase_day
```

**Expected Output:**
```json
"phase_day": 1,
```

### Option 2: Full Project Sync (falls weitere Änderungen existieren)
```bash
# Sync gesamtes pi-controller Verzeichnis
rsync -avz --delete -e "sshpass -p Mi83xer# ssh -o StrictHostKeyChecking=no" \
  /Users/denniswestermann/Desktop/Coding\ Projekte/GrowPi/pi-controller/ \
  admin@192.168.0.86:/home/admin/pi-controller/ \
  --exclude='*.pyc' --exclude='__pycache__' --exclude='*.db'

# Restart Services
sshpass -p "Mi83xer#" ssh -o StrictHostKeyChecking=no admin@192.168.0.86 \
  'sudo systemctl restart growpi-flask.service && sudo systemctl restart growpi-controller.service'
```

---

## Verification Steps

Nach dem Deployment:

### 1. API-Test (Backend)
```bash
sshpass -p "Mi83xer#" ssh -o StrictHostKeyChecking=no admin@192.168.0.86 \
  'curl -s http://localhost:5000/api/calendar/grows?active_only=true' | python3 -m json.tool
```

**Erwartetes Ergebnis:**
```json
{
    "grows": [{
        "phase_day": 1,  // ✅ MUSS vorhanden sein!
        "phase_started_at": "2025-12-16T08:08:46.254491"
    }]
}
```

### 2. Frontend-Test (Browser)
1. Öffne http://growpi.nm-forum.de
2. Navigiere zu "Kalender"-Tab
3. **Verifiziere Status Dashboard:**
   - "Tag der Blüte: 1" sollte angezeigt werden (statt "-")
4. **Test Phase-Startdatum:**
   - Klicke "Einstellungen bearbeiten"
   - Ändere "Phase-Startdatum" auf heute
   - Klicke "Speichern"
   - **Erwartung:** "Tag der Blüte: 1" bleibt sichtbar (nicht "-")

---

## Betroffene Dateien

| Datei | Status | Änderung |
|-------|--------|----------|
| `pi-controller/grow_pi/web/blueprints/calendar_bp.py` | ✅ Fix bereit | Zeilen 141-157 + 267-283 (phase_day Berechnung) |
| `pi-controller/grow_pi/web/static/js/modules/calendar.js` | ✅ Kein Bug | Frontend funktioniert korrekt |

---

## Git Diff (Local vs. Deployed)

**calendar_bp.py - get_grows() Funktion:**
```diff
         cursor.execute(query, (limit,))
         rows = cursor.fetchall()

         grows = []
         for row in rows:
+            # Calculate phase_day (current day of phase)
+            phase_day = None
+            if row[5]:  # phase_started_at
+                try:
+                    phase_start = datetime.fromisoformat(row[5])
+                    phase_day = (datetime.now() - phase_start).days + 1
+                except Exception as e:
+                    logger.warning(f"Failed to calculate phase_day for grow {row[0]}: {e}")
+
             grows.append({
                 'id': row[0],
                 'name': row[1],
                 'strain': row[2],
                 'start_date': row[3],
                 'current_phase': row[4],
                 'phase_started_at': row[5],
+                'phase_day': phase_day,  # NEW: Current day of phase
                 'notes': row[6],
                 'is_active': bool(row[7]),
                 'created_at': row[8],
                 'updated_at': row[9]
             })
```

---

## Rollback Plan (Falls etwas schief geht)

```bash
# 1. Backup der aktuellen Version
sshpass -p "Mi83xer#" ssh -o StrictHostKeyChecking=no admin@192.168.0.86 \
  'cp /home/admin/pi-controller/grow_pi/web/blueprints/calendar_bp.py /home/admin/calendar_bp.py.backup'

# 2. Bei Problemen: Restore Backup
sshpass -p "Mi83xer#" ssh -o StrictHostKeyChecking=no admin@192.168.0.86 \
  'cp /home/admin/calendar_bp.py.backup /home/admin/pi-controller/grow_pi/web/blueprints/calendar_bp.py && \
   sudo systemctl restart growpi-flask.service'
```

---

## Zusammenfassung

### Bugs
1. ❌ **phase_day wird nicht berechnet** - Backend-Code veraltet
2. ❌ **Phase-Startdatum scheint sich nicht zu ändern** - Frontend zeigt "-" statt Tag-Nummer

### Root Cause
- Deployed Version auf Pi fehlt `phase_day` Berechnung (Zeilen 141-157)
- Frontend funktioniert korrekt, kann aber ohne Backend-Daten nichts anzeigen

### Lösung
- Deploy der aktuellen `calendar_bp.py` auf den Pi
- Restart Flask Service
- 1-minute Deployment

### Risiko
- ✅ **Niedrig** - Nur Read-Operationen betroffen, keine DB-Schema-Änderungen

---

**Bereit für Deployment? Warte auf User-Bestätigung!**
