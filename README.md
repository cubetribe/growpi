# 🌱 GrowPi — Autonomous Raspberry Pi Greenhouse & Grow Box Controller

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.9%20%7C%203.11%20%7C%203.13-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform: Raspberry Pi](https://img.shields.io/badge/Platform-Raspberry%20Pi%203%20%7C%204%20%7C%20Zero%202W-C51A4A.svg?logo=raspberry-pi&logoColor=white)](https://www.raspberrypi.com/)
[![Tests](https://img.shields.io/badge/Tests-168%20Passing-brightgreen.svg)]()
[![Status: Battle--Tested](https://img.shields.io/badge/Production--Tested-12%2B%20Weeks%20Continuous-success.svg)]()

**A lightweight, production-hardened Raspberry Pi automation system for 4-channel PWM lighting, natural sunrise/sunset curves, environmental telemetry, and smart dehumidification.**

[Features](#-key-features) •
[Architecture](#-architecture) •
[Hardware & Pinout](#-hardware--pinout) •
[Quick Start](#-quick-start) •
[Web Dashboard](#-embedded-web-dashboard) •
[API Reference](#-rest-api-overview) •
[Contributing](#-contributing) •
[License](#-license)

</div>

---

## 📖 Overview

**GrowPi** is a standalone, local-first greenhouse and grow box automation controller developed by **Dennis Westermann**. It transforms a standard Raspberry Pi into an intelligent, fail-safe cultivation environment.

GrowPi has been tested and refined over months of continuous real-world use — running **8 to 12+ weeks non-stop** without single dropped lamp states, memory leaks, or stability issues.

Unlike heavy cloud-dependent IoT platforms, GrowPi is designed to be:
- **100% Local & Private**: No cloud required. Runs completely self-contained on your local network.
- **Fail-Safe & Resilient**: Lamps never go dark unexpectedly during service restarts or database maintenance.
- **Resource-Efficient**: Zero heavy background runtimes, lean SQLite database with automated retention, and ultra-low CPU/RAM footprint.
- **Open Source**: MIT licensed — free for everyone to use, customize, and extend.

---

## ✨ Key Features

### 🌅 4-Channel Spectrum Lighting Control
- **Independent Channels**: Dedicated PWM channels for **Far Red (730nm)**, **Warm White (3000K)**, **Cool White (6500K)**, and **UV-A/B (385nm)**.
- **Natural Solar Curves**: Smooth 24-hour time-curve interpolation (Hermite & linear) mimicking natural sunrise, midday peak, and sunset spectrum transitions.
- **Zero-Downtime State Sync**: Hardware PWM state is tracked in real-time (`/run/growpi/pwm_state.json`). Service restarts or web updates never interrupt ongoing illumination.
- **Manual Override & Presets**: Easily switch between automated curve mode and instant manual intensity sliders.

### 🌡️ Resilient Environmental Telemetry
- **DHT22 Temperature & Humidity**: Continuous readings with high-precision metrics.
- **Circuit Breaker Protection**: Integrated `pybreaker` automatically isolates sensor hardware glitches, prevents process hangs, and attempts self-healing recovery.
- **Isolated Process Reads**: Sensor polling is executed in isolated worker processes with strict timeouts to prevent hardware locks.

### 🔌 Smart Dehumidifier & Plug Automation
- **Target Humidity Regulation**: Automatic control of dehumidifiers via Smart Plugs (local / Tuya integration).
- **Hysteresis & Cycle Protection**: Configurable high/low thresholds, minimum runtimes, and cool-down intervals to protect compressor hardware.
- **Safety Fallback**: Automatic safe-state shutoff if environmental sensors are unresponsive.

### 📊 Optimized Local SQLite Storage
- **Automated Retention Management**: Retains a rolling 7-day window of sensor and lamp history to keep the database small and fast.
- **Daily Automated VACUUM**: Automatically defragments SQLite storage in the background.
- **In-Memory Deduplication**: Unchanged lamp states are deduplicated in RAM before disk commit, reducing SD card write wear by over **90%**.

### ⚡ Raspberry Pi Hardware & Power Observability
- **Real-Time Undervoltage Detection**: Actively monitors Pi power rails (`vcgencmd get_throttled`) and warns of undervoltage (`< 4.63V`) or CPU throttling right in the dashboard.
- **System Metrics**: Live CPU temperature, RAM usage, storage utilization, and system uptime.
- **systemd Watchdog**: Native watchdog heartbeat integration (`sd_notify`) with automated service recovery.

### 📱 Embedded Responsive Web Dashboard
- **Zero Build Toolchain**: Pure HTML5, modern CSS3, and vanilla ES6 JavaScript — no Node.js, Webpack, or npm dependencies required at runtime.
- **Mobile-Friendly**: Optimized for smartphones, tablets, and desktop browsers with dark mode UI.

---

## 🏛 Architecture

GrowPi employs a **dual-process architecture** for maximum reliability:

```
                          ┌───────────────────────────┐
                          │   Raspberry Pi Hardware   │
                          └─────────────┬─────────────┘
                                        │
                 ┌──────────────────────┴──────────────────────┐
                 │                                             │
      ┌──────────▼──────────┐                       ┌──────────▼──────────┐
      │   grow-pi.service   │                       │  growpi-web.service │
      │  (Controller Loop)  │                       │   (Flask Web API)   │
      └──────────┬──────────┘                       └──────────┬──────────┘
                 │                                             │
                 ├─► PWM Lighting (pigpio)                     ├─► REST API (Port 5000)
                 ├─► DHT22 Sensor Polling                      ├─► Embedded Web UI
                 ├─► Dehumidifier Automation                   └─► Power / Health Probes
                 ├─► Watchdog Heartbeats (systemd)
                 │
                 ▼
      ┌─────────────────────┐
      │  SQLite DB Storage  │
      │ (/opt/grow-pi/data) │
      └─────────────────────┘
```

---

## 🔌 Hardware & Pinout

### Default GPIO Mapping

| Function | Default GPIO | Physical Pin | Description |
| :--- | :--- | :--- | :--- |
| **Far Red PWM** | `GPIO 18` | Pin 12 | Hardware PWM Channel 0 |
| **Warm White PWM** | `GPIO 23` | Pin 16 | PWM Lighting Channel 2 |
| **Cool White PWM** | `GPIO 24` | Pin 18 | PWM Lighting Channel 3 |
| **UV PWM** | `GPIO 25` | Pin 22 | PWM Lighting Channel 4 |
| **DHT22 Data** | `GPIO 4` | Pin 7 | Temperature & Humidity Sensor (with 4.7kΩ pullup) |

> 💡 **Power Supply Tip**: Raspberry Pi boards running hardware PWM and sensors require a clean power source. We strongly recommend using an official **5.1V / 3.0A Raspberry Pi power supply** and a short, high-gauge USB cable to prevent undervoltage throttling.

---

## 🚀 Quick Start

### 1. Raspberry Pi Automatic Installation

Clone the repository directly onto your Raspberry Pi:

```bash
git clone https://github.com/cubetribe/growpi.git
cd growpi/pi-controller
chmod +x install.sh
sudo ./install.sh
```

The installer will:
1. Install system prerequisites (`pigpio`, `libgpiod2`, Python venv).
2. Set up the Python virtual environment and dependencies.
3. Configure and enable `grow-pi.service`, `growpi-web.service`, and `pigpiod`.
4. Initialize the SQLite database and default lighting curves.

### 2. Verify Service Status

```bash
sudo systemctl status grow-pi
sudo systemctl status growpi-web
```

Open your browser and navigate to:
```text
http://<your-raspberry-pi-ip>:5000
```

---

## 💻 Local Development & Testing

You can develop and test GrowPi on macOS, Linux, or Windows without physical Raspberry Pi hardware:

```bash
# Clone the repository
git clone https://github.com/cubetribe/growpi.git
cd growpi

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r pi-controller/requirements.txt pytest pytest-cov

# Run the full unit test suite (168 tests)
PYTHONPATH=pi-controller pytest pi-controller/tests/unit -v

# Start the mock development server
python -m grow_pi.web.app
```

---

## 🌐 REST API Overview

GrowPi provides a RESTful JSON API on port `5000`:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/status` | `GET` | Complete system overview (channels, temperatures, mode, uptime) |
| `/api/lamps` | `GET` / `POST` | Get current lamp states or manually set channel intensities |
| `/api/mode` | `GET` / `POST` | Switch between `auto` (curve schedule) and `manual` mode |
| `/api/curves` | `GET` / `POST` | Retrieve or update 24h lighting curves per channel |
| `/api/curves/presets` | `GET` / `POST` | Manage preset lighting schedules (Seedling, Veg, Bloom) |
| `/api/temperature` | `GET` | Current DHT22 temperature and humidity reading |
| `/api/dehumidifier` | `GET` / `POST` | Dehumidifier controller status and threshold configuration |
| `/api/health` | `GET` / `POST` | System health check (power status, CPU temp, circuit breaker, RAM, disk) |
| `/api/logs/lamps` | `GET` | Historical lamp state logs with downsampling support |
| `/api/logs/sensors` | `GET` | Historical sensor logs (temperature & humidity) |

---

## 🤝 Contributing

GrowPi is an open-source project and contributions are **warmly welcomed**!

Whether you want to:
- 🐛 Report a bug or hardware edge-case
- 💡 Propose a new feature (e.g. soil moisture, CO2 sensors, relay modules)
- 📝 Improve documentation or translations
- 🧪 Submit a Pull Request with bug fixes or enhancements

Feel free to open an **[Issue](https://github.com/cubetribe/growpi/issues)** or submit a **[Pull Request](https://github.com/cubetribe/growpi/pulls)**.

### Development Guidelines
1. Keep changes small, modular, and well-tested.
2. Run unit tests before submitting PRs: `PYTHONPATH=pi-controller pytest pi-controller/tests/unit -v`.
3. Adhere to project guidelines in [`AGENTS.md`](AGENTS.md).

---

## 👤 Author & Credits

- **Creator & Lead Developer**: **Dennis Westermann**
- **Community & Contributions**: [GrowPi Contributors](https://github.com/cubetribe/growpi/graphs/contributors)

---

## 📄 License

This project is licensed under the **[MIT License](LICENSE)** — feel free to use, modify, distribute, and build upon this software for personal and commercial projects alike.
