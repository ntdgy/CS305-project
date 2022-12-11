import random
import config
import time
import logging
import util.simsocket as simsocket
from dataPack import UDP

logging.basicConfig(
	format=
	'%(asctime)s,%(msecs)03d - %(levelname)s - %(funcName)s - %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S',
	level=logging.NOTSET)
logger = logging.getLogger()

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
                logger.error("Unknown Congestion Status")
                raise Exception("Unknown Congestion Status")
        elif event == event.TIMEOUT:
            self.duplicateAck = 0
            self.retranmission()
            if self.congestionStatus == congestionStatus.SlowStart:
                self.ssthresh = self.cwnd / 2
                self.cwnd = self.MSS
            elif self.congestionStatus == congestionStatus.CongestionAvoidance:
                self.ssthresh = self.cwnd / 2
                self.cwnd = self.MSS
                self.congestionStatus = congestionStatus.SlowStart
            elif self.congestionStatus == congestionStatus.FastRecovery:
                self.ssthresh = self.cwnd / 2
                self.cwnd = self.MSS
                self.congestionStatus = congestionStatus.SlowStart
            else:
                logger.error("Unknown Congestion Status")
                raise Exception("Unknown Congestion Status")
        elif event == event.DUP_ACK:
            self.duplicateAck += 1
            if self.duplicateAck == 3:
                self.retranmission()
                if self.congestionStatus == congestionStatus.SlowStart:
                    self.ssthresh = self.cwnd / 2
                    self.cwnd = self.ssthresh + 3 
                    self.congestionStatus = congestionStatus.CONGESTION_AVOIDANCE
                elif self.congestionStatus == congestionStatus.CongestionAvoidance:
                    self.ssthresh = self.cwnd / 2
                    self.cwnd = self.ssthresh + 3 
                    self.congestionStatus = congestionStatus.CONGESTION_AVOIDANCE
                elif self.congestionStatus == congestionStatus.FastRecovery:
                    pass
                else:
                    logger.error("Unknown Congestion Status")
                    raise Exception("Unknown Congestion Status")
        else:
            logger.error("Unknown Event")
            raise Exception("Unknown Event")
        if self.cwnd > self.ssthresh:
            self.congestionStatus = congestionStatus.CongestionAvoidance
        if oldStatus != self.congestionStatus:
            logger.info("Congestion Status Changed from %s to %s", oldStatus, self.congestionStatus)



    def retranmission(self):
        pass


