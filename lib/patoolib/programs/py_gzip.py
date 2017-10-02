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
"""Archive commands for the gzip Python module."""
from __future__ import absolute_import
# now gzip refers to the Python standard module, not the local one
import gzip
from .. import util

READ_SIZE_BYTES = 1024*1024

def extract_gzip (archive, compression, cmd, verbosity, interactive, outdir):
    """Extract a GZIP archive with the gzip Python module."""
    targetname = util.get_single_outfile(outdir, archive)
    try:
        with gzip.GzipFile(archive) as gzipfile:
            with open(targetname, 'wb') as targetfile:
                data = gzipfile.read(READ_SIZE_BYTES)
                while data:
                    targetfile.write(data)
                    data = gzipfile.read(READ_SIZE_BYTES)
    except Exception as err:
        msg = "error extracting %s to %s: %s" % (archive, targetname, err)
        raise util.PatoolError(msg)
    return None


def create_gzip (archive, compression, cmd, verbosity, interactive, filenames):
    """Create a GZIP archive with the gzip Python module."""
    if len(filenames) > 1:
        raise util.PatoolError('multi-file compression not supported in Python gzip')
    try:
        with gzip.GzipFile(archive, 'wb') as gzipfile:
            filename = filenames[0]
            with open(filename, 'rb') as srcfile:
                data = srcfile.read(READ_SIZE_BYTES)
                while data:
                    gzipfile.write(data)
                    data = srcfile.read(READ_SIZE_BYTES)
    except Exception as err:
        msg = "error creating %s: %s" % (archive, err)
        raise util.PatoolError(msg)
    return None
