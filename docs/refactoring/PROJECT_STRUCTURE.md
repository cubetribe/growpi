# GrowPi - Project Structure (Post-Refactoring Phase 1)

**Last Updated:** 2025-12-06
**Schema Version:** Post-Refactoring v6.4
**Status:** Production-Ready (Pi-Controller Modularized)

---

## Directory Tree Overview

```
GrowPi/
│
├── 📁 pi-controller/                     🎯 MAIN APPLICATION (Modularized Flask)
│   ├── 📁 grow_pi/                       Core application package
│   │   ├── 📁 config/
│   │   │   ├── room_config.json         Room/zone configuration
│   │   │   └── config_schema.json       Validation schema
│   │   │
│   │   ├── 📁 database/                 Database layer
│   │   │   ├── db.py                    SQLite connection
│   │   │   ├── models.py                ORM models (SQLAlchemy)
│   │   │   ├── repositories/            Data access patterns
│   │   │   │   ├── lamp_repository.py
│   │   │   │   ├── sensor_repository.py
│   │   │   │   └── settings_repository.py
│   │   │   └── migrations/              Schema versions
│   │   │
│   │   ├── 📁 lamps/                    Lighting control module
│   │   │   ├── lamp_controller.py       PWM control logic
│   │   │   ├── curve_manager.py         Lighting curve interpolation
│   │   │   └── lamp_types.py            Channel definitions
│   │   │
│   │   ├── 📁 sensors/                  Sensor reading module
│   │   │   ├── sensor_manager.py        Sensor abstraction
│   │   │   ├── dht22.py                 Temperature/Humidity sensor
│   │   │   └── sensor_types.py          Type definitions
│   │   │
│   │   ├── 📁 utils/                    Shared utilities
│   │   │   ├── logger.py                Logging configuration
│   │   │   ├── dehumidifier_controller.py  Humidity control
│   │   │   ├── mode_manager.py          Operation modes (manual/auto/off)
│   │   │   └── constants.py             App-wide constants
│   │   │
│   │   ├── 📁 web/                      Flask web interface
│   │   │   ├── 📁 blueprints/           API endpoints (8 modules)
│   │   │   │   ├── status_bp.py         Status & health check
│   │   │   │   ├── lighting_bp.py       Lamp curve API
│   │   │   │   ├── sensors_bp.py        Sensor data API
│   │   │   │   ├── settings_bp.py       Configuration API
│   │   │   │   ├── modes_bp.py          Mode management API
│   │   │   │   ├── costs_bp.py          Electricity cost tracking
│   │   │   │   ├── dehumidifier_bp.py   Humidity control API
│   │   │   │   └── __init__.py          Blueprint registration
│   │   │   │
│   │   │   ├── 📁 services/             Business logic (4 services)
│   │   │   │   ├── lighting_service.py
│   │   │   │   ├── sensor_service.py
│   │   │   │   ├── settings_service.py
│   │   │   │   └── mode_service.py
│   │   │   │
│   │   │   ├── 📁 static/               Frontend assets
│   │   │   │   ├── 📁 css/
│   │   │   │   │   ├── main.css         Global styles
│   │   │   │   │   └── dark-theme.css   Dark mode (glassmorphism)
│   │   │   │   │
│   │   │   │   ├── 📁 js/               JavaScript modules
│   │   │   │   │   ├── api.js           API client (axios)
│   │   │   │   │   ├── state.js         Client-side state (localStorage)
│   │   │   │   │   ├── utils.js         Helper functions
│   │   │   │   │   ├── charts.js        Chart.js integration
│   │   │   │   │   └── 📁 modules/      Feature modules (5)
│   │   │   │   │       ├── dashboard-module.js
│   │   │   │   │       ├── lighting-module.js
│   │   │   │   │       ├── sensors-module.js
│   │   │   │   │       ├── settings-module.js
│   │   │   │   │       └── modes-module.js
│   │   │   │   │
│   │   │   │   ├── 📁 images/
│   │   │   │   └── index.html           SPA entry point
│   │   │   │
│   │   │   ├── app.py                   Flask application factory
│   │   │   ├── middleware.py            Request/response middleware
│   │   │   └── error_handler.py         Exception handling
│   │   │
│   │   ├── 📁 __init__.py               Package initialization
│   │   └── 📁 version.py                Version constant
│   │
│   ├── 📁 tests/                        Unit & Integration Tests
│   │   ├── conftest.py                  pytest configuration
│   │   ├── 📁 unit/
│   │   │   ├── test_lamp_controller.py
│   │   │   ├── test_curve_manager.py
│   │   │   ├── test_sensor_manager.py
│   │   │   ├── test_mode_manager.py
│   │   │   └── test_dehumidifier.py
│   │   │
│   │   └── 📁 integration/
│   │       ├── test_api_endpoints.py
│   │       ├── test_database_operations.py
│   │       └── test_full_workflow.py
│   │
│   ├── 📁 test_environment/             Development without Hardware
│   │   ├── mock_services.py             Service mocks
│   │   ├── demo_mode.py                 Demo data generation
│   │   └── README.md                    Setup guide
│   │
│   ├── 📁 config/                       Configuration templates
│   │   ├── config.example.yaml          Template (Pi deployment)
│   │   └── room_config_example.json     Template (Zone config)
│   │
│   ├── 📁 scripts/                      Utility scripts
│   │   ├── backup.sh                    Database backup
│   │   ├── restore.sh                   Database restore
│   │   └── setup.sh                     Installation script
│   │
│   ├── 📁 systemd/                      Service management
│   │   ├── grow-pi.service              systemd unit file
│   │   └── grow-pi.socket               Socket activation
│   │
│   ├── 📁 venv/                         Virtual environment (.gitignored)
│   ├── 📁 .pytest_cache/                pytest cache (.gitignored)
│   │
│   ├── requirements.txt                 Python dependencies
│   ├── pytest.ini                       pytest configuration
│   ├── setup.py                         Package setup
│   └── README.md                        Module documentation
│
├── 📁 frontend/                         ⚠️  DEPRECATED (Integration in Progress)
│   ├── 📁 app/
│   │   ├── (dashboard)/
│   │   │   ├── layout.tsx
│   │   │   ├── dashboard/page.tsx
│   │   │   ├── lighting/page.tsx
│   │   │   ├── sensors/page.tsx
│   │   │   └── settings/page.tsx
│   │   │
│   │   ├── login/page.tsx
│   │   ├── api/                        API Routes (DEPRECATED)
│   │   ├── globals.css                 Dark theme
│   │   └── layout.tsx
│   │
│   ├── 📁 components/
│   │   ├── 📁 ui/                      shadcn/ui components
│   │   └── 📁 dashboard/               Custom components
│   │
│   ├── 📁 contexts/
│   │   └── LanguageContext.tsx         i18n state
│   │
│   ├── 📁 hooks/
│   │   ├── useLanguage.ts
│   │   └── useFetch.ts
│   │
│   ├── 📁 lib/
│   │   ├── db.ts                       Prisma client
│   │   └── utils.ts
│   │
│   ├── 📁 prisma/
│   │   ├── schema.prisma               Supabase schema
│   │   └── seed.ts
│   │
│   ├── 📁 public/                      Static assets
│   ├── 📁 supabase/
│   ├── 📁 .next/                       Build output (.gitignored)
│   ├── 📁 .bolt/                       Bolt artifacts
│   ├── 📁 out/                         Static export
│   │
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   ├── package-lock.json
│   └── README.md
│
├── 📁 docs/                             📚 Documentation
│   ├── ARCHITECTURE.md                 System design
│   ├── SPEC_FRONTEND.md                Frontend spec
│   ├── SPEC_RASPBERRY_PI.md            Hardware spec
│   ├── REFACTORING_COMPLETE.md         Phase 1 completion
│   ├── iOS-App_Plan.md                 Future mobile app
│   └── API_DOCUMENTATION.md            API endpoints
│
├── 📁 .archive/                         ♻️  Archived Files (.gitignored)
│   └── 📁 2025-12-06_pre-refactoring-cleanup/
│       ├── MANIFEST.md                 Archive index
│       ├── .env_new_Server             Old server config
│       ├── api.py.remote               Legacy API backup
│       ├── main.py.remote              Legacy main backup
│       ├── 📁 tests/                   Old test scripts
│       └── 📁 remote-plug/             Old network tools
│
├── 📁 .git/                            Version control (.gitignored)
├── 📁 .claude/                         Claude configuration
├── 📁 .playwright-mcp/                 Browser automation (.gitignored)
│
├── 📄 CHANGELOG.md                     Version history
├── 📄 CLAUDE.md                        Project configuration ⚙️
├── 📄 README.md                        Quick start guide
├── 📄 PROJECT_STRUCTURE.md             This file
├── 📄 .gitignore                       Git ignore rules
├── 📄 .env.example                     Environment template
├── 📄 .env                             Secrets (.gitignored)
│
└── 📄 CLEANUP_REPORT.md               (Generated) Cleanup report
```

