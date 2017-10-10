"""
Module: resample
Version: 1.0
Author: Nguyen Huy Anh

Requires:

Resample a file_id into /resample
"""

import logging
import os
import sys

from ffmpy import FFmpeg

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CUR_DIR))
DATA_DIR = os.path.join(ROOT_DIR, 'data/')

MODULE_NAME = 'resample'
LOG_H = logging.StreamHandler()
LOG_F = logging.Formatter(
    '%(asctime)s (%(name)s | %(levelname)s) : %(message)s')
LOG_H.setFormatter(LOG_F)
LOG = logging.getLogger(MODULE_NAME)
LOG.propagate = False
LOG.addHandler(LOG_H)
LOG.setLevel(logging.DEBUG)


def resample_audio(audio_in, audio_out):
    """Resample an audio stream.

    Arguments:
        audio_in: str - path to input stream
        audio_out: str - path to output stream
    """
    # complete checks
    if os.path.exists(audio_out) and os.path.getsize(audio_out) > 0:
        LOG.debug('Previously resampled %s', audio_out)
    else:
        inputs = {audio_in: None}
        outputs = {audio_out: '-ac 1 -ar 16000 -sample_fmt s16'}
        ffmp = FFmpeg(inputs=inputs, outputs=outputs)
        fnull = open(os.devnull, 'w')
        ffmp.run(stdout=fnull, stderr=fnull)  # silent output
        LOG.debug('Resampled %s to %s', audio_in, audio_out)


def resample(process_id, file_id):
    """Entry point for module.

    Arguments:
        process_id: str - process id
        file_id: str - file id
    """
    # init paths
    working_dir = os.path.join(DATA_DIR, process_id, file_id)
    raw_dir = os.path.join(working_dir, 'raw/')
    raw_files = os.listdir(raw_dir)
    resample_dir = os.path.join(working_dir, 'resample/')
    if not os.path.exists(resample_dir):
        os.makedirs(resample_dir)

    # case 1: single file
    if len(raw_files) == 1:
        audio_in = os.path.join(raw_dir, os.listdir(raw_dir)[0])
        audio_out = os.path.join(resample_dir, '{}.wav'.format(file_id))
        resample_audio(audio_in, audio_out)
    # case 2: more than one file
    elif raw_files:
        for file_ in raw_files:
            audio_in = os.path.join(raw_dir, file_)
            audio_out = os.path.join(
                resample_dir, '{}.wav'.format(os.path.splitext(file_)[0]))
            resample_audio(audio_in, audio_out)


if __name__ == '__main__':
    resample(sys.argv[1], sys.argv[2])
