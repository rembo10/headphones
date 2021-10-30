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
"""Archive commands for the unzip program."""

def extract_zip (archive, compression, cmd, verbosity, interactive, outdir):
    """Extract a ZIP archive."""
    cmdlist = [cmd]
    if verbosity > 1:
        cmdlist.append('-v')
    cmdlist.extend(['--', archive, '-d', outdir])
    return cmdlist

def list_zip (archive, compression, cmd, verbosity, interactive):
    """List a ZIP archive."""
    cmdlist = [cmd, '-l']
    if verbosity > 1:
        cmdlist.append('-v')
    cmdlist.extend(['--', archive])
    return cmdlist

def test_zip (archive, compression, cmd, verbosity, interactive):
    """Test a ZIP archive."""
    cmdlist = [cmd, '-t']
    if verbosity > 1:
        cmdlist.append('-v')
    cmdlist.extend(['--', archive])
    return cmdlist
