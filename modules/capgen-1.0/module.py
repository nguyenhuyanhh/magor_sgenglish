"""
Module: capgen
Version: 1.0
Author: Peter
Modified by: Nguyen Huy Anh

Requires: model/, neuraltalk2/

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


class CaptionGenerator:
    """
    Caption generator for a video.
    Syntax: CaptionGenerator()
    """

    def __init__(self, model_path):
        self.model_path = model_path
        self.neuraltalk2_dir = os.path.join(CUR_DIR, 'neuraltalk2')
        self.eval_path = os.path.join(self.neuraltalk2_dir, 'eval.lua')
        # [Parsed_showinfo_1 @ 0x2842bc0] n:   0 pts: 456569 pts_time:5.07299 pos:   760122
        self.parser = re.compile(
            '\\[Parsed_showinfo_1 @ \\w+] n: {0,3}(\\d+) pts: {0,6}\\d+ pts_time:(\\d+\\.\\d+|\\d+) ')
        # img /mnt/c/Users/Peter/OneDrive/FinalYearProject/temp2/00001.png: a
        # cat laying on top of a green field
        self.parser2 = re.compile('img ([^:]+): ([^\\n]+)')

    def convert(self, video_path, dump_dir, converted_vidname):
        conv_vid_path = os.path.join(dump_dir, converted_vidname + '.mp4')
        p_args = ['ffmpeg', '-hide_banner', '-i', video_path,
                  conv_vid_path, '-nostats', '-loglevel', '0']
        p_open = Popen(p_args)
        _ = p_open.wait()
        return conv_vid_path

    def extract(self, video_path):
        p_args = ['ffmpeg', '-hide_banner', '-i', video_path, '-vf',
                  "select=gte(scene\\,0.40),showinfo", '-vsync', '2',
                  '-loglevel', 'info', '-nostats', '-f', 'null', 'null', '-y']
        p_open = Popen(p_args, stderr=PIPE)
        expected_id = 0
        result = [0.]
        while True:
            line = p_open.stderr.readline().rstrip()
            if line == '':
                break
            matches = self.parser.match(line)
            if matches is None:
                continue
            expected_id += 1
            groups = matches.groups()
            # Shift 0-based indexing to 1-based
            frame_id = int(groups[0]) + 1
            start_time = float(groups[1])
            assert expected_id == frame_id, 'Missing frame id! Expected: %d, received: %d' % (
                expected_id, frame_id)
            result.append(start_time)
        return result

    def get_length(self, video_path):
        p_args = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                  '-of', 'default=noprint_wrappers=1:nokey=1', video_path]
        p_open = Popen(p_args, stdout=PIPE)
        dur_str = p_open.stdout.readline()
        dur = float(dur_str)
        return dur

    def get_middle(self, video_path, dump_dir, t_arr):
        frames = []
        dur = self.get_length(video_path)
        next_id = 0
        t_arr.append(dur)
        for i in range(1, len(t_arr)):
            t_start = t_arr[i - 1]
            t_middle = t_start + (t_arr[i] - t_start) / 2.
            # fix weird behaviour when a scene is detected near end of a video
            if dur - t_start < 1.:
                break
            next_id += 1
            img_path = os.path.join(dump_dir, '%05d.png' % next_id)
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
        return frames

    def predict(self, dump_dir, frames):
        # I am sorry this has to be done
        dump_dir = os.path.abspath(dump_dir)
        model_path = os.path.abspath(self.model_path)
        resf_path = os.path.join(dump_dir, 'result.json')
        # Remove processed frames
        for frame in frames:
            if frame['caption'] != '' and os.path.isfile(frame['path']):
                os.remove(frame['path'])
        p_args = ['th', 'eval.lua', '-model', model_path, '-num_images', '-1', '-gpuid',
                  '-1', '-beam_size', '5', '-dump_images', '0', '-image_folder', dump_dir]
        # (Important) It is assumed that ./neuraltalk2 is already there!
        p_open = Popen(p_args, cwd=self.neuraltalk2_dir, stdout=PIPE)

        while True:
            line = p_open.stdout.readline().rstrip()
            if line == '':
                break
            matches = self.parser2.match(line)
            if matches is None:
                continue
            groups = matches.groups()
            img_path = groups[0]
            txt_desc = groups[1]
            print img_path

            # Write caption to log
            for frame in frames:
                if os.path.samefile(frame['path'], img_path):
                    frame['caption'] = txt_desc
            json.dump(frames, open(resf_path, 'w'), indent=4, sort_keys=True)

        return resf_path

    def process(self, video_path, dump_dir, converted_vidname='converted', convert_to_mp4=False):
        # Create the dump directory recursively beforehand
        try:
            os.makedirs(dump_dir)
        except OSError:
            if not os.path.isdir(dump_dir):
                raise
        resf_path = os.path.join(dump_dir, 'result.json')
        if os.path.isfile(resf_path):
            frames = json.load(open(resf_path))
            return self.predict(dump_dir, frames)

        # Else
        _, ext = os.path.splitext(video_path)
        if convert_to_mp4 and ext != '.mp4':
            video_path = self.convert(video_path, dump_dir, converted_vidname)
        t_arr = self.extract(video_path)
        # Get middle frame from each scene
        frames = self.get_middle(video_path, dump_dir, t_arr)
        # Predict caption
        return self.predict(dump_dir, frames)


def capgen(file_id):
    """Generate caption for file_id."""
    working_dir = os.path.join(DATA_DIR, file_id)
    raw_dir = os.path.join(working_dir, 'raw/')
    raw_file = os.path.join(raw_dir, os.listdir(raw_dir)[0])
    capgen_dir = os.path.join(working_dir, 'keyframes/')
    model_path = os.path.join(
        CUR_DIR, 'model/model_id1-501-1448236541.t7_cpu.t7')
    cap_gen = CaptionGenerator(model_path)
    if os.path.splitext(raw_file)[1] == '.mp4':
        _ = cap_gen.process(raw_file, capgen_dir, convert_to_mp4=True)

if __name__ == '__main__':
    capgen(sys.argv[1])
