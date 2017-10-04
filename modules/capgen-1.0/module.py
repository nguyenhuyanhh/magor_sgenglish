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
import shutil
import sys
import subprocess

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
    """Get the length of a video.

    Arguments:
        video_path: str - path to video file
    Returns:
        dur: float - duration of video in seconds
    """
    args = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', video_path]
    return float(subprocess.check_output(args))


def extract(video_path, temp_dir):
    """Extract scenes from a video.

    Arguments:
        video_path: str - path to video file
        temp_dir: str - path to temp directory
    Returns:
        t_arr: list - list of scene start times
    """
    # complete check using temp file
    # if completed, deserialize to t_arr; else start process
    temp_extract = os.path.join(temp_dir, 'temp_extract.json')
    if os.path.exists(temp_extract):
        with open(temp_extract, 'r') as file_:
            t_arr = json.load(file_)
        LOG.debug('extract operation previously completed')
    else:
        p_args = ['ffmpeg', '-hide_banner', '-i', video_path, '-vf',
                  "select=gte(scene\\,0.40),showinfo", '-vsync', '2',
                  '-loglevel', 'info', '-nostats', '-f', 'null', 'null', '-y']
        p_open = subprocess.Popen(p_args, stderr=subprocess.PIPE)
        expected_id = 0
        t_arr = [0.]
        # [Parsed_showinfo_1 @ 0x2842bc0] n:   0 pts: 456569 pts_time:5.07299 pos:   760122
        parser = re.compile(
            r'\[Parsed_showinfo_1 @ \w+] n: {0,3}(\d+) pts: {0,6}\d+ pts_time:(\d+.\d+|\d+) ')
        while True:
            line = p_open.stderr.readline().rstrip()
            if not line:
                break
            matches = parser.match(line)
            if not matches:
                continue
            expected_id += 1
            groups = matches.groups()
            frame_id = int(groups[0]) + 1  # shift 0-based indexing to 1-based
            start_time = float(groups[1])
            assert expected_id == frame_id, 'Missing frame id! Expected: %d, received: %d' % (
                expected_id, frame_id)
            t_arr.append(start_time)
        with open(temp_extract, 'w') as file_out:
            json.dump(t_arr, file_out, indent=4)
        LOG.debug('extract operation completed')
    return t_arr


def get_middle(video_path, video_length, t_arr, temp_dir):
    """Get keyframe (middle frame) from each scene.

    Arguments:
        video_path: str - path to video file
        video_length: float - length of video file in seconds
        t_arr: list - list of scene start times from extract()
        temp_dir: str - path to temp directory
    Returns:
        frames: dict - frames data structure
    """
    frames = dict()

    # complete check using temp file
    # if completed, deserialize to frames; else start process
    temp_get_middle = os.path.join(temp_dir, 'temp_get_middle.json')
    if os.path.exists(temp_get_middle):
        with open(temp_get_middle, 'r') as file_:
            frames = json.load(file_)
        LOG.debug('get_middle operation previously completed')
    else:
        next_id = 0
        t_arr.append(video_length)
        for i in range(1, len(t_arr)):
            t_start = t_arr[i - 1]
            t_middle = t_start + (t_arr[i] - t_start) / 2.
            # fix weird behaviour when a scene is detected near end of a video
            if video_length - t_start < 1.:
                break
            next_id += 1
            img_path = os.path.join(temp_dir, '%05d.png' % next_id)
            p_args = ['ffmpeg', '-ss', '%.6f' % t_middle, '-i', video_path,
                      '-loglevel', 'quiet', '-nostats', '-vframes', '1', '-y', img_path]
            p_open = subprocess.Popen(p_args)
            ret_code = p_open.wait()
            assert ret_code == 0, 'subprocess %s exit status != 0' % str(
                p_args)
            frames['%05d.png' % next_id] = {
                'time': t_arr[i - 1],
                'path': img_path
            }
        with open(temp_get_middle, 'w') as file_out:
            json.dump(frames, file_out, indent=4, sort_keys=True)
        LOG.debug('get_middle operation completed')
    return frames


def predict(frames, temp_dir, neuraltalk_dir):
    """Generate caption for each frame.

    Arguments:
        frames: dict - frames data structure from get_middle()
        temp_dir: str - path to temp directory
        neuraltalk_dir: str - path to neuraltalk2 library
    Returns:
        frames: dict - frames data structure
    """
    model_path = os.path.join(
        neuraltalk_dir, 'model/model_id1-501-1448236541.t7_cpu.t7')
    temp_predict = os.path.join(temp_dir, 'temp_predict.json')

    # complete check using temp file
    # if completed, deserialize to frames; else start process
    if os.path.exists(temp_predict):
        with open(temp_predict, 'r') as file_:
            frames = json.load(file_)
        LOG.debug('predict operation previously completed')
    else:
        # complete check using temp file
        count = len(frames)
        for key in frames:
            path = frames[key]['path']
            path_done = path + '.done'
            tmp = path + '.tmp'
            if os.path.exists(tmp):
                if not os.path.exists(path_done):
                    os.rename(path, path_done)
                with open(tmp, 'r') as file_:
                    frames[key]['caption'] = file_.read().strip()
                count -= 1
                LOG.debug('Previously captioned %s', key)

        # caption remaining frames
        if count > 0:
            p_args = ['th', 'eval.lua', '-model', model_path, '-num_images', '-1', '-gpuid',
                      '-1', '-beam_size', '5', '-dump_images', '0', '-image_folder', temp_dir]
            p_open = subprocess.Popen(
                p_args, cwd=neuraltalk_dir, stdout=subprocess.PIPE)
            # img /.../00001.png: a cat laying on top of a green field
            parser = re.compile(r'img ([^:]+): ([^\n]+)')
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
                tmp = img_path + '.tmp'
                with open(tmp, 'w') as file_:
                    file_.write(txt_desc)
                frames[os.path.basename(img_path)]['caption'] = txt_desc
                LOG.debug('Captioned %s', os.path.basename(img_path))

        # rename .done files to original
        for key, frame in frames.items():
            path = frame['path']
            path_done = path + '.done'
            if os.path.exists(path_done):
                os.rename(path_done, path)

        with open(temp_predict, 'w') as file_out:
            json.dump(frames, file_out, indent=4, sort_keys=True)
        LOG.debug('predict operation completed')
    return frames


