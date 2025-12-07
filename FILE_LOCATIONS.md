# GrowPi v6.5 - File Locations Reference

Dieses Dokument hilft dir verschobene, archivierte und neue Dateien wiederzufinden.

**Stand:** 2025-12-06
**Version:** v6.5 Refactoring Integration

---

## Projekt-Struktur Uebersicht

```
GrowPi/
|-- .archive/                    # Archivierte obsolete Dateien
|-- .env                         # Secrets (gitignored)
|-- .env.example                 # Template
|-- .gitignore                   # Git Exclusions
|-- CHANGELOG.md                 # Versionshistorie
|-- CLAUDE.md                    # Projekt-Instruktionen
|-- FILE_LOCATIONS.md            # Diese Datei
|-- README.md                    # Projekt-Uebersicht
|-- docs/                        # Dokumentation
|   |-- refactoring/             # Refactoring Reports
|   |-- ARCHITECTURE.md          # System-Uebersicht
|   |-- BACKEND_INTEGRATION.md   # Backend-Guide
|   |-- DEPLOYMENT_GUIDE.md      # Deployment-Anleitung
|   |-- SPEC_FRONTEND.md         # Frontend-Spezifikation
|   |-- SPEC_RASPBERRY_PI.md     # Hardware-Spezifikation
|-- frontend/                    # Next.js Dashboard
|-- pi-controller/               # Python Controller
    |-- grow_pi/                 # Haupt-Package
    |   |-- config/              # Konfiguration
    |   |-- hardware/            # GPIO/Hardware
    |   |-- utils/               # Utilities
    |   |-- web/                 # Flask Web-App
    |       |-- blueprints/      # API-Module
    |       |-- services/        # Business Logic
    |       |-- static/          # Frontend Assets
    |           |-- js/
    |               |-- modules/ # JavaScript Module
    |-- tests/                   # Unit & Integration Tests
```

---

## Refactoring Dokumentation

**Alle Reports:** `/docs/refactoring/`

### Master Index
- **Index:** `docs/refactoring/INDEX.md` (Uebersicht aller Reports)

### Executive Summaries
| Datei | Beschreibung |
|-------|--------------|
| `docs/refactoring/REFACTORING_V6.5_SUMMARY.md` | v6.5 Integration Summary |
| `docs/refactoring/REFACTORING_SUCCESS.md` | Phase 1 Success Report |

### Detail-Reports
| Datei | Inhalt |
|-------|--------|
| `docs/refactoring/MERGE_ANALYSIS.md` | Git Branch Merge Analyse |
| `docs/refactoring/CODE_VERIFICATION_REPORT.md` | Code-Qualitaetspruefung |
| `docs/refactoring/API_FIX_REPORT.md` | API Konsistenz-Fixes |
| `docs/refactoring/TEST_RESULTS.md` | Unit Test Ergebnisse (140/140) |
| `docs/refactoring/CLEANUP_REPORT.md` | Root-Bereinigung |
| `docs/refactoring/REFACTORED_INDEX_FINAL.md` | Frontend Integration |
| `docs/refactoring/DEHUMIDIFIER_MODULE.md` | Entfeuchter-Modul Doku |
| `docs/refactoring/DOCUMENTATION_UPDATE_SUMMARY.md` | Dokumentations-Update |
| `docs/refactoring/PROJECT_STRUCTURE.md` | Projekt-Struktur Analyse |
| `docs/refactoring/FINAL_VERIFICATION.md` | 22-Punkte Checkliste |
| `docs/refactoring/FINAL_CLEANUP_REPORT.md` | Finaler Cleanup Bericht |

### Phase 1 Original
| Datei | Beschreibung |
|-------|--------------|
| `docs/refactoring/REFACTORING_COMPLETE.md` | Phase 1 Completion |
| `docs/refactoring/REFACTORING_PHASE1_SUMMARY.md` | Phase 1 Summary |

---

## Archivierte Dateien

**Location:** `.archive/2025-12-06_pre-refactoring-cleanup/`

**Manifest:** `.archive/2025-12-06_pre-refactoring-cleanup/MANIFEST.md`

### Archivierte Elemente

| Original | Archiv-Pfad | Grund |
|----------|-------------|-------|
| `.env_new_Server` | `.archive/.../` | Alte VPS Config |
| `api.py.remote` | `.archive/.../` | Alte monolithische API |
| `main.py.remote` | `.archive/.../` | Alter Main-Controller |
| `DEHUMIDIFIER_EXTRACTION_SUMMARY.txt` | `.archive/.../` | Temp Notizen |
| `REFACTORING_SUMMARY.txt` | `.archive/.../` | Temp Merge-Notizen |
| `remote-plug/` | `.archive/.../remote-plug/` | Obsolete Tools |
| `tests/` (root) | `.archive/.../tests/` | Alte GPIO Tests |

