import read_sqmlu as sqmlu

try:
    sqmlu.init( True )
    sqmlu.read()

finally:
    sqmlu.stop()