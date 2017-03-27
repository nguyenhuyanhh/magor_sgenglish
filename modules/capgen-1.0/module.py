"""
Module: capgen
Version: 1.0
Author: Peter
Modified by: Nguyen Huy Anh

Requires: neuraltalk2/

Generating captions for video keyframes.
"""

import json
import logging
import os
import re
import sys
from subprocess import PIPE, Popen

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CUR_DIR))
DATA_DIR = os.path.join(ROOT_DIR, 'data/')

MODULE_NAME = 'capgen'
LOG_H = logging.StreamHandler()
LOG_F = logging.Formatter(
    '%(asctime)s (%(name)s | %(levelname)s) : %(message)s')
LOG_H.setFormatter(LOG_F)
LOG = logging.getLogger(MODULE_NAME)
LOG.propagate = False
LOG.addHandler(LOG_H)
LOG.setLevel(logging.DEBUG)


def get_length(video_path):
    """Get the length of a video."""
    p_args = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
              '-of', 'default=noprint_wrappers=1:nokey=1', video_path]
    p_open = Popen(p_args, stdout=PIPE)
    dur_str = p_open.stdout.readline()
    dur = float(dur_str)
    LOG.debug('Video length: %s seconds', dur)
    return dur


def extract(video_path):
    """Extract scenes from a video."""
    p_args = ['ffmpeg', '-hide_banner', '-i', video_path, '-vf',
              "select=gte(scene\\,0.40),showinfo", '-vsync', '2',
              '-loglevel', 'info', '-nostats', '-f', 'null', 'null', '-y']
    p_open = Popen(p_args, stderr=PIPE)
    expected_id = 0
    result = [0.]
    # [Parsed_showinfo_1 @ 0x2842bc0] n:   0 pts: 456569 pts_time:5.07299 pos:   760122
    parser = re.compile(
        '\\[Parsed_showinfo_1 @ \\w+] n: {0,3}(\\d+) pts: {0,6}\\d+ pts_time:(\\d+\\.\\d+|\\d+) ')
    while True:
        line = p_open.stderr.readline().rstrip()
        if line == '':
            break
        matches = parser.match(line)
        if matches is None:
            continue
        expected_id += 1
        groups = matches.groups()
        frame_id = int(groups[0]) + 1  # shift 0-based indexing to 1-based
        start_time = float(groups[1])
        assert expected_id == frame_id, 'Missing frame id! Expected: %d, received: %d' % (
            expected_id, frame_id)
        result.append(start_time)
    LOG.debug('extract operation completed')
    return result


def get_middle(video_path, t_arr, out_dir):
    """Get keyframe (middle frame) from each scene"""
    frames = []
    dur = get_length(video_path)
    next_id = 0
    t_arr.append(dur)
    for i in range(1, len(t_arr)):
        t_start = t_arr[i - 1]
        t_middle = t_start + (t_arr[i] - t_start) / 2.
        # fix weird behaviour when a scene is detected near end of a video
        if dur - t_start < 1.:
            break
        next_id += 1
        img_path = os.path.join(out_dir, '%05d.png' % next_id)
        p_args = ['ffmpeg', '-ss', '%.6f' % t_middle, '-i', video_path,
                  '-loglevel', 'quiet', '-nostats', '-vframes', '1', '-y', img_path]
        p_open = Popen(p_args)
        ret_code = p_open.wait()
        assert ret_code == 0, 'subprocess %s exit status != 0' % str(
            p_args)
        frames.append({
            'time': t_arr[i - 1],
            'path': img_path,
            'caption': '',
        })
    LOG.debug('get_middle operation completed')
    return frames


def predict(file_id, frames, neuraltalk_dir, out_dir):
    """Generate caption for each frame."""
    model_path = os.path.join(
        neuraltalk_dir, 'model/model_id1-501-1448236541.t7_cpu.t7')
    resf_path = os.path.join(out_dir, '{}.json'.format(file_id))
    # Remove processed frames
    for frame in frames:
        if frame['caption'] != '' and os.path.isfile(frame['path']):
            os.remove(frame['path'])
    p_args = ['th', 'eval.lua', '-model', model_path, '-num_images', '-1', '-gpuid',
              '-1', '-beam_size', '5', '-dump_images', '0', '-image_folder', out_dir]
    p_open = Popen(p_args, cwd=neuraltalk_dir, stdout=PIPE)
    # img /.../00001.png: a cat laying on top of a green field
    parser = re.compile('img ([^:]+): ([^\\n]+)')
    while True:
        line = p_open.stdout.readline().rstrip()
        if line == '':
            break
        matches = parser.match(line)
        if matches is None:
            continue
        groups = matches.groups()
        img_path = groups[0]
        txt_desc = groups[1]
        LOG.debug('Processed %s', os.path.basename(img_path))

        # Write caption to log
        for frame in frames:
            if os.path.samefile(frame['path'], img_path):
                frame['caption'] = txt_desc
        json.dump(frames, open(resf_path, 'w'), indent=4, sort_keys=True)
    LOG.debug('Written %s', resf_path)


def capgen(file_id):
    """Generate caption for file_id."""
    # init paths
    working_dir = os.path.join(DATA_DIR, file_id)
    raw_dir = os.path.join(working_dir, 'raw/')
    raw_file = os.path.join(raw_dir, os.listdir(raw_dir)[0])
    capgen_dir = os.path.join(working_dir, 'keyframes/')
    if not os.path.exists(capgen_dir):
        os.makedirs(capgen_dir)
    neuraltalk_dir = os.path.join(CUR_DIR, 'neuraltalk2')

    # generate caption
    if os.path.splitext(raw_file)[1] == '.mp4':
        t_arr = extract(raw_file)
        frames = get_middle(raw_file, t_arr, capgen_dir)
        predict(file_id, frames, neuraltalk_dir, capgen_dir)

if __name__ == '__main__':
    capgen(sys.argv[1])
