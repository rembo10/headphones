import sys
import re
import unittestcompat
from unittestcompat import TestCase, TestArgs

from headphones.config.typeconv import boolext, path
from headphones.config.datamodel import OptionModel

class OptionModelTest(TestCase):

    @TestArgs(
        (1, int),
        (100, int),
        (0, int),
        ('', str),
        ('asdf', str),
        (True, bool),
    )
    def test_default_get(self, deflt, tp):
        """ test get of default value """
        p = OptionModel('KEY', 'GeneralSection', deflt, tp)
        st = {}
        p.bindToConfig(lambda:st)

        self.assertIsNotNone(p)
        self.assertIsInstance(p, OptionModel)

        act = p.get()
        self.assertIsInstance(act, tp)
        self.assertEqual(act, deflt)

    @TestArgs(
        (1, int, 1, int),
        ("1", int, 1, int),
        ("100", int, 100, int),

        ("1", boolext, True, bool),
        ("on", boolext, True, bool),

        ("hello", str, "hello", str),
    )
    def test_default_get_with_conv(self, deflt, conv, expval, exptp):
        """ test get of default value vith type conversion """
        p = OptionModel('KEY', 'GeneralSection', deflt, conv)
        st = {}
        p.bindToConfig(lambda:st)

        self.assertIsNotNone(p)
        self.assertIsInstance(p, OptionModel)

        act = p.get()
        self.assertIsInstance(act, exptp)
        self.assertEqual(act, expval)
