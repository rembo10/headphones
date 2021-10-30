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
"""Archive commands for the GNU tar program."""
import os


def extract_tar (archive, compression, cmd, verbosity, interactive, outdir):
    """Extract a TAR archive."""
    cmdlist = [cmd, '--extract']
    add_tar_opts(cmdlist, compression, verbosity)
    cmdlist.extend(["--file", archive, '--directory', outdir])
    return cmdlist

def list_tar (archive, compression, cmd, verbosity, interactive):
    """List a TAR archive."""
    cmdlist = [cmd, '--list']
    add_tar_opts(cmdlist, compression, verbosity)
    cmdlist.extend(["--file", archive])
    return cmdlist

test_tar = list_tar

def create_tar (archive, compression, cmd, verbosity, interactive, filenames):
    """Create a TAR archive."""
    cmdlist = [cmd, '--create']
    add_tar_opts(cmdlist, compression, verbosity)
    cmdlist.extend(["--file", archive, '--'])
    cmdlist.extend(filenames)
    return cmdlist

def add_tar_opts (cmdlist, compression, verbosity):
    """Add tar options to cmdlist."""
    progname = os.path.basename(cmdlist[0])
    if compression == 'gzip':
        cmdlist.append('-z')
    elif compression == 'compress':
        cmdlist.append('-Z')
    elif compression == 'bzip2':
        cmdlist.append('-j')
    elif compression in ('lzma', 'xz') and progname == 'bsdtar':
        cmdlist.append('--%s' % compression)
    elif compression in ('lzma', 'xz', 'lzip'):
        # use the compression name as program name since
        # tar is picky which programs it can use
        program = compression
        # set compression program
        cmdlist.extend(['--use-compress-program', program])
    if verbosity > 1:
        cmdlist.append('--verbose')
