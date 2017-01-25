"""
Module: diarize
Version: 8.4.1
Requires: LIUM_SpkDiarization-8.4.1.jar

Python wrapper for speaker diarization using LIUM
"""

import os
import subprocess
import sys

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CUR_DIR))
DATA_DIR = os.path.join(ROOT_DIR, 'data/')


def diarize(file_id):
    """Diarize a file using LIUM, into /diarization."""
    # init paths
    working_dir = os.path.join(DATA_DIR, file_id)
    resample_dir = os.path.join(working_dir, 'resample/')
    diarize_dir = os.path.join(working_dir, 'diarization/')
    if not os.path.exists(diarize_dir):
        os.makedirs(diarize_dir)

    # diarize
    resample_file = os.path.join(resample_dir, '{}.wav'.format(file_id))
    lium_path = os.path.join(CUR_DIR, 'LIUM_SpkDiarization-8.4.1.jar')
    diarize_file = os.path.join(diarize_dir, '{}.seg'.format(file_id))
    fnull = open(os.devnull, 'w')
    args = ['java', '-Xmx2048m', '-jar', lium_path, '--fInputMask=' +
            resample_file, '--sOutputMask=' + diarize_file, '--doCEClustering', file_id]
    subprocess.call(args, stdout=fnull, stderr=subprocess.STDOUT)

if __name__ == '__main__':
    diarize(sys.argv[1])