### Restore-Befehl

```bash
# Eine Datei wiederherstellen
cp .archive/2025-12-06_pre-refactoring-cleanup/[datei] ./

# Ein Verzeichnis wiederherstellen
cp -r .archive/2025-12-06_pre-refactoring-cleanup/[verzeichnis] ./
```

---

## Code-Struktur

### Backend Blueprints

**Location:** `pi-controller/grow_pi/web/blueprints/`

| Blueprint | Status | Endpoints |
|-----------|--------|-----------|
| `status_bp.py` | Existing | /api/status |
| `settings_bp.py` | Existing | /api/settings/* |
| `data_bp.py` | Existing | /api/history/* |
| `control_bp.py` | Existing | /api/control/* |
| `light_bp.py` | Existing | /api/light/* |
| `modes_bp.py` | Existing | /api/modes/* |
| `costs_bp.py` | **NEW v6.3** | /api/costs/* |
| `dehumidifier_bp.py` | **NEW v6.4** | /api/dehumidifier/* |

### Frontend Modules

**Location:** `pi-controller/grow_pi/web/static/js/modules/`

| Modul | Status | LOC | Funktion |
|-------|--------|-----|----------|
| `main.js` | Existing | ~100 | Bootstrap & Navigation |
| `curves.js` | Refactored | ~200 | Kurven-Editor |
| `history.js` | Refactored | ~150 | Historie & Charts |
| `costs.js` | **NEW v6.3** | 205 | Kosten-Monitoring |
| `environment.js` | **NEW v6.4** | 175 | Entfeuchter-Steuerung |

**API Client:** `pi-controller/grow_pi/web/static/js/api.js` (19 Methoden)

**README:** `pi-controller/grow_pi/web/static/js/modules/README.md`

### Unit Tests

**Location:** `pi-controller/tests/unit/`

| Test-Datei | Status | Tests | Coverage |
|------------|--------|-------|----------|
| `test_hardware.py` | Existing | 40 | Hardware |
| `test_light_schedule.py` | Existing | 51 | Lichtsteuerung |
| `test_costs_calculation.py` | **NEW v6.3** | 19 | Kostenrechnung |
| `test_dehumidifier_logic.py` | **NEW v6.4** | 30 | Entfeuchter-Logik |

**Test README:** `pi-controller/tests/README.md`

---

## Konfiguration

### Pi-Controller Config

**Location:** `pi-controller/grow_pi/config/room_config.json`

```json
{
  "zones": [...],
  "dehumidifier": {
    "enabled": true,
    "threshold": 60
  },
  "costs": {
    "electricity_rate": 0.30,
    "currency": "EUR"
  }
}
```

### Environment

**Location:** `.env` (gitignored)

**Template:** `.env.example`

---

## Deployment

### Guides
- **Haupt-Guide:** `docs/DEPLOYMENT_GUIDE.md`
- **Verification:** `docs/refactoring/FINAL_VERIFICATION.md` (22 Checks)

### Pi-Controller Installation

```bash
ssh admin@192.168.0.86
cd /opt/grow-pi
git pull origin refactoring/phase-1-modularization
pip install -r requirements.txt
sudo systemctl restart grow-pi
```

---

## Schnellzugriff

### Start Here
1. `README.md` - Projekt-Uebersicht
2. `CHANGELOG.md` - v6.5 Entry oben
3. `docs/refactoring/INDEX.md` - Alle Reports
4. `FILE_LOCATIONS.md` - Diese Datei

### Deployment
1. `docs/DEPLOYMENT_GUIDE.md`
2. `docs/refactoring/FINAL_VERIFICATION.md`

### Development
1. `pi-controller/grow_pi/web/static/js/modules/README.md`
2. `pi-controller/tests/README.md`
3. `CLAUDE.md` - Claude Code Instruktionen

---

## Version Control

### Branches
| Branch | Status | Inhalt |
|--------|--------|--------|
| `main` | Production | Stable v6.2 |
| `refactoring/phase-1-modularization` | Development | v6.5 Integration |

### Remote
- **Origin:** GitHub (cubetribe/GrowPi oder aehnlich)
- **Push-Protokoll:** Siehe CLAUDE.md

---

## Kontakt

**Developer:** Dennis Westermann
**Email:** d.westermann@ol-mg.de

---

**Last Updated:** 2025-12-06
**Created By:** Agent #13 (GitHub & Documentation Master)
