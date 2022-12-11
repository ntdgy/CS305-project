import struct
import socket
import config

class UDP:
    def __init__(self) -> None:
        self.HEADER_LEN = struct.calcsize("HBBHHII")
        self.HEADER_LEN_PACKAGE = socket.htons(struct.calcsize("HBBHHII"))
        self.BUF_SIZE = 1400
        self.MAGIC = socket.htons(52305)
        self.TEAM = config.TEAM
        temp = ""
        temp.strip()

    def pack(self, type: int, data: bytes, seq: int, ack: int):
        return (
            struct.pack(
                "HBBHHII",
                self.MAGIC,
                self.TEAM,
                type,
                self.HEADER_LEN_PACKAGE,
                self.HEADER_LEN + len(data),
                socket.htonl(seq),
                socket.htonl(ack),
            )
            + data
        )
    
    def unpack(self, package: bytes):
        return struct.unpack("HBBHHII", package[:self.HEADER_LEN]), package[self.HEADER_LEN:]


