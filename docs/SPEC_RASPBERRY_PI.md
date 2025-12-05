# Grow-Pi Raspberry Pi Controller Specification

**Version:** 1.0.0\
**Status:** Draft\
**Last Updated:** 2025-12-03\
**Author:** Dennis Westermann d.westermann@ol-mg.de

---

## 1. Executive Summary

This document specifies the Raspberry Pi controller software for the Grow-Pi
greenhouse management system. The Pi acts as the physical interface between the
web-based dashboard and the actual hardware (sensors and lamp power supplies).

The Pi software is responsible for:

- Reading sensor data via various interfaces (GPIO, RS485)
- Controlling lamp power supplies via PWM signals
- Communicating with the central VPS server via HTTPS API
- Operating autonomously when internet connection is lost

---

## 2. Hardware Requirements

### 2.1 Raspberry Pi Model

**Recommended:** Raspberry Pi 4 Model B (2GB+ RAM)\
**Minimum:** Raspberry Pi 3 Model B+

### 2.2 Required Interfaces

| Interface     | Purpose                                 |
| ------------- | --------------------------------------- |
| GPIO          | PWM output for lamp control             |
| GPIO          | Direct sensor connections (DHT22, etc.) |
| USB/UART      | RS485 adapter for soil sensors          |
| Ethernet/WiFi | Network connectivity                    |

### 2.3 Hardware Connections

```
Raspberry Pi 3B+ (growpi / 192.168.0.86)
│
├── GPIO Pins (PWM Output) - ACTIVE CONFIG 2025-12-05
│   ├── GPIO 16 (Pin 36) → Lamp Channel 1 (Far Red)
│   ├── GPIO 13 (Pin 33) → Lamp Channel 2 (Warm White)
│   ├── GPIO 12 (Pin 32) → Lamp Channel 3 (Cool White)
│   └── GPIO 18 (Pin 12) → Lamp Channel 4 (UV)
│
├── GPIO Pins (Sensor Input)
│   ├── GPIO 4  → DHT22 (Temperature + Humidity)
│   └── GPIO 17 → [Reserved for additional sensors]
│
├── USB Port
│   └── USB-to-RS485 Adapter
│       └── RS485 Bus
│           ├── Soil Moisture Sensor
│           ├── Soil Temperature Sensor
│           ├── Soil pH Sensor
│           ├── Soil EC Sensor
│           └── Soil NPK Sensor
│
└── Ethernet / WiFi
    └── Internet Connection → VPS Server
```

### 2.4 Power Supply Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Per Lamp Channel                          │
│                                                              │
│   ┌─────────┐      ┌─────────────┐      ┌───────────────┐  │
│   │ Pi GPIO │──PWM─▶│ PWM Driver  │──────▶│ LED Power     │  │
│   │  (3.3V) │      │ (e.g. MOSFET│      │ Supply        │  │
│   └─────────┘      │  or PCA9685)│      │ (24V/48V DC)  │  │
│                    └─────────────┘      └───────────────┘  │
│                                                │            │
│                                                ▼            │
│                                         ┌───────────┐      │
│                                         │ LED Grow  │      │
│                                         │ Lights    │      │
│                                         └───────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Software Architecture

### 3.1 Technology Stack

| Component           | Technology                |
| ------------------- | ------------------------- |
| Language            | Python 3.11+              |
| GPIO Control        | RPi.GPIO or gpiozero      |
| PWM Control         | Hardware PWM (pigpio)     |
| RS485 Communication | pyserial + minimalmodbus  |
| HTTP Client         | requests or httpx         |
| Configuration       | YAML files                |
| Process Manager     | systemd                   |
| Logging             | Python logging → journald |

### 3.2 Application Structure

```
/opt/grow-pi/
├── grow_pi/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── config.py            # Configuration loader
│   │
│   ├── sensors/
│   │   ├── __init__.py
│   │   ├── base.py          # Abstract sensor class
│   │   ├── dht22.py         # Temperature/Humidity sensor
│   │   ├── rs485_soil.py    # RS485 soil sensors
│   │   └── mock.py          # Mock sensors for testing
│   │
│   ├── lamps/
│   │   ├── __init__.py
│   │   ├── pwm_controller.py
│   │   └── lamp_manager.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py        # HTTP client for VPS API
│   │   └── models.py        # Data models
│   │
│   ├── scheduler/
│   │   ├── __init__.py
│   │   ├── sensor_scheduler.py
│   │   └── lamp_scheduler.py
│   │
│   └── utils/
│       ├── __init__.py
│       └── interpolation.py  # Curve interpolation
│
├── config/
│   └── config.yaml          # Main configuration
│
├── logs/                    # Log files (optional)
│
├── requirements.txt
├── setup.py
└── README.md
```

