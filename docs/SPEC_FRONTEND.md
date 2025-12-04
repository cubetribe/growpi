# Grow-Pi Frontend Specification

**Version:** 1.0.0\
**Status:** Draft\
**Last Updated:** 2025-12-03\
**Author:** Dennis Westermann d.westermann@ol-mg.de

---

## 1. Executive Summary

Grow-Pi is a professional greenhouse management platform designed for commercial
nurseries in Germany. The system provides real-time monitoring of environmental
sensors and automated control of multi-channel grow lighting systems via
Raspberry Pi integration.

This document specifies the web-based frontend application that will be deployed
on a VPS and accessed by users via browser.

---

## 2. Technical Architecture

### 2.1 Technology Stack

| Layer                | Technology                      |
| -------------------- | ------------------------------- |
| Framework            | Next.js 14 (App Router)         |
| Language             | TypeScript (strict mode)        |
| Styling              | TailwindCSS                     |
| UI Components        | shadcn/ui                       |
| Charts               | Recharts                        |
| Database             | Prisma ORM                      |
| DB Engine (Dev)      | SQLite                          |
| DB Engine (Prod)     | PostgreSQL                      |
| Authentication       | JWT in HTTP-only cookies        |
| Internationalization | next-intl or custom i18n        |
| State Management     | React Context + SWR/React Query |

### 2.2 Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         VPS Server                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Next.js Application                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │   Pages     │  │  API Routes │  │  Database   │ │   │
│  │  │  (React)    │  │  (REST)     │  │  (Prisma)   │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS API
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Raspberry Pi (per Zone)                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Pi Controller Software                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │  Sensors    │  │  PWM Lamps  │  │  API Client │ │   │
│  │  │  (RS485)    │  │  (GPIO)     │  │  (HTTP)     │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Multi-Tenant Preparation

The database schema is designed to support future multi-tenant SaaS operations:

- Each `User` can have multiple `Zones` (greenhouses)
- Each `Zone` has its own `LampChannels`, `Sensors`, `Settings`, and
  `AlertConfigs`
- API endpoints are zone-scoped
- Pi devices register to specific zones via API key

---

## 3. Database Schema

### 3.1 Entity Relationship Diagram

```
User (1) ─────< (n) Zone
                    │
         ┌──────────┼──────────┐
         │          │          │
         ▼          ▼          ▼
    LampChannel   Sensor    Settings
         │          │          
         │          ▼          
         │    SensorReading    
         │                     
         └──── AlertConfig ────┘
```

### 3.2 Model Definitions

#### User

```prisma
model User {
  id        String   @id @default(uuid())
  username  String   @unique
  password  String   // bcrypt hashed
  email     String?
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  zones     Zone[]
}
```

#### Zone

```prisma
model Zone {
  id          String         @id @default(uuid())
  name        String
  description String?
  apiKey      String         @unique @default(uuid())
  userId      String
  user        User           @relation(fields: [userId], references: [id])
  lamps       LampChannel[]
  sensors     Sensor[]
  settings    Settings?
  alerts      AlertConfig[]
  piStatus    PiStatus?
  createdAt   DateTime       @default(now())
  updatedAt   DateTime       @updatedAt
}
```

#### LampChannel

```prisma
model LampChannel {
  id          String   @id @default(uuid())
  zoneId      String
  zone        Zone     @relation(fields: [zoneId], references: [id], onDelete: Cascade)
  name        String   // e.g., "Red", "Blue", "Warm White"
  channel     Int      // PWM channel number (1-5)
  color       String?  // Hex color for UI representation
  curve       Json     // Array of { time: "HH:MM", intensity: 0-100 }
  isActive    Boolean  @default(true)
  override    Int?     // Manual override value (null = use curve)
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt

  @@unique([zoneId, channel])
}
```

#### Sensor

