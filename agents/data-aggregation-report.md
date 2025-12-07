# Data Aggregation / Downsampling Implementation Report

**Agent**: Opus 4.5
**Date**: 2025-12-07
**Task**: Implement intelligent downsampling for all log data

---

## Executive Summary

Successfully implemented query-time downsampling for all three data types (sensors, lamps, plugs) to enable unlimited data storage while maintaining fast chart rendering. The system automatically aggregates historical data based on the requested time range.

---

## Problem Statement

- Previous implementation used `limit=1000` for all queries
- With 6 plugs x 1 reading/minute = 360 entries/hour
- For 7 days: ~60,000 entries needed (impossible with limit=1000)
- Goal: Store data indefinitely for year-long views

---

## Solution: Query-Time Downsampling

### Downsampling Rules (Applied to ALL Data Types)

| Time Range | Resolution | SQL Strategy |
|------------|------------|--------------|
| 0-4 hours | Raw data (1 min) | No aggregation |
| 4-24 hours | 5-minute intervals | AVG() GROUP BY 5-min bucket |
| 1-7 days | 15-minute intervals | AVG() GROUP BY 15-min bucket |
| 7-30 days | 30-minute intervals | AVG() GROUP BY 30-min bucket |
| >30 days | 1-hour intervals | AVG() GROUP BY hour |

### Key Design Decisions

1. **Always use AVG()** - Never MIN/MAX/FIRST/LAST. Averages provide the most representative data for visualization.

2. **Round appropriately**:
   - Temperature/Humidity: 2 decimal places
   - Power (W): 1 decimal place
   - Voltage (V): 1 decimal place
   - Current (A): 3 decimal places
   - Lamp Intensity: Integer (0-100)

3. **No limit on queries** - Backend automatically reduces data volume through aggregation.

---

## Files Modified

### 1. `/pi-controller/grow_pi/database/db.py`

Added three new methods:

#### `get_sensor_readings_downsampled(sensor_type, hours)`
```python
def get_sensor_readings_downsampled(
    self,
    sensor_type: Optional[str] = None,
    hours: int = 24
) -> List[Dict[str, Any]]:
    """
    Get sensor readings with intelligent downsampling based on time range.
    Returns list of dicts with: sensor_type, value, unit, created_at
    """
```

#### `get_lamp_state_log_downsampled(channel, hours)`
```python
def get_lamp_state_log_downsampled(
    self,
    channel: Optional[int] = None,
    hours: int = 24
) -> List[Dict[str, Any]]:
    """
    Get lamp state log entries with intelligent downsampling.
    Returns list of dicts with: channel, name, intensity, source, curve_time, created_at
    """
```

#### `get_plug_logs_downsampled(device_id, hours)`
```python
def get_plug_logs_downsampled(
    self,
    device_id: Optional[str] = None,
    hours: int = 24
) -> List[Dict[str, Any]]:
    """
    Get plug logs with intelligent downsampling.
    Returns list of dicts with: device_id, voltage, current, power, created_at
    """
```

### 2. `/pi-controller/grow_pi/web/blueprints/logs_bp.py`

Updated all three log endpoints to use downsampled methods:

- `GET /api/logs/sensors` - Now uses `get_sensor_readings_downsampled()`
- `GET /api/logs/lamps` - Now uses `get_lamp_state_log_downsampled()`
- `GET /api/logs/plugs` - Now uses `get_plug_logs_downsampled()`

**API Response now includes**:
```json
{
    "success": true,
    "readings": [...],
    "count": 1234,
    "hours": 168,
    "downsampled": true
}
```

### 3. `/pi-controller/grow_pi/web/static/js/api.js`

Removed `limit` parameter from API calls:
- `getSensorLogs(type, hours)` - was `getSensorLogs(type, hours, limit)`
- `getLampLogs(channel, hours)` - was `getLampLogs(channel, hours, limit)`
- `getPlugLogs(hours)` - was `getPlugLogs(hours, limit)`

### 4. `/pi-controller/grow_pi/web/static/js/modules/history.js`

Updated `loadHistoryData()` to not pass limit parameter:
```javascript
const [temps, hums, plugs] = await Promise.all([
    GrowPiAPI.getSensorLogs('temperature', hours),
    GrowPiAPI.getSensorLogs('humidity', hours),
    GrowPiAPI.getPlugLogs(hours)
]);
```