### 3.3 Process Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      Main Process                            │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   Startup                             │  │
│  │  1. Load configuration                                │  │
│  │  2. Initialize GPIO/PWM                               │  │
│  │  3. Initialize RS485                                  │  │
│  │  4. Register with VPS server                          │  │
│  │  5. Fetch initial lamp curves                         │  │
│  │  6. Start scheduler threads                           │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                 │
│              ┌─────────────┼─────────────┐                  │
│              │             │             │                  │
│              ▼             ▼             ▼                  │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐     │
│  │ Sensor Thread │ │  Lamp Thread  │ │  API Thread   │     │
│  │               │ │               │ │               │     │
│  │ - Read sensors│ │ - Calculate   │ │ - Heartbeat   │     │
│  │   at interval │ │   intensity   │ │ - Poll cmds   │     │
│  │ - Buffer data │ │   from curves │ │ - Send data   │     │
│  │               │ │ - Set PWM     │ │ - Fetch curves│     │
│  └───────────────┘ └───────────────┘ └───────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Configuration

### 4.1 Configuration File (config.yaml)

```yaml
# Grow-Pi Controller Configuration

# Server Connection
server:
    url: "https://grow-pi.example.com"
    api_key: "your-zone-api-key-here"
    timeout: 10 # seconds
    retry_attempts: 3
    retry_delay: 5 # seconds

# Sensor Configuration
sensors:
    read_interval: 60 # seconds (overridden by server)

    # DHT22 Temperature/Humidity Sensor
    dht22:
        enabled: true
        gpio_pin: 4

    # RS485 Soil Sensors
    rs485:
        enabled: true
        port: "/dev/ttyUSB0"
        baudrate: 9600
        timeout: 1

        devices:
            - address: 1
              type: "soil_moisture"
              register: 0

            - address: 2
              type: "soil_temperature"
              register: 0

            - address: 3
              type: "soil_ph"
              register: 0

            - address: 4
              type: "soil_ec"
              register: 0

            - address: 5
              type: "soil_npk"
              registers:
                  n: 0
                  p: 1
                  k: 2

# Lamp Configuration - ACTIVE CONFIG 2025-12-05
lamps:
    update_interval: 1 # seconds (how often to recalculate intensity)

    channels:
        - channel: 1
          name: "Far Red"
          gpio_pin: 16  # Pin 36
          pwm_frequency: 1000

        - channel: 2
          name: "Warm White"
          gpio_pin: 13  # Pin 33
          pwm_frequency: 1000

        - channel: 3
          name: "Cool White"
          gpio_pin: 12  # Pin 32
          pwm_frequency: 1000

        - channel: 4
          name: "UV"
          gpio_pin: 18  # Pin 12
          pwm_frequency: 1000

# Offline Mode
offline:
    # Continue operating with last known curves when offline
    enabled: true
    # Maximum time to operate offline before safety shutdown
    max_offline_hours: 24
    # Store readings locally and sync when back online
    buffer_readings: true
    buffer_max_size: 10000

# Logging
logging:
    level: "INFO" # DEBUG, INFO, WARNING, ERROR
    file: "/var/log/grow-pi/controller.log"
    max_size_mb: 10
    backup_count: 5

# System
system:
    heartbeat_interval: 30 # seconds
    command_poll_interval: 10 # seconds
```

### 4.2 Environment Variables (Optional Overrides)

```bash
GROW_PI_SERVER_URL=https://grow-pi.example.com
GROW_PI_API_KEY=your-zone-api-key-here
GROW_PI_LOG_LEVEL=DEBUG
```

---

## 5. Core Components

### 5.1 Sensor Manager

