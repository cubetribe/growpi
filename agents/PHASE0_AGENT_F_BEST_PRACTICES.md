# Agent F - Web Research Report: Bulletproof Sensor Ingestion on Raspberry Pi

**Date:** 2025-12-26
**Agent:** Agent F - Web Research / Best Practices Specialist
**Context:** GrowPi Raspberry Pi system with DHT22 sensor showing increasing lockups/hangs during sensor reads

---

## Executive Summary

This report compiles industry best practices for reliable sensor data ingestion on Raspberry Pi systems. Based on extensive web research, the core issues with DHT22 sensors stem from their **inherently unreliable timing requirements** and tendency to randomly lock up. The recommended approach combines multiple defensive layers:

1. **Process isolation** with timeouts (prevent sensor hangs from freezing main application)
2. **Hardware watchdog** (automatic reboot on complete system freeze)
3. **Software watchdog** via systemd (automatic service restart on partial hang)
4. **Circuit breaker pattern** (graceful degradation when sensor unavailable)
5. **SQLite hardening** for SD card longevity (WAL mode + optimal pragmas)

**Priority Recommendations (by effort/impact ratio):**
1. **HIGH IMPACT, LOW EFFORT:** Enable hardware watchdog + systemd WatchdogSec
2. **HIGH IMPACT, MEDIUM EFFORT:** Implement process isolation for sensor reads with timeout
3. **MEDIUM IMPACT, LOW EFFORT:** Switch SQLite to WAL mode + busy_timeout pragma
4. **MEDIUM IMPACT, MEDIUM EFFORT:** Add circuit breaker pattern for graceful degradation
5. **LOW IMPACT, HIGH EFFORT:** Power-cycle sensor via GPIO (hardware workaround)

---

## 1. Sensor-Read Best Practices

### 1.1 DHT22 Known Issues

The DHT22 sensor is **notoriously unreliable** for Raspberry Pi applications:

