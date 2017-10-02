# -*- coding: utf-8 -*-
# Copyright (C) 2010-2016 Bastian Kleineidam
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
"""Utility functions."""
from __future__ import print_function
import os
import sys
import shutil
import subprocess
import mimetypes
import tempfile
import time
import traceback
import locale
from . import configuration, ArchiveMimetypes, ArchiveCompressions
try:
    from shutil import which
except ImportError:
    # from Python 3.3
    def which(cmd, mode=os.F_OK | os.X_OK, path=None):
        """Given a command, mode, and a PATH string, return the path which
        conforms to the given mode on the PATH, or None if there is no such
        file.
        `mode` defaults to os.F_OK | os.X_OK. `path` defaults to the result
        of os.environ.get("PATH"), or can be overridden with a custom search
        path.
        """
        def _access_check(fn, mode):
            """Check that a given file can be accessed with the correct mode.
            Additionally check that `fn` is not a directory, as on Windows
            directories pass the os.access check."""
            return (os.path.exists(fn) and os.access(fn, mode)
                    and not os.path.isdir(fn))
        # If we're given a path with a directory part, look it up directly rather
        # than referring to PATH directories. This includes checking relative to the
        # current directory, e.g. ./script
        if os.path.dirname(cmd):
            if _access_check(cmd, mode):
                return cmd
            return None
        path = (path or os.environ.get("PATH", os.defpath)).split(os.pathsep)
        if sys.platform == "win32":
            # The current directory takes precedence on Windows.
            if not os.curdir in path:
                path.insert(0, os.curdir)
            # PATHEXT is necessary to check on Windows.
            pathext = os.environ.get("PATHEXT", "").split(os.pathsep)
            # See if the given file matches any of the expected path extensions.
            # This will allow us to short circuit when given "python.exe".
            # If it does match, only test that one, otherwise we have to try
            # others.
            if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
                files = [cmd]
            else:
                files = [cmd + ext for ext in pathext]
        else:
            # On other platforms you don't have things like PATHEXT to tell you
            # what file suffixes are executable, so just pass on cmd as-is.
            files = [cmd]
        seen = set()
        for dir in path:
            normdir = os.path.normcase(dir)
            if not normdir in seen:
                seen.add(normdir)
                for thefile in files:
                    name = os.path.join(dir, thefile)
                    if _access_check(name, mode):
                        return name
        return None


def system_search_path():
    """Get the list of directories on a system to search for executable programs.
    It is either the PATH environment variable or if PATH is undefined the value
    of os.defpath.
    """
    return os.environ.get("PATH", os.defpath)


# internal MIME database
mimedb = None

def init_mimedb():
    """Initialize the internal MIME database."""
    global mimedb
    try:
        mimedb = mimetypes.MimeTypes(strict=False)
    except Exception as msg:
        log_error("could not initialize MIME database: %s" % msg)
        return
    add_mimedb_data(mimedb)


