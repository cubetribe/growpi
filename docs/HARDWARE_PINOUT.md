# GrowPi - Raspberry Pi 3B+ Hardware Pin-Belegung

**Hardware**: Raspberry Pi 3B+ **Hostname**: growpi **IP**: 192.168.0.86
**Dokumentiert**: 2025-12-04 **Status**: ✅ DHT22 verifiziert | ✅ PWM GPIO-18
verifiziert

---

## 📌 Pin-Übersicht (40-Pin GPIO Header)

### Raspberry Pi 3B+ GPIO Layout (Draufsicht)

**So ist der GPIO-Header aufgebaut:**
- Die Pins sind in 2 Reihen angeordnet (ungerade Pins links, gerade Pins rechts)
- USB-Ports zeigen nach unten in dieser Darstellung
- Physische Pin-Nummern in eckigen Klammern [1] bis [40]

**Farblegende:**
- 🟢 = **DHT22 Sensor** (in Verwendung)
- 🔴 = **PWM getestet** (verifiziert)
- 🟡 = **PWM geplant** (noch nicht getestet)

```
        ╔═══════════════════════════════════════╗
        ║   Raspberry Pi 3B+ - GPIO Header     ║
        ║   (Blick von oben, USB nach unten)   ║
        ╚═══════════════════════════════════════╝

   Links (ungerade)         Rechts (gerade)
   ════════════════         ═══════════════

   [ 1] 🟢 3.3V ──────────── 5V         [ 2]
   [ 3]    GPIO2 ──────────── 5V         [ 4]
   [ 5]    GPIO3 ──────────── GND    🟢  [ 6]
   [ 7] 🟢 GPIO4 ──────────── GPIO14     [ 8]
   [ 9]    GND ────────────── GPIO15     [10]
   [11]    GPIO17 ──────────── GPIO18 🔴 [12]  ← PWM Kanal 3 ✅
   [13]    GPIO27 ──────────── GND        [14]
   [15]    GPIO22 ──────────── GPIO23     [16]
   [17]    3.3V ────────────── GPIO24     [18]
   [19]    GPIO10 ──────────── GND        [20]
   [21]    GPIO9 ────────────── GPIO25    [22]
   [23]    GPIO11 ──────────── GPIO8      [24]
   [25]    GND ────────────── GPIO7      [26]
   [27]    GPIO0 ────────────── GPIO1     [28]
   [29]    GPIO5 ────────────── GND        [30]
   [31]    GPIO6 ────────────── GPIO12 🟡 [32]  ← PWM Kanal 1
   [33] 🟡 GPIO13 ──────────── GND        [34]
   [35] 🟡 GPIO19 ──────────── GPIO16     [36]
   [37]    GPIO26 ──────────── GPIO20     [38]
   [39]    GND ────────────── GPIO21 🟡 [40]  ← PWM Kanal 5

        ╔═══════════════════════════════════════╗
        ║         USB-Ports (unten)             ║
        ╚═══════════════════════════════════════╝
```

### 🟢 DHT22 Sensor Pins

| Funktion | Physischer Pin | GPIO/Spannung | Markierung |
|----------|----------------|---------------|------------|
| VCC (Stromversorgung) | **Pin 1** | 3.3V | 🟢 |
| DATA (Signal) | **Pin 7** | GPIO-4 | 🟢 |
| GND (Ground) | **Pin 6** | GND | 🟢 |

### 🔴 PWM Lampen Pins (Kanal 3 - verifiziert)

| Funktion | Physischer Pin | GPIO | Markierung | Status |
|----------|----------------|------|------------|--------|
| PWM Signal (Warm White) | **Pin 12** | GPIO-18 | 🔴 | ✅ Getestet |

### 🟡 PWM Lampen Pins (weitere Kanäle - geplant)

| Kanal | Farbe | Physischer Pin | GPIO | Status |
|-------|-------|----------------|------|--------|
| 1 | Red | **Pin 32** | GPIO-12 | ⏳ Pending |
| 2 | Blue | **Pin 33** | GPIO-13 | ⏳ Pending |
| 4 | Cool White | **Pin 35** | GPIO-19 | ⏳ Pending |
| 5 | UV | **Pin 40** | GPIO-21 | ⏳ Pending |