**Core Problems:**
- **Random lockups:** Sensors stop responding after random intervals (seconds to months), requiring power cycle ([Raspberry Pi Forums - DHT22 stops working](https://forums.raspberrypi.com/viewtopic.php?t=293876))
- **Timing sensitivity:** Signal requires microsecond-level accuracy, difficult on non-realtime Linux ([Raspberry Pi Forums - DHT22 Temperature Sensor](https://forums.raspberrypi.com/viewtopic.php?t=72911))
- **~15% failure rate:** Even under ideal conditions, 15% of reads fail ([Raspberry Pi Forums - Low DHT22 reading success rate](https://forums.raspberrypi.com/viewtopic.php?t=339121))
- **Polling frequency:** Reading more often than every 2-3 seconds **will eventually cause permanent hang** ([Domoticz Forum - DHT22 stops reading](https://www.domoticz.com/forum/viewtopic.php?t=34037))

**Recommended Timeouts:**
```python
# CRITICAL: Minimum 2 seconds between reads, 3 seconds is safer
MIN_READ_INTERVAL = 3.0  # seconds

# Timeout for single read attempt
SENSOR_READ_TIMEOUT = 10.0  # seconds

# Retry logic (Adafruit library default)
MAX_RETRIES = 15
RETRY_DELAY = 2.0  # seconds
```

### 1.2 Library Comparison

**Adafruit CircuitPython DHT Library:**
- **Pros:** Built-in retry logic (`read_retry()` attempts 15x with 2s delays)
- **Cons:** Susceptible to software lockups, no timeout protection
- **Use case:** Simple setups where occasional hangs are acceptable
- **Source:** [Adafruit DHT Learning Guide](https://learn.adafruit.com/dht-humidity-sensing-on-raspberry-pi-with-gdocs-logging/python-setup)

**pigpio Library (joan2937/pigpio):**
- **Pros:** Better signal timing accuracy, hardware-level timing
- **Cons:**
  - **NOT supported on Raspberry Pi 5** ([Raspberry Pi Forums - DHT22 on Pi 5](https://forums.raspberrypi.com/viewtopic.php?t=386699))
  - Requires pigpio daemon running (`sudo pigpiod`)
  - On faster/newer Pis, needs 10ms delay after trigger
- **Use case:** Pi 3/4 with pigpio daemon infrastructure
- **Source:** [GitHub - pigpio DHT22 Example](https://github.com/joan2937/pigpio/blob/master/EXAMPLES/Python/DHT22_AM2302_SENSOR/DHT22.py)

**Recommendation:** Use **Adafruit library** wrapped in process isolation (see Section 1.4)

### 1.3 Hardware Workarounds

**Power Cycling via GPIO (Nuclear Option):**
```python
import RPi.GPIO as GPIO

SENSOR_POWER_PIN = 8  # Example GPIO pin
SENSOR_DATA_PIN = 4

def power_cycle_sensor():
    """Reset sensor by cutting power for 1 second"""
    GPIO.output(SENSOR_POWER_PIN, GPIO.LOW)
    time.sleep(1.0)
    GPIO.output(SENSOR_POWER_PIN, GPIO.HIGH)
    time.sleep(2.0)  # Allow sensor to stabilize
```

**Requirements:**
- Wire DHT22 VCC to GPIO pin (not 3.3V rail)
- GPIO can supply ~16mA safely (DHT22 draws ~2.5mA max)
- Use 3.3V for simpler/safer operation ([Rototron DHT22 Tutorial](https://www.rototron.info/dht22-tutorial-for-raspberry-pi/))

**Capacitor for Stability:**
- Add 0.1μF capacitor between VCC and GND pins
- Reduces voltage spikes from relay switching
- **Critical if DHT22 shares power rail with relays/motors**
- **Source:** [Raspberry Pi Forums - DHT22 AM2302 problems](https://forums.raspberrypi.com/viewtopic.php?t=211294)

### 1.4 Process Isolation Pattern (CRITICAL)

**Problem:** When DHT22 hangs, it blocks the calling thread indefinitely.

**Solution:** Run sensor read in **separate process** with timeout using `multiprocessing`:

```python
import multiprocessing as mp
from contextlib import contextmanager

@contextmanager
def sensor_read_timeout(timeout=10.0):
    """Context manager for isolated sensor read with timeout"""
    def _read_sensor(queue):
        try:
            # Your actual sensor read logic here
            import Adafruit_DHT
            humidity, temperature = Adafruit_DHT.read_retry(
                Adafruit_DHT.DHT22,
                SENSOR_PIN,
                retries=3  # Reduced from default 15
            )
            queue.put({'temp': temperature, 'humidity': humidity})
        except Exception as e:
            queue.put({'error': str(e)})

    queue = mp.Queue()
    process = mp.Process(target=_read_sensor, args=(queue,))
    process.start()
    process.join(timeout=timeout)

    if process.is_alive():
        # Timeout reached - kill the hung process
        process.terminate()
        process.join(timeout=1.0)
        if process.is_alive():
            process.kill()  # Force kill if terminate fails
        raise TimeoutError(f"Sensor read exceeded {timeout}s timeout")

    try:
        result = queue.get_nowait()
        if 'error' in result:
            raise RuntimeError(result['error'])
        yield result
    except:
        raise RuntimeError("Sensor read failed without result")

# Usage:
try:
    with sensor_read_timeout(timeout=10.0) as data:
        temperature = data['temp']
        humidity = data['humidity']
except TimeoutError:
    # Log failure, use cached value, trigger circuit breaker
    pass
```

**Libraries for Cleaner Implementation:**

**Pebble Library** ([Pebble Documentation](https://pebble.readthedocs.io/)):
```python
from pebble import concurrent
from concurrent.futures import TimeoutError

@concurrent.process(timeout=10.0)
def read_sensor():
    import Adafruit_DHT
    return Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, SENSOR_PIN)

# Usage:
future = read_sensor()
try:
    humidity, temperature = future.result()
except TimeoutError:
    # Handle timeout gracefully
    pass
```

**Benefits:**
- Isolated process prevents main application freeze
- Automatic cleanup of hung processes
- Clear timeout behavior
- **Source:** [Pebble - Process Isolation](https://pebble.readthedocs.io/), [Function Timeout with Multiprocessing](https://alexandra-zaharia.github.io/posts/function-timeout-in-python-multiprocessing/)

### 1.5 GPIO Cleanup Patterns

**Problem:** Crashed scripts leave GPIO pins in undefined states.

**Solution:** Always use `try/finally` with proper cleanup:

```python
import RPi.GPIO as GPIO
import atexit

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    # Setup pins...

def cleanup_gpio():
    GPIO.cleanup()

# Register cleanup on exit
atexit.register(cleanup_gpio)

# Also in exception handlers:
try:
    # Main application logic
    pass
except KeyboardInterrupt:
    print("Interrupted by user")
except Exception as e:
    print(f"Fatal error: {e}")
finally:
    cleanup_gpio()
```

**For I2C Bus Recovery:**
If using I2C sensors (not DHT22), toggle SCL 9 times to clear stuck bus:
```python
import RPi.GPIO as GPIO

def i2c_bus_recovery():
    """Software I2C recovery - toggle SCL 9 times"""
    SCL_PIN = 3  # GPIO3 for I2C1
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SCL_PIN, GPIO.OUT)

    for _ in range(9):
        GPIO.output(SCL_PIN, GPIO.HIGH)
        time.sleep(0.001)
        GPIO.output(SCL_PIN, GPIO.LOW)
        time.sleep(0.001)

    # Restore to I2C mode (ALT0)
    os.system(f"gpio mode {SCL_PIN} ALT0")
```

**Source:** [Raspberry Pi Forums - I2C Bus Recovery](https://forums.raspberrypi.com/viewtopic.php?t=326603), [QuadMeUp - Reset I2C Devices](https://blog.quadmeup.com/2015/12/14/raspberry-pi-reset-external-i2c-devices-not-only-i2c/)

---

## 2. Watchdog Mechanisms

### 2.1 Hardware Watchdog (BCM2835)

**All Raspberry Pis have built-in hardware watchdog timers** that can force reboot if system completely hangs.

**Enabling Hardware Watchdog:**

1. **Enable in boot config** (`/boot/config.txt` or `/boot/firmware/config.txt`):
```bash
dtparam=watchdog=on
```

2. **Verify module loaded:**
```bash
# Module is built into kernel (not shown in lsmod)
cat /lib/modules/$(uname -r)/modules.builtin | grep wdt
# Should show: kernel/drivers/watchdog/bcm2835_wdt.ko

# Check device exists:
ls -l /dev/watchdog
# Should show: crw------- 1 root root 10, 130 Dec 26 10:00 /dev/watchdog
```

3. **Install watchdog daemon:**
```bash
sudo apt install watchdog
sudo systemctl enable watchdog
```

4. **Configure** (`/etc/watchdog.conf`):
```conf
# CRITICAL: Max timeout is 15 seconds on BCM2835!
watchdog-device = /dev/watchdog
watchdog-timeout = 15

# Ping interval (should be < timeout/2)
interval = 10

# System load thresholds (reboot if exceeded)
max-load-1 = 24    # 1-minute load average
max-load-5 = 18
max-load-15 = 12

# Realtime priority for watchdog process
realtime = yes
priority = 1

# Test for file system writes
file = /var/log/watchdog-test
change = 300  # Reboot if file unchanged for 5 minutes
```

**IMPORTANT:** Hardware watchdog is **single-user device**. Choose EITHER:
- **Option A:** watchdog daemon (system-wide, tests load/disk/etc)
- **Option B:** systemd RuntimeWatchdogSec (service-specific)

**DO NOT enable both** - they conflict!

**Sources:**
- [Domoticz - Setting up Raspberry Pi Watchdog](https://www.domoticz.com/wiki/Setting_up_the_raspberry_pi_watchdog)
- [IoT Assistant - Watchdog Timer on RPi](https://iotassistant.io/raspberry-pi/how-to-set-watchdog-timer-raspberrypi/)
- [Xavier.Arnaus.net - Watchdog Service](https://xavier.arnaus.net/blog/watchdog-service-for-raspberry-pi-machines)
- [Raspberry Pi Forums - Hardware Watchdog](https://forums.raspberrypi.com/viewtopic.php?t=353094)

### 2.2 Software Watchdog (systemd)

**For service-level monitoring**, use systemd's built-in watchdog instead of hardware watchdog daemon.

**Configuration in systemd service file** (`/etc/systemd/system/grow-pi.service`):

```ini
[Unit]
Description=GrowPi Sensor Controller
After=network.target

[Service]
Type=notify
ExecStart=/usr/bin/python3 /opt/grow-pi/main.py
WorkingDirectory=/opt/grow-pi
User=pi
Restart=on-failure
RestartSec=10

# Watchdog configuration
WatchdogSec=30s
NotifyAccess=main

# Restart limits (prevent reboot loops)
StartLimitBurst=4
StartLimitIntervalSec=300
StartLimitAction=reboot-force

# Abort timeout (for core dumps)
TimeoutAbortSec=60s

[Install]
WantedBy=multi-user.target
```

**Application Integration:**

Install Python library:
```bash
pip install systemd-watchdog
```

In your Python application:
```python
import systemd_watchdog
import time

# Initialize watchdog
wd = systemd_watchdog.watchdog()

if wd.is_enabled:
    # Get ping interval (half of WatchdogSec)
    interval = wd.timeout / 2
    print(f"Watchdog enabled, ping every {interval}s")

# Main loop:
while True:
    try:
        # Do work (read sensors, write DB, etc)
        read_sensors()

        # Ping watchdog to signal "still alive"
        if wd.is_enabled:
            wd.ping()

        time.sleep(60)  # Next cycle
    except Exception as e:
        # Log error but keep service alive
        print(f"Error: {e}")
        # Don't ping watchdog on error
        # If errors persist > WatchdogSec, systemd will restart service
```

**How It Works:**
1. Service must call `sd_notify("WATCHDOG=1")` every `< WatchdogSec` seconds
2. If ping missing for `WatchdogSec`, systemd kills service with SIGABRT
3. `Restart=on-failure` causes automatic restart
4. After `StartLimitBurst` failures in `StartLimitIntervalSec`, trigger `StartLimitAction=reboot-force`

**Rationale:** Systemd watchdog detects **hung services** (process alive but not responding), while hardware watchdog detects **kernel panics** (entire system frozen).

**Sources:**
- [freedesktop.org - systemd Watchdog Tutorial](http://0pointer.de/blog/projects/watchdog.html)
- [systemd.service Manual](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [PyPI - systemd-watchdog](https://pypi.org/project/systemd-watchdog/)
- [Medo64 - Systemd Watchdog for Any Service](https://www.medo64.com/2019/01/systemd-watchdog-for-any-service/)

### 2.3 Combined Watchdog Strategy (RECOMMENDED)

**Use both layers** for maximum reliability:

```
Layer 1: Application-level circuit breaker
         (graceful degradation on sensor failure)
              ↓
Layer 2: systemd WatchdogSec
         (restart service if hung for 30s)
              ↓
Layer 3: Hardware watchdog in systemd.conf
         (reboot entire Pi if systemd frozen for 15s)
```

**Configuration:**

1. **Application:** Circuit breaker (see Section 3)
2. **Service:** WatchdogSec in unit file (Section 2.2)
3. **System:** Edit `/etc/systemd/system.conf`:
```ini
[Manager]
RuntimeWatchdogSec=15s
RebootWatchdogSec=10min
ShutdownWatchdogSec=10min
```

4. **Reboot to apply:**
```bash
sudo systemctl daemon-reload
sudo reboot
```

---

## 3. Recovery Patterns

### 3.1 Circuit Breaker Pattern

**Purpose:** Prevent cascading failures when sensor becomes unreliable. Instead of continuous retry loops that freeze the system, **fail fast** and use fallback data.

**Python Implementation using `pybreaker`:**

```bash
pip install pybreaker
```

```python
from pybreaker import CircuitBreaker

# Configure circuit breaker
sensor_breaker = CircuitBreaker(
    fail_max=5,              # Open after 5 consecutive failures
    timeout_duration=60,      # Stay open for 60 seconds
    name='DHT22_Sensor'
)

@sensor_breaker
def read_sensor_with_timeout():
    """Sensor read wrapped with circuit breaker"""
    # Use process isolation from Section 1.4
    with sensor_read_timeout(timeout=10.0) as data:
        return data

# Main application loop:
def get_sensor_reading():
    try:
        data = read_sensor_with_timeout()
        return {
            'temperature': data['temp'],
            'humidity': data['humidity'],
            'source': 'live'
        }
    except CircuitBreakerError:
        # Circuit is open - return cached value
        print("Sensor circuit breaker OPEN, using cached data")
        return {
            'temperature': last_valid_reading.get('temperature'),
            'humidity': last_valid_reading.get('humidity'),
            'source': 'cache'
        }
    except Exception as e:
        # Sensor read failed but circuit still closed
        print(f"Sensor read failed: {e}")
        # Failure will count toward fail_max threshold
        raise
```

**Circuit States:**
1. **CLOSED (normal):** All requests pass through
2. **OPEN (failed):** All requests immediately return fallback (no sensor access)
3. **HALF-OPEN (testing):** After timeout, allow one request to test if sensor recovered

**Benefits:**
- Prevents retry storms during sensor outages
- System remains functional with degraded data
- Automatic recovery when sensor stabilizes
- Clear logging of availability issues

**Alternative Libraries:**
- [circuitbreaker](https://pypi.org/project/circuitbreaker/) - Simpler, decorator-based
- [pybreaker](https://github.com/danielfm/pybreaker) - More features, Redis support for distributed systems

**Sources:**
- [PyBreaker GitHub](https://github.com/danielfm/pybreaker)
- [GeeksforGeeks - Circuit Breaker Pattern](https://www.geeksforgeeks.org/system-design/what-is-circuit-breaker-pattern-in-microservices/)
- [Medium - Circuit Breaker in Python](https://medium.com/@sarkarpabitra1999/enhancing-microservice-resilience-with-the-circuit-breaker-pattern-in-python-and-java-f04395e07b99)

### 3.2 Graceful Degradation Strategy

**Fallback Hierarchy:**
```
1. Live sensor read (primary)
   ↓ (on failure)
2. Cached last valid reading (< 5 minutes old)
   ↓ (if cache stale)
3. Interpolated value from historical trend
   ↓ (if no history)
4. Default safe value (e.g., 20°C, 50% humidity)
```

**Implementation:**
```python
from datetime import datetime, timedelta

class SensorCache:
    def __init__(self, max_age_seconds=300):  # 5 minutes
        self.last_reading = None
        self.last_timestamp = None
        self.max_age = timedelta(seconds=max_age_seconds)

    def update(self, reading):
        self.last_reading = reading
        self.last_timestamp = datetime.now()

    def get(self):
        if self.last_reading is None:
            return None

        age = datetime.now() - self.last_timestamp
        if age > self.max_age:
            return None  # Too stale

        return {
            **self.last_reading,
            'age_seconds': age.total_seconds(),
            'is_cached': True
        }

# Usage:
cache = SensorCache(max_age_seconds=300)

def get_sensor_data_with_fallback():
    try:
        # Attempt live read with circuit breaker
        data = read_sensor_with_timeout()
        cache.update(data)
        return {**data, 'source': 'live'}

    except CircuitBreakerError:
        # Circuit open - try cache
        cached = cache.get()
        if cached:
            return {**cached, 'source': 'cache'}
        else:
            return {'temperature': 20.0, 'humidity': 50.0, 'source': 'default'}

    except TimeoutError:
        # Sensor hung - try cache
        cached = cache.get()
        return cached or {'temperature': 20.0, 'humidity': 50.0, 'source': 'default'}
```

### 3.3 Health Check Endpoints

**For systemd/monitoring integration:**

```python
from flask import Flask, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)

# Global health state
health_state = {
    'sensor_last_success': None,
    'sensor_last_failure': None,
    'circuit_breaker_state': 'closed',
    'database_writable': True
}

@app.route('/health')
def health_check():
    """
    Returns 200 OK if system healthy, 503 if degraded
    """
    now = datetime.now()

    # Check sensor health
    sensor_ok = (
        health_state['sensor_last_success'] and
        now - health_state['sensor_last_success'] < timedelta(minutes=5)
    )

    # Check database health
    db_ok = health_state['database_writable']

    status_code = 200 if (sensor_ok and db_ok) else 503

    return jsonify({
        'status': 'healthy' if status_code == 200 else 'degraded',
        'sensor': {
            'available': sensor_ok,
            'last_success': health_state['sensor_last_success'].isoformat() if health_state['sensor_last_success'] else None,
            'circuit_state': health_state['circuit_breaker_state']
        },
        'database': {
            'writable': db_ok
        },
        'timestamp': now.isoformat()
    }), status_code

# Update health state in your main loop:
def update_health_after_sensor_read(success):
    now = datetime.now()
    if success:
        health_state['sensor_last_success'] = now
        health_state['circuit_breaker_state'] = 'closed'
    else:
        health_state['sensor_last_failure'] = now
```

**Monitoring Integration:**
```bash
# External monitoring can check:
curl http://localhost:5000/health

# Or systemd service can use this for watchdog:
# In service: Type=notify
# Application calls: sd_notify("WATCHDOG=1") only if /health returns 200
```

---

## 4. SQLite on Raspberry Pi

### 4.1 WAL Mode (CRITICAL for SD Cards)

**Problem:** Default SQLite journal mode causes 2x writes (journal + database), wearing SD cards faster.

**Solution:** Enable Write-Ahead Logging (WAL) mode:

```python
import sqlite3

conn = sqlite3.connect('/opt/grow-pi/sensors.db')

# Enable WAL mode (persistent setting)
conn.execute("PRAGMA journal_mode=WAL")

# Verify:
result = conn.execute("PRAGMA journal_mode").fetchone()
print(f"Journal mode: {result[0]}")  # Should print "wal"
```

**Benefits:**
- **Much faster writes** (append to log instead of in-place updates)
- **Concurrent reads during writes** (readers don't block writers)
- **More sequential I/O** (better for SD cards)
- **Reduced SD card wear** (fewer write cycles)

**Tradeoffs:**
- Creates `.db-wal` and `.db-shm` files alongside `.db`
- WAL file can grow large during heavy writes (automatic checkpointing usually handles this)
- **Not recommended for transactions > 100MB** (use rollback journal for large imports)

**WAL File Management:**
```python
# Force checkpoint (write WAL to main DB) before backup:
conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

# Monitor WAL size:
wal_pages = conn.execute("PRAGMA wal_checkpoint").fetchone()[0]
print(f"WAL pages pending: {wal_pages}")
```

**Sources:**
- [SQLite WAL Documentation](https://sqlite.org/wal.html)
- [Anže's Blog - SQLite Write-Ahead Logging](https://blog.pecar.me/sqlite-wal)
- [High Performance SQLite - WAL Mode](https://highperformancesqlite.com/watch/wal-mode)
- [Atomic Object - Optimizing SQLite on Raspberry Pi](https://spin.atomicobject.com/sqlite-raspberry-pi/)

### 4.2 Busy Timeout Configuration

**Problem:** With default `busy_timeout=0`, concurrent writes immediately fail with `SQLITE_BUSY`.

**Solution:** Set reasonable timeout on every connection:

```python
import sqlite3

def get_connection():
    conn = sqlite3.connect('/opt/grow-pi/sensors.db')

    # Set busy timeout (NOT PERSISTENT - must set on each connection)
    conn.execute("PRAGMA busy_timeout = 5000")  # 5 seconds

    # Verify:
    timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    print(f"Busy timeout: {timeout}ms")

    return conn
```

**Recommended Values:**
- **Sensor logging:** 3000-5000ms (3-5 seconds)
- **Web API queries:** 1000-2000ms (1-2 seconds)
- **Background jobs:** 10000ms+ (10+ seconds)

**IMPORTANT:**
- `busy_timeout` is **per-connection**, not persistent
- Must be set on every new connection
- Requires SQLite compiled with `HAVE_USLEEP` (default on Raspberry Pi OS)

**Advanced: Immediate Transactions for Writers:**
```python
# For write-heavy operations, start with IMMEDIATE to avoid upgrade deadlocks
conn.execute("BEGIN IMMEDIATE")
try:
    conn.execute("INSERT INTO readings VALUES (?)", (data,))
    conn.commit()
except sqlite3.OperationalError as e:
    conn.rollback()
    # This prevents "cannot upgrade from read to write lock" errors
```

**Sources:**
- [SQLite busy_timeout Documentation](https://sqlite.org/c3ref/busy_timeout.html)
- [High Performance SQLite - Busy Timeout](https://highperformancesqlite.com/watch/busy-timeout)
- [Bert Hubert - SQLITE_BUSY Despite Timeout](https://berthub.eu/articles/posts/a-brief-post-on-sqlite3-database-locked-despite-timeout/)
- [SQLite Tutorial - PRAGMA busy_timeout](https://www.sqlitetutor.com/pragma-busy_timeout/)

### 4.3 SD Card Longevity Best Practices

**Filesystem Configuration (`/etc/fstab`):**
```bash
# Use ext4 (NOT FAT32/exFAT)
# Add noatime to reduce writes
/dev/mmcblk0p2  /  ext4  defaults,noatime  0  1
```

**SQLite Optimizations:**
```python
conn = sqlite3.connect('/opt/grow-pi/sensors.db')

# WAL mode (Section 4.1)
conn.execute("PRAGMA journal_mode=WAL")

# Synchronous mode (tradeoff: speed vs safety)
# NORMAL: Good balance (recommended for WAL mode)
# FULL: Safest but slowest (default)
# OFF: Fastest but risk data loss on power failure
conn.execute("PRAGMA synchronous=NORMAL")

# Memory settings
conn.execute("PRAGMA cache_size=-64000")  # 64MB cache (negative = KB)
conn.execute("PRAGMA temp_store=MEMORY")  # Use RAM for temp tables

# Auto-vacuum (optional - reclaims space but adds overhead)
conn.execute("PRAGMA auto_vacuum=INCREMENTAL")
```

**Transaction Batching (CRITICAL for performance):**
```python
# BAD: 1000 transactions = 1000 fsync calls
for reading in sensor_readings:
    conn.execute("INSERT INTO readings VALUES (?)", (reading,))
    conn.commit()  # Slow!

# GOOD: 1 transaction = 1 fsync call
conn.execute("BEGIN")
for reading in sensor_readings:
    conn.execute("INSERT INTO readings VALUES (?)", (reading,))
conn.commit()  # Fast!
```

**Alternative: Move Database Off SD Card:**
```bash
# Mount USB SSD for database
sudo mount /dev/sda1 /mnt/database

# Symlink database:
ln -s /mnt/database/sensors.db /opt/grow-pi/sensors.db
```

**Data Retention Policy:**
```sql
-- Prevent infinite database growth
-- Archive old data monthly
DELETE FROM sensor_readings
WHERE timestamp < datetime('now', '-90 days');

-- Or aggregate old data:
INSERT INTO daily_aggregates
SELECT date(timestamp), sensor_id, avg(value), min(value), max(value)
FROM sensor_readings
WHERE timestamp < datetime('now', '-30 days')
GROUP BY date(timestamp), sensor_id;

DELETE FROM sensor_readings
WHERE timestamp < datetime('now', '-30 days');
```

**Sources:**
- [Raspberry Pi Forums - SQLite on SSD](https://forums.raspberrypi.com/viewtopic.php?t=255573)
- [Hacker News - WAL Mode Discussion](https://news.ycombinator.com/item?id=32581375)
- [Raspberry Pi Forums - SD Card Best Practices](https://forums.raspberrypi.com/viewtopic.php?t=75508)

---

## 5. systemd Integration

### 5.1 Service File Best Practices

**Complete example** (`/etc/systemd/system/grow-pi.service`):

```ini
[Unit]
Description=GrowPi Greenhouse Controller
Documentation=https://github.com/your-repo/grow-pi
After=network-online.target
Wants=network-online.target
# Start after hardware watchdog enabled
After=watchdog.service

[Service]
Type=notify
User=pi
Group=pi
WorkingDirectory=/opt/grow-pi

# Main process
ExecStart=/usr/bin/python3 /opt/grow-pi/main.py

# Environment
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=/opt/grow-pi/.env

# Restart policy
Restart=on-failure
RestartSec=10s

# Watchdog configuration
WatchdogSec=30s
NotifyAccess=main

# Startup limits (prevent boot loops)
StartLimitBurst=4
StartLimitIntervalSec=300
StartLimitAction=reboot-force

# Timeouts
TimeoutStartSec=60s
TimeoutStopSec=30s
TimeoutAbortSec=60s

# Resource limits (prevent runaway process)
MemoryMax=512M
CPUQuota=80%

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/grow-pi

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=grow-pi

[Install]
WantedBy=multi-user.target
```

**Key Settings Explained:**

**Restart Behavior:**
```ini
Restart=on-failure          # Restart if exits non-zero or times out
RestartSec=10s              # Wait 10s before restart
StartLimitBurst=4           # Allow max 4 restarts...
StartLimitIntervalSec=300   # ...within 5 minutes
StartLimitAction=reboot-force  # If limit exceeded, force reboot
```

**Watchdog:**
```ini
WatchdogSec=30s             # Service must ping every <30s
NotifyAccess=main           # Allow main process to sd_notify
TimeoutAbortSec=60s         # Time to write core dump before SIGKILL
```

**Resource Limits:**
```ini
MemoryMax=512M              # Kill if exceeds 512MB RAM
CPUQuota=80%                # Limit to 80% of one CPU core
```

**Sources:**
- [freedesktop.org - systemd.service Manual](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [Ubuntu Manpage - systemd.service](https://manpages.ubuntu.com/manpages/jammy/man5/systemd.service.5.html)

### 5.2 Hardware Watchdog in systemd.conf

**Instead of watchdog daemon**, use systemd's built-in support:

Edit `/etc/systemd/system.conf`:
```ini
[Manager]
# Ping hardware watchdog every 10s (max 15s on BCM2835)
RuntimeWatchdogSec=15s

# Watchdog timeout for reboot/shutdown
RebootWatchdogSec=10min
ShutdownWatchdogSec=10min

# Watchdog timeout during kexec
KExecWatchdogSec=10min
```

**Apply changes:**
```bash
sudo systemctl daemon-reload
sudo reboot  # Changes only apply after reboot
```

**Verify watchdog active:**
```bash
# Check systemd status
systemctl status systemd

# Should show: "Watchdog: activated"

# Check hardware watchdog device
ls -l /dev/watchdog
# Should be accessed by systemd (PID 1)
```

**This replaces the watchdog daemon** - don't install both!

---

## 6. Prioritized Implementation Plan

### Phase 1: Quick Wins (1-2 hours)

**1. Enable SQLite WAL Mode**
```bash
sqlite3 /opt/grow-pi/sensors.db "PRAGMA journal_mode=WAL"
```
**Impact:** Immediate performance improvement + reduced SD card wear

**2. Set busy_timeout in Code**
```python
# Add to database connection function:
conn.execute("PRAGMA busy_timeout = 5000")
```
**Impact:** Prevents SQLITE_BUSY errors under concurrent access

**3. Enable Hardware Watchdog**
```bash
# Add to /boot/firmware/config.txt:
echo "dtparam=watchdog=on" | sudo tee -a /boot/firmware/config.txt

# Add to /etc/systemd/system.conf:
[Manager]
RuntimeWatchdogSec=15s

sudo reboot
```
**Impact:** Automatic recovery from complete system freezes

### Phase 2: Service Hardening (2-4 hours)

**4. Add systemd WatchdogSec**
```ini
# In /etc/systemd/system/grow-pi.service:
[Service]
WatchdogSec=30s
NotifyAccess=main
Restart=on-failure
StartLimitBurst=4
StartLimitIntervalSec=300
StartLimitAction=reboot-force
```

**5. Implement Watchdog Pings in Application**
```bash
pip install systemd-watchdog
```
```python
# In main loop:
import systemd_watchdog
wd = systemd_watchdog.watchdog()

while True:
    try:
        do_work()
        if wd.is_enabled:
            wd.ping()
    except Exception as e:
        log_error(e)
        # Don't ping on error - let watchdog restart us
```
**Impact:** Service auto-restarts on hangs (without full system reboot)

### Phase 3: Process Isolation (4-6 hours)

**6. Wrap Sensor Reads in Timeout**
```bash
pip install pebble  # Or use multiprocessing directly
```
```python
from pebble import concurrent

@concurrent.process(timeout=10.0)
def read_sensor():
    import Adafruit_DHT
    return Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, PIN)

# In main loop:
future = read_sensor()
try:
    humidity, temperature = future.result()
except TimeoutError:
    # Log failure, use cached value
    pass
```
**Impact:** Sensor hangs no longer freeze main application

### Phase 4: Graceful Degradation (4-6 hours)

**7. Implement Circuit Breaker**
```bash
pip install pybreaker
```
```python
from pybreaker import CircuitBreaker

sensor_breaker = CircuitBreaker(fail_max=5, timeout_duration=60)

@sensor_breaker
def read_sensor_protected():
    return read_sensor_with_timeout()
```

**8. Add Sensor Cache**
```python
class SensorCache:
    # Implementation from Section 3.2
    pass

# Fallback hierarchy: live → cache → default
```
**Impact:** System remains functional during sensor outages

### Phase 5: Monitoring (2-3 hours)

**9. Add Health Check Endpoint**
```python
@app.route('/health')
def health_check():
    # Implementation from Section 3.3
    pass
```

**10. External Monitoring**
```bash
# Setup cron job to check health:
*/5 * * * * curl -f http://localhost:5000/health || systemctl restart grow-pi
```
**Impact:** Proactive detection of degraded states

---

## 7. Testing Strategy

### 7.1 Simulating Sensor Failures

**Temporary sensor disconnect:**
```bash
# Remove power from DHT22 while service running
# Expected: Circuit breaker opens, fallback to cache, service continues
```

**Infinite hang simulation:**
```python
# In sensor read function, temporarily add:
import time
time.sleep(999999)  # Simulate hang

# Expected:
# - Process timeout kills hung read after 10s
# - Circuit breaker opens after 5 failures
# - systemd restarts service after 30s without pings
```

### 7.2 Watchdog Testing

**systemd WatchdogSec:**
```python
# Comment out wd.ping() in main loop
# Expected: Service killed by SIGABRT after WatchdogSec, then restarted
```

**Hardware watchdog:**
```bash
# Fork bomb to freeze system:
:(){ :|:& };:

# Expected: System hard reboots after 15 seconds
```

### 7.3 Database Stress Testing

**Concurrent writes:**
```python
import sqlite3
import threading

def hammer_db():
    for i in range(1000):
        conn = sqlite3.connect('sensors.db')
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("INSERT INTO readings VALUES (?)", (i,))
        conn.commit()

threads = [threading.Thread(target=hammer_db) for _ in range(10)]
for t in threads:
    t.start()

# Expected: All threads succeed with WAL + busy_timeout
```

---

## 8. Known Limitations & Alternatives

### 8.1 DHT22 Alternatives

**If DHT22 continues causing issues**, consider upgrading to more reliable sensors:

**BME280 (I2C):**
- Temperature, humidity, pressure
- I2C interface (more reliable than DHT22's 1-wire)
- No timing issues
- ~$10 vs. ~$5 for DHT22
- **Source:** [Raspberry Pi Forums - BME280 more reliable](https://forums.raspberrypi.com/viewtopic.php?t=211294)

**SHT31/SHT85 (I2C):**
- Industrial-grade accuracy
- I2C interface
- ~$15-30
- Used in commercial applications

### 8.2 Raspberry Pi 5 Compatibility

**pigpio library does NOT work on Pi 5** - if upgrading hardware:
- Use Adafruit CircuitPython DHT library
- Or switch to I2C sensors (BME280, SHT31)
- **Source:** [Raspberry Pi Forums - DHT22 on Pi 5](https://forums.raspberrypi.com/viewtopic.php?t=386699)

### 8.3 Long Cable Runs

**If DHT22 on cable > 15cm:**
- Add shielded cable
- Lower pull-up resistor value (1kΩ instead of 10kΩ)
- Add capacitor near sensor (0.1μF)
- Consider switching to I2C sensor with twisted pair cable
- **Source:** [Rototron - DHT22 Troubleshooting](https://www.rototron.info/dht22-troubleshooting-tips/)

---

## 9. Summary Checklist

**Essential (do first):**
- [ ] Enable SQLite WAL mode (`PRAGMA journal_mode=WAL`)
- [ ] Set `busy_timeout=5000` on all DB connections
- [ ] Enable hardware watchdog (`dtparam=watchdog=on`)
- [ ] Configure systemd `RuntimeWatchdogSec=15s`
- [ ] Add systemd service `WatchdogSec=30s`
- [ ] Implement watchdog pings in application (`sd_notify`)

**High value:**
- [ ] Wrap sensor reads in process isolation with timeout
- [ ] Implement circuit breaker pattern
- [ ] Add sensor data cache with fallback
- [ ] Set restart policies in systemd service file
- [ ] Add health check endpoint

**Nice to have:**
- [ ] Power-cycle sensor via GPIO on failures
- [ ] External monitoring via cron
- [ ] Data retention policy (delete old readings)
- [ ] Move database to USB SSD

**Hardware upgrades (if problems persist):**
- [ ] Replace DHT22 with BME280 (I2C)
- [ ] Add capacitor to DHT22 power pins
- [ ] Use shielded cable for sensor

---

## 10. Sources & Further Reading

### Sensor Reliability
- [Raspberry Pi Forums - DHT22 Temperature Sensor](https://forums.raspberrypi.com/viewtopic.php?t=72911)
- [Raspberry Pi Forums - Low DHT22 Success Rate](https://forums.raspberrypi.com/viewtopic.php?t=339121)
- [Domoticz - DHT22 Stops Reading](https://www.domoticz.com/forum/viewtopic.php?t=34037)
- [Raspberry Pi Forums - DHT22 Stops Working](https://forums.raspberrypi.com/viewtopic.php?t=293876)
- [Adafruit DHT Learning Guide](https://learn.adafruit.com/dht-humidity-sensing-on-raspberry-pi-with-gdocs-logging/python-setup)
- [GitHub - pigpio DHT22 Example](https://github.com/joan2937/pigpio/blob/master/EXAMPLES/Python/DHT22_AM2302_SENSOR/DHT22.py)
- [Rototron - DHT22 Tutorial](https://www.rototron.info/dht22-tutorial-for-raspberry-pi/)
- [Rototron - DHT22 Troubleshooting](https://www.rototron.info/dht22-troubleshooting-tips/)

### Process Isolation
- [Pebble Documentation](https://pebble.readthedocs.io/)
- [Python multiprocessing Documentation](https://docs.python.org/3/library/multiprocessing.html)
- [Alexandra Zaharia - Function Timeout](https://alexandra-zaharia.github.io/posts/function-timeout-in-python-multiprocessing/)
- [FlipDazed - Parallel Functions with Timeouts](https://flipdazed.github.io/blog/quant%20dev/parallel-functions-with-timeouts)

### Circuit Breaker Pattern
- [PyBreaker GitHub](https://github.com/danielfm/pybreaker)
- [GeeksforGeeks - Circuit Breaker Pattern](https://www.geeksforgeeks.org/system-design/what-is-circuit-breaker-pattern-in-microservices/)
- [Medium - Circuit Breaker in Python](https://medium.com/@sarkarpabitra1999/enhancing-microservice-resilience-with-the-circuit-breaker-pattern-in-python-and-java-f04395e07b99)

### Watchdog Systems
- [Domoticz - Raspberry Pi Watchdog Setup](https://www.domoticz.com/wiki/Setting_up_the_raspberry_pi_watchdog)
- [IoT Assistant - Watchdog Timer](https://iotassistant.io/raspberry-pi/how-to-set-watchdog-timer-raspberrypi/)
- [Xavier.Arnaus.net - Watchdog Service](https://xavier.arnaus.net/blog/watchdog-service-for-raspberry-pi-machines)
- [freedesktop.org - systemd Watchdog](http://0pointer.de/blog/projects/watchdog.html)
- [PyPI - systemd-watchdog](https://pypi.org/project/systemd-watchdog/)
- [Medo64 - Systemd Watchdog for Any Service](https://www.medo64.com/2019/01/systemd-watchdog-for-any-service/)

### systemd Configuration
- [systemd.service Manual](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [Ubuntu Manpage - systemd.service](https://manpages.ubuntu.com/manpages/jammy/man5/systemd.service.5.html)

### SQLite Optimization
- [SQLite WAL Documentation](https://sqlite.org/wal.html)
- [Anže's Blog - SQLite Write-Ahead Logging](https://blog.pecar.me/sqlite-wal)
- [High Performance SQLite - WAL Mode](https://highperformancesqlite.com/watch/wal-mode)
- [Atomic Object - Optimizing SQLite on Raspberry Pi](https://spin.atomicobject.com/sqlite-raspberry-pi/)
- [SQLite busy_timeout Documentation](https://sqlite.org/c3ref/busy_timeout.html)
- [High Performance SQLite - Busy Timeout](https://highperformancesqlite.com/watch/busy-timeout)
- [Bert Hubert - SQLITE_BUSY Despite Timeout](https://berthub.eu/articles/posts/a-brief-post-on-sqlite3-database-locked-despite-timeout/)

### GPIO & I2C
- [Raspberry Pi Forums - I2C Bus Recovery](https://forums.raspberrypi.com/viewtopic.php?t=326603)
- [QuadMeUp - Reset I2C Devices](https://blog.quadmeup.com/2015/12/14/raspberry-pi-reset-external-i2c-devices-not-only-i2c/)

---

**END OF REPORT**
