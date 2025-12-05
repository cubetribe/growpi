# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**GrowPi** is a professional greenhouse management platform for commercial nurseries. The system provides real-time environmental monitoring and automated grow light control via Raspberry Pi integration.

**Architecture**: Monorepo with Next.js frontend + future Raspberry Pi controller

**Deployed at**: http://growpi.nm-forum.de

---

## Tech Stack

### Frontend (Production-Ready)
- **Framework**: Next.js 13.5.1 with App Router
- **Language**: TypeScript (strict mode)
- **Database**: Supabase (PostgreSQL)
- **Styling**: TailwindCSS
- **UI Components**: shadcn/ui (Radix UI primitives)
- **Charts**: Recharts
- **Authentication**: JWT in HTTP-only cookies
- **i18n**: German (de) / English (en)

### Hardware Integration (ACTIVE - 2025-12-05)
- **Target**: Raspberry Pi 3B+ (hostname: growpi, IP: 192.168.0.86)
- **Backend**: Python 3.13 with pigpio
- **Communication**: Local Flask API on port 5000
- **Sensors**: DHT22 temperature/humidity (GPIO 4)
- **Lighting**: 4-channel PWM LED control

#### Pin Configuration (FINAL)
| Channel | Name | GPIO | Pin |
|---------|------|------|-----|
| 1 | Far Red | 16 | 36 |
| 2 | Warm White | 13 | 33 |
| 3 | Cool White | 12 | 32 |
| 4 | UV | 18 | 12 |

---

## Development Commands

### Frontend Development

```bash
# Start development server (default port 3000)
cd frontend
npm run dev

# Type checking (critical before commits)
npm run typecheck

# Build for production
npm run build

# Start production build
npm start

# Linting
npm run lint

# Database operations
npm run db:push          # Push Prisma schema to Supabase
npm run db:studio        # Open Prisma Studio
npm run seed             # Seed demo data
```

### SSH Access to Raspberry Pi

```bash
# Credentials in .env file (DO NOT COMMIT)
ssh admin@192.168.0.86
# Hostname: growpi
```

---

## Project Structure

```
GrowPi/
├── frontend/                    # Next.js application
│   ├── app/
│   │   ├── (dashboard)/         # Protected dashboard routes
│   │   │   ├── layout.tsx       # Sidebar + Header layout
│   │   │   ├── dashboard/       # Main overview
│   │   │   ├── lighting/        # Lamp curve editor
│   │   │   ├── sensors/         # Sensor charts
│   │   │   └── settings/        # Configuration
│   │   ├── login/               # Authentication page
│   │   ├── api/                 # API routes
│   │   │   ├── auth/            # Login/logout endpoints
│   │   │   ├── lighting/        # Lamp control API
│   │   │   ├── sensors/         # Sensor data API
│   │   │   └── pi/              # Raspberry Pi communication
│   │   └── globals.css          # Dark theme styles
│   ├── components/
│   │   ├── ui/                  # shadcn/ui components
│   │   └── dashboard/           # Custom components
│   ├── contexts/
│   │   └── LanguageContext.tsx  # i18n state
│   ├── supabase/
│   │   └── migrations/          # Database schema
│   ├── middleware.ts            # Auth protection
│   └── next.config.js
├── docs/
│   ├── ARCHITECTURE.md          # System overview
│   ├── SPEC_FRONTEND.md         # Detailed frontend spec
│   └── SPEC_RASPBERRY_PI.md     # Hardware controller spec
├── .env                         # Secrets (NEVER COMMIT)
└── CHANGELOG.md                 # Version history
```

---

## Key Architecture Patterns

### Multi-Tenant Database Design

The database schema supports future SaaS expansion with multi-tenancy:

```
User (1) ──< (n) Zone
                │
     ┌──────────┼──────────┐
     │          │          │
     ▼          ▼          ▼
 LampChannel  Sensor   Settings
     │          │
     │          ▼
     │    SensorReading
     │
     └──── AlertConfig
```

**Key Concepts**:
- Each user owns multiple **Zones** (greenhouses)
- Zone-scoped API access via `zoneId` query parameters
- Raspberry Pi authenticates with zone-specific API keys
- Row-Level Security (RLS) enforces data isolation

### API Communication Protocol

**Frontend ↔ Next.js API Routes**:
- RESTful JSON endpoints under `/api/*`
- Protected with JWT cookie authentication
- All routes validate `zoneId` belongs to authenticated user