```python
# sensors/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class SensorReading:
    sensor_type: str
    value: float
    unit: str
    timestamp: datetime
    
class BaseSensor(ABC):
    def __init__(self, name: str, sensor_type: str, unit: str):
        self.name = name
        self.sensor_type = sensor_type
        self.unit = unit
        self._last_reading: Optional[SensorReading] = None
        
    @abstractmethod
    def read(self) -> Optional[SensorReading]:
        """Read current sensor value."""
        pass
        
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize sensor hardware."""
        pass
        
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup resources."""
        pass
```

```python
# sensors/dht22.py

import Adafruit_DHT
from .base import BaseSensor, SensorReading

class DHT22Sensor(BaseSensor):
    def __init__(self, gpio_pin: int, sensor_type: str):
        unit = "°C" if sensor_type == "TEMPERATURE" else "%"
        super().__init__(f"DHT22_{sensor_type}", sensor_type, unit)
        self.gpio_pin = gpio_pin
        self.sensor = Adafruit_DHT.DHT22
        
    def initialize(self) -> bool:
        # DHT22 doesn't require explicit initialization
        return True
        
    def read(self) -> Optional[SensorReading]:
        humidity, temperature = Adafruit_DHT.read_retry(
            self.sensor, 
            self.gpio_pin
        )
        
        if humidity is None or temperature is None:
            return None
            
        value = temperature if self.sensor_type == "TEMPERATURE" else humidity
        
        return SensorReading(
            sensor_type=self.sensor_type,
            value=round(value, 2),
            unit=self.unit,
            timestamp=datetime.now()
        )
        
    def cleanup(self) -> None:
        pass
```

```python
# sensors/rs485_soil.py

import minimalmodbus
from .base import BaseSensor, SensorReading

class RS485SoilSensor(BaseSensor):
    def __init__(
        self, 
        port: str,
        address: int,
        sensor_type: str,
        register: int,
        baudrate: int = 9600
    ):
        super().__init__(f"RS485_{sensor_type}", sensor_type, self._get_unit(sensor_type))
        self.port = port
        self.address = address
        self.register = register
        self.baudrate = baudrate
        self.instrument: Optional[minimalmodbus.Instrument] = None
        
    def _get_unit(self, sensor_type: str) -> str:
        units = {
            "SOIL_MOISTURE": "%",
            "SOIL_TEMP": "°C",
            "SOIL_PH": "pH",
            "SOIL_EC": "mS/cm",
            "SOIL_N": "mg/kg",
            "SOIL_P": "mg/kg",
            "SOIL_K": "mg/kg",
        }
        return units.get(sensor_type, "")
        
    def initialize(self) -> bool:
        try:
            self.instrument = minimalmodbus.Instrument(
                self.port, 
                self.address
            )
            self.instrument.serial.baudrate = self.baudrate
            self.instrument.serial.timeout = 1
            return True
        except Exception as e:
            logging.error(f"Failed to initialize RS485 sensor: {e}")
            return False
            
    def read(self) -> Optional[SensorReading]:
        if not self.instrument:
            return None
            
        try:
            value = self.instrument.read_register(
                self.register,
                number_of_decimals=2
            )
            
            return SensorReading(
                sensor_type=self.sensor_type,
                value=value,
                unit=self.unit,
                timestamp=datetime.now()
            )
        except Exception as e:
            logging.error(f"Failed to read RS485 sensor: {e}")
            return None
            
    def cleanup(self) -> None:
        if self.instrument:
            self.instrument.serial.close()
```

### 5.2 Lamp Controller

