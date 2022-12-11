import random
import config
import time
import logging
import util.simsocket as simsocket
from dataPack import UDP
from config import CongestionStatus, Event
from typing import List, Tuple

logging.basicConfig(
    format="%(asctime)s,%(msecs)03d - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.NOTSET,
)
logger = logging.getLogger()


class Connection(UDP):
    def __init__(self, sock: simsocket, addr: tuple, MSS: int = 1248) -> None:
        super().__init__(sock)
        self.addr = addr
        self.MSS = MSS
        self.SndBufferCapacity = int(65536 / self.MSS)
        self.initSeqNum = random.randint(1000, 10000)
        self.NextSeqNum = self.initSeqNum
        self.NextByteFill = self.initSeqNum
        self.duplicateAck = 0
        self.rwnd = 0
        self.TimeoutInterval = 1.0
        self.EstimatedRTT = 1.0
        self.DevRTT = 0
        self.congestionStatus = CongestionStatus.SlowStart
        self.cwnd = MSS
        self.ssthresh = 65536
        self.TimeStart = time.time()
        self.SndBuffer = [
            [
                self.NextByteFill,
            ]
        ]
        self.sendList = []

    def switchCongestionStatus(self, event: Event):
        oldStatus = self.congestionStatus
        if event == Event.NEW_ACK:
            self.duplicateAck = 0
            if self.congestionStatus == CongestionStatus.SlowStart:
                self.cwnd += self.MSS
            elif self.congestionStatus == CongestionStatus.CongestionAvoidance:
                self.cwnd += self.MSS * self.MSS / self.cwnd
            elif self.congestionStatus == CongestionStatus.FastRecovery:
                self.cwnd = self.ssthresh
                self.congestionStatus = CongestionStatus.CongestionAvoidance
            else:
                logger.error("Unknown Congestion Status")
                raise Exception("Unknown Congestion Status")
        elif event == Event.TIMEOUT:
            self.duplicateAck = 0
            self.retranmission()
            if self.congestionStatus == CongestionStatus.SlowStart:
                self.ssthresh = self.cwnd // 2
                self.cwnd = self.MSS
            elif self.congestionStatus == CongestionStatus.CongestionAvoidance:
                self.ssthresh = self.cwnd / 2
                self.cwnd = self.MSS
                self.congestionStatus = CongestionStatus.SlowStart
            elif self.congestionStatus == CongestionStatus.FastRecovery:
                self.ssthresh = self.cwnd / 2
                self.cwnd = self.MSS
                self.congestionStatus = CongestionStatus.SlowStart
            else:
                logger.error("Unknown Congestion Status")
                raise Exception("Unknown Congestion Status")
        elif event == Event.DUP_ACK:
            self.duplicateAck += 1
            if self.duplicateAck == 3:
                self.retranmission()
                if self.congestionStatus == CongestionStatus.SlowStart:
                    self.ssthresh = self.cwnd / 2
                    self.cwnd = self.ssthresh + 3
                    self.congestionStatus = CongestionStatus.CONGESTION_AVOIDANCE
                elif self.congestionStatus == CongestionStatus.CongestionAvoidance:
                    self.ssthresh = self.cwnd / 2
                    self.cwnd = self.ssthresh + 3
                    self.congestionStatus = CongestionStatus.CONGESTION_AVOIDANCE
                elif self.congestionStatus == CongestionStatus.FastRecovery:
                    pass
                else:
                    logger.error("Unknown Congestion Status")
                    raise Exception("Unknown Congestion Status")
        else:
            logger.error("Unknown Event")
            raise Exception("Unknown Event")
        if self.cwnd > self.ssthresh:
            self.congestionStatus = CongestionStatus.CongestionAvoidance
        if oldStatus != self.congestionStatus:
            logger.info(
                "Congestion Status Changed from %s to %s",
                oldStatus,
                self.congestionStatus,
            )

    def countDown(self):
        pass

    def retranmission(self):
        pass

    def send(self, type:config.Type,data: bytes) -> None:
        self.sendList.append((time.time(), self.NextSeqNum, data))
        self.NextSeqNum += len(data)
        self.NextByteFill += len(data)
        self.SndBuffer.append([self.NextByteFill, data])
        super().send(type, data, self.NextSeqNum, 0, self.rwnd, self.addr)
