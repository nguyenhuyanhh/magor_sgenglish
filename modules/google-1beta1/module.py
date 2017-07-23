"""
Module: google
Version: 1beta1
Author: Nguyen Huy Anh

Requires: key.json

Transcribe a file_id into /transcript/google
"""

import io
import json
import logging
import os
import sys
import wave
from decimal import Decimal
from random import randint
from time import sleep

from ffmpy import FFmpeg
from google.cloud import speech
from google.cloud.speech import enums, types

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CUR_DIR))
DATA_DIR = os.path.join(ROOT_DIR, 'data/')

# silent google loggers
logging.getLogger('google.auth').setLevel(logging.ERROR)

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

    # complete check using temp file
    # if completed, deserialize to diarize_dict; else start process
    temp_seg_to_dict = os.path.join(temp_dir, 'seg_to_dict.json')
    if os.path.exists(temp_seg_to_dict):
        with open(temp_seg_to_dict, 'r') as file_:
            tmp = json.load(file_)
            diarize_dict = {int(k): v for k, v in tmp.items()}
        LOG.debug('seg_to_dict operation previously completed')
    else:
        with open(diarize_file, 'r') as file_:
            segs = [seg.strip().split() for seg in file_.readlines()
                    if not seg.startswith(';')]
            for seg in segs:
                speaker_gender = seg[7] + '-' + seg[4]
                start_time = Decimal(seg[2]) / 100
                end_time = (Decimal(seg[2]) + Decimal(seg[3])) / 100
                diarize_dict[int(seg[2])] = [speaker_gender,
                                             str(start_time), str(end_time)]
        with open(temp_seg_to_dict, 'w') as file_out:
            json.dump(diarize_dict, file_out, sort_keys=True, indent=4)
        LOG.debug('seg_to_dict operation completed')
    return diarize_dict


def dict_to_wav(diarize_dict, resample_file, temp_dir):
    """Split resampled wav file into segments based on seg_to_dict."""
    # complete check using temp file
    # if completed, deserialize to diarize_dict; else start process
    temp_dict_to_wav = os.path.join(temp_dir, 'dict_to_wav.json')
    if os.path.exists(temp_dict_to_wav):
        with open(temp_dict_to_wav, 'r') as file_:
            tmp = json.load(file_)
            diarize_dict = {int(k): v for k, v in tmp.items()}
        LOG.debug('dict_to_wav operation previously completed')
    else:
        count = 1
        sorted_keys = sorted([x for x in diarize_dict.keys()])
        for key in sorted_keys:
            value = diarize_dict[key]
            diar_part_file = os.path.join(
                temp_dir, '{}-{}.wav'.format(count, value[0]))
            part_dur = Decimal(value[2]) - Decimal(value[1])
            inputs = {
                resample_file: '-ss {} -t {}'.format(value[1], str(part_dur))}
            outputs = {diar_part_file: None}
            fnull = open(os.devnull, 'w')
            FFmpeg(inputs=inputs, outputs=outputs).run(
                stdout=fnull, stderr=fnull)
            diarize_dict[key] = value + [diar_part_file]
            count += 1
        with open(temp_dict_to_wav, 'w') as file_out:
            json.dump(diarize_dict, file_out, sort_keys=True, indent=4)
        LOG.debug('dict_to_wav operation completed')
    return diarize_dict