```python
# lamps/pwm_controller.py

import pigpio
from dataclasses import dataclass
from typing import Dict, List, Optional
import logging

@dataclass
class LampChannel:
    channel: int
    name: str
    gpio_pin: int
    pwm_frequency: int
    software_pwm: bool = False
    current_intensity: int = 0

class PWMController:
    def __init__(self):
        self.pi: Optional[pigpio.pi] = None
        self.channels: Dict[int, LampChannel] = {}
        
    def initialize(self, channels: List[dict]) -> bool:
        """Initialize pigpio and configure PWM channels."""
        try:
            self.pi = pigpio.pi()
            if not self.pi.connected:
                raise RuntimeError("Failed to connect to pigpio daemon")
                
            for ch_config in channels:
                channel = LampChannel(**ch_config)
                self.channels[channel.channel] = channel
                
                # Set PWM frequency
                self.pi.set_PWM_frequency(
                    channel.gpio_pin, 
                    channel.pwm_frequency
                )
                
                # Start with 0% intensity
                self.set_intensity(channel.channel, 0)
                
            logging.info(f"Initialized {len(self.channels)} PWM channels")
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize PWM controller: {e}")
            return False
            
    def set_intensity(self, channel: int, intensity: int) -> bool:
        """
        Set lamp intensity for a channel.
        
        Args:
            channel: Channel number (1-5)
            intensity: Intensity percentage (0-100)
        """
        if channel not in self.channels:
            logging.error(f"Unknown channel: {channel}")
            return False
            
        # Clamp intensity to valid range
        intensity = max(0, min(100, intensity))
        
        ch = self.channels[channel]
        
        # Convert percentage to PWM duty cycle (0-255)
        duty_cycle = int(intensity * 255 / 100)
        
        try:
            self.pi.set_PWM_dutycycle(ch.gpio_pin, duty_cycle)
            ch.current_intensity = intensity
            logging.debug(f"Channel {channel} ({ch.name}): {intensity}%")
            return True
            
        except Exception as e:
            logging.error(f"Failed to set PWM for channel {channel}: {e}")
            return False
            
    def set_all_intensities(self, intensities: Dict[int, int]) -> None:
        """Set intensities for multiple channels at once."""
        for channel, intensity in intensities.items():
            self.set_intensity(channel, intensity)
            
    def all_on(self, intensity: int = 100) -> None:
        """Turn all lamps to specified intensity."""
        for channel in self.channels:
            self.set_intensity(channel, intensity)
            
    def all_off(self) -> None:
        """Turn all lamps off."""
        for channel in self.channels:
            self.set_intensity(channel, 0)
            
    def get_current_state(self) -> Dict[int, int]:
        """Get current intensity of all channels."""
        return {
            ch: self.channels[ch].current_intensity 
            for ch in self.channels
        }
        
    def cleanup(self) -> None:
        """Cleanup GPIO resources."""
        if self.pi:
            # Turn all lamps off
            self.all_off()
            self.pi.stop()
```

### 5.3 Curve Interpolation

```python
# utils/interpolation.py

from dataclasses import dataclass
from typing import List
from datetime import datetime, time

@dataclass
class CurvePoint:
    time: str      # "HH:MM"
    intensity: int # 0-100

def parse_time(time_str: str) -> time:
    """Parse "HH:MM" string to time object."""
    hours, minutes = map(int, time_str.split(":"))
    return time(hours, minutes)

def time_to_minutes(t: time) -> int:
    """Convert time to minutes since midnight."""
    return t.hour * 60 + t.minute

def interpolate_intensity(curve: List[CurvePoint], current_time: datetime) -> int:
    """
    Calculate lamp intensity for current time based on curve.
    
    Uses linear interpolation between curve points.
    Wraps around midnight (23:59 → 00:00).
    
    Args:
        curve: List of CurvePoints sorted by time
        current_time: Current datetime
        
    Returns:
        Interpolated intensity (0-100)
    """
    if not curve:
        return 0
        
    # Sort curve by time
    sorted_curve = sorted(curve, key=lambda p: parse_time(p.time))
    
    current = current_time.time()
    current_minutes = time_to_minutes(current)
    
    # Find surrounding points
    prev_point = sorted_curve[-1]  # Last point (for wrap-around)
    next_point = sorted_curve[0]   # First point (for wrap-around)
    
    for i, point in enumerate(sorted_curve):
        point_time = parse_time(point.time)
        
        if point_time > current:
            next_point = point
            prev_point = sorted_curve[i - 1] if i > 0 else sorted_curve[-1]
            break
    else:
        # Current time is after all points
        prev_point = sorted_curve[-1]
        next_point = sorted_curve[0]
    
    # Calculate interpolation
    prev_minutes = time_to_minutes(parse_time(prev_point.time))
    next_minutes = time_to_minutes(parse_time(next_point.time))
    
    # Handle wrap-around midnight
    if next_minutes < prev_minutes:
        next_minutes += 24 * 60
    if current_minutes < prev_minutes:
        current_minutes += 24 * 60
        
    # Linear interpolation
    if next_minutes == prev_minutes:
        return prev_point.intensity
        
    ratio = (current_minutes - prev_minutes) / (next_minutes - prev_minutes)
    intensity = prev_point.intensity + ratio * (next_point.intensity - prev_point.intensity)
    
    return int(round(intensity))
```

