import serial
# from Serial import Serial
from serial.serialutil import *
import threading
# import serial.serialutil as serialutil
# from serial import win32
# import sys
# from SerialBrewerWin32 import SerialBrewerWin32
import SerialBrewer as SerialBrewer
from SerialBrewerWin32 import SerialException

s = serial.Serial('COM1',
         baudrate=9600,        # baudrate
         bytesize=FIVEBITS,    # number of databits
         parity=PARITY_NONE,    # enable parity checking
         stopbits=STOPBITS_ONE_POINT_FIVE, # number of stopbits
         timeout=5,             # set a timeout value, None for waiting forever
         xonxoff=0,             # enable software flow control
         rtscts=0              # enable RTS/CTS flow control
    )

def daemon():
    string = ""
    while True:
        if s.in_waiting:
            c = s.read(1)
            string += c
            print
            print string
            for str in string:
                print hex(ord(str)),
            if (c == '\r'):
                s.write(" -> ")
            # print hex(ord(c))

        time.sleep(0.5)

d = threading.Thread(target=daemon, name="Daemon")
d.setDaemon(True)
d.start()

# s2 = SerialBrewer.serial_for_url("COM2")

while True:
    time.sleep(10)
