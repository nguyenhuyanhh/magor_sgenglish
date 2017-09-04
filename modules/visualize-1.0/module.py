"""
Module: visualize
Version: 1.0
Author: Nguyen Huy Anh

Requires: image.png

Visualize a file_id with transcripts into /visualize
"""

import json
import logging
import os
import shutil
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


def tg_to_srt(textgrid_file, id_, temp_file):
    """Convert a TextGrid file to an SRT data structure."""
    srt = dict()

    # complete checks
    if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
        with open(temp_file, 'r') as json_:
            tmp = json.load(json_)
            srt = {int(k): v for k, v in tmp.items()}
        LOG.debug('tg_to_srt operation previously completed for %s', textgrid_file)
    else:
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
                    text = ' '.join(
                        lines[i + 2].strip().split()[2:]).strip('"')
                    trans = '[{}]{}: {}'.format(id_, spk_id, text)
                    srt[xmin_key] = {
                        'xmin': xmin,
                        'xmax': xmax,
                        'trans': trans,
                    }
                    i += 4
            i += 1

        # write output
        with open(temp_file, 'w') as json_:
            json.dump(srt, json_, indent=4, sort_keys=True)
        LOG.debug('tg_to_srt operation completed for %s', textgrid_file)

    return srt


def combine_srt(srt1, srt2):
    """Combine two srt data structures together."""
    result = dict()
    for key, value in srt1.items():
        result[key] = {
            'xmin': value['xmin'],
            'xmax': value['xmax'],
            'trans': value['trans'] + '\n' + srt2[key]['trans']
        }
    LOG.debug('combine_srt operation completed')
    return result


def write_srt(srt, srt_file):
    """Write srt file from srt data structure."""
    i = 1
    srt_dict = dict()
    for key in sorted(srt):
        srt_dict[i] = list()
        srt_dict[i].append(
            '{} --> {}'.format(secs_to_timestamp(srt[key]['xmin']), secs_to_timestamp(srt[key]['xmax'])))
        srt_dict[i].append(srt[key]['trans'])
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
    raw_dir = os.path.join(working_dir, 'raw/')
    raw_file = os.path.join(raw_dir, os.listdir(raw_dir)[0])
    resample_dir = os.path.join(working_dir, 'resample/')
    resample_file = os.path.join(resample_dir, '{}.wav'.format(file_id))
    trans_dir = os.path.join(working_dir, 'transcript')
    visualize_dir = os.path.join(working_dir, 'visualize/')
    if not os.path.exists(visualize_dir):
        os.makedirs(visualize_dir)
    srt_file = os.path.join(visualize_dir, '{}.srt'.format(file_id))
    video_file = os.path.join(visualize_dir, '{}.mp4'.format(file_id))
    temp_dir = os.path.join(working_dir, 'temp/visualize')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    # write srt
    tmp = list()
    if os.listdir(trans_dir):
        # transform all textgrids to srt data structure
        for trans in os.listdir(trans_dir):
            trans_file = os.path.join(
                trans_dir, trans, '{}.TextGrid'.format(file_id))
            temp_file = os.path.join(temp_dir, '{}.json'.format(trans))
            tmp.append(tg_to_srt(trans_file, trans, temp_file))

        # merge srt data structures if necessary
        srt_data = tmp[0]
        if len(tmp) >= 2:
            for i in range(1, len(tmp)):
                srt_data = combine_srt(srt_data, tmp[i])

        # write srt
        write_srt(srt_data, srt_file)
    else:
        LOG.debug('No transcripts found for %s', file_id)

    # produce video_file
    # complete checks for video_file
    if os.path.exists(video_file) and os.path.getsize(video_file) > 0:
        LOG.debug('Previously processed %s', video_file)
    elif os.path.splitext(raw_file)[1].lower() == '.mp4':
        shutil.copy2(raw_file, video_file)
        LOG.debug('Video raw file, copied into %s', video_file)
    elif os.path.exists(resample_file):
        video(resample_file, video_file)


if __name__ == '__main__':
    visualize(sys.argv[1])
