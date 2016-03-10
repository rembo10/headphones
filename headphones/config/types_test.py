import sys
import re
import unittestcompat
from unittestcompat import TestCase, TestArgs

from headphones.config.types import path

class ConfigPathTest(TestCase):

    def test_path(self):
        p = path('/tmp')

        self.assertIsNotNone(p)
        self.assertIsInstance(p, path)

    def test_path_call(self):
        s = '/tmp'
        p1 = path(s)
        self.assertEqual(p1, s)

    def test_path_static(self):
        s = '/tmp'
        p2 = path.__call__(s)
        self.assertEqual(p2, s)

    def test_path_static_equal_call(self):
        s = '/tmp'
        p1 = path(s)
        p2 = path.__call__(s)
        self.assertEqual(p1, p2)

    def test_path_repr(self):
        s = '/tmp'
        p1 = path(s)
        self.assertIn('headphones.config.path', p1.__repr__())

    @TestArgs(
        (None),
        (''),
        ('     '),
    )
    def test_empty_path(self, s):
        """ headphones.path does not modify empty strings """
        p1 = path(s)
        a = str(p1)
        e = str(s)
        self.assertEqual(a, e)