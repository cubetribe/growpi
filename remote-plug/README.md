# GrowPi Remote Plug Integration

## Übersicht

Dieses Modul ermöglicht die lokale Steuerung von **Tuya-basierten Smart Plugs** (Steckdosen) über den Raspberry Pi. Die Steckdosen können ein-/ausgeschaltet werden und liefern Echtzeit-Energiemesswerte (Leistung, Spannung, Strom).

**Anwendungsfall:** Steuerung von Grow-Lampen und Pumpen im Gewächshaus mit Stromverbrauchsmessung.

---

## Hardware

### Verwendete Steckdosen

| Hersteller | Modell | Verbindung | Energiemessung |
|------------|--------|------------|----------------|
| ANTELA | F1s202-EU | WiFi | Ja |
| Diverse | Tuya-kompatibel | WiFi | Ja |

**Wichtig:** Die Steckdosen sind Tuya-basiert und werden über die **Smart Life App** eingerichtet.

### Raspberry Pi

- **Host:** growpi
- **IP:** 192.168.0.86
- **User:** admin

---

## Gefundene Geräte

Im Netzwerk wurden **6 Smart Plugs** gefunden:

### WiFi-Steckdosen (direkt steuerbar)

| Name | IP-Adresse | Device ID | Status |
|------|------------|-----------|--------|
| Main Light | 192.168.0.73 | bf36487f67d7bb8fc18buj | Getestet ✓ |
| Wohnzimmer | 192.168.0.96 | bfcf3ba95588e232b08mg6 | Verfügbar |
| Mittags Sonne | 192.168.0.130 | bfbbc4e059a6ae812csbyq | Verfügbar |
| FR main | 192.168.0.93 | bfc332c0bf2f53a5cc23uz | Verfügbar |

### BLE-Steckdosen (nicht direkt steuerbar)

| Name | MAC-Adresse | Device ID | Status |
|------|-------------|-----------|--------|
| ANTELA Smart Steckdose | 18:DE:50:93:13:6D | bfc705014c6241667avzn8 | Nur via Cloud |
| Pumpe | - | bfad1a5081fa6a2342j7ye | Nur via Cloud |

**Hinweis:** BLE-Steckdosen erfordern eine spezielle Bluetooth-Integration und sind komplexer anzusteuern.

---

## Credentials & Authentifizierung

### Tuya IoT Cloud

Die Credentials werden benötigt, um Device-Informationen (Local Keys) abzurufen.

| Parameter | Wert | Speicherort |
|-----------|------|-------------|
| Access ID | `x7gt474g4ac9nvwredk4` | `.env` |
| Access Secret | `cd29a6ddf61f4197b1965370272a4100` | `.env` |
| Region | `eu` (Central Europe) | `.env` |
| Projekt-Name | GrowPi Smart Home | Tuya IoT Portal |

**Portal:** https://iot.tuya.com/

### Device Credentials

Jedes Gerät hat einen **Local Key**, der für die lokale Kommunikation benötigt wird. Diese Keys sind in `devices.json` gespeichert.

**WICHTIG:** Die Local Keys sind geheim und sollten NICHT committet werden!

---

## Technische Details

### Kommunikationsprotokoll

Die Steckdosen kommunizieren über das **Tuya Local Protocol v3.3**:

```
Raspberry Pi  <---->  Smart Plug
     |                    |
     |   TCP Port 6668    |
     |   AES-128-ECB      |
     |   JSON Payload     |
```

- **Verschlüsselung:** AES-128-ECB mit Local Key
- **Port:** 6668 (TCP)
- **Protokoll-Version:** 3.3

### Data Points (DPS)

Tuya-Geräte verwenden "Data Points" (DPS) für alle Funktionen:

| DPS | Typ | Beschreibung | Einheit |
|-----|-----|--------------|---------|
| 1 | bool | Switch (Ein/Aus) | - |
| 9 | int | Countdown Timer | Sekunden |
| 17 | int | Power (alternativ) | 0.1 W |
| 18 | int | Current (Strom) | mA |
| 19 | int | Power (Leistung) | 0.1 W |
| 20 | int | Voltage (Spannung) | 0.1 V |
| 23 | int | Energy Total | 0.01 Wh |
| 38 | string | Power-on State | "memory"/"on"/"off" |
| 39 | string | Relay Status | "relay" |

### Skalierung der Messwerte

Die Rohwerte müssen umgerechnet werden:

```python
# Rohdaten -> Echte Werte
power_watt    = DPS_19 / 10      # z.B. 1865 -> 186.5 W
voltage_volt  = DPS_20 / 10      # z.B. 2310 -> 231.0 V
current_amp   = DPS_18 / 1000    # z.B. 820  -> 0.82 A
energy_wh     = DPS_23 / 100     # z.B. 23000 -> 230.0 Wh
```

**Beispiel Rohdaten:**
```json
{
  "dps": {
    "1": true,
    "17": 93,
    "18": 822,
    "19": 1865,
    "20": 2310,
    "23": 30484
  }
}
```

**Umgerechnet:**
- Status: AN
- Leistung: 186.5 W
- Spannung: 231.0 V
- Strom: 0.82 A

---

## Bibliothek: TinyTuya

Für die Kommunikation wird **TinyTuya** verwendet.

### Installation

```bash
pip3 install tinytuya
```

### Verbindung herstellen

