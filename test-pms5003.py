import read_pms5003 as pms5003

try:
    pms5003.init( True )
    pms5003.read()

finally:
    pms5003.stop()