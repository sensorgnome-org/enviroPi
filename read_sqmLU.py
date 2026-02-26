import serial
import logging

# Replace with the actual port your SQM is on
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 115200

def init(set_verbose = False):
    global verbose
    verbose = set_verbose
    if verbose:
        print("[SQM-LU] Initializing...")
        logging.info("[SQM-LU] Initializing...")

def read(port=SERIAL_PORT):
    if verbose:
        print("[SQM-LU] Reading...")
        logging.info("[SQM-LU] Reading...")
    try:
        with serial.Serial(port, BAUD_RATE, timeout=2) as ser:
            # Send the read command
            ser.write(b'Rx\r')
            ser.flush()
            # Read the response
            response = ser.read(255).decode('utf-8').strip()
            if verbose:
                print(f"[SQM-LU] Response: {response}")
                logging.info(f"[SQM-LU] Response: {response}")
            return parse(response)
    except serial.SerialException as e:
        if verbose:
            print(f"[SQM-LU] Serial error: {e}")
        logging.info(f"[SQM-LU] Serial error: {e}")
        return None

def parse(data):
    try:
        parts = [part.strip() for part in data.split(',')]
        if len(parts) >= 1 and parts[0] == 'r':
            light_level = parts[1].rstrip('m')                 # '11.33'
            frequency = int(parts[2].rstrip('Hz'))              # 2772
            count = int(parts[3].rstrip('c'))                    # 0
            duration = float(parts[4].rstrip('s'))               # 0.0
            temperature = float(parts[5].rstrip('C'))            # 22.8
            return light_level,frequency,count,duration,temperature
        else:
            return None
    except ValueError:
        if verbose:
            print(f"[SQM-LU] Failed to parse: {data}")
        logging.info(f"[SQM-LU] Failed to parse: {data}")
        return None