### 5.4 API Client

```python
# api/client.py

import requests
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import logging

@dataclass
class LampCommand:
    channel: int
    intensity: int

@dataclass
class ServerConfig:
    sensor_interval: int
    lamps: List[Dict]

class GrowPiClient:
    def __init__(self, server_url: str, api_key: str, timeout: int = 10):
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["X-API-Key"] = api_key
        self.session.headers["Content-Type"] = "application/json"
        
    def register(self, version: str, ip_address: str) -> Optional[ServerConfig]:
        """Register Pi with server and get initial configuration."""
        try:
            response = self.session.post(
                f"{self.server_url}/api/pi/register",
                json={
                    "version": version,
                    "ipAddress": ip_address
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            return ServerConfig(
                sensor_interval=data["config"]["sensorInterval"],
                lamps=data["config"]["lampCurves"]
            )
            
        except Exception as e:
            logging.error(f"Failed to register with server: {e}")
            return None
            
    def send_heartbeat(self, status: Dict[str, Any]) -> bool:
        """Send heartbeat to confirm Pi is online."""
        try:
            response = self.session.post(
                f"{self.server_url}/api/pi/heartbeat",
                json=status,
                timeout=self.timeout
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            logging.warning(f"Failed to send heartbeat: {e}")
            return False
            
    def send_readings(self, readings: List[Dict]) -> bool:
        """Send sensor readings to server."""
        try:
            response = self.session.post(
                f"{self.server_url}/api/pi/readings",
                json={"readings": readings},
                timeout=self.timeout
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            logging.error(f"Failed to send readings: {e}")
            return False
            
    def get_commands(self) -> Optional[Dict]:
        """Poll server for pending commands."""
        try:
            response = self.session.get(
                f"{self.server_url}/api/pi/commands",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logging.warning(f"Failed to get commands: {e}")
            return None
            
    def get_lamp_curves(self) -> Optional[List[Dict]]:
        """Fetch current lamp curves from server."""
        try:
            response = self.session.get(
                f"{self.server_url}/api/pi/curves",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()["lamps"]
            
        except Exception as e:
            logging.error(f"Failed to get lamp curves: {e}")
            return None
```

### 5.5 Main Controller

