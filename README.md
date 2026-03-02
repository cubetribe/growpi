# GrowPi - Greenhouse Management System

Professional greenhouse automation and monitoring platform powered by Raspberry Pi.

**Live Demo**: http://growpi.nm-forum.de
**Version**: v6.25.2 (2026-03-02)
**Status**: Production-Ready

> **Note**: This repository contains the **Raspberry Pi backend** (pi-controller).
> The **Next.js Web Frontend** has been moved to: [cubetribe/growpi_web_public](https://github.com/cubetribe/growpi_web_public)

---

## Features

### Real-time Monitoring
- **Environmental Sensors**: Temperature, Humidity, Soil metrics (DHT22)
- **4-Channel LED Control**: Far Red, Warm White, Cool White, UV
- **Smart Automation**: Custom light curves with linear interpolation
- **Energy Tracking**: Real-time electricity consumption monitoring (v6.3)
- **Dehumidifier Control**: Automated humidity management (v6.4)

### Web Interface
- **Responsive Dashboard**: Optimized for mobile and desktop
- **Live Charts**: 24h sensor data visualization (Recharts)
- **Curve Editor**: Visual light schedule designer
- **Cost Analysis**: Device-level energy consumption breakdown
- **Camera Integration**: Live plant monitoring
- **i18n**: German / English language support

---

## System Architecture (v6.5)

### Frontend (Modular - 408 LOC)
```
static/js/
├── api.js          # Centralized API client (GrowPiAPI class)
├── state.js        # Global state management (Pub/Sub)
├── utils.js        # Tab switching + notifications
└── modules/
    ├── control.js      # Manual lamp control
    ├── curves.js       # Curve editor (450 LOC)
    ├── history.js      # Sensor charts
    ├── environment.js  # Environment monitoring
    ├── costs.js        # Energy cost tracking (NEW v6.3)
    ├── room.js         # Dehumidifier control (NEW v6.4)
    └── camera.js       # Camera module
```

### Backend (8 Flask Blueprints)
```
grow_pi/
├── controllers/
│   ├── lamp_controller.py
│   ├── sensor_controller.py
│   └── dehumidifier_controller.py
├── web/
│   ├── app.py (Flask app factory)
│   └── blueprints/
│       ├── health_bp.py      # /api/health
│       ├── status_bp.py      # /api/status
│       ├── lamp_bp.py        # /api/lamp/*
│       ├── curves_bp.py      # /api/curves/*
│       ├── logs_bp.py        # /api/logs/*
│       ├── costs_bp.py       # /api/costs/* (NEW)
│       ├── dehumidifier_bp.py # /api/room/* (NEW)
│       └── camera_bp.py      # /api/camera/*
└── utils/
    ├── database.py
    ├── mode_manager.py
    └── config_manager.py
```

---

## Quick Start

### Requirements
- Raspberry Pi 3B+ or higher
- Python 3.9+
- DHT22 sensor (GPIO 4)
- 4-Channel PWM LED driver

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/GrowPi.git
cd GrowPi

# Install backend
cd pi-controller
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start server
python -m grow_pi.web.api
```

### Automatic Pi Deployment (GitHub Actions)

This repository supports auto-deploy to Raspberry Pi via a **self-hosted GitHub Actions runner**.

- Workflow: `.github/workflows/pi-autodeploy.yml`
- Deploy script: `scripts/pi/github_runner_deploy.sh`
- Setup guide: `docs/GITHUB_ACTIONS_PI_AUTODEPLOY.md`

Important:
- No inbound router ports are required.
- The Pi runner connects outbound to GitHub over HTTPS and executes jobs locally.
- GitHub Actions shows direct PASS/FAIL feedback from the Pi deployment.

### Access Web Interface

```
http://192.168.0.86:5000
```

---

## Hardware Configuration

### Raspberry Pi 3B+
- **Hostname**: growpi
- **IP**: 192.168.0.86
- **SSH**: Port 22 (admin user)

### GPIO Pin Assignment (FINAL)

| Channel | Name | GPIO | Pin | Status |
|---------|------|------|-----|--------|
| 1 | Far Red | 16 | 36 | Active |
| 2 | Warm White | 13 | 33 | Active |
| 3 | Cool White | 18 | 12 | Active |
| 4 | UV | 12 | 32 | Active |
| - | DHT22 Sensor | 4 | 7 | Verified |

---

## API Endpoints

### Core Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | System health check |
| `/api/status` | GET | Temperature, humidity, lamp status |
| `/api/curves` | GET | Get all lamp curves |
| `/api/curves/<channel>` | PUT | Update lamp curve |

### Cost Tracking (v6.3)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/costs?period=today` | GET | Energy consumption |
| `/api/costs/config` | GET | kWh price configuration |
| `/api/costs/config` | POST | Update kWh price |

### Room Control (v6.4)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/room` | GET | Dehumidifier status |
| `/api/room/config` | GET | Automation config |
| `/api/room/toggle` | POST | Manual override |

### Logging (v6.16 - Downsampling)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/logs/sensors` | GET | Sensor readings (downsampled) |
| `/api/logs/lamps` | GET | Lamp state changes (downsampled) |
| `/api/logs/plugs` | GET | Smart plug power data (downsampled) |
| `/api/logs/events` | GET | System events |
| `/api/logs/stats` | GET | Logging statistics |

---

## Testing

```bash
# Run all unit tests
cd pi-controller
source venv/bin/activate
pytest tests/ -v --cov=grow_pi

# Expected: 140/140 tests PASSED (93% coverage)
```

```bash
# Smoke tests (requires running server)
cd pi-controller
./smoke_test.sh http://localhost:5000

# Expected: 14/14 API endpoints passing
```

---

## Recent Updates

### v6.16.0 (2025-12-08) - Critical Bug Fixes

**Bug Fixes:**
- Humidity Control Race-Condition (Input-Werte sprangen während Bearbeitung)
- Stromverbrauchs-Historie zeigte nur 2-3h statt 24h+ Daten

**API Improvements:**
- Alle `/api/logs/*` Routes zu Blueprint-Architektur migriert
- Intelligentes Downsampling für große Zeitbereiche
- Keine hardcoded Limits mehr

**Previous:**
- v6.15.0: Interactive Bezier Curve Editor
- v6.14.0: Room Control Verification
- v6.13.0: Status-Desync Fix

See [CHANGELOG.md](CHANGELOG.md) for complete history.

---

## Project Structure

```
GrowPi/
├── pi-controller/          # Raspberry Pi Backend
│   ├── grow_pi/
│   │   ├── controllers/    # Hardware controllers
│   │   ├── database/       # SQLite + migrations
│   │   ├── web/            # Flask app + blueprints
│   │   │   ├── blueprints/ # API endpoints
│   │   │   └── static/     # Embedded web UI
│   │   └── utils/          # Utilities
│   ├── tests/              # Unit tests (140 tests)
│   └── smoke_test.sh       # API smoke tests
├── docs/                   # Documentation
│   ├── ARCHITECTURE.md
│   ├── ROADMAP.md
│   └── DEPLOYMENT_GUIDE.md
├── agents/                 # AI Agent reports
├── CHANGELOG.md            # Version history
└── CLAUDE.md               # Claude Code instructions
```

> **Frontend**: The Next.js web dashboard is in a separate repository:
> [cubetribe/growpi_web_public](https://github.com/cubetribe/growpi_web_public)

---

## Development

### Git Workflow
- **Main Branch**: Production-ready code
- **Feature Branches**: `feature/feature-name`
- **Refactoring**: `refactoring/phase-X`

### Code Standards
- Python: PEP 8, type hints
- JavaScript: ES6+, no external dependencies
- Tests: pytest with fixtures

### Contributing
1. Fork the repository
2. Create feature branch
3. Run tests (`pytest`)
4. Submit pull request

---

## Documentation

- [CHANGELOG.md](CHANGELOG.md) - Complete version history
- [CLAUDE.md](CLAUDE.md) - Development instructions
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design
- [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) - Deployment steps
- [docs/HARDWARE_PINOUT.md](docs/HARDWARE_PINOUT.md) - GPIO configuration

---

## Tech Stack

### Backend (Raspberry Pi) - This Repository
- **Runtime**: Python 3.13
- **Framework**: Flask + Blueprints
- **GPIO**: pigpio (hardware PWM)
- **Sensors**: adafruit-circuitpython-dht
- **Database**: SQLite (local logging)

### Frontend (Separate Repository)
- **Repository**: [cubetribe/growpi_web_public](https://github.com/cubetribe/growpi_web_public)
- **Framework**: Next.js 13.5.1 (App Router)
- **Language**: TypeScript (strict mode)
- **Database**: PostgreSQL (Prisma ORM)
- **UI**: shadcn/ui + TailwindCSS

---

## Support

**Developer**: Dennis Westermann (d.westermann@ol-mg.de)
**Project Status**: Active Development
**License**: Proprietary

---

## Acknowledgments

Built with:
- Flask (Web framework)
- pigpio (GPIO control)
- SQLite (Data storage)
- Recharts (Charting)
- Vanilla JS (Frontend modules)

Orchestrated with Claude Code (17 parallel agents for v6.5 refactoring)

---

**Last Updated**: 2025-12-08
**Version**: v6.16.0
