# Blueprint Integration Example

This document shows how to integrate the new blueprints into `api.py`.

## Step 1: Import Blueprints

Add after the existing imports in `api.py`:

```python
# Import blueprints
from .blueprints import (
    temperature_bp, init_temperature_bp,
    logs_bp, init_logs_bp
)
```

## Step 2: Initialize Blueprints

Add after hardware initialization (around line 213):

```python
# Initialize Temperature Blueprint
init_temperature_bp(dht_sensor)

# Initialize Logs Blueprint
init_logs_bp(DB_AVAILABLE, data_logger, get_database)
```

## Step 3: Register Blueprints

Add before the route definitions (around line 327):

```python
# Register blueprints
app.register_blueprint(temperature_bp)
app.register_blueprint(logs_bp)
```

## Step 4: Remove Old Routes

After registering blueprints, you can remove these routes from `api.py`:

- `@app.route('/api/temperature')` (lines 432-450)
- `@app.route('/api/logs/sensors')` (lines 457-479)
- `@app.route('/api/logs/lamps')` (lines 482-504)
- `@app.route('/api/logs/events')` (lines 507-535)
- `@app.route('/api/logs/plugs')` (lines 538-559)
- `@app.route('/api/logs/stats')` (lines 562-574)

Also remove the `read_dht22()` helper function (lines 234-270) as it's now in the blueprint.

## Testing

After integration, test all endpoints:

```bash
# Temperature endpoint
curl http://localhost:5000/api/temperature

# Logs endpoints
curl http://localhost:5000/api/logs/sensors?hours=24
curl http://localhost:5000/api/logs/lamps?channel=1&hours=24
curl http://localhost:5000/api/logs/events?severity=error&hours=24
curl http://localhost:5000/api/logs/plugs?hours=24
curl http://localhost:5000/api/logs/stats
```

## Expected Response Format

All endpoints maintain the exact same response format as before:

### GET /api/temperature
```json
{
  "success": true,
  "temperature": 22.5,
  "humidity": 65.3,
  "unit_temperature": "°C",
  "unit_humidity": "%"
}
```

### GET /api/logs/sensors
```json
{
  "success": true,
  "readings": [...],
  "count": 100,
  "hours": 24
}
```

### GET /api/logs/lamps
```json
{
  "success": true,
  "logs": [...],
  "count": 50,
  "hours": 24
}
```

### GET /api/logs/events
```json
{
  "success": true,
  "events": [...],
  "count": 25,
  "hours": 24
}
```

### GET /api/logs/plugs
```json
{
  "success": true,
  "data": [...],
  "count": 75,
  "hours": 24
}
```

### GET /api/logs/stats
```json
{
  "success": true,
  "running": true,
  "sensor_readings": 1234,
  "lamp_logs": 567,
  "events": 89,
  ...
}
```
