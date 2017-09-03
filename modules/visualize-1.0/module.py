"""
Module: visualize
Version: 1.0
Author: Nguyen Huy Anh

Requires: image.png

Visualize a file_id with transcripts into /visualize
"""

import logging
import os
import sys
from decimal import Decimal

from ffmpy import FFmpeg

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CUR_DIR))
DATA_DIR = os.path.join(ROOT_DIR, 'data/')

MODULE_NAME = 'visualize'
LOG_H = logging.StreamHandler()
LOG_F = logging.Formatter(
    '%(asctime)s (%(name)s | %(levelname)s) : %(message)s')
LOG_H.setFormatter(LOG_F)
LOG = logging.getLogger(MODULE_NAME)
LOG.propagate = False
LOG.addHandler(LOG_H)
LOG.setLevel(logging.DEBUG)

PNG_FILE = os.path.join(CUR_DIR, 'image.png')


def secs_to_timestamp(secs):
    """Convert a timestamp in seconds to a timestamp in hh:mm:ss,sss"""
    time = int(Decimal(secs) * 1000)
    time_s, time_ms = divmod(time, 1000)
    time_m, time_s = divmod(time_s, 60)
    time_h, time_m = divmod(time_m, 60)
    return '{:02d}:{:02d}:{:02d},{:03d}'.format(time_h, time_m, time_s, time_ms)


def tg_to_srt(textgrid_file, srt_file):
    """Convert a TextGrid file to an SRT file."""
    srt = dict()
    with open(textgrid_file, 'r') as file_:
        lines = file_.readlines()

    # convert textgrid to dict structure
    i = 0
    while i < len(lines):
        if lines[i].startswith(' ' * 8 + 'name'):
            # find the spk_id
            spk_id = lines[i].strip().split()[2].strip('"')
            # get the xmin, xmax and text
            i += 5
            while i < len(lines) and lines[i].startswith(' ' * 12 + 'xmin'):
                xmin = lines[i].strip().split()[2]
                xmin_key = int(Decimal(xmin) * 100)
                xmax = lines[i + 1].strip().split()[2]
                text = ' '.join(lines[i + 2].strip().split()[2:]).strip('"')
                trans = '{}: {}'.format(spk_id, text)
                srt[xmin_key] = [xmin, xmax, trans]
                i += 4
        i += 1

    # convert dict structure to srt
    i = 1
    srt_dict = dict()
    for key in sorted(srt):
        srt_dict[i] = list()
        srt_dict[i].append(
            '{} --> {}'.format(secs_to_timestamp(srt[key][0]), secs_to_timestamp(srt[key][1])))
        srt_dict[i].append(srt[key][2])
        i += 1

    with open(srt_file, 'w') as file_:
        for key in sorted(srt_dict):
            file_.write('{}\n'. format(key))
            file_.write(srt_dict[key][0] + '\n')
            file_.write(srt_dict[key][1] + '\n')
            file_.write('\n')

    LOG.debug('Written %s', srt_file)


def video(audio_file, video_file):
    """Convert an audio file to a black-screened video file."""
    # complete checks
    if os.path.exists(video_file) and os.path.getsize(video_file) > 0:
        LOG.debug('Previously converted %s', video_file)
    else:
        # specify ffmpeg inputs and outputs
        inputs = {audio_file: None, PNG_FILE: '-loop 1'}
        outputs = {
            video_file: '-c:v libx264 -c:a libvo_aacenc -b:a 128k -pix_fmt yuv420p -shortest'}
        # perform operation
        ff_ = FFmpeg(inputs=inputs, outputs=outputs)
        LOG.debug('Command: %s', ff_.cmd)
        fnull = open(os.devnull, 'w')
        ff_.run(stdout=fnull, stderr=fnull)  # silent output
        LOG.debug('Converted %s into video file %s', audio_file, video_file)


def visualize(file_id):
    """Visualize a file_id."""
    # init paths
    working_dir = os.path.join(DATA_DIR, file_id)
    # raw_dir = os.path.join(working_dir, 'raw/')
    resample_dir = os.path.join(working_dir, 'resample/')
    resample_file = os.path.join(resample_dir, '{}.wav'.format(file_id))
    trans_dir = os.path.join(working_dir, 'transcript/google')
    textgrid_file = os.path.join(trans_dir, '{}.TextGrid'.format(file_id))
    visualize_dir = os.path.join(working_dir, 'visualize/')
    if not os.path.exists(visualize_dir):
        os.makedirs(visualize_dir)
    srt_file = os.path.join(visualize_dir, '{}.srt'.format(file_id))
    video_file = os.path.join(visualize_dir, '{}.mp4'.format(file_id))

    # operations
    tg_to_srt(textgrid_file, srt_file)
    if os.path.exists(resample_file):
        video(resample_file, video_file)


if __name__ == '__main__':
    visualize(sys.argv[1])
