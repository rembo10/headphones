# This file is part of beets.
# Copyright 2014, Adrian Sampson.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# This particular version has been slightly modified to work with Headphones
# https://github.com/rembo10/headphones

__version__ = '1.3.10-headphones'
__author__ = 'Adrian Sampson <adrian@radbox.org>'

import os

import beets.library
from beets.util import confit

Library = beets.library.Library

config = confit.LazyConfig(os.path.dirname(__file__), __name__)
