"""Core system for magor_sgenglish."""

import argparse
import json
import logging
import os
import shutil
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

# load manifest
MANIFEST_FILE = os.path.join(CUR_DIR, 'manifest.json')
with open(MANIFEST_FILE, 'r') as file_:
    MANIFEST = json.load(file_)
PROCEDURES = MANIFEST['procedures']
FILE_TYPES = MANIFEST['file_types']
VALID_TYPES = [x.decode('utf-8')
               for x in FILE_TYPES['audio'] + FILE_TYPES['video']]
# load modules' manifests
MANIFEST['modules'] = dict()
for mod in os.listdir(MODULES_DIR):
    mod_dir = os.path.join(MODULES_DIR, mod)
    mod_manifest = os.path.join(mod_dir, 'manifest.json')
    with open(mod_manifest, 'r') as file_:
        MANIFEST['modules'][mod] = json.load(file_)
MODULES = MANIFEST['modules']


def manifest_check():
    """
    Check the manifest at startup for consistency.
    Disable violating modules/ procedures.
    """
    LOG.info('Startup manifest checks...')
    # check modules
    mod_violate = list()
    for mod_id, mod_ in MODULES.items():
        mod_path = os.path.join(MODULES_DIR, mod_id)
        if not os.path.exists(mod_path):
            LOG.info('Cannot find module %s at %s', mod_id, mod_path)
            mod_violate.append(mod_id)
            continue
        else:
            mod_reqs = mod_['requires'] + ['module.py']
            for mod_req in mod_reqs:
                mod_req_path = os.path.join(mod_path, mod_req)
                if not os.path.exists(mod_req_path):
                    LOG.info('Cannot find module %s requirement at %s',
                             mod_id, mod_req_path)
                    mod_violate.append(mod_id)
                    break
    for mod_id in mod_violate:
        del MODULES[mod_id]
    LOG.info('Valid modules: %s', ', '.join(MODULES.keys()))

    # check procedures
    proc_violate = list()
    for proc_id, proc_ in PROCEDURES.items():
        proc_inputs = set(['raw'])
        for proc in proc_:
            if proc not in MODULES.keys():
                LOG.info('Invalid module %s for procedure %s', proc, proc_id)
                proc_violate.append(proc_id)
                break
            else:
                tmp_in = set(MODULES[proc]['inputs'])
                tmp_out = set(MODULES[proc]['outputs'])
                if not tmp_in.issubset(proc_inputs):
                    LOG.info(
                        'Invalid requirements for module %s in procedure %s', proc, proc_id)
                    proc_violate.append(proc_id)
                    break
                else:
                    proc_inputs = proc_inputs.union(tmp_out)
    for proc_id in proc_violate:
        del PROCEDURES[proc_id]
    LOG.info('Valid procedures: %s ', ', '.join(PROCEDURES.keys()))


class Process(object):
    """
    Processing tasks.
    Syntax: Process(filename, procedure_id)
    """

    def __init__(self, filename, procedure_id):
        LOG.info('')
        LOG.info('')
        self.filename = filename
        LOG.info('Filename: %s.', self.filename)
        self.file_id = slugify(os.path.splitext(filename)[0])
        LOG.info('File ID: %s.', self.file_id)
        self.procedure_id = procedure_id
        LOG.info('Procedure: %s.', self.procedure_id)

        # set later during verify()
        self.module_list = None

    def verify(self):
        """Verify the file type and procedure."""
        if (os.path.splitext(self.filename)[1]) not in VALID_TYPES:
            LOG.info('%s is of invalid type', self.filename)
            return False
        if self.procedure_id not in PROCEDURES.keys():
            LOG.info('Procedure %s does not exist', self.procedure_id)
            return False
        # set module list
        self.module_list = PROCEDURES[self.procedure_id]
        return True

    def import_file(self):
        """Import the file into /data."""
        file_path = os.path.join(CRAWL_DIR, self.filename)
        working_dir = os.path.join(DATA_DIR, self.file_id)
        raw_dir = os.path.join(working_dir, 'raw/')
        raw_file = os.path.join(raw_dir, self.filename)
        if os.path.exists(raw_file):
            LOG.info('Previously imported to %s', raw_file)
        else:
            if not os.path.exists(raw_dir):
                os.makedirs(raw_dir)
            shutil.copy2(file_path, raw_dir)
            LOG.info('Imported %s to %s', file_path, raw_dir)

    def call(self, module_id):
        """Atom instruction to call a module."""
        try:
            exec_ = os.path.join(MODULES_DIR, module_id, 'module.py')
            args = ['python', exec_, self.file_id]
            subprocess.call(args)
        except BaseException:
            LOG.info('Error occured.', exc_info=True)

    def pipeline(self):
        """Pipeline for processing."""
        if self.verify():
            self.import_file()
            for mod_id in self.module_list:
                self.call(mod_id)
            LOG.info('Pipeline completed for %s using procedure %s',
                     self.filename, self.procedure_id)
        else:
            LOG.info('Verification failed for %s using procedure %s',
                     self.filename, self.procedure_id)


def workflow(procedure_list):
    """Processing workflow, using a procedure list."""
    manifest_check()
    for filename in os.listdir(CRAWL_DIR):
        path_ = os.path.join(CRAWL_DIR, filename)
        if os.path.isfile(path_):
            for procedure in procedure_list:
                if procedure in PROCEDURES.keys():
                    Process(filename=filename,
                            procedure_id=procedure).pipeline()


if __name__ == '__main__':
    ARG_PARSER = argparse.ArgumentParser()
    ARG_PARSER.add_argument('-p', '--procedures', metavar='procedure_id',
                            help='procedures to pass to workflow', nargs='*')
    ARG_PARSER.add_argument(
        '-t', '--test', action='store_true', help='just do system checks and exit')
    ARGS = ARG_PARSER.parse_args()
    if ARGS.test:
        manifest_check()
    elif ARGS.procedures is None:
        workflow(['google', 'lvcsr'])
    else:
        workflow(ARGS.procedures)
