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
Test module for pathrender.
"""
import headphones.pathrender as _pr
from headphones.pathrender import Pattern, Warnings

from unittestcompat import TestCase


__author__ = "Andrzej Ciarkowski <andrzej.ciarkowski@gmail.com>"


class PathRenderTest(TestCase):
    """
    Tests for pathrender module.
    """

    def test_parsing(self):
        """pathrender: pattern parsing"""
        pattern = Pattern(u"{$Disc.}$Track - $Artist - $Title{ [$Year]}")
        expected = [
            _pr._OptionalBlock([
                _pr._Replacement(u"$Disc"),
                _pr._LiteralText(u".")
            ]),
            _pr._Replacement(u"$Track"),
            _pr._LiteralText(u" - "),
            _pr._Replacement(u"$Artist"),
            _pr._LiteralText(u" - "),
            _pr._Replacement(u"$Title"),
            _pr._OptionalBlock([
                _pr._LiteralText(u" ["),
                _pr._Replacement(u"$Year"),
                _pr._LiteralText(u"]")
            ])
        ]
        self.assertEqual(expected, pattern._pattern)
        self.assertItemsEqual([], pattern.warnings)

    def test_parsing_warnings(self):
        """pathrender: pattern parsing with warnings"""
        pattern = Pattern(u"{$Disc.}$Track - $Artist - $Title{ [$Year]")
        self.assertEqual(set([Warnings.UNCLOSED_OPTIONAL]), pattern.warnings)
        pattern = Pattern(u"{$Disc.}$Track - $Artist - $Title{ [$Year]'}")
        self.assertEqual(set([Warnings.UNCLOSED_ESCAPE, Warnings.UNCLOSED_OPTIONAL]), pattern.warnings)

    def test_replacement(self):
        """pathrender: _Replacement variable substitution"""
        r = _pr._Replacement(u"$Title")
        subst = {'$Title': 'foo', '$Track': 'bar'}
        res = r.render(subst)
        self.assertEqual(res, u'foo', 'check valid replacement')
        subst = {}
        res = r.render(subst)
        self.assertEqual(res, u'$Title', 'check missing replacement')
        subst = {'$Title': None}
        res = r.render(subst)
        self.assertEqual(res, '', 'check render() works with None')

    def test_literal(self):
        """pathrender: _Literal text rendering"""
        l = _pr._LiteralText(u"foo")
        subst = {'$foo': 'bar'}
        res = l.render(subst)
        self.assertEqual(res, 'foo')

    def test_optional(self):
        """pathrender: _OptionalBlock element processing"""
        o = _pr._OptionalBlock([
            _pr._Replacement(u"$Title"),
            _pr._LiteralText(u".foobar")
        ])
        subst = {'$Title': 'foo', '$Track': 'bar'}
        res = o.render(subst)
        self.assertEqual(res, u'foo.foobar', 'check non-empty replacement')
        subst = {'$Title': ''}
        res = o.render(subst)
        self.assertEqual(res, '', 'check empty replacement')
        subst = {'$Title': None}
        res = o.render(subst)
        self.assertEqual(res, '', 'check render() works with None')
