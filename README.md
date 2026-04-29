# ENPI
## Particulate and light level monitoring with the Raspberry Pi

## Details
A total of three sensors on two hardware components are used to measure:
- Particulates (pm1.0, pm2.5,pm10) - PMS5003
- Humidity, temperature, air pressure - BME280
- Light levels - SQM-LU

Air sensors are all attached to a custom-built "bonnet" for the Raspberry Pi purpose-built for Motus, using the pin headers for connection plus a daughter board for with 

Light level sensor is a USB device made by UniHedron used to detect light pollution.

## Installation
With internet connection, run: 
```
curl -sSL https://raw.githubusercontent.com/sensorgnome-org/enpi/main/install.sh | sudo bash
```


## SensorGnome integration
Switch to [sensorgnome branch](https://github.com/sensorgnome-org/enpi/tree/sensorgnome) for more details.


