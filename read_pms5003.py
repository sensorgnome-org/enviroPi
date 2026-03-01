import serial
import time
import struct
import logging
import RPi.GPIO as GPIO
import pigpio


RX_pms5003 = 27 # For software UART
exists = False

PAYLOAD_SIZE = 28
HEADER_SIZE = 4

def init( PIN_pms5003 = 17, set_verbose = False):
    global verbose,pi,exists
    verbose = set_verbose

    if verbose:
        print("[PMS5003] Initializing...")
        logging.info("[PMS5003] Initializing...")

    GPIO.setup(PIN_pms5003, GPIO.OUT)

    # Always have 5v on
    GPIO.output(PIN_pms5003, GPIO.LOW)

    time.sleep(0.1)

    pi = pigpio.pi()
    if not pi.connected:
        if verbose:
            print("[PMS5003] Error: Could not connect to pigpio daemon")
            logging.error("[PMS5003] Error: Could not connect to pigpio daemon")
        return False

    # Connect to UART for PMS5003 (default UART on GPIO14/15 is /dev/serial0)
    #ser = serial.Serial(device, baudrate=9600, timeout=5)
    status = pi.bb_serial_read_open(RX_pms5003, 9600)
    # Discard data for 300 ms to let PMS5003 align to next frame
    # start = time.time()
    # buf = bytearray()
    
    # while time.time() - start < 2.0:  # up to 2 seconds
    #     count, data = pi.bb_serial_read(RX_pms5003)
    #     if count > 0:
    #         buf.extend(data)

    #     if b'\x42\x4d' in buf:
    #         exists = True
    #         if verbose:
    #             print("[PMS5003] Found a header")
    #             logging.error("[PMS5003] Found a header")
    #         break

    #     time.sleep(0.01)

    time.sleep(2.0)
    pi.bb_serial_read(RX_pms5003)  # drain whatever accumulated during warmup



def on(pin):
    GPIO.output(pin, GPIO.LOW)

def off(pin):
    GPIO.output(pin, GPIO.HIGH)

def stop():
    pi.bb_serial_read_close(RX_pms5003)
    pi.stop()

def poll():
    global exists
    if not exists:
        if verbose:
            print(f"[PMS5003] Checking if pms5003 exists...")
            logging.error(f"[PMS5003] Checking if pms5003 exists...")
        exists = read( True )
    return exists

def read( poll = False ):
    global exists

    if verbose:
        print("[PMS5003] Reading...")
        logging.info("[PMS5003] Reading...")

    start = time.time()
    buf = bytearray()
    MAX_TIME = 3.0   # seconds

    while time.time() - start < MAX_TIME:
        count, data = pi.bb_serial_read(RX_pms5003)
        if count > 0:
            buf.extend(data)

        if len(buf) < HEADER_SIZE + PAYLOAD_SIZE:
            time.sleep(0.1)  # nothing yet, wait for data to arrive
            continue
        # Look for header
        while True:
            idx = buf.find(b'\x42\x4d')
            if idx < 0:
                if verbose:
                    # print(f"[PMS5003] No header found")
                    print(f"[PMS5003] No header found, buf length={len(buf)}, buf={buf.hex()}")
                    logging.error(f"[PMS5003] No header found")
                break  # header not found yet
                            
            # Need at least header (4 bytes) to read length
            if len(buf) < idx + HEADER_SIZE + PAYLOAD_SIZE:
                if verbose:
                    print(f"[PMS5003] Buffer too short: buf length={len(buf)}, buf={buf.hex()}")
                    logging.error(f"[PMS5003] No header found")
                continue  # need more data

            # Get payload size
            length = struct.unpack(">H", buf[idx+2:idx+4])[0]

            if length != PAYLOAD_SIZE:
                if verbose:
                    print(f"[PMS5003] Payload wrong length: expected {PAYLOAD_SIZE} bytes, got {length}")
                logging.error(f"[PMS5003] Payload wrong length: expected {PAYLOAD_SIZE} bytes, got {length}")
                # Skip past this false header and keep scanning
                del buf[:idx+2]
                continue
            elif verbose:
                print(f"[PMS5003] Payload length is {length}")
            
            frame_len = HEADER_SIZE + length  # header + length + (payload + checksum)

            # Don't have a full frame yet
            if len(buf) < idx + frame_len:
                if verbose:
                    print(f"[PMS5003] Buffer too short to contain frame: expected {idx + frame_len} bytes, got {len(buf)}")
                logging.error(f"[PMS5003] Buffer too short to contain frame: expected {idx + frame_len} bytes, got {len(buf)}")
                break  # need more data

            frame = buf[idx:idx+frame_len]
            # Remove frame from buffer
            del buf[:idx+frame_len]

            # Parse payload
            payload = frame[HEADER_SIZE:HEADER_SIZE+length]
            parsed = struct.unpack('>HHHHHHHHHHHHHH', payload)

            if poll:
                return True
                
            exists = True

            checksum_recv = struct.unpack(">H", frame[frame_len-2:frame_len])[0]

            # Compute checksum
            checksum_calc = (sum(frame[0:frame_len-2])) & 0xFFFF

            if checksum_calc != checksum_recv:
                # Bad frame, skip
                if verbose:
                    print(f"[PMS5003] Checksum failed")
                    print("BAD FRAME:", frame.hex())
                    print("checksum_recv:", checksum_recv)
                logging.error(f"[PMS5003] Checksum failed")
                #del buf[:idx+2]  # remove only the 0x42 0x4D
                #continue


            # Ignored (Factory only)
            pm1_control = parsed[0] # (CF=1)
            pm2_5_control = parsed[1] # (CF=1)
            pm10_control = parsed[2] # (CF=1)

            # Measured
            pm1 = parsed[3] # (atmospheric environment)
            pm2_5 = parsed[4] # (atmospheric environment)
            pm10 = parsed[5] # (atmospheric environment)
            
            pc0_3 = parsed[6] # Particle count per 0.1L of air
            pc0_5 = parsed[7] # Particle count per 0.1L of air
            pc1 = parsed[8] # Particle count per 0.1L of air
            pc2_5 = parsed[9] # Particle count per 0.1L of air
            pc5 = parsed[10] # Particle count per 0.1L of air
            pc10 = parsed[11] # Particle count per 0.1L of air

            if verbose:
                print(f"[PMS5003] PM1.0: {pm1} µg/m³, PM2.5: {pm2_5} µg/m³, PM10: {pm10} µg/m³, PC0.3: {pc0_3}, PC0.5: {pc0_5}, PC1: {pc1}, PC2.5: {pc2_5}, PC5: {pc5}, PC10: {pc10}")

            return pm1, pm2_5, pm10, pc0_3, pc0_5, pc1, pc2_5, pc5, pc10

        if verbose:
            print(f"[PMS5003] Serial error")
            logging.error(f"[PMS5003] Serial error")
        return False if poll else ("NA",)*9
            
    if verbose:
        print(f"[PMS5003] No response.")
        logging.error(f"[PMS5003] No response.")
    return False if poll else ("NA",)*9