def output(frames, capgen_dir, capgen_file):
    """Produce the output frames and captions.

    Arguments:
        frames: dict - frames data structure from predict()
        capgen_dir: str - path to output directory
        capgen_file: str - path to output file
    Returns:
        None
    """
    # complete check
    if os.path.exists(capgen_file) and os.path.getsize(capgen_file) > 0:
        LOG.debug('Previously written %s', capgen_file)
    else:
        # copy keyframes to folder and write output file
        for key in frames:
            path = frames[key]['path']
            new_path = os.path.join(capgen_dir, key)
            shutil.copy2(path, new_path)
            frames[key]['path'] = new_path
        with open(capgen_file, 'w') as file_out:
            json.dump(frames, file_out, indent=4, sort_keys=True)
    LOG.debug('Written %s', capgen_file)


def output_to_tg(frames, video_length, capgen_textgrid):
    """Produce the output TextGrid for visualization.

    Arguments:
        frames: dict - frames data structure from predict()
        video_length: float - length of video file
        capgen_textgrid: str - path to TextGrid file
    Returns:
        None
    """
    # complete checks
    if os.path.exists(capgen_textgrid) and os.path.getsize(capgen_textgrid) > 0:
        LOG.debug('Previously written %s', capgen_textgrid)
    else:
        tab4 = ' ' * 4
        tab8 = ' ' * 8
        tab12 = ' ' * 12
        frame = sorted(frames.keys())
        with open(capgen_textgrid, 'w') as file_out:
            file_out.write('File type = "ooTextFile"\n')
            file_out.write('Object class = "TextGrid"\n\n')
            file_out.write('xmin = 0.0\n')
            file_out.write('xmax = {}\n'.format(video_length))
            file_out.write('tiers? <exists>\n')
            file_out.write('size = 1\n')
            file_out.write('item []:\n')
            file_out.write(tab4 + 'item [1]:\n')
            file_out.write(tab8 + 'class = "IntervalTier"\n')
            file_out.write(tab8 + 'name = "C"\n')
            file_out.write(tab8 + 'xmin = 0.0\n')
            file_out.write(tab8 + 'xmax = {}\n'.format(video_length))
            file_out.write(tab8 + 'intervals: size = {}\n'.format(len(frames)))
            frame_cnt = 1
            while frame_cnt <= len(frames):
                key = frame[frame_cnt - 1]
                file_out.write(tab8 + 'intervals [{}]:\n'.format(frame_cnt))
                file_out.write(
                    tab12 + 'xmin = {}\n'.format(frames[key]['time']))
                if frame_cnt < len(frames):
                    file_out.write(
                        tab12 + 'xmax = {}\n'.format(frames[frame[frame_cnt]]['time']))
                else:
                    file_out.write(tab12 + 'xmax = {}\n'.format(video_length))
                file_out.write(
                    tab12 + 'text = "{}"\n'.format(frames[key]['caption']))
                frame_cnt += 1


def capgen(file_id):
    """Generate caption for file_id."""
    # init paths
    working_dir = os.path.join(DATA_DIR, file_id)
    convert_dir = os.path.join(working_dir, 'convert/')
    convert_file = os.path.join(convert_dir, '{}.mp4'.format(file_id))
    temp_dir = os.path.join(working_dir, 'temp/capgen')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    capgen_dir = os.path.join(working_dir, 'keyframes/')
    if not os.path.exists(capgen_dir):
        os.makedirs(capgen_dir)
    capgen_file = os.path.join(capgen_dir, '{}.json'.format(file_id))
    capgen_textgrid = os.path.join(capgen_dir, '{}.TextGrid'.format(file_id))
    neuraltalk_dir = os.path.join(CUR_DIR, 'neuraltalk2')

    # complete check
    if os.path.exists(capgen_file) and os.path.exists(capgen_textgrid):
        LOG.debug('Previously generated caption for %s', file_id)
    else:
        video_length = get_length(convert_file)
        t_arr = extract(convert_file, temp_dir)
        frames = get_middle(convert_file, video_length, t_arr, temp_dir)
        frames = predict(frames, temp_dir, neuraltalk_dir)
        output(frames, capgen_dir, capgen_file)
        output_to_tg(frames, video_length, capgen_textgrid)


if __name__ == '__main__':
    capgen(sys.argv[1])
