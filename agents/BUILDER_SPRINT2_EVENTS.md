# Builder Report - Sprint 2: Ereignisliste (Milestones)

**Agent**: @builder
**Datum**: 2025-12-16
**Task**: Implementierung der Ereignisliste für den Kalender-Tab
**Status**: ✅ **ABGESCHLOSSEN**

---

## Executive Summary

Die **Ereignisliste (Milestones)** wurde erfolgreich in den Kalender-Tab integriert. User können nun:
- Alle Milestones für die aktuelle Phase anzeigen
- Events per Toggle Ein-/Ausschalten
- Eigene Custom Events erstellen
- Custom Events wieder löschen
- System-Events sind schreibgeschützt

---

## Implementierte Features

### 1. Events Section (HTML)
**Datei**: `pi-controller/grow_pi/web/static/index.html`

✅ Neue Section zwischen Status Dashboard und Calendar Grid:
```html
<div class="events-section" id="eventsSection">
    <div class="events-header">
        <h3 class="events-title">📅 Ereignisse für <span id="eventsPhaseLabel">-</span></h3>
        <button class="btn-small" id="btnAddEvent">+ Neues Event</button>
    </div>
    <div class="events-list" id="eventsList">
        <div class="events-loading">Lade Ereignisse...</div>
    </div>
</div>
```

✅ Add Event Modal:
- Titel (required)
- Beschreibung (optional)
- Tag-Range (day_offset_min bis day_offset_max)
- Icon (optional)

---

### 2. JavaScript Funktionalität
**Datei**: `pi-controller/grow_pi/web/static/js/modules/calendar.js`

#### 2.1 DOM-Referenzen
```javascript
const eventsSection = document.getElementById('eventsSection');
const eventsPhaseLabel = document.getElementById('eventsPhaseLabel');
const eventsList = document.getElementById('eventsList');
const btnAddEvent = document.getElementById('btnAddEvent');
```

#### 2.2 State Management
```javascript
let currentPhaseEvents = []; // Events für aktuelle Phase
```

#### 2.3 Core Functions

**loadPhaseEvents()**
- Lädt alle Milestones für `currentGrow.current_phase`
- API: `GET /api/calendar/milestones?phase={phase}`
- Error Handling mit Fallback-UI

**renderEventsList()**
- Rendert Liste aller Events mit:
  - Toggle Switch (Enable/Disable)
  - Icon + Titel + Tag-Badge
  - Beschreibung (wenn vorhanden)
  - Delete-Button (nur bei Custom Events)
- Category-basierte Border-Colors:
  - Training: Blue (`#3b82f6`)
  - Environment: Green (`#22c55e`)
  - Nutrients: Orange (`#f97316`)
  - Observation: Purple (`#a855f7`)
  - Harvest: Red (`#ef4444`)

**window.toggleEvent(eventId, enabled)** (Global)
- Toggle Event Enable-State
- API: `PATCH /api/calendar/milestones/{id}/toggle`
- Optimistic UI Update

**window.deleteEvent(eventId)** (Global)
- Löscht Custom Event mit Confirm-Dialog
- API: `DELETE /api/calendar/milestones/{id}`
- System-Events sind geschützt (kein Delete-Button)

#### 2.4 Add Event Modal

**openAddEventModal()**
- Pre-Fill mit `currentGrow.phase_day`
- Reset Form

**saveNewEvent()**
- Validierung: Titel + day_offset_min required
- API: `POST /api/calendar/milestones`
- Payload:
  ```javascript
  {
      phase: currentGrow.current_phase,
      day_offset_min: dayMin,
      day_offset_max: dayMax || null,
      title: title,
      description: description || null,
      icon: icon || '📌',
      category: 'observation'
  }
  ```

---

### 3. API Extensions
**Datei**: `pi-controller/grow_pi/web/static/js/api.js`

✅ Neue Methoden hinzugefügt:

```javascript
async createMilestone(data) {
    return await post('/api/calendar/milestones', data);
}

async deleteMilestone(id) {
    return await request(`/api/calendar/milestones/${id}`, { method: 'DELETE' });
}
```

Bereits vorhanden:
- `getMilestones(phase)` ✅
- `toggleMilestone(id, enabled)` ✅

---

### 4. CSS Styling
**Datei**: `pi-controller/grow_pi/web/static/css/calendar.css`

#### 4.1 Events Section
```css
.events-section {
    background: rgba(20, 20, 20, 0.9);
    border-radius: 12px;
    padding: 16px;
    border: 1px solid #2a2a2a;
    margin-bottom: 20px;
}

.events-list {
    max-height: 300px;
    overflow-y: auto;
}
```

#### 4.2 Event Items
```css
.event-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 8px;
    border-left: 3px solid #666;
}

.event-item.disabled {
    opacity: 0.5;
}
```

Category-Colors:
- `.event-item.training { border-left-color: #3b82f6; }`
- `.event-item.environment { border-left-color: #22c55e; }`
- `.event-item.nutrients { border-left-color: #f97316; }`
- `.event-item.observation { border-left-color: #a855f7; }`
- `.event-item.harvest { border-left-color: #ef4444; }`

#### 4.3 Toggle Switch
```css
.toggle-switch {
    width: 36px;
    height: 20px;
}

.toggle-switch input:checked + .toggle-slider {
    background-color: rgba(17, 255, 85, 0.3);
}

.toggle-switch input:checked + .toggle-slider:before {
    transform: translateX(16px);
    background-color: #11ff55;
}
```

#### 4.4 Event Day Badge
```css
.event-day-badge {
    font-size: 11px;
    padding: 2px 8px;
    background: rgba(17, 255, 85, 0.15);
    border: 1px solid rgba(17, 255, 85, 0.3);
    border-radius: 10px;
    color: #11ff55;
}
```

