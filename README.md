# SkyPi
## Particulate and light level monitoring with the Raspberry Pi

## Details
A total of three sensors on two hardware components are used to measure:
- Particulates (pm1.0, pm2.5,pm10) - PMS5003
- Humidity, temperature, air pressure - BME280
- Light levels - SQM-LU

Air sensors are all attached to a custom-built "bonnet" for the Raspberry Pi purpose-built for Motus, using the pin headers for connection plus a daughter board for with 

Light level sensor is a USB device made by UniHedron used to detect light pollution.

## Installation
With internet connection, run: `curl -sSL https://raw.githubusercontent.com/sensorgnome-org/enviroPi/main/install.sh | sudo bash`


---

## Next steps

- Test miniUART (ttyS0) with PMS5003
  - Switch to pins 32/33 or something
  - Test with GPS hat plugged in
- Switch BMP/BME280 pin from 4 to 27
- Test with Cell Hat
- Add reporting to SG web interface


---

## Manual install

## Requirements

### Python virtual environment
Latest RPi OS locks down the Python environment, preventing you from installing packages into the system interpreter using Pip. For this reason, you need to use a virtual environment.
- Run this code:
    ```
    sudo apt install python3-venv
    python3 -m venv env
    source env/bin/activate
    ```
- Install required packages from `requirements.txt`
    ```
    pip install -r requirements.txt
    ```

### Modifying services
```
sudo mv /home/enpi/enpi-*.yml /etc/shiftwrap/services/
sudo mv /home/enpi/*.rules /etc/udev/rules.d/
sudo mv /home/enpi/*.py /opt/enpi/
sudo mv /home/enpi/env/ /opt/enpi/env/
sudo mv /home/enpi/update.sh /opt/enpi/
sudo mv /home/enpi/enpi-*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable enpi-air
sudo systemctl start enpi-air 
```
- See if modifications worked by checking the status: `sudo systemctl status enpi-air`
```
sudo systemctl daemon-reload
sudo systemctl restart enpi-air
sudo systemctl status enpi-air

journalctl -u enpi -n 50 --no-pager
```
- Make log folder if it doesn't exist
```
sudo mkdir -p /var/log/enpi
sudo chown ampi:ampi /var/log/enpi
sudo chmod 755 /var/log/enpi
```
- update udev rules
```
sudo mv /home/enpi/*.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```
### PMS5003
Uses UART interface which is disabled by default. Steps to make it work:
- Edit `/boot/firmware/config.txt` and add line `enable_uart=1`
- Enter `raspi-config` and select `Interface Options --> Serial Port` and answer the questions:
  - Login shell over serial --> NO
  - Enable serial hardware --> YES
- Reboot

- Notes: might try to reconfigure uart to use miniuart (ttyS0) so that it's compatible with GPS HAT
  - /boot/config.txt -> dtoverlay=uart1,txd1_pin=32,rxd1_pin=33

### BME280
- Enter `raspi-config` and select `Interface Options --> I2C --> Enable`
- Reboot

### SQM-LU
- 

---
## TESTING
sudo env $(grep -v '^\s*#' /opt/sensorgnome/enpi/secrets.env | grep -v '^\s*$' | xargs) /opt/sensorgnome/enpi/env/bin/python3 /opt/sensorgnome/enpi/uploader.py