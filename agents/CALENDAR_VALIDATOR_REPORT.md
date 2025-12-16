# Calendar Feature Validator Report
**Version:** v6.20.0  
**Feature:** Grow-Kalender mit Phasen-Tracking und Daily Logs  
**Validation Date:** 2025-12-12  
**Status:** CRITICAL ISSUES FOUND - REQUIRES FIXES

---

## Executive Summary

Die Grow-Kalender-Implementierung weist **mehrere kritische Inkonsistenzen** zwischen Frontend und Backend auf. Die Hauptprobleme liegen in:

1. **Phase-Namen-Mismatch** (vegetative vs. veggie, flowering vs. bloom)
2. **API-Contract-Verletzungen** (fehlende Endpoints, falsche Parameter)
3. **Fehlende Schema-Felder** (ec_value, ph_value, observations nicht in DB)

---

## 1. Backend-Validierung

### 1.1 SQL-Migration ✅ PASSED

**Datei:** `pi-controller/grow_pi/database/migrations/20251212_grow_calendar.sql`

| Check | Status | Details |
|-------|--------|---------|
| SQL Syntax | ✅ OK | Migration erfolgreich getestet |
| Tabellen-Anzahl | ✅ OK | 3 Tabellen (grows, phase_events, daily_logs) |
| Foreign Keys | ✅ OK | CASCADE DELETE vorhanden |
| UNIQUE Constraints | ✅ OK | `UNIQUE(grow_id, log_date)` korrekt |
| Indexes | ✅ OK | 6 Indexes definiert |
| Demo Data | ✅ OK | Seed-Daten vorhanden |

**Schema-Prüfung:**
```sql
-- grows table
id, name, strain, start_date, current_phase, phase_started_at, 
notes, is_active, created_at, updated_at ✅

-- phase_events table
id, grow_id, phase, started_at, ended_at, duration_days, 
notes, created_at ✅

-- daily_logs table
id, grow_id, log_date, watered, fertilized, water_amount_ml,
fertilizer_type, fertilizer_amount_ml, notes, plant_height_cm,
photos, created_at, updated_at ✅
```

---

### 1.2 Blueprint Implementation ✅ PASSED (mit Warnings)

**Datei:** `pi-controller/grow_pi/web/blueprints/calendar_bp.py`

| Check | Status | Details |
|-------|--------|---------|
| Python Syntax | ✅ OK | AST-Parsing erfolgreich |
| Endpoint-Anzahl | ✅ OK | 13 Endpoints implementiert |
| Import-Statements | ✅ OK | Alle Imports vorhanden |
| Error Handling | ✅ OK | 400/404/500 Status-Codes |
| UUID Generation | ✅ OK | Helper-Funktion vorhanden |
| Database Connection | ✅ OK | `get_db_connection()` korrekt |

**Implementierte Endpoints:**
```
✅ GET  /api/calendar/grows
✅ POST /api/calendar/grows
✅ GET  /api/calendar/grows/<id>
✅ PUT  /api/calendar/grows/<id>
✅ DELETE /api/calendar/grows/<id>
✅ POST /api/calendar/grows/<id>/phase
✅ GET  /api/calendar/grows/<id>/timeline
✅ GET  /api/calendar/grows/<id>/logs
✅ POST /api/calendar/logs
✅ GET  /api/calendar/logs/<id>
✅ PUT  /api/calendar/logs/<id>
✅ DELETE /api/calendar/logs/<id>
✅ GET  /api/calendar/month/<YYYY-MM>
```

---

### 1.3 Blueprint Registration ✅ PASSED

**Datei:** `pi-controller/grow_pi/web/app.py`

| Check | Status | Line |
|-------|--------|------|
| Import Calendar Blueprint | ✅ OK | Line 402 |
| Register Blueprint | ✅ OK | Line 466 |

```python
Line 402: from .blueprints.calendar_bp import calendar_bp
Line 466: app.register_blueprint(calendar_bp)
```

---

## 2. Frontend-Backend Integration (API Contract Check)