### 📍 Wichtige Hinweise zur Pin-Nummerierung

**ZWEI verschiedene Nummerierungen:**

1. **Physische Pin-Nummer** [1] bis [40]
   - Zählt die Position auf dem Header
   - Beispiel: Pin 12 (12. Position)

2. **GPIO-Nummer** (BCM-Modus)
   - Software-Bezeichnung in Python
   - Beispiel: GPIO-18 (GPIO Nummer 18)

**In Python:**
```python
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)    # BCM = GPIO-Nummern verwenden
GPIO.setup(18, GPIO.OUT)   # GPIO-18 = Pin 12 (physisch)
```

---

## 🌡️ DHT22 Temperatur & Luftfeuchtigkeit Sensor

### Hardware-Verbindung ✅ VERIFIZIERT

| DHT22 Pin | Funktion           | Raspberry Pi Pin | GPIO/Pin   |
| --------- | ------------------ | ---------------- | ---------- |
| Pin 1     | VCC (3.3V-5V)      | Pin 1            | 3.3V       |
| Pin 2     | DATA               | **Pin 7**        | **GPIO-4** |
| Pin 3     | NC (not connected) | -                | -          |
| Pin 4     | GND                | **Pin 6**        | **GND**    |

### Verkabelung

```
DHT22 Sensor
┌─────────────┐
│  1  2  3  4 │
└──┬──┬──┬──┬─┘
   │  │  │  │
   │  │  │  └─────────────────────┐
   │  │  └── (nicht verbunden)    │
   │  │                           │
   │  └─────────────┐             │
   │                │             │
   └────────┐       │             │
            │       │             │
         Pin 1   Pin 7          Pin 6
         (3.3V)  (GPIO-4)       (GND)
```

### Test-Ergebnisse

```python
# GPIO-4 = board.D4
import board
import adafruit_dht

dhtDevice = adafruit_dht.DHT22(board.D4)
temperature = dhtDevice.temperature  # 21.0°C
humidity = dhtDevice.humidity        # 64.0%
```

**Gemessene Werte**:

- Temperatur: 21.0°C
- Luftfeuchtigkeit: 64.0%
- Status: Stabil, keine Fehler

---

## 💡 PWM Lampen-Steuerung (5 Kanäle)

### Kanal-Übersicht

| Kanal | Farbe      | GPIO BCM    | Physischer Pin | PWM Typ      | Status         |
| ----- | ---------- | ----------- | -------------- | ------------ | -------------- |
| 1     | Red        | GPIO-12     | Pin 32         | Hardware PWM | ⏳ Pending     |
| 2     | Blue       | GPIO-13     | Pin 33         | Hardware PWM | ⏳ Pending     |
| 3     | Warm White | **GPIO-18** | **Pin 12**     | Hardware PWM | ✅ Verifiziert |
| 4     | Cool White | GPIO-19     | Pin 35         | Hardware PWM | ⏳ Pending     |
| 5     | UV         | GPIO-21     | Pin 40         | Software PWM | ⏳ Pending     |

### PWM GPIO-18 Test ✅ VERIFIZIERT

**Verkabelung für Test**:

```
Raspberry Pi 3B+
┌─────────────────────────┐
│                         │
│  Pin 12 (GPIO-18) ──────┼──── PWM Signal (getestet)
│                         │
│  Pin 9 (GND) ───────────┼──── Ground (Test)
│                         │
└─────────────────────────┘
```

**Test-Konfiguration**:

- **Frequenz**: 1000 Hz (1 kHz)
- **Duty Cycle**: 0% → 25% → 50% → 75% → 100% → 75% → 50% → 25% → 0%
- **Ergebnis**: ✅ PWM-Signal erfolgreich generiert

**Python Code**:

```python
import RPi.GPIO as GPIO

PWM_PIN = 18  # GPIO-18 = Pin 12
PWM_FREQUENCY = 1000  # 1 kHz

GPIO.setmode(GPIO.BCM)
GPIO.setup(PWM_PIN, GPIO.OUT)
pwm = GPIO.PWM(PWM_PIN, PWM_FREQUENCY)

pwm.start(0)              # Start mit 0%
pwm.ChangeDutyCycle(50)   # 50% Helligkeit
pwm.ChangeDutyCycle(100)  # 100% Helligkeit
pwm.stop()
GPIO.cleanup()
```

