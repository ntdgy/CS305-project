import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import struct
import socket
import config
import util.simsocket as simsocket

print(sys.path)

type = config.Type
headerType = config.headerType


class UDP:
    def __init__(self, sock: simsocket) -> None:
        self.HEADER_LEN = struct.calcsize(headerType)
        self.HEADER_LEN_PACKAGE = socket.htons(struct.calcsize(headerType))
        self.BUF_SIZE = 1400
        self.MAGIC = socket.htons(52305)
        self.TEAM = config.TEAM
        self.sock = sock

    def pack(self, type: int, data: bytes, seq: int, ack: int, rwnd: int = 0):
        return (
            struct.pack(
                headerType,
                self.MAGIC,
                self.TEAM,
                type,
                self.HEADER_LEN_PACKAGE,
                self.HEADER_LEN + len(data),
                socket.htonl(seq),
                socket.htonl(ack),
                socket.htonl(rwnd),
            )
            + data
        )

    def unpack(self, package: bytes):
        return (
            struct.unpack(headerType, package[: self.HEADER_LEN]),
            package[self.HEADER_LEN :],
        )

    def send(self, type: config.Type, data: bytes, seq: int, ack: int, rwnd: int, addr: tuple):
        self.sock.sendto(self.pack(type.value, data, seq, ack), addr)

    def recv(self):
        package, addr = self.sock.recvfrom(self.BUF_SIZE)
        header, data = self.unpack(package)
        return header, data, addr
addr = ('127.0.0.1',48001)
sock = simsocket.SimSocket(1,address=addr)
UDP = UDP(None)
a = UDP.pack(type.IHAVE.value, b"", 1, 1)
print(len(a[: struct.calcsize(headerType)]))
print(len(a))

