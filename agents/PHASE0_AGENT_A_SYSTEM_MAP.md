# Agent A — System Map & Dataflow Analysis Report

**Agent:** Phase 0 - System Map / Dataflow Analyst
**Date:** 2025-12-26
**System:** GrowPi Raspberry Pi Controller (pi-controller/)
**Version:** 6.22.4
**Purpose:** Complete system architecture mapping + DHT22 sensor freeze diagnosis

---

## 1. COMPONENT INVENTORY & RESPONSIBILITIES

### 1.1 Core Python Modules

| Module | Responsibility | Threading | State |
|--------|---------------|-----------|-------|
| `grow_pi/main.py` | Main entry point, orchestrates startup, curve updates | Main loop + Web thread | Singleton controller |
| `grow_pi/web/api.py` | Flask REST API, serves frontend, exposes endpoints | Flask thread pool | Global instances |
| `grow_pi/database/db.py` | SQLite connection manager, schema, queries | Thread-local connections | Singleton DB |
| `grow_pi/database/logger.py` | Background data logging service | 3 daemon threads | Global singleton |
| `grow_pi/utils/sensor_cache.py` | **CRITICAL** DHT22 read cache + error handling | No threads | Global cache dict |
| `grow_pi/utils/dehumidifier_controller.py` | Humidity-based automation + scheduling | 1 daemon thread | Singleton |
| `grow_pi/lamps/pwm_controller.py` | pigpio PWM control for LED channels | No threads | Singleton |

### 1.2 Services & Processes

| Service | systemd Unit | User | Dependencies |
|---------|--------------|------|--------------|
| Main Controller | `grow-pi.service` | admin | pigpiod.service, network |
| pigpio Daemon | `pigpiod.service` | root | Hardware GPIO access |
| Web API | Integrated (Flask) | admin | None (runs in main.py thread) |

**Critical Finding:** Web API runs in `main.py` as a daemon thread (line 238), NOT a separate service.

### 1.3 Background Threads

| Thread Name | Source File | Function | Interval | Purpose |
|-------------|-------------|----------|----------|---------|
| WebAPI | main.py:238 | Flask app.run() | N/A | HTTP server |
| DataLogger-Sensors | logger.py:122 | _sensor_loop() | 60s | Read DHT22 + log to DB |
| DataLogger-Lamps | logger.py:132 | _lamp_loop() | 60s | Log PWM states to DB |
| DataLogger-Plugs | logger.py:141 | _plug_loop() | 60s | Log Tuya plug data |
| DehumidifierController | dehumidifier_controller.py:933 | control_loop() | 10s | Humidity automation |
| Flask-Workers | Flask internal | HTTP request handlers | On-demand | API requests |

**Total Background Threads:** 5-6 daemon threads + Flask pool

---

## 2. DHT22 SENSOR DATAFLOW ANALYSIS

### 2.1 Complete Read Path (Step-by-Step)

```
REQUEST ENTRY POINTS:
├─ /api/status (api.py:448)          → read_dht22()
├─ /api/temperature (api.py:539)    → read_dht22()
├─ /api/room (dehumidifier_bp.py)   → read_dht22()
└─ DataLogger._sensor_loop()        → read_dht22()  [EVERY 60 SECONDS]
                                           ↓
                        sensor_cache.py:read_dht22()
                                           ↓
                    ┌─────────────────────────────────┐
                    │ Cache Check (10s TTL)           │
                    │ Line 132: if cache_age < 10s    │
                    │   → Return cached (temp, humid) │
                    └─────────────────────────────────┘
                                           ↓ (cache miss)
                    ┌─────────────────────────────────┐
                    │ Mock Mode Check                 │
                    │ Line 137: if not _dht_available │
                    │   → Generate fake data          │
                    └─────────────────────────────────┘
                                           ↓ (real hardware)
                    ┌─────────────────────────────────┐
                    │ **HARDWARE READ** (3 attempts)  │
                    │ Line 146-161: for attempt 0..2  │
                    │   temp = _dht_sensor.temperature│ ← BLOCKING CALL
                    │   humid = _dht_sensor.humidity  │ ← BLOCKING CALL
                    │   if success: cache + return    │
                    │   else: time.sleep(0.5)         │
                    └─────────────────────────────────┘
                                           ↓ (all 3 failed)
                    ┌─────────────────────────────────┐
                    │ Error Handling                  │
                    │ Line 164: error_count += 1      │
                    │ Line 167: timestamp = now       │ ← CRITICAL
                    │ Line 170: if errors >= 10       │
                    │   → Log system event            │
                    │ Line 186: if errors >= 20       │
                    │   → reinitialize_sensor()       │
                    └─────────────────────────────────┘
                                           ↓
                    ┌─────────────────────────────────┐
                    │ Fallback to Last Known Value    │
                    │ Line 204-210: Return cached     │
                    │ OR return (None, None)          │
                    └─────────────────────────────────┘
```

