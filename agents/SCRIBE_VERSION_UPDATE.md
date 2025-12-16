# Scribe Report: Version Update v6.20.0

**Datum:** 2025-12-16
**Agent:** @scribe
**Task:** Versionsnummer und CHANGELOG für v6.20.0 aktualisieren

---

## Aufgaben

### 1. CHANGELOG.md aktualisiert ✅

**Datei:** `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/CHANGELOG.md`

**Neuer Eintrag für v6.20.0 hinzugefügt:**
- Position: Am Anfang der Datei (nach Header, vor v6.19.0)
- Datum: 2025-12-16
- Status: ⏳ Wartet auf User-Test

**Inhalt:**

#### Added
- **Grow Calendar Status Dashboard** 📊
  - Große Tag-Anzeige: "Tag X der aktuellen Phase"
  - Phase-Info mit Icon und Namen (Keim/Wachstum/Blüte)
  - Grow-Startdatum und Phase-Startdatum sichtbar
  - Einstellungen-Button für Datum-Editierung

- **Grow-Einstellungen Modal** ⚙️
  - Grow-Name und Sorte editierbar
  - Grow-Startdatum änderbar
  - Phase-Startdatum änderbar (z.B. "Blüte begann am...")
  - Automatische Neuberechnung des aktuellen Tags

#### Changed
- **Backend API erweitert:**
  - `GET /api/calendar/grows` liefert jetzt `phase_day` (berechneter Tag der Phase)
  - `PUT /api/calendar/grows/<id>` akzeptiert jetzt `start_date` und `phase_started_at`
  - Validierung: Datum darf nicht in der Zukunft liegen

#### Technical Details
- `calendar_bp.py`: +68 LOC (phase_day Berechnung, Datum-Editierung)
- `calendar.js`: +150 LOC (Status Dashboard, Settings Modal)
- `calendar.css`: +120 LOC (Dashboard Styling)
- `index.html`: +60 LOC (Dashboard HTML, Modal HTML)

---

### 2. Versionsnummern aktualisiert ✅

#### Versionsverwaltungs-Architektur

Das GrowPi-Projekt verwendet ein **Single Source of Truth** System:

1. **VERSION-Datei** (Primäre Quelle)
   - Pfad: `/pi-controller/VERSION`
   - Alte Version: `6.18.0` (⚠️ war veraltet, nicht mal 6.19.0!)
   - **Neue Version: `6.20.0`** ✅

2. **Python Package Version**
   - Pfad: `/pi-controller/grow_pi/__init__.py`
   - Variable: `__version__ = "6.20.0"`
   - Zweck: Python-Modul-Versionierung

3. **API Version** (Web Dependency Injection)
   - Pfad: `/pi-controller/grow_pi/web/dependencies.py`
   - Variable: `_api_version = "6.20.0"`
   - Alte Version: `6.8.0` (⚠️ stark veraltet!)
   - Zweck: API-Versionsanzeige im Header

#### Wie die Version im Frontend angezeigt wird

**Fluss:**

```
VERSION file (6.20.0)
  ↓
grow_pi/version.py → get_version() → caches version
  ↓
/api/version endpoint → returns { version_display: "v6.20.0" }
  ↓
JavaScript: GrowPiAPI.getVersion()
  ↓
environment.js → updateVersionDisplay()
  ↓
index.html: <span id="versionBadge">v6.20.0</span>
```

**Relevante Dateien:**

| Datei | Funktion | Beschreibung |
|-------|----------|--------------|
| `pi-controller/VERSION` | Single Source of Truth | Enthält nur `6.20.0` |
| `grow_pi/version.py` | Version Loader | Liest VERSION-Datei und cached |
| `grow_pi/web/api.py` | API Endpoint | Route `/api/version` mit `get_version_display()` |
| `static/js/api.js` | API Client | `GrowPiAPI.getVersion()` Methode |
| `static/js/modules/environment.js` | Frontend Logic | `updateVersionDisplay()` aktualisiert Badge |
| `static/index.html` | UI Element | `<span id="versionBadge">` im Header |

---

### 3. Gefundene Probleme ⚠️

#### Version-Inkonsistenzen (vor diesem Update)

| Datei | Alte Version | Status |
|-------|--------------|--------|
| `VERSION` | 6.18.0 | ⚠️ 2 Versionen zurück! |
| `grow_pi/__init__.py` | 6.19.0 | ⚠️ 1 Version zurück |
| `grow_pi/web/dependencies.py` | 6.8.0 | ⚠️ 12 Versionen zurück! |

**Root Cause:**
Die `dependencies.py` API-Version wurde seit v6.8.0 nicht mehr aktualisiert. Dies könnte zu Verwirrung führen, da der `/api/version` Endpoint die korrekte Version aus der VERSION-Datei liest, aber das alte System (`_api_version` Variable) noch existiert.

**Empfehlung:**
- Das `_api_version` System in `dependencies.py` sollte DEPRECATED werden
- Alle API-Endpoints sollten `grow_pi.version.get_version()` verwenden
- Oder: Automatisches Synchronisieren über ein Pre-Commit Hook

---

## Zusammenfassung

✅ **CHANGELOG.md** - v6.20.0 Eintrag hinzugefügt
✅ **VERSION** - 6.18.0 → 6.20.0
✅ **grow_pi/__init__.py** - 6.19.0 → 6.20.0
✅ **dependencies.py** - 6.8.0 → 6.20.0

**Alle Versionsnummern sind jetzt synchronisiert auf v6.20.0.**

---

## Geänderte Dateien

1. `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/CHANGELOG.md`
2. `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/VERSION`
3. `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi/__init__.py`
4. `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi/web/dependencies.py`

---

## Next Steps (für Deployment)

Nach User-Test und Freigabe:

```bash
# Auf dem Pi
cd /opt/grow-pi
git pull origin main
echo "6.20.0" > /opt/grow-pi/VERSION
sudo systemctl restart grow-pi
```

Frontend sollte dann `v6.20.0` im Header-Badge anzeigen.

---

**Report erstellt:** 2025-12-16
**Agent:** @scribe (Technical Writer)
