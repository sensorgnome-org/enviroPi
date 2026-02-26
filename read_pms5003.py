import serial
import time
import struct
import logging
import RPi.GPIO as GPIO

exists = False

def init( PIN_pms5003 = 17, set_verbose = False ):
    global verbose
    global ser
    verbose = set_verbose

    if verbose:
        print("[PMS5003] Initializing...")
        logging.info("[PMS5003] Initializing...")

    GPIO.setup(PIN_pms5003, GPIO.OUT)

    # Always have 5v on
    GPIO.output(PIN_pms5003, GPIO.LOW)

    time.sleep(0.1)

    # Connect to UART for PMS5003 (default UART on GPIO14/15 is /dev/serial0)
    ser = serial.Serial('/dev/serial0', baudrate=9600, timeout=5)

def on(pin):
    GPIO.output(pin, GPIO.LOW)

def off(pin):
    GPIO.output(pin, GPIO.HIGH)

def stop():
    ser.close()

def poll():
    global exists
    if not exists:
        exists = read( True ) is not None
    return exists

def read( poll = False ):
    global exists
    ser.reset_input_buffer()
    time.sleep(0.1)

    if verbose:
        print("[PMS5003] Reading...")
        logging.info("[PMS5003] Reading...")
    
    for _ in range(60):
        try:
            if ser.read(1) != b'\x42':
                continue
            if ser.read(1) != b'\x4d':
                continue
            
            # Get payload size
            length_bytes = ser.read(2)
            length = struct.unpack(">H", length_bytes)[0] # Should be 28

            if verbose:
                print(f"[PMS5003] Payload length is {length}")
            payload = ser.read(length)  # 28 bytes total including header
            
            if len(payload) != length:
                if verbose:
                    print(f"[PMS5003] Incomplete payload: expected {length} bytes, got {len(payload)}")
                logging.error(f"[PMS5003] Incomplete payload: expected {length} bytes, got {len(payload)}")
                continue

            exists = True
            checksum = ser.read(2)
            calc = ( sum(length_bytes) + sum(payload[:length]) + 0x42 + 0x4D ) & 0xFFFF

            recv = struct.unpack(">H", checksum)[0]

            # if calc != recv:
            #     print("Checksum mismatch")
            #     logging.error("Checksum mismatch")
            #     continue

            data = struct.unpack('>HHHHHHHHHHHHHH', payload[:length])

            # Ignored (Factory only)
            pm1_control = data[0] # (CF=1)
            pm2_5_control = data[1] # (CF=1)
            pm10_control = data[2] # (CF=1)

            # Measured
            pm1 = data[3] # (atmospheric environment)
            pm2_5 = data[4] # (atmospheric environment)
            pm10 = data[5] # (atmospheric environment)
            
            pc0_3 = data[6] # Particle count per 0.1L of air
            pc0_5 = data[7] # Particle count per 0.1L of air
            pc1 = data[8] # Particle count per 0.1L of air
            pc2_5 = data[9] # Particle count per 0.1L of air
            pc5 = data[10] # Particle count per 0.1L of air
            pc10 = data[11] # Particle count per 0.1L of air

            if verbose:
                print(f"[PMS5003] PM1.0: {pm1} µg/m³, PM2.5: {pm2_5} µg/m³, PM10: {pm10} µg/m³, PC0.3: {pc0_3}, PC0.5: {pc0_5}, PC1: {pc1}, PC2.5: {pc2_5}, PC5: {pc5}, PC10: {pc10}")

            return pm1, pm2_5, pm10, pc0_3, pc0_5, pc1, pc2_5, pc5, pc10
        except serial.SerialException as e:
            if verbose:
                print(f"[PMS5003] Serial error: {e}")
                logging.error(f"[PMS5003] Serial error: {e}")
            return None if poll else "NA", "NA", "NA", "NA", "NA", "NA", "NA", "NA", "NA"
    return None if poll else "NA", "NA", "NA", "NA", "NA", "NA", "NA", "NA", "NA"