---

## Module Organization

### Pi-Controller Architecture

#### Layer 1: Hardware Layer
- **Lamps Module** (`grow_pi/lamps/`)
  - PWM control via pigpio
  - Curve interpolation
  - Channel mapping (4 LED channels)

- **Sensors Module** (`grow_pi/sensors/`)
  - DHT22 temperature/humidity
  - Future: RS485 soil sensors

#### Layer 2: Database Layer
- **Models** (`grow_pi/database/models.py`)
  - Lamp configurations
  - Sensor readings
  - User settings
  - Curves and alerts

- **Repositories** (`grow_pi/database/repositories/`)
  - Data access patterns
  - Query optimization
  - Transaction handling

#### Layer 3: Business Logic
- **Services** (`grow_pi/web/services/`)
  - Lighting service
  - Sensor service
  - Settings service
  - Mode service

#### Layer 4: API Layer
- **Blueprints** (`grow_pi/web/blueprints/`)
  - 8 Feature modules
  - RESTful endpoints
  - Input validation
  - Error handling

#### Layer 5: Frontend
- **Static Files** (`grow_pi/web/static/`)
  - HTML SPA
  - CSS (dark theme, glassmorphism)
  - JavaScript modules
  - Chart.js visualizations

---

## Key Statistics

| Metric | Value |
|--------|-------|
| Python Modules | 25+ |
| Flask Blueprints | 8 |
| Services | 4 |
| Test Files | 10+ |
| JavaScript Modules | 5 |
| CSS Files | 2 |
| Total Lines (Pi-Controller) | ~5000 |
| Total Lines (Frontend) | ~3000 |

