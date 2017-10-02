# -*- coding: utf-8 -*-

# Copyright (C) 2012  Matias Bordese
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

from __future__ import print_function

import ctypes
import io
import os
import sys

from unrar import constants
from unrar import unrarlib


__all__ = ["BadRarFile", "is_rarfile", "RarFile", "RarInfo"]


if sys.version < '3':
    def b(x):
        return x
else:
    def b(x):
        if x is not None:
            # encode using DOS OEM standard
            return x.encode('cp437')


class BadRarFile(Exception):
    """RAR file error."""


def is_rarfile(filename):
    """Return true if file is a valid RAR file."""
    mode = constants.RAR_OM_LIST_INCSPLIT
    archive = unrarlib.RAROpenArchiveDataEx(filename, mode=mode)
    try:
        handle = unrarlib.RAROpenArchiveEx(ctypes.byref(archive))
    except unrarlib.UnrarException:
        return False
    unrarlib.RARCloseArchive(handle)
    return (archive.OpenResult == constants.SUCCESS)


class RarInfo(object):
    """Class with attributes describing each member in the RAR archive."""

    __slots__ = (
        'filename',
        'date_time',
        'compress_type',
        'comment',
        'create_system',
        'extract_version',
        'flag_bits',
        'CRC',
        'compress_size',
        'file_size',
        '_raw_time',
    )

    def __init__(self, header):
        """Initialize a RarInfo object with a member header data."""
        self.filename = header.FileNameW
        self._raw_time = header.FileTime
        self.date_time = unrarlib.dostime_to_timetuple(header.FileTime)
        self.compress_size = header.PackSize + (header.PackSizeHigh << 32)
        self.file_size = header.UnpSize + (header.UnpSizeHigh << 32)
        self.create_system = header.HostOS
        self.extract_version = header.UnpVer
        self.CRC = header.FileCRC
        self.flag_bits = header.Flags
        if header.CmtState == constants.RAR_COMMENTS_SUCCESS:
            self.comment = header.CmtBuf.value
        else:
            self.comment = None


class _ReadIntoMemory(object):
    """Internal class to handle in-memory extraction."""

    def __init__(self):
        super(_ReadIntoMemory, self).__init__()
        self._data = None

    def _callback(self, msg, user_data, p1, p2):
        if msg == constants.UCM_PROCESSDATA:
            if self._data is None:
                self._data = b('')
            chunk = (ctypes.c_char * p2).from_address(p1).raw
            self._data += chunk
        return 1

    def get_bytes(self):
        return io.BytesIO(self._data)