```python
# main.py

import signal
import sys
import time
import threading
import logging
from datetime import datetime
from typing import Dict, List

from config import load_config
from sensors import SensorManager
from lamps import PWMController, LampManager
from api import GrowPiClient
from utils.interpolation import interpolate_intensity

class GrowPiController:
    def __init__(self, config_path: str = "/opt/grow-pi/config/config.yaml"):
        self.config = load_config(config_path)
        self.running = False
        
        # Components
        self.sensor_manager = SensorManager(self.config["sensors"])
        self.pwm_controller = PWMController()
        self.api_client = GrowPiClient(
            self.config["server"]["url"],
            self.config["server"]["api_key"]
        )
        
        # State
        self.lamp_curves: Dict[int, List] = {}
        self.is_online = False
        self.reading_buffer: List = []
        
        # Threads
        self.threads: List[threading.Thread] = []
        
    def initialize(self) -> bool:
        """Initialize all components."""
        logging.info("Initializing Grow-Pi Controller...")
        
        # Initialize sensors
        if not self.sensor_manager.initialize():
            logging.error("Failed to initialize sensors")
            return False
            
        # Initialize PWM controller
        if not self.pwm_controller.initialize(self.config["lamps"]["channels"]):
            logging.error("Failed to initialize PWM controller")
            return False
            
        # Register with server
        server_config = self.api_client.register(
            version="1.0.0",
            ip_address=self._get_ip_address()
        )
        
        if server_config:
            self.is_online = True
            self.lamp_curves = {
                lamp["channel"]: lamp["curve"]
                for lamp in server_config.lamps
            }
            logging.info("Registered with server successfully")
        else:
            logging.warning("Failed to register with server, running in offline mode")
            self._load_cached_curves()
            
        return True
        
    def start(self) -> None:
        """Start the controller."""
        self.running = True
        
        # Start sensor reading thread
        sensor_thread = threading.Thread(
            target=self._sensor_loop,
            daemon=True
        )
        sensor_thread.start()
        self.threads.append(sensor_thread)
        
        # Start lamp control thread
        lamp_thread = threading.Thread(
            target=self._lamp_loop,
            daemon=True
        )
        lamp_thread.start()
        self.threads.append(lamp_thread)
        
        # Start API communication thread
        api_thread = threading.Thread(
            target=self._api_loop,
            daemon=True
        )
        api_thread.start()
        self.threads.append(api_thread)
        
        logging.info("Grow-Pi Controller started")
        
        # Keep main thread alive
        while self.running:
            time.sleep(1)
            
    def stop(self) -> None:
        """Stop the controller gracefully."""
        logging.info("Stopping Grow-Pi Controller...")
        self.running = False
        
        # Wait for threads
        for thread in self.threads:
            thread.join(timeout=5)
            
        # Cleanup
        self.pwm_controller.cleanup()
        self.sensor_manager.cleanup()
        
        logging.info("Grow-Pi Controller stopped")
        
    def _sensor_loop(self) -> None:
        """Continuously read sensors at configured interval."""
        interval = self.config["sensors"]["read_interval"]
        
        while self.running:
            readings = self.sensor_manager.read_all()
            
            if readings:
                if self.is_online:
                    success = self.api_client.send_readings(readings)
                    if not success:
                        self._buffer_readings(readings)
                else:
                    self._buffer_readings(readings)
                    
            time.sleep(interval)
            
    def _lamp_loop(self) -> None:
        """Continuously update lamp intensities based on curves."""
        interval = self.config["lamps"]["update_interval"]
        
        while self.running:
            current_time = datetime.now()
            
            for channel, curve in self.lamp_curves.items():
                intensity = interpolate_intensity(curve, current_time)
                self.pwm_controller.set_intensity(channel, intensity)
                
            time.sleep(interval)
            
    def _api_loop(self) -> None:
        """Handle API communication (heartbeat, commands, sync)."""
        heartbeat_interval = self.config["system"]["heartbeat_interval"]
        command_interval = self.config["system"]["command_poll_interval"]
        
        last_heartbeat = 0
        last_command_poll = 0
        
        while self.running:
            now = time.time()
            
            # Send heartbeat
            if now - last_heartbeat >= heartbeat_interval:
                status = self._get_system_status()
                if self.api_client.send_heartbeat(status):
                    self.is_online = True
                    self._sync_buffered_readings()
                else:
                    self.is_online = False
                last_heartbeat = now
                
            # Poll for commands
            if now - last_command_poll >= command_interval:
                commands = self.api_client.get_commands()
                if commands:
                    self._process_commands(commands)
                last_command_poll = now
                
            time.sleep(1)
            
    def _process_commands(self, commands: Dict) -> None:
        """Process commands from server."""
        # Update lamp curves if changed
        if "lamps" in commands:
            for lamp in commands["lamps"]:
                self.lamp_curves[lamp["channel"]] = lamp["curve"]
            self._cache_curves()
            
        # Handle override commands
        if "override" in commands:
            action = commands["override"]
            if action == "all_on":
                self.pwm_controller.all_on()
            elif action == "all_off":
                self.pwm_controller.all_off()
                
        # Update sensor interval
        if "config" in commands:
            if "sensorInterval" in commands["config"]:
                # Update will take effect next loop iteration
                self.config["sensors"]["read_interval"] = commands["config"]["sensorInterval"]
                
    def _buffer_readings(self, readings: List) -> None:
        """Buffer readings for later sync when offline."""
        max_size = self.config["offline"]["buffer_max_size"]
        self.reading_buffer.extend(readings)
        
        # Trim buffer if too large
        if len(self.reading_buffer) > max_size:
            self.reading_buffer = self.reading_buffer[-max_size:]
            
    def _sync_buffered_readings(self) -> None:
        """Sync buffered readings when back online."""
        if not self.reading_buffer:
            return
            
        # Send in batches
        batch_size = 100
        while self.reading_buffer:
            batch = self.reading_buffer[:batch_size]
            if self.api_client.send_readings(batch):
                self.reading_buffer = self.reading_buffer[batch_size:]
            else:
                break
                
    def _get_system_status(self) -> Dict:
        """Get current system status for heartbeat."""
        import psutil
        
        return {
            "status": "online",
            "uptime": int(time.time() - self._start_time),
            "cpuTemp": self._get_cpu_temp(),
            "cpuUsage": psutil.cpu_percent(),
            "memoryUsage": psutil.virtual_memory().percent,
            "lampState": self.pwm_controller.get_current_state()
        }
        
    def _get_cpu_temp(self) -> float:
        """Get Raspberry Pi CPU temperature."""
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                return float(f.read()) / 1000
        except:
            return 0.0
            
    def _get_ip_address(self) -> str:
        """Get local IP address."""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "unknown"
            
    def _load_cached_curves(self) -> None:
        """Load lamp curves from local cache."""
        # Implementation: Load from JSON file
        pass
        
    def _cache_curves(self) -> None:
        """Cache lamp curves locally."""
        # Implementation: Save to JSON file
        pass


def main():
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    controller = GrowPiController()
    
    # Handle signals for graceful shutdown
    def signal_handler(sig, frame):
        controller.stop()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if controller.initialize():
        controller.start()
    else:
        logging.error("Failed to initialize controller")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## 6. System Service

### 6.1 systemd Service File

```ini
# /etc/systemd/system/grow-pi.service