def add_mimedb_data(mimedb):
    """Add missing encodings and mimetypes to MIME database."""
    mimedb.encodings_map['.bz2'] = 'bzip2'
    mimedb.encodings_map['.lzma'] = 'lzma'
    mimedb.encodings_map['.xz'] = 'xz'
    mimedb.encodings_map['.lz'] = 'lzip'
    mimedb.suffix_map['.tbz2'] = '.tar.bz2'
    add_mimetype(mimedb, 'application/x-lzop', '.lzo')
    add_mimetype(mimedb, 'application/x-adf', '.adf')
    add_mimetype(mimedb, 'application/x-arj', '.arj')
    add_mimetype(mimedb, 'application/x-lzma', '.lzma')
    add_mimetype(mimedb, 'application/x-xz', '.xz')
    add_mimetype(mimedb, 'application/java-archive', '.jar')
    add_mimetype(mimedb, 'application/x-rar', '.rar')
    add_mimetype(mimedb, 'application/x-rar', '.cbr')
    add_mimetype(mimedb, 'application/x-7z-compressed', '.7z')
    add_mimetype(mimedb, 'application/x-7z-compressed', '.cb7')
    add_mimetype(mimedb, 'application/x-cab', '.cab')
    add_mimetype(mimedb, 'application/x-rpm', '.rpm')
    add_mimetype(mimedb, 'application/x-debian-package', '.deb')
    add_mimetype(mimedb, 'application/x-ace', '.ace')
    add_mimetype(mimedb, 'application/x-ace', '.cba')
    add_mimetype(mimedb, 'application/x-archive', '.a')
    add_mimetype(mimedb, 'application/x-alzip', '.alz')
    add_mimetype(mimedb, 'application/x-arc', '.arc')
    add_mimetype(mimedb, 'application/x-lrzip', '.lrz')
    add_mimetype(mimedb, 'application/x-lha', '.lha')
    add_mimetype(mimedb, 'application/x-lzh', '.lzh')
    add_mimetype(mimedb, 'application/x-rzip', '.rz')
    add_mimetype(mimedb, 'application/x-zoo', '.zoo')
    add_mimetype(mimedb, 'application/x-dms', '.dms')
    add_mimetype(mimedb, 'application/x-zip-compressed', '.crx')
    add_mimetype(mimedb, 'application/x-shar', '.shar')
    add_mimetype(mimedb, 'application/x-tar', '.cbt')
    add_mimetype(mimedb, 'application/x-vhd', '.vhd')
    add_mimetype(mimedb, 'audio/x-ape', '.ape')
    add_mimetype(mimedb, 'audio/x-shn', '.shn')
    add_mimetype(mimedb, 'audio/flac', '.flac')
    add_mimetype(mimedb, 'application/x-chm', '.chm')
    add_mimetype(mimedb, 'application/x-iso9660-image', '.iso')
    add_mimetype(mimedb, 'application/zip', '.cbz')
    add_mimetype(mimedb, 'application/zip', '.epub')
    add_mimetype(mimedb, 'application/zip', '.apk')
    add_mimetype(mimedb, 'application/zpaq', '.zpaq')


def add_mimetype(mimedb, mimetype, extension):
    """Add or replace a mimetype to be used with the given extension."""
    # If extension is already a common type, strict=True must be used.
    strict = extension in mimedb.types_map[True]
    mimedb.add_type(mimetype, extension, strict=strict)


class PatoolError (Exception):
    """Raised when errors occur."""
    pass


class memoized (object):
    """Decorator that caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned, and
    not re-evaluated."""

    def __init__(self, func):
        """Set func and init cache."""
        self.func = func
        self.cache = {}

    def __call__(self, *args):
        """Try to find result for function arguments in local cache or
        execute the function and fill the cache with the result."""
        try:
            return self.cache[args]
        except KeyError:
            self.cache[args] = value = self.func(*args)
            return value
        except TypeError:
            # uncachable -- for instance, passing a list as an argument.
            # Better to not cache than to blow up entirely.
            return self.func(*args)

    def __repr__(self):
        """Return the function's docstring."""
        return self.func.__doc__


def backtick (cmd, encoding='utf-8'):
    """Return decoded output from command."""
    data = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]
    return data.decode(encoding)


def run (cmd, verbosity=0, **kwargs):
    """Run command without error checking.
    @return: command return code"""
    # Note that shell_quote_nt() result is not suitable for copy-paste
    # (especially on Unix systems), but it looks nicer than shell_quote().
    if verbosity >= 0:
        log_info("running %s" % " ".join(map(shell_quote_nt, cmd)))
    if kwargs:
        if verbosity >= 0:
            log_info("    with %s" % ", ".join("%s=%s" % (k, shell_quote(str(v)))\
                                           for k, v in kwargs.items()))
        if kwargs.get("shell"):
            # for shell calls the command must be a string
            cmd = " ".join(cmd)
    if verbosity < 1:
        # hide command output on stdout
        with open(os.devnull, 'wb') as devnull:
            kwargs['stdout'] = devnull
            res = subprocess.call(cmd, **kwargs)
    else:
        res = subprocess.call(cmd, **kwargs)
    return res


