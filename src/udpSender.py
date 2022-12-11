import random
import config
import time
import json
import util.simsocket as simsocket
from dataPack import UDP

congestionStatus = config.congestionStatus
event = config.event


class sender(UDP):
    def __init__(self, sock: simsocket, MSS: int = 1248) -> None:
        super().__init__(sock)
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
        self.congestionStatus = congestionStatus.SlowStart
        self.cwnd = MSS
        self.ssthresh = 65536
        self.TimeStart = time.time()
        self.SndBuffer = [
            [
                self.NextByteFill,
            ]
        ]
    
    def switchCongestionStatus(self, event:event):
        oldStatus = self.congestionStatus
        if event == event.NEW_ACK:
            self.duplicateAck = 0
            if self.congestionStatus == congestionStatus.SlowStart:
                self.cwnd += self.MSS
            elif self.congestionStatus == congestionStatus.CongestionAvoidance:
                self.cwnd += self.MSS * self.MSS / self.cwnd
            elif self.congestionStatus == congestionStatus.FastRecovery:
                self.cwnd = self.ssthresh
                self.congestionStatus = congestionStatus.CongestionAvoidance
            else:
                raise Exception("Unknown Congestion Status")
        elif event == congestionStatus.DUPLICATE_ACK:

