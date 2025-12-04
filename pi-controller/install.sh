#!/bin/bash
# =============================================================================
# GrowPi Controller - Installation Script
# =============================================================================
# Dieses Script installiert den GrowPi Controller auf dem Raspberry Pi.
#
# Voraussetzungen:
#   - Raspberry Pi OS (Debian-basiert)
#   - Python 3.11+
#   - Internetverbindung für pip packages
#
# Usage:
#   chmod +x install.sh
#   ./install.sh
# =============================================================================

set -e  # Exit on error

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "=============================================="
echo "   GrowPi Controller - Installation"
echo "=============================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Bitte NICHT als root ausführen!${NC}"
    echo "Das Script fragt bei Bedarf nach sudo."
    exit 1
fi

# Detect script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INSTALL_DIR="/opt/grow-pi"

echo -e "${YELLOW}Script-Verzeichnis: ${SCRIPT_DIR}${NC}"
echo -e "${YELLOW}Installations-Verzeichnis: ${INSTALL_DIR}${NC}"
echo ""

# Step 1: Install system packages
echo -e "${GREEN}[1/6] Installiere System-Pakete...${NC}"
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv python3-pigpio pigpio-tools

# Step 2: Enable and start pigpiod
echo ""
echo -e "${GREEN}[2/6] Aktiviere pigpio Daemon...${NC}"

# Create pigpiod service if it doesn't exist (needed on Debian Trixie)
if [ ! -f /etc/systemd/system/pigpiod.service ]; then
    echo "  Erstelle pigpiod.service..."
    sudo tee /etc/systemd/system/pigpiod.service > /dev/null << 'EOF'
[Unit]
Description=Pigpio Daemon
After=network.target

[Service]
Type=forking
ExecStartPre=/bin/rm -f /var/run/pigpio.pid
ExecStart=/usr/local/bin/pigpiod
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
fi

sudo systemctl enable pigpiod
sudo systemctl start pigpiod || {
    echo "  pigpiod start fehlgeschlagen, versuche manuell..."
    sudo rm -f /var/run/pigpio.pid
    sudo pigpiod
    sleep 2
}
echo "  pigpiod Status: $(pgrep pigpiod > /dev/null && echo 'running' || echo 'not running')"

# Step 3: Create installation directory
echo ""
echo -e "${GREEN}[3/6] Erstelle Installations-Verzeichnis...${NC}"
sudo mkdir -p ${INSTALL_DIR}
sudo chown $(whoami):$(whoami) ${INSTALL_DIR}

# Step 4: Copy files
echo ""
echo -e "${GREEN}[4/6] Kopiere Dateien...${NC}"
cp -r ${SCRIPT_DIR}/grow_pi ${INSTALL_DIR}/
cp -r ${SCRIPT_DIR}/config ${INSTALL_DIR}/
cp ${SCRIPT_DIR}/requirements.txt ${INSTALL_DIR}/

# Create logs directory
mkdir -p ${INSTALL_DIR}/logs

echo "  Dateien kopiert nach ${INSTALL_DIR}"

# Step 5: Create virtual environment and install dependencies
echo ""
echo -e "${GREEN}[5/6] Erstelle Virtual Environment...${NC}"
cd ${INSTALL_DIR}

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  Virtual Environment erstellt"
else
    echo "  Virtual Environment existiert bereits"
fi

# Activate and install
source venv/bin/activate
pip install --upgrade pip
pip install PyYAML pigpio
deactivate

echo "  Dependencies installiert"

# Step 6: Install systemd service
echo ""
echo -e "${GREEN}[6/6] Installiere systemd Service...${NC}"
sudo cp ${SCRIPT_DIR}/systemd/grow-pi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable grow-pi

echo ""
echo "=============================================="
echo -e "${GREEN}   Installation abgeschlossen!${NC}"
echo "=============================================="
echo ""
echo "Nächste Schritte:"
echo ""
echo "1. Konfiguration anpassen:"
echo "   nano ${INSTALL_DIR}/config/config.yaml"
echo ""
echo "2. Service starten:"
echo "   sudo systemctl start grow-pi"
echo ""
echo "3. Status prüfen:"
echo "   sudo systemctl status grow-pi"
echo ""
echo "4. Logs anzeigen:"
echo "   sudo journalctl -u grow-pi -f"
echo ""
echo "5. Test-Modus (ohne dauerhaft zu laufen):"
echo "   cd ${INSTALL_DIR} && source venv/bin/activate"
echo "   python -m grow_pi.main --test"
echo ""
