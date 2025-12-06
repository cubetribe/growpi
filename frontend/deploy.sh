#!/bin/bash
# GrowPi Deployment Script to VPS
# Run this script to deploy all changes to the production server

set -e

echo "🚀 GrowPi Deployment Script"
echo "============================"
echo ""

# Configuration
VPS_HOST="5.182.17.148"
VPS_USER="root"
VPS_PATH="/var/www/growpi"
LOCAL_DIR="."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1:${NC} Creating deployment package..."
tar czf /tmp/growpi-deploy.tar.gz \
  --exclude='node_modules' \
  --exclude='.git' \
  --exclude='.next' \
  --exclude='deploy.sh' \
  --exclude='growpi-update.tar.gz' \
  -C "$LOCAL_DIR" .

echo -e "${GREEN}✓${NC} Package created"
echo ""

echo -e "${YELLOW}Step 2:${NC} Uploading to VPS..."
scp /tmp/growpi-deploy.tar.gz ${VPS_USER}@${VPS_HOST}:/tmp/

echo -e "${GREEN}✓${NC} Upload complete"
echo ""

echo -e "${YELLOW}Step 3:${NC} Deploying on VPS..."
ssh ${VPS_USER}@${VPS_HOST} << 'ENDSSH'
set -e

echo "📦 Extracting files..."
cd /var/www/growpi
tar xzf /tmp/growpi-deploy.tar.gz
rm /tmp/growpi-deploy.tar.gz

echo "📚 Installing dependencies..."
npm install --production

echo "🏗️  Building application..."
npm run build

echo "🔄 Restarting PM2..."
pm2 restart growpi

echo "✅ Deployment complete!"
pm2 status
ENDSSH

echo ""
echo -e "${GREEN}✅ Deployment successful!${NC}"
echo ""
echo "🌐 Application running at: http://growpi.nm-forum.de"
echo ""
echo "📊 Check logs with: ssh ${VPS_USER}@${VPS_HOST} 'pm2 logs growpi'"
echo "📈 Check status with: ssh ${VPS_USER}@${VPS_HOST} 'pm2 status'"
echo ""
