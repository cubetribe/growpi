# GrowPi Roadmap - Geplante Features

**Letzte Aktualisierung**: 2025-12-05
**Status**: Planning Phase
**Platform**: Raspberry Pi 3B+ @ 192.168.0.86

---

## Übersicht

Dieses Dokument definiert geplante Funktionen für das GrowPi-System in priorisierten Phasen.

---

## Phase 1: Kosten-Monitoring & Energie-Tracking

### Feature 1.1: Stromverbrauch-Messung & Kosten-Anzeige

**Ziel**: Energiekosten transparent darstellen und Verbrauch analysieren

#### Anforderungen

**Messung**:
- Stromverbrauch in Watt/kWh erfassen
- Timestamp-basierte Speicherung in SQLite
- Kontinuierliche Messung mit konfigurierbarem Intervall

**Kostenberechnung**:
- Kilowattstunden-Preis (€/kWh) konfigurierbar
- Automatische Berechnung:
  - Tageskosten
  - Monatskosten
  - Jahreskosten
- Historische Kosten-Trends

**UI/UX**:
- Integration in bestehende Statistik-Seite (Web-Interface)
- Kosten-Anzeige unter Sensor-Verlaufs-Charts
- Eingabefeld für kWh-Preis in Settings
- Kosten-Breakdown: Heute / Dieser Monat / Dieses Jahr

#### Technische Umsetzung

**Datenbank-Erweiterung**:
```sql
CREATE TABLE power_readings (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    watt REAL,              -- Aktuelle Leistung in Watt
    kwh_cumulative REAL     -- Kumulierte kWh seit Start
);

CREATE TABLE settings (
    -- Bestehende Felder...
    kwh_price REAL DEFAULT 0.30  -- €/kWh (default: 30 Cent)
);
```

**API-Endpunkte**:
- `GET /api/power/current` - Aktueller Verbrauch (W)
- `GET /api/power/history?range=24h` - Verlauf
- `GET /api/power/costs?period=day|month|year` - Kosten-Aggregation
- `POST /api/settings/kwh_price` - Preis aktualisieren

**Frontend**:
- Neue Komponente: `PowerCostWidget`
- Kosten-Chart mit Recharts (Balkendiagramm)
- Settings-Formular für kWh-Preis

#### Akzeptanzkriterien

- [ ] Stromverbrauch wird sekündlich gemessen und gespeichert
- [ ] kWh-Preis kann in Settings gespeichert werden
- [ ] Tageskosten werden korrekt berechnet (00:00 - 23:59)
- [ ] Monatskosten summieren alle Tage des aktuellen Monats
- [ ] Jahreskosten summieren alle Monate des aktuellen Jahres
- [ ] Kosten-Widget zeigt Echtzeit-Updates (Auto-Refresh)
- [ ] Historische Kosten können als Chart angezeigt werden

#### Priorität
**HOCH** - User-Request, klarer Business-Value

---

## Phase 2: Schaltbare Geräte & Automatisierung

### Feature 2.1: Bluetooth-Schalter Integration

**Ziel**: Schaltbare Geräte (z.B. Entfeuchter) automatisch steuern

#### Anforderungen

**Hardware**:
- Bluetooth-fähiger Schalter (bereits vorhanden & getestet)
- Steuerung via Raspberry Pi Bluetooth
- Ein/Aus-Schaltung (nicht PWM)

**Geräte-Typen**:
- **Entfeuchtungsanlage** (Priorität 1)
- Weitere Geräte später erweiterbar (Heizung, Lüftung, etc.)

#### Feature 2.2: Entfeuchter-Automatik

**Ziel**: Automatische Feuchtigkeitsregelung mit Hysterese-Logik

#### Konfiguration

