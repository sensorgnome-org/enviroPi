#!/usr/bin/env bash
set -e

HOME_DIR="/home/gnome"
ENPI_DIR="/opt/sensorgnome/enpi"
LOG_DIR="/var/log/enpi"
DATA_DIR="/data/enpi"
REPO_NAME="enviroPi"
SERVICE_USER="gnome"
SG_REPO_NAME="sensorgnome-control-enpi"


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

cd "$HOME_DIR"
git clone https://github.com/sensorgnome-org/"$REPO_NAME".git
cd "$REPO_NAME"


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
sudo mv "$ENPI_DIR/systemd/" /etc/systemd/system

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

#6. udev rules
echo "[6/7] Installing udev rules..."
# Copy rules from repo to system directory
sudo cp "$ENPI_DIR/udev/10-enpi.rules" /etc/udev/rules.d/
# Ensure correct permissions
sudo chmod 644 /etc/udev/rules.d/10-enpi.rules
# Reload and trigger
sudo udevadm control --reload-rules
sudo udevadm trigger


#7. Clone and install sg-control repo
echo "[7/7] Installing custom sg-control software"
cd "$HOME_DIR"
git clone "https://github.com/leberrigan/$SG_REPO_NAME.git"
cd "$SG_REPO_NAME"

sudo mv "acquisition.json" /etc/sensorgnome/
sudo mv "src/dashboard.js" /opt/sensorgnome/control/
sudo mv "src/enpi.js" /opt/sensorgnome/control/
sudo mv "src/fd-config.json" /opt/sensorgnome/control/
sudo mv "src/main.js" /opt/sensorgnome/control/
sudo mv "src/motus_up.js" /opt/sensorgnome/control/

sudo systemctl restart sg-control



echo "=== Installation complete ==="
echo "Logs: $LOG_DIR"
echo "Data: $DATA_DIR"
echo "Services: pigpio"