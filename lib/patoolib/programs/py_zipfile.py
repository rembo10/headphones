# -*- coding: utf-8 -*-
# Copyright (C) 2012-2015 Bastian Kleineidam
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Archive commands for the zipfile Python module."""
from __future__ import print_function
from .. import util
import zipfile
import os

READ_SIZE_BYTES = 1024*1024


def list_zip(archive, compression, cmd, verbosity, interactive):
    """List member of a ZIP archive with the zipfile Python module."""
    try:
        with zipfile.ZipFile(archive, "r") as zfile:
            for name in zfile.namelist():
                if verbosity >= 0:
                    print(name)
    except Exception as err:
        msg = "error listing %s: %s" % (archive, err)
        raise util.PatoolError(msg)
    return None

test_zip = list_zip

def extract_zip(archive, compression, cmd, verbosity, interactive, outdir):
    """Extract a ZIP archive with the zipfile Python module."""
    try:
        with zipfile.ZipFile(archive) as zfile:
            zfile.extractall(outdir)
    except Exception as err:
        msg = "error extracting %s: %s" % (archive, err)
        raise util.PatoolError(msg)
    return None


def create_zip(archive, compression, cmd, verbosity, interactive, filenames):
    """Create a ZIP archive with the zipfile Python module."""
    try:
        with zipfile.ZipFile(archive, 'w') as zfile:
            for filename in filenames:
                if os.path.isdir(filename):
                    write_directory(zfile, filename)
                else:
                    zfile.write(filename)
    except Exception as err:
        msg = "error creating %s: %s" % (archive, err)
        raise util.PatoolError(msg)
    return None


def write_directory (zfile, directory):
    """Write recursively all directories and filenames to zipfile instance."""
    for dirpath, dirnames, filenames in os.walk(directory):
        zfile.write(dirpath)
        for filename in filenames:
            zfile.write(os.path.join(dirpath, filename))