**Soll-Wert & Toleranzen**:
```yaml
dehumidifier:
  enabled: true
  bluetooth_mac: "XX:XX:XX:XX:XX:XX"
  control_mode: "auto"  # auto | manual | off

  # Feuchtigkeits-Steuerung
  target_humidity: 60.0      # Soll-Wert in %
  start_threshold: 5.0       # Hysterese obere Grenze (+5%)
  stop_threshold: 2.0        # Hysterese untere Grenze (-2%)

  # Beispiel:
  # target = 60%
  # Einschalten bei: 60% + 5% = 65%
  # Ausschalten bei: 60% - 2% = 58%
```

**Logik-Regeln**:
1. **Einschalten**: Wenn `current_humidity > (target + start_threshold)`
2. **Ausschalten**: Wenn `current_humidity < (target - stop_threshold)`
3. **Hysterese**: Verhindert häufiges An/Aus-Schalten
4. **Min-Laufzeit**: Optional, z.B. mindestens 5 Minuten laufen

**UI/UX**:
- Neuer Tab im Web-Interface: "Automatisierung"
- Entfeuchter-Karte mit:
  - Ein/Aus Toggle (manuell)
  - Auto-Modus Toggle
  - Soll-Wert Slider (40-80%)
  - Start-Schwelle Slider (1-10%)
  - Stop-Schwelle Slider (1-10%)
  - Aktueller Status: "Aus" | "Läuft" | "Wartet"
  - Laufzeit-Historie (heute, diese Woche)

#### Technische Umsetzung

**Datenbank-Erweiterung**:
```sql
CREATE TABLE switchable_devices (
    id INTEGER PRIMARY KEY,
    name TEXT,                      -- "Entfeuchter"
    type TEXT,                      -- "dehumidifier"
    bluetooth_mac TEXT,
    enabled BOOLEAN DEFAULT 1
);

CREATE TABLE device_automation_config (
    id INTEGER PRIMARY KEY,
    device_id INTEGER,
    control_mode TEXT,              -- "auto" | "manual" | "off"
    target_value REAL,              -- Soll-Wert (z.B. 60% Luftfeuchtigkeit)
    start_threshold REAL,           -- Einschalt-Schwelle (+5%)
    stop_threshold REAL,            -- Ausschalt-Schwelle (-2%)
    FOREIGN KEY (device_id) REFERENCES switchable_devices(id)
);

CREATE TABLE device_states (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    device_id INTEGER,
    state TEXT,                     -- "on" | "off"
    trigger_reason TEXT,            -- "manual" | "auto_humidity_high" | "auto_humidity_low"
    FOREIGN KEY (device_id) REFERENCES switchable_devices(id)
);
```

**Python Controller**:
```python
# grow_pi/devices/bluetooth_switch.py
class BluetoothSwitch:
    def __init__(self, mac_address: str):
        self.mac = mac_address

    def turn_on(self) -> bool:
        # Bluetooth-Befehl senden
        pass

    def turn_off(self) -> bool:
        # Bluetooth-Befehl senden
        pass

    def get_state(self) -> bool:
        # Status abfragen
        pass

# grow_pi/automation/dehumidifier_controller.py
class DehumidifierController:
    def __init__(self, config, switch, sensor):
        self.config = config
        self.switch = switch
        self.sensor = sensor
        self.last_state = False
        self.last_change_time = None

    def update(self):
        """Wird jede Sekunde aufgerufen"""
        if self.config.control_mode != "auto":
            return

        current_humidity = self.sensor.get_humidity()
        target = self.config.target_value

        # Hysterese-Logik
        if current_humidity > (target + self.config.start_threshold):
            if not self.last_state:
                self.switch.turn_on()
                self.log_state_change("on", "auto_humidity_high")

        elif current_humidity < (target - self.config.stop_threshold):
            if self.last_state:
                self.switch.turn_off()
                self.log_state_change("off", "auto_humidity_low")
```

**API-Endpunkte**:
- `GET /api/devices` - Liste schaltbarer Geräte
- `POST /api/devices/<id>/toggle` - Manuell ein/aus
- `GET /api/devices/<id>/config` - Automation-Config
- `POST /api/devices/<id>/config` - Config aktualisieren
- `GET /api/devices/<id>/history?hours=24` - Schalt-Historie

