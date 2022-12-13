import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import struct
import socket
import config
import util.simsocket as simsocket
from config import Type



class UDP:
    # def __init__(self, sock: simsocket) -> None:
    def __init__(self, sock: None) -> None:
        self.HEADER_LEN = struct.calcsize(config.headerType)
        self.BUF_SIZE = 1400
        self.MAGIC = socket.htons(52305)
        self.TEAM = config.TEAM
        # self.sock = sock
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def pack(self, type1: int, data: bytes, seq: int, ack: int, sf: int, rwnd: int = 0):
        return (
            struct.pack(
                config.headerType,
                self.MAGIC,
                self.TEAM,
                type1,
                socket.htons(struct.calcsize(config.headerType)),
                socket.htons(self.HEADER_LEN + len(data)),
                socket.htonl(seq),
                socket.htonl(ack),
                socket.htons(sf),
                socket.htonl(rwnd),
            )
            + data
        )

    def unpack(self, package: bytes):
        return (
            struct.unpack(config.headerType, package[: self.HEADER_LEN]),
            package[self.HEADER_LEN :],
        )

    def send(
        self,
        package: bytes,
        addr: tuple,
    ):
        self.sock.sendto(package, addr)
    
    def sendSegment(self, type1: Type,data: bytes, seq: int, ack: int, sf: int, rwnd: int = 0, addr: tuple = None):
        self.send(self.pack(type1.value, data, seq, ack, sf, rwnd), addr)

    def recv(self):
        package, addr = self.sock.recvfrom(self.BUF_SIZE)
        header, data = self.unpack(package)
        return header, data, addr


# addr = ("127.0.0.1", 48001)
# sock = simsocket.SimSocket(1, address=addr)
# UDP = UDP(None)
# print(struct.calcsize(headerType))
# a = UDP.pack(Type.IHAVE.value, b"1", 1, 1,1,1)
# print(a)
# header, data = UDP.unpack(a)
# print(header)
# socket.ntohl(header[6])
# print(data)