---

## SQL Query Examples

### 5-Minute Bucket Aggregation (SQLite)
```sql
SELECT
    sensor_type,
    AVG(value) as avg_value,
    unit,
    strftime('%Y-%m-%dT%H:', created_at) ||
        printf('%02d', (CAST(strftime('%M', created_at) AS INTEGER) / 5) * 5) ||
        ':00' as time_bucket
FROM sensor_readings
WHERE created_at >= ? AND created_at < ?
GROUP BY sensor_type, time_bucket, unit
ORDER BY time_bucket DESC
```

### Time Bucket Calculation
- **5-min**: `(minutes / 5) * 5` -> 0, 5, 10, 15...
- **15-min**: `(minutes / 15) * 15` -> 0, 15, 30, 45
- **30-min**: `(minutes / 30) * 30` -> 0, 30
- **Hourly**: `strftime('%Y-%m-%dT%H:00:00', created_at)`

---

## Data Volume Comparison

### Before (limit=1000)
| Range | Max Records | Coverage |
|-------|-------------|----------|
| 24h | 1000 | ~16h (2 sensors) |
| 7d | 1000 | ~16h (2 sensors) |
| 30d | 1000 | ~16h (2 sensors) |

### After (Downsampled)
| Range | Est. Records per Sensor | Coverage |
|-------|------------------------|----------|
| 24h | ~240 (raw) + ~240 (5min) | Full 24h |
| 7d | ~240 (raw) + ~240 (5min) + ~672 (15min) | Full 7d |
| 30d | ~240 + ~240 + ~672 + ~1104 | Full 30d |
| 1y | ~2296 + ~8760 (hourly) | Full year |

---

## Deployment Instructions

### Deploy Python Files (Backend)
```bash
# Copy db.py
sshpass -p 'Mi83xer#' scp /Users/denniswestermann/Desktop/Coding\ Projekte/GrowPi/pi-controller/grow_pi/database/db.py admin@192.168.0.86:/opt/grow-pi/grow_pi/database/db.py

# Copy logs_bp.py
sshpass -p 'Mi83xer#' scp /Users/denniswestermann/Desktop/Coding\ Projekte/GrowPi/pi-controller/grow_pi/web/blueprints/logs_bp.py admin@192.168.0.86:/opt/grow-pi/grow_pi/web/blueprints/logs_bp.py
```

### Deploy JavaScript Files (Frontend)
```bash
# Copy api.js
sshpass -p 'Mi83xer#' scp /Users/denniswestermann/Desktop/Coding\ Projekte/GrowPi/pi-controller/grow_pi/web/static/js/api.js admin@192.168.0.86:/opt/grow-pi/grow_pi/web/static/js/api.js

# Copy history.js
sshpass -p 'Mi83xer#' scp /Users/denniswestermann/Desktop/Coding\ Projekte/GrowPi/pi-controller/grow_pi/web/static/js/modules/history.js admin@192.168.0.86:/opt/grow-pi/grow_pi/web/static/js/modules/history.js
```

### Restart Service (ONLY after user approval!)
```bash
sshpass -p 'Mi83xer#' ssh admin@192.168.0.86 "sudo systemctl restart grow-pi"
```

---

## Testing Recommendations

1. **Test 24h view** - Should show smooth, detailed charts
2. **Test 7d view** - Should show aggregated but still detailed data
3. **Test 30d view** - Should work without timeout
4. **Check console** - Should see `"downsampled": true` in API responses
5. **Compare averages** - Spot-check that averages are reasonable

---

## Future Enhancements

1. **Add 1-year range button** - UI currently has 24h, 7d, 30d
2. **Pre-aggregate for performance** - Store hourly aggregates in separate table
3. **Data retention policy** - Optional cleanup of very old raw data
4. **Export functionality** - Allow CSV export of historical data

---

## Status

- [x] Sensor readings downsampling implemented
- [x] Lamp state log downsampling implemented
- [x] Plug logs downsampling implemented
- [x] API endpoints updated
- [x] Frontend JS updated
- [ ] Deployed to Pi (awaiting user approval)
- [ ] Service restart (awaiting user approval)
- [ ] Tested with real data

---

**Report generated by Opus 4.5 Agent**
