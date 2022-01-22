# encoding=utf8
#  This file is part of Headphones.
#
#  Headphones is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Headphones is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Headphones.  If not, see <http://www.gnu.org/licenses/>.
"""
Path pattern substitution module, see details below for syntax.

The pattern matching is loosely based on foobar2000 pattern syntax,
i.e. the notion of escaping characters with \' and optional elements
enclosed in square brackets [] is taken from there while the
substitution variable names are Perl-ish or sh-ish. The following
syntax elements are supported:
* escaped literal strings, that is everything that is enclosed
  within single quotes (like 'this');
* substitution variables, which start with dollar sign ($) and
  extend until next non-alphanumeric+underscore character
  (like $This and $5_that).
* optional elements enclosed in curly braces, which render
  nonempty value only if any variable or optional inside returned
  nonempty value, ignoring literals (like {'{'$That'}'}).
"""

from enum import Enum

__author__ = "Andrzej Ciarkowski <andrzej.ciarkowski@gmail.com>"


class _PatternElement(object):
    '''ABC for hierarchy of path name renderer pattern elements.'''

    def render(self, replacement):
        # type: (Mapping[str,str]) -> str
        '''Format this _PatternElement into string using provided substitution dictionary.'''
        raise NotImplementedError()

    def __ne__(self, other):
        return not self == other


class _Generator(_PatternElement):
    # pylint: disable=abstract-method
    '''Tagging interface for "content-generating" elements like replacement or optional block.'''
    pass


class _Replacement(_Generator):
    '''Replacement variable, eg. $title.'''

    def __init__(self, pattern):
        # type: (str)
        self._pattern = pattern

    def render(self, replacement):
        # type: (Mapping[str,str]) -> str
        res = replacement.get(self._pattern, self._pattern)
        if res is None:
            return ''
        else:
            return res

    def __str__(self):
        return self._pattern

    @property
    def pattern(self):
        return self._pattern

    def __eq__(self, other):
        return isinstance(other, _Replacement) and \
            self._pattern == other.pattern


class _LiteralText(_PatternElement):
    '''Just a plain piece of text to be rendered "as is".'''

    def __init__(self, text):
        # type: (str)
        self._text = text

    def render(self, replacement):
        # type: (Mapping[str,str]) -> str
        return self._text

    def __str__(self):
        return self._text

    @property
    def text(self):
        return self._text

    def __eq__(self, other):
        return isinstance(other, _LiteralText) and self._text == other.text


class _OptionalBlock(_Generator):
    '''Optional block will render its contents only if any _Generator in its scope did return non-empty result.'''

    def __init__(self, scope):
        # type: ([_PatternElement])
        self._scope = scope

    def render(self, replacement):
        # type: (Mapping[str,str]) -> str
        res = [(isinstance(x, _Generator), x.render(replacement)) for x in self._scope]
        if any((t[0] and t[1] is not None and len(t[1]) != 0) for t in res):
            return "".join(t[1] for t in res)
        else:
            return ""

    def __eq__(self, other):
        """
        :type other: _OptionalBlock
        """
        return isinstance(other, _OptionalBlock) and self._scope == other._scope


_OPTIONAL_START = '{'
_OPTIONAL_END = '}'
_ESCAPE_CHAR = '\''
_REPLACEMENT_START = '$'


def _is_replacement_valid(c):
    # type: (str) -> bool
    return c.isalnum() or c == '_'


class _State(Enum):
    LITERAL = 0
    ESCAPE = 1
    REPLACEMENT = 2


def _append_literal(scope, text):
    # type: ([_PatternElement], str) -> None
    '''Append literal text to the scope BUT ONLY if it's not an empty string.'''
    if len(text) == 0:
        return
    scope.append(_LiteralText(text))


class Warnings(Enum):
    '''Pattern parsing warnings, as stored withing warnings property of Pattern object after parsing.'''
    UNCLOSED_ESCAPE = 'Warnings.UNCLOSED_ESCAPE'
    UNCLOSED_OPTIONAL = 'Warnings.UNCLOSED_OPTIONAL'


