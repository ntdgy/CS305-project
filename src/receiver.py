import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import random
import config
import time
import logging
import socket
import util.simsocket as simsocket
from dataPack import UDP
from config import CongestionStatus, Event, Type, HEADER_LEN
from typing import List, Tuple

logging.basicConfig(
    format="%(asctime)s,%(msecs)03d - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.NOTSET,
)
logger = logging.getLogger()


class Receiver(UDP):
    def __init__(self, sock: simsocket, addr: tuple, Mss: int = 1248) -> None:
        super().__init__(sock)
        self.finished = False
        self.addr = addr
        self.MSS = Mss
        self.data = b""
        self.dataLen = 0
        self.RcvBufferCapacity = int(65536 / Mss)
        self.RcvBuffer = []  # [(SeqNum, Data, sf)]
        self.rwnd = 0
        self.first = True
        self.dataLen = 0
        self.progress = 1
        self.count = 0
        self.lastTime = 0
        self.NextSeqNum = 0

    def rcvSegment(self, header: tuple, data: bytes) -> bool:
        finishFlag = False
        _, _, type1, _, _, seq, ack, sf, rwnd = header
        seqNum = socket.ntohl(seq)
        sf = socket.ntohs(sf)
        if sf == 1:
            self.NextSeqNum = seq + len(data)
        elif len(self.RcvBuffer) < self.RcvBufferCapacity and seqNum >= self.NextSeqNum:
            if self.first == True:
                self.first = False
                self.dataLen = int(data.decode())
                logger.info(f"Data length: {self.dataLen}")
                self.NextSeqNum = seq + len(data)
                self.lastTime = time.time()
            else:
                progress = self.progress
                while self.count * self.MSS / self.dataLen >= self.progress * 0.05:
                    self.progress += 1
                if self.progress != progress:
                    logger.info(f"Progress: {self.progress * 5}%")
                    speed = self.count / (time.time() - self.lastTime)
                    logger.info(f"Speed: {speed} bytes/s")
                i = 0
                while i < len(self.RcvBuffer) and self.RcvBuffer[i][0] < seqNum:
                    i += 1
                if (
                    len(self.RcvBuffer) == 0
                    or i == len(self.RcvBuffer)
                    or self.RcvBuffer[i][0] != seqNum
                ):
                    self.RcvBuffer.insert(i, (seqNum, data, sf))
                    i = 0
                    while (
                        i < len(self.RcvBuffer)
                        and self.NextSeqNum == self.RcvBuffer[i][0]
                    ):
                        self.NextSeqNum += len(self.RcvBuffer[i][1])
                        if self.RcvBuffer[i][2] == 2:
                            finishFlag = True
                            logger.info("Finish flag received")
                        else:
                            self.data += self.RcvBuffer[i][1]
                            self.count += 1
                        i += 1
                    self.RcvBuffer = self.RcvBuffer[i:]
                    if len(self.RcvBuffer) == self.RcvBufferCapacity:
                        self.RcvBuffer.pop(0)
        rwnd = self.RcvBufferCapacity - len(self.RcvBuffer) * self.MSS
        super().sendSegment(
            Type.ACK,
            data=b"",
            seq=0,
            ack=self.NextSeqNum,
            sf=0,
            rwnd=rwnd,
            addr=self.addr,
        )
        return finishFlag
