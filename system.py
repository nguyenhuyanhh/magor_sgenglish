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

logging.basicConfig(level=logging.INFO, format='%(asctime)s : %(message)s')
LOG = logging.getLogger(__name__)

MANIFEST_FILE = os.path.join(CUR_DIR, 'manifest.json')
with open(MANIFEST_FILE, 'r') as file_:
    MANIFEST = json.load(file_)
PROCEDURES = MANIFEST['procedures']
MODULES = MANIFEST['modules']


class Speech():
    """
    Speech processing tasks.
    Syntax: Speech(filename, procedure_id)
    """

    def __init__(self, filename, procedure_id):
        self.filename = filename
        self.file_id = slugify(os.path.splitext(filename)[0])
        self.procedure_id = procedure_id

        # set later during verify()
        self.raw_mod = None
        self.resample_mod = None
        self.diarize_mod = None
        self.transcribe_mod = None

    def verify(self):
        """Verify the procedure and modules."""
        # verify procedure
        if self.procedure_id not in PROCEDURES.keys():
            LOG.info('Procedure %s does not exist.', self.procedure_id)
            return False
        else:
            LOG.info('Procedure %s.', self.procedure_id)

        # verify modules
        procedure = PROCEDURES[self.procedure_id]
        for type_, mod_ in procedure.items():
            if mod_ not in MODULES.keys():
                LOG.info("Module %s does not exist", mod_)
                return False
            module = MODULES[mod_]
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

        # set modules
        self.raw_mod = procedure['raw']
        self.resample_mod = procedure['resample']
        self.diarize_mod = procedure['diarize']
        self.transcribe_mod = procedure['transcribe']

        return True

    def raw(self):
        """Import a raw file."""
        try:
            exec_ = os.path.join(MODULES_DIR, self.raw_mod, 'module.py')
            args = ['python', exec_, self.filename]
            subprocess.call(args)
            LOG.info('Import completed for %s using module %s',
                     self.filename, self.raw_mod)
        except:
            LOG.info('Error occured.')

    def resample(self):
        """Resample a file using module resample."""
        try:
            exec_ = os.path.join(MODULES_DIR, self.resample_mod, 'module.py')
            args = ['python', exec_, self.file_id]
            subprocess.call(args)
            LOG.info('Resampling completed for %s using module %s',
                     self.file_id, self.resample_mod)
        except:
            LOG.info('Error occured.')

    def diarize(self):
        """Diarize a file using module diarize."""
        try:
            exec_ = os.path.join(MODULES_DIR, self.diarize_mod, 'module.py')
            args = ['python', exec_, self.file_id]
            subprocess.call(args)
            LOG.info('Diarization completed for %s using module %s',
                     self.file_id, self.diarize_mod)
        except:
            LOG.info('Error occured.')

    def transcribe(self):
        """Transcribe a file using module google or lvcsr."""
        try:
            exec_ = os.path.join(MODULES_DIR, self.transcribe_mod, 'module.py')
            args = ['python', exec_, self.file_id]
            subprocess.call(args)
            LOG.info('Transcription completed for %s using module %s',
                     self.file_id, self.transcribe_mod)
        except:
            LOG.info('Error occured.')

    def pipeline(self):
        """Pipeline for processing."""
        if self.verify():
            self.raw()
            self.resample()
            self.diarize()
            self.transcribe()

if __name__ == '__main__':
    SP = Speech(filename='TRAILER_DebateIQ_Budget_2016.wav',
                procedure_id='lvcsr')
    SP.pipeline()
