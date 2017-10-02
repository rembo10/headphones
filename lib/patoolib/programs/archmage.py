# -*- coding: utf-8 -*-
# Copyright (C) 2012-2015 Bastian Kleineidam
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
"""Archive commands for the archmage program."""
import os
from .. import util


def extract_chm (archive, compression, cmd, verbosity, interactive, outdir):
    """Extract a CHM archive."""
    # archmage can only extract in non-existing directories
    # so a nice dirname is created
    name = util.get_single_outfile("", archive)
    outfile = os.path.join(outdir, name)
    return [cmd, '-x', os.path.abspath(archive), outfile]


def test_chm (archive, compression, cmd, verbosity, interactive):
    """Test a CHM archive."""
    return [cmd, '-d', os.path.abspath(archive)]