### 2.1 Critical Mismatches ❌ FAILED

#### Issue #1: Phase-Namen-Inkonsistenz ❌ CRITICAL

**Problem:** Frontend und Backend nutzen unterschiedliche Phase-Namen!

| Context | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|---------|---------|---------|---------|---------|
| **Backend SQL** | seedling | vegetative | **flowering** | drying |
| **Backend Validation** | seedling | vegetative | **flowering** | drying |
| **Frontend calendar.js** | seedling | vegetative | **bloom** | harvest |
| **Frontend PHASE_LABELS** | seedling | vegetative | **bloom** | harvest |

**Location:** 
- Backend: `calendar_bp.py` Line 381 (valid_phases)
- Frontend: `calendar.js` Line 55-59 (PHASE_LABELS)

**Impact:** ❌ API-Calls werden fehlschlagen!

**Required Fix:**
```javascript
// Frontend calendar.js - MUSS geändert werden:
const PHASE_LABELS = {
    seedling: { de: 'Keim', en: 'Seedling', color: '#4ade80', icon: '🌱' },
    vegetative: { de: 'Wachstum', en: 'Veggie', color: '#60a5fa', icon: '🌿' },
    flowering: { de: 'Blüte', en: 'Bloom', color: '#c084fc', icon: '🌸' },  // NICHT bloom!
    drying: { de: 'Trocknung', en: 'Drying', color: '#fbbf24', icon: '🌾' }  // NICHT harvest!
};
```

---

#### Issue #2: API-Parameter-Mismatch ❌ CRITICAL

**Problem:** Frontend sendet falsche Feldnamen an Backend!

**createGrow() - Line 174-179:**
```javascript
// ❌ WRONG:
await GrowPiAPI.createGrow({
    started_at: startDate,  // ❌ Backend erwartet: start_date
    current_phase: 'seedling'  // ❌ Backend setzt automatisch
});

// ✅ CORRECT (Backend erwartet):
{
    name: "string",
    start_date: "YYYY-MM-DD",  // NICHT started_at!
    strain: "string" (optional),
    notes: "string" (optional)
}
```

**transitionPhase() - Line 208-211:**
```javascript
// ❌ WRONG:
await GrowPiAPI.transitionPhase(currentGrow.id, {
    phase: phase,  // ❌ Backend erwartet: new_phase
    phase_started_at: ...  // ❌ Backend berechnet automatisch
});

// ✅ CORRECT (Backend erwartet):
{
    new_phase: "seedling|vegetative|flowering|drying|curing",
    notes: "string" (optional)
}
```

---

#### Issue #3: Fehlende Schema-Felder ❌ CRITICAL

**Problem:** Frontend nutzt Felder, die NICHT in der Datenbank existieren!

**saveDailyLog() - Line 441-460:**

Frontend sendet:
```javascript
{
    ec_value: 1.8,           // ❌ NICHT in daily_logs schema!
    ph_value: 6.2,           // ❌ NICHT in daily_logs schema!
    fertilizer_notes: "...", // ❌ Schema hat nur: fertilizer_type, fertilizer_amount_ml
    observations: ["burnt_tips"],  // ❌ NICHT in schema!
    water_amount: 500        // ❌ Schema erwartet: water_amount_ml
}
```

**Tatsächliches Schema (daily_logs):**
```sql
watered BOOLEAN
fertilized BOOLEAN
water_amount_ml INTEGER      -- NICHT water_amount!
fertilizer_type TEXT
fertilizer_amount_ml INTEGER
notes TEXT                   -- NUR ein Feld für alle Notizen
plant_height_cm REAL
photos TEXT (JSON Array)
```

**Required Fix:** Schema erweitern ODER Frontend anpassen!

---

#### Issue #4: Fehlender Endpoint ❌ CRITICAL

**Problem:** Frontend ruft Endpoint auf, der NICHT existiert!

