# Calendar Improvement Analysis Report

**Datum:** 2025-12-16
**Agent:** @architect
**Version:** v6.21.0 (geplant)

---

## 1. IST-Zustand

### Backend (calendar_bp.py) - 90% vollständig
- ✅ Grows CRUD (GET, POST, PUT, DELETE)
- ✅ Phase Management (change_phase, timeline)
- ✅ Daily Logs (CRUD)
- ✅ Month View
- ✅ Milestones System (60 System-Events für alle Phasen)
- ❌ FEHLT: `phase_day` in GET-Response
- ❌ FEHLT: `start_date`/`phase_started_at` editierbar in PUT

### Frontend (calendar.js) - 40% vollständig
- ✅ Kalender-Grid mit Monatsansicht
- ✅ Daily Log Modal (Bewässerung, Düngung, Beobachtungen)
- ✅ Phase-Buttons (Keim, Wachstum, Blüte)
- ✅ Events als Dots im Kalender
- ❌ FEHLT: Status Dashboard oben
- ❌ FEHLT: Grow-Einstellungen Editor
- ❌ FEHLT: Ereignisliste (Milestones anzeigen/editieren)

### Datenbank-Schema - 100% vollständig
- `grows` - Grow-Zyklen
- `phase_events` - Phasen-Übergänge
- `daily_logs` - Tägliche Einträge
- `phase_milestones` - System + Custom Events

---

## 2. SOLL-Zustand (User-Anforderungen)

### 2.1 Status Dashboard (PRIORITY HIGH)
User will oben sehen:
- Aktuelle Phase (z.B. "🌸 Blüte")
- Aktueller Tag der Phase (z.B. "Tag 15")
- Fortschrittsbalken (optional)
- Start-Datum der Phase (z.B. "Blütestart: 01.12.2025")

### 2.2 Editierbare Grow-Einstellungen (PRIORITY HIGH)
User muss ändern können:
- Grow-Startdatum
- Phase-Startdatum (z.B. "Blüte begann am...")
- Grow-Name
- Sorte

### 2.3 Ereignisliste (PRIORITY HIGH)
User will sehen:
- Alle Milestones für aktuelle Phase
- Toggle: Ein/Aus für einzelne Events
- Custom Events hinzufügen/löschen
- Events mit Datum-Bezug ("Tag 15-21: Zweite Schwazze")

### 2.4 Phase Manual Override (PRIORITY MEDIUM)
User will setzen können:
- "Ich bin in Blüte"
- "Tag 1 der Blüte war am XX.XX.XXXX"
- System berechnet dann automatisch aktuellen Tag

---

## 3. GAP-Analyse

| Feature | Backend | Frontend | Aufwand |
|---------|---------|----------|---------|
| Status Dashboard | ⚠️ phase_day fehlt | ❌ Komplett fehlt | Medium |
| Grow-Einstellungen | ⚠️ PUT partial | ❌ Komplett fehlt | Medium |
| Ereignisliste | ✅ API ready | ❌ Komplett fehlt | Medium |
| Phase Override | ❌ Fehlt | ❌ Fehlt | High |

---

## 4. Implementierungsplan

### Sprint 1: Core Features (v6.21.0)

#### Task 1.1: Backend - phase_day in Response
**Datei:** `calendar_bp.py`
**Funktion:** `get_grows()` (Zeile 99-158)

Änderung: Bei jedem Grow `phase_day` berechnen und mitgeben:
```python
# Nach Zeile 151
phase_day = None
if row[5]:  # phase_started_at
    phase_start = datetime.fromisoformat(row[5])
    phase_day = (datetime.now() - phase_start).days + 1

grows.append({
    ...
    'phase_day': phase_day,  # NEU
})
```

#### Task 1.2: Backend - Datum editierbar
**Datei:** `calendar_bp.py`
**Funktion:** `update_grow()` (Zeile 276-340)

Änderung: `start_date` und `phase_started_at` erlauben:
```python
if 'start_date' in data:
    if not validate_date(data['start_date']):
        return jsonify(create_response(False, error="Invalid date")), 400
    updates.append("start_date = ?")
    params.append(data['start_date'])

if 'phase_started_at' in data:
    if not validate_datetime(data['phase_started_at']):
        return jsonify(create_response(False, error="Invalid datetime")), 400
    updates.append("phase_started_at = ?")
    params.append(data['phase_started_at'])
```

#### Task 1.3: Frontend - Status Dashboard
**Datei:** `index.html` (Calendar-Tab Section)

