TEAM = 1
headerType = ">HBBHHIIBI"


import struct
HEADER_LEN = struct.calcsize(headerType)

from enum import Enum


class Type(Enum):
    WHOHAS = 0
    IHAVE = 1
    GET = 2
    DATA = 3
    ACK = 4
    DENIED = 5
    DONT_HAVE = 6


class CongestionStatus(Enum):
    SLOW_START = 0
    CONGESTION_AVOIDANCE = 1
    FAST_RECOVERY = 2


class Event(Enum):
    NEW_ACK = 0
    TIMEOUT = 1
    DUP_ACK = 1
    