**getCalendarMonth() - Line 577:**
```javascript
// ❌ Frontend erwartet:
GET /api/calendar/logs?month=YYYY-MM

// ✅ Backend hat:
GET /api/calendar/month/<YYYY-MM>
```

**api.js muss angepasst werden:**
```javascript
// Line 577 - WRONG:
async getCalendarMonth(month) {
    return await get(`/api/calendar/logs?month=${month}`);
}

// CORRECT:
async getCalendarMonth(month) {
    return await get(`/api/calendar/month/${month}`);
}
```

---

### 2.2 API Contract Matrix

| Frontend Method | Expected Endpoint | Actual Backend | Status |
|-----------------|-------------------|----------------|--------|
| `getGrows(includeArchived)` | `/api/calendar/grows?archived=true` | `/api/calendar/grows?active_only=false` | ❌ Param-Mismatch |
| `createGrow(data)` | POST `/api/calendar/grows` | POST `/api/calendar/grows` | ❌ Feldnamen falsch |
| `getGrow(id)` | GET `/api/calendar/grows/<id>` | GET `/api/calendar/grows/<id>` | ✅ OK |
| `updateGrow(id, updates)` | PUT `/api/calendar/grows/<id>` | PUT `/api/calendar/grows/<id>` | ✅ OK |
| `transitionPhase(id, data)` | PUT `/api/calendar/grows/<id>/phase` | POST `/api/calendar/grows/<id>/phase` | ❌ HTTP-Methode falsch! |
| `saveDailyLog(data)` | POST `/api/calendar/logs` | POST `/api/calendar/logs` | ❌ Schema-Mismatch |
| `getCalendarMonth(month)` | GET `/api/calendar/logs?month=...` | GET `/api/calendar/month/<YYYY-MM>` | ❌ URL falsch |

---

## 3. Frontend-Validierung

### 3.1 JavaScript-Modul ✅ PASSED (mit Warnings)

**Datei:** `pi-controller/grow_pi/web/static/js/modules/calendar.js`

| Check | Status | Details |
|-------|--------|---------|
| Module-Export | ✅ OK | `export function initCalendarTab()` vorhanden |
| Import-Statements | ✅ OK | `api.js`, `utils.js` korrekt |
| DOM-Element-Zugriff | ⚠️ WARNING | Nicht alle IDs in HTML |
| Event-Listener | ✅ OK | Setup-Funktion korrekt |
| Syntax | ✅ OK | Keine JavaScript-Fehler |

---

### 3.2 HTML-Integration ✅ PASSED (mit Warnings)

**Datei:** `pi-controller/grow_pi/web/static/index.html`

| Check | Status | Line |
|-------|--------|------|
| Calendar-Tab Button | ✅ OK | Line 44 |
| Calendar Tab Content | ✅ OK | Line 193-271 |
| Daily Log Modal | ✅ OK | Line 623-754 |
| CSS-Import | ✅ OK | Line 12 |
| Module-Import | ✅ OK | Line 768 |
| Init-Call | ✅ OK | Line 783 |

**Tab-Integration:**
```html
Line 44: <button class="tab-btn" data-tab="calendar">Kalender</button>
Line 193: <div id="tab-calendar" class="tab-content">
Line 768: import { initCalendarTab } from './js/modules/calendar.js';
Line 783: initCalendarTab();
```

---

### 3.3 Modal-HTML Vollständigkeit ⚠️ WARNING

**Fehlende DOM-IDs in calendar.js:**

