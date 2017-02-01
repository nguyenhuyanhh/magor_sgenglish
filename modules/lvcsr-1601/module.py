"""
Module: lvcsr
Version: 1601
Author: Nguyen Huy Anh

Requires: scripts/, systems/

Python wrapper for Singapore English LVCSR platform
"""

import logging
import os
import subprocess
import sys

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CUR_DIR))
DATA_DIR = os.path.join(ROOT_DIR, 'data/')

MODULE_NAME = 'lvcsr'
LOG_H = logging.StreamHandler()
LOG_F = logging.Formatter(
    '%(asctime)s (%(name)s | %(levelname)s) : %(message)s')
LOG_H.setFormatter(LOG_F)
LOG = logging.getLogger(MODULE_NAME)
LOG.propagate = False
LOG.addHandler(LOG_H)
LOG.setLevel(logging.DEBUG)


def lvcsr(file_id):
    """Transcribe a file using LVCSR system, into /transcript/lvcsr."""
    # init paths
    system_dir = os.path.join(CUR_DIR, 'systems')
    graph_dir = os.path.join(system_dir, 'graph')
    nnet_dir = os.path.join(system_dir, 'fbank_nnet')

    # transcribe
    os.chdir(os.path.join(CUR_DIR, 'scripts/'))
    args = ['./decoding.sh', system_dir, graph_dir, nnet_dir, file_id]
    LOG.debug('Command: %s', ' '.join(args))
    subprocess.call(args)

if __name__ == '__main__':
    lvcsr(sys.argv[1])
