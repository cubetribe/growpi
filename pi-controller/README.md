# GrowPi Controller & Web Backend

This directory contains the Python core controller, hardware drivers, SQLite database manager, and embedded Flask REST API for the Raspberry Pi.

---

## 🎯 Architecture Overview

```text
pi-controller/
├── grow_pi/
│   ├── main.py                     # Main controller daemon (grow-pi.service)
│   ├── config.py                   # YAML configuration loader
│   ├── database/
│   │   ├── db.py                   # SQLite manager (WAL, retries, retention, vacuum)
│   │   ├── logger.py               # Background DataLogger (sensors, lamps, plugs)
│   │   └── models.py               # Data models (dataclasses)
│   ├── lamps/
│   │   ├── pwm_controller.py       # pigpio PWM hardware driver & state sync
│   │   ├── curve_controller.py     # 24h curve calculation & interpolation
│   │   └── smart_plug_controller.py # Tuya / Local smart plug integration
│   ├── utils/
│   │   ├── sensor_cache.py         # DHT22 reader with pybreaker circuit breaker
│   │   ├── mode_manager.py         # Thread-safe Auto/Manual mode manager
│   │   └── dehumidifier_controller.py # Smart dehumidifier logic & safety limits
│   └── web/
│       ├── app.py                  # Flask Application Factory
│       ├── api.py                  # Web service runner (growpi-web.service)
│       ├── blueprints/             # Modular API endpoints
│       │   ├── lamps_bp.py         # /api/lamps
│       │   ├── curves_bp.py        # /api/curves
│       │   ├── temperature_bp.py   # /api/temperature
│       │   ├── status_bp.py        # /api/status & /api/health
│       │   ├── health_bp.py        # /api/health sub-routes
│       │   ├── dehumidifier_bp.py  # /api/dehumidifier
│       │   └── logs_bp.py          # /api/logs/*
│       └── static/                 # Embedded responsive Web UI (HTML5/CSS3/ES6)
├── config/
│   └── config.yaml                 # Active configuration
├── systemd/
│   ├── grow-pi.service             # Hardware controller daemon
│   └── growpi-web.service          # Web API & UI service
├── tests/
│   └── unit/                       # 168+ automated unit tests
├── requirements.txt                # Python dependencies
└── install.sh                      # Automated systemd installer
```

---

## ⚡ Key System Hardening Features

1. **Dual-Process Architecture**:
   - `grow-pi.service`: High-priority real-time hardware loop (pigpio PWM, curve interpolation, sensor polling, systemd watchdog).
   - `growpi-web.service`: Web interface and REST API on port `5000`.
   - Shared atomic state via `/run/growpi/pwm_state.json` and `/run/growpi/mode.txt` ensures zero flicker during web service restarts.

2. **Database Retention & Wear Leveling**:
   - Rolling 7-day retention (`cleanup_old_data`) prevents SQLite bloat on SD cards.
   - In-memory lamp deduplication reduces disk write cycles by **>90%**.
   - Automatic daily `VACUUM` defragmentation.

3. **Sensor Circuit Breaker (`pybreaker`)**:
   - Prevents system lockups if DHT22 sensor cables glitch or disconnect.
   - Automatically attempts self-healing reinitialization.

4. **Power & Undervoltage Health Monitoring**:
   - Real-time detection of Raspberry Pi power supply drops (`0x50005` throttled flags).
   - Instant visual alerts in the Web UI.

---

## 🧪 Running Unit Tests

```bash
# From the repository root:
PYTHONPATH=pi-controller pi-controller/venv/bin/pytest pi-controller/tests/unit -v
```

---

## 📄 License

MIT License — Copyright (c) 2026 Dennis Westermann.