def run_checked (cmd, ret_ok=(0,), **kwargs):
    """Run command and raise PatoolError on error."""
    retcode = run(cmd, **kwargs)
    if retcode not in ret_ok:
        msg = "Command `%s' returned non-zero exit status %d" % (cmd, retcode)
        raise PatoolError(msg)
    return retcode


@memoized
def guess_mime (filename):
    """Guess the MIME type of given filename using file(1) and if that
    fails by looking at the filename extension with the Python mimetypes
    module.

    The result of this function is cached.
    """
    mime, encoding = guess_mime_file(filename)
    if mime is None:
        mime, encoding = guess_mime_mimedb(filename)
    assert mime is not None or encoding is None
    return mime, encoding


Encoding2Mime = {
    'gzip': "application/gzip",
    'bzip2': "application/x-bzip2",
    'compress': "application/x-compress",
    'lzma': "application/x-lzma",
    'lzip': "application/x-lzip",
    'xz': "application/x-xz",
}
Mime2Encoding = dict([(_val, _key) for _key, _val in Encoding2Mime.items()])
# libmagic before version 5.14 identified .gz files as application/x-gzip
Mime2Encoding['application/x-gzip'] = 'gzip'


def guess_mime_mimedb (filename):
    """Guess MIME type from given filename.
    @return: tuple (mime, encoding)
    """
    mime, encoding = None, None
    if mimedb is not None:
        mime, encoding = mimedb.guess_type(filename, strict=False)
    if mime not in ArchiveMimetypes and encoding in ArchiveCompressions:
        # Files like 't.txt.gz' are recognized with encoding as format, and
        # an unsupported mime-type like 'text/plain'. Fix this.
        mime = Encoding2Mime[encoding]
        encoding = None
    return mime, encoding


def guess_mime_file (filename):
    """Determine MIME type of filename with file(1):
     (a) using `file --mime`
     (b) using `file` and look the result string
    @return: tuple (mime, encoding)
    """
    mime, encoding = None, None
    base, ext = os.path.splitext(filename)
    if ext.lower() in ('.alz',):
        # let mimedb recognize these extensions
        return mime, encoding
    if os.path.isfile(filename):
        file_prog = find_program("file")
        if file_prog:
            mime, encoding = guess_mime_file_mime(file_prog, filename)
            if mime is None:
                mime = guess_mime_file_text(file_prog, filename)
                encoding = None
    if mime in Mime2Encoding:
        # try to look inside compressed archives
        cmd = [file_prog, "--brief", "--mime", "--uncompress", filename]
        try:
            outparts = backtick(cmd).strip().split(";")
        except OSError:
            # ignore errors, as file(1) is only a fallback
            return mime, encoding
        mime2 = outparts[0].split(" ", 1)[0]
        # Some file(1) implementations return an empty or unknown mime type
        # when the uncompressor program is not installed, other
        # implementation return the original file type.
        # The following detects both cases.
        if (mime2 in ('application/x-empty', 'application/octet-stream') or
            mime2 in Mime2Encoding):
            # The uncompressor program file(1) uses is not installed
            # or is not able to uncompress.
            # Try to get mime information from the file extension.
            mime2, encoding2 = guess_mime_mimedb(filename)
            if mime2 in ArchiveMimetypes:
                mime = mime2
                encoding = encoding2
        elif mime2 in ArchiveMimetypes:
            mime = mime2
            encoding = get_file_mime_encoding(outparts)
    return mime, encoding


def guess_mime_file_mime (file_prog, filename):
    """Determine MIME type of filename with file(1) and --mime option.
    @return: tuple (mime, encoding)
    """
    mime, encoding = None, None
    cmd = [file_prog, "--brief", "--mime-type", filename]
    try:
        mime = backtick(cmd).strip()
    except OSError:
        # ignore errors, as file(1) is only a fallback
        pass
    if mime not in ArchiveMimetypes:
        mime, encoding = None, None
    return mime, encoding


