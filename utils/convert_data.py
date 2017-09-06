"""
Convert /data between different versions of magor_sgenglish.

This is updated whenever there are breaking changes to the /data structure due to a new version.
"""

import os

UTILS_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(UTILS_DIR)
DATA_DIR = os.path.join(ROOT_DIR, 'data')


def to_34():
    """Convert data structures from version >= 0.8 to version 0.34.

    Change the temp/google format.
    """
    for file_id in os.listdir(DATA_DIR):
        # init paths
        working_dir = os.path.join(DATA_DIR, file_id)
        temp_dir = os.path.join(working_dir, 'temp', 'google')

        # detect old data structures
        if os.path.exists(temp_dir):
            temp_seg_to_dict = os.path.join(temp_dir, 'seg_to_dict.json')
            if os.path.exists(temp_seg_to_dict):
                # old data structure found!
                print 'Converting {}'.format(file_id)
                temp_id = file_id[:8] + '0'
                for temp_file in os.listdir(temp_dir):
                    old_path = os.path.join(temp_dir, temp_file)
                    new_path = os.path.join(
                        temp_dir, '{}_{}'.format(temp_id, temp_file))
                    os.rename(old_path, new_path)


if __name__ == '__main__':
    to_34()