**Raspberry Pi ↔ VPS Server** (Future):
```
1. Register: POST /api/pi/register (with API key)
2. Heartbeat: POST /api/pi/heartbeat (every 30s)
3. Send Readings: POST /api/pi/readings (every 60s default)
4. Poll Commands: GET /api/pi/commands (every 10s)
```

### Lighting Curve System

**Data Format**:
```json
{
  "curve": [
    { "time": "06:00", "intensity": 0 },
    { "time": "08:00", "intensity": 80 },
    { "time": "20:00", "intensity": 0 }
  ]
}
```

**Interpolation**:
- Linear interpolation between curve points
- Handles midnight wrap-around (23:59 → 00:00)
- Pi controller recalculates intensity every second
- Frontend displays real-time preview

---

## Critical Development Rules

### Authentication Flow

1. **Login**: POST `/api/auth/login` with username/password
2. **Session**: JWT stored in HTTP-only cookie (`grow-pi-session`)
3. **Middleware**: `middleware.ts` redirects unauthenticated users
4. **API Protection**: All API routes check auth status via cookie

**Demo Credentials**:
- Username: `admin`
- Password: `Mi83xer#` (specified in SPEC_FRONTEND.md)

### Database Access Pattern

**NEVER directly import Prisma client in pages**. Always use API routes:

```typescript
// ❌ WRONG - In page.tsx
import prisma from '@/lib/db'
const data = await prisma.sensor.findMany()

// ✅ CORRECT - In page.tsx
const response = await fetch('/api/sensors?zoneId=...')
const data = await response.json()

// ✅ CORRECT - In app/api/sensors/route.ts
import prisma from '@/lib/db'
export async function GET() {
  const data = await prisma.sensor.findMany()
  return Response.json(data)
}
```

### Security Requirements

**Environment Variables**:
- `.env` contains sensitive credentials (Supabase, JWT secret, SSH passwords)
- **NEVER commit `.env`** - it's in `.gitignore`
- Use `.env.example` as template for new developers

**Row-Level Security**:
- All database queries automatically filtered by `auth.uid()`
- API routes must pass authenticated user ID to queries
- Raspberry Pi uses API key in `X-API-Key` header

### TypeScript Strict Mode

This project uses **strict TypeScript**. All errors must be fixed before committing:

```bash
# This MUST pass with 0 errors
npm run typecheck
```

Common issues:
- Missing `null` checks when fetching data
- Untyped API responses (use `interface` definitions)
- `any` types (avoid or explicitly annotate)

---

## Working with Lighting System

### Curve Editor Component

**Location**: `app/(dashboard)/lighting/page.tsx`

**Features**:
- Tab-based interface for 5 lamp channels (Red, Blue, Warm White, Cool White, UV)
- Time/Intensity table with inline editing
- Add/Remove curve points
- Real-time validation (intensity 0-100)
- Save button with optimistic UI updates
- Reset button to revert changes

**State Management**:
```typescript
const [lamps, setLamps] = useState<LampChannel[]>([])        // Original data
const [editedLamps, setEditedLamps] = useState<LampChannel[]>([])  // Edits
const [activeTab, setActiveTab] = useState(0)
```

**API Integration**:
```typescript
// Fetch lamps
GET /api/lighting?zoneId={uuid}

// Update curve
PUT /api/lighting
Body: { lampId: string, curve: CurvePoint[] }

// Override all lamps
POST /api/lighting/override
Body: { action: "all_on" | "all_off", zoneId: string }
```

### Manual Override System

**Use Case**: Emergency full power or shutdown

**Implementation**:
1. User clicks "All On" or "All Off"
2. API route updates ALL lamp curves to single point at current time
3. Intensity set to 100 (on) or 0 (off)
4. Frontend refetches data to show changes
5. Raspberry Pi polls `/api/pi/commands` and receives new curves

---

## Sensor Data & Charts

### Sensor Types

Defined in Supabase schema:
- `temperature` - Air temperature (°C)
- `humidity` - Air humidity (%)
- `soilMoisture` - Soil moisture (%)
- `soilTemp` - Soil temperature (°C)
- `soilPH` - Soil pH (pH)
- `soilEC` - Soil electrical conductivity (mS/cm)
- `soilN`, `soilP`, `soilK` - NPK nutrients (mg/kg)

### Time-Series Queries