| calendar.js Variable | Expected ID | HTML Status |
|---------------------|-------------|-------------|
| `calendarHeader` | `calendarHeader` | ❌ NICHT GEFUNDEN |
| `calendarGrid` | `calendarGrid` | ✅ Line 231 |
| `currentGrowName` | `currentGrowName` | ✅ Line 199 |
| `currentPhaseInfo` | `currentPhaseInfo` | ✅ Line 200 |
| `phaseButtonSeedling` | `phaseBtnSeedling` | ✅ Line 210 |
| `phaseButtonVeggie` | `phaseBtnVeggie` | ✅ Line 213 |
| `phaseButtonBloom` | `phaseBtnBloom` | ✅ Line 216 |
| `btnNewGrow` | `btnNewGrow` | ✅ Line 203 |
| `dailyLogModal` | `dailyLogModal` | ✅ Line 623 |
| `modalDate` | `modalDate` | ✅ Line 627 |
| `modalPhaseInfo` | `modalPhaseInfo` | ✅ Line 628 |
| `logFertilized` | `logFertilized` | ✅ Line 638 |
| `logEcValue` | `logEcValue` | ✅ Line 644 |
| `logPhValue` | `logPhValue` | ✅ Line 648 |
| `logFertilizerNotes` | `logFertilizerNotes` | ✅ Line 653 |
| `logWatered` | `logWatered` | ✅ Line 661 |
| `logWaterAmount` | `logWaterAmount` | ✅ Line 666 |
| `logNotes` | `logNotes` | ✅ Line 744 |
| `logObservations` | `observations` (name) | ✅ Lines 675-736 |

**Fix benötigt:** `calendarHeader` wird in calendar.js referenziert, ist aber nicht in HTML!

---

### 3.4 CSS-Konsistenz ✅ PASSED

**Datei:** `pi-controller/grow_pi/web/static/css/calendar.css`

| Check | Status | Details |
|-------|--------|---------|
| Syntax-Validierung | ✅ OK | Keine CSS-Fehler |
| Klassen-Coverage | ✅ OK | Alle JS-Klassen definiert |
| Responsive Design | ✅ OK | Mobile Breakpoints vorhanden |
| Neon-Theme | ✅ OK | #11ff55 konsistent |

**Definierte Klassen:**
```css
.calendar-container ✅
.grow-header ✅
.phase-selector ✅
.calendar-grid ✅
.calendar-day ✅
.daily-log-modal ✅
.log-modal-content ✅
.log-section ✅
.observations-grid ✅
```

---

## 4. Cross-File-Konsistenz

### 4.1 Type-Mapping ❌ FAILED

| Data Type | Backend | Frontend | Status |
|-----------|---------|----------|--------|
| Phase Names | flowering, drying, curing | bloom, harvest | ❌ MISMATCH |
| Grow Fields | start_date | started_at | ❌ MISMATCH |
| Log Fields | water_amount_ml | water_amount | ❌ MISMATCH |
| HTTP Methods | POST /phase | PUT /phase | ❌ MISMATCH |

---

### 4.2 Response-Format-Konsistenz ✅ OK

Backend standardisiert alle Responses:
```python
def create_response(success: bool, data: dict = None, error: str = None) -> dict
```

Frontend erwartet:
```javascript
if (data.success) { ... }
```

✅ Konsistent!

---

## 5. Potenzielle Fehlerquellen

### 5.1 Runtime-Fehler (Garantiert) ❌ CRITICAL

1. **Phase-Transition wird fehlschlagen:**
   ```javascript
   // calendar.js Line 208
   transitionPhase('bloom')  // ❌ Backend akzeptiert nur 'flowering'
   // → Backend antwortet: 400 "Invalid phase"
   ```

2. **getCalendarMonth wird 404 werfen:**
   ```javascript
   // api.js Line 577
   GET /api/calendar/logs?month=2025-12  // ❌ Endpoint existiert nicht
   // → Backend antwortet: 404 "Endpoint not found"
   ```

3. **createGrow wird fehlschlagen:**
   ```javascript
   // calendar.js Line 177
   { started_at: "2025-12-12" }  // ❌ Backend erwartet start_date
   // → Backend antwortet: 400 "start_date is required"
   ```

---

### 5.2 Undefined-Variablen ⚠️ WARNING

**calendar.js Line 15:**
```javascript
const calendarHeader = document.getElementById('calendarHeader');
```
❌ Element existiert nicht in HTML → `calendarHeader` ist `null`

**Potentieller Error:**
```javascript
// Falls calendar.js versucht darauf zuzugreifen:
calendarHeader.textContent = "...";  // ❌ TypeError: Cannot read property 'textContent' of null
```