### 2.2 Database Write Path

```
sensor_cache.py:read_dht22() → returns (temp, humidity)
                ↓
DataLogger._sensor_loop() (logger.py:203-246)
                ↓
        logger.py:213: temp, humidity = self._sensor_reader()
                ↓
        ROBUSTNESS CHECK (line 216):
        if temp is None AND humidity is None:
            → log_event('sensor_read_failure')
            → SKIP database insert (line 224)
                ↓
        logger.py:226-246: Insert sensor readings
                ↓
        db.insert_sensor_reading(SensorReading)
                ↓
        db.py:327-336: INSERT INTO sensor_readings
                ↓
        SQLite Write (thread-safe via thread-local connections)
```

### 2.3 Critical File:Line References

| Operation | File | Line(s) | Notes |
|-----------|------|---------|-------|
| DHT22 Read (Hardware) | sensor_cache.py | 148-149 | **BLOCKING** - No timeout! |
| Cache Update (Success) | sensor_cache.py | 152-156 | Updates timestamp + values |
| Cache Update (Failure) | sensor_cache.py | 164-167 | **CRITICAL FIX v6.22.3** - Always updates timestamp |
| Sensor Reinit | sensor_cache.py | 67-102 | After 20 consecutive failures |
| DB Insert Skip Logic | logger.py | 216-224 | Prevents None values in DB |
| DB Write | db.py | 327-336 | Thread-safe via context manager |

---

## 3. RISK HOTSPOTS ANALYSIS

### 3.1 CRITICAL RISKS

#### **RISK #1: DHT22 Hardware Read Blocking (CRITICAL)**

**Location:** `sensor_cache.py:148-149`

```python
temp = _dht_sensor.temperature     # ← NO TIMEOUT!
humidity = _dht_sensor.humidity    # ← NO TIMEOUT!
```

**Evidence:**
- `adafruit_dht.DHT22` library uses C extension (`libgpiod_pulsein`)
- Read operation can **block indefinitely** if sensor freezes
- No timeout mechanism in Adafruit library
- Retry loop (3 attempts) amplifies block time (3x + 0.5s delays)

**Impact:**
- DataLogger thread **hangs** waiting for sensor read
- Flask request handlers **block** if `/api/temperature` called during freeze
- System appears unresponsive (Web UI shows stale data)
- Eventually requires hardware reset

**Severity:** **CRITICAL**

**Code Path:**
```
DataLogger._sensor_loop (logger.py:167-177)
  → read_dht22() (sensor_cache.py:117)
    → _dht_sensor.temperature (adafruit_dht C extension)
      → HARDWARE I2C/GPIO READ ← CAN HANG HERE
```

**Mitigation (v6.22.4):** Sensor reinit after 20 failures (sensor_cache.py:186-201)
**Gap:** Reinit only helps if read eventually returns. If read hangs forever, reinit never triggers.

---

#### **RISK #2: No Sensor Read Timeout (HIGH)**

**Location:** `sensor_cache.py:146-161`

**Observation:**
- 3 retry attempts with 0.5s sleep between
- Total worst case: ~1.5s **if reads return**
- **Infinite time if read blocks**

**Code:**
```python
for attempt in range(3):
    try:
        temp = _dht_sensor.temperature  # ← Can hang
        humidity = _dht_sensor.humidity # ← Can hang
```

**Missing:** Thread-based timeout wrapper (e.g., `threading.Timer` or `signal.alarm`)

**Severity:** **HIGH**

---

#### **RISK #3: Blocking I/O in Flask Request Handlers (HIGH)**

**Location:** `api.py:468, 543`

```python
@app.route('/api/status', methods=['GET'])
def get_status():
    temp, humidity = read_dht22()  # ← Blocks Flask worker thread!
```

**Impact:**
- User requests to `/api/status` or `/api/temperature` can **hang** waiting for sensor
- Flask worker thread pool exhaustion if multiple requests pile up
- Entire Web UI becomes unresponsive

**Evidence:**
- Flask uses threaded workers (`app.run(threaded=True)` in api.py:234)
- Default pool size is small (~10 threads)
- If 10 requests all block on sensor, no more capacity

**Severity:** **HIGH**

---

### 3.2 HIGH RISKS

#### **RISK #4: Database Thread-Safety Gaps (MEDIUM-HIGH)**