Neues HTML vor dem Calendar-Grid:
```html
<div class="grow-status-dashboard">
    <div class="status-phase">
        <span class="phase-icon" id="statusPhaseIcon">🌸</span>
        <span class="phase-name" id="statusPhaseName">Blüte</span>
    </div>
    <div class="status-day">
        <span class="day-label">Tag</span>
        <span class="day-number" id="statusPhaseDay">15</span>
    </div>
    <div class="status-dates">
        <div class="date-row">
            <span class="date-label">Grow-Start:</span>
            <span class="date-value" id="statusGrowStart">01.11.2025</span>
            <button class="edit-btn" id="btnEditGrowStart">✏️</button>
        </div>
        <div class="date-row">
            <span class="date-label">Phase-Start:</span>
            <span class="date-value" id="statusPhaseStart">01.12.2025</span>
            <button class="edit-btn" id="btnEditPhaseStart">✏️</button>
        </div>
    </div>
</div>
```

#### Task 1.4: Frontend - JS für Status Dashboard
**Datei:** `calendar.js`

Neue Funktion:
```javascript
function updateStatusDashboard() {
    if (!currentGrow) return;

    const phaseInfo = PHASE_LABELS[currentGrow.current_phase];
    document.getElementById('statusPhaseIcon').textContent = phaseInfo.icon;
    document.getElementById('statusPhaseName').textContent = phaseInfo.de;
    document.getElementById('statusPhaseDay').textContent = currentGrow.phase_day || '?';
    document.getElementById('statusGrowStart').textContent = formatDateDE(currentGrow.start_date);
    document.getElementById('statusPhaseStart').textContent = formatDateDE(currentGrow.phase_started_at);
}
```

#### Task 1.5: Frontend - Einstellungen Modal
**Datei:** `calendar.js`

Neue Funktion für Datum-Editierung:
```javascript
async function openGrowSettingsModal() {
    // Modal mit Date-Pickern für start_date und phase_started_at
}

async function saveGrowSettings(newStartDate, newPhaseStartedAt) {
    const data = await GrowPiAPI.updateGrow(currentGrow.id, {
        start_date: newStartDate,
        phase_started_at: newPhaseStartedAt
    });
    if (data.success) {
        showSuccess('Einstellungen gespeichert!');
        await loadGrows();
    }
}
```

### Sprint 2: Ereignisliste (v6.21.1)

#### Task 2.1: Frontend - Ereignisliste Section
Neue Section unter Status Dashboard mit:
- Liste aller Milestones für aktuelle Phase
- Day-Range anzeigen ("Tag 15-21")
- Toggle-Switches für Enable/Disable
- "Hinzufügen" Button für Custom Events

#### Task 2.2: API-Integration
- `GET /api/calendar/milestones?phase={phase}` aufrufen
- `PATCH /api/calendar/milestones/{id}/toggle` für Toggle
- `POST /api/calendar/milestones` für neue Events

---

## 5. CSS-Änderungen (calendar.css)

```css
/* Status Dashboard */
.grow-status-dashboard {
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 20px;
    background: rgba(20, 20, 20, 0.9);
    border-radius: 12px;
    padding: 20px;
    border: 1px solid #2a2a2a;
    margin-bottom: 20px;
    align-items: center;
}

.status-day .day-number {
    font-size: 48px;
    font-weight: 700;
    color: #11ff55;
    line-height: 1;
}

.status-dates .edit-btn {
    background: none;
    border: none;
    cursor: pointer;
    opacity: 0.5;
    transition: opacity 0.2s;
}

.status-dates .edit-btn:hover {
    opacity: 1;
}
```

---

## 6. Risiken & Hinweise

1. **Phase-Day Berechnung:** Backend sollte UTC nutzen für Konsistenz
2. **Date-Picker:** Native HTML5 `<input type="date">` nutzen
3. **Backwards Compatibility:** Alte Grows ohne phase_day müssen funktionieren
4. **Validierung:** Datum darf nicht in der Zukunft liegen

---

## 7. Test-Checkliste

- [ ] phase_day wird korrekt berechnet (Backend)
- [ ] Status Dashboard zeigt korrekten Tag
- [ ] Grow-Start editierbar
- [ ] Phase-Start editierbar
- [ ] Ereignisliste lädt
- [ ] Toggle funktioniert
- [ ] Custom Event hinzufügen funktioniert
- [ ] Mobile-Responsive

---

**Nächster Schritt:** @builder mit Sprint 1 Tasks beauftragen