#### 4.5 Responsive Design
- Mobile: `max-height: 200px` für Events-Liste
- Event-Header-Row: Column-Layout auf Mobile

---

## Integration Flow

### Initial Load
```
1. initCalendarTab()
2. loadGrows()
3. currentGrow = data.grows[0]
4. loadPhaseEvents()  ← NEU!
5. renderEventsList()
6. renderCalendar()
```

### User Interactions

**Event Toggle**:
```
User klickt Toggle
  → window.toggleEvent(id, enabled)
  → API PATCH /api/calendar/milestones/{id}/toggle
  → Update local state
  → renderEventsList()
```

**Custom Event erstellen**:
```
User klickt "+ Neues Event"
  → openAddEventModal()
  → User füllt Form aus
  → User klickt "Speichern"
  → saveNewEvent()
  → API POST /api/calendar/milestones
  → loadPhaseEvents()  (Reload komplette Liste)
  → renderEventsList()
```

**Custom Event löschen**:
```
User klickt 🗑️
  → Confirm Dialog
  → window.deleteEvent(id)
  → API DELETE /api/calendar/milestones/{id}
  → loadPhaseEvents()
  → renderEventsList()
```

---

## Geänderte Dateien

| Datei | Änderungen | Lines |
|-------|-----------|-------|
| `index.html` | + Events Section + Add Event Modal | +46 |
| `calendar.js` | + Events Logic + Modal Handling | +175 |
| `api.js` | + createMilestone + deleteMilestone | +24 |
| `calendar.css` | + Events Section Styles + Toggle Switch | +178 |

**Total**: 423 neue Zeilen Code

---

## Backend API Requirements (bereits vorhanden)

✅ `GET /api/calendar/milestones?phase={phase}` - Alle Milestones für Phase
✅ `PATCH /api/calendar/milestones/{id}/toggle` - Enable/Disable
✅ `POST /api/calendar/milestones` - Custom Milestone erstellen
✅ `DELETE /api/calendar/milestones/{id}` - Custom Milestone löschen

**Alle APIs sind bereits im Backend implementiert!**

---

## UI/UX Features

### Visual Feedback
- ✅ Loading State: "Lade Ereignisse..."
- ✅ Empty State: "Keine Ereignisse für diese Phase"
- ✅ Error State: "Fehler beim Laden"
- ✅ Success Toasts: "Event aktiviert", "Event erstellt!"
- ✅ Error Toasts: "Titel ist erforderlich"

### Accessibility
- ✅ Toggle Switch mit Visual State
- ✅ Disabled Events mit reduzierter Opacity
- ✅ Delete-Button nur bei Custom Events sichtbar
- ✅ Confirm Dialog vor Delete

### Responsive
- ✅ Mobile: Reduzierte max-height (200px)
- ✅ Mobile: Event-Header als Column
- ✅ Touch-friendly Toggle Switch (36x20px)

---

## Known Limitations

1. **Category hardcoded**: Custom Events haben immer `category: 'observation'`
   → Future: Dropdown für Category-Auswahl im Modal

2. **Keine Sortierung**: Events werden in API-Reihenfolge angezeigt
   → Backend sortiert nach `day_offset_min ASC`

3. **Keine Pagination**: Bei >50 Events könnte Performance leiden
   → Aktuell unkritisch (max ~30 System-Milestones pro Phase)

---

## Testing Checklist

### Manual Tests (durchzuführen)

- [ ] **Load Events**: Kalender-Tab öffnen → Events-Liste erscheint
- [ ] **Empty State**: Neue Phase ohne Events → "Keine Ereignisse"
- [ ] **Toggle Enable**: Event deaktivieren → Opacity 0.5
- [ ] **Toggle Disable**: Event aktivieren → Opacity 1.0
- [ ] **Create Custom Event**: "+ Neues Event" → Form ausfüllen → Speichern
- [ ] **Validation**: Leerer Titel → Error Toast "Titel ist erforderlich"
- [ ] **Delete Custom Event**: 🗑️ klicken → Confirm → Event verschwindet
- [ ] **System Event Protection**: System-Events haben KEINEN Delete-Button
- [ ] **Phase Switch**: Phase wechseln → Events-Liste aktualisiert sich
- [ ] **Tag Badge**: Day Range anzeige korrekt (z.B. "Tag 15-21" oder "Tag 10")
- [ ] **Modal Close**: ESC oder Overlay-Click schließt Modal
- [ ] **Responsive**: Mobile View → max-height 200px, Column-Layout

---

## Browser Console Logs

```javascript
[Calendar] Initializing calendar tab...
[Calendar] Failed to load events: Error message  // Bei API-Fehler
[Calendar] Toggle error: Error message           // Bei Toggle-Fehler
[Calendar] Delete error: Error message           // Bei Delete-Fehler
[Calendar] Create event error: Error message     // Bei Create-Fehler
```

---

## Next Steps (optional enhancements)

1. **Category Selector**: Dropdown im Add Event Modal
2. **Edit Milestone**: Bestehende Events editierbar machen
3. **Bulk Actions**: "Alle aktivieren/deaktivieren" Button
4. **Filters**: Filter nach Category oder Enabled-State
5. **Search**: Suchfeld für Event-Titel
6. **Drag & Drop**: Sortierung per Drag-and-Drop

---

## Conclusion

✅ **Alle Tasks erfolgreich implementiert**
✅ **Code folgt GrowPi Dark-Theme Guidelines**
✅ **API-Integration vollständig**
✅ **Responsive Design umgesetzt**
✅ **Error Handling robust**

**Ready for Testing!** 🚀

---

**Signatur**: @builder
**Timestamp**: 2025-12-16 20:45 UTC
