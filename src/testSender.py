import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from sender import Sender

import socket


with open("src/test.txt", "rb") as f:
    data = f.read(10 * 1024 * 1024)

sender = Sender(
    socket.socket(socket.AF_INET, socket.SOCK_DGRAM),
    addr=("127.0.0.1", 40001),
    data=data,
    MSS=1248,
)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind("127.0.0.1", 40000)

