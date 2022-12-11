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


class Sender(UDP):
    def __init__(
        self, sock: simsocket, addr: tuple, data: bytes, MSS: int = 1248
    ) -> None:
        super().__init__(sock)
        self.addr = addr
        self.data = data
        self.dataPointer = 0
        self.dataLen = len(data)
        self.MSS = MSS
        self.SndBufferCapacity = int(65536 / self.MSS)
        self.initSeqNum = random.randint(1000, 10000)
        self.NextSeqNum = self.initSeqNum
        self.NextByteFill = self.initSeqNum
        self.duplicateAck = 0
        self.rwnd = 0
        self.EstimatedRTT = 1.0
        self.progress = 1
        self.DevRTT = 0
        self.congestionStatus = CongestionStatus.SlowStart
        self.cwnd = MSS
        self.ssthresh = 65536
        self.TimeStart = time.time()
        self.TimeoutInterval = 1.0
        # [[SeqNum, Segment, Sent, Start Time]]
        self.SndBuffer = [
            [
                self.NextByteFill,
                super.pack(Type.DATA.value, b"", self.NextByteFill, 0, 1, 0),
                False,
                0,
            ]
        ]
        self.NextByteFill += len(self.SndBuffer[0][1]) - HEADER_LEN
        self.sendList = []
        self.first = True

    def fillSndBuffer(self):
        if self.first == True:
            self.SndBuffer.append(
                [
                    self.NextByteFill,
                    super.pack(
                        Type.DATA.value,
                        str(self.dataLen).encode(),
                        self.NextByteFill,
                        0,
                        0,
                        0,
                    ),
                    False,
                    time.time(),
                ]
            )
            self.first = False
            self.NextByteFill += len(self.SndBuffer[-1][1]) - HEADER_LEN
        if len(self.SndBuffer) < self.SndBufferCapacity:
            segment = self.data[self.dataPointer : self.dataPointer + self.MSS]
            self.dataPointer += self.MSS
            if len(segment) == 0:
                # pack(self, type: int, data: bytes, seq: int, ack: int, sf: int, rwnd: int = 0):
                self.SndBuffer.append(
                    [
                        self.NextByteFill,
                        super.pack(
                            Type.DATA.value,
                            b"0",
                            self.NextByteFill,
                            0,
                            2,
                            0,
                        ),
                        False,
                    ]
                )
                return
            self.SndBuffer.append(
                [
                    self.NextByteFill,
                    super.pack(Type.DATA.value, segment, self.NextByteFill, 0, 0, 0),
                    False,
                    time.time(),
                ]
            )
            self.NextByteFill += len(self.SndBuffer[-1][1]) - HEADER_LEN

    # if the package if ack
    def recvAckAndRwnd(self, ack: int, rwnd: int):
        # header, data = super().unpack(package)
        # _, _, type1, _, _, seq, ack, sf, rwnd = header
        # # seq = socket.ntohl(seq)
        # ack = socket.ntohl(ack)
        # # sf = socket.ntohs(sf)
        # rwnd = socket.ntohl(rwnd)
        if ack == self.NextSeqNum:
            self.switchCongestionStatus(Event.DUP_ACK)
        elif ack > self.NextSeqNum:
            self.NextSeqNum = ack
            self.switchCongestionStatus(Event.NEW_ACK)
            progress = self.progress
            while (
                self.NextSeqNum - self.initSeqNum
            ) / self.dataLen >= self.progress * 0.05:
                self.progress += 1
            if progress < self.progress:
                logger.info("Progress: %d%%", self.progress * 5)
                logger.info(
                    "EstimatedRTT={0:.2} DevRTT={1:.2} TimeoutInterval={2:.2}".format(
                        self.EstimatedRTT, self.DevRTT, self.TimeoutInterval
                    )
                )
            while len(self.SndBuffer) and self.SndBuffer[0][0] < self.NextSeqNum:
                self.updateTimeOutInterval(self.SndBuffer[0][3])
                s = self.SndBuffer.pop(0)
                if (len(self.SndBuffer)) == 0 and socket.ntohs(
                    super.unpack(s[1])[6]
                ) == 2:
                    logger.info("Finish")
                    logger.info("Time: %f", time.time() - self.TimeStart)
            self.rwnd = rwnd
            self.TimeStart = time.time()

    def updateTimeOutInterval(self, startTime):
        sampleRTT = time.time() - startTime
        self.EstimatedRTT = 0.875 * self.EstimatedRTT + 0.125 * sampleRTT
        self.DevRTT = 0.75 * self.DevRTT + 0.25 * abs(sampleRTT - self.EstimatedRTT)
        self.TimeoutInterval = self.EstimatedRTT + 4 * self.DevRTT

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

    def detectTimeout(self):
        if time.time() - self.TimeStart > self.TimeoutInterval:
            self.switchCongestionStatus(Event.TIMEOUT)

    def slideWindow(self):
        for i in range(len(self.SndBuffer)):
            if self.SndBuffer[i][2] == False and self.SndBuffer[i][0] - self.NextSeqNum <= min(self.rwnd, self.cwnd):
                self.SndBuffer[i].append(time.time())
                logger.info("Send: %d", self.SndBuffer[i][0])
                super().send(self.SndBuffer[i][1], self.addr)
                self.TimeStart = time.time()
                self.SndBuffer[i][2] = True
            elif self.sndBuffer[i][2] == True:
                break
                

    def retranmission(self):
        for segment in self.SndBuffer:
            if segment[0] == self.NextSeqNum:
                segment[3] = time.time()
                super().send(segment[1], self.addr)
                logger.info("Retranmission: %d", segment[0])
                self.TimeStart = time.time()
                break


    def send(self, type: config.Type, data: bytes) -> None:
        self.sendList.append((time.time(), self.NextSeqNum, data))
        self.NextSeqNum += len(data)
        self.NextByteFill += len(data)
        self.SndBuffer.append([self.NextByteFill, data])
        super().send(type, data, self.NextSeqNum, 0, self.rwnd, self.addr)