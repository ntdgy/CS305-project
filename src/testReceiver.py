import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from receiver import Receiver
import socket
from dataPack import UDP

if __name__ == '__main__':
    receiver = Receiver(
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM),
        addr=("127.0.0.1", 40000),
    )
    # data = b'\xccQ\x01\x01\x00\x15\x00\x18\x00\x00\x00\x01\x00\x00\x00\x01\x01\x00\x00\x00\x01123'
    # header, data = receiver.unpack(data)
    # print(header)
    # print(data)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 40001))
    sock.settimeout(1)
    while True:
        try:
            data, addr = sock.recvfrom(receiver.MSS + 21)
            import random

            if random.randint(0, 100) < 5:
                print("loss!!! seq = ", receiver.unpack(data)[0][5])
                raise socket.timeout
        except socket.timeout:
            continue
        # print(data)
        header, data = receiver.unpack(data)
        # print(header)
        if receiver.rcvSegment(header, data):
            break
    with open("test1.txt", "wb") as f:
        f.write(receiver.data)
