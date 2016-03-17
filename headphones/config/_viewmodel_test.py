from unittestcompat import TestCase, TestArgs
from _viewmodel import OptionBase, OptionInternal, OptionDeprecated

class OptionInternalTest(TestCase):

    # ---------------------------------------------------------------
    # __init__
    # ---------------------------------------------------------------
    def test_init(self):
        """ OptionInternal: __init__ """
        p = OptionInternal('KEY', 'GeneralSection', 0, typeconv=int)

        self.assertIsNotNone(p)
        self.assertIsInstance(p, OptionBase)
        self.assertIsInstance(p, OptionInternal)

    # ---------------------------------------------------------------
    # render
    # ---------------------------------------------------------------
    def test_render(self):
        """ OptionInternal: render """
        p = OptionInternal('KEY', 'GeneralSection', 0, typeconv=int)

        self.assertEqual(p.render(), "")


class OptionDeprecatedTest(TestCase):

    # ---------------------------------------------------------------
    # __init__
    # ---------------------------------------------------------------
    def test_init(self):
        """ OptionDeprecated: __init__ """
        p = OptionDeprecated('KEY', 'GeneralSection', 0, typeconv=int)

        self.assertIsNotNone(p)
        self.assertIsInstance(p, OptionBase)
        self.assertIsInstance(p, OptionDeprecated)

    # ---------------------------------------------------------------
    # render
    # ---------------------------------------------------------------
    def test_render(self):
        """ OptionDeprecated: render """
        p = OptionDeprecated('KEY', 'GeneralSection', 0, typeconv=int)

        self.assertEqual(p.render(), "")