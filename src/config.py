TEAM = 1
headerType = ">HBBHHIIBI"

import struct

HEADER_LEN = struct.calcsize(headerType)

from enum import Enum
from typing import Tuple


class ChunkStatusType(Enum):
    ASKING = 0
    DOWNLOADING = 1
    DOWNLOADED = 2
    SUSPENDING = 3
    UNUSED = 4
    # This peer declares it has the chunk, but this peer is downloading other chunk


class ChunkStatus:
    chunk_hash: str
    peer: Tuple[str, int]
    request_time: float
    status: ChunkStatusType = ChunkStatusType.ASKING

    def __init__(self, chunk_hash: str, peer: Tuple[str, int], request_time: float):
        self.chunk_hash = chunk_hash
        self.peer = peer
        self.request_time = request_time

    def __str__(self):
        return f"[ChunkStatus: {self.chunk_hash}, {self.peer}, {self.request_time}, {self.status}]"


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
