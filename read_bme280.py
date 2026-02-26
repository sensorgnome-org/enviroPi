import RPi.GPIO as GPIO
import time
import board
import busio
import logging
from adafruit_bme280 import basic as adafruit_bme280

exists = False

def init( select_pin = 4, set_verbose = False ):
    global PIN_bme280,verbose,bme280,exists

    if select_pin is not None:
        PIN_bme280 = select_pin

    verbose = set_verbose

    if verbose:
        print("[BME280] Initializing...")
        logging.info("[BME280] Initializing...")

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIN_bme280, GPIO.OUT)

    time.sleep(0.1)
    try:
        # Set up I2C bus for BME280
        i2c = busio.I2C(board.SCL, board.SDA)
        # Initialize BME280 sensor
        bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)  # Or 0x77
        exists = True

    except Exception as e:
        if verbose:
            print(f"[BME280] Initialization error: {e}")
            logging.error(f"[BME280] Initialization error: {e}")
        exists = False
        
    return exists

def on():
    GPIO.output(PIN_bme280, GPIO.LOW)

def off():
    GPIO.output(PIN_bme280, GPIO.HIGH)

def poll():
    return exists if exists else init(PIN_bme280, verbose)

def read():
    
    if exists:
        if verbose:
            print("[BME280] Reading...")
            logging.info("[BME280] Reading...")
        temp = bme280.temperature
        pressure = bme280.pressure
        humidity = bme280.humidity
        if verbose:
            print(f"[BME280] Temp: {temp:.2f} °C, Pressure: {pressure:.2f} hPa, Humidity: {humidity:.2f} %")
        return f"{temp:.2f}", f"{pressure:.2f}", f"{humidity:.2f}"
    else:
        return "NA", "NA", "NA"