def get_file_mime_encoding (parts):
    """Get encoding value from splitted output of file --mime --uncompress."""
    for part in parts:
        for subpart in part.split(" "):
            if subpart.startswith("compressed-encoding="):
                mime = subpart.split("=")[1].strip()
                return Mime2Encoding.get(mime)
    return None


# Match file(1) output text to mime types
FileText2Mime = {
    "7-zip archive data": "application/x-7z-compressed",
    "ACE archive data": "application/x-ace",
    "Amiga DOS disk": "application/x-adf",
    "ARJ archive data": "application/x-arj",
    "bzip2 compressed data": "application/x-bzip2",
    "cpio archive": "application/x-cpio",
    "ASCII cpio archive": "application/x-cpio",
    "Debian binary package": "application/x-debian-package",
    "gzip compressed data": "application/x-gzip",
    "LZMA compressed data": "application/x-lzma",
    "LRZIP compressed data": "application/x-lrzip",
    "lzop compressed data": "application/x-lzop",
    "Microsoft Cabinet archive data": "application/vnd.ms-cab-compressed",
    "RAR archive data": "application/x-rar",
    "RPM ": "application/x-redhat-package-manager",
    "POSIX tar archive": "application/x-tar",
    "xz compressed data": "application/x-xz",
    "Zip archive data": "application/zip",
    "compress'd data": "application/x-compress",
    "lzip compressed data": "application/x-lzip",
    "rzip compressed data": "application/x-rzip",
    "current ar archive": "application/x-archive",
    "LHa ": "application/x-lha",
    "ARC archive data": "application/x-arc",
    "Zoo archive data": "application/x-zoo",
    "DMS archive data": "application/x-dms",
    "Monkey's Audio": "audio/x-ape",
    "FLAC audio bitstream data": "audio/flac",
    "MS Windows HtmlHelp Data": "application/x-chm",
    "ZPAQ stream": "application/zpaq",
}

def guess_mime_file_text (file_prog, filename):
    """Determine MIME type of filename with file(1)."""
    cmd = [file_prog, "--brief", filename]
    try:
        output = backtick(cmd).strip()
    except OSError:
        # ignore errors, as file(1) is only a fallback
        return None
    # match output against known strings
    for matcher, mime in FileText2Mime.items():
        if output.startswith(matcher) and mime in ArchiveMimetypes:
            return mime
    return None


def check_existing_filename (filename, onlyfiles=True):
    """Ensure that given filename is a valid, existing file."""
    if not os.path.exists(filename):
        raise PatoolError("file `%s' was not found" % filename)
    if not os.access(filename, os.R_OK):
        raise PatoolError("file `%s' is not readable" % filename)
    if onlyfiles and not os.path.isfile(filename):
        raise PatoolError("`%s' is not a file" % filename)


def check_writable_filename(filename):
    """Ensure that the given filename is writable."""
    if not os.access(filename, os.W_OK):
        raise PatoolError("file `%s' is not writable" % filename)


def check_new_filename (filename):
    """Check that filename does not already exist."""
    if os.path.exists(filename):
        raise PatoolError("cannot overwrite existing file `%s'" % filename)


def check_archive_filelist (filenames):
    """Check that file list is not empty and contains only existing files."""
    if not filenames:
        raise PatoolError("cannot create archive with empty filelist")
    for filename in filenames:
        check_existing_filename(filename, onlyfiles=False)


def set_mode (filename, flags):
    """Set mode flags for given filename if not already set."""
    try:
        mode = os.lstat(filename).st_mode
    except OSError:
        # ignore
        return
    if not (mode & flags):
        try:
            os.chmod(filename, flags | mode)
        except OSError as msg:
            log_error("could not set mode flags for `%s': %s" % (filename, msg))


def get_filesize(filename):
    """Return file size in Bytes, or -1 on error."""
    return os.path.getsize(filename)


