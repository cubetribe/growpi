# DHT22 Sensor - Internet-Recherche: Problem nach Software-Reboot

**Datum:** 2025-12-23
**Agent:** Opus 4.5 Research Agent
**Problem:** DHT22 funktioniert nach `sudo reboot` nicht, erst nach Strom-Reset (Stecker ziehen)

---

## 1. Gefundene Ursachen des Problems

### 1.1 Das DHT22-Protokoll-Problem

Der DHT22 verwendet ein zeitkritisches 1-Wire-Protokoll, das anfaellig fuer Timing-Probleme ist. Das Hauptproblem:

> "The DHT22 is known to just hang on occasion. Sometimes it takes minutes, sometimes months. The only solution is a power cycle."
>
> Quelle: [Raspberry Pi Forums - DHT22 stops working](https://forums.raspberrypi.com/viewtopic.php?t=293876)

### 1.2 GPIO-Zustand nach Software-Reboot

Bei einem Software-Reboot (`sudo reboot`) behalt der DHT22-Sensor seinen internen Zustand, da die 3.3V/5V Stromversorgung NICHT unterbrochen wird. Der Sensor kann in einem "stuck" Zustand verbleiben:

- Die Datenleitung kann in einem LOW-Zustand haengen bleiben
- Der interne Zustandsautomat des Sensors ist blockiert
- Nur ein Power-Cycle (Strom weg) kann den Sensor zuruecksetzen

### 1.3 libgpiod_pulsein Prozess-Problem (Adafruit Library)

Bei der adafruit_dht Library kann der `libgpiod_pulsein` Hintergrundprozess haengen bleiben:

> "If you get 'Unable to set line 4 to input' then the background job libgpiod_pulsein may be in runaway and need to be killed."
>
> Quelle: [Raspberry Pi Forums - DHT22: libgpiod_pulsein issue](https://forums.raspberrypi.com/viewtopic.php?t=282584)

### 1.4 Fehlendes dhtDevice.exit()

Wenn das Python-Skript nicht sauber beendet wird (z.B. SIGTERM beim Reboot), werden GPIO-Ressourcen nicht freigegeben:

> "You need to make sure dhtDevice.exit() is called before your script exits in all cases."
>
> Quelle: [Raspberry Pi Forums - adafruit_dht works but won't run again until reboot](https://forums.raspberrypi.com/viewtopic.php?p=2271575)

---

## 2. KONKRETE Loesungsvorschlaege mit Code-Beispielen

### Loesung 1: DHT22 ueber GPIO mit Strom versorgen (BESTE LOESUNG)

**Konzept:** Statt den DHT22 direkt an 3.3V anzuschliessen, wird er ueber einen GPIO-Pin mit Strom versorgt. So kann die Software den Sensor bei Bedarf power-cyclen.

**Hardware-Aenderung:**
```
DHT22 VCC  --> GPIO Pin (z.B. GPIO 17)
DHT22 DATA --> GPIO 4 (mit 10k Pull-up zu 3.3V)
DHT22 GND  --> GND
```

**ACHTUNG:** DHT22 zieht ca. 1-1.5mA, was innerhalb der 16mA GPIO-Grenze liegt.

**Python-Code mit pigpio Library:**
```python
#!/usr/bin/env python3
import pigpio
import DHT22  # joan2937's DHT22 module
import time

# pigpio daemon muss laufen: sudo pigpiod

pi = pigpio.pi()
if not pi.connected:
    print("Fehler: pigpio daemon nicht gestartet!")
    exit(1)

# DHT22 auf GPIO 4, Power ueber GPIO 17
# Bei Sensor-Hang wird automatisch power-cycled
sensor = DHT22.sensor(pi, 4, power=17)

try:
    while True:
        sensor.trigger()
        time.sleep(0.2)  # Warte auf Messung

        temp = sensor.temperature()
        hum = sensor.humidity()

        if temp is not None and hum is not None:
            print(f"Temperatur: {temp:.1f}C, Luftfeuchtigkeit: {hum:.1f}%")
        else:
            print("Lesefehler - Sensor wird automatisch resettet")

        time.sleep(3)  # Mindestens 2s zwischen Messungen

except KeyboardInterrupt:
    pass
finally:
    sensor.cancel()
    pi.stop()
```

**Quelle:** [joan2937/pigpio DHT22.py](https://github.com/joan2937/pigpio/blob/master/EXAMPLES/Python/DHT22_AM2302_SENSOR/DHT22.py)

---

### Loesung 2: Transistor-basierter Power-Switch

**Fuer hoehere Stroeme oder 5V-Betrieb:**

```
                  +5V
                   |
              [DHT22 VCC]
                   |
            [Collector]
    GPIO 17 ---[Basis]--- NPN-Transistor (z.B. 2N2222)
               (1k Ohm)
            [Emitter]
                   |
                  GND
```

**Python-Code:**
```python
import RPi.GPIO as GPIO
import time
import adafruit_dht
import board

POWER_PIN = 17
DATA_PIN = board.D4

def power_cycle_sensor():
    """Schaltet Sensor aus und wieder ein"""
    GPIO.output(POWER_PIN, GPIO.LOW)
    time.sleep(2)  # 2 Sekunden warten
    GPIO.output(POWER_PIN, GPIO.HIGH)
    time.sleep(2)  # Sensor braucht Zeit zum Starten

def init_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(POWER_PIN, GPIO.OUT)
    GPIO.output(POWER_PIN, GPIO.HIGH)
    time.sleep(2)

def read_sensor_with_retry(dht, max_retries=5):
    for attempt in range(max_retries):
        try:
            return dht.temperature, dht.humidity
        except RuntimeError as e:
            print(f"Lesefehler (Versuch {attempt+1}): {e}")
            if attempt == max_retries - 1:
                print("Max Retries erreicht - Power Cycle")
                power_cycle_sensor()
            time.sleep(2)
    return None, None

# Hauptprogramm
init_gpio()
dht = adafruit_dht.DHT22(DATA_PIN, use_pulseio=False)

try:
    while True:
        temp, hum = read_sensor_with_retry(dht)
        if temp is not None:
            print(f"T: {temp:.1f}C, H: {hum:.1f}%")
        time.sleep(3)
except KeyboardInterrupt:
    pass
finally:
    dht.exit()
    GPIO.cleanup()
```

**Quelle:** [Raspberry Pi Forums - DHT22/11 Sensor Software Reset](https://forums.raspberrypi.com/viewtopic.php?p=2073960)

---

### Loesung 3: Systemd Service mit sauberem Shutdown

**Problem:** Beim Reboot wird das Python-Skript nicht sauber beendet.

**/etc/systemd/system/dht22-cleanup.service:**
```ini
[Unit]
Description=DHT22 GPIO Cleanup Service
DefaultDependencies=no
Before=shutdown.target reboot.target halt.target

[Service]
Type=oneshot
ExecStart=/bin/true
ExecStop=/usr/bin/python3 /opt/growpi/cleanup_dht.py
RemainAfterExit=yes
TimeoutStopSec=10

[Install]
WantedBy=multi-user.target
```

**/opt/growpi/cleanup_dht.py:**
```python
#!/usr/bin/env python3
"""
Wird vor dem Shutdown ausgefuehrt um GPIO sauber freizugeben
"""
import subprocess
import os

# Beende libgpiod_pulsein Prozesse
subprocess.run(['killall', 'libgpiod_pulsein'], stderr=subprocess.DEVNULL)

# GPIO 4 unexport (falls via sysfs genutzt)
try:
    with open('/sys/class/gpio/unexport', 'w') as f:
        f.write('4')
except:
    pass

# Power GPIO LOW setzen (Sensor ausschalten)
try:
    with open('/sys/class/gpio/gpio17/direction', 'w') as f:
        f.write('out')
    with open('/sys/class/gpio/gpio17/value', 'w') as f:
        f.write('0')
except:
    pass

print("DHT22 Cleanup abgeschlossen")
```

**Installation:**
```bash
sudo chmod +x /opt/growpi/cleanup_dht.py
sudo systemctl enable dht22-cleanup.service
```

---

### Loesung 4: libgpiod_pulsein Prozess killen beim Start

**Im Sensor-Initialisierungscode hinzufuegen:**
```python
import subprocess
import time
import adafruit_dht
import board

def kill_stale_pulsein():
    """Beendet haengende libgpiod_pulsein Prozesse"""
    try:
        subprocess.run(['killall', 'libgpiod_pulsein'],
                      stderr=subprocess.DEVNULL,
                      timeout=5)
        time.sleep(0.5)
    except:
        pass

# VOR der Sensor-Initialisierung aufrufen
kill_stale_pulsein()

# Dann Sensor initialisieren
dht = adafruit_dht.DHT22(board.D4, use_pulseio=False)
```

**Quelle:** [Adafruit Forums - DHT22 Works as User but Not as Sudo](https://forums.adafruit.com/viewtopic.php?t=168136)

---

### Loesung 5: Signal Handler fuer sauberes Exit

```python
#!/usr/bin/env python3
import signal
import threading
import time
import adafruit_dht
import board

# Globale Variablen
shutdown_event = threading.Event()
dht_device = None

def signal_handler(signum, frame):
    """Handler fuer SIGTERM/SIGINT"""
    print(f"Signal {signum} empfangen - beende sauber...")
    shutdown_event.set()

def main():
    global dht_device

    # Signal Handler registrieren
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    dht_device = adafruit_dht.DHT22(board.D4, use_pulseio=False)

    try:
        while not shutdown_event.is_set():
            try:
                temp = dht_device.temperature
                humidity = dht_device.humidity
                if temp is not None:
                    print(f"T: {temp:.1f}C, H: {humidity:.1f}%")
            except RuntimeError as e:
                print(f"Lesefehler: {e}")

            # Warte 3s oder bis Shutdown
            shutdown_event.wait(timeout=3.0)
    finally:
        print("Raume auf...")
        if dht_device:
            dht_device.exit()
        print("Cleanup abgeschlossen")

if __name__ == "__main__":
    main()
```

---

## 3. Alternative Libraries (stabiler als adafruit_dht)

### 3.1 pigpio DHT22 Module (EMPFOHLEN)

**Vorteile:**
- Eingebaute automatische Power-Cycling bei Sensor-Hang
- Laeuft als Daemon (keine Root-Rechte im Python-Skript noetig)
- Zuverlaessiger als adafruit_dht

**Installation:**
```bash
sudo apt-get install pigpio
sudo pigpiod  # Daemon starten

# DHT22.py herunterladen
wget https://raw.githubusercontent.com/joan2937/pigpio/master/EXAMPLES/Python/DHT22_AM2302_SENSOR/DHT22.py
```

**ACHTUNG:** pigpio funktioniert NICHT auf Raspberry Pi 5!

**Quelle:** [pigpio Library](https://abyz.me.uk/rpi/pigpio/examples.html)

---

### 3.2 pigpio-dht (pip Package)

**Einfachere Installation:**
```bash
pip install pigpio-dht
sudo pigpiod
```

**Beispiel:**
```python
from pigpio_dht import DHT22
import time

sensor = DHT22(4)  # GPIO 4

while True:
    result = sensor.read()
    if result['valid']:
        print(f"T: {result['temp_c']:.1f}C, H: {result['humidity']:.1f}%")
    time.sleep(3)
```

**Quelle:** [PyPI - pigpio-dht](https://pypi.org/project/pigpio-dht/)

---

### 3.3 BME280 als Alternative (I2C-basiert)

Wenn der DHT22 zu unzuverlaessig ist, ist der BME280 eine sehr gute Alternative:

**Vorteile:**
- I2C-Protokoll (viel stabiler als 1-Wire)
- Keine Timing-Probleme
- Kein Power-Cycling noetig
- Zusaetzlich: Luftdruck-Messung

**Installation:**
```bash
pip install adafruit-circuitpython-bme280

# I2C aktivieren:
sudo raspi-config  # Interface Options -> I2C -> Enable
```

**Code:**
```python
import board
import adafruit_bme280.advanced as adafruit_bme280

i2c = board.I2C()
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

temp = bme280.temperature
humidity = bme280.humidity
print(f"T: {temp:.1f}C, H: {humidity:.1f}%")
```

**Quelle:** [DHT22 Troubleshooting Tips - Rototron](https://www.rototron.info/dht22-troubleshooting-tips/)

---

## 4. Zusammenfassung und Empfehlung

### Sofort-Fix (ohne Hardware-Aenderung):

1. **libgpiod_pulsein beim Start killen** (Loesung 4)
2. **Signal Handler implementieren** (Loesung 5)
3. **Systemd Cleanup-Service** (Loesung 3)

### Langfristige Loesung (Hardware-Aenderung):

1. **DHT22 VCC an GPIO-Pin anschliessen** (Loesung 1)
2. **pigpio Library mit power-Parameter nutzen**
3. Optional: Transistor fuer 5V-Betrieb (Loesung 2)

### Falls DHT22 weiterhin Probleme macht:

- **BME280 Sensor** als zuverlaessige Alternative (I2C)
- Kein Power-Cycling noetig, stabiles Protokoll

---

## 5. Quellen

### GitHub Issues & Repositories
- [adafruit/Adafruit_CircuitPython_DHT - Issue #49](https://github.com/adafruit/Adafruit_CircuitPython_DHT/issues/49)
- [adafruit/Adafruit_CircuitPython_DHT - Issue #80](https://github.com/adafruit/Adafruit_CircuitPython_DHT/issues/80)
- [arendst/Tasmota - Issue #3522](https://github.com/arendst/Tasmota/issues/3522) - DHT22 Reboot-Problem
- [joan2937/pigpio - DHT22.py](https://github.com/joan2937/pigpio/blob/master/EXAMPLES/Python/DHT22_AM2302_SENSOR/DHT22.py)

### Raspberry Pi Forums
- [DHT22 stops working](https://forums.raspberrypi.com/viewtopic.php?t=293876)
- [DHT22/11 Sensor Software Reset](https://forums.raspberrypi.com/viewtopic.php?p=2073960)
- [DHT22: libgpiod_pulsein issue](https://forums.raspberrypi.com/viewtopic.php?t=282584)
- [adafruit_dht works but won't run again](https://forums.raspberrypi.com/viewtopic.php?p=2271575)
- [GPIO cleanup reset](https://forums.raspberrypi.com/viewtopic.php?t=130500)

### Tutorials & Dokumentation
- [DHT22 Troubleshooting Tips - Rototron](https://www.rototron.info/dht22-troubleshooting-tips/)
- [DHT22 Tutorial for Raspberry Pi - Rototron](https://www.rototron.info/dht22-tutorial-for-raspberry-pi/)
- [Random Nerd Tutorials - DHT11/DHT22](https://randomnerdtutorials.com/raspberry-pi-dht11-dht22-python/)
- [Adafruit Learning System - DHT Python Setup](https://learn.adafruit.com/dht-humidity-sensing-on-raspberry-pi-with-gdocs-logging/python-setup)
- [pigpio-dht PyPI](https://pypi.org/project/pigpio-dht/)

### Adafruit Forums
- [DHT22 Works as User but Not as Sudo](https://forums.adafruit.com/viewtopic.php?t=168136)
- [DHT22 sensor Unable to set line to input](https://forums.adafruit.com/viewtopic.php?t=169472)

---

**Fazit:** Das Problem ist ein bekanntes Issue mit dem DHT22-Sensor. Die zuverlaessigste Loesung ist, den Sensor ueber einen GPIO-Pin mit Strom zu versorgen und die pigpio-Library mit automatischem Power-Cycling zu verwenden.
