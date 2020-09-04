#%% run
import socket
import struct
import time

INFLUX_IP = 'BenTerry-PC'
INFLUX_PORT = 6001

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((INFLUX_IP, INFLUX_PORT))

for i in range(0,50, 1):
    data = struct.pack("<ccHff",b"G",b"T", 0x342, float(i), 6.6)
    sock.send(data)
    time.sleep(500/1000)


sock.close()