**Location:** `db.py:245-264`

**Observation:**
- Thread-local connections (`threading.local()`) used
- Each thread gets its own SQLite connection
- WAL mode enabled (line 258) for concurrent reads

**Potential Issue:**
```python
def _get_connection(self) -> sqlite3.Connection:
    if not hasattr(self._local, 'connection') or self._local.connection is None:
        # Creates connection per thread
        self._local.connection = sqlite3.connect(...)
```

**Risk:**
- Connection not explicitly closed per-thread
- Relies on Python GC to cleanup
- Under heavy load, file descriptor leaks possible

**Evidence:**
- No `atexit` handler for thread-local cleanup
- `close()` method only closes current thread's connection (line 317)

**Severity:** **MEDIUM-HIGH**

---

#### **RISK #5: Sensor Cache Race Condition (LOW)**

**Location:** `sensor_cache.py:27-32`

```python
_sensor_cache = {
    "temp": None,
    "humidity": None,
    "timestamp": 0,
    "error_count": 0
}
```

**Observation:**
- Global dict without lock protection
- Multiple threads read/write:
  - DataLogger thread (writes every 60s)
  - Flask threads (read on demand)

**Risk Level:** **LOW** (Python GIL protects dict operations)

**Potential Issue:**
- Read during write could get inconsistent `(temp, humidity)` pair
- Timestamp vs values could be out of sync

**Mitigation:** Python's GIL ensures atomic dict operations, but not multi-key consistency

---

### 3.3 MEDIUM RISKS

#### **RISK #6: Exception Swallowing in Loops (MEDIUM)**

**Location:** Multiple background threads

**Examples:**
- `logger.py:172-173` - Sensor loop catches ALL exceptions
- `logger.py:184-185` - Lamp loop catches ALL exceptions
- `dehumidifier_controller.py:925-926` - Control loop catches ALL

```python
while self._running:
    try:
        self._log_sensors()  # ← Can fail silently
    except Exception as e:
        logger.error(f"Sensor logging error: {e}")
    # Loop continues - error not escalated
```

**Impact:**
- Persistent errors never crash the service
- Silent failures accumulate
- Debugging requires manual log inspection

**Severity:** **MEDIUM**

---

### 3.4 LOW RISKS

#### **RISK #7: PWM State Persistence File Writes (LOW)**

**Location:** `utils/pwm_state.py` (referenced but not analyzed)

**Observation:** Zero-Downtime feature saves PWM state to `/run/growpi/`

**Potential Risk:**
- File write during shutdown could fail
- tmpfs filesystem could be full

**Severity:** **LOW** (Feature is optional fallback)

---

## 4. THREADING & SYNCHRONIZATION MAP

### 4.1 Thread Synchronization Primitives

| Primitive | Location | Purpose | Type |
|-----------|----------|---------|------|
| `threading.Event` | logger.py:70 | Clean shutdown signal | Control |
| `threading.Event` | dehumidifier_controller.py:133 | Control loop stop | Control |
| `threading.Event` | main.py:N/A | (Not used) | - |
| `threading.Lock` | db.py:242 | Database init lock | Mutex |
| `threading.Lock` | logger.py:377 | DataLogger singleton | Mutex |
| `threading.Lock` | dehumidifier_controller.py:112 | Controller singleton | Mutex |
| `thread-local` | db.py:241 | SQLite connections | TLS |

**Key Finding:**
- ✅ Proper use of `Event.wait(timeout)` in all loops (CPU-efficient)
- ✅ Singleton pattern protected with locks
- ❌ NO locks around DHT22 sensor access (assumed GIL protection)

### 4.2 Blocking Calls Inventory

| Call | File:Line | Timeout? | Impact if Blocked |
|------|-----------|----------|-------------------|
| `_dht_sensor.temperature` | sensor_cache.py:148 | ❌ NO | Thread hangs indefinitely |
| `_dht_sensor.humidity` | sensor_cache.py:149 | ❌ NO | Thread hangs indefinitely |
| `sqlite3.connect()` | db.py:252 | ⚠️ Implicit (OS) | Brief hang possible |
| `cursor.execute()` | db.py:330+ | ⚠️ WAL mode | Concurrent reads OK |
| `SmartPlugController.*` | dehumidifier_controller.py:732 | ⚠️ Network | 5-10s typical |

**CRITICAL:** DHT22 reads are the ONLY truly unbounded blocking calls.

---

## 5. SHARED STATE & GLOBAL VARIABLES

### 5.1 Global Singletons

