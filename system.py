"""MAGOR 938 demo system."""

import argparse
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

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s (%(name)s | %(levelname)s) : %(message)s')
LOG = logging.getLogger('system')

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
        LOG.info('Filename: %s.', self.filename)
        self.file_id = slugify(os.path.splitext(filename)[0])
        LOG.info('File ID: %s.', self.file_id)
        self.procedure_id = procedure_id
        LOG.info('Procedure: %s.', self.procedure_id)

        # set later during verify()
        self.raw_mod = None
        self.resample_mod = None
        self.diarize_mod = None
        self.transcribe_mod = None

    def verify(self):
        """Verify the procedure and modules."""
        LOG.info('Verifying procedures and modules...')

        # verify procedure
        if self.procedure_id not in PROCEDURES.keys():
            LOG.info('Procedure %s does not exist', self.procedure_id)
            return False

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
                    LOG.info('Module %s version %s: %s does not exist',
                             mod_, module['version'], exec_)
                    return False
        LOG.info("Verification completed. Setting modules...")

        # set modules
        if 'raw' in procedure.keys():
            self.raw_mod = procedure['raw']
            LOG.info('Raw module: %s', self.raw_mod)
        if 'resample' in procedure.keys():
            self.resample_mod = procedure['resample']
            LOG.info('Resample module: %s', self.resample_mod)
        if 'diarize' in procedure.keys():
            self.diarize_mod = procedure['diarize']
            LOG.info('Diarize module: %s', self.diarize_mod)
        if 'transcribe' in procedure.keys():
            self.transcribe_mod = procedure['transcribe']
            LOG.info('Transcribe module: %s', self.transcribe_mod)

        return True

    def raw(self):
        """Import a raw file."""
        try:
            exec_ = os.path.join(MODULES_DIR, self.raw_mod, 'module.py')
            args = ['python', exec_, self.filename]
            subprocess.call(args)
            LOG.info('Import completed for %s using module %s',
                     self.file_id, self.raw_mod)
        except:
            LOG.info('Error occured.', exc_info=True)

    def resample(self):
        """Resample a file using module resample."""
        try:
            exec_ = os.path.join(MODULES_DIR, self.resample_mod, 'module.py')
            args = ['python', exec_, self.file_id]
            subprocess.call(args)
            LOG.info('Resampling completed for %s using module %s',
                     self.file_id, self.resample_mod)
        except:
            LOG.info('Error occured.', exc_info=True)

    def diarize(self):
        """Diarize a file using module diarize."""
        try:
            exec_ = os.path.join(MODULES_DIR, self.diarize_mod, 'module.py')
            args = ['python', exec_, self.file_id]
            subprocess.call(args)
            LOG.info('Diarization completed for %s using module %s',
                     self.file_id, self.diarize_mod)
        except:
            LOG.info('Error occured.', exc_info=True)

    def transcribe(self):
        """Transcribe a file using module google or lvcsr."""
        try:
            exec_ = os.path.join(MODULES_DIR, self.transcribe_mod, 'module.py')
            args = ['python', exec_, self.file_id]
            subprocess.call(args)
            LOG.info('Transcription completed for %s using module %s',
                     self.file_id, self.transcribe_mod)
        except:
            LOG.info('Error occured.', exc_info=True)

    def pipeline(self):
        """Pipeline for processing."""
        if self.verify():
            if self.raw_mod is not None:
                self.raw()
            if self.resample_mod is not None:
                self.resample()
            if self.diarize_mod is not None:
                self.diarize()
            if self.transcribe_mod is not None:
                self.transcribe()
            LOG.info('Pipeline completed for %s using procedure %s',
                     self.filename, self.procedure_id)
        else:
            LOG.info('Verification failed for %s using procedure %s',
                     self.filename, self.procedure_id)


def workflow(procedure_list):
    """Processing workflow, using a procedure list."""
    for filename in os.listdir(CRAWL_DIR):
        path_ = os.path.join(CRAWL_DIR, filename)
        if os.path.isfile(path_):
            for procedure in procedure_list:
                if procedure in PROCEDURES.keys():
                    Speech(filename=filename, procedure_id=procedure).pipeline()

if __name__ == '__main__':
    ARG_PARSER = argparse.ArgumentParser()
    ARG_PARSER.add_argument('-p', '--procedures', metavar='procedure_id',
                            help='procedures to pass to workflow', nargs='*')
    ARGS = ARG_PARSER.parse_args()
    if ARGS.procedures is None:
        workflow(['google', 'lvcsr'])
    else:
        workflow(ARGS.procedures)
