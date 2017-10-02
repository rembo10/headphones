# -*- coding: utf-8 -*-
# Copyright (C) 2011-2015 Bastian Kleineidam
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
"""Archive commands for the xdms program."""
from .. import util


def extract_dms (archive, compression, cmd, verbosity, interactive, outdir):
    """Extract a DMS archive."""
    check_archive_ext(archive)
    cmdlist = [cmd, '-d', outdir]
    if verbosity > 1:
        cmdlist.append('-v')
    cmdlist.extend(['u', archive])
    return cmdlist


def list_dms (archive, compression, cmd, verbosity, interactive):
    """List a DMS archive."""
    check_archive_ext(archive)
    return [cmd, 'v', archive]


def test_dms (archive, compression, cmd, verbosity, interactive):
    """Test a DMS archive."""
    check_archive_ext(archive)
    return [cmd, 't', archive]


def check_archive_ext (archive):
    """xdms(1) cannot handle files with extensions other than '.dms'."""
    if not archive.lower().endswith(".dms"):
        rest = archive[-4:]
        msg = "xdms(1) archive file must end with `.dms', not `%s'" % rest
        raise util.PatoolError(msg)
