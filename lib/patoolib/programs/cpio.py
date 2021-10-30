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
"""Archive commands for the cpio program."""
import os
import sys
from .. import util

def extract_cpio (archive, compression, cmd, verbosity, interactive, outdir):
    """Extract a CPIO archive."""
    cmdlist = [util.shell_quote(cmd), '--extract', '--make-directories',
        '--preserve-modification-time']
    if sys.platform.startswith('linux') and not cmd.endswith('bsdcpio'):
        cmdlist.extend(['--no-absolute-filenames',
        '--force-local', '--nonmatching', r'"*\.\.*"'])
    if verbosity > 1:
        cmdlist.append('-v')
    cmdlist.extend(['<', util.shell_quote(os.path.abspath(archive))])
    return (cmdlist, {'cwd': outdir, 'shell': True})


def list_cpio (archive, compression, cmd, verbosity, interactive):
    """List a CPIO archive."""
    cmdlist = [cmd, '-i', '-t']
    if verbosity > 1:
        cmdlist.append('-v')
    cmdlist.extend(['-F', archive])
    return cmdlist

test_cpio = list_cpio

def create_cpio(archive, compression, cmd, verbosity, interactive, filenames):
    """Create a CPIO archive."""
    cmdlist = [util.shell_quote(cmd), '--create']
    if verbosity > 1:
        cmdlist.append('-v')
    if len(filenames) != 0:
        findcmd = ['find']
        findcmd.extend([util.shell_quote(x) for x in filenames])
        findcmd.extend(['-print0', '|'])
        cmdlist[0:0] = findcmd
        cmdlist.append('-0')
    cmdlist.extend([">", util.shell_quote(archive)])
    return (cmdlist, {'shell': True})
