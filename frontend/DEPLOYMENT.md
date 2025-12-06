# 🚀 Deployment Guide - Grow-Pi

Comprehensive guide for deploying Grow-Pi to a production VPS.

## 📋 Prerequisites

### Server Requirements
- Ubuntu 24.04 LTS (or similar Linux distribution)
- Node.js 20+ installed
- PostgreSQL 16+ installed
- PM2 installed globally (`npm install -g pm2`)
- NGINX installed and configured
- Minimum 1GB RAM
- SSH access with root or sudo privileges

### Local Requirements
- Git
- Node.js 20+
- SSH client (sshpass recommended for automated deployment)

## 🎯 Quick Deployment

### Automated Deployment Script

The easiest way to deploy is using the included script:

```bash
cd /path/to/growpi/frontend
./deploy.sh
```

Enter the VPS password when prompted. The script will:
1. ✅ Create deployment archive
2. ✅ Upload to VPS
3. ✅ Extract files
4. ✅ Install dependencies
5. ✅ Build application
6. ✅ Restart PM2 process

## 📝 Manual Deployment Steps

### 1. Prepare VPS Environment

#### Install Node.js
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
node --version  # Should be 20+
```

#### Install PostgreSQL
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### Install PM2
```bash
sudo npm install -g pm2
pm2 startup  # Follow the instructions
```

#### Install NGINX
```bash
sudo apt-get install nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### 2. Setup Database

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE growpi;
CREATE USER growpi_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE growpi TO growpi_user;

# Configure remote access (if needed)
sudo nano /etc/postgresql/16/main/pg_hba.conf
# Add: host all all 0.0.0.0/0 scram-sha-256

sudo nano /etc/postgresql/16/main/postgresql.conf
# Set: listen_addresses = '*'

sudo systemctl restart postgresql
```

### 3. Prepare Application Directory

```bash
# Create directory
sudo mkdir -p /var/www/growpi
sudo chown $USER:$USER /var/www/growpi
cd /var/www/growpi
```

### 4. Deploy Application Files

#### Option A: Using Git (Recommended)

```bash
cd /var/www/growpi
git clone https://github.com/cubetribe/growpi.git .
npm install --production
```

#### Option B: Using SCP

```bash
# On local machine
cd /path/to/growpi/frontend
tar czf /tmp/growpi-deploy.tar.gz \
  --exclude='node_modules' \
  --exclude='.git' \
  --exclude='.next' \
  .

scp /tmp/growpi-deploy.tar.gz root@your-vps-ip:/tmp/

# On VPS
cd /var/www/growpi
tar xzf /tmp/growpi-deploy.tar.gz
npm install --production
```

### 5. Configure Environment

```bash
cd /var/www/growpi
nano .env
```

Add the following:
```env
# Database
DATABASE_URL="postgresql://growpi_user:your_secure_password@localhost:5432/growpi?schema=public"

# Authentication
JWT_SECRET="generate-a-secure-random-string-here"
SESSION_COOKIE_NAME="grow-pi-session"

# Application
NEXT_PUBLIC_APP_URL="https://growpi.your-domain.com"
NODE_ENV="production"
DEMO_MODE_DEFAULT="true"
```

**Important**: Generate a secure JWT secret:
```bash
openssl rand -base64 32
```

### 6. Initialize Database

```bash
cd /var/www/growpi

# Push schema to database
npm run db:push

# Optional: Seed with demo data
npm run seed
```

### 7. Build Application

```bash
cd /var/www/growpi
npm run build
```

### 8. Setup PM2

Create PM2 ecosystem file:
```bash
nano ecosystem.config.js
```

Add:
```javascript
module.exports = {
  apps: [{
    name: "growpi",
    script: "npm",
    args: "start",
    cwd: "/var/www/growpi",
    env: {
      NODE_ENV: "production",
      PORT: 3001
    },
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    error_file: '/var/www/growpi/logs/error.log',
    out_file: '/var/www/growpi/logs/output.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
  }]
}
```

Start PM2:
```bash
mkdir -p /var/www/growpi/logs
pm2 start ecosystem.config.js
pm2 save
```

### 9. Configure NGINX

```bash
sudo nano /etc/nginx/sites-available/growpi
```

Add:
```nginx
server {
    listen 80;
    server_name growpi.your-domain.com;

    location / {
        proxy_pass http://localhost:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Optional: Add SSL configuration with certbot
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/growpi /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 10. Setup SSL (Optional but Recommended)

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d growpi.your-domain.com
```

## 🔄 Updates & Redeployment

### Quick Update

```bash
cd /var/www/growpi
git pull origin main
npm install --production
npm run build
pm2 restart growpi
```

### Or use deploy script

```bash
./deploy.sh
```

## 🐛 Troubleshooting

### Check PM2 Status

```bash
pm2 status
pm2 logs growpi --lines 50
pm2 monit
```

### Check NGINX Status

```bash
sudo systemctl status nginx
sudo nginx -t
sudo tail -f /var/log/nginx/error.log
```

### Database Connection Issues

```bash
# Test database connection
psql -U growpi_user -d growpi -h localhost

# Check PostgreSQL status
sudo systemctl status postgresql

# View PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-16-main.log
```

### Port Already in Use

```bash
# Find process using port 3001
lsof -i :3001

# Kill process if needed
kill -9 <PID>

# Or change port in ecosystem.config.js
```

### Build Failures

```bash
# Clear Next.js cache
rm -rf .next

# Clear node_modules and reinstall
rm -rf node_modules
npm install --production

# Rebuild
npm run build
```

## 🔐 Security Checklist

- [ ] Change default admin password
- [ ] Generate secure JWT_SECRET
- [ ] Configure firewall (ufw)
- [ ] Setup SSL certificate
- [ ] Configure database backups
- [ ] Setup log rotation
- [ ] Restrict database access
- [ ] Use environment variables for secrets
- [ ] Enable HTTPS only (redirect HTTP)
- [ ] Configure rate limiting

### Basic Firewall Setup

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

## 📊 Monitoring

### PM2 Monitoring

```bash
# Real-time monitoring
pm2 monit

# Detailed info
pm2 info growpi

# View logs
pm2 logs growpi
```

### System Resources

```bash
# Check disk space
df -h

# Check memory
free -h

# Check CPU
htop
```

## 🔄 Backup & Restore

### Database Backup

```bash
# Create backup
pg_dump -U growpi_user growpi > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
psql -U growpi_user growpi < backup_20231203_120000.sql
```

### Application Backup

```bash
# Backup entire application
tar czf growpi_backup_$(date +%Y%m%d_%H%M%S).tar.gz /var/www/growpi
```

## 📞 Support

For deployment issues:
1. Check PM2 logs: `pm2 logs growpi`
2. Check NGINX logs: `sudo tail -f /var/log/nginx/error.log`
3. Check database connection in .env
4. Verify all environment variables are set
5. Ensure port 3001 is not in use

## 🎉 Post-Deployment

After successful deployment:
1. ✅ Test login functionality
2. ✅ Verify dashboard loads
3. ✅ Test lighting controls
4. ✅ Check sensor data display
5. ✅ Test mobile responsiveness
6. ✅ Verify theme toggle
7. ✅ Test settings save

---

**Production URL**: http://growpi.nm-forum.de
**Status**: ✅ Deployed and Running
**PM2 Process**: growpi
**Port**: 3001 (proxied via NGINX on port 80)
