"""
Module: vad
Version: 1.0
Author: Pham Van Tung

Requires:

Perform voice activity detection (VAD) on a multi-channel recording into /vad
"""

import logging
import math
import os
import random
import sys
from copy import deepcopy

import numpy as np
import scipy.fftpack
import scipy.interpolate
import scipy.signal
import soundfile as sf
from ffmpy import FFmpeg

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CUR_DIR))
DATA_DIR = os.path.join(ROOT_DIR, 'data/')

MODULE_NAME = 'vad'
LOG_H = logging.StreamHandler()
LOG_F = logging.Formatter(
    '%(asctime)s (%(name)s | %(levelname)s) : %(message)s')
LOG_H.setFormatter(LOG_F)
LOG = logging.getLogger(MODULE_NAME)
LOG.propagate = False
LOG.addHandler(LOG_H)
LOG.setLevel(logging.DEBUG)


class VAD(object):
    """Class representing VAD values."""

    def __init__(self):
        self.vad_flag = 0
        self.count_vadon = 0
        self.frame_idx = 0
        self.nf_ = 0
        self.slow_nf = 0
        self.speech_var = 0
        self.th_ = 0
        self.th2 = 0
        self.val = 0
        self.min_ratio_spnf = 0  # min_ratio_speech_peak_noise_floor
        self.th_offset = 0
        self.min_feature_val = 0


class Seg(object):
    """Class representing a segment."""

    def __init__(self):
        self.start = []
        self.stop = []
        self.label = []


