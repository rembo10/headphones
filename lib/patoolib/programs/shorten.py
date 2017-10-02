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
"""Archive commands for the shorten program."""
from .. import util

def extract_shn (archive, compression, cmd, verbosity, interactive, outdir):
    """Decompress a SHN archive to a WAV file."""
    cmdlist = [util.shell_quote(cmd)]
    outfile = util.get_single_outfile(outdir, archive, extension=".wav")
    cmdlist.extend(['-x', '-', util.shell_quote(outfile), '<',
        util.shell_quote(archive)])
    return (cmdlist, {'shell': True})


def create_shn (archive, compression, cmd, verbosity, interactive, filenames):
    """Compress a WAV file to a SHN archive."""
    if len(filenames) > 1:
        raise util.PatoolError("multiple filenames for shorten not supported")
    cmdlist = [util.shell_quote(cmd)]
    cmdlist.extend(['-', util.shell_quote(archive), '<',
        util.shell_quote(filenames[0])])
    return (cmdlist, {'shell': True})
