# -*- coding: utf-8 -*-
# Copyright (C) 2010-2015 Bastian Kleineidam
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
"""Archive commands for the xz program."""
from . import extract_singlefile_standard, test_singlefile_standard
from .. import util


extract_xz = extract_singlefile_standard
test_xz = test_singlefile_standard

def list_xz (archive, compression, cmd, verbosity, interactive):
    """List a XZ archive."""
    cmdlist = [cmd]
    cmdlist.append('-l')
    if verbosity > 1:
        cmdlist.append('-v')
    cmdlist.append(archive)
    return cmdlist


def create_xz(archive, compression, cmd, verbosity, interactive, filenames):
    """Create an XZ archive."""
    cmdlist = [util.shell_quote(cmd)]
    if verbosity > 1:
        cmdlist.append('-v')
    cmdlist.extend(['-c', '-9', '--'])
    cmdlist.extend([util.shell_quote(x) for x in filenames])
    cmdlist.extend(['>', util.shell_quote(archive)])
    return (cmdlist, {'shell': True})


def extract_lzma(archive, compression, cmd, verbosity, interactive, outdir):
    """Extract an LZMA archive."""
    cmdlist = [util.shell_quote(cmd), '--format=lzma']
    if verbosity > 1:
        cmdlist.append('-v')
    outfile = util.get_single_outfile(outdir, archive)
    cmdlist.extend(['-c', '-d', '--', util.shell_quote(archive), '>',
        util.shell_quote(outfile)])
    return (cmdlist, {'shell': True})


def test_lzma(archive, compression, cmd, verbosity, interactive):
    """Test an LZMA archive."""
    cmdlist = [cmd, '--format=lzma']
    if verbosity > 1:
        cmdlist.append('-v')
    cmdlist.extend(['--test', archive])
    return cmdlist


def create_lzma(archive, compression, cmd, verbosity, interactive, filenames):
    """Create an LZMA archive."""
    cmdlist = [util.shell_quote(cmd), '--format=lzma']
    if verbosity > 1:
        cmdlist.append('-v')
    cmdlist.extend(['-c', '-9', '--'])
    cmdlist.extend([util.shell_quote(x) for x in filenames])
    cmdlist.extend(['>', util.shell_quote(archive)])
    return (cmdlist, {'shell': True})
