# 🌱 Grow-Pi - Professional Greenhouse Control System

[![Next.js](https://img.shields.io/badge/Next.js-13.5.1-black)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2.2-blue)](https://www.typescriptlang.org/)
[![Prisma](https://img.shields.io/badge/Prisma-5.20.0-2D3748)](https://www.prisma.io/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A professional web-based control system for Raspberry Pi greenhouse automation. Monitor sensors, control lighting, and manage your growing environment from anywhere.

## 🚀 Features

### 📊 Real-time Dashboard
- Live sensor monitoring (Temperature, Humidity, Soil Moisture, EC, NPK)
- Visual status indicators
- Configurable refresh intervals
- Demo mode for testing

### 💡 Lighting Control
- **Advanced Curve Editor** - Create custom lighting schedules
- Time-based intensity curves with visual feedback
- Add/Remove curve points dynamically
- All On/All Off quick controls
- Reset functionality to restore defaults

### 📈 Sensor Data Analytics
- Historical data visualization
- Multiple time ranges (10m, 1h, 24h, 7d, 30d)
- Interactive charts with Recharts
- NPK soil nutrient tracking

### ⚙️ Settings Management
- Language support (German/English)
- Dark/Light theme toggle
- Demo mode configuration
- Sensor reading intervals (5-3600 seconds)
- Input validation with user feedback

### 📱 Mobile Responsive
- Hamburger menu for mobile devices
- Responsive grid layouts
- Touch-friendly controls
- Optimized for all screen sizes

## 🛠️ Tech Stack

### Frontend
- **Framework**: Next.js 13.5.1 (App Router)
- **Language**: TypeScript 5.2.2
- **Styling**: Tailwind CSS 3.3.3
- **UI Components**: Radix UI + shadcn/ui
- **Charts**: Recharts 2.12.7
- **Icons**: Lucide React
- **Themes**: next-themes
- **Notifications**: Sonner (Toast)

### Backend
- **Database**: PostgreSQL 16
- **ORM**: Prisma 5.20.0
- **Authentication**: JWT with jose
- **Password Hashing**: bcryptjs
- **API**: Next.js API Routes (Server Actions)

### Deployment
- **Server**: Ubuntu 24.04 VPS
- **Process Manager**: PM2
- **Web Server**: NGINX (Reverse Proxy)
- **Domain**: growpi.nm-forum.de

## 📦 Installation

### Prerequisites
- Node.js 20+
- PostgreSQL 16
- npm or yarn

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```

   Edit `.env`:
   ```env
   DATABASE_URL="postgresql://user:password@localhost:5432/growpi"
   JWT_SECRET="your-secret-key-change-in-production"
   NEXT_PUBLIC_APP_URL="http://localhost:3000"
   ```

4. **Setup database**
   ```bash
   npm run db:push      # Push schema to database
   npm run seed         # Seed with demo data (optional)
   ```

5. **Run development server**
   ```bash
   npm run dev
   ```

   Open [http://localhost:3000](http://localhost:3000)

6. **Login credentials**
   - Username: `admin`
   - Password: `Mi83xer#` (or check seed script)

## 🏗️ Build & Deploy

### Build for Production

```bash
npm run build
npm start
```

### Deploy to VPS

Use the included deployment script:

```bash
./deploy.sh
```

This will:
1. Create a deployment archive
2. Upload to VPS via SCP
3. Extract files
4. Install dependencies
5. Build the application
6. Restart PM2 process

### Manual Deployment

```bash
# 1. Create archive
tar czf /tmp/growpi-deploy.tar.gz \
  --exclude='node_modules' \
  --exclude='.git' \
  --exclude='.next' \
  .

# 2. Upload to VPS
scp /tmp/growpi-deploy.tar.gz root@your-vps-ip:/tmp/

# 3. Deploy on VPS
ssh root@your-vps-ip
cd /var/www/growpi
tar xzf /tmp/growpi-deploy.tar.gz
npm install --production
npm run build
pm2 restart growpi
```

## 🗄️ Database Schema

### Core Models

- **User** - Authentication and user management
- **Zone** - Growing zones/greenhouses
- **LampChannel** - Lighting control with JSON curves
- **Sensor** - Sensor definitions
- **SensorReading** - Time-series sensor data
- **Settings** - User preferences
- **AlertConfig** - Alert thresholds
- **PiConnection** - Raspberry Pi connection status

See `prisma/schema.prisma` for complete schema.

## 📜 Scripts

```bash
npm run dev          # Start development server
npm run build        # Production build
npm start            # Start production server
npm run lint         # ESLint check
npm run typecheck    # TypeScript check
npm run seed         # Seed database with demo data
npm run db:push      # Push Prisma schema to database
npm run db:studio    # Open Prisma Studio
```

## 🎨 Project Structure

```
frontend/
├── app/                      # Next.js App Router
│   ├── (dashboard)/         # Protected routes
│   │   ├── dashboard/       # Main dashboard
│   │   ├── lighting/        # Lighting control
│   │   ├── sensors/         # Sensor analytics
│   │   └── settings/        # Settings page
│   ├── api/                 # API routes
│   │   ├── auth/           # Authentication
│   │   ├── dashboard/      # Dashboard data
│   │   ├── lighting/       # Lighting control
│   │   ├── readings/       # Sensor readings
│   │   └── settings/       # Settings CRUD
│   ├── login/              # Login page
│   └── layout.tsx          # Root layout
├── components/
│   ├── dashboard/          # Dashboard components
│   ├── layout/             # Layout components (Sidebar)
│   └── ui/                 # shadcn/ui components
├── contexts/
│   └── LanguageContext.tsx # i18n context
├── lib/
│   ├── auth.ts            # JWT authentication
│   ├── i18n.ts            # Translations
│   └── prisma.ts          # Prisma client
├── prisma/
│   ├── schema.prisma      # Database schema
│   └── seed.ts            # Seed script
├── public/
│   └── favicon.svg        # Favicon
└── deploy.sh              # Deployment script
```

## 🌍 Environment Variables

### Required
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET` - Secret for JWT signing

### Optional
- `NEXT_PUBLIC_APP_URL` - Public app URL
- `NODE_ENV` - Environment (development/production)
- `DEMO_MODE_DEFAULT` - Default demo mode (true/false)

## 🔐 Security

- JWT-based authentication with httpOnly cookies
- bcrypt password hashing (10 rounds)
- SQL injection prevention via Prisma ORM
- CSRF protection via SameSite cookies
- Input validation on all forms
- Type-safe API with TypeScript

## 🧪 Testing

Current build status: ✅ All checks passing
- TypeScript compilation: ✅ No errors
- Next.js build: ✅ Success
- Bundle size: 79.5 kB (First Load JS)

## 📊 Performance

- First Load JS: 79.5 kB (Excellent)
- Largest page: /sensors (197 kB including Recharts)
- Server-side rendering for authenticated routes
- Static generation for public pages

## 🌐 Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

### Code Style
- TypeScript strict mode
- ESLint configuration
- Prettier formatting
- Conventional commits

## 📝 License

MIT License - See LICENSE file for details

## 👥 Authors

- Dennis Westermann - Initial work

## 🙏 Acknowledgments

- Next.js team for the amazing framework
- shadcn for the beautiful UI components
- Vercel for excellent deployment platform

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review CHANGELOG.md for recent changes

## 🔄 Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

---

**Live Demo**: http://growpi.nm-forum.de

**Status**: ✅ Production Ready
