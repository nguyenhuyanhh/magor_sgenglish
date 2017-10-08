"""Core system for magor_sgenglish."""

from __future__ import print_function

import argparse
import json
import itertools
import logging
import os
import shutil
import subprocess

try:
    from slugify import slugify
except ImportError:
    subprocess.call(['pip2', 'install', '--user', 'python-slugify'])
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
AUDIO_TYPES = [x.decode('utf-8') for x in FILE_TYPES['audio']]
VIDEO_TYPES = [x.decode('utf-8') for x in FILE_TYPES['video']]
VALID_TYPES = AUDIO_TYPES + VIDEO_TYPES
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


class Operation(object):
    """
    Processing tasks.
    Syntax: Operation(procedure_id, file_name=None, file_id=None)
    """

    def __init__(self, procedure_id, file_name=None, file_id=None):
        if not (file_name or file_id):
            self.valid = False  # invalid operation
        elif file_name:
            self.file_name = file_name
            self.file_id = slugify(os.path.splitext(file_name)[0])
            self.valid = True
        elif file_id:
            self.file_name = None
            self.file_id = file_id
            self.valid = True
        self.procedure_id = procedure_id

        # set later during verify()
        self.module_list = None

    def __repr__(self):
        result = 'Operation(file_name={}, file_id={}, procedure_id={})'.format(
            self.file_name, self.file_id, self.procedure_id)
        return result

    def verify(self):
        """Verify the files and procedure."""
        # check for valid operation
        if not self.valid:
            return False

        # check for valid file and file_id
        if self.file_name:
            if (os.path.splitext(self.file_name)[1].lower()) not in VALID_TYPES:
                LOG.info('%s is of invalid type', self.file_name)
                return False
        elif self.file_id:
            if not os.path.exists(os.path.join(DATA_DIR, self.file_id)):
                LOG.info('%s does not exist', self.file_id)
                return False

        # check for valid procedure
        if self.procedure_id not in PROCEDURES.keys():
            LOG.info('Procedure %s does not exist', self.procedure_id)
            return False

        # if all is well, set module list
        self.module_list = PROCEDURES[self.procedure_id]
        return True

    def import_file(self):
        """Import the file into /data."""
        # init paths
        working_dir = os.path.join(DATA_DIR, self.file_id)
        raw_dir = os.path.join(working_dir, 'raw/')
        if not os.path.exists(raw_dir):
            os.makedirs(raw_dir)

        if self.file_name:
            file_path = os.path.join(CRAWL_DIR, self.file_name)
            raw_file = os.path.join(raw_dir, self.file_name)
            if os.path.exists(raw_file):
                LOG.info('Previously imported to %s', raw_file)
            else:
                shutil.copy2(file_path, raw_dir)
                LOG.info('Imported %s to %s', file_path, raw_dir)
        else:
            if os.path.exists(raw_dir) and os.listdir(raw_dir):
                LOG.info('Previously imported to %s', raw_dir)

    def call(self, module_id):
        """Atom instruction to call a module."""
        try:
            exec_ = os.path.join(MODULES_DIR, module_id, 'module.py')
            args = ['python', exec_, self.file_id]
            subprocess.call(args)
            return True
        except BaseException:
            LOG.info('Error occured.', exc_info=True)
            return False

    def pipeline(self):
        """Pipeline for processing."""
        print('\n')
        if self.file_name:
            LOG.info('Filename: %s.', self.file_name)
        LOG.info('File ID: %s.', self.file_id)
        LOG.info('Procedure: %s.', self.procedure_id)
        if self.verify():
            self.import_file()
            for mod_id in self.module_list:
                if not self.call(mod_id):
                    # module failure, terminate operation
                    LOG.info('Pipeline failed for %s at procedure %s, module %s',
                             self.file_id, self.procedure_id, mod_id)
                    return
            LOG.info('Pipeline completed for %s using procedure %s',
                     self.file_id, self.procedure_id)
        else:
            LOG.info('Verification failed for %s using procedure %s',
                     self.file_id, self.procedure_id)


def setup(args):
    """Setup all modules."""
    LOG.info('Starting setup...')
    if args.all:  # setup all modules
        for mod_id in os.listdir(MODULES_DIR):
            try:
                args = [os.path.join(MODULES_DIR, mod_id, 'setup')]
                subprocess.call(args)
                LOG.info('Setup successful for module %s', mod_id)
            except BaseException:
                LOG.info('Setup failed for module %s', mod_id)
    elif args.modules:  # setup specified modules
        for mod_id in args.modules:
            try:
                args = [os.path.join(MODULES_DIR, mod_id, 'setup')]
                subprocess.call(args)
                LOG.info('Setup successful for module %s', mod_id)
            except BaseException:
                LOG.info('Setup failed for module %s', mod_id)


def workflow(file_names, file_ids, procedures, test=False, simulate=False):
    """Processing workflow."""
    manifest_check()
    if test:  # manifest check only, no processing
        return
    valid_procs = [i for i in procedures if i in PROCEDURES.keys()]
    if file_names:
        valid_names = [i for i in file_names if os.path.isfile(
            os.path.join(CRAWL_DIR, i))]
        for i in itertools.product(valid_names, valid_procs):
            if simulate:
                LOG.debug('%s', Operation(file_name=i[0], procedure_id=i[1]))
            else:
                Operation(file_name=i[0], procedure_id=i[1]).pipeline()
    if file_ids:
        valid_ids = [i for i in file_ids if os.path.isdir(
            os.path.join(DATA_DIR, i))]
        for i in itertools.product(valid_ids, valid_procs):
            if simulate:
                LOG.debug('%s', Operation(file_id=i[0], procedure_id=i[1]))
            else:
                Operation(file_id=i[0], procedure_id=i[1]).pipeline()
    if not (file_names or file_ids):  # do everything
        workflow(file_names=os.listdir(CRAWL_DIR), file_ids=os.listdir(
            DATA_DIR), procedures=valid_procs, simulate=simulate)


def process(args):
    """Wrapper for workflow."""
    workflow(args.files, args.ids, args.procedures, args.test, args.simulate)


def main():
    """Entry point for the system."""
    # top-level argument parser
    arg_parser = argparse.ArgumentParser()
    sub_parsers = arg_parser.add_subparsers()

    # setup sub-command
    setup_parser = sub_parsers.add_parser('setup', help='setup the system')
    setup_parser.add_argument(
        '-m', '--modules', metavar='module_id', help='module_ids to setup', nargs='*')
    setup_parser.add_argument(
        '-a', '--all', action='store_true', help='setup all available modules')
    setup_parser.set_defaults(func=setup)

    # process sub-command
    process_parser = sub_parsers.add_parser('process', help='process files')
    process_parser.add_argument(
        '-f', '--files', metavar='file_name', help='file_names to process', nargs='*')
    process_parser.add_argument(
        '-i', '--ids', metavar='file_id', help='file_ids to process', nargs='*')
    process_parser.add_argument('-p', '--procedures', metavar='procedure_id',
                                help='procedures to pass to workflow', nargs='*')
    process_parser.add_argument(
        '-t', '--test', action='store_true', help='just do system checks and exit')
    process_parser.add_argument('-n', '--simulate', action='store_true',
                                help='simulate the system run, without processing any file')
    process_parser.set_defaults(func=process)

    # parse args and perform operations
    args = arg_parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
