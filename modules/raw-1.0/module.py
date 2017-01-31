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

MODULE_NAME = 'raw-1.0'
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s (%(name)s) : %(message)s')
logging.getLogger().disabled = True
LOG = logging.getLogger(MODULE_NAME)


def raw(filename):
    """Import a file inside /crawl into /data."""
    file_path = os.path.join(CRAWL_DIR, filename)
    name, ext = os.path.splitext(filename)
    if ext in AUDIO_EXTS:
        file_id = slugify(name)
        working_dir = os.path.join(DATA_DIR, file_id + '/')
        raw_dir = os.path.join(working_dir, 'raw/')
        if not os.path.exists(raw_dir):
            os.makedirs(raw_dir)
        shutil.copy2(file_path, raw_dir)
        LOG.info('Imported %s to %s', file_path, raw_dir)

if __name__ == '__main__':
    raw(sys.argv[1])