[Unit]
Description=Grow-Pi Greenhouse Controller
After=network.target pigpiod.service
Requires=pigpiod.service

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/opt/grow-pi
ExecStart=/opt/grow-pi/venv/bin/python -m grow_pi.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment
Environment=PYTHONUNBUFFERED=1

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/grow-pi/logs /opt/grow-pi/data

[Install]
WantedBy=multi-user.target
```

### 6.2 pigpiod Service (Required for PWM)

```bash
# Enable hardware PWM daemon
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
```

### 6.3 Installation Script

```bash
#!/bin/bash
# install.sh

set -e

echo "Installing Grow-Pi Controller..."

# Create directory structure
sudo mkdir -p /opt/grow-pi
sudo chown pi:pi /opt/grow-pi

# Copy files
cp -r . /opt/grow-pi/

# Create virtual environment
cd /opt/grow-pi
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup configuration
if [ ! -f /opt/grow-pi/config/config.yaml ]; then
    cp /opt/grow-pi/config/config.example.yaml /opt/grow-pi/config/config.yaml
    echo "Please edit /opt/grow-pi/config/config.yaml with your settings"
fi

# Install systemd service
sudo cp /opt/grow-pi/systemd/grow-pi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable grow-pi

echo "Installation complete!"
echo "Start the service with: sudo systemctl start grow-pi"
```

---

## 7. API Communication Protocol

### 7.1 Registration Flow

```
Pi                                     Server
│                                        │
│ ──── POST /api/pi/register ──────────▶ │
│      {                                 │
│        "apiKey": "zone-key",           │
│        "version": "1.0.0",             │
│        "ipAddress": "192.168.1.100"    │
│      }                                 │
│                                        │
│ ◀──────────── 200 OK ──────────────── │
│      {                                 │
│        "success": true,                │
│        "zoneId": "uuid",               │
│        "zoneName": "Gewächshaus 1",    │
│        "config": {                     │
│          "sensorInterval": 60,         │
│          "lampCurves": [...]           │
│        }                               │
│      }                                 │
│                                        │
```

### 7.2 Operational Loop

```
Pi                                     Server
│                                        │
│ ──── POST /api/pi/heartbeat ─────────▶ │
│      (every 30 seconds)                │
│                                        │
│ ◀──────────── 200 OK ──────────────── │
│                                        │
│ ──── POST /api/pi/readings ──────────▶ │
│      (every N seconds based on config) │
│      {                                 │
│        "readings": [                   │
│          { "sensorType": "TEMP", ... } │
│        ]                               │
│      }                                 │
│                                        │
│ ◀──────────── 200 OK ──────────────── │
│                                        │
│ ──── GET /api/pi/commands ───────────▶ │
│      (every 10 seconds)                │
│                                        │
│ ◀──────────── 200 OK ──────────────── │
│      {                                 │
│        "lamps": [...],                 │
│        "config": {...},                │
│        "commands": []                  │
│      }                                 │
│                                        │
```

### 7.3 Error Handling

| HTTP Status | Meaning       | Pi Action                  |
| ----------- | ------------- | -------------------------- |
| 200         | Success       | Process response           |
| 400         | Bad Request   | Log error, check payload   |
| 401         | Unauthorized  | Check API key, re-register |
| 404         | Not Found     | Re-register                |
| 500         | Server Error  | Retry with backoff         |
| Timeout     | Network issue | Enter offline mode         |

---

## 8. Offline Mode

### 8.1 Behavior

When the Pi cannot reach the server:

1. **Lamp Control:** Continue using last known curves
2. **Sensor Readings:** Buffer locally (up to configured limit)
3. **Heartbeat:** Keep attempting every 30 seconds
4. **On Reconnect:** Sync buffered readings to server

### 8.2 Safety Limits

| Condition          | Action                              |
| ------------------ | ----------------------------------- |
| Offline > 24 hours | Warning log, continue operation     |
| Offline > 48 hours | Error log, optional safety shutdown |
| Buffer full        | Discard oldest readings             |
| Hardware failure   | Stop PWM, alert if possible         |

---

## 9. Testing

### 9.1 Mock Sensor Mode

For development without physical sensors:

```python
# sensors/mock.py

