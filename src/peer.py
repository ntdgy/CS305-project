import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import select
import util.simsocket as simsocket
import struct
import socket
import util.bt_utils as bt_utils
import hashlib
import argparse
import pickle
import time
from config import HEADER_LEN, Type
from enum import Enum
from typing import List, Tuple, Dict, NamedTuple
from dataPack import UDP
from receiver import Receiver
from sender import Sender


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

"""
This is CS305 project skeleton code.
Please refer to the example files - example/dumpreceiver.py and example/dumpsender.py - to learn how to play with this skeleton.
"""

BUF_SIZE = 1400

config1 = None
ReceiverList: Dict[Tuple[str, int], Receiver] = dict()
chunkStatuses: List[ChunkStatus] = []

SenderList: Dict[Tuple[str, int], Sender] = {}
udp: UDP = None
simsock: simsocket.SimSocket = None
start_time = 0


def process_download(sock, chunkfile: str, outputfile: str):
    """
    if DOWNLOAD is used, the peer will keep getting files until it is done
    """
    global start_time
    start_time = time.time()
    # load configs, fill has_chunks, chunk_output_file, and pending_chunks
    with open(chunkfile, "r") as cf:
        lines = cf.readlines()
        for line in lines:
            index, chunkhash_str = line.strip().split(" ")
            config1.haschunks[chunkhash_str] = b''
            config1.chunk_output_file = outputfile
            config1.pending_chunks.append(chunkhash_str)
    print(f"Pending Chunks: {config1.pending_chunks}")
    for chunk_hash in config1.pending_chunks:
        for peer in config1.peers:
            if int(peer[0]) != config1.identity:
                # print(udp.pack(type1=Type.WHOHAS.value, data=datahash, ack=0, seq=0, sf=0))
                print(f"Send WHOHAS to {peer}: Asking {chunk_hash}")
                sock.sendto(udp.pack(type1=Type.WHOHAS.value, data=chunk_hash.encode(), ack=0, seq=0, sf=0),
                            (peer[1], int(peer[2])))
                chunkStatuses.append(ChunkStatus(chunk_hash, (peer[1], int(peer[2])), time.time()))


def start_download(sock, chunk_hash: str, from_peer: Tuple[str, int]):
    for chunkStatus in chunkStatuses:
        if chunkStatus.chunk_hash == chunk_hash and chunkStatus.peer == from_peer:
            chunkStatus.status = ChunkStatusType.DOWNLOADING
    print(f"Create Receiver and send GET to {from_peer}, {chunk_hash}")
    global ReceiverList
    ReceiverList[from_peer] = Receiver(sock=sock, hash=chunk_hash, remote_addr=from_peer)
    ReceiverList[from_peer].sendSegment(type1=Type.GET, data=chunk_hash.encode(), seq=0, ack=0, sf=0, rwnd=0,
                                        addr=from_peer)
    print(f"ReceiverList: {ReceiverList}")