---

### 5.3 Schema-Validierung-Fehler ❌ CRITICAL

**saveDailyLog() sendet ungültige Felder:**
```javascript
{
    ec_value: 1.8,           // ❌ Spalte existiert nicht
    ph_value: 6.2,           // ❌ Spalte existiert nicht
    observations: ["burnt"]  // ❌ Spalte existiert nicht
}
// → Backend INSERT wird fehlschlagen
```

---

## 6. Empfohlene Fixes

### 6.1 CRITICAL (MUSS vor Deployment)

#### Fix #1: Phase-Namen-Synchronisierung ❌ MANDATORY

**Option A (Empfohlen): Frontend anpassen**
```javascript
// calendar.js Line 55-59
const PHASE_LABELS = {
    seedling: { de: 'Keim', en: 'Seedling', color: '#4ade80', icon: '🌱' },
    vegetative: { de: 'Wachstum', en: 'Veggie', color: '#60a5fa', icon: '🌿' },
    flowering: { de: 'Blüte', en: 'Bloom', color: '#c084fc', icon: '🌸' },   // ✅
    drying: { de: 'Trocknung', en: 'Drying', color: '#f59e0b', icon: '🌾' }, // ✅
    curing: { de: 'Curing', en: 'Curing', color: '#fbbf24', icon: '🏺' }    // ✅
};

// HTML Line 210-217
<button class="phase-btn flowering" id="phaseBtnBloom">🌸 Blüte</button>
```

**Affected Files:**
- `calendar.js` Line 55-59, 109-111
- `index.html` Line 210-217

---

#### Fix #2: API-Feldnamen korrigieren ❌ MANDATORY

**calendar.js Line 174-179:**
```javascript
// BEFORE:
await GrowPiAPI.createGrow({
    name: name,
    strain: strain || null,
    started_at: startDate,  // ❌ WRONG
    current_phase: 'seedling'  // ❌ UNNECESSARY
});

// AFTER:
await GrowPiAPI.createGrow({
    name: name,
    strain: strain || '',
    start_date: startDate,  // ✅ CORRECT
    notes: ''
});
```

**calendar.js Line 208-211:**
```javascript
// BEFORE:
await GrowPiAPI.transitionPhase(currentGrow.id, {
    phase: phase,  // ❌ WRONG
    phase_started_at: new Date().toISOString().split('T')[0]  // ❌ UNNECESSARY
});

// AFTER:
await GrowPiAPI.transitionPhase(currentGrow.id, {
    new_phase: phase,  // ✅ CORRECT
    notes: ''
});
```

---

#### Fix #3: API-URL korrigieren ❌ MANDATORY

**api.js Line 577:**
```javascript
// BEFORE:
async getCalendarMonth(month) {
    return await get(`/api/calendar/logs?month=${month}`);  // ❌ WRONG
}

// AFTER:
async getCalendarMonth(month) {
    return await get(`/api/calendar/month/${month}`);  // ✅ CORRECT
}
```

---

#### Fix #4: HTTP-Methode korrigieren ❌ MANDATORY

**api.js Line 549:**
```javascript
// BEFORE:
async transitionPhase(growId, phaseData) {
    return await put(`/api/calendar/grows/${growId}/phase`, phaseData);  // ❌ PUT
}

// AFTER:
async transitionPhase(growId, phaseData) {
    return await post(`/api/calendar/grows/${growId}/phase`, phaseData);  // ✅ POST
}
```

---

#### Fix #5: Schema erweitern ODER Frontend-Felder entfernen ❌ MANDATORY

**Option A (Empfohlen): Schema erweitern**

Neue Migration `20251212_grow_calendar_v2.sql`:
```sql
ALTER TABLE daily_logs ADD COLUMN ec_value REAL;
ALTER TABLE daily_logs ADD COLUMN ph_value REAL;
ALTER TABLE daily_logs ADD COLUMN fertilizer_notes TEXT;
ALTER TABLE daily_logs ADD COLUMN observations TEXT;  -- JSON Array

-- Rename für Konsistenz
ALTER TABLE daily_logs RENAME COLUMN water_amount_ml TO water_amount_ml;  -- OK
```

