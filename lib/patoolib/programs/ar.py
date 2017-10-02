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
"""Archive commands for the ar program."""
import os

def extract_ar (archive, compression, cmd, verbosity, interactive, outdir):
    """Extract a AR archive."""
    opts = 'x'
    if verbosity > 1:
        opts += 'v'
    cmdlist = [cmd, opts, os.path.abspath(archive)]
    return (cmdlist, {'cwd': outdir})

def list_ar (archive, compression, cmd, verbosity, interactive):
    """List a AR archive."""
    opts = 't'
    if verbosity > 1:
        opts += 'v'
    return [cmd, opts, archive]

test_ar = list_ar

def create_ar (archive, compression, cmd, verbosity, interactive, filenames):
    """Create a AR archive."""
    opts = 'rc'
    if verbosity > 1:
        opts += 'v'
    cmdlist = [cmd, opts, archive]
    cmdlist.extend(filenames)
    return cmdlist