def wav_to_trans(diarize_dict, speech_client, temp_dir):
    """Transcribe segment by segment."""
    # complete check using temp file
    # if completed, deserialize to diarize_dict; else start process
    temp_wav_to_trans = os.path.join(temp_dir, 'wav_to_trans.json')
    if os.path.exists(temp_wav_to_trans):
        with open(temp_wav_to_trans, 'r') as file_:
            tmp = json.load(file_)
            diarize_dict = {int(k): v for k, v in tmp.items()}
        LOG.debug('wav_to_trans operation previously completed')
    else:
        sorted_keys = sorted([x for x in diarize_dict.keys()])
        for key in sorted_keys:
            value = diarize_dict[key]
            tmp = os.path.join(temp_dir, str(key))

            # complete check using temp file
            if os.path.exists(tmp):
                with open(tmp, 'r') as file_:
                    diarize_dict[key] = value + [file_.read().strip()]
                LOG.debug('Transcription previously acquired for key %s', key)
            else:
                with io.open(value[3], 'rb') as file_:
                    content = file_.read()
                audio = types.RecognitionAudio(content=content)
                config = types.RecognitionConfig(
                    encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=16000,
                    language_code='en-US')

                # exponential backoff in case it fails
                attempt = 1
                while attempt <= 5:
                    try:
                        res = speech_client.recognize(config, audio)
                        break
                    except BaseException:
                        sleep(2**attempt + randint(0, 1000) / 1000)
                        LOG.debug('Retrying transcription for key %s', key)
                        attempt += 1

                # process and write results
                if attempt == 6:
                    # fail all attempts
                    new_value = value + ['<unk>']
                    trans = '<unk>'
                    LOG.debug('Failed transcription for key %s', key)
                elif not res.results:
                    # empty transcription
                    new_value = value + ['<unk>']
                    trans = '<unk>'
                    LOG.debug('Empty transcription for key %s', key)
                else:
                    # get transcription
                    result_list = [x.alternatives[0].transcript.strip()
                                   for x in res.results]
                    result_str = ' '.join(result_list)
                    new_value = value + [result_str.encode('utf-8')]
                    trans = result_str.encode('utf-8')
                    LOG.debug('Transcription acquired for key %s', key)
                diarize_dict[key] = new_value
                with open(tmp, 'w') as file_:
                    file_.write(trans)

        with open(temp_wav_to_trans, 'w') as file_out:
            json.dump(diarize_dict, file_out, sort_keys=True, indent=4)
        LOG.debug('wav_to_trans operation completed')
    return diarize_dict


def trans_to_tg(diarize_dict, resample_file, temp_dir, google_file, google_textgrid):
    """Produce text transcript and TextGrid with speaker ids."""
    # complete check for google_file
    if os.path.exists(google_file):
        LOG.debug('Previously written %s', google_file)
    else:
        with open(google_file, 'w') as file_out:
            for key in sorted(diarize_dict):
                file_out.write(diarize_dict[key][4].encode('utf-8') + '\n')
        LOG.debug('Written %s', google_file)

    # complete check for google_textgrid
    if os.path.exists(google_textgrid):
        LOG.debug('Previously written %s', google_textgrid)
    else:
        textgrid_dict = dict()
        for key in sorted(diarize_dict.keys()):
            value = diarize_dict[key]
            spk_id = value[0]
            if spk_id not in textgrid_dict.keys():
                textgrid_dict[spk_id] = [(value[1], value[2], value[4])]
            else:
                textgrid_dict[spk_id].append((value[1], value[2], value[4]))
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
                file_out.write(
                    tab8 + 'intervals: size = {}\n'.format(len(segs)))
                spk_count += 1
                seg_count = 1
                for seg in segs:
                    file_out.write(
                        tab8 + 'intervals [{}]:\n'.format(seg_count))
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

    # complete check
    if os.path.exists(google_file) and os.path.exists(google_textgrid):
        LOG.debug('Previously transcribed %s, %s',
                  google_file, google_textgrid)
    else:
        if not os.path.exists(transcribe_dir):
            os.makedirs(transcribe_dir)

        # init google api
        json_key = os.path.join(CUR_DIR, 'key.json')
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = json_key
        client = speech.SpeechClient()

        # operations
        diarize_dict = seg_to_dict(diarize_file, temp_dir)
        diarize_dict = dict_to_wav(diarize_dict, resample_file, temp_dir)
        diarize_dict = wav_to_trans(diarize_dict, client, temp_dir)
        trans_to_tg(diarize_dict, resample_file, temp_dir,
                    google_file, google_textgrid)


if __name__ == '__main__':
    google(sys.argv[1])
