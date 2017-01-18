"""MAGOR 938 demo system."""

import json
import logging
import os
import subprocess

from slugify import slugify

CUR_DIR = os.path.dirname(os.path.realpath(__file__))
MODULES_DIR = os.path.join(CUR_DIR, 'modules/')
DATA_DIR = os.path.join(CUR_DIR, 'data/')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
CRAWL_DIR = os.path.join(CUR_DIR, 'crawl/')
if not os.path.exists(CRAWL_DIR):
    os.makedirs(CRAWL_DIR)

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)


class Speech():
    """
    Speech processing tasks.
    Syntax: Speech(filename, procedure_id)
    """

    def __init__(self, filename, procedure_id):
        self.filename = filename
        self.file_id = slugify(os.path.splitext(filename)[0])
        self.procedure_id = procedure_id

    def verify(self):
        """Verify the procedure and modules."""
        manifest_file = os.path.join(CUR_DIR, 'manifest.json')
        with open(manifest_file, 'r') as file_:
            manifest = json.load(file_)

        # verify procedure
        procedures = manifest['procedures']
        if not self.procedure_id in procedures.keys():
            LOG.info('Procedure %s does not exist.', self.procedure_id)
            return False
        else:
            LOG.info('Procedure %s.', self.procedure_id)

        # verify modules
        modules = manifest['modules']
        procedure = procedures[self.procedure_id]
        for type_, mod_ in procedure.items():
            if mod_ not in modules.keys():
                LOG.info("Module %s does not exist", mod_)
                return False
            module = modules[mod_]
            if not module['type'] == type_:
                LOG.info("Type %s and module %s do not match", type_, mod_)
                return False
            execs = module['requires'] + ['module.py']
            for exec_ in execs:
                exec_path = os.path.join(MODULES_DIR, mod_, exec_)
                if not os.path.exists(exec_path):
                    LOG.info('Module %s version %s: %s does not exist.',
                             mod_, module['version'], exec_)
                    return False
                else:
                    LOG.info('Module %s version %s: %s.',
                             mod_, module['version'], exec_)

        return True

    def raw(self):
        """Import a raw file."""
        pass

    def resample(self):
        """Resample a file using module resample."""
        pass

    def diarize(self):
        """Diarize a file using module diarize."""
        pass

    def transcribe(self):
        """Transcribe a file using module google or lvcsr."""
        pass

if __name__ == '__main__':
    SP = Speech(filename='', procedure_id='googlw')
    SP.verify()
