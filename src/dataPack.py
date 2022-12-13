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
            package[self.HEADER_LEN:],
        )

    def send(
            self,
            package: bytes,
            addr: tuple,
    ):
        self.sock.sendto(package, addr)

    def sendSegment(self, type1: Type, data: bytes, seq: int, ack: int, sf: int, rwnd: int = 0, addr: tuple = None):
        # print("sendSegment")
        # print(type1, data, seq, ack, sf, rwnd, addr)
        if rwnd < 0:
            rwnd = 0
        self.send(self.pack(type1.value, data, seq, ack, sf, rwnd), addr)

    def recv(self):
        package, addr = self.sock.recvfrom(self.BUF_SIZE)
        header, data = self.unpack(package)
        return header, data, addr


# data = b""
# a = struct.pack(">HBBHHIIBI", 52305, 1, 1, struct.calcsize(">HBBHHIIBI"), struct.calcsize(">HBBHHIIBI") + len(data), 1, 1,
#                 1, 1, )
# print(a)
# StdHeaderLen = struct.calcsize("HBBHHII")
# magic, team, pkt_type, header_len, pkt_len, seq, ack = struct.unpack("HBBHHII", a[:StdHeaderLen])
# data = b'\xccQ\x01\x03\x00\x15\x00\x16\x00\xa0\x046\x00\x00\x00\x00\x02\x00\x00\x00\x000'
# header, data = UDP.unpack(data)
# print(header)
# print(data)
# data = b'\xccQ\x01\x03\x00\x15\x00\x16\x00\xa0\tZ\x00\x00\x00\x00\x02\x00\x00\x00\x000'
# header, data = UDP.unpack(data)
# print(header)
# print(data)
