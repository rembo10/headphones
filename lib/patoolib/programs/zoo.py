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
"""Archive commands for the zoo program."""
import os

def extract_zoo(archive, compression, cmd, verbosity, interactive, outdir):
    """Extract a ZOO archive."""
    # Since extracted files will be placed in the current directory,
    # the cwd argument has to be the output directory.
    cmdlist = [cmd, '-extract', os.path.abspath(archive)]
    return (cmdlist, {'cwd': outdir})


def list_zoo(archive, compression, cmd, verbosity, interactive):
    """List a ZOO archive."""
    return [cmd, '-list', archive]


def test_zoo(archive, compression, cmd, verbosity, interactive):
    """Test a ZOO archive."""
    return [cmd, '-test', archive]


def create_zoo(archive, compression, cmd, verbosity, interactive, filenames):
    """Create a ZOO archive."""
    cmdlist = [cmd, '-add', archive]
    cmdlist.extend(filenames)
    return cmdlist