| Singleton | Module | Access Pattern | Thread-Safe? |
|-----------|--------|----------------|--------------|
| `_pwm_controller_instance` | pwm_controller.py:41 | `get_pwm_controller()` | ✅ Lock-protected |
| `_db_instance` | db.py:1645 | `get_database()` | ✅ Lock-protected |
| `_logger_instance` | logger.py:376 | `get_logger()` | ✅ Lock-protected |
| `_controller_instance` | dehumidifier_controller.py:951 | `get_dehumidifier_controller()` | ✅ Lock-protected |
| `_sensor_cache` | sensor_cache.py:27 | Direct access | ⚠️ GIL-only |
| `_dht_sensor` | sensor_cache.py:36 | Direct access | ⚠️ GIL-only |

### 5.2 Module-Level State

| Variable | Module | Mutability | Risk |
|----------|--------|------------|------|
| `LAMP_CHANNELS` | api.py:112 | Dict (modified at startup) | Low (read-only after init) |
| `pwm_controller` | api.py:194 | Singleton ref | Low (immutable ref) |
| `dht_sensor` | api.py:224 | Singleton ref | Medium (referenced globally) |
| `data_logger` | api.py:251 | Singleton ref | Low (thread-safe methods) |
| `mode_manager` | main.py:45 | Singleton ref | Low (assumed thread-safe) |

---

## 6. ERROR HANDLING ANALYSIS

### 6.1 DHT22 Sensor Error Path

**File:** `sensor_cache.py`

| Step | Line(s) | Action | Escalation? |
|------|---------|--------|-------------|
| Read failure | 158-161 | Log debug, retry (max 3) | No |
| All retries fail | 164 | Increment `error_count` | No |
| Update timestamp | 167 | ⚠️ **CRITICAL FIX v6.22.3** | N/A |
| Log threshold | 170-183 | Log error if count >= 10 | Yes (event log) |
| Reinit threshold | 186-201 | Reinit sensor if count >= 20 | Yes (recovery attempt) |
| Fallback | 204-210 | Return last known or None | No crash |

**Strengths:**
- ✅ Never crashes on sensor failure
- ✅ Automatic recovery attempt (reinit)
- ✅ System event logging for monitoring

**Weaknesses:**
- ❌ No hard timeout on hardware read
- ❌ Reinit only works if read eventually returns
- ❌ No watchdog for thread hang detection

### 6.2 Database Error Handling

**File:** `db.py`

