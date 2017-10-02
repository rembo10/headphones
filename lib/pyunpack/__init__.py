from easyprocess import EasyProcess
import logging
import os.path
import sys
import zipfile
from pyunpack.about import __version__


log = logging.getLogger(__name__)
log.debug('version=' + __version__)


class PatoolError(Exception):
    pass


def _fullpath(x):
    x = os.path.expandvars(x)
    x = os.path.expanduser(x)
    x = os.path.normpath(x)
    x = os.path.abspath(x)
    return x


def _exepath(cmd):
    for p in os.environ['PATH'].split(os.pathsep):
        fullp = os.path.join(p, cmd)
        if os.access(fullp, os.X_OK):
            return fullp


class Archive(object):

    '''
    :param backend: ``auto``, ``patool`` or ``zipfile``
    :param filename: path to archive file
    '''

    def __init__(self, filename, backend='auto', timeout=None):
        self.filename = _fullpath(filename)
        self.backend = backend
        self.timeout = timeout

    def extractall_patool(self, directory, patool_path):
        log.debug('starting backend patool')
        if not patool_path:
            patool_path = _exepath('patool')
        if not patool_path:
            raise ValueError('patool not found! Please install patool!')            
        p = EasyProcess([
            sys.executable,
            patool_path,
            '--non-interactive',
            'extract',
            self.filename,
            '--outdir=' + directory,
            #                     '--verbose',
        ]).call(timeout=self.timeout)
        if p.timeout_happened:
            raise PatoolError('patool timeout\n' + str(p.stdout) + '\n' + str(p.stderr))
        if p.return_code:
            raise PatoolError('patool can not unpack\n' + str(p.stderr))

    def extractall_zipfile(self, directory):
        log.debug('starting backend zipfile')
        zipfile.ZipFile(self.filename).extractall(directory)

    def extractall(self, directory, auto_create_dir=False, patool_path=None):
        '''
        :param directory: directory to extract to
        :param auto_create_dir: auto create directory
        :param patool_path: the path to the patool backend
        '''
        log.debug('extracting %s into %s (backend=%s)', self.filename, directory, self.backend)
        is_zipfile = zipfile.is_zipfile(self.filename)
        directory = _fullpath(directory)
        if not os.path.exists(self.filename):
            raise ValueError(
                'archive file does not exist:' + str(self.filename))
        if not os.path.exists(directory):
            if auto_create_dir:
                os.makedirs(directory)
            else:
                raise ValueError('directory does not exist:' + str(directory))

        if self.backend == 'auto':
            if is_zipfile:
                self.extractall_zipfile(directory)
            else:
                self.extractall_patool(directory, patool_path)

        if self.backend == 'zipfile':
            if not is_zipfile:
                raise ValueError('file is not zip file:' + str(self.filename))
            self.extractall_zipfile(directory)

        if self.backend == 'patool':
            self.extractall_patool(directory, patool_path)