### Produktions-Verkabelung (alle Kanäle)

```
┌─────────────────────────────────────────────────────────────┐
│                    Raspberry Pi 3B+                          │
│                                                              │
│  Pin 32 (GPIO-12) ──────┬──── PWM Kanal 1 (Red)             │
│  Pin 33 (GPIO-13) ──────┼──── PWM Kanal 2 (Blue)            │
│  Pin 12 (GPIO-18) ──────┼──── PWM Kanal 3 (Warm White) ✅   │
│  Pin 35 (GPIO-19) ──────┼──── PWM Kanal 4 (Cool White)      │
│  Pin 40 (GPIO-21) ──────┼──── PWM Kanal 5 (UV)              │
│                         │                                    │
│  Pin 6  (GND) ──────────┴──── Common Ground (alle Kanäle)   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   PWM Driver / MOSFET  │
              │      (pro Kanal)       │
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   LED Power Supply     │
              │      (24V/48V DC)      │
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │    LED Grow Lights     │
              └────────────────────────┘
```

### Ground-Pins für Lampen

Mehrere GND-Pins verfügbar (alle intern verbunden):

- **Pin 6** (GND) - Für DHT22 verwendet ✅
- **Pin 9** (GND) - Für PWM-Test verwendet ✅
- Pin 14 (GND)
- Pin 20 (GND)
- Pin 25 (GND)
- Pin 30 (GND)
- Pin 34 (GND)
- Pin 39 (GND)

**Empfehlung**: Pin 34 (GND) für gemeinsamen Lampen-Ground verwenden (zentral
gelegen)

---

## 🌱 RS485 Bodensensoren

### USB-zu-RS485 Adapter

| Komponente        | Verbindung | Geräte-Pfad    |
| ----------------- | ---------- | -------------- |
| USB-RS485 Adapter | USB Port   | `/dev/ttyUSB0` |

### RS485 Bus Sensoren (geplant)

| Sensor            | Modbus Adresse | Register | Einheit | Status     |
| ----------------- | -------------- | -------- | ------- | ---------- |
| Bodenfeuchtigkeit | 1              | 0        | %       | ⏳ Pending |
| Bodentemperatur   | 2              | 0        | °C      | ⏳ Pending |
| Boden-pH          | 3              | 0        | pH      | ⏳ Pending |
| Boden-EC          | 4              | 0        | mS/cm   | ⏳ Pending |
| NPK-Sensor        | 5              | 0,1,2    | mg/kg   | ⏳ Pending |

**RS485 Verkabelung**:

```
USB-RS485 Adapter
        │
        ├─── A+ (Data+)
        ├─── B- (Data-)
        └─── GND
             │
             ├──────┬──────┬──────┬──────┬
             │      │      │      │      │
         Sensor  Sensor Sensor Sensor Sensor
           1      2      3      4      5
        (Feuchte)(Temp) (pH)  (EC)  (NPK)
```

---

## ⚡ Stromversorgung

### Raspberry Pi 3B+ Power Requirements

| Komponente   | Spannung | Strom    | Pin        |
| ------------ | -------- | -------- | ---------- |
| Pi 3B+       | 5V       | 2.5A     | Micro-USB  |
| GPIO 3.3V    | 3.3V     | 50mA max | Pins 1, 17 |
| GPIO 5V      | 5V       | -        | Pins 2, 4  |
| DHT22 Sensor | 3.3V     | ~1mA     | Pin 1      |

### LED Lampen Power (separates Netzteil)

| Kanal         | Typ           | Spannung        | Leistung        |
| ------------- | ------------- | --------------- | --------------- |
| Alle 5 Kanäle | LED Strip/COB | 24V oder 48V DC | Je nach LED-Typ |

**⚠️ WICHTIG**:

- LED-Lampen benötigen **separates Netzteil** (24V/48V DC)
- **NICHT direkt an Raspberry Pi** anschließen!
- PWM-Signal steuert MOSFET/Treiber, der das LED-Netzteil schaltet

---

## 🔌 Hardware-PWM Kanäle (Pi 3B+)

