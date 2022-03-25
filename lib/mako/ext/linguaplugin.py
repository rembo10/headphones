# ext/linguaplugin.py
# Copyright 2006-2020 the Mako authors and contributors <see AUTHORS file>
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

import io

from lingua.extractors import Extractor
from lingua.extractors import get_extractor
from lingua.extractors import Message

from mako import compat
from mako.ext.extract import MessageExtractor


class LinguaMakoExtractor(Extractor, MessageExtractor):

    """Mako templates"""

    extensions = [".mako"]
    default_config = {"encoding": "utf-8", "comment-tags": ""}

    def __call__(self, filename, options, fileobj=None):
        self.options = options
        self.filename = filename
        self.python_extractor = get_extractor("x.py")
        if fileobj is None:
            fileobj = open(filename, "rb")
            must_close = True
        else:
            must_close = False
        try:
            for message in self.process_file(fileobj):
                yield message
        finally:
            if must_close:
                fileobj.close()

    def process_python(self, code, code_lineno, translator_strings):
        source = code.getvalue().strip()
        if source.endswith(compat.b(":")):
            if source in (
                compat.b("try:"),
                compat.b("else:"),
            ) or source.startswith(compat.b("except")):
                source = compat.b("")  # Ignore try/except and else
            elif source.startswith(compat.b("elif")):
                source = source[2:]  # Replace "elif" with "if"
            source += compat.b("pass")
        code = io.BytesIO(source)
        for msg in self.python_extractor(
            self.filename, self.options, code, code_lineno - 1
        ):
            if translator_strings:
                msg = Message(
                    msg.msgctxt,
                    msg.msgid,
                    msg.msgid_plural,
                    msg.flags,
                    compat.u(" ").join(translator_strings + [msg.comment]),
                    msg.tcomment,
                    msg.location,
                )
            yield msg
