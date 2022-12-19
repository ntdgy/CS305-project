import peer
import sys
import os
import pickle
import util.bt_utils as bt_utils


class BtConfig():
    def __init__(self, args):
        self.output_file = 'output.dat'
        self.peer_list_file = args['p']
        self.has_chunk_file = args['c']
        self.max_conn = args['m']
        self.identity = args['i']
        self.peers = []
        self.haschunks = dict()
        self.verbose = args['v']
        self.timeout = args['t']

        self.bt_parse_peer_list()
        self.bt_parse_haschunk_list()

        if self.identity == 0:
            print('bt_parse error:  Node identity must not be zero!')
            sys.exit(1)

        p = self.bt_peer_info(self.identity)
        if p is None:
            print('bt_parse error:  No peer information for myself (id ', self.identity, ')!')
            sys.exit(1)

        self.ip = p[1]
        self.port = int(p[2])

    def bt_parse_peer_list(self):
        with open(self.peer_list_file, 'r') as file:
            for line in file:
                if line[0] == '#':
                    continue
                line = line.strip(os.linesep)
                self.peers.append(line.split(' '))

    def bt_parse_haschunk_list(self):
        with open(self.has_chunk_file, 'rb') as file:
            self.haschunks = pickle.load(file)

    def bt_peer_info(self, identity):
        for item in self.peers:
            if int(item[0]) == identity:
                return item
        return None
# "test/tmp1/nodes1.map", "test/tmp1/data1.fragment", 1, ("127.0.0.1", 48001)
args = {}
args['i'] = 2
args['p'] = "../test/tmp1/nodes1.map"
args['c'] = "../test/tmp1/data2.fragment"
args['m'] = 1
args['v'] = 0
args['t'] = 0

config1 = BtConfig(args)
peer1 = peer.peer_run(config1)

