"""

Usage:
    python3 test-sensors.py [-d] [--once]

Options:
    -d, --debug      Enable debug mode (shorter wait times)
    --once          Only take one sample and exit

Description:
    This script reads data from a BMP280 temperature and pressure sensor and a PMS5003 particulate matter sensor.

"""


import struct
import time
import board
import busio
import adafruit_bmp280
import RPi.GPIO as GPIO
import csv
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import argparse
import sys
import gzip
import read_bmp280 as bmp280
import read_bme280 as bme280
import read_pms5003 as pms5003
from datetime import date
from enpi import __version__
from enpi import __log_dir__
from enpi import __data_dir__



# Parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
parser.add_argument("-dir", help="Data storage directory (default = /data)", type=str, default=__data_dir__)
parser.add_argument("-v", "--verbose", action="store_true", help="Log a lot of messages", default = False)
parser.add_argument("-i","--interval", help="Sample interval in seconds (default is 300s, or 5 minutes)", type=int, default=300)
parser.add_argument("--once", action="store_true", help="Only take one sample and exit")
args = parser.parse_args()

# Air temp and pressure sensor
PIN_bmp280 = 4 # Requires 3v3
PIN_bme280 = 4 # Requires 3v3
# Particulate sensor
PIN_pms5003 = 17 # Requires 5v
# Seconds after waking from sleep before a measurement should be taken
wakeLatency = 3 if args.debug else 60
# Seconds between samples
sampleInterval = args.interval # default: 5 Minutes
        
sensors = {
    "bmp280": bmp280,
    "bme280": bme280,
    "pms5003": pms5003
}

today = date.today()

def init():

    setup_logging()

    # Make sure data dir exists
    os.makedirs(__data_dir__, exist_ok=True)

    print("[enpi-air] Starting enpi-air version " + __version__)
    logging.info("[enpi-air] Starting enpi-air version " + __version__)

    if args.debug:
        print("[enpi-air] ### Running in debug mode")
        logging.info("[enpi-air] ### Running in debug mode")
        
    if args.once:
        print("[enpi-air] ### Sampling only once")
        logging.info("[enpi-air] ### Sampling only once")

    
    if args.verbose:
        print("[enpi-air] Start logging.")
        logging.info("[enpi-air] Start logging.")

    try: 
        GPIO.setmode(GPIO.BCM)
        bmp280.init( PIN_bmp280, args.verbose )
        bme280.init( PIN_bme280, args.verbose )
        pms5003.init( PIN_pms5003, args.verbose )

    except Exception as e:
        print(f"[enpi-air] Something went wrong: {e}")
        logging.info(f"[enpi-air] Something went wrong: {e}")

    # Give PMS5003 time to stabilize
    #print("Waiting 60s for PMS5003 to stabilize...")
    #time.sleep(60)

def setup_logging():
    handler = TimedRotatingFileHandler(
        f"{__log_dir__}/enpi-air.log",
        when="midnight",
        interval=1,
        backupCount=14,   # keep 14 days of logs
        utc=False
    )
    formatter = logging.Formatter("(%(asctime)s) %(message)s")
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

def activate_sensors( on ):
    if on:
        bme280.on()
    else:
        bme280.off()
    time.sleep(0.5)

def poll_sensors():
    response = {}
    for sensor in sensors:
        response[sensor] = sensors[sensor].poll()
    return response

def read():

    results = {}

    for sensor in sensors:
        results[sensor] = sensors[sensor].read()

    return results

def stop():
    logging.info("[enpi-air] Exiting...")
    pms5003.stop()
    GPIO.cleanup()
    sys.exit()

def zip_and_remove(path):
    with open(path, "rb") as src, gzip.open(path + ".gz", "wb") as dst:
        dst.writelines(src)

    if args.verbose:
        print(f"[enpi-air] Zipped file {path}")
        logging.info(f"[enpi-air] Zipped file {path}")

    os.remove(path)
    return path + ".gz"

def get_filename(date = date.today()):
    formatted_date = date.strftime('%Y-%m-%d')
    return f"{args.dir}/air-quality_v{__version__}_{formatted_date}.csv"

def main():
    init()
    try:
        while True:
            global today
            if today != date.today():
                zip_and_remove(get_filename(today))
                today = date.today()

            filename = get_filename(today)

            with open(filename, mode="a", newline='') as file:
                # Poll the sensors and initialize them if they aren't already
                existing_sensors = poll_sensors()

                
                if args.verbose:
                    logging.info("[enpi-air] Opened CSV for writing...")
                writer = csv.writer(file)

                # Write header if file doesn't exist or is empty
                if not os.path.isfile(filename) or os.path.getsize(filename) == 0:
                    writer.writerow(["ts","temp","pressure","humidity","pm1","pm2.5","pm10", "pc0.3", "pc0.5", "pc1", "pc2.5", "pc5", "pc10"])
                
                if args.verbose:
                    print("[enpi-air] Turning sensors on.")
                    logging.info("[enpi-air] Turning sensors on.")
                # Turn on Sensors
                activate_sensors( True )
                
                if args.verbose:
                    print(f"[enpi-air] Sleeping for {wakeLatency} seconds to get an accurate reading")
                    logging.info(f"[enpi-air] Sleeping for {wakeLatency} seconds to get an accurate reading")
                
                # Sleep for a bit before measuring
                for i in range(wakeLatency):
                    time.sleep( 1 )
                    if args.verbose:
                        print( "[enpi-air] ", wakeLatency - i - 1, "s remaining..." )
                    
                ts = time.time() # Time received
                
                # Read sensor data
                sensor_data = read()

                if existing_sensors["bme280"]:
                    sensor_data = sensor_data["bme280"] + sensor_data["pms5003"]
                else:
                    sensor_data = sensor_data["bmp280"] + sensor_data["pms5003"]
                    if args.verbose:
                        print("[enpi-air] Using BMP280 data instead of BME280")
                        logging.info("[enpi-air] Using BMP280 data instead of BME280")
                
                if args.verbose:
                    print("[enpi-air] Writing to CSV")
                    logging.info("[enpi-air] Writing to CSV")

                writer.writerow([ts] + list(sensor_data))
                
                if args.verbose:
                    print("[enpi-air] Turning sensors off.")
                    logging.info("[enpi-air] Turning sensors off.")
                # Turn off sensors
                activate_sensors( False )
                
                if args.once:
                    stop()
                    
                if args.verbose:
                    print(f"[enpi-air] Sleeping for {sampleInterval} seconds before sampling again")
                    logging.info(f"[enpi-air] Sleeping for {sampleInterval} seconds before sampling again")
                    
                # Sleep until next measurement
                time.sleep( sampleInterval )
                
        
    except KeyboardInterrupt:
        stop()
        

if __name__ == "__main__":
    main()