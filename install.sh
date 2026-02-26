#!/usr/bin/env bash
set -e

ENPI_DIR="/opt/enpi"
LOG_DIR="/var/log/enpi"
DATA_DIR="/data/enpi"
SERVICE_USER="ampi"

echo "=== enviroPi Installer ==="

# 1. Ensure required packages
echo "[1/8] Installing system dependencies..."
sudo apt update
sudo apt install -y python3-full python3-venv git i2c-tools

# 2. Create service user if missing
echo "[2/8] Ensuring user '$SERVICE_USER' exists..."
if ! id "$SERVICE_USER" >/dev/null 2>&1; then
    sudo useradd -m -s /bin/bash "$SERVICE_USER"
fi

# Add required groups
sudo usermod -aG gpio,i2c,dialout "$SERVICE_USER"

# 3. Install code into /opt/enpi
echo "[3/8] Installing code into $ENPI_DIR..."
sudo mkdir -p "$ENPI_DIR"
sudo rsync -av --delete ./ "$ENPI_DIR"/
sudo chown -R "$SERVICE_USER":"$SERVICE_USER" "$ENPI_DIR"

# 4. Create data + log directories
echo "[4/8] Creating data and log directories..."
sudo mkdir -p "$DATA_DIR"
sudo mkdir -p "$LOG_DIR"
sudo chown -R "$SERVICE_USER":"$SERVICE_USER" "$DATA_DIR"
sudo chown -R "$SERVICE_USER":"$SERVICE_USER" "$LOG_DIR"

# 5. Python virtual environment
echo "[5/8] Setting up Python virtual environment..."
sudo -u "$SERVICE_USER" bash <<EOF
cd "$ENPI_DIR"
python3 -m venv env
source env/bin/activate
pip install --upgrade pip
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi
EOF

# 6. Install systemd services
echo "[6/8] Installing systemd services..."
sudo cp "$ENPI_DIR/systemd/enpi-air.service" /etc/systemd/system/
sudo cp "$ENPI_DIR/systemd/enpi-light@.service" /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable enpi-air.service
sudo systemctl enable enpi-light@default.service

# 7. Start services
echo "[7/8] Starting services..."
sudo systemctl restart enpi-air.service


echo "[8/8] Installing udev rules..."
# Copy rules from repo to system directory
sudo cp "$ENPI_DIR/udev/99-enpi.rules" /etc/udev/rules.d/
# Ensure correct permissions
sudo chmod 644 /etc/udev/rules.d/99-enpi.rules
# Reload and trigger
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "=== Installation complete ==="
echo "Logs: $LOG_DIR"
echo "Data: $DATA_DIR"
echo "Services: enpi-air, enpi-light@default"