def _parse_pattern(pattern, warnings):
    # type: (str,MutableSet[Warnings]) -> [_PatternElement]
    '''Parse path pattern text into list of _PatternElements, put warnings into the provided set.'''
    start = 0                   # index of current state start char
    root_scope = []             # here our _PatternElements will reside
    scope_stack = [root_scope]  # stack so that we can return to the outer scope
    scope = root_scope          # pointer to the current list for _OptionalBlock
    inside_optional = 0         # nesting level of _OptionalBlocks
    state = _State.LITERAL      # current state
    for i, c in enumerate(pattern):
        if state is _State.ESCAPE:
            if c != _ESCAPE_CHAR:
                # only escape char can get us out of _State.ESCAPE
                continue
            _append_literal(scope, pattern[start + 1:i])
            state = _State.LITERAL
            start = i + 1
            # after exiting _State.ESCAPE on escape char no more processing of c
            continue
        if state is _State.REPLACEMENT:
            if _is_replacement_valid(c):
                # only replacement invalid can get us out _State.REPLACEMENT
                continue
            scope.append(_Replacement(pattern[start:i]))
            state = _State.LITERAL
            start = i
            # intentional fall-through to _State.LITERAL
        assert state is _State.LITERAL
        if c == _ESCAPE_CHAR:
            _append_literal(scope, pattern[start:i])
            state = _State.ESCAPE
            start = i
            # no more processing to escape char c
            continue
        if c == _REPLACEMENT_START:
            _append_literal(scope, pattern[start:i])
            state = _State.REPLACEMENT
            start = i
            # no more processing to replacement char c
            continue
        if c == _OPTIONAL_START:
            _append_literal(scope, pattern[start:i])
            inside_optional += 1
            new_scope = []
            scope_stack.append(new_scope)
            scope = new_scope
            start = i + 1
            continue
        if c == _OPTIONAL_END:
            if inside_optional == 0:
                # no optional block to end, just treat as literal text
                continue
            inside_optional -= 1
            _append_literal(scope, pattern[start:i])
            scope_stack.pop()
            prev_scope = scope_stack[-1]
            prev_scope.append(_OptionalBlock(scope))
            scope = prev_scope
            start = i + 1
        # fi
    # done
    if state is _State.ESCAPE:
        warnings.add(Warnings.UNCLOSED_ESCAPE)
    if inside_optional != 0:
        warnings.add(Warnings.UNCLOSED_OPTIONAL)
    if state is _State.REPLACEMENT:
        root_scope.append(_Replacement(pattern[start:]))
    else:
        # don't care about unclosed elements :P
        _append_literal(root_scope, pattern[start:])
    return root_scope


class Pattern(object):
    '''Stores preparsed rename pattern for repeated use.

       If using the same pattern repeatedly it is much more effective
       to parse the pattern into Pattern object and use it instead of
       parsing the textual pattern on each substitution. To use Pattern
       object for substitution simply call it as it was function
       providing dictionary as an argument (see __call__()).'''

    def __init__(self, pattern):
        # type: (str)
        self._warnings = set()
        self._pattern = _parse_pattern(pattern, self._warnings)

    def __call__(self, replacement):
        # type: (Mapping[str,str]) -> str
        '''Execute path rendering/substitution based on replacement dictionary.'''
        return "".join(p.render(replacement) for p in self._pattern)

    def _get_warnings(self):
        # type: () -> str
        '''Getter for warnings property.'''
        return self._warnings

    warnings = property(_get_warnings, doc="Access warnings raised during pattern parsing")


def render(pattern, replacement):
    # type: (str, Mapping[str,str]) -> (str, AbstractSet[Warnings])
    '''Render path name based on replacement pattern and dictionary.'''
    p = Pattern(pattern)
    return p(replacement), p.warnings


if __name__ == "__main__":
    # primitive test ;)
    p = Pattern("{$Disc.}$Track - $Artist - $Title{ [$Year]}")
    d = {'$Disc': '', '$Track': '05', '$Artist': 'Grzegżółka', '$Title': 'Błona kapłona', '$Year': '2019'}
    assert p(d) == "05 - Grzegżółka - Błona kapłona [2019]"