def cal_power_sum_seg(audio, sample_rate):
    """Calculate power sum of a segment."""
    flength = int(sample_rate * 0.025)
    hsize = int(sample_rate * 0.01)
    audio_len = len(audio)

    # dither the speech signal
    for i in range(audio_len):
        audio[i] = audio[i] + np.random.randn() / (pow(2, 32))

    # DC removal
    audio = scipy.signal.lfilter(
        np.array([0.999, -0.999]), np.array([1, -0.999]), audio)

    # pre-emphasis
    tmp_audio = np.zeros(audio_len)
    for i in range(1, audio_len):
        tmp_audio[i] = audio[i] - 0.97 * audio[i - 1]
    tmp_audio[0] = audio[0]
    audio = tmp_audio

    # perform FFT
    num_frame = int(math.floor((audio_len - flength) / hsize + 1))
    spec = np.zeros((257, num_frame), dtype=np.complex)
    for i in range(num_frame):
        frame_dat = audio[i * hsize: i * hsize + flength]
        frame_dat = frame_dat * np.hamming(flength)
        result = scipy.fftpack.fft(frame_dat, 512)
        result = result[0:result.size // 2 + 1]
        spec[:, i] = result
    tmp = np.multiply(spec, np.conjugate(spec))
    power = tmp.real
    power_sum = power.sum(axis=0)

    LOG.debug('cal_power_sum_seg operation completed')
    return power_sum


def batch_peridoc_pitch_count_fast(test_wave, sample_rate, nframe,
                                   nsample_per_frame, nsample_forward):
    """Return features from audio."""
    x_start = 0
    x_end = nsample_per_frame
    act_frame_x = np.zeros((nsample_per_frame * 2, nframe))  # A matrix
    for j in range(nframe):
        tmp_arr = np.concatenate(
            [test_wave[x_start:x_end], np.zeros(x_end - x_start)])
        act_frame_x[:, j] = tmp_arr
        x_start = x_start + nsample_forward
        x_end = x_end + nsample_forward

    frame_size, nfr = act_frame_x.shape
    bin_width = sample_rate / frame_size
    hamm_frame = np.hamming(frame_size)
    hpfreq_upper = 800
    n_hpfreq_upper_bin = int(math.ceil(hpfreq_upper / bin_width))

    # frequency filtering
    map_x = list(range(1, n_hpfreq_upper_bin + 1))  # [1:n_hpfreq_upper_bin]
    map_x = 1.0 / n_hpfreq_upper_bin * np.array(map_x)  # map_x = map_x'
    frame_x = np.zeros((nsample_per_frame * 2, nframe))
    for i in range(nfr):
        tmp_norm = np.linalg.norm(act_frame_x[:, i])
        if tmp_norm == 0:
            for j in range(frame_x.shape[0]):
                frame_x[j, i] = random.random() * 0.00001
            continue
        frame_x[:, i] = act_frame_x[:, i] / np.linalg.norm(act_frame_x[:, i])
        # so that signal level is NOT at play here!!!
    frame_x_hamm = np.zeros((nsample_per_frame * 2, nframe))
    for i in range(nfr):
        frame_x_hamm[:, i] = np.multiply(frame_x[:, i], hamm_frame)
    abs_fft_x = np.absolute(np.fft.fft(
        frame_x_hamm, axis=0))  # PLEASE CHECK
    for i in range(nfr):
        abs_fft_x[:n_hpfreq_upper_bin, i] = np.multiply(
            abs_fft_x[:n_hpfreq_upper_bin, i], map_x)
    max_each_col = np.reciprocal(np.amax(
        abs_fft_x[:2 * hpfreq_upper / bin_width, :], axis=0))
    for i in range(frame_size):
        abs_fft_x[i, :] = np.multiply(abs_fft_x[i, :], max_each_col)

    # extract noise level from 2K-3K freq range
    abs_fft_x = np.power(abs_fft_x, 1.2)  # abs_fft_x = abs_fft_x.^1.2
    second_dim = abs_fft_x.shape[1]
    bin_width = (sample_rate / (math.floor(frame_size / 2) * 2))
    # pitch_range_lower = 80, pitch_range_upper = 250
    pitch_idx_range = int(math.ceil(250 - 80) / bin_width)
    val_hist_peak = np.zeros((second_dim, pitch_idx_range))
    val_hist_trough = np.zeros((second_dim, pitch_idx_range))
    sum_peak_val = np.zeros((second_dim, pitch_idx_range, 6))
    sum_trough_val = np.zeros((second_dim, pitch_idx_range, 6))
    beam_width = 2

    for i in range(pitch_idx_range):
        # pitch_range_lower = 80
        pitch_val = math.floor(((80 / bin_width) + i) * bin_width)
        # number of harmonics, skipping the first harmonics bcos very noisy!!!
        for j in range(1, 7):
            # PLEASE CHECK
            idx = int(math.floor(((j + 1) * pitch_val) / bin_width))
            idx_trough = int(math.floor(idx + (pitch_val / (2 * bin_width))))
            tmp_mat_pi = abs_fft_x[idx - beam_width - 1:idx + beam_width, :]
            p_i = tmp_mat_pi.sum(axis=0)
            tmp_mat_ti = abs_fft_x[idx_trough -
                                   beam_width - 1:idx_trough + beam_width, :]
            t_i = tmp_mat_ti.sum(axis=0)
            sum_peak_val[:, i, j - 1] = p_i
            sum_trough_val[:, i, j - 1] = t_i

    sum_peak = sum_peak_val.sum(axis=2)
    sum_trough = sum_trough_val.sum(axis=2)
    val_hist_trough = np.power(sum_trough, 2)

    for i in range(pitch_idx_range):
        curr_sum_peak_val = sum_peak_val[:, i, :].squeeze().transpose()
        curr_sum_trough_val = sum_trough_val[:,
                                             i, :].squeeze().conj().transpose()
        val_hist_peak[:, i] = np.power(sum_peak[:, i], 2) - \
            np.var(curr_sum_peak_val, axis=0, ddof=1).transpose() - \
            np.var(curr_sum_trough_val, axis=0, ddof=1).transpose()

    val_hist_peak_conj_transp = val_hist_peak.conj().transpose()
    vhp_max = val_hist_peak_conj_transp.max(0)
    vhp_argmax = val_hist_peak_conj_transp.argmax(0)
    vhp_2 = np.zeros(nfr)
    for i in range(nfr):
        vhp_2[i] = abs(val_hist_trough[i, vhp_argmax[i]])
    val_feature = np.divide(vhp_max, vhp_2)
    return val_feature


def adapt_threshold(s_old, val):
    """Adapt threshold."""
    if s_old.frame_idx <= 1:
        s_old.val = val
    s_new = VAD()
    s_new = s_old
    s_new.frame_idx = s_new.frame_idx + 1
    if s_new.frame_idx < 3:
        s_new.vad_flagc = 0
        s_new.count_vadon = 0
        if s_new.frame_idx == 1:
            s_new.nf_ = s_new.val
            s_new.slow_nf = s_new.val
        s_new.nf_ = max(s_new.nf_, s_new.val)
        s_new.slow_nf = max(s_new.slow_nf, s_new.val)
        s_new.speech_var = s_new.min_ratio_spnf * s_new.nf_ + s_new.th_offset
        s_new.th_ = s_new.slow_nf + s_new.th_offset
        s_new.th2 = s_new.slow_nf * 1.3 + s_new.th_offset
    s_new.val = val
    if s_new.frame_idx >= 3:
        s_new.speech_var = 0.8 * s_new.speech_var + 0.2 * s_new.val
        if s_new.speech_var < s_new.th2:
            s_new.speech_var = s_new.th2
        if s_new.val > s_new.th2:
            s_new.vad_flag = 1
            if s_new.val > s_new.speech_var:
                s_new.speech_var = s_new.val
        else:
            s_new.vad_flag = 0
        s_new.nf_ = 0.99 * s_new.nf_ + 0.01 * s_new.val
        s_new.slow_nf = 0.999 * s_new.slow_nf + 0.001 * s_new.val
        if s_new.val < s_new.slow_nf:
            s_new.slow_nf = s_new.val
            if s_new.slow_nf < s_new.min_feature_val:
                s_new.slow_nf = s_new.min_feature_val
        if s_new.val < s_new.nf_:
            s_new.nf_ = s_new.val
            if s_new.nf_ < s_new.min_feature_val:
                s_new.nf_ = s_new.min_feature_val
        s_new.th_ = s_new.nf_ + s_new.th_offset
        s_new.th2 = s_new.nf_ * 1.3 + s_new.th_offset

    return s_new


def combine_vad(audio, sample_rate):
    """Combine VAD values."""
    max_nsample_total = len(audio)
    frame_sztime = 0.1  # ?? msec frame Window
    # the current wisdom is to use bin Bandwidth of 10 Hz for FFT resolution
    frame_forward = 0.02  # % ?? No overlap in this example
    nsample_per_frame = int(frame_sztime * sample_rate)
    nsample_forward = int(frame_forward * sample_rate)
    nframes = int(math.floor(
        (max_nsample_total - nsample_per_frame) * 1.0 / nsample_forward))

    s_new = VAD()
    s_new.frame_idx = 0
    s_new.min_feature_val = 15
    s_new.min_ratio_spnf = 2.5
    s_new.th_offset = 10

    periodic_vad_val = batch_peridoc_pitch_count_fast(
        audio, sample_rate, nframes, nsample_per_frame, nsample_forward)
    x_start = 0
    x_end = nsample_per_frame

    energy_vad_flag = np.zeros(nframes)
    vad_flag = np.zeros(nframes)
    for j in range(nframes):
        frame_x = audio[x_start:x_end]
        energy_vad_flag[j] = np.linalg.norm(frame_x)
        s_new = adapt_threshold(s_new, periodic_vad_val[j])
        vad_flag[j] = s_new.vad_flag
        x_start = x_start + nsample_forward
        x_end = x_end + nsample_forward

    return vad_flag


def median_filter(audio, filter_len):
    """Perform a median filter on the audio."""
    nframes = len(audio)
    hlen = (filter_len - 1) / 2
    audio_copy = deepcopy(audio)
    for i in range(hlen, nframes - hlen):
        audio_copy[i] = np.median(audio[i - hlen:i + hlen + 1])
    return audio_copy


def post_process_vad(vad, buffer_len, filter_len=40):
    """Post-process VAD values."""
    vad = vad[:]

    # First filter the vad flat using a median filter
    vad_smoothed = median_filter(vad, 3)

    # Then grow any valid speech frame by 20 frames, as we think
    # anything immediately before and after the voiced frames are
    # speech.
    bool_arr = np.greater(np.convolve(
        np.ones(filter_len), vad_smoothed), 0.5)
    vad_extended = bool_arr.astype(np.double)
    vad_extended = vad_extended[filter_len / 2:]
    vad_extended = vad_extended[:len(vad_extended) - filter_len / 2 + 1]

    # We don't want to have too many segments. Sometimes, we can merge
    # several segments into one.
    filter_len = buffer_len - 40
    if filter_len > 0:
        bool_arr2 = np.greater(np.convolve(
            np.ones(filter_len), vad_extended), 0.5)
        vad_merged = bool_arr2.astype(np.double)
        vad_merged = vad_merged[filter_len / 2:]
        vad_merged = vad_merged[:len(vad_merged) - filter_len / 2 + 1]
    else:
        vad_merged = vad_extended

    return vad_merged


def label2seg(label):
    """Convert label to segment structure."""
    diff = label[1:] - label[0:len(label) - 1]
    idx_tuple = np.nonzero(diff)
    idx = idx_tuple[0]
    n_seg = len(idx)
    seg = Seg()
    if n_seg == 0:
        seg.start.append(0)
        seg.stop.append(len(label) - 1)
        seg.label.append(label[0])
        return seg
    for i in range(n_seg):
        if i == 0:
            seg.start.append(0)
        else:
            seg.start.append(idx[i - 1] + 1)
        seg.stop.append(idx[i])
        seg.label.append(label[idx[i]])
    seg.start.append(idx[-1] + 1)
    seg.stop.append(len(label) - 1)
    seg.label.append(label[-1])

    return seg


def seg2label(seg, nframes):
    """Convert segment structure to label."""
    label = np.zeros(nframes, dtype=np.int)
    n_seg = len(seg.label)
    for i in range(n_seg):
        label[seg.start[i]: seg.stop[i] + 1] = seg.label[i]
    return label


def write_seg(seg, nchans, posfix, temp_dir):
    """Write segment info to temp files."""
    n_seg = len(seg.label)
    seg_info = [[] for _ in range(nchans)]
    for i in range(n_seg):
        if seg.label[i] > 0:
            label = 'chan{} {} {} 1'.format(
                seg.label[i], seg.start[i] * 0.01, seg.stop[i] * 0.01)
            seg_info[seg.label[i] - 1].append(label)

    for i in range(nchans):
        temp_file = os.path.join(
            temp_dir, 'segment_chan{}_{}.txt'.format(i + 1, posfix))
        with open(temp_file, 'w') as file_:
            for j in range(len(seg_info[i])):
                file_.write(seg_info[i][j] + '\n')


def gen_final_vad(audio, sample_rate, postfix, nchannels, temp_dir):
    """Generate final VAD and store in temp folder."""
    power_sum = np.empty((0, 0), dtype=np.double)
    nframes = -1
    for i in range(len(audio)):
        curr_power_sum = cal_power_sum_seg(audio[i, :], sample_rate)
        if i == 0:
            power_sum = np.empty((0, len(curr_power_sum)), dtype=np.double)
            nframes = len(curr_power_sum)
        power_sum = np.vstack([power_sum, curr_power_sum])

    sum_all = np.sum(power_sum, axis=0)
    power_sum_norm = np.zeros(power_sum.shape)
    for i in range(nframes):
        power_sum_norm[:i] = np.divide(power_sum[:i], sum_all)
    for i in range(len(audio)):
        temp_file = os.path.join(
            temp_dir, 'power_sum_{}_chan_{}.txt'.format(postfix, i + 1))
        np.savetxt(temp_file, power_sum_norm[i, :], fmt='%.3f')
    LOG.debug('Finish normalising energy')

    channels = np.argmax(power_sum_norm, axis=0)
    for i in range(len(channels)):
        channels[i] = channels[i] + 1
    np.savetxt(os.path.join(
        temp_dir, 'vad_energy_raw_{}.txt'.format(postfix)), channels, fmt='%d')
    channels_smooth = median_filter(channels, 51)
    np.savetxt(os.path.join(temp_dir, 'vad_energy_{}.txt'.format(
        postfix)), channels_smooth, fmt='%d')

    pitch_vad = np.empty((0, 0), dtype=np.int)
    for i in range(nchannels):
        comb_vad_flag = combine_vad(audio[i, :], sample_rate)
        curr_vad = comb_vad_flag
        idx_arr = np.zeros(len(curr_vad), dtype=np.int)
        for j in range(len(curr_vad)):
            idx_arr[j] = j * 2
        func = scipy.interpolate.interp1d(
            idx_arr, curr_vad, kind='nearest', fill_value='extrapolate')
        new_arr_idx = list(range(2 * len(curr_vad)))
        curr_vad = func(new_arr_idx)
        curr_vad_post = post_process_vad(curr_vad, 20)
        if i == 0:
            pitch_vad = np.empty((0, len(curr_vad_post)), dtype=np.int)
        pitch_vad = np.vstack([pitch_vad, curr_vad_post])

    for i in range(pitch_vad.shape[0]):
        temp_file = os.path.join(
            temp_dir, 'vad_pitch_{}_channel{}.txt'.format(postfix, i + 1))
        np.savetxt(temp_file, pitch_vad[i, :], fmt='%d')

    spk_id_seg = label2seg(channels_smooth)
    spk_id_seg_refined = deepcopy(spk_id_seg)
    for i in range(len(spk_id_seg.label)):
        curr_start = spk_id_seg.start[i]
        curr_stop = spk_id_seg.stop[i]
        curr_spk = spk_id_seg.label[i]
        curr_pitch_vad = pitch_vad[curr_spk - 1,
                                   curr_start: min(pitch_vad.shape[1], curr_stop + 1)]
        if not curr_pitch_vad.shape[0]:  # len(curr_pitch_vad) == 0
            continue
        if np.median(curr_pitch_vad) == 0:
            spk_id_seg_refined.label[i] = 0
    write_seg(spk_id_seg_refined, len(audio), postfix, temp_dir)
    spk_id_smooth_refined = seg2label(spk_id_seg_refined, nframes)
    np.savetxt(os.path.join(temp_dir, 'vad_refined_{}.txt'.format(
        postfix)), spk_id_smooth_refined, fmt='%d')
    LOG.debug('Finish processing segment %s', postfix)

    return spk_id_smooth_refined


def modify_signal(tmp_audio, spk_id_smooth_refined, hsize, flength):
    """Modify the audio signal."""
    LOG.debug('Modifying the signal...')
    audio = deepcopy(tmp_audio)
    nsample = len(tmp_audio[0, :])

    if audio.shape[0] == 0 or audio.shape[1] == 0:
        LOG.debug('Wrong audio shape: %s,%s', audio.shape[0], audio.shape[1])
    spk_id_smooth_refined_len = len(spk_id_smooth_refined)
    for j in range(spk_id_smooth_refined_len):
        active_channel = spk_id_smooth_refined[j]
        start_frame = j * hsize
        end_frame = min(start_frame + flength, nsample)

        for i in range(len(tmp_audio)):
            if i != active_channel - 1:
                for k in range(start_frame, end_frame):
                    if abs(audio[i, k]) == 0:
                        continue
                    audio[i, k] = audio[i, k] * \
                        random.random() / (abs(audio[i, k]) * 10000000000)
    return audio


def combine_segment(channel_id, nsamples, nsegs, tolerance, discard_short_seg,
                    length_per_seg, diarize_file, temp_dir):
    """Write segments into diarization file."""
    curr_start = 0
    curr_end = 0
    curr_seg = 0
    with open(diarize_file, 'w') as file_:
        full_sample_based_vad = np.zeros(nsamples, dtype=np.double)
        for i in range(nsegs):
            temp_file = os.path.join(
                temp_dir, 'segment_chan{}_seg{}.txt'.format(channel_id, i + 1))
            with open(temp_file) as tmp:
                lines = [x.strip() for x in tmp.readlines()]
            for line in lines:
                aseg = line.split(' ')
                start = float(aseg[1]) + length_per_seg * i
                end = float(aseg[2]) + length_per_seg * i
                is_speech = aseg[3]
                if is_speech == '1':  # Only care if aseg is a speech segment
                    if curr_seg == 0:
                        # Already finish the process of merging close segments
                        # Now starting a new segment
                        curr_seg = 1
                        curr_end = end
                        curr_start = start
                    elif start - curr_end <= tolerance:
                        # In the process of merging close segments
                        # The segment aseg can be merged into the current segment
                        curr_end = end
                    elif (curr_end - curr_start) >= discard_short_seg:
                        # The segment aseg is too far from the current segment
                        # Write down the current segment and start new segment
                        LOG.debug('Speech %s,%s', curr_start, curr_end)
                        label = 'channel{} 1 {} {} U S U S{}'.format(channel_id, int(
                            curr_start * 100), int((curr_end - curr_start) * 100), channel_id)
                        file_.write(label + '\n')
                        start_samp = int(curr_start * 100 * 160)
                        end_samp = int(min(curr_end * 100 * 160, nsamples))
                        for k in range(start_samp, end_samp):
                            full_sample_based_vad[k] = 0.5 + random.random()
                        curr_start = start
                        curr_end = end
                        curr_seg = 1
                    else:
                        # Segment is too short
                        curr_start = start
                        curr_end = end
                        curr_seg = 1
    LOG.debug('Written %s', diarize_file)
    np.savetxt(os.path.join(temp_dir, 'final_sample_vad_chan{}'.format(
        channel_id)), full_sample_based_vad, fmt='%.5f')


def crosstalk_remover(file_id):
    """Remove crosstalk from multi-channel inputs."""
    # init paths
    working_dir = os.path.join(DATA_DIR, file_id)
    resample_dir = os.path.join(working_dir, 'resample/')
    resample_files = sorted(os.listdir(resample_dir))
    vad_dir = os.path.join(working_dir, 'vad/')
    if not os.path.exists(vad_dir):
        os.makedirs(vad_dir)
    diarize_dir = os.path.join(working_dir, 'diarization')
    if not os.path.exists(diarize_dir):
        os.makedirs(diarize_dir)
    temp_dir = os.path.join(working_dir, 'temp/vad')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    # define constants
    tolerance = 0.5  # Merge 2 speech segments that have their gap smaller than this tolerance
    discard_short_seg = 0.5  # Ignore speech segment that smaller than this value
    audio_dat, sample_rate = sf.read(
        os.path.join(resample_dir, resample_files[0]))
    nsample = len(audio_dat)
    LOG.debug('Number of samples: %s', nsample)
    nframe_per_seg = 20000
    flength = int(sample_rate * 0.025)
    hsize = int(sample_rate * 0.01)
    nsample_per_seg = (nframe_per_seg - 1) * hsize + flength
    LOG.debug('Number of samples per segment: %s', nsample_per_seg)

    # load all inputs into array
    audio = np.empty((0, nsample), dtype=np.double)
    for file_ in resample_files:
        audio_dat, sample_rate = sf.read(os.path.join(resample_dir, file_))
        audio = np.vstack([audio, audio_dat])

    # perform operations
    sample_start_frame = 0
    sample_end_frame = min(nsample, sample_start_frame + nsample_per_seg)
    seg_count = 1
    while sample_start_frame < nsample:
        LOG.debug('Segment %s, start sample = %s, end sample = %s',
                  seg_count, sample_start_frame, sample_end_frame)
        curr_seg_audio = audio[:, sample_start_frame:sample_end_frame]
        spk_id_smooth_refined = gen_final_vad(
            curr_seg_audio, sample_rate, 'seg' + str(seg_count), len(resample_files), temp_dir)
        seg_count = seg_count + 1
        audio[:, sample_start_frame:sample_end_frame] = modify_signal(
            audio[:, sample_start_frame:sample_end_frame], spk_id_smooth_refined, hsize, flength)
        sample_start_frame = sample_start_frame + nsample_per_seg
        sample_end_frame = min(nsample, sample_end_frame + nsample_per_seg)

    # write output files
    i = 0
    out_files = list()
    for file_ in resample_files:
        out_file = os.path.join(vad_dir, file_)
        out_files.append(out_file)
        sf.write(out_file, audio[i, :], sample_rate)
        LOG.debug('Written %s', out_file)
        i += 1

    # join output files
    inputs = {k: None for k in out_files}
    o_file = os.path.join(vad_dir, '{}.wav'.format(file_id))
    outputs = {o_file: '-filter_complex amerge -ac 1'}
    fnull = open(os.devnull)
    FFmpeg(inputs=inputs, outputs=outputs).run(stdout=fnull, stderr=fnull)
    LOG.debug('Written %s', o_file)

    # write segment files
    i = 1
    for file_ in resample_files:
        diarize_file = os.path.join(
            diarize_dir, '{}.seg'.format(os.path.splitext(file_)[0]))
        combine_segment(i, nsample, seg_count - 1, tolerance,
                        discard_short_seg, nframe_per_seg * 0.01, diarize_file, temp_dir)
        i += 1


if __name__ == '__main__':
    crosstalk_remover(sys.argv[1])