**Integration in main.py**:
```python
# In grow_pi/main.py run() loop
dehumidifier_controller = DehumidifierController(...)

while True:
    # ... bestehende Logik ...

    # Automatisierung aktualisieren (jede Sekunde)
    dehumidifier_controller.update()

    time.sleep(1)
```

#### Akzeptanzkriterien

- [ ] Bluetooth-Schalter kann manuell ein-/ausgeschaltet werden (API)
- [ ] Soll-Wert für Luftfeuchtigkeit kann gespeichert werden
- [ ] Start-Schwelle und Stop-Schwelle sind konfigurierbar
- [ ] Auto-Modus schaltet Entfeuchter basierend auf Hysterese
- [ ] Mindestens 1 Minute zwischen Schaltvorgängen (Schutz)
- [ ] Schalt-Historie wird in Datenbank gespeichert
- [ ] Web-UI zeigt aktuellen Status und Konfiguration
- [ ] Trigger-Grund wird geloggt (manual vs. auto)

#### Priorität
**MITTEL-HOCH** - Hardware vorhanden, klarer Use-Case

---

## Phase 3: Erweiterte Automatisierung (Future)

### Mögliche Features (noch nicht detailliert)

- **Feature 3.1**: Multi-Geräte-Szenarien (z.B. "Nacht-Modus")
- **Feature 3.2**: Zeitbasierte Schaltungen (z.B. Lüftung 10min/Stunde)
- **Feature 3.3**: Sensor-basierte Trigger (z.B. Heizung bei <18°C)
- **Feature 3.4**: Push-Benachrichtigungen (Telegram/Email)
- **Feature 3.5**: VPD-Optimierung (Vapor Pressure Deficit)

---

## Implementierungs-Reihenfolge

### Vorgeschlagene Reihenfolge

1. **Phase 1.1**: Kosten-Monitoring (1-2 Tage)
   - Stromverbrauch-Messung
   - kWh-Preis-Konfiguration
   - Kosten-Anzeige im Dashboard

2. **Phase 2.1**: Bluetooth-Schalter (1 Tag)
   - Python Bluetooth-Integration
   - Manuelles Ein/Aus via API
   - Status-Anzeige

3. **Phase 2.2**: Entfeuchter-Automatik (2-3 Tage)
   - Hysterese-Logik
   - Auto-Modus Konfiguration
   - UI für Soll-Wert & Schwellen

4. **Testing & Optimierung** (1-2 Tage)
   - Reale Lasttests mit Entfeuchter
   - Hysterese-Parameter optimieren
   - Kosten-Berechnung validieren

**Geschätzte Gesamtdauer**: 5-8 Arbeitstage

---

## Offene Fragen

1. **Stromverbrauch-Messung**:
   - Welcher Sensor wird verwendet? (z.B. Shelly Plug, PZEM-004T)
   - Ist der Sensor bereits vorhanden?
   - Wo wird gemessen? (Gesamtstrom oder pro Gerät?)

2. **Bluetooth-Schalter**:
   - ✅ **Modell**: Tuya-Smart Bluetooth Steckdosen
   - ✅ **Python-Code**: Bereits im Projekt integriert
   - ✅ **Status**: Getestet und funktionsfähig

3. **Entfeuchter**:
   - Max. Schaltfrequenz? (z.B. max. 6x/Stunde)
   - Min. Laufzeit pro Zyklus?
   - Leistungsaufnahme für Kosten-Tracking?

4. **UI-Platzierung**:
   - Neuer Tab "Automatisierung" oder Integration in bestehendes Dashboard?
   - Mobil-optimiert wie bisheriges Interface?

---

## Nächste Schritte

1. **Klärung offener Fragen** (siehe oben)
2. **Hardware-Spezifikation dokumentieren**
3. **Phase 1.1 starten**: Kosten-Monitoring
4. **Prototyp für Bluetooth-Schalter testen**

---

## Change Log

| Datum | Änderung | Autor |
|-------|----------|-------|
| 2025-12-05 | Initial Draft - Phase 1 & 2 definiert | Dennis + Claude |