---

## Technology Stack

### Pi-Controller Backend
- **Framework:** Flask 2.x
- **Language:** Python 3.13
- **Database:** SQLite
- **Hardware:** pigpio, RPi.GPIO
- **Testing:** pytest, unittest.mock
- **Logging:** Python logging

### Frontend Dashboard
- **Framework:** Next.js 13.5
- **Language:** TypeScript
- **Styling:** TailwindCSS
- **Database:** Supabase (PostgreSQL)
- **UI Components:** shadcn/ui (Radix)
- **Charts:** Recharts
- **Auth:** JWT (HTTP-only cookies)

---

## Git Workflow

### Current Branch
```
main
├── 30f5ee7 (feat: v6.3 Kosten-Tab + v6.4 Entfeuchter-UI)
├── 24370a8 (origin/main)
└── c7766fd (feat: Phase 1 Refactoring - Modular Flask Architecture)
```

### Archived
```
refactoring/phase-1-modularization
└── b16b609 (chore: Monorepo Cleanup - Frontend integriert)
```

---

## Important Notes

### ✅ What's Production-Ready
- Pi-Controller (modularized, tested)
- Web interface (Flask + HTML/JS)
- Dashboard (Next.js, fully functional)
- Database schema (SQLite)
- Configuration system

### ⚠️ Work in Progress
- Mobile app integration (planned)
- Advanced analytics (future)
- Multi-zone support expansion (planned)

### ⛔ Deprecated
- Old monolithic API (archived)
- Old main controller (archived)
- Old test scripts (archived)

---

## File Size Summary

```
pi-controller/          ~150 MB (includes venv)
  ├── grow_pi/          ~50 MB (includes .pytest_cache)
  ├── venv/             ~80 MB
  └── tests/            ~20 MB

frontend/               ~400 MB
  ├── node_modules/     ~350 MB
  ├── .next/            ~30 MB
  └── src/              ~20 MB

docs/                   ~2 MB
.archive/               ~84 KB
```

---

## Development Workflow

### Starting the Pi-Controller

```bash
# 1. Activate virtual environment
cd pi-controller
source venv/bin/activate

# 2. Run the Flask app
python -m grow_pi.web.app

# 3. Access web interface
open http://localhost:5000
```

### Starting the Dashboard (Frontend)

```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Run development server
npm run dev

# 3. Open browser
open http://localhost:3000
```

---

## Documentation Map

| Document | Purpose | Audience |
|----------|---------|----------|
| **CLAUDE.md** | Project config & rules | All Developers |
| **ARCHITECTURE.md** | System design | Architects |
| **SPEC_FRONTEND.md** | Frontend details | Frontend Developers |
| **SPEC_RASPBERRY_PI.md** | Hardware details | Backend/Pi Developers |
| **REFACTORING_COMPLETE.md** | Phase 1 summary | Project Managers |
| **API_DOCUMENTATION.md** | Endpoint reference | API Consumers |
| **PROJECT_STRUCTURE.md** | This file | All |

---

## Next Steps (Post-Refactoring)

1. ✅ **Phase 1:** Modularize Flask Architecture (COMPLETE)
2. 🔄 **Phase 2:** Mobile App Integration (PLANNED)
3. 🔄 **Phase 3:** Advanced Analytics (PLANNED)
4. 🔄 **Phase 4:** Multi-Zone Expansion (PLANNED)

---

## Support & Contact

**Project Lead:** Dennis Westermann
**Email:** d.westermann@ol-mg.de
**Repository:** GrowPi Monorepo
**Status:** Active Development

---

**Last Updated:** 2025-12-06T19:19:00Z
**Schema Version:** Post-Refactoring v6.4
**Status:** Production-Ready
