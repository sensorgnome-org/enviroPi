import serial
import serial.tools.list_ports
import logging
import json
import time

# Replace with the actual port your SQM is on
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 115200
VENDOR_ID = 0x0403
PRODUCT_ID = 0x6001

def init(set_verbose = False):
    global verbose
    verbose = set_verbose
    if is_serial_device(SERIAL_PORT):
        vid, pid, desc = get_port_info(SERIAL_PORT)
        if vid == VENDOR_ID and pid == PRODUCT_ID:
            if verbose:
                print("[SQM-LU] Device found.")
                logging.info("[SQM-LU] Device found.")
            print(json.dumps(["status", "connected"]), flush=True)
        else:
            if verbose:
                print(f"[SQM-LU] Wrong device found at address \"{SERIAL_PORT}\": vendor={vid}, product={pid}")
                logging.info(f"[SQM-LU] Wrong device found at address: {SERIAL_PORT}")
            print(json.dumps(["status", "no-dev"]), flush=True)
    else:
        if verbose:
            print(f"[SQM-LU] No device at address {SERIAL_PORT}")
            logging.info(f"[SQM-LU] No device at address {SERIAL_PORT}")
        print(json.dumps(["status", "no-dev"]), flush=True)

def read(port=SERIAL_PORT):
    if verbose:
        print("[SQM-LU] Reading...")
        logging.info("[SQM-LU] Reading...")
    try:
        with serial.Serial(port, BAUD_RATE, timeout=5) as ser:
            time.sleep(0.3)          # let port settle after open
            ser.reset_input_buffer() # clear any stale data
            # Send the read command
            ser.write(b'Rx\r')
            ser.flush()
            # Read the response
            response = ser.read(255).decode('utf-8').strip()
            print(json.dumps(["status", "connected"]), flush=True)
            if verbose:
                print(f"[SQM-LU] Response: {response}")
                logging.info(f"[SQM-LU] Response: {response}")
            return parse(response)
    except serial.SerialException as e:
        if verbose:
            print(f"[SQM-LU] Serial error: {e}")
        print(json.dumps(["status", "no-dev"]), flush=True)
        logging.info(f"[SQM-LU] Serial error: {e}")
        return None

def parse(data):
    try:
        parts = [part.strip() for part in data.split(',')]
        if len(parts) == 6 and parts[0] == 'r':
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
        print(json.dumps(["status", "error"]), flush=True)
        return None

def is_serial_device(port):
    try:
        s = serial.Serial(port)
        s.close()
        return True
    except serial.SerialException:
        return False

def get_port_info(device):
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.device == device:
            return port.vid, port.pid, port.description
    return None