def strsize(b, grouping=True):
    """Return human representation of bytes b. A negative number of bytes
    raises a value error."""
    if b < 0:
        raise ValueError("Invalid negative byte number")
    if b < 1024:
        return u"%sB" % locale.format("%d", b, grouping)
    if b < 1024 * 10:
        return u"%sKB" % locale.format("%d", (b // 1024), grouping)
    if b < 1024 * 1024:
        return u"%sKB" % locale.format("%.2f", (float(b) / 1024), grouping)
    if b < 1024 * 1024 * 10:
        return u"%sMB" % locale.format("%.2f", (float(b) / (1024*1024)), grouping)
    if b < 1024 * 1024 * 1024:
        return u"%sMB" % locale.format("%.1f", (float(b) / (1024*1024)), grouping)
    if b < 1024 * 1024 * 1024 * 10:
        return u"%sGB" % locale.format("%.2f", (float(b) / (1024*1024*1024)), grouping)
    return u"%sGB" % locale.format("%.1f", (float(b) / (1024*1024*1024)), grouping)


def tmpdir (dir=None):
    """Return a temporary directory for extraction."""
    return tempfile.mkdtemp(suffix='', prefix='Unpack_', dir=dir)


def tmpfile (dir=None, prefix="temp", suffix=None):
    """Return a temporary file."""
    return tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)[1]


def shell_quote (value):
    """Quote all shell metacharacters in given string value with strong
    (ie. single) quotes, handling the single quote especially."""
    if os.name == 'nt':
        return shell_quote_nt(value)
    return "'%s'" % value.replace("'", r"'\''")


def shell_quote_nt (value):
    """Quote argument for Windows system. Modeled after distutils
    _nt_quote_args() function."""
    if " " in value:
        return '"%s"' % value
    return value


def stripext (filename):
    """Return the basename without extension of given filename."""
    return os.path.splitext(os.path.basename(filename))[0]


def get_single_outfile (directory, archive, extension=""):
    """Get output filename if archive is in a single file format like gzip."""
    outfile = os.path.join(directory, stripext(archive))
    if os.path.exists(outfile + extension):
        # prevent overwriting existing files
        i = 1
        newfile = "%s%d" % (outfile, i)
        while os.path.exists(newfile + extension):
            newfile = "%s%d" % (outfile, i)
            i += 1
        outfile = newfile
    return outfile + extension


def log_error (msg, out=sys.stderr):
    """Print error message to stderr (or any other given output)."""
    print("patool error:", msg, file=out)


def log_info (msg, out=sys.stdout):
    """Print info message to stdout (or any other given output)."""
    print("patool:", msg, file=out)


def log_internal_error(out=sys.stderr, etype=None, evalue=None, tb=None):
    """Print internal error message (output defaults to stderr)."""
    print(os.linesep, file=out)
    print("""********** Oops, I did it again. *************

You have found an internal error in %(app)s. Please write a bug report
at %(url)s and include at least the information below:

Not disclosing some of the information below due to privacy reasons is ok.
I will try to help you nonetheless, but you have to give me something
I can work with ;) .
""" % dict(app=configuration.AppName, url=configuration.SupportUrl), file=out)
    if etype is None:
        etype = sys.exc_info()[0]
    if evalue is None:
        evalue = sys.exc_info()[1]
    print(etype, evalue, file=out)
    if tb is None:
        tb = sys.exc_info()[2]
    traceback.print_exception(etype, evalue, tb, None, out)
    print_app_info(out=out)
    print_locale_info(out=out)
    print(os.linesep,
      "******** %s internal error, over and out ********" % configuration.AppName, file=out)

def print_env_info(key, out=sys.stderr):
    """If given environment key is defined, print it out."""
    value = os.getenv(key)
    if value is not None:
        print(key, "=", repr(value), file=out)


def print_locale_info(out=sys.stderr):
    """Print locale info."""
    for key in ("LANGUAGE", "LC_ALL", "LC_CTYPE", "LANG"):
        print_env_info(key, out=out)


def print_app_info(out=sys.stderr):
    """Print system and application info (output defaults to stderr)."""
    print("System info:", file=out)
    print(configuration.App, file=out)
    print("Python %(version)s on %(platform)s" %
                    {"version": sys.version, "platform": sys.platform}, file=out)
    stime = strtime(time.time())
    print("Local time:", stime, file=out)
    print("sys.argv", sys.argv, file=out)


def strtime(t):
    """Return ISO 8601 formatted time."""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t)) + \
           strtimezone()


