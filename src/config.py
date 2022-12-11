TEAM = 1
headerType = "HBBHHIII"

from enum import Enum
class Type(Enum):
    WHOHAS = 0
    IHAVE = 1
    GET = 2
    DATA = 3
    ACK = 4
    DENIED = 5

class congestionStatus(Enum):
    SLOW_START = 0
    CONGESTION_AVOIDANCE = 1
    FAST_RECOVERY = 2

class event(Enum):
    NEW_ACK = 0
    TIMEOUT = 1
    DUP_ACK = 1
    