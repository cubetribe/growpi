# GrowPi - Raspberry Pi 3B+ Hardware Pin-Belegung

**Hardware**: Raspberry Pi 3B+ **Hostname**: growpi **IP**: 192.168.0.86
**Dokumentiert**: 2025-12-05 **Status**: ✅ FINAL - Alle 4 PWM Kanäle verifiziert

---

## 📌 AKTIVE PIN-KONFIGURATION (FINAL)

### Lampen-Kanäle (4 Kanäle)

| Kanal | Name | GPIO | Pin | PWM Typ | Farbe (UI) | Status |
|-------|------|------|-----|---------|------------|--------|
| 1 | Far Red | **GPIO-16** | **Pin 36** | Software PWM | #ff4444 | ✅ Aktiv |
| 2 | Warm White | **GPIO-13** | **Pin 33** | Hardware PWM | #ffbb44 | ✅ Aktiv |
| 3 | Cool White | **GPIO-12** | **Pin 32** | Hardware PWM | #88ddff | ✅ Aktiv |
| 4 | UV | **GPIO-18** | **Pin 12** | Hardware PWM | #cc66ff | ✅ Aktiv |

### Sensoren

| Sensor | GPIO | Pin | Status |
|--------|------|-----|--------|
| DHT22 (Temp/Humidity) | **GPIO-4** | **Pin 7** | ✅ Aktiv |

---

## 📌 Pin-Übersicht (40-Pin GPIO Header)

### Raspberry Pi 3B+ GPIO Layout (Draufsicht)

**Farblegende:**
- 🟢 = **DHT22 Sensor** (in Verwendung)
- 🔴 = **PWM aktiv** (verifiziert)

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
   [ 7] 🟢 GPIO4 ──────────── GPIO14     [ 8]   ← DHT22 DATA ✅
   [ 9]    GND ────────────── GPIO15     [10]
   [11]    GPIO17 ──────────── GPIO18 🔴 [12]   ← Kanal 4 (UV) ✅
   [13]    GPIO27 ──────────── GND        [14]
   [15]    GPIO22 ──────────── GPIO23     [16]
   [17]    3.3V ────────────── GPIO24     [18]
   [19]    GPIO10 ──────────── GND        [20]
   [21]    GPIO9 ────────────── GPIO25    [22]
   [23]    GPIO11 ──────────── GPIO8      [24]
   [25]    GND ────────────── GPIO7      [26]
   [27]    GPIO0 ────────────── GPIO1     [28]
   [29]    GPIO5 ────────────── GND        [30]
   [31]    GPIO6 ────────────── GPIO12 🔴 [32]   ← Kanal 3 (Cool White) ✅
   [33] 🔴 GPIO13 ──────────── GND        [34]   ← Kanal 2 (Warm White) ✅
   [35]    GPIO19 ──────────── GPIO16 🔴  [36]   ← Kanal 1 (Far Red) ✅
   [37]    GPIO26 ──────────── GPIO20     [38]
   [39]    GND ────────────── GPIO21     [40]

        ╔═══════════════════════════════════════╗
        ║         USB-Ports (unten)             ║
        ╚═══════════════════════════════════════╝
```

---

## 🌡️ DHT22 Temperatur & Luftfeuchtigkeit Sensor

### Hardware-Verbindung ✅ VERIFIZIERT (2025-12-05)

**Aktuell verwendet**: 3-Pin Breakout-Board Variante

| DHT22 Pin | Funktion | Raspberry Pi Pin | GPIO/Spannung |
|-----------|----------|------------------|---------------|
| 1 | VCC | **Pin 1** | **3.3V** |
| 2 | DATA | **Pin 7** | **GPIO-4** |
| 3 | GND | **Pin 6** | **GND** |

**Hinweis**: Es gibt zwei DHT22-Varianten:
- **3-Pin Breakout-Board** (wie hier verwendet): VCC, DATA, GND
- **4-Pin Rohsensor**: VCC, DATA, NC (nicht verbunden), GND

### Verkabelung (3-Pin Version)

```
DHT22 Breakout
┌───────────┐
│  +  S  -  │
│  1  2  3  │
└──┬──┬──┬──┘
   │  │  │
   │  │  └─────────────────┐
   │  │                    │
   │  └─────────────┐      │
   │                │      │
   └────────┐       │      │
            │       │      │
         Pin 1   Pin 7   Pin 6
         (3.3V)  (GPIO-4) (GND)
```

### Software-Bibliothek

```bash
# Installation (im venv)
pip install adafruit-circuitpython-dht

