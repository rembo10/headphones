#  This file is part of Headphones.
#
#  Headphones is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Headphones is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Headphones.  If not, see <http://www.gnu.org/licenses/>.

import os
import logging
import headphones

from logging import handlers
from headphones import helpers

MAX_SIZE = 1000000 # 1 MB
MAX_FILES = 5

FILENAME = 'headphones.log'

# Headphones logger
logger = logging.getLogger('headphones')

class LogListHandler(logging.Handler):
    """
    Log handler for Web UI.
    """

    def emit(self, record):
        headphones.LOG_LIST.insert(0, (helpers.now(), self.format(record), record.levelname, record.threadName))

def initLogger(verbose=1):
    """
    Setup logging for Headphones. It uses the logger instance with the name
    'headphones'. Three log handlers are added:

    * RotatingFileHandler: for the file headphones.log
    * LogListHandler: for Web UI
    * StreamHandler: for console (if verbose > 0)
    """

    # Configure the logger to accept all messages
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    # Setup file logger
    filename = os.path.join(headphones.LOG_DIR, FILENAME)

    file_formatter = logging.Formatter('%(asctime)s - %(levelname)-7s :: %(threadName)s : %(message)s', '%d-%b-%Y %H:%M:%S')
    file_handler = handlers.RotatingFileHandler(filename, maxBytes=MAX_SIZE, backupCount=MAX_FILES)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    logger.addHandler(file_handler)

    # Add list logger
    loglist_handler = LogListHandler()
    loglist_handler.setLevel(logging.INFO)

    logger.addHandler(loglist_handler)

    # Setup console logger
    if verbose:
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s :: %(threadName)s : %(message)s', '%d-%b-%Y %H:%M:%S')
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)

        if verbose == 1:
            console_handler.setLevel(logging.INFO)
        elif verbose == 2:
            console_handler.setLevel(logging.DEBUG)

        logger.addHandler(console_handler)

# Expose logger methods
info = logger.info
warn = logger.warn
error = logger.error
debug = logger.debug
warning = logger.warning
exception = logger.exception