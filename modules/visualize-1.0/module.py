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
import subprocess
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


def check_ffmpeg_v3():
    """Return True if ffmpeg is v3 and above."""
    version_str = subprocess.check_output(['ffmpeg', '-version'])
    return version_str.split('\n')[0].split()[2] >= '3'


def tg_to_srt(textgrid_file, textgrid_id, temp_dir):
    """Convert a TextGrid file to an SRT data structure, and store in temp file.

    Arguments:
        textgrid_file: str - path to TextGrid file
        textgrid_id: str - id of TextGrid file (in case of multiple TextGrids)
        temp_dir: str - path to temp folder
    """
    srt = dict()
    temp_file = os.path.join(temp_dir, '{}.json'.format(textgrid_id))

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
                    xmin = int(Decimal(lines[i].strip().split()[2]) * 100)
                    xmax = int(Decimal(lines[i + 1].strip().split()[2]) * 100)
                    text = ' '.join(
                        lines[i + 2].strip().split()[2:]).strip('"')
                    srt[xmin] = {
                        'xmin': xmin,
                        'xmax': xmax,
                        'tg_id': textgrid_id,
                        'spk_id': spk_id,
                        'text': text,
                    }
                    i += 4
            i += 1

        # write output
        with open(temp_file, 'w') as json_:
            json.dump(srt, json_, indent=4, sort_keys=True)
        LOG.debug('tg_to_srt operation completed for %s', textgrid_file)

    return srt


def combine_srt(srt_list, temp_dir):
    """Combine multiple srt data structures together.

    Arguments:
        srt_list: list(dict) - list of srt data structures
        temp_dir: str - path to temp folder
    """
    temp_file = os.path.join(temp_dir, 'combine_srt.json')
    # get a list of start-end time boundaries
    time_bound = set()
    for srt in srt_list:
        for value in srt.values():
            time_bound.add(value['xmin'])
            time_bound.add(value['xmax'])
    time_bound = sorted(list(time_bound))

    # assign texts to time boundaries
    result = dict()
    for i in range(len(time_bound) - 1):
        ymin = time_bound[i]
        ymax = time_bound[i + 1]
        tmp = dict()
        for srt in srt_list:
            for key, value in sorted(srt.items()):
                if key <= ymin <= ymax <= value['xmax']:
                    tmp[value['tg_id']] = [value['spk_id'], value['text']]
        if tmp:
            result[ymin] = {
                'ymin': ymin,
                'ymax': ymax,
            }
            for key, value in sorted(tmp.items()):
                result[ymin][key] = value

    with open(temp_file, 'w') as json_:
        json.dump(result, json_, indent=4, sort_keys=True)
    LOG.debug('combine_srt operation completed')
    return result


def secs_to_hms(secs):
    """Convert a timestamp in srt data structure to a timestamp in hh:mm:ss,sss.

    Arguments:
        secs: int/ str - timestamp in srt data structure
    """
    time = int(Decimal(secs) * 10)
    time_s, time_ms = divmod(time, 1000)
    time_m, time_s = divmod(time_s, 60)
    time_h, time_m = divmod(time_m, 60)
    return '{:02d}:{:02d}:{:02d},{:03d}'.format(time_h, time_m, time_s, time_ms)


def write_srt(srt, srt_file):
    """Write srt file from srt data structure."""
    i = 1
    srt_dict = dict()
    for key, value in sorted(srt.items()):
        trans = sorted(
            [j for j in value.keys() if j != 'ymin' and j != 'ymax'])
        srt_dict[i] = list()
        srt_dict[i].append(
            '{} --> {}'.format(secs_to_hms(value['ymin']), secs_to_hms(value['ymax'])))
        for tran in trans:
            srt_dict[i].append('[{}]{}: {}'.format(
                tran, value[tran][0], value[tran][1]))
        i += 1

    with open(srt_file, 'w') as file_:
        for key, value in sorted(srt_dict.items()):
            file_.write('\n'.join([str(key)] + value))
            file_.write('\n\n')

    LOG.debug('Written %s', srt_file)


def video(audio_file, video_file):
    """Convert an audio file to a black-screened video file."""
    # specify ffmpeg inputs and outputs
    inputs = {audio_file: None, PNG_FILE: '-loop 1'}
    if check_ffmpeg_v3():
        outputs = {
            video_file: '-c:v libx264 -c:a aac -b:a 128k -pix_fmt yuv420p -shortest'}
    else:  # add '-strict -2' for ffmpeg 2.8 and below
        outputs = {
            video_file: '-c:v libx264 -c:a aac -b:a 128k -pix_fmt yuv420p -shortest -strict -2'}
    # perform operation
    ff_ = FFmpeg(inputs=inputs, outputs=outputs)
    LOG.debug('Command: %s', ff_.cmd)
    fnull = open(os.devnull, 'w')
    ff_.run(stdout=fnull, stderr=fnull)  # silent output
    LOG.debug('Converted %s into video file %s', audio_file, video_file)


def visualize(process_id, file_id):
    """Entry point for module.

    Arguments:
        process_id: str - process id
        file_id: str - file id
    """
    # init paths
    working_dir = os.path.join(DATA_DIR, process_id, file_id)
    raw_dir = os.path.join(working_dir, 'raw/')
    raw_file = os.path.join(raw_dir, os.listdir(raw_dir)[0])
    resample_dir = os.path.join(working_dir, 'resample/')
    resample_file = os.path.join(resample_dir, '{}.wav'.format(file_id))
    vad_dir = os.path.join(working_dir, 'vad/')
    vad_file = os.path.join(vad_dir, '{}.wav'.format(file_id))
    trans_dir = os.path.join(working_dir, 'transcript')
    capgen_dir = os.path.join(working_dir, 'keyframes/')
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
    # transform all transcripts to srt data structure
    if os.path.exists(trans_dir):
        for trans in os.listdir(trans_dir):
            trans_subdir = os.path.join(trans_dir, trans)
            trans_single = os.path.join(
                trans_subdir, '{}.TextGrid'.format(file_id))
            trans_files = [i for i in os.listdir(trans_subdir) if os.path.splitext(i)[
                1] == '.TextGrid']
            if os.path.exists(trans_single):  # single-file transcript
                tmp.append(tg_to_srt(trans_single, trans, temp_dir))
            elif trans_files:  # multi-file transcript
                for file_ in trans_files:
                    tmp.append(tg_to_srt(os.path.join(
                        trans_subdir, file_), os.path.splitext(file_)[0], temp_dir))
    # transform captions to srt data structure
    if os.path.exists(capgen_dir):
        capgen_textgrid = os.path.join(
            capgen_dir, '{}.TextGrid'.format(file_id))
        tmp.append(tg_to_srt(capgen_textgrid, 'capgen', temp_dir))
    # merge srt data structures and write
    if tmp:
        write_srt(combine_srt(tmp, temp_dir), srt_file)
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
    elif os.path.exists(vad_file):
        video(vad_file, video_file)


if __name__ == '__main__':
    visualize(sys.argv[1], sys.argv[2])
