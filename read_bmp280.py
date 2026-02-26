import RPi.GPIO as GPIO
import time
import board
import busio
import logging
import adafruit_bmp280

exists = False

def init( select_pin = 4, set_verbose = False ):
    global PIN_bmp280,verbose,bmp280,exists

    if select_pin is not None:
        PIN_bmp280 = select_pin

    verbose = set_verbose

    if verbose:
        print("[BMP280] Initializing...")
        logging.info("[BMP280] Initializing...")

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIN_bmp280, GPIO.OUT)

    time.sleep(0.1)

    try:
        # Set up I2C bus for BMP280
        i2c = busio.I2C(board.SCL, board.SDA)
        # Initialize BMP280 sensor
        bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=0x76)  # Or 0x77
        exists = True
    except Exception as e:
        if verbose:
            print(f"[BMP280] Initialization error: {e}")
            logging.error(f"[BMP280] Initialization error: {e}")
        exists = False

    return exists

def on():
    GPIO.output(PIN_bmp280, GPIO.LOW)

def off():
    GPIO.output(PIN_bmp280, GPIO.HIGH)

def poll():
    return exists if exists else init(PIN_bmp280, verbose)

def read():
    if exists:
        if verbose:
            print("[BMP280] Reading...")
            logging.info("[BMP280] Reading...")
        temp = bmp280.temperature
        pressure = bmp280.pressure
        if verbose:
            print(f"[BMP280] Temp: {temp:.2f} °C, Pressure: {pressure:.2f} hPa, Humidity: (not measured)")
        return f"{temp:.2f}", f"{pressure:.2f}", "NA"
    else:
        return "NA", "NA", "NA"
