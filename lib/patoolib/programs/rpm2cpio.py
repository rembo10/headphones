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
"""Archive commands for the rpm2cpio program."""
import os
from .. import util

def extract_rpm (archive, compression, cmd, verbosity, interactive, outdir):
    """Extract a RPM archive."""
    # also check cpio
    cpio = util.find_program("cpio")
    if not cpio:
        raise util.PatoolError("cpio(1) is required for rpm2cpio extraction; please install it")
    path = util.shell_quote(os.path.abspath(archive))
    cmdlist = [util.shell_quote(cmd), path, "|", util.shell_quote(cpio),
        '--extract', '--make-directories', '--preserve-modification-time',
        '--no-absolute-filenames', '--force-local', '--nonmatching',
        r'"*\.\.*"']
    if verbosity > 1:
        cmdlist.append('-v')
    return (cmdlist, {'cwd': outdir, 'shell': True})
