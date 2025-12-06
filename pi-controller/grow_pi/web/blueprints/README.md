# GrowPi API Blueprints

Modular Flask blueprints for the GrowPi Web API.

## Overview

This directory contains modularized API endpoints organized by functionality. Each blueprint handles a specific domain of the system.

## Available Blueprints

### 1. Temperature Blueprint (`temperature_bp.py`)

**Purpose**: DHT22 sensor data with intelligent caching

**Endpoints**:
- `GET /api/temperature` - Current temperature & humidity

**Features**:
- 3-second caching to protect sensor
- Automatic retry logic (3 attempts)
- Graceful fallback to last known value
- Mock data when sensor unavailable

**Response Format**:
```json
{
  "success": true,
  "temperature": 22.5,
  "humidity": 65.3,
  "unit_temperature": "°C",
  "unit_humidity": "%"
}
```

### 2. Logs Blueprint (`logs_bp.py`)

**Purpose**: Historical data query endpoints

**Endpoints**:
- `GET /api/logs/sensors` - Sensor reading history
- `GET /api/logs/lamps` - Lamp state changes
- `GET /api/logs/events` - System events
- `GET /api/logs/plugs` - Smart plug data
- `GET /api/logs/stats` - Database statistics

**Query Parameters** (common):
- `hours` (default: 24) - Hours of history
- `limit` (default: varies) - Max records returned

**Sensor Logs Parameters**:
- `type` (optional) - Filter by sensor type

**Lamp Logs Parameters**:
- `channel` (optional) - Filter by lamp channel (1-4)

**Event Logs Parameters**:
- `type` (optional) - Filter by event type
- `severity` (optional) - Filter by severity (info, warning, error)

**Response Formats**:

Sensors:
```json
{
  "success": true,
  "readings": [
    {
      "id": 1,
      "sensor_type": "temperature",
      "value": 22.5,
      "timestamp": "2025-12-06T10:30:00"
    }
  ],
  "count": 100,
  "hours": 24
}
```

Lamps:
```json
{
  "success": true,
  "logs": [
    {
      "id": 1,
      "channel": 1,
      "name": "Far Red",
      "intensity": 80,
      "source": "curve",
      "timestamp": "2025-12-06T10:30:00"
    }
  ],
  "count": 50,
  "hours": 24
}
```

Events:
```json
{
  "success": true,
  "events": [
    {
      "id": 1,
      "event_type": "startup",
      "severity": "info",
      "message": "System started",
      "details": {},
      "timestamp": "2025-12-06T10:00:00"
    }
  ],
  "count": 25,
  "hours": 24
}
```

Plugs:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "plug_id": "plug_1",
      "state": true,
      "power": 150.5,
      "voltage": 230.0,
      "current": 0.65,
      "timestamp": "2025-12-06T10:30:00"
    }
  ],
  "count": 75,
  "hours": 24
}
```

Stats:
```json
{
  "success": true,
  "running": true,
  "sensor_readings": 1234,
  "lamp_logs": 567,
  "events": 89,
  "plug_logs": 45,
  "database_size_mb": 2.5
}
```

## Blueprint Architecture

### Dependency Injection Pattern

All blueprints use dependency injection to receive shared instances (sensor, database, logger) from the main application:

```python
# In blueprint file
dht_sensor = None

def init_temperature_bp(dht_sensor_instance):
    global dht_sensor
    dht_sensor = dht_sensor_instance

# In api.py
from .blueprints import temperature_bp, init_temperature_bp

init_temperature_bp(dht_sensor)
app.register_blueprint(temperature_bp)
```

### Benefits

1. **Separation of Concerns**: Each blueprint handles one domain
2. **Testability**: Easy to mock dependencies
3. **Maintainability**: Smaller, focused files
4. **Reusability**: Blueprints can be used in different apps
5. **Type Safety**: Clear initialization contracts

## Error Handling

All endpoints follow the standardized response format:

**Success**:
```json
{
  "success": true,
  "data": {...}
}
```

**Error**:
```json
{
  "success": false,
  "error": "Error description"
}
```

HTTP Status Codes:
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `500` - Internal Server Error
- `503` - Service Unavailable (hardware/database not available)

## Testing

Test individual blueprints:

```bash
# Temperature
curl http://localhost:5000/api/temperature

# Sensor logs (last 24h)
curl http://localhost:5000/api/logs/sensors?hours=24

# Lamp logs (channel 1, last 12h)
curl http://localhost:5000/api/logs/lamps?channel=1&hours=12

# Events (errors only, last 48h)
curl http://localhost:5000/api/logs/events?severity=error&hours=48

# Plug logs (last 7 days)
curl http://localhost:5000/api/logs/plugs?hours=168

# Statistics
curl http://localhost:5000/api/logs/stats
```

## Future Blueprints

Planned modularization:

- [ ] `curves_bp.py` - Lamp curve management
- [ ] `mode_bp.py` - Auto/Manual mode switching
- [ ] `lamps_bp.py` - Lamp control endpoints
- [ ] `plugs_bp.py` - Smart plug control (when implemented)
- [ ] `config_bp.py` - System configuration

## Migration from Monolithic API

See `INTEGRATION_EXAMPLE.md` for step-by-step integration guide.

The migration maintains 100% backward compatibility - all endpoints keep the same URLs and response formats.