```prisma
model Sensor {
  id        String          @id @default(uuid())
  zoneId    String
  zone      Zone            @relation(fields: [zoneId], references: [id], onDelete: Cascade)
  name      String
  type      SensorType
  unit      String          // e.g., "°C", "%", "mS/cm"
  readings  SensorReading[]
  isActive  Boolean         @default(true)
  createdAt DateTime        @default(now())
  updatedAt DateTime        @updatedAt
}

enum SensorType {
  TEMPERATURE
  HUMIDITY
  SOIL_MOISTURE
  SOIL_TEMP
  SOIL_PH
  SOIL_EC
  SOIL_N
  SOIL_P
  SOIL_K
}
```

#### SensorReading

```prisma
model SensorReading {
  id        String   @id @default(uuid())
  sensorId  String
  sensor    Sensor   @relation(fields: [sensorId], references: [id], onDelete: Cascade)
  value     Float
  createdAt DateTime @default(now())

  @@index([sensorId, createdAt])
}
```

#### Settings

```prisma
model Settings {
  id              String  @id @default(uuid())
  zoneId          String  @unique
  zone            Zone    @relation(fields: [zoneId], references: [id], onDelete: Cascade)
  sensorInterval  Int     @default(60)    // seconds (5 - 3600)
  demoMode        Boolean @default(true)
  language        String  @default("de")  // "de" | "en"
  theme           String  @default("dark") // "dark" | "light"
  emailAlerts     String? // Email address for alerts
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt
}
```

#### AlertConfig

```prisma
model AlertConfig {
  id          String     @id @default(uuid())
  zoneId      String
  zone        Zone       @relation(fields: [zoneId], references: [id], onDelete: Cascade)
  sensorType  SensorType
  name        String?
  minValue    Float?
  maxValue    Float?
  emailAlert  Boolean    @default(true)
  pushAlert   Boolean    @default(true)
  enabled     Boolean    @default(true)
  createdAt   DateTime   @default(now())
  updatedAt   DateTime   @updatedAt

  @@unique([zoneId, sensorType])
}
```

#### PiStatus

```prisma
model PiStatus {
  id            String   @id @default(uuid())
  zoneId        String   @unique
  zone          Zone     @relation(fields: [zoneId], references: [id], onDelete: Cascade)
  isOnline      Boolean  @default(false)
  lastHeartbeat DateTime?
  ipAddress     String?
  version       String?
  createdAt     DateTime @default(now())
  updatedAt     DateTime @updatedAt
}
```

---

## 4. API Specification

### 4.1 Authentication Endpoints

#### POST /api/auth/login

Authenticate user and create session.

**Request:**

```json
{
  "username": "admin",
  "password": "Mi83xer#"
}
```

**Response (200):**

```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "username": "admin"
  }
}
```

**Cookies Set:**

- `grow-pi-session`: Signed JWT token (HTTP-only, Secure, SameSite=Strict)

#### POST /api/auth/logout

Destroy session and clear cookies.

#### GET /api/auth/me

Get current authenticated user.

---

### 4.2 Sensor Endpoints

#### GET /api/readings

Get sensor readings with optional filtering.

**Query Parameters:**

| Parameter  | Type     | Required | Description                                 |
| ---------- | -------- | -------- | ------------------------------------------- |
| zoneId     | string   | Yes      | Zone UUID                                   |
| sensorId   | string   | No       | Filter by specific sensor                   |
| sensorType | string   | No       | Filter by sensor type                       |
| range      | string   | No       | Time range: `10m`, `1h`, `24h`, `7d`, `30d` |
| from       | ISO date | No       | Custom start date                           |
| to         | ISO date | No       | Custom end date                             |

**Response (200):**

```json
{
  "readings": [
    {
      "id": "uuid",
      "sensorId": "uuid",
      "sensorType": "TEMPERATURE",
      "sensorName": "Temperatur Luft",
      "value": 24.5,
      "unit": "°C",
      "createdAt": "2025-12-03T10:30:00Z"
    }
  ],
  "meta": {
    "total": 1440,
    "from": "2025-12-02T10:30:00Z",
    "to": "2025-12-03T10:30:00Z"
  }
}
```

