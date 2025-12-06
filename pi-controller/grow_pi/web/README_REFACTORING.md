# GrowPi Web API - Phase 1 Refactoring

## Overview

This directory contains the refactored modular Flask application for the GrowPi controller system.

## Architecture

### Old Structure (api.py)
- **Single monolithic file**: `api.py` (~1000 lines)
- All routes, logic, and dependencies in one file
- Hard to test, maintain, and extend

### New Structure (Phase 1 - Modular)

```
grow_pi/web/
├── __init__.py                 # Package entry point (backward compatible)
├── app.py                      # Flask Application Factory
├── dependencies.py             # Centralized Dependency Injection
├── api.py                      # OLD implementation (backup, will be removed)
│
├── blueprints/                 # Modular API endpoints
│   ├── __init__.py
│   ├── status_bp.py           # /api/status, /api/health
│   ├── temperature_bp.py      # /api/temperature
│   ├── logs_bp.py             # /api/logs/*
│   ├── lamps_bp.py            # /api/lamp/<channel>
│   ├── mode_bp.py             # /api/mode
│   └── curves_bp.py           # /api/curves/*
│
├── services/                   # Hardware abstraction layer
│   ├── __init__.py
│   ├── lamp_config.py         # Lamp channel configuration
│   ├── hardware_service.py    # PWM & sensor abstraction
│   ├── logging_service.py     # Database logging abstraction
│   └── curve_service.py       # Curve & mode management
│
└── static/                     # Frontend files
    └── index.html
```

## Key Components

### 1. Application Factory (`app.py`)

Creates and configures the Flask application with all dependencies.

```python
from grow_pi.web.app import create_app, run_server

# Create app
app = create_app()

# Run server
run_server(app, host='0.0.0.0', port=5000)
```

**Features:**
- Dependency initialization
- Blueprint registration
- Error handling
- Static file serving
- Graceful shutdown

### 2. Dependency Injection (`dependencies.py`)

Centralized singleton access to all core services.

```python
from grow_pi.web import dependencies

# Get services
pwm = dependencies.get_pwm_controller()
sensor = dependencies.get_dht_sensor()
logger = dependencies.get_data_logger()
curves = dependencies.get_curve_controller()
mode_mgr = dependencies.get_mode_manager()

# Check availability
if dependencies.is_dht_available():
    temp, humidity = dependencies.get_dht_reader()()
```

**Why?**
- Blueprints don't directly import hardware modules
- Easy to mock for testing
- Single source of truth for all services

### 3. Blueprints (Modular Routes)

Each blueprint handles a specific domain:

| Blueprint | Endpoints | Purpose |
|-----------|-----------|---------|
| `status_bp` | `/api/status`, `/api/health` | System status |
| `temperature_bp` | `/api/temperature` | DHT22 sensor |
| `logs_bp` | `/api/logs/*` | Database queries |
| `lamps_bp` | `/api/lamp/<channel>` | PWM control |
| `mode_bp` | `/api/mode` | Auto/Manual mode |
| `curves_bp` | `/api/curves/*` | Lamp curves |

**Example Blueprint:**
```python
from flask import Blueprint, jsonify
from ..dependencies import get_pwm_controller

lamps_bp = Blueprint('lamps', __name__)

@lamps_bp.route('/api/lamp/<int:channel>', methods=['POST'])
def set_lamp(channel: int):
    pwm = get_pwm_controller()
    # ... handle request
    return jsonify({"success": True})
```

### 4. Services (Hardware Abstraction)

Services decouple blueprints from hardware implementations:

- **`lamp_config.py`**: Static channel definitions
- **`hardware_service.py`**: PWM & sensor wrapper functions
- **`logging_service.py`**: Database logging wrapper
- **`curve_service.py`**: Curve interpolation & mode management

**Example Service:**
```python
from grow_pi.web.services import set_lamp_intensity, PWM_AVAILABLE

if PWM_AVAILABLE:
    success = set_lamp_intensity(channel=1, intensity=75)
```

## Migration Guide

### For Developers

**Old Code:**
```python
# api.py
from grow_pi.lamps.pwm_controller import get_pwm_controller

@app.route('/api/lamp/<int:channel>', methods=['POST'])
def set_lamp(channel):
    pwm = get_pwm_controller()
    pwm.set_intensity(channel, intensity)
```

