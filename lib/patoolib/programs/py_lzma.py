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
"""Archive commands for the lzma Python module."""
from .. import util
import lzma

READ_SIZE_BYTES = 1024*1024

def _extract(archive, compression, cmd, format, verbosity, outdir):
    """Extract an LZMA or XZ archive with the lzma Python module."""
    targetname = util.get_single_outfile(outdir, archive)
    try:
        with lzma.LZMAFile(archive, format=format) as lzmafile:
            with open(targetname, 'wb') as targetfile:
                data = lzmafile.read(READ_SIZE_BYTES)
                while data:
                    targetfile.write(data)
                    data = lzmafile.read(READ_SIZE_BYTES)
    except Exception as err:
        msg = "error extracting %s to %s: %s" % (archive, targetname, err)
        raise util.PatoolError(msg)
    return None

def extract_lzma(archive, compression, cmd, verbosity, interactive, outdir):
    """Extract an LZMA archive with the lzma Python module."""
    return _extract(archive, compression, cmd, lzma.FORMAT_ALONE, verbosity, outdir)

def extract_xz(archive, compression, cmd, verbosity, interactive, outdir):
    """Extract an XZ archive with the lzma Python module."""
    return _extract(archive, compression, cmd, lzma.FORMAT_XZ, verbosity, outdir)


def _create(archive, compression, cmd, format, verbosity, filenames):
    """Create an LZMA or XZ archive with the lzma Python module."""
    if len(filenames) > 1:
        raise util.PatoolError('multi-file compression not supported in Python lzma')
    try:
        with lzma.LZMAFile(archive, mode='wb', format=format, preset=9) as lzmafile:
            filename = filenames[0]
            with open(filename, 'rb') as srcfile:
                data = srcfile.read(READ_SIZE_BYTES)
                while data:
                    lzmafile.write(data)
                    data = srcfile.read(READ_SIZE_BYTES)
    except Exception as err:
        msg = "error creating %s: %s" % (archive, err)
        raise util.PatoolError(msg)
    return None

def create_lzma(archive, compression, cmd, verbosity, interactive, filenames):
    """Create an LZMA archive with the lzma Python module."""
    return _create(archive, compression, cmd, lzma.FORMAT_ALONE, verbosity, filenames)

def create_xz(archive, compression, cmd, verbosity, interactive, filenames):
    """Create an XZ archive with the lzma Python module."""
    return _create(archive, compression, cmd, lzma.FORMAT_XZ, verbosity, filenames)
