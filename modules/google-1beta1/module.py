"""
Module: google
Version: 1beta1
Author: Nguyen Huy Anh

Requires: key.json

Transcribe a file_id into /transcript/google
"""

import json
import logging
import os
import sys
import wave
from base64 import b64encode
from decimal import Decimal
from random import randint
from time import sleep

from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from sox import Transformer

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CUR_DIR))
DATA_DIR = os.path.join(ROOT_DIR, 'data/')

logging.getLogger().disabled = True
logging.getLogger('oauth2client').setLevel(logging.ERROR)
logging.getLogger('googleapiclient').setLevel(logging.ERROR)

MODULE_NAME = 'google'
LOG_H = logging.StreamHandler()
LOG_F = logging.Formatter(
    '%(asctime)s (%(name)s | %(levelname)s) : %(message)s')
LOG_H.setFormatter(LOG_F)
LOG = logging.getLogger(MODULE_NAME)
LOG.propagate = False
LOG.addHandler(LOG_H)
LOG.setLevel(logging.DEBUG)


def seg_to_dict(diarize_file, temp_dir):
    """Parse segment file to python-friendly structure."""
    diarize_dict = dict()
    with open(diarize_file, 'r') as file_:
        segs = [seg.strip().split() for seg in file_.readlines()
                if not seg.startswith(';')]
        for seg in segs:
            speaker_gender = seg[7] + '-' + seg[4]
            start_time = Decimal(seg[2]) / 100
            end_time = (Decimal(seg[2]) + Decimal(seg[3])) / 100
            diarize_dict[int(seg[2])] = (
                speaker_gender, str(start_time), str(end_time))
    temp_seg_to_dict = os.path.join(temp_dir, 'seg_to_dict.json')
    with open(temp_seg_to_dict, 'w') as file_out:
        json.dump(diarize_dict, file_out, sort_keys=True, indent=4)
    LOG.debug('seg_to_dict operation completed')
    return diarize_dict


def dict_to_wav(diarize_dict, resample_file, temp_dir):
    """Split resampled wav file into segments based on seg_to_dict."""
    count = 1
    sorted_keys = sorted([x for x in diarize_dict.keys()])
    for key in sorted_keys:
        value = diarize_dict[key]
        diar_part_filename = '{}-{}.wav'.format(count, value[0])
        diar_part_path = os.path.join(temp_dir, diar_part_filename)
        tfm = Transformer()
        tfm.trim(Decimal(value[1]), Decimal(value[2]))
        tfm.build(resample_file, diar_part_path)
        diarize_dict[key] = (
            value[0], value[1], value[2], diar_part_path)
        count += 1
    temp_dict_to_wav = os.path.join(temp_dir, 'dict_to_wav.json')
    with open(temp_dict_to_wav, 'w') as file_out:
        json.dump(diarize_dict, file_out, sort_keys=True, indent=4)
    LOG.debug('dict_to_wav operation completed')
    return diarize_dict


def wav_to_trans(diarize_dict, speech, temp_dir, google_file):
    """Transcribe segment by segment, then write transcript to text."""
    sorted_keys = sorted([x for x in diarize_dict.keys()])
    for key in sorted_keys:
        value = diarize_dict[key]
        diar_part_path = value[3]
        with open(diar_part_path, 'rb') as file_:
            content = b64encode(file_.read()).decode('utf-8')
        request_body = {
            "audio": {
                "content": content
            },
            "config": {
                "languageCode": "en-US",
                "encoding": "LINEAR16",
                "sampleRate": 16000
            },
        }
        # exponential backoff in case it fails
        attempt = 1
        while attempt <= 5:
            try:
                sync_response = speech.syncrecognize(
                    body=request_body).execute()
                break
            except:
                sleep(2**attempt + randint(0, 1000) / 1000)
                LOG.debug('Retrying transcription for key %s', key)
                attempt += 1
        if attempt == 6:
            new_value = (value[0], value[1], value[2], '<unk>')
            LOG.debug('Failed transcription for key %s', key)
        elif 'results' not in sync_response.keys():
            new_value = (value[0], value[1], value[2], '<unk>')
            LOG.debug('Empty transcription for key %s', key)
        else:
            result_list = sync_response['results']
            trans_list = list()
            for item in result_list:
                trans = item['alternatives'][0]['transcript'].strip()
                if len(trans) == 0:
                    trans = '<unk>'
                trans_list.append(trans)
            result_str = ' '.join(trans_list)
            new_value = (value[0], value[1], value[2],
                         result_str.encode('utf-8'))
            LOG.debug('Transcription acquired for key %s', key)
        diarize_dict[key] = new_value
    temp_wav_to_trans = os.path.join(temp_dir, 'wav_to_trans.json')
    with open(temp_wav_to_trans, 'w') as file_out:
        json.dump(diarize_dict, file_out, sort_keys=True, indent=4)
    LOG.debug('wav_to_trans operation completed')

    # write text file
    with open(google_file, 'w') as file_out:
        for key in sorted_keys:
            value = diarize_dict[key]
            file_out.write(value[3].encode('utf-8') + '\n')
    LOG.debug('Written %s', google_file)
    return diarize_dict


