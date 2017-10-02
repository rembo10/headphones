from entrypoint2 import entrypoint
from pyunpack import Archive
import logging

log = logging.getLogger(__name__)
# log=logging


@entrypoint
def extractall(filename, directory, backend='auto', auto_create_dir=False):
    '''
    :param backend: auto, patool or zipfile
    :param filename: path to archive file
    :param directory: directory to extract to
    :param auto_create_dir: auto create directory
    '''
    Archive(filename, backend).extractall(directory,
                                          auto_create_dir=auto_create_dir)