**Option B: Frontend-Felder entfernen**
```javascript
// calendar.js - Felder entfernen:
// Line 453-455 - ec_value, ph_value, fertilizer_notes löschen
// Line 458 - observations löschen
// Nur nutzen: fertilizer_type, fertilizer_amount_ml, notes
```

---

#### Fix #6: Fehlende HTML-Elemente ⚠️ RECOMMENDED

**index.html - Hinzufügen:**
```html
<!-- Line 223 (nach calendar-nav) -->
<div id="calendarHeader" class="calendar-header-info" style="display: none;">
    <!-- Optional: Zusätzliche Header-Info -->
</div>
```

**ODER calendar.js anpassen:**
```javascript
// Line 15 - Entfernen oder null-check:
const calendarHeader = document.getElementById('calendarHeader');
// ... später nur nutzen wenn vorhanden:
if (calendarHeader) {
    calendarHeader.textContent = "...";
}
```

---

### 6.2 HIGH Priority (Empfohlen)

#### Fix #7: Query-Parameter-Konsistenz

**api.js Line 504-506:**
```javascript
// BEFORE:
async getGrows(includeArchived = false) {
    const url = includeArchived ? '/api/calendar/grows?archived=true' : '/api/calendar/grows';
    return await get(url);
}

// AFTER (Backend nutzt active_only):
async getGrows(activeOnly = true) {
    const url = activeOnly ? '/api/calendar/grows?active_only=true' : '/api/calendar/grows';
    return await get(url);
}
```

---

#### Fix #8: saveDailyLog Schema-Mapping

**calendar.js Line 449-460:**
```javascript
// BEFORE:
const logData = {
    grow_id: currentGrow.id,
    date: selectedDate,
    fertilized: logFertilized.checked,
    ec_value: logFertilized.checked ? parseFloat(logEcValue.value) || null : null,
    ph_value: logFertilized.checked ? parseFloat(logPhValue.value) || null : null,
    fertilizer_notes: logFertilized.checked ? logFertilizerNotes.value : null,
    watered: logWatered.checked,
    water_amount: logWatered.checked ? parseInt(logWaterAmount.value) || null : null,
    observations: observations,
    notes: logNotes.value || null
};

// AFTER (Backend-Schema entsprechend):
const logData = {
    grow_id: currentGrow.id,
    log_date: selectedDate,  // ✅ Backend erwartet log_date
    fertilized: logFertilized.checked,
    fertilizer_type: logFertilized.checked ? logFertilizerNotes.value : null,  // ✅
    fertilizer_amount_ml: null,  // ✅ Oder aus neuem Input-Feld
    watered: logWatered.checked,
    water_amount_ml: logWatered.checked ? parseInt(logWaterAmount.value) || null : null,  // ✅
    notes: logNotes.value || null,
    plant_height_cm: null,  // ✅ Optional
    photos: null  // ✅ JSON Array
};
```

---

## 7. TypeScript-Validierung

❌ **NOT APPLICABLE** - Projekt nutzt kein TypeScript (reines JavaScript)

**Empfehlung:** Für zukünftige Entwicklung TypeScript verwenden um solche Contract-Fehler zu verhindern!

---

## 8. Gesamtbewertung

| Kategorie | Status | Score |
|-----------|--------|-------|
| Backend SQL | ✅ PASSED | 10/10 |
| Backend Blueprint | ✅ PASSED | 9/10 |
| Backend Registration | ✅ PASSED | 10/10 |
| **Frontend-Backend Contract** | ❌ **FAILED** | **3/10** |
| Frontend JS | ⚠️ WARNING | 7/10 |
| Frontend HTML | ⚠️ WARNING | 8/10 |
| Frontend CSS | ✅ PASSED | 10/10 |
| **Cross-File-Konsistenz** | ❌ **FAILED** | **2/10** |

