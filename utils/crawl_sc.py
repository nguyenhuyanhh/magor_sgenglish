"""
Crawl curated playlist into /crawl
Mainly to support 938 data collection from soundcloud

Requires scdl to be installed. To install, run
    sudo pip3 install scdl
"""

import os
import shutil
import subprocess
import sys

UTILS_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(UTILS_DIR)
CRAWL_DIR = os.path.join(ROOT_DIR, 'crawl')
MONTHS = {1: 'jan', 2: 'feb', 3: 'mar', 4: 'apr', 5: 'may', 6: 'jun',
          7: 'jul', 8: 'aug', 9: 'sep', 10: 'oct', 11: 'nov', 12: 'dec'}


def crawl(year, month):
    """Crawl the curated playlist for that year/ month."""
    # crawl
    mth = ''
    for key, value in MONTHS.items():
        if key == int(month):
            mth = value
            break
    addr = 'https://soundcloud.com/nguyen-huy-anh/sets/{}-{}'.format(
        mth, year)
    args = ['scdl', '-l', addr, '--onlymp3', '--path', CRAWL_DIR]
    subprocess.call(args)

    # move to correct folder
    old_dir = os.path.join(CRAWL_DIR, '{} {}'.format(mth.title(), year))
    for file_ in os.listdir(old_dir):
        old_path = os.path.join(old_dir, file_)
        shutil.move(old_path, CRAWL_DIR)
    shutil.rmtree(old_dir, ignore_errors=True)


if __name__ == '__main__':
    crawl(sys.argv[1], sys.argv[2])
