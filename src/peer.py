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
from typing import List, Tuple
from dataPack import UDP
from receiver import Receiver
from sender import Sender

"""
This is CS305 project skeleton code.
Please refer to the example files - example/dumpreceiver.py and example/dumpsender.py - to learn how to play with this skeleton.
"""

BUF_SIZE = 1400

config1 = None
ReceiverList = {}
SenderList = {}
udp: UDP
checkList = []
chunk_output = {}
simsock = None
start_time = 0


def process_download(sock, chunkfile, outputfile):
    '''
    if DOWNLOAD is used, the peer will keep getting files until it is done
    '''
    print('PROCESS DOWNLOAD SKELETON CODE CALLED.  Fill me in!')
    global start_time
    start_time = time.time()
    with open(chunkfile, "r") as cf:
        lines = cf.readlines()
        for line in lines:
            index, datahash_str = line.strip().split(" ")
            # datahash = bytes.fromhex(datahash_str)
            datahash = datahash_str.encode()
            chunk_output[datahash_str] = outputfile
            config1.haschunks[datahash] = None
            for peer in config1.peers:
                if int(peer[0]) != config1.identity:
                    print(udp.pack(type1=Type.WHOHAS.value, data=datahash, ack=0, seq=0, sf=0))
                    sock.sendto(udp.pack(type1=Type.WHOHAS.value, data=datahash, ack=0, seq=0, sf=0), (peer[1],
                                                                                                       int(peer[2])))
                checkList.append((datahash, (peer[1], int(peer[2]), time.time())))


def process_inbound_udp(sock):
    # Receive pkt
    pkt, from_addr = sock.recvfrom(BUF_SIZE)
    # print(f"Received pkt from {from_addr}")
    # print(f"pkt: {pkt}")
    header, data = udp.unpack(pkt)
    _, _, type1, _, _, seq, ack, sf, rwnd = header
    # print('RECEIVED PKT: type = {}, seq = {}, ack = {}, sf = {}, rwnd = {}'.format(type1, seq, ack, sf, rwnd))
    # print('RECEIVED PKT: data = {}'.format(data))
    if type1 == 0:
        # WHOHAS
        # see what chunk the sender has
        if len(SenderList) >= config1.max_conn:
            udp.sendSegment(type1=Type.DENIED, data=b'', ack=0, seq=0, sf=0, addr=from_addr)
            return
        whohas_chunk_hash = data
        # chunkhash_str = bytes.hex(whohas_chunk_hash)
        chunkhash_str = whohas_chunk_hash.decode()
        if chunkhash_str in config1.haschunks:
            print(f"ihave: {chunkhash_str}, has: {list(config1.haschunks.keys())}")
            udp.sendSegment(type1=Type.IHAVE, data=whohas_chunk_hash, seq=0, ack=0, sf=0, rwnd=0, addr=from_addr)
        else:
            print(f"idonthave: {chunkhash_str}, has: {list(config1.haschunks.keys())}")
            udp.sendSegment(type1=Type.DONT_HAVE, data=whohas_chunk_hash, seq=0, ack=0, sf=0, rwnd=0, addr=from_addr)
    elif type1 == 1:
        # ihave
        # get_chunk_hash : bytes
        get_chunk_hash = data.decode()
        # print(f"get: {get_chunk_hash}")
        # print(f"ihave: {get_chunk_hash}, has: {list(config1.haschunks.keys())}")
        for check in checkList:
            if check[0] == get_chunk_hash:
                checkList.remove(check)
        get_chunk_hash = get_chunk_hash.encode()
        udp.sendSegment(type1=Type.GET, data=get_chunk_hash, seq=0, ack=0, sf=0, rwnd=0, addr=from_addr)
        receiver = Receiver(sock=sock, hash=get_chunk_hash, addr=from_addr)
        ReceiverList[from_addr] = receiver
    elif type1 == 2:
        # get
        get_chunk_hash = data.decode()
        # print(f"get: {get_chunk_hash}")
        # print(f"get: {get_chunk_hash}, has: {list(config1.haschunks.keys())}")
        chunk_data = config1.haschunks[get_chunk_hash]
        sender = Sender(sock=sock, data=chunk_data, addr=from_addr)
        SenderList[from_addr] = sender
        sender.fillSndBuffer()
        sender.slideWindow()
    elif type1 == 3:
        # DATA
        if from_addr in ReceiverList:
            receiver = ReceiverList[from_addr]
            # header, data = receiver.unpack(data)
            if receiver.rcvSegment(header, data):
                config1.haschunks[receiver.hash.decode()] = receiver.data
                with open(config1.has_chunk_file, "wb") as f:
                    pickle.dump(config1.haschunks, f)
                with open(chunk_output[receiver.hash.decode()], "wb") as f:
                    pickle.dump({receiver.hash.decode(): receiver.data}, f)
                print(f"GOT chunk {receiver.hash}")
                sha1 = hashlib.sha1()
                sha1.update(receiver.data)
                received_chunkhash_str = sha1.hexdigest()
                print(f"Expected chunkhash: {receiver.hash}")
                print(f"Received chunkhash: {received_chunkhash_str}")
                success = receiver.hash == received_chunkhash_str.encode()
                print(f"Successful received: {success}")
                print(f"Time elapsed: {time.time() - start_time}")
                if success:
                    print("Congrats! You have completed the example!")
                else:
                    print("Example fails. Please check the example files carefully.")
    elif type1 == 4:
        # ACK
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
        get_chunk_hash = data
        for check in checkList:
            if check[0] == get_chunk_hash:
                checkList.remove(check)
    elif type1 == 6:
        # don't have
        get_chunk_hash = data
        for check in checkList:
            if check[0] == get_chunk_hash and check[1] == from_addr:
                checkList.remove(check)


def checkCheckList():
    now = time.time()
    for check in checkList:
        if now - check[2] > 3:
            checkList.remove(check)
            simsock.sendto(udp.pack(type1=Type.WHOHAS.value, data=check[0], ack=0, seq=0, sf=0), (check[1][0],
                                                                                                  check[1][1]))


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
            ready = select.select([sock, sys.stdin], [], [], 0.001)
            read_ready = ready[0]
            if len(read_ready) > 0:
                if sock in read_ready:
                    process_inbound_udp(sock)
                if sys.stdin in read_ready:
                    process_user_input(sock)
            else:
                # No pkt nor input arrives during this period 
                for addr in SenderList:
                    SenderList[addr].detectTimeout()
                    SenderList[addr].fillSndBuffer()
                    SenderList[addr].slideWindow()
                try:
                    checkCheckList()
                except:
                    pass
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