Der Raspberry Pi 3B+ hat **2 Hardware-PWM-Controller** mit je **2 Kanälen**:

| PWM Controller | Kanal     | GPIO    | Pin | Alternative GPIO |
| -------------- | --------- | ------- | --- | ---------------- |
| PWM0           | Channel 0 | GPIO-12 | 32  | GPIO-18          |
| PWM0           | Channel 1 | GPIO-13 | 33  | GPIO-19          |
| PWM1           | Channel 0 | GPIO-18 | 12  | GPIO-12          |
| PWM1           | Channel 1 | GPIO-19 | 35  | GPIO-13          |

**Unsere Belegung**:

- GPIO-12 → PWM0 Channel 0 (Kanal 1 - Red)
- GPIO-13 → PWM0 Channel 1 (Kanal 2 - Blue)
- GPIO-18 → PWM1 Channel 0 (Kanal 3 - Warm White) ✅
- GPIO-19 → PWM1 Channel 1 (Kanal 4 - Cool White)
- GPIO-21 → Software PWM (Kanal 5 - UV)

**Warum GPIO-21 Software PWM?**

- GPIO-21 hat kein Hardware-PWM
- Für 5 Kanäle benötigt (4 Hardware + 1 Software)
- Ausreichend für LED-Steuerung (Software PWM bei 1 kHz ist stabil)

---

## 📋 Reservierte Pins

| Pin Range        | Funktion   | Verwendung              |
| ---------------- | ---------- | ----------------------- |
| Pin 1, 17        | 3.3V Power | Sensor Power            |
| Pin 2, 4         | 5V Power   | Reserviert              |
| Pin 6            | GND        | DHT22 Ground ✅         |
| Pin 7 (GPIO-4)   | Input      | DHT22 Data ✅           |
| Pin 9            | GND        | PWM Test Ground ✅      |
| Pin 12 (GPIO-18) | PWM Output | Kanal 3 (Warm White) ✅ |
| Pin 32 (GPIO-12) | PWM Output | Kanal 1 (Red)           |
| Pin 33 (GPIO-13) | PWM Output | Kanal 2 (Blue)          |
| Pin 35 (GPIO-19) | PWM Output | Kanal 4 (Cool White)    |
| Pin 40 (GPIO-21) | PWM Output | Kanal 5 (UV)            |
| Pin 11 (GPIO-17) | Reserved   | Zukünftige Sensoren     |

---

## 🛡️ Sicherheitshinweise

### GPIO-Limits

⚠️ **KRITISCH - NICHT ÜBERSCHREITEN**:

- **Pro GPIO-Pin**: Max 16 mA
- **Alle GPIO zusammen**: Max 50 mA
- **3.3V Rail (alle 3.3V Pins)**: Max 50 mA
- **5V Rail**: Nicht für externe Geräte nutzen (Pi-Versorgung!)

### LED-Lampen Sicherheit

✅ **RICHTIG**:

```
Pi GPIO → MOSFET Gate → LED-Netzteil (24V) → LED
```

❌ **FALSCH** (zerstört den Pi!):

```
Pi GPIO → LED direkt (NIEMALS!)
```

### Schutz-Maßnahmen

1. **PWM zu MOSFET**:
   - Logic-Level MOSFET verwenden (3.3V Gate)
   - Gate-Widerstand 220Ω-1kΩ
   - Flyback-Diode für induktive Lasten

2. **Sensor zu GPIO**:
   - DHT22 läuft mit 3.3V (sicher)
   - Pull-up Widerstand 4.7kΩ-10kΩ am DHT22 Data-Pin

3. **Ground Loops vermeiden**:
   - Gemeinsamer Ground für Pi + Sensoren
   - LED-Netzteil-Ground mit Pi-Ground verbinden

---

## 🧪 Test-Scripts

### DHT22 Sensor Test

**Speicherort**: `/tmp/test_dht22.py`

```python
import board
import adafruit_dht

dhtDevice = adafruit_dht.DHT22(board.D4)

temperature = dhtDevice.temperature
humidity = dhtDevice.humidity

print(f'Temperatur: {temperature:.1f}°C')
print(f'Luftfeuchtigkeit: {humidity:.1f}%')

dhtDevice.exit()
```