#### POST /api/readings

Submit new sensor reading (for Pi).

**Headers:**

- `X-API-Key`: Zone API key

**Request:**

```json
{
  "readings": [
    { "sensorType": "TEMPERATURE", "value": 24.5 },
    { "sensorType": "HUMIDITY", "value": 68.2 }
  ]
}
```

#### GET /api/readings/current

Get latest reading for each sensor in a zone.

**Query Parameters:**

| Parameter | Type   | Required |
| --------- | ------ | -------- |
| zoneId    | string | Yes      |

---

### 4.3 Lighting Endpoints

#### GET /api/lighting

Get all lamp channels and their curves for a zone.

**Query Parameters:**

| Parameter | Type   | Required |
| --------- | ------ | -------- |
| zoneId    | string | Yes      |

**Response (200):**

```json
{
  "lamps": [
    {
      "id": "uuid",
      "name": "Red",
      "channel": 1,
      "color": "#ff4444",
      "isActive": true,
      "override": null,
      "curve": [
        { "time": "06:00", "intensity": 0 },
        { "time": "07:00", "intensity": 30 },
        { "time": "08:00", "intensity": 80 },
        { "time": "18:00", "intensity": 80 },
        { "time": "19:00", "intensity": 30 },
        { "time": "20:00", "intensity": 0 }
      ]
    }
  ]
}
```

#### PUT /api/lighting/:lampId

Update a lamp channel's curve.

**Request:**

```json
{
  "name": "Red",
  "curve": [
    { "time": "06:00", "intensity": 0 },
    { "time": "07:00", "intensity": 50 }
  ]
}
```

#### GET /api/lighting/current

Get current calculated intensity for all lamps based on time.

**Query Parameters:**

| Parameter | Type   | Required |
| --------- | ------ | -------- |
| zoneId    | string | Yes      |

**Response (200):**

```json
{
  "timestamp": "2025-12-03T14:30:00Z",
  "lamps": [
    { "channel": 1, "name": "Red", "intensity": 45 },
    { "channel": 2, "name": "Blue", "intensity": 80 },
    { "channel": 3, "name": "Warm White", "intensity": 100 },
    { "channel": 4, "name": "Cool White", "intensity": 90 },
    { "channel": 5, "name": "UV", "intensity": 20 }
  ]
}
```

#### POST /api/lighting/override

Set manual override for all lamps.

**Request:**

```json
{
  "zoneId": "uuid",
  "action": "all_on" | "all_off" | "reset"
}
```

---

### 4.4 Raspberry Pi Communication Endpoints

#### POST /api/pi/register

Register a new Pi device to a zone.

**Request:**

```json
{
  "apiKey": "zone-api-key",
  "version": "1.0.0",
  "ipAddress": "192.168.1.100"
}
```

**Response (200):**

```json
{
  "success": true,
  "zoneId": "uuid",
  "zoneName": "Gewächshaus 1",
  "config": {
    "sensorInterval": 60,
    "sensors": ["TEMPERATURE", "HUMIDITY", "SOIL_MOISTURE"],
    "lampChannels": [1, 2, 3, 4, 5]
  }
}
```

#### POST /api/pi/heartbeat

Send heartbeat to confirm Pi is online.

**Headers:**

- `X-API-Key`: Zone API key

**Request:**

```json
{
  "status": "online",
  "uptime": 3600,
  "cpuTemp": 45.2,
  "memoryUsage": 42
}
```

#### GET /api/pi/commands

Poll for pending commands (lamp intensities, config changes).

**Headers:**

- `X-API-Key`: Zone API key

**Response (200):**

