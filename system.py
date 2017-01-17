"""MAGOR 938 demo system."""

import json
import logging
import os

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
MODULES_DIR = os.path.join(CUR_DIR, 'modules/')

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)


def verify_modules():
    """Verify the modules are in place."""
    manifest_file = os.path.join(CUR_DIR, 'modules.json')
    with open(manifest_file, 'r') as file_:
        manifest = json.load(file_)
    for key, item in manifest.items():
        executable_file = os.path.join(
            MODULES_DIR, item['id'], item['requires'])
        req = "exists" if os.path.exists(executable_file) else "does not exist"
        LOG.info('Module %s version %s: %s', key, item['version'], req)

if __name__ == '__main__':
    verify_modules()