class MockDHT22Sensor(BaseSensor):
    def read(self) -> SensorReading:
        import random
        
        base = 22.0 if self.sensor_type == "TEMPERATURE" else 65.0
        variation = 5.0 if self.sensor_type == "TEMPERATURE" else 15.0
        
        value = base + random.uniform(-variation, variation)
        
        return SensorReading(
            sensor_type=self.sensor_type,
            value=round(value, 2),
            unit=self.unit,
            timestamp=datetime.now()
        )
```

### 9.2 Test Commands

```bash
# Test PWM output
python -m grow_pi.test.test_pwm

# Test sensor reading
python -m grow_pi.test.test_sensors

# Test API communication
python -m grow_pi.test.test_api

# Full integration test
python -m grow_pi.test.integration
```

---

## 10. Logging & Monitoring

### 10.1 Log Levels

| Level   | Usage                                                           |
| ------- | --------------------------------------------------------------- |
| DEBUG   | Detailed operation info (sensor values, PWM changes)            |
| INFO    | Normal operation (startup, registration, config changes)        |
| WARNING | Recoverable issues (failed API call, retry)                     |
| ERROR   | Failures requiring attention (hardware error, offline too long) |

### 10.2 Log Output

```
2025-12-03 10:30:00 - grow_pi.main - INFO - Grow-Pi Controller started
2025-12-03 10:30:01 - grow_pi.sensors - DEBUG - DHT22: 24.5°C, 68%
2025-12-03 10:30:01 - grow_pi.lamps - DEBUG - Channel 1 (Red): 45%
2025-12-03 10:30:30 - grow_pi.api - INFO - Heartbeat sent successfully
```

### 10.3 Status Reporting

The Pi reports the following in each heartbeat:

- Uptime
- CPU temperature
- CPU usage
- Memory usage
- Current lamp states
- Sensor health status
- Buffer size (if buffering)

---

## 11. Security Considerations

### 11.1 API Key Management

- API key stored in config file (read-only permissions)
- Key can be regenerated from web dashboard
- HTTPS required for all API communication

### 11.2 Local Security

```bash
# Config file permissions
chmod 600 /opt/grow-pi/config/config.yaml
chown pi:pi /opt/grow-pi/config/config.yaml
```

### 11.3 Network Security

- Pi should be on separate IoT VLAN
- Only outbound HTTPS to VPS required
- No inbound ports needed

---

## 12. Dependencies

### 12.1 System Packages

```bash
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    pigpio \
    python3-pigpio
```

### 12.2 Python Packages (requirements.txt)

```
# Core
pigpio>=1.78
RPi.GPIO>=0.7.0
gpiozero>=1.6.2

# Sensors
Adafruit-DHT>=1.4.0
minimalmodbus>=2.0.1
pyserial>=3.5

# HTTP Client
requests>=2.28.0
httpx>=0.24.0

# Configuration
PyYAML>=6.0

# System monitoring
psutil>=5.9.0

# Development
pytest>=7.0.0
pytest-cov>=4.0.0
```

---

## 13. Future Considerations

### Phase 2

- Camera integration for plant monitoring
- Irrigation valve control
- Temperature/humidity control (fans, heaters)
- Multiple sensor types (light level, CO2)

### Phase 3

- Local web interface as fallback
- Bluetooth configuration mode
- OTA updates
- Mesh networking for multiple Pis

---

**End of Raspberry Pi Specification**
