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
"""Archive commands for the flac program."""
from .. import util

def extract_flac (archive, compression, cmd, verbosity, interactive, outdir):
    """Decompress a FLAC archive to a WAV file."""
    outfile = util.get_single_outfile(outdir, archive, extension=".wav")
    cmdlist = [cmd, '--decode', archive, '--output-name', outfile]
    return cmdlist


def create_flac (archive, compression, cmd, verbosity, interactive, filenames):
    """Compress a WAV file to a FLAC archive."""
    cmdlist = [cmd, filenames[0], '--best', '--output-name', archive]
    return cmdlist


def test_flac (archive, compression, cmd, verbosity, interactive):
    """Test a FLAC file."""
    return [cmd, '--test', archive]