```json
{
  "lamps": [
    { "channel": 1, "intensity": 45 },
    { "channel": 2, "intensity": 80 },
    { "channel": 3, "intensity": 100 },
    { "channel": 4, "intensity": 90 },
    { "channel": 5, "intensity": 20 }
  ],
  "config": {
    "sensorInterval": 60
  },
  "commands": []
}
```

---

### 4.5 Settings Endpoints

#### GET /api/settings

Get zone settings.

#### PUT /api/settings

Update zone settings.

**Request:**

```json
{
  "zoneId": "uuid",
  "sensorInterval": 30,
  "demoMode": false,
  "language": "de",
  "theme": "dark",
  "emailAlerts": "info@example.com"
}
```

---

### 4.6 Alert Endpoints

#### GET /api/alerts

Get all alert configurations for a zone.

#### PUT /api/alerts/:alertId

Update alert configuration.

**Request:**

```json
{
  "minValue": 10,
  "maxValue": 35,
  "emailAlert": true,
  "pushAlert": true,
  "enabled": true
}
```

#### GET /api/alerts/active

Get currently triggered alerts.

---

## 5. Frontend Pages & Components

### 5.1 Page Structure

```
/app
├── (auth)
│   └── login
│       └── page.tsx
├── (dashboard)
│   ├── layout.tsx          # Main layout with sidebar
│   ├── dashboard
│   │   └── page.tsx        # Overview dashboard
│   ├── lighting
│   │   └── page.tsx        # Lamp control with curve editor
│   ├── sensors
│   │   └── page.tsx        # Sensor data charts
│   └── settings
│       └── page.tsx        # Configuration
└── api
    └── [...]
```

### 5.2 Component Hierarchy

```
<RootLayout>
├── <ThemeProvider>
├── <I18nProvider>
└── <AuthProvider>
    │
    ├── <LoginPage>
    │   ├── <AnimatedBackground>
    │   └── <LoginCard>
    │
    └── <DashboardLayout>
        ├── <Sidebar>
        │   ├── <Logo>
        │   ├── <NavLinks>
        │   ├── <PiStatus>
        │   └── <SettingsToggles>
        │       ├── <LanguageSwitch>
        │       └── <ThemeSwitch>
        │
        ├── <Header>
        │   ├── <Breadcrumbs>
        │   ├── <DemoModeBadge>
        │   └── <UserMenu>
        │
        └── <MainContent>
            │
            ├── <DashboardPage>
            │   ├── <OverviewCards>
            │   │   ├── <SensorCard type="temperature">
            │   │   ├── <SensorCard type="humidity">
            │   │   ├── <SensorCard type="soilMoisture">
            │   │   ├── <SensorCard type="soilEC">
            │   │   └── <SensorCard type="npk">
            │   ├── <LampStatusPanel>
            │   ├── <AlertsPanel>
            │   └── <SystemStatus>
            │
            ├── <LightingPage>
            │   ├── <LampTabs>
            │   ├── <CurveEditor>
            │   │   ├── <CurveGraph>        # SVG/Canvas interactive
            │   │   └── <CurveTable>        # Excel-like editor
            │   ├── <CurveControls>
            │   │   ├── <SaveButton>
            │   │   ├── <ResetButton>
            │   │   ├── <PreviewButton>
            │   │   └── <SyncToPiButton>
            │   └── <MasterOverride>
            │       ├── <AllOnButton>
            │       ├── <AllOffButton>
            │       └── <ResumeButton>
            │
            ├── <SensorsPage>
            │   └── <SensorChartGrid>
            │       └── <ChartPanel> (x9)
            │           ├── <ChartHeader>
            │           │   ├── <Title>
            │           │   ├── <RangeFilter>
            │           │   └── <ExpandButton>
            │           └── <LineChart>
            │
            └── <SettingsPage>
                ├── <GeneralSettings>
                ├── <SensorSettings>
                ├── <AlertSettings>
                ├── <ZoneManagement>
                └── <PiConnection>
```

### 5.3 Key Components Specification

#### CurveEditor

The central component for lamp automation.

**Props:**

