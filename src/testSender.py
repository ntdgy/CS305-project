import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from sender import Sender

import socket

with open("src/test.txt", "rb") as f:
    data = f.read(100 * 1024)

if __name__ == '__main__':
    sender = Sender(
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM),
        addr=("127.0.0.1", 40001),
        data=data,
        MSS=1248,
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 40000))
    sock.settimeout(1)
    while True:
        sender.fillSndBuffer()
        sender.slideWindow()
        try:
            data, addr = sock.recvfrom(sender.MSS + 21)
        except socket.timeout:
            sender.detectTimeout()
            continue
        # print(data)
        header, data = sender.unpack(data)
        ack = header[6]
        rwnd = header[8]
        # print(ack, rwnd)
        sender.recvAckAndRwnd(ack=ack, rwnd=rwnd)
        sender.detectTimeout()
        # sender.fillSndBuffer()
