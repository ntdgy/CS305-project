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


os.chdir("..")

args = dict()
args['i'] = 1
args['p'] = "test/tmp2/nodes2.map"
args['c'] = "test/tmp2/data1.fragment"
args['m'] = 100
args['v'] = 0
args['t'] = 0
# DOWNLOAD test/tmp2/download_target.chunkhash test/tmp2/download_result.fragment

if __name__ == '__main__':
    config1 = bt_utils.BtConfig(dotdict(args))
    peer1 = peer.peer_run(config1)

