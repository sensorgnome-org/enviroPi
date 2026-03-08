#!/usr/bin/env bash
set -e

ENPI_DIR="/opt/sensorgnome/enpi"
LOG_DIR="/var/log/enpi"
DATA_DIR="/data/enpi"
SERVICE_USER="gnome"

echo "=== enviroPi Installer ==="

# 1. Ensure required packages
echo "[1/7] Installing system dependencies..."
# sudo apt update || true
sudo apt install -y python3-full python3-venv git i2c-tools pigpio

# 2. Create service user if missing
echo "[2/7] Ensuring user '$SERVICE_USER' exists..."
if ! id "$SERVICE_USER" >/dev/null 2>&1; then
    sudo useradd -m -s /bin/bash "$SERVICE_USER"
fi

# Add required groups
sudo usermod -aG gpio,i2c,dialout "$SERVICE_USER"

# 3. Install code into /opt/enpi
echo "[3/7] Installing code into $ENPI_DIR..."
sudo mkdir -p "$ENPI_DIR"
sudo rsync -av --delete ./ "$ENPI_DIR"/
sudo chown -R "$SERVICE_USER":"$SERVICE_USER" "$ENPI_DIR"

# 4. Create data + log directories
echo "[4/7] Creating data and log directories..."
sudo mkdir -p "$DATA_DIR"
sudo mkdir -p "$LOG_DIR"
sudo chown -R "$SERVICE_USER":"$SERVICE_USER" "$LOG_DIR"


# 5. Python virtual environment
echo "[5/7] Setting up Python virtual environment..."
sudo -u "$SERVICE_USER" bash <<EOF
cd "$ENPI_DIR"
python3 -m venv env
source env/bin/activate
pip install --upgrade pip
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi
EOF

# 6. Pigpio service
echo "[6/7] Setting up services..."
sudo mv "$ENPI_DIR/systemd/*" /etc/systemd/system

sudo tee /etc/systemd/system/pigpiod.service > /dev/null <<EOF
[Unit]
Description=Pigpio Daemon
After=network.target

[Service]
Type=forking
ExecStart=/usr/bin/pigpiod
ExecStop=/bin/systemctl kill pigpiod

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable enpi-uploader.timer
sudo systemctl enable pigpiod
sudo systemctl start enpi-uploader.timer
sudo systemctl start pigpiod

echo "[6/7] Installing udev rules..."
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
echo "Services: pigpio"