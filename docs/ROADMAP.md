# GrowPi Roadmap - Geplante Features

**Letzte Aktualisierung**: 2025-12-06
**Status**: Phase 2 abgeschlossen, Phase 1 in Arbeit
**Platform**: Raspberry Pi 3B+ @ 192.168.0.86

---

## Übersicht

Dieses Dokument definiert geplante Funktionen für das GrowPi-System in priorisierten Phasen.

---

## Phase 2: Schaltbare Geräte & Automatisierung ✅ ABGESCHLOSSEN

### Feature 2.1: Tuya Smart Plug Integration ✅

**Status**: FERTIG (2025-12-06)

**Implementiert**:
- TuyaCloudService für Smart Plug Steuerung via Cloud API
- Unterstützung für WiFi und BLE Steckdosen
- 6 Geräte verbunden (Main Light, Wohnzimmer, Mittags Sonne, FR main, ANTELA, Pumpe)

**Dateien**:
- `utils/tuya_cloud.py` - Tuya Cloud API Service

### Feature 2.2: Entfeuchter-Automatik ✅

**Status**: FERTIG (2025-12-06)

**Implementiert**:
- Neue "Room" Seite im Web-Interface
- Live Temperatur & Luftfeuchtigkeit vom DHT22
- Hysterese-Logik: AN wenn > threshold_high, AUS wenn < threshold_low
- Konfigurierbar: Sollwert, oberer/unterer Schwellwert
- Minimale Lauf-/Auszeit zum Kompressorschutz
- Manuell AN/AUS + Automatik-Toggle
- Manuelle Buttons deaktiviert bei Automatik-Modus
- Startup-Sync: Echter Steckdosen-Status wird beim Start von Cloud abgefragt

**Dateien**:
- `utils/dehumidifier_controller.py` - Hysterese Controller
- `config/room_config.json` - Konfiguration
- `web/api.py` - Room API Endpoints
- `web/static/index.html` - Room Tab UI

**Default-Konfiguration**:
```json
{
  "dehumidifier": {
    "enabled": true,
    "target": 60.0,
    "threshold_high": 65.0,
    "threshold_low": 55.0,
    "device_id": "bfc705014c6241667avzn8",
    "min_run_time": 60,
    "min_off_time": 60
  }
}
```

---

## Phase 1: Kosten-Monitoring & Energie-Tracking 🔄 IN ARBEIT

### Feature 1.1: Stromverbrauch-Messung & Kosten-Anzeige

**Ziel**: Energiekosten transparent darstellen und Verbrauch analysieren

#### Datenquellen

**Bereits verfügbar**:
- Tuya Smart Plugs liefern Power-Daten (Watt, Volt, Ampere)
- `TuyaCloudService.get_device_status()` gibt `cur_power`, `cur_voltage`, `cur_current` zurück
- Daten werden bereits in `plug_logs` Tabelle gespeichert

**Bestehende Datenbank-Tabelle** (`database/db.py`):
```sql
plug_logs (
    id TEXT PRIMARY KEY,
    timestamp DATETIME,
    plug_id TEXT,
    plug_name TEXT,
    switch_state INTEGER,
    power REAL,      -- Watt
    voltage REAL,    -- Volt
    current REAL,    -- Ampere
    synced_at DATETIME
)
```

#### Anforderungen

**Kostenberechnung**:
- kWh-Preis (€/kWh) konfigurierbar in Settings
- Berechnung aus Watt-Messungen über Zeit
- Aggregation: Heute, Diese Woche, Dieser Monat, Dieses Jahr

**UI/UX**:
- Neuer Tab "Kosten" oder Integration in "Verlauf"
- Kosten-Übersicht mit Breakdown pro Gerät
- Historische Trends als Chart
- Settings: kWh-Preis Eingabe

#### Technische Umsetzung

**Datenbank-Erweiterung**:
```sql
-- Neue Settings-Spalte
ALTER TABLE settings ADD COLUMN kwh_price REAL DEFAULT 0.30;

-- Aggregations-View (optional)
CREATE VIEW daily_power_consumption AS
SELECT
    date(timestamp) as date,
    plug_name,
    SUM(power * 60 / 3600 / 1000) as kwh  -- Watt → kWh (60s Intervall)
FROM plug_logs
GROUP BY date(timestamp), plug_name;
```

