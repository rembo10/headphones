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
"""Archive commands for the unadf program."""


def extract_adf (archive, compression, cmd, verbosity, interactive, outdir):
    """Extract an ADF archive."""
    return [cmd, archive, '-d', outdir]


def list_adf (archive, compression, cmd, verbosity, interactive):
    """List an ADF archive."""
    return [cmd, '-l', archive]

test_adf = list_adf