```typescript
interface CurveEditorProps {
  lampId: string;
  initialCurve: CurvePoint[];
  onSave: (curve: CurvePoint[]) => Promise<void>;
  disabled?: boolean;
}

interface CurvePoint {
  time: string; // "HH:MM" format
  intensity: number; // 0-100
}
```

**Features:**

- Interactive SVG graph with draggable points
- Click to add new points
- Double-click to delete points
- Smooth interpolation visualization
- Synchronized data table below
- Undo/redo support
- Keyboard navigation (arrow keys to adjust selected point)

#### ChartPanel

Reusable chart component for sensor data.

**Props:**

```typescript
interface ChartPanelProps {
  sensorType: SensorType;
  title: string;
  unit: string;
  color?: string;
  defaultRange?: TimeRange;
  expandable?: boolean;
}

type TimeRange = "10m" | "1h" | "24h" | "7d" | "30d";
```

#### SensorCard

Dashboard overview card.

**Props:**

```typescript
interface SensorCardProps {
  type: SensorType;
  title: string;
  value: number;
  unit: string;
  trend?: "up" | "down" | "stable";
  alertStatus?: "normal" | "warning" | "critical";
}
```

---

## 6. Design System

### 6.1 Color Palette

#### Dark Mode (Primary)

| Name             | Hex                    | Usage                       |
| ---------------- | ---------------------- | --------------------------- |
| Background       | #0a0a0a                | Main background             |
| Surface          | #141414                | Cards, panels               |
| Surface Elevated | #1a1a1a                | Modals, dropdowns           |
| Border           | #2a2a2a                | Default borders             |
| Border Accent    | #11ff55                | Highlighted borders         |
| Text Primary     | #ffffff                | Main text                   |
| Text Secondary   | #888888                | Muted text                  |
| Accent           | #11ff55                | Primary accent (neon green) |
| Accent Glow      | rgba(17, 255, 85, 0.3) | Glow effects                |
| Error            | #ff4444                | Error states                |
| Warning          | #ffaa00                | Warning states              |
| Success          | #11ff55                | Success states              |

#### Light Mode

| Name             | Hex     | Usage                         |
| ---------------- | ------- | ----------------------------- |
| Background       | #f5f5f5 | Main background               |
| Surface          | #ffffff | Cards, panels                 |
| Surface Elevated | #ffffff | Modals, dropdowns             |
| Border           | #e0e0e0 | Default borders               |
| Border Accent    | #00aa44 | Highlighted borders           |
| Text Primary     | #1a1a1a | Main text                     |
| Text Secondary   | #666666 | Muted text                    |
| Accent           | #00aa44 | Primary accent (darker green) |

### 6.2 Typography

| Element | Font           | Size | Weight |
| ------- | -------------- | ---- | ------ |
| H1      | Inter          | 32px | 700    |
| H2      | Inter          | 24px | 600    |
| H3      | Inter          | 20px | 600    |
| Body    | Inter          | 16px | 400    |
| Small   | Inter          | 14px | 400    |
| Caption | Inter          | 12px | 400    |
| Mono    | JetBrains Mono | 14px | 400    |

### 6.3 Spacing Scale

```
4px  - xs
8px  - sm
12px - md
16px - base
24px - lg
32px - xl
48px - 2xl
64px - 3xl
```

### 6.4 Animation Guidelines

| Animation             | Duration | Easing                 |
| --------------------- | -------- | ---------------------- |
| Hover effects         | 150ms    | ease-out               |
| Panel expand/collapse | 300ms    | ease-in-out            |
| Page transitions      | 200ms    | ease-out               |
| Glow pulse            | 2000ms   | ease-in-out (infinite) |
| Vine growth           | 20000ms  | linear (infinite)      |
| Particle float        | 10000ms  | linear (infinite)      |

### 6.5 Effects

#### Glassmorphism

```css
.glass-panel {
  background: rgba(20, 20, 20, 0.8);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
}
```

