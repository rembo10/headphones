import sys
import itertools

IS_PY3 = sys.version_info[0] == 3

if IS_PY3:
    _range = range
    _zip_longest = itertools.zip_longest
    _no_bytes_err = 'expected str, got bytes'
else:
    _range = xrange
    _zip_longest = itertools.izip_longest
    _no_bytes_err = 'expected unicode, got str'