**API Endpoint**: `GET /api/sensors?zoneId={uuid}&range=24h`

**Supported Ranges**:
- `10m` - Last 10 minutes
- `1h` - Last hour
- `24h` - Last 24 hours (default)
- `7d` - Last 7 days
- `30d` - Last 30 days

**Performance Optimization**:
- Index on `(sensor_id, created_at DESC)`
- Limit query results to avoid memory issues
- Consider data aggregation for ranges > 7 days

---

## Demo Mode

**Purpose**: Allow testing without Raspberry Pi hardware

**Behavior**:
- Lamp curves calculated in browser with time interpolation
- Sensor readings generated with realistic patterns + noise
- "DEMO MODE" badge displayed in header
- Database operations still work (curves can be saved)

**Configuration**:
- Stored in `settings` table per zone
- Toggle in Settings page
- Default: `true` (demo mode enabled)

---

## Internationalization

**Implementation**: React Context (`contexts/LanguageContext.tsx`)

**Translation Files**: `frontend/messages/{de,en}.json`

**Usage**:
```typescript
import { useLanguage } from '@/contexts/LanguageContext'

function Component() {
  const { t, language, setLanguage } = useLanguage()

  return (
    <div>
      <h1>{t('dashboard.title')}</h1>
      <button onClick={() => setLanguage('en')}>English</button>
    </div>
  )
}
```

**Key Namespaces**:
- `common.*` - Shared UI text (save, cancel, delete)
- `dashboard.*` - Overview page
- `lighting.*` - Lamp control
- `sensors.*` - Sensor monitoring
- `settings.*` - Configuration

---

## Styling Guidelines

### Theme System

**Primary Colors** (Dark Mode):
- Background: `#0a0a0a`
- Surface: `#141414`
- Accent: `#11ff55` (neon green)
- Border: `#2a2a2a`

**Effects**:
```css
/* Glassmorphism */
.glass-panel {
  background: rgba(20, 20, 20, 0.8);
  backdrop-filter: blur(12px);
  border-radius: 12px;
}

/* Neon Glow */
.neon-border {
  box-shadow: 0 0 10px rgba(17, 255, 85, 0.3);
  border: 1px solid rgba(17, 255, 85, 0.5);
}
```

### Responsive Design

**Breakpoints** (TailwindCSS defaults):
- `sm`: 640px
- `md`: 768px (where sidebar becomes visible)
- `lg`: 1024px
- `xl`: 1280px

**Mobile Considerations**:
- Sidebar is slide-out drawer on mobile
- Charts adapt to narrow viewports
- Touch-friendly tap targets (min 44x44px)

---

## Testing Strategy

### Current State
- **Unit Tests**: Not yet implemented
- **E2E Tests**: Manual testing via deployed instance
- **Type Safety**: Enforced via `npm run typecheck`

### Future Testing Needs
- API route integration tests
- Curve interpolation algorithm tests
- Raspberry Pi communication mocks
- Sensor data generation utilities

### Manual Testing Checklist

**Critical Paths**:
1. ✅ Login with demo credentials
2. ✅ Navigate all dashboard pages
3. ✅ Edit lighting curves (add/remove/save)
4. ✅ Trigger All On/All Off override
5. ✅ View sensor charts with different time ranges
6. ✅ Switch language (de ↔ en)
7. ✅ Mobile responsive (sidebar menu)

---

## Deployment

### Production Environment

**Hosting**: Custom VPS
**URL**: http://growpi.nm-forum.de
**Database**: Supabase (managed PostgreSQL)

**Build Process**:
```bash
cd frontend
npm run build    # Creates .next/ directory
npm start        # Runs production server
```

**Environment Variables Required**:
- `DATABASE_URL` - Supabase connection string
- `JWT_SECRET` - Minimum 32 characters
- `NEXT_PUBLIC_APP_URL` - Frontend URL
- `SUPABASE_URL`, `SUPABASE_ANON_KEY` - Supabase credentials

### Raspberry Pi Deployment (Future)

**Installation**:
```bash
# On Raspberry Pi
ssh admin@192.168.0.86
cd /opt/grow-pi
sudo ./install.sh
sudo systemctl start grow-pi
```

**Configuration**:
- Edit `/opt/grow-pi/config/config.yaml`
- Set API key from web dashboard
- Configure GPIO pins for lamps
- Set RS485 port for sensors

---

