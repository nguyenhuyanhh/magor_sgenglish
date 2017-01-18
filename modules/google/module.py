"""
Module: google
Version: 1.0

Transcribe a file_id into /transcript/google
"""

import json
import os
import sys
import wave
from base64 import b64encode
from time import sleep
from decimal import Decimal
from random import randint

from sox import Transformer
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CUR_DIR))
DATA_DIR = os.path.join(ROOT_DIR, 'data/')


def google(file_id):
    """Transcribe a file_id using Google Cloud Speech API."""
    # init paths
    working_dir = os.path.join(DATA_DIR, file_id)
    resample_dir = os.path.join(working_dir, 'resample/')
    diarize_dir = os.path.join(working_dir, 'diarization/')
    transcribe_dir = os.path.join(working_dir, 'transcript', 'google')
    if not os.path.exists(transcribe_dir):
        os.makedirs(transcribe_dir)
    temp_dir = os.path.join(working_dir, 'temp/')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    # init google api
    json_key = os.path.join(CUR_DIR, 'key.json')
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        json_key, scopes=['https://www.googleapis.com/auth/cloud-platform'])
    speech = build('speech', 'v1beta1', credentials=credentials).speech()

    # seg to dict
    diarize_file = os.path.join(diarize_dir, '{}.seg'.format(file_id))
    diarize_dict = dict()
    with open(diarize_file, 'r') as file_:
        line_list = file_.readlines()
        for line in line_list:
            words = line.strip().split()
            if words[0] == file_id:
                speaker_gender = words[7] + '-' + words[4]
                start_time = Decimal(words[2]) / 100
                end_time = (Decimal(words[2]) + Decimal(words[3])) / 100
                diarize_dict[int(words[2])] = (
                    speaker_gender, str(start_time), str(end_time))
    temp_seg_to_dict = os.path.join(temp_dir, 'seg_to_dict.json')
    with open(temp_seg_to_dict, 'w') as file_out:
        json.dump(diarize_dict, file_out, sort_keys=True, indent=4)

    # dict to wav
    count = 1
    sorted_keys = sorted([x for x in diarize_dict.keys()])
    resample_file = os.path.join(resample_dir, '{}.wav'.format(file_id))
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

    # wav to trans
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
                attempt += 1

        if attempt == 6:
            new_value = (value[0], value[1], value[2], '')
        elif 'results' not in sync_response.keys():
            new_value = (value[0], value[1], value[2], '')
        else:
            result_list = sync_response['results']
            trans_list = list()
            for item in result_list:
                trans_list.append(item['alternatives'][0]['transcript'])
            result_str = ' '.join(trans_list)
            new_value = (value[0], value[1], value[2],
                         result_str.encode('utf-8'))
        diarize_dict[key] = new_value
    temp_wav_to_trans = os.path.join(temp_dir, 'wav_to_trans.json')
    with open(temp_wav_to_trans, 'w') as file_out:
        json.dump(diarize_dict, file_out, sort_keys=True, indent=4)

    # write transcript
    sorted_keys = sorted([x for x in diarize_dict.keys()])
    intervals = len(diarize_dict)
    file_ = wave.open(resample_file, 'r')
    duration = Decimal(file_.getnframes() / file_.getframerate())
    file_.close()

    google_file = os.path.join(transcribe_dir, '{}.txt'.format(file_id))
    with open(google_file, 'w') as file_out:
        for key in sorted_keys:
            value = diarize_dict[key]
            file_out.write(value[3].encode('utf-8') + '\n')

    # textgrid
    google_textgrid = os.path.join(
        transcribe_dir, '{}.TextGrid'.format(file_id))
    with open(google_textgrid, 'w') as file_out:
        # header
        file_out.write('File type = "ooTextFile"\n')
        file_out.write('Object class = "TextGrid"\n\n')
        file_out.write('xmin = 0.0\nxmax = {}\n'.format(duration))
        file_out.write('tiers? <exists>\nsize = 1\nitem []:\n')
        file_out.write('    item[1]:\n        class = "IntervalTier"\n')
        file_out.write('        name = "default"\n')
        file_out.write('        xmin = 0.0\n')
        file_out.write('        xmax = {}\n'.format(duration))
        file_out.write('        intervals: size = {}\n'.format(intervals))
        # items
        count = 1
        for key in sorted_keys:
            value = diarize_dict[key]
            file_out.write('        intervals [{}]\n'.format(count))
            file_out.write('            xmin = {}\n'.format(value[1]))
            file_out.write('            xmax = {}\n'.format(value[2]))
            file_out.write('            text = "{}"\n'.format(
                value[3].encode('utf-8')))
            count += 1

if __name__ == '__main__':
    google(sys.argv[1])
