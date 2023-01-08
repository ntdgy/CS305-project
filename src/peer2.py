import peer
import sys
import os
import pickle
import util.bt_utils as bt_utils


class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

# "test/tmp1/nodes1.map", "test/tmp1/data1.fragment", 1, ("127.0.0.1", 48001)
os.chdir("..")
args = dict()
args['i'] = 2
args['p'] = "test/tmp2/nodes2.map"
args['c'] = "test/tmp2/data2.fragment"
args['m'] = 1
args['v'] = 0
args['t'] = 0

if __name__ == '__main__':
    config1 = bt_utils.BtConfig(dotdict(args))
    peer1 = peer.peer_run(config1)

