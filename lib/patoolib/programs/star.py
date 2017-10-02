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
"""Archive commands for the star program."""
from .tar import add_tar_opts as add_star_opts

def extract_tar (archive, compression, cmd, verbosity, interactive, outdir):
    """Extract a TAR archive."""
    cmdlist = [cmd, '-x']
    add_star_opts(cmdlist, compression, verbosity)
    cmdlist.extend(['-C', outdir, 'file=%s' % archive])
    return cmdlist

def list_tar (archive, compression, cmd, verbosity, interactive):
    """List a TAR archive."""
    cmdlist = [cmd, '-n']
    add_star_opts(cmdlist, compression, verbosity)
    cmdlist.append("file=%s" % archive)
    return cmdlist

test_tar = list_tar

def create_tar (archive, compression, cmd, verbosity, interactive, filenames):
    """Create a TAR archive."""
    cmdlist = [cmd, '-c']
    add_star_opts(cmdlist, compression, verbosity)
    cmdlist.append("file=%s" % archive)
    cmdlist.extend(filenames)
    return cmdlist