def process_inbound_udp(sock):
    global ReceiverList
    # Receive pkt
    pkt, from_addr = sock.recvfrom(BUF_SIZE)
    header, data = udp.unpack(pkt)
    _, _, type1, _, totalLen, seq, ack, sf, rwnd = header
    # print(f"RECV {from_addr[1]}: dataLen:{len(data)} seq:{seq} ack:{ack} sf:{sf} rwnd:{rwnd}")
    if type1 == 0:
        # WHOHAS
        # see what chunk the sender has
        whohas_chunk_hash: bytes = data
        chunkhash_str = whohas_chunk_hash.decode()
        print(f"WHOHAS from {from_addr}, {chunkhash_str}")
        if chunkhash_str in config1.haschunks and config1.haschunks[chunkhash_str]:
            print(f"ihave: {chunkhash_str}, has: {list(config1.haschunks.keys())}")
            udp.sendSegment(type1=Type.IHAVE, data=whohas_chunk_hash, seq=0, ack=0, sf=0, rwnd=0, addr=from_addr)
        else:
            print(f"idonthave: {chunkhash_str}, has: {list(config1.haschunks.keys())}")
            udp.sendSegment(type1=Type.DONT_HAVE, data=whohas_chunk_hash, seq=0, ack=0, sf=0, rwnd=0, addr=from_addr)
    elif type1 == 1:
        # receive IHAVE
        chunk_hash_bytes: bytes = data
        chunk_hash_str: str = chunk_hash_bytes.decode()
        print(f"IHAVE from {from_addr}, {chunk_hash_str}")
        if from_addr in ReceiverList:
            # This peer {from_addr} is downloading other chunk, mark this chunk as SUSPENDING and exit
            print(f"Duplicated IHAVE from {from_addr}, {chunk_hash_str}: Exist chunk_hash {ReceiverList[from_addr].hash}, mark as suspended")
            for chunkStatus in chunkStatuses:
                if chunkStatus.chunk_hash == chunk_hash_str and chunkStatus.peer == from_addr:
                    chunkStatus.status = ChunkStatusType.SUSPENDING
            return
        for recv in ReceiverList:
            if ReceiverList[recv].hash == chunk_hash_str:
                # This chunk is downloading from {chunkStatus.peer}, mark this chunk as SUSPENDING and exit
                print(f"Duplicated IHAVE from {from_addr}, {chunk_hash_str}: Exist peer {recv} is downloading, mark as suspended")
                for chunkStatus in chunkStatuses:
                    if chunkStatus.chunk_hash == chunk_hash_str and chunkStatus.peer == from_addr:
                        chunkStatus.status = ChunkStatusType.SUSPENDING
                        break
                return
        # This peer is free, and this chunk is not downloading, start to download
        start_download(sock, chunk_hash_str, from_addr)
    elif type1 == 2:
        # GET
        chunk_hash_bytes: bytes = data
        chunk_hash_str: str = chunk_hash_bytes.decode()
        # print(f"get: {get_chunk_hash}")
        # print(f"get: {get_chunk_hash}, has: {list(config1.haschunks.keys())}")
        chunk_data = config1.haschunks[chunk_hash_str]
        sender = Sender(sock=sock, data=chunk_data, addr=from_addr)
        SenderList[from_addr] = sender
        sender.fillSndBuffer()
        sender.slideWindow()
        print(f"Receive GET from {from_addr}, {chunk_hash_str}: Create Sender")
    elif type1 == 3:
        # DATA
        # print(f"Receive DATA from {from_addr}, recvs: {ReceiverList}")
        if from_addr in ReceiverList:
            receiver = ReceiverList[from_addr]
            chunk_hash_str: str = receiver.hash
            if receiver.rcvSegment(header, data):
                # This chunk_hash is completed
                # store data, remove chunk_hash from pending_chunks, and delete Receiver
                config1.haschunks[chunk_hash_str] = receiver.data
                config1.downloaded_chunks[chunk_hash_str] = receiver.data
                config1.pending_chunks.remove(chunk_hash_str)
                for chunkStatus in chunkStatuses:
                    if chunkStatus.chunk_hash == chunk_hash_str and chunkStatus.peer == from_addr:
                        chunkStatus.status = ChunkStatusType.DOWNLOADED
                del ReceiverList[from_addr]
                print(f"Complete Chunk: {chunk_hash_str}")

                for chunkStatus in chunkStatuses:
                    if chunkStatus.peer == from_addr and chunkStatus.status == ChunkStatusType.SUSPENDING:
                        # if this chunk is downloading from other peer, ignore this.
                        if any(recv.hash == chunkStatus.chunk_hash for recv in ReceiverList.values()):
                            continue
                        # if this chunk is downloaded, mark it as unused
                        if chunkStatus.chunk_hash in config1.downloaded_chunks:
                            chunkStatus.status = ChunkStatusType.UNUSED
                            continue
                        print(f"Resume suspended Chunk: {chunkStatus.chunk_hash} from {chunkStatus.peer}")
                        start_download(sock, chunkStatus.chunk_hash, chunkStatus.peer)
                        break

                if len(config1.pending_chunks) == 0:
                    # all chunks are received
                    with open(config1.chunk_output_file, "wb") as f:
                        pickle.dump(config1.downloaded_chunks, f)
                    print(f"GOT {config1.chunk_output_file}")
                    # sha1 = hashlib.sha1()
                    # sha1.update(receiver.data)
                    # received_chunkhash_str = sha1.hexdigest()
                    # print(f"Expected chunkhash: {receiver.hash}")
                    # print(f"Received chunkhash: {received_chunkhash_str}")
                    # success = receiver.hash == received_chunkhash_str.encode()
                    # print(f"Successful received: {success}")
                    # print(f"Time elapsed: {time.time() - start_time}")
                    # if success:
                    #     print("Congrats! You have completed the example!")
                    # else:
                    #     print("Example fails. Please check the example files carefully.")
    elif type1 == 4:
        # ACK
        print(f"ACK from {from_addr}: {header}")
        if from_addr in SenderList:
            sender = SenderList[from_addr]
            # header, data = sender.unpack(data)
            ack = header[6]
            rwnd = header[8]
            sender.recvAckAndRwnd(ack=ack, rwnd=rwnd)
            sender.detectTimeout()
            sender.fillSndBuffer()
            sender.slideWindow()
            if sender.finish:
                del SenderList[from_addr]
    elif type1 == 5:
        # DENIED
        chunk_hash_str = data.decode()
        for chunkStatus in chunkStatuses:
            if chunkStatus.chunk_hash == chunk_hash_str and chunkStatus.peer == from_addr:
                chunkStatus.status = ChunkStatusType.UNUSED
    elif type1 == 6:
        # don't have
        chunk_hash_str = data.decode()
        print(f"DONT HAVE from {from_addr}: {chunk_hash_str}")
        for chunkStatus in chunkStatuses:
            if chunkStatus.chunk_hash == chunk_hash_str and chunkStatus.peer == from_addr:
                chunkStatus.status = ChunkStatusType.UNUSED