---

## 9. Final Verdict

### Status: ❌ REQUIRES MANDATORY FIXES BEFORE DEPLOYMENT

**CRITICAL Issues (6):**
1. ❌ Phase-Namen-Mismatch (flowering vs bloom)
2. ❌ createGrow Feldnamen falsch (start_date vs started_at)
3. ❌ transitionPhase Parameter falsch (new_phase vs phase)
4. ❌ transitionPhase HTTP-Methode falsch (POST vs PUT)
5. ❌ getCalendarMonth URL falsch
6. ❌ saveDailyLog Schema-Felder fehlen

**HIGH Priority Issues (2):**
7. ⚠️ Query-Parameter-Inkonsistenz (active_only vs archived)
8. ⚠️ Fehlende HTML-Elemente (calendarHeader)

---

## 10. Deployment-Checkliste

### BEFORE Deployment (MANDATORY):

- [ ] Fix #1: Phase-Namen-Synchronisierung
- [ ] Fix #2: createGrow Feldnamen
- [ ] Fix #3: getCalendarMonth URL
- [ ] Fix #4: transitionPhase HTTP-Methode
- [ ] Fix #5: Schema erweitern ODER Frontend-Felder entfernen
- [ ] Fix #6: calendarHeader null-check

### AFTER Deployment (RECOMMENDED):

- [ ] Fix #7: Query-Parameter-Konsistenz
- [ ] Fix #8: saveDailyLog Schema-Mapping
- [ ] Integration-Tests schreiben
- [ ] TypeScript-Migration planen

---

## 11. Test-Szenarien (Post-Fix)

Nach Implementierung der Fixes MUSS getestet werden:

1. **Grow Creation:**
   ```bash
   curl -X POST http://localhost:5000/api/calendar/grows \
     -H "Content-Type: application/json" \
     -d '{"name":"Test Grow","start_date":"2025-12-12"}'
   ```

2. **Phase Transition:**
   ```bash
   curl -X POST http://localhost:5000/api/calendar/grows/<id>/phase \
     -H "Content-Type: application/json" \
     -d '{"new_phase":"vegetative"}'
   ```

3. **Calendar Month View:**
   ```bash
   curl http://localhost:5000/api/calendar/month/2025-12
   ```

4. **Daily Log Creation:**
   ```bash
   curl -X POST http://localhost:5000/api/calendar/logs \
     -H "Content-Type: application/json" \
     -d '{"grow_id":"<id>","log_date":"2025-12-12","watered":true,"water_amount_ml":500}'
   ```

---

## 12. Risk Assessment

| Risk | Severity | Likelihood | Impact | Mitigation |
|------|----------|------------|--------|------------|
| Phase-Transition Failure | CRITICAL | 100% | Complete Feature Broken | Fix #1 (Phase-Namen) |
| Calendar-Rendering 404 | CRITICAL | 100% | No Calendar Data | Fix #3 (URL) |
| Grow-Creation Failure | CRITICAL | 100% | Cannot Create Grows | Fix #2 (Feldnamen) |
| Daily-Log-Save Failure | HIGH | 90% | Data Loss | Fix #5 (Schema) |
| Frontend Null-Errors | MEDIUM | 50% | UI Glitches | Fix #6 (null-check) |

---

## 13. Conclusion

Die Grow-Kalender-Feature-Implementierung ist **NICHT production-ready**. Es existieren **6 CRITICAL Bugs**, die zu **kompletter Feature-Dysfunktion** führen würden.

**Geschätzte Fix-Dauer:** 2-3 Stunden

**Empfehlung:** 
1. Implementiere alle MANDATORY Fixes
2. Schreibe Integration-Tests
3. Validiere erneut mit Test-Szenarien
4. Dann erst deployen

---

**Validator:** Claude Opus 4.5 (Validator-Agent)  
**Report Version:** 1.0  
**Next Validation:** Nach Implementierung der Fixes
