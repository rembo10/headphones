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
"""Archive commands for the lha program."""

def extract_lzh (archive, compression, cmd, verbosity, interactive, outdir):
    """Extract a LZH archive."""
    opts = 'x'
    if verbosity > 1:
        opts += 'v'
    opts += "w=%s" % outdir
    return [cmd, opts, archive]

def list_lzh (archive, compression, cmd, verbosity, interactive):
    """List a LZH archive."""
    cmdlist = [cmd]
    if verbosity > 1:
        cmdlist.append('v')
    else:
        cmdlist.append('l')
    cmdlist.append(archive)
    return cmdlist

def test_lzh (archive, compression, cmd, verbosity, interactive):
    """Test a LZH archive."""
    opts = 't'
    if verbosity > 1:
        opts += 'v'
    return [cmd, opts, archive]

def create_lzh (archive, compression, cmd, verbosity, interactive, filenames):
    """Create a LZH archive."""
    opts = 'a'
    if verbosity > 1:
        opts += 'v'
    cmdlist = [cmd, opts, archive]
    cmdlist.extend(filenames)
    return cmdlist