**Neue API-Endpunkte**:
- `GET /api/costs/summary` - Kosten-Übersicht (Tag/Woche/Monat/Jahr)
- `GET /api/costs/history?range=7d` - Historische Kosten
- `GET /api/costs/by-device` - Kosten pro Gerät
- `GET /api/settings/kwh_price` - Preis lesen
- `POST /api/settings/kwh_price` - Preis setzen

**Berechnungslogik**:
```python
def calculate_kwh(power_readings: List[PlugLog], interval_seconds: int = 60) -> float:
    """
    Berechnet kWh aus Watt-Messungen.

    Formel: kWh = Σ(Watt × Intervall_in_Stunden)
    Bei 60s Intervall: kWh = Σ(Watt × (60/3600)) = Σ(Watt / 60)
    """
    total_kwh = 0
    for reading in power_readings:
        watt_hours = reading.power * (interval_seconds / 3600)
        total_kwh += watt_hours / 1000  # Wh → kWh
    return total_kwh

def calculate_cost(kwh: float, price_per_kwh: float) -> float:
    """Berechnet Kosten in Euro."""
    return kwh * price_per_kwh
```

**Frontend**:
- Kosten-Widget mit Tabs: Heute | Woche | Monat | Jahr
- Balkendiagramm (Recharts) mit täglichen Kosten
- Tortendiagramm für Kosten-Verteilung pro Gerät
- Settings: Eingabefeld für kWh-Preis (Default: 0.30 €)

#### Akzeptanzkriterien

- [ ] kWh-Preis kann in Settings gespeichert werden
- [ ] Tageskosten werden korrekt aus plug_logs berechnet
- [ ] Wochenkosten aggregieren 7 Tage
- [ ] Monatskosten aggregieren alle Tage des aktuellen Monats
- [ ] Kosten pro Gerät werden separat angezeigt
- [ ] Historische Kosten als Chart (letzte 30 Tage)
- [ ] Auto-Refresh alle 60 Sekunden

#### Priorität
**HOCH** - User-Request, klarer Business-Value

---

## Phase 3: Erweiterte Automatisierung (Future)

### Mögliche Features (noch nicht detailliert)

- **Feature 3.1**: Multi-Geräte-Szenarien (z.B. "Nacht-Modus")
- **Feature 3.2**: Zeitbasierte Schaltungen (z.B. Lüftung 10min/Stunde)
- **Feature 3.3**: Sensor-basierte Trigger (z.B. Heizung bei <18°C)
- **Feature 3.4**: Push-Benachrichtigungen (Telegram/Email)
- **Feature 3.5**: VPD-Optimierung (Vapor Pressure Deficit)
- **Feature 3.6**: Bewässerungssteuerung (Pumpe nach Zeitplan/Bodenfeuchtigkeit)

---

## Implementierungs-Reihenfolge

### Abgeschlossen ✅

1. **Phase 2.1**: Tuya Smart Plug Integration ✅
2. **Phase 2.2**: Entfeuchter-Automatik ✅

### Aktuell 🔄

3. **Phase 1.1**: Kosten-Monitoring
   - kWh-Preis-Konfiguration
   - Kosten-Berechnung aus plug_logs
   - Kosten-Tab im Web-Interface

### Geplant 📋

4. **Phase 3.x**: Erweiterte Automatisierung
   - Nach Bedarf priorisieren

---

## Offene Fragen

1. **Stromverbrauch-Messung**:
   - ✅ **Quelle**: Tuya Smart Plugs mit Power-Monitoring
   - ✅ **Speicherung**: plug_logs Tabelle (60s Intervall)
   - Frage: Alle Plugs messen Power oder nur bestimmte?

2. **Kosten-Berechnung**:
   - Default kWh-Preis: 0.30 € (ca. deutscher Durchschnitt)
   - Soll es verschiedene Tarife geben (Tag/Nacht)?

3. **UI-Platzierung**:
   - Neuer Tab "Kosten" oder in "Verlauf" integrieren?
   - Separate Mobile-Ansicht nötig?

---

## Change Log

| Datum | Änderung | Autor |
|-------|----------|-------|
| 2025-12-06 | Phase 2 (Entfeuchter) abgeschlossen, Roadmap aktualisiert | Dennis + Claude |
| 2025-12-05 | Initial Draft - Phase 1 & 2 definiert | Dennis + Claude |