def trans_to_tg(diarize_dict, resample_file, temp_dir, google_textgrid):
    """Produce TextGrid with speaker ids."""
    textgrid_dict = dict()
    for key in sorted(diarize_dict.keys()):
        value = diarize_dict[key]
        spk_id = value[0]
        if spk_id not in textgrid_dict.keys():
            textgrid_dict[spk_id] = [(value[1], value[2], value[3])]
        else:
            textgrid_dict[spk_id].append((value[1], value[2], value[3]))
    temp_trans_to_tg = os.path.join(temp_dir, 'trans_to_tg.json')
    with open(temp_trans_to_tg, 'w') as file_out:
        json.dump(textgrid_dict, file_out, sort_keys=True, indent=4)
    LOG.debug('trans_to_tg operation completed')
    # write textgrid
    tab4 = ' ' * 4
    tab8 = ' ' * 8
    tab12 = ' ' * 12
    file_ = wave.open(resample_file, 'r')
    duration = Decimal(file_.getnframes() / file_.getframerate())
    file_.close()
    with open(google_textgrid, 'w') as file_out:
        file_out.write('File type = "ooTextFile"\n')
        file_out.write('Object class = "TextGrid"\n\n')
        file_out.write('xmin = 0.0\n')
        file_out.write('xmax = {}\n'.format(duration))
        file_out.write('tiers? <exists>\n')
        file_out.write('size = {}\n'.format(len(textgrid_dict)))
        file_out.write('item []:\n')
        spk_count = 1
        for spk_id, segs in textgrid_dict.items():
            file_out.write(tab4 + 'item [{}]:\n'.format(spk_count))
            file_out.write(tab8 + 'class = "IntervalTier"\n')
            file_out.write(tab8 + 'name = "{}"\n'.format(spk_id))
            file_out.write(tab8 + 'xmin = {}\n'.format(segs[0][0]))
            file_out.write(tab8 + 'xmax = {}\n'.format(segs[-1][1]))
            file_out.write(tab8 + 'intervals: size = {}\n'.format(len(segs)))
            spk_count += 1
            seg_count = 1
            for seg in segs:
                file_out.write(tab8 + 'intervals [{}]\n'.format(seg_count))
                file_out.write(tab12 + 'xmin = {}\n'.format(seg[0]))
                file_out.write(tab12 + 'xmax = {}\n'.format(seg[1]))
                file_out.write(tab12 + 'text = "{}"\n'.format(seg[2]))
                seg_count += 1
    LOG.debug('Written %s', google_textgrid)


def google(file_id):
    """Transcribe a file_id using Google Cloud Speech API."""
    # init paths
    working_dir = os.path.join(DATA_DIR, file_id)
    resample_dir = os.path.join(working_dir, 'resample/')
    resample_file = os.path.join(resample_dir, '{}.wav'.format(file_id))
    diarize_dir = os.path.join(working_dir, 'diarization/')
    diarize_file = os.path.join(diarize_dir, '{}.seg'.format(file_id))
    transcribe_dir = os.path.join(working_dir, 'transcript', 'google')
    google_file = os.path.join(transcribe_dir, '{}.txt'.format(file_id))
    google_textgrid = os.path.join(
        transcribe_dir, '{}.TextGrid'.format(file_id))
    temp_dir = os.path.join(working_dir, 'temp', 'google')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    if os.path.exists(google_file) and os.path.exists(google_textgrid):
        LOG.debug('Previously transcribed %s, %s',
                  google_file, google_textgrid)
    else:
        if not os.path.exists(transcribe_dir):
            os.makedirs(transcribe_dir)

        # init google api
        json_key = os.path.join(CUR_DIR, 'key.json')
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            json_key, scopes=['https://www.googleapis.com/auth/cloud-platform'])
        speech = build('speech', 'v1beta1', credentials=credentials).speech()

        # operations
        diarize_dict = seg_to_dict(diarize_file, temp_dir)
        diarize_dict = dict_to_wav(diarize_dict, resample_file, temp_dir)
        diarize_dict = wav_to_trans(
            diarize_dict, speech, temp_dir, google_file)
        trans_to_tg(diarize_dict, resample_file, temp_dir, google_textgrid)

if __name__ == '__main__':
    google(sys.argv[1])