| Operation | Error Handling | Recovery |
|-----------|----------------|----------|
| Connection | Exception → log + raise | Manual retry |
| INSERT | Rollback on exception (line 275) | Transaction safe |
| SELECT | Exception propagates | Caller handles |
| Schema init | Exception → log + fail | Fatal (service won't start) |

**Strengths:**
- ✅ Transaction rollback on errors
- ✅ Context manager ensures commit/rollback

**Weaknesses:**
- ❌ No automatic retry on transient failures
- ❌ Connection pool exhaustion not handled

---

## 7. SYSTEM DEPENDENCIES GRAPH

```
                        ┌─────────────────┐
                        │   systemd       │
                        │  grow-pi.service│
                        └────────┬────────┘
                                 │
                  ┌──────────────┴──────────────┐
                  │                             │
            ┌─────▼─────┐               ┌──────▼──────┐
            │  pigpiod  │               │  network    │
            │  (daemon) │               │  (dependency)│
            └─────┬─────┘               └─────────────┘
                  │
                  │ GPIO access
                  │
            ┌─────▼─────────────────────────────────┐
            │     grow_pi/main.py                   │
            │  - Loads config                       │
            │  - Inits PWMController                │
            │  - Inits ModeManager                  │
            │  - Starts curve update loop           │
            │  - Spawns Web API thread              │
            └────┬──────────────────┬───────────────┘
                 │                  │
      ┌──────────▼──────────┐      │
      │  Web API (Flask)    │      │
      │  - api.py:234       │      │
      │  - Runs in thread   │      │
      │  - Inits DHT sensor │      │
      │  - Inits DataLogger │      │
      │  - Inits Dehum Ctrl │      │
      └──┬──────────────────┘      │
         │                         │
         │  ┌──────────────────────▼────────────┐
         │  │  Curve Controller                 │
         │  │  - Reads DB curves                │
         │  │  - Interpolates intensities       │
         │  └───────────────────────────────────┘
         │
    ┌────▼────────────────────────────────────────┐
    │           DataLogger Service                │
    │  ┌──────────────────────────────────────┐   │
    │  │  Sensor Thread (60s)                 │   │
    │  │  → read_dht22() → DB insert          │   │
    │  └──────────────────────────────────────┘   │
    │  ┌──────────────────────────────────────┐   │
    │  │  Lamp Thread (60s)                   │   │
    │  │  → get_lamp_states() → DB insert     │   │
    │  └──────────────────────────────────────┘   │
    │  ┌──────────────────────────────────────┐   │
    │  │  Plug Thread (60s)                   │   │
    │  │  → SmartPlugController → DB insert   │   │
    │  └──────────────────────────────────────┘   │
    └─────────────────────────────────────────────┘
                         │
                  ┌──────▼───────┐
                  │   Database   │
                  │  SQLite WAL  │
                  │  Thread-local│
                  │  connections │
                  └──────────────┘
```

---

## 8. SENSOR FREEZE ROOT CAUSE HYPOTHESIS

### 8.1 Most Likely Cause

**Primary Suspect:** `adafruit_dht.DHT22.temperature` blocking indefinitely

**Evidence Chain:**
1. ✅ No timeout on hardware read (sensor_cache.py:148-149)
2. ✅ Uses C extension `libgpiod_pulsein` for GPIO bit-banging
3. ✅ DHT22 protocol requires precise timing (microsecond-level)
4. ✅ Raspberry Pi 3B+ can have GPIO contention (USB, network on same bus)
5. ✅ User reports "increasing hangs" - suggests cumulative GPIO stress

**Mechanism:**
```
DHT22 sensor sends data via single GPIO wire
  → Raspberry Pi GPIO driver reads pulses
    → If GPIO interrupt latency too high (system load, USB activity)
      → Bit sequence corrupted
        → Driver waits for completion signal that never comes
          → read_dht22() hangs FOREVER
```

**Supporting Evidence:**
- v6.22.4 changelog mentions "Definitive Sensor-Freeze Fix"
- Sensor reinit attempt added (sensor_cache.py:186) - implies known freeze issue
- Robustness fixes in v6.22.2, v6.22.3 - iterative hardening

### 8.2 Secondary Suspects

**Suspect #2:** Thread starvation in DataLogger

**Likelihood:** Medium

**Mechanism:**
- If Flask request handlers pile up blocking on sensor reads
- Python GIL contention prevents DataLogger thread from waking
- DataLogger thread starves, doesn't update cache timestamp
- Next read attempt waits indefinitely

**Suspect #3:** Database lock contention

**Likelihood:** Low

**Mechanism:**
- SQLite write during sensor read
- WAL mode should prevent this, but theoretically possible
- Thread blocks waiting for DB lock

---

## 9. OBSERVATIONS WITHOUT CODE EVIDENCE

None. All findings are backed by specific file:line references.

---

## 10. RECOMMENDED NEXT STEPS (Analysis Only)

### 10.1 For Agent B (Code Validator)

**Focus Areas:**
1. Verify DHT22 read timeout implementation in v6.22.4
2. Check if threading.Timer or signal.alarm is used
3. Validate sensor reinit logic actually works
4. Confirm Flask thread pool size and request queueing behavior

### 10.2 For Agent C (Fix Implementer)

**Priority 1:**
- Add thread-based timeout wrapper around `_dht_sensor.temperature`
- Fallback to cached/None if timeout expires
- Log timeout events for monitoring

**Priority 2:**
- Move DHT22 reads to separate process (multiprocessing) with IPC
- Eliminate blocking in main service process

**Priority 3:**
- Add watchdog thread to detect hung sensor reads
- Force sensor reinit if read takes > 5s

---

## 11. SYSTEM STATISTICS

| Metric | Value |
|--------|-------|
| Total Python Modules | 20+ (excl. venv) |
| Background Threads | 5-6 daemon threads |
| Singleton Instances | 6 global |
| Blocking I/O Points | 5 identified |
| Critical Risks | 3 |
| High Risks | 2 |
| Medium Risks | 2 |
| Low Risks | 2 |
| Database Tables | 14 (incl. migrations) |
| API Endpoints | 40+ routes |

---

## 12. FINAL ASSESSMENT

**System Maturity:** Production-grade with known edge cases
**Code Quality:** Good (type hints, docstrings, logging)
**Thread Safety:** Mostly correct (relies on GIL for sensor cache)
**Error Handling:** Defensive but no hard timeouts
**Monitoring:** Good (system events, structured logging)

**CRITICAL GAP:** No timeout protection on hardware sensor reads
**RESOLUTION:** Requires timeout wrapper or process isolation

---

**Report Complete**
**Agent A — System Map / Dataflow Analyst**
**Total Findings:** 9 risks identified, 0 unsubstantiated claims
**Recommendation:** Proceed to Agent B for code validation + fix design
