# GrowPi - Architektur-Dokumentation

## System-Übersicht

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Web Browser   │         │  Raspberry Pi    │         │    Sensoren     │
│   (Frontend)    │◄───────►│    (Backend)     │◄───────►│   & Hardware    │
│                 │  HTTP   │                  │  GPIO   │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
```

## Komponenten

### 1. Frontend (Web-Dashboard)

**Technologie**: React 18 + Modern JavaScript

**Hauptaufgaben**:
- Daten-Visualisierung
- Echtzeit-Updates via WebSocket/Polling
- Benutzer-Interface für Konfiguration
- Responsive Design für Mobile/Desktop

**Geplante Pages**:
- `/` - Landing Page / Dashboard
- `/sensors` - Sensor-Übersicht
- `/system` - System-Informationen
- `/settings` - Konfiguration

### 2. Backend (Raspberry Pi)

**Technologie**: Node.js oder Python (TBD)

**Hauptaufgaben**:
- REST API für Frontend
- Datensammlung von Sensoren
- System-Monitoring (CPU, RAM, Temperatur)
- Datenbank für historische Werte
- GPIO-Steuerung

**API Endpoints (geplant)**:
```
GET  /api/system/status       # CPU, RAM, Temperatur
GET  /api/sensors             # Alle Sensor-Daten
GET  /api/sensors/:id         # Einzelner Sensor
POST /api/sensors/:id/config  # Sensor konfigurieren
GET  /api/history/:sensor     # Historische Daten
```

### 3. Hardware (Raspberry Pi)

**Konfiguration**:
- **Modell**: TBD (wird beim ersten SSH-Zugriff ermittelt)
- **OS**: Raspberry Pi OS
- **Hostname**: growpi
- **IP**: 192.168.0.86
- **SSH**: Port 22

**Angeschlossene Hardware**:
- (wird später dokumentiert)

## Datenfluss

### Sensor-Daten sammeln
```
1. Backend liest Sensor-Daten (via GPIO/I2C)
2. Daten werden validiert und formatiert
3. Speicherung in lokaler Datenbank
4. Bei API-Request: Daten an Frontend senden
```

### System-Monitoring
```
1. Backend sammelt System-Metriken (CPU, RAM, etc.)
2. Regelmäßige Updates (z.B. alle 5 Sekunden)
3. Frontend pollt API oder erhält WebSocket-Updates
4. Visualisierung im Dashboard
```

## Kommunikation

### HTTP REST API
- Frontend ↔ Backend Kommunikation
- JSON als Datenformat
- CORS-Konfiguration für lokales Development
- Später: HTTPS mit SSL-Zertifikaten

### WebSocket (optional)
- Echtzeit-Updates für Dashboard
- Reduziert API-Polling
- Effiziente Datenübertragung

## Sicherheit

### Development
- Lokales Netzwerk (192.168.0.x)
- SSH mit Passwort (später: SSH-Keys)
- Keine externe Exposition

### Production (geplant)
- SSL/TLS Verschlüsselung
- Authentifizierung (Login-System)
- SSH-Key basierte Authentifizierung
- Firewall-Konfiguration
- Rate-Limiting für API

## Datenbank

**Option 1: SQLite** (empfohlen für Start)
- Einfaches Setup
- Keine zusätzliche Installation nötig
- Ausreichend für historische Sensor-Daten
- File-basiert

**Option 2: PostgreSQL** (für später)
- Mehr Features
- Bessere Performance bei vielen Daten
- Komplexere Queries

**Schema (geplant)**:
```sql
sensors (
  id, name, type, unit, config
)

sensor_readings (
  id, sensor_id, value, timestamp
)

system_metrics (
  id, cpu_usage, ram_usage, temperature, timestamp
)
```

## Deployment-Strategie

### Phase 1: Lokale Entwicklung
1. Frontend lokal entwickeln (Port 3000)
2. Backend-API-Mock für Tests
3. SSH-Zugriff zum Pi einrichten

### Phase 2: Pi-Integration
1. Backend auf Raspberry Pi deployen
2. Datensammlung implementieren
3. Frontend mit echtem Backend verbinden

### Phase 3: Production
1. Frontend Build optimieren
2. Frontend auf Server deployen
3. Reverse Proxy Setup (nginx)
4. SSL-Zertifikate einrichten
5. Monitoring und Logging

## Technologie-Entscheidungen

### Warum React?
- Moderne, gut unterstützte Library
- Große Community
- Viele UI-Komponenten verfügbar
- Gute Performance

### Warum Node.js für Backend? (TBD)
- JavaScript Full-Stack
- Gute GPIO-Libraries verfügbar
- Asynchrone I/O ideal für Sensor-Polling
- Leichtgewichtig für Raspberry Pi

**Alternative: Python**
- Sehr gute Raspberry Pi Unterstützung
- Viele Sensor-Libraries
- Einfacher für Hardware-Zugriff

## Performance-Überlegungen

### Raspberry Pi Optimierung
- Effizientes Sensor-Polling (nicht zu häufig)
- Caching von häufig angefragten Daten
- Datenbank-Indexing für schnelle Queries
- Alte Daten regelmäßig archivieren

### Frontend Optimierung
- Code-Splitting
- Lazy Loading für Pages
- Optimierte Bundle-Size
- Service Worker für Offline-Fähigkeit

## Monitoring & Logging

### Backend
- System-Logs (systemd/journald)
- API-Request Logging
- Fehler-Tracking
- Performance-Metriken

### Frontend
- Console Error Tracking
- User Analytics (optional)
- Performance Monitoring

## Next Steps

1. Entscheidung: Node.js vs Python für Backend
2. Erste Backend-Implementation
3. SSH-Verbindung testen und System-Info abrufen
4. Frontend-Basis aufsetzen
5. Erste Integration testen

---

**Dokumentversion**: 1.0
**Letzte Aktualisierung**: 2025-12-03
**Autor**: Dennis Westermann
