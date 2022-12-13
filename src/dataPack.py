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
        self.MAGIC = 52305
        self.TEAM = config.TEAM
        # self.sock = sock
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def pack(self, type1: int, data: bytes, seq: int, ack: int, sf: int, rwnd: int = 0):
        a = (
            struct.pack(
                config.headerType,
                self.MAGIC,
                self.TEAM,
                type1,
                struct.calcsize(config.headerType),
                self.HEADER_LEN + len(data),
                seq,
                ack,
                sf,
                rwnd,
            )
            + data
        )
        return a

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
        print("sendSegment")
        self.send(self.pack(type1.value, data, seq, ack, sf, rwnd), addr)

    def recv(self):
        package, addr = self.sock.recvfrom(self.BUF_SIZE)
        header, data = self.unpack(package)
        return header, data, addr


# UDP=UDP(None)
# a = UDP.pack(1, b"123", 1, 1, 1, 1)
# print(a)
