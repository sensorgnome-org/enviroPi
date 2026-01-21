#!/usr/bin/env bash
set -e

REPO_URL="https://github.com/sensorgnome-org/enviroPi.git"
APP_DIR="/opt/enviroPi"
VENV_DIR="/opt/enviroPi_env"
SERVICE_NAME="enviroPi.service"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"

echo "=== enviroPi installer starting ==="

# Ensure basic tools
sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-pip i2c-tools
# Enable I2C and UART in /boot/config.txt
BOOT_CONFIG="/boot/config.txt"

if ! grep -q "^dtparam=i2c_arm=on" "$BOOT_CONFIG"; then
  echo "dtparam=i2c_arm=on" | sudo tee -a "$BOOT_CONFIG"
fi

if ! grep -q "^enable_uart=1" "$BOOT_CONFIG"; then
  echo "enable_uart=1" | sudo tee -a "$BOOT_CONFIG"
fi

# Disable serial console (free UART)
sudo systemctl disable serial-getty@ttyAMA0.service 2>/dev/null || true
sudo systemctl disable serial-getty@ttyS0.service 2>/dev/null || true

# Load I2C modules
echo "i2c-dev" | sudo tee -a /etc/modules >/dev/null || true

# Clone or update repo
if [ -d "$APP_DIR/.git" ]; then
  echo "Updating existing enviroPi repo..."
  sudo git -C "$APP_DIR" pull --ff-only
else
  echo "Cloning enviroPi repo..."
  sudo git clone "$REPO_URL" "$APP_DIR"
  sudo chmod +x /opt/enviroPi/update.sh
fi

sudo chown -R pi:pi "$APP_DIR" || true

# Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

# Install Python dependencies
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$APP_DIR/requirements.txt"
deactivate

# Install systemd service
sudo cp "$APP_DIR/systemd/enviroPi.service" "$SERVICE_FILE"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "=== enviroPi installation complete ==="
echo "Rebooting to apply UART/I2C changes..."
sudo reboot