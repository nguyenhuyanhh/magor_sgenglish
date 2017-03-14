"""Convert ctm transcripts to TextGrid, keeping speaker ids."""

import sys
from decimal import Decimal


def parse_ctm_seg(ctm_file, seg_file):
    """Parse ctm and segment files to python-friendly structures."""
    result = dict()
    segments = dict()
    with open(seg_file, 'r') as seg_:
        segs = [seg.strip().split() for seg in seg_.readlines()
                if not seg.startswith(';')]
        for seg in segs:
            spk_id = seg[7] + '-' + seg[4]
            str_time = Decimal(seg[2]) / 100
            end_time = str_time + Decimal(seg[3]) / 100
            str_end = (str_time, end_time)
            if spk_id not in result.keys():
                result[spk_id] = [str_end]
            else:
                result[spk_id].append(str_end)
            segments[str_end] = list()
    with open(ctm_file, 'r') as ctm_:
        ctms = [ctm.strip().split() for ctm in ctm_.readlines()]
        for ctm in ctms:
            for str_end, sentence in segments.items():
                str_time = Decimal(ctm[2])
                end_time = str_time + Decimal(ctm[3])
                if str_time >= str_end[0] and end_time <= str_end[1]:
                    sentence.append(ctm[4])  # ctm already sorted
    for str_end, sentence in segments.items():
        new_sent = ' '.join(sentence)
        segments[str_end] = new_sent
    end_file = sorted(segments.keys(), reverse=True)[0][1]
    for spk_id, str_ends in result.items():
        temp = list()
        spk_str = end_file
        spk_end = Decimal(0)
        for str_end in str_ends:
            for key, value in segments.items():
                if key == str_end:
                    if key[0] < spk_str:
                        spk_str = key[0]
                    if key[1] > spk_end:
                        spk_end = key[1]
                    temp.append({key: value})
        temp.append((spk_str, spk_end))
        result[spk_id] = temp
    print result
    print end_file
    return result, end_file


def ctm_2_trans(ctm_file, seg_file, textgrid_file):
    """Take the parsed ctm and segment files, produce corresponding TextGrid."""
    tab4 = ' ' * 4
    tab8 = ' ' * 8
    tab12 = ' ' * 12
    parsed, end_file = parse_ctm_seg(ctm_file, seg_file)

    with open(textgrid_file, 'w') as txt_:
        # header
        txt_.write('File type = "ooTextFile"\n')
        txt_.write('Object class = "TextGrid"\n')
        txt_.write('\n')
        txt_.write('xmin = 0.0\n')
        txt_.write('xmax = {}\n'.format(end_file))
        txt_.write('tiers? <exists>\n')
        txt_.write('size = {}\n'.format(len(parsed)))
        txt_.write('item []:\n')

        spk_count = 1
        for spk_id, segs in parsed.items():
            txt_.write(tab4 + 'item [{}]:\n'.format(spk_count))
            spk_count += 1
            txt_.write(tab8 + 'class = "IntervalTier"\n')
            txt_.write(tab8 + 'name = "{}"\n'.format(spk_id))
            txt_.write(tab8 + 'xmin = {}\n'.format(segs[len(segs) - 1][0]))
            txt_.write(tab8 + 'xmax = {}\n'.format(segs[len(segs) - 1][1]))
            txt_.write(tab8 + 'intervals: size = {}\n'.format(len(segs) - 1))
            seg_count = 1
            while seg_count < len(segs):
                txt_.write(tab8 + 'intervals [{}]\n'.format(seg_count))
                txt_.write(
                    tab12 + 'xmin = {}\n'.format(segs[seg_count - 1].keys()[0][0]))
                txt_.write(
                    tab12 + 'xmax = {}\n'.format(segs[seg_count - 1].keys()[0][1]))
                txt_.write(
                    tab12 + 'text = "{}"\n'.format(segs[seg_count - 1].values()[0]))
                seg_count += 1


if __name__ == "__main__":
    ctm_2_trans(sys.argv[1], sys.argv[2], sys.argv[3])
