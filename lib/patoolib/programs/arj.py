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
"""Archive commands for the arj program."""

def extract_arj (archive, compression, cmd, verbosity, interactive, outdir):
    """Extract an ARJ archive."""
    cmdlist = [cmd, 'x', '-r']
    if not interactive:
        cmdlist.append('-y')
    cmdlist.extend([archive, outdir])
    return cmdlist


def list_arj (archive, compression, cmd, verbosity, interactive):
    """List an ARJ archive."""
    cmdlist = [cmd]
    if verbosity > 1:
        cmdlist.append('v')
    else:
        cmdlist.append('l')
    if not interactive:
        cmdlist.append('-y')
    cmdlist.extend(['-r', archive])
    return cmdlist


def test_arj (archive, compression, cmd, verbosity, interactive):
    """Test an ARJ archive."""
    cmdlist = [cmd, 't', '-r']
    if not interactive:
        cmdlist.append('-y')
    cmdlist.append(archive)
    return cmdlist


def create_arj (archive, compression, cmd, verbosity, interactive, filenames):
    """Create an ARJ archive."""
    cmdlist = [cmd, 'a', '-r']
    if not interactive:
        cmdlist.append('-y')
    cmdlist.append(archive)
    cmdlist.extend(filenames)
    return cmdlist