#### Neon Glow

```css
.neon-border {
  box-shadow:
    0 0 5px rgba(17, 255, 85, 0.3),
    0 0 10px rgba(17, 255, 85, 0.2),
    0 0 20px rgba(17, 255, 85, 0.1);
  border: 1px solid rgba(17, 255, 85, 0.5);
}
```

#### Animated Vines

SVG-based decorative elements with CSS keyframe animations:

- Slow growth animation (scale + opacity)
- Subtle sway animation
- Positioned at screen edges

---

## 7. Internationalization (i18n)

### 7.1 Supported Languages

- German (de) - Default
- English (en)

### 7.2 Translation File Structure

```
/messages
├── de.json
└── en.json
```

### 7.3 Key Namespaces

```json
{
  "common": {
    "save": "Speichern",
    "cancel": "Abbrechen",
    "delete": "Löschen",
    "loading": "Laden...",
    "error": "Fehler"
  },
  "auth": {
    "login": "Anmelden",
    "logout": "Abmelden",
    "username": "Benutzername",
    "password": "Passwort"
  },
  "dashboard": {
    "title": "Übersicht",
    "temperature": "Temperatur",
    "humidity": "Luftfeuchtigkeit"
  },
  "lighting": {
    "title": "Beleuchtung",
    "channel": "Kanal",
    "intensity": "Intensität",
    "curve": "Automatisierungskurve"
  },
  "sensors": {
    "title": "Sensoren",
    "soilMoisture": "Bodenfeuchtigkeit",
    "soilEC": "Boden-Leitfähigkeit"
  },
  "settings": {
    "title": "Einstellungen",
    "general": "Allgemein",
    "alerts": "Benachrichtigungen"
  }
}
```

---

## 8. State Management

### 8.1 Global State (React Context)

```typescript
// AuthContext
interface AuthState {
  user: User | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

// ThemeContext
interface ThemeState {
  theme: "dark" | "light";
  setTheme: (theme: "dark" | "light") => void;
}

// SettingsContext
interface SettingsState {
  language: "de" | "en";
  demoMode: boolean;
  sensorInterval: number;
  setLanguage: (lang: "de" | "en") => void;
  setDemoMode: (enabled: boolean) => void;
}
```

### 8.2 Server State (SWR/React Query)

```typescript
// Sensor readings
useSensorReadings(zoneId, sensorType, range);

// Lamp channels
useLampChannels(zoneId);
useLampChannel(lampId);
useUpdateLampCurve(lampId);

// Current values
useCurrentSensorValues(zoneId); // Auto-refresh every N seconds
useCurrentLampIntensities(zoneId);

// Pi status
usePiStatus(zoneId); // Polling for online status
```

---

## 9. Demo Mode

When demo mode is enabled:

### 9.1 Simulated Sensor Data

```typescript
function generateDemoReading(sensorType: SensorType): number {
  const baseValues = {
    TEMPERATURE: 22, // ±5°C variation
    HUMIDITY: 65, // ±15% variation
    SOIL_MOISTURE: 45, // ±20% variation
    SOIL_TEMP: 18, // ±3°C variation
    SOIL_PH: 6.5, // ±0.5 variation
    SOIL_EC: 1.8, // ±0.4 variation
    SOIL_N: 150, // ±50 variation
    SOIL_P: 50, // ±20 variation
    SOIL_K: 200, // ±40 variation
  };

  // Add time-based patterns (e.g., temperature higher at noon)
  // Add random noise within realistic bounds
  // Return realistic value
}
```

### 9.2 Simulated Lamp Control

- Lamp intensities calculated from stored curves
- Time-based interpolation runs in browser
- No actual Pi communication
- "Sync to Pi" shows success message

### 9.3 UI Indicators

- "DEMO MODE" badge in header
- Different border color (orange instead of green)
- Tooltip explaining demo mode

---

## 10. Error Handling