```python
import tinytuya

device = tinytuya.OutletDevice(
    dev_id="bf36487f67d7bb8fc18buj",   # Device ID
    address="192.168.0.73",             # IP-Adresse
    local_key="e3bcb8213df8febf",       # Local Key (geheim!)
    version=3.3                          # Protokoll-Version
)
```

### Status abfragen

```python
status = device.status()
# Ergebnis:
# {'dps': {'1': True, '17': 93, '18': 822, '19': 1865, '20': 2310, ...}}

# Switch-Status
is_on = status["dps"]["1"]  # True = An, False = Aus

# Energiewerte
power_watt = status["dps"]["19"] / 10
voltage_volt = status["dps"]["20"] / 10
current_amp = status["dps"]["18"] / 1000
```

### Schalten

```python
# Einschalten
device.turn_on()

# Ausschalten
device.turn_off()

# Umschalten
device.set_status(not is_on)
```

### Fehlerbehandlung

```python
status = device.status()

if status is None:
    print("Keine Verbindung")
elif "Error" in str(status):
    print(f"Fehler: {status}")
else:
    # Erfolgreich
    pass
```

**Häufige Fehler:**
- `Network Error` - Gerät nicht erreichbar (falsche IP?)
- `Decrypt Error` - Falscher Local Key
- Leere Werte (0) - Gerät braucht 1-2 Sekunden für Refresh

---

## Geräte scannen

### Netzwerk-Scan (findet WiFi-Geräte)

```python
import tinytuya

devices = tinytuya.deviceScan(verbose=True, maxretry=2)
# Zeigt alle Tuya-Geräte im lokalen Netzwerk
```

### Cloud-Abfrage (holt alle Device-Infos inkl. Local Keys)

```python
import tinytuya

cloud = tinytuya.Cloud(
    apiRegion="eu",
    apiKey="x7gt474g4ac9nvwredk4",
    apiSecret="cd29a6ddf61f4197b1965370272a4100"
)

devices = cloud.getdevices()
for d in devices:
    print(f"Name: {d['name']}")
    print(f"Device ID: {d['id']}")
    print(f"Local Key: {d['key']}")
```

---

## Dateien in diesem Verzeichnis

```
remote-plug/
├── README.md           # Diese Dokumentation
├── devices.json        # Alle Geräte mit Credentials
└── SCAN_RESULT.md      # Ergebnis des BLE-Scans
```

### devices.json Struktur

```json
{
  "devices": [
    {
      "name": "Main Light",
      "device_id": "bf36487f67d7bb8fc18buj",
      "local_key": "e3bcb8213df8febf",
      "ip": "192.168.0.73",
      "version": 3.3,
      "connection": "wifi",
      "tested": true
    }
  ],
  "tuya_cloud": {
    "region": "eu",
    "access_id": "x7gt474g4ac9nvwredk4"
  }
}
```

---

## Schnellstart-Beispiel

Komplettes Beispiel zum Testen einer Steckdose:

```python
import tinytuya
import time

# Verbindung herstellen
device = tinytuya.OutletDevice(
    dev_id="bf36487f67d7bb8fc18buj",
    address="192.168.0.73",
    local_key="e3bcb8213df8febf",
    version=3.3
)

# Status abfragen
status = device.status()
dps = status.get("dps", {})

print(f"Switch: {'AN' if dps.get('1') else 'AUS'}")
print(f"Leistung: {dps.get('19', 0) / 10:.1f} W")
print(f"Spannung: {dps.get('20', 0) / 10:.1f} V")
print(f"Strom: {dps.get('18', 0) / 1000:.2f} A")

# Ausschalten
device.turn_off()
time.sleep(1)

# Einschalten
device.turn_on()
```

---

## Integration in GrowPi

### Mögliche Funktionen

1. **Lampensteuerung:** Grow-Lampen nach Zeitplan ein-/ausschalten
2. **Pumpensteuerung:** Bewässerungspumpe steuern
3. **Energiemonitoring:** Stromverbrauch aller Geräte tracken
4. **Notfall-Aus:** Alle Steckdosen auf einmal ausschalten

### API-Endpunkte (Vorschlag)

```
GET  /api/plugs              # Liste aller Steckdosen
GET  /api/plugs/:id          # Status einer Steckdose
POST /api/plugs/:id/on       # Einschalten
POST /api/plugs/:id/off      # Ausschalten
GET  /api/plugs/:id/energy   # Energiemesswerte
```

---

## Troubleshooting

### Gerät nicht erreichbar

1. IP-Adresse prüfen: `ping 192.168.0.73`
2. Netzwerk-Scan durchführen: `tinytuya.deviceScan()`
3. Gerät in Smart Life App prüfen (online?)

### Falscher Local Key

- Local Key ändert sich wenn Gerät neu gepairt wird
- Neu abrufen via Cloud API

### Werte sind 0

- Warten (1-2 Sekunden zwischen Abfragen)
- Erneut abfragen
- Gerät hat evtl. keinen Verbraucher angeschlossen

### BLE-Geräte

- WiFi-Steuerung nicht möglich
- Erfordern Tuya BLE Protokoll (komplexer)
- Alternative: Über Tuya Cloud API steuern

---

## Referenzen

- [TinyTuya GitHub](https://github.com/jasonacox/tinytuya)
- [Tuya IoT Platform](https://iot.tuya.com/)
- [Tuya Local Protocol Dokumentation](https://github.com/codetheweb/tuyapi/wiki)

---

**Erstellt:** 2025-12-06
**Getestet von:** Claude Code
**Hardware:** Raspberry Pi 3B+ (growpi)