### PWM GPIO-18 Test

**Speicherort**: `/tmp/test_pwm_gpio18.py`

```python
import RPi.GPIO as GPIO
import time

PWM_PIN = 18
PWM_FREQUENCY = 1000

GPIO.setmode(GPIO.BCM)
GPIO.setup(PWM_PIN, GPIO.OUT)
pwm = GPIO.PWM(PWM_PIN, PWM_FREQUENCY)

pwm.start(0)
for duty in [0, 25, 50, 75, 100, 75, 50, 25, 0]:
    pwm.ChangeDutyCycle(duty)
    time.sleep(1.5)

pwm.stop()
GPIO.cleanup()
```

---

## 📐 Schaltplan-Übersicht

### Vollständiges System-Diagramm

```
┌──────────────────────────────────────────────────────────────┐
│                  Raspberry Pi 3B+ (growpi)                    │
│                                                               │
│  Power: 5V/2.5A Micro-USB                                    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              GPIO Header (40 Pins)                   │    │
│  │                                                       │    │
│  │  Pin 1  (3.3V) ────────────┬─────── DHT22 VCC       │    │
│  │  Pin 6  (GND)  ────────────┼─────── DHT22 GND       │    │
│  │  Pin 7  (GPIO-4) ──────────┘                        │    │
│  │                     └────────────── DHT22 DATA       │    │
│  │                                                       │    │
│  │  Pin 12 (GPIO-18) ────┬──── PWM Kanal 3 ✅          │    │
│  │  Pin 32 (GPIO-12) ────┼──── PWM Kanal 1             │    │
│  │  Pin 33 (GPIO-13) ────┼──── PWM Kanal 2             │    │
│  │  Pin 35 (GPIO-19) ────┼──── PWM Kanal 4             │    │
│  │  Pin 40 (GPIO-21) ────┼──── PWM Kanal 5             │    │
│  │                       │                              │    │
│  │  Pin 34 (GND) ────────┴──── Common Ground           │    │
│  │                                                       │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  USB Port ───────────────────── USB-RS485 Adapter            │
│                                       │                       │
└───────────────────────────────────────┼───────────────────────┘
                                        │
                    ┌───────────────────┴──────────────────┐
                    │        RS485 Bus                     │
                    │  (Bodensensoren via Modbus)          │
                    └──────────────────────────────────────┘

         PWM Signals (5 Kanäle)
                    │
                    ▼
         ┌────────────────────────┐
         │   MOSFET Driver Board  │
         │   (5 Kanäle)           │
         └────────────────────────┘
                    │
                    ▼
         ┌────────────────────────┐
         │  LED Power Supply      │
         │  (24V/48V DC, separates│
         │   Netzteil)            │
         └────────────────────────┘
                    │
                    ▼
         ┌────────────────────────┐
         │  LED Grow Lights       │
         │  (5 Kanäle)            │
         └────────────────────────┘
```

---

## 📚 Referenzen

- **SPEC_RASPBERRY_PI.md**: Vollständige Software-Spezifikation
- **ARCHITECTURE.md**: System-Architektur
- **Python Library**: `adafruit-circuitpython-dht` 4.0.10
- **Python Library**: `RPi.GPIO` für PWM-Steuerung
- **Modbus Library**: `minimalmodbus` für RS485-Sensoren

---

## 🔄 Changelog

| Datum      | Änderung                               | Status |
| ---------- | -------------------------------------- | ------ |
| 2025-12-04 | DHT22 auf GPIO-4 (Pin 7) verifiziert   | ✅     |
| 2025-12-04 | DHT22 Ground auf Pin 6 dokumentiert    | ✅     |
| 2025-12-04 | PWM GPIO-18 (Pin 12) verifiziert       | ✅     |
| 2025-12-04 | PWM Test Ground Pin 9 dokumentiert     | ✅     |
| 2025-12-04 | Vollständige Pin-Belegung dokumentiert | ✅     |

---

**Dokumentiert von**: Claude Code **Basierend auf**: Hardware-Tests am realen
Raspberry Pi 3B+ **Verifiziert**: DHT22 (GPIO-4) ✅ | PWM (GPIO-18) ✅

_Für Fragen oder Updates: d.westermann@ol-mg.de_
