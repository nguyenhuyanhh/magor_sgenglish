"""
Module: convert
Version: 1.0
Author: Nguyen Huy Anh

Requires:

Convert a video file_id into /convert
"""

import logging
import os
import shutil
import sys

from ffmpy import FFmpeg

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CUR_DIR))
DATA_DIR = os.path.join(ROOT_DIR, 'data/')

MODULE_NAME = 'convert'
LOG_H = logging.StreamHandler()
LOG_F = logging.Formatter(
    '%(asctime)s (%(name)s | %(levelname)s) : %(message)s')
LOG_H.setFormatter(LOG_F)
LOG = logging.getLogger(MODULE_NAME)
LOG.propagate = False
LOG.addHandler(LOG_H)
LOG.setLevel(logging.DEBUG)


def convert(process_id, file_id):
    """Convert a file_id."""
    # init paths
    working_dir = os.path.join(DATA_DIR, process_id, file_id)
    raw_dir = os.path.join(working_dir, 'raw/')
    convert_dir = os.path.join(working_dir, 'convert/')

    # convert
    video_in = os.path.join(raw_dir, os.listdir(raw_dir)[0])
    video_out = os.path.join(convert_dir, '{}.mp4'.format(file_id))
    if os.path.exists(video_out) and os.path.getsize(video_out) > 0:
        LOG.debug('Previously converted %s', video_out)
    else:
        if not os.path.exists(convert_dir):
            os.makedirs(convert_dir)
        if os.path.splitext(video_in)[1] == '.mp4':
            shutil.copy2(video_in, video_out)
            LOG.debug('%s already in mp4', video_in)
        else:
            inputs = {video_in: None}
            outputs = {video_out: None}
            ffmp = FFmpeg(inputs=inputs, outputs=outputs)
            LOG.debug('Converting command: %s', ffmp.cmd)
            fnull = open(os.devnull, 'w')
            ffmp.run(stdout=fnull, stderr=fnull)  # silent output
            LOG.debug('Converted %s to %s', video_in, video_out)


if __name__ == '__main__':
    convert(sys.argv[1], sys.argv[2])