def strtimezone():
    """Return timezone info, %z on some platforms, but not supported on all.
    """
    if time.daylight:
        zone = time.altzone
    else:
        zone = time.timezone
    return "%+04d" % (-zone//3600)


def p7zip_supports_rar():
    """Determine if the RAR codec is installed for 7z program."""
    if os.name == 'nt':
        # Assume RAR support is compiled into the binary.
        return True
    # the subdirectory and codec name
    codecname = 'p7zip/Codecs/Rar29.so'
    # search canonical user library dirs
    for libdir in ('/usr/lib', '/usr/local/lib', '/usr/lib64', '/usr/local/lib64', '/usr/lib/i386-linux-gnu', '/usr/lib/x86_64-linux-gnu'):
        fname = os.path.join(libdir, codecname)
        if os.path.exists(fname):
            return True
    return False


@memoized
def find_program (program):
    """Look for program in environment PATH variable."""
    if os.name == 'nt':
        # Add some well-known archiver programs to the search path
        path = os.environ['PATH']
        path = append_to_path(path, get_nt_7z_dir())
        path = append_to_path(path, get_nt_mac_dir())
        path = append_to_path(path, get_nt_winrar_dir())
    else:
        # use default path
        path = None
    return which(program, path=path)


def append_to_path (path, directory):
    """Add a directory to the PATH environment variable, if it is a valid
    directory."""
    if not os.path.isdir(directory) or directory in path:
        return path
    if not path.endswith(os.pathsep):
        path += os.pathsep
    return path + directory


def get_nt_7z_dir ():
    """Return 7-Zip directory from registry, or an empty string."""
    # Python 3.x renamed the _winreg module to winreg
    try:
        import _winreg as winreg
    except ImportError:
        import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\7-Zip")
        try:
            return winreg.QueryValueEx(key, "Path")[0]
        finally:
            winreg.CloseKey(key)
    except WindowsError:
        return ""


def get_nt_program_dir ():
    """Return the Windows program files directory."""
    progvar = "%ProgramFiles%"
    return os.path.expandvars(progvar)


def get_nt_mac_dir ():
    """Return Monkey Audio Compressor (MAC) directory."""
    return os.path.join(get_nt_program_dir(), "Monkey's Audio")


def get_nt_winrar_dir():
    """Return WinRAR directory."""
    return os.path.join(get_nt_program_dir(), "WinRAR")


def strlist_with_or (alist):
    """Return comma separated string, and last entry appended with ' or '."""
    if len(alist) > 1:
        return "%s or %s" % (", ".join(alist[:-1]), alist[-1])
    return ", ".join(alist)


def is_same_file (filename1, filename2):
    """Check if filename1 and filename2 point to the same file object.
    There can be false negatives, ie. the result is False, but it is
    the same file anyway. Reason is that network filesystems can create
    different paths to the same physical file.
    """
    if filename1 == filename2:
        return True
    if os.name == 'posix':
        return os.path.samefile(filename1, filename2)
    return is_same_filename(filename1, filename2)


def is_same_filename (filename1, filename2):
    """Check if filename1 and filename2 are the same filename."""
    return os.path.realpath(filename1) == os.path.realpath(filename2)


def link_or_copy(src, dst, verbosity=0):
    """Try to make a hard link from src to dst and if that fails
    copy the file. Hard links save some disk space and linking
    should fail fast since no copying is involved.
    """
    if verbosity > 0:
        log_info("Copying %s -> %s" % (src, dst))
    try:
        os.link(src, dst)
    except (AttributeError, OSError):
        try:
            shutil.copy(src, dst)
        except OSError as msg:
            raise PatoolError(msg)


def chdir(directory):
    """Remember and return current directory before calling os.chdir().
    If the current directory could not be determined, return None.
    """
    try:
        olddir = os.getcwd()
    except OSError:
        olddir = None
    os.chdir(directory)
    return olddir


init_mimedb()