### 10.1 API Error Responses

```typescript
interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

// Error codes
type ErrorCode =
  | "UNAUTHORIZED"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "VALIDATION_ERROR"
  | "PI_OFFLINE"
  | "RATE_LIMITED"
  | "INTERNAL_ERROR";
```

### 10.2 User-Facing Error Messages

All error messages are translated and user-friendly:

```json
{
  "errors": {
    "UNAUTHORIZED": "Bitte melden Sie sich an.",
    "PI_OFFLINE": "Der Raspberry Pi ist nicht erreichbar.",
    "VALIDATION_ERROR": "Bitte überprüfen Sie Ihre Eingaben."
  }
}
```

### 10.3 Error Boundaries

React Error Boundaries wrap major page sections to prevent full app crashes.

---

## 11. Security Considerations

### 11.1 Authentication

- Passwords hashed with bcrypt (cost factor 12)
- JWT tokens expire after 24 hours
- HTTP-only cookies prevent XSS token theft
- CSRF protection via SameSite cookie attribute

### 11.2 API Security

- All endpoints require authentication (except login)
- Pi endpoints authenticated via API key header
- Rate limiting on sensitive endpoints
- Input validation on all endpoints

### 11.3 Data Protection

- No sensitive data logged
- API keys can be regenerated
- Prepared for GDPR compliance (data export, deletion)

---

## 12. Performance Requirements

| Metric                       | Target  |
| ---------------------------- | ------- |
| Initial page load            | < 3s    |
| API response time            | < 500ms |
| Chart render (1000 points)   | < 100ms |
| Real-time update latency     | < 2s    |
| Lighthouse Performance Score | > 90    |

---

## 13. Browser Support

| Browser        | Minimum Version |
| -------------- | --------------- |
| Chrome         | 90+             |
| Firefox        | 88+             |
| Safari         | 14+             |
| Edge           | 90+             |
| Mobile Safari  | iOS 14+         |
| Chrome Android | 90+             |

---

## 14. Future Considerations

### Phase 2 Features (Prepared in Architecture)

- Multi-zone support (multiple greenhouses per user)
- User registration and subscription management
- Team access with role-based permissions
- Telegram/WhatsApp alert integration
- Historical data export (CSV, Excel)
- Automated reports

### Phase 3 Features

- AI-based growth optimization suggestions
- Weather API integration
- Irrigation system control
- Camera integration with timelapse
- Mobile app (React Native)

---

## Appendix A: Environment Variables

```env
# Database
DATABASE_URL="file:./dev.db"

# Authentication
JWT_SECRET="your-secret-key-min-32-chars"
SESSION_COOKIE_NAME="grow-pi-session"

# Email (for alerts)
SMTP_HOST=""
SMTP_PORT=""
SMTP_USER=""
SMTP_PASS=""
ALERT_FROM_EMAIL=""

# Application
NEXT_PUBLIC_APP_URL="http://localhost:3000"
DEMO_MODE_DEFAULT="true"
```

---

## Appendix B: Seed Data

Default zone configuration for development:

```typescript
const defaultLampCurves = {
  red: [
    { time: "05:30", intensity: 0 },
    { time: "06:00", intensity: 30 },
    { time: "07:00", intensity: 50 },
    { time: "08:00", intensity: 20 },
    { time: "09:00", intensity: 0 },
    { time: "17:00", intensity: 0 },
    { time: "18:00", intensity: 20 },
    { time: "19:00", intensity: 50 },
    { time: "20:00", intensity: 30 },
    { time: "20:30", intensity: 0 },
  ],
  blue: [
    { time: "07:00", intensity: 0 },
    { time: "08:00", intensity: 50 },
    { time: "09:00", intensity: 100 },
    { time: "17:00", intensity: 100 },
    { time: "18:00", intensity: 50 },
    { time: "19:00", intensity: 0 },
  ],
  // ... etc
};
```

---

**End of Frontend Specification**