**New Code:**
```python
# blueprints/lamps_bp.py
from ..dependencies import get_pwm_controller

@lamps_bp.route('/api/lamp/<int:channel>', methods=['POST'])
def set_lamp(channel):
    pwm = get_pwm_controller()
    pwm.set_intensity(channel, intensity)
```

### Backward Compatibility

The `__init__.py` provides backward compatibility:

```python
# Still works!
from grow_pi.web import app, run_server
```

Internally, it:
1. Tries to import new `app.py`
2. Falls back to old `api.py` if import fails
3. Creates default app instance

## Testing

### Integration Test

```bash
cd pi-controller
source venv/bin/activate
python3 << 'EOF'
from grow_pi.web.app import create_app

app = create_app({'DEBUG': False})
print(f"Registered blueprints: {list(app.blueprints.keys())}")
print(f"Routes: {len(list(app.url_map.iter_rules()))}")
EOF
```

### Expected Output:
```
Registered blueprints: ['status', 'temperature', 'logs', 'lamps', 'mode', 'curves']
Routes: 18
```

## API Endpoints

All endpoints remain unchanged for backward compatibility:

### Status
- `GET /api/status` - Get all lamp values & sensor data
- `GET /api/health` - Health check with component availability

### Lamps
- `POST /api/lamp/<channel>` - Set lamp intensity (0-100)

### Sensors
- `GET /api/temperature` - Get current temperature & humidity

### Curves
- `GET /api/curves` - Get all lamp curves
- `GET /api/curves/<channel>` - Get curve for specific channel
- `PUT /api/curves/<channel>` - Update curve
- `GET /api/curves/preview` - 24h preview
- `GET /api/curves/intensities` - Current interpolated values

### Mode
- `GET /api/mode` - Get current mode (auto/manual)
- `POST /api/mode` - Switch mode

### Logs
- `GET /api/logs/sensors` - Sensor readings
- `GET /api/logs/lamps` - Lamp state changes
- `GET /api/logs/events` - System events
- `GET /api/logs/stats` - Database statistics

## Configuration

### Lamp Channels

Defined in `services/lamp_config.py`:

```python
LAMP_CHANNELS = {
    1: LampChannel(id=1, name="Far Red", color="#ff4444", gpio=16),
    2: LampChannel(id=2, name="Warm White", color="#ffbb44", gpio=13),
    3: LampChannel(id=3, name="Cool White", color="#88ddff", gpio=12),
    4: LampChannel(id=4, name="UV", color="#cc66ff", gpio=18),
}
```

Automatically loads from `config/config.yaml` if available.

## Running the Server

### Development Mode
```bash
cd pi-controller
source venv/bin/activate
python3 -m grow_pi.web.app
```

### Production Mode
```bash
cd pi-controller
source venv/bin/activate
python3 << 'EOF'
from grow_pi.web.app import create_app, run_server

app = create_app({'DEBUG': False})
run_server(app, host='0.0.0.0', port=5000)
EOF
```

## Next Steps (Phase 2)

- [ ] Remove old `api.py` after thorough testing
- [ ] Add unit tests for each blueprint
- [ ] Add integration tests for services
- [ ] Implement request validation middleware
- [ ] Add API versioning (v1, v2)
- [ ] Implement rate limiting
- [ ] Add OpenAPI/Swagger documentation

## Troubleshooting

### "No module named 'flask'"
```bash
pip install flask flask-cors PyYAML
```

### "PWM Controller running in SIMULATION MODE"
- Normal on development machine (no `pigpio` daemon)
- Will work on Raspberry Pi with `sudo pigpiod` running

### "Database module not available"
- Expected if database isn't configured
- Logs will be disabled, but API still works

### "Failed to initialize CurveController: No module named 'tinytuya'"
- Optional dependency for smart plug control
- Not needed for basic lamp operation

## Credits

**Refactored by**: Agent 15 (Main App Entry Point Integration)
**Date**: 2025-12-06
**Branch**: `refactoring/phase-1-modularization`
**API Version**: 2.0.0

---

**Previous Implementation**: `api.py` (preserved as backup)
**New Implementation**: Flask Application Factory with Blueprints
