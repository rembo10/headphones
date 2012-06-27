# mako/lexer.py
# Copyright (C) 2006-2011 the Mako authors and contributors <see AUTHORS file>
#
# This module is part of Mako and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""provides the Lexer class for parsing template strings into parse trees."""

import re, codecs
from mako import parsetree, exceptions, util
from mako.pygen import adjust_whitespace

_regexp_cache = {}

class Lexer(object):
    def __init__(self, text, filename=None, 
                        disable_unicode=False, 
                        input_encoding=None, preprocessor=None):
        self.text = text
        self.filename = filename
        self.template = parsetree.TemplateNode(self.filename)
        self.matched_lineno = 1
        self.matched_charpos = 0
        self.lineno = 1
        self.match_position = 0
        self.tag = []
        self.control_line = []
        self.disable_unicode = disable_unicode
        self.encoding = input_encoding
 
        if util.py3k and disable_unicode:
            raise exceptions.UnsupportedError(
                                    "Mako for Python 3 does not "
                                    "support disabling Unicode")
 
        if preprocessor is None:
            self.preprocessor = []
        elif not hasattr(preprocessor, '__iter__'):
            self.preprocessor = [preprocessor]
        else:
            self.preprocessor = preprocessor
 
    @property
    def exception_kwargs(self):
        return {'source':self.text, 
                'lineno':self.matched_lineno, 
                'pos':self.matched_charpos, 
                'filename':self.filename}
 
    def match(self, regexp, flags=None):
        """compile the given regexp, cache the reg, and call match_reg()."""
 
        try:
            reg = _regexp_cache[(regexp, flags)]
        except KeyError:
            if flags:
                reg = re.compile(regexp, flags)
            else:
                reg = re.compile(regexp)
            _regexp_cache[(regexp, flags)] = reg
 
        return self.match_reg(reg)
 
    def match_reg(self, reg):
        """match the given regular expression object to the current text position.
 
        if a match occurs, update the current text and line position.
 
        """

        mp = self.match_position

        match = reg.match(self.text, self.match_position)
        if match:
            (start, end) = match.span()
            if end == start:
                self.match_position = end + 1
            else:
                self.match_position = end
            self.matched_lineno = self.lineno
            lines = re.findall(r"\n", self.text[mp:self.match_position])
            cp = mp - 1
            while (cp >= 0 and cp<self.textlength and self.text[cp] != '\n'):
                cp -=1
            self.matched_charpos = mp - cp
            self.lineno += len(lines)
            #print "MATCHED:", match.group(0), "LINE START:", 
            # self.matched_lineno, "LINE END:", self.lineno
        #print "MATCH:", regexp, "\n", self.text[mp : mp + 15], (match and "TRUE" or "FALSE")
        return match
 
    def parse_until_text(self, *text):
        startpos = self.match_position
        while True:
            match = self.match(r'#.*\n')
            if match:
                continue
            match = self.match(r'(\"\"\"|\'\'\'|\"|\')')
            if match:
                m = self.match(r'.*?%s' % match.group(1), re.S)
                if not m:
                    raise exceptions.SyntaxException(
                                "Unmatched '%s'" % 
                                match.group(1), 
                                **self.exception_kwargs)
            else:
                match = self.match(r'(%s)' % r'|'.join(text))
                if match:
                    return \
                        self.text[startpos:self.match_position-len(match.group(1))],\
                        match.group(1)
                else:
                    match = self.match(r".*?(?=\"|\'|#|%s)" % r'|'.join(text), re.S)
                    if not match:
                        raise exceptions.SyntaxException(
                                    "Expected: %s" % 
                                    ','.join(text), 
                                    **self.exception_kwargs)
 
    def append_node(self, nodecls, *args, **kwargs):
        kwargs.setdefault('source', self.text)
        kwargs.setdefault('lineno', self.matched_lineno)
        kwargs.setdefault('pos', self.matched_charpos)
        kwargs['filename'] = self.filename
        node = nodecls(*args, **kwargs)
        if len(self.tag):
            self.tag[-1].nodes.append(node)
        else:
            self.template.nodes.append(node)
        if isinstance(node, parsetree.Tag):
            if len(self.tag):
                node.parent = self.tag[-1]
            self.tag.append(node)
        elif isinstance(node, parsetree.ControlLine):
            if node.isend:
                self.control_line.pop()
            elif node.is_primary:
                self.control_line.append(node)
            elif len(self.control_line) and \
                    not self.control_line[-1].is_ternary(node.keyword):
                raise exceptions.SyntaxException(
                                "Keyword '%s' not a legal ternary for keyword '%s'" %
                                (node.keyword, self.control_line[-1].keyword),
                                **self.exception_kwargs)

    _coding_re = re.compile(r'#.*coding[:=]\s*([-\w.]+).*\r?\n')

    def decode_raw_stream(self, text, decode_raw, known_encoding, filename):
        """given string/unicode or bytes/string, determine encoding
           from magic encoding comment, return body as unicode
           or raw if decode_raw=False

        """
        if isinstance(text, unicode):
            m = self._coding_re.match(text)
            encoding = m and m.group(1) or known_encoding or 'ascii'
            return encoding, text

        if text.startswith(codecs.BOM_UTF8):
            text = text[len(codecs.BOM_UTF8):]
            parsed_encoding = 'utf-8'
            m = self._coding_re.match(text.decode('utf-8', 'ignore'))
            if m is not None and m.group(1) != 'utf-8':
                raise exceptions.CompileException(
                                "Found utf-8 BOM in file, with conflicting "
                                "magic encoding comment of '%s'" % m.group(1), 
                                text.decode('utf-8', 'ignore'), 
                                0, 0, filename)
        else:
            m = self._coding_re.match(text.decode('utf-8', 'ignore'))
            if m:
                parsed_encoding = m.group(1)
            else:
                parsed_encoding = known_encoding or 'ascii'

        if decode_raw:
            try:
                text = text.decode(parsed_encoding)
            except UnicodeDecodeError, e:
                raise exceptions.CompileException(
                                "Unicode decode operation of encoding '%s' failed" %
                                parsed_encoding, 
                                text.decode('utf-8', 'ignore'), 
                                0, 0, filename)

        return parsed_encoding, text

    def parse(self):
        self.encoding, self.text = self.decode_raw_stream(self.text, 
                                        not self.disable_unicode, 
                                        self.encoding,
                                        self.filename,)

        for preproc in self.preprocessor:
            self.text = preproc(self.text)
 
        # push the match marker past the 
        # encoding comment.
        self.match_reg(self._coding_re)
 
        self.textlength = len(self.text)
 
        while (True):
            if self.match_position > self.textlength: 
                break
 
            if self.match_end():
                break
            if self.match_expression():
                continue
            if self.match_control_line():
                continue
            if self.match_comment():
                continue
            if self.match_tag_start(): 
                continue
            if self.match_tag_end():
                continue
            if self.match_python_block():
                continue
            if self.match_text(): 
                continue
 
            if self.match_position > self.textlength: 
                break
            raise exceptions.CompileException("assertion failed")
 
        if len(self.tag):
            raise exceptions.SyntaxException("Unclosed tag: <%%%s>" % 
                                                self.tag[-1].keyword, 
                                                **self.exception_kwargs)
        if len(self.control_line):
            raise exceptions.SyntaxException("Unterminated control keyword: '%s'" %
                                            self.control_line[-1].keyword, 
                                            self.text, 
                                            self.control_line[-1].lineno,
                                            self.control_line[-1].pos, self.filename)
        return self.template

    def match_tag_start(self):
        match = self.match(r'''
            \<%     # opening tag
 
            ([\w\.\:]+)   # keyword
 
            ((?:\s+\w+|\s*=\s*|".*?"|'.*?')*)  # attrname, = sign, string expression
 
            \s*     # more whitespace
 
            (/)?>   # closing
 
            ''', 
 
            re.I | re.S | re.X)
 
        if match:
            keyword, attr, isend = match.group(1), match.group(2), match.group(3)
            self.keyword = keyword
            attributes = {}
            if attr:
                for att in re.findall(r"\s*(\w+)\s*=\s*(?:'([^']*)'|\"([^\"]*)\")", attr):
                    key, val1, val2 = att
                    text = val1 or val2
                    text = text.replace('\r\n', '\n')
                    attributes[key] = text
            self.append_node(parsetree.Tag, keyword, attributes)
            if isend:
                self.tag.pop()
            else:
                if keyword == 'text':
                    match = self.match(r'(.*?)(?=\</%text>)',  re.S)
                    if not match:
                        raise exceptions.SyntaxException(
                                            "Unclosed tag: <%%%s>" % 
                                            self.tag[-1].keyword, 
                                            **self.exception_kwargs)
                    self.append_node(parsetree.Text, match.group(1))
                    return self.match_tag_end()
            return True
        else: 
            return False
 
    def match_tag_end(self):
        match = self.match(r'\</%[\t ]*(.+?)[\t ]*>')
        if match:
            if not len(self.tag):
                raise exceptions.SyntaxException(
                                        "Closing tag without opening tag: </%%%s>" %
                                        match.group(1), 
                                        **self.exception_kwargs)
            elif self.tag[-1].keyword != match.group(1):
                raise exceptions.SyntaxException(
                                        "Closing tag </%%%s> does not match tag: <%%%s>" %
                                        (match.group(1), self.tag[-1].keyword),
                                        **self.exception_kwargs)
            self.tag.pop()
            return True
        else:
            return False
 
    def match_end(self):
        match = self.match(r'\Z', re.S)
        if match:
            string = match.group()
            if string:
                return string
            else:
                return True
        else:
            return False
 
    def match_text(self):
        match = self.match(r"""
                (.*?)         # anything, followed by:
                (
                 (?<=\n)(?=[ \t]*(?=%|\#\#)) # an eval or line-based 
                                             # comment preceded by a 
                                             # consumed newline and whitespace
                 |
                 (?=\${)      # an expression
                 |
                 (?=\#\*)     # multiline comment
                 |
                 (?=</?[%&])  # a substitution or block or call start or end
                              # - don't consume
                 |
                 (\\\r?\n)    # an escaped newline  - throw away
                 |
                 \Z           # end of string
                )""", re.X | re.S)
 
        if match:
            text = match.group(1)
            if text:
                self.append_node(parsetree.Text, text)
            return True
        else:
            return False
 
    def match_python_block(self):
        match = self.match(r"<%(!)?")
        if match:
            line, pos = self.matched_lineno, self.matched_charpos
            text, end = self.parse_until_text(r'%>')
            # the trailing newline helps 
            # compiler.parse() not complain about indentation
            text = adjust_whitespace(text) + "\n" 
            self.append_node(
                            parsetree.Code, 
                            text, 
                            match.group(1)=='!', lineno=line, pos=pos)
            return True
        else:
            return False
 
    def match_expression(self):
        match = self.match(r"\${")
        if match:
            line, pos = self.matched_lineno, self.matched_charpos
            text, end = self.parse_until_text(r'\|', r'}')
            if end == '|':
                escapes, end = self.parse_until_text(r'}')
            else:
                escapes = ""
            text = text.replace('\r\n', '\n')
            self.append_node(
                            parsetree.Expression, 
                            text, escapes.strip(), 
                            lineno=line, pos=pos)
            return True
        else:
            return False

    def match_control_line(self):
        match = self.match(r"(?<=^)[\t ]*(%(?!%)|##)[\t ]*((?:(?:\\r?\n)|[^\r\n])*)(?:\r?\n|\Z)", re.M)
        if match:
            operator = match.group(1)
            text = match.group(2)
            if operator == '%':
                m2 = re.match(r'(end)?(\w+)\s*(.*)', text)
                if not m2:
                    raise exceptions.SyntaxException(
                                "Invalid control line: '%s'" % 
                                text, 
                                **self.exception_kwargs)
                isend, keyword = m2.group(1, 2)
                isend = (isend is not None)
 
                if isend:
                    if not len(self.control_line):
                        raise exceptions.SyntaxException(
                                "No starting keyword '%s' for '%s'" % 
                                (keyword, text), 
                                **self.exception_kwargs)
                    elif self.control_line[-1].keyword != keyword:
                        raise exceptions.SyntaxException(
                                "Keyword '%s' doesn't match keyword '%s'" % 
                                (text, self.control_line[-1].keyword), 
                                **self.exception_kwargs)
                self.append_node(parsetree.ControlLine, keyword, isend, text)
            else:
                self.append_node(parsetree.Comment, text)
            return True
        else:
            return False

    def match_comment(self):
        """matches the multiline version of a comment"""
        match = self.match(r"<%doc>(.*?)</%doc>", re.S)
        if match:
            self.append_node(parsetree.Comment, match.group(1))
            return True
        else:
            return False
 
