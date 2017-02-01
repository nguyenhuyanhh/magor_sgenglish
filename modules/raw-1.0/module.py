"""
Module: raw
Version: 1.0
Author: Nguyen Huy Anh

Requires:

Import raw files into /data
"""

import logging
import os
import shutil
import sys

from slugify import slugify

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CUR_DIR))
DATA_DIR = os.path.join(ROOT_DIR, 'data/')
CRAWL_DIR = os.path.join(ROOT_DIR, 'crawl/')
AUDIO_EXTS = ['.wav', '.mp3']

MODULE_NAME = 'raw'
LOG_H = logging.StreamHandler()
LOG_F = logging.Formatter(
    '%(asctime)s (%(name)s | %(levelname)s) : %(message)s')
LOG_H.setFormatter(LOG_F)
LOG = logging.getLogger(MODULE_NAME)
LOG.propagate = False
LOG.addHandler(LOG_H)
LOG.setLevel(logging.DEBUG)


def raw(filename):
    """Import a file inside /crawl into /data."""
    file_path = os.path.join(CRAWL_DIR, filename)
    name, ext = os.path.splitext(filename)
    if ext in AUDIO_EXTS:
        file_id = slugify(name)
        working_dir = os.path.join(DATA_DIR, file_id + '/')
        raw_dir = os.path.join(working_dir, 'raw/')
        raw_file = os.path.join(raw_dir, filename)
        if os.path.exists(raw_file):
            LOG.debug('Previously imported to %s', raw_file)
        else:
            if not os.path.exists(raw_dir):
                os.makedirs(raw_dir)
            shutil.copy2(file_path, raw_dir)
            LOG.debug('Imported %s to %s', file_path, raw_dir)

if __name__ == '__main__':
    raw(sys.argv[1])
