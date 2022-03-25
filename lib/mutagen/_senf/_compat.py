# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys


PY2 = sys.version_info[0] == 2
PY3 = not PY2


if PY2:
    from urlparse import urlparse, urlunparse
    urlparse, urlunparse
    from urllib import quote, unquote
    quote, unquote

    from StringIO import StringIO
    BytesIO = StringIO
    from io import StringIO as TextIO
    TextIO

    string_types = (str, unicode)
    text_type = unicode

    iteritems = lambda d: d.iteritems()
elif PY3:
    from urllib.parse import urlparse, quote, unquote, urlunparse
    urlparse, quote, unquote, urlunparse

    from io import StringIO
    StringIO = StringIO
    TextIO = StringIO
    from io import BytesIO
    BytesIO = BytesIO

    string_types = (str,)
    text_type = str

    iteritems = lambda d: iter(d.items())
