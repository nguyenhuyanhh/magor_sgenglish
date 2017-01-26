"""
Module: lvcsr
Version: 1601
Requires: cmd.sh, path.sh, decoding.sh

Python wrapper for Singapore English LVCSR platform
"""

import os
import subprocess
import sys

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CUR_DIR))
DATA_DIR = os.path.join(ROOT_DIR, 'data/')


def lvcsr(file_id):
    """Transcribe a file using LVCSR system, into /transcript/lvcsr."""
    # init paths
    system_dir = os.path.join(CUR_DIR, 'systems')
    graph_dir = os.path.join(system_dir, 'graph')
    nnet_dir = os.path.join(system_dir, 'fbank_nnet')

    # transcribe
    os.chdir(os.path.join(CUR_DIR, 'scripts/'))
    args = ['./decoding.sh', system_dir, graph_dir, nnet_dir, file_id]
    subprocess.call(args)

if __name__ == '__main__':
    lvcsr(sys.argv[1])