## Common Tasks

### Adding a New API Endpoint

1. Create route file: `frontend/app/api/your-route/route.ts`
2. Implement HTTP methods (GET, POST, PUT, DELETE):
```typescript
import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  // Validate authentication
  // Query database
  // Return JSON response
  return NextResponse.json({ data })
}
```
3. Add TypeScript interface for response
4. Update frontend to consume endpoint
5. Test with `curl` or Postman

### Adding a New Sensor Type

1. Add enum value in Supabase migration
2. Update TypeScript types
3. Add translation keys (`messages/{de,en}.json`)
4. Create chart component in sensors page
5. Update Raspberry Pi controller to read sensor

### Modifying Database Schema

**⚠️ CRITICAL**: Schema is in Supabase, not Prisma-managed

1. Create new migration: `supabase/migrations/YYYYMMDDHHMMSS_description.sql`
2. Write SQL DDL (CREATE TABLE, ALTER TABLE, etc.)
3. Add RLS policies for new tables
4. Apply migration via Supabase dashboard or CLI
5. Update Prisma schema if using Prisma client
6. Regenerate types: `npm run db:push`

---

## Troubleshooting

### "Failed to fetch" errors in browser

**Cause**: API route not running or CORS issue

**Fix**:
```bash
# Ensure dev server is running
cd frontend && npm run dev

# Check API route exists
ls app/api/your-route/route.ts
```

### TypeScript errors in production build

**Cause**: Strict type checking catches issues

**Fix**:
```bash
# Run type checker locally
npm run typecheck

# Common issues:
# - Missing null checks: use optional chaining `data?.field`
# - Untyped fetch responses: add `interface` definitions
# - Implicit any: explicitly type function parameters
```

### Raspberry Pi not connecting

**Cause**: Network issue or incorrect API key

**Debug Steps**:
1. Check Pi is online: `ping 192.168.0.86`
2. SSH to Pi: `ssh admin@192.168.0.86`
3. Check logs: `sudo journalctl -u grow-pi -f`
4. Verify API key in `/opt/grow-pi/config/config.yaml`
5. Test API manually: `curl -H "X-API-Key: KEY" https://growpi.nm-forum.de/api/pi/commands`

### Lighting curves not updating on Pi

**Cause**: Pi not polling or curve format invalid

**Fix**:
1. Check Pi status in dashboard (online indicator)
2. Verify curve format in database (JSON array)
3. Check Pi logs for interpolation errors
4. Manually trigger override to force update

---

## Important Notes

### Hardware Integration Status

**Current**: Frontend fully functional with demo mode
**Next Phase**: Raspberry Pi controller development
**Blocked By**: Physical hardware delivery

**When Ready**:
1. Implement Python controller (see `docs/SPEC_RASPBERRY_PI.md`)
2. Test GPIO PWM output with LEDs
3. Connect RS485 sensors
4. Deploy controller as systemd service
5. Integrate with production API

### Performance Considerations

**Database**:
- Sensor readings table grows quickly (1 reading/minute = 43k/month)
- Consider data retention policy (archive old data)
- Indexes on `(sensor_id, created_at)` critical for chart queries

**Frontend**:
- Code splitting via Next.js App Router
- Lazy load chart components
- Optimize image assets (use WebP)

### Security Hardening (Production)

**TODO Before Public Launch**:
- [ ] Enable HTTPS (Let's Encrypt)
- [ ] Rate limiting on API routes
- [ ] CSRF token validation
- [ ] SSH key-based auth (disable password)
- [ ] Firewall rules (only port 443 open)
- [ ] Regular security updates
- [ ] Database backups (daily)

---

## Resources

**Documentation**:
- [Next.js App Router](https://nextjs.org/docs/app)
- [Supabase Docs](https://supabase.com/docs)
- [shadcn/ui](https://ui.shadcn.com/)
- [TailwindCSS](https://tailwindcss.com/)

**Internal Specs**:
- `docs/SPEC_FRONTEND.md` - Complete frontend specification
- `docs/SPEC_RASPBERRY_PI.md` - Hardware controller spec
- `docs/ARCHITECTURE.md` - System overview

**Support**:
- Developer: Dennis Westermann (d.westermann@ol-mg.de)
- Project Status: See `CHANGELOG.md`

---

**Last Updated**: 2025-12-04
**Schema Version**: 20251203153352
**Next.js Version**: 13.5.1