class RarFile(object):
    """RAR archive file."""

    def __init__(self, filename, mode='r', pwd=None):
        """Load RAR archive file with mode read only "r"."""
        self.filename = filename
        mode = constants.RAR_OM_LIST_INCSPLIT

        archive = unrarlib.RAROpenArchiveDataEx(filename, mode=mode)
        handle = self._open(archive)

        # assert(archive.OpenResult == constants.SUCCESS)
        self.pwd = pwd
        self.filelist = []
        self.NameToInfo = {}
        if archive.CmtState == constants.RAR_COMMENTS_SUCCESS:
            self.comment = archive.CmtBuf.value
        else:
            self.comment = None
        self._load_metadata(handle)
        self._close(handle)

    def _read_header(self, handle):
        """Read current member header into a RarInfo object."""
        rarinfo = None
        header_data = unrarlib.RARHeaderDataEx()
        res = unrarlib.RARReadHeaderEx(handle, ctypes.byref(header_data))
        if res != constants.ERAR_END_ARCHIVE:
            rarinfo = RarInfo(header=header_data)
        return rarinfo

    def _process_current(self, handle, op, dest_path=None, dest_name=None):
        """Process current member with 'op' operation."""
        unrarlib.RARProcessFileW(handle, op, dest_path, dest_name)

    def _load_metadata(self, handle):
        """Load archive members metadata."""
        rarinfo = self._read_header(handle)
        while rarinfo:
            self.filelist.append(rarinfo)
            self.NameToInfo[rarinfo.filename] = rarinfo
            self._process_current(handle, constants.RAR_SKIP)
            rarinfo = self._read_header(handle)

    def _open(self, archive):
        """Open RAR archive file."""
        try:
            handle = unrarlib.RAROpenArchiveEx(ctypes.byref(archive))
        except unrarlib.UnrarException:
            raise BadRarFile("Invalid RAR file.")
        return handle

    def _close(self, handle):
        """Close RAR archive file."""
        try:
            unrarlib.RARCloseArchive(handle)
        except unrarlib.UnrarException:
            raise BadRarFile("RAR archive close error.")

    def open(self, member, pwd=None):
        """Return file-like object for 'member'.

           'member' may be a filename or a RarInfo object.
        """
        if isinstance(member, RarInfo):
            member = member.filename

        archive = unrarlib.RAROpenArchiveDataEx(
            self.filename, mode=constants.RAR_OM_EXTRACT)
        handle = self._open(archive)

        password = pwd or self.pwd
        if password is not None:
            unrarlib.RARSetPassword(handle, b(password))

        # based on BrutuZ (https://github.com/matiasb/python-unrar/pull/4)
        # and Cubixmeister work
        data = _ReadIntoMemory()
        c_callback = unrarlib.UNRARCALLBACK(data._callback)
        unrarlib.RARSetCallback(handle, c_callback, 0)

        try:
            rarinfo = self._read_header(handle)
            while rarinfo is not None:
                if rarinfo.filename == member:
                    self._process_current(handle, constants.RAR_TEST)
                    break
                else:
                    self._process_current(handle, constants.RAR_SKIP)
                rarinfo = self._read_header(handle)

            if rarinfo is None:
                data = None

        except unrarlib.UnrarException:
            raise BadRarFile("Bad RAR archive data.")
        finally:
            self._close(handle)

        if data is None:
            raise KeyError('There is no item named %r in the archive' % member)

        # return file-like object
        return data.get_bytes()

    def read(self, member, pwd=None):
        """Return file bytes (as a string) for name."""
        return self.open(member, pwd).read()

    def namelist(self):
        """Return a list of file names in the archive."""
        names = []
        for member in self.filelist:
            names.append(member.filename)
        return names

    def setpassword(self, pwd):
        """Set default password for encrypted files."""
        self.pwd = pwd

    def getinfo(self, name):
        """Return the instance of RarInfo given 'name'."""
        rarinfo = self.NameToInfo.get(name)
        if rarinfo is None:
            raise KeyError('There is no item named %r in the archive' % name)
        return rarinfo

    def infolist(self):
        """Return a list of class RarInfo instances for files in the
        archive."""
        return self.filelist

    def printdir(self):
        """Print a table of contents for the RAR file."""
        print("%-46s %19s %12s" % ("File Name", "Modified    ", "Size"))
        for rarinfo in self.filelist:
            date = "%d-%02d-%02d %02d:%02d:%02d" % rarinfo.date_time[:6]
            print("%-46s %s %12d" % (
                rarinfo.filename, date, rarinfo.file_size))

    def testrar(self):
        """Read all the files and check the CRC."""
        error = None
        rarinfo = None
        archive = unrarlib.RAROpenArchiveDataEx(
            self.filename, mode=constants.RAR_OM_EXTRACT)
        handle = self._open(archive)

        if self.pwd:
            unrarlib.RARSetPassword(handle, b(self.pwd))

        try:
            rarinfo = self._read_header(handle)
            while rarinfo is not None:
                self._process_current(handle, constants.RAR_TEST)
                rarinfo = self._read_header(handle)
        except unrarlib.UnrarException:
            error = rarinfo.filename if rarinfo else self.filename
        finally:
            self._close(handle)
        return error

    def extract(self, member, path=None, pwd=None):
        """Extract a member from the archive to the current working directory,
           using its full name. Its file information is extracted as accurately
           as possible. `member' may be a filename or a RarInfo object. You can
           specify a different directory using `path'.
        """
        if isinstance(member, RarInfo):
            member = member.filename

        if path is None:
            path = os.getcwd()

        self._extract_members([member], path, pwd)
        return os.path.join(path, member)

    def extractall(self, path=None, members=None, pwd=None):
        """Extract all members from the archive to the current working
           directory. `path' specifies a different directory to extract to.
           `members' is optional and must be a subset of the list returned
           by namelist().
        """
        if members is None:
            members = self.namelist()
        self._extract_members(members, path, pwd)

    def _extract_members(self, members, targetpath, pwd):
        """Extract the RarInfo objects 'members' to a physical
           file on the path targetpath.
        """
        archive = unrarlib.RAROpenArchiveDataEx(
            self.filename, mode=constants.RAR_OM_EXTRACT)
        handle = self._open(archive)

        password = pwd or self.pwd
        if password is not None:
            unrarlib.RARSetPassword(handle, b(password))

        try:
            rarinfo = self._read_header(handle)
            while rarinfo is not None:
                if rarinfo.filename in members:
                    self._process_current(
                        handle, constants.RAR_EXTRACT, targetpath)
                else:
                    self._process_current(handle, constants.RAR_SKIP)
                rarinfo = self._read_header(handle)
        except unrarlib.UnrarException:
            raise BadRarFile("Bad RAR archive data.")
        finally:
            self._close(handle)


def main(args=None):
    import textwrap
    USAGE = textwrap.dedent("""\
        Usage:
            rarfile.py -l rarfile.rar        # Show listing of a rarfile
            rarfile.py -t rarfile.rar        # Test if a rarfile is valid
            rarfile.py -e rarfile.rar target # Extract rarfile into target dir
        """)

    valid_args = {'-l': 2, '-e': 3, '-t': 2}
    if args is None:
        args = sys.argv[1:]

    cmd = args and args[0] or None
    if not cmd or cmd not in valid_args or len(args) != valid_args[cmd]:
        print(USAGE)
        sys.exit(1)

    if cmd == '-l':
        # list
        rf = RarFile(args[1], 'r')
        rf.printdir()
    elif cmd == '-t':
        # test
        rf = RarFile(args[1], 'r')
        err = rf.testrar()
        if err:
            print("The following enclosed file is corrupted: {!r}".format(err))
        print("Done testing")
    elif cmd == '-e':
        # extract
        rf = RarFile(args[1], 'r')
        dest = args[2]
        rf.extractall(path=dest)


if __name__ == "__main__":
    main()
