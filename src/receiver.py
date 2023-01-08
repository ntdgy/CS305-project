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
    def __init__(self, sock: simsocket, remote_addr: Tuple[str, int], hash: str, Mss: int = 1400) -> None:
        super().__init__(sock=sock)
        self.finished = False
        self.remote_addr = remote_addr
        self.hash: str = hash
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
        self.lastTime = time.time()
        self.next_expected_seq = 0

    def rcvSegment(self, header: tuple, data: bytes) -> bool:
        finishFlag = False
        _, _, type1, _, _, seq, ack, sf, rwnd = header
        # logger.info("Recv: seq: %d, ack: %d, len: %d", seq, ack, len(data))
        self.lastTime = time.time()
        if sf == 1:
            self.next_expected_seq = seq + len(data)
            self.first = True
            self.data = b""
        elif len(self.RcvBuffer) < self.RcvBufferCapacity and seq >= self.next_expected_seq:
            if self.first == True:
                self.first = False
                self.dataLen = int(data.decode())
                logger.info(f"Data length: {self.dataLen}")
                self.next_expected_seq = seq + len(data)
                # print("NextSeqNum2: ", self.NextSeqNum)
            else:
                # progress = self.progress
                # while self.count * self.MSS / self.dataLen >= self.progress * 0.05:
                #     self.progress += 1
                # if self.progress > progress:
                #     logger.info(f"Progress: {self.progress * 5}%")
                #     speed = self.count / (time.time() - self.lastTime)
                #     logger.info(f"Speed: {speed} bytes/s")
                i = 0
                while i < len(self.RcvBuffer) and self.RcvBuffer[i][0] < seq:
                    i += 1
                if len(self.RcvBuffer) == 0 or i == len(self.RcvBuffer) or self.RcvBuffer[i][0] != seq:
                    self.RcvBuffer.insert(i, (seq, data, sf))
                i = 0
                while i < len(self.RcvBuffer):  # and self.next_expected_seq == self.RcvBuffer[i][0]:
                    if self.next_expected_seq != self.RcvBuffer[i][0]:
                        self.fastRetransmit(self.next_expected_seq)
                        break
                    self.next_expected_seq += len(self.RcvBuffer[i][1])
                    # print("NextSeqNum3: ", self.NextSeqNum)
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
        rwnd = (self.RcvBufferCapacity - len(self.RcvBuffer)) * self.MSS
        super().sendSegment(
            Type.ACK,
            data=b"",
            seq=0,
            ack=self.next_expected_seq,
            sf=0,
            rwnd=rwnd,
            addr=self.remote_addr,
        )
        # logger.info(f"Send: ack {self.next_expected_seq}, rwnd: {rwnd}")
        return finishFlag

    def fastRetransmit(self, seq: int):
        super().sendSegment(
            Type.ACK,
            data=b"",
            seq=0,
            ack=seq,
            sf=0,
            rwnd=0,
            addr=self.remote_addr,
        )
        super().sendSegment(
            Type.ACK,
            data=b"",
            seq=0,
            ack=seq,
            sf=0,
            rwnd=0,
            addr=self.remote_addr,
        )
        super().sendSegment(
            Type.ACK,
            data=b"",
            seq=0,
            ack=seq,
            sf=0,
            rwnd=0,
            addr=self.remote_addr,
        )
        logger.info(f"Send: ack {self.next_expected_seq}")