def checkCheckList():
    now = time.time()
    for check in chunkStatuses:
        if check.status == ChunkStatusType.ASKING:
            if now - check.request_time > 3:
                print(check)
                simsock.sendto(udp.pack(type1=Type.WHOHAS.value, data=check.chunk_hash.encode(), ack=0, seq=0, sf=0), check.peer)
                check.request_time = now


def process_user_input(sock):
    command, chunkf, outf = input().split(' ')
    print(f"command: {command}, chunkf: {chunkf}, outf: {outf}")
    if command == 'DOWNLOAD':
        process_download(sock, chunkf, outf)
    else:
        pass


def peer_run(config):
    global config1
    config1 = config
    addr = (config1.ip, config1.port)
    sock = simsocket.SimSocket(config1.identity, addr, verbose=config1.verbose)
    global simsock
    simsock = sock
    global udp
    udp = UDP(sock)
    try:
        while True:
            ready = select.select([sock, sys.stdin], [], [], 0.005)
            read_ready = ready[0]
            if len(read_ready) > 0:
                if sock in read_ready:
                    process_inbound_udp(sock)
                if sys.stdin in read_ready:
                    process_user_input(sock)
            else:
                global ReceiverList
                # No pkt nor input arrives during this period 
                for addr in SenderList:
                    SenderList[addr].detectTimeout()
                    SenderList[addr].fillSndBuffer()
                    SenderList[addr].slideWindow()
                delReceiverKeys = []
                initialAddrs = list(ReceiverList.keys())
                for addr in initialAddrs:
                    recv = ReceiverList[addr]
                    if recv.lastTime + 10 < time.time():
                        # recv is timeout for 10 seconds, delete this peer and mark all chunks from it as unused
                        peer_addr = recv.remote_addr
                        for chunkStatus in chunkStatuses:
                            if chunkStatus.peer == peer_addr:
                                chunkStatus.status = ChunkStatusType.UNUSED
                        chunk_hash = recv.hash
                        print(f"Receiver {addr} timeout, downloading {chunk_hash}")
                        for chunkStatus in chunkStatuses:
                            if chunkStatus.chunk_hash == chunk_hash and chunkStatus.status == ChunkStatusType.SUSPENDING:
                                if chunkStatus.peer not in ReceiverList:
                                    # if this peer is free, download chunk_hash from this peer
                                    start_download(sock, chunk_hash, chunkStatus.peer)
                                    break
                        delReceiverKeys.append(addr)
                for addr in delReceiverKeys:
                    del ReceiverList[addr]
                checkCheckList()
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()


if __name__ == '__main__':
    """
    -p: Peer list file, it will be in the form "*.map" like nodes.map.
    -c: Chunkfile, a dictionary dumped by pickle. It will be loaded automatically in bt_utils. The loaded dictionary has the form: {chunkhash: chunkdata}
    -m: The max number of peer that you can send chunk to concurrently. If more peers ask you for chunks, you should reply "DENIED"
    -i: ID, it is the index in nodes.map
    -v: verbose level for printing logs to stdout, 0 for no verbose, 1 for WARNING level, 2 for INFO, 3 for DEBUG.
    -t: pre-defined timeout. If it is not set, you should estimate timeout via RTT. If it is set, you should not change this time out.
        The timeout will be set when running test scripts. PLEASE do not change timeout if it set.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', type=str, help='<peerfile>     The list of all peers', default='nodes.map')
    parser.add_argument('-c', type=str, help='<chunkfile>    Pickle dumped dictionary {chunkhash: chunkdata}')
    parser.add_argument('-m', type=int, help='<maxconn>      Max # of concurrent sending')
    parser.add_argument('-i', type=int, help='<identity>     Which peer # am I?')
    parser.add_argument('-v', type=int, help='verbose level', default=0)
    parser.add_argument('-t', type=int, help="pre-defined timeout", default=0)
    args = parser.parse_args()

    config1 = bt_utils.BtConfig(args)
    peer_run(config1)