# Test
python3 -c "import board; import adafruit_dht; d=adafruit_dht.DHT22(board.D4); print(d.temperature, d.humidity)"
```

---

## 💡 PWM Lampen-Steuerung (4 Kanäle)

### Kanal-Übersicht (FINAL)

| Kanal | Farbe | GPIO BCM | Physischer Pin | PWM Typ | Status |
|-------|-------|----------|----------------|---------|--------|
| 1 | Far Red | **GPIO-16** | **Pin 36** | Software PWM | ✅ Aktiv |
| 2 | Warm White | **GPIO-13** | **Pin 33** | Hardware PWM | ✅ Aktiv |
| 3 | Cool White | **GPIO-12** | **Pin 32** | Hardware PWM | ✅ Aktiv |
| 4 | UV | **GPIO-18** | **Pin 12** | Hardware PWM | ✅ Aktiv |

### Produktions-Verkabelung

```
┌─────────────────────────────────────────────────────────────┐
│                    Raspberry Pi 3B+                          │
│                                                              │
│  Pin 36 (GPIO-16) ──────┬──── PWM Kanal 1 (Far Red)    ✅   │
│  Pin 33 (GPIO-13) ──────┼──── PWM Kanal 2 (Warm White) ✅   │
│  Pin 32 (GPIO-12) ──────┼──── PWM Kanal 3 (Cool White) ✅   │
│  Pin 12 (GPIO-18) ──────┼──── PWM Kanal 4 (UV)         ✅   │
│                         │                                    │
│  Pin 34 (GND) ──────────┴──── Common Ground (alle Kanäle)   │
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
- **Pin 34** (GND) - Empfohlen für Lampen-Ground
- Pin 9, 14, 20, 25, 30, 39 (GND) - Zusätzliche Ground-Pins

---

## 📋 Reservierte Pins (FINAL)

| Pin | GPIO | Funktion | Verwendung |
|-----|------|----------|------------|
| Pin 1 | 3.3V | Power | DHT22 VCC ✅ |
| Pin 6 | GND | Ground | DHT22 GND ✅ |
| Pin 7 | GPIO-4 | Input | DHT22 DATA ✅ |
| Pin 12 | GPIO-18 | PWM Output | Kanal 4 (UV) ✅ |
| Pin 32 | GPIO-12 | PWM Output | Kanal 3 (Cool White) ✅ |
| Pin 33 | GPIO-13 | PWM Output | Kanal 2 (Warm White) ✅ |
| Pin 34 | GND | Ground | Lampen Ground |
| Pin 36 | GPIO-16 | PWM Output | Kanal 1 (Far Red) ✅ |

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

---

## 📐 Schaltplan-Übersicht (FINAL)

```
┌──────────────────────────────────────────────────────────────┐
│                  Raspberry Pi 3B+ (growpi)                    │
│                  IP: 192.168.0.86                             │
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
│  │  Pin 36 (GPIO-16) ────┬──── PWM Kanal 1 (Far Red)   │    │
│  │  Pin 33 (GPIO-13) ────┼──── PWM Kanal 2 (Warm White)│    │
│  │  Pin 32 (GPIO-12) ────┼──── PWM Kanal 3 (Cool White)│    │
│  │  Pin 12 (GPIO-18) ────┼──── PWM Kanal 4 (UV)        │    │
│  │                       │                              │    │
│  │  Pin 34 (GND) ────────┴──── Common Ground           │    │
│  │                                                       │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
└───────────────────────────────────────────────────────────────┘

         PWM Signals (4 Kanäle)
                    │
                    ▼
         ┌────────────────────────┐
         │   MOSFET Driver Board  │
         │   (4 Kanäle)           │
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
         │  (4 Kanäle)            │
         └────────────────────────┘
```

---

## 🔄 Changelog

| Datum | Änderung | Status |
|-------|----------|--------|
| 2025-12-05 | **FINALE KONFIGURATION**: 4 Kanäle statt 5 | ✅ |
| 2025-12-05 | Kanal 1 (Far Red): GPIO-16 / Pin 36 | ✅ |
| 2025-12-05 | Kanal 2 (Warm White): GPIO-13 / Pin 33 | ✅ |
| 2025-12-05 | Kanal 3 (Cool White): GPIO-12 / Pin 32 | ✅ |
| 2025-12-05 | Kanal 4 (UV): GPIO-18 / Pin 12 | ✅ |
| 2025-12-04 | DHT22 auf GPIO-4 (Pin 7) verifiziert | ✅ |
| 2025-12-04 | PWM GPIO-18 (Pin 12) initial getestet | ✅ |

---

**Dokumentiert von**: Claude Code
**Basierend auf**: Hardware-Tests am realen Raspberry Pi 3B+
**Letzte Aktualisierung**: 2025-12-05
**Verifiziert**: Alle 4 PWM Kanäle ✅ | DHT22 (GPIO-4) ✅

_Für Fragen oder Updates: d.westermann@ol-mg.de_
